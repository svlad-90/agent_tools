# Agent Tools

Agent Tools is a local workspace system for working with AI agents as practical
engineering partners. It is built for a human-in-the-loop workflow where the
developer keeps product judgment and final control, while the agent accelerates
investigation, implementation, refactoring, validation, and routine repository
work.

The core idea is simple: do not rely on the model alone to remember the whole
engineering process. Put the process into the workspace. Tasks, rules, actions,
validation gates, reusable environments, and knowledge files give the agent a
clear operating model and give the human a repeatable way to steer the work.

## What Problem This Solves

AI agents are useful, but a plain chat session is a weak execution environment.
Context gets lost, commands are reconstructed from memory, validation is easy
to skip, generated artifacts leak into commits, and every new session has to
rediscover project-specific habits.

Agent Tools turns that loose interaction into a structured local workflow:

- every unit of work has a task directory with durable context;
- repeated commands are exposed as task actions instead of ad hoc shell text;
- validations produce receipts that can be enforced before push;
- reusable Docker/PAF environments make builds and tests reproducible;
- public and private knowledge are separated;
- rules and skills tell agents how to work in the repository.

This keeps the feedback loop short without making the agent unbounded or
opaque.

## The Workflow

Work starts from a task. A task is not just a note; it is the workspace unit
that ties together intent, context, source checkouts, scripts, reports, and
validation evidence.

```text
tasks/<task-name>/
  TASK_DESCRIPTION.md   Stable request, scope, acceptance criteria, links.
  TASK_CONTEXT.md       Current state, decisions, validation, blockers.
  dev/                  Repositories, reproducers, build inputs.
  scripts/              Repeatable task-local commands.
  report/               Logs, review output, generated evidence.
```

The agent reads the task context before working, updates it when important
state changes, and uses the task directory as the anchor for its decisions.
That makes the workflow resilient across restarts, context compaction, and
handoffs between humans or agents.

## The Desktop Workspace

Agent Tools includes a desktop task dashboard:

```sh
./agent-workspace
```

Agent Workspace lists tasks, shows descriptions and active context, opens task
artifacts, manages per-task terminals, and launches interactive AI sessions
with the selected task context. It is agent-neutral by design: Codex, Claude
Code, shell sessions, and task commands all live in the same workspace model.

The GUI is meant to be a cockpit for daily work, not a marketing page. It keeps
the human close to the real task state: source directories, reports, validation
results, terminals, and actions are visible in one place.

Detailed GUI documentation lives in
[tools/agent_workspace/README.md](tools/agent_workspace/README.md).

## Task Actions

Task actions are the bridge between project-specific commands and the GUI.
They are declared in `TASK_ACTIONS.json` at the task root and represent
commands that a human is likely to run repeatedly: full builds, unit tests,
hardware flashing, image copying, board access, smoke checks, report
generation, and cleanup.

Actions can have parameters, reusable parameter sets, global parameters shared
between actions, and shortcuts for common combinations. This gives repeated
work a stable interface. The human can click a known action, and the agent can
reason around a declared command instead of inventing one.

Task actions are intentionally not a dumping ground for every helper script.
They are for commands that belong in the human workflow.

## Guardrails, Not Just Prompts

The workspace treats important process rules as enforceable tooling:

- `task_check` validates task structure and workflow metadata.
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

Tool documentation starts at [tools/README.md](tools/README.md). Commit and
push policy is documented in [rules/git-commits.md](rules/git-commits.md).

## Reusable Environments

Many real engineering tasks cannot be validated with a host-side command. They
need a known Ubuntu image, CI-compatible dependencies, a Yocto or Zephyr build
environment, a QEMU/Xen runtime harness, or a local reproduction of a GitHub
Actions workflow.

Agent Tools keeps those repeatable environments under `paf_workspace/`. PAF
scenarios can prepare Docker images, mount the workspace at known paths, run
multi-stage builds or tests, collect artifacts, and mark the target repository
as validated for `push_guard`.

The result is a validation path that an agent can run, a human can inspect, and
another machine can reproduce.

See [paf_workspace/README.md](paf_workspace/README.md) and
[paf_workspace/domains/environments/README.md](paf_workspace/domains/environments/README.md).

## Knowledge And Skills

Agent Tools separates durable knowledge from transient task notes.

`knowledge/` stores findings that should help future work: repeated failure
patterns, environment gotchas, diagnostic checklists, and topic-specific
lessons. Public knowledge is commit-ready only when it contains no private
data. Private knowledge stays in ignored local storage.

`skills/` contains agent-facing workflow wrappers. A skill does not implement
the tool; it points the agent to the checked-in tool, rule, or PAF scenario
that should be used for a class of tasks. This reduces repeated reasoning
without stuffing every prompt with all possible instructions.

See [knowledge/README.md](knowledge/README.md) and
[rules/workspace-skills.md](rules/workspace-skills.md).

## Privacy Model

The repository describes mechanisms, not private values.

Task directories are local workspace state and should not be merged into the
public tool repository. Public rules, examples, tests, knowledge, and reports
must avoid personal identities, email addresses, account mappings, customer
details, tokens, secrets, and private project data.

When a workflow needs local identity routing or private configuration, it
belongs in local Git config, environment variables, or ignored private files.
The public toolset should remain reusable by other people.

## Repository Structure

```text
rules/          Workspace rules that agents must follow.
tools/          Standalone CLI tools and the Agent Workspace GUI.
paf_workspace/  Reusable PAF automation, domains, scenarios, environments.
knowledge/      Public recurring findings and topic routing.
skills/         Workspace-local agent workflow wrappers.
```

## Why It Matters

Agent Tools is not trying to hide engineering complexity behind a chat box. It
keeps the complexity visible, named, and runnable. The human sees the task, the
agent sees the same task, and the repository enforces the checks that matter.

That makes AI assistance less dependent on a perfect prompt and more dependent
on a repeatable engineering system.
