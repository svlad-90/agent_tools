from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import trim
from .models import AgentSearchError


@dataclass(frozen=True)
class FileSnippet:
    path: Path
    start: int
    end: int
    lines: tuple[tuple[int, str], ...]


def show_file_range(
    *,
    path: Path,
    line: int | None = None,
    line_range: str | None = None,
    around: int = 5,
) -> FileSnippet:
    if not path.exists():
        raise AgentSearchError(f"file does not exist: {path}")
    if not path.is_file():
        raise AgentSearchError(f"path is not a file: {path}")
    all_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if line_range:
        start, end = parse_line_range(line_range)
    elif line is not None:
        start = max(1, line - around)
        end = min(len(all_lines), line + around)
    else:
        start = 1
        end = min(len(all_lines), max(1, around * 2 + 1))
    start = max(1, min(start, len(all_lines) or 1))
    end = max(start, min(end, len(all_lines) or 1))
    selected = tuple((idx, all_lines[idx - 1]) for idx in range(start, end + 1)) if all_lines else ()
    return FileSnippet(path=path.resolve(), start=start, end=end, lines=selected)


def parse_line_range(value: str) -> tuple[int, int]:
    separators = (":", "-")
    for separator in separators:
        if separator in value:
            left, right = value.split(separator, 1)
            start = int(left)
            end = int(right)
            if start > end:
                raise AgentSearchError(f"invalid range start > end: {value}")
            return start, end
    line = int(value)
    return line, line


def render_file_snippet(snippet: FileSnippet, *, max_line_chars: int = 240) -> str:
    lines = [f"{snippet.path}:{snippet.start}:{snippet.end}"]
    for line_no, text in snippet.lines:
        lines.append(f"{line_no:5d}  {trim(text, max_line_chars)}")
    return "\n".join(lines) + "\n"
