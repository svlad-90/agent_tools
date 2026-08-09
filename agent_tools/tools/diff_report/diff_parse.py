from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class DiffLine:
    kind: str
    raw: str
    file_path: str | None = None
    old_line: int | None = None
    new_line: int | None = None
    content: str | None = None


def iter_diff_lines(diff_text: str) -> Iterator[DiffLine]:
    current_file: str | None = None
    old_no: int | None = None
    new_no: int | None = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            current_file = file_from_diff_header(raw_line)
            old_no = None
            new_no = None
            yield DiffLine(kind="file", raw=raw_line, file_path=current_file)
            continue

        if current_file is None:
            continue

        hunk_match = _HUNK_RE.match(raw_line)
        if hunk_match:
            old_no = int(hunk_match.group(1))
            new_no = int(hunk_match.group(3))
            yield DiffLine(
                kind="hunk",
                raw=raw_line,
                file_path=current_file,
                old_line=old_no,
                new_line=new_no,
            )
            continue

        if is_diff_metadata(raw_line):
            yield DiffLine(kind="metadata", raw=raw_line, file_path=current_file)
            continue

        if old_no is None or new_no is None:
            yield DiffLine(kind="header", raw=raw_line, file_path=current_file)
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            yield DiffLine(
                kind="add",
                raw=raw_line,
                file_path=current_file,
                old_line=None,
                new_line=new_no,
                content=raw_line[1:],
            )
            new_no += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            yield DiffLine(
                kind="delete",
                raw=raw_line,
                file_path=current_file,
                old_line=old_no,
                new_line=None,
                content=raw_line[1:],
            )
            old_no += 1
        else:
            yield DiffLine(
                kind="context",
                raw=raw_line,
                file_path=current_file,
                old_line=old_no,
                new_line=new_no,
                content=raw_line[1:] if raw_line.startswith(" ") else raw_line,
            )
            old_no += 1
            new_no += 1


def file_from_diff_header(line: str) -> str:
    match = re.match(r"diff --git a/(.*?) b/(.*)", line)
    if not match:
        return line
    return match.group(2)


def is_diff_metadata(line: str) -> bool:
    prefixes = (
        "--- ",
        "+++ ",
        "index ",
        "new file",
        "deleted file",
        "similarity ",
        "rename ",
        "old mode",
        "new mode",
    )
    return line.startswith(prefixes)
