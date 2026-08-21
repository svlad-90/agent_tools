# Workspace Tools

This directory owns standalone workspace CLI tools. Run them from the workspace
root through their module entry points:

```sh
python -m agent_tools.tools.code_map
python -m agent_tools.tools.cpp_code_map
python -m agent_tools.tools.yaml_map
python -m agent_tools.tools.diff_report
python -m agent_tools.tools.task_context
python -m agent_tools.tools.commit_msg
python -m agent_tools.tools.push_guard
python -m agent_tools.tools.agent_workspace
python -m agent_tools.tools.rules_sync
```

Keep PAF orchestration under `agent_tools/paf_workspace/`; this directory is
for reusable tool implementations that are not PAF domains.

## Python Environment

Install Agent Workspace, workspace-local tool dependencies, the launcher,
desktop entry, and mirrored agent skills from the workspace root:

```sh
cd /path/to/workspace
python3 install-agent-tools.py
```

Install developer/test dependencies too:

```sh
python3 install-agent-tools.py --dev
```

Install the legacy GTK/VTE UI dependencies only when that UI is needed:

```sh
python3 install-agent-tools.py --gui
```

The default installation does not install GTK/VTE. Agent Workspace tries UI
backends in order: GTK, web, then Tk. When the web UI exists it can be used as
the fallback on hosts without GTK/VTE.

```sh
python3 install-agent-tools.py --venv /path/to/venv --dev
```

Dependency files live under `requirements/`:

- `runtime.txt`: CLI runtime dependencies, including `PyYAML` and `tiktoken`.
- `dev.txt`: runtime plus test dependencies.
- `gui.txt`: runtime plus notes for the optional system GTK/VTE profile.

## Rules Sync

`rules_sync` mirrors `agent_tools/rules/*.md` and `agent_tools/skills/*/SKILL.md`
(the Codex-facing source of truth) into other agents' native conventions, for
example Claude Code's `.claude/skills/` and the generated block in
`CLAUDE.md`. See `agent_tools/rules/workspace-skills.md` for the `sync:` and
`rule:` frontmatter conventions it depends on.

Regenerate the mirrors after editing any rule or skill file:

```sh
python -m agent_tools.tools.rules_sync sync
```

Check for drift without writing (fails if any mirrored file is stale):

```sh
python -m agent_tools.tools.rules_sync sync --check
```

## Task Context

Use `task_context` to keep long-running tasks compact without losing history.
It stores durable context in `TASK_CONTEXT.sqlite3`. Agents read active entries
from the database; resolved and stale entries stay queryable history.
Labels are validated against the fixed vocabulary used by
`agent_tools.tools.task_context`.

Add a dated finding:

```sh
python -m agent_tools.tools.task_context add \
  --task tasks/my-task \
  --severity high \
  --label validation \
  --label build \
  "Docker pytest passed for the Agent Workspace suite"
```

Legacy tasks can be imported once with:

```sh
python -m agent_tools.tools.task_context migrate --task tasks/my-task
```

Query active journal entries by date, severity, or labels:

```sh
python -m agent_tools.tools.task_context query \
  --task tasks/my-task \
  --since 2026-08-19 \
  --severity mid..critical \
  --label validation \
  --format markdown
```

`query` defaults to active entries. Use `--all-statuses` or explicit
`--status resolved` / `--status stale` only when historical context is needed.

Batch edit or delete selected entries:

```sh
python -m agent_tools.tools.task_context edit \
  --task tasks/my-task \
  --label validation \
  --status active \
  --until 2026-08-19 \
  --set-status resolved \
  --add-label superseded
```

Use `--dry-run` before broad edits. Combine selectors such as `--id`, `--all`,
`--since`, `--until`, `--severity`, `--label`, and `--status` with operations
such as `--set-status`, `--set-label`, `--add-label`, `--remove-label`,
artifact updates, or `--delete`.

Before handoff, push-ready handoff, validation handoff, blocker resolution, or
compaction, audit active entries and move completed or superseded context out
of the active set:

```sh
python -m agent_tools.tools.task_context query \
  --task tasks/my-task \
  --severity mid..critical \
  --status active \
  --format text
```

Only entries that still affect the next session should remain `active`.

Regenerate compact active context:

```sh
python -m agent_tools.tools.task_context compact --task tasks/my-task
```

## Commit Message

Use `commit_msg` to compose and format commit messages from structured parts:

```sh
python -m agent_tools.tools.commit_msg \
  --repo <target-repo> \
  --title "subsys: concise subject" \
  --body "Body paragraphs are wrapped to 72 columns." \
  --signoff "Name <email@example.com>" \
  --reviewed-by "Reviewer <reviewer@example.com>" \
  --tested-by "Tester <tester@example.com>" \
  --acked-by "Acker <acker@example.com>" \
  --assisted-by "Codex:gpt-5 cpp-code-map" \
  --check
```

Use `commit_msg.workflow` when the same structured parts should create or
amend the commit directly:

```sh
python -m agent_tools.tools.commit_msg.workflow \
  --repo <target-repo> \
  --title "subsys: concise subject" \
  --body "Body paragraphs are wrapped to 72 columns." \
  --signoff "Name <email@example.com>" \
  --assisted-by "Codex:gpt-5 cpp-code-map" \
  --commit
```

## Push Guard

Use `push_guard` to enforce the workspace rule that every push must follow a
successful build or validation run for the exact commit being pushed:

```sh
python -m agent_tools.tools.push_guard install-hook
<build-or-validation-command>
python -m agent_tools.tools.push_guard mark-success \
  --source <build-or-validation-id>
git push
```

The hook blocks a push when the local commit tip has no recorded successful
validation stamp under the repository's Git metadata. The same hook also checks
commit messages for pushed commits: every line must fit the configured width
(72 by default), every pushed commit must have a `Signed-off-by` trailer, and
Zephyr repositories must also have a Zephyr-format `Assisted-by` trailer.

For reusable build systems such as PAF, pass the target repository into the PAF
workspace scenario. Its final `push_guard` phase records the same stamp after
the build step has already succeeded:

```sh
python -m agent_tools.tools.push_guard install-hook --repo <target-repo>
agent_tools/paf_workspace/run-paf.sh <scenario-file> <scenario> \
  --parameter PUSH_GUARD_REPO=<target-repo> \
  --parameter PUSH_GUARD_SOURCE=<build-or-validation-id>
git -C <target-repo> push
```

`mark-success` writes the same repository-local validation marker that the
pre-push hook checks. `status` prints whether the current commit already has a
recorded marker:

```sh
python -m agent_tools.tools.push_guard status --repo <target-repo>
```

## Agent Workspace

Use `agent_workspace` for the local task dashboard. It is agent-neutral by
design: Codex and Claude Code are supported interactive terminal sessions,
while the workspace and task controls are useful without any AI session
running.

```sh
./agent-workspace
```

It lists workspace tasks, renders `TASK_DESCRIPTION.md`, shows
`TASK_CONTEXT.sqlite3` as a newest-first context journal with date, severity,
status, and label filters. It opens task and `dev/` folders, edits task
descriptions on demand, runs compact `task_check`, discovers repositories under
`dev/`, runs task-declared actions from `TASK_ACTIONS.json` in the active
console, manages per-task terminal tabs, starts one interactive AI agent
session per task, and shows task artifacts from `report/`, `report/diff/`, and
`report/puml/` with open and cleanup actions. GUI settings persist theme,
language, text size, button text size, window geometry, and the default AI
agent. The selected agent is saved per task; switching between running AI
agents requires confirmation, and missing agent commands show an installation
prompt. Closing the window warns when AI agent sessions are still running.
Tasks with agent sessions that appear to be waiting for permission or approval
are marked with `⚠` in the task list. GUI-launched task actions set
`PAF_HIDE_TASK_ENV=1` to keep PAF parameter dumps out of the console.
