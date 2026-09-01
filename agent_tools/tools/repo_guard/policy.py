"""Policy loading and repository identity resolution for repo_guard."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Mapping

import yaml

from .git_context import github_slug
from .git_context import normalize_remote_url
from .git_context import remote_urls
from .models import CheckConfig
from .models import RepoIdentity


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_ROOT = WORKSPACE_ROOT / "agent_tools" / "validation"


def load_policy(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> tuple[RepoIdentity | None, tuple[CheckConfig, ...], str]:
    root = policy_root or DEFAULT_POLICY_ROOT
    workspace_policy = _load_yaml(root / "workspace-policy.yaml")
    workspace_checks = _checks_from_data(workspace_policy, root / "workspace-policy.yaml")
    repo_identity, repo_checks = _matched_repo_policy(repo, root)
    task_checks = _task_checks(task_dir)
    checks = _dedupe_checks([*workspace_checks, *repo_checks, *task_checks])
    policy_hash = _policy_hash(workspace_policy, repo_identity, checks)
    return repo_identity, checks, policy_hash


def policy_summary(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> dict[str, Any]:
    repo_identity, checks, policy_hash = load_policy(
        repo,
        task_dir=task_dir,
        policy_root=policy_root,
    )
    return {
        "repo": str(repo),
        "repo_id": repo_identity.repo_id if repo_identity is not None else None,
        "policy_hash": policy_hash,
        "checks": [
            {
                "id": check.check_id,
                "level": check.level,
                "backend": check.backend,
                "cost": check.cost,
                "required": check.required,
            }
            for check in checks
        ],
    }


def _matched_repo_policy(repo: Path, root: Path) -> tuple[RepoIdentity | None, tuple[CheckConfig, ...]]:
    for path in sorted((root / "repos").glob("*.yaml")):
        data = _load_yaml(path)
        identity = _identity_from_data(data, path)
        if _matches_identity(repo, identity):
            return identity, _checks_from_data(data, path)
    return None, ()


def _matches_identity(repo: Path, identity: RepoIdentity) -> bool:
    for filename in identity.characteristic_files:
        if not (repo / filename).exists():
            return False
    if identity.verify_command is not None:
        completed = subprocess.run(
            list(identity.verify_command),
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            return False
    urls = remote_urls(repo)
    if not urls and not identity.github_repos and identity.names:
        return repo.name in identity.names
    normalized_policy_urls = {normalize_remote_url(url) for url in identity.github_repos}
    policy_slugs = {_split_slug(slug) for slug in identity.github_repos if "/" in slug}
    for url in urls.values():
        normalized = normalize_remote_url(url)
        if normalized in normalized_policy_urls:
            return True
        slug = github_slug(url)
        if slug is None:
            continue
        if slug in policy_slugs:
            return True
        if identity.allow_forks and slug[1] in identity.names:
            return True
    return False


def _split_slug(value: str) -> tuple[str, str]:
    normalized = normalize_remote_url(value)
    if normalized.startswith("github.com/"):
        normalized = normalized[len("github.com/") :]
    owner, name = normalized.removesuffix(".git").split("/", 1)
    return owner, name


def _task_checks(task_dir: Path | None) -> tuple[CheckConfig, ...]:
    if task_dir is None:
        return ()
    path = task_dir / "TASK_GUARD.yaml"
    if not path.is_file():
        return ()
    return _checks_from_data(_load_yaml(path), path)


def _checks_from_data(data: Mapping[str, Any], path: Path) -> tuple[CheckConfig, ...]:
    checks: list[CheckConfig] = []
    for raw_check in _list_value(data.get("checks")):
        if not isinstance(raw_check, Mapping):
            raise ValueError(f"{path}: checks entries must be mappings")
        check_id = _required_str(raw_check, "id", path)
        checks.append(
            CheckConfig(
                check_id=check_id,
                level=str(raw_check.get("level", "repo")),
                backend=str(raw_check.get("backend", "builtin")),
                cost=str(raw_check.get("cost", "medium")),
                required=bool(raw_check.get("required", True)),
                command=tuple(str(part) for part in _list_value(raw_check.get("command"))),
                cwd=_optional_str(raw_check.get("cwd")),
                scenario=_optional_str(raw_check.get("scenario")),
                profile=_optional_str(raw_check.get("profile")),
                task=_optional_str(raw_check.get("task")),
                strict_warnings=bool(raw_check.get("strict_warnings", False)),
                config=dict(raw_check),
                policy_path=path,
            )
        )
    return tuple(checks)


def _identity_from_data(data: Mapping[str, Any], path: Path) -> RepoIdentity:
    repo_data = data.get("repo")
    if not isinstance(repo_data, Mapping):
        raise ValueError(f"{path}: missing repo mapping")
    repo_id = _required_str(repo_data, "id", path)
    names = tuple(str(item) for item in _list_value(repo_data.get("names", [repo_id])))
    github_repos = tuple(str(item) for item in _list_value(repo_data.get("github_repos")))
    characteristic_files = tuple(
        str(item) for item in _list_value(repo_data.get("characteristic_files"))
    )
    verify_command_value = repo_data.get("verify_command")
    verify_command = (
        tuple(str(part) for part in _list_value(verify_command_value))
        if verify_command_value is not None
        else None
    )
    return RepoIdentity(
        repo_id=repo_id,
        names=names,
        github_repos=github_repos,
        allow_forks=bool(repo_data.get("allow_forks", True)),
        characteristic_files=characteristic_files,
        verify_command=verify_command,
        policy_path=path,
    )


def _policy_hash(
    workspace_policy: Mapping[str, Any],
    repo_identity: RepoIdentity | None,
    checks: Iterable[CheckConfig],
) -> str:
    payload = {
        "workspace_policy": workspace_policy,
        "repo_id": repo_identity.repo_id if repo_identity else None,
        "checks": [
            {
                "id": check.check_id,
                "level": check.level,
                "backend": check.backend,
                "cost": check.cost,
                "required": check.required,
                "config": check.config,
            }
            for check in checks
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _dedupe_checks(checks: list[CheckConfig]) -> tuple[CheckConfig, ...]:
    result: list[CheckConfig] = []
    seen: set[str] = set()
    for check in checks:
        if check.check_id in seen:
            continue
        seen.add(check.check_id)
        result.append(check)
    return tuple(result)


def _load_yaml(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{path}: top-level YAML value must be a mapping")
    return data


def _list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"expected list value, got {type(value).__name__}")


def _required_str(data: Mapping[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: missing required string key {key!r}")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def workspace_root_from_env() -> Path:
    value = os.environ.get("AGENT_TOOLS_WORKSPACE_ROOT")
    return Path(value).resolve() if value else WORKSPACE_ROOT
