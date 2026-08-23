"""Public API for Codex hook subscriptions."""

from __future__ import annotations

from ..src.hooks import CodexHookCommandResult
from ..src.hooks import CodexHookEvent
from ..src.hooks import CodexHookRegistry
from ..src.hooks import CodexHookRequest
from ..src.hooks import CodexHookResult
from ..src.hooks import CodexHookSubscription
from ..src.hooks import HookCallback
from ..src.hooks import clear_subscriptions
from ..src.hooks import codex_hooks_config
from ..src.hooks import dispatch
from ..src.hooks import handle_command_hook
from ..src.hooks import main
from ..src.hooks import subscribe
from ..src.hooks import subscribe_all

__all__ = [
    "CodexHookCommandResult",
    "CodexHookEvent",
    "CodexHookRegistry",
    "CodexHookRequest",
    "CodexHookResult",
    "CodexHookSubscription",
    "HookCallback",
    "clear_subscriptions",
    "codex_hooks_config",
    "dispatch",
    "handle_command_hook",
    "main",
    "subscribe",
    "subscribe_all",
]
