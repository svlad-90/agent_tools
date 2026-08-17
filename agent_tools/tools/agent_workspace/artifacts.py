from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os

from .core import TaskSummary

_LOG_SUFFIXES = {".log"}


@dataclass(frozen=True)
class ArtifactEntry:
    group: str
    path: Path
    updated: float


def task_artifact_entries(
    task: TaskSummary,
    *,
    sort_column: str = "name",
    descending: bool = False,
) -> list[ArtifactEntry]:
    entries: list[ArtifactEntry] = []
    for path in task_artifact_files(task):
        group = artifact_group(task, path)
        if group is not None:
            entries.append(ArtifactEntry(group, path, artifact_updated_timestamp(path)))
    result: list[ArtifactEntry] = []
    for group in sorted({entry.group for entry in entries}, key=artifact_group_sort_key):
        group_entries = [entry for entry in entries if entry.group == group]
        if sort_column == "updated":
            if descending:
                group_entries.sort(
                    key=lambda entry: (-entry.updated, artifact_relative_label(task, entry.path).casefold())
                )
            else:
                group_entries.sort(
                    key=lambda entry: (entry.updated, artifact_relative_label(task, entry.path).casefold())
                )
        else:
            group_entries.sort(
                key=lambda entry: (entry.path.name.casefold(), artifact_relative_label(task, entry.path).casefold()),
                reverse=descending,
            )
        result.extend(group_entries)
    return result


def task_artifact_files(task: TaskSummary) -> Iterator[Path]:
    report = task.path / "report"
    if not report.is_dir():
        return
    for root, dirs, files in os.walk(report):
        dirs.sort()
        for filename in sorted(files, key=str.casefold):
            yield Path(root) / filename


def artifact_group(task: TaskSummary, path: Path) -> str | None:
    suffix = path.suffix.casefold()
    try:
        rel = path.relative_to(task.path)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 1 or parts[0] != "report":
        return None
    if len(parts) >= 2 and parts[1] == "diff":
        return "diff_reports"
    if len(parts) >= 2 and parts[1] == "puml":
        return "diagrams"
    if suffix in _LOG_SUFFIXES:
        return "logs"
    return "artifacts"


def artifact_group_sort_key(group: str) -> int:
    order = {"logs": 0, "diagrams": 1, "diff_reports": 2, "artifacts": 3}
    return order.get(group, 99)


def artifact_relative_label(task: TaskSummary, path: Path) -> str:
    try:
        return str(path.relative_to(task.path))
    except ValueError:
        return str(path)


def artifact_updated_timestamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def artifact_updated_label(updated: float) -> str:
    if updated <= 0:
        return ""
    return datetime.fromtimestamp(updated).strftime("%Y-%m-%d %H:%M")


def artifact_delete_paths(
    task: TaskSummary,
    *,
    artifact_path: Path | None = None,
    group: str | None = None,
    delete_all: bool = False,
) -> list[Path]:
    if artifact_path is not None:
        try:
            artifact_path.relative_to(task.path)
        except ValueError:
            return []
        return [artifact_path] if artifact_path.is_file() else []
    if delete_all:
        return files_under(task.path / "report")
    if group == "logs":
        return [
            path
            for path in files_under(task.path / "report")
            if path.suffix.casefold() in _LOG_SUFFIXES
        ]
    if group == "diagrams":
        return files_under(task.path / "report" / "puml")
    if group == "diff_reports":
        return files_under(task.path / "report" / "diff")
    if group == "artifacts":
        return [
            path
            for path in files_under(task.path / "report")
            if artifact_group(task, path) == "artifacts"
        ]
    return []


def artifact_context_action(artifact_path: Path | None, group: str | None) -> str:
    if artifact_path is not None:
        return "artifact"
    if group is not None:
        return "group"
    return "all"


def artifact_selectable_path(task: TaskSummary, artifact_path: Path) -> Path | None:
    try:
        artifact_path.relative_to(task.path)
    except ValueError:
        return None
    return artifact_path if artifact_path.is_file() else None


def files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for filename in sorted(files, key=str.casefold):
            path = Path(current) / filename
            if path.is_file():
                paths.append(path)
    return paths
