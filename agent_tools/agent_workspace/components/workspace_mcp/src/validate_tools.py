from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from agent_tools.tools import push_guard
from agent_tools.tools import validate as validate_tool

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, optional_string_arg, resolve_workspace_path, string_arg


def validate_tools() -> list[McpTool]:
    return [
        McpTool(
            name="validate_changed",
            title="Validate Changed",
            description="Validate changed files in a workspace git repository.",
            input_schema=_changed_input_schema(),
            handler=_validate_changed,
        ),
        McpTool(
            name="validate_task",
            title="Validate Task",
            description="Validate changed files and one workspace task directory.",
            input_schema=_task_input_schema(),
            handler=_validate_task,
        ),
    ]


def _validate_changed(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    changed = validate_tool._changed_files(repo)
    receipt = _receipt_path(
        context,
        repo,
        optional_string_arg(arguments, "receipt"),
        repo / "report" / "validation" / "latest.json",
    )
    return _run_validation_for_mcp(
        repo,
        changed,
        None,
        receipt,
        mark_push_guard=bool_arg(arguments, "mark_push_guard", False),
    )


def _validate_task(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    task_dir = _task_dir(context, repo, string_arg(arguments, "task_dir"))
    changed = validate_tool._changed_files(repo)
    receipt = _receipt_path(
        context,
        repo,
        optional_string_arg(arguments, "receipt"),
        task_dir / "report" / "validation" / "latest.json",
    )
    return _run_validation_for_mcp(
        repo,
        changed,
        task_dir,
        receipt,
        mark_push_guard=bool_arg(arguments, "mark_push_guard", False),
    )


def _run_validation_for_mcp(
    repo: Path,
    changed: list[Path],
    task_dir: Path | None,
    receipt: Path,
    *,
    mark_push_guard: bool,
) -> ToolResult:
    commands = validate_tool._validation_commands(repo, changed, task_dir)
    results = [
        validate_tool._guard_changed_files(repo, changed),
        *[validate_tool._run_command(command) for command in commands],
    ]
    status = "pass" if all(result.status == "pass" for result in results) else "fail"
    commit = validate_tool._git(["rev-parse", "HEAD"], cwd=repo)
    payload = {
        "repo": str(repo),
        "commit": commit,
        "status": status,
        "task_dir": str(task_dir) if task_dir is not None else None,
        "changed_files": [str(path) for path in changed],
        "commands": [asdict(result) for result in results],
        "receipt": str(receipt),
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "push_guard_marked": False,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if status == "pass" and mark_push_guard:
        source = push_guard._validated_receipt_source(repo, commit, receipt)
        push_guard._record_success(repo, commit, source)
        payload["push_guard_marked"] = True
        payload["push_guard_source"] = source
    return ToolResult(
        text=_validation_text(payload),
        structured_content=payload,
        is_error=status != "pass",
    )


def _repo(context: ToolContext, arguments: JsonObject) -> Path:
    repo = resolve_workspace_path(context.workspace, string_arg(arguments, "repo", "."))
    return validate_tool._repo_root(repo)


def _task_dir(context: ToolContext, repo: Path, value: str) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (repo / path).resolve()
    try:
        resolved.relative_to(context.workspace)
    except ValueError as error:
        raise ValueError(f"task_dir is outside workspace: {value}") from error
    return resolved


def _receipt_path(
    context: ToolContext,
    repo: Path,
    value: str | None,
    default: Path,
) -> Path:
    if value is None:
        return default.resolve()
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (repo / path).resolve()
    try:
        resolved.relative_to(context.workspace)
    except ValueError as error:
        raise ValueError(f"receipt is outside workspace: {value}") from error
    return resolved


def _validation_text(payload: JsonObject) -> str:
    lines = [f"validate: {payload['status']}: {payload['receipt']}"]
    for command in payload["commands"]:
        lines.append(f"  {command['status']}\t{command['name']}\t{command['duration_sec']:.2f}s")
        if command["status"] == "fail":
            if command.get("stdout_tail"):
                lines.append(str(command["stdout_tail"]).rstrip())
            if command.get("stderr_tail"):
                lines.append(str(command["stderr_tail"]).rstrip())
    if payload.get("push_guard_marked"):
        lines.append(f"push_guard: source: {payload.get('push_guard_source', '')}")
    return "\n".join(lines) + "\n"


def _changed_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "default": ".",
                "description": "Workspace-relative or absolute git repository path.",
            },
            "receipt": {
                "type": "string",
                "description": "Workspace-local receipt output path.",
            },
            "mark_push_guard": {
                "type": "boolean",
                "default": False,
                "description": "Record push_guard success when validation passes.",
            },
        },
        "additionalProperties": False,
    }


def _task_input_schema() -> JsonObject:
    schema = _changed_input_schema()
    schema["properties"]["task_dir"] = {
        "type": "string",
        "description": "Workspace-relative, repo-relative, or absolute task directory.",
    }
    schema["required"] = ["task_dir"]
    return schema
