from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from agent_tools.tools.cpp_code_map.core import CppCodeMapError
from agent_tools.tools.cpp_code_map.core import add_include_statement
from agent_tools.tools.cpp_code_map.core import apply_batch_edits
from agent_tools.tools.cpp_code_map.core import insert_after_symbol
from agent_tools.tools.cpp_code_map.core import insert_before_symbol
from agent_tools.tools.cpp_code_map.core import render_batch_edit_result
from agent_tools.tools.cpp_code_map.core import render_code_map
from agent_tools.tools.cpp_code_map.core import render_compile_doctor
from agent_tools.tools.cpp_code_map.core import render_edit_result
from agent_tools.tools.cpp_code_map.core import render_parse_check
from agent_tools.tools.cpp_code_map.core import render_puml_audit
from agent_tools.tools.cpp_code_map.core import render_symbol_index
from agent_tools.tools.cpp_code_map.core import render_symbol_snapshot
from agent_tools.tools.cpp_code_map.core import replace_symbol
from agent_tools.tools.cpp_code_map.core import replace_symbol_body

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


DEFAULT_CACHE_DIR = ".cache/cpp_code_map"


def cpp_code_map_tools() -> list[McpTool]:
    return [
        McpTool(
            name="cpp_code_map_map",
            title="C++ Code Map",
            description="Print libclang-backed C/C++ class/function maps.",
            input_schema=_source_input_schema(),
            handler=_cpp_code_map_map,
        ),
        McpTool(
            name="cpp_code_map_doctor",
            title="C++ Code Map Doctor",
            description="Diagnose libclang compile database, compiler, and parse setup for one C/C++ source file.",
            input_schema=_source_input_schema(),
            handler=_cpp_code_map_doctor,
        ),
        McpTool(
            name="cpp_code_map_index",
            title="C++ Code Map Index",
            description="Write cached libclang-backed C/C++ symbol maps.",
            input_schema=_index_input_schema(),
            handler=_cpp_code_map_index,
        ),
        McpTool(
            name="cpp_code_map_symbol_get",
            title="C++ Code Map Symbol Get",
            description="Print a libclang-backed C/C++ symbol snapshot and hash.",
            input_schema=_symbol_input_schema(),
            handler=_cpp_code_map_symbol_get,
        ),
        McpTool(
            name="cpp_code_map_parse_check",
            title="C++ Code Map Parse Check",
            description="Parse one C/C++ source file through libclang and report diagnostics.",
            input_schema=_source_input_schema(),
            handler=_cpp_code_map_parse_check,
        ),
        McpTool(
            name="cpp_code_map_puml_audit",
            title="C++ Code Map PUML Audit",
            description="Audit checked PlantUML class relations against libclang AST relations.",
            input_schema=_source_input_schema(),
            handler=_cpp_code_map_puml_audit,
        ),
        McpTool(
            name="cpp_code_map_replace_symbol",
            title="C++ Code Map Replace Symbol",
            description="Replace one C/C++ symbol through a libclang span and expected-hash guard.",
            input_schema=_edit_input_schema("replacement"),
            handler=_cpp_code_map_replace_symbol,
        ),
        McpTool(
            name="cpp_code_map_replace_symbol_body",
            title="C++ Code Map Replace Symbol Body",
            description="Replace one C/C++ function body through a libclang span and expected-hash guard.",
            input_schema=_edit_input_schema("replacement"),
            handler=_cpp_code_map_replace_symbol_body,
        ),
        McpTool(
            name="cpp_code_map_insert_before_symbol",
            title="C++ Code Map Insert Before Symbol",
            description="Insert C/C++ text before an anchor symbol through a libclang span guard.",
            input_schema=_edit_input_schema("snippet"),
            handler=_cpp_code_map_insert_before_symbol,
        ),
        McpTool(
            name="cpp_code_map_insert_after_symbol",
            title="C++ Code Map Insert After Symbol",
            description="Insert C/C++ text after an anchor symbol through a libclang span guard.",
            input_schema=_edit_input_schema("snippet"),
            handler=_cpp_code_map_insert_after_symbol,
        ),
        McpTool(
            name="cpp_code_map_includes_add",
            title="C++ Code Map Includes Add",
            description="Insert one C/C++ include statement unless it already exists.",
            input_schema=_include_input_schema(),
            handler=_cpp_code_map_includes_add,
        ),
        McpTool(
            name="cpp_code_map_batch",
            title="C++ Code Map Batch",
            description="Apply a cpp_code_map JSON batch edit plan with optional check-only mode.",
            input_schema=_batch_input_schema(),
            handler=_cpp_code_map_batch,
        ),
    ]


def _cpp_code_map_map(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_code_map)


def _cpp_code_map_doctor(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_compile_doctor)


def _cpp_code_map_index(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "paths"))
    if not paths:
        raise ValueError("paths must not be empty")
    try:
        text = render_symbol_index(
            paths,
            _compile_db(context, arguments),
            clang_args=_clang_args(arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            cache_dir=_cache_dir(context, arguments),
            json_output=_json_output(arguments),
        )
    except CppCodeMapError as error:
        return _error_result(error)
    return _render_result(text, json_output=_json_output(arguments))


def _cpp_code_map_symbol_get(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, compile_db, clang_args, allow_fallback, json_output: render_symbol_snapshot(
            path,
            string_arg(arguments, "symbol"),
            compile_db,
            clang_args=clang_args,
            allow_fallback=allow_fallback,
            json_output=json_output,
        ),
    )


def _cpp_code_map_parse_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_parse_check)


def _cpp_code_map_puml_audit(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_puml_audit)


def _cpp_code_map_replace_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, replace_symbol, "replacement")


def _cpp_code_map_replace_symbol_body(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, replace_symbol_body, "replacement")


def _cpp_code_map_insert_before_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, insert_before_symbol, "snippet")


def _cpp_code_map_insert_after_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, insert_after_symbol, "snippet")


def _cpp_code_map_includes_add(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = add_include_statement(
            path,
            string_arg(arguments, "include"),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except CppCodeMapError as error:
        return _error_result(error)
    return _render_result(render_edit_result(result, json_output=_json_output(arguments)), json_output=_json_output(arguments))


def _cpp_code_map_batch(context: ToolContext, arguments: JsonObject) -> ToolResult:
    plan = _guard_batch_plan(context, arguments.get("plan"))
    try:
        result = apply_batch_edits(
            plan,
            _compile_db(context, arguments),
            clang_args=_clang_args(arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except CppCodeMapError as error:
        return _error_result(error)
    return _render_result(
        render_batch_edit_result(result, json_output=_json_output(arguments)),
        json_output=_json_output(arguments),
    )


def _source_result(
    context: ToolContext,
    arguments: JsonObject,
    renderer: Callable[..., str],
) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        text = renderer(
            path,
            _compile_db(context, arguments),
            clang_args=_clang_args(arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            json_output=_json_output(arguments),
        )
    except CppCodeMapError as error:
        return _error_result(error)
    return _render_result(text, json_output=_json_output(arguments))


def _edit_result(
    context: ToolContext,
    arguments: JsonObject,
    editor: Callable[..., Any],
    text_key: str,
) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = editor(
            path,
            string_arg(arguments, "symbol"),
            string_arg(arguments, "expect_hash"),
            string_arg(arguments, text_key),
            _compile_db(context, arguments),
            clang_args=_clang_args(arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except CppCodeMapError as error:
        return _error_result(error)
    return _render_result(render_edit_result(result, json_output=_json_output(arguments)), json_output=_json_output(arguments))


def _render_result(text: str, *, json_output: bool) -> ToolResult:
    if not json_output:
        return ToolResult(text=text.rstrip() + "\n")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("json tool output must be an object")
    return ToolResult(text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", structured_content=payload)


def _error_result(error: CppCodeMapError) -> ToolResult:
    payload = json.loads(error.to_json())
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _compile_db(context: ToolContext, arguments: JsonObject) -> Path | None:
    value = optional_string_arg(arguments, "compile_db")
    if value is None:
        return None
    return resolve_workspace_path(context.workspace, value)


def _cache_dir(context: ToolContext, arguments: JsonObject) -> Path:
    return resolve_workspace_path(context.workspace, string_arg(arguments, "cache_dir", DEFAULT_CACHE_DIR))


def _clang_args(arguments: JsonObject) -> tuple[str, ...]:
    return tuple(string_list_arg(arguments, "clang_args"))


def _json_output(arguments: JsonObject) -> bool:
    return string_arg(arguments, "output_format", "text") == "json"


def _guard_batch_plan(context: ToolContext, plan: object) -> object:
    if isinstance(plan, list):
        return [_guard_batch_operation(context, operation) for operation in plan]
    if isinstance(plan, dict):
        guarded = dict(plan)
        operations = guarded.get("operations", [])
        if not isinstance(operations, list):
            raise ValueError("batch plan must include an 'operations' list")
        guarded["operations"] = [_guard_batch_operation(context, operation) for operation in operations]
        return guarded
    raise ValueError("batch plan must be a JSON object or array")


def _guard_batch_operation(context: ToolContext, operation: object) -> dict[str, object]:
    if not isinstance(operation, dict):
        raise ValueError("batch operation must be an object")
    guarded = dict(operation)
    file_path = guarded.get("file_path")
    if not isinstance(file_path, str):
        raise ValueError("batch operation requires string file_path")
    guarded["file_path"] = str(resolve_workspace_path(context.workspace, file_path))
    return guarded


def _output_format_property() -> JsonObject:
    return {"type": "string", "enum": ["text", "json"], "default": "text"}


def _cpp_context_properties() -> JsonObject:
    return {
        "compile_db": {
            "type": "string",
            "description": "Workspace-relative compile_commands.json file or build directory.",
        },
        "clang_args": {"type": "array", "items": {"type": "string"}, "default": []},
        "allow_fallback": {"type": "boolean", "default": False},
        "output_format": _output_format_property(),
    }


def _source_input_schema(extra: JsonObject | None = None) -> JsonObject:
    properties = {"path": {"type": "string", "description": "Workspace-relative C/C++ source file path."}}
    properties.update(_cpp_context_properties())
    if extra:
        properties.update(extra)
    return {
        "type": "object",
        "properties": properties,
        "required": ["path"],
        "additionalProperties": False,
    }


def _symbol_input_schema() -> JsonObject:
    return _source_input_schema({"symbol": {"type": "string"}}) | {"required": ["path", "symbol"]}


def _edit_input_schema(text_key: str) -> JsonObject:
    return _source_input_schema(
        {
            "symbol": {"type": "string"},
            "expect_hash": {"type": "string"},
            text_key: {"type": "string"},
            "check_only": {"type": "boolean", "default": False},
        }
    ) | {"required": ["path", "symbol", "expect_hash", text_key]}


def _include_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "include": {"type": "string"},
            "check_only": {"type": "boolean", "default": False},
        }
    ) | {"required": ["path", "include"]}


def _index_input_schema() -> JsonObject:
    properties = {
        "paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Workspace-relative C/C++ source file paths.",
        },
        "cache_dir": {"type": "string", "default": DEFAULT_CACHE_DIR},
    }
    properties.update(_cpp_context_properties())
    return {
        "type": "object",
        "properties": properties,
        "required": ["paths"],
        "additionalProperties": False,
    }


def _batch_input_schema() -> JsonObject:
    properties = {
        "plan": {"type": ["object", "array"]},
        "check_only": {"type": "boolean", "default": False},
    }
    properties.update(_cpp_context_properties())
    return {
        "type": "object",
        "properties": properties,
        "required": ["plan"],
        "additionalProperties": False,
    }
