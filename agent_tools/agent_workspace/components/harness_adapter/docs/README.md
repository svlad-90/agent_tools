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

`PreToolUse` wraps Bash tool calls for both Codex and Claude Code with the
`limited_bash` runner. The wrapper executes the original command through Bash,
counts combined stdout/stderr output with an estimated token limit, and leaves
normal output unchanged while it stays under the limit. When output exceeds the
limit, the wrapper returns a concise message instead of the full output:

- the configured and observed token counts;
- a bounded stdout preview with the first 10 and last 10 logical lines;
- a bounded stderr preview with the same shape when stderr is present;
- a reminder to rerun with narrower output;
- paths to complete stdout, stderr, and metadata logs.

Preview lines are individually capped so a single long line cannot flood agent
context. Complete logs are published only on overflow, under the task's
`report/logs/limited-bash/` directory when `AGENT_TOOLS_TASK_DIR` or
`PAF_TASK_DIR` is available.

Command entry points:

```sh
python -m agent_tools.agent_workspace.components.harness_adapter.codex
python -m agent_tools.agent_workspace.components.harness_adapter.claude
python -m agent_tools.agent_workspace.components.harness_adapter.limited_bash
```
