---
sync: always
---

# Task workflow

These rules apply to every task directory under the workspace root.

1. Start each task by identifying the task directory under `tasks/<task-name>/`.
   If the task directory does not exist and the user is asking for
   implementation, validation, or review work, create the standard layout from
   `AGENTS.md`.
2. Do not run a task-local front-door bell as part of normal task work.
   Workspace policy is enforced by harness hooks when the active agent harness
   supports them. Hook policy handles session start, user prompt lifecycle,
   task_check gates, durable slot freshness before Stop, and compact
   checkpoints. Legacy `front_door_bell.py` scripts may remain in old local
   tasks as manual fallback only; do not create or require them for new tasks.
3. Before working inside an existing task directory, query current task context
   slots from `TASK_CONTEXT.sqlite3` after the directory is selected when task
   state is needed. Use
   `python3 -m agent_tools.tools.task_context query --task <task-dir>
   --format agent` for agent work, or `--format markdown` when rendering for a
   human. Filter with `--category <slot>` or `--cats env,validation` when only
   specific slots are needed. If the database is missing, the tool creates it
   and imports legacy `TASK_DESCRIPTION.md`/`TASK_CONTEXT.md` content into the
   `legacy` slot.
4. Do not scan neighboring task context databases during normal task discovery.
5. Identify the task topics before deep work. Read
   `agent_tools/knowledge/README.md` and every matching topic file under
   `agent_tools/knowledge/topics/`, for example Xen/QEMU work reads
   `topics/xen.md`, workspace tool work reads `topics/agent_tools.md`, and
   Moulin product work reads `topics/moulin.md`. Record the topic files read
   through the task context journal.
6. Maintain task context through singleton SQLite slots:

   - `TASK_CONTEXT.sqlite3` is the only task context source.
   - Slots are current state, not an append-only changelog. Update the relevant
     slot in place with `python3 -m agent_tools.tools.task_context slot --task
     <task-dir> --category <slot> --content <text>`.
   - Slot categories are `goal`, `env`, `decisions`, `findings`,
     `validation`, `blocker-risk`, `operational-memory`, `user-preference`,
     and `legacy`.
   - `goal` and `operational-memory` are required. `env` and `validation` are
     recommended. `legacy` is temporary migration material; move still-current
     facts into typed slots and then clear or shrink it.
   - Durable slot content must use terse factual engineering prose. Prefer
     commands, facts, paths, statuses, risks, and next actions. Avoid praise,
     motivational phrasing, narrative recap, hedging, and decorative adjectives.
   - When an agent identifies stable domain terminology that should keep one
     identity across sessions, add it through
     `python3 -m agent_tools.tools.task_context dictionary --task <task-dir>
     --add <term>`. Do not encode terms by hand in slot text; use dictionary
     aliases returned by `--format agent`.

7. Record the task bootstrap through the task context slots before deep work:

   ```text
   goal, active repositories and branches, selected environment, build or
   product path, compile databases, runtime harness, validation path, blockers
   ```

   Use this command for a quick check of the task layout and workflow metadata:

   ```sh
   python -m agent_tools.paf_workspace.task_check <task-dir>
   ```

   Before authoritative build, runtime validation, report regeneration, or a
   push-ready handoff, run `task_check` with `--strict-warnings` and bring the
   result to 0 warnings and 0 errors. Treat this as a mandatory workspace
   hygiene gate when the tool is available. If `task_check` itself is broken or
   blocked by a missing environment, record the exact command, failure, and
   follow-up through the task context journal before continuing.
   Agent Workspace runs the compact check once immediately before starting a
   new AI session and includes any failures in the initial agent message.
   The repository pre-commit hook runs the strict task check at the commit
   boundary. Do not run it after every individual action.

   Use `--init-layout` to create a missing task layout from workspace
   templates. Use `--init-runtime-product` for Xen/QEMU/Moulin runtime tasks
   that need a starter artifact manifest and harness scenario.
   Before a long environment build or runtime run, use `--env-check-command`
   to print the reusable environment preflight command.
   Use `--run-env-check` only when the task should actually execute the
   environment domain's safe PAF check-only scenario.

8. For tasks that need a reusable environment, choose the environment before
   building or validating. Record the selected
   `agent_tools/paf_workspace/domains/environments/...` profile/scenario,
   reason for choosing it, PAF scenario/task entry point, and validation
   command through the task context journal.
   Prefer running the task through its PAF scenario/build-run entry point when
   one exists. If a direct helper command fails or is tempting as a shortcut,
   first check whether the PAF scenario should be run or extended instead.
   For Xen/Zephyr, QEMU, Yocto, Moulin, and other runtime-product tasks,
   expand the task-local PAF scenario or reusable domain tasks so the build and
   validation remain reproducible; use direct helper scripts only as a focused
   diagnostic and record that exception through the task context journal.
9. Track validation by level instead of using one ambiguous "validated" note:

   ```text
   static: code maps, parse checks, linters, schema checks
   build: authoritative compile or package build
   runtime: emulator, hypervisor, integration, or hardware run
   review: generated diff report or reviewer artifact
   ```

   Mark each level as `not run`, `pass`, `fail`, or `blocked`, with the exact
   command or artifact path that supports the status.
10. When a workspace tool or environment command fails, do not silently bypass
   it. Record the command, short failure summary, whether it blocks exact
   source analysis or only fast feedback, and the next fix through the task
   context journal.
11. Keep source, generated build output, product output, runtime logs, and
   review/report artifacts separate. Fix the source, product definition, or
   reusable environment that reproduces generated output; do not hand-edit
   generated output unless the task explicitly asks for generated artifact
   patching.
12. For runtime products that combine multiple target artifacts, maintain a
    task-owned artifact manifest based on
    `agent_tools/paf_workspace/templates/product-artifacts.yaml`. Keep it under
    the task's `dev/` tree and update it when artifact paths, domain roles, or
    compile databases change.
13. Task-local GUI actions are the normal way to expose repeated task commands
    in `agent-workspace`. Declare them in `TASK_ACTIONS.json` at the task root
    only when the action is useful for a human user to run directly without an
    AI agent. Good candidates include long builds, component builds, hardware
    flashing/copying, board access, smoke tests, report generation, and cleanup
    commands that the user is likely to launch repeatedly. Do not add GUI
    actions for internal agent preprocessing, tiny convenience wrappers,
    exploratory commands, or one-off experiments just because a script exists.
    The file is JSON with an `actions` list:

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

    `id`, `label`, and `command` are required. `command` may be either a string
    shell command or an argv list. `cwd` is optional, defaults to `.`, and must
    stay inside the task directory. `env` is optional and must be a string map.
    Prefer commands under `scripts/` for repeatable task routines; keep
    agent-only helpers and one-off experiments out of `TASK_ACTIONS.json`.
14. Keep commit-ready source/tooling changes separate from review/report
    artifacts unless the user asks to include both. Review tasks place reports
    under `report/`; source tasks should not accumulate report output as a side
    effect.
15. Task directories are local workspace state, not part of the public
    `agent_tools` repository payload. Do not merge or push `tasks/<task-name>/`
    contents into `agent_tools`; keep only the `tasks/` placeholder files
    needed to preserve the local directory layout in a fresh checkout. If a
    task directory was accidentally tracked, remove it from Git with
    `git rm --cached -r tasks/<task-name>` so the local files stay available.
