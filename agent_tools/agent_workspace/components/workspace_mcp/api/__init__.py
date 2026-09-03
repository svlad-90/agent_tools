"""Public API for Agent Workspace MCP server."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..src.registry import McpTool
from ..src.registry import ToolContext
from ..src.registry import ToolResult
from ..src.registry import WorkspaceMcpRegistry
from ..src.config import WORKSPACE_MCP_TOOL_GROUP_IDS
from ..src.config import WORKSPACE_MCP_TOOL_GROUPS
from ..src.config import WORKSPACE_MCP_REQUIRED_TOOL_GROUP_IDS
from ..src.config import workspace_mcp_tool_allowed
from ..src.config import workspace_mcp_tool_group_description
from ..src.config import workspace_mcp_tool_group_label
from ..src.config import workspace_mcp_stdio_config

if TYPE_CHECKING:
    from ..src.server import WorkspaceMcpServer


def build_workspace_mcp_server(
    workspace: Path,
    *,
    enabled_tool_groups: tuple[str, ...] | None = None,
) -> WorkspaceMcpServer:
    """Build the server without importing search dependencies during UI startup."""
    from ..src.server import build_workspace_mcp_server as build_server

    return build_server(workspace, enabled_tool_groups=enabled_tool_groups)


def __getattr__(name: str) -> object:
    if name == "WorkspaceMcpServer":
        from ..src.server import WorkspaceMcpServer

        return WorkspaceMcpServer
    raise AttributeError(name)

__all__ = [
    "McpTool",
    "ToolContext",
    "ToolResult",
    "WORKSPACE_MCP_TOOL_GROUP_IDS",
    "WORKSPACE_MCP_TOOL_GROUPS",
    "WORKSPACE_MCP_REQUIRED_TOOL_GROUP_IDS",
    "WorkspaceMcpRegistry",
    "WorkspaceMcpServer",
    "build_workspace_mcp_server",
    "workspace_mcp_tool_allowed",
    "workspace_mcp_tool_group_description",
    "workspace_mcp_tool_group_label",
    "workspace_mcp_stdio_config",
]
