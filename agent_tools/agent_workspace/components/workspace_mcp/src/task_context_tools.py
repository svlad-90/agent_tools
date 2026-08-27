from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.task_context import load_slots, render_slots

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, resolve_workspace_path, string_arg, string_list_arg


def task_context_tools() -> list[McpTool]:
    return [
        McpTool(
            name="task_context_query",
            title="Task Context Query",
            description="Read TASK_CONTEXT.sqlite3 slots for a workspace task.",
            input_schema=_query_input_schema(),
            handler=_task_context_query,
        ),
    ]


def _task_context_query(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    categories = string_list_arg(arguments, "categories")
    include_legacy = bool_arg(arguments, "include_legacy", False)
    format_name = string_arg(arguments, "format", "text")

    slots = load_slots(task_dir, categories)
    if not include_legacy:
        slots = [slot for slot in slots if slot.category != "legacy"]

    if format_name == "json":
        text = json.dumps([slot.to_json() for slot in slots], ensure_ascii=False, indent=2)
        return ToolResult(text=text + "\n", structured_content={"slots": [slot.to_json() for slot in slots]})
    return ToolResult(text=render_slots(slots, format_name=format_name, task_dir=task_dir) + "\n")


def _resolve_task_dir(workspace: Path, value: str) -> Path:
    resolved = resolve_workspace_path(workspace, value)
    try:
        resolved.relative_to((workspace / "tasks").resolve())
    except ValueError as error:
        raise ValueError(f"task must be under workspace tasks/: {value}") from error
    return resolved


def _query_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Workspace-relative or absolute task directory under workspace tasks/.",
            },
            "categories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "goal",
                        "env",
                        "decisions",
                        "findings",
                        "validation",
                        "blocker-risk",
                        "operational-memory",
                        "user-preference",
                        "legacy",
                    ],
                },
                "default": [],
            },
            "format": {
                "type": "string",
                "enum": ["text", "markdown", "agent", "json"],
                "default": "text",
            },
            "include_legacy": {"type": "boolean", "default": False},
        },
        "required": ["task"],
        "additionalProperties": False,
    }
