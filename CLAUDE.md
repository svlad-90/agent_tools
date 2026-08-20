# Claude Code workspace instructions

Read and follow `AGENTS.md` in this directory. It is the canonical workspace instruction file and loads the shared rule files under `agent_tools/rules/`.

<!-- BEGIN GENERATED agent_tools/tools/rules_sync: always-rules -->

<!-- Source: agent_tools/rules/git-commits.md -->

## Git commit workflow

These rules apply to every repository under the workspace root.

1. Unless the user explicitly asks for a different format, every commit
   message must wrap lines at 72 characters.
2. Every commit message must include a `Signed-off-by` trailer matching the
   repository author's local Git identity. Prefer `git commit -s` when it fits.

   ```text
   Signed-off-by: Name <email@example.com>
   ```

   Exception: when preparing commits or pull requests for the Zephyr project,
   including Zephyr mainline and Xen Troops / xen-troops related branches, AI
   agents must not add `Signed-off-by` trailers or otherwise certify the
   Developer Certificate of Origin. Only the human submitter may add their own
   `Signed-off-by` after reviewing the contribution, checking license
   compatibility, and taking responsibility for the change.

   Before adding a `Signed-off-by` trailer on behalf of the human user, ask the
   user for explicit permission in the current task context. Do this even when
   a repository hook requires the trailer before push. If the permission was
   granted earlier in a long-running task, mention that permission before
   pushing so the user can stop or correct the push.

   For Zephyr pull requests that used AI assistance, include an
   `Assisted-by` trailer in the contribution metadata:

   ```text
   Assisted-by: Codex:gpt-5 <specialized-tool>
   ```

   Use the current agent and model name, and list only specialized analysis
   tools that materially assisted the contribution. Do not list basic
   development tools such as `git`, compilers, build systems, or editors.

3. Paragraphs in the commit body are allowed. Do not add gratuitous blank
   lines that create empty paragraphs.
4. Put trailers in a separate trailer block: add one blank line before
   `Signed-off-by`.
5. When drafting, rewriting, or amending commit messages, prefer the workspace
   formatter before committing:

   ```sh
   python -m agent_tools.tools.commit_msg --repo path/to/repo draft-message.txt \
     --output formatted-message.txt --check
   git -C path/to/repo commit -F formatted-message.txt
   ```

   The formatter wraps body paragraphs to 72 columns and adds the
   `Signed-off-by` trailer from the target repository's `git config`
   `user.name` and `user.email`. Do not use this automatic trailer insertion
   when drafting Zephyr project commits or pull requests unless the human
   submitter has explicitly provided the `Signed-off-by` text to include.
6. Before any `git push`, run the repository's authoritative build or
   validation command successfully. Use the normal project build when one
   exists; for CI-only or tooling repositories, run the closest local
   equivalent of the pushed workflow. Record the exact successful command in
   the task context, final response, or handoff notes before pushing.

   Enforce this with the workspace push guard in every repository that will be
   pushed:

   ```sh
   python -m agent_tools.tools.push_guard install-hook
   <build-or-validation-command>
   python -m agent_tools.tools.push_guard mark-success \
     --source <build-or-validation-id>
   git push
   ```

   The `mark-success` command records a successful build for the current
   commit, and the installed pre-push hook rejects pushes whose local commit
   tip has no recorded success. `push_guard` must not wrap or execute the build
   command itself; the build workflow owns validation and records the stamp
   after success.

   For reusable build systems such as PAF, pass the target repository to the
   PAF workspace build or validation scenario so its final `push_guard` phase
   records the stamp after a successful build:

   ```sh
   agent_tools/paf_workspace/run-paf.sh <scenario-file> <scenario> \
     --parameter PUSH_GUARD_REPO=<target-repo> \
     --parameter PUSH_GUARD_SOURCE=<build-or-validation-id>
   ```

   The pre-push hook checks only for the repository-local marker under the
   target repository's Git metadata, so the same marker must be written by the
   build workflow that actually validated the commit.

   The installed hook also checks the commit messages being pushed. It rejects
   pushed commits with lines longer than 72 columns, missing `Signed-off-by`
   trailers, and, for Zephyr repositories, missing Zephyr-format
   `Assisted-by` trailers.

   If the build cannot be run or fails, do not push unless the user explicitly
   overrides this rule after being told the exact command and failure or
   blocker.
7. Do not store personal Git identities, email addresses, usernames, tokens, or
   organization-specific account mappings in tracked workspace files. Use local
   Git config, environment variables, or ignored/private configuration files.

   Repositories with GitHub remotes under `xen-troops` require an explicit
   private identity rule before push. Configure it outside tracked source, for
   example via:

   ```sh
   git config agentTools.identityRulesFile ~/.config/agent_tools/identity-rules.json
   ```

   The JSON file uses this shape:

   ```json
   {
     "rules": [
       {
         "github_owner": "xen-troops",
         "user_name": "Name From Local Git Config",
         "user_email": "email-from-local-git-config@example.com"
       }
     ]
   }
   ```

   The pre-push commit-message hook checks the target repository's local
   `user.name` and `user.email` against that private rule. Keep the concrete
   personal values out of commits, public knowledge, and task artifacts unless
   the task explicitly requires sharing them.

   When reporting commit or hook results back to the user, do not echo the
   concrete local Git identity from `git log`, `git config`, or hook output.
   Say that the sign-off matched the repository's local identity, or that the
   local identity must be checked, without repeating the name or email.

<!-- Source: agent_tools/rules/task-workflow.md -->

## Task workflow

These rules apply to every task directory under the workspace root.

1. Start each task by identifying the task directory under `tasks/<task-name>/`.
   If the task directory does not exist and the user is asking for
   implementation, validation, or review work, create the standard layout from
   `AGENTS.md`.
2. Before working inside an existing task directory, read
   `TASK_DESCRIPTION.md` for the stable request, intended scope, acceptance
   criteria, and non-status background. If it is missing, create or refresh it
   from `agent_tools/paf_workspace/templates/TASK_DESCRIPTION.md`.
3. Query active task context from `TASK_CONTEXT.sqlite3` only after the
   directory is selected as the target task, or when the user explicitly asks
   to inspect neighboring or related tasks. Use
   `python3 -m agent_tools.tools.task_context query --task <task-dir>
   --severity mid..critical --status active --format markdown`. Do not scan every
   neighboring task context database during normal task discovery. Active
   entries are the compact working set, not the historical log. If the database
   is missing or too sparse to continue safely, create or update it with
   `python3 -m agent_tools.tools.task_context`.
4. Identify the task topics before deep work. Read
   `agent_tools/knowledge/README.md` and every matching topic file under
   `agent_tools/knowledge/topics/`, for example Xen/QEMU work reads
   `topics/xen.md`, workspace tool work reads `topics/agent_tools.md`, and
   Moulin product work reads `topics/moulin.md`. Record the topic files read
   through the task context journal.
5. Maintain task context through the structured journal:

   - `TASK_CONTEXT.sqlite3` is the transactional journal of dated findings and
     the only task context source.
   - Use `python3 -m agent_tools.tools.task_context add --task <task-dir> ...`
     to record facts with severity, status, labels, details, and artifacts.
   - Use `python3 -m agent_tools.tools.task_context query --task <task-dir>
     ...` to retrieve history by date, severity range, status, or labels.
   - Use `python3 -m agent_tools.tools.task_context edit --task <task-dir>
     ...` to batch update status, severity, labels, details, artifacts, or to
     delete selected erroneous entries.
   - Active context is a working set, not an append-only changelog. Before
     handoff, before final responses that change task state, before or after
     validation handoff, before push-ready handoff, after resolving blockers,
     and before every compaction, query active entries and update stale or
     superseded items with `task_context edit`. Completed or superseded entries
     must become `resolved`; obsolete or misleading entries must become
     `stale`; only facts that still affect the next session stay `active`.
   - Use `python3 -m agent_tools.tools.task_context compact --task <task-dir>`
     only after the active-entry audit when a compact active-context rendering
     is useful for review. It prints the current active working set; it must not
     regenerate a markdown task context file.
     Legacy JSONL journals can be imported once with
     `python3 -m agent_tools.tools.task_context migrate --task <task-dir>`.

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

<!-- END GENERATED agent_tools/tools/rules_sync -->
