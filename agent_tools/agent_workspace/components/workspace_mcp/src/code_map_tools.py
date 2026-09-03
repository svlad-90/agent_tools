from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_tools.tools.code_map.core import CodeMapEditError
from agent_tools.tools.code_map.core import add_import_statement
from agent_tools.tools.code_map.core import apply_batch_edits
from agent_tools.tools.code_map.core import build_facade_audit
from agent_tools.tools.code_map.core import build_protocol_audit
from agent_tools.tools.code_map.core import insert_after_symbol
from agent_tools.tools.code_map.core import insert_before_symbol
from agent_tools.tools.code_map.core import parse_check
from agent_tools.tools.code_map.core import render_batch_edit_result
from agent_tools.tools.code_map.core import render_batch_edit_result_json
from agent_tools.tools.code_map.core import render_class_diagram
from agent_tools.tools.code_map.core import render_code_map
from agent_tools.tools.code_map.core import render_code_map_json
from agent_tools.tools.code_map.core import render_edit_result
from agent_tools.tools.code_map.core import render_edit_result_json
from agent_tools.tools.code_map.core import render_error_json
from agent_tools.tools.code_map.core import render_facade_audit
from agent_tools.tools.code_map.core import render_facade_audit_json
from agent_tools.tools.code_map.core import render_parse_check
from agent_tools.tools.code_map.core import render_parse_check_json
from agent_tools.tools.code_map.core import render_protocol_audit
from agent_tools.tools.code_map.core import render_protocol_audit_json
from agent_tools.tools.code_map.core import render_symbol_snapshot
from agent_tools.tools.code_map.core import render_symbol_snapshot_json
from agent_tools.tools.code_map.core import replace_symbol
from agent_tools.tools.code_map.core import replace_symbol_body

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, resolve_workspace_path, string_arg, string_list_arg


def code_map_tools() -> list[McpTool]:
    return [
        McpTool(
            name="code_map_map",
            title="Code Map",
            description=(
                "Use instead of grep/sed when inspecting Python structure. Returns "
                "compact class/function maps for workspace-relative Python files."
            ),
            input_schema=_paths_input_schema(),
            handler=_code_map_map,
        ),
        McpTool(
            name="code_map_symbol_get",
            title="Code Map Symbol Get",
            description=(
                "Use before Python symbol edits instead of guessing line ranges. "
                "Resolves exact spans plus node_hash/body_hash guards for "
                "replace/insert calls."
            ),
            input_schema=_symbol_get_input_schema(),
            handler=_code_map_symbol_get,
        ),
        McpTool(
            name="code_map_parse_check",
            title="Code Map Parse Check",
            description=(
                "Use after Python edits instead of ad-hoc compileall commands. "
                "Parses workspace-relative files and returns compact syntax status."
            ),
            input_schema=_paths_input_schema(),
            handler=_code_map_parse_check,
        ),
        McpTool(
            name="code_map_imports_add",
            title="Code Map Imports Add",
            description=(
                "Use instead of manually editing import blocks. Adds an import to "
                "workspace-relative Python files only when it is not already present."
            ),
            input_schema=_imports_add_input_schema(),
            handler=_code_map_imports_add,
        ),
        McpTool(
            name="code_map_replace_symbol",
            title="Code Map Replace Symbol",
            description=(
                "Use instead of sed/apply_patch for whole Python symbols when a "
                "current node_hash is known. Refuses stale edits via expect_hash."
            ),
            input_schema=_symbol_edit_input_schema("replacement"),
            handler=_code_map_replace_symbol,
        ),
        McpTool(
            name="code_map_replace_symbol_body",
            title="Code Map Replace Symbol Body",
            description=(
                "Use instead of manual indentation-sensitive body edits when a "
                "current body_hash is known. Replaces only the symbol body."
            ),
            input_schema=_symbol_edit_input_schema("replacement"),
            handler=_code_map_replace_symbol_body,
        ),
        McpTool(
            name="code_map_insert_before_symbol",
            title="Code Map Insert Before Symbol",
            description=(
                "Use instead of line-number insertion when adding Python code before "
                "a known anchor symbol. Uses expect_hash to avoid stale placement."
            ),
            input_schema=_symbol_edit_input_schema("snippet"),
            handler=_code_map_insert_before_symbol,
        ),
        McpTool(
            name="code_map_insert_after_symbol",
            title="Code Map Insert After Symbol",
            description=(
                "Use instead of line-number insertion when adding Python code after "
                "a known anchor symbol. Uses expect_hash to avoid stale placement."
            ),
            input_schema=_symbol_edit_input_schema("snippet"),
            handler=_code_map_insert_after_symbol,
        ),
        McpTool(
            name="code_map_batch",
            title="Code Map Batch",
            description=(
                "Use for multi-file Python edits that need path validation and "
                "optional check-only planning. Applies guarded code_map operations "
                "from one JSON plan."
            ),
            input_schema=_batch_input_schema(),
            handler=_code_map_batch,
        ),
        McpTool(
            name="code_map_class_diagram",
            title="Code Map Class Diagram",
            description=(
                "Use instead of manually sketching Python class relations. Generates "
                "PlantUML from workspace Python source structure."
            ),
            input_schema=_target_input_schema(),
            handler=_code_map_class_diagram,
        ),
        McpTool(
            name="code_map_facade_audit",
            title="Code Map Facade Audit",
            description=(
                "Use for architecture review instead of ad-hoc grep. Audits a Python "
                "facade symbol, wrappers, and caller roots with structured output."
            ),
            input_schema=_facade_audit_input_schema(),
            handler=_code_map_facade_audit,
        ),
        McpTool(
            name="code_map_protocol_audit",
            title="Code Map Protocol Audit",
            description=(
                "Use for the legacy wrong_adventure-style protocol/bridge layout "
                "instead of manual feature scans. Expects src/wrong_adventure/features "
                "under the workspace root and reports owner mixes/facade relationships."
            ),
            input_schema=_protocol_audit_input_schema(),
            handler=_code_map_protocol_audit,
        ),
    ]


def _code_map_map(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = _paths(context, arguments)
    if string_arg(arguments, "output_format", "text") == "json":
        maps = [json.loads(render_code_map_json(path, context.workspace)) for path in paths]
        payload = maps[0] if len(maps) == 1 else {"maps": maps}
        return _json_result(payload)
    return ToolResult(text="\n\n".join(render_code_map(path, context.workspace).rstrip() for path in paths) + "\n")


def _code_map_symbol_get(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = _paths(context, arguments)
    symbol = string_arg(arguments, "symbol")
    if string_arg(arguments, "output_format", "text") == "json":
        snapshots = [json.loads(render_symbol_snapshot_json(path, context.workspace, symbol)) for path in paths]
        payload = snapshots[0] if len(snapshots) == 1 else {"symbols": snapshots}
        return _json_result(payload)
    outputs = [render_symbol_snapshot(path, context.workspace, symbol).rstrip() for path in paths]
    return ToolResult(text="\n\n".join(outputs) + "\n")


def _code_map_parse_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = _paths(context, arguments)
    results = [parse_check(path) for path in paths]
    is_error = any(not result.ok for result in results)
    if string_arg(arguments, "output_format", "text") == "json":
        payloads = [json.loads(render_parse_check_json(result, context.workspace)) for result in results]
        payload = payloads[0] if len(payloads) == 1 else {"ok": not is_error, "results": payloads}
        return _json_result(payload, is_error=is_error)
    text = "\n".join(render_parse_check(result, context.workspace) for result in results) + "\n"
    return ToolResult(text=text, is_error=is_error)


def _code_map_imports_add(context: ToolContext, arguments: JsonObject) -> ToolResult:
    paths = _paths(context, arguments)
    statement = string_arg(arguments, "statement")
    check_only = bool_arg(arguments, "check_only", False)
    try:
        results = [add_import_statement(path, statement, check_only=check_only) for path in paths]
    except CodeMapEditError as error:
        return _edit_error(error, context)
    if string_arg(arguments, "output_format", "text") == "json":
        payloads = [json.loads(render_edit_result_json(result, context.workspace)) for result in results]
        payload = payloads[0] if len(payloads) == 1 else {
            "changed": any(result.changed for result in results),
            "results": payloads,
        }
        return _json_result(payload)
    text = "\n\n".join(render_edit_result(result, context.workspace) for result in results) + "\n"
    return ToolResult(text=text)


def _code_map_replace_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, replace_symbol, "replacement")


def _code_map_replace_symbol_body(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, replace_symbol_body, "replacement")


def _code_map_insert_before_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, insert_before_symbol, "snippet")


def _code_map_insert_after_symbol(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _symbol_edit_result(context, arguments, insert_after_symbol, "snippet")


def _code_map_batch(context: ToolContext, arguments: JsonObject) -> ToolResult:
    plan = arguments.get("plan")
    if plan is None:
        raise ValueError("plan is required")
    plan = _guard_batch_plan(context, plan)
    try:
        result = apply_batch_edits(plan, context.workspace, check_only=bool_arg(arguments, "check_only", False))
    except CodeMapEditError as error:
        return _edit_error(error, context)
    if string_arg(arguments, "output_format", "text") == "json":
        return _json_result(json.loads(render_batch_edit_result_json(result, context.workspace)))
    return ToolResult(text=render_batch_edit_result(result, context.workspace) + "\n")


def _code_map_class_diagram(context: ToolContext, arguments: JsonObject) -> ToolResult:
    target = resolve_workspace_path(context.workspace, string_arg(arguments, "target"))
    return ToolResult(text=render_class_diagram(target, context.workspace))


def _code_map_facade_audit(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    caller_roots = tuple(resolve_workspace_path(context.workspace, value) for value in string_list_arg(arguments, "callers"))
    report = build_facade_audit(
        path,
        string_arg(arguments, "symbol"),
        caller_roots,
        context.workspace,
        include_private=bool_arg(arguments, "include_private", False),
    )
    if string_arg(arguments, "output_format", "text") == "json":
        return _json_result(json.loads(render_facade_audit_json(report, context.workspace)))
    return ToolResult(text=render_facade_audit(report, context.workspace) + "\n")


def _code_map_protocol_audit(context: ToolContext, arguments: JsonObject) -> ToolResult:
    target = resolve_workspace_path(context.workspace, string_arg(arguments, "target"))
    expected_features = context.workspace / "src" / "wrong_adventure" / "features"
    if not expected_features.is_dir():
        return ToolResult(
            text=(
                "code_map_protocol_audit requires the legacy wrong_adventure layout: "
                f"{expected_features} is missing. Use code_map_map, "
                "code_map_facade_audit, or project-specific checks for other Python projects.\n"
            ),
            structured_content={
                "code": "unsupported-layout",
                "expected_features_dir": str(expected_features),
                "target": str(target),
            },
            is_error=True,
        )
    facade_file = _optional_workspace_path(context, arguments, "facade_file")
    report = build_protocol_audit(
        target,
        context.workspace,
        symbol=_optional_string(arguments, "symbol"),
        include_private=bool_arg(arguments, "include_private", False),
        facade_file_path=facade_file,
        facade_symbol=string_arg(arguments, "facade_symbol", "GameSession"),
    )
    if string_arg(arguments, "output_format", "text") == "json":
        return _json_result(json.loads(render_protocol_audit_json(report, context.workspace)))
    return ToolResult(text=render_protocol_audit(report, context.workspace) + "\n")


def _symbol_edit_result(context: ToolContext, arguments: JsonObject, edit_function: Any, text_key: str) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = edit_function(
            path,
            context.workspace,
            string_arg(arguments, "symbol"),
            string_arg(arguments, "expect_hash"),
            string_arg(arguments, text_key),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except CodeMapEditError as error:
        return _edit_error(error, context)
    if string_arg(arguments, "output_format", "text") == "json":
        return _json_result(json.loads(render_edit_result_json(result, context.workspace)))
    return ToolResult(text=render_edit_result(result, context.workspace) + "\n")


def _paths(context: ToolContext, arguments: JsonObject) -> list[Path]:
    values = string_list_arg(arguments, "paths")
    if not values:
        raise ValueError("paths must not be empty")
    return [resolve_workspace_path(context.workspace, value) for value in values]


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


def _optional_string(arguments: JsonObject, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _optional_workspace_path(context: ToolContext, arguments: JsonObject, name: str):
    value = _optional_string(arguments, name)
    if value is None:
        return None
    return resolve_workspace_path(context.workspace, value)


def _json_result(payload: JsonObject, *, is_error: bool = False) -> ToolResult:
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=is_error,
    )


def _edit_error(error: CodeMapEditError, context: ToolContext) -> ToolResult:
    payload = json.loads(render_error_json(error, context.workspace))
    return _json_result(payload, is_error=True)


def _output_format_property() -> JsonObject:
    return {
        "type": "string",
        "enum": ["text", "json"],
        "description": "Use text for compact model-readable output or json for structured consumers.",
        "default": "text",
    }


def _paths_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Workspace-relative Python file paths. Include the leading agent_tools/ when called through MCP.",
            },
            "output_format": _output_format_property(),
        },
        "required": ["paths"],
        "additionalProperties": False,
    }


def _symbol_get_input_schema() -> JsonObject:
    schema = _paths_input_schema()
    schema["properties"]["symbol"] = {"type": "string", "description": "Qualified or visible Python symbol name to resolve."}
    schema["required"] = ["paths", "symbol"]
    return schema


def _imports_add_input_schema() -> JsonObject:
    schema = _paths_input_schema()
    schema["properties"]["statement"] = {"type": "string", "description": "Import statement to add, for example 'from pkg import name'."}
    schema["properties"]["check_only"] = {"type": "boolean", "description": "Preview the edit without writing files.", "default": False}
    schema["required"] = ["paths", "statement"]
    return schema


def _symbol_edit_input_schema(text_key: str) -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative Python file path. Include the leading agent_tools/ when applicable."},
            "symbol": {"type": "string", "description": "Qualified or visible Python symbol name used as the edit anchor."},
            "expect_hash": {
                "type": "string",
                "description": "Current node_hash or body_hash from code_map_symbol_get; stale hashes block the edit.",
            },
            text_key: {"type": "string", "description": "Replacement or inserted Python source text."},
            "check_only": {"type": "boolean", "description": "Preview the edit without writing files.", "default": False},
            "output_format": _output_format_property(),
        },
        "required": ["path", "symbol", "expect_hash", text_key],
        "additionalProperties": False,
    }


def _batch_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "plan": {"type": "object", "description": "code_map batch edit plan with workspace-relative file_path values."},
            "check_only": {"type": "boolean", "description": "Validate the batch plan without writing files.", "default": False},
            "output_format": _output_format_property(),
        },
        "required": ["plan"],
        "additionalProperties": False,
    }


def _target_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Workspace-relative Python file or directory path."},
        },
        "required": ["target"],
        "additionalProperties": False,
    }


def _facade_audit_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative Python file containing the facade symbol."},
            "symbol": {"type": "string", "description": "Facade class/function symbol to audit."},
            "callers": {"type": "array", "items": {"type": "string"}, "description": "Workspace-relative caller root files or directories to scan."},
            "include_private": {"type": "boolean", "description": "Include private/underscore members in the audit.", "default": False},
            "output_format": _output_format_property(),
        },
        "required": ["path", "symbol", "callers"],
        "additionalProperties": False,
    }


def _protocol_audit_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Workspace-relative Python file or directory path inside a wrong_adventure-style source tree.",
            },
            "symbol": {
                "type": "string",
                "description": "Optional protocol or bridge symbol to focus on.",
            },
            "include_private": {"type": "boolean", "description": "Include private/underscore symbols in the audit.", "default": False},
            "facade_file": {"type": "string", "description": "Optional workspace-relative facade file used for relationship checks."},
            "facade_symbol": {"type": "string", "description": "Facade symbol name used when facade_file is provided.", "default": "GameSession"},
            "output_format": _output_format_property(),
        },
        "required": ["target"],
        "additionalProperties": False,
    }
