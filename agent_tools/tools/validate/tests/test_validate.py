from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml
from agent_tools.tools import validate as validate_module
from agent_tools.tools.validate import _run_validation
from agent_tools.tools.validate import _changed_files
from agent_tools.tools.validate import _guard_changed_files
from agent_tools.tools.validate import _validation_commands


def test_validation_commands_follow_changed_file_types(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "agent_tools" / "tools").mkdir(parents=True)
    (repo / "agent_tools" / "agent_workspace").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "agent_tools" / "tools" / "example.py").write_text("print('ok')\n", encoding="utf-8")
    (repo / "scripts" / "check.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo / "agent-workspace.desktop").write_text("[Desktop Entry]\nType=Application\nName=Agent Workspace\n", encoding="utf-8")
    commands = _validation_commands(
        repo,
        [
            Path("agent_tools/tools/example.py"),
            Path("scripts/check.sh"),
            Path("agent-workspace.desktop"),
            Path("agent_tools/tools/deleted.py"),
        ],
        repo / "tasks" / "sample-task",
    )

    names = [command.name for command in commands]
    assert "parse-check agent_tools/tools/example.py" in names
    assert "parse-check agent_tools/tools/deleted.py" not in names
    assert "bash -n scripts/check.sh" in names
    assert "task_check strict" in names


def test_validation_commands_include_policy_command_checks(monkeypatch, tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    (policy_root / "repos").mkdir(parents=True)
    (policy_root / "workspace-policy.yaml").write_text("version: 1\n", encoding="utf-8")
    (policy_root / "repos" / "sample.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "repo": {
                    "id": "sample",
                    "names": ["repo"],
                    "characteristic_files": ["marker.txt"],
                },
                "checks": [
                    {
                        "id": "repo-policy-smoke",
                        "description": "Run repo policy smoke command.",
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
    repo.mkdir()
    (repo / "marker.txt").write_text("ok\n", encoding="utf-8")
    original_load_validation_policy = validate_module.load_validation_policy
    monkeypatch.setattr(  # type: ignore[attr-defined]
        validate_module,
        "load_validation_policy",
        lambda repo, task_dir=None: original_load_validation_policy(
            repo,
            task_dir=task_dir,
            policy_root=policy_root,
        ),
    )
    commands = _validation_commands(repo, [], None)

    assert any(command.name == "policy repo-policy-smoke" for command in commands)


def test_run_validation_writes_receipt_for_empty_command_set(monkeypatch: object, tmp_path: Path) -> None:
    repo = tmp_path
    receipt = repo / "tasks" / "sample-task" / "report" / "validation" / "latest.json"
    monkeypatch.setattr(validate_module, "_git", lambda _args, *, cwd: "abc123")

    result = _run_validation(repo, [], None, receipt, mark_push_guard=False)

    assert result == 0
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert [command["name"] for command in payload["commands"]] == ["guard changed files"]


def test_changed_files_includes_untracked(monkeypatch: object, tmp_path: Path) -> None:
    def fake_git(args: list[str], *, cwd: Path) -> str:
        if args == ["diff", "--name-only", "HEAD"]:
            return "agent_tools/existing.py\n"
        if args == ["ls-files", "--others", "--exclude-standard"]:
            return "agent_tools/new.py\n"
        raise AssertionError(args)

    monkeypatch.setattr(validate_module, "_git", fake_git)

    assert _changed_files(tmp_path) == [Path("agent_tools/existing.py"), Path("agent_tools/new.py")]


def test_guard_changed_files_blocks_untracked_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "debug-output.deb"
    artifact.write_text("artifact\n", encoding="utf-8")

    result = _guard_changed_files(tmp_path, [Path("debug-output.deb")])

    assert result.status == "fail"
    assert "artifact-like file suffix '.deb' is blocked" in result.stderr_tail
