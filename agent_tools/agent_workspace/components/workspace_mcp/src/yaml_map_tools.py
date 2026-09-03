from __future__ import annotations

import json

from agent_tools.tools.yaml_map.core import YamlMapEditError
from agent_tools.tools.yaml_map.core import insert_item
from agent_tools.tools.yaml_map.core import parse_check
from agent_tools.tools.yaml_map.core import path_delete
from agent_tools.tools.yaml_map.core import path_get
from agent_tools.tools.yaml_map.core import path_set
from agent_tools.tools.yaml_map.core import project_map
from agent_tools.tools.yaml_map.core import render_edit_result
from agent_tools.tools.yaml_map.core import render_edit_result_json
from agent_tools.tools.yaml_map.core import render_error_json
from agent_tools.tools.yaml_map.core import render_parse_check
from agent_tools.tools.yaml_map.core import render_parse_check_json
from agent_tools.tools.yaml_map.core import render_path_snapshot
from agent_tools.tools.yaml_map.core import render_path_snapshot_json
from agent_tools.tools.yaml_map.core import render_project_map
from agent_tools.tools.yaml_map.core import render_project_map_json
from agent_tools.tools.yaml_map.core import render_yaml_map
from agent_tools.tools.yaml_map.core import render_yaml_map_json

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, resolve_workspace_path, string_arg


def yaml_map_tools() -> list[McpTool]:
    return [
        McpTool(
            name="yaml_map_file",
            title="YAML Map File",
            description=(
                "Use instead of cat/sed for YAML inspection when structure matters. "
                "Returns a compact workspace-relative map with paths and value_hash "
                "guards for safe follow-up reads or edits."
            ),
            input_schema=_file_input_schema(),
            handler=_yaml_map_file,
        ),
        McpTool(
            name="yaml_map_project",
            title="YAML Map Project",
            description=(
                "Use instead of find plus ad-hoc parsing when locating YAML config. "
                "Lists YAML files under a workspace path with compact summaries, "
                "optionally scanning deeper trees."
            ),
            input_schema=_project_input_schema(),
            handler=_yaml_map_project,
        ),
        McpTool(
            name="yaml_map_path_get",
            title="YAML Map Path Get",
            description=(
                "Use instead of one-off Python snippets to read a YAML subtree. "
                "Resolves one YAML path, returns the value and value_hash needed "
                "for stale-edit guarded mutations."
            ),
            input_schema=_path_get_input_schema(),
            handler=_yaml_map_path_get,
        ),
        McpTool(
            name="yaml_map_path_set",
            title="YAML Map Path Set",
            description=(
                "Use instead of manual YAML edits when replacing a nested value. "
                "Validates the workspace file, checks expect_hash, preserves YAML "
                "syntax, and supports check_only previews."
            ),
            input_schema=_path_set_input_schema(),
            handler=_yaml_map_path_set,
        ),
        McpTool(
            name="yaml_map_item_insert",
            title="YAML Map Item Insert",
            description=(
                "Use instead of indentation-sensitive manual inserts into YAML. "
                "Adds a mapping entry or list item at a YAML path with expect_hash "
                "protection and optional check_only preview."
            ),
            input_schema=_item_insert_input_schema(),
            handler=_yaml_map_item_insert,
        ),
        McpTool(
            name="yaml_map_path_delete",
            title="YAML Map Path Delete",
            description=(
                "Use instead of manually deleting YAML blocks. Removes one YAML path "
                "only when the current subtree hash matches, avoiding stale or "
                "mis-indented edits."
            ),
            input_schema=_path_delete_input_schema(),
            handler=_yaml_map_path_delete,
        ),
        McpTool(
            name="yaml_map_parse_check",
            title="YAML Map Parse Check",
            description=(
                "Use after YAML edits instead of running a custom parser command. "
                "Parses one workspace-relative YAML file and returns compact validity "
                "or diagnostic output."
            ),
            input_schema=_parse_check_input_schema(),
            handler=_yaml_map_parse_check,
        ),
    ]


def _yaml_map_file(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    if string_arg(arguments, "output_format", "text") == "json":
        text = render_yaml_map_json(path, context.workspace)
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    return ToolResult(text=render_yaml_map(path, context.workspace) + "\n")


def _yaml_map_project(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path", "."))
    report = project_map(path, context.workspace, deep=bool_arg(arguments, "deep", False))
    if string_arg(arguments, "output_format", "text") == "json":
        text = render_project_map_json(report, context.workspace)
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    return ToolResult(text=render_project_map(report, context.workspace) + "\n")


def _yaml_map_path_get(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    snapshot = path_get(path, string_arg(arguments, "yaml_path"))
    if string_arg(arguments, "output_format", "text") == "json":
        text = render_path_snapshot_json(snapshot, context.workspace)
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    return ToolResult(text=render_path_snapshot(snapshot, context.workspace) + "\n")


def _yaml_map_path_set(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = path_set(
            path,
            string_arg(arguments, "yaml_path"),
            string_arg(arguments, "expect_hash"),
            _value(arguments),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except YamlMapEditError as error:
        return _edit_error(error, context)
    return _edit_result(result, context, arguments)


def _yaml_map_item_insert(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = insert_item(
            path,
            string_arg(arguments, "yaml_path"),
            string_arg(arguments, "expect_hash"),
            _value(arguments),
            key=_optional_string(arguments, "key"),
            index=_optional_int(arguments, "index"),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except YamlMapEditError as error:
        return _edit_error(error, context)
    return _edit_result(result, context, arguments)


def _yaml_map_path_delete(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    try:
        result = path_delete(
            path,
            string_arg(arguments, "yaml_path"),
            string_arg(arguments, "expect_hash"),
            check_only=bool_arg(arguments, "check_only", False),
        )
    except YamlMapEditError as error:
        return _edit_error(error, context)
    return _edit_result(result, context, arguments)


def _yaml_map_parse_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    result = parse_check(path)
    if string_arg(arguments, "output_format", "text") == "json":
        text = render_parse_check_json(result, context.workspace)
        return ToolResult(text=text + "\n", structured_content=json.loads(text), is_error=not result.ok)
    return ToolResult(text=render_parse_check(result, context.workspace) + "\n", is_error=not result.ok)


def _value(arguments: JsonObject) -> object:
    if "value" not in arguments:
        raise ValueError("value is required")
    return arguments["value"]


def _edit_result(result: object, context: ToolContext, arguments: JsonObject) -> ToolResult:
    if string_arg(arguments, "output_format", "text") == "json":
        text = render_edit_result_json(result, context.workspace)
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    return ToolResult(text=render_edit_result(result, context.workspace) + "\n")


def _edit_error(error: YamlMapEditError, context: ToolContext) -> ToolResult:
    text = render_error_json(error, context.workspace)
    return ToolResult(text=text + "\n", structured_content=json.loads(text), is_error=True)


def _optional_string(arguments: JsonObject, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


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


def _file_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Workspace-relative YAML file path.",
            },
            "output_format": _output_format_property(),
        },
        "required": ["path"],
        "additionalProperties": False,
    }


def _project_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Workspace-relative directory or YAML file path to scan.",
                "default": ".",
            },
            "deep": {
                "type": "boolean",
                "description": "Scan recursively instead of only the immediate directory.",
                "default": False,
            },
            "output_format": _output_format_property(),
        },
        "additionalProperties": False,
    }


def _path_get_input_schema() -> JsonObject:
    schema = _file_input_schema()
    schema["properties"]["yaml_path"] = {
        "type": "string",
        "description": "Dot/bracket YAML path to read, as printed by yaml_map_file.",
    }
    schema["required"] = ["path", "yaml_path"]
    return schema


def _guarded_edit_properties() -> JsonObject:
    return {
        "path": {
            "type": "string",
            "description": "Workspace-relative YAML file path.",
        },
        "yaml_path": {
            "type": "string",
            "description": "Dot/bracket YAML path to edit, as printed by yaml_map_file or yaml_map_path_get.",
        },
        "expect_hash": {
            "type": "string",
            "description": "Current value_hash from yaml_map_file or yaml_map_path_get; stale hashes block the edit.",
        },
        "check_only": {
            "type": "boolean",
            "description": "Preview validation and resulting operation without writing the file.",
            "default": False,
        },
        "output_format": _output_format_property(),
    }


def _path_set_input_schema() -> JsonObject:
    properties = _guarded_edit_properties()
    properties["value"] = {
        "description": "JSON-compatible value to write at yaml_path.",
    }
    return {
        "type": "object",
        "properties": properties,
        "required": ["path", "yaml_path", "expect_hash", "value"],
        "additionalProperties": False,
    }


def _item_insert_input_schema() -> JsonObject:
    properties = _guarded_edit_properties()
    properties["value"] = {
        "description": "JSON-compatible mapping entry value or list item value to insert.",
    }
    properties["key"] = {
        "type": "string",
        "description": "Mapping key to insert when yaml_path points to a mapping.",
    }
    properties["index"] = {
        "type": "integer",
        "description": "List index to insert at when yaml_path points to a sequence.",
    }
    return {
        "type": "object",
        "properties": properties,
        "required": ["path", "yaml_path", "expect_hash", "value"],
        "additionalProperties": False,
    }


def _path_delete_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": _guarded_edit_properties(),
        "required": ["path", "yaml_path", "expect_hash"],
        "additionalProperties": False,
    }


def _parse_check_input_schema() -> JsonObject:
    return _file_input_schema()
