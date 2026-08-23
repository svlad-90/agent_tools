from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


class CodexHookEvent(StrEnum):
    ALL = "*"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_COMPACT = "PreCompact"
    POST_COMPACT = "PostCompact"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    STOP = "Stop"


HookCallback = Callable[["CodexHookRequest"], Any]


@dataclass(frozen=True)
class CodexHookRequest:
    event: CodexHookEvent
    payload: dict[str, Any]
    task_dir: Path | None = None
    workspace: Path | None = None
    session_id: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CodexHookRequest":
        event = _event_from_payload(payload)
        cwd = payload.get("cwd")
        task_dir = payload.get("task_dir") or payload.get("taskDirectory") or payload.get("taskDir")
        workspace = payload.get("workspace")
        return cls(
            event=event,
            payload=payload,
            task_dir=_path_or_none(task_dir) or _path_or_none(os.environ.get("AGENT_TOOLS_TASK_DIR")),
            workspace=_path_or_none(workspace) or _path_or_none(cwd) or _path_or_none(os.environ.get("AGENT_TOOLS_WORKSPACE")),
            session_id=_string_or_none(payload.get("session_id")) or _string_or_none(os.environ.get("AGENT_TOOLS_SESSION_ID")),
        )


@dataclass(frozen=True)
class CodexHookResult:
    subscriber_id: str
    value: Any = None
    error: str | None = None


@dataclass(frozen=True)
class CodexHookSubscription:
    event: CodexHookEvent
    subscriber_id: str
    unsubscribe: Callable[[], bool]


@dataclass(frozen=True)
class CodexHookCommandResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


class CodexHookRegistry:
    def __init__(self) -> None:
        self._callbacks: dict[CodexHookEvent, dict[str, HookCallback]] = defaultdict(dict)

    def subscribe(
        self,
        event: CodexHookEvent,
        callback: HookCallback,
        *,
        subscriber_id: str | None = None,
    ) -> CodexHookSubscription:
        event = _normalize_event(event)
        subscriber_id = subscriber_id or uuid4().hex
        self._callbacks[event][subscriber_id] = callback
        return CodexHookSubscription(
            event=event,
            subscriber_id=subscriber_id,
            unsubscribe=lambda: self.unsubscribe(event, subscriber_id),
        )

    def subscribe_all(
        self,
        callback: HookCallback,
        *,
        subscriber_id: str | None = None,
    ) -> CodexHookSubscription:
        return self.subscribe(CodexHookEvent.ALL, callback, subscriber_id=subscriber_id)

    def unsubscribe(self, event: CodexHookEvent, subscriber_id: str) -> bool:
        event = _normalize_event(event)
        callbacks = self._callbacks.get(event)
        if callbacks is None or subscriber_id not in callbacks:
            return False
        del callbacks[subscriber_id]
        if not callbacks:
            self._callbacks.pop(event, None)
        return True

    def dispatch(self, request: CodexHookRequest) -> tuple[CodexHookResult, ...]:
        callbacks = list(self._callbacks.get(request.event, {}).items())
        callbacks.extend(self._callbacks.get(CodexHookEvent.ALL, {}).items())
        results: list[CodexHookResult] = []
        for subscriber_id, callback in callbacks:
            try:
                results.append(CodexHookResult(subscriber_id=subscriber_id, value=callback(request)))
            except Exception as exc:  # Hook policy errors are returned to the adapter caller.
                results.append(CodexHookResult(subscriber_id=subscriber_id, error=str(exc)))
        return tuple(results)

    def clear(self) -> None:
        self._callbacks.clear()


_DEFAULT_REGISTRY = CodexHookRegistry()


def subscribe(
    event: CodexHookEvent,
    callback: HookCallback,
    *,
    subscriber_id: str | None = None,
) -> CodexHookSubscription:
    return _DEFAULT_REGISTRY.subscribe(event, callback, subscriber_id=subscriber_id)


def subscribe_all(
    callback: HookCallback,
    *,
    subscriber_id: str | None = None,
) -> CodexHookSubscription:
    return _DEFAULT_REGISTRY.subscribe_all(callback, subscriber_id=subscriber_id)


def dispatch(request: CodexHookRequest) -> tuple[CodexHookResult, ...]:
    return _DEFAULT_REGISTRY.dispatch(request)


def clear_subscriptions() -> None:
    _DEFAULT_REGISTRY.clear()


def codex_hooks_config(command: str) -> dict[str, list[dict[str, Any]]]:
    return {
        event.value: [{"hooks": [{"type": "command", "command": command}]}]
        for event in CodexHookEvent
        if event is not CodexHookEvent.ALL
    }


def handle_command_hook(
    stdin_text: str,
    *,
    registry: CodexHookRegistry | None = None,
) -> CodexHookCommandResult:
    registry = registry or _DEFAULT_REGISTRY
    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError as exc:
        return CodexHookCommandResult(exit_code=1, stderr=f"Invalid Codex hook JSON: {exc}")
    if not isinstance(payload, dict):
        return CodexHookCommandResult(exit_code=1, stderr="Codex hook input must be a JSON object")
    try:
        request = CodexHookRequest.from_payload(payload)
    except ValueError as exc:
        return CodexHookCommandResult(exit_code=1, stderr=str(exc))
    return _command_result_from_hook_results(registry.dispatch(request))


def main() -> int:
    result = handle_command_hook(sys.stdin.read())
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.exit_code


def _command_result_from_hook_results(results: tuple[CodexHookResult, ...]) -> CodexHookCommandResult:
    output: dict[str, Any] = {}
    errors = [result.error for result in results if result.error]
    for result in results:
        if result.error or result.value is None:
            continue
        if isinstance(result.value, str):
            _append_text(output, "systemMessage", result.value)
        elif isinstance(result.value, dict):
            _merge_hook_output(output, result.value)
        else:
            _append_text(output, "systemMessage", str(result.value))
    if errors:
        _append_text(output, "systemMessage", "\n".join(errors))
    stdout = f"{json.dumps(output, ensure_ascii=False)}\n" if output else ""
    return CodexHookCommandResult(exit_code=0, stdout=stdout)


def _merge_hook_output(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key in {"systemMessage", "stopReason", "reason"} and isinstance(value, str):
            _append_text(target, key, value)
        elif key == "hookSpecificOutput" and isinstance(value, dict):
            nested = target.setdefault(key, {})
            if isinstance(nested, dict):
                _merge_hook_output(nested, value)
        else:
            target[key] = value


def _append_text(target: dict[str, Any], key: str, value: str) -> None:
    if not value:
        return
    previous = target.get(key)
    target[key] = f"{previous}\n{value}" if isinstance(previous, str) and previous else value


def _event_from_payload(payload: dict[str, Any]) -> CodexHookEvent:
    value = payload.get("hook_event_name") or payload.get("event") or payload.get("hookEventName")
    if not isinstance(value, str) or not value:
        raise ValueError("Codex hook input is missing hook_event_name")
    try:
        return CodexHookEvent(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported Codex hook event: {value}") from exc


def _normalize_event(event: CodexHookEvent) -> CodexHookEvent:
    if not isinstance(event, CodexHookEvent):
        raise TypeError("event must be a CodexHookEvent")
    return event


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _path_or_none(value: Any) -> Path | None:
    return Path(value) if isinstance(value, str) and value else None
