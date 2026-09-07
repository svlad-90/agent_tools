from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .core import JavaCodeMapError
from .core import JavaCompileContext
from .core import add_import_statement
from .core import apply_batch_edits
from .core import compact_help
from .core import insert_after_symbol
from .core import insert_before_symbol
from .core import render_batch_edit_result
from .core import render_code_map
from .core import render_compile_doctor
from .core import render_edit_result
from .core import render_call_graph
from .core import render_calls
from .core import render_parse_check
from .core import render_parse_checks
from .core import render_refs
from .core import render_symbol_index
from .core import render_symbol_snapshot
from .core import replace_symbol
from .core import replace_symbol_body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print and edit Java source maps with javac validation.")
    subparsers = parser.add_subparsers(dest="command")

    map_parser = subparsers.add_parser("map", help="Print a javac-validated Java symbol map.")
    _add_java_context_args(map_parser)
    map_parser.add_argument("--json", action="store_true")

    doctor_parser = subparsers.add_parser("doctor", help="Explain javac argument selection and validation.")
    _add_java_context_args(doctor_parser)
    doctor_parser.add_argument("--json", action="store_true")

    index_parser = subparsers.add_parser("index", help="Cache Java symbol maps for one or more files.")
    index_parser.add_argument("java_files", nargs="+")
    _add_shared_context_args(index_parser)
    index_parser.add_argument("--cache-dir")
    index_parser.add_argument("--json", action="store_true")

    symbol_parser = subparsers.add_parser("symbol-get", help="Print a Java symbol snapshot.")
    _add_java_context_args(symbol_parser)
    symbol_parser.add_argument("--symbol", required=True)
    symbol_parser.add_argument("--json", action="store_true")

    calls_parser = subparsers.add_parser("calls", help="List javac-validated Java calls.")
    _add_java_context_args(calls_parser)
    calls_parser.add_argument("--symbol")
    calls_parser.add_argument("--json", action="store_true")

    graph_parser = subparsers.add_parser("call-graph", help="List javac-validated Java call graph edges.")
    _add_java_context_args(graph_parser)
    graph_parser.add_argument("--json", action="store_true")

    refs_parser = subparsers.add_parser("refs", help="List javac-validated Java references.")
    _add_java_context_args(refs_parser)
    refs_parser.add_argument("--name", required=True)
    refs_parser.add_argument("--scope")
    refs_parser.add_argument("--json", action="store_true")

    parse_parser = subparsers.add_parser("parse-check", help="Run javac validation for one or more Java files.")
    parse_parser.add_argument("java_files", nargs="+")
    _add_shared_context_args(parse_parser)
    parse_parser.add_argument("--json", action="store_true")

    replace_parser = subparsers.add_parser("replace-symbol", help="Replace one Java symbol with hash guard.")
    _add_edit_args(replace_parser, "replacement")

    replace_body_parser = subparsers.add_parser("replace-symbol-body", help="Replace one Java symbol body with hash guard.")
    _add_edit_args(replace_body_parser, "replacement")

    insert_before_parser = subparsers.add_parser("insert-before-symbol", help="Insert code before an anchor symbol.")
    _add_edit_args(insert_before_parser, "snippet")

    insert_after_parser = subparsers.add_parser("insert-after-symbol", help="Insert code after an anchor symbol.")
    _add_edit_args(insert_after_parser, "snippet")

    imports_parser = subparsers.add_parser("imports-add", help="Insert one Java import statement if missing.")
    imports_parser.add_argument("java_file")
    imports_parser.add_argument("--import", dest="import_statement", required=True)
    imports_parser.add_argument("--check-only", action="store_true")
    imports_parser.add_argument("--json", action="store_true")

    batch_parser = subparsers.add_parser("batch", help="Apply a JSON plan of guarded Java edit commands.")
    batch_group = batch_parser.add_mutually_exclusive_group(required=True)
    batch_group.add_argument("--plan-env")
    batch_group.add_argument("--plan-file")
    batch_group.add_argument("--plan-text")
    batch_group.add_argument("--plan-stdin", action="store_true")
    _add_shared_context_args(batch_parser)
    batch_parser.add_argument("--check-only", action="store_true")
    batch_parser.add_argument("--json", action="store_true")

    subparsers.add_parser("help", help="Print compact help.")

    args = parser.parse_args(argv)
    if args.command in (None, "help"):
        print(compact_help())
        return 0

    try:
        return _run_command(args, parser)
    except (JavaCodeMapError, ValueError) as error:
        message = error.to_json() if isinstance(error, JavaCodeMapError) else json.dumps({"error": str(error)}, indent=2)
        print(message, file=sys.stderr)
        return 2


def _run_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    context = _compile_context(args)
    allow_fallback = bool(getattr(args, "allow_fallback", False))
    if args.command == "map":
        print(render_code_map(Path(args.java_file).resolve(), context, allow_fallback=allow_fallback, json_output=args.json))
    elif args.command == "doctor":
        print(render_compile_doctor(Path(args.java_file).resolve(), context, allow_fallback=allow_fallback, json_output=args.json))
    elif args.command == "index":
        print(render_symbol_index(tuple(Path(item).resolve() for item in args.java_files),
                                  context,
                                  allow_fallback=allow_fallback,
                                  cache_dir=Path(args.cache_dir).resolve() if args.cache_dir else None,
                                  json_output=args.json))
    elif args.command == "symbol-get":
        print(render_symbol_snapshot(Path(args.java_file).resolve(),
                                     args.symbol,
                                     context,
                                     allow_fallback=allow_fallback,
                                     json_output=args.json))
    elif args.command == "calls":
        print(render_calls(Path(args.java_file).resolve(),
                           context,
                           symbol_name=args.symbol,
                           allow_fallback=allow_fallback,
                           json_output=args.json))
    elif args.command == "call-graph":
        print(render_call_graph(Path(args.java_file).resolve(),
                                context,
                                allow_fallback=allow_fallback,
                                json_output=args.json))
    elif args.command == "refs":
        print(render_refs(Path(args.java_file).resolve(),
                          args.name,
                          context,
                          scope_symbol=args.scope,
                          allow_fallback=allow_fallback,
                          json_output=args.json))
    elif args.command == "parse-check":
        paths = tuple(Path(item).resolve() for item in args.java_files)
        if len(paths) == 1:
            text = render_parse_check(paths[0], context, allow_fallback=allow_fallback, json_output=args.json)
        else:
            text = render_parse_checks(paths, context, allow_fallback=allow_fallback, json_output=args.json)
        print(text)
        return 0 if _parse_check_ok(text, json_output=args.json) else 2
    elif args.command == "replace-symbol":
        result = replace_symbol(Path(args.java_file).resolve(),
                                args.symbol,
                                args.expect_hash,
                                _resolve_text(args, "replacement"),
                                context,
                                allow_fallback=allow_fallback,
                                check_only=args.check_only)
        print(render_edit_result(result, json_output=args.json))
    elif args.command == "replace-symbol-body":
        result = replace_symbol_body(Path(args.java_file).resolve(),
                                     args.symbol,
                                     args.expect_hash,
                                     _resolve_text(args, "replacement"),
                                     context,
                                     allow_fallback=allow_fallback,
                                     check_only=args.check_only)
        print(render_edit_result(result, json_output=args.json))
    elif args.command == "insert-before-symbol":
        result = insert_before_symbol(Path(args.java_file).resolve(),
                                      args.symbol,
                                      args.expect_hash,
                                      _resolve_text(args, "snippet"),
                                      context,
                                      allow_fallback=allow_fallback,
                                      check_only=args.check_only)
        print(render_edit_result(result, json_output=args.json))
    elif args.command == "insert-after-symbol":
        result = insert_after_symbol(Path(args.java_file).resolve(),
                                     args.symbol,
                                     args.expect_hash,
                                     _resolve_text(args, "snippet"),
                                     context,
                                     allow_fallback=allow_fallback,
                                     check_only=args.check_only)
        print(render_edit_result(result, json_output=args.json))
    elif args.command == "imports-add":
        result = add_import_statement(Path(args.java_file).resolve(),
                                      args.import_statement,
                                      check_only=args.check_only)
        print(render_edit_result(result, json_output=args.json))
    elif args.command == "batch":
        result = apply_batch_edits(_load_batch_plan(args),
                                   context,
                                   allow_fallback=allow_fallback,
                                   check_only=args.check_only)
        print(render_batch_edit_result(result, json_output=args.json))
    else:
        parser.error(f"unknown command {args.command!r}")
    return 0


def _parse_check_ok(text: str, *, json_output: bool) -> bool:
    if json_output:
        payload = json.loads(text)
        return bool(payload.get("ok"))
    return " failed" not in text and "ok: false" not in text


def _add_java_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("java_file")
    _add_shared_context_args(parser)


def _add_shared_context_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--classpath", action="append", default=[])
    parser.add_argument("--sourcepath", action="append", default=[])
    parser.add_argument("--release")
    parser.add_argument("--javac-arg", action="append", default=[])
    parser.add_argument("--ast-backend", choices=("auto", "tree-sitter", "jdt"), default="auto")
    parser.add_argument("--jdt-helper")
    parser.add_argument("--allow-fallback", action="store_true")


def _add_edit_args(parser: argparse.ArgumentParser, text_kind: str) -> None:
    _add_java_context_args(parser)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--expect-hash", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(f"--{text_kind}-env")
    group.add_argument(f"--{text_kind}-file")
    group.add_argument(f"--{text_kind}-text")
    group.add_argument(f"--{text_kind}-stdin", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--json", action="store_true")


def _compile_context(args: argparse.Namespace) -> JavaCompileContext:
    return JavaCompileContext(
        classpath=tuple(Path(item).resolve() for item in getattr(args, "classpath", [])),
        sourcepath=tuple(Path(item).resolve() for item in getattr(args, "sourcepath", [])),
        release=getattr(args, "release", None),
        javac_args=tuple(getattr(args, "javac_arg", [])),
        ast_backend=getattr(args, "ast_backend", "auto"),
        jdt_helper=Path(args.jdt_helper).resolve() if getattr(args, "jdt_helper", None) else None,
    )


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


def _load_batch_plan(args: argparse.Namespace) -> object:
    if args.plan_text is not None:
        return json.loads(args.plan_text)
    if args.plan_env is not None:
        try:
            return json.loads(os.environ[args.plan_env])
        except KeyError as exc:
            raise ValueError(f"environment variable not found: {args.plan_env}") from exc
    if args.plan_stdin:
        return json.loads(sys.stdin.read())
    if args.plan_file is not None:
        return json.loads(Path(args.plan_file).resolve().read_text(encoding="utf-8"))
    raise ValueError("expected batch plan source")
