# Workspace instructions

Read `agent_tools/rules/task-workflow.md` first, then read only the additional
rule files that match the current task. Do not load every rule file by default.
Always read `agent_tools/rules/git-commits.md` before commit or push work.

These rules apply to the entire workspace unless a more specific `AGENTS.md` or
`CLAUDE.md` deeper in the directory tree overrides them for its own agent.

Rule routing: Python -> `python-code.md`; C/C++/assembly ->
`cpp-code.md`; Docker/CI/PAF/SDK/emulator environments ->
`reusable-environments.md`; commit/push -> `git-commits.md`; diff reports ->
`diff-reports.md`; workspace skills -> `workspace-skills.md`; Xen/Zephyr/QEMU
runtime -> `xen-zephyr-abi.md`.

Workspace-local skills live under `agent_tools/skills/`. When a task matches a
workspace-local skill, read that skill's `SKILL.md` before acting and follow it
in addition to the rule files above.

Recurring findings live under `agent_tools/knowledge/`. Read its `README.md`
and matching topic files before deep investigation.

## Task layout

Every task lives under `tasks/<task-name>/`:

- `TASK_CONTEXT.sqlite3` - transactional structured task context and the only
  current task context source. It stores singleton slots: `goal`, `env`,
  `decisions`, `findings`, `validation`, `blocker-risk`,
  `operational-memory`, `user-preference`, and `legacy`.
- `dev/` - repositories, reproducers, workspaces, build files, and other
  development inputs for the task.
- `Dockerfile/` - task-specific Dockerfiles, container build context files,
  environment scripts, and notes needed to reproduce the task environment.
- `scripts/` - task-specific scripts for repeated routine work.
- `report/` - notes, logs, generated reports, and non-source artifacts.
- `report/diff/` - diff, patch, patch-bundle artifacts, generated HTML diff
  review reports, and the comments JSON used to generate those reports.
- `report/puml/` - PlantUML diagrams and generated diagram assets. Every
  `.puml` diagram added or changed for a task must be rendered to an adjacent
  `.svg` file before the task is considered complete.

Diff/review reports must be GitHub-style HTML under `report/diff/`; follow
`agent_tools/rules/diff-reports.md`.

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

Before working inside a task after a user message, run the task-local
`front_door_bell.py` with the available Python interpreter and follow its
returned stage until it returns `ITERATION_DONE` or `BLOCKED`. When the bell or
the task requires direct context access, query current task context slots from
`TASK_CONTEXT.sqlite3` with
`python3 -m agent_tools.tools.task_context query --task <task-dir> --format
agent`. Use `--category`/`--cats` for targeted slot reads. Legacy
`TASK_DESCRIPTION.md` and `TASK_CONTEXT.md` files are imported into the
`legacy` slot when a new slot database is created; they are not current context
sources.

Move repeated routine work into `scripts/` when it reduces repeated reasoning
or makes commands easier to rerun.

## File references

When pointing the user to local files, provide a console-friendly absolute
`path:line` reference in addition to any Markdown link when a specific line is
useful. The plain path must be copyable from the terminal and should not use
`file://`, editor-specific URI schemes, or relative paths.

Workspace infrastructure such as `.git`, `.agents`, `.codex`, `CLAUDE.md`, and
`agent_tools/` stays at the workspace root and is not a task.
