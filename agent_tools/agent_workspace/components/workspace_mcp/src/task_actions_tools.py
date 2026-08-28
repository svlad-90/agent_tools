from __future__ import annotations

import json

from agent_tools.tools import task_actions

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import resolve_workspace_path, string_arg


def task_actions_tools() -> list[McpTool]:
    return [
        McpTool(
            name="task_actions_list",
            title="Task Actions List",
            description="List actions declared by a workspace task.",
            input_schema=_list_input_schema(),
            handler=_task_actions_list,
        ),
        McpTool(
            name="task_actions_add",
            title="Task Actions Add",
            description="Add one GUI action to a workspace task TASK_ACTIONS.json file.",
            input_schema=_add_input_schema(),
            handler=_task_actions_add,
        ),
        McpTool(
            name="task_actions_delete",
            title="Task Actions Delete",
            description="Delete one GUI action from a workspace task TASK_ACTIONS.json file.",
            input_schema=_delete_input_schema(),
            handler=_task_actions_delete,
        ),
        McpTool(
            name="task_actions_update",
            title="Task Actions Update",
            description="Update one GUI action in a workspace task TASK_ACTIONS.json file.",
            input_schema=_update_input_schema(),
            handler=_task_actions_update,
        ),
        McpTool(
            name="task_actions_show",
            title="Task Actions Show",
            description="Show one task-declared action with command, cwd, env, and parameters.",
            input_schema=_show_input_schema(),
            handler=_task_actions_show,
        ),
        McpTool(
            name="task_actions_run",
            title="Task Actions Run",
            description="Run one task-declared action with optional parameter bindings.",
            input_schema=_run_input_schema(),
            handler=_task_actions_run,
        ),
    ]


def _task_actions_add(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    payload = task_actions.add_action(
        task_dir,
        string_arg(arguments, "action"),
        string_arg(arguments, "label"),
        _command(arguments, required=True),
        cwd=string_arg(arguments, "cwd", "."),
        env=_string_map(arguments, "env"),
        parameters=_object_list(arguments, "parameters"),
    )
    return ToolResult(
        text=json.dumps(payload["action"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=bool(payload["errors"]),
    )


def _task_actions_delete(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    payload = task_actions.delete_action(task_dir, string_arg(arguments, "action"))
    return ToolResult(
        text=_delete_text(payload),
        structured_content=payload,
        is_error=bool(payload["errors"]),
    )


def _task_actions_update(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    payload = task_actions.update_action(
        task_dir,
        string_arg(arguments, "action"),
        label=_optional_string(arguments, "label"),
        command=_command(arguments, required=False),
        cwd=_optional_string(arguments, "cwd"),
        env=_string_map(arguments, "env") if "env" in arguments else None,
        parameters=_object_list(arguments, "parameters") if "parameters" in arguments else None,
    )
    return ToolResult(
        text=json.dumps(payload["action"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=bool(payload["errors"]),
    )


def _task_actions_list(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    payload = task_actions.list_actions(task_dir)
    return ToolResult(
        text=_actions_text(payload),
        structured_content=payload,
        is_error=bool(payload["errors"]),
    )


def _task_actions_show(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    payload = task_actions.show_action(task_dir, string_arg(arguments, "action"))
    action = payload["action"]
    return ToolResult(
        text=json.dumps(action, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=bool(payload["errors"]),
    )


def _task_actions_run(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    bindings = _bindings(arguments)
    payload = task_actions.run_action(task_dir, string_arg(arguments, "action"), bindings)
    return ToolResult(
        text=_run_text(payload),
        structured_content=payload,
        is_error=bool(payload["errors"]) or payload["returncode"] != 0,
    )


def _task_dir(context: ToolContext, value: str):
    task_dir = resolve_workspace_path(context.workspace, value)
    try:
        task_dir.relative_to(context.workspace / "tasks")
    except ValueError as error:
        raise ValueError(f"task must be under workspace tasks/: {value}") from error
    return task_dir


def _bindings(arguments: JsonObject) -> dict[str, str]:
    value = arguments.get("bindings", {})
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise ValueError("bindings must be a string map")
    return dict(value)


def _optional_string(arguments: JsonObject, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def _command(arguments: JsonObject, *, required: bool) -> str | list[str] | None:
    value = arguments.get("command")
    if value is None and not required:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise ValueError("command must be a string or list of strings")


def _string_map(arguments: JsonObject, name: str) -> dict[str, str] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise ValueError(f"{name} must be a string map")
    return dict(value)


def _object_list(arguments: JsonObject, name: str) -> list[dict[str, object]] | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{name} must be a list of objects")
    return [dict(item) for item in value]


def _actions_text(payload: dict[str, object]) -> str:
    lines = [f"task_actions: {payload['task']}"]
    for action in payload["actions"]:
        if isinstance(action, dict):
            lines.append(f"  {action['id']}\t{action['label']}")
    for error in payload["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines) + "\n"


def _delete_text(payload: dict[str, object]) -> str:
    deleted = payload["deleted"]
    if not isinstance(deleted, dict):
        return "task_actions: delete complete\n"
    return (
        f"task_actions: deleted {deleted['id']} "
        f"(actions={deleted['actions']}, shortcuts={deleted['shortcuts']})\n"
    )


def _run_text(payload: dict[str, object]) -> str:
    lines = [
        f"task_actions: run {payload['action']['id']}",
        f"cwd: {payload['cwd']}",
        f"exit code: {payload['returncode']}",
    ]
    if payload["stdout"]:
        lines.extend(["stdout:", str(payload["stdout"]).rstrip()])
    if payload["stderr"]:
        lines.extend(["stderr:", str(payload["stderr"]).rstrip()])
    for error in payload["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines) + "\n"


def _list_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Workspace-relative or absolute task directory under tasks/.",
            },
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _add_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Workspace-relative or absolute task directory under tasks/.",
            },
            "action": {"type": "string"},
            "label": {"type": "string"},
            "command": {
                "description": "Shell command string or argv string list.",
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ],
            },
            "cwd": {"type": "string", "default": "."},
            "env": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "default": {},
            },
            "parameters": {
                "type": "array",
                "items": {"type": "object"},
                "default": [],
            },
        },
        "required": ["task", "action", "label", "command"],
        "additionalProperties": False,
    }


def _delete_input_schema() -> JsonObject:
    schema = _show_input_schema()
    schema["description"] = "Delete the base action with this id, or a matching shortcut."
    return schema


def _update_input_schema() -> JsonObject:
    schema = _add_input_schema()
    schema["required"] = ["task", "action"]
    return schema


def _show_input_schema() -> JsonObject:
    schema = _list_input_schema()
    schema["properties"]["action"] = {"type": "string"}
    schema["required"] = ["task", "action"]
    return schema


def _run_input_schema() -> JsonObject:
    schema = _show_input_schema()
    schema["properties"]["bindings"] = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "default": {},
    }
    return schema
