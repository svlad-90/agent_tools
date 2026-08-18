from __future__ import annotations

import json
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
    return f"""
  <section class="report-relationship-section" id="report-relationship-graph">
    <h2>{_esc(graph.title)}</h2>
    <div class="relationship-browser" data-relationship-browser>
      <script type="application/json" data-relationship-graph-data>{graph_json}</script>
      <div class="relationship-toolbar">
        <label><span class="label">Find node</span><input type="search" data-relationship-search placeholder="VSR, HAL, CTS, CDD"></label>
        <select data-relationship-node-select aria-label="Select graph node"></select>
        <div class="relationship-depth-controls" aria-label="Graph depth">
          <button type="button" data-relationship-depth="1">Depth 1</button>
          <button type="button" data-relationship-depth="2">Depth 2</button>
        </div>
        <div class="relationship-nav-controls" aria-label="Graph history">
          <button type="button" data-relationship-fit>Fit</button>
          <button type="button" data-relationship-back>Back</button>
          <button type="button" data-relationship-forward>Forward</button>
        </div>
      </div>
      <div class="relationship-layout">
        <div class="relationship-canvas-wrap">
          <div class="relationship-canvas" data-relationship-canvas role="img" aria-label="{_esc(graph.title)}"></div>
        </div>
        <aside class="relationship-detail" data-relationship-detail>
          <p>Select a node to inspect related requirements, CDD, HALs, tests, evidence, gaps, and notes.</p>
        </aside>
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

  function setActiveToc(id, reveal) {
    if (!id || id === activeTocId) {
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
    setActiveToc(currentReadableTocId(), true);
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
    setActiveToc(href.slice(1), true);
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

  function buildNeighborhood(selectedId, depth, nodesById, edges) {
    const visible = new Set([selectedId]);
    let frontier = new Set([selectedId]);
    for (let step = 0; step < depth; step += 1) {
      const next = new Set();
      for (const edge of edges) {
        if (frontier.has(edge.source) && !visible.has(edge.target)) {
          next.add(edge.target);
        }
        if (frontier.has(edge.target) && !visible.has(edge.source)) {
          next.add(edge.source);
        }
      }
      for (const id of next) visible.add(id);
      frontier = next;
      if (!frontier.size) break;
    }
    const visibleEdges = edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target));
    const visibleNodes = Array.from(visible).map((id) => nodesById.get(id)).filter(Boolean);
    return {nodes: visibleNodes, edges: visibleEdges};
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
    return graph.edges.filter((edge) => {
      if (edge.source === selectedId || edge.target === selectedId) return true;
      const source = graph.nodes.find((node) => node.id === edge.source);
      const target = graph.nodes.find((node) => node.id === edge.target);
      return source && target && source.type !== "artifact" && target.type !== "artifact";
    });
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
    const text = cssValue("--text", "#d8dee9");
    const panel = cssValue("--panel", "#202124");
    const metaPanel = cssValue("--meta-panel", "#1b1c1f");
    const border = cssValue("--meta-border", "#3a3f46");
    const link = cssValue("--link", "#2f81f7");
    const muted = cssValue("--muted", "#8b949e");
    const risk = cssValue("--comment-border", "#d0a800");
    const fail = cssValue("--stat-del", "#ff6b6b");
    const pass = cssValue("--stat-add", "#6bd97c");
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
      {selector: 'node[type = "domain"]', style: {"shape": "ellipse", "background-color": metaPanel}},
      {selector: 'node[type = "vsr"]', style: {"shape": "round-rectangle"}},
      {selector: 'node[type = "cdd"]', style: {"shape": "diamond", "width": 130, "height": 86}},
      {selector: 'node[type = "hal"]', style: {"shape": "hexagon"}},
      {selector: 'node[type = "test"]', style: {"shape": "barrel"}},
      {selector: 'node[type = "artifact"]', style: {"shape": "tag", "background-color": metaPanel}},
      {selector: 'node[type = "evidence"]', style: {"shape": "round-tag", "background-color": metaPanel}},
      {selector: "edge", style: {"width": 1.4, "line-color": muted, "target-arrow-color": muted, "target-arrow-shape": "triangle", "curve-style": "bezier", "opacity": .52}},
      {selector: ".status-covered, .status-covered-candidate, .status-pass", style: {"border-color": pass}},
      {selector: ".status-risk, .status-needs-evidence, .status-not-applicable-candidate", style: {"border-color": risk}},
      {selector: ".status-gap, .status-fail, .status-blocked", style: {"border-color": fail}},
      {selector: ".is-selected", style: {"border-color": link, "border-width": 4, "background-color": cssValue("--button-hover-bg", "#143d66")}},
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
      classes: `${cssStatus(node.status)} ${node.id === graph.selectedId ? "is-selected" : ""}`
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

  function renderGraph(browser, state) {
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (!canvas || !state.selectedId) return;
    if (typeof cytoscape !== "function") {
      canvas.textContent = "Cytoscape.js is not available.";
      return;
    }
    const graph = buildNeighborhood(state.selectedId, state.depth, state.nodesById, state.edges);
    graph.selectedId = state.selectedId;
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
      boxSelectionEnabled: false
    });
    state.cy.on("tap", "node", (event) => selectNode(browser, state, event.target.id(), true));
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
    fitGraph(state, 88);
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
      const relation = edge.relation || "related_to";
      const key = direction === "out" ? relation : `${relation} (incoming)`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    }
    return groups;
  }

  function renderDetail(browser, state) {
    const detail = browser.querySelector("[data-relationship-detail]");
    if (!detail || !state.selectedId) return;
    const node = state.nodesById.get(state.selectedId);
    if (!node) return;
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
      for (const [relation, nodes] of groups) {
        html += `<section><h4>${esc(relation.replaceAll("_", " "))}</h4><div class="relationship-related-list">`;
        for (const related of nodes.sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)))) {
          html += `<button type="button" data-relationship-jump="${esc(related.id)}"><span>${esc(related.label || related.id)}</span><small>${esc(nodeTypeLabel(related))}</small></button>`;
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
    const select = browser.querySelector("[data-relationship-node-select]");
    if (select) select.value = nodeId;
    renderGraph(browser, state);
    renderDetail(browser, state);
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
      depth: 1,
      cy: null,
      backStack: [],
      forwardStack: []
    };
    const select = browser.querySelector("[data-relationship-node-select]");
    if (select) {
      const sortedNodes = [...graph.nodes].sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id)));
      const groups = new Map();
      for (const node of sortedNodes) {
        const label = nodeTypeLabel(node);
        if (!groups.has(label)) {
          const group = document.createElement("optgroup");
          group.label = label;
          groups.set(label, group);
          select.appendChild(group);
        }
        const option = document.createElement("option");
        option.value = node.id;
        option.textContent = node.label || node.id;
        groups.get(label).appendChild(option);
      }
      select.addEventListener("change", () => selectNode(browser, state, select.value, true));
    }
    const search = browser.querySelector("[data-relationship-search]");
    if (search && select) {
      search.addEventListener("input", () => {
        const query = search.value.trim().toLowerCase();
        for (const option of select.options) {
          option.hidden = query && !option.textContent.toLowerCase().includes(query);
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
        fitGraph(state, 88);
      });
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
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (nodeElement) {
        selectNode(browser, state, nodeElement.getAttribute("data-node-id"), true);
        return;
      }
      const jump = event.target.closest && event.target.closest("[data-relationship-jump]");
      if (jump) {
        selectNode(browser, state, jump.getAttribute("data-relationship-jump"), true);
      }
    });
    browser.addEventListener("keydown", (event) => {
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (!nodeElement || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      selectNode(browser, state, nodeElement.getAttribute("data-node-id"), true);
    });
    window.addEventListener("resize", () => fitGraph(state, 88), {passive: true});
    selectNode(browser, state, state.selectedId, false);
  }

  document.querySelectorAll("[data-relationship-browser]").forEach(initBrowser);
})();
</script>
"""
