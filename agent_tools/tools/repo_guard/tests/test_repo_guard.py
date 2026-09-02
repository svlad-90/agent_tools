from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from agent_tools.tools.repo_guard import main
from agent_tools.tools.repo_guard.git_context import head_commit
from agent_tools.tools.repo_guard.git_context import pre_push_dry_run_stdin
from agent_tools.tools.repo_guard.policy import load_policy
from agent_tools.tools.repo_guard.policy import policy_summary
from agent_tools.tools.repo_guard.runner import compact_report
from agent_tools.tools.repo_guard.runner import pre_push
from agent_tools.tools.repo_guard.runner import pre_push_dry_run
from agent_tools.tools.repo_guard.runner import validate
from agent_tools.tools.task_context import set_slot


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


def _commit(repo: Path, message: str = "Add change") -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message, "-s")
    return head_commit(repo)


def _policy_root(tmp_path: Path) -> Path:
    root = tmp_path / "policy"
    (root / "repos").mkdir(parents=True)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "workspace-file-hygiene",
                        "level": "workspace",
                        "backend": "builtin",
                        "cost": "cheap",
                        "required": True,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def test_repo_policy_matches_github_fork_by_repo_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "agent_tools").mkdir()
    (repo / "install-agent-tools.py").write_text("print('install')\n", encoding="utf-8")
    _commit(repo)
    root = _policy_root(tmp_path)
    (root / "repos" / "agent_tools.yaml").write_text(
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

    identity, checks, _policy_hash = load_policy(repo, policy_root=root)

    assert identity is not None
    assert identity.repo_id == "agent_tools"
    assert [check.check_id for check in checks] == [
        "workspace-file-hygiene",
        "python-parse-check-changed",
    ]


def test_pre_push_runs_non_heavy_checks_and_requires_heavy_receipt(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    commit = _commit(repo)
    root = _policy_root(tmp_path)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "workspace-file-hygiene",
                        "backend": "builtin",
                        "cost": "cheap",
                    },
                    {
                        "id": "runtime-matrix",
                        "backend": "command",
                        "cost": "heavy",
                        "command": [sys.executable, "-c", "raise SystemExit(0)"],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    stdin_text = f"refs/heads/topic {commit} refs/heads/topic {'0' * 40}\n"

    result = pre_push(
        repo,
        remote_name="origin",
        remote_url="git@github.com:fork/repo.git",
        stdin_text=stdin_text,
        policy_root=root,
    )

    assert result.status == "fail"
    assert [(check.check_id, check.status) for check in result.checks] == [
        ("workspace-file-hygiene", "pass"),
        ("runtime-matrix", "fail"),
    ]
    assert "requires a current validation receipt" in compact_report(result)


def test_validate_include_heavy_records_receipt_used_by_pre_push(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    commit = _commit(repo)
    root = _policy_root(tmp_path)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "runtime-matrix",
                        "backend": "command",
                        "cost": "heavy",
                        "command": [sys.executable, "-c", "raise SystemExit(0)"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    stdin_text = f"refs/heads/topic {commit} refs/heads/topic {'0' * 40}\n"

    validate_result = validate(repo, include_heavy=True, policy_root=root)
    pre_push_result = pre_push(
        repo,
        remote_name="origin",
        remote_url="git@github.com:fork/repo.git",
        stdin_text=stdin_text,
        policy_root=root,
    )

    assert validate_result.status == "pass"
    assert pre_push_result.status == "pass"
    assert pre_push_result.checks[0].receipt_path is not None


def test_pre_push_dry_run_uses_current_branch_upstream_range(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    upstream_commit = _commit(repo)
    current_branch = _git(repo, "branch", "--show-current")
    _git(repo, "update-ref", f"refs/remotes/origin/{current_branch}", upstream_commit)
    _git(repo, "branch", "--set-upstream-to", f"origin/{current_branch}")
    (repo / "debug.zip").write_text("artifact\n", encoding="utf-8")
    local_commit = _commit(repo, "Add artifact")
    root = _policy_root(tmp_path)

    result = pre_push_dry_run(repo, policy_root=root)
    stdin_text = pre_push_dry_run_stdin(repo)

    assert local_commit in stdin_text
    assert upstream_commit in stdin_text
    assert result.context.mode == "pre-push"
    assert result.context.commits == (local_commit,)
    assert result.status == "fail"
    assert "debug.zip" in compact_report(result)


def test_pre_push_dry_run_treats_missing_upstream_as_new_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    commit = _commit(repo)
    root = _policy_root(tmp_path)

    result = pre_push_dry_run(repo, policy_root=root)
    stdin_text = pre_push_dry_run_stdin(repo)

    assert commit in stdin_text
    assert " " + ("0" * 40) + "\n" in stdin_text
    assert result.context.mode == "pre-push"
    assert result.context.commits == (commit,)


def test_pre_push_dry_run_command_installs_registered_hooks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample"
    repo = task_dir / "dev" / "repo"
    _init_repo(workspace)
    (workspace / "README.md").write_text("workspace\n", encoding="utf-8")
    _commit(workspace)
    repo.parent.mkdir(parents=True)
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _commit(repo)
    set_slot(task_dir, "repo-registry", "repositories:\n  - path: tasks/sample/dev/repo\n")

    result = main(
        [
            "pre-push-dry-run",
            "--repo",
            str(workspace),
            "--task-dir",
            str(task_dir),
        ]
    )

    assert result == 0
    assert (repo / ".git" / "hooks" / "pre-push").is_file()
    assert (repo / ".git" / "hooks" / "pre-commit").is_file()


def test_command_backend_reports_compact_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _commit(repo)
    root = _policy_root(tmp_path)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "checks": [
                    {
                        "id": "custom-check",
                        "backend": "command",
                        "cost": "medium",
                        "command": [
                            sys.executable,
                            "-c",
                            "import sys; print('bad detail', file=sys.stderr); sys.exit(7)",
                        ],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = validate(repo, policy_root=root)

    assert result.status == "fail"
    assert "bad detail" in compact_report(result)
    assert "suggested command:" in compact_report(result)
    assert result.checks[0].returncode == 7


def test_validate_includes_dirty_worktree_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _commit(repo)
    (repo / "debug.zip").write_text("artifact\n", encoding="utf-8")
    root = _policy_root(tmp_path)

    result = validate(repo, policy_root=root)

    assert result.status == "fail"
    assert "debug.zip" in compact_report(result)


def test_validate_parse_check_skips_deleted_python_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    source = repo / "agent_tools" / "deleted.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _commit(repo)
    source.unlink()
    _git(repo, "add", "agent_tools/deleted.py")
    _git(repo, "commit", "-m", "Delete source", "-s")
    root = _policy_root(tmp_path)
    (root / "workspace-policy.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
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

    result = validate(repo, policy_root=root)

    assert result.status == "pass"
    assert result.checks[0].summary == "no changed Python files"


def test_compact_report_omits_passed_checks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _commit(repo)
    root = _policy_root(tmp_path)

    result = validate(repo, policy_root=root)
    report = compact_report(result)

    assert "repo_guard: pass" in report
    assert "repo_guard: 1 passed check(s) omitted" in report
    assert "repo_guard: all checks passed" in report
    assert "pass\tworkspace-file-hygiene" not in report


def test_policy_summary_is_json_serializable_for_agent_surface(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _commit(repo)

    payload = policy_summary(repo)

    json.dumps(payload, sort_keys=True)
    assert "checks" in payload
