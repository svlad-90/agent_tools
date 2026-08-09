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
   discovery. If the selected task's context is missing or too sparse to
   continue safely, create or refresh it from
   `agent_tools/paf_workspace/templates/TASK_CONTEXT.md`.
4. Identify the task topics before deep work. Read
   `agent_tools/knowledge/README.md` and every matching topic file under
   `agent_tools/knowledge/topics/`, for example Xen/QEMU work reads
   `topics/xen.md`, workspace tool work reads `topics/agent_tools.md`, and
   Moulin product work reads `topics/moulin.md`. Record the topic files read in
   `TASK_CONTEXT.md`.
5. Record the task bootstrap in `TASK_CONTEXT.md` before deep work:

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
   follow-up in `TASK_CONTEXT.md` before continuing.

   Use `--init-layout` to create a missing task layout from workspace
   templates. Use `--init-runtime-product` for Xen/QEMU/Moulin runtime tasks
   that need a starter artifact manifest and harness scenario.
   Before a long environment build or runtime run, use `--env-check-command`
   to print the reusable environment preflight command.
   Use `--run-env-check` only when the task should actually execute the
   environment domain's safe PAF check-only scenario.

6. For tasks that need a reusable environment, choose the environment before
   building or validating. Record the selected
   `agent_tools/paf_workspace/domains/environments/...` profile/scenario,
   reason for choosing it, PAF scenario/task entry point, and validation
   command in `TASK_CONTEXT.md`.
   Prefer running the task through its PAF scenario/build-run entry point when
   one exists. If a direct helper command fails or is tempting as a shortcut,
   first check whether the PAF scenario should be run or extended instead.
   For Xen/Zephyr, QEMU, Yocto, Moulin, and other runtime-product tasks,
   expand the task-local PAF scenario or reusable domain tasks so the build and
   validation remain reproducible; use direct helper scripts only as a focused
   diagnostic and record that exception in `TASK_CONTEXT.md`.
7. Track validation by level instead of using one ambiguous "validated" note:

   ```text
   static: code maps, parse checks, linters, schema checks
   build: authoritative compile or package build
   runtime: emulator, hypervisor, integration, or hardware run
   review: generated diff report or reviewer artifact
   ```

   Mark each level as `not run`, `pass`, `fail`, or `blocked`, with the exact
   command or artifact path that supports the status.
8. When a workspace tool or environment command fails, do not silently bypass
   it. Record the command, short failure summary, whether it blocks exact
   source analysis or only fast feedback, and the next fix in `TASK_CONTEXT.md`.
9. Keep source, generated build output, product output, runtime logs, and
   review/report artifacts separate. Fix the source, product definition, or
   reusable environment that reproduces generated output; do not hand-edit
   generated output unless the task explicitly asks for generated artifact
   patching.
10. For runtime products that combine multiple target artifacts, maintain a
    task-owned artifact manifest based on
    `agent_tools/paf_workspace/templates/product-artifacts.yaml`. Keep it under
    the task's `dev/` tree and update it when artifact paths, domain roles, or
    compile databases change.
11. Task-local GUI actions are the normal way to expose repeated task commands
    in `agent-workspace`. Declare them in `TASK_ACTIONS.json` at the task root
    whenever a task has useful build, component-build, test, smoke, report, or
    cleanup commands that a human may rerun without involving an AI agent.
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
    one-off experiments out of `TASK_ACTIONS.json`.
12. Keep commit-ready source/tooling changes separate from review/report
    artifacts unless the user asks to include both. Review tasks place reports
    under `report/`; source tasks should not accumulate report output as a side
    effect.
