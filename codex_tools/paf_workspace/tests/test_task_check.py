from __future__ import annotations

from pathlib import Path

from paf_workspace.task_check import Check
from paf_workspace.task_check import check_task
from paf_workspace.task_check import initialize_task_layout


def test_initialize_task_layout_creates_description_and_context(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"

    initialize_checks = initialize_task_layout(task_dir, workspace=tmp_path)
    checks = check_task(task_dir, workspace=tmp_path)

    assert (task_dir / "TASK_DESCRIPTION.md").is_file()
    assert (task_dir / "TASK_CONTEXT.md").is_file()
    assert _has_check(initialize_checks, "PASS", "init-task-description")
    assert _has_check(checks, "PASS", "task-description")


def test_missing_task_description_is_warning_for_existing_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task_dir, workspace=tmp_path)
    (task_dir / "TASK_DESCRIPTION.md").unlink()

    checks = check_task(task_dir, workspace=tmp_path)

    assert _has_check(checks, "WARN", "task-description-missing")
    assert not any(check.status == "FAIL" for check in checks)


def _has_check(checks: list[Check], status: str, code: str) -> bool:
    return any(check.status == status and check.code == code for check in checks)
