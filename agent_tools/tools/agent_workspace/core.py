from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import faulthandler
import fcntl
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import traceback
from typing import Any
import uuid

from agent_tools.paf_workspace.task_check import check_task
from agent_tools.paf_workspace.task_check import render_text

from .workspace_strings import AGENT_STATUS_MANUAL_ENTRIES
from .workspace_strings import AGENT_STATUS_MANUAL_MENU_LABEL
from .workspace_strings import AGENT_STATUS_MANUAL_SUBTITLE
from .workspace_strings import AGENT_STATUS_MANUAL_TITLE
from .workspace_strings import AGENT_STATUS_MANUAL_USAGE_ENTRIES
from .workspace_strings import AGENT_STATUS_MANUAL_USAGE_TITLE
from .workspace_strings import AGENT_STATUS_RUNNING_LABEL
from .workspace_strings import AGENT_STATUS_TOOLTIPS


TASK_CONTEXT_BUDGET = 8_000
TASKS_DIR_NAME = "tasks"
MARKDOWN_TABLE_WIDTH = 96
TASK_ACTIONS_FILE = "TASK_ACTIONS.json"
PAF_HIDE_TASK_ENV_VAR = "PAF_HIDE_TASK_ENV"
TASK_ACTION_LOGS_DIR = Path("report") / "logs"
AGENT_WORKSPACE_SETTINGS_FILE = "settings.json"
AGENT_WORKSPACE_TASK_STATE_FILE = ".agent-workspace-state.json"
AGENT_WORKSPACE_CRASH_LOG_FILE = "agent-workspace-crash.log"
AGENT_WORKSPACE_LOCK_FILE = ".agent-workspace.lock"
AGENT_WORKSPACE_THEMES = ("light", "dark")
AGENT_WORKSPACE_LANGUAGES = ("ru", "uk", "en")
AGENT_WORKSPACE_AGENTS = ("codex", "claude")
AGENT_WORKSPACE_DEFAULT_AGENT = "codex"
AGENT_WORKSPACE_DEFAULT_CODEX_MODEL = "gpt-5.5"
AGENT_WORKSPACE_DEFAULT_CODEX_REASONING = "medium"
AGENT_WORKSPACE_DEFAULT_CLAUDE_MODEL = "sonnet"
AGENT_WORKSPACE_DEFAULT_CLAUDE_EFFORT = "medium"
AGENT_WORKSPACE_DEFAULT_CLAUDE_PERMISSION_MODE = "auto"
AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS = (
    "",
    "gpt-5.6-sol",
    "gpt-5.6-sol-wm",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.3-codex-spark",
)
AGENT_WORKSPACE_CLAUDE_MODELS = ("", "sonnet", "opus", "fable")
AGENT_WORKSPACE_REASONING_EFFORTS = ("", "low", "medium", "high", "xhigh", "max")
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
AGENT_SESSION_MARKER = "Ⅱ"
AGENT_IDLE_MARKER = "□"
AGENT_EXTERNAL_ACTIVE_MARKER = "×"
AGENT_RUNNING_SPINNER_FRAMES = ("▷",)
CODEX_SESSION_ID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
AGENT_WORKSPACE_GEOMETRY_RE = re.compile(r"^\d+x\d+(?:[+-]\d+[+-]\d+)?$")
ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
ANSI_OSC_RE = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
AGENT_MISSING_SESSION_RE = re.compile(
    r"no\s+conversation\s+found\s+with\s+session\s+id",
    re.IGNORECASE,
)
AGENT_TURN_COMPLETE_RE = re.compile(
    r"(?:^|\n)\s*(?:"
    r"(?:tokens?\s+used|total\s+tokens?|cost|duration):\s*[\w$.,: -]+|"
    r"(?:done|completed|task\s+complete|ready\s+for\s+(?:the\s+)?next\s+(?:task|prompt))\.?"
    r")\s*(?:$|\n)",
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
class TaskActionParameter:
    name: str
    label: str
    parameter_type: str
    set_name: str
    default: str
    global_name: str | None = None


@dataclass(frozen=True)
class TaskAction:
    action_id: str
    label: str
    command: str | tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    parameters: tuple[TaskActionParameter, ...] = ()
    bindings: dict[str, str] | None = None
    base_action_id: str | None = None
    is_shortcut: bool = False


@dataclass(frozen=True)
class TaskActionsConfig:
    actions: list[TaskAction]
    base_actions: list[TaskAction]
    parameter_sets: dict[str, dict[str, dict[str, str]]]
    global_parameter_bindings: dict[str, str]
    errors: list[str]


@dataclass(frozen=True)
class ConsoleChunk:
    text: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class AgentSessionState:
    agent: str
    resume: bool = False
    session_id: str | None = None


@dataclass(frozen=True)
class AgentWorkspaceRuntimeSettings:
    text_font_size: int
    button_font_size: int
    theme: str
    language: str
    default_agent: str
    default_codex_model: str
    default_codex_reasoning: str
    default_claude_model: str
    default_claude_effort: str
    window_geometry: str


@dataclass(frozen=True)
class AgentModelSettings:
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class AgentLaunchCommand:
    command: list[str]
    session_state: AgentSessionState
    model_settings: AgentModelSettings


@dataclass(frozen=True)
class AgentLaunchState:
    label_key: str
    reset_enabled: bool


@dataclass(frozen=True)
class AgentSwitchDecision:
    action: str
    agent: str
    current_agent: str | None = None


@dataclass(frozen=True)
class AgentOutputAnalysis:
    missing_session: bool
    requests_permission: bool
    turn_complete: bool
    permission_signature: str | None


@dataclass(frozen=True)
class AgentOutputStateUpdate:
    missing_session: bool
    permission_requested: bool
    exited: bool
    permission_pending: bool


@dataclass(frozen=True)
class ActiveTaskAgentRun:
    agent: str
    owner_pid: int
    run_id: str


_CRASH_LOG_HANDLE: Any | None = None
_PREVIOUS_EXCEPTHOOK: Any | None = None
_PREVIOUS_THREADING_EXCEPTHOOK: Any | None = None


def agent_workspace_crash_log_path(workspace: Path) -> Path:
    return workspace.resolve() / AGENT_WORKSPACE_CRASH_LOG_FILE


def agent_workspace_lock_path(workspace: Path) -> Path:
    return workspace.resolve() / AGENT_WORKSPACE_LOCK_FILE


def acquire_agent_workspace_lock(workspace: Path) -> io.TextIOWrapper | None:
    lock_path = agent_workspace_lock_path(workspace)
    try:
        handle = lock_path.open("w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        return handle
    except BlockingIOError:
        return None
    except OSError:
        return None


def log_agent_workspace_exception(
    workspace: Path,
    frontend: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: Any,
) -> None:
    log_path = agent_workspace_crash_log_path(workspace)
    try:
        with log_path.open("a", encoding="utf-8") as stream:
            timestamp = datetime.now().isoformat(timespec="seconds")
            stream.write(f"\n[{timestamp}] Agent Workspace {frontend} exception pid={os.getpid()}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=stream)
            stream.flush()
    except OSError:
        return


def install_agent_workspace_exception_logger(workspace: Path, frontend: str) -> Path:
    global _CRASH_LOG_HANDLE
    global _PREVIOUS_EXCEPTHOOK
    global _PREVIOUS_THREADING_EXCEPTHOOK

    workspace = workspace.resolve()
    log_path = agent_workspace_crash_log_path(workspace)
    try:
        _CRASH_LOG_HANDLE = log_path.open("a", encoding="utf-8")
        timestamp = datetime.now().isoformat(timespec="seconds")
        _CRASH_LOG_HANDLE.write(f"\n[{timestamp}] Agent Workspace {frontend} started pid={os.getpid()}\n")
        _CRASH_LOG_HANDLE.flush()
        faulthandler.enable(file=_CRASH_LOG_HANDLE, all_threads=True)
    except OSError:
        _CRASH_LOG_HANDLE = None

    if _PREVIOUS_EXCEPTHOOK is None:
        _PREVIOUS_EXCEPTHOOK = sys.excepthook
    if _PREVIOUS_THREADING_EXCEPTHOOK is None and hasattr(threading, "excepthook"):
        _PREVIOUS_THREADING_EXCEPTHOOK = threading.excepthook

    def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        log_agent_workspace_exception(workspace, frontend, exc_type, exc_value, exc_traceback)
        if _PREVIOUS_EXCEPTHOOK is not None:
            _PREVIOUS_EXCEPTHOOK(exc_type, exc_value, exc_traceback)

    def threading_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is not None and args.exc_value is not None:
            log_agent_workspace_exception(workspace, frontend, args.exc_type, args.exc_value, args.exc_traceback)
        if _PREVIOUS_THREADING_EXCEPTHOOK is not None:
            _PREVIOUS_THREADING_EXCEPTHOOK(args)

    sys.excepthook = excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = threading_excepthook
    return log_path


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


def codex_model_choices(cache_path: Path | None = None) -> tuple[str, ...]:
    path = cache_path or (Path.home() / ".codex" / "models_cache.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS
    models = data.get("models")
    if not isinstance(models, list):
        return AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS
    choices = [""]
    for model in models:
        if not isinstance(model, dict):
            continue
        slug = model.get("slug")
        if isinstance(slug, str) and slug and slug not in choices:
            choices.append(slug)
    if len(choices) == 1:
        return AGENT_WORKSPACE_CODEX_MODEL_FALLBACKS
    return tuple(choices)


def model_choices_with_current(choices: tuple[str, ...], current: str) -> tuple[str, ...]:
    current = current.strip()
    if current and current not in choices:
        return (*choices, current)
    return choices


def append_ai_agent_model_options(
    command: list[str],
    agent: str,
    *,
    model: str = "",
    reasoning_effort: str = "",
) -> None:
    model = model.strip()
    reasoning_effort = reasoning_effort.strip()
    if model:
        command.extend(["--model", model])
    if not reasoning_effort:
        return
    if normalize_agent(agent) == "claude":
        command.extend(["--effort", reasoning_effort])
    else:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])


def append_ai_agent_permission_options(command: list[str], agent: str) -> None:
    if normalize_agent(agent) == "claude":
        command.extend(["--permission-mode", AGENT_WORKSPACE_DEFAULT_CLAUDE_PERMISSION_MODE])


def build_ai_agent_console_command(
    workspace: Path,
    prompt: str,
    agent: str,
    *,
    codex_executable: str,
    claude_executable: str,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
) -> list[str]:
    agent = normalize_agent(agent)
    if agent == "claude":
        command = [claude_executable]
        append_ai_agent_permission_options(command, agent)
        append_ai_agent_model_options(command, agent, model=model, reasoning_effort=reasoning_effort)
        if resume and resume_session_id:
            command.extend(["--resume", resume_session_id])
        else:
            if resume_session_id:
                command.extend(["--session-id", resume_session_id])
            command.append(prompt)
        return command

    command = [codex_executable]
    append_ai_agent_model_options(command, agent, model=model, reasoning_effort=reasoning_effort)
    if resume:
        command.extend(["resume", "--cd", str(workspace), "--no-alt-screen"])
        command.append(resume_session_id or "--last")
        return command
    command.extend(["--cd", str(workspace), "--no-alt-screen", prompt])
    return command


def ai_agent_task_context_prompt(task: TaskSummary, workspace: Path, suffix: str = "") -> str:
    message = (
        f"We are working in workspace task `{task.name}`. "
        f"Workspace: {workspace}. "
        f"Task directory: {task.path}. "
        "Before changing files, read that task's TASK_DESCRIPTION.md and "
        "TASK_CONTEXT.md and treat them as the active task context."
    )
    if suffix:
        return f"{message} {suffix}"
    return message


def prepare_ai_agent_launch_command(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    *,
    codex_model: str,
    codex_reasoning: str,
    claude_model: str,
    claude_effort: str,
    codex_executable: str,
    claude_executable: str,
    prompt_suffix: str = "",
) -> AgentLaunchCommand:
    agent = normalize_agent(agent)
    session_state = prepare_task_agent_session(task, workspace, agent)
    model_settings = ai_agent_model_settings(
        agent,
        codex_model=codex_model,
        codex_reasoning=codex_reasoning,
        claude_model=claude_model,
        claude_effort=claude_effort,
    )
    prompt = ai_agent_task_context_prompt(task, workspace, prompt_suffix)
    return AgentLaunchCommand(
        command=build_ai_agent_console_command(
            workspace,
            prompt,
            agent,
            codex_executable=codex_executable,
            claude_executable=claude_executable,
            resume=session_state.resume,
            resume_session_id=session_state.session_id,
            model=model_settings.model,
            reasoning_effort=model_settings.reasoning_effort,
        ),
        session_state=session_state,
        model_settings=model_settings,
    )


def agent_workspace_setting_or_default(settings: dict[str, int | str], key: str, default: str) -> str:
    value = settings.get(key)
    if not isinstance(value, str):
        return default
    value = value.strip()
    return value or default


def agent_workspace_runtime_settings(
    settings: dict[str, int | str],
    *,
    default_font_size: int,
    default_language: str = "ru",
    default_geometry: str = "1180x760",
) -> AgentWorkspaceRuntimeSettings:
    return AgentWorkspaceRuntimeSettings(
        text_font_size=_int_setting(settings, "text_font_size", default_font_size),
        button_font_size=_int_setting(settings, "button_font_size", default_font_size),
        theme=_choice_setting(settings, "theme", AGENT_WORKSPACE_THEMES, "light"),
        language=_choice_setting(settings, "language", AGENT_WORKSPACE_LANGUAGES, default_language),
        default_agent=normalize_agent(settings.get("default_agent", AGENT_WORKSPACE_DEFAULT_AGENT)),
        default_codex_model=agent_workspace_setting_or_default(
            settings, "default_codex_model", AGENT_WORKSPACE_DEFAULT_CODEX_MODEL
        ),
        default_codex_reasoning=agent_workspace_setting_or_default(
            settings, "default_codex_reasoning", AGENT_WORKSPACE_DEFAULT_CODEX_REASONING
        ),
        default_claude_model=agent_workspace_setting_or_default(
            settings, "default_claude_model", AGENT_WORKSPACE_DEFAULT_CLAUDE_MODEL
        ),
        default_claude_effort=agent_workspace_setting_or_default(
            settings, "default_claude_effort", AGENT_WORKSPACE_DEFAULT_CLAUDE_EFFORT
        ),
        window_geometry=_str_setting(settings, "geometry", default_geometry),
    )


def ai_agent_model_settings(
    agent: str,
    *,
    codex_model: str,
    codex_reasoning: str,
    claude_model: str,
    claude_effort: str,
) -> AgentModelSettings:
    if normalize_agent(agent) == "claude":
        return AgentModelSettings(
            model=claude_model,
            reasoning_effort=claude_effort,
        )
    return AgentModelSettings(
        model=codex_model,
        reasoning_effort=codex_reasoning,
    )


def ai_agent_launch_state(*, running: bool, resumable: bool) -> AgentLaunchState:
    if running:
        return AgentLaunchState(label_key="ai_agent_running", reset_enabled=True)
    if resumable:
        return AgentLaunchState(label_key="restore_ai_agent_session", reset_enabled=True)
    return AgentLaunchState(label_key="run_ai_agent", reset_enabled=False)


def ai_agent_launch_state_for_selection(
    task: TaskSummary | None,
    workspace: Path,
    agent: str,
    *,
    running_agent: str | None,
) -> AgentLaunchState:
    if task is None:
        return ai_agent_launch_state(running=False, resumable=False)
    agent = normalize_agent(agent)
    running = running_agent == agent
    resumable = task_agent_has_resumable_state(task, workspace, agent)
    return ai_agent_launch_state(running=running, resumable=resumable)


def ai_agent_switch_decision(
    agent: str,
    *,
    current_agent: str | None,
    start_if_changed: bool,
) -> AgentSwitchDecision:
    agent = normalize_agent(agent)
    if current_agent is None:
        return AgentSwitchDecision(action="start_selected", agent=agent)
    current_agent = normalize_agent(current_agent)
    if current_agent == agent:
        return AgentSwitchDecision(
            action="activate_current",
            agent=agent,
            current_agent=current_agent,
        )
    if not start_if_changed:
        return AgentSwitchDecision(
            action="keep_current",
            agent=current_agent,
            current_agent=current_agent,
        )
    return AgentSwitchDecision(
        action="confirm_switch",
        agent=agent,
        current_agent=current_agent,
    )


def session_is_agent(*, session_kind: str) -> bool:
    return session_kind in AGENT_WORKSPACE_AGENTS


def session_is_running_agent(*, session_kind: str, exited: bool) -> bool:
    return session_is_agent(session_kind=session_kind) and not exited


def session_should_clear_pending_permission(
    *,
    session_kind: str,
    permission_pending: bool,
) -> bool:
    return session_is_agent(session_kind=session_kind) and permission_pending


def session_marks_task_running_agent(
    *,
    session_kind: str,
    session_task_path: Path,
    exited: bool,
    task_path: Path,
) -> bool:
    return (
        session_is_running_agent(session_kind=session_kind, exited=exited)
        and session_task_path == task_path
    )


def session_marks_task_pending_permission(
    *,
    session_kind: str,
    session_task_path: Path,
    permission_pending: bool,
    exited: bool,
    task_path: Path,
) -> bool:
    return (
        session_marks_task_running_agent(
            session_kind=session_kind,
            session_task_path=session_task_path,
            exited=exited,
            task_path=task_path,
        )
        and permission_pending
    )


def _int_setting(settings: dict[str, int | str], key: str, default: int) -> int:
    value = settings.get(key)
    if isinstance(value, int):
        return value
    return default


def _choice_setting(
    settings: dict[str, int | str],
    key: str,
    choices: tuple[str, ...],
    default: str,
) -> str:
    value = settings.get(key)
    if isinstance(value, str) and value in choices:
        return value
    return default


def _str_setting(settings: dict[str, int | str], key: str, default: str) -> str:
    value = settings.get(key)
    if isinstance(value, str):
        return value
    return default


def _normalized_agent_output_tail(text: str) -> str:
    normalized = ANSI_OSC_RE.sub("", text)
    normalized = ANSI_ESCAPE_RE.sub("", normalized)
    normalized = normalized.replace("\r", "\n")
    return normalized[-8000:]


def agent_permission_prompt_signature(text: str) -> str | None:
    _ = text
    return None


def _line_looks_like_agent_permission_prompt(line: str) -> bool:
    _ = line
    return False


def analyze_agent_output(text: str) -> AgentOutputAnalysis:
    tail = _normalized_agent_output_tail(text)
    return AgentOutputAnalysis(
        missing_session=AGENT_MISSING_SESSION_RE.search(tail) is not None,
        requests_permission=False,
        turn_complete=AGENT_TURN_COMPLETE_RE.search(tail) is not None,
        permission_signature=None,
    )


def agent_output_requests_permission(text: str) -> bool:
    return analyze_agent_output(text).requests_permission


def agent_output_reports_missing_session(text: str) -> bool:
    return analyze_agent_output(text).missing_session


def agent_output_reports_turn_complete(text: str) -> bool:
    return analyze_agent_output(text).turn_complete


def agent_output_state_update(
    text: str,
    *,
    exited: bool,
    permission_pending: bool,
) -> AgentOutputStateUpdate:
    analysis = analyze_agent_output(text)
    if analysis.missing_session:
        return AgentOutputStateUpdate(
            missing_session=True,
            permission_requested=False,
            exited=True,
            permission_pending=False,
        )
    if exited or permission_pending:
        return AgentOutputStateUpdate(
            missing_session=False,
            permission_requested=False,
            exited=exited,
            permission_pending=permission_pending,
        )
    return AgentOutputStateUpdate(
        missing_session=False,
        permission_requested=False,
        exited=exited,
        permission_pending=permission_pending,
    )


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


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _process_cmdline(pid: int) -> list[str]:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [part.decode(errors="ignore") for part in raw.split(b"\0") if part]


def _process_is_agent_workspace_owner(pid: int) -> bool:
    cmdline = _process_cmdline(pid)
    if not cmdline:
        return False
    joined = " ".join(cmdline)
    return any(
        Path(part).name == "agent-workspace"
        or "agent-workspace" in part
        or "agent_tools.tools.agent_workspace" in part
        or "/agent_workspace/" in part
        for part in cmdline
    ) or "agent_tools.tools.agent_workspace" in joined


def _process_start_time_ticks(pid: int) -> int | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        after_name = stat.rsplit(") ", 1)[1]
        return int(after_name.split()[19])
    except (IndexError, ValueError):
        return None


def _process_start_time_epoch(pid: int) -> float | None:
    start_ticks = _process_start_time_ticks(pid)
    if start_ticks is None:
        return None
    try:
        uptime = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
        ticks_per_second = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    except (OSError, IndexError, KeyError, ValueError):
        return None
    boot_epoch = time.time() - uptime
    return boot_epoch + (start_ticks / ticks_per_second)


def _current_boot_id() -> str | None:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _active_agent_owner_is_current(task: TaskSummary, active: dict[str, Any], owner_pid: int) -> bool:
    if not process_is_alive(owner_pid):
        return False
    if not _process_is_agent_workspace_owner(owner_pid):
        return False
    owner_boot_id = active.get("owner_boot_id")
    current_boot_id = _current_boot_id()
    if isinstance(owner_boot_id, str) and current_boot_id is not None and owner_boot_id != current_boot_id:
        return False
    owner_start_time = active.get("owner_start_time")
    current_start_time = _process_start_time_ticks(owner_pid)
    if (
        isinstance(owner_start_time, int)
        and current_start_time is not None
        and owner_start_time != current_start_time
    ):
        return False
    process_start_epoch = _process_start_time_epoch(owner_pid)
    if process_start_epoch is not None:
        try:
            marker_mtime = task_state_path(task).stat().st_mtime
        except OSError:
            marker_mtime = None
        if marker_mtime is not None and marker_mtime + 1 < process_start_epoch:
            return False
    return True


def load_task_active_agent_run(task: TaskSummary) -> ActiveTaskAgentRun | None:
    data = load_task_state(task)
    active = data.get("active_agent_run")
    if not isinstance(active, dict):
        return None
    agent = active.get("agent")
    owner_pid = active.get("owner_pid")
    run_id = active.get("run_id")
    if not isinstance(agent, str) or not isinstance(owner_pid, int) or not isinstance(run_id, str):
        data.pop("active_agent_run", None)
        save_task_state(task, data)
        return None
    agent = normalize_agent(agent)
    if not _active_agent_owner_is_current(task, active, owner_pid):
        data.pop("active_agent_run", None)
        save_task_state(task, data)
        return None
    return ActiveTaskAgentRun(agent=agent, owner_pid=owner_pid, run_id=run_id)


def save_task_active_agent_run(
    task: TaskSummary,
    agent: str,
    run_id: str,
    owner_pid: int | None = None,
) -> None:
    data = load_task_state(task)
    owner_pid = os.getpid() if owner_pid is None else owner_pid
    active: dict[str, object] = {
        "agent": normalize_agent(agent),
        "owner_pid": owner_pid,
        "run_id": run_id,
    }
    owner_boot_id = _current_boot_id()
    if owner_boot_id is not None:
        active["owner_boot_id"] = owner_boot_id
    owner_start_time = _process_start_time_ticks(owner_pid)
    if owner_start_time is not None:
        active["owner_start_time"] = owner_start_time
    data["active_agent_run"] = active
    save_task_state(task, data)


def clear_task_active_agent_run(
    task: TaskSummary,
    *,
    run_id: str | None = None,
    agent: str | None = None,
) -> bool:
    data = load_task_state(task)
    active = data.get("active_agent_run")
    if not isinstance(active, dict):
        return False
    if run_id is not None and active.get("run_id") != run_id:
        return False
    if agent is not None:
        active_agent = active.get("agent")
        if not isinstance(active_agent, str) or normalize_agent(active_agent) != normalize_agent(agent):
            return False
    data.pop("active_agent_run", None)
    save_task_state(task, data)
    return True


def task_has_external_active_agent_run(
    task: TaskSummary,
    local_run_ids: set[str] | frozenset[str],
) -> bool:
    active = load_task_active_agent_run(task)
    return active is not None and active.run_id not in local_run_ids


def task_for_path(tasks: list[TaskSummary], path: Path) -> TaskSummary:
    for task in tasks:
        if task.path == path:
            return task
    return TaskSummary(
        name=path.name,
        path=path,
        has_description=False,
        has_context=False,
        description_tokens=0,
        context_tokens=0,
        context_over_budget=False,
    )


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
    data["agent_sessions"] = {agent: session}
    save_task_state(task, data)


def prepare_task_agent_session(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    home: Path | None = None,
) -> AgentSessionState:
    agent = normalize_agent(agent)
    session_state = load_task_agent_session(task, agent)
    session_id = find_task_agent_session_id(task, workspace, agent, home=home)
    save_task_agent_session(task, agent, session_id=session_id)
    return AgentSessionState(
        agent=agent,
        resume=session_state.resume,
        session_id=session_id,
    )


def clear_task_agent_session(task: TaskSummary, agent: str) -> bool:
    agent = normalize_agent(agent)
    data = load_task_state(task)
    sessions = data.get("agent_sessions")
    if not isinstance(sessions, dict) or agent not in sessions:
        return False
    sessions.pop(agent, None)
    if sessions:
        data["agent_sessions"] = sessions
    else:
        data.pop("agent_sessions", None)
    save_task_state(task, data)
    return True


def reset_task_agent_session(task: TaskSummary, agent: str) -> bool:
    agent = normalize_agent(agent)
    cleared = clear_task_agent_session(task, agent)
    cleared = clear_task_active_agent_run(task, agent=agent) or cleared
    save_task_agent(task, agent)
    return cleared


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
    return find_task_agent_session_id(task, workspace, agent, home=home) is not None


def task_agent_has_resumable_state(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    home: Path | None = None,
) -> bool:
    return find_task_agent_session_id(task, workspace, agent, home=home) is not None


def task_selected_agent_has_resumable_state(
    task: TaskSummary,
    workspace: Path,
    default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT,
    home: Path | None = None,
) -> bool:
    agent = load_task_agent(task, default_agent)
    return task_agent_has_resumable_state(task, workspace, agent, home=home)


def task_agent_selection_with_resumable_fallback(
    task: TaskSummary,
    workspace: Path,
    default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT,
    home: Path | None = None,
) -> str:
    agent = load_task_agent(task, default_agent)
    if task_agent_has_resumable_state(task, workspace, agent, home=home):
        return agent
    for candidate in AGENT_WORKSPACE_AGENTS:
        if task_agent_has_resumable_state(task, workspace, candidate, home=home):
            return candidate
    return agent


def task_agent_session_markers(
    task: TaskSummary,
    workspace: Path,
    home: Path | None = None,
) -> tuple[str, ...]:
    agent = load_task_agent(task)
    if task_agent_has_resumable_state(task, workspace, agent, home=home):
        return (AGENT_SESSION_MARKER,)
    return ()


def task_status_label(
    task_name: str,
    *,
    permission_pending: bool,
    session_markers: tuple[str, ...] = (),
) -> str:
    _ = permission_pending
    markers: list[str] = []
    markers.extend(session_markers)
    if not markers:
        return task_name
    return f"{' '.join(markers)} {task_name}"


def task_agent_status_text(
    task: TaskSummary,
    workspace: Path,
    *,
    permission_pending: bool,
    running_agents: tuple[str, ...] = (),
    external_active: bool = False,
    spinner_frame: str = "",
    session_markers: tuple[str, ...] | None = None,
    home: Path | None = None,
) -> str:
    _ = permission_pending
    _ = spinner_frame
    parts: list[str] = []
    if external_active:
        return AGENT_EXTERNAL_ACTIVE_MARKER
    if running_agents:
        return "▷"
    markers = list(
        session_markers
        if session_markers is not None
        else task_agent_session_markers(task, workspace, home=home)
    )
    parts.extend(markers)
    return " ".join(parts) if parts else AGENT_IDLE_MARKER


def agent_status_tooltip_text(status_text: str) -> str:
    status_text = status_text.strip()
    if not status_text:
        return ""
    labels: list[str] = []
    for marker in status_text.split():
        if marker.startswith("▷"):
            label = AGENT_STATUS_RUNNING_LABEL
        else:
            label = AGENT_STATUS_TOOLTIPS.get(marker, "")
        if label and label not in labels:
            labels.append(label)
    return "; ".join(labels)


def find_task_agent_session_id(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    home: Path | None = None,
) -> str | None:
    agent = normalize_agent(agent)
    session = load_task_agent_session(task, agent)
    if session.session_id is not None:
        if agent == "codex":
            if codex_session_id_exists(session.session_id, home=home):
                return session.session_id
        elif agent == "claude":
            return session.session_id
    if agent == "codex" and session.resume:
        return find_latest_codex_session_id(task, workspace, home=home)
    if agent == "claude" and session.resume:
        return find_latest_claude_session_id(task, workspace, home=home)
    return None



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


def find_latest_claude_session_id(task: TaskSummary, workspace: Path, home: Path | None = None) -> str | None:
    projects_dir = (home or Path.home()) / ".claude" / "projects"
    if not projects_dir.is_dir():
        return None
    task_marker = f"workspace task `{task.name}`"
    task_path_marker = f"Task directory: {task.path}"
    try:
        session_files = sorted(
            projects_dir.rglob("*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for session_file in session_files:
        session_id = _claude_session_id_from_file(session_file)
        if session_id is None:
            continue
        try:
            with session_file.open("r", encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    if task_marker in line and task_path_marker in line:
                        return session_id
        except OSError:
            continue
    return None


def _claude_session_id_from_file(path: Path) -> str | None:
    if CODEX_SESSION_ID_RE.fullmatch(path.stem):
        return path.stem
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
    default_codex_model = data.get("default_codex_model")
    default_codex_reasoning = data.get("default_codex_reasoning")
    default_claude_model = data.get("default_claude_model")
    default_claude_effort = data.get("default_claude_effort")
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
    if isinstance(default_codex_model, str):
        settings["default_codex_model"] = default_codex_model.strip()
    if isinstance(default_codex_reasoning, str) and default_codex_reasoning in AGENT_WORKSPACE_REASONING_EFFORTS:
        settings["default_codex_reasoning"] = default_codex_reasoning
    if isinstance(default_claude_model, str):
        settings["default_claude_model"] = default_claude_model.strip()
    if isinstance(default_claude_effort, str) and default_claude_effort in AGENT_WORKSPACE_REASONING_EFFORTS:
        settings["default_claude_effort"] = default_claude_effort
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
    config = load_task_actions_config(task)
    return config.actions, config.errors


def load_task_actions_config(task: TaskSummary) -> TaskActionsConfig:
    path = task.path / TASK_ACTIONS_FILE
    if not path.is_file():
        return TaskActionsConfig([], [], {}, {}, [])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return TaskActionsConfig([], [], {}, {}, [f"{TASK_ACTIONS_FILE}: {error}"])

    entries = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return TaskActionsConfig([], [], {}, {}, [f"{TASK_ACTIONS_FILE}: expected object with actions list"])

    parameter_sets, parameter_errors = _parse_parameter_sets(data.get("parameter_sets", {}))
    parameter_types, parameter_type_errors = _parse_parameter_types(data.get("parameter_types", {}))
    global_bindings, global_errors = _parse_global_parameter_bindings(data.get("global_parameters", {}))
    actions_by_id: dict[str, TaskAction] = {}
    base_actions: list[TaskAction] = []
    launch_actions: list[TaskAction] = []
    errors: list[str] = []
    errors.extend(parameter_errors)
    errors.extend(parameter_type_errors)
    errors.extend(global_errors)
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        action, error = _parse_task_action(task, entry, index, parameter_types)
        if error is not None:
            errors.append(error)
            continue
        if action.action_id in seen:
            errors.append(f"{TASK_ACTIONS_FILE}: duplicate action id {action.action_id!r}")
            continue
        seen.add(action.action_id)
        base_actions.append(action)
        actions_by_id[action.action_id] = action
        launch_actions.append(
            bind_task_action_parameters(action, parameter_sets, action.bindings or {}, global_bindings)
        )

    shortcuts = data.get("shortcuts", []) if isinstance(data, dict) else []
    if shortcuts is not None and not isinstance(shortcuts, list):
        errors.append(f"{TASK_ACTIONS_FILE}: shortcuts must be a list")
        shortcuts = []
    shortcut_seen: set[str] = set()
    for index, entry in enumerate(shortcuts, start=1):
        shortcut, error = _parse_task_shortcut(entry, index, actions_by_id, parameter_sets, global_bindings)
        if error is not None:
            errors.append(error)
            continue
        if shortcut.action_id in seen or shortcut.action_id in shortcut_seen:
            errors.append(f"{TASK_ACTIONS_FILE}: duplicate shortcut id {shortcut.action_id!r}")
            continue
        shortcut_seen.add(shortcut.action_id)
        launch_actions.append(shortcut)
    return TaskActionsConfig(launch_actions, base_actions, parameter_sets, global_bindings, errors)


def bind_task_action_parameters(
    action: TaskAction,
    parameter_sets: dict[str, dict[str, dict[str, str]]],
    bindings: dict[str, str],
    global_bindings: dict[str, str] | None = None,
) -> TaskAction:
    effective_bindings: dict[str, str] = {}
    env = dict(action.env)
    for parameter in action.parameters:
        selected = ""
        if parameter.global_name and global_bindings is not None:
            selected = global_bindings.get(parameter.global_name, "")
        if not selected:
            selected = bindings.get(parameter.name) or parameter.default
        effective_bindings[parameter.name] = selected
        _add_parameter_env(env, parameter, selected, parameter_sets)
    return TaskAction(
        action_id=action.action_id,
        label=action.label,
        command=action.command,
        cwd=action.cwd,
        env=env,
        parameters=action.parameters,
        bindings=effective_bindings,
        base_action_id=action.base_action_id,
        is_shortcut=action.is_shortcut,
    )


def load_task_actions_data(task: TaskSummary) -> tuple[dict[str, Any], list[str]]:
    path = task.path / TASK_ACTIONS_FILE
    if not path.is_file():
        return {"actions": []}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {}, [f"{TASK_ACTIONS_FILE}: {error}"]
    if not isinstance(data, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: expected object"]
    return data, []


def save_task_actions_data(task: TaskSummary, data: dict[str, Any]) -> None:
    path = task.path / TASK_ACTIONS_FILE
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


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
    parameter_types: dict[str, str],
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

    parameters, parameter_error = _parse_action_parameters(action_id, entry.get("parameters", []), parameter_types)
    if parameter_error is not None:
        return None, parameter_error

    return TaskAction(
        action_id=action_id,
        label=label,
        command=command,
        cwd=cwd,
        env=dict(env_data),
        parameters=parameters,
        bindings={parameter.name: parameter.default for parameter in parameters},
    ), None


def _parse_task_shortcut(
    entry: object,
    index: int,
    actions_by_id: dict[str, TaskAction],
    parameter_sets: dict[str, dict[str, dict[str, str]]],
    global_bindings: dict[str, str],
) -> tuple[TaskAction, None] | tuple[None, str]:
    if not isinstance(entry, dict):
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} must be an object"
    shortcut_id = _string_field(entry, "id")
    label = _string_field(entry, "label")
    action_id = _string_field(entry, "action")
    if shortcut_id is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} missing string id"
    if label is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {index} missing string label"
    if action_id is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} missing string action"
    base = actions_by_id.get(action_id)
    if base is None:
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} references unknown action {action_id!r}"
    bindings = entry.get("bindings", {})
    if not isinstance(bindings, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in bindings.items()
    ):
        return None, f"{TASK_ACTIONS_FILE}: shortcut {shortcut_id!r} bindings must be string map"
    bound = bind_task_action_parameters(base, parameter_sets, dict(bindings), global_bindings)
    return TaskAction(
        action_id=shortcut_id,
        label=label,
        command=bound.command,
        cwd=bound.cwd,
        env=bound.env,
        parameters=bound.parameters,
        bindings=bound.bindings,
        base_action_id=base.action_id,
        is_shortcut=True,
    ), None


def _parse_action_parameters(
    action_id: str,
    entries: object,
    parameter_types: dict[str, str],
) -> tuple[tuple[TaskActionParameter, ...], str | None]:
    if entries in (None, []):
        return (), None
    if not isinstance(entries, list):
        return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameters must be a list"
    parameters: list[TaskActionParameter] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {index} must be an object"
        name = _string_field(entry, "name")
        parameter_type = _string_field(entry, "type")
        if name is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {index} missing string name"
        if parameter_type is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {name!r} missing string type"
        set_name = parameter_types.get(parameter_type)
        if set_name is None:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} parameter {name!r} references unknown type {parameter_type!r}"
        if name in seen:
            return (), f"{TASK_ACTIONS_FILE}: action {action_id!r} duplicate parameter {name!r}"
        seen.add(name)
        label = _string_field(entry, "label") or name
        default = _string_field(entry, "default") or ""
        global_name = _string_field(entry, "global")
        parameters.append(
            TaskActionParameter(
                name=name,
                label=label,
                parameter_type=parameter_type,
                set_name=set_name,
                default=default,
                global_name=global_name,
            )
        )
    return tuple(parameters), None


def _parse_global_parameter_bindings(value: object) -> tuple[dict[str, str], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: global_parameters must be an object"]
    bindings: dict[str, str] = {}
    errors: list[str] = []
    for name, definition in value.items():
        if not isinstance(name, str):
            errors.append(f"{TASK_ACTIONS_FILE}: global parameter names must be strings")
            continue
        if isinstance(definition, str):
            bindings[name] = definition
            continue
        if not isinstance(definition, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: global parameter {name!r} must be a string or object")
            continue
        selected = _string_field(definition, "value") or _string_field(definition, "default")
        if selected:
            bindings[name] = selected
    return bindings, errors


def _parse_parameter_types(value: object) -> tuple[dict[str, str], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: parameter_types must be an object"]
    parameter_types: dict[str, str] = {}
    errors: list[str] = []
    for type_name, definition in value.items():
        if not isinstance(type_name, str):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter_types keys must be strings")
            continue
        if not isinstance(definition, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter type {type_name!r} must be an object")
            continue
        set_name = _string_field(definition, "set")
        if set_name is None:
            errors.append(f"{TASK_ACTIONS_FILE}: parameter type {type_name!r} missing string set")
            continue
        parameter_types[type_name] = set_name
    return parameter_types, errors


def _parse_parameter_sets(value: object) -> tuple[dict[str, dict[str, dict[str, str]]], list[str]]:
    if value in (None, {}):
        return {}, []
    if not isinstance(value, dict):
        return {}, [f"{TASK_ACTIONS_FILE}: parameter_sets must be an object"]
    parameter_sets: dict[str, dict[str, dict[str, str]]] = {}
    errors: list[str] = []
    for set_name, entries in value.items():
        if not isinstance(set_name, str) or not isinstance(entries, dict):
            errors.append(f"{TASK_ACTIONS_FILE}: parameter set names and values must be objects")
            continue
        set_entries: dict[str, dict[str, str]] = {}
        for entry_name, fields in entries.items():
            if not isinstance(entry_name, str) or not isinstance(fields, dict):
                errors.append(f"{TASK_ACTIONS_FILE}: parameter set {set_name!r} entries must be objects")
                continue
            set_entries[entry_name] = {
                str(key): str(field_value)
                for key, field_value in fields.items()
                if isinstance(key, str) and isinstance(field_value, (str, int, float, bool))
            }
        parameter_sets[set_name] = set_entries
    return parameter_sets, errors


def _add_parameter_env(
    env: dict[str, str],
    parameter: TaskActionParameter,
    selected: str,
    parameter_sets: dict[str, dict[str, dict[str, str]]],
) -> None:
    parameter_key = _env_key(parameter.name)
    env[f"TASK_ACTION_PARAM_{parameter_key}"] = selected
    values = parameter_sets.get(parameter.set_name, {}).get(selected, {})
    for field, value in values.items():
        env[f"TASK_ACTION_PARAM_{parameter_key}_{_env_key(field)}"] = value


def _env_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return key or "VALUE"


def _string_field(entry: dict[str, Any], name: str) -> str | None:
    value = entry.get(name)
    return value if isinstance(value, str) and value else None


def _command_field(value: object) -> str | tuple[str, ...] | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return tuple(value)
    return None


def _file_tokens(path: Path) -> int:
    return rough_token_count(path.read_text(encoding="utf-8", errors="replace"))
