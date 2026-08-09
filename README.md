# Agent workspace tools

This repository contains a portable agent workspace setup: root `AGENTS.md`
instructions for Codex, a root `CLAUDE.md` shim for Claude Code, and the
`agent_tools/` helper package used by those instructions.

The goal is to make the working style reproducible. Clone this repository as a
workspace root, put task directories next to `agent_tools/`, and supported
agents will have the same rules, helper commands, review-report tooling, and
validation conventions available in every task.

## Repository Map

This repository tracks reusable workspace infrastructure only:

- `AGENTS.md` - the canonical workspace-level instructions.
- `CLAUDE.md` - a Claude Code shim that points to `AGENTS.md`.
- `agent_tools/tools/` - standalone CLI tools such as `code_map`,
  `cpp_code_map`, `yaml_map`, `diff_report`, `commit_msg`, and
  `agent_workspace`.
- `agent_tools/paf_workspace/` - PAF orchestration assets, domains,
  reusable environments, task bootstrap templates, task workflow checks, and
  PAF workspace tests.
- `agent_tools/rules/` - mandatory workspace policy loaded through root agent
  instruction files.
- `agent_tools/skills/` - operating manuals for specific tools and workflows.
- `agent_tools/knowledge/` - durable findings that should inform future tasks.
- `.gitignore` - keeps task directories, build outputs, caches, and local
  artifacts out of this setup repository.

Task-specific work does not belong in this repository. Task directories are
created at the workspace root and are intentionally ignored by Git so the same
workspace can contain many unrelated development efforts without mixing them
into the setup history.

## Workspace contract

Every task lives in its own top-level directory under the workspace root. A task
directory is expected to contain:

- `TASK_CONTEXT.md` for active context, decisions, branch information,
  validation status, constraints, and remaining work.
- `dev/` for repositories, reproducers, workspaces, build files, and other
  development inputs.
- `Dockerfile/` for task-specific Dockerfiles, container build contexts,
  environment scripts, and reproduction notes.
- `scripts/` for task-specific scripts that make repeated routine work cheaper
  and more reliable.
- `report/` for notes, logs, generated reports, and other non-source artifacts.
- `report/diff/` for source diffs, patch bundles, HTML diff review reports, and
  the JSON comments used to generate those reports.
- `report/puml/` for PlantUML diagrams and adjacent rendered SVG outputs.

The `scripts/` directory is a workspace directive, not a mandatory abstraction
for every command. Use scripts when they reduce repeated reasoning, reduce
outgoing tokens, or make recurring validation and reproduction steps easier to
rerun. Avoid scripts for one-off commands or tiny tasks where a script would add
more overhead than value.

## Workspace rules

The root `AGENTS.md` file requires agents to read and follow all rule files in
`agent_tools/rules/` before working in the workspace. `CLAUDE.md` delegates
Claude Code to the same file.

Current rule files:

- `python-code.md` - use `python -m agent_tools.tools.code_map` when inspecting,
  editing, or validating Python code.
- `cpp-code.md` - use `python -m agent_tools.tools.cpp_code_map` when inspecting,
  editing, or validating C and C++ code.
- `reusable-environments.md` - keep reusable container environments under
  `agent_tools/paf_workspace/domains/environments/` and task-specific runtime
  material under the task directory.
- `task-workflow.md` - keep task directories, context, validation status, and
  runtime metadata consistent.
- `diff-reports.md` - keep diff review artifacts consistent, self-contained,
  and evidence-led when validation artifacts matter.
- `git-commits.md` - keep commit messages wrapped and include the required
  `Signed-off-by` trailer.
- `workspace-skills.md` and `xen-zephyr-abi.md` - define workspace skill
  routing and Xen/Zephyr ABI review expectations.

More specific `AGENTS.md` or `CLAUDE.md` files inside task directories may
override the root instructions for their subtree.

## Included tools

Standalone CLI tools live under `agent_tools/tools/`. The old module paths
such as `agent_tools.code_map` and `agent_tools.diff_report` are intentionally
not kept as compatibility shims.

### `agent_tools.tools.code_map`

Python source inspection and guarded editing support. It can map file structure,
resolve symbols, inspect exact spans, and parse-check changed Python files.

Typical commands:

```sh
python -m agent_tools.tools.code_map map path/to/file.py
python -m agent_tools.tools.code_map symbol-get path/to/file.py --symbol Name
python -m agent_tools.tools.code_map parse-check path/to/file.py
```

### `agent_tools.tools.cpp_code_map`

C and C++ source inspection and validation support built around libclang and
compile databases. It helps map C++ files, inspect symbols, and parse-check
changes with explicit build context.

Typical commands:

```sh
python -m agent_tools.tools.cpp_code_map map path/to/file.cpp --compile-db build
python -m agent_tools.tools.cpp_code_map symbol-get path/to/file.cpp \
  --symbol Namespace::Name --compile-db build
python -m agent_tools.tools.cpp_code_map parse-check path/to/file.cpp \
  --compile-db build
```

### `agent_tools.tools.diff_report`

GitHub-style HTML diff review report generation. Review artifacts should live
under a task's `report/diff/` directory, including the source diff, comments
JSON, and generated HTML.

Reports can include file-level comments, inline comments, guided story steps,
diagram and log previews, diagram-to-code links, and evidence-led
`Reviewer Summary` sections that interleave prose with diagram or log previews.

Typical command:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file report/diff/changes.diff \
  --comments report/diff/comments.json \
  --output report/diff/review.html
```

### `agent_tools.tools.agent_workspace`

Local desktop dashboard for navigating task directories and running routine
workspace operations without spending agent context. Its visible application
name is `Agent Workspace`, because the workspace can be driven by Codex, Claude
Code, shell sessions, or another task-local agent.

Launch it from the workspace root:

```sh
./agent-workspace
```

The dashboard provides:

- a task list backed by the `tasks/` directory, with case-insensitive sorting
  and quick task/folder context actions;
- rendered `TASK_DESCRIPTION.md` and `TASK_CONTEXT.md` views with editable
  task descriptions when needed;
- a task action panel that reads `TASK_ACTIONS.json`, runs actions in the
  active task terminal, and supports repository scanning, `task_check`, and
  `git status`;
- per-task terminal tabs, including an interactive Codex launcher that tells
  the agent which task is active and which language to use;
- an artifacts tab for logs, PlantUML/SVG diagrams, and diff-review outputs,
  with open and cleanup actions;
- persistent GUI settings for theme, UI language, text size, button text size,
  and window geometry.

### `agent_tools.tools.yaml_map`

YAML structure inspection helpers for workflows and configuration files.

### `agent_tools.paf_workspace`

PAF orchestration for reusable workflow automation. This owns domain scenarios,
profiles, templates, reusable environment definitions, PAF-specific tests, and
the task workflow checker:

```sh
python -m agent_tools.paf_workspace.task_check <task-dir>
```

## Deployment model

Use this repository as the root of an agent workspace:

```sh
git clone git@github.com:svlad-90/agent_tools.git agent-workspace
cd agent-workspace
```

Then create task directories next to `agent_tools/`:

```text
agent-workspace/
  AGENTS.md
  CLAUDE.md
  agent_tools/
  some-task/
    TASK_CONTEXT.md
    dev/
    Dockerfile/
    scripts/
    report/
```

Because `.gitignore` ignores everything by default and explicitly re-includes
only the reusable setup files, task directories remain local unless they are
managed by their own nested repositories.

## Maintenance notes

- Keep workspace-wide behavior in the root `AGENTS.md`.
- Keep standalone CLI tools in `agent_tools/tools/`.
- Keep PAF orchestration and PAF workflow helpers in
  `agent_tools/paf_workspace/`.
- Keep language-specific and workflow-specific requirements in
  `agent_tools/rules/`.
- Keep generated caches, task outputs, downloaded repositories, and local
  reproduction artifacts out of this repository.
- Commit messages must follow `agent_tools/rules/git-commits.md`.
