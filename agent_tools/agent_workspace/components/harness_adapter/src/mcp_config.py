from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...workspace_mcp.api import workspace_mcp_stdio_config


CODEX_WORKSPACE_MCP_SERVER_ID = "agent_tools_workspace"
CLAUDE_WORKSPACE_MCP_SERVER_ID = "agent-tools"


def codex_workspace_mcp_config_options(
    workspace: Path,
    *,
    python_executable: str | None = None,
) -> list[str]:
    config = workspace_mcp_stdio_config(workspace, python_executable=python_executable)
    prefix = f"mcp_servers.{CODEX_WORKSPACE_MCP_SERVER_ID}"
    options = [
        f"{prefix}.command={_toml_literal(config['command'])}",
        f"{prefix}.args={_toml_literal(config['args'])}",
        f"{prefix}.enabled=true",
        f"{prefix}.require_approval=\"never\"",
        f"{prefix}.startup_timeout_sec=10",
        f"{prefix}.tool_timeout_sec=60",
    ]
    env = config.get("env", {})
    if isinstance(env, dict):
        for key, value in sorted(env.items()):
            options.append(f"{prefix}.env.{key}={_toml_literal(str(value))}")
    return options


def claude_workspace_mcp_settings(
    workspace: Path,
    *,
    python_executable: str | None = None,
) -> dict[str, Any]:
    config = workspace_mcp_stdio_config(workspace, python_executable=python_executable)
    return {
        "mcpServers": {
            CLAUDE_WORKSPACE_MCP_SERVER_ID: {
                "type": "stdio",
                "command": config["command"],
                "args": config["args"],
                "env": config["env"],
            }
        }
    }


def merge_claude_workspace_mcp_settings(
    settings: dict[str, Any],
    workspace: Path,
    *,
    python_executable: str | None = None,
) -> dict[str, Any]:
    merged = dict(settings)
    existing_servers = merged.get("mcpServers", {})
    servers = dict(existing_servers) if isinstance(existing_servers, dict) else {}
    servers.update(
        claude_workspace_mcp_settings(
            workspace,
            python_executable=python_executable,
        )["mcpServers"]
    )
    merged["mcpServers"] = servers
    return merged


def _toml_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
