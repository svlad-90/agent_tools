"""Public API for Agent Workspace harness adapters."""

from __future__ import annotations

from typing import Any

from ..src.claude_adapter import ClaudeHookEvent as ClaudeHarnessEvent
from ..src.claude_adapter import claude_harness_settings as _claude_harness_settings
from ..src.codex_adapter import CodexHookEvent as CodexHarnessEvent
from ..src.codex_adapter import codex_harness_config as _codex_harness_config
from ..src.policy import AgentHookEvent
from ..src.policy import AgentType
from ..src.policy import HarnessDebugEvent
from ..src.policy import HarnessStatusEvent
from ..src.policy import HarnessStatusSubscription
from ..src.policy import HarnessStatusUpdate
from ..src.policy import StatusCallback
from ..src.policy import clear_harness_debug_events
from ..src.policy import clear_harness_status_subscriptions
from ..src.policy import load_harness_debug_events
from ..src.policy import subscribe_harness_status


def claude_harness_settings(command: str) -> dict[str, Any]:
    return _claude_harness_settings(command)


def codex_harness_config(command: str) -> dict[str, list[dict[str, Any]]]:
    return _codex_harness_config(command)


__all__ = [
    "AgentHookEvent",
    "AgentType",
    "ClaudeHarnessEvent",
    "CodexHarnessEvent",
    "HarnessDebugEvent",
    "HarnessStatusEvent",
    "HarnessStatusSubscription",
    "HarnessStatusUpdate",
    "StatusCallback",
    "claude_harness_settings",
    "clear_harness_debug_events",
    "clear_harness_status_subscriptions",
    "codex_harness_config",
    "load_harness_debug_events",
    "subscribe_harness_status",
]
