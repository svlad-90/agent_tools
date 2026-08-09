from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import textwrap
from typing import Any

from codex_tools.paf_workspace.task_check import check_task
from codex_tools.paf_workspace.task_check import render_text


TASK_CONTEXT_BUDGET = 8_000
TASKS_DIR_NAME = "tasks"
MARKDOWN_TABLE_WIDTH = 96
TASK_ACTIONS_FILE = "TASK_ACTIONS.json"
WORKSPACE_GUI_SETTINGS_FILE = "settings.json"


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


@dataclass(frozen=True)
class TaskAction:
    action_id: str
    label: str
    command: str | tuple[str, ...]
    cwd: Path
    env: dict[str, str]


def rough_token_count(text: str) -> int:
    lexical_tokens = len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
    char_tokens = (len(text) + 3) // 4
    return max(lexical_tokens, char_tokens)


def render_markdown_chunks(text: str) -> list[MarkdownChunk]:
    chunks: list[MarkdownChunk] = []
    in_code = False
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            index += 1
            continue
        if in_code:
            chunks.append(MarkdownChunk(line + "\n", "code"))
            index += 1
            continue
        if _is_table_line(stripped):
            table_lines = []
            while index < len(lines) and _is_table_line(lines[index].strip()):
                table_lines.append(lines[index].strip())
                index += 1
            chunks.extend(_render_table_block(table_lines))
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped[level:].strip()
            chunks.append(MarkdownChunk(title + "\n", f"h{min(level, 3)}"))
        elif _is_list_item(stripped):
            chunks.append(MarkdownChunk(_render_list_item(stripped) + "\n", "list"))
        elif stripped:
            chunks.append(MarkdownChunk(_strip_inline_code(line) + "\n", "paragraph"))
        else:
            chunks.append(MarkdownChunk("\n", "paragraph"))
        index += 1
    return chunks


def _is_list_item(stripped: str) -> bool:
    return stripped.startswith(("- ", "* ")) or re.match(r"\d+\.\s+", stripped) is not None


def _render_list_item(stripped: str) -> str:
    if stripped.startswith(("- ", "* ")):
        body = stripped[2:].strip()
    else:
        body = re.sub(r"^\d+\.\s+", "", stripped).strip()
    return "- " + _strip_inline_code(body)


def _strip_inline_code(text: str) -> str:
    return re.sub(r"`([^`]*)`", r"\1", text)


def _is_table_line(stripped: str) -> bool:
    return stripped.startswith("|") and stripped.endswith("|")


def _is_table_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _parse_table_row(line: str) -> list[str]:
    return [_strip_inline_code(cell.strip()) for cell in line.strip("|").split("|")]


def _render_table_block(lines: list[str]) -> list[MarkdownChunk]:
    rows = [_parse_table_row(line) for line in lines]
    if len(rows) < 2 or not _is_table_separator(rows[1]):
        return [MarkdownChunk(_strip_inline_code(line) + "\n", "table") for line in lines]

    headers = rows[0]
    chunks: list[MarkdownChunk] = []
    border = "+" + "-" * (MARKDOWN_TABLE_WIDTH - 2) + "+"
    for row_index, row in enumerate(rows[2:], start=1):
        lines = [border, _boxed_line(f"Row {row_index}")]
        for header, value in zip(headers, row):
            if not header and not value:
                continue
            label = f"{header}: " if header else ""
            wrapped = textwrap.wrap(
                label + value,
                width=MARKDOWN_TABLE_WIDTH - 4,
                subsequent_indent=" " * len(label),
            ) or [label.rstrip()]
            lines.extend(_boxed_line(part) for part in wrapped)
        lines.append(border)
        chunks.append(MarkdownChunk("\n".join(lines) + "\n\n", "table"))
    return chunks


def _boxed_line(text: str) -> str:
    width = MARKDOWN_TABLE_WIDTH - 4
    return f"| {text[:width].ljust(width)} |"


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


def workspace_gui_settings_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / "codex_tools" / "workspace_gui" / WORKSPACE_GUI_SETTINGS_FILE
    return Path.home() / ".config" / "codex_tools" / "workspace_gui" / WORKSPACE_GUI_SETTINGS_FILE


def load_workspace_gui_settings(path: Path | None = None) -> dict[str, int]:
    settings_path = path or workspace_gui_settings_path()
    if not settings_path.is_file():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    font_size = data.get("font_size")
    if isinstance(font_size, int):
        return {"font_size": max(8, min(28, font_size))}
    return {}


def save_workspace_gui_settings(settings: dict[str, int], path: Path | None = None) -> None:
    settings_path = path or workspace_gui_settings_path()
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return


def load_task_actions(task: TaskSummary) -> tuple[list[TaskAction], list[str]]:
    path = task.path / TASK_ACTIONS_FILE
    if not path.is_file():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [], [f"{TASK_ACTIONS_FILE}: {error}"]

    entries = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return [], [f"{TASK_ACTIONS_FILE}: expected object with actions list"]

    actions: list[TaskAction] = []
    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        action, error = _parse_task_action(task, entry, index)
        if error is not None:
            errors.append(error)
            continue
        if action.action_id in seen:
            errors.append(f"{TASK_ACTIONS_FILE}: duplicate action id {action.action_id!r}")
            continue
        seen.add(action.action_id)
        actions.append(action)
    return actions, errors


def run_task_action(action: TaskAction) -> str:
    env = os.environ.copy()
    env.update(action.env)
    command = list(action.command) if isinstance(action.command, tuple) else action.command
    completed = subprocess.run(
        command,
        cwd=action.cwd,
        env=env,
        shell=isinstance(action.command, str),
        check=False,
        text=True,
        capture_output=True,
    )
    output = completed.stdout
    if completed.stderr:
        output += completed.stderr
    output += f"\nexit code: {completed.returncode}\n"
    return output


def _parse_task_action(
    task: TaskSummary,
    entry: object,
    index: int,
) -> tuple[TaskAction, None] | tuple[None, str]:
    if not isinstance(entry, dict):
        return None, f"{TASK_ACTIONS_FILE}: action {index} must be an object"

    action_id = _string_field(entry, "id")
    label = _string_field(entry, "label")
    command = _command_field(entry.get("command"))
    if action_id is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing string id"
    if label is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing string label"
    if command is None:
        return None, f"{TASK_ACTIONS_FILE}: action {index} missing command"

    cwd_text = _string_field(entry, "cwd") or "."
    cwd = (task.path / cwd_text).resolve()
    try:
        cwd.relative_to(task.path.resolve())
    except ValueError:
        return None, f"{TASK_ACTIONS_FILE}: action {action_id!r} cwd escapes task"

    env_data = entry.get("env", {})
    if not isinstance(env_data, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in env_data.items()
    ):
        return None, f"{TASK_ACTIONS_FILE}: action {action_id!r} env must be string map"

    return TaskAction(
        action_id=action_id,
        label=label,
        command=command,
        cwd=cwd,
        env=dict(env_data),
    ), None


def _string_field(entry: dict[str, Any], name: str) -> str | None:
    value = entry.get(name)
    return value if isinstance(value, str) and value else None


def _command_field(value: object) -> str | tuple[str, ...] | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return tuple(value)
    return None


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
