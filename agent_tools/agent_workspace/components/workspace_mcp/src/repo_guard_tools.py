from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_tools.tools.repo_guard.policy import policy_summary
from agent_tools.tools.repo_guard.runner import compact_report
from agent_tools.tools.repo_guard.runner import validate

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, optional_string_arg, resolve_workspace_path, string_arg


def repo_guard_tools() -> list[McpTool]:
    return [
        McpTool(
            name="workspace_validation_policy",
            title="Workspace Validation Policy",
            description=(
                "Use instead of opening validation YAML files by hand. Resolves "
                "workspace, repo, and task validation policy for a repository and "
                "returns check ids, cost, backend, and suggested commands."
            ),
            input_schema=_policy_schema(),
            handler=_workspace_validation_policy,
        ),
        McpTool(
            name="workspace_validation_status",
            title="Workspace Validation Status",
            description=(
                "Use to preview what repo_guard would validate without running checks "
                "or reading receipts. Returns resolved check metadata for cheap "
                "planning before workspace_validate."
            ),
            input_schema=_policy_schema(),
            handler=_workspace_validation_policy,
        ),
        McpTool(
            name="workspace_validate",
            title="Workspace Validate",
            description=(
                "Use instead of manually running policy commands. Executes resolved "
                "repo_guard checks for a workspace repository, writes receipts, and "
                "returns compact actionable failures."
            ),
            input_schema=_validate_schema(),
            handler=_workspace_validate,
        ),
    ]


def _workspace_validation_policy(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    payload = policy_summary(repo, task_dir=_task_dir(context, arguments))
    return ToolResult(
        text=_policy_text(payload),
        structured_content=payload,
    )


def _workspace_validate(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = _repo(context, arguments)
    result = validate(
        repo,
        task_dir=_task_dir(context, arguments),
        include_heavy=bool_arg(arguments, "include_heavy", False),
    )
    payload = _run_payload(result)
    return ToolResult(
        text=compact_report(result) + "\n",
        structured_content=payload,
        is_error=result.status != "pass",
    )


def _repo(context: ToolContext, arguments: JsonObject) -> Path:
    return resolve_workspace_path(context.workspace, string_arg(arguments, "repo", "."))


def _task_dir(context: ToolContext, arguments: JsonObject) -> Path | None:
    value = optional_string_arg(arguments, "task_dir")
    if value is None:
        return None
    return resolve_workspace_path(context.workspace, value)


def _policy_text(payload: JsonObject) -> str:
    lines = [
        f"repo_guard: repo_id: {payload.get('repo_id') or '<unmatched>'}",
        f"repo_guard: policy_hash: {payload.get('policy_hash')}",
    ]
    for check in payload.get("checks", []):
        lines.append(
            "{cost}\t{backend}\t{id}".format(
                cost=check.get("cost"),
                backend=check.get("backend"),
                id=check.get("id"),
            )
        )
    return "\n".join(lines) + "\n"


def _run_payload(result: Any) -> JsonObject:
    return {
        "status": result.status,
        "repo_id": result.repo_id,
        "policy_hash": result.policy_hash,
        "repo": str(result.context.repo),
        "receipt": str(result.receipt_path),
        "checks": [
            {
                "id": check.check_id,
                "status": check.status,
                "level": check.level,
                "backend": check.backend,
                "cost": check.cost,
                "required": check.required,
                "summary": check.summary,
                "receipt_path": str(check.receipt_path) if check.receipt_path else None,
                "suggested_command": list(check.suggested_command),
            }
            for check in result.checks
        ],
    }


def _policy_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "default": ".",
                "description": "Workspace-relative or absolute path inside the git repository.",
            },
            "task_dir": {
                "type": "string",
                "description": "Optional workspace-relative or absolute task directory for task-level policy.",
            },
        },
        "additionalProperties": False,
    }


def _validate_schema() -> JsonObject:
    schema = _policy_schema()
    schema["properties"]["include_heavy"] = {
        "type": "boolean",
        "default": False,
        "description": "Run heavy checks now instead of requiring existing current receipts.",
    }
    return schema
