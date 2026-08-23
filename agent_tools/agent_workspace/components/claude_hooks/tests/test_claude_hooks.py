from __future__ import annotations

import json
from pathlib import Path

from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookEvent
from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookRegistry
from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookRequest
from agent_tools.agent_workspace.components.claude_hooks.api import claude_hooks_settings
from agent_tools.agent_workspace.components.claude_hooks.api import clear_subscriptions
from agent_tools.agent_workspace.components.claude_hooks.api import dispatch
from agent_tools.agent_workspace.components.claude_hooks.api import handle_command_hook
from agent_tools.agent_workspace.components.claude_hooks.api import subscribe
from agent_tools.agent_workspace.components.claude_hooks.api import subscribe_all


def test_claude_hook_registry_dispatches_matching_event_subscribers(tmp_path: Path) -> None:
    registry = ClaudeHookRegistry()
    seen: list[ClaudeHookRequest] = []

    registry.subscribe(
        ClaudeHookEvent.USER_PROMPT_SUBMIT,
        lambda request: seen.append(request) or {"hookSpecificOutput": {"additionalContext": "ok"}},
        subscriber_id="a",
    )
    registry.subscribe(ClaudeHookEvent.STOP, lambda request: "ignored", subscriber_id="b")

    request = ClaudeHookRequest(
        event=ClaudeHookEvent.USER_PROMPT_SUBMIT,
        payload={"hook_event_name": "UserPromptSubmit", "prompt": "hello"},
        task_dir=tmp_path / "task",
        workspace=tmp_path,
        session_id="session-1",
    )

    results = registry.dispatch(request)

    assert seen == [request]
    assert [(result.subscriber_id, result.value, result.error) for result in results] == [
        ("a", {"hookSpecificOutput": {"additionalContext": "ok"}}, None)
    ]


def test_claude_hook_registry_dispatches_all_after_exact() -> None:
    registry = ClaudeHookRegistry()
    calls: list[str] = []

    registry.subscribe_all(lambda request: calls.append("all") or "all", subscriber_id="all")
    registry.subscribe(ClaudeHookEvent.PRE_TOOL_USE, lambda request: calls.append("exact") or "one", subscriber_id="one")

    results = registry.dispatch(ClaudeHookRequest(event=ClaudeHookEvent.PRE_TOOL_USE, payload={}))

    assert calls == ["exact", "all"]
    assert [result.value for result in results] == ["one", "all"]


def test_claude_hook_subscription_can_unsubscribe() -> None:
    registry = ClaudeHookRegistry()
    subscription = registry.subscribe(ClaudeHookEvent.POST_TOOL_USE, lambda request: "called", subscriber_id="one")

    assert subscription.unsubscribe()
    assert not subscription.unsubscribe()
    assert registry.dispatch(ClaudeHookRequest(event=ClaudeHookEvent.POST_TOOL_USE, payload={})) == ()


def test_claude_hook_dispatch_returns_callback_errors() -> None:
    registry = ClaudeHookRegistry()

    def fail(_: ClaudeHookRequest) -> None:
        raise RuntimeError("nope")

    registry.subscribe(ClaudeHookEvent.PRE_TOOL_USE, fail, subscriber_id="broken")

    results = registry.dispatch(ClaudeHookRequest(event=ClaudeHookEvent.PRE_TOOL_USE, payload={}))

    assert len(results) == 1
    assert results[0].subscriber_id == "broken"
    assert results[0].value is None
    assert results[0].error == "nope"


def test_claude_hook_module_default_registry_is_clearable() -> None:
    clear_subscriptions()
    subscribe(ClaudeHookEvent.USER_PROMPT_SUBMIT, lambda request: request.payload["prompt"], subscriber_id="one")

    request = ClaudeHookRequest(event=ClaudeHookEvent.USER_PROMPT_SUBMIT, payload={"prompt": "hello"})
    assert [result.value for result in dispatch(request)] == ["hello"]

    clear_subscriptions()
    assert dispatch(request) == ()


def test_claude_hook_rejects_non_enum_event() -> None:
    registry = ClaudeHookRegistry()

    try:
        registry.subscribe("UserPromptSubmit", lambda request: None)  # type: ignore[arg-type]
    except TypeError as exc:
        assert str(exc) == "event must be a ClaudeHookEvent"
    else:
        raise AssertionError("string hook name was accepted")


def test_claude_hooks_settings_registers_all_concrete_events() -> None:
    settings = claude_hooks_settings("python -m agent_tools.agent_workspace.components.claude_hooks.api")
    hooks = settings["hooks"]

    assert "*" not in hooks
    assert set(hooks) == {event.value for event in ClaudeHookEvent if event is not ClaudeHookEvent.ALL}
    assert hooks["UserPromptSubmit"][0]["hooks"][0]["type"] == "command"


def test_claude_command_hook_reads_stdin_and_returns_json() -> None:
    registry = ClaudeHookRegistry()
    registry.subscribe(ClaudeHookEvent.USER_PROMPT_SUBMIT, lambda request: "context", subscriber_id="one")
    registry.subscribe_all(
        lambda request: {"hookSpecificOutput": {"additionalContext": "global"}},
        subscriber_id="all",
    )

    result = handle_command_hook(
        json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"}),
        registry=registry,
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"hookSpecificOutput": {"additionalContext": "context\nglobal"}}


def test_claude_command_hook_reports_invalid_event() -> None:
    result = handle_command_hook(json.dumps({"hook_event_name": "Missing"}))

    assert result.exit_code == 1
    assert "Unsupported Claude hook event" in result.stderr
