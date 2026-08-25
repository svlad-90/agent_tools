from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from ...localization.api import AGENT_STATUS_RUNNING_LABEL
from ...localization.api import AGENT_STATUS_TOOLTIPS
from ...settings.api import AGENT_WORKSPACE_AGENTS
from ...task_catalog.api import TaskSummary
from ...task_sessions.api import AGENT_EXTERNAL_ACTIVE_MARKER
from ...task_sessions.api import AGENT_IDLE_MARKER
from ...task_sessions.api import task_agent_session_markers


AGENT_PROMPT_MARKER = "▸"
AGENT_RUNNING_READY_MARKER = AGENT_PROMPT_MARKER
AGENT_TOOL_MARKER = "◆"
AGENT_RUNNING_SPINNER_FRAMES = (AGENT_RUNNING_READY_MARKER,)
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
    parts: list[str] = []
    if external_active:
        return AGENT_EXTERNAL_ACTIVE_MARKER
    if running_agents:
        return spinner_frame or "●"
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
        if marker.startswith(AGENT_RUNNING_READY_MARKER):
            label = AGENT_STATUS_RUNNING_LABEL
        else:
            label = AGENT_STATUS_TOOLTIPS.get(marker, "")
        if label and label not in labels:
            labels.append(label)
    return "; ".join(labels)
