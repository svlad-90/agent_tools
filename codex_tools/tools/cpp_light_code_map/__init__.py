import argparse
import json
import os
from pathlib import Path
import sys

from .core import CppLightCodeMapError
from .core import compact_help
from .core import render_call_graph
from .core import render_calls
from .core import render_complexity
from .core import render_diagnose
from .core import render_includes
from .core import render_index
from .core import render_index_dir
from .core import render_locals
from .core import render_macros
from .core import render_map
from .core import render_parse_check
from .core import render_query
from .core import render_refs
from .core import render_rename_symbol
from .core import render_replace_symbol
from .core import render_replace_symbol_body
from .core import render_insert_relative_to_symbol
from .core import render_symbol_snapshot
from .core import render_symbols
from .core import render_unmapped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map C/C++ source structure without a build context.")
    subparsers = parser.add_subparsers(dest="command")

    map_parser = subparsers.add_parser("map", help="Print a structural C/C++ symbol map.")
    _add_source_args(map_parser)
    map_parser.add_argument("--compact", action="store_true")
    map_parser.add_argument("--json", action="store_true")

    outline_parser = subparsers.add_parser("outline", help="Alias for map.")
    _add_source_args(outline_parser)
    outline_parser.add_argument("--compact", action="store_true")
    outline_parser.add_argument("--json", action="store_true")

    diagnose_parser = subparsers.add_parser("diagnose", help="Diagnose tree-sitter light-map coverage.")
    _add_source_args(diagnose_parser)
    diagnose_parser.add_argument("--json", action="store_true")

    unmapped_parser = subparsers.add_parser("unmapped", help="List top-level tree-sitter nodes not mapped as symbols.")
    _add_source_args(unmapped_parser)
    unmapped_parser.add_argument("--json", action="store_true")

    symbols_parser = subparsers.add_parser("symbols", help="List flattened structural symbols.")
    _add_source_args(symbols_parser)
    symbols_parser.add_argument("--kind")
    symbols_parser.add_argument("--name")
    symbols_parser.add_argument("--contains", type=int, dest="contains_line")
    symbols_parser.add_argument("--compact", action="store_true")
    symbols_parser.add_argument("--json", action="store_true")

    symbol_parser = subparsers.add_parser("symbol-get", help="Print a structural symbol snapshot.")
    _add_source_args(symbol_parser)
    symbol_parser.add_argument("--symbol", required=True)
    symbol_parser.add_argument("--with-doc", action="store_true")
    symbol_parser.add_argument("--json", action="store_true")

    includes_parser = subparsers.add_parser("includes", help="List #include directives.")
    _add_source_args(includes_parser)
    includes_parser.add_argument("--json", action="store_true")

    macros_parser = subparsers.add_parser("macros", help="List preprocessor macro directives.")
    _add_source_args(macros_parser)
    macros_parser.add_argument("--json", action="store_true")

    calls_parser = subparsers.add_parser("calls", help="List structural function calls.")
    _add_source_args(calls_parser)
    calls_parser.add_argument("--symbol")
    calls_parser.add_argument("--json", action="store_true")

    graph_parser = subparsers.add_parser("call-graph", help="List structural call graph edges.")
    _add_source_args(graph_parser)
    graph_parser.add_argument("--json", action="store_true")

    refs_parser = subparsers.add_parser("refs", help="List structural identifier references.")
    _add_source_args(refs_parser)
    refs_parser.add_argument("--name", required=True)
    refs_parser.add_argument("--scope")
    refs_parser.add_argument("--json", action="store_true")

    locals_parser = subparsers.add_parser("locals", help="List parameters, locals, and labels for a symbol.")
    _add_source_args(locals_parser)
    locals_parser.add_argument("--symbol", required=True)
    locals_parser.add_argument("--json", action="store_true")

    complexity_parser = subparsers.add_parser("complexity", help="Print simple structural complexity metrics.")
    _add_source_args(complexity_parser)
    complexity_parser.add_argument("--symbol")
    complexity_parser.add_argument("--json", action="store_true")

    parse_parser = subparsers.add_parser("parse-check", help="Check whether structural parsing found symbols.")
    _add_source_args(parse_parser)
    parse_parser.add_argument("--json", action="store_true")

    index_parser = subparsers.add_parser("index", help="Write cached structural symbol maps.")
    index_parser.add_argument("cpp_files", nargs="+")
    index_parser.add_argument("--cache-dir")
    index_parser.add_argument("--json", action="store_true")

    index_dir_parser = subparsers.add_parser("index-dir", help="Index C/C++ files under a directory.")
    index_dir_parser.add_argument("root_dir")
    index_dir_parser.add_argument("--include", action="append", default=[])
    index_dir_parser.add_argument("--exclude", action="append", default=[])
    index_dir_parser.add_argument("--cache-dir")
    index_dir_parser.add_argument("--json", action="store_true")

    query_parser = subparsers.add_parser("query", help="Search cached structural symbol maps.")
    query_parser.add_argument("--name", required=True)
    query_parser.add_argument("--cache-dir")
    query_parser.add_argument("--json", action="store_true")

    rename_parser = subparsers.add_parser("rename-symbol", help="Rename structural identifier refs inside a safe scope.")
    _add_source_args(rename_parser)
    rename_parser.add_argument("--symbol", required=True)
    rename_parser.add_argument("--expect-hash", required=True)
    rename_parser.add_argument("--new-name", required=True)
    rename_parser.add_argument("--scope")
    rename_parser.add_argument("--check-only", action="store_true")
    rename_parser.add_argument("--json", action="store_true")

    replace_symbol_parser = subparsers.add_parser("replace-symbol", help="Replace one whole symbol by structural span.")
    _add_source_args(replace_symbol_parser)
    replace_symbol_parser.add_argument("--symbol", required=True)
    replace_symbol_parser.add_argument("--expect-hash", required=True)
    group = replace_symbol_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--replacement-env")
    group.add_argument("--replacement-file")
    group.add_argument("--replacement-text")
    group.add_argument("--replacement-stdin", action="store_true")
    replace_symbol_parser.add_argument("--check-only", action="store_true")
    replace_symbol_parser.add_argument("--json", action="store_true")

    replace_body_parser = subparsers.add_parser("replace-symbol-body", help="Replace one function body by structural span.")
    _add_source_args(replace_body_parser)
    replace_body_parser.add_argument("--symbol", required=True)
    replace_body_parser.add_argument("--expect-hash", required=True)
    group = replace_body_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--replacement-env")
    group.add_argument("--replacement-file")
    group.add_argument("--replacement-text")
    group.add_argument("--replacement-stdin", action="store_true")
    replace_body_parser.add_argument("--check-only", action="store_true")
    replace_body_parser.add_argument("--json", action="store_true")

    for command_name, help_text in (
        ("insert-before-symbol", "Insert sibling text before an anchor symbol."),
        ("insert-after-symbol", "Insert sibling text after an anchor symbol."),
    ):
        insert_parser = subparsers.add_parser(command_name, help=help_text)
        _add_source_args(insert_parser)
        insert_parser.add_argument("--symbol", required=True)
        insert_parser.add_argument("--expect-hash", required=True)
        group = insert_parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--snippet-env")
        group.add_argument("--snippet-file")
        group.add_argument("--snippet-text")
        group.add_argument("--snippet-stdin", action="store_true")
        insert_parser.add_argument("--check-only", action="store_true")
        insert_parser.add_argument("--json", action="store_true")

    subparsers.add_parser("help", help="Print compact help.")

    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        print(compact_help())
        return 0
    try:
        if args.command in {"map", "outline"}:
            target = Path(args.cpp_file).resolve()
            print(render_map(target, compact=args.compact, json_output=args.json))
        elif args.command == "diagnose":
            target = Path(args.cpp_file).resolve()
            print(render_diagnose(target, json_output=args.json))
        elif args.command == "unmapped":
            target = Path(args.cpp_file).resolve()
            print(render_unmapped(target, json_output=args.json))
        elif args.command == "symbols":
            target = Path(args.cpp_file).resolve()
            print(render_symbols(target,
                                 kind=args.kind,
                                 name=args.name,
                                 contains_line=args.contains_line,
                                 compact=args.compact,
                                 json_output=args.json))
        elif args.command == "symbol-get":
            target = Path(args.cpp_file).resolve()
            print(render_symbol_snapshot(target, args.symbol, with_doc=args.with_doc, json_output=args.json))
        elif args.command == "includes":
            target = Path(args.cpp_file).resolve()
            print(render_includes(target, json_output=args.json))
        elif args.command == "macros":
            target = Path(args.cpp_file).resolve()
            print(render_macros(target, json_output=args.json))
        elif args.command == "calls":
            target = Path(args.cpp_file).resolve()
            print(render_calls(target, symbol_name=args.symbol, json_output=args.json))
        elif args.command == "call-graph":
            target = Path(args.cpp_file).resolve()
            print(render_call_graph(target, json_output=args.json))
        elif args.command == "refs":
            target = Path(args.cpp_file).resolve()
            print(render_refs(target, args.name, scope_symbol=args.scope, json_output=args.json))
        elif args.command == "locals":
            target = Path(args.cpp_file).resolve()
            print(render_locals(target, args.symbol, json_output=args.json))
        elif args.command == "complexity":
            target = Path(args.cpp_file).resolve()
            print(render_complexity(target, symbol_name=args.symbol, json_output=args.json))
        elif args.command == "parse-check":
            target = Path(args.cpp_file).resolve()
            print(render_parse_check(target, json_output=args.json))
        elif args.command == "index":
            print(render_index(tuple(Path(item).resolve() for item in args.cpp_files),
                               cache_dir=Path(args.cache_dir).resolve() if args.cache_dir else None,
                               json_output=args.json))
        elif args.command == "index-dir":
            print(render_index_dir(Path(args.root_dir).resolve(),
                                   includes=tuple(args.include),
                                   excludes=tuple(args.exclude),
                                   cache_dir=Path(args.cache_dir).resolve() if args.cache_dir else None,
                                   json_output=args.json))
        elif args.command == "query":
            print(render_query(args.name,
                               cache_dir=Path(args.cache_dir).resolve() if args.cache_dir else None,
                               json_output=args.json))
        elif args.command == "rename-symbol":
            target = Path(args.cpp_file).resolve()
            print(render_rename_symbol(target,
                                       args.symbol,
                                       args.expect_hash,
                                       args.new_name,
                                       scope_symbol=args.scope,
                                       check_only=args.check_only,
                                       json_output=args.json))
        elif args.command == "replace-symbol":
            target = Path(args.cpp_file).resolve()
            print(render_replace_symbol(target,
                                        args.symbol,
                                        args.expect_hash,
                                        _resolve_text(args, "replacement"),
                                        check_only=args.check_only,
                                        json_output=args.json))
        elif args.command == "replace-symbol-body":
            target = Path(args.cpp_file).resolve()
            print(render_replace_symbol_body(target,
                                             args.symbol,
                                             args.expect_hash,
                                             _resolve_text(args, "replacement"),
                                             check_only=args.check_only,
                                             json_output=args.json))
        elif args.command in {"insert-before-symbol", "insert-after-symbol"}:
            target = Path(args.cpp_file).resolve()
            position = "before" if args.command == "insert-before-symbol" else "after"
            print(render_insert_relative_to_symbol(target,
                                                   args.symbol,
                                                   args.expect_hash,
                                                   _resolve_text(args, "snippet"),
                                                   position=position,
                                                   check_only=args.check_only,
                                                   json_output=args.json))
        else:
            parser.error(f"unknown command {args.command!r}")
    except CppLightCodeMapError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": exc.message, "details": exc.details}, indent=2, sort_keys=True))
        else:
            print(exc.message, file=sys.stderr)
        return 2
    except ValueError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return 1
    return 0


def _add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("cpp_file")


def _resolve_text(args: argparse.Namespace, prefix: str) -> str:
    text = getattr(args, f"{prefix}_text")
    if text is not None:
        return str(text)
    env_name = getattr(args, f"{prefix}_env")
    if env_name is not None:
        try:
            return os.environ[env_name]
        except KeyError as exc:
            raise ValueError(f"environment variable not found: {env_name}") from exc
    if getattr(args, f"{prefix}_stdin"):
        return sys.stdin.read()
    file_name = getattr(args, f"{prefix}_file")
    if file_name is None:
        raise ValueError(f"expected {prefix} text source")
    return Path(file_name).resolve().read_text(encoding="utf-8")
