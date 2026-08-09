# Workspace instructions

Before working in this directory or any of its subdirectories, read and follow
all instruction files in `agent_tools/rules/`.

These rules apply to the entire workspace unless a more specific `AGENTS.md` or
`CLAUDE.md` deeper in the directory tree overrides them for its own agent.

Current rule files:

- `agent_tools/rules/python-code.md`
- `agent_tools/rules/cpp-code.md`
- `agent_tools/rules/task-workflow.md`
- `agent_tools/rules/reusable-environments.md`
- `agent_tools/rules/git-commits.md`
- `agent_tools/rules/diff-reports.md`
- `agent_tools/rules/workspace-skills.md`
- `agent_tools/rules/xen-zephyr-abi.md`

Workspace-local skills live under `agent_tools/skills/`. When a task matches a
workspace-local skill, read that skill's `SKILL.md` before acting and follow it
in addition to the rule files above.

Recurring findings live under `agent_tools/knowledge/`. Before starting a task,
read `agent_tools/knowledge/README.md`, identify matching topic files, and scan
those findings for known patterns that could save investigation time.

## Task layout

Every task in this workspace must live in its own directory under
`tasks/<task-name>/`. Each task directory must use this layout:

- `TASK_DESCRIPTION.md` - stable task description: original request, intended
  scope, acceptance criteria, important links, and non-status background that
  should remain useful for the whole task.
- `TASK_CONTEXT.md` - active task context, decisions, branches, repositories,
  validation status, discovered constraints, and remaining work.
- `dev/` - repositories, reproducers, workspaces, build files, and other
  development inputs for the task.
- `Dockerfile/` - task-specific Dockerfiles, container build context files,
  environment scripts, and notes needed to reproduce the task environment.
- `scripts/` - task-specific scripts for repeated routine work.
- `report/` - review reports, notes, logs, generated HTML/JSON reports, and
  other non-source task artifacts.
- `report/diff/` - diff, patch, patch-bundle artifacts, generated HTML diff
  review reports, and the comments JSON used to generate those reports.
- `report/puml/` - PlantUML diagrams and generated diagram assets. Every
  `.puml` diagram added or changed for a task must be rendered to an adjacent
  `.svg` file before the task is considered complete.

Diff/review reports must be delivered as GitHub-style HTML under
`report/diff/`; follow `agent_tools/rules/diff-reports.md` for the artifact
set and generation workflow. Markdown files may be used for short notes or
navigation, but they are not a substitute for the HTML diff review report.

Comments in diff reports, diagrams, and explanatory notes must be written for a
reader with strong application, middleware, and architecture experience but
limited systems-programming background. For low-level topics such as memory
copying, bit operations, assembly, Xen, Zephyr, U-Boot, boot flows, MMIO,
interrupts, PFNs/GFNs, page tables, cache flushes, and hypercalls, do not rely
on terse systems shorthand. Introduce each new term in plain language, state
what problem the step solves, explain what would break if the step were absent,
and only then name the exact variable, register, constant, or API. When several
low-level terms are involved, repeat the role of each term locally instead of
assuming the reader remembers it from earlier comments.

Before working inside a task directory, read that task's `TASK_DESCRIPTION.md`.
Read `TASK_CONTEXT.md` only after the directory is selected as the target task,
or when the user explicitly asks to inspect neighboring or related tasks. Do
not scan every neighboring `TASK_CONTEXT.md` during normal task discovery:
those files are working state and may be token-heavy.

Keep `TASK_CONTEXT.md` as active working context, not an indefinite historical
log. By default it should contain the current goal, current repository state,
important decisions, validation status, blockers, and enough recent detail from
roughly the last 2-3 days to continue work reliably. Move long history,
superseded attempts, and old investigation details into `report/` artifacts
when they still need to be preserved.

Move repeated routine work into `scripts/` when doing so is useful. The decision
to create or use a script is left to the model's judgment; prefer scripts when
they reduce outgoing tokens, avoid repeated reasoning, or make recurring work
easier to rerun reliably. Do not create scripts for one-off commands or tiny
tasks when a script would add more overhead than value.

Follow `agent_tools/rules/git-commits.md` for commit message formatting.

## File references

When pointing the user to local files, provide a console-friendly absolute
`path:line` reference in addition to any Markdown link when a specific line is
useful. The plain path must be copyable from the terminal and should not use
`file://`, editor-specific URI schemes, or relative paths.

Workspace infrastructure such as `.git`, `.agents`, `.codex`, `CLAUDE.md`, and
`agent_tools/` stays at the workspace root and is not a task.
