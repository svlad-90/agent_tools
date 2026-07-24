from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .models import DiffReportError, DiffSource, DiffStats


def load_diff_source(
    repo_path: Path | None,
    rev_range: str,
    diff_file: Path | None,
    context: int,
    display_label: str | None,
) -> DiffSource:
    if diff_file is not None:
        diff_text = diff_file.read_text(encoding="utf-8")
        commit, subject, message = commit_message_from_patch(diff_text)
        return DiffSource(
            diff_text=diff_text,
            stat_text="Loaded from diff file; git stat is unavailable.",
            label=display_label or str(diff_file),
            commit=commit,
            subject=subject,
            message=message,
        )
    if repo_path is None:
        raise DiffReportError("--repo is required unless --diff-file is used")
    if not repo_path.exists():
        raise DiffReportError(f"Repository path does not exist: {repo_path}")
    base, head = parse_rev_range(rev_range)
    diff_text = git(repo_path, ["diff", "--find-renames", f"--unified={context}", base, head])
    stat_text = git(repo_path, ["diff", "--stat", base, head])
    commit = git(repo_path, ["rev-parse", head]).strip()
    subject = git(repo_path, ["log", "-1", "--pretty=%s", head]).strip()
    message = git(repo_path, ["log", "-1", "--format=%B", head]).strip()
    return DiffSource(
        diff_text=diff_text,
        stat_text=stat_text,
        label=display_label or f"{repo_path} {base}..{head}",
        commit=None if display_label else commit,
        subject=subject,
        message=message,
    )


def diff_stats(diff_text: str) -> DiffStats:
    lines_added = 0
    lines_deleted = 0
    files_changed = 0
    files_added = 0
    files_deleted = 0
    files_renamed = 0
    current_metadata: set[str] = set()

    def close_file() -> None:
        nonlocal files_added, files_deleted, files_renamed
        if not current_metadata:
            return
        if "renamed" in current_metadata:
            files_renamed += 1
        elif "added" in current_metadata:
            files_added += 1
        elif "deleted" in current_metadata:
            files_deleted += 1

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            close_file()
            files_changed += 1
            current_metadata = set()
            continue
        if line.startswith("new file mode "):
            current_metadata.add("added")
        elif line.startswith("deleted file mode "):
            current_metadata.add("deleted")
        elif line.startswith("rename from ") or line.startswith("rename to "):
            current_metadata.add("renamed")
        if line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            lines_deleted += 1
    close_file()
    return DiffStats(
        files_changed=files_changed,
        files_added=files_added,
        files_deleted=files_deleted,
        files_renamed=files_renamed,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
    )


def diff_files(diff_text: str) -> list[str]:
    files: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            files.append(file_from_diff_header(line))
    return files


def parse_rev_range(rev_range: str) -> tuple[str, str]:
    if "..." in rev_range:
        base, head = rev_range.split("...", 1)
    elif ".." in rev_range:
        base, head = rev_range.split("..", 1)
    else:
        raise DiffReportError("--range must use '..' or '...', for example HEAD^..HEAD")
    if not base or not head:
        raise DiffReportError("--range must include both base and head revisions")
    return base, head


def git(repo_path: Path, args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo_path), *args], text=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or str(error)
        raise DiffReportError(message) from error


def commit_message_from_patch(diff_text: str) -> tuple[str | None, str | None, str | None]:
    commit_id = None
    message_lines: list[str] = []
    in_message = False

    for line in diff_text.splitlines():
        if commit_id is None and line.startswith("From "):
            parts = line.split()
            if len(parts) >= 2:
                commit_id = parts[1]
        if line.startswith("diff --git "):
            break
        if line.startswith("    "):
            in_message = True
            message_lines.append(line[4:])
        elif in_message and line == "":
            message_lines.append("")
        elif in_message:
            break

    while message_lines and message_lines[0] == "":
        message_lines.pop(0)
    while message_lines and message_lines[-1] == "":
        message_lines.pop()

    if not message_lines:
        return commit_id, None, None

    message = "\n".join(message_lines)
    subject = next((line for line in message_lines if line), None)
    return commit_id, subject, message


def file_from_diff_header(line: str) -> str:
    match = re.match(r"diff --git a/(.*?) b/(.*)", line)
    if not match:
        return line
    return match.group(2)
