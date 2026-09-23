from __future__ import annotations

import argparse
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
from agent_tools.tools.push_guard import _repo_guard_enabled
from agent_tools.tools.push_guard import _set_repo_guard_enabled
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


def _zephyr_checker_module() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "validation"
        / "repos"
        / "zephyr"
        / "zephyr.py"
    )


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
    _set_repo_guard_enabled(argparse.Namespace(repo=str(repo)), enabled=False)
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
    assert _repo_guard_enabled(repo)
    assert (repo / ".git" / "hooks" / "pre-push").is_file()
    assert (repo / ".git" / "hooks" / "pre-commit").is_file()


def test_repos_commands_manage_task_repo_registry(tmp_path: Path, capsys: object) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample"
    repo = task_dir / "dev" / "repo"
    repo.parent.mkdir(parents=True)
    _init_repo(repo)

    add_status = main(
        [
            "repos",
            "add",
            "--workspace",
            str(workspace),
            "--task-dir",
            str(task_dir),
            "--repo",
            str(repo),
            "--role",
            "task-dev",
        ]
    )

    assert add_status == 0
    assert "tasks/sample/dev/repo" in capsys.readouterr().out

    assert main(["repos", "list", "--workspace", str(workspace), "--task-dir", str(task_dir)]) == 0
    listed = capsys.readouterr().out
    assert "role: task-dev" in listed

    assert main(["repos", "validate", "--workspace", str(workspace), "--task-dir", str(task_dir)]) == 0
    assert "PASS" in capsys.readouterr().out

    remove_status = main(
        [
            "repos",
            "remove",
            "--workspace",
            str(workspace),
            "--task-dir",
            str(task_dir),
            "--repo",
            str(repo),
        ]
    )

    assert remove_status == 0
    assert capsys.readouterr().out.strip() == "repositories: []"


def test_repos_commands_resolve_relative_task_dir_against_workspace(
    tmp_path: Path,
    monkeypatch: object,
    capsys: object,
) -> None:
    workspace = tmp_path / "workspace"
    task_dir = workspace / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    set_slot(task_dir, "repo-registry", "repositories:\n  - path: tasks/sample/dev/repo\n")
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    status = main(
        [
            "repos",
            "list",
            "--workspace",
            str(workspace),
            "--task-dir",
            "tasks/sample",
        ]
    )

    assert status == 0
    assert "tasks/sample/dev/repo" in capsys.readouterr().out


def test_repos_commands_report_registry_errors(tmp_path: Path, capsys: object) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    set_slot(task_dir, "repo-registry", "repositories: broken: yaml:")

    status = main(["repos", "validate", "--task-dir", str(task_dir)])

    assert status == 1
    assert "FAIL" in capsys.readouterr().out


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


def test_validate_writes_compatibility_receipt_when_requested(tmp_path: Path, capsys: object) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    commit = _commit(repo)
    receipt = tmp_path / "receipt.json"

    status = main(["validate", "--repo", str(repo), "--receipt", str(receipt)])

    assert status == 0
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["commit"] == commit
    assert payload["status"] == "pass"
    assert [command["name"] for command in payload["commands"]] == ["guard changed files"]
    assert "repo_guard validate: pass" in capsys.readouterr().out


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


def test_zephyr_spdx_file_copyright_blocks_plain_added_copyright(tmp_path: Path) -> None:
    repo = tmp_path / "zephyr"
    _init_repo(repo, remote="git@github.com:fork/zephyr.git")
    for filename in ("west.yml", "Kconfig.zephyr", "README.rst", "REUSE.toml"):
        (repo / filename).write_text("repo marker\n", encoding="utf-8")
    _commit(repo)
    source = repo / "drivers" / "xen" / "fdt.c"
    source.parent.mkdir(parents=True)
    source.write_text(
        "/*\n"
        " * Copyright (c) 2026 EPAM Systems\n"
        " * SPDX-License-Identifier: Apache-2.0\n"
        " */\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Add Xen FDT", "-s")
    root = _policy_root(tmp_path)
    (root / "repos" / "zephyr.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "zephyr",
                    "names": ["zephyr"],
                    "github_repos": ["github.com/zephyrproject-rtos/zephyr"],
                    "allow_forks": True,
                    "characteristic_files": [
                        "west.yml",
                        "Kconfig.zephyr",
                        "README.rst",
                        "REUSE.toml",
                    ],
                },
                "checks": [
                    {
                        "id": "zephyr-spdx-file-copyright",
                        "backend": "python",
                        "module": str(_zephyr_checker_module()),
                        "function": "zephyr_spdx_file_copyright",
                        "cost": "cheap",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = validate(repo, policy_root=root)

    assert result.status == "fail"
    report = compact_report(result)
    assert "zephyr-spdx-file-copyright" in report
    assert "drivers/xen/fdt.c" in report
    assert "SPDX-FileCopyrightText" in report


def test_zephyr_spdx_file_copyright_accepts_spdx_file_copyright_text(tmp_path: Path) -> None:
    repo = tmp_path / "zephyr"
    _init_repo(repo, remote="git@github.com:fork/zephyr.git")
    for filename in ("west.yml", "Kconfig.zephyr", "README.rst", "REUSE.toml"):
        (repo / filename).write_text("repo marker\n", encoding="utf-8")
    _commit(repo)
    source = repo / "drivers" / "xen" / "fdt.c"
    source.parent.mkdir(parents=True)
    source.write_text(
        "/*\n"
        " * SPDX-FileCopyrightText: Copyright (c) 2026 EPAM Systems\n"
        " * SPDX-License-Identifier: Apache-2.0\n"
        " */\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Add Xen FDT", "-s")
    root = _policy_root(tmp_path)
    (root / "repos" / "zephyr.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "zephyr",
                    "names": ["zephyr"],
                    "github_repos": ["github.com/zephyrproject-rtos/zephyr"],
                    "allow_forks": True,
                    "characteristic_files": [
                        "west.yml",
                        "Kconfig.zephyr",
                        "README.rst",
                        "REUSE.toml",
                    ],
                },
                "checks": [
                    {
                        "id": "zephyr-spdx-file-copyright",
                        "backend": "python",
                        "module": str(_zephyr_checker_module()),
                        "function": "zephyr_spdx_file_copyright",
                        "cost": "cheap",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = validate(repo, policy_root=root)

    assert result.status == "pass"
    assert result.checks[0].check_id == "workspace-file-hygiene"
    assert result.checks[1].check_id == "zephyr-spdx-file-copyright"


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
