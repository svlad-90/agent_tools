from __future__ import annotations

from pathlib import Path
from typing import Any

from .comments import comment_line_range, required
from .diff_parse import iter_diff_lines
from .models import DiffReportError


_TARGET_STATUS_ORDER = {
    "found": 0,
    "moved": 1,
    "ambiguous": 2,
    "not_found": 3,
}


def enrich_comments_payload(diff_text: str, payload: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(payload)
    raw_inline = enriched.get("inline", [])
    if not isinstance(raw_inline, list):
        raise DiffReportError("comments.inline must be a list")

    targets = diff_line_targets(diff_text)
    content_targets = diff_content_targets(targets)
    enriched_inline: list[Any] = []
    for item in raw_inline:
        if not isinstance(item, dict):
            raise DiffReportError("comments.inline entries must be objects")
        file_path = str(required(item, "file"))
        line = int(required(item, "line"))
        enriched_item = dict(item)
        line_range = comment_line_range(enriched_item.get("range"), line=line)
        if line_range is not None:
            enriched_item["range"] = {"start": line_range[0], "end": line_range[1]}
        target = targets.get((file_path, line))
        if target is not None:
            enriched_item["target"] = target_with_status(target, "found")
            enriched_inline.append(enriched_item)
            continue

        old_target = item.get("target", {})
        old_content = old_target.get("content") if isinstance(old_target, dict) else None
        if isinstance(old_content, str) and old_content:
            matches = content_targets.get((file_path, old_content), [])
            if len(matches) == 1:
                moved_target = target_with_status(
                    matches[0],
                    "moved",
                    previous_line=line,
                )
                enriched_item["line"] = moved_target["line"]
                if line_range is not None:
                    line_delta = int(moved_target["line"]) - line
                    enriched_item["range"] = {
                        "start": line_range[0] + line_delta,
                        "end": line_range[1] + line_delta,
                    }
                enriched_item["target"] = moved_target
                enriched_inline.append(enriched_item)
                continue
            if len(matches) > 1:
                enriched_item["target"] = {
                    "file": file_path,
                    "line": line,
                    "found": False,
                    "status": "ambiguous",
                    "candidate_lines": [match["line"] for match in matches],
                    "content": old_content,
                }
                enriched_inline.append(enriched_item)
                continue

        enriched_item["target"] = {
            "file": file_path,
            "line": line,
            "found": False,
            "status": "not_found",
            "content": old_content,
        }
        enriched_inline.append(enriched_item)
    enriched["inline"] = sorted(enriched_inline, key=inline_sort_key)
    return enriched


def diff_content_targets(
    targets: dict[tuple[str, int], dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    content_targets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for target in targets.values():
        content = target.get("content")
        file_path = target.get("file")
        if isinstance(file_path, str) and isinstance(content, str) and content:
            content_targets.setdefault((file_path, content), []).append(target)
    return content_targets


def target_with_status(
    target: dict[str, Any],
    status: str,
    *,
    previous_line: int | None = None,
) -> dict[str, Any]:
    updated = dict(target)
    updated["found"] = True
    updated["status"] = status
    if previous_line is not None and previous_line != updated.get("line"):
        updated["previous_line"] = previous_line
    return updated


def inline_sort_key(item: Any) -> tuple[int, str, int, str]:
    if not isinstance(item, dict):
        return (99, "", 0, "")
    target = item.get("target", {})
    status = target.get("status") if isinstance(target, dict) else None
    return (
        _TARGET_STATUS_ORDER.get(str(status), 99),
        str(item.get("file", "")),
        int(item.get("line", 0)),
        str(item.get("title", "")),
    )


def print_refresh_attention(
    comments_path: Path,
    payload: dict[str, Any],
    comments_json: str,
) -> None:
    raw_inline = payload.get("inline", [])
    if not isinstance(raw_inline, list):
        return

    ranges = inline_item_line_ranges(comments_json)
    attention: list[tuple[int, int, dict[str, Any]]] = []
    moved = 0
    for index, item in enumerate(raw_inline):
        if not isinstance(item, dict):
            continue
        target = item.get("target", {})
        status = target.get("status") if isinstance(target, dict) else None
        if status == "moved":
            moved += 1
        if status in {"ambiguous", "not_found"}:
            start, end = ranges[index] if index < len(ranges) else (0, 0)
            attention.append((start, end, item))

    if moved:
        print(f"refresh-targets: {comments_path}: moved={moved} auto-updated")
    if not attention:
        print(f"refresh-targets: {comments_path}: attention=0")
        return

    print(f"refresh-targets: {comments_path}: attention={len(attention)}")
    for start, end, item in attention:
        target = item.get("target", {})
        status = target.get("status") if isinstance(target, dict) else "unknown"
        location = f"{item.get('file')}:{item.get('line')}"
        title = str(item.get("title", "Review comment"))
        line_range = f"{start}-{end}" if start and end else "unknown"
        print(f"  lines {line_range}: {status} {location} {title}")


def inline_item_line_ranges(comments_json: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    in_inline = False
    object_start: int | None = None
    object_depth = 0

    for line_no, line in enumerate(comments_json.splitlines(), start=1):
        stripped = line.strip()
        if not in_inline:
            if stripped == '"inline": [':
                in_inline = True
            continue
        if object_start is None and (stripped == "]" or stripped == "],"):
            break
        if object_start is None and stripped.startswith("{"):
            object_start = line_no
            object_depth = 0
        if object_start is not None:
            object_depth += line.count("{")
            object_depth -= line.count("}")
            if object_depth == 0:
                ranges.append((object_start, line_no))
                object_start = None

    return ranges


def diff_line_targets(diff_text: str) -> dict[tuple[str, int], dict[str, Any]]:
    targets: dict[tuple[str, int], dict[str, Any]] = {}
    for line in iter_diff_lines(diff_text):
        if line.file_path is None or line.new_line is None:
            continue
        if line.kind not in {"add", "context"}:
            continue
        targets[(line.file_path, line.new_line)] = {
            "file": line.file_path,
            "line": line.new_line,
            "old_line": line.old_line,
            "new_line": line.new_line,
            "kind": line.kind,
            "content": line.content,
            "diff_line": line.raw,
            "found": True,
        }

    return targets
