from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InlineComment:
    file_path: str
    line: int
    body: str
    title: str = "Review comment"
    line_range: tuple[int, int] | None = None
    diagram: str | None = None
    log: str | None = None
    diagram_focus: tuple[str, ...] = ()
    log_focus: tuple[str, ...] = ()
    diagram_notes: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Diagram:
    diagram_id: str
    title: str
    svg: str
    code_links: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class LogAttachment:
    log_id: str
    title: str
    text: str


@dataclass(frozen=True)
class StoryStep:
    step_id: str
    title: str
    body: str
    file_path: str | None = None
    line: int | None = None
    comment_file_path: str | None = None
    comment_line: int | None = None
    diagram: str | None = None
    log: str | None = None
    diagram_focus: tuple[str, ...] = ()
    log_focus: tuple[str, ...] = ()
    diagram_notes: tuple[dict[str, Any], ...] = ()
    diagram_zoom: float | None = None
    log_zoom: float | None = None
    artifact_comment: str | None = None


@dataclass(frozen=True)
class SummaryBlock:
    kind: str
    text: str | None = None
    diagram: str | None = None
    log: str | None = None
    diagram_focus: tuple[str, ...] = ()
    log_focus: tuple[str, ...] = ()
    diagram_notes: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class VocabularyTerm:
    term: str
    definition: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewComments:
    file_comments: dict[str, str]
    inline_comments: dict[tuple[str, int], tuple[InlineComment, ...]]
    diagrams: dict[str, Diagram]
    logs: dict[str, LogAttachment]
    story: tuple[StoryStep, ...]
    file_diagrams: dict[str, str]
    file_logs: dict[str, str]
    file_diagram_focus: dict[str, tuple[str, ...]]
    file_log_focus: dict[str, tuple[str, ...]]
    file_diagram_notes: dict[str, tuple[dict[str, Any], ...]]
    summary: str | None = None
    summary_blocks: tuple[SummaryBlock, ...] = ()
    vocabulary: tuple[VocabularyTerm, ...] = ()
    commit_id: str | None = None
    commit_message: str | None = None


@dataclass(frozen=True)
class DiffSource:
    diff_text: str
    stat_text: str
    label: str
    commit: str | None = None
    subject: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class DiffStats:
    files_changed: int
    files_added: int
    files_deleted: int
    files_renamed: int
    lines_added: int
    lines_deleted: int


class DiffReportError(ValueError):
    pass
