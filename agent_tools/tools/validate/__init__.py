"""Deprecated compatibility CLI for changed-file validation receipts.

Use ``python -m agent_tools.tools.repo_guard validate`` for repository policy
validation. This module remains as a transition wrapper for the older
``validate changed`` and ``validate task`` receipt format.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from agent_tools.tools.repo_guard import legacy_validate
from agent_tools.tools.repo_guard.legacy_validate import ValidationCommand
from agent_tools.tools.repo_guard.legacy_validate import ValidationResult
from agent_tools.tools.repo_guard.legacy_validate import _changed_files
from agent_tools.tools.repo_guard.legacy_validate import _guard_changed_files
from agent_tools.tools.repo_guard.legacy_validate import _git
from agent_tools.tools.repo_guard.legacy_validate import _repo_root
from agent_tools.tools.repo_guard.legacy_validate import _run_command
from agent_tools.tools.repo_guard.legacy_validate import _run_validation
from agent_tools.tools.repo_guard.legacy_validate import _validation_commands


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Deprecated: prefer python -m agent_tools.tools.repo_guard validate for policy checks.",
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    changed_parser = subparsers.add_parser("changed", help="Validate changed files in the repository.")
    _add_common_args(changed_parser)
    changed_parser.set_defaults(func=validate_changed)

    task_parser = subparsers.add_parser("task", help="Validate changed files and one task directory.")
    task_parser.add_argument("task_dir")
    _add_common_args(task_parser)
    task_parser.set_defaults(func=validate_task)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repository root or path inside it. Default: current directory.")
    parser.add_argument(
        "--receipt",
        help="Receipt output path. Default: <task>/report/validation/latest.json or report/validation/latest.json.",
    )
    parser.add_argument("--mark-push-guard", action="store_true", help="Record push_guard success when checks pass.")


def validate_changed(args: argparse.Namespace) -> int:
    return legacy_validate.validate_changed(
        Path(args.repo),
        receipt=Path(args.receipt).expanduser().resolve() if args.receipt else None,
        mark_push_guard=bool(args.mark_push_guard),
        label="validate",
    )


def validate_task(args: argparse.Namespace) -> int:
    return legacy_validate.validate_task(
        Path(args.repo),
        Path(args.task_dir),
        receipt=Path(args.receipt).expanduser().resolve() if args.receipt else None,
        mark_push_guard=bool(args.mark_push_guard),
        label="validate",
    )


if __name__ == "__main__":
    raise SystemExit(main())
