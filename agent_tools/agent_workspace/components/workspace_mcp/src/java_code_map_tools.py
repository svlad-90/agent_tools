from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from agent_tools.tools.java_code_map.core import JavaCodeMapError
from agent_tools.tools.java_code_map.core import JavaCompileContext
from agent_tools.tools.java_code_map.core import add_import_statement
from agent_tools.tools.java_code_map.core import apply_batch_edits
from agent_tools.tools.java_code_map.core import insert_after_symbol
from agent_tools.tools.java_code_map.core import insert_before_symbol
from agent_tools.tools.java_code_map.core import render_batch_edit_result
from agent_tools.tools.java_code_map.core import render_code_map
from agent_tools.tools.java_code_map.core import render_compile_doctor
from agent_tools.tools.java_code_map.core import render_edit_result
from agent_tools.tools.java_code_map.core import render_parse_check
from agent_tools.tools.java_code_map.core import render_parse_checks
from agent_tools.tools.java_code_map.core import render_symbol_index
from agent_tools.tools.java_code_map.core import render_symbol_snapshot
from agent_tools.tools.java_code_map.core import replace_symbol
from agent_tools.tools.java_code_map.core import replace_symbol_body
from agent_tools.tools.java_code_map.core import render_call_graph
from agent_tools.tools.java_code_map.core import render_calls
from agent_tools.tools.java_code_map.core import render_refs

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


DEFAULT_CACHE_DIR = ".cache/java_code_map"


def java_code_map_tools() -> list[McpTool]:
    return [
        McpTool(
            name="java_code_map_map",
            title="Java Code Map",
            description=(
                "Use instead of grep when Java structure matters and a javac context "
                "is available. Returns tree-sitter symbol maps after javac validation "
                "for one workspace-relative source file."
            ),
            input_schema=_source_input_schema(),
            handler=_java_code_map_map,
        ),
        McpTool(
            name="java_code_map_doctor",
            title="Java Code Map Doctor",
            description=(
                "Use before Java code_map failures instead of guessing classpath flags. "
                "Diagnoses source, javac availability, classpath, sourcepath, release, "
                "and parse validation for one Java file."
            ),
            input_schema=_source_input_schema(),
            handler=_java_code_map_doctor,
        ),
        McpTool(
            name="java_code_map_index",
            title="Java Code Map Index",
            description=(
                "Use before repeated Java queries across files. Validates workspace "
                "sources with javac, then writes cached structural symbol maps under "
                "cache_dir."
            ),
            input_schema=_index_input_schema(),
            handler=_java_code_map_index,
        ),
        McpTool(
            name="java_code_map_symbol_get",
            title="Java Code Map Symbol Get",
            description=(
                "Use before Java symbol edits instead of guessing line ranges. Resolves "
                "a javac-validated structural symbol snapshot with hash and body_hash."
            ),
            input_schema=_symbol_input_schema(),
            handler=_java_code_map_symbol_get,
        ),
        McpTool(
            name="java_code_map_parse_check",
            title="Java Code Map Parse Check",
            description=(
                "Use after Java edits when classpath context is available. Runs javac "
                "for one or more workspace-relative sources and returns compact diagnostics."
            ),
            input_schema=_parse_check_input_schema(),
            handler=_java_code_map_parse_check,
        ),
        McpTool(
            name="java_code_map_calls",
            title="Java Code Map Calls",
            description=(
                "Use when Java method calls matter and javac/JDT context is available. "
                "Returns binding-backed calls with tree-sitter fallback."
            ),
            input_schema=_calls_input_schema(),
            handler=_java_code_map_calls,
        ),
        McpTool(
            name="java_code_map_call_graph",
            title="Java Code Map Call Graph",
            description=(
                "Use to inspect Java call edges with javac/JDT context. Returns "
                "binding-backed call graph edges with tree-sitter fallback."
            ),
            input_schema=_source_input_schema(),
            handler=_java_code_map_call_graph,
        ),
        McpTool(
            name="java_code_map_refs",
            title="Java Code Map Refs",
            description=(
                "Use when Java references matter and javac/JDT context is available. "
                "Returns binding-backed identifier references with tree-sitter fallback."
            ),
            input_schema=_refs_input_schema(),
            handler=_java_code_map_refs,
        ),
        McpTool(
            name="java_code_map_replace_symbol",
            title="Java Code Map Replace Symbol",
            description=(
                "Use instead of line-based edits for whole Java symbols when a current "
                "hash from java_code_map_symbol_get is known. Revalidates with javac "
                "before writing."
            ),
            input_schema=_edit_input_schema("replacement"),
            handler=_java_code_map_replace_symbol,
        ),
        McpTool(
            name="java_code_map_replace_symbol_body",
            title="Java Code Map Replace Symbol Body",
            description=(
                "Use instead of brace-counting edits for Java method or constructor "
                "bodies. Replaces only the parsed body span and refuses stale hashes."
            ),
            input_schema=_edit_input_schema("replacement"),
            handler=_java_code_map_replace_symbol_body,
        ),
        McpTool(
            name="java_code_map_insert_before_symbol",
            title="Java Code Map Insert Before Symbol",
            description=(
                "Use instead of line-number insertion when adding Java code before an "
                "anchor symbol. Uses symbol hash guards and javac validation."
            ),
            input_schema=_edit_input_schema("snippet"),
            handler=_java_code_map_insert_before_symbol,
        ),
        McpTool(
            name="java_code_map_insert_after_symbol",
            title="Java Code Map Insert After Symbol",
            description=(
                "Use instead of line-number insertion when adding Java code after an "
                "anchor symbol. Uses symbol hash guards and javac validation."
            ),
            input_schema=_edit_input_schema("snippet"),
            handler=_java_code_map_insert_after_symbol,
        ),
        McpTool(
            name="java_code_map_imports_add",
            title="Java Code Map Imports Add",
            description=(
                "Use instead of manually editing Java import blocks. Inserts one import "
                "statement only when absent and supports check_only preview."
            ),
            input_schema=_import_input_schema(),
            handler=_java_code_map_imports_add,
        ),
        McpTool(
            name="java_code_map_batch",
            title="Java Code Map Batch",
            description=(
                "Use for multi-file Java guarded edit plans instead of many manual line "
                "edits. Validates workspace paths and applies one java_code_map JSON batch."
            ),
            input_schema=_batch_input_schema(),
            handler=_java_code_map_batch,
        ),
    ]


def _java_code_map_map(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_code_map)


def _java_code_map_doctor(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_compile_doctor)


def _java_code_map_index(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "paths"))
    if not paths:
        raise ValueError("paths must not be empty")
    try:
        text = render_symbol_index(
            paths,
            _java_context(context, arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            cache_dir=_cache_dir(context, arguments),
            json_output=_json_output(arguments),
        )
    except JavaCodeMapError as error:
        return _error_result(error)
    return _render_result(text, json_output=_json_output(arguments))


def _java_code_map_symbol_get(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, java_context, allow_fallback, json_output: render_symbol_snapshot(
            path,
            string_arg(arguments, "symbol"),
            java_context,
            allow_fallback=allow_fallback,
            json_output=json_output,
        ),
    )


def _java_code_map_parse_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = _parse_check_paths(context, arguments)
    try:
        if len(paths) == 1:
            text = render_parse_check(
                paths[0],
                _java_context(context, arguments),
                allow_fallback=bool_arg(arguments, "allow_fallback", False),
                json_output=_json_output(arguments),
            )
        else:
            text = render_parse_checks(
                paths,
                _java_context(context, arguments),
                allow_fallback=bool_arg(arguments, "allow_fallback", False),
                json_output=_json_output(arguments),
            )
    except JavaCodeMapError as error:
        return _error_result(error)
    return _render_result(text, json_output=_json_output(arguments))


def _java_code_map_calls(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, java_context, allow_fallback, json_output: render_calls(
            path,
            java_context,
            symbol_name=optional_string_arg(arguments, "symbol"),
            allow_fallback=allow_fallback,
            json_output=json_output,
        ),
    )


def _java_code_map_call_graph(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(context, arguments, render_call_graph)


def _java_code_map_refs(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _source_result(
        context,
        arguments,
        lambda path, java_context, allow_fallback, json_output: render_refs(
            path,
            string_arg(arguments, "name"),
            java_context,
            scope_symbol=optional_string_arg(arguments, "scope"),
            allow_fallback=allow_fallback,
            json_output=json_output,
        ),
    )


def _java_code_map_replace_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, replace_symbol, "replacement")


def _java_code_map_replace_symbol_body(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, replace_symbol_body, "replacement")


def _java_code_map_insert_before_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, insert_before_symbol, "snippet")


def _java_code_map_insert_after_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _edit_result(context, arguments, insert_after_symbol, "snippet")


def _java_code_map_imports_add(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = add_import_statement(
            path,
            string_arg(arguments, "import"),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except JavaCodeMapError as error:
        return _error_result(error)
    return _render_result(render_edit_result(result, json_output=_json_output(arguments)), json_output=_json_output(arguments))


def _java_code_map_batch(context: ToolContext, arguments: JsonObject) -> ToolResult:
    plan = _guard_batch_plan(context, arguments.get("plan"))
    try:
        result = apply_batch_edits(
            plan,
            _java_context(context, arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except JavaCodeMapError as error:
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
            _java_context(context, arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            json_output=_json_output(arguments),
        )
    except JavaCodeMapError as error:
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
            _java_context(context, arguments),
            allow_fallback=bool_arg(arguments, "allow_fallback", False),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except JavaCodeMapError as error:
        return _error_result(error)
    return _render_result(render_edit_result(result, json_output=_json_output(arguments)), json_output=_json_output(arguments))


def _render_result(text: str, *, json_output: bool) -> ToolResult:
    if not json_output:
        return ToolResult(text=text.rstrip() + "\n")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("json tool output must be an object")
    return ToolResult(text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", structured_content=payload)


def _error_result(error: JavaCodeMapError) -> ToolResult:
    payload = json.loads(error.to_json())
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _java_context(context: ToolContext, arguments: JsonObject) -> JavaCompileContext:
    return JavaCompileContext(
        classpath=tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "classpath")),
        sourcepath=tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "sourcepath")),
        release=optional_string_arg(arguments, "release"),
        javac_args=tuple(string_list_arg(arguments, "javac_args")),
        ast_backend=string_arg(arguments, "ast_backend", "auto"),
        jdt_helper=resolve_workspace_path(context.workspace, helper)
        if (helper := optional_string_arg(arguments, "jdt_helper")) is not None else None,
    )


def _cache_dir(context: ToolContext, arguments: JsonObject) -> Path:
    return resolve_workspace_path(context.workspace, string_arg(arguments, "cache_dir", DEFAULT_CACHE_DIR))


def _json_output(arguments: JsonObject) -> bool:
    return string_arg(arguments, "output_format", "text") == "json"


def _parse_check_paths(context: ToolContext, arguments: JsonObject) -> tuple[Path, ...]:
    has_path = "path" in arguments
    has_paths = "paths" in arguments
    if has_path == has_paths:
        raise ValueError("provide exactly one of path or paths")
    if has_path:
        return (resolve_workspace_path(context.workspace, string_arg(arguments, "path")),)
    paths = tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "paths"))
    if not paths:
        raise ValueError("paths must not be empty")
    return paths


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
    return {
        "type": "string",
        "enum": ["text", "json"],
        "description": "Use text for compact agent output or json for structured consumers.",
        "default": "text",
    }


def _java_context_properties() -> JsonObject:
    return {
        "classpath": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Workspace-relative jar, class directory, or dependency path entries for javac.",
            "default": [],
        },
        "sourcepath": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Workspace-relative Java source roots passed to javac -sourcepath.",
            "default": [],
        },
        "release": {
            "type": "string",
            "description": "Optional Java release version passed to javac --release.",
        },
        "javac_args": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Extra javac arguments when classpath or release are not enough.",
            "default": [],
        },
        "ast_backend": {
            "type": "string",
            "enum": ["auto", "tree-sitter", "jdt"],
            "description": "AST backend for maps: auto uses JDT helper when available, tree-sitter forces structural fallback, jdt requires helper.",
            "default": "auto",
        },
        "jdt_helper": {
            "type": "string",
            "description": "Workspace-relative JDT helper executable or jar path used when ast_backend is jdt or auto.",
        },
        "allow_fallback": {
            "type": "boolean",
            "description": "Allow structural results when javac validation fails; prefer false for reliable analysis.",
            "default": False,
        },
        "output_format": _output_format_property(),
    }


def _source_input_schema(extra: JsonObject | None = None) -> JsonObject:
    properties = {
        "path": {
            "type": "string",
            "description": "Workspace-relative Java source file path.",
        }
    }
    properties.update(_java_context_properties())
    if extra:
        properties.update(extra)
    return {
        "type": "object",
        "properties": properties,
        "required": ["path"],
        "additionalProperties": False,
    }


def _parse_check_input_schema() -> JsonObject:
    properties = {
        "path": {
            "type": "string",
            "description": "Workspace-relative Java source file path.",
        },
        "paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Workspace-relative Java source file paths.",
        },
    }
    properties.update(_java_context_properties())
    return {
        "type": "object",
        "properties": properties,
        "anyOf": [
            {"required": ["path"]},
            {"required": ["paths"]},
        ],
        "additionalProperties": False,
    }


def _symbol_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "symbol": {
                "type": "string",
                "description": "Qualified or visible Java symbol name to resolve.",
            }
        }
    ) | {"required": ["path", "symbol"]}


def _calls_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "symbol": {
                "type": "string",
                "description": "Optional qualified or visible Java symbol whose body scopes returned calls.",
            }
        }
    )


def _refs_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "name": {
                "type": "string",
                "description": "Identifier, qualified name, or binding key to match.",
            },
            "scope": {
                "type": "string",
                "description": "Optional qualified or visible Java symbol whose body scopes returned refs.",
            },
        }
    ) | {"required": ["path", "name"]}


def _edit_input_schema(text_key: str) -> JsonObject:
    return _source_input_schema(
        {
            "symbol": {
                "type": "string",
                "description": "Qualified or visible Java symbol name used as the edit anchor.",
            },
            "expect_hash": {
                "type": "string",
                "description": "Current hash or body_hash from java_code_map_symbol_get; stale hashes block the edit.",
            },
            text_key: {
                "type": "string",
                "description": "Replacement or inserted Java source text.",
            },
            "check_only": {
                "type": "boolean",
                "description": "Preview the edit without writing files.",
                "default": False,
            },
        }
    ) | {"required": ["path", "symbol", "expect_hash", text_key]}


def _import_input_schema() -> JsonObject:
    return _source_input_schema(
        {
            "import": {
                "type": "string",
                "description": "Import statement or fully qualified Java name to add.",
            },
            "check_only": {
                "type": "boolean",
                "description": "Preview the import edit without writing files.",
                "default": False,
            },
        }
    ) | {"required": ["path", "import"]}


def _index_input_schema() -> JsonObject:
    properties = {
        "paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Workspace-relative Java source file paths to index.",
        },
        "cache_dir": {
            "type": "string",
            "description": "Workspace-relative cache directory for symbol index files.",
            "default": DEFAULT_CACHE_DIR,
        },
    }
    properties.update(_java_context_properties())
    return {
        "type": "object",
        "properties": properties,
        "required": ["paths"],
        "additionalProperties": False,
    }


def _batch_input_schema() -> JsonObject:
    properties = {
        "plan": {
            "type": "object",
            "description": "JSON edit plan with operations and workspace-relative file_path values.",
        },
        "check_only": {
            "type": "boolean",
            "description": "Preview all batch edits without writing files.",
            "default": False,
        },
    }
    properties.update(_java_context_properties())
    return {
        "type": "object",
        "properties": properties,
        "required": ["plan"],
        "additionalProperties": False,
    }
