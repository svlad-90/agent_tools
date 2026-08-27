from __future__ import annotations

import fnmatch
import os
from pathlib import Path
import subprocess
from typing import Iterable


DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        ".cache",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
    }
)


def iter_candidate_files(
    root: Path,
    *,
    include: Iterable[str],
    exclude: Iterable[str],
    hidden: bool,
    use_gitignore: bool,
) -> Iterable[Path]:
    include_patterns = tuple(include)
    exclude_patterns = tuple(exclude)
    if root.is_file():
        if file_allowed(root.parent, root, include_patterns, exclude_patterns, hidden):
            yield root
        return
    if use_gitignore:
        git_files = iter_git_candidate_files(root, include_patterns, exclude_patterns, hidden)
        if git_files is not None:
            yield from git_files
            return
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if directory_allowed(root, current / dirname, exclude_patterns, hidden)
        ]
        for filename in filenames:
            path = current / filename
            if file_allowed(root, path, include_patterns, exclude_patterns, hidden):
                yield path


def iter_git_candidate_files(
    root: Path,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    hidden: bool,
) -> Iterable[Path] | None:
    try:
        repo_result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    if repo_result.returncode != 0:
        return None
    repo_root = Path(repo_result.stdout.strip()).resolve()
    try:
        rel_root = root.resolve().relative_to(repo_root)
    except ValueError:
        return None
    command = ["git", "-C", str(repo_root), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--"]
    if rel_root.as_posix() != ".":
        command.append(rel_root.as_posix())
    try:
        files_result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None
    if files_result.returncode != 0:
        return None
    candidates: list[Path] = []
    for raw_entry in files_result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        rel = Path(raw_entry.decode("utf-8", errors="replace"))
        path = repo_root / rel
        if not path.is_file():
            continue
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if file_allowed(root, path, include_patterns, exclude_patterns, hidden):
            candidates.append(path)
    return candidates


def directory_allowed(
    root: Path,
    path: Path,
    exclude_patterns: tuple[str, ...],
    hidden: bool,
) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = rel.parts
    if not hidden and any(part.startswith(".") for part in parts):
        return False
    if any(part in DEFAULT_EXCLUDED_DIRS for part in parts):
        return False
    rel_text = rel.as_posix()
    if exclude_patterns and any(fnmatch.fnmatch(rel_text, pattern) for pattern in exclude_patterns):
        return False
    return True


def file_allowed(
    root: Path,
    path: Path,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    hidden: bool,
) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    parts = rel.parts
    if not hidden and any(part.startswith(".") for part in parts):
        return False
    if any(part in DEFAULT_EXCLUDED_DIRS for part in parts[:-1]):
        return False
    rel_text = rel.as_posix()
    if include_patterns and not any(fnmatch.fnmatch(rel_text, pattern) for pattern in include_patterns):
        return False
    if exclude_patterns and any(fnmatch.fnmatch(rel_text, pattern) for pattern in exclude_patterns):
        return False
    return True
