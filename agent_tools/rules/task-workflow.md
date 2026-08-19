---
sync: always
---

# Task workflow

These rules apply to every task directory under the workspace root.

1. Start each task by identifying the task directory under `tasks/<task-name>/`.
   If the task directory does not exist and the user is asking for
   implementation, validation, or review work, create the standard layout from
   `AGENTS.md`.
2. Before working inside an existing task directory, read
   `TASK_DESCRIPTION.md` for the stable request, intended scope, acceptance
   criteria, and non-status background. If it is missing, create or refresh it
   from `agent_tools/paf_workspace/templates/TASK_DESCRIPTION.md`.
3. Read `TASK_CONTEXT.md` only after the directory is selected as the target
   task, or when the user explicitly asks to inspect neighboring or related
   tasks. Do not scan every neighboring `TASK_CONTEXT.md` during normal task
   discovery. `TASK_CONTEXT.md` is the compact active working set, not the
   historical log. If it is missing or too sparse to continue safely, query or
   create `TASK_CONTEXT.sqlite3` with
   `python3 -m agent_tools.tools.task_context` and regenerate compact context.
4. Identify the task topics before deep work. Read
   `agent_tools/knowledge/README.md` and every matching topic file under
   `agent_tools/knowledge/topics/`, for example Xen/QEMU work reads
   `topics/xen.md`, workspace tool work reads `topics/agent_tools.md`, and
   Moulin product work reads `topics/moulin.md`. Record the topic files read
   through the task context journal.
5. Maintain task context through the structured journal:

   - `TASK_CONTEXT.sqlite3` is the transactional journal of dated findings.
   - `TASK_CONTEXT.md` is generated compact active context for the next human
     or agent session.
   - Use `python3 -m agent_tools.tools.task_context add --task <task-dir> ...`
     to record facts with severity, status, labels, details, and artifacts.
   - Use `python3 -m agent_tools.tools.task_context query --task <task-dir>
     ...` to retrieve history by date, severity range, status, or labels.
   - Use `python3 -m agent_tools.tools.task_context compact --task <task-dir>`
     before handoff, after validation, after resolving blockers, and whenever
     `TASK_CONTEXT.md` is becoming noisy. Legacy JSONL journals can be imported
     once with `python3 -m agent_tools.tools.task_context migrate --task <task-dir>`.

   Severity values are `note`, `low`, `mid`, `high`, and `critical`. Status
   values are `active`, `resolved`, and `stale`. Prefer stable labels such as
   `goal`, `repo`, `decision`, `blocker`, `validation`, `build`, `runtime`,
   `env`, `artifact`, `report`, `ui`, `bug`, `test`, `user-preference`, and
   `next-step`.

6. Record the task bootstrap through the task context journal before deep work:

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

7. For tasks that need a reusable environment, choose the environment before
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
8. Track validation by level instead of using one ambiguous "validated" note:

   ```text
   static: code maps, parse checks, linters, schema checks
   build: authoritative compile or package build
   runtime: emulator, hypervisor, integration, or hardware run
   review: generated diff report or reviewer artifact
   ```

   Mark each level as `not run`, `pass`, `fail`, or `blocked`, with the exact
   command or artifact path that supports the status.
9. When a workspace tool or environment command fails, do not silently bypass
   it. Record the command, short failure summary, whether it blocks exact
   source analysis or only fast feedback, and the next fix through the task
   context journal.
10. Keep source, generated build output, product output, runtime logs, and
   review/report artifacts separate. Fix the source, product definition, or
   reusable environment that reproduces generated output; do not hand-edit
   generated output unless the task explicitly asks for generated artifact
   patching.
11. For runtime products that combine multiple target artifacts, maintain a
    task-owned artifact manifest based on
    `agent_tools/paf_workspace/templates/product-artifacts.yaml`. Keep it under
    the task's `dev/` tree and update it when artifact paths, domain roles, or
    compile databases change.
12. Task-local GUI actions are the normal way to expose repeated task commands
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
13. Keep commit-ready source/tooling changes separate from review/report
    artifacts unless the user asks to include both. Review tasks place reports
    under `report/`; source tasks should not accumulate report output as a side
    effect.
14. Task directories are local workspace state, not part of the public
    `agent_tools` repository payload. Do not merge or push `tasks/<task-name>/`
    contents into `agent_tools`; keep only the `tasks/` placeholder files
    needed to preserve the local directory layout in a fresh checkout. If a
    task directory was accidentally tracked, remove it from Git with
    `git rm --cached -r tasks/<task-name>` so the local files stay available.
