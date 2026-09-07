from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from agent_tools.tools.java_light_code_map.core import JavaLightCodeMapError
from agent_tools.tools.java_light_code_map.core import LightSymbol
from agent_tools.tools.java_light_code_map.core import SourceSpan
from agent_tools.tools.java_light_code_map.core import parse_light_file
from agent_tools.tools.java_light_code_map.core import render_call_graph as render_light_call_graph
from agent_tools.tools.java_light_code_map.core import render_calls as render_light_calls
from agent_tools.tools.java_light_code_map.core import render_index as render_light_index
from agent_tools.tools.java_light_code_map.core import render_map as render_light_map
from agent_tools.tools.java_light_code_map.core import render_refs as render_light_refs
from agent_tools.tools.java_light_code_map.core import render_symbol_snapshot as render_light_symbol_snapshot


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class JavaCompileContext:
    classpath: tuple[Path, ...] = ()
    sourcepath: tuple[Path, ...] = ()
    release: str | None = None
    javac_args: tuple[str, ...] = ()
    ast_backend: str = "auto"
    jdt_helper: Path | None = None


@dataclass(frozen=True)
class SymbolSnapshot:
    symbol: str
    qualified: str
    kind: str
    span: SourceSpan
    hash: str
    body_span: SourceSpan | None
    body_hash: str | None


@dataclass(frozen=True)
class ResolvedSymbol:
    name: str
    qualified_name: str
    kind: str
    span: SourceSpan
    hash: str
    body_span: SourceSpan | None
    body_hash: str | None


@dataclass(frozen=True)
class ParseCheckResult:
    ok: bool
    diagnostics: tuple[str, ...]
    command: tuple[str, ...]


@dataclass(frozen=True)
class EditResult:
    file_path: Path
    operation: str
    target: str
    changed: bool
    check_only: bool
    old_hash: str | None = None
    new_hash: str | None = None
    snapshot: SymbolSnapshot | None = None
    insert_line: int | None = None
    statement: str | None = None
    diff: str | None = None


@dataclass(frozen=True)
class BatchEditResult:
    operations: tuple[EditResult, ...]
    check_only: bool


class JavaCodeMapError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_json(self) -> str:
        return json.dumps({"error": self.message, "details": self.details}, indent=2)


def compact_help() -> str:
    context = (
        "[--classpath <path>] [--sourcepath <path>] [--release <version>] "
        "[--javac-arg <arg>] [--ast-backend auto|tree-sitter|jdt] "
        "[--jdt-helper <path>] [--allow-fallback]"
    )
    return "\n".join([
        "java_code_map help",
        f"java_code_map doctor <java_file> {context} [--json]",
        f"java_code_map map <java_file> {context} [--json]",
        f"java_code_map index <java_file> [<java_file> ...] {context} [--cache-dir <dir>] [--json]",
        f"java_code_map symbol-get <java_file> --symbol <name> {context} [--json]",
        f"java_code_map calls <java_file> [--symbol <name>] {context} [--json]",
        f"java_code_map call-graph <java_file> {context} [--json]",
        f"java_code_map refs <java_file> --name <identifier-or-qualified-name> [--scope <symbol>] {context} [--json]",
        f"java_code_map parse-check <java_file> [<java_file> ...] {context} [--json]",
        f"java_code_map replace-symbol <java_file> --symbol <name> --expect-hash <sha256> "
        f"(--replacement-env <VAR> | --replacement-file <path> | --replacement-text <text> | --replacement-stdin) "
        f"{context} [--check-only] [--json]",
        f"java_code_map replace-symbol-body <java_file> --symbol <name> --expect-hash <sha256> "
        f"(--replacement-env <VAR> | --replacement-file <path> | --replacement-text <text> | --replacement-stdin) "
        f"{context} [--check-only] [--json]",
        f"java_code_map insert-before-symbol <java_file> --symbol <name> --expect-hash <sha256> "
        f"(--snippet-env <VAR> | --snippet-file <path> | --snippet-text <text> | --snippet-stdin) "
        f"{context} [--check-only] [--json]",
        f"java_code_map insert-after-symbol <java_file> --symbol <name> --expect-hash <sha256> "
        f"(--snippet-env <VAR> | --snippet-file <path> | --snippet-text <text> | --snippet-stdin) "
        f"{context} [--check-only] [--json]",
        "java_code_map imports-add <java_file> --import <statement-or-qualified-name> [--check-only] [--json]",
        f"java_code_map batch (--plan-env <VAR> | --plan-file <path> | --plan-text <json> | --plan-stdin) "
        f"{context} [--check-only] [--json]",
    ])


def render_code_map(file_path: Path,
                    context: JavaCompileContext,
                    *,
                    allow_fallback: bool = False,
                    json_output: bool = False) -> str:
    parse_result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if not parse_result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed",
                               details={"file": str(file_path), "diagnostics": list(parse_result.diagnostics)})
    ast_payload = _ast_payload(file_path, context)
    payload = ast_payload or json.loads(render_light_map(file_path, json_output=True))
    payload.update({
        "schema_version": SCHEMA_VERSION,
        "compile_validated": _javac_validated(parse_result),
        "compiler": "javac",
        "diagnostics": list(parse_result.diagnostics),
        "semantic": payload.get("semantic", False),
        "confidence": payload.get("confidence", "javac-validated-structural"),
        "ast_backend": payload.get("ast_backend", "tree-sitter"),
    })
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        str(file_path),
        "engine: tree-sitter+javac",
        "semantic: false",
        f"compile_validated: {str(parse_result.ok).lower()}",
    ]
    for diagnostic in parse_result.diagnostics:
        lines.append(f"diagnostic: {diagnostic}")
    for symbol in parse_light_file(file_path).symbols:
        lines.extend(_render_symbol(symbol, 0))
    return "\n".join(lines)


def render_symbol_snapshot(file_path: Path,
                           symbol_name: str,
                           context: JavaCompileContext,
                           *,
                           allow_fallback: bool = False,
                           json_output: bool = False) -> str:
    _ensure_compile_valid(file_path, context, allow_fallback=allow_fallback)
    ast_payload = _ast_payload(file_path, context)
    if ast_payload is not None:
        symbol = _resolve_symbol_payload(ast_payload.get("symbols", []), symbol_name, file_path)
        payload = dict(symbol)
        payload["name"] = str(payload.get("name", ""))
        payload["qualified_name"] = str(payload.get("qualified_name", payload["name"]))
    else:
        payload = json.loads(render_light_symbol_snapshot(file_path, symbol_name, json_output=True))
    payload.update({
        "schema_version": SCHEMA_VERSION,
        "compile_validated": _javac_validated(build_parse_check(file_path, context, allow_fallback=allow_fallback)),
        "compiler": "javac",
        "semantic": ast_payload.get("semantic", False) if ast_payload is not None else False,
        "confidence": ast_payload.get("confidence", "javac-validated-structural") if ast_payload is not None else "javac-validated-structural",
        "ast_backend": ast_payload.get("ast_backend", "tree-sitter") if ast_payload is not None else "tree-sitter",
    })
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    return "\n".join([
        f"{file_path} :: symbol-get",
        "engine: tree-sitter+javac",
        "semantic: false",
        f"symbol: {payload['name']}",
        f"qualified: {payload['qualified_name']}",
        f"kind: {payload['kind']}",
        f"span: {_span_text(SourceSpan(**payload['span']))} hash={payload['hash']}",
        f"body: {_span_text(SourceSpan(**payload['body_span']) if payload.get('body_span') else None)} "
        f"hash={payload.get('body_hash')}",
    ])


def render_calls(file_path: Path,
                 context: JavaCompileContext,
                 *,
                 symbol_name: str | None = None,
                 allow_fallback: bool = False,
                 json_output: bool = False) -> str:
    parse_result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if not parse_result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed",
                               details={"file": str(file_path), "diagnostics": list(parse_result.diagnostics)})
    ast_payload = _ast_payload(file_path, context)
    if ast_payload is None:
        payload = json.loads(render_light_calls(file_path, symbol_name=symbol_name, json_output=True))
        return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="calls")
    calls = list(ast_payload.get("calls", []))
    resolved_symbol = _resolve_symbol_payload(ast_payload.get("symbols", []), symbol_name, file_path) if symbol_name else None
    if resolved_symbol is not None:
        calls = [call for call in calls if call.get("enclosing_symbol") == resolved_symbol.get("qualified_name")]
    payload = _analysis_payload(ast_payload, parse_result) | {
        "symbol": symbol_name,
        "calls": calls,
    }
    return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="calls")


def render_call_graph(file_path: Path,
                      context: JavaCompileContext,
                      *,
                      allow_fallback: bool = False,
                      json_output: bool = False) -> str:
    parse_result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if not parse_result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed",
                               details={"file": str(file_path), "diagnostics": list(parse_result.diagnostics)})
    ast_payload = _ast_payload(file_path, context)
    if ast_payload is None:
        payload = json.loads(render_light_call_graph(file_path, json_output=True))
        return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="edges")
    payload = _analysis_payload(ast_payload, parse_result) | {
        "edges": list(ast_payload.get("call_graph", [])),
    }
    return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="edges")


def render_refs(file_path: Path,
                name: str,
                context: JavaCompileContext,
                *,
                scope_symbol: str | None = None,
                allow_fallback: bool = False,
                json_output: bool = False) -> str:
    parse_result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if not parse_result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed",
                               details={"file": str(file_path), "diagnostics": list(parse_result.diagnostics)})
    ast_payload = _ast_payload(file_path, context)
    if ast_payload is None:
        payload = json.loads(render_light_refs(file_path, name, scope_symbol=scope_symbol, json_output=True))
        return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="refs")
    scope = _resolve_symbol_payload(ast_payload.get("symbols", []), scope_symbol, file_path) if scope_symbol else None
    refs = [
        ref for ref in ast_payload.get("references", [])
        if _reference_matches(ref, name)
        and (scope is None or ref.get("enclosing_symbol") == scope.get("qualified_name"))
    ]
    payload = _analysis_payload(ast_payload, parse_result) | {
        "name": name,
        "scope": scope_symbol,
        "refs": refs,
    }
    return _render_analysis_payload(file_path, payload, parse_result, json_output=json_output, lines_key="refs")


def render_symbol_index(file_paths: tuple[Path, ...],
                        context: JavaCompileContext,
                        *,
                        allow_fallback: bool = False,
                        cache_dir: Path | None = None,
                        json_output: bool = False) -> str:
    for file_path in file_paths:
        _ensure_compile_valid(file_path, context, allow_fallback=allow_fallback)
    return render_light_index(file_paths, cache_dir=cache_dir, json_output=json_output)


def render_parse_check(file_path: Path,
                       context: JavaCompileContext,
                       *,
                       allow_fallback: bool = False,
                       json_output: bool = False) -> str:
    result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if json_output:
        return json.dumps(_parse_check_payload(result), indent=2, sort_keys=True)
    return _render_parse_check_text(file_path, result)


def render_parse_checks(file_paths: tuple[Path, ...],
                        context: JavaCompileContext,
                        *,
                        allow_fallback: bool = False,
                        json_output: bool = False) -> str:
    results = tuple((path, build_parse_check(path, context, allow_fallback=allow_fallback)) for path in file_paths)
    if json_output:
        return json.dumps({
            "ok": all(result.ok for _path, result in results),
            "files": [
                {"file": str(path), **_parse_check_payload(result)}
                for path, result in results
            ],
        }, indent=2, sort_keys=True)
    lines = [
        "java_code_map :: parse-check",
        f"ok: {str(all(result.ok for _path, result in results)).lower()}",
    ]
    for path, result in results:
        lines.append(_render_parse_check_text(path, result))
    return "\n".join(lines)


def build_parse_check(file_path: Path,
                      context: JavaCompileContext,
                      *,
                      allow_fallback: bool = False) -> ParseCheckResult:
    source = _read_source(file_path)
    return _build_parse_check_from_source(file_path, source, context, allow_fallback=allow_fallback)


def render_compile_doctor(file_path: Path,
                          context: JavaCompileContext,
                          *,
                          allow_fallback: bool = False,
                          json_output: bool = False) -> str:
    javac = shutil.which("javac")
    source_status = "ok" if file_path.exists() and file_path.is_file() else "missing"
    result = build_parse_check(file_path, context, allow_fallback=allow_fallback) if source_status == "ok" else None
    payload = {
        "ok": source_status == "ok" and javac is not None and (result.ok if result else False),
        "source": {"status": source_status, "path": str(file_path)},
        "compiler": {"status": "ok" if javac else "missing", "path": javac or ""},
        "classpath": [_path_status(path) for path in context.classpath],
        "sourcepath": [_path_status(path) for path in context.sourcepath],
        "release": context.release,
        "javac_args": list(context.javac_args),
        "ast_backend": _backend_status(context),
        "fallback_allowed": allow_fallback,
        "parse_check": _parse_check_payload(result) if result else None,
        "semantic": _backend_status(context)["selected"] == "jdt",
        "confidence": "jdt-ast+javac" if _backend_status(context)["selected"] == "jdt" else "javac-validated-structural",
    }
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        f"{file_path} :: java_code_map doctor",
        f"ok: {str(payload['ok']).lower()}",
        f"source: {source_status} {file_path}",
        f"compiler: {payload['compiler']['status']} {payload['compiler']['path']}".rstrip(),
        f"classpath: {len(context.classpath)}",
        f"sourcepath: {len(context.sourcepath)}",
        f"release: {context.release or ''}".rstrip(),
        f"ast_backend: {payload['ast_backend']['selected']} {payload['ast_backend']['status']}",
        f"fallback_allowed: {str(allow_fallback).lower()}",
    ]
    if result is not None:
        lines.append(f"parse_check: {str(result.ok).lower()}")
        lines.extend(f"diagnostic: {diagnostic}" for diagnostic in result.diagnostics)
    return "\n".join(lines)


def replace_symbol(file_path: Path,
                   symbol_name: str,
                   expected_hash: str,
                   replacement_text: str,
                   context: JavaCompileContext,
                   *,
                   allow_fallback: bool = False,
                   check_only: bool = False) -> EditResult:
    return _replace_span(file_path, symbol_name, expected_hash, replacement_text, context,
                         scope="node", allow_fallback=allow_fallback, check_only=check_only)


def replace_symbol_body(file_path: Path,
                        symbol_name: str,
                        expected_hash: str,
                        replacement_text: str,
                        context: JavaCompileContext,
                        *,
                        allow_fallback: bool = False,
                        check_only: bool = False) -> EditResult:
    return _replace_span(file_path, symbol_name, expected_hash, replacement_text, context,
                         scope="body", allow_fallback=allow_fallback, check_only=check_only)


def insert_before_symbol(file_path: Path,
                         symbol_name: str,
                         expected_hash: str,
                         snippet_text: str,
                         context: JavaCompileContext,
                         *,
                         allow_fallback: bool = False,
                         check_only: bool = False) -> EditResult:
    return _insert_relative(file_path, symbol_name, expected_hash, snippet_text, context,
                            position="before", allow_fallback=allow_fallback, check_only=check_only)


def insert_after_symbol(file_path: Path,
                        symbol_name: str,
                        expected_hash: str,
                        snippet_text: str,
                        context: JavaCompileContext,
                        *,
                        allow_fallback: bool = False,
                        check_only: bool = False) -> EditResult:
    return _insert_relative(file_path, symbol_name, expected_hash, snippet_text, context,
                            position="after", allow_fallback=allow_fallback, check_only=check_only)


def add_import_statement(file_path: Path,
                         import_statement: str,
                         *,
                         check_only: bool = False) -> EditResult:
    source = _read_source(file_path)
    statement = _normalize_import(import_statement)
    if statement in source:
        return EditResult(file_path=file_path,
                          operation="imports-add",
                          target=statement,
                          changed=False,
                          check_only=check_only,
                          statement=statement)
    insert_offset = _import_insert_offset(source)
    new_source = source[:insert_offset] + statement + "\n" + source[insert_offset:]
    if not check_only:
        file_path.write_text(new_source, encoding="utf-8")
    return EditResult(file_path=file_path,
                      operation="imports-add",
                      target=statement,
                      changed=True,
                      check_only=check_only,
                      old_hash=_hash_text(source),
                      new_hash=_hash_text(new_source),
                      statement=statement,
                      diff=_render_unified_diff(source, new_source, file_path))


def apply_batch_edits(plan: object,
                      context: JavaCompileContext,
                      *,
                      allow_fallback: bool = False,
                      check_only: bool = False) -> BatchEditResult:
    operations = _batch_operations(plan)
    results: list[EditResult] = []
    for operation in operations:
        kind = _string_value(operation, "operation")
        path = Path(_string_value(operation, "file_path")).resolve()
        if kind == "replace-symbol":
            results.append(replace_symbol(path,
                                          _string_value(operation, "symbol"),
                                          _string_value(operation, "expect_hash"),
                                          _string_value(operation, "replacement"),
                                          context,
                                          allow_fallback=allow_fallback,
                                          check_only=check_only))
        elif kind == "replace-symbol-body":
            results.append(replace_symbol_body(path,
                                               _string_value(operation, "symbol"),
                                               _string_value(operation, "expect_hash"),
                                               _string_value(operation, "replacement"),
                                               context,
                                               allow_fallback=allow_fallback,
                                               check_only=check_only))
        elif kind == "insert-before-symbol":
            results.append(insert_before_symbol(path,
                                                _string_value(operation, "symbol"),
                                                _string_value(operation, "expect_hash"),
                                                _string_value(operation, "snippet"),
                                                context,
                                                allow_fallback=allow_fallback,
                                                check_only=check_only))
        elif kind == "insert-after-symbol":
            results.append(insert_after_symbol(path,
                                               _string_value(operation, "symbol"),
                                               _string_value(operation, "expect_hash"),
                                               _string_value(operation, "snippet"),
                                               context,
                                               allow_fallback=allow_fallback,
                                               check_only=check_only))
        elif kind == "imports-add":
            results.append(add_import_statement(path,
                                                _string_value(operation, "import"),
                                                check_only=check_only))
        else:
            raise JavaCodeMapError("unsupported batch operation", details={"operation": kind})
    return BatchEditResult(operations=tuple(results), check_only=check_only)


def render_edit_result(result: EditResult, *, json_output: bool = False) -> str:
    if json_output:
        return json.dumps(_edit_result_payload(result), indent=2, sort_keys=True)
    parts = [
        f"target={result.target}",
        f"changed={str(result.changed).lower()}",
        f"check_only={str(result.check_only).lower()}",
    ]
    if result.old_hash is not None:
        parts.append(f"old_hash={result.old_hash}")
    if result.new_hash is not None:
        parts.append(f"new_hash={result.new_hash}")
    if result.insert_line is not None:
        parts.append(f"insert_line={result.insert_line}")
    rendered = f"{result.file_path} :: {result.operation} " + " ".join(parts)
    if result.diff:
        return rendered + "\n" + result.diff
    return rendered


def render_batch_edit_result(result: BatchEditResult, *, json_output: bool = False) -> str:
    if json_output:
        return json.dumps({
            "check_only": result.check_only,
            "operations": [_edit_result_payload(operation) for operation in result.operations],
        }, indent=2, sort_keys=True)
    changed_count = sum(1 for operation in result.operations if operation.changed)
    lines = [
        "java_code_map :: batch "
        + f"operations={len(result.operations)} "
        + f"changed={changed_count} "
        + f"check_only={str(result.check_only).lower()}",
    ]
    for operation in result.operations:
        lines.append("")
        lines.append(render_edit_result(operation))
    return "\n".join(lines)


def _ensure_compile_valid(file_path: Path, context: JavaCompileContext, *, allow_fallback: bool) -> None:
    result = build_parse_check(file_path, context, allow_fallback=allow_fallback)
    if not result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed",
                               details={"file": str(file_path), "diagnostics": list(result.diagnostics)})


def _replace_span(file_path: Path,
                  symbol_name: str,
                  expected_hash: str,
                  replacement_text: str,
                  context: JavaCompileContext,
                  *,
                  scope: str,
                  allow_fallback: bool,
                  check_only: bool) -> EditResult:
    source, symbol = _source_and_symbol(file_path, symbol_name, context, allow_fallback=allow_fallback)
    span = symbol.span if scope == "node" else symbol.body_span
    actual_hash = symbol.hash if scope == "node" else symbol.body_hash
    if span is None or actual_hash is None:
        raise JavaCodeMapError("symbol has no replaceable body" if scope == "body" else "symbol span missing",
                               details={"file": str(file_path), "symbol": symbol.qualified_name})
    if actual_hash != expected_hash:
        raise JavaCodeMapError(f"symbol {scope} hash mismatch",
                               details={"file": str(file_path),
                                        "symbol": symbol.qualified_name,
                                        "expected_hash": expected_hash,
                                        "actual_hash": actual_hash})
    replacement = _normalize_body_replacement(replacement_text, source[span.start_offset:span.end_offset]) \
        if scope == "body" else _normalize_block(replacement_text)
    new_source = source[:span.start_offset] + replacement + source[span.end_offset:]
    _validate_new_source(file_path, new_source, context, allow_fallback=allow_fallback)
    if not check_only:
        file_path.write_text(new_source, encoding="utf-8")
    return EditResult(file_path=file_path,
                      operation="replace-symbol-body" if scope == "body" else "replace-symbol",
                      target=symbol.qualified_name,
                      changed=source != new_source,
                      check_only=check_only,
                      old_hash=actual_hash,
                      new_hash=_hash_text(new_source),
                      snapshot=_snapshot_for_symbol(symbol),
                      diff=_render_unified_diff(source, new_source, file_path))


def _insert_relative(file_path: Path,
                     symbol_name: str,
                     expected_hash: str,
                     snippet_text: str,
                     context: JavaCompileContext,
                     *,
                     position: str,
                     allow_fallback: bool,
                     check_only: bool) -> EditResult:
    source, symbol = _source_and_symbol(file_path, symbol_name, context, allow_fallback=allow_fallback)
    if symbol.hash != expected_hash:
        raise JavaCodeMapError("anchor symbol hash mismatch",
                               details={"file": str(file_path),
                                        "symbol": symbol.qualified_name,
                                        "expected_hash": expected_hash,
                                        "actual_hash": symbol.hash})
    line_offsets = _line_start_offsets(source)
    if position == "before":
        insert_offset = line_offsets[symbol.span.start_line - 1]
    elif position == "after":
        insert_offset = symbol.span.end_offset
        if source[insert_offset:insert_offset + 1] == "\n":
            insert_offset += 1
    else:
        raise ValueError(f"unsupported insert position: {position}")
    snippet = _normalize_block(snippet_text)
    new_source = source[:insert_offset] + snippet + source[insert_offset:]
    _validate_new_source(file_path, new_source, context, allow_fallback=allow_fallback)
    if not check_only:
        file_path.write_text(new_source, encoding="utf-8")
    return EditResult(file_path=file_path,
                      operation=f"insert-{position}-symbol",
                      target=symbol.qualified_name,
                      changed=source != new_source,
                      check_only=check_only,
                      old_hash=symbol.hash,
                      new_hash=_hash_text(new_source),
                      snapshot=_snapshot_for_symbol(symbol),
                      insert_line=symbol.span.start_line if position == "before" else symbol.span.end_line + 1,
                      diff=_render_unified_diff(source, new_source, file_path))


def _source_and_symbol(file_path: Path,
                       symbol_name: str,
                       context: JavaCompileContext,
                       *,
                       allow_fallback: bool) -> tuple[str, ResolvedSymbol]:
    _ensure_compile_valid(file_path, context, allow_fallback=allow_fallback)
    source = _read_source(file_path)
    ast_payload = _ast_payload(file_path, context)
    if ast_payload is not None:
        symbol = _resolve_symbol_payload(ast_payload.get("symbols", []), symbol_name, file_path)
        return source, _anchor_from_symbol_payload(symbol, file_path)
    result = parse_light_file(file_path)
    return result.source, _anchor_from_light_symbol(_resolve_symbol(result.symbols, symbol_name, file_path))


def _validate_new_source(file_path: Path,
                         source: str,
                         context: JavaCompileContext,
                         *,
                         allow_fallback: bool) -> None:
    result = _build_parse_check_from_source(file_path, source, context, allow_fallback=allow_fallback)
    if not result.ok and not allow_fallback:
        raise JavaCodeMapError("javac validation failed after edit",
                               details={"file": str(file_path), "diagnostics": list(result.diagnostics)})


def _build_parse_check_from_source(file_path: Path,
                                   source: str,
                                   context: JavaCompileContext,
                                   *,
                                   allow_fallback: bool) -> ParseCheckResult:
    javac = shutil.which("javac")
    with tempfile.TemporaryDirectory(prefix="java-code-map-") as temp_dir:
        temp_root = Path(temp_dir)
        temp_source = temp_root / file_path.name
        temp_source.write_text(source, encoding="utf-8")
        try:
            light_result = parse_light_file(temp_source)
        except JavaLightCodeMapError as error:
            return ParseCheckResult(ok=False,
                                    diagnostics=(f"tree-sitter: {error.message}",),
                                    command=())
        if light_result.diagnostics:
            return ParseCheckResult(ok=False,
                                    diagnostics=tuple(f"tree-sitter: {diagnostic}"
                                                      for diagnostic in light_result.diagnostics),
                                    command=())
        if javac is None:
            return ParseCheckResult(ok=allow_fallback,
                                    diagnostics=("javac not found",),
                                    command=("javac",))
        output_dir = temp_root / "classes"
        output_dir.mkdir()
        command = _javac_command(javac, temp_source, output_dir, context)
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    diagnostics = tuple(line for line in (completed.stderr + completed.stdout).splitlines() if line.strip())
    return ParseCheckResult(ok=completed.returncode == 0, diagnostics=diagnostics, command=tuple(command))


def _javac_command(javac: str, source_file: Path, output_dir: Path, context: JavaCompileContext) -> list[str]:
    command = [javac, "-proc:none", "-d", str(output_dir)]
    if context.release:
        command.extend(["--release", context.release])
    if context.classpath:
        command.extend(["-classpath", os.pathsep.join(str(path) for path in context.classpath)])
    if context.sourcepath:
        command.extend(["-sourcepath", os.pathsep.join(str(path) for path in context.sourcepath)])
    command.extend(context.javac_args)
    command.append(str(source_file))
    return command


def _ast_payload(file_path: Path, context: JavaCompileContext) -> dict[str, Any] | None:
    backend = _normalize_ast_backend(context.ast_backend)
    helper = _resolve_jdt_helper(context)
    if backend == "tree-sitter":
        return None
    if helper is None or not _jdt_helper_runnable(helper):
        if backend == "jdt":
            raise JavaCodeMapError(
                "JDT AST helper not found",
                details={
                    "hint": "build agent_tools/tools/java_code_map/jdt_backend, pass --jdt-helper, and ensure java is on PATH for jar helpers",
                    "env": "AGENT_TOOLS_JAVA_CODE_MAP_JDT_HELPER",
                },
            )
        return None
    return _run_jdt_helper(helper, file_path, context)


def _normalize_ast_backend(value: str) -> str:
    if value not in {"auto", "tree-sitter", "jdt"}:
        raise JavaCodeMapError("unsupported Java AST backend", details={"backend": value})
    return value


def _resolve_jdt_helper(context: JavaCompileContext) -> Path | None:
    if context.jdt_helper is not None:
        return context.jdt_helper.resolve() if context.jdt_helper.exists() else None
    candidates: list[Path] = []
    env_value = os.environ.get("AGENT_TOOLS_JAVA_CODE_MAP_JDT_HELPER")
    if env_value:
        candidates.append(Path(env_value))
    candidates.append(Path(__file__).resolve().parent / "jdt_backend/build/libs/java-code-map-jdt-backend.jar")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _jdt_helper_runnable(helper: Path) -> bool:
    return helper.suffix != ".jar" or shutil.which("java") is not None


def _backend_status(context: JavaCompileContext) -> dict[str, Any]:
    backend = _normalize_ast_backend(context.ast_backend)
    helper = _resolve_jdt_helper(context)
    runnable = helper is not None and _jdt_helper_runnable(helper)
    selected = "jdt" if backend == "jdt" or (backend == "auto" and runnable) else "tree-sitter"
    return {
        "requested": backend,
        "selected": selected,
        "status": "ok" if selected == "tree-sitter" or runnable else "missing",
        "helper": str(helper) if helper is not None else "",
    }


def _run_jdt_helper(helper: Path, file_path: Path, context: JavaCompileContext) -> dict[str, Any]:
    command = _jdt_helper_command(helper, file_path, context)
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise JavaCodeMapError(
            "JDT AST helper failed",
            details={"command": command, "error": str(exc)},
        ) from exc
    if completed.returncode != 0:
        raise JavaCodeMapError(
            "JDT AST helper failed",
            details={"command": command, "stderr": completed.stderr.strip(), "stdout": completed.stdout.strip()},
        )
    try:
        payload = _parse_jdt_helper_json(completed.stdout)
    except json.JSONDecodeError as exc:
        raise JavaCodeMapError(
            "JDT AST helper returned invalid JSON",
            details={"command": command, "stdout": completed.stdout[:1000]},
        ) from exc
    if not isinstance(payload, dict):
        raise JavaCodeMapError("JDT AST helper returned non-object JSON", details={"command": command})
    payload.setdefault("ast_backend", "jdt")
    payload.setdefault("engine", "jdt")
    payload.setdefault("semantic", True)
    payload.setdefault("confidence", "jdt-ast+javac")
    return payload


def _parse_jdt_helper_json(stdout: str) -> object:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start < 0 or end < start:
            raise
        return json.loads(stdout[start:end + 1])


def _jdt_helper_command(helper: Path, file_path: Path, context: JavaCompileContext) -> list[str]:
    if helper.suffix == ".jar":
        command = ["java", "-jar", str(helper)]
    else:
        command = [str(helper)]
    command.extend(["map", "--file", str(file_path)])
    for path in context.classpath:
        command.extend(["--classpath", str(path)])
    for path in context.sourcepath:
        command.extend(["--sourcepath", str(path)])
    if context.release:
        command.extend(["--release", context.release])
    return command


def _resolve_symbol_payload(symbols: object, symbol_name: str, file_path: Path) -> dict[str, Any]:
    matches = [
        symbol for symbol in _flatten_symbol_payloads(symbols)
        if symbol.get("qualified_name") == symbol_name or symbol.get("name") == symbol_name
    ]
    if not matches:
        raise JavaCodeMapError("symbol not found", details={"file": str(file_path), "symbol": symbol_name})
    if len(matches) > 1:
        raise JavaCodeMapError(
            "symbol is ambiguous",
            details={"file": str(file_path), "symbol": symbol_name, "matches": [item.get("qualified_name") for item in matches]},
        )
    return dict(matches[0])


def _flatten_symbol_payloads(symbols: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(symbols, list):
        return ()
    result: list[dict[str, Any]] = []
    for symbol in symbols:
        if not isinstance(symbol, dict):
            continue
        result.append(symbol)
        result.extend(_flatten_symbol_payloads(symbol.get("children", [])))
    return tuple(result)


def _path_status(path: Path) -> dict[str, str]:
    return {"path": str(path), "status": "ok" if path.exists() else "missing"}


def _parse_check_payload(result: ParseCheckResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "ok": result.ok,
        "compile_validated": _javac_validated(result),
        "diagnostics": list(result.diagnostics),
        "command": list(result.command),
    }


def _analysis_payload(ast_payload: dict[str, Any], parse_result: ParseCheckResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "file": ast_payload.get("file", ""),
        "engine": ast_payload.get("engine", "jdt"),
        "ast_backend": ast_payload.get("ast_backend", "jdt"),
        "semantic": ast_payload.get("semantic", True),
        "confidence": ast_payload.get("confidence", "jdt-ast+javac"),
        "compile_validated": _javac_validated(parse_result),
        "compiler": "javac",
        "diagnostics": list(parse_result.diagnostics),
    }


def _render_analysis_payload(file_path: Path,
                             payload: dict[str, Any],
                             parse_result: ParseCheckResult,
                             *,
                             json_output: bool,
                             lines_key: str) -> str:
    payload.update({
        "schema_version": SCHEMA_VERSION,
        "compile_validated": _javac_validated(parse_result),
        "compiler": "javac",
        "diagnostics": list(parse_result.diagnostics),
        "semantic": payload.get("semantic", False),
        "confidence": payload.get("confidence", "javac-validated-structural"),
        "ast_backend": payload.get("ast_backend", "tree-sitter"),
    })
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        str(file_path),
        f"engine: {payload.get('engine', '')}+javac",
        f"semantic: {str(bool(payload.get('semantic'))).lower()}",
        f"compile_validated: {str(bool(payload.get('compile_validated'))).lower()}",
    ]
    for diagnostic in parse_result.diagnostics:
        lines.append(f"diagnostic: {diagnostic}")
    if lines_key == "calls":
        lines.extend(
            f"{call.get('line')}:{call.get('column')} {call.get('qualified_name') or call.get('name')} "
            f"in {call.get('enclosing_symbol', '')}"
            for call in payload.get("calls", [])
        )
    elif lines_key == "edges":
        lines.extend(
            f"{edge.get('from')} -> {edge.get('to')} @ {edge.get('line')}:{edge.get('column')}"
            for edge in payload.get("edges", [])
        )
    elif lines_key == "refs":
        lines.extend(
            f"{ref.get('line')}:{ref.get('column')} {ref.get('binding_kind') or ref.get('kind')} "
            f"{ref.get('qualified_name') or ref.get('name')} in {ref.get('enclosing_symbol', '')}"
            for ref in payload.get("refs", [])
        )
    return "\n".join(lines)


def _javac_validated(result: ParseCheckResult) -> bool:
    return result.ok and result.command and result.command[0] != "javac"


def _render_parse_check_text(file_path: Path, result: ParseCheckResult) -> str:
    lines = [f"{file_path} :: javac parse-check {'ok' if result.ok else 'failed'}"]
    lines.extend(f"diagnostic: {diagnostic}" for diagnostic in result.diagnostics)
    return "\n".join(lines)


def _reference_matches(ref: object, name: str) -> bool:
    if not isinstance(ref, dict):
        return False
    return name in {
        str(ref.get("name", "")),
        str(ref.get("qualified_name", "")),
        str(ref.get("binding_key", "")),
    }


def _resolve_symbol(symbols: tuple[LightSymbol, ...], symbol_name: str, file_path: Path) -> LightSymbol:
    flattened = _flatten_symbols(symbols)
    matches = [symbol for symbol in flattened if symbol.qualified_name == symbol_name or symbol.name == symbol_name]
    if not matches:
        raise JavaCodeMapError("symbol not found", details={"file": str(file_path), "symbol": symbol_name})
    if len(matches) > 1:
        raise JavaCodeMapError("symbol is ambiguous",
                               details={"file": str(file_path),
                                        "symbol": symbol_name,
                                        "matches": [match.qualified_name for match in matches]})
    return matches[0]


def _flatten_symbols(symbols: tuple[LightSymbol, ...]) -> tuple[LightSymbol, ...]:
    flattened: list[LightSymbol] = []
    for symbol in symbols:
        flattened.append(symbol)
        flattened.extend(_flatten_symbols(symbol.children))
    return tuple(flattened)


def _anchor_from_light_symbol(symbol: LightSymbol) -> ResolvedSymbol:
    return ResolvedSymbol(name=symbol.name,
                          qualified_name=symbol.qualified_name,
                          kind=symbol.kind,
                          span=symbol.span,
                          hash=symbol.hash,
                          body_span=symbol.body_span,
                          body_hash=symbol.body_hash)


def _anchor_from_symbol_payload(symbol: dict[str, Any], file_path: Path) -> ResolvedSymbol:
    name = symbol.get("name")
    span = symbol.get("span")
    if not isinstance(name, str) or not isinstance(span, dict):
        raise JavaCodeMapError("JDT symbol payload is missing anchor fields",
                               details={"file": str(file_path), "symbol": name or "<unknown>"})
    qualified_name = symbol.get("qualified_name", name)
    kind = symbol.get("kind", "")
    symbol_hash = symbol.get("hash")
    body_span = symbol.get("body_span")
    body_hash = symbol.get("body_hash")
    if not isinstance(qualified_name, str) or not isinstance(kind, str) or not isinstance(symbol_hash, str):
        raise JavaCodeMapError("JDT symbol payload has invalid anchor fields",
                               details={"file": str(file_path), "symbol": name})
    if body_span is not None and not isinstance(body_span, dict):
        raise JavaCodeMapError("JDT symbol payload has invalid body span",
                               details={"file": str(file_path), "symbol": qualified_name})
    if body_hash is not None and not isinstance(body_hash, str):
        raise JavaCodeMapError("JDT symbol payload has invalid body hash",
                               details={"file": str(file_path), "symbol": qualified_name})
    try:
        parsed_span = SourceSpan(**span)
        parsed_body_span = SourceSpan(**body_span) if body_span is not None else None
    except TypeError as exc:
        raise JavaCodeMapError("JDT symbol payload has incomplete span fields",
                               details={"file": str(file_path), "symbol": qualified_name}) from exc
    return ResolvedSymbol(name=name,
                          qualified_name=qualified_name,
                          kind=kind,
                          span=parsed_span,
                          hash=symbol_hash,
                          body_span=parsed_body_span,
                          body_hash=body_hash)


def _snapshot_for_symbol(symbol: ResolvedSymbol) -> SymbolSnapshot:
    return SymbolSnapshot(symbol=symbol.name,
                          qualified=symbol.qualified_name,
                          kind=symbol.kind,
                          span=symbol.span,
                          hash=symbol.hash,
                          body_span=symbol.body_span,
                          body_hash=symbol.body_hash)


def _edit_result_payload(result: EditResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["file_path"] = str(result.file_path)
    return payload


def _batch_operations(plan: object) -> list[dict[str, object]]:
    if isinstance(plan, list):
        operations = plan
    elif isinstance(plan, dict):
        operations = plan.get("operations", [])
    else:
        raise JavaCodeMapError("batch plan must be a JSON object or array")
    if not isinstance(operations, list):
        raise JavaCodeMapError("batch plan must include an operations list")
    result: list[dict[str, object]] = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise JavaCodeMapError("batch operation must be an object")
        result.append(operation)
    return result


def _string_value(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise JavaCodeMapError("batch operation field must be a string", details={"field": key})
    return value


def _normalize_import(import_statement: str) -> str:
    text = import_statement.strip()
    if not text.startswith("import "):
        text = f"import {text}"
    if not text.endswith(";"):
        text = text + ";"
    return text


def _import_insert_offset(source: str) -> int:
    offsets = _line_start_offsets(source)
    lines = source.splitlines(keepends=True)
    insert_line = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("package ") or stripped.startswith("import "):
            insert_line = index + 1
            continue
        if stripped == "":
            continue
        break
    return offsets[insert_line] if insert_line < len(offsets) else len(source)


def _normalize_block(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    return normalized if normalized.endswith("\n") else normalized + "\n"


def _normalize_body_replacement(replacement: str, old_text: str) -> str:
    normalized = replacement.replace("\r\n", "\n")
    if old_text.startswith("\n") and not normalized.startswith("\n"):
        normalized = "\n" + normalized
    if old_text.endswith("\n") and not normalized.endswith("\n"):
        normalized = normalized + "\n"
    return normalized


def _render_symbol(symbol: LightSymbol, indent: int) -> list[str]:
    prefix = "  " * indent
    lines = [
        f"{prefix}{symbol.kind} {symbol.qualified_name} "
        f"[{_span_text(symbol.span)}] hash={symbol.hash} body_hash={symbol.body_hash}",
    ]
    for child in symbol.children:
        lines.extend(_render_symbol(child, indent + 1))
    return lines


def _line_start_offsets(source: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(source):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _span_text(span: SourceSpan | None) -> str:
    if span is None:
        return "<none>"
    return f"{span.start_line}:{span.start_column}-{span.end_line}:{span.end_column}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render_unified_diff(old_source: str, new_source: str, file_path: Path) -> str:
    return "".join(difflib.unified_diff(old_source.splitlines(keepends=True),
                                        new_source.splitlines(keepends=True),
                                        fromfile=f"{file_path}:before",
                                        tofile=f"{file_path}:after"))


def _read_source(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise JavaCodeMapError("failed to read source file", details={"file": str(file_path), "error": str(exc)}) from exc
