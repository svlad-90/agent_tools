from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from codex_tools.paf_workspace.task_check import check_task
from codex_tools.paf_workspace.task_check import render_text


TASK_CONTEXT_BUDGET = 8_000
TASKS_DIR_NAME = "tasks"


@dataclass(frozen=True)
class TaskSummary:
    name: str
    path: Path
    has_description: bool
    has_context: bool
    description_tokens: int
    context_tokens: int
    context_over_budget: bool


@dataclass(frozen=True)
class GitRepoStatus:
    path: Path
    branch_line: str
    changes: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class MarkdownChunk:
    text: str
    tag: str


def rough_token_count(text: str) -> int:
    lexical_tokens = len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
    char_tokens = (len(text) + 3) // 4
    return max(lexical_tokens, char_tokens)


def render_markdown_chunks(text: str) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            chunks.append(MarkdownChunk(line + "\n", "code"))
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            chunks.append(MarkdownChunk(title + "\n", f"h{min(level, 3)}"))
        elif stripped.startswith(("- ", "* ")):
            chunks.append(MarkdownChunk("  * " + stripped[2:].strip() + "\n", "list"))
        elif stripped.startswith("|") and stripped.endswith("|"):
            chunks.append(MarkdownChunk(line + "\n", "table"))
        elif stripped:
            chunks.append(MarkdownChunk(line + "\n", "paragraph"))
        else:
            chunks.append(MarkdownChunk("\n", "paragraph"))
    return chunks


def discover_tasks(workspace: Path) -> list[TaskSummary]:
    workspace = workspace.resolve()
    tasks = []
    for path in sorted(
        _candidate_task_dirs(workspace),
        key=lambda candidate: candidate.name.casefold(),
    ):
        description_path = path / "TASK_DESCRIPTION.md"
        context_path = path / "TASK_CONTEXT.md"
        has_description = description_path.is_file()
        has_context = context_path.is_file()
        if not has_description and not has_context:
            continue
        description_tokens = _file_tokens(description_path) if has_description else 0
        context_tokens = _file_tokens(context_path) if has_context else 0
        tasks.append(
            TaskSummary(
                name=path.name,
                path=path,
                has_description=has_description,
                has_context=has_context,
                description_tokens=description_tokens,
                context_tokens=context_tokens,
                context_over_budget=context_tokens > TASK_CONTEXT_BUDGET,
            )
        )
    return tasks


def _candidate_task_dirs(workspace: Path) -> list[Path]:
    tasks_root = workspace / TASKS_DIR_NAME
    if not tasks_root.is_dir():
        return []
    return [
        path
        for path in tasks_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]


def read_task_file(task: TaskSummary, filename: str) -> str:
    path = task.path / filename
    if not path.is_file():
        return f"{filename} is missing.\n"
    return path.read_text(encoding="utf-8", errors="replace")


def run_task_check(task: TaskSummary, workspace: Path) -> str:
    checks = check_task(task.path, workspace=workspace.resolve())
    return render_text(task.path, checks)


def find_dev_git_repos(task: TaskSummary) -> list[Path]:
    dev_dir = task.path / "dev"
    if not dev_dir.is_dir():
        return []
    repos = []
    for git_dir in sorted(dev_dir.rglob(".git")):
        if git_dir.is_dir() or git_dir.is_file():
            repos.append(git_dir.parent)
    return repos


def git_status(repo: Path) -> GitRepoStatus:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "status", "--short", "--branch"],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as error:
        return GitRepoStatus(path=repo, branch_line="", changes=(), error=str(error))

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        return GitRepoStatus(path=repo, branch_line="", changes=(), error=message)

    lines = completed.stdout.splitlines()
    branch_line = lines[0] if lines else ""
    return GitRepoStatus(path=repo, branch_line=branch_line, changes=tuple(lines[1:]))


def _file_tokens(path: Path) -> int:
    return rough_token_count(path.read_text(encoding="utf-8", errors="replace"))
