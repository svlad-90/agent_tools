from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class AgentSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class TextMatch:
    path: Path
    line: int
    column: int
    text: str
    groups: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class FileMatch:
    path: Path
    score: int
    reason: str


@dataclass(frozen=True)
class RangeSnippet:
    path: Path
    start: int
    end: int
    match_lines: tuple[int, ...]
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class TextSearchReport:
    root: Path
    query: str
    elapsed_seconds: float
    files_scanned: int
    files_skipped: int
    matches: tuple[TextMatch, ...]
    ranges: tuple[RangeSnippet, ...]
    truncated: bool


@dataclass(frozen=True)
class FileSearchReport:
    root: Path
    query: str
    elapsed_seconds: float
    files_scanned: int
    matches: tuple[FileMatch, ...]
    truncated: bool
