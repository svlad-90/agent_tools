from __future__ import annotations

from pathlib import Path

from agent_tools.tools.task_actualize import actualize_task
from agent_tools.tools.task_actualize import main


def test_actualize_task_creates_front_door_bell_for_existing_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)

    results = actualize_task(task_dir, workspace=tmp_path)

    front_door = task_dir / "front_door_bell.py"
    assert _has_result(results, "PASS", "actualize-front-door-bell-created")
    assert front_door.is_file()
    assert "front_desk_bell" in front_door.read_text(encoding="utf-8")


def test_actualize_task_is_idempotent(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)
    actualize_task(task_dir, workspace=tmp_path)

    results = actualize_task(task_dir, workspace=tmp_path)

    assert _has_result(results, "PASS", "actualize-front-door-bell-existing")


def test_actualize_task_reports_blocked_front_door_path(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    (task_dir / "front_door_bell.py").mkdir(parents=True)

    results = actualize_task(task_dir, workspace=tmp_path)

    assert _has_result(results, "FAIL", "actualize-front-door-bell-blocked")


def test_actualize_cli_returns_failure_for_blocked_front_door_path(tmp_path: Path, capsys) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    (task_dir / "front_door_bell.py").mkdir(parents=True)

    exit_code = main(["--workspace", str(tmp_path), "--task", str(task_dir)])

    assert exit_code == 1
    assert "actualize-front-door-bell-blocked" in capsys.readouterr().out


def _has_result(results, status: str, code: str) -> bool:
    return any(result.status == status and result.code == code for result in results)
