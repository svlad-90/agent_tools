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
            description="Print a structural C/C++ symbol map without a build context.",
            input_schema=_source_input_schema({"compact": {"type": "boolean", "default": False}}),
            handler=_cpp_light_map,
        ),
        McpTool(
            name="cpp_light_diagnose",
            title="C++ Light Diagnose",
            description="Diagnose tree-sitter light-map coverage for one C/C++ source file.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_diagnose,
        ),
        McpTool(
            name="cpp_light_unmapped",
            title="C++ Light Unmapped",
            description="List top-level tree-sitter nodes not mapped as symbols.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_unmapped,
        ),
        McpTool(
            name="cpp_light_symbols",
            title="C++ Light Symbols",
            description="List flattened structural C/C++ symbols with optional filters.",
            input_schema=_symbols_input_schema(),
            handler=_cpp_light_symbols,
        ),
        McpTool(
            name="cpp_light_symbol_get",
            title="C++ Light Symbol Get",
            description="Print a structural C/C++ symbol snapshot and hash.",
            input_schema=_symbol_get_input_schema(),
            handler=_cpp_light_symbol_get,
        ),
        McpTool(
            name="cpp_light_includes",
            title="C++ Light Includes",
            description="List C/C++ include directives.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_includes,
        ),
        McpTool(
            name="cpp_light_macros",
            title="C++ Light Macros",
            description="List C/C++ preprocessor macro directives.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_macros,
        ),
        McpTool(
            name="cpp_light_calls",
            title="C++ Light Calls",
            description="List structural function calls, optionally scoped to a symbol.",
            input_schema=_calls_input_schema(),
            handler=_cpp_light_calls,
        ),
        McpTool(
            name="cpp_light_call_graph",
            title="C++ Light Call Graph",
            description="List structural C/C++ call graph edges.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_call_graph,
        ),
        McpTool(
            name="cpp_light_refs",
            title="C++ Light Refs",
            description="List structural identifier references by name.",
            input_schema=_refs_input_schema(),
            handler=_cpp_light_refs,
        ),
        McpTool(
            name="cpp_light_locals",
            title="C++ Light Locals",
            description="List parameters, locals, and labels for a symbol.",
            input_schema=_symbol_input_schema(),
            handler=_cpp_light_locals,
        ),
        McpTool(
            name="cpp_light_complexity",
            title="C++ Light Complexity",
            description="Print simple structural complexity metrics.",
            input_schema=_calls_input_schema(),
            handler=_cpp_light_complexity,
        ),
        McpTool(
            name="cpp_light_parse_check",
            title="C++ Light Parse Check",
            description="Check whether structural parsing found C/C++ symbols.",
            input_schema=_source_input_schema(),
            handler=_cpp_light_parse_check,
        ),
        McpTool(
            name="cpp_light_index",
            title="C++ Light Index",
            description="Write cached structural symbol maps for C/C++ files.",
            input_schema=_index_input_schema(),
            handler=_cpp_light_index,
        ),
        McpTool(
            name="cpp_light_index_dir",
            title="C++ Light Index Dir",
            description="Index C/C++ files under a workspace directory.",
            input_schema=_index_dir_input_schema(),
            handler=_cpp_light_index_dir,
        ),
        McpTool(
            name="cpp_light_query",
            title="C++ Light Query",
            description="Search cached structural symbol maps.",
            input_schema=_query_input_schema(),
            handler=_cpp_light_query,
        ),
        McpTool(
            name="cpp_light_rename_symbol",
            title="C++ Light Rename Symbol",
            description="Rename structural identifier references inside a safe scope.",
            input_schema=_rename_input_schema(),
            handler=_cpp_light_rename_symbol,
        ),
        McpTool(
            name="cpp_light_replace_symbol",
            title="C++ Light Replace Symbol",
            description="Replace one whole C/C++ symbol by structural span.",
            input_schema=_replace_input_schema("replacement"),
            handler=_cpp_light_replace_symbol,
        ),
        McpTool(
            name="cpp_light_replace_symbol_body",
            title="C++ Light Replace Symbol Body",
            description="Replace one C/C++ function body by structural span.",
            input_schema=_replace_input_schema("replacement"),
            handler=_cpp_light_replace_symbol_body,
        ),
        McpTool(
            name="cpp_light_insert_before_symbol",
            title="C++ Light Insert Before Symbol",
            description="Insert sibling text before an anchor C/C++ symbol.",
            input_schema=_replace_input_schema("snippet"),
            handler=_cpp_light_insert_before_symbol,
        ),
        McpTool(
            name="cpp_light_insert_after_symbol",
            title="C++ Light Insert After Symbol",
            description="Insert sibling text after an anchor C/C++ symbol.",
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
    return {"type": "string", "enum": ["text", "json"], "default": "text"}


def _source_input_schema(extra: JsonObject | None = None) -> JsonObject:
    properties = {
        "path": {"type": "string", "description": "Workspace-relative C/C++ source file path."},
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
            "kind": {"type": "string"},
            "name": {"type": "string"},
            "contains_line": {"type": "integer"},
            "compact": {"type": "boolean", "default": False},
        }
    )


def _symbol_input_schema() -> JsonObject:
    schema = _source_input_schema()
    schema["properties"]["symbol"] = {"type": "string"}
    schema["required"] = ["path", "symbol"]
    return schema


def _symbol_get_input_schema() -> JsonObject:
    schema = _symbol_input_schema()
    schema["properties"]["with_doc"] = {"type": "boolean", "default": False}
    return schema


def _calls_input_schema() -> JsonObject:
    return _source_input_schema({"symbol": {"type": "string"}})


def _refs_input_schema() -> JsonObject:
    schema = _source_input_schema({"name": {"type": "string"}, "scope": {"type": "string"}})
    schema["required"] = ["path", "name"]
    return schema


def _index_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}},
            "cache_dir": {"type": "string", "default": DEFAULT_CACHE_DIR},
            "output_format": _output_format_property(),
        },
        "required": ["paths"],
        "additionalProperties": False,
    }


def _index_dir_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "root": {"type": "string", "description": "Workspace-relative source directory."},
            "include": {"type": "array", "items": {"type": "string"}, "default": []},
            "exclude": {"type": "array", "items": {"type": "string"}, "default": []},
            "cache_dir": {"type": "string", "default": DEFAULT_CACHE_DIR},
            "output_format": _output_format_property(),
        },
        "required": ["root"],
        "additionalProperties": False,
    }


def _query_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "cache_dir": {"type": "string", "default": DEFAULT_CACHE_DIR},
            "output_format": _output_format_property(),
        },
        "required": ["name"],
        "additionalProperties": False,
    }


def _rename_input_schema() -> JsonObject:
    schema = _replace_input_schema("new_name")
    schema["properties"]["scope"] = {"type": "string"}
    return schema


def _replace_input_schema(text_key: str) -> JsonObject:
    schema = _symbol_input_schema()
    schema["properties"]["expect_hash"] = {"type": "string"}
    schema["properties"][text_key] = {"type": "string"}
    schema["properties"]["check_only"] = {"type": "boolean", "default": False}
    schema["required"] = ["path", "symbol", "expect_hash", text_key]
    return schema
