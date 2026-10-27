from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from agent_tools.paf_workspace.task_check import check_task
from agent_tools.paf_workspace.task_check import render_text
from agent_tools.tools.task_actualize import actualize_task
from agent_tools.tools.task_context import DATABASE_FILENAME as TASK_CONTEXT_DATABASE_FILE
from agent_tools.tools.task_context import agent_visible_slots as agent_visible_task_context_slots
from agent_tools.tools.task_context import filter_entries as filter_task_context_entries
from agent_tools.tools.task_context import load_entries as load_task_context_entries
from agent_tools.tools.task_context import load_slots as load_task_context_slots
from agent_tools.tools.task_context import render_agent_entries as render_agent_context_entries
from agent_tools.tools.task_context import render_slots as render_task_context_slots

from ...markdown.api import rough_token_count


TASK_CONTEXT_BUDGET = 8_000
TASKS_DIR_NAME = "tasks"
_WINDOWS_RESERVED_TASK_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_WINDOWS_INVALID_TASK_NAME_CHARS = frozenset('<>:"/\\|?*')


@dataclass(frozen=True)
class TaskSummary:
    name: str
    path: Path
    has_description: bool
    has_context: bool
    description_tokens: int
    context_tokens: int
    context_over_budget: bool


def discover_tasks(workspace: Path, *, include_context_tokens: bool = True) -> list[TaskSummary]:
    workspace = workspace.resolve()
    tasks = []
    for path in sorted(
        _candidate_task_dirs(workspace),
        key=lambda candidate: candidate.name.casefold(),
    ):
        context_path = path / TASK_CONTEXT_DATABASE_FILE
        legacy_description_path = path / "TASK_DESCRIPTION.md"
        legacy_context_path = path / "TASK_CONTEXT.md"
        has_description = True
        has_context = context_path.is_file()
        has_legacy_context = legacy_description_path.is_file() or legacy_context_path.is_file()
        if not has_context and not has_legacy_context:
            continue
        _actualize_task_for_gui(path, workspace)
        description_tokens = 0
        context_tokens = _task_context_tokens(path) if has_context and include_context_tokens else 0
        tasks.append(
            TaskSummary(
                name=path.name,
                path=path,
                has_description=has_description,
                has_context=has_context,
                description_tokens=description_tokens,
                context_tokens=context_tokens,
                context_over_budget=context_tokens > TASK_CONTEXT_BUDGET,
            )
        )
    return tasks


def read_task_file(task: TaskSummary, filename: str) -> str:
    path = task.path / filename
    if not path.is_file():
        return f"{filename} is missing.\n"
    return path.read_text(encoding="utf-8", errors="replace")


def run_task_check(task: TaskSummary, workspace: Path, *, issues_only: bool = False) -> str:
    checks = check_task(task.path, workspace=workspace.resolve())
    if issues_only:
        return render_text(task.path, checks, issues_only=True)
    return render_text(task.path, checks, errors_only=True)


def task_path_for_name(workspace: Path, task_name: str) -> Path | None:
    if not _valid_task_name(task_name):
        return None
    task_path = (workspace / TASKS_DIR_NAME / task_name).resolve()
    tasks_root = (workspace / TASKS_DIR_NAME).resolve()
    try:
        task_path.relative_to(tasks_root)
    except ValueError:
        return None
    return task_path


def _valid_task_name(task_name: str) -> bool:
    if not task_name or task_name.startswith(".") or task_name[-1] in {" ", "."}:
        return False
    if any(character in _WINDOWS_INVALID_TASK_NAME_CHARS for character in task_name):
        return False
    if any(ord(character) < 32 for character in task_name):
        return False
    try:
        name_units = len(task_name.encode("utf-16-le")) // 2
    except UnicodeEncodeError:
        return False
    if name_units > 255:
        return False
    stem = task_name.split(".", 1)[0].upper()
    return stem not in _WINDOWS_RESERVED_TASK_NAMES


def task_init_command(
    workspace: Path,
    task_path: Path,
    *,
    privacy: str = "public",
) -> list[str]:
    command = [
        sys.executable or "python3",
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


def _actualize_task_for_gui(task_dir: Path, workspace: Path) -> None:
    try:
        actualize_task(task_dir, workspace=workspace)
    except OSError:
        return


def _candidate_task_dirs(workspace: Path) -> list[Path]:
    tasks_root = workspace / TASKS_DIR_NAME
    if not tasks_root.is_dir():
        return []
    return [
        path
        for path in tasks_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]


def _task_context_tokens(task_path: Path) -> int:
    return max(_slot_context_tokens(task_path), _legacy_active_context_tokens(task_path))


def _slot_context_tokens(task_path: Path) -> int:
    try:
        slots = agent_visible_task_context_slots(load_task_context_slots(task_path))
    except (OSError, ValueError):
        return 0
    if not slots:
        return 0
    return rough_token_count(render_task_context_slots(slots, format_name="agent", task_dir=task_path))


def _legacy_active_context_tokens(task_path: Path) -> int:
    try:
        entries = filter_task_context_entries(
            load_task_context_entries(task_path),
            severity="mid..critical",
            statuses=("active",),
        )
    except (OSError, ValueError):
        return 0
    return rough_token_count(render_agent_context_entries(task_path, entries, format_name="markdown"))
