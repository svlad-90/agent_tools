from __future__ import annotations

from typing import Any

from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookEvent
from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookRegistry
from agent_tools.agent_workspace.components.codex_hooks.api import CodexHookSubscription

from .policy import AgentHookEvent
from .policy import AgentType
from .policy import HarnessPolicySubscription
from .policy import handle_policy_event
from .policy import unsubscribe_policy_subscriptions


_CODEX_EVENT_MAP = {
    CodexHookEvent.SESSION_START: AgentHookEvent.SESSION_START,
    CodexHookEvent.SESSION_END: AgentHookEvent.SESSION_END,
    CodexHookEvent.USER_PROMPT_SUBMIT: AgentHookEvent.USER_PROMPT_SUBMIT,
    CodexHookEvent.PRE_TOOL_USE: AgentHookEvent.PRE_TOOL_USE,
    CodexHookEvent.POST_TOOL_USE: AgentHookEvent.POST_TOOL_USE,
    CodexHookEvent.PRE_COMPACT: AgentHookEvent.PRE_COMPACT,
    CodexHookEvent.POST_COMPACT: AgentHookEvent.POST_COMPACT,
    CodexHookEvent.SUBAGENT_START: AgentHookEvent.SUBAGENT_START,
    CodexHookEvent.SUBAGENT_STOP: AgentHookEvent.SUBAGENT_STOP,
    CodexHookEvent.STOP: AgentHookEvent.STOP,
}


def register_codex_policy(registry: CodexHookRegistry) -> HarnessPolicySubscription:
    subscriptions: list[CodexHookSubscription] = []
    for codex_event, agent_event in _CODEX_EVENT_MAP.items():
        subscriptions.append(
            registry.subscribe(
                codex_event,
                lambda request, event=agent_event: handle_policy_event(
                    AgentType.CODEX,
                    event,
                    request,
                    format_stop_block=_format_codex_stop_block,
                ),
                subscriber_id=f"harness-policy:{codex_event.value}",
            )
        )
    return HarnessPolicySubscription(
        agent_type=AgentType.CODEX,
        unsubscribe=lambda: unsubscribe_policy_subscriptions(subscriptions),
    )


def _format_codex_stop_block(reason: str) -> dict[str, Any]:
    return {"decision": "block", "reason": reason}
