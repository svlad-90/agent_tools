from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import ClaudeHookEvent
from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import ClaudeHookRegistry
from agent_tools.agent_workspace.components.harness_adapter.src.claude_adapter import handle_command_hook as handle_claude_hook
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import CodexHookEvent
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import CodexHookRegistry
from agent_tools.agent_workspace.components.harness_adapter.src.codex_adapter import handle_command_hook as handle_codex_hook
from agent_tools.agent_workspace.components.harness_adapter.api import AgentType
from agent_tools.agent_workspace.components.harness_adapter.api import HarnessStatusEvent
from agent_tools.agent_workspace.components.harness_adapter.api import clear_harness_debug_events
from agent_tools.agent_workspace.components.harness_adapter.api import clear_harness_status_subscriptions
from agent_tools.agent_workspace.components.harness_adapter.api import load_harness_debug_events
from agent_tools.agent_workspace.components.harness_adapter.api import record_harness_status
from agent_tools.agent_workspace.components.harness_adapter.api import subscribe_harness_status
from agent_tools.agent_workspace.components.harness_adapter.src.claude_policy import register_claude_adapter
from agent_tools.agent_workspace.components.harness_adapter.src.commands import handle_claude_adapter_hook
from agent_tools.agent_workspace.components.harness_adapter.src.commands import handle_codex_adapter_hook
from agent_tools.agent_workspace.components.harness_adapter.src.codex_policy import register_codex_adapter
from agent_tools.tools.task_context import database_path
from agent_tools.tools.task_context import ensure_database
from agent_tools.tools.task_context import set_slot


def test_harness_adapter_emits_status_updates_for_codex_prompt(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)
    seen: list[HarnessStatusEvent] = []
    clear_harness_status_subscriptions()
    subscribe_harness_status(lambda update: seen.append(update.event))

    result = handle_codex_hook(
        json.dumps({"hook_event_name": CodexHookEvent.USER_PROMPT_SUBMIT.value, "task_dir": str(task_dir), "session_id": "s1"}),
        registry=registry,
    )

    assert result.exit_code == 0
    assert HarnessStatusEvent.USER_PROMPT_RECEIVED in seen
    assert result.stdout == ""


def test_harness_adapter_blocks_codex_stop_after_work_without_journal_update(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    _codex(registry, task_dir, CodexHookEvent.USER_PROMPT_SUBMIT)
    _codex(registry, task_dir, CodexHookEvent.POST_TOOL_USE)
    result = _codex(registry, task_dir, CodexHookEvent.STOP)

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert "Stop blocked" in output["reason"]


def test_harness_adapter_allows_codex_stop_after_journal_update(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    _codex(registry, task_dir, CodexHookEvent.USER_PROMPT_SUBMIT)
    _codex(registry, task_dir, CodexHookEvent.POST_TOOL_USE)
    set_slot(task_dir, "operational-memory", "Updated after prompt.", updated_at="2999-01-01T00:00:00+00:00")
    result = _codex(registry, task_dir, CodexHookEvent.STOP)

    assert result.exit_code == 0
    assert result.stdout == ""


def test_harness_adapter_precompact_is_silent_when_current(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = ClaudeHookRegistry()
    register_claude_adapter(registry)

    result = handle_claude_hook(
        json.dumps({"hook_event_name": ClaudeHookEvent.PRE_COMPACT.value, "task_dir": str(task_dir), "session_id": "s1"}),
        registry=registry,
    )

    assert result.exit_code == 0
    assert result.stdout == ""


def test_harness_adapter_precompact_logs_pending_codex_checkpoint_when_journal_is_stale(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    clear_harness_debug_events(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    _codex(registry, task_dir, CodexHookEvent.USER_PROMPT_SUBMIT)
    _codex(registry, task_dir, CodexHookEvent.POST_TOOL_USE)
    result = _codex(registry, task_dir, CodexHookEvent.PRE_COMPACT)
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert result.exit_code == 0
    assert result.stdout == ""
    assert events[-1].hook_event == "pre_compact"
    assert events[-1].status_event is HarnessStatusEvent.JOURNAL_REQUIRED
    assert events[-1].outcome == "pending"


def test_harness_adapter_precompact_logs_pending_claude_checkpoint_when_journal_is_stale(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    clear_harness_debug_events(tmp_path)
    registry = ClaudeHookRegistry()
    register_claude_adapter(registry)

    _claude(registry, task_dir, ClaudeHookEvent.USER_PROMPT_SUBMIT)
    _claude(registry, task_dir, ClaudeHookEvent.POST_TOOL_USE)
    result = _claude(registry, task_dir, ClaudeHookEvent.PRE_COMPACT)
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert result.exit_code == 0
    assert result.stdout == ""
    assert events[-1].hook_event == "pre_compact"
    assert events[-1].status_event is HarnessStatusEvent.JOURNAL_REQUIRED
    assert events[-1].outcome == "pending"


def test_harness_adapter_postcompact_injects_current_task_slots(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = ClaudeHookRegistry()
    register_claude_adapter(registry)

    result = handle_claude_hook(
        json.dumps({"hook_event_name": ClaudeHookEvent.POST_COMPACT.value, "task_dir": str(task_dir), "session_id": "s1"}),
        registry=registry,
    )

    assert result.exit_code == 0
    additional_context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Current task state from TASK_CONTEXT.sqlite3 is injected below" in additional_context
    assert "Test goal." in additional_context
    assert "Initial memory." in additional_context


def test_harness_adapter_codex_command_entrypoint_registers_default_adapter(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)

    result = handle_codex_adapter_hook(
        json.dumps({"hook_event_name": CodexHookEvent.USER_PROMPT_SUBMIT.value, "task_dir": str(task_dir), "session_id": "s1"})
    )

    assert result.exit_code == 0
    assert result.stdout == ""


def test_harness_adapter_claude_command_entrypoint_registers_default_adapter(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)

    result = handle_claude_adapter_hook(
        json.dumps({"hook_event_name": ClaudeHookEvent.USER_PROMPT_SUBMIT.value, "task_dir": str(task_dir), "session_id": "s1"})
    )

    assert result.exit_code == 0
    assert result.stdout == ""


def test_harness_adapter_records_debug_events_with_tool_name(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    clear_harness_debug_events(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    result = handle_codex_hook(
        json.dumps(
            {
                "hook_event_name": CodexHookEvent.PRE_TOOL_USE.value,
                "task_dir": str(task_dir),
                "session_id": "s1",
                "tool_name": "exec_command",
                "tool_input": {"command": "python3 -m pytest agent_tools/agent_workspace/components/harness_adapter/tests"},
            }
        ),
        registry=registry,
    )
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert result.exit_code == 0
    assert events[-1].hook_event == "pre_tool_use"
    assert events[-1].status_event is HarnessStatusEvent.TOOL_STARTED
    assert events[-1].tool_name == "exec_command"
    assert events[-1].tool_detail.startswith("python3 -m pytest")
    assert events[-1].outcome == "started"
    with sqlite3.connect(database_path(task_dir)) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'harness_debug_events'"
        ).fetchone()
    assert table is None


def test_harness_adapter_records_context_injection_points(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    clear_harness_debug_events(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    _codex(registry, task_dir, CodexHookEvent.SESSION_START)
    _codex(registry, task_dir, CodexHookEvent.USER_PROMPT_SUBMIT)
    _codex(registry, task_dir, CodexHookEvent.POST_COMPACT)
    events = load_harness_debug_events(task_dir, session_id="s1")

    injected = [event for event in events if event.outcome == "injected"]
    assert [event.hook_event for event in injected] == ["session_start", "post_compact"]
    assert injected[0].icon == "●"
    assert all("injected" in event.message for event in injected)


def test_harness_adapter_records_observed_hook_events(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = ClaudeHookRegistry()
    register_claude_adapter(registry)

    result = handle_claude_hook(
        json.dumps(
            {
                "hook_event_name": ClaudeHookEvent.SUBAGENT_START.value,
                "task_dir": str(task_dir),
                "session_id": "s1",
            }
        ),
        registry=registry,
    )
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert result.exit_code == 0
    assert events[-1].hook_event == "subagent_start"
    assert events[-1].status_event is HarnessStatusEvent.HOOK_OBSERVED
    assert events[-1].outcome == "observed"


def test_harness_adapter_tool_finish_returns_task_to_play_icon(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)
    registry = CodexHookRegistry()
    register_codex_adapter(registry)

    _codex(registry, task_dir, CodexHookEvent.POST_TOOL_USE)
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert events[-1].status_event is HarnessStatusEvent.TOOL_FINISHED
    assert events[-1].icon == "▹"
    assert events[-1].outcome == "finished"


def test_harness_adapter_records_runtime_interrupt_status(tmp_path: Path) -> None:
    task_dir = _task(tmp_path)

    record_harness_status(
        task_dir,
        agent_type=AgentType.CODEX,
        session_id="s1",
        event=HarnessStatusEvent.HOOK_OBSERVED,
        icon="○",
        message="Agent interrupt requested.",
        tool_name="terminal",
        outcome="interrupted",
    )
    events = load_harness_debug_events(task_dir, session_id="s1")

    assert events[-1].icon == "○"
    assert events[-1].tool_name == "terminal"
    assert events[-1].outcome == "interrupted"


def _task(tmp_path: Path) -> Path:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    for dirname in ("dev", "Dockerfile", "scripts", "report", "report/diff", "report/puml"):
        (task_dir / dirname).mkdir(parents=True, exist_ok=True)
    ensure_database(task_dir)
    set_slot(task_dir, "goal", "Test goal.")
    set_slot(task_dir, "operational-memory", "Initial memory.")
    return task_dir


def _codex(registry: CodexHookRegistry, task_dir: Path, event: CodexHookEvent):
    return handle_codex_hook(
        json.dumps({"hook_event_name": event.value, "task_dir": str(task_dir), "session_id": "s1"}),
        registry=registry,
    )


def _claude(registry: ClaudeHookRegistry, task_dir: Path, event: ClaudeHookEvent):
    return handle_claude_hook(
        json.dumps({"hook_event_name": event.value, "task_dir": str(task_dir), "session_id": "s1"}),
        registry=registry,
    )
