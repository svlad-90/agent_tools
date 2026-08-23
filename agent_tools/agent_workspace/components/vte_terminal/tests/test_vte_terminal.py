from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_embedded_terminal_command_uses_vte_launcher(tmp_path: Path) -> None:
    command = embedded_terminal_command(
        socket_id=42,
        cwd=tmp_path,
        command=["codex", "--cd", str(tmp_path)],
        font_size=16,
        theme="dark",
    )

    assert command[1:] == [
        "-m",
        "agent_tools.agent_workspace.components.vte_terminal.api",
        "--socket-id",
        "42",
        "--cwd",
        str(tmp_path),
        "--font-size",
        "16",
        "--theme",
        "dark",
        "--",
        "codex",
        "--cd",
        str(tmp_path),
    ]

