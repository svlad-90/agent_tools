# Harness Adapter Component

`harness_adapter` owns Agent Workspace integration with supported agent
harness hooks. It is the single component that knows how Codex and Claude Code
represent hook events.

Public callers use `components.harness_adapter.api` for:

- Codex and Claude hook configuration snippets used by `agent_runtime`;
- hook/status enums shared with frontends;
- runtime status subscriptions;
- debug event loading/clearing for UI panes;
- `record_harness_status()` for local runtime events that do not come from a
  harness hook, such as manual terminal interruption.

Codex-specific and Claude-specific event parsing, command handling, and policy
registration are implementation details under `src/`.

The policy layer maps harness events to task status:

```text
● session started/restored or Stop allowed
▶ user prompt received
⚙ tool started
▷ tool finished, agent can continue
○ manual interruption recorded by the UI
```

Stop and compact hooks enforce task context freshness. They use
`TASK_CONTEXT.sqlite3` slots as the durable state source and emit blocking hook
output only when policy requires agent action.

Command entry points:

```sh
python -m agent_tools.agent_workspace.components.harness_adapter.codex
python -m agent_tools.agent_workspace.components.harness_adapter.claude
```
