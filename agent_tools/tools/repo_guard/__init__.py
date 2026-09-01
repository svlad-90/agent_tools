"""Repository validation policy runner."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .policy import policy_summary
from .runner import compact_report
from .runner import pre_push
from .runner import validate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    validate_parser = subparsers.add_parser("validate", help="Run repo_guard checks.")
    _add_common_args(validate_parser)
    validate_parser.add_argument("--include-heavy", action="store_true")
    validate_parser.set_defaults(func=_validate_command)

    status_parser = subparsers.add_parser("status", help="Show resolved repo_guard policy.")
    _add_common_args(status_parser)
    status_parser.set_defaults(func=_status_command)

    policy_parser = subparsers.add_parser("policy", help="Print resolved policy JSON.")
    _add_common_args(policy_parser)
    policy_parser.set_defaults(func=_policy_command)

    pre_push_parser = subparsers.add_parser("pre-push", help="Run pre-push repo guard.")
    _add_common_args(pre_push_parser)
    pre_push_parser.add_argument("remote_name", nargs="?")
    pre_push_parser.add_argument("remote_url", nargs="?")
    pre_push_parser.set_defaults(func=_pre_push_command)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repository root or path inside it.")
    parser.add_argument("--task-dir", help="Optional task directory for task-level policy.")
    parser.add_argument("--policy-root", help="Optional repo_guard policy root.")


def _validate_command(args: argparse.Namespace) -> int:
    result = validate(
        Path(args.repo).expanduser().resolve(),
        task_dir=_task_dir(args),
        include_heavy=bool(args.include_heavy),
        policy_root=_policy_root(args),
    )
    print(compact_report(result))
    return 0 if result.status == "pass" else 1


def _status_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    print(
        json.dumps(
            policy_summary(repo, task_dir=_task_dir(args), policy_root=_policy_root(args)),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _policy_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    print(
        json.dumps(
            policy_summary(repo, task_dir=_task_dir(args), policy_root=_policy_root(args)),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _pre_push_command(args: argparse.Namespace) -> int:
    result = pre_push(
        Path(args.repo).expanduser().resolve(),
        remote_name=args.remote_name,
        remote_url=args.remote_url,
        stdin_text=sys.stdin.read(),
        task_dir=_task_dir(args),
        policy_root=_policy_root(args),
    )
    print(compact_report(result), file=sys.stderr if result.status != "pass" else sys.stdout)
    return 0 if result.status == "pass" else 1


def _task_dir(args: argparse.Namespace) -> Path | None:
    if not args.task_dir:
        return None
    return Path(args.task_dir).expanduser().resolve()


def _policy_root(args: argparse.Namespace) -> Path | None:
    if not args.policy_root:
        return None
    return Path(args.policy_root).expanduser().resolve()


__all__ = ["main", "pre_push", "validate"]
