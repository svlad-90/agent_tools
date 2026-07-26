from __future__ import annotations

import base64
import json
import re
from typing import Any

from .assets import copy_selection_script, diagram_script, html_header, story_script, theme_script
from .diff_source import diff_files, diff_stats
from .html_utils import anchor as _anchor
from .html_utils import comment_anchor as _comment_anchor
from .html_utils import esc as _esc
from .html_utils import format_text as _format_text
from .html_utils import line_anchor as _line_anchor
from .models import (
    Diagram,
    DiffSource,
    DiffStats,
    LogAttachment,
    ReviewComments,
    StoryStep,
)
from .render_diff import render_diff


def render_html_report(
    title: str,
    source: DiffSource,
    comments: ReviewComments,
) -> str:
    comment_count = _comment_count(comments)
    commit_id = comments.commit_id or source.commit
    commit_message = comments.commit_message or source.message
    commit_subject = next((line for line in (commit_message or "").splitlines() if line.strip()), None)
    subject = source.subject or commit_subject
    stats = diff_stats(source.diff_text)
    parts: list[str] = []
    parts.append(html_header(title))
    parts.append(
        f"""
<main>
  <header>
    <h1>{_esc(title)}</h1>
  </header>
"""
    )
    if commit_id:
        parts.append(_render_note_section("Commit ID", commit_id))
    if subject:
        parts.append(_render_note_section("Subject", subject))
    if commit_message:
        parts.append(_render_note_section("Commit Message", _commit_body_without_subject(commit_message)))
    parts.append(_render_diff_stats_section(stats))
    if comments.summary or comments.summary_blocks:
        parts.append(_render_summary_section(comments))
    if comments.diagrams:
        parts.append(_render_diagrams_section(comments))
    if comments.logs:
        parts.append(_render_logs_section(comments))
    if comments.story:
        parts.append(_render_story_section(comments))
    if comment_count:
        parts.append(_render_comments_index(comments, diff_files(source.diff_text)))
    parts.append(
        render_diff(
            source.diff_text,
            comments,
            render_file_comment_assets=lambda file_path: _render_comment_assets(
                comments,
                comments.file_diagrams.get(file_path),
                comments.file_logs.get(file_path),
                comments.file_diagram_focus.get(file_path, ()),
                comments.file_log_focus.get(file_path, ()),
                comments.file_diagram_notes.get(file_path, ()),
            ),
            render_inline_comment_assets=lambda comment: _render_comment_assets(
                comments,
                comment.diagram,
                comment.log,
                comment.diagram_focus,
                comment.log_focus,
                comment.diagram_notes,
            ),
        )
    )
    parts.append(_render_settings_launcher(" report-settings-launcher"))
    parts.append(_render_to_top_button())
    if comments.diagrams or comments.logs:
        parts.append(_render_diagram_modal(comments))
    parts.append(copy_selection_script())
    parts.append(story_script())
    parts.append(theme_script())
    parts.append("</main>\n</body>\n</html>\n")
    return "".join(parts)


def _render_note_section(title: str, text: str) -> str:
    return f'  <section class="note-section"><h2>{_esc(title)}</h2><pre class="report-note">{_esc(text)}</pre></section>\n'


def _commit_body_without_subject(message: str) -> str:
    lines = message.splitlines()
    if not lines:
        return message
    body_lines = lines[1:]
    while body_lines and body_lines[0] == "":
        body_lines.pop(0)
    return "\n".join(body_lines)


def _render_diff_stats_section(stats: DiffStats) -> str:
    return (
        '  <section><h2>Diff Stats</h2><div class="diff-stats">'
        '<div class="diff-stats-row diff-stats-lines">'
        f'<div><span class="label">Added lines</span><strong class="diff-stat-add">+{stats.lines_added}</strong></div>'
        f'<div><span class="label">Deleted lines</span><strong class="diff-stat-del">-{stats.lines_deleted}</strong></div>'
        '</div>'
        '<div class="diff-stats-row diff-stats-files">'
        f'<div><span class="label">Files changed</span><strong>{stats.files_changed}</strong></div>'
        f'<div><span class="label">Added files</span><strong class="diff-stat-add">{stats.files_added}</strong></div>'
        f'<div><span class="label">Deleted files</span><strong class="diff-stat-del">{stats.files_deleted}</strong></div>'
        f'<div><span class="label">Renamed files</span><strong>{stats.files_renamed}</strong></div>'
        '</div>'
        "</div></section>\n"
    )


def _comment_count(comments: ReviewComments) -> int:
    return len(comments.file_comments) + sum(len(items) for items in comments.inline_comments.values())


def _render_summary_section(comments: ReviewComments) -> str:
    parts = ['  <section class="summary-section"><h2>Reviewer Summary</h2><div class="review-summary-blocks">\n']
    if comments.summary_blocks:
        for block in comments.summary_blocks:
            if block.kind == "text":
                parts.append(
                    f'    <p class="review-summary">{_format_text(block.text or "", comments.vocabulary)}</p>\n'
                )
            elif block.kind == "diagram":
                parts.append(
                    '    <div class="summary-artifact-preview">'
                    f'{_render_comment_diagram(comments, block.diagram, block.diagram_focus, block.diagram_notes)}'
                    "</div>\n"
                )
            elif block.kind == "log":
                parts.append(
                    '    <div class="summary-artifact-preview">'
                    f'{_render_comment_log(comments, block.log, block.log_focus)}'
                    "</div>\n"
                )
    elif comments.summary:
        parts.append(
            f'    <p class="review-summary">{_format_text(comments.summary, comments.vocabulary)}</p>\n'
        )
    parts.append("  </div></section>\n")
    return "".join(parts)


def _render_comments_index(comments: ReviewComments, diff_file_order: list[str]) -> str:
    parts = [
        '  <section class="review-nav" id="review-comments">'
        '<div class="review-nav-head"><h2>Review Comments</h2>'
        '<button type="button" data-review-nav-reset>Reset tree</button></div>\n'
    ]
    comment_file_paths = set(comments.file_comments) | {key[0] for key in comments.inline_comments}
    file_paths = list(diff_file_order)
    file_paths.extend(sorted(comment_file_paths - set(file_paths)))
    comments_by_file = {
        file_path: [
            comment
            for key in sorted(comments.inline_comments)
            if key[0] == file_path
            for comment in comments.inline_comments[key]
        ]
        for file_path in file_paths
    }
    tree: dict[str, Any] = {"__items__": []}
    for file_path in file_paths:
        node = tree
        parts_path = file_path.split("/")
        for path_part in parts_path[:-1]:
            if path_part not in node:
                node[path_part] = {"__items__": []}
                node["__items__"].append(("dir", path_part))
            node = node[path_part]
        node["__items__"].append(("file", file_path))

    def render_tree(node: dict[str, Any], depth: int) -> None:
        items = list(node.get("__items__", ()))
        if not items:
            return
        parts.append(f'{" " * (6 + depth * 2)}<ul class="review-nav-children">\n')
        for item_kind, item_value in items:
            if item_kind == "dir":
                dirname = item_value
                child = node[dirname]
                child_items = list(child.get("__items__", ()))
                child_dirs = [kind for kind, _value in child_items if kind == "dir"]
                child_files = [kind for kind, _value in child_items if kind == "file"]
                is_passthrough = not child_files and len(child_dirs) == 1
                parts.append(
                    f'{" " * (8 + depth * 2)}<li class="review-nav-node review-nav-dir '
                    f'{"review-nav-passthrough " if is_passthrough else ""}is-open">\n'
                )
                if is_passthrough:
                    toggle = '<span class="review-nav-toggle-spacer" aria-hidden="true"></span>'
                else:
                    toggle = (
                        '<button type="button" class="review-nav-toggle" aria-expanded="true">'
                        '<span class="review-nav-twist" aria-hidden="true"></span></button>'
                    )
                parts.append(
                    f'{" " * (10 + depth * 2)}<div class="review-nav-row">{toggle}'
                    f'<span class="review-nav-label">{_esc(dirname)}</span></div>\n'
                )
                render_tree(child, depth + 1)
                parts.append(f'{" " * (8 + depth * 2)}</li>\n')
                continue
            if item_kind == "file":
                file_path = item_value
                filename = file_path.rsplit("/", 1)[-1]
                file_comments = comments_by_file[file_path]
                parts.append(f'{" " * (8 + depth * 2)}<li class="review-nav-node review-nav-file">\n')
                if file_comments:
                    toggle = (
                        '<button type="button" class="review-nav-toggle" aria-expanded="false">'
                        '<span class="review-nav-twist" aria-hidden="true"></span></button>'
                    )
                else:
                    toggle = '<span class="review-nav-toggle-spacer" aria-hidden="true"></span>'
                parts.append(
                    f'{" " * (10 + depth * 2)}<div class="review-nav-row">{toggle}'
                    f'<a class="review-nav-label" href="#{_anchor(file_path)}">{_esc(filename)}</a></div>\n'
                )
                if file_comments:
                    parts.append(
                        f'{" " * (12 + depth * 2)}<ol class="review-nav-comments">\n'
                    )
                    for comment in file_comments:
                        comment_id = _comment_anchor(comment.file_path, comment.line)
                        parts.append(
                            f'{" " * (14 + depth * 2)}<li>'
                            f'<a href="#{comment_id}" data-review-comment-link="{comment_id}">'
                            f'<span class="review-nav-line">{comment.line}</span>'
                            f'<span>{_esc(comment.title)}</span></a></li>\n'
                        )
                    parts.append(f'{" " * (12 + depth * 2)}</ol>\n')
                parts.append(f'{" " * (8 + depth * 2)}</li>\n')
        parts.append(f'{" " * (6 + depth * 2)}</ul>\n')

    parts.append('    <nav class="review-nav-tree" aria-label="Review comments navigation">\n')
    render_tree(tree, 0)
    parts.append("    </nav>\n")
    parts.append('    <div class="review-nav-resizer" aria-hidden="true"></div>\n')
    parts.append("  </section>\n")
    return "".join(parts)


def _render_story_section(comments: ReviewComments) -> str:
    parts = ['  <section class="story" id="story"><h2>Review Story</h2>\n']
    parts.append('    <div class="story-step-strip">\n')
    parts.append(
        '      <button type="button" class="story-page-button" data-story-nav="prev" '
        'aria-label="Previous story steps">&lsaquo;</button>\n'
    )
    parts.append('    <ol class="story-steps">\n')
    for index, step in enumerate(comments.story):
        attrs = _story_step_attrs(step, index, comments)
        parts.append(
            f'      <li><button type="button" class="story-step" id="{_story_anchor(step, index)}"'
            f'{attrs}><span class="story-step-index">{index + 1:02d}</span>'
            f'<span class="story-step-text"><strong>{_esc(step.title)}</strong></span></button></li>\n'
        )
    parts.append("    </ol>\n")
    parts.append(
        '      <button type="button" class="story-page-button" data-story-nav="next" '
        'aria-label="Next story steps">&rsaquo;</button>\n'
    )
    parts.append("    </div>\n")
    parts.append('    <div class="story-details" id="story-details">\n')
    parts.append('      <div class="story-details-title" id="story-details-title">Details</div>\n')
    parts.append('      <div id="story-details-body"></div>\n')
    parts.append("    </div>\n")
    parts.append("  </section>\n")
    return "".join(parts)


def _render_settings_launcher(extra_class: str = "") -> str:
    return (
        f'<div class="settings-launcher{extra_class}">\n'
        '  <button type="button" class="settings-toggle" data-settings-toggle '
        'aria-haspopup="dialog" aria-expanded="false" aria-label="Settings">'
        '<span aria-hidden="true"></span></button>\n'
        "</div>\n"
    )


def _render_to_top_button() -> str:
    return '  <button type="button" class="to-top-button" data-story-top aria-label="To top">↑</button>\n'


def _story_step_attrs(step: StoryStep, index: int, comments: ReviewComments) -> str:
    attrs = [
        f' data-story-index="{index}"',
        f' data-story-title="{_esc(step.title)}"',
        f' data-story-body="{_esc(step.body)}"',
        f' data-story-body-html="{_esc(_format_text(step.body, comments.vocabulary))}"',
    ]
    target = _story_target(step)
    if target is not None:
        attrs.append(f' data-story-target="{_esc(target)}"')
    if step.diagram:
        attrs.append(f' data-story-diagram="{_esc(step.diagram)}"')
        attrs.append(_json_attr("data-story-diagram-focus", step.diagram_focus))
        attrs.append(_json_attr("data-story-diagram-notes", step.diagram_notes))
        if step.diagram_zoom is not None:
            attrs.append(f' data-story-diagram-zoom="{step.diagram_zoom:g}"')
    if step.log:
        attrs.append(f' data-story-log="{_esc(step.log)}"')
        attrs.append(_json_attr("data-story-log-focus", step.log_focus))
        if step.log_zoom is not None:
            attrs.append(f' data-story-log-zoom="{step.log_zoom:g}"')
    artifact_comment = step.artifact_comment
    if artifact_comment is None and (step.diagram or step.log):
        artifact_comment = step.body
    if artifact_comment:
        attrs.append(f' data-story-artifact-comment="{_esc(artifact_comment)}"')
    return "".join(attrs)


def _story_target(step: StoryStep) -> str | None:
    if step.comment_file_path is not None and step.comment_line is not None:
        return _comment_anchor(step.comment_file_path, step.comment_line)
    if step.file_path is not None and step.line is not None:
        return _line_anchor(step.file_path, step.line)
    if step.file_path is not None:
        return _anchor(step.file_path)
    return None


def _story_anchor(step: StoryStep, index: int) -> str:
    return f"story-{index + 1}-{_anchor(step.step_id)}"


def _render_diagrams_section(comments: ReviewComments) -> str:
    parts = ['  <details class="asset-inventory"><summary>Diagrams</summary><div class="diagram-list">\n']
    for diagram in sorted(comments.diagrams.values(), key=lambda item: item.diagram_id):
        parts.append(_render_diagram_preview(diagram))
    parts.append("  </div></details>\n")
    return "".join(parts)


def _render_logs_section(comments: ReviewComments) -> str:
    parts = ['  <details class="asset-inventory"><summary>Logs</summary><div class="diagram-list">\n']
    for log in sorted(comments.logs.values(), key=lambda item: item.log_id):
        parts.append(_render_log_preview(log))
    parts.append("  </div></details>\n")
    return "".join(parts)


def _render_comment_assets(
    comments: ReviewComments,
    diagram_id: str | None,
    log_id: str | None,
    diagram_focus: tuple[str, ...] = (),
    log_focus: tuple[str, ...] = (),
    diagram_notes: tuple[dict[str, Any], ...] = (),
) -> str:
    return (
        _render_comment_diagram(comments, diagram_id, diagram_focus, diagram_notes)
        + _render_comment_log(comments, log_id, log_focus)
    )


def _render_comment_diagram(
    comments: ReviewComments,
    diagram_id: str | None,
    focus_terms: tuple[str, ...] = (),
    notes: tuple[dict[str, Any], ...] = (),
) -> str:
    if not diagram_id:
        return ""
    diagram = comments.diagrams.get(diagram_id)
    if diagram is None:
        return ""
    return (
        '<div class="diagram-preview-wrap">'
        f'{_render_diagram_preview(diagram, focus_terms, notes)}'
        "</div>"
    )


def _render_comment_log(
    comments: ReviewComments,
    log_id: str | None,
    focus_terms: tuple[str, ...] = (),
) -> str:
    if not log_id:
        return ""
    log = comments.logs.get(log_id)
    if log is None:
        return ""
    return (
        '<div class="diagram-preview-wrap">'
        f'{_render_log_preview(log, focus_terms)}'
        "</div>"
    )


def _render_diagram_preview(
    diagram: Diagram,
    focus_terms: tuple[str, ...] = (),
    notes: tuple[dict[str, Any], ...] = (),
) -> str:
    safe_id = _anchor(diagram.diagram_id)
    focus_attr = _focus_attr("data-diagram-focus", focus_terms)
    notes_attr = _json_attr("data-diagram-notes", notes)
    preview_src = _svg_data_uri(diagram.svg)
    dark_preview_src = _svg_data_uri(_dark_preview_svg(diagram.svg))
    return (
        '<button type="button" class="diagram-preview" '
        f'data-diagram-id="{_esc(safe_id)}"{focus_attr}{notes_attr} aria-label="Open diagram: {_esc(diagram.title)}">'
        f'<span class="diagram-preview-title">{_esc(diagram.title)}</span>'
        f'<span class="diagram-preview-canvas"><img class="diagram-preview-img-light" src="{_esc(preview_src)}" alt="">'
        f'<img class="diagram-preview-img-dark" src="{_esc(dark_preview_src)}" alt=""></span>'
        "</button>\n"
    )


def _svg_data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _dark_preview_svg(svg: str) -> str:
    style = """
<style>
svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover),
svg tspan:not(.diagram-note-text):not(.diagram-note-marker-text):not(.asset-focus-match):not(.asset-focus-related-hover) { fill: #d4d4d4 !important; }
svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link),
svg path:not(.diagram-note-box):not(.diagram-note-link),
svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector) { stroke: #c5c5c5 !important; }
svg polygon[fill="#FFFFFF"],
svg polygon[fill="#FEFECE"],
svg polygon[fill="#EEEEEE"],
svg path[fill="#FEFECE"] { fill: #252526 !important; stroke: #c5c5c5 !important; }
svg rect:not(.diagram-note-box):not(.diagram-code-link-badge-box) { fill: #252526 !important; stroke: #c5c5c5 !important; }
svg path[fill="#FBFB77"] { fill: #3a3217 !important; stroke: #cca700 !important; }
</style>
"""
    return re.sub(r"(<svg\b[^>]*>)", r"\1" + style, svg, count=1, flags=re.IGNORECASE)


def _render_log_preview(log: LogAttachment, focus_terms: tuple[str, ...] = ()) -> str:
    safe_id = _anchor(log.log_id)
    focus_attr = _focus_attr("data-log-focus", focus_terms)
    return (
        '<button type="button" class="diagram-preview log-preview" '
        f'data-log-id="{_esc(safe_id)}"{focus_attr} aria-label="Open log: {_esc(log.title)}">'
        f'<span class="diagram-preview-title">{_esc(log.title)}</span>'
        f'<pre class="log-preview-text">{_esc(_log_excerpt(log.text))}</pre>'
        "</button>\n"
    )


def _render_diagram_modal(comments: ReviewComments) -> str:
    parts = ['<div class="diagram-modal" id="diagram-modal" hidden>\n']
    parts.append('  <div class="diagram-backdrop" data-diagram-close></div>\n')
    parts.append('  <div class="diagram-dialog" role="dialog" aria-modal="true" aria-labelledby="diagram-modal-title">\n')
    parts.append('    <div class="diagram-toolbar">\n')
    parts.append('      <h2 id="diagram-modal-title">Diagram</h2>\n')
    parts.append('      <div class="diagram-tools">\n')
    parts.append('        <div class="diagram-search-tools">\n')
    parts.append('        <input id="diagram-search" type="search" placeholder="Search" aria-label="Search opened asset">\n')
    parts.append('        <span id="diagram-search-count" class="diagram-search-count"></span>\n')
    parts.append('        <button type="button" data-diagram-search="prev" aria-label="Previous search match">Prev</button>\n')
    parts.append('        <button type="button" data-diagram-search="next" aria-label="Next search match">Next</button>\n')
    parts.append("        </div>\n")
    parts.append('        <div class="diagram-action-tools">\n')
    parts.append('        <button type="button" id="diagram-export" data-asset-export hidden>Export</button>\n')
    parts.append('        <button type="button" data-diagram-zoom="out" data-diagram-zoom-tool aria-label="Zoom out">-</button>\n')
    parts.append(
        '        <button type="button" data-diagram-zoom="reset" data-diagram-zoom-tool aria-label="Reset zoom">'
        '<span id="diagram-zoom-label">100%</span></button>\n'
    )
    parts.append('        <button type="button" data-diagram-zoom="in" data-diagram-zoom-tool aria-label="Zoom in">+</button>\n')
    parts.append('        <button type="button" data-diagram-close aria-label="Close diagram">&times;</button>\n')
    parts.append("        </div>\n")
    parts.append("      </div>\n")
    parts.append("    </div>\n")
    parts.append('    <div class="diagram-scroll" id="diagram-modal-content"></div>\n')
    parts.append("  </div>\n")
    parts.append("</div>\n")
    parts.append('<div class="diagram-story-nav" aria-label="Review story navigation">\n')
    parts.append('  <button type="button" data-diagram-story-step="prev" aria-label="Previous review story step">&larr; Previous slide</button>\n')
    parts.append('  <button type="button" class="story-slide-toggle" data-diagram-story-toggle data-tooltip="Open slide" aria-label="Open slide"></button>\n')
    parts.append('  <button type="button" data-diagram-story-step="next" aria-label="Next review story step">Next slide &rarr;</button>\n')
    parts.append("</div>\n")
    parts.append('<div class="diagram-store" hidden>\n')
    for diagram in comments.diagrams.values():
        safe_id = _anchor(diagram.diagram_id)
        links_attr = _json_attr("data-code-links", diagram.code_links)
        parts.append(
            f'  <template id="diagram-template-{_esc(safe_id)}" '
            f'data-title="{_esc(diagram.title)}"{links_attr}>{diagram.svg}</template>\n'
        )
    for log in comments.logs.values():
        safe_id = _anchor(log.log_id)
        parts.append(
            f'  <template id="log-template-{_esc(safe_id)}" '
            f'data-title="{_esc(log.title)}">'
            f'<pre class="log-view-text">{_esc(log.text)}</pre></template>\n'
        )
    parts.append("</div>\n")
    parts.append(diagram_script())
    return "".join(parts)


def _maybe_code(value: str | None) -> str:
    if not value:
        return "n/a"
    return f"<code>{_esc(value)}</code>"


def _log_excerpt(text: str, *, max_lines: int = 12, max_chars: int = 1400) -> str:
    excerpt = "\n".join(text.splitlines()[:max_lines])
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip()
    if excerpt != text:
        excerpt = f"{excerpt}\n..."
    return excerpt


def _focus_attr(name: str, terms: tuple[str, ...]) -> str:
    if not terms:
        return ""
    payload = json.dumps(list(terms), ensure_ascii=False)
    return f' {name}="{_esc(payload)}"'


def _json_attr(name: str, value: object) -> str:
    if not value:
        return ""
    payload = json.dumps(value, ensure_ascii=False)
    return f' {name}="{_esc(payload)}"'
