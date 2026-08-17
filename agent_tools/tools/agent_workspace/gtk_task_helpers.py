from __future__ import annotations

from pathlib import Path

from .commands import sys_executable
from .core import TASK_ACTIONS_FILE
from .core import TaskSummary


def task_actions_signature(task: TaskSummary) -> tuple[Path, int | None]:
    path = task.path / TASK_ACTIONS_FILE
    try:
        return (path, path.stat().st_mtime_ns)
    except FileNotFoundError:
        return (path, None)


def task_path_for_name(workspace: Path, task_name: str) -> Path | None:
    if not task_name or task_name in {".", ".."}:
        return None
    if "/" in task_name or "\\" in task_name:
        return None
    task_path = (workspace / "tasks" / task_name).resolve()
    tasks_root = (workspace / "tasks").resolve()
    try:
        task_path.relative_to(tasks_root)
    except ValueError:
        return None
    return task_path


def task_init_command(
    workspace: Path,
    task_path: Path,
    *,
    privacy: str = "public",
) -> list[str]:
    command = [
        sys_executable(),
        "-m",
        "agent_tools.paf_workspace.task_check",
        str(task_path),
        "--workspace",
        str(workspace),
        "--init-layout",
    ]
    if privacy != "public":
        command.extend(["--privacy", privacy])
    return command
