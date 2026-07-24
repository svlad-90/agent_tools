from __future__ import annotations

from typing import Any

from .diff_parse import iter_diff_lines
from .diff_source import diff_files
from .refresh import target_with_status


def build_comments_template(diff_text: str, *, title_prefix: str = "Review") -> dict[str, Any]:
    files = diff_files(diff_text)
    added_lines: list[dict[str, Any]] = []
    for line in iter_diff_lines(diff_text):
        if line.kind != "add" or line.file_path is None or line.new_line is None:
            continue
        target = {
            "file": line.file_path,
            "line": line.new_line,
            "old_line": line.old_line,
            "new_line": line.new_line,
            "kind": line.kind,
            "content": line.content,
            "diff_line": line.raw,
            "found": True,
        }
        added_lines.append(
            {
                "file": line.file_path,
                "line": line.new_line,
                "title": f"{title_prefix}: {line.file_path}:{line.new_line}",
                "body": "",
                "target": target_with_status(target, "found"),
            }
        )

    return {
        "summary": "",
        "files": {},
        "inline": [],
        "diagrams": {},
        "logs": {},
        "story": [],
        "_template": {
            "files": files,
            "added_lines": added_lines,
        },
    }
