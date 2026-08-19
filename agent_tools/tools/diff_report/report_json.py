from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .comments import comments_from_payload
from .html_utils import anchor as _anchor
from .html_utils import esc as _esc
from .html_utils import format_text as _format_text
from .models import DiffReportError, ReviewComments
from .render import (
    _render_comment_assets,
    _render_diagram_modal,
    _render_diagrams_section,
    _render_logs_section,
    _render_settings_launcher,
    _render_story_section,
    _render_summary_section,
    _render_to_top_button,
)
from .assets import copy_selection_script, html_header, story_script, theme_script


@dataclass(frozen=True)
class ReportMetric:
    label: str
    value: str
    status: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ReportStatusCard:
    title: str
    status: str
    body: str
    metrics: tuple[ReportMetric, ...] = ()
    links: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class ReportHeatmap:
    title: str
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ReportTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    filterable: bool = True


@dataclass(frozen=True)
class ReportTimelineItem:
    title: str
    body: str | None = None
    status: str | None = None
    time: str | None = None


@dataclass(frozen=True)
class ReportArtifact:
    title: str
    path: str
    kind: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ReportTocItem:
    label: str
    href: str


@dataclass(frozen=True)
class ReportTocGroup:
    title: str
    items: tuple[ReportTocItem, ...]
    open: bool = True


@dataclass(frozen=True)
class RelationshipGraph:
    title: str
    nodes: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class GenericReport:
    title: str
    comments: ReviewComments
    metrics: tuple[ReportMetric, ...] = ()
    status_cards: tuple[ReportStatusCard, ...] = ()
    heatmaps: tuple[ReportHeatmap, ...] = ()
    tables: tuple[ReportTable, ...] = ()
    timeline: tuple[ReportTimelineItem, ...] = ()
    artifacts: tuple[ReportArtifact, ...] = ()
    toc_groups: tuple[ReportTocGroup, ...] = ()
    relationship_graph: RelationshipGraph | None = None


def load_report_json(report_file: Path) -> GenericReport:
    payload = json.loads(report_file.read_text(encoding="utf-8"))
    return report_from_payload(payload, base_dir=report_file.parent)


def report_from_payload(
    payload: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> GenericReport:
    if not isinstance(payload, dict):
        raise DiffReportError("report JSON must be an object")
    title = str(payload.get("title", "Report"))
    if not title.strip():
        raise DiffReportError("report.title must be non-empty")
    comments = comments_from_payload(payload, base_dir=base_dir)
    return GenericReport(
        title=title,
        comments=comments,
        metrics=metrics_from_payload(payload.get("metrics", [])),
        status_cards=status_cards_from_payload(payload.get("status_cards", [])),
        heatmaps=heatmaps_from_payload(payload.get("heatmaps", payload.get("heatmap", []))),
        tables=tables_from_payload(payload.get("tables", [])),
        timeline=timeline_from_payload(payload.get("timeline", [])),
        artifacts=artifacts_from_payload(payload.get("artifacts", [])),
        toc_groups=toc_groups_from_payload(payload.get("toc_groups", [])),
        relationship_graph=relationship_graph_from_payload(payload.get("relationship_graph")),
    )


def render_report_json_html(report: GenericReport) -> str:
    comments = report.comments
    parts: list[str] = []
    parts.append(html_header(report.title))
    parts.append(_render_report_toc(report))
    parts.append(
        f"""
<main class="general-report">
  <header id="report-top">
    <h1>{_esc(report.title)}</h1>
  </header>
"""
    )
    if comments.summary or comments.summary_blocks:
        parts.append(_render_summary_section(comments))
    if report.metrics:
        parts.append(_render_metrics_section(report.metrics))
    if report.status_cards:
        parts.append(_render_status_cards_section(report.status_cards))
    if report.heatmaps:
        parts.append(_render_heatmaps_section(report.heatmaps))
    if report.relationship_graph:
        parts.append(_render_relationship_graph_section(report.relationship_graph))
    if report.tables:
        parts.append(_render_tables_section(report.tables, comments))
    if report.timeline:
        parts.append(_render_timeline_section(report.timeline))
    if report.artifacts:
        parts.append(_render_artifacts_section(report.artifacts))
    if comments.diagrams:
        parts.append(_render_diagrams_section(comments))
    if comments.logs:
        parts.append(_render_logs_section(comments))
    if comments.story:
        parts.append(_render_story_section(comments))
    parts.append(_render_settings_launcher(" report-settings-launcher"))
    parts.append(_render_to_top_button())
    if comments.diagrams or comments.logs:
        parts.append(_render_diagram_modal(comments))
    parts.append(copy_selection_script())
    parts.append(_report_filter_script())
    if report.relationship_graph:
        parts.append(_cytoscape_vendor_script())
        parts.append(_relationship_graph_script())
    parts.append(story_script())
    parts.append(theme_script())
    parts.append("</main>\n</body>\n</html>\n")
    return "".join(parts)


def metrics_from_payload(raw_metrics: Any) -> tuple[ReportMetric, ...]:
    if raw_metrics is None:
        return ()
    if not isinstance(raw_metrics, list):
        raise DiffReportError("report.metrics must be a list")
    metrics: list[ReportMetric] = []
    for index, item in enumerate(raw_metrics):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.metrics[{index}] must be an object")
        metrics.append(
            ReportMetric(
                label=_required_text(item, "label", f"report.metrics[{index}]"),
                value=str(item.get("value", "")),
                status=_optional_text(item, "status"),
                note=_optional_text(item, "note"),
            )
        )
    return tuple(metrics)


def status_cards_from_payload(raw_cards: Any) -> tuple[ReportStatusCard, ...]:
    if raw_cards is None:
        return ()
    if not isinstance(raw_cards, list):
        raise DiffReportError("report.status_cards must be a list")
    cards: list[ReportStatusCard] = []
    for index, item in enumerate(raw_cards):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.status_cards[{index}] must be an object")
        cards.append(
            ReportStatusCard(
                title=_required_text(item, "title", f"report.status_cards[{index}]"),
                status=str(item.get("status", "unknown")),
                body=str(item.get("body", "")),
                metrics=metrics_from_payload(item.get("metrics", [])),
                links=links_from_payload(item.get("links", []), f"report.status_cards[{index}].links"),
            )
        )
    return tuple(cards)


def heatmaps_from_payload(raw_heatmaps: Any) -> tuple[ReportHeatmap, ...]:
    if raw_heatmaps is None:
        return ()
    if isinstance(raw_heatmaps, dict):
        raw_heatmaps = [raw_heatmaps]
    if not isinstance(raw_heatmaps, list):
        raise DiffReportError("report.heatmaps must be a list")
    heatmaps: list[ReportHeatmap] = []
    for index, item in enumerate(raw_heatmaps):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.heatmaps[{index}] must be an object")
        rows = item.get("rows", [])
        if not isinstance(rows, list):
            raise DiffReportError(f"report.heatmaps[{index}].rows must be a list")
        heatmaps.append(
            ReportHeatmap(
                title=str(item.get("title", "Status Heatmap")),
                rows=tuple(_object_row(row, f"report.heatmaps[{index}].rows") for row in rows),
            )
        )
    return tuple(heatmaps)


def tables_from_payload(raw_tables: Any) -> tuple[ReportTable, ...]:
    if raw_tables is None:
        return ()
    if not isinstance(raw_tables, list):
        raise DiffReportError("report.tables must be a list")
    tables: list[ReportTable] = []
    for index, item in enumerate(raw_tables):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.tables[{index}] must be an object")
        raw_columns = item.get("columns", [])
        if not isinstance(raw_columns, list) or not raw_columns:
            raise DiffReportError(f"report.tables[{index}].columns must be a non-empty list")
        rows = item.get("rows", [])
        if not isinstance(rows, list):
            raise DiffReportError(f"report.tables[{index}].rows must be a list")
        tables.append(
            ReportTable(
                title=str(item.get("title", f"Table {index + 1}")),
                columns=tuple(str(column) for column in raw_columns),
                rows=tuple(_object_row(row, f"report.tables[{index}].rows") for row in rows),
                filterable=bool(item.get("filterable", True)),
            )
        )
    return tuple(tables)


def timeline_from_payload(raw_items: Any) -> tuple[ReportTimelineItem, ...]:
    if raw_items is None:
        return ()
    if not isinstance(raw_items, list):
        raise DiffReportError("report.timeline must be a list")
    items: list[ReportTimelineItem] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.timeline[{index}] must be an object")
        items.append(
            ReportTimelineItem(
                title=_required_text(item, "title", f"report.timeline[{index}]"),
                body=_optional_text(item, "body"),
                status=_optional_text(item, "status"),
                time=_optional_text(item, "time"),
            )
        )
    return tuple(items)


def artifacts_from_payload(raw_items: Any) -> tuple[ReportArtifact, ...]:
    if raw_items is None:
        return ()
    if not isinstance(raw_items, list):
        raise DiffReportError("report.artifacts must be a list")
    artifacts: list[ReportArtifact] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise DiffReportError(f"report.artifacts[{index}] must be an object")
        artifacts.append(
            ReportArtifact(
                title=_required_text(item, "title", f"report.artifacts[{index}]"),
                path=_required_text(item, "path", f"report.artifacts[{index}]"),
                kind=_optional_text(item, "kind"),
                note=_optional_text(item, "note"),
            )
        )
    return tuple(artifacts)


def toc_groups_from_payload(raw_groups: Any) -> tuple[ReportTocGroup, ...]:
    if raw_groups is None:
        return ()
    if not isinstance(raw_groups, list):
        raise DiffReportError("report.toc_groups must be a list")
    groups: list[ReportTocGroup] = []
    for group_index, group in enumerate(raw_groups):
        if not isinstance(group, dict):
            raise DiffReportError(f"report.toc_groups[{group_index}] must be an object")
        raw_items = group.get("items", [])
        if not isinstance(raw_items, list) or not raw_items:
            raise DiffReportError(f"report.toc_groups[{group_index}].items must be a non-empty list")
        items: list[ReportTocItem] = []
        for item_index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise DiffReportError(f"report.toc_groups[{group_index}].items[{item_index}] must be an object")
            href = _required_text(item, "href", f"report.toc_groups[{group_index}].items[{item_index}]")
            if not href.startswith("#"):
                raise DiffReportError(f"report.toc_groups[{group_index}].items[{item_index}].href must start with #")
            items.append(
                ReportTocItem(
                    label=_required_text(item, "label", f"report.toc_groups[{group_index}].items[{item_index}]"),
                    href=href,
                )
            )
        groups.append(
            ReportTocGroup(
                title=_required_text(group, "title", f"report.toc_groups[{group_index}]"),
                items=tuple(items),
                open=bool(group.get("open", True)),
            )
        )
    return tuple(groups)


def relationship_graph_from_payload(raw_graph: Any) -> RelationshipGraph | None:
    if raw_graph is None:
        return None
    if not isinstance(raw_graph, dict):
        raise DiffReportError("report.relationship_graph must be an object")
    raw_nodes = raw_graph.get("nodes", [])
    raw_edges = raw_graph.get("edges", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise DiffReportError("report.relationship_graph.nodes must be a non-empty list")
    if not isinstance(raw_edges, list):
        raise DiffReportError("report.relationship_graph.edges must be a list")
    nodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_node in enumerate(raw_nodes):
        node = _object_row(raw_node, "report.relationship_graph.nodes")
        node_id = _required_text(node, "id", f"report.relationship_graph.nodes[{index}]")
        if node_id in seen_ids:
            raise DiffReportError(f"report.relationship_graph.nodes[{index}].id duplicates {node_id}")
        seen_ids.add(node_id)
        _required_text(node, "label", f"report.relationship_graph.nodes[{index}]")
        node.setdefault("type", "entity")
        node.setdefault("status", "unknown")
        nodes.append(node)
    edges: list[dict[str, Any]] = []
    for index, raw_edge in enumerate(raw_edges):
        edge = _object_row(raw_edge, "report.relationship_graph.edges")
        source = _required_text(edge, "source", f"report.relationship_graph.edges[{index}]")
        target = _required_text(edge, "target", f"report.relationship_graph.edges[{index}]")
        if source not in seen_ids:
            raise DiffReportError(f"report.relationship_graph.edges[{index}].source references missing node {source}")
        if target not in seen_ids:
            raise DiffReportError(f"report.relationship_graph.edges[{index}].target references missing node {target}")
        edge.setdefault("relation", "related_to")
        edges.append(edge)
    return RelationshipGraph(
        title=str(raw_graph.get("title", "Relationship Graph")),
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def links_from_payload(raw_links: Any, field: str) -> tuple[dict[str, str], ...]:
    if raw_links is None:
        return ()
    if not isinstance(raw_links, list):
        raise DiffReportError(f"{field} must be a list")
    links: list[dict[str, str]] = []
    for index, item in enumerate(raw_links):
        if not isinstance(item, dict):
            raise DiffReportError(f"{field}[{index}] must be an object")
        links.append(
            {
                "label": _required_text(item, "label", f"{field}[{index}]"),
                "href": _required_text(item, "href", f"{field}[{index}]"),
            }
        )
    return tuple(links)


def _render_metrics_section(metrics: tuple[ReportMetric, ...]) -> str:
    parts = ['  <section class="report-metrics" id="report-metrics"><h2>Metrics</h2><div class="report-metric-grid">\n']
    for metric in metrics:
        status = _status_class(metric.status)
        parts.append(
            f'    <div class="report-metric {status}">'
            f'<span class="label">{_esc(metric.label)}</span>'
            f'<strong>{_esc(metric.value)}</strong>'
        )
        if metric.note:
            parts.append(f'<span class="report-metric-note">{_format_text(metric.note)}</span>')
        parts.append("</div>\n")
    parts.append("  </div></section>\n")
    return "".join(parts)


def _render_status_cards_section(cards: tuple[ReportStatusCard, ...]) -> str:
    parts = ['  <section class="report-status-cards" id="report-status-cards"><h2>Status Cards</h2><div class="report-card-grid">\n']
    for card in cards:
        parts.append(
            f'    <article class="report-card {_status_class(card.status)}" id="{_anchor(card.title)}">'
            f'<div class="report-card-head"><h3>{_esc(card.title)}</h3>{_render_status_badge(card.status)}</div>'
            f'<div class="report-card-body">{_format_text(card.body)}</div>'
        )
        if card.metrics:
            parts.append('<div class="report-card-metrics">')
            for metric in card.metrics:
                parts.append(
                    f'<span><span class="label">{_esc(metric.label)}</span><strong>{_esc(metric.value)}</strong></span>'
                )
            parts.append("</div>")
        if card.links:
            parts.append('<div class="report-card-links">')
            for link in card.links:
                parts.append(f'<a href="{_esc(link["href"])}">{_esc(link["label"])}</a>')
            parts.append("</div>")
        parts.append("</article>\n")
    parts.append("  </div></section>\n")
    return "".join(parts)


def _render_heatmaps_section(heatmaps: tuple[ReportHeatmap, ...]) -> str:
    parts: list[str] = []
    for index, heatmap in enumerate(heatmaps):
        keys = _heatmap_keys(heatmap.rows)
        section_id = "report-heatmaps" if index == 0 else f"report-heatmap-{index + 1}"
        parts.append(f'  <section class="report-heatmap" id="{section_id}"><h2>{_esc(heatmap.title)}</h2>\n')
        parts.append('    <div class="report-heatmap-grid" role="table">\n')
        parts.append('      <div class="report-heatmap-row report-heatmap-header" role="row">\n')
        for key in keys:
            parts.append(f'        <div role="columnheader">{_esc(_label_for_key(key))}</div>\n')
        parts.append("      </div>\n")
        for row in heatmap.rows:
            parts.append('      <div class="report-heatmap-row" role="row">\n')
            for key in keys:
                value = row.get(key, "")
                cell_status = str(row.get("status", value if key == "status" else ""))
                parts.append(
                    f'        <div class="report-heatmap-cell {_status_class(cell_status)}" role="cell">'
                    f'{_esc(str(value))}</div>\n'
                )
            parts.append("      </div>\n")
        parts.append("    </div>\n  </section>\n")
    return "".join(parts)


def _render_tables_section(tables: tuple[ReportTable, ...], comments: ReviewComments) -> str:
    parts: list[str] = []
    for index, table in enumerate(tables):
        table_id = f"report-table-{index + 1}"
        parts.append(f'  <section class="report-table-section" id="{table_id}"><h2>{_esc(table.title)}</h2>\n')
        if table.filterable:
            parts.append(
                f'    <label class="report-table-filter"><span class="label">Filter</span>'
                f'<input type="search" data-report-table-filter="{table_id}" placeholder="Filter rows"></label>\n'
            )
        parts.append(f'    <div class="report-table-wrap"><table class="report-table" data-report-table="{table_id}">\n')
        parts.append("      <thead><tr>")
        for column in table.columns:
            parts.append(f"<th>{_esc(_label_for_key(column))}</th>")
        parts.append("</tr></thead>\n      <tbody>\n")
        for row in table.rows:
            haystack = " ".join(str(row.get(column, "")) for column in table.columns)
            parts.append(f'        <tr data-report-filter-text="{_esc(haystack.lower())}">')
            for column in table.columns:
                parts.append(f"<td>{_render_table_value(row.get(column, ''), comments)}</td>")
            parts.append("</tr>\n")
        parts.append("      </tbody>\n    </table></div>\n  </section>\n")
    return "".join(parts)


def _render_timeline_section(items: tuple[ReportTimelineItem, ...]) -> str:
    parts = ['  <section class="report-timeline" id="report-timeline"><h2>Timeline</h2><ol class="report-timeline-list">\n']
    for item in items:
        parts.append(f'    <li class="{_status_class(item.status)}">')
        parts.append('<div class="report-timeline-marker"></div><div class="report-timeline-content">')
        if item.time:
            parts.append(f'<time>{_esc(item.time)}</time>')
        parts.append(f"<strong>{_esc(item.title)}</strong>")
        if item.status:
            parts.append(_render_status_badge(item.status))
        if item.body:
            parts.append(f'<p>{_format_text(item.body)}</p>')
        parts.append("</div></li>\n")
    parts.append("  </ol></section>\n")
    return "".join(parts)


def _render_artifacts_section(artifacts: tuple[ReportArtifact, ...]) -> str:
    parts = ['  <section class="report-artifacts" id="report-artifacts"><h2>Artifacts</h2><div class="report-artifact-list">\n']
    for artifact in artifacts:
        parts.append(
            f'    <a class="report-artifact" href="{_esc(artifact.path)}">'
            f'<span>{_esc(artifact.title)}</span>'
        )
        meta = " · ".join(item for item in (artifact.kind, artifact.note) if item)
        if meta:
            parts.append(f'<small>{_esc(meta)}</small>')
        parts.append("</a>\n")
    parts.append("  </div></section>\n")
    return "".join(parts)


def _render_relationship_graph_section(graph: RelationshipGraph) -> str:
    graph_payload = {
        "nodes": list(graph.nodes),
        "edges": list(graph.edges),
    }
    graph_json = json.dumps(graph_payload, ensure_ascii=False).replace("</", "<\\/")
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    type_counts = Counter(str(node.get("type") or "entity") for node in graph.nodes)
    status_counts = Counter(str(node.get("status") or "unknown") for node in graph.nodes)
    type_preview = "".join(
        f'<span>{_esc(item)} <strong>{count}</strong></span>'
        for item, count in type_counts.most_common(8)
    )
    status_preview = "".join(
        f'<span class="{_status_class(item)}">{_esc(item)} <strong>{count}</strong></span>'
        for item, count in status_counts.most_common(6)
    )
    return f"""
  <section class="report-relationship-section" id="report-relationship-graph">
    <h2>{_esc(graph.title)}</h2>
    <div class="relationship-launcher">
      <button type="button" data-relationship-open>Open graph</button>
      <div>
        <strong>{_esc(graph.title)}</strong>
        <p>{node_count} nodes, {edge_count} links. Open the graph in a larger workspace to inspect requirement, domain, CDD, HAL, CTS/VTS, and evidence relationships.</p>
        <div class="relationship-preview" aria-label="Graph preview">
          <div><span class="label">Types</span><div class="relationship-preview-row">{type_preview}</div></div>
          <div><span class="label">Statuses</span><div class="relationship-preview-row">{status_preview}</div></div>
        </div>
      </div>
    </div>
    <div class="relationship-modal" data-relationship-modal hidden role="dialog" aria-modal="true" aria-labelledby="report-relationship-graph-modal-title">
      <div class="relationship-modal-panel">
        <div class="relationship-modal-head">
          <div>
            <span class="label">Traceability graph</span>
            <h3 id="report-relationship-graph-modal-title">{_esc(graph.title)}</h3>
          </div>
          <button type="button" data-relationship-close aria-label="Close graph">Close</button>
        </div>
        <div class="relationship-browser" data-relationship-browser data-relationship-defer>
          <script type="application/json" data-relationship-graph-data>{graph_json}</script>
          <div class="relationship-toolbar">
            <div class="relationship-search-controls">
              <label><span class="label">Find node</span><input type="search" data-relationship-search placeholder="VSR, HAL, CTS, CDD"></label>
              <label><span class="label">Focus <small data-relationship-node-count></small></span><select data-relationship-node-select aria-label="Select graph node"></select></label>
            </div>
            <div class="relationship-view-controls">
              <fieldset class="relationship-type-filter" data-relationship-type-filter>
                <legend>Entity types</legend>
              </fieldset>
            </div>
          </div>
          <div class="relationship-layout">
            <div class="relationship-explorer-main">
              <div class="relationship-canvas-wrap">
                <div class="relationship-canvas-controls" aria-label="Graph view controls">
                  <div class="relationship-depth-controls" aria-label="Graph depth">
                    <button type="button" data-relationship-depth="1">Depth 1</button>
                    <button type="button" data-relationship-depth="2">Depth 2</button>
                  </div>
                  <div class="relationship-nav-controls" aria-label="Graph history">
                    <button type="button" data-relationship-fit title="Fit graph" aria-label="Fit graph">Fit</button>
                    <button type="button" data-relationship-back title="Back" aria-label="Back">←</button>
                    <button type="button" data-relationship-forward title="Forward" aria-label="Forward">→</button>
                  </div>
                </div>
                <div class="relationship-canvas" data-relationship-canvas role="img" aria-label="{_esc(graph.title)}"></div>
              </div>
              <div class="relationship-selection-table" data-relationship-selection-table>
                <div class="relationship-selection-table-head">
                  <span>Selection table</span>
                  <small data-relationship-selection-count></small>
                </div>
                <div class="relationship-selection-table-scroll">
                  <table>
                    <thead><tr><th>Type</th><th>Node</th><th>Status</th><th>Links</th><th>Summary</th></tr></thead>
                    <tbody data-relationship-selection-body></tbody>
                  </table>
                </div>
              </div>
            </div>
            <aside class="relationship-detail" data-relationship-detail>
              <p>Select a node to inspect related requirements, CDD, HALs, tests, evidence, gaps, and notes.</p>
            </aside>
          </div>
        </div>
      </div>
    </div>
  </section>
"""


def _render_table_value(value: Any, comments: ReviewComments) -> str:
    if isinstance(value, dict):
        text = str(value.get("text", value.get("value", "")))
        status = _optional_text(value, "status")
        href = _optional_text(value, "href")
        diagram = _optional_text(value, "diagram")
        log = _optional_text(value, "log")
        parts: list[str] = []
        if status:
            parts.append(_render_status_badge(status))
        if href:
            parts.append(f'<a href="{_esc(href)}">{_format_text(text, comments.vocabulary)}</a>')
        else:
            parts.append(_format_text(text, comments.vocabulary))
        if diagram or log:
            parts.append(
                _render_comment_assets(
                    comments,
                    diagram,
                    log,
                    (),
                    (),
                    (),
                )
            )
        return "".join(parts)
    status_text = str(value)
    if _looks_like_status(status_text):
        return _render_status_badge(status_text)
    return _format_text(status_text, comments.vocabulary)


def _render_report_toc(report: GenericReport) -> str:
    items = _report_toc_items(report)
    if not items:
        return ""
    parts = ['<nav class="report-toc" aria-label="Report table of contents">\n']
    parts.append('  <div class="report-toc-head">Contents</div>\n')
    if report.toc_groups:
        parts.append('  <div class="report-toc-tree">\n')
        for group in report.toc_groups:
            open_attr = " open" if group.open else ""
            parts.append(f'    <details class="report-toc-group"{open_attr}>\n')
            parts.append(f'      <summary>{_esc(group.title)}</summary>\n')
            parts.append("      <ol>\n")
            for item in group.items:
                parts.append(f'        <li><a href="{_esc(item.href)}">{_esc(item.label)}</a></li>\n')
            parts.append("      </ol>\n")
            parts.append("    </details>\n")
        parts.append("  </div>\n</nav>\n")
    else:
        parts.append("  <ol>\n")
        for label, href in items:
            parts.append(f'    <li><a href="{_esc(href)}">{_esc(label)}</a></li>\n')
        parts.append("  </ol>\n</nav>\n")
    return "".join(parts)


def _report_toc_items(report: GenericReport) -> list[tuple[str, str]]:
    if report.toc_groups:
        return [(item.label, item.href) for group in report.toc_groups for item in group.items]
    items: list[tuple[str, str]] = [("Top", "#report-top")]
    if report.comments.summary or report.comments.summary_blocks:
        items.append(("Summary", "#summary-section"))
    if report.metrics:
        items.append(("Metrics", "#report-metrics"))
    if report.status_cards:
        items.append(("Status Cards", "#report-status-cards"))
    if report.heatmaps:
        items.append(("Heatmaps", "#report-heatmaps"))
    if report.relationship_graph:
        items.append((report.relationship_graph.title, "#report-relationship-graph"))
    for index, table in enumerate(report.tables):
        items.append((table.title, f"#report-table-{index + 1}"))
    if report.timeline:
        items.append(("Timeline", "#report-timeline"))
    if report.artifacts:
        items.append(("Artifacts", "#report-artifacts"))
    if report.comments.diagrams:
        items.append(("Diagrams", "#report-diagrams"))
    if report.comments.logs:
        items.append(("Logs", "#report-logs"))
    if report.comments.story:
        items.append(("Story", "#story"))
    return items


def _render_status_badge(status: str | None) -> str:
    if not status:
        return ""
    return f'<span class="report-status-badge {_status_class(status)}">{_esc(status)}</span>'


def _status_class(status: str | None) -> str:
    if not status:
        return "status-unknown"
    normalized = "".join(char if char.isalnum() else "-" for char in status.lower()).strip("-")
    return f"status-{normalized or 'unknown'}"


def _looks_like_status(value: str) -> bool:
    return value.lower() in {
        "covered",
        "covered_candidate",
        "gap",
        "risk",
        "needs_evidence",
        "not_applicable",
        "not_applicable_candidate",
        "not_started",
        "unknown",
        "pass",
        "fail",
        "blocked",
    }


def _heatmap_keys(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    preferred = ("domain", "status", "total", "risk", "needs_evidence", "gap", "covered")
    keys: list[str] = [key for key in preferred if any(key in row for row in rows)]
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    return tuple(keys)


def _label_for_key(key: str) -> str:
    return key.replace("_", " ").title()


def _object_row(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DiffReportError(f"{field} entries must be objects")
    return dict(value)


def _required_text(item: dict[str, Any], key: str, field: str) -> str:
    if key not in item:
        raise DiffReportError(f"{field}.{key} is required")
    value = str(item[key])
    if not value.strip():
        raise DiffReportError(f"{field}.{key} must be non-empty")
    return value


def _optional_text(item: dict[str, Any], key: str) -> str | None:
    if key not in item or item[key] is None:
        return None
    return str(item[key])


def _report_filter_script() -> str:
    return """
<script>
(() => {
  document.querySelectorAll("[data-report-table-filter]").forEach((input) => {
    const tableId = input.getAttribute("data-report-table-filter");
    const table = document.querySelector(`[data-report-table="${tableId}"]`);
    if (!table) return;
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach((row) => {
        const text = row.getAttribute("data-report-filter-text") || "";
        row.hidden = query.length > 0 && !text.includes(query);
      });
    });
  });
  const tocLinks = Array.from(document.querySelectorAll(".report-toc a[href^='#']"));
  const tocEntries = tocLinks.map((link) => {
    const id = decodeURIComponent(String(link.getAttribute("href") || "").replace(/^#/, ""));
    const section = id ? document.getElementById(id) : null;
    return {id, link, section};
  }).filter((entry) => entry.id && entry.section);
  let activeTocId = "";
  let tocScrollRaf = 0;
  let pendingTocId = "";
  let pendingTocSince = 0;

  function setActiveToc(id, reveal) {
    if (!id) {
      return;
    }
    activeTocId = id;
    for (const entry of tocEntries) {
      const active = entry.id === id;
      entry.link.classList.toggle("is-current", active);
      if (active) {
        entry.link.setAttribute("aria-current", "location");
        const group = entry.link.closest(".report-toc-group");
        if (group) {
          group.open = true;
        }
        if (reveal) {
          entry.link.scrollIntoView({block: "nearest", inline: "nearest"});
        }
      } else {
        entry.link.removeAttribute("aria-current");
      }
    }
  }

  function currentReadableTocId() {
    if (!tocEntries.length) {
      return "";
    }
    const probeY = 112;
    let current = tocEntries[0];
    for (const entry of tocEntries) {
      const rect = entry.section.getBoundingClientRect();
      if (rect.top <= probeY) {
        current = entry;
        continue;
      }
      if (rect.top > probeY) {
        break;
      }
    }
    return current.id;
  }

  function updateActiveTocFromScroll() {
    tocScrollRaf = 0;
    if (pendingTocId) {
      const pending = tocEntries.find((entry) => entry.id === pendingTocId);
      const pendingTop = pending ? pending.section.getBoundingClientRect().top : 0;
      if (pending && Math.abs(pendingTop) > 18 && Date.now() - pendingTocSince < 1800) {
        setActiveToc(pendingTocId, false);
        window.setTimeout(scheduleActiveTocUpdate, 120);
        return;
      }
      pendingTocId = "";
      pendingTocSince = 0;
    }
    const lockUntil = Number(document.documentElement.dataset.tocLockUntil || "0");
    if (Date.now() < lockUntil) {
      window.setTimeout(scheduleActiveTocUpdate, Math.max(0, lockUntil - Date.now()));
      return;
    }
    setActiveToc(currentReadableTocId(), false);
  }

  function scheduleActiveTocUpdate() {
    if (tocScrollRaf) {
      return;
    }
    tocScrollRaf = window.requestAnimationFrame(updateActiveTocFromScroll);
  }

  if (tocEntries.length) {
    setActiveToc(
      decodeURIComponent(String(location.hash || "").replace(/^#/, "")) || currentReadableTocId(),
      true
    );
    window.addEventListener("scroll", scheduleActiveTocUpdate, {passive: true});
    window.addEventListener("resize", scheduleActiveTocUpdate);
    window.addEventListener("hashchange", scheduleActiveTocUpdate);
  }
  document.addEventListener("click", (event) => {
    const link = event.target.closest && event.target.closest(".report-toc a[href^='#']");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    const target = document.getElementById(href.slice(1));
    if (!target) return;
    event.preventDefault();
    event.stopPropagation();
    const id = decodeURIComponent(href.slice(1));
    pendingTocId = id;
    pendingTocSince = Date.now();
    document.documentElement.dataset.tocLockUntil = String(Date.now() + 1800);
    setActiveToc(id, true);
    target.scrollIntoView({block: "start", inline: "nearest"});
    if (history.pushState) {
      history.pushState(null, "", href);
    } else {
      location.hash = href;
    }
  }, true);
})();
</script>
"""


def _cytoscape_vendor_script() -> str:
    script_path = Path(__file__).with_name("vendor") / "cytoscape.min.js"
    try:
        script = script_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DiffReportError(f"missing Cytoscape.js vendor bundle: {script_path}") from exc
    script = script.replace("</script", "<\\/script")
    return f"<script>\n{script}\n</script>\n"


def _relationship_graph_script() -> str:
    return r"""
<script>
(() => {
  const TYPE_ORDER = ["domain", "vsr", "cdd", "hal", "feature", "property", "test", "artifact", "evidence", "gap", "decision"];
  const TYPE_LABELS = {
    vsr: "VSR",
    cdd: "CDD",
    hal: "HAL",
    test: "CTS/VTS",
    artifact: "Artifact",
    evidence: "Evidence",
    gap: "Gap",
    decision: "Decision",
    domain: "Domain",
    feature: "Feature",
    property: "Property"
  };

  function cssStatus(status) {
    return "status-" + String(status || "unknown").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[char]));
  }

  function shortText(value, limit) {
    const text = String(value || "");
    return text.length > limit ? text.slice(0, limit - 1) + "…" : text;
  }

  function nodeTypeLabel(node) {
    return TYPE_LABELS[node.type] || node.type || "Entity";
  }

  function parseGraph(browser) {
    const script = browser.querySelector("[data-relationship-graph-data]");
    if (!script) return {nodes: [], edges: []};
    try {
      const parsed = JSON.parse(script.textContent || "{}");
      return {
        nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
        edges: Array.isArray(parsed.edges) ? parsed.edges : []
      };
    } catch (_error) {
      return {nodes: [], edges: []};
    }
  }

  function isTypeEnabled(node, selectedId, enabledTypes) {
    if (!node) return false;
    return enabledTypes.has(node.type || "entity");
  }

  function buildNeighborhood(selectedId, depth, nodesById, edges, enabledTypes) {
    const selected = nodesById.get(selectedId);
    if (!isTypeEnabled(selected, selectedId, enabledTypes)) {
      return {nodes: [], edges: [], distances: new Map()};
    }
    const distances = new Map([[selectedId, 0]]);
    let frontier = new Set([selectedId]);
    for (let step = 0; step < depth; step += 1) {
      const next = new Set();
      for (const edge of edges) {
        const sourceNode = nodesById.get(edge.source);
        const targetNode = nodesById.get(edge.target);
        if (frontier.has(edge.source) && !distances.has(edge.target) && isTypeEnabled(targetNode, selectedId, enabledTypes)) {
          next.add(edge.target);
        }
        if (frontier.has(edge.target) && !distances.has(edge.source) && isTypeEnabled(sourceNode, selectedId, enabledTypes)) {
          next.add(edge.source);
        }
      }
      for (const id of next) distances.set(id, step + 1);
      frontier = next;
      if (!frontier.size) break;
    }
    const visibleEdges = edges.filter((edge) => {
      const sourceDistance = distances.get(edge.source);
      const targetDistance = distances.get(edge.target);
      if (sourceDistance == null || targetDistance == null) return false;
      if (edge.source === selectedId || edge.target === selectedId) return true;
      return Math.abs(sourceDistance - targetDistance) === 1 && Math.min(sourceDistance, targetDistance) < depth;
    });
    const visibleNodes = Array.from(distances.keys()).map((id) => nodesById.get(id)).filter(Boolean);
    return {nodes: visibleNodes, edges: visibleEdges, distances};
  }

  function graphMatchesSearch(graph, query) {
    const normalized = String(query || "").trim().toLowerCase();
    if (!normalized) return graph;
    const nodes = graph.nodes.filter((node) => searchableText(node).includes(normalized));
    const visible = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)),
      distances: graph.distances
    };
  }

  function capGraph(graph, selectedId, limit) {
    if (!limit || graph.nodes.length <= limit) return graph;
    const score = (node) => {
      const status = String(node.status || "");
      const distance = graph.distances && graph.distances.get(node.id);
      const statusScore = ["gap", "risk", "needs_evidence", "fail", "blocked"].includes(status) ? 0 : 1;
      return [
        node.id === selectedId ? -1 : 0,
        distance == null ? 9 : distance,
        statusScore,
        typeRank(node),
        String(node.label || node.id)
      ];
    };
    const sorted = [...graph.nodes].sort((left, right) => {
      const leftScore = score(left);
      const rightScore = score(right);
      for (let index = 0; index < leftScore.length; index += 1) {
        if (leftScore[index] < rightScore[index]) return -1;
        if (leftScore[index] > rightScore[index]) return 1;
      }
      return 0;
    });
    const nodes = sorted.slice(0, limit);
    const visible = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)),
      distances: graph.distances,
      omitted: graph.nodes.length - nodes.length
    };
  }

  function nodeDistanceMap(selectedId, edges) {
    const distances = new Map([[selectedId, 0]]);
    let frontier = new Set([selectedId]);
    for (let distance = 1; distance <= 2; distance += 1) {
      const next = new Set();
      for (const edge of edges) {
        if (frontier.has(edge.source) && !distances.has(edge.target)) next.add(edge.target);
        if (frontier.has(edge.target) && !distances.has(edge.source)) next.add(edge.source);
      }
      for (const id of next) distances.set(id, distance);
      frontier = next;
    }
    return distances;
  }

  function typeRank(node) {
    const index = TYPE_ORDER.indexOf(node.type || "entity");
    return index === -1 ? 99 : index;
  }

  function layoutNodes(nodes, width, height, selectedId, edges) {
    const positions = new Map();
    const center = {x: width / 2, y: height / 2};
    positions.set(selectedId, center);
    const distances = nodeDistanceMap(selectedId, edges);
    const others = nodes
      .filter((node) => node.id !== selectedId)
      .sort((left, right) => {
        const dl = distances.get(left.id) || 9;
        const dr = distances.get(right.id) || 9;
        return dl - dr || typeRank(left) - typeRank(right) || String(left.label || left.id).localeCompare(String(right.label || right.id));
      });
    const inner = others.filter((node) => (distances.get(node.id) || 9) <= 1);
    const outer = others.filter((node) => (distances.get(node.id) || 9) > 1);
    const placeRing = (ringNodes, radiusX, radiusY, startAngle) => {
      if (!ringNodes.length) return;
      const count = ringNodes.length;
      ringNodes.forEach((node, index) => {
        const angle = startAngle + (Math.PI * 2 * index) / count;
        const x = Math.max(86, Math.min(width - 86, center.x + Math.cos(angle) * radiusX));
        const y = Math.max(36, Math.min(height - 36, center.y + Math.sin(angle) * radiusY));
        positions.set(node.id, {x, y});
      });
    };
    placeRing(inner, Math.min(width * 0.31, 260), Math.min(height * 0.30, 170), -Math.PI / 2);
    placeRing(outer, Math.min(width * 0.43, 360), Math.min(height * 0.41, 245), -Math.PI / 2 + Math.PI / Math.max(outer.length, 2));
    for (const node of others) {
      if (positions.has(node.id)) continue;
      positions.set(node.id, {
        x: 86 + Math.random() * Math.max(1, width - 172),
        y: 36 + Math.random() * Math.max(1, height - 72)
      });
    }
    return positions;
  }

  function visibleEdgesForCanvas(selectedId, graph) {
    return graph.edges || [];
  }

  function wrapLabel(value) {
    const text = String(value || "");
    const tokens = text.split(/([@./:_-])/).filter(Boolean);
    const lines = [];
    let line = "";
    for (const token of tokens) {
      const candidate = line + token;
      if (candidate.length > 22 && line) {
        lines.push(line);
        line = token.trimStart();
      } else {
        line = candidate;
      }
      if (lines.length >= 3) break;
    }
    if (line && lines.length < 4) lines.push(line);
    return lines.slice(0, 4).join("\n");
  }

  function cssValue(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function cytoscapeStyle() {
    const text = cssValue("--graph-node-text", "#111827");
    const panel = cssValue("--graph-node-bg", "#ffffff");
    const metaPanel = cssValue("--graph-artifact-bg", "#f1f5f9");
    const domainPanel = cssValue("--graph-domain-bg", "#e0f2fe");
    const border = cssValue("--graph-node-border", "#94a3b8");
    const link = cssValue("--graph-focus", "#2563eb");
    const active = cssValue("--graph-active", "#0f766e");
    const muted = cssValue("--graph-edge", "#64748b");
    const risk = cssValue("--graph-status-risk-border", "#d97706");
    const riskBg = cssValue("--graph-status-risk-bg", "#fffbeb");
    const fail = cssValue("--graph-status-fail-border", "#dc2626");
    const failBg = cssValue("--graph-status-fail-bg", "#fef2f2");
    const pass = cssValue("--graph-status-pass-border", "#16a34a");
    const passBg = cssValue("--graph-status-pass-bg", "#f0fdf4");
    return [
      {
        selector: "node",
        style: {
          "label": "data(displayLabel)",
          "text-wrap": "wrap",
          "text-max-width": 150,
          "text-valign": "center",
          "text-halign": "center",
          "font-size": 12,
          "font-weight": 700,
          "color": text,
          "background-color": panel,
          "border-color": border,
          "border-width": 2,
          "width": 170,
          "height": 66,
          "padding": 8,
          "overlay-opacity": 0
        }
      },
      {selector: 'node[type = "domain"]', style: {"shape": "ellipse", "background-color": domainPanel}},
      {selector: 'node[type = "vsr"]', style: {"shape": "round-rectangle"}},
      {selector: 'node[type = "cdd"]', style: {"shape": "diamond", "width": 130, "height": 86}},
      {selector: 'node[type = "hal"]', style: {"shape": "hexagon"}},
      {selector: 'node[type = "test"]', style: {"shape": "barrel"}},
      {selector: 'node[type = "artifact"]', style: {"shape": "tag", "background-color": metaPanel}},
      {selector: 'node[type = "evidence"]', style: {"shape": "round-tag", "background-color": metaPanel}},
      {selector: "edge", style: {"width": 1.4, "line-color": muted, "target-arrow-color": muted, "target-arrow-shape": "triangle", "curve-style": "bezier", "opacity": .52}},
      {selector: ".status-covered, .status-covered-candidate, .status-pass", style: {"border-color": pass, "background-color": passBg}},
      {selector: ".status-risk, .status-needs-evidence, .status-not-applicable-candidate, .status-warning", style: {"border-color": risk, "background-color": riskBg}},
      {selector: ".status-gap, .status-fail, .status-blocked", style: {"border-color": fail, "background-color": failBg}},
      {selector: ".is-selected", style: {"border-color": link, "border-width": 5, "outline-color": link, "outline-width": 3, "outline-opacity": .52}},
      {selector: ".is-active", style: {"border-color": active, "border-width": 4}},
      {selector: "node:selected", style: {"border-color": link, "border-width": 4}}
    ];
  }

  function cytoscapeElements(graph) {
    const nodes = graph.nodes.map((node) => ({
      group: "nodes",
      data: {
        id: node.id,
        label: node.label || node.id,
        displayLabel: `${nodeTypeLabel(node)}\n${wrapLabel(node.label || node.id)}`,
        type: node.type || "entity",
        status: node.status || "unknown"
      },
      classes: `${cssStatus(node.status)} ${node.id === graph.selectedId ? "is-selected" : ""} ${node.id === graph.activeId ? "is-active" : ""}`
    }));
    const edges = visibleEdgesForCanvas(graph.selectedId, graph).map((edge, index) => ({
      group: "edges",
      data: {
        id: `edge:${index}:${edge.source}:${edge.target}`,
        source: edge.source,
        target: edge.target,
        relation: edge.relation || "related_to"
      }
    }));
    return [...nodes, ...edges];
  }

  function fitGraph(state, padding) {
    if (!state.cy) return;
    requestAnimationFrame(() => {
      if (!state.cy) return;
      state.cy.resize();
      state.cy.fit(undefined, padding || 72);
    });
  }

  function setGraphInteractive(browser, state, interactive) {
    state.graphInteractive = Boolean(interactive);
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (canvas) {
      canvas.setAttribute("data-graph-interactive", state.graphInteractive ? "true" : "false");
    }
    if (!state.cy) return;
    state.cy.userZoomingEnabled(state.graphInteractive);
    state.cy.userPanningEnabled(state.graphInteractive);
    state.cy.autoungrabify(!state.graphInteractive);
  }

  function renderGraph(browser, state) {
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (!canvas || !state.selectedId) return;
    if (typeof cytoscape !== "function") {
      canvas.textContent = "Cytoscape.js is not available.";
      return;
    }
    const hasSearch = String(state.searchQuery || "").trim();
    const graph = capGraph(graphMatchesSearch(
      buildNeighborhood(state.selectedId, state.depth, state.nodesById, state.edges, state.enabledTypes),
      state.searchQuery
    ), state.selectedId, hasSearch ? 0 : 80);
    if (!graph.nodes.some((node) => node.id === state.activeId)) {
      state.activeId = state.selectedId;
    }
    graph.selectedId = state.selectedId;
    graph.activeId = state.activeId;
    state.visibleGraph = graph;
    state.visibleNodeIds = new Set(graph.nodes.map((node) => node.id));
    if (state.cy) {
      state.cy.destroy();
      state.cy = null;
    }
    state.cy = cytoscape({
      container: canvas,
      elements: cytoscapeElements(graph),
      style: cytoscapeStyle(),
      wheelSensitivity: .18,
      minZoom: .25,
      maxZoom: 3,
      userZoomingEnabled: Boolean(state.graphInteractive),
      userPanningEnabled: Boolean(state.graphInteractive),
      autoungrabify: !state.graphInteractive,
      boxSelectionEnabled: false
    });
    setGraphInteractive(browser, state, state.graphInteractive);
    state.cy.on("tap", "node", (event) => {
      const nodeId = event.target.id();
      if (state.tapTimer && state.tapTarget === nodeId) {
        window.clearTimeout(state.tapTimer);
        state.tapTimer = 0;
        state.tapTarget = "";
        selectNode(browser, state, nodeId, true);
        return;
      }
      if (state.tapTimer) {
        window.clearTimeout(state.tapTimer);
      }
      state.tapTarget = nodeId;
      state.tapTimer = window.setTimeout(() => {
        state.tapTimer = 0;
        state.tapTarget = "";
        activateNode(browser, state, nodeId);
      }, 240);
    });
    if (!graph.nodes.length) {
      canvas.setAttribute("data-empty-graph", "true");
      canvas.setAttribute("data-graph-message", hasSearch ? "No matching nodes in the current neighborhood." : "No entity types selected.");
      renderSelectionTable(browser, state);
      return;
    }
    canvas.removeAttribute("data-empty-graph");
    if (graph.omitted) {
      canvas.setAttribute("data-graph-message", `${graph.omitted} more nodes hidden. Use search or entity filters to narrow the graph.`);
    } else {
      canvas.removeAttribute("data-graph-message");
    }
    const layout = state.cy.layout({
      name: "cose",
      animate: false,
      fit: true,
      padding: 80,
      nodeRepulsion: 9000,
      idealEdgeLength: 150,
      edgeElasticity: 120,
      nestingFactor: .8,
      gravity: .18,
      numIter: 900
    });
    layout.run();
    const selected = state.cy.getElementById(state.selectedId);
    if (selected.length) selected.select();
    renderSelectionTable(browser, state);
    fitGraph(state, 88);
  }

  function visibleGraphDegree(nodeId, graph) {
    if (!graph || !Array.isArray(graph.edges)) return 0;
    return graph.edges.filter((edge) => edge.source === nodeId || edge.target === nodeId).length;
  }

  function renderSelectionTable(browser, state) {
    const body = browser.querySelector("[data-relationship-selection-body]");
    const count = browser.querySelector("[data-relationship-selection-count]");
    if (!body) return;
    const graph = state.visibleGraph || {nodes: [], edges: []};
    const nodes = [...(graph.nodes || [])].sort((left, right) =>
      typeRank(left) - typeRank(right) ||
      String(left.label || left.id).localeCompare(String(right.label || right.id))
    );
    if (count) {
      count.textContent = `${nodes.length} nodes, ${(graph.edges || []).length} links`;
    }
    body.replaceChildren();
    for (const node of nodes) {
      const row = document.createElement("tr");
      row.setAttribute("data-relationship-table-node", node.id);
      row.classList.toggle("is-focus", node.id === state.selectedId);
      row.classList.toggle("is-active", node.id === state.activeId);
      const cells = [
        {text: nodeTypeLabel(node)},
        {text: node.label || node.id},
        {text: node.status || "unknown", status: node.status || "unknown"},
        {text: String(visibleGraphDegree(node.id, graph))},
        {text: shortText(node.summary || "", 180)}
      ];
      for (const value of cells) {
        const cell = document.createElement("td");
        if (value.status) {
          const badge = document.createElement("span");
          badge.className = `report-status-badge ${cssStatus(value.status)}`;
          badge.textContent = value.text;
          cell.appendChild(badge);
        } else {
          cell.textContent = value.text;
        }
        row.appendChild(cell);
      }
      body.appendChild(row);
    }
  }

  function relatedGroups(nodeId, state) {
    const groups = new Map();
    for (const edge of state.edges) {
      let relatedId = "";
      let direction = "";
      if (edge.source === nodeId) {
        relatedId = edge.target;
        direction = "out";
      } else if (edge.target === nodeId) {
        relatedId = edge.source;
        direction = "in";
      } else {
        continue;
      }
      const node = state.nodesById.get(relatedId);
      if (!node) continue;
      if (!isTypeEnabled(node, nodeId, state.enabledTypes)) continue;
      const relation = edge.relation || "related_to";
      const key = direction === "out" ? relation : `${relation} (incoming)`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    }
    return groups;
  }

  function renderDetail(browser, state) {
    const detail = browser.querySelector("[data-relationship-detail]");
    const nodeId = state.activeId || state.selectedId;
    if (!detail || !nodeId) return;
    const node = state.nodesById.get(nodeId);
    if (!node) return;
    if (!isTypeEnabled(node, state.selectedId, state.enabledTypes)) {
      detail.innerHTML = "<p>No entity types selected. Enable at least one type or use All.</p>";
      return;
    }
    if (state.searchQuery && !searchableText(node).includes(String(state.searchQuery).trim().toLowerCase())) {
      detail.innerHTML = "<p>The selected node is outside the current search filter. Pick a matching Focus item or clear the search.</p>";
      return;
    }
    const details = node.details && typeof node.details === "object" ? node.details : {};
    const groups = relatedGroups(node.id, state);
    const detailRows = Object.entries(details).filter(([, value]) => value != null && String(value).trim());
    let html = `<div class="relationship-detail-head"><span class="relationship-node-pill">${esc(nodeTypeLabel(node))}</span>`;
    html += `<span class="report-status-badge ${cssStatus(node.status)}">${esc(node.status || "unknown")}</span></div>`;
    html += `<h3>${esc(node.label || node.id)}</h3>`;
    if (node.summary) html += `<p>${esc(node.summary)}</p>`;
    if (detailRows.length) {
      html += '<dl class="relationship-detail-fields">';
      for (const [key, value] of detailRows) {
        html += `<dt>${esc(key.replaceAll("_", " "))}</dt><dd>${esc(value)}</dd>`;
      }
      html += "</dl>";
    }
    if (groups.size) {
      html += '<div class="relationship-related">';
      const visibleNodeIds = state.visibleNodeIds || new Set();
      for (const [relation, nodes] of groups) {
        html += `<section><h4>${esc(relation.replaceAll("_", " "))}</h4><div class="relationship-related-list">`;
        for (const related of nodes.sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)))) {
          const isVisible = visibleNodeIds.has(related.id);
          const className = isVisible ? "is-visible" : "is-outside-view";
          const visibility = isVisible ? "shown on current graph" : "focus to show";
          html += `<button type="button" class="${className}" data-relationship-jump="${esc(related.id)}" data-relationship-jump-visible="${isVisible ? "true" : "false"}"><span>${esc(related.label || related.id)}</span><small>${esc(nodeTypeLabel(related))} · ${visibility}</small></button>`;
        }
        html += "</div></section>";
      }
      html += "</div>";
    }
    detail.innerHTML = html;
  }

  function selectNode(browser, state, nodeId, recordHistory) {
    if (!state.nodesById.has(nodeId)) return;
    if (recordHistory && state.selectedId && state.selectedId !== nodeId) {
      state.backStack.push(state.selectedId);
      state.forwardStack.length = 0;
    }
    state.selectedId = nodeId;
    state.activeId = nodeId;
    renderNodeSelect(browser, state);
    renderGraph(browser, state);
    renderDetail(browser, state);
  }

  function updateActiveGraphNode(state) {
    if (!state.cy) return;
    state.cy.nodes().removeClass("is-active");
    const active = state.cy.getElementById(state.activeId || "");
    if (active.length) active.addClass("is-active");
  }

  function updateActiveTableRow(browser, state) {
    browser.querySelectorAll("[data-relationship-table-node]").forEach((row) => {
      row.classList.toggle("is-active", row.getAttribute("data-relationship-table-node") === state.activeId);
      row.classList.toggle("is-focus", row.getAttribute("data-relationship-table-node") === state.selectedId);
    });
  }

  function activateNode(browser, state, nodeId) {
    if (!state.nodesById.has(nodeId)) return;
    state.activeId = nodeId;
    updateActiveGraphNode(state);
    updateActiveTableRow(browser, state);
    renderDetail(browser, state);
  }

  function graphTypes(nodes) {
    const seen = new Set(nodes.map((node) => node.type || "entity"));
    return TYPE_ORDER.filter((type) => seen.has(type)).concat(
      Array.from(seen).filter((type) => !TYPE_ORDER.includes(type)).sort()
    );
  }

  function searchableText(node) {
    const details = node.details && typeof node.details === "object" ? Object.values(node.details).join(" ") : "";
    return `${node.id} ${nodeTypeLabel(node)} ${node.type || ""} ${node.label || ""} ${node.summary || ""} ${details}`.toLowerCase();
  }

  function searchRank(node, query) {
    const normalized = String(query || "").trim().toLowerCase();
    if (!normalized) return 0;
    const type = String(node.type || "entity").toLowerCase();
    const typeLabel = nodeTypeLabel(node).toLowerCase();
    const id = String(node.id || "").toLowerCase();
    const label = String(node.label || "").toLowerCase();
    if (type === normalized || typeLabel === normalized) return 0;
    if (id === normalized || label === normalized) return 1;
    if (id.startsWith(normalized) || label.startsWith(normalized)) return 2;
    if (id.includes(normalized) || label.includes(normalized)) return 3;
    return 4;
  }

  function visibleNodeDegree(node, state) {
    if (!node || !isTypeEnabled(node, state.selectedId, state.enabledTypes)) return 0;
    let degree = 0;
    for (const edge of state.edges) {
      let otherId = "";
      if (edge.source === node.id) {
        otherId = edge.target;
      } else if (edge.target === node.id) {
        otherId = edge.source;
      } else {
        continue;
      }
      if (isTypeEnabled(state.nodesById.get(otherId), state.selectedId, state.enabledTypes)) {
        degree += 1;
      }
    }
    return degree;
  }

  function selectableNodes(state, includeSelected) {
    const query = String(state.searchQuery || "").trim().toLowerCase();
    return state.nodes
      .filter((node) => {
        if (includeSelected && node.id === state.selectedId) return state.enabledTypes.has(node.type || "entity");
        return state.enabledTypes.has(node.type || "entity");
      })
      .filter((node) => !query || searchableText(node).includes(query))
      .sort((left, right) => {
        const leftDegree = visibleNodeDegree(left, state);
        const rightDegree = visibleNodeDegree(right, state);
        return searchRank(left, query) - searchRank(right, query) ||
          Number(leftDegree === 0) - Number(rightDegree === 0) ||
          rightDegree - leftDegree ||
          typeRank(left) - typeRank(right) ||
          String(left.label || left.id).localeCompare(String(right.label || right.id));
      });
  }

  function renderNodeSelect(browser, state) {
    const select = browser.querySelector("[data-relationship-node-select]");
    if (!select) return [];
    const includeSelected = !String(state.searchQuery || "").trim();
    const nodes = selectableNodes(state, includeSelected);
    const count = browser.querySelector("[data-relationship-node-count]");
    const degrees = new Map(nodes.map((node) => [node.id, visibleNodeDegree(node, state)]));
    const linkedCount = nodes.filter((node) => degrees.get(node.id)).length;
    const isolatedCount = nodes.length - linkedCount;
    if (count) {
      count.textContent = nodes.length ? `(${linkedCount} linked, ${isolatedCount} isolated, ${nodes.length} shown)` : "(0 shown)";
    }
    select.replaceChildren();
    if (!nodes.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No matching nodes";
      option.disabled = true;
      select.appendChild(option);
      return nodes;
    }
    const groupCounts = new Map();
    for (const node of nodes) {
      const degree = degrees.get(node.id) || 0;
      const key = `${nodeTypeLabel(node)} · ${degree ? "linked" : "no visible links"}`;
      groupCounts.set(key, (groupCounts.get(key) || 0) + 1);
    }
    const groups = new Map();
    for (const node of nodes) {
      const degree = degrees.get(node.id) || 0;
      const key = `${nodeTypeLabel(node)} · ${degree ? "linked" : "no visible links"}`;
      const label = `${key} (${groupCounts.get(key) || 0})`;
      if (!groups.has(label)) {
        const group = document.createElement("optgroup");
        group.label = label;
        groups.set(label, group);
        select.appendChild(group);
      }
      const option = document.createElement("option");
      option.value = node.id;
      option.textContent = degree ? (node.label || node.id) : `${node.label || node.id} · no visible links`;
      option.className = degree ? "" : "relationship-option-isolated";
      option.setAttribute("data-relationship-visible-links", String(degree));
      groups.get(label).appendChild(option);
    }
    if (nodes.some((node) => node.id === state.selectedId)) {
      select.value = state.selectedId;
    }
    return nodes;
  }

  function firstSelectableNode(state) {
    return selectableNodes(state, false)[0] || selectableNodes(state, true)[0] || null;
  }

  function ensureSelectableFocus(state) {
    const selected = state.nodesById.get(state.selectedId);
    if (!selected || !state.enabledTypes.size || state.enabledTypes.has(selected.type || "entity")) return;
    const next = firstSelectableNode(state);
    if (next) state.selectedId = next.id;
  }

  function refreshTypeFilterState(container, state, types) {
    container.querySelectorAll("[data-relationship-type]").forEach((checkbox) => {
      checkbox.checked = state.enabledTypes.has(checkbox.value);
    });
    const allCheckbox = container.querySelector("[data-relationship-type-all]");
    if (!allCheckbox) return;
    const selectedCount = types.filter((type) => state.enabledTypes.has(type)).length;
    allCheckbox.checked = selectedCount === types.length;
    allCheckbox.indeterminate = selectedCount > 0 && selectedCount < types.length;
  }

  function renderTypeFilters(browser, state) {
    const container = browser.querySelector("[data-relationship-type-filter]");
    if (!container) return;
    const types = graphTypes(state.nodes);
    const actions = document.createElement("div");
    actions.className = "relationship-type-filter-actions";
    const allLabel = document.createElement("label");
    allLabel.className = "relationship-type-filter-all";
    const allCheckbox = document.createElement("input");
    allCheckbox.type = "checkbox";
    allCheckbox.setAttribute("data-relationship-type-all", "");
    allCheckbox.addEventListener("change", () => {
      state.enabledTypes = allCheckbox.checked ? new Set(types) : new Set();
      ensureSelectableFocus(state);
      refreshTypeFilterState(container, state, types);
      renderNodeSelect(browser, state);
      renderGraph(browser, state);
      renderDetail(browser, state);
    });
    allLabel.appendChild(allCheckbox);
    allLabel.appendChild(document.createTextNode("All"));
    actions.appendChild(allLabel);
    const list = document.createElement("div");
    list.className = "relationship-type-filter-list";
    for (const type of types) {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = type;
      checkbox.setAttribute("data-relationship-type", type);
      checkbox.checked = state.enabledTypes.has(type);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          state.enabledTypes.add(type);
        } else {
          state.enabledTypes.delete(type);
        }
        ensureSelectableFocus(state);
        refreshTypeFilterState(container, state, types);
        renderNodeSelect(browser, state);
        renderGraph(browser, state);
        renderDetail(browser, state);
      });
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(TYPE_LABELS[type] || type));
      list.appendChild(label);
    }
    container.appendChild(actions);
    container.appendChild(list);
    refreshTypeFilterState(container, state, types);
  }

  function initBrowser(browser) {
    const graph = parseGraph(browser);
    const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
    if (!nodesById.size) return;
    const preferred =
      graph.nodes.find((node) => node.type === "vsr" && ["gap", "risk"].includes(String(node.status || ""))) ||
      graph.nodes.find((node) => node.type === "vsr" && String(node.status || "") === "needs_evidence") ||
      graph.nodes.find((node) => node.type !== "artifact" && ["gap", "risk", "needs_evidence"].includes(String(node.status || ""))) ||
      graph.nodes[0];
    const state = {
      nodes: graph.nodes,
      edges: graph.edges,
      nodesById,
      selectedId: preferred.id,
      activeId: preferred.id,
      depth: 1,
      cy: null,
      tapTimer: 0,
      tapTarget: "",
      backStack: [],
      forwardStack: [],
      searchQuery: "",
      graphInteractive: false,
      enabledTypes: new Set(graphTypes(graph.nodes))
    };
    renderTypeFilters(browser, state);
    const select = browser.querySelector("[data-relationship-node-select]");
    if (select) {
      select.addEventListener("change", () => selectNode(browser, state, select.value, true));
      renderNodeSelect(browser, state);
    }
    const search = browser.querySelector("[data-relationship-search]");
    if (search && select) {
      search.addEventListener("input", () => {
        state.searchQuery = search.value;
        const matches = renderNodeSelect(browser, state);
        const normalized = String(state.searchQuery || "").trim();
        if (normalized && matches.length && matches[0].id !== state.selectedId) {
          selectNode(browser, state, matches[0].id, false);
        } else {
          renderGraph(browser, state);
          renderDetail(browser, state);
        }
      });
      search.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        const match = selectableNodes(state, false)[0];
        if (match) {
          event.preventDefault();
          selectNode(browser, state, match.id, true);
        }
      });
    }
    browser.querySelectorAll("[data-relationship-depth]").forEach((button) => {
      button.addEventListener("click", () => {
        state.depth = Number(button.getAttribute("data-relationship-depth") || "1") || 1;
        browser.querySelectorAll("[data-relationship-depth]").forEach((item) => item.classList.toggle("is-active", item === button));
        renderGraph(browser, state);
      });
    });
    const defaultDepth = browser.querySelector('[data-relationship-depth="1"]');
    if (defaultDepth) defaultDepth.classList.add("is-active");
    const back = browser.querySelector("[data-relationship-back]");
    const forward = browser.querySelector("[data-relationship-forward]");
    const fit = browser.querySelector("[data-relationship-fit]");
    if (fit) {
      fit.addEventListener("click", () => {
        setGraphInteractive(browser, state, true);
        fitGraph(state, 88);
      });
    }
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (canvas) {
      canvas.addEventListener("pointerdown", () => {
        if (!state.graphInteractive) {
          setGraphInteractive(browser, state, true);
        }
      }, {capture: true});
    }
    if (back) {
      back.addEventListener("click", () => {
        const previous = state.backStack.pop();
        if (!previous) return;
        state.forwardStack.push(state.selectedId);
        selectNode(browser, state, previous, false);
      });
    }
    if (forward) {
      forward.addEventListener("click", () => {
        const next = state.forwardStack.pop();
        if (!next) return;
        state.backStack.push(state.selectedId);
        selectNode(browser, state, next, false);
      });
    }
    browser.addEventListener("click", (event) => {
      const tableRow = event.target.closest && event.target.closest("[data-relationship-table-node]");
      if (tableRow) {
        activateNode(browser, state, tableRow.getAttribute("data-relationship-table-node"));
        return;
      }
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (nodeElement) {
        activateNode(browser, state, nodeElement.getAttribute("data-node-id"));
        return;
      }
      const jump = event.target.closest && event.target.closest("[data-relationship-jump]");
      if (jump) {
        const nodeId = jump.getAttribute("data-relationship-jump");
        if (jump.getAttribute("data-relationship-jump-visible") === "true") {
          activateNode(browser, state, nodeId);
        } else {
          selectNode(browser, state, nodeId, true);
        }
      }
    });
    browser.addEventListener("dblclick", (event) => {
      const tableRow = event.target.closest && event.target.closest("[data-relationship-table-node]");
      if (!tableRow) return;
      event.preventDefault();
      selectNode(browser, state, tableRow.getAttribute("data-relationship-table-node"), true);
    });
    browser.addEventListener("keydown", (event) => {
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (!nodeElement || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      activateNode(browser, state, nodeElement.getAttribute("data-node-id"));
    });
    window.addEventListener("resize", () => fitGraph(state, 88), {passive: true});
    selectNode(browser, state, state.selectedId, false);
    browser.__relationshipState = state;
  }

  function openRelationshipModal(modal) {
    if (!modal) return;
    modal.hidden = false;
    document.body.classList.add("relationship-modal-open");
    const browser = modal.querySelector("[data-relationship-browser]");
    if (browser && !browser.dataset.relationshipInitialized) {
      initBrowser(browser);
      browser.dataset.relationshipInitialized = "true";
    } else if (browser && browser.__relationshipState) {
      fitGraph(browser.__relationshipState, 88);
    }
    const close = modal.querySelector("[data-relationship-close]");
    if (close) close.focus({preventScroll: true});
  }

  function closeRelationshipModal(modal) {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("relationship-modal-open");
  }

  document.querySelectorAll("[data-relationship-open]").forEach((button) => {
    button.addEventListener("click", () => {
      openRelationshipModal(button.closest(".report-relationship-section").querySelector("[data-relationship-modal]"));
    });
  });
  document.querySelectorAll("[data-relationship-modal]").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeRelationshipModal(modal);
    });
    const close = modal.querySelector("[data-relationship-close]");
    if (close) close.addEventListener("click", () => closeRelationshipModal(modal));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll("[data-relationship-modal]:not([hidden])").forEach(closeRelationshipModal);
  });
  document.querySelectorAll("[data-relationship-browser]:not([data-relationship-defer])").forEach(initBrowser);
})();
</script>
"""
