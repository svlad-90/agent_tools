from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import (
    Diagram,
    DiffReportError,
    InlineComment,
    LogAttachment,
    ReviewComments,
    StoryStep,
    SummaryBlock,
    VocabularyTerm,
)


def load_comments(comments_file: Path | None) -> ReviewComments:
    payload = load_comments_payload(comments_file)
    base_dir = comments_file.parent if comments_file is not None else None
    return comments_from_payload(payload, base_dir=base_dir)


def comments_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> ReviewComments:
    if not isinstance(payload, dict):
        raise DiffReportError("Comments JSON must be an object")

    raw_commit = payload.get("commit", {})
    if raw_commit is None:
        raw_commit = {}
    if not isinstance(raw_commit, dict):
        raise DiffReportError("comments.commit must be an object")
    commit_id = str(raw_commit["id"]) if "id" in raw_commit else None
    commit_message = str(raw_commit["message"]) if "message" in raw_commit else None

    raw_files = payload.get("files", {})
    if not isinstance(raw_files, dict):
        raise DiffReportError("comments.files must be an object")
    file_comments: dict[str, str] = {}
    file_diagrams: dict[str, str] = {}
    file_logs: dict[str, str] = {}
    file_diagram_focus: dict[str, tuple[str, ...]] = {}
    file_log_focus: dict[str, tuple[str, ...]] = {}
    file_diagram_notes: dict[str, tuple[dict[str, Any], ...]] = {}
    for path, value in raw_files.items():
        path_key = str(path)
        if isinstance(value, dict):
            file_comments[path_key] = str(value.get("body", ""))
            if "diagram" in value:
                file_diagrams[path_key] = str(value["diagram"])
            if "diagram_focus" in value:
                file_diagram_focus[path_key] = focus_terms(value["diagram_focus"], field="diagram_focus")
            if "diagram_notes" in value:
                file_diagram_notes[path_key] = diagram_notes(value["diagram_notes"])
            if "log" in value:
                file_logs[path_key] = str(value["log"])
            if "log_focus" in value:
                file_log_focus[path_key] = focus_terms(value["log_focus"], field="log_focus")
        else:
            file_comments[path_key] = str(value)

    diagrams = diagrams_from_payload(payload, base_dir=base_dir)
    logs = logs_from_payload(payload, base_dir=base_dir)

    grouped: dict[tuple[str, int], list[InlineComment]] = {}
    raw_inline = payload.get("inline", [])
    if not isinstance(raw_inline, list):
        raise DiffReportError("comments.inline must be a list")
    for item in raw_inline:
        if not isinstance(item, dict):
            raise DiffReportError("comments.inline entries must be objects")
        file_path = str(required(item, "file"))
        line = int(required(item, "line"))
        line_range = comment_line_range(item.get("range"), line=line)
        body = str(required(item, "body"))
        title = str(item.get("title", "Review comment"))
        diagram = str(item["diagram"]) if "diagram" in item else None
        if diagram is not None and diagram not in diagrams:
            raise DiffReportError(f"unknown diagram referenced by inline comment: {diagram}")
        log = str(item["log"]) if "log" in item else None
        if log is not None and log not in logs:
            raise DiffReportError(f"unknown log referenced by inline comment: {log}")
        diagram_focus = focus_terms(item.get("diagram_focus", ()), field="diagram_focus")
        log_focus = focus_terms(item.get("log_focus", ()), field="log_focus")
        notes = diagram_notes(item.get("diagram_notes", ()))
        grouped.setdefault((file_path, line), []).append(
            InlineComment(
                file_path=file_path,
                line=line,
                line_range=line_range,
                body=body,
                title=title,
                diagram=diagram,
                log=log,
                diagram_focus=diagram_focus,
                log_focus=log_focus,
                diagram_notes=notes,
            )
        )
    for file_path, diagram in file_diagrams.items():
        if diagram not in diagrams:
            raise DiffReportError(f"unknown diagram referenced by file comment {file_path}: {diagram}")
    for file_path, log in file_logs.items():
        if log not in logs:
            raise DiffReportError(f"unknown log referenced by file comment {file_path}: {log}")
    story = story_from_payload(payload, diagrams=diagrams, logs=logs)
    summary_blocks = summary_blocks_from_payload(payload, diagrams=diagrams, logs=logs)
    vocabulary = vocabulary_from_payload(payload)
    return ReviewComments(
        file_comments=file_comments,
        inline_comments={key: tuple(value) for key, value in grouped.items()},
        diagrams=diagrams,
        logs=logs,
        story=story,
        file_diagrams=file_diagrams,
        file_logs=file_logs,
        file_diagram_focus=file_diagram_focus,
        file_log_focus=file_log_focus,
        file_diagram_notes=file_diagram_notes,
        vocabulary=vocabulary,
        summary=str(payload["summary"]) if "summary" in payload else None,
        summary_blocks=summary_blocks,
        commit_id=commit_id,
        commit_message=commit_message,
    )


def vocabulary_from_payload(payload: dict[str, Any]) -> tuple[VocabularyTerm, ...]:
    raw_vocabulary = payload.get("vocabulary", {})
    if raw_vocabulary is None:
        return ()
    if not isinstance(raw_vocabulary, dict):
        raise DiffReportError("comments.vocabulary must be an object")

    terms: list[VocabularyTerm] = []
    seen_terms: set[str] = set()
    for raw_term, raw_value in raw_vocabulary.items():
        term = str(raw_term).strip()
        if not term:
            raise DiffReportError("comments.vocabulary keys must be non-empty terms")
        term_key = term.casefold()
        if term_key in seen_terms:
            raise DiffReportError(f"duplicate vocabulary term: {term}")
        seen_terms.add(term_key)

        if isinstance(raw_value, dict):
            if "definition" not in raw_value:
                raise DiffReportError(f"comments.vocabulary.{term} must define definition")
            definition = str(raw_value["definition"]).strip()
            aliases = focus_terms(raw_value.get("aliases", ()), field=f"vocabulary.{term}.aliases")
        else:
            definition = str(raw_value).strip()
            aliases = ()
        if not definition:
            raise DiffReportError(f"comments.vocabulary.{term} definition must be non-empty")
        terms.append(VocabularyTerm(term=term, definition=definition, aliases=aliases))
    return tuple(sorted(terms, key=lambda item: item.term.casefold()))


def summary_blocks_from_payload(
    payload: dict[str, Any],
    *,
    diagrams: dict[str, Diagram],
    logs: dict[str, LogAttachment],
) -> tuple[SummaryBlock, ...]:
    raw_blocks = payload.get("summary_blocks")
    if raw_blocks is None:
        return ()
    if not isinstance(raw_blocks, list):
        raise DiffReportError("comments.summary_blocks must be a list")
    blocks: list[SummaryBlock] = []
    for index, item in enumerate(raw_blocks):
        if isinstance(item, str):
            blocks.append(SummaryBlock(kind="text", text=item))
            continue
        if not isinstance(item, dict):
            raise DiffReportError("comments.summary_blocks entries must be strings or objects")
        block_type = str(item.get("type", "")).strip().lower()
        if not block_type:
            if "diagram" in item:
                block_type = "diagram"
            elif "log" in item:
                block_type = "log"
            else:
                block_type = "text"
        if block_type in {"text", "paragraph"}:
            text = item.get("body", item.get("text", ""))
            blocks.append(SummaryBlock(kind="text", text=str(text)))
            continue
        if block_type == "diagram":
            diagram = str(required(item, "diagram"))
            if diagram not in diagrams:
                raise DiffReportError(f"unknown diagram referenced by summary block {index}: {diagram}")
            blocks.append(
                SummaryBlock(
                    kind="diagram",
                    diagram=diagram,
                    diagram_focus=focus_terms(item.get("diagram_focus", ()), field="diagram_focus"),
                    diagram_notes=diagram_notes(item.get("diagram_notes", ())),
                )
            )
            continue
        if block_type == "log":
            log = str(required(item, "log"))
            if log not in logs:
                raise DiffReportError(f"unknown log referenced by summary block {index}: {log}")
            blocks.append(
                SummaryBlock(
                    kind="log",
                    log=log,
                    log_focus=focus_terms(item.get("log_focus", ()), field="log_focus"),
                )
            )
            continue
        raise DiffReportError(f"unknown summary block type at index {index}: {block_type}")
    return tuple(blocks)


def story_from_payload(
    payload: dict[str, Any],
    *,
    diagrams: dict[str, Diagram],
    logs: dict[str, LogAttachment],
) -> tuple[StoryStep, ...]:
    raw_story = payload.get("story", ())
    if raw_story in ((), [], None):
        return ()
    if not isinstance(raw_story, list):
        raise DiffReportError("comments.story must be a list")

    steps: list[StoryStep] = []
    for index, raw_step in enumerate(raw_story):
        if not isinstance(raw_step, dict):
            raise DiffReportError(f"comments.story[{index}] must be an object")
        title = str(required(raw_step, "title"))
        body = str(raw_step.get("body", ""))
        file_path = str(raw_step["file"]) if "file" in raw_step else None
        line = int(raw_step["line"]) if "line" in raw_step else None
        if line is not None and file_path is None:
            raise DiffReportError(f"comments.story[{index}] line requires file")
        if line is not None and line < 1:
            raise DiffReportError(f"comments.story[{index}] line must be a positive integer")

        comment_file_path: str | None = None
        comment_line: int | None = None
        if "comment" in raw_step:
            raw_comment = raw_step["comment"]
            if not isinstance(raw_comment, dict):
                raise DiffReportError(f"comments.story[{index}].comment must be an object")
            comment_file_path = str(required(raw_comment, "file"))
            comment_line = int(required(raw_comment, "line"))
            if comment_line < 1:
                raise DiffReportError(
                    f"comments.story[{index}].comment.line must be a positive integer"
                )

        diagram = str(raw_step["diagram"]) if "diagram" in raw_step else None
        if diagram is not None and diagram not in diagrams:
            raise DiffReportError(f"unknown diagram referenced by story step {index + 1}: {diagram}")
        log = str(raw_step["log"]) if "log" in raw_step else None
        if log is not None and log not in logs:
            raise DiffReportError(f"unknown log referenced by story step {index + 1}: {log}")
        diagram_zoom = float(raw_step["diagram_zoom"]) if "diagram_zoom" in raw_step else None
        if diagram_zoom is not None and diagram_zoom <= 0:
            raise DiffReportError(
                f"comments.story[{index}].diagram_zoom must be a positive number"
            )
        log_zoom = float(raw_step["log_zoom"]) if "log_zoom" in raw_step else None
        if log_zoom is not None and log_zoom <= 0:
            raise DiffReportError(f"comments.story[{index}].log_zoom must be a positive number")
        if not any((file_path, comment_file_path, diagram, log)):
            raise DiffReportError(
                f"comments.story[{index}] must target a file, comment, diagram, or log"
            )
        steps.append(
            StoryStep(
                step_id=str(raw_step.get("id", f"story-step-{index + 1}")),
                title=title,
                body=body,
                file_path=file_path,
                line=line,
                comment_file_path=comment_file_path,
                comment_line=comment_line,
                diagram=diagram,
                log=log,
                diagram_focus=focus_terms(raw_step.get("diagram_focus", ()), field="diagram_focus"),
                log_focus=focus_terms(raw_step.get("log_focus", ()), field="log_focus"),
                diagram_notes=diagram_notes(raw_step.get("diagram_notes", ())),
                diagram_zoom=diagram_zoom,
                log_zoom=log_zoom,
                artifact_comment=(
                    str(raw_step["artifact_comment"]) if "artifact_comment" in raw_step else None
                ),
            )
        )
    return tuple(steps)


def diagrams_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path | None,
) -> dict[str, Diagram]:
    raw_diagrams = payload.get("diagrams", {})
    if raw_diagrams in ({}, None):
        return {}
    if not isinstance(raw_diagrams, dict):
        raise DiffReportError("comments.diagrams must be an object")

    diagrams: dict[str, Diagram] = {}
    for diagram_id, raw in raw_diagrams.items():
        diagram_key = str(diagram_id)
        if not isinstance(raw, dict):
            raise DiffReportError(f"diagram entry must be an object: {diagram_key}")
        title = str(raw.get("title", diagram_key))
        if "svg_inline" in raw:
            svg = normalize_svg(str(raw["svg_inline"]), source=f"diagram {diagram_key}")
        elif "svg" in raw:
            svg_path = Path(str(raw["svg"]))
            if not svg_path.is_absolute() and base_dir is not None:
                svg_path = base_dir / svg_path
            svg = read_svg_file(svg_path)
        else:
            raise DiffReportError(f"diagram entry is missing svg or svg_inline: {diagram_key}")
        code_links = diagram_code_links(raw, diagram_key)
        diagrams[diagram_key] = Diagram(
            diagram_id=diagram_key,
            title=title,
            svg=svg,
            code_links=code_links,
        )
    return diagrams


def diagram_code_links(raw: dict[str, Any], diagram_key: str) -> tuple[dict[str, Any], ...]:
    raw_links = raw.get("code_links", ())
    if raw_links in ((), [], None):
        return ()
    if not isinstance(raw_links, list):
        raise DiffReportError(f"diagram code_links must be a list: {diagram_key}")

    links: list[dict[str, Any]] = []
    for index, raw_link in enumerate(raw_links):
        if not isinstance(raw_link, dict):
            raise DiffReportError(f"diagram code_links[{index}] must be an object: {diagram_key}")
        target = str(raw_link.get("target", "")).strip()
        file_path = str(raw_link.get("file", "")).strip()
        line = raw_link.get("line")
        if not target:
            raise DiffReportError(f"diagram code_links[{index}] is missing target: {diagram_key}")
        if not file_path:
            raise DiffReportError(f"diagram code_links[{index}] is missing file: {diagram_key}")
        if not isinstance(line, int):
            raise DiffReportError(f"diagram code_links[{index}] line must be an integer: {diagram_key}")
        link: dict[str, Any] = {
            "target": target,
            "file": file_path,
            "line": line,
            "title": str(raw_link.get("title", target)),
        }
        if "range" in raw_link:
            link["range"] = raw_link["range"]
        links.append(link)
    return tuple(links)


def read_svg_file(svg_path: Path) -> str:
    if svg_path.suffix.lower() != ".svg":
        raise DiffReportError(f"diagram file must be an .svg file: {svg_path}")
    if not svg_path.exists():
        raise DiffReportError(f"diagram SVG file does not exist: {svg_path}")
    svg = svg_path.read_text(encoding="utf-8")
    return normalize_svg(svg, source=str(svg_path))


def logs_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path | None,
) -> dict[str, LogAttachment]:
    raw_logs = payload.get("logs", {})
    if raw_logs in ({}, None):
        return {}
    if not isinstance(raw_logs, dict):
        raise DiffReportError("comments.logs must be an object")

    logs: dict[str, LogAttachment] = {}
    for log_id, raw in raw_logs.items():
        log_key = str(log_id)
        if not isinstance(raw, dict):
            raise DiffReportError(f"log entry must be an object: {log_key}")
        title = str(raw.get("title", log_key))
        if "text_inline" in raw:
            text = str(raw["text_inline"])
        elif "path" in raw:
            log_path = Path(str(raw["path"]))
            if not log_path.is_absolute() and base_dir is not None:
                log_path = base_dir / log_path
            text = read_log_file(log_path)
        else:
            raise DiffReportError(f"log entry is missing path or text_inline: {log_key}")
        logs[log_key] = LogAttachment(log_id=log_key, title=title, text=text)
    return logs


def read_log_file(log_path: Path) -> str:
    if not log_path.exists():
        raise DiffReportError(f"log file does not exist: {log_path}")
    if not log_path.is_file():
        raise DiffReportError(f"log path is not a file: {log_path}")
    return log_path.read_text(encoding="utf-8", errors="replace")


def normalize_svg(svg: str, *, source: str) -> str:
    if "<svg" not in svg:
        raise DiffReportError(f"diagram does not look like SVG: {source}")
    if re.search(r"<\s*script\b", svg, flags=re.IGNORECASE):
        raise DiffReportError(f"diagram SVG must not contain script tags: {source}")
    svg = re.sub(r"^\s*<\?xml[^>]*>\s*", "", svg)
    svg = re.sub(r"^\s*<!DOCTYPE[^>]*>\s*", "", svg, flags=re.IGNORECASE)
    return svg


def load_comments_payload(comments_file: Path | None) -> dict[str, Any]:
    if comments_file is None:
        return {}
    payload = json.loads(comments_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DiffReportError("Comments JSON must be an object")
    return payload


def comment_line_range(value: Any, *, line: int) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        start = int(required(value, "start"))
        end = int(required(value, "end"))
    elif isinstance(value, list) and len(value) == 2:
        start = int(value[0])
        end = int(value[1])
    else:
        raise DiffReportError(
            "comments.inline[].range must be an object with start/end or a [start, end] array"
        )
    if start < 1 or end < start:
        raise DiffReportError("comments.inline[].range must use positive inclusive line numbers")
    if line < start or line > end:
        raise DiffReportError("comments.inline[].line must be inside comments.inline[].range")
    return (start, end)


def required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise DiffReportError(f"comments inline entry is missing required key: {key}")
    return payload[key]


def focus_terms(raw: Any, *, field: str) -> tuple[str, ...]:
    if raw in (None, "", []):
        return ()
    if isinstance(raw, str):
        return (raw,)
    if not isinstance(raw, (list, tuple)):
        raise DiffReportError(f"comments {field} must be a string or list of strings")
    return tuple(str(item) for item in raw if str(item))


def diagram_notes(raw: Any) -> tuple[dict[str, Any], ...]:
    if raw in (None, "", [], ()):
        return ()
    if not isinstance(raw, list):
        raise DiffReportError("comments diagram_notes must be a list of objects")
    notes: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise DiffReportError("comments diagram_notes entries must be objects")
        text = str(required(item, "text"))
        note: dict[str, Any] = {"text": text}
        if "target" in item:
            note["target"] = str(item["target"])
        for key in ("x", "y", "dx", "dy"):
            if key in item:
                note[key] = float(item[key])
        if "target" not in note and ("x" not in note or "y" not in note):
            raise DiffReportError("diagram_notes entries must include target or both x and y")
        notes.append(note)
    return tuple(notes)
