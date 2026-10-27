from __future__ import annotations

from pathlib import Path
import os

import pytest

from agent_tools.agent_workspace.components.web_terminal.src.shell import shell_command
from agent_tools.agent_workspace.components.web_terminal.src.shell import shell_environment
from agent_tools.agent_workspace.components.web_terminal.src.shell import (
    sanitize_terminal_output,
)


@pytest.mark.skipif(os.name == "nt" or not Path("/bin/bash").exists(), reason="requires POSIX bash")
def test_shell_command_uses_clean_bash_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")

    assert shell_command() == ["/bin/bash", "--noprofile", "--norc", "-i"]


def test_shell_environment_uses_short_user_host_task_prompt() -> None:
    env = shell_environment({"USER": "workspace-user"}, "sample-task")

    assert env["PS1"].startswith("workspace-user@")
    assert env["PS1"].endswith(":sample-task$ ")
    assert "/" not in env["PS1"]


def test_shell_environment_sanitizes_untrusted_prompt_labels() -> None:
    env = shell_environment({"USER": "$(touch bad-user)"}, "$(touch bad-task)")

    assert "$(" not in env["PS1"]
    assert env["PS1"].endswith(":__touch_bad-task_$ ")


def test_sanitize_terminal_output_removes_osc_and_ansi_sequences() -> None:
    raw = (
        "\x1b]666;vte.shell.postexec=0\x1b\\"
        "\x1b[01;34mproject\x1b[00m$ echo 123\r\n"
        "\x9d0;owned\x9c\x9b31mred\x9b0m"
    )

    assert sanitize_terminal_output(raw) == "project$ echo 123\r\nred"


def test_sanitize_terminal_output_removes_all_string_controls() -> None:
    raw = (
        "before"
        "\x90dcs\x9c"
        "\x98sos\x1b\\"
        "\x9epm\x9c"
        "\x1b_apc\x1b\\"
        "after"
    )

    assert sanitize_terminal_output(raw) == "beforeafter"


def test_sanitize_terminal_output_consumes_unterminated_control_linearly() -> None:
    malformed = "\x1b]" + ("payload" * 10_000)

    assert sanitize_terminal_output(malformed) == ""
