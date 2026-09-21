# SQLite Reports

Author entity types, ownership, association and context rules with the
[declarative graph model](GRAPH_MODEL.md), then store the compiled graph.

`diff_report.sqlite_store` owns the graph/document schema and serialization.
`diff_report.sqlite_runtime` packages that database and the bundled sql.js/WASM
runtime into one offline HTML file. Neither module needs AOSP tables or scripts.
The existing inline graph mode is still supported.

```python
import sqlite3
from pathlib import Path
from diff_report.sqlite_store import create_schema, write_report, read_report
from diff_report.sqlite_runtime import build_single_html
from diff_report.report_json import report_from_payload, render_report_json_html

connection = sqlite3.connect("report.sqlite3")
try:
    create_schema(connection)
    write_report(connection, payload)  # A normal report with relationship_graph.
    connection.commit()
    html = render_report_json_html(report_from_payload(read_report(connection)))
finally:
    connection.close()
Path("report.html").write_text(html, encoding="utf-8")
build_single_html(Path("report.html"), Path("report.sqlite3"), Path("single.html"))
```

## Store Contract

The store has one graph: `graph_nodes`, `graph_edges`, `graph_meta`, and report
documents in `report_documents`. Node/edge JSON preserves arbitrary metadata
and original order. The compiled model is stored in `graph_meta.model_json`;
generated edge provenance retains its source-edge references. `write_report` validates IDs, edge endpoints and contextual
child references; a failed write rolls back its own work. Applications may add
their own tables in the same database. `create_schema` initializes a fresh store;
these APIs do not merge multiple independent graphs.

Context edges use `source: parent`, `target: focus`, and `context_children` as an
explicit list of direct focus-child IDs. They are not containment links. The
application defines membership and verdicts; the renderer applies parent
inspection, history and pagination. Test cases need not be graph entities.

The optional `context_group` identifies a membership dimension, defaulting to the
parent node's type. It must be a non-empty string, consistent on every context
edge from the same parent. Membership constrains highlighted paths, not the
displayed child set. An explicitly empty membership highlights no children;
it never removes the focus or its contents.

Opening a topic through any parent shows its complete neighborhood, all context
parents and their ownership ancestors up to the product. The entry route does
not create a filter. Parent inspection prioritizes matching children within
their normal type ordering, highlights blue paths or shared group contours,
and dims unrelated alternatives without hiding them. The child set and primary
focus remain unchanged. There are no parent checkboxes or orange filter accents;
Ctrl+click has no separate filtering action.
It toggles an additive parent comparison: children shared by more selected
parents sort first, separate contours enclose each exact membership set, and numbered color
markers identify each child's parent memberships. Unrelated children remain
visible and dimmed. The comparison does not alter SQLite records or memberships.
Comparison is limited to one hierarchy rank: a click on another rank starts a
new selection. Ctrl/Command initiators have a distinct magenta outline;
ordinary inspection remains blue. Membership badges are numbered consecutively
within the selected basket in visual row order (left to right, then top to bottom),
independently of entity type or identifier, and scale with zoom. Leaf requirements can form a
basket even without visible descendants. The graph context menu can temporarily
show only related objects and fit them, then restore all objects; this does not
remove any database records or change the source graph.

An ancestor above multiple branching levels uses a set overview to avoid
repeating every member-to-member path. Dashed arrows aggregate existing links
between blocks, retain their exact edge IDs and show a connection count on
hover; they do not assert all-to-all membership. Narrower inspection restores
detailed paths. Adjacent CTS/VTS modules can share a visual block without
merging their entity types, verdicts or stored records.
Multi-parent comparisons use the same summary links between membership blocks.
Children shared by parents 1 and 2 appear once in a `1+2` block, separate from
the `1` and `2` blocks. This grouping never changes database memberships.

The AOSP producer omits domains without outgoing graph links, while retaining
the domain catalog. It aggregates execution signals from requirements into
subtopics and then topics. These are inherited execution signals, not new
compliance assessments; review status remains separate. A direct topic/module
association alone cannot grant a topic a test verdict.

Back and forward restore focus and pagination without inherited parent
restrictions. Ordinary status and hierarchy-level filters, search scope and
explicit Plain list remain available. Inspection never changes stored
memberships, application-provided node verdicts or review evidence.

## Browser Provider

`window.__diffReportData` exposes:

- `ready`: database initialization promise; rejects on load/configuration errors.
- `loadStatus()`: current state, message and overlay visibility.
- `getGraph()`: complete graph snapshot from SQLite.
- `query(url)`: a named query returning `{query, rows, count}` or a graph payload.

Built-in URLs are `/api/report/relationship-graph` and
`/api/report/search?q=...&limit=...`. Search reads generic graph nodes, not
application-specific leaf tables. The Python `query_report` function implements
the same built-in routes for HTTP hosts; the graph uses HTTP when no embedded
provider is present. SQL is never accepted from query-string parameters.

The database opens in memory at page load, with a full-screen progress overlay
inserted before report content. It is set to query-only mode. The graph snapshot
loads when needed; traversal, contextual filtering and pagination still run in
JavaScript. This extraction deliberately preserves that behavior rather than
changing every graph interaction into a SQL query.

## Application Query Plugins

Pass trusted JavaScript factory expressions through `query_plugins=(source,)` to
`build_single_html`. Each factory receives `queryRows`, `limitValue` and
`relationshipGraph`, and returns `{prefix, query}`:

```javascript
({queryRows, limitValue}) => ({
  prefix: "/api/inventory/",
  query(database, name, params) {
    if (name !== "parts") throw new Error("Unknown inventory query");
    return queryRows(database, "select name from parts limit ?",
      [limitValue(params.get("limit"))]);
  }
})
```

Prefixes must be unique `/api/<lowercase-name>/` paths; `/api/report/` is reserved.
Handlers return row arrays (or a structured payload for programmatic use).
Links to registered row queries open the shared, escaped drilldown table.
Factories are executable application code, not untrusted data or report input.
Use bound SQL parameters for values. Application hosts provide equivalent HTTP
handlers for their custom routes if server mode is required.

In the AOSP report, `src/scripts/aosp-sqlite-queries.js` supplies CTS/VTS queries
under the existing `/api/evidence/` URLs. Parsing, compliance statuses and
requirement-to-test mappings remain outside `diff_report`.
