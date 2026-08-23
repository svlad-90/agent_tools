from __future__ import annotations

import json
from pathlib import Path

from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookEvent
from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookRegistry
from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookRequest
from agent_tools.agent_workspace.components.codex_hooks.api import clear_subscriptions
from agent_tools.agent_workspace.components.codex_hooks.api import codex_hooks_config
from agent_tools.agent_workspace.components.codex_hooks.api import dispatch
from agent_tools.agent_workspace.components.codex_hooks.api import handle_command_hook
from agent_tools.agent_workspace.components.codex_hooks.api import subscribe
from agent_tools.agent_workspace.components.codex_hooks.api import subscribe_all


def test_codex_hook_registry_dispatches_matching_event_subscribers(tmp_path: Path) -> None:
    registry = CodexHookRegistry()
    seen: list[CodexHookRequest] = []

    registry.subscribe(
        CodexHookEvent.USER_PROMPT_SUBMIT,
        lambda request: seen.append(request) or {"systemMessage": "ok"},
        subscriber_id="a",
    )
    registry.subscribe(CodexHookEvent.STOP, lambda request: "ignored", subscriber_id="b")

    request = CodexHookRequest(
        event=CodexHookEvent.USER_PROMPT_SUBMIT,
        payload={"hook_event_name": "UserPromptSubmit", "prompt": "hello"},
        task_dir=tmp_path / "task",
        workspace=tmp_path,
        session_id="session-1",
    )

    results = registry.dispatch(request)

    assert seen == [request]
    assert [(result.subscriber_id, result.value, result.error) for result in results] == [
        ("a", {"systemMessage": "ok"}, None)
    ]


def test_codex_hook_registry_dispatches_all_after_exact() -> None:
    registry = CodexHookRegistry()
    calls: list[str] = []

    registry.subscribe_all(lambda request: calls.append("all") or "all", subscriber_id="all")
    registry.subscribe(CodexHookEvent.PRE_TOOL_USE, lambda request: calls.append("exact") or "one", subscriber_id="one")

    results = registry.dispatch(CodexHookRequest(event=CodexHookEvent.PRE_TOOL_USE, payload={}))

    assert calls == ["exact", "all"]
    assert [result.value for result in results] == ["one", "all"]


def test_codex_hook_subscription_can_unsubscribe() -> None:
    registry = CodexHookRegistry()
    subscription = registry.subscribe(CodexHookEvent.POST_TOOL_USE, lambda request: "called", subscriber_id="one")

    assert subscription.unsubscribe()
    assert not subscription.unsubscribe()
    assert registry.dispatch(CodexHookRequest(event=CodexHookEvent.POST_TOOL_USE, payload={})) == ()


def test_codex_hook_dispatch_returns_callback_errors() -> None:
    registry = CodexHookRegistry()

    def fail(_: CodexHookRequest) -> None:
        raise RuntimeError("nope")

    registry.subscribe(CodexHookEvent.PRE_TOOL_USE, fail, subscriber_id="broken")

    results = registry.dispatch(CodexHookRequest(event=CodexHookEvent.PRE_TOOL_USE, payload={}))

    assert len(results) == 1
    assert results[0].subscriber_id == "broken"
    assert results[0].value is None
    assert results[0].error == "nope"


def test_codex_hook_module_default_registry_is_clearable() -> None:
    clear_subscriptions()
    subscribe(CodexHookEvent.USER_PROMPT_SUBMIT, lambda request: request.payload["prompt"], subscriber_id="one")

    request = CodexHookRequest(event=CodexHookEvent.USER_PROMPT_SUBMIT, payload={"prompt": "hello"})
    assert [result.value for result in dispatch(request)] == ["hello"]

    clear_subscriptions()
    assert dispatch(request) == ()


def test_codex_hook_rejects_non_enum_event() -> None:
    registry = CodexHookRegistry()

    try:
        registry.subscribe("UserPromptSubmit", lambda request: None)  # type: ignore[arg-type]
    except TypeError as exc:
        assert str(exc) == "event must be a CodexHookEvent"
    else:
        raise AssertionError("string hook name was accepted")


def test_codex_hooks_config_registers_all_concrete_events() -> None:
    config = codex_hooks_config("python -m agent_tools.agent_workspace.components.codex_hooks.api")

    assert "*" not in config
    assert set(config) == {event.value for event in CodexHookEvent if event is not CodexHookEvent.ALL}
    assert config["UserPromptSubmit"][0]["hooks"][0]["type"] == "command"


def test_codex_command_hook_reads_stdin_and_returns_json() -> None:
    registry = CodexHookRegistry()
    registry.subscribe(CodexHookEvent.USER_PROMPT_SUBMIT, lambda request: "context", subscriber_id="one")
    registry.subscribe_all(lambda request: {"systemMessage": "global"}, subscriber_id="all")

    result = handle_command_hook(
        json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"}),
        registry=registry,
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"systemMessage": "context\nglobal"}


def test_codex_command_hook_reports_invalid_event() -> None:
    result = handle_command_hook(json.dumps({"hook_event_name": "Missing"}))

    assert result.exit_code == 1
    assert "Unsupported Codex hook event" in result.stderr
