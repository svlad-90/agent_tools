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
        old_target = item.get("target", {})
        old_content = old_target.get("content") if isinstance(old_target, dict) else None
        if target is not None:
            if isinstance(old_content, str) and old_content and target.get("content") != old_content:
                enriched_inline.append(
                    refresh_item_from_content(
                        enriched_item,
                        file_path=file_path,
                        line=line,
                        line_range=line_range,
                        old_content=old_content,
                        content_targets=content_targets,
                        line_target=target,
                    )
                )
                continue
            enriched_item["target"] = target_with_status(target, "found")
            enriched_inline.append(enriched_item)
            continue

        if isinstance(old_content, str) and old_content:
            enriched_inline.append(
                refresh_item_from_content(
                    enriched_item,
                    file_path=file_path,
                    line=line,
                    line_range=line_range,
                    old_content=old_content,
                    content_targets=content_targets,
                )
            )
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
    enriched["diagrams"] = enrich_diagram_code_links_payload(targets, content_targets, enriched)
    return enriched


def enrich_diagram_code_links_payload(
    targets: dict[tuple[str, int], dict[str, Any]],
    content_targets: dict[tuple[str, str], list[dict[str, Any]]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw_diagrams = payload.get("diagrams", {})
    if raw_diagrams in ({}, None):
        return raw_diagrams
    if not isinstance(raw_diagrams, dict):
        raise DiffReportError("comments.diagrams must be an object")

    enriched_diagrams: dict[str, Any] = {}
    for diagram_key, raw_diagram in raw_diagrams.items():
        if not isinstance(raw_diagram, dict):
            enriched_diagrams[str(diagram_key)] = raw_diagram
            continue
        enriched_diagram = dict(raw_diagram)
        raw_links = raw_diagram.get("code_links", [])
        if raw_links in ([], (), None):
            enriched_diagrams[str(diagram_key)] = enriched_diagram
            continue
        if not isinstance(raw_links, list):
            raise DiffReportError(f"diagram code_links must be a list: {diagram_key}")
        enriched_diagram["code_links"] = [
            enrich_code_link_payload(link, targets, content_targets, diagram_key=str(diagram_key))
            for link in raw_links
        ]
        enriched_diagrams[str(diagram_key)] = enriched_diagram
    return enriched_diagrams


def enrich_code_link_payload(
    raw_link: Any,
    targets: dict[tuple[str, int], dict[str, Any]],
    content_targets: dict[tuple[str, str], list[dict[str, Any]]],
    *,
    diagram_key: str,
) -> Any:
    if not isinstance(raw_link, dict):
        raise DiffReportError(f"diagram code_links entries must be objects: {diagram_key}")
    file_path = str(required(raw_link, "file"))
    line = int(required(raw_link, "line"))
    enriched_link = dict(raw_link)
    target = targets.get((file_path, line))
    old_target = raw_link.get("target_info", raw_link.get("target_meta", raw_link.get("target_status")))
    old_content = old_target.get("content") if isinstance(old_target, dict) else None
    if target is not None:
        if isinstance(old_content, str) and old_content and target.get("content") != old_content:
            return refresh_code_link_from_content(
                enriched_link,
                file_path=file_path,
                line=line,
                old_content=old_content,
                content_targets=content_targets,
                line_target=target,
            )
        enriched_link["target_info"] = target_with_status(target, "found")
        return enriched_link
    if isinstance(old_content, str) and old_content:
        return refresh_code_link_from_content(
            enriched_link,
            file_path=file_path,
            line=line,
            old_content=old_content,
            content_targets=content_targets,
        )
    enriched_link["target_info"] = {
        "file": file_path,
        "line": line,
        "found": False,
        "status": "not_found",
    }
    return enriched_link


def refresh_code_link_from_content(
    link: dict[str, Any],
    *,
    file_path: str,
    line: int,
    old_content: str,
    content_targets: dict[tuple[str, str], list[dict[str, Any]]],
    line_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched_link = dict(link)
    matches = content_targets.get((file_path, old_content), [])
    if len(matches) == 1:
        moved_target = target_with_status(matches[0], "moved", previous_line=line)
        enriched_link["line"] = moved_target["line"]
        enriched_link["target_info"] = moved_target
        return enriched_link
    if len(matches) > 1:
        enriched_link["target_info"] = {
            "file": file_path,
            "line": line,
            "found": False,
            "status": "ambiguous",
            "candidate_lines": [match["line"] for match in matches],
            "content": old_content,
        }
        return enriched_link
    target: dict[str, Any] = {
        "file": file_path,
        "line": line,
        "found": False,
        "status": "not_found",
        "content": old_content,
    }
    if line_target is not None:
        target["line_content"] = line_target.get("content")
    enriched_link["target_info"] = target
    return enriched_link


def refresh_item_from_content(
    item: dict[str, Any],
    *,
    file_path: str,
    line: int,
    line_range: tuple[int, int] | None,
    old_content: str,
    content_targets: dict[tuple[str, str], list[dict[str, Any]]],
    line_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched_item = dict(item)
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
        return enriched_item
    if len(matches) > 1:
        enriched_item["target"] = {
            "file": file_path,
            "line": line,
            "found": False,
            "status": "ambiguous",
            "candidate_lines": [match["line"] for match in matches],
            "content": old_content,
        }
        return enriched_item

    target: dict[str, Any] = {
        "file": file_path,
        "line": line,
        "found": False,
        "status": "not_found",
        "content": old_content,
    }
    if line_target is not None:
        target["line_content"] = line_target.get("content")
    enriched_item["target"] = target
    return enriched_item


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
    code_link_attention: list[tuple[str, str, dict[str, Any]]] = []
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
    code_link_moved, code_link_attention = diagram_code_link_attention(payload)
    moved += code_link_moved
    overlaps = inline_range_overlaps(raw_inline)

    if moved:
        print(f"refresh-targets: {comments_path}: moved={moved} auto-updated")
    if not attention and not overlaps:
        print(f"refresh-targets: {comments_path}: attention=0")
        return

    print(
        f"refresh-targets: {comments_path}: "
        f"attention={len(attention) + len(overlaps) + len(code_link_attention)}"
    )
    for start, end, item in attention:
        target = item.get("target", {})
        status = target.get("status") if isinstance(target, dict) else "unknown"
        location = f"{item.get('file')}:{item.get('line')}"
        title = str(item.get("title", "Review comment"))
        line_range = f"{start}-{end}" if start and end else "unknown"
        print(f"  lines {line_range}: {status} {location} {title}")
    for previous_item, previous_range, item, overlap_range in overlaps:
        file_path = str(item.get("file", ""))
        previous_title = str(previous_item.get("title", "Review comment"))
        title = str(item.get("title", "Review comment"))
        print(
            f"  overlap {file_path}:{previous_range[0]}-{previous_range[1]} "
            f"{previous_title} overlaps {overlap_range[0]}-{overlap_range[1]} {title}"
        )
    for diagram_key, status, link in code_link_attention:
        location = f"{link.get('file')}:{link.get('line')}"
        title = str(link.get("title", link.get("target", "Code link")))
        print(f"  diagram {diagram_key}: {status} {location} {title}")


def diagram_code_link_attention(
    payload: dict[str, Any],
) -> tuple[int, list[tuple[str, str, dict[str, Any]]]]:
    raw_diagrams = payload.get("diagrams", {})
    if not isinstance(raw_diagrams, dict):
        return (0, [])

    moved = 0
    attention: list[tuple[str, str, dict[str, Any]]] = []
    for diagram_key, diagram in raw_diagrams.items():
        if not isinstance(diagram, dict):
            continue
        raw_links = diagram.get("code_links", [])
        if not isinstance(raw_links, list):
            continue
        for link in raw_links:
            if not isinstance(link, dict):
                continue
            target = link.get("target_info", {})
            status = target.get("status") if isinstance(target, dict) else None
            if status == "moved":
                moved += 1
            if status in {"ambiguous", "not_found"}:
                attention.append((str(diagram_key), str(status), link))
    return (moved, attention)


def inline_range_overlaps(
    raw_inline: list[Any],
) -> list[tuple[dict[str, Any], tuple[int, int], dict[str, Any], tuple[int, int]]]:
    ranges_by_file: dict[str, list[tuple[int, int, dict[str, Any]]]] = {}
    for item in raw_inline:
        if not isinstance(item, dict):
            continue
        try:
            line = int(required(item, "line"))
        except (DiffReportError, TypeError, ValueError):
            continue
        line_range = comment_line_range(item.get("range"), line=line) or (line, line)
        ranges_by_file.setdefault(str(item.get("file", "")), []).append(
            (line_range[0], line_range[1], item)
        )

    overlaps: list[tuple[dict[str, Any], tuple[int, int], dict[str, Any], tuple[int, int]]] = []
    for ranges in ranges_by_file.values():
        previous: tuple[int, int, dict[str, Any]] | None = None
        for start, end, item in sorted(ranges, key=lambda entry: (entry[0], entry[1])):
            if previous is not None:
                previous_start, previous_end, previous_item = previous
                if start <= previous_end:
                    overlaps.append(
                        (previous_item, (previous_start, previous_end), item, (start, end))
                    )
            if previous is None or end > previous[1]:
                previous = (start, end, item)
    return overlaps


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
