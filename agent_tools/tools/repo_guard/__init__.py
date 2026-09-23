"""Repository validation policy runner."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .policy import policy_summary
from . import legacy_validate
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
    validate_parser.add_argument(
        "--receipt",
        help="Write a compatibility changed/task validation receipt instead of a repo_guard policy receipt.",
    )
    validate_parser.add_argument(
        "--mark-push-guard",
        action="store_true",
        help="Record push_guard success after writing a passing compatibility receipt.",
    )
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

    repos_parser = subparsers.add_parser("repos", help="Manage task registered repositories.")
    repos_subparsers = repos_parser.add_subparsers(dest="repos_command_name", required=True)

    repos_list_parser = repos_subparsers.add_parser("list", help="List task registered repositories.")
    _add_repos_common_args(repos_list_parser)
    repos_list_parser.add_argument("--json", action="store_true", help="Render JSON.")
    repos_list_parser.set_defaults(func=_repos_list_command)

    repos_validate_parser = repos_subparsers.add_parser("validate", help="Validate task registered repositories.")
    _add_repos_common_args(repos_validate_parser)
    repos_validate_parser.add_argument("--json", action="store_true", help="Render JSON.")
    repos_validate_parser.set_defaults(func=_repos_validate_command)

    repos_add_parser = repos_subparsers.add_parser("add", help="Add a repository to the task registry.")
    _add_repos_common_args(repos_add_parser)
    repos_add_parser.add_argument("--repo", required=True, help="Git repository root to register.")
    repos_add_parser.add_argument("--role", default="", help="Optional repository role.")
    repos_add_parser.add_argument("--json", action="store_true", help="Render JSON.")
    repos_add_parser.set_defaults(func=_repos_add_command)

    repos_remove_parser = repos_subparsers.add_parser("remove", help="Remove a repository from the task registry.")
    _add_repos_common_args(repos_remove_parser)
    repos_remove_parser.add_argument("--repo", required=True, help="Git repository root to unregister.")
    repos_remove_parser.add_argument("--json", action="store_true", help="Render JSON.")
    repos_remove_parser.set_defaults(func=_repos_remove_command)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as error:
        print(f"repo_guard: error: {error}", file=sys.stderr)
        return 1


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repository root or path inside it.")
    parser.add_argument("--task-dir", help="Optional task directory for task-level policy.")
    parser.add_argument("--policy-root", help="Optional repo_guard policy root.")


def _add_repos_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-dir", required=True, help="Task directory that owns the repo registry.")
    parser.add_argument("--workspace", help="Workspace root. Default: inferred from task directory.")


def _validate_command(args: argparse.Namespace) -> int:
    if args.receipt or args.mark_push_guard:
        repo = Path(args.repo).expanduser().resolve()
        receipt = Path(args.receipt).expanduser().resolve() if args.receipt else None
        task_dir = _task_dir(args)
        if task_dir is not None:
            return legacy_validate.validate_task(
                repo,
                task_dir,
                receipt=receipt,
                mark_push_guard=bool(args.mark_push_guard),
            )
        return legacy_validate.validate_changed(
            repo,
            receipt=receipt,
            mark_push_guard=bool(args.mark_push_guard),
        )
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


def _repos_list_command(args: argparse.Namespace) -> int:
    from agent_tools.tools.repo_registry import repo_registry_entry_objects
    from agent_tools.tools.repo_registry import render_repo_registry

    task_dir, _workspace = _repos_task_workspace(args)
    entries = repo_registry_entry_objects(_repo_registry_content(task_dir))
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries) if entries else "repositories: []")
    return 0


def _repos_validate_command(args: argparse.Namespace) -> int:
    from agent_tools.tools.repo_registry import validate_repo_registry

    task_dir, workspace = _repos_task_workspace(args)
    validation = validate_repo_registry(task_dir, workspace=workspace)
    if args.json:
        print(
            json.dumps(
                {
                    "repositories": [str(path) for path in validation.repositories],
                    "errors": list(validation.errors),
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for path in validation.repositories:
            print(f"PASS {path}")
        for error in validation.errors:
            print(f"FAIL {error}")
        if not validation.repositories and not validation.errors:
            print("WARN repo-registry is empty")
    return 1 if validation.errors else 0


def _repos_add_command(args: argparse.Namespace) -> int:
    from agent_tools.tools.repo_registry import add_repository
    from agent_tools.tools.repo_registry import render_repo_registry

    task_dir, workspace = _repos_task_workspace(args)
    entries = add_repository(task_dir, workspace=workspace, repo=Path(args.repo), role=args.role)
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries))
    return 0


def _repos_remove_command(args: argparse.Namespace) -> int:
    from agent_tools.tools.repo_registry import remove_repository
    from agent_tools.tools.repo_registry import render_repo_registry

    task_dir, workspace = _repos_task_workspace(args)
    entries = remove_repository(task_dir, workspace=workspace, repo=Path(args.repo))
    if args.json:
        print(json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True))
    else:
        print(render_repo_registry(entries) if entries else "repositories: []")
    return 0


def _task_dir(args: argparse.Namespace) -> Path | None:
    if not args.task_dir:
        return None
    return Path(args.task_dir).expanduser().resolve()


def _policy_root(args: argparse.Namespace) -> Path | None:
    if not args.policy_root:
        return None
    return Path(args.policy_root).expanduser().resolve()


def _repos_task_workspace(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
    else:
        raw_task_dir = Path(args.task_dir).expanduser()
        workspace = _workspace_for_task(raw_task_dir.resolve()) or Path.cwd().resolve()

    task_dir = Path(args.task_dir).expanduser()
    if not task_dir.is_absolute():
        task_dir = workspace / task_dir
    return task_dir.resolve(), workspace


def _repo_registry_content(task_dir: Path) -> str:
    from agent_tools.tools.repo_registry import REPO_REGISTRY_SLOT_CATEGORY
    from agent_tools.tools.task_context import load_slots

    slots = load_slots(task_dir, (REPO_REGISTRY_SLOT_CATEGORY,))
    return slots[0].content if slots else "repositories: []"


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
