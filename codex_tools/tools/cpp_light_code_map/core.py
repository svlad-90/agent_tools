from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import difflib
import fnmatch
import hashlib
from importlib import metadata
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
SOURCE_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}


@dataclass(frozen=True)
class SourceSpan:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class LightSymbol:
    name: str
    qualified_name: str
    kind: str
    span: SourceSpan
    body_span: SourceSpan | None
    hash: str
    body_hash: str | None
    children: tuple["LightSymbol", ...] = ()


@dataclass(frozen=True)
class LightParseResult:
    source: str
    symbols: tuple[LightSymbol, ...]
    engine: str
    diagnostics: tuple[str, ...] = ()


class CppLightCodeMapError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def compact_help() -> str:
    return "\n".join([
        "cpp_light_code_map help",
        "cpp_light_code_map map <cpp_file> [--compact] [--json]",
        "cpp_light_code_map outline <cpp_file> [--compact] [--json]",
        "cpp_light_code_map diagnose <cpp_file> [--json]",
        "cpp_light_code_map unmapped <cpp_file> [--json]",
        "cpp_light_code_map symbols <cpp_file> [--kind <kind>] [--name <text>] "
        "[--contains <line>] [--compact] [--json]",
        "cpp_light_code_map symbol-get <cpp_file> --symbol <name> [--with-doc] [--json]",
        "cpp_light_code_map includes <cpp_file> [--json]",
        "cpp_light_code_map macros <cpp_file> [--json]",
        "cpp_light_code_map calls <cpp_file> [--symbol <name>] [--json]",
        "cpp_light_code_map call-graph <cpp_file> [--json]",
        "cpp_light_code_map refs <cpp_file> --name <identifier> [--scope <symbol>] [--json]",
        "cpp_light_code_map locals <cpp_file> --symbol <name> [--json]",
        "cpp_light_code_map complexity <cpp_file> [--symbol <name>] [--json]",
        "cpp_light_code_map parse-check <cpp_file> [--json]",
        "cpp_light_code_map index <cpp_file> [<cpp_file> ...] [--cache-dir <dir>] [--json]",
        "cpp_light_code_map index-dir <dir> [--include <glob>] [--exclude <glob>] "
        "[--cache-dir <dir>] [--json]",
        "cpp_light_code_map query --name <name> [--cache-dir <dir>] [--json]",
        "cpp_light_code_map rename-symbol <cpp_file> --symbol <name> --expect-hash <sha256> "
        "--new-name <identifier> [--scope <symbol>] [--check-only] [--json]",
        "cpp_light_code_map replace-symbol <cpp_file> --symbol <name> --expect-hash <sha256> "
        "(--replacement-env <VAR> | --replacement-file <path> | --replacement-text <text> | --replacement-stdin) "
        "[--check-only] [--json]",
        "cpp_light_code_map replace-symbol-body <cpp_file> --symbol <name> --expect-hash <sha256> "
        "(--replacement-env <VAR> | --replacement-file <path> | --replacement-text <text> | --replacement-stdin) "
        "[--check-only] [--json]",
        "cpp_light_code_map insert-before-symbol <cpp_file> --symbol <name> --expect-hash <sha256> "
        "(--snippet-env <VAR> | --snippet-file <path> | --snippet-text <text> | --snippet-stdin) "
        "[--check-only] [--json]",
        "cpp_light_code_map insert-after-symbol <cpp_file> --symbol <name> --expect-hash <sha256> "
        "(--snippet-env <VAR> | --snippet-file <path> | --snippet-text <text> | --snippet-stdin) "
        "[--check-only] [--json]",
    ])


def render_diagnose(file_path: Path, *, json_output: bool = False) -> str:
    package_versions: dict[str, str] = {}
    packages_ok = True
    for package in ("tree-sitter", "tree-sitter-cpp"):
        try:
            package_versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages_ok = False
            package_versions[package] = "missing"
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    symbols = tuple(_flatten_symbols(result.symbols))
    calls = _collect_calls(tree.root_node, source_bytes, _line_start_offsets(result.source), result.symbols, None)
    unmapped = _collect_unmapped_nodes(tree.root_node, source_bytes, _line_start_offsets(result.source))
    payload = _base_payload(file_path, engine=result.engine) | {
        "ok": packages_ok and not result.diagnostics,
        "packages": package_versions,
        "readable": True,
        "syntax_errors": tree.root_node.has_error,
        "diagnostics": list(result.diagnostics),
        "symbol_count": len(symbols),
        "symbol_kinds": _kind_counts(symbol.kind for symbol in symbols),
        "call_count": len(calls),
        "unmapped_count": len(unmapped),
        "unmapped_node_types": _kind_counts(item["node_type"] for item in unmapped),
    }
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [
        f"{file_path} :: diagnose",
        f"engine: {result.engine}",
        f"ok: {str(payload['ok']).lower()}",
        f"packages: {payload['packages']}",
        f"symbols: {payload['symbol_count']} {payload['symbol_kinds']}",
        f"calls: {payload['call_count']}",
        f"unmapped: {payload['unmapped_count']} {payload['unmapped_node_types']}",
    ]
    lines.extend(f"diagnostic: {diagnostic}" for diagnostic in result.diagnostics)
    return "\n".join(lines)


def render_unmapped(file_path: Path, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    unmapped = _collect_unmapped_nodes(tree.root_node, source_bytes, _line_start_offsets(result.source))
    payload = _base_payload(file_path, engine=result.engine) | {
        "unmapped": unmapped,
        "node_types": _kind_counts(item["node_type"] for item in unmapped),
    }
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    lines.extend(f"{item['line']}:{item['column']} {item['node_type']} {item['text']}" for item in unmapped)
    return "\n".join(lines)


def render_map(file_path: Path, *, compact: bool = False, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    if json_output:
        return json.dumps(_base_payload(file_path, engine=result.engine) | {
            "diagnostics": list(result.diagnostics),
            "symbols": [_symbol_payload(symbol) for symbol in result.symbols],
        }, indent=2)
    lines = [
        str(file_path),
        f"engine: {result.engine}",
        "semantic: false",
        "compile_validated: false",
    ]
    for diagnostic in result.diagnostics:
        lines.append(f"diagnostic: {diagnostic}")
    for symbol in result.symbols:
        lines.extend(_render_symbol(symbol, 0, compact=compact))
    return "\n".join(lines)


def render_symbols(file_path: Path,
                   *,
                   kind: str | None = None,
                   name: str | None = None,
                   contains_line: int | None = None,
                   compact: bool = False,
                   json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    symbols = tuple(_filtered_symbols(result.symbols,
                                      kind=kind,
                                      name=name,
                                      contains_line=contains_line))
    if json_output:
        return json.dumps(_base_payload(file_path, engine=result.engine) | {
            "filters": {"kind": kind, "name": name, "contains_line": contains_line},
            "symbols": [_symbol_payload(symbol, include_children=False) for symbol in symbols],
        }, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    for symbol in symbols:
        lines.extend(_render_symbol(symbol, 0, compact=compact, include_children=False))
    return "\n".join(lines)


def render_symbol_snapshot(file_path: Path,
                           symbol_name: str,
                           *,
                           with_doc: bool = False,
                           json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    payload = _base_payload(file_path, engine=result.engine) | _symbol_payload(symbol)
    if with_doc:
        payload["doc"] = _preceding_doc_block(result.source, symbol.span.start_offset)
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [
        f"{file_path} :: symbol-get",
        f"engine: {result.engine}",
        "semantic: false",
        f"symbol: {symbol.name}",
        f"qualified: {symbol.qualified_name}",
        f"kind: {symbol.kind}",
        f"span: {_span_text(symbol.span)} hash={symbol.hash}",
        f"body: {_span_text(symbol.body_span)} hash={symbol.body_hash}",
    ]
    if with_doc and payload.get("doc"):
        lines.append("doc:")
        lines.append(str(payload["doc"]))
    return "\n".join(lines)


def render_includes(file_path: Path, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    includes = _collect_includes(tree.root_node, source_bytes, _line_start_offsets(result.source))
    if json_output:
        return json.dumps(_base_payload(file_path, engine=result.engine) | {
            "diagnostics": list(result.diagnostics),
            "includes": includes,
        }, indent=2)
    lines = [
        str(file_path),
        f"engine: {result.engine}",
        "semantic: false",
    ]
    for diagnostic in result.diagnostics:
        lines.append(f"diagnostic: {diagnostic}")
    lines.extend(f"{item['line']}: {item['text']}" for item in includes)
    return "\n".join(lines)


def render_macros(file_path: Path, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    macros = _collect_macros(tree.root_node, source_bytes, _line_start_offsets(result.source))
    payload = _base_payload(file_path, engine=result.engine) | {"macros": macros}
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    lines.extend(f"{macro['line']}: {macro['kind']} {macro['name']}" for macro in macros)
    return "\n".join(lines)


def render_calls(file_path: Path, *, symbol_name: str | None = None, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    target_span: SourceSpan | None = None
    if symbol_name:
        target_span = _resolve_symbol(result.symbols, symbol_name, file_path).span
    calls = _collect_calls(tree.root_node, source_bytes, _line_start_offsets(result.source), result.symbols, target_span)
    payload = _base_payload(file_path, engine=result.engine) | {
        "symbol": symbol_name,
        "calls": calls,
    }
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    lines.extend(f"{call['line']}:{call['column']} {call['name']} in {call['enclosing_symbol']}" for call in calls)
    return "\n".join(lines)


def render_call_graph(file_path: Path, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    calls = _collect_calls(tree.root_node, source_bytes, _line_start_offsets(result.source), result.symbols, None)
    edges = [
        {"from": call["enclosing_symbol"], "to": call["name"], "line": call["line"], "column": call["column"]}
        for call in calls
        if call["enclosing_symbol"]
    ]
    payload = _base_payload(file_path, engine=result.engine) | {"edges": edges}
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    lines.extend(f"{edge['from']} -> {edge['to']} @ {edge['line']}:{edge['column']}" for edge in edges)
    return "\n".join(lines)


def render_refs(file_path: Path,
                name: str,
                *,
                scope_symbol: str | None = None,
                json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    target_span = _resolve_symbol(result.symbols, scope_symbol, file_path).span if scope_symbol else None
    refs = _collect_refs(tree.root_node, source_bytes, _line_start_offsets(result.source), result.symbols, name, target_span)
    payload = _base_payload(file_path, engine=result.engine) | {
        "name": name,
        "scope": scope_symbol,
        "refs": refs,
    }
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    lines.extend(f"{ref['line']}:{ref['column']} {ref['kind']} in {ref['enclosing_symbol']}" for ref in refs)
    return "\n".join(lines)


def render_locals(file_path: Path, symbol_name: str, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    body_node = _node_for_span(tree.root_node, symbol.span.start_offset, symbol.span.end_offset)
    locals_payload = _collect_locals(body_node, source_bytes, _line_start_offsets(result.source)) if body_node else []
    payload = _base_payload(file_path, engine=result.engine) | {
        "symbol": symbol.qualified_name,
        "locals": locals_payload,
    }
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false", f"symbol: {symbol.qualified_name}"]
    lines.extend(f"{item['line']}:{item['column']} {item['kind']} {item['name']}" for item in locals_payload)
    return "\n".join(lines)


def render_complexity(file_path: Path, *, symbol_name: str | None = None, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source_bytes, tree = _tree_sitter_parse(result.source)
    symbols = (_resolve_symbol(result.symbols, symbol_name, file_path),) if symbol_name else tuple(
        symbol for symbol in _flatten_symbols(result.symbols) if symbol.kind == "function"
    )
    metrics = []
    for symbol in symbols:
        node = _node_for_span(tree.root_node, symbol.span.start_offset, symbol.span.end_offset)
        metrics.append(_complexity_for_symbol(symbol, node, source_bytes) if node else _empty_complexity(symbol))
    payload = _base_payload(file_path, engine=result.engine) | {"metrics": metrics}
    if json_output:
        return json.dumps(payload, indent=2)
    lines = [str(file_path), f"engine: {result.engine}", "semantic: false"]
    for item in metrics:
        lines.append(
            f"{item['symbol']} lines={item['lines']} branches={item['branches']} "
            f"loops={item['loops']} returns={item['returns']} calls={item['calls']} max_nesting={item['max_nesting']}"
        )
    return "\n".join(lines)


def render_parse_check(file_path: Path, *, json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    diagnostics = list(result.diagnostics)
    if _brace_balance(_mask_comments_and_strings(result.source)) != 0:
        diagnostics.append("brace balance is not zero after masking comments and strings")
    payload = _base_payload(file_path, engine=result.engine) | {
        "ok": not diagnostics,
        "diagnostics": diagnostics,
        "symbol_count": len(tuple(_flatten_symbols(result.symbols))),
    }
    if json_output:
        return json.dumps(payload, indent=2)
    status = "ok" if payload["ok"] else "error"
    lines = [f"{file_path} :: structural parse-check {status}"]
    lines.extend(diagnostics)
    return "\n".join(lines)


def render_index(file_paths: tuple[Path, ...],
                 *,
                 cache_dir: Path | None = None,
                 json_output: bool = False) -> str:
    target_cache_dir = (cache_dir or Path(".cache/cpp_light_code_map")).resolve()
    target_cache_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    ok = True
    for file_path in file_paths:
        source_path = file_path.resolve()
        item: dict[str, Any] = {"file": str(source_path), "status": "ok"}
        try:
            result = parse_light_file(source_path)
            cache_path = target_cache_dir / f"{_index_cache_key(source_path, result.source)}.json"
            payload = _base_payload(source_path, engine=result.engine) | {
                "symbols": [_symbol_payload(symbol) for symbol in result.symbols],
            }
            cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            item["cache"] = str(cache_path)
            item["symbol_count"] = len(tuple(_flatten_symbols(result.symbols)))
        except Exception as exc:
            ok = False
            item["status"] = "error"
            item["error"] = str(exc)
        files.append(item)
    payload = {"schema_version": SCHEMA_VERSION, "ok": ok, "cache_dir": str(target_cache_dir), "files": files}
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = ["cpp_light_code_map :: index", f"ok: {str(ok).lower()}", f"cache_dir: {target_cache_dir}"]
    lines.extend(f"{item['status']} {item['file']} symbols={item.get('symbol_count', 0)}" for item in files)
    return "\n".join(lines)


def render_index_dir(root_path: Path,
                     *,
                     includes: tuple[str, ...] = (),
                     excludes: tuple[str, ...] = (),
                     cache_dir: Path | None = None,
                     json_output: bool = False) -> str:
    files = tuple(_collect_index_dir_files(root_path, includes=includes, excludes=excludes))
    return render_index(files, cache_dir=cache_dir, json_output=json_output)


def render_query(name: str, *, cache_dir: Path | None = None, json_output: bool = False) -> str:
    target_cache_dir = (cache_dir or Path(".cache/cpp_light_code_map")).resolve()
    matches: list[dict[str, Any]] = []
    for cache_file in sorted(target_cache_dir.glob("*.json")):
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        for symbol in _flatten_symbol_payloads(payload.get("symbols", [])):
            if name in symbol.get("qualified_name", "") or name in symbol.get("name", ""):
                matches.append({"file": payload.get("file", ""), "symbol": symbol, "cache": str(cache_file)})
    payload = {"schema_version": SCHEMA_VERSION, "cache_dir": str(target_cache_dir), "name": name, "matches": matches}
    if json_output:
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = ["cpp_light_code_map :: query", f"cache_dir: {target_cache_dir}", f"matches: {len(matches)}"]
    lines.extend(f"{match['file']} :: {match['symbol']['qualified_name']}" for match in matches)
    return "\n".join(lines)


def render_rename_symbol(file_path: Path,
                         symbol_name: str,
                         expected_hash: str,
                         new_name: str,
                         *,
                         scope_symbol: str | None = None,
                         check_only: bool = False,
                         json_output: bool = False) -> str:
    if not new_name.isidentifier():
        raise CppLightCodeMapError("new name must be a valid identifier", details={"new_name": new_name})
    result = parse_light_file(file_path)
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    if symbol.hash != expected_hash:
        raise CppLightCodeMapError("symbol hash mismatch",
                                   details={"file": str(file_path),
                                            "symbol": symbol.qualified_name,
                                            "expected_hash": expected_hash,
                                            "actual_hash": symbol.hash})
    old_name = symbol.name.split("::")[-1]
    source_bytes, tree = _tree_sitter_parse(result.source)
    scope = _resolve_symbol(result.symbols, scope_symbol, file_path).span if scope_symbol else symbol.span
    refs = _collect_refs(tree.root_node,
                         source_bytes,
                         _line_start_offsets(result.source),
                         result.symbols,
                         old_name,
                         scope)
    spans = sorted({(ref["span"]["start_offset"], ref["span"]["end_offset"]) for ref in refs}, reverse=True)
    new_source = result.source
    for start, end in spans:
        new_source = new_source[:start] + new_name + new_source[end:]
    return _render_edit_payload(file_path,
                                "rename-symbol",
                                symbol.qualified_name,
                                result.source,
                                new_source,
                                check_only=check_only,
                                json_output=json_output,
                                engine=result.engine,
                                old_hash=symbol.hash)


def render_replace_symbol(file_path: Path,
                          symbol_name: str,
                          expected_hash: str,
                          replacement_text: str,
                          *,
                          check_only: bool = False,
                          json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source = result.source
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    if symbol.hash != expected_hash:
        raise CppLightCodeMapError("symbol hash mismatch",
                                   details={"file": str(file_path),
                                            "symbol": symbol.qualified_name,
                                            "expected_hash": expected_hash,
                                            "actual_hash": symbol.hash})
    replacement = _normalize_block(replacement_text)
    new_source = source[:symbol.span.start_offset] + replacement + source[symbol.span.end_offset:]
    return _render_edit_payload(file_path,
                                "replace-symbol",
                                symbol.qualified_name,
                                source,
                                new_source,
                                check_only=check_only,
                                json_output=json_output,
                                engine=result.engine,
                                old_hash=symbol.hash)


def render_replace_symbol_body(file_path: Path,
                               symbol_name: str,
                               expected_hash: str,
                               replacement_text: str,
                               *,
                               check_only: bool = False,
                               json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source = result.source
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    if symbol.body_span is None or symbol.body_hash is None:
        raise CppLightCodeMapError("symbol has no replaceable body",
                                   details={"file": str(file_path), "symbol": symbol.qualified_name})
    if symbol.body_hash != expected_hash:
        raise CppLightCodeMapError("symbol body hash mismatch",
                                   details={
                                       "file": str(file_path),
                                       "symbol": symbol.qualified_name,
                                       "expected_hash": expected_hash,
                                       "actual_hash": symbol.body_hash,
                                   })
    replacement = _normalize_body_replacement(replacement_text,
                                              old_text=source[symbol.body_span.start_offset:symbol.body_span.end_offset])
    new_source = source[:symbol.body_span.start_offset] + replacement + source[symbol.body_span.end_offset:]
    return _render_edit_payload(file_path,
                                "replace-symbol-body",
                                symbol.qualified_name,
                                source,
                                new_source,
                                check_only=check_only,
                                json_output=json_output,
                                engine=result.engine,
                                old_hash=symbol.body_hash)


def render_insert_relative_to_symbol(file_path: Path,
                                     symbol_name: str,
                                     expected_hash: str,
                                     snippet_text: str,
                                     *,
                                     position: str,
                                     check_only: bool = False,
                                     json_output: bool = False) -> str:
    result = parse_light_file(file_path)
    source = result.source
    symbol = _resolve_symbol(result.symbols, symbol_name, file_path)
    if symbol.hash != expected_hash:
        raise CppLightCodeMapError("anchor symbol hash mismatch",
                                   details={"file": str(file_path),
                                            "symbol": symbol.qualified_name,
                                            "expected_hash": expected_hash,
                                            "actual_hash": symbol.hash})
    if position == "before":
        insert_offset = _line_start_offsets(source)[symbol.span.start_line - 1]
    elif position == "after":
        insert_offset = symbol.span.end_offset
        if source[insert_offset:insert_offset + 1] == "\n":
            insert_offset += 1
    else:
        raise ValueError(f"unsupported insert position: {position}")
    snippet = _normalize_block(snippet_text)
    new_source = source[:insert_offset] + snippet + source[insert_offset:]
    return _render_edit_payload(file_path,
                                f"insert-{position}-symbol",
                                symbol.qualified_name,
                                source,
                                new_source,
                                check_only=check_only,
                                json_output=json_output,
                                engine=result.engine,
                                old_hash=symbol.hash)


def parse_light_file(file_path: Path) -> LightParseResult:
    source = _read_source(file_path)
    return _parse_tree_sitter(source)


def parse_light_symbols(file_path: Path) -> tuple[str, tuple[LightSymbol, ...]]:
    result = parse_light_file(file_path)
    return result.source, result.symbols


def _parse_tree_sitter(source: str) -> LightParseResult:
    source_bytes, tree = _tree_sitter_parse(source)
    line_offsets = _line_start_offsets(source)
    diagnostics: list[str] = []
    if tree.root_node.has_error:
        diagnostics.append("tree-sitter reported syntax errors")
    symbols = tuple(_tree_sitter_symbols(tree.root_node, source, source_bytes, line_offsets, ()))
    return LightParseResult(source=source,
                            symbols=symbols,
                            engine="tree-sitter",
                            diagnostics=tuple(diagnostics))


def _tree_sitter_parse(source: str) -> tuple[bytes, Any]:
    try:
        from tree_sitter import Language
        from tree_sitter import Parser
        import tree_sitter_cpp
    except ImportError as exc:
        raise CppLightCodeMapError(
            "tree-sitter backend is required for cpp_light_code_map",
            details={"packages": ["tree-sitter", "tree-sitter-cpp"]},
        ) from exc
    parser = Parser(Language(tree_sitter_cpp.language()))
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    return source_bytes, tree


def _tree_sitter_symbols(node: Any,
                         source: str,
                         source_bytes: bytes,
                         line_offsets: list[int],
                         parents: tuple[str, ...]) -> list[LightSymbol]:
    symbols: list[LightSymbol] = []
    for child in node.children:
        symbol = _tree_sitter_symbol(child, source, source_bytes, line_offsets, parents)
        if symbol is not None:
            symbols.append(symbol)
            continue
        symbols.extend(_tree_sitter_symbols(child, source, source_bytes, line_offsets, parents))
    return symbols


def _collect_calls(node: Any,
                   source_bytes: bytes,
                   line_offsets: list[int],
                   symbols: tuple[LightSymbol, ...],
                   target_span: SourceSpan | None) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    if node.type == "call_expression" and _node_in_span(node, target_span):
        callee = node.children[0] if node.children else None
        if callee is not None:
            span = _span_from_offsets(line_offsets, callee.start_byte, callee.end_byte)
            calls.append({
                "name": _node_text(callee, source_bytes).replace(" ", ""),
                "line": span.start_line,
                "column": span.start_column,
                "span": asdict(span),
                "enclosing_symbol": _enclosing_symbol_name(span.start_offset, symbols),
            })
    for child in node.children:
        calls.extend(_collect_calls(child, source_bytes, line_offsets, symbols, target_span))
    return calls


def _collect_refs(node: Any,
                  source_bytes: bytes,
                  line_offsets: list[int],
                  symbols: tuple[LightSymbol, ...],
                  name: str,
                  target_span: SourceSpan | None = None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    if node.type in {"identifier", "field_identifier", "type_identifier", "namespace_identifier"} and _node_in_span(node, target_span):
        text = _node_text(node, source_bytes)
        if text == name:
            span = _span_from_offsets(line_offsets, node.start_byte, node.end_byte)
            refs.append({
                "kind": node.type,
                "category": _ref_category(node),
                "line": span.start_line,
                "column": span.start_column,
                "span": asdict(span),
                "enclosing_symbol": _enclosing_symbol_name(span.start_offset, symbols),
            })
    for child in node.children:
        refs.extend(_collect_refs(child, source_bytes, line_offsets, symbols, name, target_span))
    return refs


def _ref_category(node: Any) -> str:
    if node.type in {"type_identifier", "namespace_identifier"}:
        return "type"
    if node.type == "field_identifier":
        return "field"
    parent = getattr(node, "parent", None)
    if parent is not None and parent.type in {"declaration", "init_declarator", "parameter_declaration"}:
        return "declaration"
    return "identifier"


def _collect_macros(node: Any, source_bytes: bytes, line_offsets: list[int]) -> list[dict[str, Any]]:
    macros: list[dict[str, Any]] = []
    if node.type in {"preproc_def", "preproc_function_def", "preproc_call", "preproc_ifdef", "preproc_ifndef"}:
        span = _span_from_offsets(line_offsets, node.start_byte, node.end_byte)
        macros.append({
            "kind": node.type,
            "name": _macro_name(node, source_bytes),
            "line": span.start_line,
            "column": span.start_column,
            "text": _node_text(node, source_bytes).strip(),
            "span": asdict(span),
        })
    for child in node.children:
        macros.extend(_collect_macros(child, source_bytes, line_offsets))
    return macros


def _macro_name(node: Any, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type == "identifier":
            return _node_text(child, source_bytes)
    text = _node_text(node, source_bytes).strip()
    parts = text.split()
    return parts[1].split("(", 1)[0] if len(parts) > 1 else ""


def _collect_locals(node: Any, source_bytes: bytes, line_offsets: list[int]) -> list[dict[str, Any]]:
    locals_payload: list[dict[str, Any]] = []
    _collect_locals_into(node, source_bytes, line_offsets, locals_payload)
    seen: set[tuple[str, str, int, int]] = set()
    deduped: list[dict[str, Any]] = []
    for item in locals_payload:
        key = (item["kind"], item["name"], item["line"], item["column"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _collect_locals_into(node: Any,
                         source_bytes: bytes,
                         line_offsets: list[int],
                         result: list[dict[str, Any]]) -> None:
    if node.type == "parameter_declaration":
        name_node = _last_identifier_child(node)
        if name_node is not None:
            result.append(_local_payload("parameter", name_node, source_bytes, line_offsets))
    elif node.type in {"declaration", "init_declarator"}:
        for name_node in _declaration_identifier_nodes(node):
            result.append(_local_payload("local", name_node, source_bytes, line_offsets))
    elif node.type == "labeled_statement":
        label = _first_child(node, {"statement_identifier", "identifier"})
        if label is not None:
            result.append(_local_payload("label", label, source_bytes, line_offsets))
    for child in node.children:
        _collect_locals_into(child, source_bytes, line_offsets, result)


def _local_payload(kind: str, node: Any, source_bytes: bytes, line_offsets: list[int]) -> dict[str, Any]:
    span = _span_from_offsets(line_offsets, node.start_byte, node.end_byte)
    return {
        "kind": kind,
        "name": _node_text(node, source_bytes),
        "line": span.start_line,
        "column": span.start_column,
        "span": asdict(span),
    }


def _last_identifier_child(node: Any) -> Any | None:
    matches: list[Any] = []
    _identifier_nodes_into(node, matches)
    return matches[-1] if matches else None


def _declaration_identifier_nodes(node: Any) -> list[Any]:
    result: list[Any] = []
    for child in node.children:
        if child.type in {"identifier", "field_identifier"}:
            result.append(child)
        elif child.type in {"init_declarator", "pointer_declarator", "array_declarator", "reference_declarator"}:
            identifier = _last_identifier_child(child)
            if identifier is not None:
                result.append(identifier)
    return result


def _identifier_nodes_into(node: Any, result: list[Any]) -> None:
    if node.type in {"identifier", "field_identifier"}:
        result.append(node)
    for child in node.children:
        _identifier_nodes_into(child, result)


def _node_for_span(node: Any, start_offset: int, end_offset: int) -> Any | None:
    if node.start_byte == start_offset and node.end_byte == end_offset:
        return node
    for child in node.children:
        if child.start_byte <= start_offset and end_offset <= child.end_byte:
            found = _node_for_span(child, start_offset, end_offset)
            if found is not None:
                return found
    return None


def _complexity_for_symbol(symbol: LightSymbol, node: Any, source_bytes: bytes) -> dict[str, Any]:
    counts = {
        "branches": 0,
        "loops": 0,
        "returns": 0,
        "calls": 0,
        "max_nesting": 0,
    }
    _complexity_walk(node, source_bytes, counts, nesting=0)
    counts["symbol"] = symbol.qualified_name
    counts["lines"] = symbol.span.end_line - symbol.span.start_line + 1
    return counts


def _empty_complexity(symbol: LightSymbol) -> dict[str, Any]:
    return {
        "symbol": symbol.qualified_name,
        "lines": symbol.span.end_line - symbol.span.start_line + 1,
        "branches": 0,
        "loops": 0,
        "returns": 0,
        "calls": 0,
        "max_nesting": 0,
    }


def _complexity_walk(node: Any, source_bytes: bytes, counts: dict[str, Any], *, nesting: int) -> None:
    branch_types = {"if_statement", "conditional_expression", "case_statement"}
    loop_types = {"for_statement", "while_statement", "do_statement", "for_range_loop"}
    next_nesting = nesting
    if node.type in branch_types:
        counts["branches"] += 1
        next_nesting += 1
    elif node.type in loop_types:
        counts["loops"] += 1
        next_nesting += 1
    elif node.type == "return_statement":
        counts["returns"] += 1
    elif node.type == "call_expression":
        counts["calls"] += 1
    counts["max_nesting"] = max(counts["max_nesting"], next_nesting)
    for child in node.children:
        _complexity_walk(child, source_bytes, counts, nesting=next_nesting)


def _filtered_symbols(symbols: tuple[LightSymbol, ...],
                      *,
                      kind: str | None,
                      name: str | None,
                      contains_line: int | None) -> list[LightSymbol]:
    result: list[LightSymbol] = []
    for symbol in _flatten_symbols(symbols):
        if kind and symbol.kind != kind:
            continue
        if name and name not in symbol.qualified_name and name not in symbol.name:
            continue
        if contains_line is not None and not (symbol.span.start_line <= contains_line <= symbol.span.end_line):
            continue
        result.append(symbol)
    return result


def _collect_index_dir_files(root_path: Path,
                             *,
                             includes: tuple[str, ...],
                             excludes: tuple[str, ...]) -> list[Path]:
    include_patterns = includes or tuple(f"*{extension}" for extension in sorted(SOURCE_EXTENSIONS))
    exclude_patterns = excludes or (
        ".git/*",
        "build/*",
        "out/*",
        ".cache/*",
        "*/.git/*",
        "*/build/*",
        "*/out/*",
        "*/.cache/*",
    )
    files: list[Path] = []
    root = root_path.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(root))
        absolute = str(path)
        if any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(absolute, pattern) for pattern in exclude_patterns):
            continue
        if any(fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in include_patterns):
            files.append(path)
    return files


def _collect_unmapped_nodes(node: Any, source_bytes: bytes, line_offsets: list[int]) -> list[dict[str, Any]]:
    unmapped: list[dict[str, Any]] = []
    for child in node.children:
        if _tree_sitter_kind(child) is not None or _is_mapped_or_noise_node(child):
            continue
        span = _span_from_offsets(line_offsets, child.start_byte, child.end_byte)
        unmapped.append({
            "node_type": child.type,
            "line": span.start_line,
            "column": span.start_column,
            "span": asdict(span),
            "text": _node_text(child, source_bytes).strip().splitlines()[0][:120] if child.end_byte > child.start_byte else "",
        })
    return unmapped


def _is_mapped_or_noise_node(node: Any) -> bool:
    return node.type in {
        "comment",
        "preproc_include",
        "preproc_def",
        "preproc_function_def",
        "preproc_call",
        "preproc_if",
        "preproc_ifdef",
        "preproc_ifndef",
        "preproc_else",
        "preproc_elif",
        "preproc_endif",
        "using_declaration",
    }


def _kind_counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return dict(sorted(counts.items()))


def _render_edit_payload(file_path: Path,
                         operation: str,
                         target: str,
                         old_source: str,
                         new_source: str,
                         *,
                         check_only: bool,
                         json_output: bool,
                         engine: str,
                         old_hash: str | None) -> str:
    diff = _render_unified_diff(old_source, new_source, file_path)
    if not check_only:
        file_path.write_text(new_source, encoding="utf-8")
    payload = _base_payload(file_path, engine=engine) | {
        "operation": operation,
        "target": target,
        "changed": old_source != new_source,
        "check_only": check_only,
        "old_hash": old_hash,
        "new_hash": _hash_text(new_source),
        "diff": diff,
    }
    if json_output:
        return json.dumps(payload, indent=2)
    return "\n".join([
        f"{file_path} :: {operation} target={target} "
        f"changed={str(payload['changed']).lower()} check_only={str(check_only).lower()}",
        diff or "",
    ]).rstrip()


def _normalize_block(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    return normalized if normalized.endswith("\n") else normalized + "\n"


def _index_cache_key(file_path: Path, source: str) -> str:
    payload = {
        "file": str(file_path),
        "source_hash": _hash_text(source),
        "engine": "tree-sitter",
        "version": 1,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _flatten_symbol_payloads(symbols: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for symbol in symbols:
        result.append(symbol)
        result.extend(_flatten_symbol_payloads(symbol.get("children", [])))
    return tuple(result)


def _preceding_doc_block(source: str, start_offset: int) -> str:
    before = source[:start_offset].rstrip()
    if not before:
        return ""
    lines = before.splitlines()
    block: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped in {"/*", "/**", "*/"}:
            block.append(line)
            continue
        if stripped.endswith("*/"):
            block.append(line)
            continue
        break
    return "\n".join(reversed(block)).strip()


def _node_in_span(node: Any, span: SourceSpan | None) -> bool:
    if span is None:
        return True
    return span.start_offset <= node.start_byte and node.end_byte <= span.end_offset


def _enclosing_symbol_name(offset: int, symbols: tuple[LightSymbol, ...]) -> str:
    matches = [
        symbol for symbol in _flatten_symbols(symbols)
        if symbol.span.start_offset <= offset <= symbol.span.end_offset
    ]
    if not matches:
        return ""
    return max(matches, key=lambda symbol: symbol.span.start_offset).qualified_name


def _tree_sitter_symbol(node: Any,
                        source: str,
                        source_bytes: bytes,
                        line_offsets: list[int],
                        parents: tuple[str, ...]) -> LightSymbol | None:
    kind = _tree_sitter_kind(node)
    if kind is None:
        return None
    name = _tree_sitter_name(node, source_bytes)
    if not name:
        return None
    if kind in {"class", "struct", "union", "enum"} and _tree_sitter_body_node(node) is None:
        return None
    qualified_name = _qualified_name(name, parents)
    child_parents = (*parents, name)
    child_root = _tree_sitter_body_node(node) or node
    children = tuple(_tree_sitter_symbols(child_root, source, source_bytes, line_offsets, child_parents))
    span = _span_from_offsets(line_offsets, node.start_byte, node.end_byte)
    body_span = _tree_sitter_body_span(node, line_offsets)
    return LightSymbol(name=name,
                       qualified_name=qualified_name,
                       kind=kind,
                       span=span,
                       body_span=body_span,
                       hash=_hash_text(source[span.start_offset:span.end_offset]),
                       body_hash=_hash_text(source[body_span.start_offset:body_span.end_offset])
                       if body_span is not None else None,
                       children=children)


def _tree_sitter_kind(node: Any) -> str | None:
    if node.type == "declaration" and _is_global_declaration(node):
        return "global_variable"
    if node.type == "function_definition":
        node_text = getattr(node, "text", b"").decode("utf-8", errors="replace")
        if "~" in node_text.split("(", 1)[0]:
            return "destructor"
        if _is_method_node(node):
            declarator_text = ""
            try:
                declarator = node.child_by_field_name("declarator") or _first_child(node, {"function_declarator"})
                if declarator is not None:
                    declarator_text = declarator.text.decode("utf-8", errors="replace")
            except Exception:
                declarator_text = ""
            class_name = _enclosing_type_name(node)
            if class_name and (f"{class_name}(" in declarator_text or f"{class_name}::" in declarator_text):
                return "constructor"
            return "method"
        return "function"
    return {
        "namespace_definition": "namespace",
        "class_specifier": "class",
        "struct_specifier": "struct",
        "union_specifier": "union",
        "enum_specifier": "enum",
        "alias_declaration": "type_alias",
        "type_definition": "type_alias",
        "field_declaration": "field",
        "enumerator": "enum_value",
        "lambda_expression": "lambda",
    }.get(node.type)


def _tree_sitter_name(node: Any, source_bytes: bytes) -> str | None:
    if node.type == "namespace_definition":
        return _first_child_text(node, source_bytes, {"namespace_identifier"}) or "anonymous_namespace"
    if node.type in {"class_specifier", "struct_specifier", "union_specifier", "enum_specifier"}:
        return _first_child_text(node, source_bytes, {"type_identifier", "identifier"})
    if node.type in {"alias_declaration", "type_definition"}:
        return _type_alias_name(node, source_bytes)
    if node.type == "declaration":
        return _declarator_name(node, source_bytes)
    if node.type in {"field_declaration", "enumerator"}:
        return _declarator_name(node, source_bytes)
    if node.type == "lambda_expression":
        return f"lambda@{node.start_byte}"
    if node.type == "function_definition":
        declarator = node.child_by_field_name("declarator") or _first_child(node, {"function_declarator"})
        if declarator is None:
            return None
        return _declarator_name(declarator, source_bytes)
    return None


def _tree_sitter_body_node(node: Any) -> Any | None:
    for child in node.children:
        if child.type in {"declaration_list", "field_declaration_list", "compound_statement", "enumerator_list"}:
            return child
    return None


def _is_method_node(node: Any) -> bool:
    parent = getattr(node, "parent", None)
    while parent is not None:
        if parent.type in {"class_specifier", "struct_specifier", "union_specifier", "field_declaration_list"}:
            return True
        if parent.type in {"translation_unit", "namespace_definition"}:
            return False
        parent = getattr(parent, "parent", None)
    return False


def _is_global_declaration(node: Any) -> bool:
    parent = getattr(node, "parent", None)
    while parent is not None:
        if parent.type in {"compound_statement", "field_declaration_list", "parameter_list"}:
            return False
        if parent.type in {"translation_unit", "namespace_definition"}:
            return True
        parent = getattr(parent, "parent", None)
    return False


def _enclosing_type_name(node: Any) -> str:
    parent = getattr(node, "parent", None)
    while parent is not None:
        if parent.type in {"class_specifier", "struct_specifier", "union_specifier"}:
            for child in parent.children:
                if child.type in {"type_identifier", "identifier"}:
                    return getattr(child, "text", b"").decode("utf-8", errors="replace")
        parent = getattr(parent, "parent", None)
    return ""


def _type_alias_name(node: Any, source_bytes: bytes) -> str | None:
    for child in node.children:
        if child.type in {"type_identifier", "identifier"}:
            return _node_text(child, source_bytes)
    return _declarator_name(node, source_bytes)


def _tree_sitter_body_span(node: Any, line_offsets: list[int]) -> SourceSpan | None:
    body = _tree_sitter_body_node(node)
    if body is None:
        return None
    start = body.start_byte
    end = body.end_byte
    if body.child_count >= 2 and body.children[0].type == "{" and body.children[-1].type == "}":
        start = body.children[0].end_byte
        end = body.children[-1].start_byte
    return _span_from_offsets(line_offsets, start, end)


def _declarator_name(node: Any, source_bytes: bytes) -> str | None:
    if node.type in {"identifier", "field_identifier", "type_identifier", "destructor_name", "operator_name"}:
        return _node_text(node, source_bytes)
    if node.type in {"qualified_identifier", "template_function"}:
        return _node_text(node, source_bytes).replace(" ", "")
    for child in node.children:
        if child.type == "parameter_list":
            break
        name = _declarator_name(child, source_bytes)
        if name:
            return name
    for child in node.children:
        name = _declarator_name(child, source_bytes)
        if name:
            return name
    return None


def _first_child(node: Any, types: set[str]) -> Any | None:
    for child in node.children:
        if child.type in types:
            return child
    return None


def _first_child_text(node: Any, source_bytes: bytes, types: set[str]) -> str | None:
    child = _first_child(node, types)
    return _node_text(child, source_bytes) if child is not None else None


def _node_text(node: Any, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _qualified_name(name: str, parents: tuple[str, ...]) -> str:
    if "::" in name:
        return "::".join((*parents, *[part for part in name.split("::") if part]))
    return "::".join((*parents, name))


def _collect_includes(node: Any, source_bytes: bytes, line_offsets: list[int]) -> list[dict[str, Any]]:
    includes: list[dict[str, Any]] = []
    if node.type == "preproc_include":
        span = _span_from_offsets(line_offsets, node.start_byte, node.end_byte)
        includes.append({
            "line": span.start_line,
            "column": span.start_column,
            "text": _node_text(node, source_bytes).strip(),
            "span": asdict(span),
        })
    for child in node.children:
        includes.extend(_collect_includes(child, source_bytes, line_offsets))
    return includes


def _resolve_symbol(symbols: tuple[LightSymbol, ...], symbol_name: str, file_path: Path) -> LightSymbol:
    matches = [
        symbol for symbol in _flatten_symbols(symbols)
        if symbol.qualified_name == symbol_name or symbol.name == symbol_name
    ]
    if not matches:
        raise CppLightCodeMapError("symbol not found", details={"file": str(file_path), "symbol": symbol_name})
    if len(matches) > 1:
        raise CppLightCodeMapError("symbol is ambiguous",
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


def _symbol_payload(symbol: LightSymbol, *, include_children: bool = True) -> dict[str, Any]:
    payload = {
        "name": symbol.name,
        "qualified_name": symbol.qualified_name,
        "kind": symbol.kind,
        "span": asdict(symbol.span),
        "body_span": asdict(symbol.body_span) if symbol.body_span else None,
        "hash": symbol.hash,
        "body_hash": symbol.body_hash,
    }
    if include_children:
        payload["children"] = [_symbol_payload(child) for child in symbol.children]
    return payload


def _base_payload(file_path: Path, *, engine: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "file": str(file_path),
        "engine": engine,
        "semantic": False,
        "compile_validated": False,
        "confidence": "structural-only",
    }


def _render_symbol(symbol: LightSymbol,
                   indent: int,
                   *,
                   compact: bool = False,
                   include_children: bool = True) -> list[str]:
    prefix = "  " * indent
    if compact:
        lines = [f"{prefix}{symbol.kind} {symbol.qualified_name} {_span_text(symbol.span)}"]
    else:
        lines = [
            f"{prefix}{symbol.kind} {symbol.qualified_name} "
            f"{_span_text(symbol.span)} hash={symbol.hash[:12]} body_hash={(symbol.body_hash or '')[:12]}"
        ]
    if include_children:
        for child in symbol.children:
            lines.extend(_render_symbol(child, indent + 1, compact=compact))
    return lines


def _normalize_body_replacement(text: str, *, old_text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    stripped = normalized.strip()
    if len(stripped) >= 2 and stripped[0] == "{" and stripped[-1] == "}":
        normalized = stripped[1:-1]
    if old_text.startswith("\n") and not normalized.startswith("\n"):
        normalized = "\n" + normalized
    if old_text.endswith("\n") and not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def _mask_comments_and_strings(source: str) -> str:
    chars = list(source)
    index = 0
    while index < len(chars):
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < len(chars) else ""
        if char == "/" and next_char == "/":
            end = source.find("\n", index)
            end = len(chars) if end == -1 else end
            _mask_range(chars, index, end)
            index = end
            continue
        if char == "/" and next_char == "*":
            end = source.find("*/", index + 2)
            end = len(chars) - 2 if end == -1 else end
            _mask_range(chars, index, end + 2)
            index = end + 2
            continue
        if char in {'"', "'"}:
            quote = char
            end = index + 1
            escaped = False
            while end < len(chars):
                current = chars[end]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    end += 1
                    break
                end += 1
            _mask_range(chars, index, end)
            index = end
            continue
        index += 1
    return "".join(chars)


def _mask_range(chars: list[str], start: int, end: int) -> None:
    for index in range(start, min(end, len(chars))):
        if chars[index] != "\n":
            chars[index] = " "


def _brace_balance(source: str) -> int:
    return source.count("{") - source.count("}")


def _line_start_offsets(source: str) -> list[int]:
    offsets = [0]
    for index, char in enumerate(source):
        if char == "\n":
            offsets.append(index + 1)
    return offsets


def _span_from_offsets(line_offsets: list[int], start: int, end: int) -> SourceSpan:
    start_line, start_column = _line_column_from_offset(line_offsets, start)
    end_line, end_column = _line_column_from_offset(line_offsets, end)
    return SourceSpan(start_line, start_column, end_line, end_column, start, end)


def _line_column_from_offset(line_offsets: list[int], offset: int) -> tuple[int, int]:
    line_number = 1
    line_start = 0
    for index, candidate in enumerate(line_offsets, start=1):
        if candidate > offset:
            break
        line_number = index
        line_start = candidate
    return line_number, offset - line_start + 1


def _span_text(span: SourceSpan | None) -> str:
    if span is None:
        return "none"
    return f"{span.start_line}:{span.start_column}-{span.end_line}:{span.end_column}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render_unified_diff(old: str, new: str, file_path: Path) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True),
                                        new.splitlines(keepends=True),
                                        fromfile=str(file_path),
                                        tofile=str(file_path)))


def _read_source(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CppLightCodeMapError("failed to read source file",
                                   details={"file": str(file_path), "error": str(exc)}) from exc
