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
            description="Print a compact merged structure map for one YAML file.",
            input_schema=_file_input_schema(),
            handler=_yaml_map_file,
        ),
        McpTool(
            name="yaml_map_project",
            title="YAML Map Project",
            description="List YAML files under a path with compact summaries.",
            input_schema=_project_input_schema(),
            handler=_yaml_map_project,
        ),
        McpTool(
            name="yaml_map_path_get",
            title="YAML Map Path Get",
            description="Resolve one YAML path and return its hash and value.",
            input_schema=_path_get_input_schema(),
            handler=_yaml_map_path_get,
        ),
        McpTool(
            name="yaml_map_path_set",
            title="YAML Map Path Set",
            description="Replace one YAML path when the expected subtree hash still matches.",
            input_schema=_path_set_input_schema(),
            handler=_yaml_map_path_set,
        ),
        McpTool(
            name="yaml_map_item_insert",
            title="YAML Map Item Insert",
            description="Insert one YAML mapping entry or list item with hash guard.",
            input_schema=_item_insert_input_schema(),
            handler=_yaml_map_item_insert,
        ),
        McpTool(
            name="yaml_map_path_delete",
            title="YAML Map Path Delete",
            description="Delete one YAML path when the expected subtree hash still matches.",
            input_schema=_path_delete_input_schema(),
            handler=_yaml_map_path_delete,
        ),
        McpTool(
            name="yaml_map_parse_check",
            title="YAML Map Parse Check",
            description="Parse one YAML file and report validity.",
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
    return {"type": "string", "enum": ["text", "json"], "default": "text"}


def _file_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative YAML file path."},
            "output_format": _output_format_property(),
        },
        "required": ["path"],
        "additionalProperties": False,
    }


def _project_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative directory or YAML file path.", "default": "."},
            "deep": {"type": "boolean", "default": False},
            "output_format": _output_format_property(),
        },
        "additionalProperties": False,
    }


def _path_get_input_schema() -> JsonObject:
    schema = _file_input_schema()
    schema["properties"]["yaml_path"] = {"type": "string"}
    schema["required"] = ["path", "yaml_path"]
    return schema


def _guarded_edit_properties() -> JsonObject:
    return {
        "path": {"type": "string", "description": "Workspace-relative YAML file path."},
        "yaml_path": {"type": "string"},
        "expect_hash": {"type": "string"},
        "check_only": {"type": "boolean", "default": False},
        "output_format": _output_format_property(),
    }


def _path_set_input_schema() -> JsonObject:
    properties = _guarded_edit_properties()
    properties["value"] = {}
    return {
        "type": "object",
        "properties": properties,
        "required": ["path", "yaml_path", "expect_hash", "value"],
        "additionalProperties": False,
    }


def _item_insert_input_schema() -> JsonObject:
    properties = _guarded_edit_properties()
    properties["value"] = {}
    properties["key"] = {"type": "string"}
    properties["index"] = {"type": "integer"}
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
