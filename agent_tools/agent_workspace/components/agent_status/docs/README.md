# Agent Status Component

Owns agent output analysis, task status labels, and status tooltip text.

Public callers import from `components.agent_status.api`.

Status rendering has two inputs:

- saved session markers from `task_sessions`;
- live/harness state supplied by the frontend.

The component does not read harness debug storage directly. Frontends pass the
latest harness icon when they have one; otherwise `task_agent_status_text()`
falls back to live process state:

```text
● live agent session is idle
▷ live agent session is busy when the caller supplies the spinner frame
Ⅱ saved session can be resumed
□ no saved session is available
× another Agent Workspace window owns the task agent process
```

Detailed hook/debug symbols such as `▶`, `⚙`, `▷`, and `○` are documented in
the workspace localization catalog and exposed through
`agent_status_tooltip_text()`.
