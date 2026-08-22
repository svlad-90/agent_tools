from __future__ import annotations

import json
from pathlib import Path

from agent_tools.paf_workspace.task_check import initialize_task_layout
from agent_tools.tools.front_desk_bell import detect_session_id
from agent_tools.tools.front_desk_bell import reset_pending_iterations
from agent_tools.tools.front_desk_bell import ring
from agent_tools.tools.task_context import set_slot


def test_front_desk_bell_onboards_then_requires_task_check_fixes(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)

    first = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    idle = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    second = ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)

    assert first.stage == "WELCOME_REQUIRED"
    assert first.exit_code == 0
    assert "front_door_bell.py" in first.message
    assert idle.stage == "IDLE"
    assert second.stage == "PRECHECK_FAILED"
    assert second.exit_code == 1
    assert "task-context-slot-required" in second.message


def test_front_desk_bell_guides_work_and_requires_slot_update(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    work = ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)
    journal = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    missing = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    set_slot(task, "operational-memory", "Current: work completed.", updated_at="2026-01-01T00:00:10+00:00")
    done = ring(task, workspace=tmp_path, agent="codex", session_id="s1")

    assert work.stage == "DO_USER_WORK"
    assert "OPTIONAL_CONTEXT_REVIEW" in work.message
    assert journal.stage == "JOURNAL_REQUIRED"
    assert journal.exit_code == 0
    assert missing.stage == "JOURNAL_REQUIRED"
    assert missing.exit_code == 1
    assert done.stage == "ITERATION_DONE"
    assert done.exit_code == 0


def test_front_desk_bell_allows_explicit_no_context_change_ack(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="claude", session_id="s1")
    ring(task, workspace=tmp_path, agent="claude", session_id="s1", open_iteration=True)
    done = ring(task, workspace=tmp_path, agent="claude", session_id="s1", ack_no_context_change=True)

    assert done.stage == "ITERATION_DONE"
    assert "explicitly acknowledged" in done.message


def test_front_desk_bell_reset_pending_iterations(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)

    assert reset_pending_iterations(task) == 1
    idle = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    work = ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)
    assert idle.stage == "IDLE"
    assert work.stage == "DO_USER_WORK"


def test_front_desk_bell_resolves_run_id_mapping_and_migrates_state(tmp_path: Path, monkeypatch: object) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)
    state_path = task / ".agent-workspace-state.json"
    state_path.write_text(
        json.dumps({"agent_run_sessions": {"run-1": "019feba2-e25e-76e1-9468-aa399758268f"}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_TOOLS_RUN_ID", "run-1")  # type: ignore[attr-defined]
    monkeypatch.setenv("AGENT_TOOLS_SESSION_ID", "run-1")  # type: ignore[attr-defined]

    ring(task, workspace=tmp_path, agent="codex", session_id="run-1")
    work = ring(
        task,
        workspace=tmp_path,
        agent="codex",
        session_id=detect_session_id(task),
        previous_session_id="run-1",
        open_iteration=True,
    )

    assert detect_session_id(task) == "019feba2-e25e-76e1-9468-aa399758268f"
    assert work.stage == "DO_USER_WORK"


def test_front_desk_bell_requires_open_iteration_after_done(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    work = ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)
    done = ring(task, workspace=tmp_path, agent="codex", session_id="s1", ack_no_context_change=True)
    idle = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    next_work = ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)

    assert work.stage == "DO_USER_WORK"
    assert done.stage == "ITERATION_DONE"
    assert idle.stage == "IDLE"
    assert "--open-iteration" in idle.message
    assert next_work.stage == "DO_USER_WORK"


def test_front_desk_bell_close_iteration_closes_journal_required(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)
    journal = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    closed = ring(task, workspace=tmp_path, agent="codex", session_id="s1", close_iteration=True)
    idle = ring(task, workspace=tmp_path, agent="codex", session_id="s1")

    assert journal.stage == "JOURNAL_REQUIRED"
    assert closed.stage == "ITERATION_DONE"
    assert "explicitly closed" in closed.message
    assert idle.stage == "IDLE"


def test_front_desk_bell_ack_no_context_change_closes_journal_required(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    initialize_task_layout(task, workspace=tmp_path)
    _fill_required_slots(task)

    ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    ring(task, workspace=tmp_path, agent="codex", session_id="s1", open_iteration=True)
    journal = ring(task, workspace=tmp_path, agent="codex", session_id="s1")
    done = ring(task, workspace=tmp_path, agent="codex", session_id="s1", ack_no_context_change=True)

    assert journal.stage == "JOURNAL_REQUIRED"
    assert done.stage == "ITERATION_DONE"


def _fill_required_slots(task: Path) -> None:
    set_slot(task, "goal", "Goal.", updated_at="2026-01-01T00:00:00+00:00")
    set_slot(task, "operational-memory", "Current: ready.", updated_at="2026-01-01T00:00:00+00:00")
    set_slot(task, "env", "Use local env.", updated_at="2026-01-01T00:00:00+00:00")
    set_slot(task, "validation", "Run smoke.", updated_at="2026-01-01T00:00:00+00:00")
