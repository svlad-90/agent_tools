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
from .runner import pre_push_dry_run
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

    dry_run_parser = subparsers.add_parser(
        "pre-push-dry-run",
        help="Run the pre-push guard pipeline without installing or invoking a git hook.",
    )
    _add_common_args(dry_run_parser)
    dry_run_parser.add_argument("--remote", default="origin", help="Remote name to compare against.")
    dry_run_parser.set_defaults(func=_pre_push_dry_run_command)

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


def _pre_push_dry_run_command(args: argparse.Namespace) -> int:
    task_dir = _task_dir(args)
    hook_status = _install_registered_hooks_for_task(
        Path(args.repo).expanduser().resolve(),
        task_dir=task_dir,
    )
    if hook_status != 0:
        return hook_status
    result = pre_push_dry_run(
        Path(args.repo).expanduser().resolve(),
        remote_name=args.remote,
        task_dir=task_dir,
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


def _install_registered_hooks_for_task(repo: Path, *, task_dir: Path | None) -> int:
    if task_dir is None:
        return 0

    from agent_tools.tools.push_guard import install_repo_hooks
    from agent_tools.tools.repo_registry import validate_repo_registry

    workspace = _workspace_for_task(task_dir) or repo
    validation = validate_repo_registry(task_dir, workspace=workspace)
    if validation.errors:
        for error in validation.errors:
            print(f"repo_guard: invalid repo-registry entry: {error}", file=sys.stderr)
        return 1
    if not validation.repositories:
        print("repo_guard: repo-registry is empty; no hooks installed", file=sys.stderr)
        return 0

    for registered_repo in validation.repositories:
        install_repo_hooks(registered_repo)
    print(f"repo_guard: installed hooks for {len(validation.repositories)} registered repo(s)")
    return 0


def _workspace_for_task(task_dir: Path) -> Path | None:
    resolved = task_dir.resolve()
    parts = resolved.parts
    if "tasks" not in parts:
        return None
    tasks_index = len(parts) - 1 - list(reversed(parts)).index("tasks")
    if tasks_index == 0:
        return None
    return Path(*parts[:tasks_index])


__all__ = ["main", "pre_push", "pre_push_dry_run", "validate"]
