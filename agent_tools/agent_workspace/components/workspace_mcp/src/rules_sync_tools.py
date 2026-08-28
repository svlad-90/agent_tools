from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.rules_sync.core import RulesSyncError
from agent_tools.tools.rules_sync.core import apply_plan
from agent_tools.tools.rules_sync.core import plan_all

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import optional_string_arg, resolve_workspace_path


def rules_sync_tools() -> list[McpTool]:
    return [
        McpTool(
            name="rules_sync_check",
            title="Rules Sync Check",
            description="Check whether mirrored agent rule files are up to date without writing.",
            input_schema=_rules_sync_input_schema(),
            handler=_rules_sync_check,
        ),
        McpTool(
            name="rules_sync_apply",
            title="Rules Sync Apply",
            description="Regenerate mirrored agent rule files such as Claude skills and CLAUDE.md blocks.",
            input_schema=_rules_sync_input_schema(),
            handler=_rules_sync_apply,
        ),
    ]


def _rules_sync_check(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _run_rules_sync(context, arguments, check_only=True)


def _rules_sync_apply(context: ToolContext, arguments: JsonObject) -> ToolResult:
    return _run_rules_sync(context, arguments, check_only=False)


def _run_rules_sync(context: ToolContext, arguments: JsonObject, *, check_only: bool) -> ToolResult:
    root = _root(context, arguments)
    try:
        result = apply_plan(plan_all(root), check_only=check_only)
    except (RulesSyncError, OSError, ValueError) as error:
        return _error_result(error)
    payload: JsonObject = {
        "root": str(root),
        "check_only": check_only,
        "clean": result.is_clean,
        "changed": [str(path.relative_to(root)) for path in result.changed],
        "unchanged": [str(path.relative_to(root)) for path in result.unchanged],
    }
    return ToolResult(
        text=_render_result_text(payload),
        structured_content=payload,
        is_error=check_only and not result.is_clean,
    )


def _root(context: ToolContext, arguments: JsonObject) -> Path:
    value = optional_string_arg(arguments, "root")
    if value is None:
        return context.workspace
    return resolve_workspace_path(context.workspace, value)


def _render_result_text(payload: JsonObject) -> str:
    verb = "would change" if payload["check_only"] else "wrote"
    lines = []
    for path in payload["changed"]:
        lines.append(f"{verb}: {path}")
    for path in payload["unchanged"]:
        lines.append(f"unchanged: {path}")
    if payload["check_only"] and not payload["clean"]:
        lines.append(f"rules_sync: {len(payload['changed'])} file(s) out of date")
    return "\n".join(lines) + "\n"


def _error_result(error: Exception) -> ToolResult:
    payload = {"error": str(error)}
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _rules_sync_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "root": {
                "type": "string",
                "description": "Workspace-relative root containing AGENTS.md and agent_tools/.",
            },
        },
        "additionalProperties": False,
    }
