---
name: patch-series-review
description: Shape, rewrite, validate, or review a git patch series as small human-reviewable commits, especially for serious external or open-source projects and reviewer-driven changes.
rule: agent_tools/rules/patch-series.md
---

# Patch Series Review

Use this skill when constructing, rewriting, validating, or reviewing a git
patch series. It is especially important for external projects where the
reviewer will read each commit independently.

Follow `agent_tools/rules/patch-series.md`; that rule is authoritative for
workspace patch-series policy.

## Workflow

1. Read the active task context and identify the base branch, target branch,
   and current patch series.
2. Inspect adjacent subsystem code that should influence architecture, naming,
   API shape, internal boundaries, tests, and validation.
3. Map user requirements and reviewer comments to commit-sized layers.
4. Rebuild or rewrite the series from the base branch so each commit has one
   clear reason to exist and can be reviewed independently.
5. Remove opportunistic cleanup unless it is directly required. Put required
   cleanup in its own commit with a concrete explanation.
6. Validate every buildable commit, then validate the final runtime behavior
   when the task has a runtime environment.
7. Generate per-commit review reports when reports are requested for a series.

## Output Expectations

When reporting back to the user, include:

- The commit order using stable indexes.
- Which reviewer comments each commit addresses.
- What was intentionally deferred to later commits.
- Any remaining risk, blocker, or validation gap.
- The exact validation command or artifact that proves the pushed series.
