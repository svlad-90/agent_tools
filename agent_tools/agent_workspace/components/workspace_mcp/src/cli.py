from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .server import build_workspace_mcp_server


def _enabled_tool_groups(value: str) -> tuple[str, ...]:
    groups = tuple(group.strip() for group in value.split(",") if group.strip())
    return groups


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Workspace MCP server over newline-delimited stdio JSON-RPC.")
    parser.add_argument("--workspace", default=".", help="Workspace root that MCP tools are allowed to access.")
    parser.add_argument(
        "--enabled-tool-groups",
        type=_enabled_tool_groups,
        default=None,
        help="Comma-separated MCP tool groups to expose. Defaults to all groups.",
    )
    args = parser.parse_args(argv)
    server = build_workspace_mcp_server(Path(args.workspace), enabled_tool_groups=args.enabled_tool_groups)
    server.serve_stdio(sys.stdin, sys.stdout)
    return 0
