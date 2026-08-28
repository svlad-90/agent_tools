<p align="center">
  <img src="docs/images/agent-workspace-logo.png" alt="Agent Workspace logo" width="144">
</p>

<h1 align="center">Agent Workspace Tools</h1>

<p align="center">
  A local engineering workspace for human-led AI agent collaboration.
</p>

Agent Workspace Tools is built for human-led AI development. The developer
keeps product judgment and final control; the workspace gives agents tasks,
rules, actions, validation gates, reusable environments, and knowledge files.

## What Problem This Solves

AI coding sessions are easy to start and hard to keep disciplined. Context
gets buried in chat, commands disappear into terminal scrollback, validation
evidence is hard to hand off, and the next agent rediscovers old facts.

Agent Workspace Tools turns that loose interaction into a structured local
workflow:

- every unit of work has a task directory with durable, queryable context;
- task context is kept in current SQLite slots so agents do not carry stale
  journal history;
- repeated commands are exposed as task actions instead of ad hoc shell text;
- validations produce receipts that can be enforced before push;
- reusable Docker/PAF environments make builds and tests reproducible;
- public and private knowledge are separated;
- rules and skills tell agents how to work in the repository.

## Getting Started

Launch the workspace dashboard from the repository root:

```sh
python3 install-agent-tools.py
./agent-workspace.sh
```

When run from a terminal without flags, the installer opens a small console
wizard. Choose the UI profile (`web`, `tk`, or `gtk`) and whether to install
common system tools such as PlantUML/Graphviz or Docker support. System package
installation may ask for `sudo` on Linux.

On macOS, open `agent-workspace.command`. On Windows, run
`agent-workspace.cmd`. Those portable launchers start the browser UI.

Typical flow:

1. Create a task and give it a name.
2. Open Codex, Claude Code, or a shell session from that task.
3. Describe the work in the AI window.
4. Let the agent capture the brief, update context, add scripts/actions, and
   record validation as the work becomes concrete.
5. Use the GUI to run actions, switch terminals, inspect context, and open
   artifacts.
6. Review, validate, and commit when the repository is ready.

### Create A Task

A task is the working unit: one investigation, feature, refactor, bug fix,
review, or release activity. From the GUI, create a task and choose whether it
is public or private. Private tasks stay local; public tasks can be used as
examples or mergeable metadata when they contain no private data.

Each task gets a predictable layout:

```text
tasks/<task-name>/
  TASK_CONTEXT.sqlite3  Current task context slots and dictionary.
  dev/                  Checkouts, reproducers, generated build inputs.
  scripts/              Repeatable helper commands.
  report/               Logs, diagrams, reviews, validation evidence.
```

`TASK_CONTEXT.sqlite3` is the task context source. It stores one current slot
per category: goal, environment, decisions, findings, validation,
blockers/risks, operational memory, user preferences, and temporary legacy
material imported from old `TASK_DESCRIPTION.md`/`TASK_CONTEXT.md` files.

Useful prompts:

```text
Show me the current validation and blocker-risk slots.
Update operational memory with the current next steps.
```

### Add Actions

Actions are commands worth turning into buttons: builds, tests, flash/copy
steps, report generation, cleanup, board access, smoke checks, or any command
you expect to run repeatedly during the task.

Usually you ask the agent to add an action when a command becomes part of the
workflow. The agent can create a script and declare it in `TASK_ACTIONS.json`.

```text
Add a task action for running the unit tests.
```

Keep actions at the level a human would actually click. A good action is
`Build image` or `Run smoke test`; a poor action is a tiny internal helper that
only exists because one agent needed it once.

### Add Parameters

Use parameters when the same action needs small variations: target board,
build profile, image path, test filter, report name, or deployment target.

In normal use, describe the variation to the agent:

```text
Make the build action accept board and profile parameters.
```

Use global parameters for values shared by several actions, such as `board`,
`device`, or `build_dir`. Save parameter sets or shortcuts for combinations
you use often, for example `Board: lab-a` plus `Profile: debug`.

### Work With The AI Window

The AI terminal is for judgment-heavy work: reading code, investigating
failures, planning refactors, making edits, reviewing diffs, and deciding which
validation matters. The GUI is for operating the workspace: selecting the task,
opening context, running known actions, switching terminals, saving shortcuts,
and opening artifacts.

## Compact Context

Long AI-assisted tasks create a lot of facts. Agent Workspace keeps them in
SQLite slots:

- `goal`: task objective and acceptance criteria.
- `env`: how to build, run, and inspect the task.
- `decisions`, `findings`, `validation`, `blocker-risk`: current facts by
  category.
- `operational-memory`: current handoff and next steps.
- `user-preference`: durable user preferences.
- `legacy`: temporary migrated old markdown or journal material.

Agents update slots in place instead of appending dated status notes.

The underlying command is:

```sh
python -m agent_tools.tools.task_context
```

## The Desktop Workspace

The desktop app is the fastest way to operate the workspace day to day:

```sh
./agent-workspace.sh
```

On macOS and Windows, use the browser UI launchers:

```text
agent-workspace.command
agent-workspace.cmd
```

Agent Workspace lists tasks, shows the goal slot, renders current task context
slots, opens task artifacts, manages per-task terminals, and launches
interactive AI sessions with hook-driven task policy. It is agent-neutral by
design: Codex, Claude Code, shell sessions, and task commands all live in the
same workspace model.

Embedded Codex and Claude Code sessions use low-redraw terminal settings and a
GTK mouse proxy around agent VTE widgets. Agent hooks also wrap Bash commands
with a token-limited output guard: oversized stdout/stderr is summarized with a
bounded first/last line preview and saved completely under the task's
`report/logs/limited-bash/` directory.

Detailed GUI documentation lives in
[agent_tools/agent_workspace/README.md](agent_tools/agent_workspace/README.md).

## Guardrails, Not Just Prompts

The workspace treats important process rules as enforceable tooling:

- `task_check` validates task structure and workflow metadata.
- `task_context` keeps long-running task memory compact, structured, and
  queryable.
- `code_map`, `cpp_code_map`, and `yaml_map` help inspect and edit source with
  structural awareness.
- `validate` records validation receipts for changed files or tasks.
- `push_guard` blocks pushes that lack a successful validation marker for the
  exact commit being pushed.
- `commit_msg` formats and checks commit messages and trailers.

The agent can still reason about what needs to be done, but the repository can
technically reject skipped validation, risky staged files, malformed commit
messages, private paths, large generated artifacts, and obvious secret leaks.

This is the difference between "please remember to validate" and "the workflow
will not let this push through without validation."

Tool documentation starts at [agent_tools/tools/README.md](agent_tools/tools/README.md).
Commit and push policy is documented in
[agent_tools/rules/git-commits.md](agent_tools/rules/git-commits.md).

## Reports And Reviews

You can ask the agent to explain work as a report instead of only answering in
chat:

```text
Prepare a report that explains the investigation results.
Summarize the validation run as a report with links to the logs.
Review this branch and generate a report I can read later.
```

General reports live under `report/`. Diff reviews live under `report/diff/`
and can produce GitHub-style HTML with inline comments tied to files.

## Reusable Environments

Real engineering tasks often need more than a host command: CI-compatible
dependencies, Yocto or Zephyr builds, QEMU/Xen runtime harnesses, or local
GitHub Actions reproductions. Agent Tools keeps repeatable environments under
`agent_tools/paf_workspace/`. PAF scenarios prepare Docker images, run
multi-stage builds or tests, collect artifacts, and mark the target repository
as validated for `push_guard`.

See [agent_tools/paf_workspace/README.md](agent_tools/paf_workspace/README.md)
and
[agent_tools/paf_workspace/domains/environments/README.md](agent_tools/paf_workspace/domains/environments/README.md).

## Knowledge And Skills

`agent_tools/knowledge/` stores repeated failure patterns, environment
gotchas, diagnostic checklists, and topic-specific lessons. Public knowledge
must contain no private data; private knowledge stays in ignored local storage.

`agent_tools/skills/` contains agent-facing workflow wrappers. A skill points
the agent to the checked-in tool, rule, or PAF scenario for a class of tasks,
reducing repeated reasoning without stuffing every prompt with all instructions.

See [agent_tools/knowledge/README.md](agent_tools/knowledge/README.md) and
[agent_tools/rules/workspace-skills.md](agent_tools/rules/workspace-skills.md).

## Privacy Model

The repository describes mechanisms, not private values.

Task directories are local workspace state and should not be merged into the
public tool repository. Public rules, examples, tests, knowledge, and reports
must avoid personal identities, email addresses, account mappings, customer
details, tokens, secrets, and private project data.

When a workflow needs local identity routing or private configuration, it
belongs in local Git config, environment variables, or ignored private files.
The public toolset should remain reusable by other people.

## Screenshots

Agent Workspace with task context, action buttons, and live agent terminals:

![Task details and durable context in Agent Workspace](docs/images/agent-workspace-details.png)

![Live Codex session running inside Agent Workspace](docs/images/agent-workspace-codex.png)

![Live Claude Code session running inside Agent Workspace](docs/images/agent-workspace-claude.png)

## Repository Structure

```text
AGENTS.md       Workspace-level instructions for AI agents.
agent-workspace Desktop dashboard launcher.
agent_tools/    Reusable tools, rules, skills, knowledge, and PAF assets.
tasks/          Local task directories, ignored except layout placeholders.
report/         Workspace-level generated reports and validation receipts.
```

## Why It Matters

Agent Tools is not trying to hide engineering complexity behind a chat box. It
keeps the complexity visible, named, and runnable. The human sees the task, the
agent sees the same task, and the repository enforces the checks that matter.

That makes AI assistance less dependent on a perfect prompt and more dependent
on a repeatable engineering system.
