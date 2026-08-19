---
name: task-context-journal
description: Maintain compact workspace task context using the structured agent_tools.tools.task_context database. Use whenever Codex starts, updates, queries, compacts, or hands off TASK_CONTEXT.md, TASK_CONTEXT.sqlite3, task decisions, validation notes, blockers, build notes, environment notes, or other task working context.
---

# Task Context Journal

Use the workspace implementation at `agent_tools/tools/task_context`. Do not
turn `TASK_CONTEXT.md` into an unbounded history file.

Also follow `agent_tools/rules/task-workflow.md`; that rule is authoritative
for task context policy.

## Core Idea

`TASK_CONTEXT.sqlite3` is the durable transactional journal.
`TASK_CONTEXT.md` is the compact active working set generated from that database.

The model decides what is worth recording. The tool owns timestamps, severity,
labels, filtering, and compaction.

## Severity

Use the lowest severity that still protects future work:

- `note`: background or breadcrumb; usually not compacted.
- `low`: minor useful detail.
- `mid`: normal working context.
- `high`: important decision, validation result, blocker, environment fact.
- `critical`: active blocker, safety issue, data-loss risk, must-read fact.

Use `status=active` for facts that should affect current work. Use
`status=resolved` for old blockers or completed investigations that should stay
queryable but not pollute the active context.

## Common Labels

Prefer a few stable labels: `goal`, `repo`, `decision`, `blocker`,
`validation`, `build`, `runtime`, `env`, `artifact`, `report`, `ui`, `bug`,
`test`, `user-preference`, `next-step`.

## Commands

Append a finding:

```sh
python3 -m agent_tools.tools.task_context add \
  --task tasks/<task-name> \
  --severity high \
  --label validation \
  --label build \
  "Docker pytest passed for Agent Workspace"
```

Query a filtered slice:

```sh
python3 -m agent_tools.tools.task_context query \
  --task tasks/<task-name> \
  --since 2026-08-19 \
  --severity mid..critical \
  --label validation \
  --format markdown
```

Regenerate compact active context:

```sh
python3 -m agent_tools.tools.task_context compact \
  --task tasks/<task-name> \
  --severity mid..critical \
  --status active
```

## Workflow

1. At task start, read `TASK_CONTEXT.md` first. Query the journal only when you
   need older, resolved, lower-severity, or label-specific history.
2. When a useful fact appears, add it with `task_context add` instead of
   manually growing `TASK_CONTEXT.md`.
3. Before handoff, after validation, or after resolving a blocker, run
   `task_context compact` so the next session starts from a short active
   context.
4. Keep details concise. Link logs, reports, commits, and artifacts instead of
   pasting long output into journal entries.
