from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from pathlib import Path
from time import time_ns
from typing import Any, Protocol
from uuid import uuid4

from agent_tools.agent_workspace.components.agent_status.api import AGENT_PROMPT_MARKER
from agent_tools.agent_workspace.components.agent_status.api import AGENT_RUNNING_READY_MARKER
from agent_tools.agent_workspace.components.agent_status.api import AGENT_TOOL_MARKER
from agent_tools.paf_workspace.task_check import check_task
from agent_tools.paf_workspace.task_check import render_text
from agent_tools.tools.task_context import agent_visible_slots
from agent_tools.tools.task_context import database_path
from agent_tools.tools.task_context import ensure_database
from agent_tools.tools.task_context import load_slots
from agent_tools.tools.task_context import render_slots

from ._compat import StrEnum
from .limited_bash import limited_bash_shell_command
from .limited_bash import limit_from_env


class AgentHookEvent(StrEnum):
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"
    STOP = "stop"


class HarnessStatusEvent(StrEnum):
    HOOK_OBSERVED = "hook_observed"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    USER_PROMPT_RECEIVED = "user_prompt_received"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    COMPACT_CHECKPOINT = "compact_checkpoint"
    COMPACT_FINISHED = "compact_finished"
    STOP_ALLOWED = "stop_allowed"
    STOP_BLOCKED = "stop_blocked"
    JOURNAL_REQUIRED = "journal_required"
    TASK_CHECK_FAILED = "task_check_failed"
    TASK_UNRESOLVED = "task_unresolved"


class AgentType(StrEnum):
    CODEX = "codex"
    CLAUDE = "claude"


@dataclass(frozen=True)
class HarnessStatusUpdate:
    task_dir: Path | None
    agent_type: AgentType
    session_id: str | None
    event: HarnessStatusEvent
    icon: str
    message: str
    updated_at: datetime
    hook_event: AgentHookEvent | None = None
    tool_name: str | None = None
    tool_detail: str = ""
    outcome: str = ""


@dataclass(frozen=True)
class HarnessDebugEvent:
    event_id: int
    task_dir: Path
    agent_type: AgentType
    session_id: str
    hook_event: str
    status_event: HarnessStatusEvent
    icon: str
    message: str
    tool_name: str
    tool_detail: str
    outcome: str
    updated_at: str

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.event_id,
            "task_dir": str(self.task_dir),
            "agent_type": self.agent_type.value,
            "session_id": self.session_id,
            "hook_event": self.hook_event,
            "status_event": self.status_event.value,
            "icon": self.icon,
            "message": self.message,
            "tool_name": self.tool_name,
            "tool_detail": self.tool_detail,
            "outcome": self.outcome,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class HarnessStatusSubscription:
    subscription_id: str
    unsubscribe: Callable[[], bool]


@dataclass(frozen=True)
class HarnessAdapterSubscription:
    agent_type: AgentType
    unsubscribe: Callable[[], bool]


StatusCallback = Callable[[HarnessStatusUpdate], None]
HookOutput = dict[str, Any] | str | None
StopBlockFormatter = Callable[[str], HookOutput]


class _HookRequest(Protocol):
    payload: dict[str, Any]
    task_dir: Path | None
    workspace: Path | None
    session_id: str | None


_STATUS_CALLBACKS: dict[str, StatusCallback] = {}

_JOURNAL_SLOT_CATEGORIES = ("operational-memory", "findings", "validation", "decisions", "blocker-risk")
_DEBUG_EVENT_FILE = ".agent-workspace-harness-debug.jsonl"
_DEBUG_EVENT_LIMIT = 1000
_DEBUG_EVENT_TAIL_BLOCK_SIZE = 64 * 1024
_POST_COMPACT_CONTEXT_LIMIT = 12000


def subscribe_harness_status(callback: StatusCallback) -> HarnessStatusSubscription:
    subscription_id = uuid4().hex
    _STATUS_CALLBACKS[subscription_id] = callback
    return HarnessStatusSubscription(
        subscription_id=subscription_id,
        unsubscribe=lambda: _unsubscribe_harness_status(subscription_id),
    )


def record_harness_status(
    task_dir: Path,
    *,
    agent_type: AgentType,
    session_id: str | None,
    event: HarnessStatusEvent,
    icon: str,
    message: str,
    hook_event: AgentHookEvent | None = None,
    tool_name: str | None = None,
    tool_detail: str = "",
    outcome: str = "",
) -> None:
    _emit(
        task_dir,
        agent_type,
        session_id,
        event,
        icon,
        message,
        hook_event=hook_event,
        tool_name=tool_name,
        tool_detail=tool_detail,
        outcome=outcome,
    )


def clear_harness_status_subscriptions() -> None:
    _STATUS_CALLBACKS.clear()


def clear_harness_debug_events(workspace: Path) -> None:
    try:
        _harness_debug_path(workspace).unlink(missing_ok=True)
    except OSError:
        return


def load_harness_debug_events(
    task_dir: Path,
    *,
    session_id: str | None = None,
    after_event_id: int | None = None,
    limit: int = 200,
) -> list[HarnessDebugEvent]:
    task_dir = task_dir.resolve()
    limit = max(1, min(limit, _DEBUG_EVENT_LIMIT))
    min_event_id = max(0, after_event_id or 0)
    events: list[HarnessDebugEvent] = []
    path = _harness_debug_path(_workspace_for_task(task_dir))
    for line in _reversed_harness_debug_lines(path):
        try:
            data = json.loads(line)
            event = _debug_event_from_json(data)
        except (TypeError, ValueError, KeyError):
            continue
        if event.task_dir != task_dir:
            continue
        if session_id is not None and event.session_id != _session_key(session_id):
            continue
        if event.event_id <= min_event_id:
            continue
        events.append(event)
        if len(events) >= limit:
            break
    events.reverse()
    return events


def load_latest_harness_debug_events_by_task(workspace: Path) -> dict[Path, HarnessDebugEvent]:
    latest: dict[Path, HarnessDebugEvent] = {}
    path = _harness_debug_path(workspace)
    for line in _reversed_harness_debug_lines(path):
        try:
            data = json.loads(line)
            event = _debug_event_from_json(data)
        except (TypeError, ValueError, KeyError):
            continue
        if event.task_dir not in latest:
            latest[event.task_dir] = event
    return latest


def handle_adapter_event(
    agent_type: AgentType,
    event: AgentHookEvent,
    request: _HookRequest,
    *,
    format_stop_block: StopBlockFormatter,
) -> HookOutput:
    task_dir = _resolve_task_dir(request)
    if task_dir is None:
        _emit_status(
            HarnessStatusUpdate(
                task_dir=None,
                agent_type=agent_type,
                session_id=request.session_id,
                event=HarnessStatusEvent.TASK_UNRESOLVED,
                icon="?",
                message="Task directory is unresolved; harness adapter is inactive for this event.",
                updated_at=datetime.now().astimezone(),
                hook_event=event,
                tool_name=_request_tool_name(request),
                outcome="inactive",
            )
        )
        return None

    ensure_database(task_dir)
    _ensure_adapter_schema(task_dir)
    tool_name = _request_tool_name(request)
    tool_detail = _request_tool_detail(request)

    if event is AgentHookEvent.SESSION_START:
        _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value, session_active=True)
        source = _request_source(request)
        if source in {"clear", "compact"}:
            _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.COMPACT_FINISHED, AGENT_TOOL_MARKER, "Context injected after compact.", hook_event=event, outcome="injected")
            return _post_compact_message(task_dir)
        _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.SESSION_STARTED, "●", "Context injected at session start.", hook_event=event, outcome="injected")
        return _session_start_message(task_dir)
    if event is AgentHookEvent.SESSION_END:
        _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value, session_active=False)
        _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.SESSION_ENDED, "■", "Session ended.", hook_event=event, outcome="done")
        return None
    if event is AgentHookEvent.USER_PROMPT_SUBMIT:
        now = _now()
        _update_adapter_state(
            task_dir,
            agent_type,
            request.session_id,
            last_event=event.value,
            last_user_prompt_at=now,
            work_observed_since_prompt=False,
            journal_updated_since_prompt=False,
        )
        _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.USER_PROMPT_RECEIVED, AGENT_PROMPT_MARKER, "User prompt observed.", hook_event=event, outcome="observed")
        return None
    if event is AgentHookEvent.PRE_TOOL_USE:
        _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value, work_observed_since_prompt=True)
        _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.TOOL_STARTED, AGENT_TOOL_MARKER, "Tool use started.", hook_event=event, tool_name=tool_name, tool_detail=tool_detail, outcome="started")
        return _limited_bash_pre_tool_output(task_dir, request)
    if event is AgentHookEvent.POST_TOOL_USE:
        _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value, work_observed_since_prompt=True)
        _refresh_journal_flag(task_dir, agent_type, request.session_id)
        _emit(task_dir, agent_type, request.session_id, HarnessStatusEvent.TOOL_FINISHED, AGENT_RUNNING_READY_MARKER, "Tool use finished.", hook_event=event, tool_name=tool_name, tool_detail=tool_detail, outcome="finished")
        return None
    if event is AgentHookEvent.PRE_COMPACT:
        return _handle_pre_compact(task_dir, agent_type, request.session_id)
    if event is AgentHookEvent.POST_COMPACT:
        _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value)
        _emit(
            task_dir,
            agent_type,
            request.session_id,
            HarnessStatusEvent.HOOK_OBSERVED,
            AGENT_TOOL_MARKER,
            "PostCompact observed; context injection is deferred to compacted session start.",
            hook_event=event,
            outcome="observed",
        )
        return None
    if event is AgentHookEvent.STOP:
        return _handle_stop(task_dir, agent_type, request.session_id, format_stop_block=format_stop_block)

    _update_adapter_state(task_dir, agent_type, request.session_id, last_event=event.value)
    _emit(
        task_dir,
        agent_type,
        request.session_id,
        HarnessStatusEvent.HOOK_OBSERVED,
        "•",
        f"{event.value} observed.",
        hook_event=event,
        tool_name=tool_name,
        tool_detail=tool_detail,
        outcome="observed",
    )
    return None


def _handle_stop(
    task_dir: Path,
    agent_type: AgentType,
    session_id: str | None,
    *,
    format_stop_block: StopBlockFormatter,
) -> HookOutput:
    _update_adapter_state(task_dir, agent_type, session_id, last_event=AgentHookEvent.STOP.value)
    checks = check_task(task_dir, workspace=_workspace_for_task(task_dir))
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        _emit(task_dir, agent_type, session_id, HarnessStatusEvent.TASK_CHECK_FAILED, "⛔", "task_check failed.", hook_event=AgentHookEvent.STOP, outcome="blocked")
        return format_stop_block(
            "Stop blocked by task_check failures. Fix these issues before ending the response:\n\n"
            + render_text(
                task_dir,
                failures,
                errors_only=True,
            )
        )

    _refresh_journal_flag(task_dir, agent_type, session_id)
    state = _load_adapter_state(task_dir, agent_type, session_id)
    if state.get("work_observed_since_prompt") and not state.get("journal_updated_since_prompt"):
        _emit(task_dir, agent_type, session_id, HarnessStatusEvent.JOURNAL_REQUIRED, "🧾", "Journal update required.", hook_event=AgentHookEvent.STOP, outcome="blocked")
        return format_stop_block(
            "Stop blocked. Update current task context slots before ending the response. "
            "Write durable current state into operational-memory, findings, validation, decisions, "
            "or blocker-risk as appropriate, then try to stop again."
        )

    _emit(task_dir, agent_type, session_id, HarnessStatusEvent.STOP_ALLOWED, "●", "Stop allowed.", hook_event=AgentHookEvent.STOP, outcome="allowed")
    return None


def _handle_pre_compact(
    task_dir: Path,
    agent_type: AgentType,
    session_id: str | None,
) -> HookOutput:
    _update_adapter_state(task_dir, agent_type, session_id, last_event=AgentHookEvent.PRE_COMPACT.value)
    _refresh_journal_flag(task_dir, agent_type, session_id)
    state = _load_adapter_state(task_dir, agent_type, session_id)
    if state.get("work_observed_since_prompt") and not state.get("journal_updated_since_prompt"):
        _emit(
            task_dir,
            agent_type,
            session_id,
            HarnessStatusEvent.JOURNAL_REQUIRED,
            "🧾",
            "Journal update still required after compact.",
            hook_event=AgentHookEvent.PRE_COMPACT,
            outcome="pending",
        )
        return None

    _emit(task_dir, agent_type, session_id, HarnessStatusEvent.COMPACT_CHECKPOINT, AGENT_TOOL_MARKER, "PreCompact checkpoint passed.", hook_event=AgentHookEvent.PRE_COMPACT, outcome="allowed")
    return None


def _session_start_message(task_dir: Path) -> str:
    return (
        "Agent Workspace session started. Task state source is TASK_CONTEXT.sqlite3 slots. "
        "Use task_context query when task context is needed; hook adapter gates Stop and records PreCompact checkpoints. "
        f"Task directory: {task_dir}"
    )


def _post_compact_message(task_dir: Path) -> str:
    rendered = render_slots(
        agent_visible_slots(load_slots(task_dir)),
        format_name="agent",
        task_dir=task_dir,
    ).strip()
    header = (
        "Compaction completed. Current task state from TASK_CONTEXT.sqlite3 is injected below. "
        "Treat these slots as source of truth; if a detail is missing or truncated, query TASK_CONTEXT.sqlite3. "
        f"Task directory: {task_dir}"
    )
    if not rendered:
        return f"{header}\n\nNo task context slots are present."
    body = _truncate_post_compact_context(rendered)
    return f"{header}\n\n{body}"


def _truncate_post_compact_context(text: str) -> str:
    if len(text) <= _POST_COMPACT_CONTEXT_LIMIT:
        return text
    omitted = len(text) - _POST_COMPACT_CONTEXT_LIMIT
    return (
        text[:_POST_COMPACT_CONTEXT_LIMIT].rstrip()
        + f"\n\n[Task context snapshot truncated by {omitted} characters; query TASK_CONTEXT.sqlite3 for full state.]"
    )


def _resolve_task_dir(request: _HookRequest) -> Path | None:
    for value in (
        request.payload.get("task_dir"),
        request.payload.get("taskDirectory"),
        request.payload.get("taskDir"),
        request.task_dir,
        request.workspace,
    ):
        path = _path_or_none(value)
        resolved = _task_dir_from_path(path) if path is not None else None
        if resolved is not None:
            return resolved
    return None


def _task_dir_from_path(path: Path) -> Path | None:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "TASK_CONTEXT.sqlite3").exists():
            return candidate
        if candidate.parent.name == "tasks":
            return candidate
    return None


def _path_or_none(value: object) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _workspace_for_task(task_dir: Path) -> Path:
    if task_dir.parent.name == "tasks":
        return task_dir.parent.parent
    return task_dir.parent


def _latest_journal_update(task_dir: Path) -> str | None:
    slots = load_slots(task_dir, _JOURNAL_SLOT_CATEGORIES)
    if not slots:
        return None
    return max(slot.updated_at for slot in slots)


def _refresh_journal_flag(task_dir: Path, agent_type: AgentType, session_id: str | None) -> None:
    state = _load_adapter_state(task_dir, agent_type, session_id)
    prompt_at = state.get("last_user_prompt_at")
    latest_update = _latest_journal_update(task_dir)
    journal_updated = bool(prompt_at and latest_update and latest_update > prompt_at)
    _update_adapter_state(task_dir, agent_type, session_id, journal_updated_since_prompt=journal_updated)


def _ensure_adapter_schema(task_dir: Path) -> None:
    with sqlite3.connect(database_path(task_dir), timeout=10) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS harness_adapter_state (
                agent_type TEXT NOT NULL,
                session_id TEXT NOT NULL,
                last_event TEXT NOT NULL DEFAULT '',
                last_user_prompt_at TEXT NOT NULL DEFAULT '',
                work_observed_since_prompt INTEGER NOT NULL DEFAULT 0,
                journal_updated_since_prompt INTEGER NOT NULL DEFAULT 0,
                session_active INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(agent_type, session_id)
            )
            """
        )
        connection.execute(
            "DROP TABLE IF EXISTS harness_debug_events"
        )


def _load_adapter_state(task_dir: Path, agent_type: AgentType, session_id: str | None) -> dict[str, Any]:
    _ensure_adapter_schema(task_dir)
    key = _session_key(session_id)
    with sqlite3.connect(database_path(task_dir), timeout=10) as connection:
        row = connection.execute(
            """
            SELECT last_event, last_user_prompt_at, work_observed_since_prompt,
                   journal_updated_since_prompt, session_active, updated_at
            FROM harness_adapter_state
            WHERE agent_type = ? AND session_id = ?
            """,
            (agent_type.value, key),
        ).fetchone()
    if row is None:
        return {
            "last_event": "",
            "last_user_prompt_at": "",
            "work_observed_since_prompt": False,
            "journal_updated_since_prompt": False,
            "session_active": False,
            "updated_at": "",
        }
    return {
        "last_event": row[0],
        "last_user_prompt_at": row[1],
        "work_observed_since_prompt": bool(row[2]),
        "journal_updated_since_prompt": bool(row[3]),
        "session_active": bool(row[4]),
        "updated_at": row[5],
    }


def _update_adapter_state(
    task_dir: Path,
    agent_type: AgentType,
    session_id: str | None,
    *,
    last_event: str | None = None,
    last_user_prompt_at: str | None = None,
    work_observed_since_prompt: bool | None = None,
    journal_updated_since_prompt: bool | None = None,
    session_active: bool | None = None,
) -> None:
    _ensure_adapter_schema(task_dir)
    state = _load_adapter_state(task_dir, agent_type, session_id)
    values = {
        "last_event": state["last_event"] if last_event is None else last_event,
        "last_user_prompt_at": state["last_user_prompt_at"] if last_user_prompt_at is None else last_user_prompt_at,
        "work_observed_since_prompt": (
            state["work_observed_since_prompt"]
            if work_observed_since_prompt is None
            else work_observed_since_prompt
        ),
        "journal_updated_since_prompt": (
            state["journal_updated_since_prompt"]
            if journal_updated_since_prompt is None
            else journal_updated_since_prompt
        ),
        "session_active": state["session_active"] if session_active is None else session_active,
    }
    with sqlite3.connect(database_path(task_dir), timeout=10) as connection:
        connection.execute(
            """
            INSERT INTO harness_adapter_state (
                agent_type, session_id, last_event, last_user_prompt_at,
                work_observed_since_prompt, journal_updated_since_prompt,
                session_active, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_type, session_id) DO UPDATE SET
                last_event = excluded.last_event,
                last_user_prompt_at = excluded.last_user_prompt_at,
                work_observed_since_prompt = excluded.work_observed_since_prompt,
                journal_updated_since_prompt = excluded.journal_updated_since_prompt,
                session_active = excluded.session_active,
                updated_at = excluded.updated_at
            """,
            (
                agent_type.value,
                _session_key(session_id),
                values["last_event"],
                values["last_user_prompt_at"],
                int(values["work_observed_since_prompt"]),
                int(values["journal_updated_since_prompt"]),
                int(values["session_active"]),
                _now(),
            ),
        )


def _emit(
    task_dir: Path,
    agent_type: AgentType,
    session_id: str | None,
    event: HarnessStatusEvent,
    icon: str,
    message: str,
    *,
    hook_event: AgentHookEvent | None = None,
    tool_name: str | None = None,
    tool_detail: str = "",
    outcome: str = "",
) -> None:
    _emit_status(
        HarnessStatusUpdate(
            task_dir=task_dir,
            agent_type=agent_type,
            session_id=session_id,
            event=event,
            icon=icon,
            message=message,
            updated_at=datetime.now().astimezone(),
            hook_event=hook_event,
            tool_name=tool_name,
            tool_detail=tool_detail,
            outcome=outcome,
        )
    )


def _emit_status(update: HarnessStatusUpdate) -> None:
    if update.task_dir is not None:
        _record_harness_debug_event(update)
    for callback in tuple(_STATUS_CALLBACKS.values()):
        callback(update)


def _record_harness_debug_event(update: HarnessStatusUpdate) -> None:
    task_dir = update.task_dir
    if task_dir is None:
        return
    path = _harness_debug_path(_workspace_for_task(task_dir))
    data = {
        "id": time_ns(),
        "task_dir": str(task_dir.resolve()),
        "agent_type": update.agent_type.value,
        "session_id": _session_key(update.session_id),
        "hook_event": update.hook_event.value if update.hook_event is not None else "",
        "status_event": update.event.value,
        "icon": update.icon,
        "message": update.message,
        "tool_name": update.tool_name or "",
        "tool_detail": update.tool_detail,
        "outcome": update.outcome,
        "updated_at": update.updated_at.isoformat(timespec="seconds"),
    }
    try:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(data, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    except OSError:
        return


def _harness_debug_path(workspace: Path) -> Path:
    return workspace.resolve() / _DEBUG_EVENT_FILE


def _reversed_harness_debug_lines(path: Path) -> list[str]:
    try:
        with path.open("rb") as stream:
            stream.seek(0, 2)
            end = stream.tell()
            if end <= 0:
                return []
            buffer = b""
            position = end
            while position > 0:
                read_size = min(_DEBUG_EVENT_TAIL_BLOCK_SIZE, position)
                position -= read_size
                stream.seek(position)
                buffer = stream.read(read_size) + buffer
                lines = buffer.splitlines()
                if len(lines) > _DEBUG_EVENT_LIMIT or position == 0:
                    return [
                        line.decode("utf-8", errors="replace")
                        for line in reversed(lines[-_DEBUG_EVENT_LIMIT:])
                    ]
    except OSError:
        return []
    return []


def _debug_event_from_json(data: dict[str, Any]) -> HarnessDebugEvent:
    return HarnessDebugEvent(
        event_id=int(data["id"]),
        task_dir=Path(str(data["task_dir"])).resolve(),
        agent_type=AgentType(str(data["agent_type"])),
        session_id=str(data["session_id"]),
        hook_event=str(data.get("hook_event", "")),
        status_event=HarnessStatusEvent(str(data["status_event"])),
        icon=str(data.get("icon", "")),
        message=str(data.get("message", "")),
        tool_name=str(data.get("tool_name", "")),
        tool_detail=str(data.get("tool_detail", "")),
        outcome=str(data.get("outcome", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def _unsubscribe_harness_status(subscription_id: str) -> bool:
    return _STATUS_CALLBACKS.pop(subscription_id, None) is not None


def unsubscribe_adapter_subscriptions(subscriptions: list[Any]) -> bool:
    changed = False
    for subscription in subscriptions:
        changed = subscription.unsubscribe() or changed
    return changed


def _session_key(session_id: str | None) -> str:
    return session_id or "default"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _request_tool_name(request: _HookRequest) -> str | None:
    for key in ("tool_name", "toolName", "tool", "name"):
        value = request.payload.get(key)
        if isinstance(value, str) and value:
            return value
    tool = request.payload.get("tool")
    if isinstance(tool, dict):
        for key in ("name", "tool_name", "toolName"):
            value = tool.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _request_tool_detail(request: _HookRequest) -> str:
    for key in ("tool_input", "toolInput", "input", "arguments", "parameters"):
        value = request.payload.get(key)
        detail = _tool_detail_from_value(value)
        if detail:
            return detail
    tool = request.payload.get("tool")
    if isinstance(tool, dict):
        for key in ("input", "arguments", "parameters"):
            detail = _tool_detail_from_value(tool.get(key))
            if detail:
                return detail
    return ""


def _limited_bash_pre_tool_output(
    task_dir: Path,
    request: _HookRequest,
) -> HookOutput:
    tool_name = _request_tool_name(request)
    if tool_name is None or tool_name.casefold() != "bash":
        return None
    tool_input = _request_tool_input(request)
    if tool_input is None:
        return None
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    if "agent_tools.agent_workspace.components.harness_adapter.limited_bash" in command:
        return None
    updated_input = dict(tool_input)
    updated_input["command"] = limited_bash_shell_command(
        command,
        limit=limit_from_env(),
        cwd=_request_cwd(request) or _workspace_for_task(task_dir),
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated_input,
        }
    }


def _request_tool_input(request: _HookRequest) -> dict[str, Any] | None:
    for key in ("tool_input", "toolInput", "input", "arguments", "parameters"):
        value = request.payload.get(key)
        if isinstance(value, dict):
            return value
    tool = request.payload.get("tool")
    if isinstance(tool, dict):
        for key in ("input", "arguments", "parameters"):
            value = tool.get(key)
            if isinstance(value, dict):
                return value
    return None


def _request_cwd(request: _HookRequest) -> Path | None:
    for key in ("cwd", "currentWorkingDirectory", "working_directory", "workingDirectory"):
        value = request.payload.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    return request.workspace


def _request_source(request: _HookRequest) -> str:
    for key in ("source", "startup_source", "startupSource", "session_source", "sessionSource"):
        value = request.payload.get(key)
        if isinstance(value, str) and value:
            return value.casefold()
    return ""


def _tool_detail_from_value(value: object) -> str:
    if isinstance(value, dict):
        for key in ("command", "cmd", "script", "patch"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return _shorten_tool_detail(nested.strip())
        try:
            return _shorten_tool_detail(json.dumps(value, ensure_ascii=False, sort_keys=True))
        except TypeError:
            return _shorten_tool_detail(str(value))
    if isinstance(value, str) and value.strip():
        return _shorten_tool_detail(value.strip())
    return ""


def _shorten_tool_detail(value: str, *, limit: int = 220) -> str:
    one_line = " ".join(value.split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1].rstrip() + "…"
