from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools import validate as validate_module
from agent_tools.tools.validate import _run_validation
from agent_tools.tools.validate import _changed_files
from agent_tools.tools.validate import _guard_changed_files
from agent_tools.tools.validate import _validation_commands


def test_validation_commands_follow_changed_file_types(tmp_path: Path) -> None:
    repo = tmp_path
    commands = _validation_commands(
        repo,
        [
            Path("agent_tools/tools/example.py"),
            Path("scripts/check.sh"),
            Path("agent-workspace.desktop"),
        ],
        repo / "tasks" / "sample-task",
    )

    names = [command.name for command in commands]
    assert "parse-check agent_tools/tools/example.py" in names
    assert "bash -n scripts/check.sh" in names
    assert "task_check strict" in names


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
