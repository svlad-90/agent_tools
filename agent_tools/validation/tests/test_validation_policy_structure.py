from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from agent_tools.validation.policy import load_validation_policy
from agent_tools.validation.policy import policy_summary


VALIDATION_ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path, *, remote: str = "git@github.com:fork/agent_tools.git") -> None:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "remote", "add", "origin", remote)


def _write_policy_root(root: Path) -> None:
    (root / "repos").mkdir(parents=True)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "commit-message",
                        "backend": "builtin",
                        "cost": "medium",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_validation_policy_files_are_mappings_with_unique_check_ids() -> None:
    paths = [
        VALIDATION_ROOT / "workspace-policy.yaml",
        *sorted((VALIDATION_ROOT / "repos").glob("*.yaml")),
    ]
    assert paths
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path
        check_ids: list[str] = []
        for check in data.get("checks", []):
            assert isinstance(check, dict), path
            assert isinstance(check.get("id"), str) and check["id"], path
            assert isinstance(check.get("description"), str) and check["description"], path
            assert check.get("backend") in {
                "builtin",
                "command",
                "paf",
                "task_check",
                "task_command",
            }, path
            assert check.get("cost") in {"cheap", "medium", "heavy"}, path
            if "command" in check:
                assert isinstance(check["command"], list), path
            if "suggested_command" in check:
                assert isinstance(check["suggested_command"], list) and check["suggested_command"], path
            check_ids.append(check["id"])
        assert len(check_ids) == len(set(check_ids)), path


def test_repo_policy_files_have_identity_evidence() -> None:
    for path in sorted((VALIDATION_ROOT / "repos").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        repo = data.get("repo")
        assert isinstance(repo, dict), path
        assert isinstance(repo.get("id"), str) and repo["id"], path
        assert repo.get("names") or repo.get("github_repos"), path
        files = repo.get("characteristic_files")
        assert isinstance(files, list) and files, path


def test_validation_policy_loads_workspace_repo_and_task_layers(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    _write_policy_root(policy_root)
    (policy_root / "repos" / "agent_tools.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "agent_tools",
                    "names": ["agent_tools"],
                    "github_repos": ["github.com/svlad-90/agent_tools"],
                    "allow_forks": True,
                    "characteristic_files": ["agent_tools", "install-agent-tools.py"],
                },
                "checks": [
                    {
                        "id": "python-parse-check-changed",
                        "backend": "builtin",
                        "cost": "medium",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    (task_dir / "TASK_GUARD.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "task-smoke",
                        "backend": "command",
                        "cost": "cheap",
                        "command": [sys.executable, "-c", "raise SystemExit(0)"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "agent_tools").mkdir()
    (repo / "install-agent-tools.py").write_text("print('install')\n", encoding="utf-8")

    policy = load_validation_policy(repo, task_dir=task_dir, policy_root=policy_root)

    assert policy.repo_identity is not None
    assert policy.repo_identity.repo_id == "agent_tools"
    assert [document.level for document in policy.documents] == ["workspace", "repo", "task"]
    assert [check.check_id for check in policy.checks] == [
        "commit-message",
        "python-parse-check-changed",
        "task-smoke",
    ]
    assert policy.checks[0].description is None
    assert policy.checks[1].description is None
    assert policy.checks[2].suggested_command == ()
    assert [check.level for check in policy.checks] == ["workspace", "repo", "task"]
    assert policy.policy_hash.startswith("sha256:")


def test_validation_policy_summary_exports_check_metadata() -> None:
    summary = policy_summary(VALIDATION_ROOT.parents[1], policy_root=VALIDATION_ROOT)

    checks = {check["id"]: check for check in summary["checks"]}

    assert checks["workspace-file-hygiene"]["description"]
    assert checks["workspace-file-hygiene"]["suggested_command"] == [
        "git",
        "status",
        "--short",
    ]


def test_validation_policy_requires_characteristic_files_for_fork_match(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    _write_policy_root(policy_root)
    (policy_root / "repos" / "agent_tools.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "agent_tools",
                    "names": ["agent_tools"],
                    "github_repos": ["github.com/svlad-90/agent_tools"],
                    "allow_forks": True,
                    "characteristic_files": ["install-agent-tools.py"],
                },
                "checks": [{"id": "repo-check", "backend": "builtin", "cost": "cheap"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    _init_repo(repo)

    policy = load_validation_policy(repo, policy_root=policy_root)

    assert policy.repo_identity is None
    assert [check.check_id for check in policy.checks] == ["commit-message"]


def test_validation_policy_verify_command_can_reject_matching_repo(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    _write_policy_root(policy_root)
    (policy_root / "repos" / "agent_tools.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "agent_tools",
                    "names": ["agent_tools"],
                    "characteristic_files": ["install-agent-tools.py"],
                    "verify_command": [sys.executable, "-c", "raise SystemExit(7)"],
                },
                "checks": [{"id": "repo-check", "backend": "builtin", "cost": "cheap"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "agent_tools"
    _init_repo(repo, remote="git@github.com:svlad-90/agent_tools.git")
    (repo / "install-agent-tools.py").write_text("print('install')\n", encoding="utf-8")

    policy = load_validation_policy(repo, policy_root=policy_root)

    assert policy.repo_identity is None
    assert [check.check_id for check in policy.checks] == ["commit-message"]


def test_validation_policy_summary_lists_policy_documents(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    _write_policy_root(policy_root)
    repo = tmp_path / "repo"
    _init_repo(repo, remote="git@github.com:other/repo.git")

    summary = policy_summary(repo, policy_root=policy_root)

    assert summary["repo_id"] is None
    assert summary["policy_documents"] == [
        {
            "path": str(policy_root.resolve() / "workspace-policy.yaml"),
            "level": "workspace",
        }
    ]


def test_validation_policy_rejects_invalid_check_schema(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    (policy_root / "repos").mkdir(parents=True)
    (policy_root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "bad-check",
                        "backend": "surprise",
                        "cost": "cheap",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    _init_repo(repo)

    try:
        load_validation_policy(repo, policy_root=policy_root)
    except ValueError as exc:
        assert "invalid backend" in str(exc)
    else:
        raise AssertionError("invalid check backend was accepted")


def test_validation_policy_requires_command_for_command_backend(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    (policy_root / "repos").mkdir(parents=True)
    (policy_root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "missing-command",
                        "description": "Broken command check.",
                        "backend": "command",
                        "cost": "cheap",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    _init_repo(repo)

    try:
        load_validation_policy(repo, policy_root=policy_root)
    except ValueError as exc:
        assert "must define command" in str(exc)
    else:
        raise AssertionError("command backend without command was accepted")
