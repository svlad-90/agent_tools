# Task workflow

These rules apply to every task directory under the workspace root.

1. Start each task by identifying the task directory. If the task directory
   does not exist and the user is asking for implementation, validation, or
   review work, create the standard layout from `AGENTS.md`.
2. Before working inside an existing task directory, read `TASK_CONTEXT.md`.
   If it is missing or too sparse to continue safely, create or refresh it from
   `codex_tools/paf_workspace/templates/TASK_CONTEXT.md`.
3. Identify the task topics before deep work. Read
   `codex_tools/knowledge/README.md` and every matching topic file under
   `codex_tools/knowledge/topics/`, for example Xen/QEMU work reads
   `topics/xen.md`, workspace tool work reads `topics/codex_tools.md`, and
   Moulin product work reads `topics/moulin.md`. Record the topic files read in
   `TASK_CONTEXT.md`.
4. Record the task bootstrap in `TASK_CONTEXT.md` before deep work:

   ```text
   goal, active repositories and branches, selected environment, build or
   product path, compile databases, runtime harness, validation path, blockers
   ```

   Use this command for a quick check of the task layout and workflow metadata:

   ```sh
   python -m codex_tools.paf_workspace.task_check <task-dir>
   ```

   Use `--init-layout` to create a missing task layout from workspace
   templates. Use `--init-runtime-product` for Xen/QEMU/Moulin runtime tasks
   that need a starter artifact manifest and harness scenario.
   Before a long environment build or runtime run, use `--env-check-command`
   to print the reusable environment preflight command.
   Use `--run-env-check` only when the task should actually execute the
   environment domain's safe PAF check-only scenario.

5. For tasks that need a reusable environment, choose the environment before
   building or validating. Record the selected
   `codex_tools/paf_workspace/domains/environments/...` profile/scenario,
   reason for choosing it, PAF scenario/task entry point, and validation
   command in `TASK_CONTEXT.md`.
6. Track validation by level instead of using one ambiguous "validated" note:

   ```text
   static: code maps, parse checks, linters, schema checks
   build: authoritative compile or package build
   runtime: emulator, hypervisor, integration, or hardware run
   review: generated diff report or reviewer artifact
   ```

   Mark each level as `not run`, `pass`, `fail`, or `blocked`, with the exact
   command or artifact path that supports the status.
7. When a workspace tool or environment command fails, do not silently bypass
   it. Record the command, short failure summary, whether it blocks exact
   source analysis or only fast feedback, and the next fix in `TASK_CONTEXT.md`.
8. Keep source, generated build output, product output, runtime logs, and
   review/report artifacts separate. Fix the source, product definition, or
   reusable environment that reproduces generated output; do not hand-edit
   generated output unless the task explicitly asks for generated artifact
   patching.
9. For runtime products that combine multiple target artifacts, maintain a
   task-owned artifact manifest based on
   `codex_tools/paf_workspace/templates/product-artifacts.yaml`. Keep it under
   the task's `dev/` tree and update it when artifact paths, domain roles, or
   compile databases change.
10. Keep commit-ready source/tooling changes separate from review/report
   artifacts unless the user asks to include both. Review tasks place reports
   under `report/`; source tasks should not accumulate report output as a side
   effect.
