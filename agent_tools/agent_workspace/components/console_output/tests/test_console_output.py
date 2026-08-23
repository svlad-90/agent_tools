from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_parse_console_output_preserves_color_tags() -> None:
    chunks = parse_console_output("\x1b[01;32muser\x1b[00m:\x1b[34m~/task\x1b[00m$ \r\n")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [
        ("user", ("console_bold", "console_fg_green")),
        (":", ()),
        ("~/task", ("console_fg_blue",)),
        ("$ \n", ()),
    ]


def test_parse_console_output_keeps_backspace_control() -> None:
    chunks = parse_console_output("abc\b \b")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("abc\b \b", ())]


def test_parse_console_output_keeps_carriage_return_control() -> None:
    chunks = parse_console_output("prompt old\rprompt new")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("prompt old\rprompt new", ())]


def test_parse_console_output_drops_terminal_title_sequence() -> None:
    chunks = parse_console_output("\x1b]0;user@host:~/task\x07task$ ")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("task$ ", ())]

