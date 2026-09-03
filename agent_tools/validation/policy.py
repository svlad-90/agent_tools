"""Declarative validation policy model and loader."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence

import yaml


JsonObject = dict[str, Any]
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_ROOT = WORKSPACE_ROOT / "agent_tools" / "validation"
CHECK_BACKENDS = {"builtin", "command", "paf", "task_check", "task_command"}
CHECK_COSTS = {"cheap", "medium", "heavy"}
CHECK_LEVELS = {"workspace", "repo", "task"}
_GITHUB_RE = re.compile(
    r"(?:github\.com[:/])(?P<owner>[^/\s:]+)/(?P<name>[^/\s]+?)(?:\.git)?$"
)


@dataclass(frozen=True)
class RepoIdentity:
    repo_id: str
    names: tuple[str, ...]
    github_repos: tuple[str, ...]
    allow_forks: bool
    characteristic_files: tuple[str, ...]
    verify_command: tuple[str, ...] | None
    policy_path: Path | None


@dataclass(frozen=True)
class CheckConfig:
    check_id: str
    description: str | None
    level: str
    backend: str
    cost: str
    required: bool
    command: tuple[str, ...]
    suggested_command: tuple[str, ...]
    cwd: str | None
    scenario: str | None
    profile: str | None
    task: str | None
    strict_warnings: bool
    config: Mapping[str, Any]
    policy_path: Path | None


@dataclass(frozen=True)
class PolicyDocument:
    path: Path
    level: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class ResolvedPolicy:
    repo: Path
    policy_root: Path
    repo_identity: RepoIdentity | None
    checks: tuple[CheckConfig, ...]
    documents: tuple[PolicyDocument, ...]
    policy_hash: str


def load_validation_policy(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> ResolvedPolicy:
    """Load workspace, repository, and optional task-local policy layers."""
    root = (policy_root or DEFAULT_POLICY_ROOT).resolve()
    repo = repo.resolve()
    workspace_path = root / "workspace-policy.yaml"
    workspace_policy = _load_policy_document(workspace_path, "workspace", required=False)
    documents = [workspace_policy]
    workspace_checks = _checks_from_data(
        workspace_policy.data,
        workspace_path,
        default_level="workspace",
    )

    repo_identity, repo_document, repo_checks = _matched_repo_policy(repo, root)
    if repo_document is not None:
        documents.append(repo_document)

    task_document, task_checks = _task_checks(task_dir)
    if task_document is not None:
        documents.append(task_document)

    checks = _dedupe_checks([*workspace_checks, *repo_checks, *task_checks])
    policy_hash = _policy_hash(repo_identity, checks, documents)
    return ResolvedPolicy(
        repo=repo,
        policy_root=root,
        repo_identity=repo_identity,
        checks=checks,
        documents=tuple(documents),
        policy_hash=policy_hash,
    )


def policy_summary(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> dict[str, Any]:
    policy = load_validation_policy(repo, task_dir=task_dir, policy_root=policy_root)
    return {
        "repo": str(policy.repo),
        "repo_id": policy.repo_identity.repo_id if policy.repo_identity is not None else None,
        "policy_hash": policy.policy_hash,
        "policy_documents": [
            {
                "path": str(document.path),
                "level": document.level,
            }
            for document in policy.documents
        ],
        "checks": [
            {
                "id": check.check_id,
                "description": check.description,
                "level": check.level,
                "backend": check.backend,
                "cost": check.cost,
                "required": check.required,
                "suggested_command": list(check.suggested_command),
            }
            for check in policy.checks
        ],
    }


def workspace_root_from_env() -> Path:
    value = os.environ.get("AGENT_TOOLS_WORKSPACE_ROOT")
    return Path(value).resolve() if value else WORKSPACE_ROOT


def _matched_repo_policy(
    repo: Path,
    root: Path,
) -> tuple[RepoIdentity | None, PolicyDocument | None, tuple[CheckConfig, ...]]:
    for path in sorted((root / "repos").glob("*.yaml")):
        document = _load_policy_document(path, "repo", required=True)
        identity = _identity_from_data(document.data, path)
        if _matches_identity(repo, identity):
            return identity, document, _checks_from_data(document.data, path, default_level="repo")
    return None, None, ()


def _matches_identity(repo: Path, identity: RepoIdentity) -> bool:
    for filename in identity.characteristic_files:
        if not (repo / filename).exists():
            return False
    if identity.verify_command is not None and not _verify_repo(repo, identity.verify_command):
        return False
    urls = _remote_urls(repo)
    if not urls and not identity.github_repos and identity.names:
        return repo.name in identity.names
    normalized_policy_urls = {_normalize_remote_url(url) for url in identity.github_repos}
    policy_slugs = {_split_slug(slug) for slug in identity.github_repos if "/" in slug}
    for url in urls.values():
        normalized = _normalize_remote_url(url)
        if normalized in normalized_policy_urls:
            return True
        slug = _github_slug(url)
        if slug is None:
            continue
        if slug in policy_slugs:
            return True
        if identity.allow_forks and slug[1] in identity.names:
            return True
    return False


def _verify_repo(repo: Path, command: Sequence[str]) -> bool:
    completed = subprocess.run(
        list(command),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.returncode == 0


def _remote_urls(repo: Path) -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    result: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result.setdefault(parts[0], parts[1])
    return result


def _normalize_remote_url(url: str) -> str:
    value = url.strip()
    value = value.removeprefix("git@")
    value = value.removeprefix("ssh://git@")
    value = value.removeprefix("https://")
    value = value.removeprefix("http://")
    return value.removesuffix(".git")


def _github_slug(url: str) -> tuple[str, str] | None:
    normalized = _normalize_remote_url(url)
    match = _GITHUB_RE.search(normalized)
    if not match:
        return None
    return match.group("owner"), match.group("name")


def _split_slug(value: str) -> tuple[str, str]:
    normalized = _normalize_remote_url(value)
    if normalized.startswith("github.com/"):
        normalized = normalized[len("github.com/") :]
    parts = normalized.removesuffix(".git").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"invalid GitHub repository slug: {value!r}")
    return parts[0], parts[1]


def _task_checks(task_dir: Path | None) -> tuple[PolicyDocument | None, tuple[CheckConfig, ...]]:
    if task_dir is None:
        return None, ()
    path = task_dir / "TASK_GUARD.yaml"
    if not path.is_file():
        return None, ()
    document = _load_policy_document(path, "task", required=True)
    return document, _checks_from_data(document.data, path, default_level="task")


def _checks_from_data(
    data: Mapping[str, Any],
    path: Path,
    *,
    default_level: str,
) -> tuple[CheckConfig, ...]:
    checks: list[CheckConfig] = []
    for raw_check in _list_value(data.get("checks"), path=path, key="checks"):
        if not isinstance(raw_check, Mapping):
            raise ValueError(f"{path}: checks entries must be mappings")
        check_id = _required_str(raw_check, "id", path)
        level = str(raw_check.get("level", default_level))
        backend = str(raw_check.get("backend", "builtin"))
        cost = str(raw_check.get("cost", "medium"))
        if level not in CHECK_LEVELS:
            raise ValueError(f"{path}: check {check_id!r} has invalid level {level!r}")
        if backend not in CHECK_BACKENDS:
            raise ValueError(f"{path}: check {check_id!r} has invalid backend {backend!r}")
        if cost not in CHECK_COSTS:
            raise ValueError(f"{path}: check {check_id!r} has invalid cost {cost!r}")
        command = tuple(str(part) for part in _list_value(raw_check.get("command"), path=path, key="command"))
        if backend == "command" and not command:
            raise ValueError(f"{path}: check {check_id!r} with command backend must define command")
        checks.append(
            CheckConfig(
                check_id=check_id,
                description=_optional_str(raw_check.get("description")),
                level=level,
                backend=backend,
                cost=cost,
                required=bool(raw_check.get("required", True)),
                command=command,
                suggested_command=tuple(
                    str(part)
                    for part in _list_value(
                        raw_check.get("suggested_command"),
                        path=path,
                        key="suggested_command",
                    )
                ),
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
    names = tuple(
        str(item) for item in _list_value(repo_data.get("names", [repo_id]), path=path, key="names")
    )
    github_repos = tuple(
        str(item) for item in _list_value(repo_data.get("github_repos"), path=path, key="github_repos")
    )
    characteristic_files = tuple(
        str(item)
        for item in _list_value(
            repo_data.get("characteristic_files"),
            path=path,
            key="characteristic_files",
        )
    )
    verify_command_value = repo_data.get("verify_command")
    verify_command = (
        tuple(
            str(part)
            for part in _list_value(verify_command_value, path=path, key="verify_command")
        )
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
    repo_identity: RepoIdentity | None,
    checks: Iterable[CheckConfig],
    documents: Iterable[PolicyDocument],
) -> str:
    payload = {
        "repo_id": repo_identity.repo_id if repo_identity else None,
        "documents": [
            {
                "path": str(document.path),
                "level": document.level,
                "data": document.data,
            }
            for document in documents
        ],
        "checks": [
            {
                "id": check.check_id,
                "description": check.description,
                "level": check.level,
                "backend": check.backend,
                "cost": check.cost,
                "required": check.required,
                "suggested_command": list(check.suggested_command),
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


def _load_policy_document(path: Path, level: str, *, required: bool) -> PolicyDocument:
    if not path.is_file():
        if required:
            raise ValueError(f"{path}: policy file is missing")
        return PolicyDocument(path=path, level=level, data={})
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"{path}: top-level YAML value must be a mapping")
    return PolicyDocument(path=path, level=level, data=data)


def _list_value(value: Any, *, path: Path, key: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"{path}: expected list value for {key!r}, got {type(value).__name__}")


def _required_str(data: Mapping[str, Any], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: missing required string key {key!r}")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
