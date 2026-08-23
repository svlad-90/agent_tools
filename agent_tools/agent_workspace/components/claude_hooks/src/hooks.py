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


class ClaudeHookEvent(StrEnum):
    ALL = "*"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    SETUP = "Setup"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    USER_PROMPT_EXPANSION = "UserPromptExpansion"
    PRE_TOOL_USE = "PreToolUse"
    PERMISSION_REQUEST = "PermissionRequest"
    PERMISSION_DENIED = "PermissionDenied"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    POST_TOOL_BATCH = "PostToolBatch"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    TEAMMATE_IDLE = "TeammateIdle"
    PRE_COMPACT = "PreCompact"
    POST_COMPACT = "PostCompact"
    CONFIG_CHANGE = "ConfigChange"
    CWD_CHANGED = "CwdChanged"
    ELICITATION = "Elicitation"
    ELICITATION_RESULT = "ElicitationResult"
    FILE_CHANGED = "FileChanged"
    INSTRUCTIONS_LOADED = "InstructionsLoaded"
    NOTIFICATION = "Notification"
    WORKTREE_CREATE = "WorktreeCreate"
    WORKTREE_REMOVE = "WorktreeRemove"


HookCallback = Callable[["ClaudeHookRequest"], Any]


@dataclass(frozen=True)
class ClaudeHookRequest:
    event: ClaudeHookEvent
    payload: dict[str, Any]
    task_dir: Path | None = None
    workspace: Path | None = None
    session_id: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ClaudeHookRequest":
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
class ClaudeHookResult:
    subscriber_id: str
    value: Any = None
    error: str | None = None


@dataclass(frozen=True)
class ClaudeHookSubscription:
    event: ClaudeHookEvent
    subscriber_id: str
    unsubscribe: Callable[[], bool]


@dataclass(frozen=True)
class ClaudeHookCommandResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


class ClaudeHookRegistry:
    def __init__(self) -> None:
        self._callbacks: dict[ClaudeHookEvent, dict[str, HookCallback]] = defaultdict(dict)

    def subscribe(
        self,
        event: ClaudeHookEvent,
        callback: HookCallback,
        *,
        subscriber_id: str | None = None,
    ) -> ClaudeHookSubscription:
        event = _normalize_event(event)
        subscriber_id = subscriber_id or uuid4().hex
        self._callbacks[event][subscriber_id] = callback
        return ClaudeHookSubscription(
            event=event,
            subscriber_id=subscriber_id,
            unsubscribe=lambda: self.unsubscribe(event, subscriber_id),
        )

    def subscribe_all(
        self,
        callback: HookCallback,
        *,
        subscriber_id: str | None = None,
    ) -> ClaudeHookSubscription:
        return self.subscribe(ClaudeHookEvent.ALL, callback, subscriber_id=subscriber_id)

    def unsubscribe(self, event: ClaudeHookEvent, subscriber_id: str) -> bool:
        event = _normalize_event(event)
        callbacks = self._callbacks.get(event)
        if callbacks is None or subscriber_id not in callbacks:
            return False
        del callbacks[subscriber_id]
        if not callbacks:
            self._callbacks.pop(event, None)
        return True

    def dispatch(self, request: ClaudeHookRequest) -> tuple[ClaudeHookResult, ...]:
        callbacks = list(self._callbacks.get(request.event, {}).items())
        callbacks.extend(self._callbacks.get(ClaudeHookEvent.ALL, {}).items())
        results: list[ClaudeHookResult] = []
        for subscriber_id, callback in callbacks:
            try:
                results.append(ClaudeHookResult(subscriber_id=subscriber_id, value=callback(request)))
            except Exception as exc:  # Hook policy errors are returned to the adapter caller.
                results.append(ClaudeHookResult(subscriber_id=subscriber_id, error=str(exc)))
        return tuple(results)

    def clear(self) -> None:
        self._callbacks.clear()


_DEFAULT_REGISTRY = ClaudeHookRegistry()


def subscribe(
    event: ClaudeHookEvent,
    callback: HookCallback,
    *,
    subscriber_id: str | None = None,
) -> ClaudeHookSubscription:
    return _DEFAULT_REGISTRY.subscribe(event, callback, subscriber_id=subscriber_id)


def subscribe_all(
    callback: HookCallback,
    *,
    subscriber_id: str | None = None,
) -> ClaudeHookSubscription:
    return _DEFAULT_REGISTRY.subscribe_all(callback, subscriber_id=subscriber_id)


def dispatch(request: ClaudeHookRequest) -> tuple[ClaudeHookResult, ...]:
    return _DEFAULT_REGISTRY.dispatch(request)


def clear_subscriptions() -> None:
    _DEFAULT_REGISTRY.clear()


def claude_hooks_settings(command: str) -> dict[str, Any]:
    return {
        "hooks": {
            event.value: [{"hooks": [{"type": "command", "command": command}]}]
            for event in ClaudeHookEvent
            if event is not ClaudeHookEvent.ALL
        }
    }


def handle_command_hook(
    stdin_text: str,
    *,
    registry: ClaudeHookRegistry | None = None,
) -> ClaudeHookCommandResult:
    registry = registry or _DEFAULT_REGISTRY
    try:
        payload = json.loads(stdin_text or "{}")
    except json.JSONDecodeError as exc:
        return ClaudeHookCommandResult(exit_code=1, stderr=f"Invalid Claude hook JSON: {exc}")
    if not isinstance(payload, dict):
        return ClaudeHookCommandResult(exit_code=1, stderr="Claude hook input must be a JSON object")
    try:
        request = ClaudeHookRequest.from_payload(payload)
    except ValueError as exc:
        return ClaudeHookCommandResult(exit_code=1, stderr=str(exc))
    return _command_result_from_hook_results(registry.dispatch(request))


def main() -> int:
    result = handle_command_hook(sys.stdin.read())
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.exit_code


def _command_result_from_hook_results(results: tuple[ClaudeHookResult, ...]) -> ClaudeHookCommandResult:
    output: dict[str, Any] = {}
    errors = [result.error for result in results if result.error]
    for result in results:
        if result.error or result.value is None:
            continue
        if isinstance(result.value, str):
            _merge_hook_output(output, {"hookSpecificOutput": {"additionalContext": result.value}})
        elif isinstance(result.value, dict):
            _merge_hook_output(output, result.value)
        else:
            _merge_hook_output(output, {"hookSpecificOutput": {"additionalContext": str(result.value)}})
    if errors:
        _merge_hook_output(output, {"hookSpecificOutput": {"additionalContext": "\n".join(errors)}})
    stdout = f"{json.dumps(output, ensure_ascii=False)}\n" if output else ""
    return ClaudeHookCommandResult(exit_code=0, stdout=stdout)


def _merge_hook_output(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key in {"additionalContext", "reason"} and isinstance(value, str):
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


def _event_from_payload(payload: dict[str, Any]) -> ClaudeHookEvent:
    value = payload.get("hook_event_name") or payload.get("event") or payload.get("hookEventName")
    if not isinstance(value, str) or not value:
        raise ValueError("Claude hook input is missing hook_event_name")
    try:
        return ClaudeHookEvent(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported Claude hook event: {value}") from exc


def _normalize_event(event: ClaudeHookEvent) -> ClaudeHookEvent:
    if not isinstance(event, ClaudeHookEvent):
        raise TypeError("event must be a ClaudeHookEvent")
    return event


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _path_or_none(value: Any) -> Path | None:
    return Path(value) if isinstance(value, str) and value else None
