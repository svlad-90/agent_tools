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
