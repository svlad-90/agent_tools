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
tracks stdout and stderr separately with estimated token budgets, and leaves
normal output unchanged while it stays under the limit. On overflow it keeps
streaming only a bounded head preview, then stores later output in full logs
and in per-stream tail buffers. When the command exits, the wrapper emits a
final bounded summary:

- the configured and observed token counts;
- the original command exit code;
- a stdout/stderr head budget summary;
- a bounded stdout tail preview;
- a bounded stderr tail preview with reserved budget so noisy stdout cannot
  hide diagnostics;
- paths to complete stdout, stderr, and metadata logs;
- a reminder to rerun with narrower output.

Wrapper service blocks use `--- limited_bash: ... ---` delimiters. One-line
runtime notices use a `[limited_bash]` prefix. Long-running commands also get a
separate capped heartbeat budget that reports interval stdout/stderr line and
token counts plus tiny recent snippets after overflow. After that heartbeat
detail budget is exhausted, the wrapper continues to emit short heartbeat
notices with interval statistics and log paths, but without log snippets.
Complete logs are published only on overflow or heartbeat emission, under the task's
`report/logs/limited-bash/` directory when `AGENT_TOOLS_TASK_DIR` or
`PAF_TASK_DIR` is available.

Command entry points:

```sh
python -m agent_tools.agent_workspace.components.harness_adapter.codex
python -m agent_tools.agent_workspace.components.harness_adapter.claude
python -m agent_tools.agent_workspace.components.harness_adapter.limited_bash
```
