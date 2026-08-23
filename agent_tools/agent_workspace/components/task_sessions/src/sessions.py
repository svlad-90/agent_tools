from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
import os
from pathlib import Path
import re
import time
from typing import Any
import uuid

from ...settings.api import AGENT_WORKSPACE_AGENTS
from ...settings.api import AGENT_WORKSPACE_DEFAULT_AGENT
from ...settings.api import normalize_agent
from ...task_catalog.api import TaskSummary


AGENT_WORKSPACE_TASK_STATE_FILE = ".agent-workspace-state.json"
AGENT_SESSION_MARKER = "Ⅱ"
AGENT_IDLE_MARKER = "□"
AGENT_EXTERNAL_ACTIVE_MARKER = "×"
CODEX_SESSION_ID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)


@dataclass(frozen=True)
class AgentSessionState:
    agent: str
    resume: bool = False
    session_id: str | None = None


@dataclass(frozen=True)
class ActiveTaskAgentRun:
    agent: str
    owner_pid: int
    run_id: str


@dataclass
class TaskSessionDiscoveryState:
    pending: set[Path] = field(default_factory=set)
    checked: set[Path] = field(default_factory=set)

    def plan(self, tasks: list[TaskSummary]) -> tuple[TaskSummary, ...]:
        planned: list[TaskSummary] = []
        for task in tasks:
            if task.path in self.pending or task.path in self.checked:
                continue
            if not task_needs_session_discovery(task):
                continue
            self.pending.add(task.path)
            planned.append(task)
        return tuple(planned)

    def finish(self, task_path: Path) -> None:
        self.pending.discard(task_path)
        self.checked.add(task_path)

    def is_pending(self, task: TaskSummary) -> bool:
        return task.path in self.pending

    def invalidate(self, task: TaskSummary) -> None:
        self.checked.discard(task.path)


def resolve_task_agent_sessions(
    task: TaskSummary,
    workspace: Path,
    *,
    home: Path | None = None,
) -> tuple[str, ...]:
    resolved: list[str] = []
    for agent in task_agents_needing_session_discovery(task):
        session_id = find_task_agent_session_id(task, workspace, agent, home=home)
        if session_id is None:
            continue
        save_task_agent_session(task, agent, session_id=session_id)
        resolved.append(agent)
        break
    return tuple(resolved)


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


def load_task_agent_run_session_id(task: TaskSummary, run_id: str) -> str | None:
    data = load_task_state(task)
    links = data.get("agent_run_sessions")
    if not isinstance(links, dict):
        return None
    session_id = links.get(run_id)
    if isinstance(session_id, str) and CODEX_SESSION_ID_RE.fullmatch(session_id):
        return session_id
    return None


def save_task_agent_run_session_id(task: TaskSummary, run_id: str, session_id: str) -> bool:
    if not run_id or not CODEX_SESSION_ID_RE.fullmatch(session_id):
        return False
    data = load_task_state(task)
    links = data.get("agent_run_sessions")
    if not isinstance(links, dict):
        links = {}
    links[run_id] = session_id
    data["agent_run_sessions"] = links
    save_task_state(task, data)
    return True


def reconcile_task_agent_run_session(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    run_id: str | None,
    *,
    home: Path | None = None,
) -> str | None:
    if not run_id:
        return None
    existing = load_task_agent_run_session_id(task, run_id)
    if existing is not None:
        return existing
    session_id = find_task_agent_session_id(task, workspace, agent, home=home)
    if session_id is None:
        normalized_agent = normalize_agent(agent)
        if normalized_agent == "codex":
            session_id = find_latest_codex_session_id(task, workspace, home=home)
        elif normalized_agent == "claude":
            session_id = find_latest_claude_session_id(task, workspace, home=home)
    if session_id is None or session_id == run_id:
        return None
    save_task_agent_session(task, agent, session_id=session_id)
    save_task_agent_run_session_id(task, run_id, session_id)
    return session_id


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


def task_agent_has_saved_resumable_state(task: TaskSummary, agent: str) -> bool:
    session = load_task_agent_session(task, agent)
    return session.resume and session.session_id is not None


def task_agent_needs_session_discovery(task: TaskSummary, agent: str) -> bool:
    session = load_task_agent_session(task, agent)
    return session.resume and session.session_id is None


def task_agents_needing_session_discovery(
    task: TaskSummary,
    default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT,
) -> tuple[str, ...]:
    saved_agent = load_task_agent(task, default_agent)
    agents = (saved_agent, *(agent for agent in AGENT_WORKSPACE_AGENTS if agent != saved_agent))
    return tuple(agent for agent in agents if task_agent_needs_session_discovery(task, agent))


def task_has_valid_agent_session(task: TaskSummary, workspace: Path, home: Path | None = None) -> bool:
    return any(
        task_agent_session_id_is_valid(task, workspace, agent, home=home)
        for agent in AGENT_WORKSPACE_AGENTS
    )


def find_task_agent_session_id(
    task: TaskSummary,
    workspace: Path,
    agent: str,
    home: Path | None = None,
) -> str | None:
    agent = normalize_agent(agent)
    session = load_task_agent_session(task, agent)
    if session.session_id is not None:
        return session.session_id
    if agent == "codex" and session.resume:
        return find_latest_codex_session_id(task, workspace, home=home)
    if agent == "claude" and session.resume:
        return find_latest_claude_session_id(task, workspace, home=home)
    return None


def find_latest_codex_session_id(task: TaskSummary, workspace: Path, home: Path | None = None) -> str | None:
    cached_session_id = load_task_agent_session(task, "codex").session_id
    if cached_session_id is not None:
        return cached_session_id
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
                if any(needle in line for line in stream):
                    return match.group(1)
        except OSError:
            continue
    return None


def find_latest_claude_session_id(task: TaskSummary, workspace: Path, home: Path | None = None) -> str | None:
    cached_session_id = load_task_agent_session(task, "claude").session_id
    if cached_session_id is not None:
        return cached_session_id
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


def task_agent_session_markers(
    task: TaskSummary,
    workspace: Path,
    home: Path | None = None,
) -> tuple[str, ...]:
    _ = workspace
    _ = home
    agent = load_task_agent(task)
    if task_agent_has_saved_resumable_state(task, agent):
        return (AGENT_SESSION_MARKER,)
    return ()


def task_agent_selection_with_resumable_fallback(
    task: TaskSummary,
    workspace: Path,
    default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT,
    home: Path | None = None,
) -> str:
    _ = workspace
    _ = home
    agent = load_task_agent(task, default_agent)
    if task_agent_has_saved_resumable_state(task, agent):
        return agent
    for candidate in AGENT_WORKSPACE_AGENTS:
        if task_agent_has_saved_resumable_state(task, candidate):
            return candidate
    return agent


def task_needs_session_discovery(task: TaskSummary) -> bool:
    return bool(task_agents_needing_session_discovery(task))


def task_selected_agent_has_resumable_state(
    task: TaskSummary,
    workspace: Path,
    default_agent: str = AGENT_WORKSPACE_DEFAULT_AGENT,
    home: Path | None = None,
) -> bool:
    _ = workspace
    _ = home
    agent = load_task_agent(task, default_agent)
    return task_agent_has_saved_resumable_state(task, agent)


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


def _claude_session_id_from_file(path: Path) -> str | None:
    if CODEX_SESSION_ID_RE.fullmatch(path.stem):
        return path.stem
    return None


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
        or "agent_tools.agent_workspace" in part
        or "/agent_workspace/" in part
        for part in cmdline
    ) or "agent_tools.agent_workspace" in joined


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
