from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


WORKSPACE_MCP_TOOL_GROUPS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "search",
        "Search",
        "Prefer over raw rg/find when bounded, model-friendly summaries, aggregate groups, or focused ranges are needed.",
        ("agent_search_",),
    ),
    (
        "python",
        "Python",
        "Prefer over sed/grep for Python symbol maps, parse checks, and hash-guarded edits.",
        ("code_map_",),
    ),
    (
        "cpp",
        "C/C++",
        "Prefer over text search for C/C++ symbols, call graphs, references, parse checks, and guarded edits.",
        ("cpp_light_", "cpp_code_map_"),
    ),
    (
        "yaml",
        "YAML",
        "Prefer over ad-hoc scripts for YAML maps and hash-guarded nested path edits.",
        ("yaml_map_",),
    ),
    (
        "diff_reports",
        "Diff reports",
        "Prefer over manual report assembly for GitHub-style HTML diff review reports and comments JSON.",
        ("diff_report_",),
    ),
    (
        "task_context",
        "Task context",
        "Required workspace infrastructure: use instead of SQLite/YAML shell commands for task slots and repo registry.",
        ("task_context_", "repo_registry_"),
    ),
    (
        "task_actions",
        "Task actions",
        "Required workspace infrastructure: inspect and edit task GUI actions without manual TASK_ACTIONS.json surgery.",
        ("task_actions_", "task_actualize"),
    ),
    (
        "commit_messages",
        "Commit messages",
        "Required workspace infrastructure: format commit messages and trailers before running git commit.",
        ("commit_msg_",),
    ),
    (
        "validation",
        "Validation",
        "Required workspace infrastructure: run policy-aware validation and push guard receipt checks instead of manual command bundles.",
        (
            "push_guard_",
            "validate_",
            "workspace_validate",
            "workspace_validation_",
        ),
    ),
    (
        "yocto",
        "Yocto diagnostics",
        "Prefer in Yocto tasks for BitBake diagnostic commands and compact graph summaries.",
        ("yocto_diag_",),
    ),
)


WORKSPACE_MCP_TOOL_GROUP_IDS: tuple[str, ...] = tuple(
    group_id for group_id, _label, _description, _prefixes in WORKSPACE_MCP_TOOL_GROUPS
)
WORKSPACE_MCP_REQUIRED_TOOL_GROUP_IDS: tuple[str, ...] = (
    "task_context",
    "task_actions",
    "commit_messages",
    "validation",
)


def workspace_mcp_tool_group_label(group_id: str) -> str:
    for candidate, label, _description, _prefixes in WORKSPACE_MCP_TOOL_GROUPS:
        if candidate == group_id:
            return label
    return group_id


def workspace_mcp_tool_group_description(group_id: str) -> str:
    for candidate, _label, description, _prefixes in WORKSPACE_MCP_TOOL_GROUPS:
        if candidate == group_id:
            return description
    return group_id


def workspace_mcp_tool_allowed(name: str, enabled_groups: tuple[str, ...] | None) -> bool:
    if enabled_groups is None:
        return True
    enabled = set(enabled_groups) | set(WORKSPACE_MCP_REQUIRED_TOOL_GROUP_IDS)
    for group_id, _label, _description, prefixes in WORKSPACE_MCP_TOOL_GROUPS:
        if group_id not in enabled:
            continue
        if any(name == prefix or name.startswith(prefix) for prefix in prefixes):
            return True
    return False


def workspace_mcp_stdio_config(
    workspace: Path,
    *,
    python_executable: str | None = None,
    enabled_tool_groups: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    args = [
        "-m",
        "agent_tools.agent_workspace.components.workspace_mcp",
        "--workspace",
        str(workspace.resolve()),
    ]
    if enabled_tool_groups is not None:
        args.extend(["--enabled-tool-groups", ",".join(enabled_tool_groups)])
    return {
        "command": python_executable or sys.executable,
        "args": args,
        "env": {
            "PYTHONPATH": str(workspace.resolve()),
        },
    }
