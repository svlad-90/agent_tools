from __future__ import annotations

from typing import TypeAlias

TargetRange: TypeAlias = tuple[int, int]
TargetRangesByFile: TypeAlias = dict[str, list[TargetRange]]


def target_range_for_line(
    ranges: TargetRangesByFile,
    file_path: str,
    line: int,
) -> TargetRange | None:
    for start, end in ranges.get(file_path, ()):
        if start <= line <= end:
            return start, end
    return None


def target_classes_for_line(target_range: TargetRange | None, line: int) -> tuple[str, ...]:
    if target_range is None:
        return ()
    start, end = target_range
    classes = ["comment-target"]
    if line == start:
        classes.append("comment-target-start")
    if line == end:
        classes.append("comment-target-end")
    if start == end:
        classes.append("comment-target-single")
    return tuple(classes)


def target_classes(
    ranges: TargetRangesByFile,
    file_path: str,
    line: int,
) -> tuple[str, ...]:
    return target_classes_for_line(target_range_for_line(ranges, file_path, line), line)


def delete_target_classes(active_target: TargetRange | None) -> tuple[str, ...]:
    return ("comment-target",) if active_target is not None else ()


def active_delete_target_after_line(
    target_range: TargetRange | None,
    line: int,
) -> TargetRange | None:
    if target_range is not None and line < target_range[1]:
        return target_range
    return None


def comment_row_kind(last_target_diff_kind: str) -> str:
    if last_target_diff_kind in {"add", "del", "ctx"}:
        return last_target_diff_kind
    if last_target_diff_kind == "delete":
        return "del"
    if last_target_diff_kind == "context":
        return "ctx"
    return "ctx"
