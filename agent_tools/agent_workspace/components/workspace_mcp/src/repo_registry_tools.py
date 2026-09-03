from __future__ import annotations

from pathlib import Path

from agent_tools.tools.repo_registry import add_repository
from agent_tools.tools.repo_registry import remove_repository
from agent_tools.tools.repo_registry import repo_registry_entry_objects
from agent_tools.tools.repo_registry import render_repo_registry
from agent_tools.tools.repo_registry import validate_repo_registry

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import resolve_workspace_path, string_arg


def repo_registry_tools() -> list[McpTool]:
    return [
        McpTool(
            name="repo_registry_list",
            title="Repo Registry List",
            description=(
                "Use instead of reading repo-registry YAML by hand. Lists the "
                "repositories a task has explicitly declared for hook installation "
                "and validation."
            ),
            input_schema=_task_input_schema(),
            handler=_repo_registry_list,
        ),
        McpTool(
            name="repo_registry_validate",
            title="Repo Registry Validate",
            description=(
                "Use before relying on repo-registry entries. Validates that every "
                "recorded path is under the workspace and resolves to a git "
                "repository root."
            ),
            input_schema=_task_input_schema(),
            handler=_repo_registry_validate,
        ),
        McpTool(
            name="repo_registry_add",
            title="Repo Registry Add",
            description=(
                "Use when an agent has identified a repository root. Verifies the "
                "workspace path and git root before writing the task repo-registry "
                "slot."
            ),
            input_schema=_add_input_schema(),
            handler=_repo_registry_add,
        ),
        McpTool(
            name="repo_registry_remove",
            title="Repo Registry Remove",
            description=(
                "Use when a task no longer works with a repository. Removes the "
                "workspace-validated path from the repo-registry slot without "
                "manual YAML editing."
            ),
            input_schema=_remove_input_schema(),
            handler=_repo_registry_remove,
        ),
    ]


def _repo_registry_list(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    entries = repo_registry_entry_objects(_repo_registry_content(task_dir))
    payload = {
        "task": str(task_dir),
        "repositories": [entry.as_dict() for entry in entries],
    }
    text = render_repo_registry(entries) if entries else "repositories: []"
    return ToolResult(text=text + "\n", structured_content=payload)


def _repo_registry_validate(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    validation = validate_repo_registry(task_dir, workspace=context.workspace)
    payload = {
        "task": str(task_dir),
        "repositories": [str(path) for path in validation.repositories],
        "errors": list(validation.errors),
        "valid": not validation.errors,
    }
    return ToolResult(
        text=_validate_text(payload),
        structured_content=payload,
        is_error=bool(validation.errors),
    )


def _repo_registry_add(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    repo = _resolve_repo_path(context.workspace, string_arg(arguments, "repo"))
    role = string_arg(arguments, "role", "")
    entries = add_repository(task_dir, workspace=context.workspace, repo=repo, role=role)
    payload = {
        "task": str(task_dir),
        "repositories": [entry.as_dict() for entry in entries],
    }
    return ToolResult(
        text=render_repo_registry(entries) + "\n",
        structured_content=payload,
    )


def _repo_registry_remove(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    repo = _resolve_repo_path(context.workspace, string_arg(arguments, "repo"))
    entries = remove_repository(task_dir, workspace=context.workspace, repo=repo)
    payload = {
        "task": str(task_dir),
        "repositories": [entry.as_dict() for entry in entries],
    }
    text = render_repo_registry(entries) if entries else "repositories: []"
    return ToolResult(text=text + "\n", structured_content=payload)


def _repo_registry_content(task_dir: Path) -> str:
    from agent_tools.tools.task_context import load_slots

    slots = load_slots(task_dir, ("repo-registry",))
    return slots[0].content if slots else ""


def _validate_text(payload: JsonObject) -> str:
    lines: list[str] = []
    for path in payload["repositories"]:
        lines.append(f"PASS {path}")
    for error in payload["errors"]:
        lines.append(f"FAIL {error}")
    if not lines:
        lines.append("WARN repo-registry is empty")
    return "\n".join(lines) + "\n"


def _resolve_task_dir(workspace: Path, value: str) -> Path:
    resolved = resolve_workspace_path(workspace, value)
    try:
        resolved.relative_to((workspace / "tasks").resolve())
    except ValueError as error:
        raise ValueError(f"task must be under workspace tasks/: {value}") from error
    return resolved


def _resolve_repo_path(workspace: Path, value: str) -> Path:
    return resolve_workspace_path(workspace, value)


def _task_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _add_input_schema() -> JsonObject:
    schema = _remove_input_schema()
    schema["properties"]["role"] = {
        "type": "string",
        "default": "",
        "description": "Optional repository role, for example workspace or task-dev.",
    }
    return schema


def _remove_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "repo": {
                "type": "string",
                "description": "Workspace-relative or absolute path that must resolve inside the workspace.",
            },
        },
        "required": ["task", "repo"],
        "additionalProperties": False,
    }


def _task_property() -> JsonObject:
    return {
        "type": "string",
        "description": "Workspace-relative or absolute task directory under workspace tasks/.",
    }
