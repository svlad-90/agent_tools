from __future__ import annotations

from pathlib import Path

from agent_tools.tools.task_actualize import actualize_task
from agent_tools.tools.task_actualize import main


def test_actualize_task_reports_harness_adapter_ready_for_existing_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)

    results = actualize_task(task_dir, workspace=tmp_path)

    front_door = task_dir / "front_door_bell.py"
    assert _has_result(results, "PASS", "actualize-harness-adapter-ready")
    assert not front_door.exists()


def test_actualize_task_is_idempotent(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    task_dir.mkdir(parents=True)
    actualize_task(task_dir, workspace=tmp_path)

    results = actualize_task(task_dir, workspace=tmp_path)

    assert _has_result(results, "PASS", "actualize-harness-adapter-ready")


def test_actualize_task_ignores_legacy_front_door_directory(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    (task_dir / "front_door_bell.py").mkdir(parents=True)

    results = actualize_task(task_dir, workspace=tmp_path)

    assert _has_result(results, "PASS", "actualize-harness-adapter-ready")


def test_actualize_cli_reports_harness_adapter_ready(tmp_path: Path, capsys) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    (task_dir / "front_door_bell.py").mkdir(parents=True)

    exit_code = main(["--workspace", str(tmp_path), "--task", str(task_dir)])

    assert exit_code == 0
    assert "actualize-harness-adapter-ready" in capsys.readouterr().out


def _has_result(results, status: str, code: str) -> bool:
    return any(result.status == status and result.code == code for result in results)
