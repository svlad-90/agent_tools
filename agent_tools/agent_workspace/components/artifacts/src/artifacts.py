from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO
import codecs
import ctypes
import os
import stat

from ...task_catalog.api import TaskSummary


_MAX_PREVIEW_BYTES = 1_000_000
_TEXT_SUFFIXES = {
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".py",
    ".sh",
    ".svg",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


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
    if len(parts) >= 2 and parts[1] == "logs":
        return "logs"
    return "artifacts"


def artifact_group_sort_key(group: str) -> int:
    order = {"logs": 0, "diagrams": 1, "diff_reports": 2, "artifacts": 3}
    return order.get(group, 99)


def artifact_group_folder(task: TaskSummary, group: str) -> Path | None:
    if group == "logs":
        return task.path / "report" / "logs"
    if group == "diagrams":
        return task.path / "report" / "puml"
    if group == "diff_reports":
        return task.path / "report" / "diff"
    if group == "artifacts":
        return task.path / "report"
    return None


def artifact_relative_label(task: TaskSummary, path: Path) -> str:
    try:
        return str(path.relative_to(task.path))
    except ValueError:
        return str(path)


def artifact_path_from_label(task: TaskSummary, label: str) -> Path | None:
    if not label or Path(label).is_absolute():
        return None
    task_root = task.path.resolve()
    candidate = (task_root / label).resolve()
    try:
        candidate.relative_to(task_root)
    except ValueError:
        return None
    if not candidate.is_file() or artifact_group(task, candidate) is None:
        return None
    return candidate


def artifact_text_preview(
    task: TaskSummary,
    label: str,
    *,
    max_bytes: int = 200_000,
) -> dict[str, object]:
    if not 1 <= max_bytes <= _MAX_PREVIEW_BYTES:
        raise ValueError(f"max_bytes must be between 1 and {_MAX_PREVIEW_BYTES}")
    path = artifact_path_from_label(task, label)
    if path is None:
        raise ValueError(f"unknown artifact: {label}")
    with _open_verified_artifact(task, label, path) as handle:
        file_stat = os.fstat(handle.fileno())
        raw = handle.read(max_bytes + 1)
    truncated = len(raw) > max_bytes
    raw = raw[:max_bytes]
    text_hint = path.suffix.casefold() in _TEXT_SUFFIXES
    binary = b"\x00" in raw and not text_hint
    if binary:
        content = ""
    else:
        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            content = decoder.decode(raw, final=not truncated)
        except UnicodeDecodeError:
            if not text_hint:
                content = ""
                binary = True
            else:
                content = raw.decode("utf-8", errors="replace")
    updated = file_stat.st_mtime
    return {
        "label": artifact_relative_label(task, path),
        "path": str(path),
        "group": artifact_group(task, path),
        "size": file_stat.st_size,
        "updated": updated,
        "updated_label": artifact_updated_label(updated),
        "content": content,
        "binary": binary,
        "truncated": truncated,
    }


def _open_verified_artifact(task: TaskSummary, label: str, path: Path) -> BinaryIO:
    if os.name == "nt":
        report_root = task.path.resolve() / "report"
        handle = path.open("rb")
        try:
            opened_path = _windows_open_file_path(handle)
            opened_path.relative_to(report_root)
        except (OSError, ValueError):
            handle.close()
            raise ValueError(f"artifact escaped task directory: {label}") from None
        return handle

    parts = Path(label).parts
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    current_fd = os.open(task.path.resolve(), directory_flags)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
    except OSError as error:
        raise ValueError(f"artifact path changed while opening: {label}") from error
    finally:
        os.close(current_fd)
    if not stat.S_ISREG(os.fstat(file_fd).st_mode):
        os.close(file_fd)
        raise ValueError(f"artifact is not a regular file: {label}")
    return os.fdopen(file_fd, "rb")


def _windows_open_file_path(handle: BinaryIO) -> Path:
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_uint
    os_handle = msvcrt.get_osfhandle(handle.fileno())
    size = kernel32.GetFinalPathNameByHandleW(os_handle, None, 0, 0)
    if not size:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(size)
    if not kernel32.GetFinalPathNameByHandleW(os_handle, buffer, size, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return Path(_normalize_windows_final_path(buffer.value)).resolve()


def _normalize_windows_final_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


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
        return files_under(task.path / "report" / "logs")
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
