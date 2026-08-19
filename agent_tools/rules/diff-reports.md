---
sync: skill
---

# Diff report workflow

These rules apply to diff/review reports generated under task `report/diff/`
directories.

1. Generate review reports with `python -m agent_tools.tools.diff_report`. Put the
   generated HTML, canonical comments JSON, and source diff or patch under the
   task's `report/diff/` directory.
2. Use stable commit indexes instead of commit hashes in human-facing report
   names, report titles, reviewer summaries, and explanatory comments.
   Number commits by their order in the reviewed series, starting from `01`,
   and keep that index consistent across `.html`, `.json`, and `.patch` files.
   Commit hashes may remain in raw git patch metadata.
3. When a report is generated for a commit or another diff source that has a
   commit message, include that commit message in its own section of the HTML
   report.
4. Replace stale report artifacts when a report is regenerated for the same
   task or review scope. Do not keep old `.html`, `.json`, `.diff`, or `.patch`
   alternatives for superseded versions.
5. Keep one canonical comments JSON per HTML report, using the same basename
   as the HTML report. For iterated reports, run `diff_report` with
   `--refresh-targets` before rendering so existing inline comments are
   re-anchored from their stored `target` data.
6. Preserve generated inline-comment `target` objects in the canonical JSON.
   Treat `found` and `moved` refresh results as handled by the tool; inspect
   `ambiguous` and `not_found` results manually before rendering the final
   report.
7. Reports may embed diagrams and logs through the top-level `diagrams` and
   `logs` objects in the comments JSON. Keep task-owned PlantUML sources and
   rendered adjacent SVG files under `report/puml/`, and keep task-owned
   runtime logs under the task's `report/` tree.
8. Non-trivial reports should use `summary_blocks` for evidence-led summaries
   and a top-level `story` array when the reader needs a guided route through
   the diff.
9. Write report prose in a human mentoring voice for a capable reader who is
   learning the subsystem. Explain what the reader is seeing, why it matters,
   what would break without it, and then name the exact symbol, file, or API.
10. Detailed comments JSON fields and generated viewer behavior are tool
    documentation, not workspace policy. Consult `agent_tools/tools/diff_report/README.md`
    when authoring reports that use diagrams, logs, focused highlights, code
    links, or story navigation.
