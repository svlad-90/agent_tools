from __future__ import annotations

from dataclasses import dataclass
import re


ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
ANSI_OSC_RE = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")


@dataclass(frozen=True)
class ConsoleChunk:
    text: str
    tags: tuple[str, ...]


def parse_console_output(text: str) -> list[ConsoleChunk]:
    text = ANSI_OSC_RE.sub("", text)
    text = text.replace("\r\n", "\n")
    chunks: list[ConsoleChunk] = []
    tags: tuple[str, ...] = ()
    offset = 0
    for match in ANSI_ESCAPE_RE.finditer(text):
        _append_console_chunk(chunks, text[offset : match.start()], tags)
        tags = _update_console_tags(match.group(0), tags)
        offset = match.end()
    _append_console_chunk(chunks, text[offset:], tags)
    return chunks


def _append_console_chunk(
    chunks: list[ConsoleChunk],
    text: str,
    tags: tuple[str, ...],
) -> None:
    cleaned = "".join(
        char
        for char in text
        if char in ("\b", "\n", "\r", "\t") or ord(char) >= 32
    )
    if cleaned:
        chunks.append(ConsoleChunk(cleaned, tags))


def _update_console_tags(sequence: str, current: tuple[str, ...]) -> tuple[str, ...]:
    if not sequence.startswith("\x1b[") or not sequence.endswith("m"):
        return current
    codes = [int(part) if part else 0 for part in sequence[2:-1].split(";")]
    tags = set(current)
    for code in codes:
        if code == 0:
            tags.clear()
        elif code == 1:
            tags.add("console_bold")
        elif code == 22:
            tags.discard("console_bold")
        elif code == 39:
            tags = {tag for tag in tags if not tag.startswith("console_fg_")}
        elif code in CONSOLE_FG_TAGS:
            tags = {tag for tag in tags if not tag.startswith("console_fg_")}
            tags.add(CONSOLE_FG_TAGS[code])
    return tuple(sorted(tags))


CONSOLE_FG_TAGS = {
    30: "console_fg_black",
    31: "console_fg_red",
    32: "console_fg_green",
    33: "console_fg_yellow",
    34: "console_fg_blue",
    35: "console_fg_magenta",
    36: "console_fg_cyan",
    37: "console_fg_white",
    90: "console_fg_bright_black",
    91: "console_fg_bright_red",
    92: "console_fg_bright_green",
    93: "console_fg_bright_yellow",
    94: "console_fg_bright_blue",
    95: "console_fg_bright_magenta",
    96: "console_fg_bright_cyan",
    97: "console_fg_bright_white",
}
