# Git commit workflow

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
   python -m codex_tools.tools.commit_msg --repo path/to/repo draft-message.txt \
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
   python -m codex_tools.tools.push_guard install-hook
   <build-or-validation-command>
   python -m codex_tools.tools.push_guard mark-success \
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
   codex_tools/paf_workspace/run-paf.sh <scenario-file> <scenario> \
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
