from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from agent_tools.tools.cpp_light_code_map.core import CppLightCodeMapError
from agent_tools.tools.cpp_light_code_map.core import render_call_graph
from agent_tools.tools.cpp_light_code_map.core import render_calls
from agent_tools.tools.cpp_light_code_map.core import render_complexity
from agent_tools.tools.cpp_light_code_map.core import render_diagnose
from agent_tools.tools.cpp_light_code_map.core import render_includes
from agent_tools.tools.cpp_light_code_map.core import render_index
from agent_tools.tools.cpp_light_code_map.core import render_index_dir
from agent_tools.tools.cpp_light_code_map.core import render_insert_relative_to_symbol
from agent_tools.tools.cpp_light_code_map.core import render_locals
from agent_tools.tools.cpp_light_code_map.core import render_macros
from agent_tools.tools.cpp_light_code_map.core import render_map
from agent_tools.tools.cpp_light_code_map.core import render_parse_check
from agent_tools.tools.cpp_light_code_map.core import render_query
from agent_tools.tools.cpp_light_code_map.core import render_refs
from agent_tools.tools.cpp_light_code_map.core import render_rename_symbol
from agent_tools.tools.cpp_light_code_map.core import render_replace_symbol
from agent_tools.tools.cpp_light_code_map.core import render_replace_symbol_body
from agent_tools.tools.cpp_light_code_map.core import render_symbol_snapshot
from agent_tools.tools.cpp_light_code_map.core import render_symbols
from agent_tools.tools.cpp_light_code_map.core import render_unmapped

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


DEFAULT_CACHE_DIR = ".cache/cpp_light_code_map"


def cpp_light_code_map_tools() -> list[McpTool]:
    return [
        McpTool(
            name="cpp_light_map",
            title="C++ Light Map",
            description=(
                "Use instead of raw rg when C/C++ structure matters but no compile "
                "database is available. Returns a tree-sitter symbol map from one "
                "workspace-relative source file, with optional compact output."
            ),
            input_schema=_source_input_schema({"compact": _compact_property()}),
            handler=_cpp_light_map,
        ),
        McpTool(
            name="cpp_light_diagnose",
            title="C++ Light Diagnose",
            description=(
                "Use when a lightweight C/C++ map looks incomplete. Reports "
                "tree-sitter coverage and parser observations without requiring a "
                "build context."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_diagnose,
        ),
        McpTool(
            name="cpp_light_unmapped",
            title="C++ Light Unmapped",
            description=(
                "Use to debug lightweight C/C++ parser coverage instead of reading "
                "raw syntax trees. Lists top-level tree-sitter nodes not mapped as "
                "symbols."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_unmapped,
        ),
        McpTool(
            name="cpp_light_symbols",
            title="C++ Light Symbols",
            description=(
                "Use instead of grep for C/C++ declaration discovery. Lists flattened "
                "structural symbols with kind/name/line filters and compact output "
                "without a compile database."
            ),
            input_schema=_symbols_input_schema(),
            handler=_cpp_light_symbols,
        ),
        McpTool(
            name="cpp_light_symbol_get",
            title="C++ Light Symbol Get",
            description=(
                "Use before lightweight C/C++ edits instead of guessing line ranges. "
                "Returns a symbol snapshot, span, hash, and body_hash for guarded replace, "
                "insert, or rename calls."
            ),
            input_schema=_symbol_get_input_schema(),
            handler=_cpp_light_symbol_get,
        ),
        McpTool(
            name="cpp_light_includes",
            title="C++ Light Includes",
            description=(
                "Use instead of grep include patterns when include structure matters. "
                "Lists C/C++ include directives from one workspace-relative file."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_includes,
        ),
        McpTool(
            name="cpp_light_macros",
            title="C++ Light Macros",
            description=(
                "Use instead of grep macro patterns when preprocessing structure "
                "matters. Lists C/C++ macro directives from one workspace-relative "
                "file."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_macros,
        ),
        McpTool(
            name="cpp_light_calls",
            title="C++ Light Calls",
            description=(
                "Use instead of text search for C/C++ call discovery. Lists structural "
                "function calls, optionally scoped to one symbol, without requiring "
                "compile commands."
            ),
            input_schema=_calls_input_schema(),
            handler=_cpp_light_calls,
        ),
        McpTool(
            name="cpp_light_call_graph",
            title="C++ Light Call Graph",
            description=(
                "Use instead of manually correlating call sites. Returns compact "
                "structural C/C++ call graph edges for one file without compile "
                "context."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_call_graph,
        ),
        McpTool(
            name="cpp_light_refs",
            title="C++ Light Refs",
            description=(
                "Use instead of raw rg when looking for C/C++ identifier references "
                "inside parsed source. Supports optional symbol scope to reduce "
                "irrelevant textual matches."
            ),
            input_schema=_refs_input_schema(),
            handler=_cpp_light_refs,
        ),
        McpTool(
            name="cpp_light_locals",
            title="C++ Light Locals",
            description=(
                "Use instead of manually scanning a C/C++ function body. Lists "
                "parameters, locals, and labels for one parsed symbol."
            ),
            input_schema=_symbol_input_schema(),
            handler=_cpp_light_locals,
        ),
        McpTool(
            name="cpp_light_complexity",
            title="C++ Light Complexity",
            description=(
                "Use for quick C/C++ risk triage instead of ad-hoc line counting. "
                "Returns simple structural complexity metrics, optionally scoped to "
                "one symbol."
            ),
            input_schema=_calls_input_schema(),
            handler=_cpp_light_complexity,
        ),
        McpTool(
            name="cpp_light_parse_check",
            title="C++ Light Parse Check",
            description=(
                "Use after lightweight C/C++ edits instead of only checking text. "
                "Reports whether tree-sitter parsing still finds expected structural "
                "symbols."
            ),
            input_schema=_source_input_schema(),
            handler=_cpp_light_parse_check,
        ),
        McpTool(
            name="cpp_light_index",
            title="C++ Light Index",
            description=(
                "Use before repeated C/C++ structural queries across files. Writes "
                "cached lightweight symbol maps for workspace-relative source paths."
            ),
            input_schema=_index_input_schema(),
            handler=_cpp_light_index,
        ),
        McpTool(
            name="cpp_light_index_dir",
            title="C++ Light Index Dir",
            description=(
                "Use instead of find plus repeated parser calls for a source tree. "
                "Indexes C/C++ files under a workspace directory with include/exclude "
                "patterns into a cache."
            ),
            input_schema=_index_dir_input_schema(),
            handler=_cpp_light_index_dir,
        ),
        McpTool(
            name="cpp_light_query",
            title="C++ Light Query",
            description=(
                "Use instead of grepping previously indexed C/C++ files. Searches "
                "cached structural symbol maps by name and returns compact matches."
            ),
            input_schema=_query_input_schema(),
            handler=_cpp_light_query,
        ),
        McpTool(
            name="cpp_light_rename_symbol",
            title="C++ Light Rename Symbol",
            description=(
                "Use instead of global search/replace for scoped C/C++ renames. "
                "Renames structural references only when the anchor hash from cpp_light_symbol_get matches and "
                "supports check_only previews."
            ),
            input_schema=_rename_input_schema(),
            handler=_cpp_light_rename_symbol,
        ),
        McpTool(
            name="cpp_light_replace_symbol",
            title="C++ Light Replace Symbol",
            description=(
                "Use instead of line-based edits for whole C/C++ symbols. Replaces "
                "the parsed symbol span only when expect_hash still matches."
            ),
            input_schema=_replace_input_schema("replacement"),
            handler=_cpp_light_replace_symbol,
        ),
        McpTool(
            name="cpp_light_replace_symbol_body",
            title="C++ Light Replace Symbol Body",
            description=(
                "Use instead of brace-counting manual edits for a C/C++ function body. "
                "Replaces only the parsed body span and refuses stale expect_hash "
                "values."
            ),
            input_schema=_replace_input_schema("replacement"),
            handler=_cpp_light_replace_symbol_body,
        ),
        McpTool(
            name="cpp_light_insert_before_symbol",
            title="C++ Light Insert Before Symbol",
            description=(
                "Use instead of line-number insertion when adding C/C++ code before "
                "a parsed anchor symbol. The expect_hash guard prevents stale "
                "placement."
            ),
            input_schema=_replace_input_schema("snippet"),
            handler=_cpp_light_insert_before_symbol,
        ),
        McpTool(
            name="cpp_light_insert_after_symbol",
            title="C++ Light Insert After Symbol",
            description=(
                "Use instead of line-number insertion when adding C/C++ code after "
                "a parsed anchor symbol. The expect_hash guard prevents stale "
                "placement."
            ),
            input_schema=_replace_input_schema("snippet"),
            handler=_cpp_light_insert_after_symbol,
        ),
    ]


def _cpp_light_map(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_map(path, compact=bool_arg(arguments, "compact", False), json_output=json_output),
    )


def _cpp_light_diagnose(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_diagnose)


def _cpp_light_unmapped(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_unmapped)


def _cpp_light_symbols(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_symbols(
            path,
            kind=optional_string_arg(arguments, "kind"),
            name=optional_string_arg(arguments, "name"),
            contains_line=_optional_int(arguments, "contains_line"),
            compact=bool_arg(arguments, "compact", False),
            json_output=json_output,
        ),
    )


def _cpp_light_symbol_get(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_symbol_snapshot(
            path,
            string_arg(arguments, "symbol"),
            with_doc=bool_arg(arguments, "with_doc", False),
            json_output=json_output,
        ),
    )


def _cpp_light_includes(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_includes)


def _cpp_light_macros(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_macros)


def _cpp_light_calls(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_calls(path, symbol_name=optional_string_arg(arguments, "symbol"), json_output=json_output),
    )


def _cpp_light_call_graph(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_call_graph)


def _cpp_light_refs(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_refs(
            path,
            string_arg(arguments, "name"),
            scope_symbol=optional_string_arg(arguments, "scope"),
            json_output=json_output,
        ),
    )


def _cpp_light_locals(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_locals(path, string_arg(arguments, "symbol"), json_output=json_output),
    )


def _cpp_light_complexity(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_complexity(path, symbol_name=optional_string_arg(arguments, "symbol"), json_output=json_output),
    )


def _cpp_light_parse_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_parse_check)


def _cpp_light_index(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "paths"))
    if not paths:
        raise ValueError("paths must not be empty")
    return _render_result(
        context,
        arguments,
        render_index(paths, cache_dir=_cache_dir(context, arguments), json_output=_json_output(arguments)),
    )


def _cpp_light_index_dir(context: ToolContext, arguments: JsonObject) -> ToolResult:
    root = resolve_workspace_path(context.workspace, string_arg(arguments, "root"))
    return _render_result(
        context,
        arguments,
        render_index_dir(
            root,
            includes=tuple(string_list_arg(arguments, "include")),
            excludes=tuple(string_list_arg(arguments, "exclude")),
            cache_dir=_cache_dir(context, arguments),
            json_output=_json_output(arguments),
        ),
    )


def _cpp_light_query(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _render_result(
        context,
        arguments,
        render_query(
            string_arg(arguments, "name"),
            cache_dir=_cache_dir(context, arguments),
            json_output=_json_output(arguments),
        ),
    )


def _cpp_light_rename_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_rename_symbol(
            path,
            string_arg(arguments, "symbol"),
            string_arg(arguments, "expect_hash"),
            string_arg(arguments, "new_name"),
            scope_symbol=optional_string_arg(arguments, "scope"),
            check_only=bool_arg(arguments, "check_only", False),
            json_output=json_output,
        ),
    )


def _cpp_light_replace_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, render_replace_symbol, "replacement")


def _cpp_light_replace_symbol_body(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, render_replace_symbol_body, "replacement")


def _cpp_light_insert_before_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _insert_result(context, arguments, "before")


def _cpp_light_insert_after_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _insert_result(context, arguments, "after")


def _symbol_edit_result(
    context: ToolContext,
    arguments: JsonObject,
    renderer: Callable[..., str],
    text_key: str,
) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: renderer(
            path,
            string_arg(arguments, "symbol"),
            string_arg(arguments, "expect_hash"),
            string_arg(arguments, text_key),
            check_only=bool_arg(arguments, "check_only", False),
            json_output=json_output,
        ),
    )


def _insert_result(context: ToolContext, arguments: JsonObject, position: str) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, json_output: render_insert_relative_to_symbol(
            path,
            string_arg(arguments, "symbol"),
            string_arg(arguments, "expect_hash"),
            string_arg(arguments, "snippet"),
            position=position,
            check_only=bool_arg(arguments, "check_only", False),
            json_output=json_output,
        ),
    )


def _source_result(
    context: ToolContext,
    arguments: JsonObject,
    renderer: Callable[[Path, bool], str],
) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        return _render_result(context, arguments, renderer(path, json_output=_json_output(arguments)))
    except CppLightCodeMapError as error:
        return _error_result(error)


def _render_result(context: ToolContext, arguments: JsonObject, text: str) -> ToolResult:
    if _json_output(arguments):
        payload = json.loads(text)
        return ToolResult(text=text.rstrip() + "\n", structured_content=payload, is_error=_is_error_payload(payload))
    return ToolResult(text=text.rstrip() + "\n")


def _error_result(error: CppLightCodeMapError) -> ToolResult:
    payload = {"error": error.message, "details": error.details}
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _is_error_payload(payload: object) -> bool:
    return isinstance(payload, dict) and payload.get("ok") is False


def _json_output(arguments: JsonObject) -> bool:
    return string_arg(arguments, "output_format", "text") == "json"


def _cache_dir(context: ToolContext, arguments: JsonObject) -> Path:
    value = optional_string_arg(arguments, "cache_dir") or DEFAULT_CACHE_DIR
    return resolve_workspace_path(context.workspace, value)


def _optional_int(arguments: JsonObject, name: str) -> int | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _output_format_property() -> JsonObject:
    return {
        "type": "string",
        "enum": ["text", "json"],
        "description": "Use text for compact agent output or json for structured consumers.",
        "default": "text",
    }


def _compact_property() -> JsonObject:
    return {
        "type": "boolean",
        "description": "Return shorter summaries instead of full symbol detail.",
        "default": False,
    }


def _source_input_schema(extra: JsonObject | None = None) -> JsonObject:
    properties = {
        "path": {
            "type": "string",
            "description": "Workspace-relative C/C++ source file path.",
        },
        "output_format": _output_format_property(),
    }
    if extra:
        properties.update(extra)
    return {
        "type": "object",
        "properties": properties,
        "required": ["path"],
        "additionalProperties": False,
    }


def _symbols_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "kind": {
                "type": "string",
                "description": "Optional symbol kind filter such as function, class, struct, enum, or macro.",
            },
            "name": {
                "type": "string",
                "description": "Optional exact or tool-supported symbol name filter.",
            },
            "contains_line": {
                "type": "integer",
                "description": "Only return symbols whose parsed span contains this 1-based line number.",
            },
            "compact": _compact_property(),
        }
    )


def _symbol_input_schema() -> JsonObject:
    schema = _source_input_schema()
    schema["properties"]["symbol"] = {
        "type": "string",
        "description": "Qualified or visible C/C++ symbol name.",
    }
    schema["required"] = ["path", "symbol"]
    return schema


def _symbol_get_input_schema() -> JsonObject:
    schema = _symbol_input_schema()
    schema["properties"]["with_doc"] = {
        "type": "boolean",
        "description": "Include adjacent documentation/comment text in the snapshot.",
        "default": False,
    }
    return schema


def _calls_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "symbol": {
                "type": "string",
                "description": "Optional C/C++ symbol scope for calls or complexity.",
            }
        }
    )


def _refs_input_schema() -> JsonObject:
    schema = _source_input_schema(
        {
            "name": {
                "type": "string",
                "description": "Identifier name to find as structural references.",
            },
            "scope": {
                "type": "string",
                "description": "Optional symbol scope that restricts reference matches.",
            },
        }
    )
    schema["required"] = ["path", "name"]
    return schema


def _index_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Workspace-relative C/C++ source file paths to index.",
            },
            "cache_dir": {
                "type": "string",
                "description": "Workspace-relative directory where lightweight index files are written.",
                "default": DEFAULT_CACHE_DIR,
            },
            "output_format": _output_format_property(),
        },
        "required": ["paths"],
        "additionalProperties": False,
    }


def _index_dir_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "root": {
                "type": "string",
                "description": "Workspace-relative source directory to scan.",
            },
            "include": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Glob patterns to include while scanning root.",
                "default": [],
            },
            "exclude": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Glob patterns to exclude while scanning root.",
                "default": [],
            },
            "cache_dir": {
                "type": "string",
                "description": "Workspace-relative directory where lightweight index files are written.",
                "default": DEFAULT_CACHE_DIR,
            },
            "output_format": _output_format_property(),
        },
        "required": ["root"],
        "additionalProperties": False,
    }


def _query_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Symbol name to search in cached lightweight indexes.",
            },
            "cache_dir": {
                "type": "string",
                "description": "Workspace-relative directory containing lightweight index files.",
                "default": DEFAULT_CACHE_DIR,
            },
            "output_format": _output_format_property(),
        },
        "required": ["name"],
        "additionalProperties": False,
    }


def _rename_input_schema() -> JsonObject:
    schema = _replace_input_schema("new_name")
    schema["properties"]["scope"] = {
        "type": "string",
        "description": "Optional symbol scope that restricts rename targets.",
    }
    return schema


def _replace_input_schema(text_key: str) -> JsonObject:
    schema = _symbol_input_schema()
    schema["properties"]["expect_hash"] = {
        "type": "string",
        "description": "Current hash or body_hash from cpp_light_symbol_get; stale hashes block the edit.",
    }
    schema["properties"][text_key] = {
        "type": "string",
        "description": "Replacement, inserted snippet, or new symbol name depending on the operation.",
    }
    schema["properties"]["check_only"] = {
        "type": "boolean",
        "description": "Preview the edit without writing files.",
        "default": False,
    }
    schema["required"] = ["path", "symbol", "expect_hash", text_key]
    return schema
