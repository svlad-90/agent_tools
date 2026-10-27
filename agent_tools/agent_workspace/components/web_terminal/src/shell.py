"""Shell command and prompt policy for browser terminal sessions."""

from __future__ import annotations

from pathlib import Path
import getpass
import os
import platform
import re


_ESC = "\x1b"
_C1_CSI = "\x9b"
_C1_ST = "\x9c"
_STRING_CONTROL_BYTES = {"P", "X", "]", "^", "_"}
_C1_STRING_CONTROLS = {"\x90", "\x98", "\x9d", "\x9e", "\x9f"}


def sanitize_terminal_output(value: str) -> str:
    visible: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == _ESC:
            if index + 1 >= len(value):
                break
            introducer = value[index + 1]
            if introducer in _STRING_CONTROL_BYTES:
                index = _skip_string_control(value, index + 2, osc=introducer == "]")
                continue
            if introducer == "[":
                index = _skip_csi(value, index + 2)
                continue
            index += 2 if "@" <= introducer <= "_" else 1
            continue
        if character in _C1_STRING_CONTROLS:
            index = _skip_string_control(value, index + 1, osc=character == "\x9d")
            continue
        if character == _C1_CSI:
            index = _skip_csi(value, index + 1)
            continue
        if "\x80" <= character <= "\x9f":
            index += 1
            continue
        visible.append(character)
        index += 1
    return "".join(visible)


def _skip_string_control(value: str, index: int, *, osc: bool) -> int:
    while index < len(value):
        if osc and value[index] == "\x07":
            return index + 1
        if value[index] == _C1_ST:
            return index + 1
        if value[index] == _ESC and index + 1 < len(value) and value[index + 1] == "\\":
            return index + 2
        index += 1
    return index


def _skip_csi(value: str, index: int) -> int:
    while index < len(value):
        character = value[index]
        index += 1
        if "@" <= character <= "~":
            break
    return index


def shell_command() -> list[str]:
    if os.name == "nt":
        return [os.environ.get("COMSPEC") or "cmd.exe"]
    shell = os.environ.get("SHELL")
    if not shell:
        shell = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"
    if Path(shell).name == "bash":
        return [shell, "--noprofile", "--norc", "-i"]
    return [shell, "-i"]


def shell_environment(base_env: dict[str, str], task_name: str) -> dict[str, str]:
    env = dict(base_env)
    env.setdefault("TERM", "xterm-256color")
    user = _safe_prompt_label(_prompt_user(env))
    host = _safe_prompt_label(_prompt_host())
    task = _safe_prompt_label(task_name)
    env["PS1"] = f"{user}@{host}:{task}$ "
    env["PROMPT_COMMAND"] = ""
    return env


def _prompt_user(env: dict[str, str]) -> str:
    return env.get("USER") or getpass.getuser() or "user"


def _prompt_host() -> str:
    return platform.node().split(".", 1)[0] or "host"


def _safe_prompt_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)
