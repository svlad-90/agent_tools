from __future__ import annotations

from pathlib import Path

from ...task_actions.api import TASK_ACTIONS_FILE
from ...task_catalog.api import TaskSummary
from ...task_catalog.api import task_init_command
from ...task_catalog.api import task_path_for_name


def task_actions_signature(task: TaskSummary) -> tuple[Path, int | None]:
    path = task.path / TASK_ACTIONS_FILE
    try:
        return (path, path.stat().st_mtime_ns)
    except FileNotFoundError:
        return (path, None)
