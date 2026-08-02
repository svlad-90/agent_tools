---
name: diff-review-report
description: Generate GitHub-style HTML diff review reports with file-level and inline comments using the workspace codex_tools.tools.diff_report CLI. Use when reviewing a repository, PR, commit, git diff, working tree changes, or creating/updating annotated HTML review reports under a task report/diff directory.
---

# Diff Review Report

Use the workspace implementation at `codex_tools/tools/diff_report`. Do not depend
on a globally installed Codex skill for this workflow.

Before generating or updating a report, read and follow
`codex_tools/rules/diff-reports.md`; it contains the workspace-specific report
policy, naming rules, refresh workflow, and requirements for diagrams, logs,
story blocks, and reviewer prose.

## Workflow

1. Inspect the target repository and choose the diff source.
   Use `--repo <repo> --range <base>..<head>` for committed changes, or
   `--diff-file <patch>` when the report must include a prepared patch or
   working-tree diff.
2. Store the source `.patch`/`.diff`, comments `.json`, and generated `.html`
   under the task's `report/diff/` directory.
3. Create or update one canonical comments JSON with the same basename as the
   HTML report.
4. Run `python -m codex_tools.tools.diff_report` from the workspace root.
5. Verify the generated HTML contains the expected title, files, and comment
   count with `rg`.
6. When the source diff changes, regenerate with the existing comments JSON
   and use the tool-assisted refresh path before manually changing anchors.

## Commands

Committed range:

```sh
python -m codex_tools.tools.diff_report \
  --repo path/to/repo \
  --range HEAD^..HEAD \
  --comments task/report/diff/01-change.json \
  --output task/report/diff/01-change.html \
  --title "Commit 01 Review"
```

Prepared diff:

```sh
python -m codex_tools.tools.diff_report \
  --diff-file task/report/diff/01-change.patch \
  --comments task/report/diff/01-change.json \
  --output task/report/diff/01-change.html \
  --title "Commit 01 Review"
```

## Checks

After generation, verify the report instead of assuming success:

```sh
rg -n "review comments loaded|Commit 01|known comment title" task/report/diff/01-change.html
```

If comments are missing, first confirm that `comments.inline[].file` matches
the diff path and `comments.inline[].line` is a rendered new-file line number.
