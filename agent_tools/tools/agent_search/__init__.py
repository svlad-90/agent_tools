from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, cast


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main(argv: list[str] | None = None) -> int:
    from .core import (
        AgentSearchError,
        file_search,
        render_file_search,
        render_file_search_json,
        render_text_search,
        render_text_search_json,
        text_search,
    )
    from .file_types import FILE_TYPES
    from .snippets import render_file_snippet, show_file_range

    effective_argv = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"text", "files", "show", "examples"}
    if effective_argv and effective_argv[0] not in known_commands and not effective_argv[0].startswith("-"):
        effective_argv = ["text", *effective_argv]

    parser = argparse.ArgumentParser(description="Compact agent-facing text and file search.")
    subparsers = parser.add_subparsers(dest="command")

    examples_parser = subparsers.add_parser("examples", help="Print compact usage examples.")
    examples_parser.set_defaults(handler=lambda _args: _print_examples(FILE_TYPES))

    text_parser = subparsers.add_parser("text", help="Search file contents and render compact results.")
    _add_common_args(text_parser)
    text_parser.add_argument("query")
    text_parser.add_argument("root", nargs="?", default=".")
    text_parser.add_argument("--mode", choices=("summary", "aggregate", "ranges"), default="summary")
    text_parser.add_argument("--fixed", action="store_true", help="Treat query as literal text.")
    text_parser.add_argument("--case-sensitive", action="store_true")
    text_parser.add_argument("--ignore-case", action="store_true")
    text_parser.add_argument("--around", type=int, default=5)
    text_parser.add_argument("--before", type=int)
    text_parser.add_argument("--after", type=int)
    text_parser.add_argument("--max-ranges", type=int, default=20)
    text_parser.add_argument("--max-lines", type=int, default=300)
    text_parser.add_argument("--max-file-bytes", type=int, default=2_000_000)
    text_parser.add_argument("--samples", type=int, default=20)
    text_parser.add_argument("--per-group-samples", type=int, default=3)
    text_parser.set_defaults(handler=lambda args: _run_text(args, text_search, render_text_search, render_text_search_json))

    files_parser = subparsers.add_parser("files", help="Search file paths and render compact results.")
    _add_common_args(files_parser)
    files_parser.add_argument("query")
    files_parser.add_argument("root", nargs="?", default=".")
    files_parser.add_argument("--mode", choices=("summary", "aggregate"), default="summary")
    files_parser.add_argument("--fixed", action="store_true", help="Treat query as literal text.")
    files_parser.add_argument("--case-sensitive", action="store_true")
    files_parser.add_argument("--ignore-case", action="store_true")
    files_parser.add_argument("--ext", action="append", default=[])
    files_parser.add_argument("--scope", choices=("path", "name"), default="path")
    files_parser.set_defaults(handler=lambda args: _run_files(args, file_search, render_file_search, render_file_search_json))

    show_parser = subparsers.add_parser("show", help="Print one file range with optional context.")
    show_parser.add_argument("file_path")
    show_parser.add_argument("--line", type=int)
    show_parser.add_argument("--range")
    show_parser.add_argument("--around", type=int, default=5)
    show_parser.add_argument("--max-line-chars", type=int, default=240)
    show_parser.set_defaults(handler=lambda args: _run_show(args, show_file_range, render_file_snippet))

    args = parser.parse_args(effective_argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    try:
        handler = cast(Callable[[argparse.Namespace], int], args.handler)
        return int(handler(args) or 0)
    except AgentSearchError as error:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(error)}, indent=2, sort_keys=True))
        else:
            print(str(error), file=sys.stderr)
        return 1


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--include", action="append", default=[], help="fnmatch glob to include. Repeatable.")
    parser.add_argument("--exclude", action="append", default=[], help="fnmatch glob to exclude. Repeatable.")
    parser.add_argument("--hidden", action="store_true", help="Include hidden files and directories.")
    parser.add_argument("--no-gitignore", action="store_true", help="Use filesystem walk instead of git ls-files.")
    parser.add_argument("--type", action="append", default=[], help="File type shortcut such as py, md, yaml, json, c, cpp.")
    parser.add_argument("--threads", type=int, default=_default_threads())
    parser.add_argument("--max-matches-scanned", type=int, default=10_000)
    parser.add_argument("--max-files", type=int, default=30)
    parser.add_argument("--max-dirs", type=int, default=20)
    parser.add_argument("--max-output-lines", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=2_000)
    parser.add_argument("--json", action="store_true")


def _default_threads() -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count // 2)


def _resolve_root(root_text: str) -> Path:
    root = Path(root_text)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root


def _run_text(
    args: argparse.Namespace,
    search: Callable[..., Any],
    render: Callable[..., str],
    render_json: Callable[..., str],
) -> int:
    from .file_types import expand_extensions

    extensions = expand_extensions([], args.type)
    include = [*args.include, *(f"*{extension}" for extension in extensions)]
    report = search(
        root=_resolve_root(args.root),
        query=args.query,
        fixed=args.fixed,
        case_sensitive=args.case_sensitive,
        ignore_case=args.ignore_case,
        include=include,
        exclude=args.exclude,
        hidden=args.hidden,
        use_gitignore=not args.no_gitignore,
        threads=args.threads,
        max_matches_scanned=args.max_matches_scanned,
        max_file_bytes=args.max_file_bytes,
        before=args.before if args.before is not None else args.around,
        after=args.after if args.after is not None else args.around,
        max_ranges=args.max_ranges,
        max_lines=args.max_lines,
    )
    if args.json:
        print(
            render_json(
                report,
                max_matches=args.max_matches_scanned,
                max_ranges=args.max_ranges,
                max_range_lines=args.max_lines,
            )
        )
    else:
        print(render(report, mode=args.mode, options=vars(args)))
    return 0


def _run_files(
    args: argparse.Namespace,
    search: Callable[..., Any],
    render: Callable[..., str],
    render_json: Callable[..., str],
) -> int:
    from .file_types import expand_extensions

    report = search(
        root=_resolve_root(args.root),
        query=args.query,
        fixed=args.fixed,
        case_sensitive=args.case_sensitive,
        ignore_case=args.ignore_case,
        include=args.include,
        exclude=args.exclude,
        hidden=args.hidden,
        use_gitignore=not args.no_gitignore,
        threads=args.threads,
        max_files_scanned=args.max_matches_scanned,
        extensions=expand_extensions(args.ext, args.type),
        scope=args.scope,
    )
    if args.json:
        print(render_json(report, max_files=args.max_files))
    else:
        print(render(report, mode=args.mode, options=vars(args)))
    return 0


def _run_show(
    args: argparse.Namespace,
    show_range: Callable[..., Any],
    render: Callable[..., str],
) -> int:
    snippet = show_range(
        path=_resolve_root(args.file_path),
        line=args.line,
        line_range=args.range,
        around=args.around,
    )
    print(render(snippet, max_line_chars=args.max_line_chars))
    return 0


def _print_examples(file_types: dict[str, tuple[str, ...]]) -> int:
    known_types = ", ".join(sorted(file_types))
    print(
        "\n".join(
            [
                "agent_search examples:",
                "  python -m agent_tools.tools.agent_search text 'def .*target' agent_tools --type py",
                "  python -m agent_tools.tools.agent_search text 'needle' agent_tools --mode ranges --around 5",
                "  python -m agent_tools.tools.agent_search text '(?P<GV>src|tests)/(?P<GV>[^/]+)' agent_tools --mode aggregate",
                "  python -m agent_tools.tools.agent_search files gtk agent_tools --type py --scope name",
                "  python -m agent_tools.tools.agent_search show agent_tools/tools/agent_search/core.py --line 10 --around 5",
                f"known --type values: {known_types}",
            ]
        )
    )
    return 0
