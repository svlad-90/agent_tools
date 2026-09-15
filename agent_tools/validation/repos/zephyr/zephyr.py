"""Zephyr-specific repo_guard checks."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Iterable

from agent_tools.tools.repo_guard.git_context import run_git
from agent_tools.tools.repo_guard.models import CheckConfig
from agent_tools.tools.repo_guard.models import CheckResult
from agent_tools.tools.repo_guard.models import GuardContext


def zephyr_spdx_file_copyright(context: GuardContext, check: CheckConfig) -> CheckResult:
    start = time.monotonic()
    findings = sorted(set(_spdx_findings(context)))
    return CheckResult(
        check_id=check.check_id,
        status="fail" if findings else "pass",
        level=check.level,
        backend=check.backend,
        cost=check.cost,
        required=check.required,
        summary=(
            "added copyright lines use SPDX-FileCopyrightText"
            if not findings
            else "added copyright lines must use SPDX-FileCopyrightText"
        ),
        command=(),
        cwd=str(context.repo),
        stdout_tail="",
        stderr_tail="\n".join(findings),
        duration_sec=time.monotonic() - start,
        returncode=1 if findings else 0,
        suggested_command=check.suggested_command,
    )


def _spdx_findings(context: GuardContext) -> Iterable[str]:
    for commit in context.commits:
        yield from _spdx_findings_from_diff(
            run_git(
                ["show", "--format=", "--unified=0", "--no-ext-diff", commit],
                cwd=context.repo,
            ),
            source=commit[:12],
        )
    if context.mode == "validate":
        yield from _spdx_findings_from_diff(
            run_git(["diff", "--unified=0", "--no-ext-diff", "HEAD"], cwd=context.repo),
            source="worktree",
        )
        for path in context.changed_paths:
            absolute = context.repo / path
            if not absolute.is_file() or _is_git_tracked(context, path):
                continue
            yield from _spdx_findings_from_lines(
                path,
                absolute.read_text(encoding="utf-8", errors="ignore").splitlines(),
                source="untracked",
            )


def _spdx_findings_from_diff(diff: str, *, source: str) -> Iterable[str]:
    current_path: Path | None = None
    new_line = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_path = Path(line.removeprefix("+++ b/"))
            continue
        if line.startswith("@@ "):
            new_line = _new_line_from_hunk(line)
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_path is None:
            continue
        yield from _spdx_findings_from_lines(
            current_path,
            [line[1:]],
            source=source,
            start_line=new_line,
        )
        new_line += 1


def _new_line_from_hunk(header: str) -> int:
    marker = " +"
    start = header.find(marker)
    if start < 0:
        return 0
    field = header[start + len(marker) :].split(" ", 1)[0]
    value = field.split(",", 1)[0]
    try:
        return int(value)
    except ValueError:
        return 0


def _spdx_findings_from_lines(
    path: Path,
    lines: Iterable[str],
    *,
    source: str,
    start_line: int = 1,
) -> Iterable[str]:
    if not _spdx_path_is_relevant(path):
        return
    for offset, line in enumerate(lines):
        if "Copyright (c)" not in line:
            continue
        if "SPDX-FileCopyrightText:" in line:
            continue
        line_number = start_line + offset if start_line > 0 else 0
        location = f"{path.as_posix()}:{line_number}" if line_number else path.as_posix()
        yield (
            f"{source}:{location}: use "
            "`SPDX-FileCopyrightText: Copyright (c) ...` instead of a plain "
            "copyright comment"
        )


def _spdx_path_is_relevant(path: Path) -> bool:
    if any(part in {".git", "build", "twister-out"} for part in path.parts):
        return False
    if path.name in {"Kconfig", "CMakeLists.txt"}:
        return True
    return path.suffix in {
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".cxx",
        ".hpp",
        ".S",
        ".s",
        ".ld",
        ".dts",
        ".dtsi",
        ".overlay",
        ".conf",
        ".cmake",
        ".py",
        ".rst",
        ".yaml",
        ".yml",
    }


def _is_git_tracked(context: GuardContext, path: Path) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path.as_posix()],
        cwd=context.repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return completed.returncode == 0
