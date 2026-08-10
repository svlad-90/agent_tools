# Agent Workspace Tools

Agent Workspace Tools is a local workspace system for people who work with AI
agents on real engineering tasks: long-lived context, multiple repositories,
build environments, validation logs, review reports, and follow-up work that
must still make sense tomorrow.

It is intentionally more than a launcher. The repository provides the root
agent instructions, task layout, workflow checks, reusable helper tools, and a
desktop dashboard that help a human and one or more AI agents keep the same
working state.

> For AI agents: this root `README.md` is written for humans. Before doing work
> in this workspace, follow `AGENTS.md` and the rule files under
> `agent_tools/rules/`. Treat those files as authoritative agent instructions.

## Why Use It

AI coding sessions are easy to start and hard to keep disciplined. Context gets
buried in chat history, commands disappear into terminal scrollback, validation
evidence is hard to hand off, and the next agent often has to rediscover the
same facts.

This workspace is built around a stricter contract:

- every task has a home under `tasks/<task-name>/`;
- task state is written down in `TASK_DESCRIPTION.md` and `TASK_CONTEXT.md`;
- source checkouts, reproducers, scripts, logs, diagrams, and reports have
  predictable locations;
- agents load the same workspace rules before editing code;
- routine checks are exposed as commands instead of being remembered manually;
- validation status is tracked by level: static, build, runtime, and review.

The result is a workspace that favors continuity over improvisation. It is most
useful when a task may span several days, several repositories, or several
agent sessions.

## What Stands Out

- **Agent-neutral task dashboard.** `Agent Workspace` can launch and resume
  task-local AI agent terminals for Codex and Claude Code, while still being
  usable with shell sessions and task actions.
- **Context that survives the chat.** The task files describe the goal,
  decisions, branches, constraints, validation status, and remaining work in a
  place future humans and agents can read.
- **Workspace rules as executable discipline.** Python, C/C++, task workflow,
  commit, reusable environment, and review-report policies live under
  `agent_tools/rules/` and are loaded by agent instructions.
- **Source navigation helpers.** `code_map`, `cpp_code_map`, and `yaml_map`
  help agents inspect structured source files before making edits.
- **Review artifacts for humans.** `diff_report` generates GitHub-style HTML
  reviews with inline comments, summaries, logs, and diagrams under a task's
  `report/diff/` directory.
- **Reusable validation workflows.** PAF workspace domains provide a place for
  repeatable build, environment, and runtime orchestration instead of leaving
  those steps in ad hoc shell history.
- **Push hygiene.** Commit formatting and `push_guard` help keep local
  validation and commit metadata from becoming an afterthought.

## Honest Trade-Offs

This is not a zero-setup productivity toy. The workflow has a real entry cost:
you need to use task directories, keep context files current, understand which
validation command matters, and let the rules shape how agents work.

For a tiny one-file experiment, that may feel heavy. For embedded work,
multi-repository changes, runtime investigations, review reports, or any task
where another agent must continue later, the structure pays back quickly.

The tools also assume a local developer workstation. Some flows depend on
Python, Git, a desktop environment, Docker, PAF, libclang, or project-specific
build inputs. The workspace tries to make those dependencies explicit, but it
does not make hard build environments disappear.

## Repository Map

This repository tracks reusable workspace infrastructure:

- `AGENTS.md` - canonical workspace-level instructions for AI agents.
- `CLAUDE.md` - a Claude Code shim that points to `AGENTS.md`.
- `agent-workspace` - convenience launcher for the desktop dashboard.
- `agent_tools/tools/` - standalone CLI tools such as `code_map`,
  `cpp_code_map`, `yaml_map`, `diff_report`, `commit_msg`, `push_guard`, and
  `agent_workspace`.
- `agent_tools/paf_workspace/` - PAF orchestration assets, domains, reusable
  environments, task bootstrap templates, task workflow checks, and tests.
- `agent_tools/rules/` - mandatory workspace policy loaded through root agent
  instruction files.
- `agent_tools/skills/` - workspace-local operating manuals for specific tools
  and workflows.
- `agent_tools/knowledge/` - durable findings that should inform future tasks.
- `.gitignore` - keeps task directories, build outputs, caches, and local
  artifacts out of this setup repository.

Task-specific source checkouts and artifacts belong under `tasks/<task-name>/`,
not in the reusable setup tree.

## Task Layout

Every task lives under the workspace root:

```text
tasks/
  my-task/
    TASK_DESCRIPTION.md
    TASK_CONTEXT.md
    dev/
    Dockerfile/
    scripts/
    report/
      diff/
      puml/
```

The main directories have stable roles:

- `TASK_DESCRIPTION.md` holds the original request, intended scope, acceptance
  criteria, links, and background that should remain useful for the whole task.
- `TASK_CONTEXT.md` holds active working context: repositories, branches,
  decisions, validation status, constraints, blockers, and remaining work.
- `dev/` holds source checkouts, reproducers, build files, and other task
  inputs.
- `Dockerfile/` holds task-specific container files and environment notes.
- `scripts/` holds repeated routine commands when a script is actually useful.
- `report/` holds logs, notes, generated reports, diagrams, and other
  non-source artifacts.
- `report/diff/` holds generated HTML diff reviews, source diffs or patches,
  and canonical comments JSON.
- `report/puml/` holds PlantUML diagrams and adjacent rendered SVG files.

Use scripts when they reduce repeated reasoning or make validation easier to
rerun. Avoid scripts for one-off commands where the script adds more process
than value.

## Agent Workspace

Launch the desktop dashboard from the workspace root:

```sh
./agent-workspace
```

The dashboard helps a human operate the workspace without spending agent
context on routine navigation:

- browse tasks under `tasks/`;
- view and edit task descriptions and context;
- run built-in checks such as `task_check` and repository scans;
- run task-declared actions from `TASK_ACTIONS.json`;
- keep per-task terminal tabs;
- launch and resume Codex or Claude Code sessions for a task;
- remember the selected AI agent and resumable agent session per task;
- warn before switching away from or closing running agent sessions;
- mark tasks whose agent terminal appears to be waiting for permission;
- browse logs, diagrams, SVGs, and diff-review artifacts.

Task actions are declared at the task root:

```json
{
  "actions": [
    {
      "id": "unit-tests",
      "label": "Unit tests",
      "command": ["scripts/run-unit-tests.sh"],
      "cwd": ".",
      "env": {"EXAMPLE": "value"}
    }
  ]
}
```

## Included CLI Tools

Standalone tools live under `agent_tools/tools/`.

### `agent_tools.tools.code_map`

Python source inspection and guarded editing support:

```sh
python -m agent_tools.tools.code_map map path/to/file.py
python -m agent_tools.tools.code_map symbol-get path/to/file.py --symbol Name
python -m agent_tools.tools.code_map parse-check path/to/file.py
```

### `agent_tools.tools.cpp_code_map`

C and C++ inspection around libclang and compile databases:

```sh
python -m agent_tools.tools.cpp_code_map map path/to/file.cpp --compile-db build
python -m agent_tools.tools.cpp_code_map symbol-get path/to/file.cpp \
  --symbol Namespace::Name --compile-db build
python -m agent_tools.tools.cpp_code_map parse-check path/to/file.cpp \
  --compile-db build
```

### `agent_tools.tools.diff_report`

GitHub-style HTML diff review report generation:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file tasks/my-task/report/diff/changes.diff \
  --comments tasks/my-task/report/diff/comments.json \
  --output tasks/my-task/report/diff/review.html
```

### `agent_tools.paf_workspace`

PAF orchestration for repeatable workflows, reusable environments, and task
workflow checks:

```sh
python -m agent_tools.paf_workspace.task_check tasks/my-task
```

Other included tools include `yaml_map`, `commit_msg`, `push_guard`, and the
`agent_workspace` package behind the desktop dashboard.

## Getting Started

Open the workspace repository:

```sh
git clone git@github.com:svlad-90/agent_tools.git agent-workspace
cd agent-workspace
```

Then use one of the normal entry points.

### Start with an AI agent

Open a terminal in the workspace root, start your agent, and ask it to create a
new task or switch to an existing one. For example:

```sh
codex
```

Then say something like:

```text
Create a new workspace task for investigating <problem>.
```

or:

```text
Switch to the existing workspace task <task-name>.
```

The agent instructions in `AGENTS.md` tell supported agents how task
directories, context files, validation notes, and workspace rules are supposed
to work.

### Start with the GUI

Launch the desktop dashboard:

```sh
./agent-workspace
```

From there, create or select a task, inspect its context, run task actions, and
launch a task-local AI agent session when needed.

### Check the task

After a task exists, `task_check` is the quick sanity check for the workspace
contract:

```sh
python -m agent_tools.paf_workspace.task_check tasks/my-task
```

Because `.gitignore` ignores local task directories and generated artifacts,
the reusable setup repository can stay clean while each task keeps its own
working state.

## Maintenance Notes

- Keep agent-facing policy in `AGENTS.md` and `agent_tools/rules/`.
- Keep this root `README.md` focused on human onboarding and project overview.
- Keep standalone CLI tools in `agent_tools/tools/`.
- Keep PAF orchestration and reusable environments in
  `agent_tools/paf_workspace/`.
- Keep workspace-local skills in `agent_tools/skills/`.
- Keep durable repeated findings in `agent_tools/knowledge/`.
- Keep generated caches, task outputs, downloaded repositories, and local
  reproduction artifacts out of the reusable setup repository.
- Follow `agent_tools/rules/git-commits.md` for commit messages.
