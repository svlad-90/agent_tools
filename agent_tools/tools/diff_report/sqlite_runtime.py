from __future__ import annotations

import base64
import gzip
import json
from html.parser import HTMLParser
from pathlib import Path


SQLJS_VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "sqljs"
SQLJS_SCRIPT = SQLJS_VENDOR_DIR / "sql-wasm.js"
SQLJS_WASM = SQLJS_VENDOR_DIR / "sql-wasm.wasm"


class _BodyLocation(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in html.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.start: int | None = None
        self.end: int | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body" and self.start is None:
            line, column = self.getpos()
            self.start = self.offsets[line - 1] + column + len(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if tag == "body":
            line, column = self.getpos()
            self.end = self.offsets[line - 1] + column


class _GraphScriptLocation(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=False)
        self.offsets = [0]
        for line in html.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.content_start: int | None = None
        self.content_end: int | None = None
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script" or self.content_start is not None:
            return
        if not any(name == "data-relationship-graph-data" for name, _value in attrs):
            return
        line, column = self.getpos()
        self.content_start = self.offsets[line - 1] + column + len(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.content_start is not None and self.content_end is None:
            line, column = self.getpos()
            self.content_end = self.offsets[line - 1] + column


def _replace_graph_with_sqlite_manifest(html: str) -> str:
    location = _GraphScriptLocation(html)
    if location.content_start is None or location.content_end is None:
        return html
    try:
        graph = json.loads(html[location.content_start:location.content_end])
    except json.JSONDecodeError as error:
        raise ValueError("relationship graph script is not valid JSON") from error
    if not isinstance(graph, dict):
        raise ValueError("relationship graph script must be a JSON object")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("relationship graph script must contain node and edge lists")
    graph["data_source"] = "sqlite"
    graph["node_count"] = int(graph.get("node_count", len(nodes)))
    graph["edge_count"] = int(graph.get("edge_count", len(edges)))
    graph["nodes"] = []
    graph["edges"] = []
    manifest = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return html[:location.content_start] + manifest + html[location.content_end:]


def build_single_html(html_path: Path, database_path: Path, output_path: Path, *, query_plugins: tuple[str, ...] = ()) -> None:
    """Embed a read-only report store and switch its graph to SQLite delivery."""
    for path in (html_path, database_path, SQLJS_SCRIPT, SQLJS_WASM):
        if not path.is_file():
            raise ValueError(f"missing single HTML input: {path}")

    html = _replace_graph_with_sqlite_manifest(html_path.read_text(encoding="utf-8"))
    body = _BodyLocation(html)
    if body.start is None or body.end is None or body.end < body.start:
        raise ValueError(f"report HTML has no complete body element: {html_path}")
    sqljs_source = SQLJS_SCRIPT.read_text(encoding="utf-8")
    wasm_base64 = encode_base64(SQLJS_WASM.read_bytes())
    database_base64 = encode_base64(gzip.compress(database_path.read_bytes(), compresslevel=9))
    injection = single_html_injection(sqljs_source, wasm_base64, database_base64, query_plugins)
    bootstrap_end = injection.index('<script type="application/octet-stream"')
    bootstrap, runtime = injection[:bootstrap_end], injection[bootstrap_end:]
    html = html[:body.start] + bootstrap + html[body.start:body.end] + runtime + html[body.end:]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def encode_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def single_html_injection(sqljs_source: str, wasm_base64: str, database_base64: str, query_plugins: tuple[str, ...] = ()) -> str:
    query_plugins_source = ",\n".join(query_plugins)
    return f"""
<style>
.embedded-evidence-load-status[hidden] {{ display: none; }}
.embedded-evidence-load-status {{
  align-items: center;
  background: rgba(15, 23, 42, 0.32);
  bottom: 0;
  display: flex;
  justify-content: center;
  left: 0;
  padding: 24px;
  position: fixed;
  right: 0;
  top: 0;
  z-index: 10001;
}}
.embedded-evidence-load-panel {{
  background: #ffffff;
  border: 1px solid #9aa7b8;
  border-left: 4px solid #2563eb;
  border-radius: 8px;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.16);
  color: #111827;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  max-width: min(420px, calc(100vw - 32px));
  padding: 10px 12px 12px;
  width: 360px;
}}
.embedded-evidence-load-status[data-state="ready"] .embedded-evidence-load-panel {{ border-left-color: #16803a; }}
.embedded-evidence-load-status[data-state="error"] .embedded-evidence-load-panel {{ border-left-color: #dc2626; }}
.embedded-evidence-load-title {{
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 4px;
}}
.embedded-evidence-load-detail {{
  color: #4b5563;
  font-size: 12px;
  line-height: 1.35;
  margin-bottom: 8px;
}}
.embedded-evidence-progress {{
  background: #e5e7eb;
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}}
.embedded-evidence-progress > div {{
  background: #2563eb;
  height: 100%;
  transition: width 180ms ease;
  width: 3%;
}}
.embedded-evidence-load-status[data-state="ready"] .embedded-evidence-progress > div {{
  background: #16803a;
}}
.embedded-evidence-load-status[data-state="error"] .embedded-evidence-progress > div {{
  background: #dc2626;
}}
</style>
<div class="embedded-evidence-load-status" role="status" aria-live="polite" data-state="loading">
  <div class="embedded-evidence-load-panel">
    <div class="embedded-evidence-load-title">Loading evidence database</div>
    <div data-load-detail class="embedded-evidence-load-detail">Preparing...</div>
    <div class="embedded-evidence-progress"><div data-load-progress></div></div>
  </div>
</div>
<script>
{sqljs_source}
</script>
<script type="application/octet-stream" id="embedded-sqlite-wasm">{wasm_base64}</script>
<script type="application/gzip" id="embedded-sqlite-db">{database_base64}</script>
<script>
(function () {{
  const API_PREFIX = "/api/report/";
  // Embedded API paths are data keys, not navigable URLs. A document preview may
  // expose an opaque location (for example, about:blank), which cannot resolve
  // a root-relative path against window.location.href.
  const QUERY_URL_BASE = "https://embedded-report.invalid/";
  let plugins = [];
  let databasePromise = null;
  const loadStatus = createLoadStatus();
  const overlay = createOverlay();

  function base64Bytes(value) {{
    const clean = String(value || "").replace(/\\s+/g, "");
    const binary = atob(clean);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {{
      bytes[index] = binary.charCodeAt(index);
    }}
    return bytes;
  }}

  async function gunzipBytes(bytes) {{
    if (!("DecompressionStream" in window)) {{
      throw new Error("This browser cannot decompress the embedded SQLite database.");
    }}
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }}

  async function evidenceDatabase() {{
    if (!databasePromise) {{
      databasePromise = (async () => {{
        plugins = [{query_plugins_source}].map(factory => factory({{queryRows, limitValue, relationshipGraph}}));
        const prefixes = new Set([API_PREFIX]);
        for (const plugin of plugins) {{
          if (!plugin || typeof plugin.query !== "function" || !/^[/]api[/][a-z0-9-]+[/]$/.test(plugin.prefix)
              || prefixes.has(plugin.prefix)) throw new Error("Invalid or duplicate report query plugin prefix");
          prefixes.add(plugin.prefix);
        }}
        updateLoadStatus("Decoding SQLite runtime...", 12, "loading");
        const wasmBytes = base64Bytes(document.getElementById("embedded-sqlite-wasm").textContent);
        updateLoadStatus("Decoding compressed database...", 28, "loading");
        const compressedDatabase = base64Bytes(document.getElementById("embedded-sqlite-db").textContent);
        updateLoadStatus("Unpacking SQLite database into memory...", 55, "loading");
        const databaseBytes = await gunzipBytes(compressedDatabase);
        const header = "SQLite format 3";
        if (databaseBytes.length < 100 || databaseBytes[15] !== 0
            || Array.from(header).some((char, index) => databaseBytes[index] !== char.charCodeAt(0))) {{
          throw new Error("Invalid embedded SQLite database header");
        }}
        updateLoadStatus("Initializing SQLite runtime...", 80, "loading");
        const SQL = await initSqlJs({{wasmBinary: wasmBytes}});
        updateLoadStatus("Opening evidence database...", 92, "loading");
        const database = new SQL.Database(databaseBytes);
        database.exec("select name from sqlite_master limit 1");
        database.run("PRAGMA query_only = ON");
        updateLoadStatus("Evidence database ready", 100, "ready");
        return database;
      }})();
      databasePromise.catch((error) => {{
        updateLoadStatus("Report database failed to load: " + String(error.message || error), 100, "error");
      }});
    }}
    return databasePromise;
  }}

  function rowsFromStatement(statement) {{
    const rows = [];
    const columns = statement.getColumnNames();
    while (statement.step()) {{
      const values = statement.get();
      const row = {{}};
      columns.forEach((column, index) => {{
        row[column] = values[index];
      }});
      rows.push(row);
    }}
    return rows;
  }}

  function queryRows(database, sql, params) {{
    const statement = database.prepare(sql);
    try {{
      statement.bind(params || []);
      return rowsFromStatement(statement);
    }} finally {{
      statement.free();
    }}
  }}

  function limitValue(value) {{
    const parsed = Number.parseInt(value || "200", 10);
    if (!Number.isFinite(parsed)) return 200;
    return Math.max(1, Math.min(parsed, 5000));
  }}

  function reportQuery(database, name, params) {{
    if (name === "relationship-graph") return relationshipGraph(database);
    if (name === "search") {{
      if (!params.get("q")) throw new Error("search requires q");
      const pattern = "%" + params.get("q") + "%";
      return queryRows(database,
        "select node_id as entity_id, node_type as entity_type, label as title, status from graph_nodes where node_id like ? or label like ? order by position limit ?",
        [pattern, pattern, limitValue(params.get("limit"))]);
    }}
    throw new Error("Unsupported report query: " + name);
  }}

  function relationshipGraph(database) {{
    const metaRows = queryRows(database, "select key, value from graph_meta", []);
    const meta = {{}};
    metaRows.forEach((row) => {{
      meta[row.key] = row.value;
    }});
    const nodes = queryRows(database, "select node_json from graph_nodes order by position", [])
      .map((row) => JSON.parse(row.node_json));
    const edges = queryRows(database, "select edge_json from graph_edges order by position", [])
      .map((row) => JSON.parse(row.edge_json));
    return {{
      title: meta.title || "Relationship Graph",
      ...(meta.model_json && meta.model_json !== "null" ? {{model: JSON.parse(meta.model_json)}} : {{}}),
      nodes,
      edges,
      traversal: JSON.parse(meta.traversal_json || "{{}}"),
      filter_defaults: JSON.parse(meta.filter_defaults_json || "{{}}"),
      status_order: JSON.parse(meta.status_order_json || "[]"),
      count: nodes.length
    }};
  }}

  function createOverlay() {{
    const element = document.createElement("div");
    element.className = "embedded-evidence-overlay";
    element.hidden = true;
    element.innerHTML = `
      <div class="embedded-evidence-dialog" role="dialog" aria-modal="true" aria-label="Evidence query result">
        <div class="embedded-evidence-header">
          <strong data-evidence-title>Evidence Query</strong>
          <button type="button" data-evidence-close>Close</button>
        </div>
        <div data-evidence-body class="embedded-evidence-body"></div>
      </div>`;
    element.querySelector("[data-evidence-close]").addEventListener("click", () => {{
      element.hidden = true;
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") element.hidden = true;
    }});
    document.body.appendChild(element);
    return element;
  }}

  function createLoadStatus() {{
    let element = document.querySelector(".embedded-evidence-load-status");
    if (!element) {{
      element = document.createElement("div");
      element.className = "embedded-evidence-load-status";
      element.setAttribute("role", "status");
      element.setAttribute("aria-live", "polite");
      element.dataset.state = "loading";
      element.innerHTML = `
        <div class="embedded-evidence-load-panel">
          <div class="embedded-evidence-load-title">Loading evidence database</div>
          <div data-load-detail class="embedded-evidence-load-detail">Preparing...</div>
          <div class="embedded-evidence-progress"><div data-load-progress></div></div>
        </div>`;
      document.body.appendChild(element);
    }}
    return {{
      element,
      detail: element.querySelector("[data-load-detail]"),
      progress: element.querySelector("[data-load-progress]")
    }};
  }}

  function updateLoadStatus(message, percent, state) {{
    if (!loadStatus) return;
    const boundedPercent = Math.max(0, Math.min(Number(percent) || 0, 100));
    loadStatus.element.hidden = false;
    loadStatus.element.dataset.state = state || "loading";
    loadStatus.detail.textContent = message;
    loadStatus.progress.style.width = `${{boundedPercent}}%`;
    if (state === "ready") {{
      loadStatus.element.hidden = true;
    }}
  }}

  function showOverlay(title, bodyHtml) {{
    overlay.querySelector("[data-evidence-title]").textContent = title;
    overlay.querySelector("[data-evidence-body]").innerHTML = bodyHtml;
    overlay.hidden = false;
  }}

  function esc(value) {{
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }}

  function parseEmbeddedQueryUrl(href) {{
    return new URL(String(href || ""), QUERY_URL_BASE);
  }}

  function renderRows(rows) {{
    if (!rows.length) return "<p>No rows matched this query.</p>";
    const sourceCaseColumns = ["id", "case_name", "kind", "presence", "result", "source_review", "source_review_requirements"];
    const sourceCaseInternalColumns = new Set([
      "source_only_case_id", "source_review_status", "source_review_artifact",
      "source_review_catalog_current", "source_review_snapshot_current", "source_review_links"
    ]);
    const rowKeys = Object.keys(rows[0]);
    const columns = rowKeys.includes("source_review_links")
      ? sourceCaseColumns.filter((column) => rowKeys.includes(column)
          && (column !== "source_review_requirements" || rows.some((row) => row[column] !== "")))
      : rowKeys.filter((column) => !sourceCaseInternalColumns.has(column));
    const header = columns.map((column) => `<th>${{esc(column)}}</th>`).join("");
    const cell = (column, value) => column.endsWith("_api") && [API_PREFIX, ...plugins.map(plugin => plugin.prefix)].some(prefix => String(value).startsWith(prefix))
      ? `<a href="${{esc(value)}}">${{esc(column.replace("_api", ""))}}</a>` : esc(value);
    const body = rows.map((row) => `<tr>${{columns.map((column) => `<td>${{cell(column, row[column])}}</td>`).join("")}}</tr>`).join("");
    return `<p>${{rows.length}} row(s)</p><div class="embedded-evidence-table-wrap"><table><thead><tr>${{header}}</tr></thead><tbody>${{body}}</tbody></table></div>`;
  }}

  async function runEmbeddedEvidenceQuery(href) {{
    const url = parseEmbeddedQueryUrl(href);
    const path = url.pathname;
    const database = await databaseReady;
    const plugin = plugins.find(plugin => path.startsWith(plugin.prefix));
    const prefix = plugin ? plugin.prefix : API_PREFIX;
    if (!path.startsWith(prefix)) throw new Error("Unsupported report query URL");
    const queryName = path.slice(prefix.length);
    const payload = plugin ? await plugin.query(database, queryName, url.searchParams) : reportQuery(database, queryName, url.searchParams);
    if (Array.isArray(payload)) {{
      return {{query: queryName, rows: payload, count: payload.length}};
    }}
    return Object.assign({{query: queryName}}, payload);
  }}

  const databaseReady = evidenceDatabase();

  window.__diffReportData = {{
    getGraph: () => runEmbeddedEvidenceQuery(API_PREFIX + "relationship-graph"),
    query: runEmbeddedEvidenceQuery,
    ready: databaseReady,
    loadStatus: () => ({{
      state: loadStatus.element.dataset.state || "",
      message: loadStatus.detail.textContent || "",
      hidden: !!loadStatus.element.hidden
    }})
  }};

  let queryHistory = [];
  let activeQuery = "";
  let queryRequest = 0;

  async function openEvidence(href, remember = true) {{
    const request = ++queryRequest;
    if (remember && activeQuery) queryHistory.push(activeQuery);
    activeQuery = href;
    showOverlay("Loading evidence query...", "");
    try {{
      const result = await runEmbeddedEvidenceQuery(href);
      if (request !== queryRequest) return;
      let controls = "";
      if (Object.hasOwn(result, "next_after")) {{
        const url = parseEmbeddedQueryUrl(href);
        controls = `<form data-source-search class="embedded-source-toolbar">
          <button type="button" data-source-back title="Previous view" aria-label="Previous view" ${{queryHistory.length ? '' : 'disabled'}}>&larr;</button>
          <input type="search" name="q" aria-label="Search this inventory" placeholder="Search" value="${{esc(url.searchParams.get('q') || '')}}">
          <button type="submit">Search</button>`;
        if (result.next_after != null) {{
          url.searchParams.set("after", result.next_after);
          controls += `<a class="embedded-source-next" href="${{esc(href.split('?')[0] + url.search)}}" title="Next page" aria-label="Next page">&rarr;</a>`;
        }}
        controls += "</form>";
      }}
      showOverlay(`${{result.query}} (${{result.rows.length}} row(s))`, controls + renderRows(result.rows));
    }} catch (error) {{
      if (request === queryRequest) showOverlay("Evidence query failed", `<pre>${{esc(error && error.message ? error.message : error)}}</pre>`);
    }}
  }}

  overlay.addEventListener("submit", (event) => {{
    if (!event.target.matches("[data-source-search]")) return;
    event.preventDefault();
    const url = parseEmbeddedQueryUrl(activeQuery);
    url.searchParams.set("q", event.target.elements.q.value);
    url.searchParams.delete("after");
    openEvidence(activeQuery.split('?')[0] + url.search);
  }});
  overlay.addEventListener("click", (event) => {{
    if (!event.target.closest("[data-source-back]") || !queryHistory.length) return;
    openEvidence(queryHistory.pop(), false);
  }});

  document.addEventListener("click", async (event) => {{
    const anchor = event.target.closest && event.target.closest("a[href]");
    if (!anchor) return;
    const href = anchor.getAttribute("href");
    if (![API_PREFIX, ...plugins.map(plugin => plugin.prefix)].some(prefix => href.startsWith(prefix))) return;
    event.preventDefault();
    if (!overlay.contains(anchor)) {{ queryHistory = []; activeQuery = ""; }}
    await openEvidence(href);
  }});
}})();
</script>
<style>
.embedded-source-toolbar {{ display: flex; gap: 8px; align-items: center; margin: 8px 0; }}
.embedded-source-toolbar input {{ min-width: 0; flex: 1; }}
.embedded-source-toolbar button, .embedded-source-next {{ min-width: 32px; min-height: 32px; text-align: center; }}
.embedded-evidence-table-wrap td {{ overflow-wrap: anywhere; }}
.embedded-evidence-load-status[hidden] {{ display: none; }}
.embedded-evidence-load-status {{
  align-items: center;
  background: rgba(15, 23, 42, 0.32);
  bottom: 0;
  display: flex;
  justify-content: center;
  left: 0;
  padding: 24px;
  position: fixed;
  right: 0;
  top: 0;
  z-index: 10001;
}}
.embedded-evidence-load-panel {{
  background: #ffffff;
  border: 1px solid #9aa7b8;
  border-left: 4px solid #2563eb;
  border-radius: 8px;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.16);
  color: #111827;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  max-width: min(420px, calc(100vw - 32px));
  padding: 10px 12px 12px;
  width: 360px;
}}
.embedded-evidence-load-status[data-state="ready"] .embedded-evidence-load-panel {{ border-left-color: #16803a; }}
.embedded-evidence-load-status[data-state="error"] .embedded-evidence-load-panel {{ border-left-color: #dc2626; }}
.embedded-evidence-load-title {{
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 4px;
}}
.embedded-evidence-load-detail {{
  color: #4b5563;
  font-size: 12px;
  line-height: 1.35;
  margin-bottom: 8px;
}}
.embedded-evidence-progress {{
  background: #e5e7eb;
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}}
.embedded-evidence-progress > div {{
  background: #2563eb;
  height: 100%;
  transition: width 180ms ease;
  width: 0;
}}
.embedded-evidence-load-status[data-state="ready"] .embedded-evidence-progress > div {{
  background: #16803a;
}}
.embedded-evidence-load-status[data-state="error"] .embedded-evidence-progress > div {{
  background: #dc2626;
}}
.embedded-evidence-overlay[hidden] {{ display: none; }}
.embedded-evidence-overlay {{
  align-items: center;
  background: rgba(15, 23, 42, 0.32);
  bottom: 0;
  display: flex;
  justify-content: center;
  left: 0;
  padding: 24px;
  position: fixed;
  right: 0;
  top: 0;
  z-index: 10000;
}}
.embedded-evidence-dialog {{
  background: #ffffff;
  color: #202832;
  color-scheme: light;
  font: 14px system-ui, sans-serif;
  border: 1px solid #b8c2d0;
  border-radius: 8px;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
  max-height: min(82vh, 900px);
  max-width: min(92vw, 1280px);
  overflow: hidden;
  width: 100%;
}}
.embedded-evidence-header {{
  align-items: center;
  background: #eef2f7;
  border-bottom: 1px solid #c8d2df;
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
}}
.embedded-evidence-header button {{
  border: 1px solid #9aa7b8;
  border-radius: 6px;
  background: #ffffff;
  cursor: pointer;
  padding: 5px 10px;
}}
.embedded-evidence-dialog button,
.embedded-evidence-dialog input {{
  background: #ffffff;
  color: #202832;
  border: 1px solid #9aa7b8;
  border-radius: 4px;
  font: inherit;
}}
.embedded-evidence-dialog input {{ padding: 6px 8px; }}
.embedded-evidence-dialog button:disabled {{ color: #77818c; cursor: default; }}
.embedded-evidence-dialog a {{ color: #0067af; }}
.embedded-evidence-dialog strong,
.embedded-evidence-dialog p,
.embedded-evidence-dialog th,
.embedded-evidence-dialog td {{ color: #202832; }}
.embedded-evidence-body {{
  max-height: calc(min(82vh, 900px) - 48px);
  overflow: auto;
  padding: 14px;
}}
.embedded-evidence-table-wrap {{ overflow: auto; }}
.embedded-evidence-body table {{
  border-collapse: collapse;
  font-size: 12px;
  min-width: 640px;
  width: 100%;
}}
.embedded-evidence-body td:first-child {{ white-space: nowrap; }}
.embedded-evidence-body th {{ white-space: nowrap; }}
.embedded-evidence-body th,
.embedded-evidence-body td {{
  border: 1px solid #c8d2df;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}}
.embedded-evidence-body th {{ background: #eef2f7; }}
</style>
"""
