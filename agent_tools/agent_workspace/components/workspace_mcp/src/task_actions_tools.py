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


def _actions_text(payload: dict[str, object]) -> str:
    lines = [f"task_actions: {payload['task']}"]
    for action in payload["actions"]:
        if isinstance(action, dict):
            lines.append(f"  {action['id']}\t{action['label']}")
    for error in payload["errors"]:
        lines.append(f"error: {error}")
    return "\n".join(lines) + "\n"


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
