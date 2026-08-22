# diff_report

Generate a GitHub-style HTML diff report with optional file-level and inline
review comments.

The same renderer can also produce a generic non-diff HTML report from a
`report-json` document. This mode is intended for task dashboards, status
reports, and evidence hubs that should reuse the diff report visual system,
diagram viewer, log viewer, story navigation, theme controls, and summary
blocks without requiring a source diff.

## Usage

```sh
python -m agent_tools.tools.diff_report \
  --repo path/to/repo \
  --range HEAD^..HEAD \
  --comments comments.json \
  --output review.html
```

You can also render an already prepared unified git diff:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file change.patch \
  --comments comments.json \
  --output review.html
```

To render a non-diff task dashboard:

```sh
python -m agent_tools.tools.diff_report \
  --report-json task/report/dashboard/dashboard.json \
  --output task/report/dashboard/index.html
```

For reports where comment anchors should be refreshed while regenerating the
HTML, enable target refresh:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file change.patch \
  --comments comments.json \
  --output review.html \
  --refresh-targets
```

In this mode the tool validates the comments JSON, updates a JSON file with
the same basename as the report, and records generated `target` anchors in
that JSON. The generated HTML is still self-contained: comments are rendered
statically into the page, and the browser does not load JSON at runtime.

Use the same-basename JSON as the editable source for the next regeneration.
For example, `review.html` should be paired with `review.json`.

To reduce manual anchor lookup before writing review notes, initialize a starter
comments JSON from the diff:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file change.patch \
  --init-comments comments.json
```

The generated JSON keeps renderable `files` and `inline` comments empty and
adds `_template.files` plus `_template.added_lines` as a non-rendered target
catalog. Copy useful entries from `_template.added_lines` into `inline`, fill
`title` and `body`, then render or refresh the report normally.

For a lower-friction path, write draft findings and let the tool compose the
canonical comments JSON with target anchors:

```json
{
  "summary": "Short review summary.",
  "files": {
    "path/to/file.py": "File-level note."
  },
  "inline": [
    {
      "file": "path/to/file.py",
      "contains": "new_code_call(",
      "kind": "add",
      "title": "Review comment",
      "body": "Line-specific note."
    }
  ]
}
```

```sh
python -m agent_tools.tools.diff_report \
  --diff-file change.patch \
  --findings findings.json \
  --output-comments comments.json
```

Inline findings may use `line`, exact `content`, or substring `contains`.
Content-based matches must resolve to exactly one rendered new-file line in the
selected file. The generated `comments.json` can then be passed to normal
rendering or `--refresh-targets`.

To compose and render in one command, add `--output`:

```sh
python -m agent_tools.tools.diff_report \
  --diff-file change.patch \
  --findings findings.json \
  --output-comments comments.json \
  --output review.html
```

When writing findings by `content` or `contains`, add `--compose-report` to get
a JSON diagnostics file for entries that did not resolve cleanly. If diagnostics
are present, the tool still writes the resolved subset to `comments.json` but
does not render HTML.

Target refresh records a status for each inline comment:

- `found`: the existing `file` and `line` still point at a rendered diff line.
- `moved`: the old line no longer matched, but the old `target.content` was
  found exactly once in the same file; the tool updates `line` automatically.
- `ambiguous`: the old content exists more than once, so a human must choose.
- `not_found`: the old content was not found in the refreshed diff.

Comments with `found` and `moved` are sorted first in the JSON. Comments with
`ambiguous` or `not_found` are sorted after them, and the CLI prints their
JSON line ranges so they can be inspected without rereading the whole file.

## Comments JSON

```json
{
  "summary": "Optional plain-text summary shown above the diff.",
  "summary_blocks": [
    {
      "type": "text",
      "body": "Optional evidence-led summary paragraph."
    },
    {
      "type": "diagram",
      "diagram": "optional-diagram-id",
      "diagram_focus": ["SVG text to highlight from this summary preview"]
    },
    {
      "type": "text",
      "body": "Optional paragraph explaining the runtime proof."
    },
    {
      "type": "log",
      "log": "optional-log-id",
      "log_focus": ["Log line text to highlight from this summary preview"]
    }
  ],
  "files": {
    "path/to/file.py": "File-level review note shown under the file header."
  },
  "inline": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "range": {
        "start": 42,
        "end": 45
      },
      "title": "Review comment",
      "body": "Inline review note shown under the target new-file line.",
      "diagram": "optional-diagram-id",
      "diagram_focus": ["SVG text to highlight only from this link"],
      "diagram_notes": [
        {
          "target": "SVG arrow label text",
          "text": "Callout text shown inside the opened diagram"
        }
      ],
      "log": "optional-log-id",
      "log_focus": ["Log line text to highlight only from this link"],
      "target": {
        "file": "path/to/file.py",
        "line": 42,
        "old_line": 40,
        "new_line": 42,
        "kind": "context",
        "content": "    existing_code();",
        "diff_line": "     existing_code();",
        "found": true,
        "status": "found"
      }
    }
  ],
  "diagrams": {
    "optional-diagram-id": {
      "title": "Diagram title",
      "svg": "../puml/diagram.svg",
      "code_links": [
        {
          "target": "SVG arrow label text",
          "file": "path/to/file.py",
          "line": 42,
          "title": "Open implementation",
          "range": {"start": 42, "end": 45}
        }
      ]
    }
  },
  "logs": {
    "optional-log-id": {
      "title": "Runtime log",
      "path": "../runtime/test.log"
    }
  },
  "story": [
    {
      "title": "Start with the changed entry point",
      "body": "This step explains why the first review comment matters.",
      "comment": {
        "file": "path/to/file.py",
        "line": 42
      }
    },
    {
      "title": "Then inspect the flow diagram",
      "body": "The same diagram opens with only the relevant arrow highlighted.",
      "diagram": "optional-diagram-id",
      "diagram_focus": ["SVG arrow label text"]
    },
    {
      "title": "Finish with the validation signal",
      "body": "The log opens around the line that proves the behavior.",
      "log": "optional-log-id",
      "log_focus": ["expected log line"]
    }
  ]
}
```

## Report JSON

`status_cards` accepts either a plain card list or an object with `title`,
`note`, and `cards`, so a report can name the section after what the cards
actually track.

`metric_tables` renders top-down metric grids whose cells can open the
relationship graph in a specific view. A column may carry a `sublabel`, drawn
as a second header line, which keeps a long composite header from stretching
the column; metric-table headers wrap while the value cells stay on one line. Each cell may carry `graph_view` with:

- `focus`: required node id the graph focuses on;
- `types`: entity types to keep enabled, so intermediate layers collapse into
  `through_filtered` links;
- `target_type`: entity type the Focus dropdown is limited to;
- `filters`: `{entity_type: {field: [allowed values]}}` subfilter overrides,
  usually a status split such as passed versus failed. A `status` key is routed
  into the graph's single global status filter rather than a per-type one;
- `label`: tooltip text for the cell control.

A cell may also hold `parts`: a list of cell objects rendered inline in one
cell, each with its own status colour and `graph_view`. Use it to keep related
counts together, for example passed, failed, no-verdict, and not-executed in a
single column instead of four. Prefer buckets that are mutually exclusive and
exhaustive, so the parts add up to the row total and the reader never has to
guess about a hidden remainder.

`--report-json` accepts the same shared artifact fields as comments JSON:
`summary`, `summary_blocks`, `diagrams`, `logs`, `story`, and `vocabulary`.
It also supports dashboard-oriented widgets:

```json
{
  "title": "Task Dashboard",
  "summary_blocks": [
    {"type": "text", "body": "Current state and what changed recently."}
  ],
  "metrics": [
    {"label": "VSR rows", "value": 115, "status": "covered_candidate"},
    {"label": "Risks", "value": 4, "status": "risk", "note": "Security first pass"}
  ],
  "status_cards": {
    "title": "Processing progress",
    "note": "AI processing status of the analysis pipeline, not product compliance.",
    "cards": [
    {
      "title": "security",
      "status": "risk",
      "body": "SELinux and KeyMint need production evidence.",
      "metrics": [{"label": "rows", "value": 10}],
      "links": [{"label": "Security pass", "href": "../domains/security/VSR_SECURITY_PASS.md"}]
    }
    ]
  },
  "heatmaps": [
    {
      "title": "Domain Heatmap",
      "rows": [
        {"domain": "security", "status": "risk", "total": 10},
        {"domain": "storage_update", "status": "covered_candidate", "total": 4}
      ]
    }
  ],
  "metric_tables": [
    {
      "title": "Metrics",
      "note": "Passed and failed counts per requirement or test entity type.",
      "columns": [
        {"key": "name", "label": "Name"},
        {"key": "passed", "label": "Passed items"},
        {"key": "failed", "label": "Failed items", "sublabel": "share of total"}
      ],
      "rows": [
        {
          "cells": {
            "name": {
              "text": "CDD",
              "graph_view": {
                "focus": "product:gen5-aaos-xen",
                "types": ["product", "cdd"],
                "target_type": "cdd",
                "label": "Product to CDD requirements"
              }
            },
            "passed": {
              "text": "12 · 0.6%",
              "status": "pass",
              "graph_view": {
                "focus": "product:gen5-aaos-xen",
                "types": ["product", "cdd"],
                "target_type": "cdd",
                "filters": {"cdd": {"status": ["covered", "covered_candidate"]}}
              }
            },
            "failed": {"text": "50 · 2.3%", "status": "fail"}
          }
        }
      ]
    }
  ],
  "tables": [
    {
      "title": "Requirement Queue",
      "columns": ["id", "domain", "status", "next"],
      "rows": [
        {"id": "VSR-3.10-023", "domain": "security", "status": "risk", "next": "Confirm production KeyMint path."}
      ]
    }
  ],
  "timeline": [
    {"time": "2026-08-17", "title": "Security pass created", "status": "risk"}
  ],
  "relationship_graph": {
    "title": "Requirement Traceability",
    "nodes": [
      {
        "id": "vsr:GAS-VSR-3.2-001.006",
        "type": "vsr",
        "label": "AIDL for partner HALs",
        "status": "risk",
        "summary": "Partner-owned HAL implementations must use AIDL, not HIDL.",
        "details": {
          "rule": "MUST",
          "trigger": "A17+, api_level 202404+",
          "current_status": "Vendor manifests still expose HIDL audio/effect/VHAL.",
          "analysis_notes": "FCM 7 may still tolerate some HIDL rows, but VSR is stricter."
        }
      },
      {
        "id": "hal:android.hardware.audio@6.0",
        "type": "hal",
        "label": "audio@6.0 HIDL",
        "status": "risk"
      }
    ],
    "edges": [
      {
        "source": "vsr:GAS-VSR-3.2-001.006",
        "target": "hal:android.hardware.audio@6.0",
        "relation": "maps_to_hal"
      }
    ]
  },
  "artifacts": [
    {"title": "Product architecture", "path": "../analysis/product/architecture/PRODUCT_ARCHITECTURE.md", "kind": "markdown"}
  ],
  "toc_groups": [
    {
      "title": "Overview",
      "items": [
        {"label": "Top", "href": "#report-top"},
        {"label": "Metrics", "href": "#report-metrics"}
      ]
    },
    {
      "title": "Requirement Rows",
      "open": false,
      "items": [
        {"label": "Security VSR Rows", "href": "#report-table-2"}
      ]
    }
  ]
}
```

Supported widget status values are free-form strings, but the built-in visual
classes recognize common task states such as `covered`, `covered_candidate`,
`risk`, `needs_evidence`, `gap`, `not_applicable`,
`not_applicable_candidate`, `not_started`, `pass`, `fail`, and `blocked`.

Tables are filterable by default. Set `"filterable": false` on a table to omit
the search box. Table cell values may be strings or objects. Object cells can
use `text`, `status`, `href`, `diagram`, or `log` to combine badges, links,
and artifact previews.

`relationship_graph` renders an offline Cytoscape.js traceability browser. Each
node must have `id` and `label`; common optional fields are `type`, `status`,
`summary`, and a `details` object. Each edge must have `source` and `target`
pointing to existing node ids, plus an optional `relation`. The browser shows
the focused node, its parent chain up to the root, and the first visible child
frontier below the focus. Hidden intermediate layers are still traversed and
rendered as derived links where needed, but a visible child is not expanded
again on the same canvas page. This keeps each page an overview rather than a
flat slice of a large subtree. It supports zoom, pan, and node drag,
keeps back/forward navigation, groups the selector by node type, and renders a
detail panel with related entities grouped by relation. Node types are rendered
with different shapes so a VSR, CDD, HAL, CTS/VTS module, and evidence artifact
are visually distinct. This is intended for requirement graphs such as
`VSR -> CDD -> HAL -> CTS/VTS -> Evidence -> Gap`.

The graph toolbar keeps one control per concept:

- `Status` chips are the status filter itself: one global set shared by every
  layer, generated from the statuses present in the graph, carrying whole-graph
  node counts. Status is not a per-type subfilter, so toggling layers can never
  desynchronise it. The leading `All` control is a
  tri-state checkbox like the one in the `Layers` row: unchecking it hides every
  status so a single status can then be picked, checking it restores all, and it
  renders indeterminate while only some are on. There is no separate status
  legend and no status group inside the filter panel.
- `Layers` checkboxes control layer visibility only. Each chip counts how many
  nodes of that type the current focus contains, following directed edges down
  the type ranks, so a product focus reports its domains, CDD, VSR, and
  CTS/VTS totals while a VSR focus reports the tests and HALs under it. The
  count is independent of the first-frontier canvas rule and of how many nodes
  fit on the current graph page. The counts live in the chip
  tooltip, not in the label, so a chip never changes width and the row never
  shifts while filters change. Chip styling carries exactly one meaning: a
  dashed, dimmed chip draws nothing for the current focus, counting both the
  focus content and the ancestry the graph always draws above it, while a solid
  chip has something to show. The tooltip says which of the two reasons applies,
  nothing of that layer inside the focus or everything of it hidden by filters,
  and when only the focus itself ends up drawn the canvas states how many nodes
  the filters are holding back.
- `Focus type` limits the focus list to one entity type, and carries no counts:
  counting is the Layers row's job. It is user-owned: selecting a node no
  longer rewrites it. The `only visible` checkbox next to it narrows the focus
  list from every node in the graph to the nodes drawn on the current graph plus
  the focus ancestry, so a leaf focus still offers a way back up.
- Unchecking the `Layers` `All` box clears every layer and returns the focus to
  the graph root, so the next single layer click reads that layer from the top
  of the hierarchy instead of from wherever the previous focus was.
- The focus node is pinned against every filter, layers and status alike, so
  clearing all statuses leaves the same one-node view as clearing all layers
  instead of an empty graph with no focus at all. A pinned focus does not pull
  its own status back into the filter, so a status-filtered view stays exact.
- The focus node itself is always drawn, even when its own layer is unchecked,
  so hiding layers narrows what hangs off the focus instead of moving the
  focus. Unchecking every layer except one therefore answers "what is the first
  visible layer below this focus", for example product plus CDD lists the first
  CDD frontier under the product through hidden domains.
- `Filters` is a collapsed disclosure that shows the remaining per-type fields
  (suite, domain, applicability, and similar) and reports how many of them are
  narrowed. Its bulk `Defaults` and `All values` actions record navigation
  history like the individual value checkboxes.
- `Shortcuts` appears only when the current focus has shortcut links.
- `Fit`, back, forward, and paging live in one control bar above the canvas.

The table of contents is flat by default. Add `toc_groups` to render it as a
grouped tree. Each item `href` must point to a section id in the rendered page,
for example `#report-top`, `#report-metrics`, `#report-table-1`, or
`#report-artifacts`. Groups are open by default; set `"open": false` to start a
large group collapsed.

Inline comments are attached to new-file line numbers in the rendered diff.
Use `range` when the comment is about several rendered new-file lines instead
of one line. The range is inclusive, uses new-file line numbers, and can be
written either as `{"start": 42, "end": 45}` or `[42, 45]`. The `line` value
remains the anchor where the comment block is rendered and must be inside the
range.

The `target` object is generated by the tool in target-refresh mode. It records
the exact rendered diff line under the comment, so a later tool can re-anchor
the comment when only line numbers move.

## Reviewer Summary

Use top-level `summary` for a short plain-text reviewer summary. Use
`summary_blocks` when the summary should read like a proof narrative with
artifact previews between paragraphs. This is useful for review reports that
need to explain why the change works, not only what changed.

Supported summary block forms are:

- A plain string, rendered as a text paragraph.
- `{"type": "text", "body": "..."}` or `{"type": "paragraph", "body": "..."}`
  for an explicit text paragraph.
- `{"type": "diagram", "diagram": "diagram-id"}` to embed a diagram preview.
- `{"type": "log", "log": "log-id"}` to embed a log preview.

Summary diagram and log previews use the same modal viewers as comment
artifacts. `diagram_focus`, `diagram_notes`, and `log_focus` are scoped to that
specific preview, so the same reusable artifact can be opened with different
highlighting from the summary, file comments, inline comments, or story.

## Story

Use the top-level `story` array when the report should guide the reader through
the review in a deliberate order. The generated report shows a sticky story
panel with `Prev` and `Next` controls. Selecting a story step scrolls to the
targeted file, diff line, or review comment. Supporting diagrams and logs stay
attached to the comments that explain them, so the story panel remains a compact
navigation route instead of becoming a second artifact index.

Each story step requires `title` and one target. Use `body` for the narrative
sentence that explains why the reader is looking at this step. Supported
targets are:

- `{"file": "path/to/file.py"}` to scroll to a changed file.
- `{"file": "path/to/file.py", "line": 42}` to scroll to a rendered new-file
  diff line.
- `{"comment": {"file": "path/to/file.py", "line": 42}}` to scroll to an
  inline review comment.
When the reader opens a diagram or log from the selected comment, the modal can
show the active story step title and body above the artifact.

## Diagrams

Comments may reference SVG diagrams through a `diagram` id. Diagrams are
declared once in the top-level `diagrams` object and can use either `svg`, a
path to a local `.svg` file relative to the comments JSON, or `svg_inline`, an
inline SVG string. The generated HTML embeds the SVG content directly, shows a
preview in the comment, and opens a modal when the preview is clicked. The
modal supports zoom buttons, a live zoom percentage, `Ctrl` + mouse wheel zoom
over the diagram, drag-to-pan with the mouse, scrolling at larger scales,
local `Ctrl` + `F` search over visible SVG text, close by backdrop click, close
by the toolbar button, and close by `Esc`.

Use `diagram_focus` on a specific file-level or inline comment link when the
same reusable diagram should open with context-specific SVG text highlighted.
The focus terms are matched against visible SVG text and are applied only when
the diagram is opened from that particular comment link.

Use `diagram_notes` on a specific file-level or inline comment link when the
opened diagram needs explanatory callouts inside the SVG. Each note uses
`target` to match visible SVG text, typically an arrow label, and `text` for
the callout body. The diagram shows a small note marker next to the matched
arrow, and hovering either the marker or the arrow/label opens the full
callout. Note callouts do not react to clicks, do not make text bold on hover,
and keep the original sequence arrow above the callout overlays. If a note
target is also included in `diagram_focus`, the tool highlights the target
label and sequence arrow without drawing a focus box around that arrow label.
Automatically placed callouts stay near their target arrow instead of drifting
across the whole diagram; set explicit `x` and `y` only when the automatic
placement is not good enough.

Use `code_links` on a diagram when an important SVG arrow should open the
corresponding rendered diff code. Each link uses `target` to match visible SVG
text, usually the arrow label, plus `file` and `line` to point at a rendered
new-file line in the diff. Use `line` for the exact call or assignment that
represents the diagram arrow, and use optional `range` for the surrounding
function or block context. In the opened diagram, the matched label and
nearby arrow connector become clickable. Clicking either one opens a
scrollable code popover over the diagram. The popover shows the available
rendered diff context for that file, lightly highlights the context range,
strongly highlights the exact target line, and
can be closed without leaving or shifting the diagram. The popover is modal
inside the diagram viewer: it appears centered over a translucent backdrop,
keeps the diagram at the same scroll position, closes when the backdrop is
clicked, and renders highlighted rows as continuous full-width code lines.
Clickable arrow connectors also get an invisible rectangular hit area around
the visible arrow connector and label. Hovering any part of a code link,
including the hit area, highlights the visible arrow connector and label in
blue so the reader can see what will open before clicking. If the same arrow
has a diagram note, that note also opens on hit-area hover. When the same
label text appears more than once in a
diagram, hover and active highlighting are scoped to the specific SVG
occurrence that the reader is pointing at.
When a code link is also part of the `diagram_focus` for the currently opened
comment, the focused-comment styling wins so all arrows relevant to that
comment read as one blue group.

## Logs

Comments may reference logs through a `log` id. Logs are declared once in the
top-level `logs` object and can use either `path`, a local text file path
relative to the comments JSON, or `text_inline`, an inline log string. The
generated HTML embeds the log text directly, shows a compact preview in the
comment, and opens the clicked log in a modal. The modal search field filters
within the opened log only; `Ctrl` + `F` focuses that local search field, and
`Enter` / `Shift` + `Enter` moves through matches.

Use `log_focus` on a specific file-level or inline comment link when the same
reusable log should open with context-specific lines highlighted. The focus
terms are matched against full log lines and are applied only when the log is
opened from that particular comment link.

## Future Ideas

A future report version could offer an optional local "Ask about this
selection" assistant bridge. Keep this out of generated reports until it is
intentionally implemented.

A reasonable design would let selection-aware report UI collect selected text
plus nearby file, line, comment, diagram, or log context. A task-local server
bound only to `127.0.0.1` could receive questions through `POST`, require a
random session token, and append the first implementation's requests to a
task-local JSONL queue. A later implementation could own a separate Codex or
model subprocess and stream replies back through SSE or WebSocket. Do not
embed API keys in self-contained HTML, and do not try to write into an existing
interactive terminal session from browser JavaScript.
