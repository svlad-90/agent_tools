from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


def workspace_mcp_stdio_config(workspace: Path, *, python_executable: str | None = None) -> dict[str, Any]:
    return {
        "command": python_executable or sys.executable,
        "args": [
            "-m",
            "agent_tools.agent_workspace.components.workspace_mcp",
            "--workspace",
            str(workspace.resolve()),
        ],
        "env": {
            "PYTHONPATH": str(workspace.resolve()),
        },
    }
