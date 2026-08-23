"""Public API for Claude hook subscriptions."""

from __future__ import annotations

from ..src.hooks import ClaudeHookCommandResult
from ..src.hooks import ClaudeHookEvent
from ..src.hooks import ClaudeHookRegistry
from ..src.hooks import ClaudeHookRequest
from ..src.hooks import ClaudeHookResult
from ..src.hooks import ClaudeHookSubscription
from ..src.hooks import HookCallback
from ..src.hooks import claude_hooks_settings
from ..src.hooks import clear_subscriptions
from ..src.hooks import dispatch
from ..src.hooks import handle_command_hook
from ..src.hooks import main
from ..src.hooks import subscribe
from ..src.hooks import subscribe_all

__all__ = [
    "ClaudeHookCommandResult",
    "ClaudeHookEvent",
    "ClaudeHookRegistry",
    "ClaudeHookRequest",
    "ClaudeHookResult",
    "ClaudeHookSubscription",
    "HookCallback",
    "claude_hooks_settings",
    "clear_subscriptions",
    "dispatch",
    "handle_command_hook",
    "main",
    "subscribe",
    "subscribe_all",
]
