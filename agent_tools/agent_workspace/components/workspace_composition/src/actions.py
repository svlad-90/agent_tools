from __future__ import annotations

import argparse
from pathlib import Path
import sys

from agent_tools.tools.task_context import DATABASE_FILENAME as TASK_CONTEXT_DATABASE_FILE

from ...task_catalog.api import TaskSummary
from ...task_catalog.api import run_task_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Workspace built-in actions.")
    subparsers = parser.add_subparsers(dest="action", required=True)

    task_check_parser = subparsers.add_parser("task-check", help="Run compact task_check output.")
    _add_task_arguments(task_check_parser)

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    workspace = Path(args.workspace).resolve()
    task = _task_summary(Path(args.task).resolve())

    if args.action == "task-check":
        print(run_task_check(task, workspace))
        return 0
    parser.error(f"unknown action {args.action!r}")
    return 2


def _add_task_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", required=True, help="Workspace root.")
    parser.add_argument("--task", required=True, help="Task directory.")


def _task_summary(task_path: Path) -> TaskSummary:
    return TaskSummary(
        name=task_path.name,
        path=task_path,
        has_description=True,
        has_context=(task_path / TASK_CONTEXT_DATABASE_FILE).is_file(),
        description_tokens=0,
        context_tokens=0,
        context_over_budget=False,
    )
