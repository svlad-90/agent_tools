---
name: task-context-journal
description: Maintain compact workspace task context using the structured agent_tools.tools.task_context database. Use whenever Codex starts, updates, queries, compacts, or hands off TASK_CONTEXT.sqlite3, task decisions, validation notes, blockers, build notes, environment notes, or other task working context.
---

# Task Context Journal

Use the workspace implementation at `agent_tools/tools/task_context`. Do not
recreate `TASK_CONTEXT.md`; the sqlite database is the task context source.

Also follow `agent_tools/rules/task-workflow.md`; that rule is authoritative
for task context policy.

## Core Idea

`TASK_CONTEXT.sqlite3` is the durable transactional journal and the task context
source. Active entries are the compact working set; resolved and stale entries
are queryable history.

The model decides what is worth recording. The tool owns timestamps, severity,
labels, filtering, dictionary encoding, and compaction.

Human-facing output renders decoded `summary` and `details` by default. Agent
context should use `--format agent`, which returns encoded entries plus only the
stable task dictionary aliases used by that query result. Dictionary aliases are
task-local immutable identifiers such as `§00`; reuse them when reading encoded
context and do not redefine them. Dictionary ids and values are append-only task
history: they must not be deleted, rewritten, or reused for a different entity.

Maintain the active working set instead of only appending notes. When a new fact
supersedes, resolves, or invalidates older active context, update those older
entries to `resolved` or `stale` in the same handoff window.

When stable domain terminology should keep one identity across sessions, add it
through `python3 -m agent_tools.tools.task_context dictionary --task <task-dir>
--add <term>`. Do not encode terms by hand in journal text; use dictionary
aliases returned by `--format agent`.

Durable internal notes, handoffs, reflections, validation notes, and task
context details must use terse factual engineering prose. Prefer commands,
facts, paths, statuses, risks, and next actions. Avoid praise, motivational
phrasing, narrative recap, hedging, and decorative adjectives. Keep technical
qualifiers when they change behavior or risk.

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
Use `status=stale` for facts that were useful but are now superseded,
misleading, or no longer relevant to the active task.

## Labels

Labels are a fixed vocabulary. Use only: `artifact`, `blocker`, `bug`,
`build`, `cli`, `commit`, `decision`, `docs`, `env`, `filter`, `goal`, `gui`,
`handoff`, `knowledge`, `legacy`, `migration`, `next-step`, `policy`, `push`,
`report`, `repo`, `runtime`, `security`, `superseded`, `task-context`, `test`,
`tooling`, `ui`, `user-preference`, and `validation`.

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

`query` defaults to `--status active` when no status is provided. Query all
history only with `--all-statuses`, or query specific history with explicit
`--status resolved` or `--status stale`.

Batch edit or delete selected entries:

```sh
python3 -m agent_tools.tools.task_context edit \
  --task tasks/<task-name> \
  --label validation \
  --status active \
  --until 2026-08-19 \
  --set-status resolved \
  --add-label superseded
```

Use `edit --dry-run` before broad changes. Selection is explicit: use `--id`,
`--all`, or filters such as `--since`, `--until`, `--severity`, and `--label`.
Use `--status active` when cleaning current context without changing already
resolved or stale history.
Operations can be combined: `--set-status`, `--set-severity`, `--set-summary`,
`--set-details`, `--set-source`, `--set-label`, `--add-label`,
`--remove-label`, `--clear-labels`, equivalent artifact options, or `--delete`.

Render compact active context:

```sh
python3 -m agent_tools.tools.task_context compact \
  --task tasks/<task-name> \
  --severity mid..critical \
  --status active
```

## Workflow

1. At task start, query active journal entries first:

   ```sh
   python3 -m agent_tools.tools.task_context query \
     --task tasks/<task-name> \
     --severity mid..critical \
     --status active \
     --format agent
   ```

   Query resolved, stale, lower-severity, or label-specific history only when
   the user asks or active context requires historical investigation.
2. When a useful fact appears, add it with `task_context add` instead of
   creating or editing markdown context files.
3. `active` is a working-set status, not a historical default. Do not leave an
   entry `active` after the work, validation, decision, blocker, or handoff it
   describes has been superseded, completed, invalidated, or made historical by
   a newer entry.
4. Before handoff, before final responses that change task state, before or
   after validation handoff, before push-ready handoff, after resolving a
   blocker, and before every `task_context compact`, you must audit current
   active entries:

   ```sh
   python3 -m agent_tools.tools.task_context query \
     --task tasks/<task-name> \
     --severity mid..critical \
     --status active \
     --format text
   ```

   For each active entry, either keep it active because it still affects the
   next session, or update it with `task_context edit`. Mark completed or
   superseded entries `resolved`; mark obsolete, misleading, or no-longer-useful
   entries `stale`; add labels such as `superseded` when that clarifies why it
   left the active set.
5. Run `task_context compact` only after the active-entry audit and edits when
   a compact rendering is useful. It must describe the current working set, not
   a newest slice of old accomplishments.
6. Keep details concise. Link logs, reports, commits, and artifacts instead of
   pasting long output into journal entries.
