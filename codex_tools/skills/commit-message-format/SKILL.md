---
name: commit-message-format
description: Format, rewrite, amend, or prepare git commit messages with the workspace commit-message formatter. Use when Codex drafts commit messages, rewrites a commit series, amends commits, cherry-picks with new messages, checks 72-column wrapping, or needs to add/normalize Signed-off-by trailers.
---

# Commit Message Format

Use the workspace workflow tool instead of hand-wrapping or manually checking
commit-message bodies. The tool calls the workspace formatter, reads the
target repository's `git config user.name` and `user.email`, wraps body
paragraphs to 72 columns, keeps trailers in a final trailer block, adds the
matching `Signed-off-by` line, and checks rewritten series.

## Workflow

1. Write the intended message as normal prose in a draft file. Keep the first
   line as the commit subject.
2. Format and commit through the script from the workspace root:

   ```sh
   python -m codex_tools.tools.commit_msg.workflow \
     --repo path/to/repo \
     --draft draft-message.txt \
     --commit
   ```

3. For amend:

   ```sh
   python -m codex_tools.tools.commit_msg.workflow \
     --repo path/to/repo \
     --draft draft-message.txt \
     --amend
   ```

4. For history rewrites, prefer `cherry-pick --no-commit` followed by
   `--commit` through this script so each replayed commit receives the checked
   message.

## Checks

- Re-run the script whenever message text changes.
- Run this final check on the resulting series:

  ```sh
  python -m codex_tools.tools.commit_msg.workflow \
    --repo path/to/repo \
    --check-series base..HEAD
  ```

- The check fails on any line over 72 columns or on a missing repository
  identity `Signed-off-by` trailer.
- If the subject itself is longer than 72 columns, rewrite the subject. Do not
  split a git subject across multiple lines.
