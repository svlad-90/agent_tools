from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
from typing import Any
import uuid

from agent_tools.paf_workspace.task_check import check_task
from agent_tools.paf_workspace.task_check import render_text


TASK_CONTEXT_BUDGET = 8_000
TASKS_DIR_NAME = "tasks"
MARKDOWN_TABLE_WIDTH = 96
TASK_ACTIONS_FILE = "TASK_ACTIONS.json"
PAF_HIDE_TASK_ENV_VAR = "PAF_HIDE_TASK_ENV"
TASK_ACTION_LOGS_DIR = Path("report") / "logs"
AGENT_WORKSPACE_SETTINGS_FILE = "settings.json"
AGENT_WORKSPACE_TASK_STATE_FILE = ".agent-workspace-state.json"
AGENT_WORKSPACE_THEMES = ("light", "dark")
AGENT_WORKSPACE_LANGUAGES = ("ru", "uk", "en")
AGENT_WORKSPACE_AGENTS = ("codex", "claude")
AGENT_WORKSPACE_DEFAULT_AGENT = "codex"
AGENT_WORKSPACE_AGENT_LABELS = {
    "codex": "Codex",
    "claude": "Claude Code",
}
AGENT_WORKSPACE_AGENT_COMMANDS = {
    "codex": "codex",
    "claude": "claude",
}
AGENT_WORKSPACE_AGENT_INSTALL_COMMANDS = {
    "codex": "npm install -g @openai/codex",
    "claude": "npm install -g @anthropic-ai/claude-code",
}
CODEX_SESSION_ID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
AGENT_PERMISSION_MARKER = "⚠"
AGENT_WORKSPACE_GEOMETRY_RE = re.compile(r"^\d+x\d+(?:[+-]\d+[+-]\d+)?$")
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
ANSI_OSC_RE = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
AGENT_PERMISSION_PROMPT_RE = re.compile(
    r"(?:requires?\s+(?:approval|permission)|"
    r"(?:allow|approve|grant|proceed|continue)\?|" 
    r"(?:allow|approve|grant)\s+.*(?:\by\b|\byes\b|\bn\b|\bno\b)|"
    r"(?:permission|approval)\s+(?:required|needed|requested)|"
    r"would you like to run the following command\?|"
    r"do you want to (?:allow|approve|continue|proceed))",
    re.IGNORECASE,
)


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


@dataclass(frozen=True)
class ConsoleChunk:
    text: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class AgentSessionState:
    agent: str
    resume: bool = False
    session_id: str | None = None


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
    return render_text(task.path, checks, errors_only=True)


def agent_workspace_settings_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE
    return Path.home() / ".config" / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE


def normalize_agent(agent: object) -> str:
    if isinstance(agent, str) and agent in AGENT_WORKSPACE_AGENTS:
        return agent
    return AGENT_WORKSPACE_DEFAULT_AGENT


def agent_label(agent: str) -> str:
    return AGENT_WORKSPACE_AGENT_LABELS.get(normalize_agent(agent), normalize_agent(agent))


def agent_command_name(agent: str) -> str:
    agent = normalize_agent(agent)
    return AGENT_WORKSPACE_AGENT_COMMANDS.get(agent, agent)


def agent_executable(agent: str) -> str | None:
    command = agent_command_name(agent)
    executable = shutil.which(command)
    if executable:
        return executable
    local_bin = Path.home() / ".local" / "bin" / command
    if local_bin.is_file():
        return str(local_bin)
    return None


def agent_install_command(agent: str) -> str:
    agent = normalize_agent(agent)
    return AGENT_WORKSPACE_AGENT_INSTALL_COMMANDS.get(agent, "")


def agent_output_requests_permission(text: str) -> bool:
    normalized = ANSI_OSC_RE.sub("", text)
    normalized = ANSI_ESCAPE_RE.sub("", normalized)
    normalized = normalized.replace("\r", "\n")
    return AGENT_PERMISSION_PROMPT_RE.search(normalized[-4000:]) is not None


def task_state_path(task: TaskSummary) -> Path:
    return task.path / AGENT_WORKSPACE_TASK_STATE_FILE


def load_task_state(task: TaskSummary) -> dict[str, Any]:
    state_path = task_state_path(task)
    if not state_path.is_file():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_task_state(task: TaskSummary, data: dict[str, Any]) -> None:
    state_path = task_state_path(task)
    try:
        state_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return


def load_task_agent(task: TaskSummary, default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT) -> str:
    data = load_task_state(task)
    return normalize_agent(data.get("agent", default_agent))


def save_task_agent(task: TaskSummary, agent: str) -> None:
    data = load_task_state(task)
    data["agent"] = normalize_agent(agent)
    save_task_state(task, data)


def load_task_agent_session(task: TaskSummary, agent: str) -> AgentSessionState:
    agent = normalize_agent(agent)
    data = load_task_state(task)
    sessions = data.get("agent_sessions")
    if not isinstance(sessions, dict):
        return AgentSessionState(agent=agent)
    session = sessions.get(agent)
    if not isinstance(session, dict):
        return AgentSessionState(agent=agent)
    session_id = session.get("session_id")
    if not isinstance(session_id, str) or not CODEX_SESSION_ID_RE.fullmatch(session_id):
        session_id = None
    return AgentSessionState(
        agent=agent,
        resume=session.get("resume") is True,
        session_id=session_id,
    )


def save_task_agent_session(task: TaskSummary, agent: str, session_id: str | None = None) -> None:
    agent = normalize_agent(agent)
    data = load_task_state(task)
    data["agent"] = agent
    sessions = data.get("agent_sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    session: dict[str, Any] = {"resume": True}
    if isinstance(session_id, str) and CODEX_SESSION_ID_RE.fullmatch(session_id):
        session["session_id"] = session_id
    elif isinstance(sessions.get(agent), dict):
        old_session_id = sessions[agent].get("session_id")
        if isinstance(old_session_id, str) and CODEX_SESSION_ID_RE.fullmatch(old_session_id):
            session["session_id"] = old_session_id
    sessions[agent] = session
    data["agent_sessions"] = sessions
    save_task_state(task, data)


def new_agent_session_id() -> str:
    return str(uuid.uuid4())


def codex_session_id_exists(session_id: str, home: Path | None = None) -> bool:
    if not CODEX_SESSION_ID_RE.fullmatch(session_id):
        return False
    sessions_dir = (home or Path.home()) / ".codex" / "sessions"
    if not sessions_dir.is_dir():
        return False
    try:
        next(sessions_dir.rglob(f"*{session_id}.jsonl"))
    except (OSError, StopIteration):
        return False
    return True


def task_agent_session_id_is_valid(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    home: Path | None = None,
) -> bool:
    agent = normalize_agent(agent)
    session = load_task_agent_session(task, agent)
    if session.session_id is not None:
        if agent == "codex":
            return codex_session_id_exists(session.session_id, home=home)
        return True
    return agent == "codex" and session.resume and find_latest_codex_session_id(task, workspace, home=home) is not None


def task_has_valid_agent_session(task: TaskSummary, workspace: Path, home: Path | None = None) -> bool:
    return any(
        task_agent_session_id_is_valid(task, workspace, agent, home=home)
        for agent in AGENT_WORKSPACE_AGENTS
    )


def find_latest_codex_session_id(task: TaskSummary, workspace: Path, home: Path | None = None) -> str | None:
    sessions_dir = (home or Path.home()) / ".codex" / "sessions"
    if not sessions_dir.is_dir():
        return None
    needle = (
        f"We are working in workspace task `{task.name}`. "
        f"Workspace: {workspace}. "
        f"Task directory: {task.path}."
    )
    try:
        session_files = sorted(
            sessions_dir.rglob("*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for session_file in session_files:
        match = CODEX_SESSION_ID_RE.search(session_file.name)
        if match is None:
            continue
        try:
            with session_file.open("r", encoding="utf-8", errors="replace") as stream:
                head = stream.read(64_000)
        except OSError:
            continue
        if needle in head:
            return match.group(1)
    return None


def load_agent_workspace_settings(path: Path | None = None) -> dict[str, int | str]:
    settings_path = path or agent_workspace_settings_path()
    if not settings_path.is_file():
        return {}
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    settings: dict[str, int | str] = {}
    text_font_size = data.get("text_font_size", data.get("font_size"))
    button_font_size = data.get("button_font_size")
    theme = data.get("theme")
    language = data.get("language")
    geometry = data.get("geometry")
    default_agent = data.get("default_agent")
    if isinstance(text_font_size, int):
        settings["text_font_size"] = max(8, min(28, text_font_size))
    if isinstance(button_font_size, int):
        settings["button_font_size"] = max(8, min(28, button_font_size))
    if isinstance(theme, str) and theme in AGENT_WORKSPACE_THEMES:
        settings["theme"] = theme
    if isinstance(language, str) and language in AGENT_WORKSPACE_LANGUAGES:
        settings["language"] = language
    if isinstance(geometry, str) and AGENT_WORKSPACE_GEOMETRY_RE.fullmatch(geometry):
        settings["geometry"] = geometry
    if isinstance(default_agent, str) and default_agent in AGENT_WORKSPACE_AGENTS:
        settings["default_agent"] = default_agent
    return settings


def save_agent_workspace_settings(settings: dict[str, int | str], path: Path | None = None) -> None:
    settings_path = path or agent_workspace_settings_path()
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        return


def parse_console_output(text: str) -> list[ConsoleChunk]:
    text = ANSI_OSC_RE.sub("", text)
    text = text.replace("\r\n", "\n")
    chunks: list[ConsoleChunk] = []
    tags: tuple[str, ...] = ()
    offset = 0
    for match in ANSI_ESCAPE_RE.finditer(text):
        _append_console_chunk(chunks, text[offset : match.start()], tags)
        tags = _update_console_tags(match.group(0), tags)
        offset = match.end()
    _append_console_chunk(chunks, text[offset:], tags)
    return chunks


def _append_console_chunk(
    chunks: list[ConsoleChunk],
    text: str,
    tags: tuple[str, ...],
) -> None:
    cleaned = "".join(
        char
        for char in text
        if char in ("\b", "\n", "\r", "\t") or ord(char) >= 32
    )
    if cleaned:
        chunks.append(ConsoleChunk(cleaned, tags))


def _update_console_tags(sequence: str, current: tuple[str, ...]) -> tuple[str, ...]:
    if not sequence.startswith("\x1b[") or not sequence.endswith("m"):
        return current
    codes = [int(part) if part else 0 for part in sequence[2:-1].split(";")]
    tags = set(current)
    for code in codes:
        if code == 0:
            tags.clear()
        elif code == 1:
            tags.add("console_bold")
        elif code == 22:
            tags.discard("console_bold")
        elif code == 39:
            tags = {tag for tag in tags if not tag.startswith("console_fg_")}
        elif code in CONSOLE_FG_TAGS:
            tags = {tag for tag in tags if not tag.startswith("console_fg_")}
            tags.add(CONSOLE_FG_TAGS[code])
    return tuple(sorted(tags))


CONSOLE_FG_TAGS = {
    30: "console_fg_black",
    31: "console_fg_red",
    32: "console_fg_green",
    33: "console_fg_yellow",
    34: "console_fg_blue",
    35: "console_fg_magenta",
    36: "console_fg_cyan",
    37: "console_fg_white",
    90: "console_fg_bright_black",
    91: "console_fg_bright_red",
    92: "console_fg_bright_green",
    93: "console_fg_bright_yellow",
    94: "console_fg_bright_blue",
    95: "console_fg_bright_magenta",
    96: "console_fg_bright_cyan",
    97: "console_fg_bright_white",
}


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
    env[PAF_HIDE_TASK_ENV_VAR] = "1"
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


def task_action_log_basename(action_id: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", action_id).strip(".-")
    return safe_name or "task-action"


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


def _file_tokens(path: Path) -> int:
    return rough_token_count(path.read_text(encoding="utf-8", errors="replace"))
