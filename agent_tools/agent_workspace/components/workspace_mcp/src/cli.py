from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .server import build_workspace_mcp_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Agent Workspace MCP server over newline-delimited stdio JSON-RPC.")
    parser.add_argument("--workspace", default=".", help="Workspace root that MCP tools are allowed to access.")
    args = parser.parse_args(argv)
    server = build_workspace_mcp_server(Path(args.workspace))
    server.serve_stdio(sys.stdin, sys.stdout)
    return 0
