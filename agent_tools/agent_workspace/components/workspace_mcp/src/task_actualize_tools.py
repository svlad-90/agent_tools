from __future__ import annotations

from agent_tools.tools.task_actualize import actualize_task
from agent_tools.tools.task_actualize import render_text

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import resolve_workspace_path, string_arg


def task_actualize_tools() -> list[McpTool]:
    return [
        McpTool(
            name="task_actualize",
            title="Task Actualize",
            description="Actualize an existing workspace task for current Agent Workspace tools.",
            input_schema=_actualize_input_schema(),
            handler=_task_actualize,
        ),
    ]


def _task_actualize(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _task_dir(context, string_arg(arguments, "task"))
    results = actualize_task(task_dir, workspace=context.workspace)
    payload = {
        "task": str(task_dir),
        "results": [result.as_dict() for result in results],
    }
    return ToolResult(
        text=render_text(results) + "\n",
        structured_content=payload,
        is_error=any(result.status == "FAIL" for result in results),
    )


def _task_dir(context: ToolContext, value: str):
    task_dir = resolve_workspace_path(context.workspace, value)
    try:
        task_dir.relative_to(context.workspace / "tasks")
    except ValueError as error:
        raise ValueError(f"task must be under workspace tasks/: {value}") from error
    return task_dir


def _actualize_input_schema() -> JsonObject:
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
