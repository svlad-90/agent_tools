from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys

from agent_tools.paf_workspace.task_check import Check
from agent_tools.paf_workspace.task_check import check_task
from agent_tools.tools.task_context import database_path
from agent_tools.tools.task_context import ensure_database
from agent_tools.tools.task_context import load_slots


DEFAULT_AGENT = "agent"
DEFAULT_SESSION_ID = "default"
FRONT_DESK_ONBOARDING_TABLE = "front_desk_agent_onboarding"
FRONT_DESK_STATE_TABLE = "front_desk_iteration_state"
PENDING_STAGES = ("precheck", "work", "journal_required")


@dataclass(frozen=True)
class BellResult:
    stage: str
    exit_code: int
    message: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guide an agent through one task-work iteration.")
    parser.add_argument("--task", type=Path, default=Path.cwd(), help="Task directory. Default: current directory.")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace root. Default: inferred from task path.")
    parser.add_argument("--agent", default="", help="Agent type, for example codex or claude. Default: env/default.")
    parser.add_argument("--session", default="", help="Agent session id. Default: env/default.")
    parser.add_argument(
        "--ack-no-context-change",
        action="store_true",
        help="Finish the iteration without requiring a slot update.",
    )
    parser.add_argument(
        "--open-iteration",
        "--open_iteration",
        action="store_true",
        help="Open a new work iteration for the latest user message.",
    )
    parser.add_argument(
        "--close-iteration",
        "--close_iteration",
        action="store_true",
        help="Close any pending work iteration for this agent/session.",
    )
    parser.add_argument(
        "--reset-pending",
        action="store_true",
        help="Reset pending iterations for this task and exit.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.open_iteration and args.close_iteration:
        parser.error("--open-iteration and --close-iteration are mutually exclusive")

    task_dir = args.task.resolve()
    workspace = (args.workspace or infer_workspace_root(task_dir)).resolve()
    agent = normalize_agent(args.agent or detect_agent())
    run_id = os.environ.get("AGENT_TOOLS_RUN_ID", "").strip()
    session_id = args.session or detect_session_id(task_dir)
    previous_session_id = run_id if run_id and run_id != session_id else None

    if args.reset_pending:
        count = reset_pending_iterations(task_dir)
        print(f"FRONT_DESK_STAGE: RESET_PENDING\nRESET_COUNT: {count}")
        return 0

    result = ring(
        task_dir,
        workspace=workspace,
        agent=agent,
        session_id=session_id,
        previous_session_id=previous_session_id,
        ack_no_context_change=args.ack_no_context_change,
        open_iteration=args.open_iteration,
        close_iteration=args.close_iteration,
    )
    print(result.message)
    return result.exit_code


def ring(
    task_dir: Path,
    *,
    workspace: Path,
    agent: str = DEFAULT_AGENT,
    session_id: str = DEFAULT_SESSION_ID,
    previous_session_id: str | None = None,
    ack_no_context_change: bool = False,
    open_iteration: bool = False,
    close_iteration: bool = False,
) -> BellResult:
    task_dir = task_dir.resolve()
    workspace = workspace.resolve()
    agent = normalize_agent(agent)
    session_id = session_id or DEFAULT_SESSION_ID
    ensure_database(task_dir)
    _ensure_schema(task_dir)
    if previous_session_id and previous_session_id != session_id:
        _migrate_state(task_dir, agent, previous_session_id, session_id)

    now = _now()
    if close_iteration:
        _save_state(
            task_dir,
            agent,
            session_id,
            stage="done",
            last_bell_at=now,
            last_context_seen_at=_latest_slot_update(task_dir),
        )
        return BellResult("ITERATION_DONE", 0, _done_message("Iteration was explicitly closed."))

    if not _is_onboarded(task_dir, agent):
        _mark_onboarded(task_dir, agent, now)
        _save_state(task_dir, agent, session_id, stage="precheck", last_bell_at=now, last_context_seen_at=_latest_slot_update(task_dir))
        return BellResult("WELCOME_REQUIRED", 0, _welcome_message(task_dir, workspace, agent, session_id))

    state = _load_state(task_dir, agent, session_id)
    stage = state.get("stage", "precheck")
    if open_iteration:
        stage = "precheck"
    elif stage in {"precheck", "done"} or not state:
        return BellResult("IDLE", 0, _idle_message())
    if ack_no_context_change and stage in {"work", "journal_required"}:
        _save_state(task_dir, agent, session_id, stage="done", last_bell_at=now, last_context_seen_at=_latest_slot_update(task_dir))
        return BellResult("ITERATION_DONE", 0, _done_message("No context change was explicitly acknowledged."))

    failures = [check for check in check_task(task_dir, workspace=workspace) if check.status == "FAIL"]
    if failures:
        _save_state(
            task_dir,
            agent,
            session_id,
            stage="precheck",
            last_bell_at=now,
            last_context_seen_at=state.get("last_context_seen_at") or _latest_slot_update(task_dir),
        )
        return BellResult("PRECHECK_FAILED", 1, _precheck_failed_message(failures))

    if stage == "precheck":
        context_seen = _latest_slot_update(task_dir)
        _save_state(task_dir, agent, session_id, stage="work", last_bell_at=now, last_context_seen_at=context_seen)
        return BellResult("DO_USER_WORK", 0, _work_message(task_dir))

    if stage == "work":
        _save_state(
            task_dir,
            agent,
            session_id,
            stage="journal_required",
            last_bell_at=now,
            last_context_seen_at=state.get("last_context_seen_at") or _latest_slot_update(task_dir),
        )
        return BellResult("JOURNAL_REQUIRED", 0, _journal_required_message())

    if stage == "journal_required":
        previous_seen = state.get("last_context_seen_at", "")
        latest_seen = _latest_slot_update(task_dir)
        if latest_seen and latest_seen > previous_seen:
            _save_state(task_dir, agent, session_id, stage="done", last_bell_at=now, last_context_seen_at=latest_seen)
            return BellResult("ITERATION_DONE", 0, _done_message("Task context slots were updated."))
        _save_state(task_dir, agent, session_id, stage="journal_required", last_bell_at=now, last_context_seen_at=previous_seen)
        return BellResult("JOURNAL_REQUIRED", 1, _journal_missing_message(previous_seen))

    _save_state(task_dir, agent, session_id, stage="precheck", last_bell_at=now, last_context_seen_at=_latest_slot_update(task_dir))
    return BellResult("PRECHECK_REQUIRED", 0, "FRONT_DESK_STAGE: PRECHECK_REQUIRED\nACTION: Run this script again.")


def reset_pending_iterations(task_dir: Path) -> int:
    task_dir = task_dir.resolve()
    ensure_database(task_dir)
    _ensure_schema(task_dir)
    with sqlite3.connect(database_path(task_dir)) as connection:
        cursor = connection.execute(
            f"UPDATE {FRONT_DESK_STATE_TABLE} SET stage = ?, updated_at = ? WHERE stage IN ({','.join('?' for _ in PENDING_STAGES)})",
            ("precheck", _now(), *PENDING_STAGES),
        )
        return int(cursor.rowcount or 0)


def reset_workspace_pending_iterations(workspace: Path) -> int:
    workspace = workspace.resolve()
    tasks_dir = workspace / "tasks"
    if not tasks_dir.is_dir():
        return 0
    total = 0
    for task_dir in tasks_dir.iterdir():
        if task_dir.is_dir() and database_path(task_dir).is_file():
            total += reset_pending_iterations(task_dir)
    return total


def infer_workspace_root(task_dir: Path) -> Path:
    task_dir = task_dir.resolve()
    if task_dir.parent.name == "tasks":
        return task_dir.parent.parent
    return Path.cwd().resolve()


def detect_agent() -> str:
    for key in ("AGENT_TOOLS_AGENT", "CODEX_AGENT", "CLAUDE_AGENT"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CONFIG_DIR"):
        return "claude"
    if os.environ.get("CODEX_HOME"):
        return "codex"
    return DEFAULT_AGENT


def detect_session_id(task_dir: Path | None = None) -> str:
    run_id = os.environ.get("AGENT_TOOLS_RUN_ID", "").strip()
    if task_dir is not None and run_id:
        mapped_session_id = _mapped_agent_session_id(task_dir, run_id)
        if mapped_session_id:
            return mapped_session_id
    for key in ("AGENT_TOOLS_SESSION_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return DEFAULT_SESSION_ID


def normalize_agent(agent: str) -> str:
    agent = agent.strip().lower()
    return agent or DEFAULT_AGENT


def _ensure_schema(task_dir: Path) -> None:
    with sqlite3.connect(database_path(task_dir)) as connection:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FRONT_DESK_ONBOARDING_TABLE} (
                agent_type TEXT PRIMARY KEY,
                welcomed_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {FRONT_DESK_STATE_TABLE} (
                agent_type TEXT NOT NULL,
                session_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_bell_at TEXT NOT NULL,
                last_context_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (agent_type, session_id)
            )
            """
        )


def _is_onboarded(task_dir: Path, agent: str) -> bool:
    with sqlite3.connect(database_path(task_dir)) as connection:
        row = connection.execute(
            f"SELECT 1 FROM {FRONT_DESK_ONBOARDING_TABLE} WHERE agent_type = ?",
            (agent,),
        ).fetchone()
    return row is not None


def _mark_onboarded(task_dir: Path, agent: str, welcomed_at: str) -> None:
    with sqlite3.connect(database_path(task_dir)) as connection:
        connection.execute(
            f"INSERT OR IGNORE INTO {FRONT_DESK_ONBOARDING_TABLE} (agent_type, welcomed_at) VALUES (?, ?)",
            (agent, welcomed_at),
        )


def _load_state(task_dir: Path, agent: str, session_id: str) -> dict[str, str]:
    with sqlite3.connect(database_path(task_dir)) as connection:
        row = connection.execute(
            f"""
            SELECT stage, started_at, last_bell_at, last_context_seen_at, updated_at
            FROM {FRONT_DESK_STATE_TABLE}
            WHERE agent_type = ? AND session_id = ?
            """,
            (agent, session_id),
        ).fetchone()
    if row is None:
        return {}
    return {
        "stage": str(row[0]),
        "started_at": str(row[1]),
        "last_bell_at": str(row[2]),
        "last_context_seen_at": str(row[3]),
        "updated_at": str(row[4]),
    }


def _save_state(
    task_dir: Path,
    agent: str,
    session_id: str,
    *,
    stage: str,
    last_bell_at: str,
    last_context_seen_at: str,
) -> None:
    with sqlite3.connect(database_path(task_dir)) as connection:
        existing = connection.execute(
            f"SELECT started_at FROM {FRONT_DESK_STATE_TABLE} WHERE agent_type = ? AND session_id = ?",
            (agent, session_id),
        ).fetchone()
        started_at = str(existing[0]) if existing else last_bell_at
        connection.execute(
            f"""
            INSERT INTO {FRONT_DESK_STATE_TABLE}
                (agent_type, session_id, stage, started_at, last_bell_at, last_context_seen_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_type, session_id) DO UPDATE SET
                stage = excluded.stage,
                last_bell_at = excluded.last_bell_at,
                last_context_seen_at = excluded.last_context_seen_at,
                updated_at = excluded.updated_at
            """,
            (agent, session_id, stage, started_at, last_bell_at, last_context_seen_at, last_bell_at),
        )


def _migrate_state(task_dir: Path, agent: str, old_session_id: str, new_session_id: str) -> None:
    with sqlite3.connect(database_path(task_dir)) as connection:
        new_state = connection.execute(
            f"SELECT 1 FROM {FRONT_DESK_STATE_TABLE} WHERE agent_type = ? AND session_id = ?",
            (agent, new_session_id),
        ).fetchone()
        if new_state is not None:
            return
        connection.execute(
            f"UPDATE {FRONT_DESK_STATE_TABLE} SET session_id = ?, updated_at = ? WHERE agent_type = ? AND session_id = ?",
            (new_session_id, _now(), agent, old_session_id),
        )


def _mapped_agent_session_id(task_dir: Path, run_id: str) -> str | None:
    state_path = task_dir / ".agent-workspace-state.json"
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    links = data.get("agent_run_sessions")
    if not isinstance(links, dict):
        return None
    session_id = links.get(run_id)
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def _latest_slot_update(task_dir: Path) -> str:
    updates = [slot.updated_at for slot in load_slots(task_dir) if slot.updated_at]
    return max(updates, default="")


def _welcome_message(task_dir: Path, workspace: Path, agent: str, session_id: str) -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: WELCOME_REQUIRED",
            f"AGENT: {agent}",
            f"SESSION: {session_id}",
            f"WORKSPACE: {workspace}",
            f"TASK: {task_dir}",
            "",
            "POLICY:",
            "This task uses a front-desk iteration loop.",
            "After each user message, run the task-local front_door_bell.py and follow the returned stage.",
            "One iteration is one useful work step for the latest user request, then control returns to the user.",
            "Do not treat the iteration as complete until this tool returns ITERATION_DONE or BLOCKED.",
            "Use task_context slots as current state, not as an append-only changelog.",
            "",
            "ACTION:",
            "Run front_door_bell.py --open-iteration again to start the precheck stage.",
        ]
    )


def _precheck_failed_message(failures: list[Check]) -> str:
    lines = [
        "FRONT_DESK_STAGE: PRECHECK_FAILED",
        "ACTION: Fix the task_check failures, then run front_door_bell.py --open-iteration again.",
        "",
        "FAILURES:",
    ]
    lines.extend(f"- {check.code}: {check.message}" for check in failures)
    return "\n".join(lines)


def _work_message(task_dir: Path) -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: DO_USER_WORK",
            "ACTION: Execute the user's latest request now.",
            "OPTIONAL_CONTEXT_REVIEW:",
            "If prior decisions, findings, validation, environment, risks, or current task state matter, query relevant slots.",
            f"Suggested full query: python3 -m agent_tools.tools.task_context query --task {task_dir} --format agent",
            "AFTER:",
            "Run front_door_bell.py again after code/context work.",
            "If this iteration must be abandoned, run front_door_bell.py --close-iteration.",
        ]
    )


def _journal_required_message() -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: JOURNAL_REQUIRED",
            "ACTION: Update current task context slots for the work just completed.",
            "Minimum slot for a substantive change: operational-memory.",
            "Also update findings, decisions, validation, or blocker-risk when facts changed.",
            "Then run front_door_bell.py again.",
            "If the user request required no durable context update, run front_door_bell.py --ack-no-context-change.",
            "If this iteration must be abandoned, run front_door_bell.py --close-iteration.",
        ]
    )


def _journal_missing_message(previous_seen: str) -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: JOURNAL_REQUIRED",
            "ERROR: No task context slot was updated after the work stage.",
            f"LAST_CONTEXT_SEEN_AT: {previous_seen or 'none'}",
            "ACTION: Update the relevant slot, then run front_door_bell.py again.",
            "If no durable context changed, run front_door_bell.py --ack-no-context-change.",
            "If this iteration must be abandoned, run front_door_bell.py --close-iteration.",
        ]
    )


def _idle_message() -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: IDLE",
            "RESULT: No iteration is open for this agent/session.",
            "ACTION: After a user message, run front_door_bell.py --open-iteration.",
        ]
    )


def _done_message(reason: str) -> str:
    return "\n".join(
        [
            "FRONT_DESK_STAGE: ITERATION_DONE",
            f"RESULT: {reason}",
            "ACTION: Return control to the user with a concise result.",
        ]
    )


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
