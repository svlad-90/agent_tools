from __future__ import annotations

from collections.abc import Callable

from .diff_parse import iter_diff_lines
from .html_utils import anchor, comment_anchor, esc, format_text, line_anchor
from .models import InlineComment, ReviewComments
from .render_state import (
    active_delete_target_after_line,
    comment_row_kind,
    delete_target_classes,
    target_classes_for_line,
    target_range_for_line,
)

FileCommentAssetsRenderer = Callable[[str], str]
InlineCommentAssetsRenderer = Callable[[InlineComment], str]


def render_diff(
    diff_text: str,
    comments: ReviewComments,
    render_file_comment_assets: FileCommentAssetsRenderer | None = None,
    render_inline_comment_assets: InlineCommentAssetsRenderer | None = None,
) -> str:
    file_comment_assets = render_file_comment_assets or _empty_file_comment_assets
    inline_comment_assets = render_inline_comment_assets or _empty_inline_comment_assets
    parts: list[str] = []
    current_file: str | None = None
    table_open = False
    comment_ranges = _comment_line_ranges(comments)
    inline_comments_by_render_line = _inline_comments_by_render_line(comments)
    active_delete_target: tuple[int, int] | None = None

    def close_file() -> None:
        nonlocal table_open, current_file, active_delete_target
        if table_open:
            parts.append("      </tbody>\n    </table>\n")
            table_open = False
        if current_file is not None:
            parts.append("  </article>\n")
        active_delete_target = None

    for line in iter_diff_lines(diff_text):
        if line.kind == "file":
            close_file()
            current_file = line.file_path
            if current_file is None:
                continue
            parts.append(
                f'  <article class="file" id="{anchor(current_file)}" '
                f'data-file="{esc(current_file)}">\n'
            )
            parts.append(f'    <div class="file-header">{esc(current_file)}</div>\n')
            if current_file in comments.file_comments:
                parts.append(
                    f'    <div class="file-comment"><strong>File review note:</strong> '
                    f'{format_text(comments.file_comments[current_file])}'
                    f'{file_comment_assets(current_file)}'
                    "</div>\n"
                )
            parts.append('    <table class="diff"><tbody>\n')
            table_open = True
            parts.append(diff_row("header", "", "", line.raw))
            continue

        if current_file is None:
            continue

        if line.kind == "hunk":
            parts.append(diff_row("hunk", "...", "...", line.raw))
            continue

        if line.kind in {"metadata", "header"}:
            parts.append(diff_row("header", "", "", line.raw))
            continue

        if line.kind == "add" and line.new_line is not None:
            line_no = line.new_line
            target_range = target_range_for_line(comment_ranges, current_file, line_no)
            parts.append(
                diff_row(
                    "add",
                    "",
                    str(line_no),
                    line.raw,
                    current_file,
                    line_no,
                    target_classes_for_line(target_range, line_no),
                )
            )
            active_delete_target = active_delete_target_after_line(target_range, line_no)
            parts.append(
                _render_inline_comments(
                    inline_comments_by_render_line,
                    current_file,
                    line_no,
                    inline_comment_assets,
                    "add" if target_range is not None else "ctx",
                )
            )
        elif line.kind == "delete" and line.old_line is not None:
            parts.append(
                diff_row(
                    "del",
                    str(line.old_line),
                    "",
                    line.raw,
                    extra_classes=delete_target_classes(active_delete_target),
                )
            )
        elif line.kind == "context" and line.old_line is not None and line.new_line is not None:
            line_no = line.new_line
            target_range = target_range_for_line(comment_ranges, current_file, line_no)
            parts.append(
                diff_row(
                    "ctx",
                    str(line.old_line),
                    str(line.new_line),
                    line.raw,
                    current_file,
                    line_no,
                    target_classes_for_line(target_range, line_no),
                )
            )
            active_delete_target = active_delete_target_after_line(target_range, line_no)
            parts.append(
                _render_inline_comments(
                    inline_comments_by_render_line,
                    current_file,
                    line_no,
                    inline_comment_assets,
                    "ctx",
                )
            )

    close_file()
    return "".join(parts)


def _comment_line_ranges(comments: ReviewComments) -> dict[str, list[tuple[int, int]]]:
    ranges: dict[str, list[tuple[int, int]]] = {}
    for (file_path, line), inline_comments in comments.inline_comments.items():
        for comment in inline_comments:
            ranges.setdefault(file_path, []).append(comment.line_range or (line, line))
    return ranges


def _inline_comments_by_render_line(
    comments: ReviewComments,
) -> dict[tuple[str, int], list[InlineComment]]:
    grouped: dict[tuple[str, int], list[InlineComment]] = {}
    for (file_path, line), inline_comments in comments.inline_comments.items():
        for comment in inline_comments:
            render_line = comment.line_range[1] if comment.line_range is not None else line
            grouped.setdefault((file_path, render_line), []).append(comment)
    return grouped


def _render_inline_comments(
    grouped_comments: dict[tuple[str, int], list[InlineComment]],
    file_path: str,
    line: int,
    render_assets: InlineCommentAssetsRenderer,
    target_kind: str = "ctx",
) -> str:
    rendered: list[str] = []
    row_kind = comment_row_kind(target_kind)
    for comment in grouped_comments.get((file_path, line), ()):
        location = _comment_location(comment)
        start, end = comment.line_range or (comment.line, comment.line)
        rendered.append(
            f'      <tr class="comment-row comment-row-{row_kind}"><td colspan="3">'
            f'<div class="review-comment" id="{comment_anchor(file_path, comment.line)}"'
            f' data-comment-file="{esc(file_path)}" data-comment-range-start="{start}"'
            f' data-comment-range-end="{end}">'
            f'<div class="title">{esc(comment.title)} on {esc(location)}</div>'
            f'<div class="body">{format_text(comment.body)}'
            f'{render_assets(comment)}</div>'
            "</div></td></tr>\n"
        )
    return "".join(rendered)


def _comment_location(comment: InlineComment) -> str:
    if comment.line_range is None or comment.line_range[0] == comment.line_range[1]:
        return f"{comment.file_path}:{comment.line}"
    start, end = comment.line_range
    return f"{comment.file_path}:{start}-{end}"


def diff_row(
    kind: str,
    old_no: str,
    new_no: str,
    text: str,
    file_path: str | None = None,
    new_line: int | None = None,
    extra_classes: tuple[str, ...] = (),
) -> str:
    attrs = ""
    if file_path is not None and new_line is not None:
        attrs = (
            f' id="{line_anchor(file_path, new_line)}"'
            f' data-file="{esc(file_path)}" data-new-line="{new_line}"'
        )
    class_name = " ".join((kind, *extra_classes))
    return (
        f'      <tr class="{class_name}" data-diff-kind="{esc(kind)}"{attrs}>'
        f'<td class="num">{esc(old_no)}</td>'
        f'<td class="num">{esc(new_no)}</td><td class="code">{esc(text)}</td></tr>\n'
    )


def _empty_file_comment_assets(_file_path: str) -> str:
    return ""


def _empty_inline_comment_assets(_comment: InlineComment) -> str:
    return ""
