from __future__ import annotations

from typing import Any

from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookEvent
from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookRegistry
from agent_tools.agent_workspace.components.claude_hooks.api import ClaudeHookSubscription

from .policy import AgentHookEvent
from .policy import AgentType
from .policy import HarnessPolicySubscription
from .policy import handle_policy_event
from .policy import unsubscribe_policy_subscriptions


_CLAUDE_EVENT_MAP = {
    ClaudeHookEvent.SESSION_START: AgentHookEvent.SESSION_START,
    ClaudeHookEvent.SESSION_END: AgentHookEvent.SESSION_END,
    ClaudeHookEvent.USER_PROMPT_SUBMIT: AgentHookEvent.USER_PROMPT_SUBMIT,
    ClaudeHookEvent.PRE_TOOL_USE: AgentHookEvent.PRE_TOOL_USE,
    ClaudeHookEvent.POST_TOOL_USE: AgentHookEvent.POST_TOOL_USE,
    ClaudeHookEvent.PRE_COMPACT: AgentHookEvent.PRE_COMPACT,
    ClaudeHookEvent.POST_COMPACT: AgentHookEvent.POST_COMPACT,
    ClaudeHookEvent.SUBAGENT_START: AgentHookEvent.SUBAGENT_START,
    ClaudeHookEvent.SUBAGENT_STOP: AgentHookEvent.SUBAGENT_STOP,
    ClaudeHookEvent.STOP: AgentHookEvent.STOP,
}


def register_claude_policy(registry: ClaudeHookRegistry) -> HarnessPolicySubscription:
    subscriptions: list[ClaudeHookSubscription] = []
    for claude_event, agent_event in _CLAUDE_EVENT_MAP.items():
        subscriptions.append(
            registry.subscribe(
                claude_event,
                lambda request, event=agent_event: handle_policy_event(
                    AgentType.CLAUDE,
                    event,
                    request,
                    format_stop_block=_format_claude_stop_block,
                ),
                subscriber_id=f"harness-policy:{claude_event.value}",
            )
        )
    return HarnessPolicySubscription(
        agent_type=AgentType.CLAUDE,
        unsubscribe=lambda: unsubscribe_policy_subscriptions(subscriptions),
    )


def _format_claude_stop_block(reason: str) -> dict[str, Any]:
    return {"decision": "block", "reason": reason}
