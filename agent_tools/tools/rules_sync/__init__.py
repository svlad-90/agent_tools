from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import RulesSyncError, apply_plan, find_project_root, plan_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mirror agent_tools/rules/*.md and agent_tools/skills/*/SKILL.md "
            "(the Codex-facing source of truth) into other agents' native "
            "conventions, for example Claude Code's .claude/skills/ and the "
            "generated block in CLAUDE.md."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Regenerate mirrored files.")
    sync_parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing; exit non-zero if anything would change.",
    )
    sync_parser.add_argument(
        "--root",
        help="Workspace root override. Defaults to the ancestor with AGENTS.md and agent_tools/.",
    )
    sync_parser.set_defaults(handler=_run_sync)

    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv and effective_argv[0] not in {"sync", "-h", "--help"}:
        effective_argv = ["sync", *effective_argv]

    args = parser.parse_args(effective_argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except RulesSyncError as error:
        print(f"rules_sync: {error}", file=sys.stderr)
        return 1


def _run_sync(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else find_project_root(Path.cwd())
    outputs = plan_all(root)
    result = apply_plan(outputs, check_only=args.check)

    for path in result.changed:
        verb = "would change" if args.check else "wrote"
        print(f"{verb}: {path.relative_to(root)}")
    for path in result.unchanged:
        print(f"unchanged: {path.relative_to(root)}")

    if args.check and not result.is_clean:
        print(
            f"rules_sync: {len(result.changed)} file(s) out of date; run without --check to fix",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
