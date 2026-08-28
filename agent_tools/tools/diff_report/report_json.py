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
    group: str | None = None
    metrics: tuple[ReportMetric, ...] = ()
    links: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class ReportHeatmap:
    title: str
    rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ReportMetricTableColumn:
    key: str
    label: str
    sublabel: str | None = None


@dataclass(frozen=True)
class ReportMetricTableCell:
    text: str
    status: str | None = None
    note: str | None = None
    graph_view: dict[str, Any] | None = None
    parts: tuple["ReportMetricTableCell", ...] = ()


@dataclass(frozen=True)
class ReportMetricTable:
    title: str
    columns: tuple[ReportMetricTableColumn, ...]
    rows: tuple[tuple[ReportMetricTableCell, ...], ...]
    note: str | None = None


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
    traversal: dict[str, Any] | None = None
    filter_defaults: dict[str, Any] | None = None


@dataclass(frozen=True)
class GenericReport:
    title: str
    comments: ReviewComments
    metrics: tuple[ReportMetric, ...] = ()
    status_cards: tuple[ReportStatusCard, ...] = ()
    status_cards_title: str = "Status Cards"
    status_cards_note: str | None = None
    heatmaps: tuple[ReportHeatmap, ...] = ()
    metric_tables: tuple[ReportMetricTable, ...] = ()
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
        status_cards_title=_status_cards_section_text(payload.get("status_cards"), "title", "Status Cards"),
        status_cards_note=_status_cards_section_text(payload.get("status_cards"), "note", ""),
        heatmaps=heatmaps_from_payload(payload.get("heatmaps", payload.get("heatmap", []))),
        metric_tables=metric_tables_from_payload(payload.get("metric_tables", [])),
        tables=tables_from_payload(payload.get("tables", [])),
        timeline=timeline_from_payload(payload.get("timeline", [])),
        artifacts=artifacts_from_payload(payload.get("artifacts", [])),
        toc_groups=toc_groups_from_payload(payload.get("toc_groups", [])),
        relationship_graph=relationship_graph_from_payload(payload.get("relationship_graph")),
    )


def render_report_json_html(report: GenericReport, test_mode: bool = False) -> str:
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
    if report.relationship_graph:
        parts.append(_render_relationship_graph_section(report.relationship_graph))
    if report.metrics:
        parts.append(_render_metrics_section(report.metrics))
    if report.metric_tables:
        parts.append(_render_metric_tables_section(report.metric_tables))
    if report.status_cards:
        parts.append(
            _render_status_cards_section(
                report.status_cards,
                report.status_cards_title,
                report.status_cards_note,
            )
        )
    if report.heatmaps:
        parts.append(_render_heatmaps_section(report.heatmaps))
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
        if test_mode:
            parts.append(_report_self_test_script())
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


def _status_cards_section_text(raw_cards: Any, key: str, fallback: str) -> str | None:
    if isinstance(raw_cards, dict):
        value = raw_cards.get(key)
        if value is not None and not isinstance(value, str):
            raise DiffReportError(f"report.status_cards.{key} must be a string")
        if value:
            return str(value)
    return fallback or None


def status_cards_from_payload(raw_cards: Any) -> tuple[ReportStatusCard, ...]:
    if raw_cards is None:
        return ()
    if isinstance(raw_cards, dict):
        raw_cards = raw_cards.get("cards", [])
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
                group=str(item.get("group", "")).strip() or None,
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


def metric_tables_from_payload(raw_metric_tables: Any) -> tuple[ReportMetricTable, ...]:
    if raw_metric_tables is None:
        return ()
    if isinstance(raw_metric_tables, dict):
        raw_metric_tables = [raw_metric_tables]
    if not isinstance(raw_metric_tables, list):
        raise DiffReportError("report.metric_tables must be a list")
    metric_tables: list[ReportMetricTable] = []
    for index, item in enumerate(raw_metric_tables):
        field = f"report.metric_tables[{index}]"
        if not isinstance(item, dict):
            raise DiffReportError(f"{field} must be an object")
        columns = _metric_table_columns_from_payload(item.get("columns", []), f"{field}.columns")
        if not columns:
            raise DiffReportError(f"{field}.columns must contain at least one column")
        raw_rows = item.get("rows", [])
        if not isinstance(raw_rows, list):
            raise DiffReportError(f"{field}.rows must be a list")
        rows = tuple(
            _metric_table_row_from_payload(row, columns, f"{field}.rows[{row_index}]")
            for row_index, row in enumerate(raw_rows)
        )
        metric_tables.append(
            ReportMetricTable(
                title=str(item.get("title", "Metrics")),
                columns=columns,
                rows=rows,
                note=_optional_text(item, "note"),
            )
        )
    return tuple(metric_tables)


def _metric_table_columns_from_payload(raw_columns: Any, field: str) -> tuple[ReportMetricTableColumn, ...]:
    if not isinstance(raw_columns, list):
        raise DiffReportError(f"{field} must be a list")
    columns: list[ReportMetricTableColumn] = []
    for index, item in enumerate(raw_columns):
        if isinstance(item, str):
            columns.append(ReportMetricTableColumn(key=item, label=_label_for_key(item)))
            continue
        if not isinstance(item, dict):
            raise DiffReportError(f"{field}[{index}] must be an object or string")
        key = _required_text(item, "key", f"{field}[{index}]")
        columns.append(
            ReportMetricTableColumn(
                key=key,
                label=str(item.get("label", "")) or _label_for_key(key),
                sublabel=_optional_text(item, "sublabel"),
            )
        )
    return tuple(columns)


def _metric_table_row_from_payload(
    raw_row: Any,
    columns: tuple[ReportMetricTableColumn, ...],
    field: str,
) -> tuple[ReportMetricTableCell, ...]:
    if not isinstance(raw_row, dict):
        raise DiffReportError(f"{field} must be an object")
    raw_cells = raw_row.get("cells", raw_row)
    if not isinstance(raw_cells, dict):
        raise DiffReportError(f"{field}.cells must be an object")
    return tuple(
        _metric_table_cell_from_payload(raw_cells.get(column.key), f"{field}.cells.{column.key}")
        for column in columns
    )


def _metric_table_cell_from_payload(raw_cell: Any, field: str) -> ReportMetricTableCell:
    if raw_cell is None:
        return ReportMetricTableCell(text="")
    if isinstance(raw_cell, (str, int, float)):
        return ReportMetricTableCell(text=str(raw_cell))
    if not isinstance(raw_cell, dict):
        raise DiffReportError(f"{field} must be an object, string, or number")
    raw_parts = raw_cell.get("parts")
    parts: tuple[ReportMetricTableCell, ...] = ()
    if raw_parts is not None:
        if not isinstance(raw_parts, list):
            raise DiffReportError(f"{field}.parts must be a list")
        parts = tuple(
            _metric_table_cell_from_payload(part, f"{field}.parts[{index}]")
            for index, part in enumerate(raw_parts)
        )
        if any(part.parts for part in parts):
            raise DiffReportError(f"{field}.parts entries must not carry their own parts")
    return ReportMetricTableCell(
        text=str(raw_cell.get("text", "")),
        status=_optional_text(raw_cell, "status"),
        note=_optional_text(raw_cell, "note"),
        graph_view=_graph_view_from_payload(raw_cell.get("graph_view"), f"{field}.graph_view"),
        parts=parts,
    )


def _graph_view_from_payload(raw_view: Any, field: str) -> dict[str, Any] | None:
    if raw_view is None:
        return None
    if not isinstance(raw_view, dict):
        raise DiffReportError(f"{field} must be an object")
    view: dict[str, Any] = {}
    for key in ("focus", "target_type", "label", "isolate_root"):
        if key in raw_view and raw_view[key] is not None:
            if not isinstance(raw_view[key], str):
                raise DiffReportError(f"{field}.{key} must be a string")
            if raw_view[key]:
                view[key] = raw_view[key]
    types = raw_view.get("types")
    if types is not None:
        if not isinstance(types, list) or not all(isinstance(item, str) for item in types):
            raise DiffReportError(f"{field}.types must be a string list")
        view["types"] = list(types)
    filters = raw_view.get("filters")
    if filters is not None:
        if not isinstance(filters, dict):
            raise DiffReportError(f"{field}.filters must be an object")
        clean_filters: dict[str, dict[str, list[str]]] = {}
        for node_type, type_filters in filters.items():
            if not isinstance(node_type, str) or not isinstance(type_filters, dict):
                raise DiffReportError(f"{field}.filters must map entity type to field filters")
            clean_type_filters: dict[str, list[str]] = {}
            for filter_field, values in type_filters.items():
                if not isinstance(filter_field, str):
                    raise DiffReportError(f"{field}.filters.{node_type} keys must be strings")
                if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                    raise DiffReportError(f"{field}.filters.{node_type}.{filter_field} must be a string list")
                clean_type_filters[filter_field] = list(values)
            clean_filters[node_type] = clean_type_filters
        view["filters"] = clean_filters
    if not view.get("focus"):
        raise DiffReportError(f"{field}.focus is required")
    return view


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
        traversal=_relationship_graph_traversal_from_payload(raw_graph.get("traversal")),
        filter_defaults=_object_optional(raw_graph.get("filter_defaults"), "report.relationship_graph.filter_defaults"),
    )


def _relationship_graph_traversal_from_payload(raw_traversal: Any) -> dict[str, Any] | None:
    if raw_traversal is None:
        return None
    if not isinstance(raw_traversal, dict):
        raise DiffReportError("report.relationship_graph.traversal must be an object")
    traversal = dict(raw_traversal)
    for key in ("terminal_types", "pass_through_types"):
        if key not in traversal:
            continue
        value = traversal[key]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise DiffReportError(f"report.relationship_graph.traversal.{key} must be a string list")
    relation_traversal = traversal.get("relation_traversal")
    if relation_traversal is not None:
        if not isinstance(relation_traversal, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in relation_traversal.items()):
            raise DiffReportError("report.relationship_graph.traversal.relation_traversal must be a string mapping")
        invalid_values = sorted(set(relation_traversal.values()).difference({"both", "forward", "reverse", "none", "fallback"}))
        if invalid_values:
            raise DiffReportError("report.relationship_graph.traversal.relation_traversal values must be both, forward, reverse, none, or fallback")
    type_ranks = traversal.get("type_ranks")
    if type_ranks is not None:
        if not isinstance(type_ranks, dict) or not all(isinstance(key, str) and isinstance(value, int) for key, value in type_ranks.items()):
            raise DiffReportError("report.relationship_graph.traversal.type_ranks must be a string to integer mapping")
    edge_direction = traversal.get("edge_direction")
    if edge_direction is not None and edge_direction not in {"both", "forward", "reverse", "focused_context"}:
        raise DiffReportError("report.relationship_graph.traversal.edge_direction must be both, forward, reverse, or focused_context")
    return traversal


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


def _render_status_cards_section(
    cards: tuple[ReportStatusCard, ...],
    title: str = "Status Cards",
    note: str | None = None,
) -> str:
    parts = [f'  <section class="report-status-cards" id="report-status-cards"><h2>{_esc(title)}</h2>\n']
    if note:
        parts.append(f'    <p class="report-status-cards-note">{_format_text(note)}</p>\n')
    parts.append('    <div class="report-card-grid">\n')
    current_group: str | None = None
    for card in cards:
        if card.group != current_group:
            current_group = card.group
            if current_group:
                parts.append(f'    <h3 class="report-card-group-title">{_esc(current_group)}</h3>\n')
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
            focus = str(row.get("__graph_focus", ""))
            focus_attr = f' data-relationship-open-focus="{_esc(focus)}"' if focus else ""
            parts.append(f'      <div class="report-heatmap-row" role="row"{focus_attr}>\n')
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


def _metric_table_section_id(index: int) -> str:
    return "report-metric-tables" if index == 0 else f"report-metric-table-{index + 1}"


def _render_metric_tables_section(metric_tables: tuple[ReportMetricTable, ...]) -> str:
    parts: list[str] = []
    for index, metric_table in enumerate(metric_tables):
        section_id = _metric_table_section_id(index)
        parts.append(
            f'  <section class="report-metric-table-section" id="{section_id}">'
            f'<h2>{_esc(metric_table.title)}</h2>\n'
        )
        if metric_table.note:
            parts.append(f'    <p class="report-metric-table-note">{_format_text(metric_table.note)}</p>\n')
        parts.append('    <div class="report-metric-table-wrap"><table class="report-metric-table">\n      <thead><tr>')
        for column in metric_table.columns:
            sublabel = (
                f'<small class="report-metric-table-sublabel">{_esc(column.sublabel)}</small>'
                if column.sublabel
                else ""
            )
            parts.append(f"<th>{_esc(column.label)}{sublabel}</th>")
        parts.append("</tr></thead>\n      <tbody>\n")
        for row in metric_table.rows:
            parts.append("        <tr>")
            for position, cell in enumerate(row):
                tag = "th" if position == 0 else "td"
                scope = ' scope="row"' if position == 0 else ""
                status_attr = f' class="{_status_class(cell.status)}"' if cell.status else ""
                parts.append(f'<{tag}{status_attr}{scope}>{_render_metric_table_cell(cell)}</{tag}>')
            parts.append("</tr>\n")
        parts.append("      </tbody>\n    </table></div>\n  </section>\n")
    return "".join(parts)


def _render_metric_table_cell(cell: ReportMetricTableCell) -> str:
    if cell.parts:
        rendered = '<span class="report-metric-cell-part-sep">·</span>'.join(
            f'<span class="report-metric-cell-part {_status_class(part.status)}">{_render_metric_table_cell(part)}</span>'
            for part in cell.parts
        )
        note = f'<small class="report-metric-cell-note">{_esc(cell.note)}</small>' if cell.note else ""
        return f'<span class="report-metric-cell-parts">{rendered}</span>{note}'
    text = _esc(cell.text)
    note = f'<small class="report-metric-cell-note">{_esc(cell.note)}</small>' if cell.note else ""
    if not cell.graph_view:
        return f"{text}{note}"
    view_json = json.dumps(cell.graph_view, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    label = cell.graph_view.get("label") or f"Open graph for {cell.text}"
    return (
        f'<button type="button" class="report-metric-cell-link" title="{_esc(str(label))}"'
        f" data-relationship-open-view='{_esc(view_json)}'>{text or '&mdash;'}</button>{note}"
    )


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
    if graph.traversal:
        graph_payload["traversal"] = graph.traversal
    if graph.filter_defaults:
        graph_payload["filter_defaults"] = graph.filter_defaults
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
          <h3 id="report-relationship-graph-modal-title">{_esc(graph.title)}</h3>
          <button type="button" data-relationship-close aria-label="Close graph">Close</button>
        </div>
        <div class="relationship-browser" data-relationship-browser data-relationship-defer>
          <script type="application/json" data-relationship-graph-data>{graph_json}</script>
          <div class="relationship-toolbar">
            <div class="relationship-status-filter" data-relationship-status-filter aria-label="Status filter">
              <span class="relationship-control-label">Status</span>
            </div>
            <div class="relationship-search-controls">
              <label class="label relationship-cell-find-label" for="relationship-find-node">Find node</label>
              <label class="label relationship-cell-focus-label" for="relationship-focus-node">Focus <small data-relationship-node-count></small></label>
              <label class="label relationship-cell-type-label" for="relationship-focus-type">Focus type</label>
              <input class="relationship-cell-find-input" id="relationship-find-node" type="search" data-relationship-search placeholder="VSR, HAL, CTS, CDD">
              <select class="relationship-cell-focus-input" id="relationship-focus-node" data-relationship-node-select aria-label="Select graph node"></select>
              <select class="relationship-cell-type-input" id="relationship-focus-type" data-relationship-focus-type aria-label="Limit focus list to one entity type"></select>
              <label class="relationship-focus-scope relationship-cell-scope"><input type="checkbox" data-relationship-focus-scope><span>only visible</span></label>
            </div>
            <div class="relationship-view-controls">
              <div class="relationship-projection-controls" data-relationship-projection-controls>
                <label class="relationship-projection-auto">
                  <input type="checkbox" data-relationship-projection-auto>
                  <span>Auto</span>
                </label>
                <div class="relationship-projection-levels" data-relationship-projection-levels></div>
              </div>
              <label class="relationship-secondary-toggle">
                <input type="checkbox" data-relationship-secondary-links>
                <span>Shortcuts</span>
              </label>
            </div>
          </div>
          <div class="relationship-layout">
            <div class="relationship-explorer-main">
              <div class="relationship-control-bar" aria-label="Graph view controls">
                <div class="relationship-nav-controls" aria-label="Graph history">
                  <button type="button" data-relationship-fit title="Fit graph" aria-label="Fit graph">Fit</button>
                  <button type="button" data-relationship-back title="Back" aria-label="Back">←</button>
                  <button type="button" data-relationship-forward title="Forward" aria-label="Forward">→</button>
                </div>
                <button type="button" class="relationship-focus-badge" data-relationship-focus-badge hidden title="Deactivate graph">Deactivate graph</button>
                <div class="relationship-page-controls" data-relationship-page-controls>
                  <button type="button" data-relationship-page-prev aria-label="Previous graph page">‹</button>
                  <span data-relationship-page-count>Page 1</span>
                  <button type="button" data-relationship-page-next aria-label="Next graph page">›</button>
                </div>
              </div>
              <div class="relationship-canvas-wrap">
                <div class="relationship-canvas" data-relationship-canvas role="img" aria-label="{_esc(graph.title)}"></div>
              </div>
              <div class="relationship-selection-panel" data-relationship-selection-table>
                <div class="relationship-selection-table-head">
                  <span>Selection table</span>
                  <small data-relationship-selection-count></small>
                </div>
                <div class="relationship-selection-table">
                  <div class="relationship-selection-table-scroll">
                    <table>
                      <thead><tr><th>Type</th><th>Node</th><th>Status</th><th>Links</th><th>Summary</th></tr></thead>
                      <tbody data-relationship-selection-body></tbody>
                    </table>
                  </div>
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
    for index, metric_table in enumerate(report.metric_tables):
        items.append((metric_table.title, f"#{_metric_table_section_id(index)}"))
    if report.status_cards:
        items.append((report.status_cards_title or "Status Cards", "#report-status-cards"))
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
        "warning",
        "skip",
        "skipped",
        "assumption_failure",
        "auto_fail_candidate",
        "auto_pass_candidate",
        "auto_no_result_candidate",
        "auto_warning_candidate",
        "not_run",
        "not_done",
        "blocked",
    }


def _heatmap_keys(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    preferred = ("domain", "status", "total", "risk", "needs_evidence", "gap", "covered")
    keys: list[str] = [key for key in preferred if any(key in row for row in rows)]
    for row in rows:
        for key in row:
            if key.startswith("__"):
                continue
            if key not in keys:
                keys.append(key)
    return tuple(keys)


def _label_for_key(key: str) -> str:
    return key.replace("_", " ").title()


def _object_row(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DiffReportError(f"{field} entries must be objects")
    return dict(value)


def _object_optional(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DiffReportError(f"{field} must be an object")
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
  const TYPE_ORDER = ["product", "analysis_entity", "domain", "vsr", "cdd", "hal", "feature", "property", "cts_module", "vts_module", "artifact", "gap", "decision"];
  const TYPE_LABELS = {
    product: "Product",
    analysis_entity: "Analysis entity",
    vsr: "VSR",
    cdd: "CDD",
    hal: "HAL",
    cts_module: "CTS module",
    vts_module: "VTS module",
    evidence: "Evidence",
    gap: "Gap",
    decision: "Decision",
    domain: "Domain",
    feature: "Feature",
    property: "Property",
    artifact: "Artifact"
  };
  const DEFAULT_TYPE_RANKS = {product: 0, analysis_entity: 1, domain: 1, vsr: 2, cdd: 2, hal: 3, feature: 3, property: 3, cts_module: 3, vts_module: 3, artifact: 4, gap: 4, decision: 4};
  const DEFAULT_TERMINAL_TYPES = ["cts_module", "vts_module", "cdd", "property", "feature", "gap", "decision"];
  const MAX_FOCUS_OPTIONS = 400;

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

  function detailFieldLabel(key) {
    const labels = {
      requirement_text: "Description",
      description: "Description",
      section_title: "Section title",
      cdd_relationship: "CDD relationship",
      relationship: "Relationship",
      actual_build_evidence: "Actual build evidence",
      actual_runtime_evidence: "Actual runtime evidence",
      expected_behavior: "Expected behavior",
      current_status: "Current status",
      analysis_notes: "Analysis notes"
    };
    return labels[key] || String(key).replaceAll("_", " ");
  }

  function orderedDetailRows(node, details) {
    const preferred = ["description", "requirement_text", "section", "section_title", "anchor", "applicability", "trigger", "rule", "relationship", "cdd_relationship", "expected_behavior", "current_status", "analysis_notes"];
    const seen = new Set();
    const rows = [];
    function pushRow(key, value) {
      if (seen.has(key) || value == null || !String(value).trim() || (value && typeof value === "object")) return;
      rows.push([key, value]);
      seen.add(key);
    }
    for (const key of preferred) pushRow(key, details[key]);
    for (const [key, value] of Object.entries(details)) pushRow(key, value);
    const hasDescription = rows.some(([key]) => key === "description" || key === "requirement_text");
    if (node.type === "cdd" && !hasDescription) {
      rows.unshift([
        "description",
        "Source CDD text is not available for this graph node. The node was created from a traceability relationship, but the referenced CDD ID was not found in the parsed CDD catalog."
      ]);
    }
    return rows;
  }

  function parseGraph(browser) {
    const script = browser.querySelector("[data-relationship-graph-data]");
    if (!script) return {nodes: [], edges: []};
    try {
      const parsed = JSON.parse(script.textContent || "{}");
      return {
        nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
        edges: Array.isArray(parsed.edges) ? parsed.edges : [],
        traversal: parsed.traversal && typeof parsed.traversal === "object" ? parsed.traversal : {},
        filterDefaults: parsed.filter_defaults && typeof parsed.filter_defaults === "object" ? parsed.filter_defaults : {}
      };
    } catch (_error) {
      return {nodes: [], edges: []};
    }
  }

  function isTypeEnabled(node, selectedId, enabledTypes) {
    if (!node) return false;
    if (selectedId && node.id === selectedId) return true;
    return enabledTypes.has(node.type || "entity");
  }

  function directedReachableIds(rootId, state) {
    const root = String(rootId || "");
    if (!root || !state.nodesById.has(root)) return null;
    const outgoing = state.outgoingAdjacency || new Map();
    const ids = new Set([root]);
    const queue = [root];
    let cursor = 0;
    while (cursor < queue.length) {
      const fromId = queue[cursor];
      cursor += 1;
      for (const edge of outgoing.get(fromId) || []) {
        if (ids.has(edge.target)) continue;
        ids.add(edge.target);
        queue.push(edge.target);
      }
    }
    return ids;
  }

  function setIsolatedRoot(state, rootId) {
    state.isolatedRootId = String(rootId || "");
    state.isolatedNodeIds = state.isolatedRootId ? directedReachableIds(state.isolatedRootId, state) : null;
    state.scopedEdgesCache = null;
    state.scopedAdjacencyCache = null;
  }

  function isolatedIdsForRoot(state, rootId) {
    const id = String(rootId || "");
    return id ? directedReachableIds(id, state) : null;
  }

  function nodeInScope(state, node) {
    if (!node) return false;
    return !state.isolatedNodeIds || state.isolatedNodeIds.has(node.id);
  }

  function isStandaloneScopeNode(node) {
    if (!node) return false;
    if ((node.type || "entity") === "analysis_entity") return true;
    const details = node.details && typeof node.details === "object" ? node.details : {};
    return Boolean(details.analysis_scope);
  }

  function stateGraphNodes(state) {
    if (!state) return [];
    if (state.isolatedNodeIds) return state.nodes.filter((node) => nodeInScope(state, node));
    return state.nodes.filter((node) => !isStandaloneScopeNode(node));
  }

  function stateGraphEdges(state) {
    if (!state) return [];
    if (state.scopedEdgesCache) return state.scopedEdgesCache;
    const visibleIds = new Set(stateGraphNodes(state).map((node) => node.id));
    state.scopedEdgesCache = state.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
    return state.scopedEdgesCache;
  }

  function stateGraphAdjacency(state) {
    if (!state) return new Map();
    if (!state.scopedAdjacencyCache) {
      state.scopedAdjacencyCache = buildAdjacency(stateGraphEdges(state));
    }
    return state.scopedAdjacencyCache;
  }

  function stateGraphTypes(state) {
    return graphTypes(stateGraphNodes(state));
  }

  function fieldValue(node, field) {
    if (!node) return "";
    if (field === "status") return String(node.status || "unknown");
    if (Object.prototype.hasOwnProperty.call(node, field)) return String(node[field] == null ? "" : node[field]);
    const details = node.details && typeof node.details === "object" ? node.details : {};
    return String(details[field] == null ? "" : details[field]);
  }

  function subfilterFieldsForType(type, nodes) {
    const candidates = ["suite", "domain", "applicability", "mapping_status", "coverage_strength", "evidence_trust"];
    const typedNodes = nodes.filter((node) => (node.type || "entity") === type);
    const fields = [];
    for (const field of candidates) {
      const values = new Set(typedNodes.map((node) => fieldValue(node, field)).filter((value) => value.trim()));
      if (values.size > 1 || field === "status" && values.size > 0) {
        fields.push({field, values: Array.from(values).sort((left, right) => String(left).localeCompare(String(right)))});
      }
    }
    return fields;
  }

  function createSubfilters(nodes, defaults) {
    const result = {};
    const rawDefaults = defaults && typeof defaults === "object" ? defaults : {};
    for (const type of graphTypes(nodes)) {
      const typeDefaults = rawDefaults[type] && typeof rawDefaults[type] === "object" ? rawDefaults[type] : {};
      const typeFilters = {};
      for (const config of subfilterFieldsForType(type, nodes)) {
        const fieldDefaults = typeDefaults[config.field] && typeof typeDefaults[config.field] === "object" ? typeDefaults[config.field] : {};
        const include = Array.isArray(fieldDefaults.include) ? new Set(fieldDefaults.include.map(String)) : null;
        const exclude = new Set(Array.isArray(fieldDefaults.exclude) ? fieldDefaults.exclude.map(String) : []);
        const enabled = new Set(config.values.filter((value) => include ? include.has(value) : !exclude.has(value)));
        typeFilters[config.field] = {values: config.values, enabled};
      }
      result[type] = typeFilters;
    }
    return result;
  }

  function createStatusFilter(nodes, defaults) {
    const values = Array.from(new Set(nodes.map((node) => fieldValue(node, "status")).filter((value) => value.trim())))
      .sort((left, right) => String(left).localeCompare(String(right)));
    let include = null;
    const exclude = new Set();
    for (const typeDefaults of Object.values(defaults && typeof defaults === "object" ? defaults : {})) {
      const config = typeDefaults && typeDefaults.status;
      if (!config || typeof config !== "object") continue;
      if (Array.isArray(config.include)) {
        include = include || new Set();
        for (const value of config.include) include.add(String(value));
      }
      if (Array.isArray(config.exclude)) {
        for (const value of config.exclude) exclude.add(String(value));
      }
    }
    const enabled = new Set(values.filter((value) => include ? include.has(value) : !exclude.has(value)));
    return {values, enabled};
  }

  function resetSubfilters(state) {
    const nodes = stateGraphNodes(state);
    state.subfilters = createSubfilters(nodes, state.filterDefaults);
    state.statusFilter = createStatusFilter(nodes, state.filterDefaults);
  }

  function isSubfilterEnabled(node, state) {
    if (!node || !state) return false;
    const statusFilter = state.statusFilter;
    if (statusFilter && statusFilter.values.length && !statusFilter.enabled.has(fieldValue(node, "status"))) return false;
    return isNonStatusSubfilterEnabled(node, state);
  }

  function isNonStatusSubfilterEnabled(node, state) {
    if (!node || !state) return false;
    const type = node.type || "entity";
    const typeFilters = state.subfilters && state.subfilters[type] || {};
    for (const [field, config] of Object.entries(typeFilters)) {
      if (field === "status") continue;
      const value = fieldValue(node, field);
      // a node that does not carry the field at all cannot be judged by it; the filter lists only
      // the values that exist, so an empty value must not silently hide the node
      if (!value) continue;
      if (config.values && config.values.length && !config.enabled.has(value)) return false;
    }
    return true;
  }

  function isNodeVisible(node, state) {
    if (!node) return false;
    if (!nodeInScope(state, node)) return false;
    if (state && node.id === state.selectedId) return true;
    return isTypeEnabled(node, state && state.selectedId, state.enabledTypes) && isSubfilterEnabled(node, state);
  }

  function includeNodeInSubfilters(state, node) {
    if (!node || !state.subfilters) return;
    const typeFilters = state.subfilters[node.type || "entity"] || {};
    for (const [field, config] of Object.entries(typeFilters)) {
      const value = fieldValue(node, field);
      if (config.values && config.values.includes(value)) config.enabled.add(value);
    }
  }

  function traversalConfig(rawTraversal) {
    const raw = rawTraversal && typeof rawTraversal === "object" ? rawTraversal : {};
    const terminalTypes = Array.isArray(raw.terminal_types) ? raw.terminal_types : DEFAULT_TERMINAL_TYPES;
    const passThroughTypes = Array.isArray(raw.pass_through_types) ? raw.pass_through_types : [];
    const relationTraversal = raw.relation_traversal && typeof raw.relation_traversal === "object" ? raw.relation_traversal : {};
    const typeRanks = raw.type_ranks && typeof raw.type_ranks === "object" ? raw.type_ranks : DEFAULT_TYPE_RANKS;
    return {
      terminalTypes: new Set(terminalTypes),
      passThroughTypes: new Set(passThroughTypes),
      relationTraversal,
      edgeDirection: raw.edge_direction || "focused_context",
      typeRanks
    };
  }

  function activeTraversal(state) {
    return state.traversal;
  }

  function edgeTraversalMode(edge, traversal) {
    const relationMode = traversal.relationTraversal && traversal.relationTraversal[edge.relation || "related_to"];
    const mode = edge.traverse || relationMode || traversal.edgeDirection || "both";
    if (traversal.ignoreFallback && mode === "fallback") return "both";
    return mode;
  }

  function isShortcutEdge(edge, traversal) {
    const relationMode = traversal.relationTraversal && traversal.relationTraversal[edge.relation || "related_to"];
    return (edge.traverse || relationMode || "") === "fallback";
  }

  function isFallbackTraversalEdge(edge, traversal) {
    return edgeTraversalMode(edge, traversal) === "fallback";
  }

  function edgeAllowsTraversal(edge, fromId, toId, traversal) {
    const mode = edgeTraversalMode(edge, traversal);
    if (mode === "none") return false;
    if (mode === "fallback") return false;
    if (mode === "both") return true;
    const forward = edge.source === fromId && edge.target === toId;
    const reverse = edge.target === fromId && edge.source === toId;
    return (mode === "forward" && forward) || (mode === "reverse" && reverse);
  }

  function edgeFallbackCandidate(edge, fromId, toId, traversal) {
    const mode = edgeTraversalMode(edge, traversal);
    if (mode !== "fallback") return false;
    return (edge.source === fromId && edge.target === toId) || (edge.target === fromId && edge.source === toId);
  }

  function edgeKey(edge) {
    return `${edge.source}\u0000${edge.target}\u0000${edge.relation || "related_to"}`;
  }

  function isSecondaryEdge(edge) {
    return String(edge.display || edge.visibility || "").toLowerCase() === "secondary";
  }

  function buildAdjacency(edges) {
    const adjacency = new Map();
    for (const edge of edges) {
      if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
      if (!adjacency.has(edge.target)) adjacency.set(edge.target, []);
      adjacency.get(edge.source).push({id: edge.target, edge});
      adjacency.get(edge.target).push({id: edge.source, edge});
    }
    return adjacency;
  }

  function buildOutgoingAdjacency(edges) {
    const adjacency = new Map();
    for (const edge of edges) {
      if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
      adjacency.get(edge.source).push(edge);
    }
    return adjacency;
  }

  function buildNeighborhood(selectedId, nodesById, edges, adjacency, nodeVisible, contextNodeVisible, traversal, includeSecondaryLinks) {
    const selected = nodesById.get(selectedId);
    if (!selected) {
      return {nodes: [], edges: [], distances: new Map()};
    }
    const rankOf = (node) => {
      if (!node) return 99;
      const ranks = traversal.typeRanks || DEFAULT_TYPE_RANKS;
      const value = ranks[node.type || "entity"];
      return Number.isFinite(value) ? value : 99;
    };
    const neighbors = (nodeId) => adjacency.get(nodeId) || [];
    const distances = new Map([[selectedId, 0]]);
    const traversedEdgeKeys = new Set();
    const traversedEdgesByKey = new Map();
    const markTraversedEdge = (edge) => {
      const key = edgeKey(edge);
      traversedEdgeKeys.add(key);
      if (!traversedEdgesByKey.has(key)) {
        traversedEdgesByKey.set(key, edge);
      }
    };
    const selectedRank = rankOf(selected);
    const sortCandidate = (left, right) => {
      const leftNode = nodesById.get(left.id);
      const rightNode = nodesById.get(right.id);
      const leftRank = rankOf(leftNode);
      const rightRank = rankOf(rightNode);
      if (left.primary !== right.primary) return left.primary ? -1 : 1;
      if (left.directed !== right.directed) return left.directed ? -1 : 1;
      if (leftRank !== rightRank) return rightRank - leftRank;
      return String(leftNode && (leftNode.label || leftNode.id) || left.id).localeCompare(String(rightNode && (rightNode.label || rightNode.id) || right.id));
    };
    const ancestry = new Set([selectedId]);
    const collectVisibleParents = (seedIds) => {
      const queue = Array.from(seedIds || []).filter((id) => nodesById.has(id));
      const seen = new Set(queue);
      while (queue.length) {
        const currentId = queue.shift();
        const currentNode = nodesById.get(currentId);
        const currentRank = rankOf(currentNode);
        const currentDistance = distances.get(currentId) ?? 0;
        const rawCandidates = neighbors(currentId).filter((item) => {
          const node = nodesById.get(item.id);
          if (!node) return false;
          if (isSecondaryEdge(item.edge) && !includeSecondaryLinks) return false;
          if (!contextNodeVisible(node)) return false;
          return rankOf(node) < currentRank;
        }).map((item) => ({
          id: item.id,
          edge: item.edge,
          directed: item.edge.source === item.id && item.edge.target === currentId,
          primary: !isSecondaryEdge(item.edge)
        })).sort(sortCandidate);
        const regularCandidates = rawCandidates.filter((item) => !isFallbackTraversalEdge(item.edge, traversal));
        const candidates = regularCandidates.length
          ? regularCandidates
          : rawCandidates.filter((item) => isFallbackTraversalEdge(item.edge, traversal));
        for (const parent of candidates) {
          markTraversedEdge(parent.edge);
          if (seen.has(parent.id)) continue;
          seen.add(parent.id);
          ancestry.add(parent.id);
          distances.set(parent.id, Math.min(distances.get(parent.id) ?? currentDistance + 1, currentDistance + 1));
          queue.push(parent.id);
        }
      }
    };
    collectVisibleParents([selectedId]);
    const downQueue = [selectedId];
    const downSeen = new Set([selectedId]);
    const downParents = new Map();
    const visibleDescendants = [];
    const fallbackDescendants = [];
    const secondaryDescendants = [];
    while (downQueue.length) {
      const fromId = downQueue.shift();
      const fromRank = rankOf(nodesById.get(fromId));
      const regularItems = [];
      const fallbackItems = [];
      for (const item of neighbors(fromId)) {
        const toId = item.id;
        const toNode = nodesById.get(toId);
        if (!toNode || downSeen.has(toId)) continue;
        const edgeSecondary = isSecondaryEdge(item.edge);
        const edgeFallback = isFallbackTraversalEdge(item.edge, traversal);
        const directedChild = item.edge.source === fromId && item.edge.target === toId;
        if (!directedChild) continue;
        if (edgeSecondary && !(includeSecondaryLinks && fromId === selectedId)) continue;
        const toRank = rankOf(toNode);
        const rankedChild = toRank > fromRank;
        const fallbackChild = fromRank === 99 && toRank === fromRank;
        if (!rankedChild && !fallbackChild) continue;
        (edgeFallback ? fallbackItems : regularItems).push({item, toId, toNode, edgeSecondary});
      }
      const visibleFallbackItems = fallbackItems.filter((candidate) => nodeVisible(candidate.toNode));
      const items = regularItems.length
        ? regularItems.concat(visibleFallbackItems)
        : fallbackItems;
      for (const candidate of items) {
        const {item, toId, toNode, edgeSecondary} = candidate;
        downSeen.add(toId);
        downParents.set(toId, {parentId: fromId, edge: item.edge});
        if (isFallbackTraversalEdge(item.edge, traversal) && nodeVisible(toNode)) {
          fallbackDescendants.push(toId);
        } else if (edgeSecondary && includeSecondaryLinks && fromId === selectedId && nodeVisible(toNode)) {
          secondaryDescendants.push(toId);
        } else if (edgeSecondary) {
          downQueue.push(toId);
        } else if (nodeVisible(toNode)) {
          visibleDescendants.push(toId);
        } else {
          downQueue.push(toId);
        }
      }
    }
    if (visibleDescendants.length || secondaryDescendants.length || fallbackDescendants.length) {
      // Draw the first visible child rank only. Hidden intermediate nodes are still traversed,
      // and direct shortcut edges to deeper ranks do not mix tests with requirements.
      const candidateDescendants = visibleDescendants.concat(secondaryDescendants, fallbackDescendants);
      const visibleChildRank = Math.min(...candidateDescendants.map((id) => rankOf(nodesById.get(id))));
      const shownDescendants = candidateDescendants.filter((id) => rankOf(nodesById.get(id)) === visibleChildRank);
      for (const targetId of shownDescendants) {
        const path = [];
        let pathId = targetId;
        while (pathId && pathId !== selectedId) {
          const parent = downParents.get(pathId);
          if (!parent) break;
          path.push({id: pathId, edge: parent.edge});
          pathId = parent.parentId;
        }
        if (pathId !== selectedId) continue;
        path.reverse();
        for (let index = 0; index < path.length; index += 1) {
          const item = path[index];
          markTraversedEdge(item.edge);
          distances.set(item.id, Math.min(distances.get(item.id) ?? index + 1, index + 1));
        }
      }
    }
    const selectedVisible = nodeVisible(selected);
    const hasVisibleNonFocusNode = Array.from(distances.keys()).some((id) => {
      if (id === selectedId) return false;
      return nodeVisible(nodesById.get(id));
    });
    const hasVisibleGraphContent = selectedVisible || hasVisibleNonFocusNode;
    const visibleIds = new Set(Array.from(distances.keys()).filter((id) => {
      if (!hasVisibleGraphContent) return false;
      const node = nodesById.get(id);
      return nodeVisible(node) || (ancestry.has(id) && contextNodeVisible(node));
    }));
    const visibleEdges = Array.from(traversedEdgesByKey.values()).filter((edge) => {
      const sourceDistance = visibleIds.has(edge.source) ? distances.get(edge.source) : null;
      const targetDistance = visibleIds.has(edge.target) ? distances.get(edge.target) : null;
      if (sourceDistance == null || targetDistance == null) return false;
      return true;
    });
    const derivedEdges = [];
    const visibleList = Array.from(visibleIds);
    for (const targetId of visibleList) {
      if (targetId === selectedId || (distances.get(targetId) ?? 0) <= 0) continue;
      const queue = [targetId];
      const seen = new Set([targetId]);
      let sourceId = "";
      while (queue.length && !sourceId) {
        const currentId = queue.shift();
        const currentDistance = distances.get(currentId) ?? 99;
        for (const item of neighbors(currentId)) {
          if (!traversedEdgeKeys.has(edgeKey(item.edge))) continue;
          if (seen.has(item.id) || !distances.has(item.id)) continue;
          const itemDistance = distances.get(item.id) ?? 99;
          if (itemDistance >= currentDistance) continue;
          seen.add(item.id);
          if (visibleIds.has(item.id)) {
            sourceId = item.id;
            break;
          }
          queue.push(item.id);
        }
      }
      if (!sourceId) continue;
      const hasDirect = visibleEdges.some((edge) =>
        (edge.source === sourceId && edge.target === targetId) || (edge.source === targetId && edge.target === sourceId)
      );
      if (!hasDirect) {
        derivedEdges.push({source: sourceId, target: targetId, relation: "through_filtered"});
      }
    }
    const visibleNodes = Array.from(visibleIds).map((id) => nodesById.get(id)).filter(Boolean);
    visibleEdges.push(...derivedEdges);
    return {nodes: visibleNodes, edges: visibleEdges, distances, contextIds: new Set(ancestry)};
  }

  function graphMatchesSearch(graph, query, state) {
    const normalized = String(query || "").trim().toLowerCase();
    if (!normalized) return graph;
    const nodes = graph.nodes.filter((node) => searchableTextForState(state, node).includes(normalized));
    const visible = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)),
      distances: graph.distances,
      contextIds: graph.contextIds,
      listMode: graph.listMode
    };
  }

  function singleEnabledType(state) {
    const types = Array.from(state.enabledTypes || []).filter(Boolean);
    return types.length === 1 ? types[0] : "";
  }

  function buildTypeListGraph(state) {
    const selectedType = singleEnabledType(state);
    if (!selectedType) return null;
    const selected = state.nodesById.get(state.selectedId || "");
    if (selected && (selected.type || "entity") !== selectedType) return null;
    const nodes = stateGraphNodes(state).filter((node) => node.type === selectedType && isSubfilterEnabled(node, state));
    return {
      nodes,
      edges: [],
      distances: new Map(nodes.map((node) => [node.id, node.id === state.selectedId ? 0 : 1])),
      listMode: true
    };
  }

  function capGraph(graph, selectedId, limit, page) {
    if (!limit) {
      return Object.assign({}, graph, {pagination: {enabled: false, page: 0, pageCount: 1, start: 0, end: graph.nodes.length, total: graph.nodes.length, rendered: graph.nodes.length}});
    }
    const score = (node) => {
      const status = String(node.status || "");
      const distance = graph.distances && graph.distances.get(node.id);
      const statusScore = ["gap", "risk", "needs_evidence", "fail", "blocked"].includes(status) ? 0 : 1;
      return [
        distance == null ? 9 : distance,
        statusScore,
        typeRank(node),
        String(node.label || node.id)
      ];
    };
    const compare = (left, right) => {
      const leftScore = score(left);
      const rightScore = score(right);
      for (let index = 0; index < leftScore.length; index += 1) {
        if (leftScore[index] < rightScore[index]) return -1;
        if (leftScore[index] > rightScore[index]) return 1;
      }
      return 0;
    };
    const selectedNode = graph.nodes.find((node) => node.id === selectedId);
    const contextIds = graph.contextIds || new Set(selectedNode ? [selectedId] : []);
    const contextNodes = graph.listMode ? [] : graph.nodes.filter((node) => contextIds.has(node.id));
    const pageSize = Math.max(1, limit);
    const buckets = new Map();
    for (const node of graph.nodes) {
      if (contextIds.has(node.id)) continue;
      const distance = graph.distances && graph.distances.get(node.id);
      const key = `${distance == null ? 9 : distance}\u0000${typeRank(node)}\u0000${node.type || "entity"}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(node);
    }
    for (const bucket of buckets.values()) bucket.sort(compare);
    const orderedKeys = Array.from(buckets.keys()).sort((left, right) => {
      const [leftDistance, leftRank, leftType] = left.split("\u0000");
      const [rightDistance, rightRank, rightType] = right.split("\u0000");
      return Number(leftDistance) - Number(rightDistance) ||
        Number(leftRank) - Number(rightRank) ||
        String(leftType).localeCompare(String(rightType));
    });
    const orderedNodes = [];
    while (orderedKeys.length) {
      let added = false;
      for (const key of orderedKeys) {
        const bucket = buckets.get(key) || [];
        const node = bucket.shift();
        if (!node) continue;
        orderedNodes.push(node);
        added = true;
      }
      if (!added) break;
    }
    const total = orderedNodes.length;
    if (total <= pageSize) {
      return Object.assign({}, graph, {
        pagination: {enabled: false, page: 0, pageCount: 1, start: total ? 1 : 0, end: total, total, pageSize, rendered: graph.nodes.length}
      });
    }
    const pageCount = Math.max(1, Math.ceil(total / pageSize));
    const currentPage = Math.min(Math.max(Number(page) || 0, 0), pageCount - 1);
    const startIndex = currentPage * pageSize;
    const pageNodes = orderedNodes.slice(startIndex, startIndex + pageSize);
    const nodes = graph.listMode ? pageNodes : contextNodes.concat(pageNodes);
    const end = Math.min(startIndex + pageSize, total);
    const visible = new Set(nodes.map((node) => node.id));
    return {
      nodes,
      edges: graph.edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)),
      distances: graph.distances,
      contextIds: graph.contextIds,
      listMode: graph.listMode,
      omitted: total - pageNodes.length,
      pagination: {
        enabled: true,
        page: currentPage,
        pageCount,
        start: startIndex + 1,
        end,
        total,
        pageSize,
        rendered: nodes.length
      }
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
    const relationPriority = (edge) => {
      const relation = String(edge && edge.relation || "");
      if (relation === "through_filtered") return 3;
      if (relation.includes("auto_candidate")) return 2;
      if (relation.includes("annotation")) return 0;
      return 1;
    };
    const byPair = new Map();
    for (const edge of graph.edges || []) {
      if (!edge || !edge.source || !edge.target) continue;
      const key = `${edge.source}\u0000${edge.target}`;
      const current = byPair.get(key);
      if (!current || relationPriority(edge) < relationPriority(current)) {
        byPair.set(key, edge);
      }
    }
    return Array.from(byPair.values());
  }

  function nodeDetailText(node, key) {
    const details = node && node.details && typeof node.details === "object" ? node.details : {};
    const value = details[key];
    return value == null ? "" : String(value);
  }

  function stripLeadingRequirementId(text) {
    return String(text || "")
      .replace(/^\s*\[[^\]]+\]\s*/, "")
      .replace(/^\s*(?:CDD|VSR|GAS-VSR)\s+[A-Z0-9./:-]+(?:\s*[·:-]\s*)?/i, "")
      .trim();
  }

  function requirementPhrase(text, requireMarker) {
    const clean = stripLeadingRequirementId(String(text || "").replace(/\s+/g, " "));
    const ruleWords = [
      "STRONGLY\\s+RECOMMENDED",
      "MUST\\s+NOT",
      "SHALL\\s+NOT",
      "SHOULD\\s+NOT",
      "MUST",
      "SHALL",
      "SHOULD",
      "REQUIRED",
      "REQUIRES",
      "RECOMMENDED",
      "PROHIBITED",
      "FORBIDDEN",
      "OPTIONAL",
      "MAY"
    ];
    const match = clean.match(new RegExp(`\\b(${ruleWords.join("|")})\\b`, "i"));
    if (requireMarker && !match) return "";
    const phrase = match ? clean.slice(match.index).trim() : clean;
    return phrase.replace(/\s+/g, " ").trim();
  }

  function nodeDisplayLabel(node) {
    const base = node && (node.label || node.id) || "";
    const type = node && (node.type || "entity") || "entity";
    if (type !== "cdd" && type !== "vsr") return base;
    const summary = nodeDetailText(node, "requirement_summary") || node.summary || "";
    const text = nodeDetailText(node, "requirement_text") || summary;
    const phrase = requirementPhrase(summary, true) || requirementPhrase(text, true) || requirementPhrase(summary, false) || requirementPhrase(text, false);
    if (!phrase || String(base).includes(phrase)) return base;
    const id = String(node.id || base).replace(/^[^:]+:/, "");
    return `${id} · ${phrase}`;
  }

  function wrapLabel(value, options) {
    const text = String(value || "");
    const config = options && typeof options === "object" ? options : {};
    const limit = config.lineLength || 22;
    const maxLines = config.maxLines || 4;
    const tokens = [];
    for (const token of text.split(/(\s+|[@./:_-])/).filter(Boolean)) {
      if (token.length <= limit) {
        tokens.push(token);
        continue;
      }
      for (let index = 0; index < token.length; index += limit) {
        tokens.push(token.slice(index, index + limit));
      }
    }
    const lines = [];
    let line = "";
    let truncated = false;
    for (const token of tokens) {
      const candidate = line + token;
      if (candidate.length > limit && line) {
        if (lines.length >= maxLines) {
          truncated = true;
          break;
        }
        lines.push(line);
        line = token.trimStart();
      } else {
        line = candidate;
      }
    }
    if (line && lines.length < maxLines) lines.push(line);
    else if (line) truncated = true;
    const wrapped = lines.slice(0, maxLines);
    if (truncated && wrapped.length) {
      wrapped[wrapped.length - 1] = `${wrapped[wrapped.length - 1].slice(0, limit - 1)}\u2026`;
    }
    return wrapped.join("\n");
  }

  function wrapNodeDisplayLabel(node) {
    const type = node && (node.type || "entity") || "entity";
    if (type === "cdd") return wrapLabel(nodeDisplayLabel(node), {lineLength: 18, maxLines: 3});
    return wrapLabel(nodeDisplayLabel(node), {lineLength: 22, maxLines: 4});
  }

  function cssValue(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  let cachedCytoscapeStyleTheme = "";
  let cachedCytoscapeStyle = null;

  function cytoscapeStyle() {
    const theme = document.documentElement.dataset.theme || "";
    if (cachedCytoscapeStyle && cachedCytoscapeStyleTheme === theme) {
      return cachedCytoscapeStyle;
    }
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
    const info = cssValue("--graph-status-info-border", "#7c3aed");
    const infoBg = cssValue("--graph-status-info-bg", "#f5f3ff");
    const autoPass = cssValue("--graph-status-auto-pass-border", "#2563eb");
    const autoPassBg = cssValue("--graph-status-auto-pass-bg", "#eff6ff");
    const neutral = cssValue("--graph-status-neutral-border", "#64748b");
    const neutralBg = cssValue("--graph-status-neutral-bg", "#f8fafc");
    cachedCytoscapeStyleTheme = theme;
    cachedCytoscapeStyle = [
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
      {selector: 'node[type = "product"]', style: {"shape": "round-rectangle", "width": 190, "height": 76, "background-color": domainPanel}},
      {selector: 'node[type = "cts_module"]', style: {"shape": "barrel"}},
      {selector: 'node[type = "vts_module"]', style: {"shape": "barrel"}},
      {selector: 'node[type = "artifact"]', style: {"shape": "tag", "background-color": metaPanel}},
      {selector: 'node[type = "evidence"]', style: {"shape": "round-tag", "background-color": metaPanel}},
      {selector: ".is-list-item", style: {"width": 190, "height": 58, "text-max-width": 162, "font-size": 9}},
      {selector: '.is-list-item[type = "cdd"]', style: {"width": 122, "height": 80, "text-max-width": 92}},
      {selector: "edge", style: {"width": 1.4, "line-color": muted, "target-arrow-color": muted, "target-arrow-shape": "triangle", "curve-style": "bezier", "opacity": .52}},
      {selector: ".status-covered, .status-covered-candidate, .status-pass, .status-not-failed", style: {"border-color": pass, "background-color": passBg}},
      {selector: ".status-risk, .status-needs-evidence, .status-not-applicable-candidate, .status-warning", style: {"border-color": risk, "background-color": riskBg}},
      {selector: ".status-gap, .status-fail, .status-blocked", style: {"border-color": fail, "background-color": failBg}},
      {selector: ".status-assumption-failure, .status-skip, .status-skipped, .status-auto-fail-candidate, .status-auto-warning-candidate", style: {"border-color": info, "background-color": infoBg}},
      {selector: ".status-auto-pass-candidate", style: {"border-color": autoPass, "background-color": autoPassBg}},
      {selector: ".status-not-run, .status-not-done, .status-unknown, .status-auto-no-result-candidate", style: {"border-color": neutral, "background-color": neutralBg}},
      {selector: ".is-selected", style: {"border-color": link, "border-width": 5, "outline-color": link, "outline-width": 3, "outline-opacity": .52}},
      {selector: ".is-active", style: {"border-color": active, "border-width": 4}},
      {selector: "node:selected", style: {"border-color": link, "border-width": 4}}
    ];
    return cachedCytoscapeStyle;
  }

  function listNodePosition(index, graph) {
    const layout = graph.listLayout || {};
    const cols = Math.max(1, layout.cols || 1);
    const rows = Math.max(1, layout.rows || 1);
    const col = index % cols;
    const row = Math.floor(index / cols);
    const left = layout.left || 120;
    const top = layout.top || 90;
    const usableWidth = Math.max(1, (layout.width || 900) - left * 2);
    const usableHeight = Math.max(1, (layout.height || 720) - top * 2);
    const colGap = cols > 1 ? usableWidth / (cols - 1) : 0;
    const rowGap = rows > 1 ? usableHeight / (rows - 1) : 0;
    return {x: left + col * colGap, y: top + row * rowGap};
  }

  function nodeTraversalRank(node, traversal) {
    if (!node) return 99;
    const ranks = traversal && traversal.typeRanks || DEFAULT_TYPE_RANKS;
    const value = ranks[node.type || "entity"];
    return Number.isFinite(value) ? value : 99;
  }

  function buildHierarchicalLayout(nodes, width, height, selectedId, traversal) {
    const positions = new Map();
    if (!nodes.length) {
      return {positions, width, height};
    }
    const groups = new Map();
    for (const node of nodes) {
      const rank = nodeTraversalRank(node, traversal);
      if (!groups.has(rank)) groups.set(rank, []);
      groups.get(rank).push(node);
    }
    const ranks = Array.from(groups.keys()).sort((left, right) => left - right);
    const columnWidth = 180;
    const rowHeight = 138;
    const rankGap = 170;
    const left = 120;
    const top = 92;
    const baseWidth = Math.max(width || 900, 640);
    const columnCounts = new Map();
    for (const [rank, group] of groups) {
      columnCounts.set(rank, Math.max(1, Math.ceil(Math.sqrt(group.length))));
    }
    const maxColumns = Math.max(...Array.from(columnCounts.values()));
    const rowCounts = new Map();
    for (const [rank, group] of groups) {
      rowCounts.set(rank, Math.max(1, Math.ceil(group.length / columnCounts.get(rank))));
    }
    const totalRows = Array.from(rowCounts.values()).reduce((sum, rows) => sum + rows, 0);
    const layoutWidth = Math.max(baseWidth, left * 2 + Math.max(0, maxColumns - 1) * columnWidth);
    const layoutHeight = Math.max(
      height || 520,
      top * 2 + Math.max(0, totalRows - 1) * rowHeight + Math.max(0, ranks.length - 1) * (rankGap - rowHeight)
    );
    const usableWidth = Math.max(1, layoutWidth - left * 2);
    let rankTop = top;
    ranks.forEach((rank) => {
      const group = groups.get(rank).slice().sort((leftNode, rightNode) => {
        if (leftNode.id === selectedId) return -1;
        if (rightNode.id === selectedId) return 1;
        return String(leftNode.label || leftNode.id).localeCompare(String(rightNode.label || rightNode.id));
      });
      const cols = Math.min(group.length, columnCounts.get(rank));
      const rows = Math.max(1, Math.ceil(group.length / cols));
      const colGap = cols > 1 ? usableWidth / (cols - 1) : 0;
      group.forEach((node, index) => {
        const colIndex = Math.floor(index / rows);
        const rowIndex = index % rows;
        positions.set(node.id, {
          x: cols > 1 ? left + colIndex * colGap : layoutWidth / 2,
          y: rankTop + rowIndex * rowHeight
        });
      });
      rankTop += Math.max(0, rows - 1) * rowHeight + rankGap;
    });
    return {positions, width: layoutWidth, height: layoutHeight};
  }

  function hierarchyNodePosition(node, graph) {
    const layout = graph.hierarchyLayout;
    if (!layout || !layout.positions) return undefined;
    const position = layout.positions.get(node.id);
    return position ? {x: position.x, y: position.y} : undefined;
  }

  function cytoscapeElements(graph) {
    const nodes = graph.nodes.map((node, index) => ({
      group: "nodes",
      data: {
        id: node.id,
        label: node.label || node.id,
        displayLabel: `${nodeTypeLabel(node)}\n${wrapNodeDisplayLabel(node)}`,
        type: node.type || "entity",
        status: node.status || "unknown"
      },
      position: graph.listMode ? listNodePosition(index, graph) : hierarchyNodePosition(node, graph),
      classes: `${cssStatus(node.status)} ${graph.listMode ? "is-list-item" : ""} ${node.id === graph.selectedId ? "is-selected" : ""} ${node.id === graph.activeId ? "is-active" : ""}`
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

  function syncGraphViewport(state) {
    if (!state.cy) return;
    state.cy.resize();
  }

  function setGraphInteractive(browser, state, interactive) {
    state.graphInteractive = Boolean(interactive);
    state.graphFocusActive = state.graphInteractive;
    syncGraphViewport(state);
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (canvas) {
      canvas.setAttribute("data-graph-interactive", state.graphInteractive ? "true" : "false");
    }
    refreshGraphFocusState(browser, state);
    if (!state.cy) return;
    state.cy.userZoomingEnabled(state.graphInteractive);
    state.cy.userPanningEnabled(state.graphInteractive);
    state.cy.autoungrabify(!state.graphInteractive);
  }

  function activateGraphFocus(browser, state) {
    syncGraphViewport(state);
    if (!state.graphInteractive) {
      setGraphInteractive(browser, state, true);
    }
    state.graphFocusActive = true;
    refreshGraphFocusState(browser, state);
  }

  function releaseGraphFocus(browser, state) {
    const hasActiveGraphFocus = state.graphInteractive || state.graphFocusActive;
    if (!hasActiveGraphFocus) return;
    const active = document.activeElement;
    if (active && typeof active.blur === "function") {
      active.blur();
    }
    setGraphInteractive(browser, state, false);
  }

  function updateGraphPageControls(browser, state, pagination) {
    const page = pagination || {enabled: false, start: 0, end: 0, total: 0, page: 0, pageCount: 1};
    browser.querySelectorAll("[data-relationship-page-controls]").forEach((controls) => {
      const prev = controls.querySelector("[data-relationship-page-prev]");
      const next = controls.querySelector("[data-relationship-page-next]");
      const count = controls.querySelector("[data-relationship-page-count]");
      controls.classList.toggle("is-single-page", !page.enabled);
      if (prev) {
        prev.hidden = !page.enabled;
        prev.disabled = !page.enabled || page.page <= 0;
      }
      if (next) {
        next.hidden = !page.enabled;
        next.disabled = !page.enabled || page.page >= page.pageCount - 1;
      }
      if (count) {
        const rendered = page.rendered == null ? page.total || 0 : page.rendered;
        count.textContent = page.enabled
          ? `${page.start}-${page.end} of ${page.total}`
          : `${rendered} ${rendered === 1 ? "node" : "nodes"}`;
      }
    });
    if (page.enabled && state.graphPage !== page.page) {
      state.graphPage = page.page;
    }
    const focusCount = browser.querySelector("[data-relationship-node-count]");
    if (focusCount) {
      const focusChoices = Number(state.focusChoiceCount || 0);
      focusCount.textContent = page.enabled
        ? `(${page.total} graph, ${focusChoices} focus choices)`
        : `(${page.total || 0} graph, ${focusChoices} focus choices)`;
    }
  }

  function focusHasSecondaryLinks(state) {
    if (!state.selectedId) return false;
    return stateGraphEdges(state).some((edge) =>
      isSecondaryEdge(edge) && (edge.source === state.selectedId || edge.target === state.selectedId)
    );
  }

  function updateSecondaryLinkControl(browser, state) {
    const secondaryLinks = browser.querySelector("[data-relationship-secondary-links]");
    if (!secondaryLinks) return;
    const available = focusHasSecondaryLinks(state);
    secondaryLinks.disabled = !available;
    if (!available && state.showSecondaryLinks) {
      state.showSecondaryLinks = false;
    }
    secondaryLinks.checked = available && state.showSecondaryLinks;
    const label = secondaryLinks.closest(".relationship-secondary-toggle");
    if (label) {
      label.hidden = !available;
      label.title = available ? "Show shortcut links of the current focus" : "";
    }
  }

  function graphRenderSignature(graph) {
    const nodes = (graph.nodes || []).map((node) => node.id).join("\u0001");
    const edges = (graph.edges || []).map((edge) => `${edge.source}\u0002${edge.target}\u0002${edge.relation || ""}`).join("\u0001");
    const layout = graph.listLayout
      ? `${graph.listLayout.cols}:${graph.listLayout.rows}:${graph.listLayout.width}:${graph.listLayout.height}`
      : "";
    const page = graph.pagination
      ? `${graph.pagination.page}:${graph.pagination.start}:${graph.pagination.end}:${graph.pagination.total}`
      : "";
    return `${graph.selectedId || ""}\u0003${graph.listMode ? "1" : "0"}\u0003${page}\u0003${layout}\u0004${nodes}\u0005${edges}`;
  }

  function renderGraph(browser, state) {
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (!canvas || !state.selectedId) return;
    browser.classList.add("is-graph-ready");
    browser.setAttribute("data-relationship-graph-ready", "true");
    refreshGraphActivityState(browser, state);
    if (typeof cytoscape !== "function") {
      canvas.textContent = "Cytoscape.js is not available.";
      return;
    }
    const hasSearch = String(state.searchQuery || "").trim();
    updateSecondaryLinkControl(browser, state);
    const nodeVisible = (node) => isNodeVisible(node, state);
    const contextNodeVisible = (node) => nodeInScope(state, node);
    const graphEdges = stateGraphEdges(state);
    const graphAdjacency = stateGraphAdjacency(state);
    const baseGraph = buildTypeListGraph(state) || buildNeighborhood(
      state.selectedId,
      state.nodesById,
      graphEdges,
      graphAdjacency,
      nodeVisible,
      contextNodeVisible,
      activeTraversal(state),
      state.showSecondaryLinks
    );
    const focusGraph = graphMatchesSearch(baseGraph, state.searchQuery, state);
    state.focusGraph = focusGraph;
    state.focusContent = focusContent(state);
    const graph = capGraph(focusGraph, state.selectedId, hasSearch ? 0 : 50, state.graphPage);
    updateGraphPageControls(browser, state, graph.pagination);
    if (!graph.nodes.some((node) => node.id === state.activeId)) {
      state.activeId = graph.nodes.some((node) => node.id === state.selectedId)
        ? state.selectedId
        : (graph.nodes[0] && graph.nodes[0].id) || state.selectedId;
    }
    graph.selectedId = state.selectedId;
    graph.activeId = state.activeId;
    state.visibleGraph = graph;
    state.visibleNodeIds = new Set(graph.nodes.map((node) => node.id));
    syncActiveSubfilterType(state);
    const typeContainer = browser.querySelector("[data-relationship-projection-controls]");
    if (typeContainer) refreshTypeFilterState(typeContainer, state, stateGraphTypes(state));
    const listColumnWidth = 220;
    const listRowHeight = 150;
    canvas.style.height = "";
    if (graph.listMode) {
      const boxWidth = canvas.clientWidth || 900;
      const listColumns = Math.max(1, Math.min(6, Math.floor(boxWidth / listColumnWidth)));
      const listRows = Math.max(1, Math.ceil(Math.max(graph.nodes.length, 1) / listColumns));
      graph.listLayout = {
        cols: listColumns,
        rows: listRows,
        width: boxWidth,
        height: Math.max(canvas.clientHeight || 520, listRows * listRowHeight),
        left: 120,
        top: 92
      };
      graph.hierarchyLayout = null;
    } else {
      graph.listLayout = null;
      graph.hierarchyLayout = buildHierarchicalLayout(
        graph.nodes,
        canvas.clientWidth || 900,
        canvas.clientHeight || 520,
        state.selectedId,
        activeTraversal(state)
      );
    }
    const renderSignature = graphRenderSignature(graph);
    if (state.cy && state.graphRenderSignature === renderSignature) {
      updateActiveGraphNode(state);
      renderSelectionTable(browser, state);
      updateActiveTableRow(browser, state);
      syncGraphViewport(state);
      return;
    }
    state.graphRenderSignature = renderSignature;
    if (state.cy) {
      state.cy.destroy();
      state.cy = null;
    }
    canvas.replaceChildren();
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
    if (!state.canvasViewportListenersAttached) {
      canvas.addEventListener("pointerenter", () => syncGraphViewport(state), {passive: true});
      canvas.addEventListener("pointerdown", () => syncGraphViewport(state), {capture: true, passive: true});
      state.canvasViewportListenersAttached = true;
    }
    state.cy.on("tap", "node", (event) => {
      activateGraphFocus(browser, state);
      const nodeId = event.target.id();
      selectNode(browser, state, nodeId, true);
    });
    if (!graph.nodes.length) {
      canvas.setAttribute("data-empty-graph", "true");
      canvas.setAttribute("data-graph-message", hasSearch ? "No matching nodes in the current neighborhood." : "No entity types selected.");
      renderSelectionTable(browser, state);
      return;
    }
    canvas.removeAttribute("data-empty-graph");
    const hiddenByFilters = hiddenByFiltersCount(state);
    if (graph.nodes.length <= 1 && hiddenByFilters > 0) {
      canvas.setAttribute(
        "data-graph-message",
        `Only the focus is drawn: ${hiddenByFilters} nodes of the enabled layers are hidden by the status filter or the filter values.`
      );
      canvas.setAttribute("data-graph-hint", "filtered");
    } else if (graph.omitted) {
      canvas.removeAttribute("data-graph-hint");
      canvas.setAttribute("data-graph-message", `${graph.omitted} more nodes hidden. Use search or entity filters to narrow the graph.`);
    } else {
      canvas.removeAttribute("data-graph-hint");
      canvas.removeAttribute("data-graph-message");
    }
    const presetPositions = (graph.listMode || graph.hierarchyLayout)
      ? new Map(graph.nodes.map((node, index) => [
        node.id,
        graph.listMode ? listNodePosition(index, graph) : hierarchyNodePosition(node, graph)
      ]))
      : null;
    const layoutOptions = presetPositions ? {
      name: "preset",
      positions: (node) => presetPositions.get(node.id()) || {x: 0, y: 0},
      animate: false,
      fit: true,
      padding: 54
    } : {
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
    };
    const layout = state.cy.layout(layoutOptions);
    layout.run();
    if (presetPositions) {
      state.cy.nodes().forEach((node) => {
        const position = presetPositions.get(node.id());
        if (position) node.position(position);
      });
    }
    const selected = state.cy.getElementById(state.selectedId);
    if (selected.length) selected.select();
    renderSelectionTable(browser, state);
    fitGraph(state, 40);
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
    const seen = new Set();
    const addEdge = (edge) => {
      if (isSecondaryEdge(edge) && !state.showSecondaryLinks) return;
      let relatedId = "";
      let direction = "";
      if (edge.source === nodeId) {
        relatedId = edge.target;
        direction = "out";
      } else if (edge.target === nodeId) {
        relatedId = edge.source;
        direction = "in";
      } else {
        return;
      }
      const node = state.nodesById.get(relatedId);
      if (!node) return;
      if (!isNodeVisible(node, state)) return;
      const relation = edge.relation || "related_to";
      const key = direction === "out" ? relation : `${relation} (incoming)`;
      const dedupeKey = `${key}\u0000${relatedId}`;
      if (seen.has(dedupeKey)) return;
      seen.add(dedupeKey);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    };
    const visibleGraph = state.visibleGraph || {edges: []};
    for (const edge of visibleGraph.edges || []) {
      addEdge(edge);
    }
    for (const edge of stateGraphEdges(state)) {
      addEdge(edge);
    }
    return groups;
  }

  function focusRequiredTypes(state, nodeId) {
    const required = new Set();
    const selected = state.nodesById.get(nodeId);
    if (!selected) return required;
    const rankOf = (node) => {
      if (!node) return 99;
      const ranks = state.traversal && state.traversal.typeRanks || DEFAULT_TYPE_RANKS;
      const value = ranks[node.type || "entity"];
      return Number.isFinite(value) ? value : typeRank(node);
    };
    const neighbors = (id) => {
      const result = [];
      for (const edge of stateGraphEdges(state)) {
        if (isSecondaryEdge(edge) && !state.showSecondaryLinks) continue;
        if (edge.source === id) {
          result.push({id: edge.target, edge});
        } else if (edge.target === id) {
          result.push({id: edge.source, edge});
        }
      }
      return result;
    };
    const sortParent = (left, right) => {
      const leftNode = state.nodesById.get(left.id);
      const rightNode = state.nodesById.get(right.id);
      const leftRank = rankOf(leftNode);
      const rightRank = rankOf(rightNode);
      const leftDirected = left.edge.source === left.id && left.edge.target === left.currentId;
      const rightDirected = right.edge.source === right.id && right.edge.target === right.currentId;
      if (leftDirected !== rightDirected) return leftDirected ? -1 : 1;
      if (leftRank !== rightRank) return leftRank - rightRank;
      return String(leftNode && (leftNode.label || leftNode.id) || left.id).localeCompare(String(rightNode && (rightNode.label || rightNode.id) || right.id));
    };
    let currentId = nodeId;
    const seen = new Set();
    while (currentId && !seen.has(currentId)) {
      seen.add(currentId);
      const current = state.nodesById.get(currentId);
      if (!current) break;
      required.add(current.type || "entity");
      const currentRank = rankOf(current);
      const parent = neighbors(currentId)
        .filter((item) => {
          const node = state.nodesById.get(item.id);
          return node && !seen.has(item.id) && rankOf(node) < currentRank;
        })
        .map((item) => Object.assign({currentId}, item))
        .sort(sortParent)[0];
      currentId = parent ? parent.id : "";
    }
    return required;
  }

  function typeRankValue(state, type) {
    const ranks = state && state.traversal && state.traversal.typeRanks || DEFAULT_TYPE_RANKS;
    const value = ranks[type || "entity"];
    if (Number.isFinite(value)) return value;
    const index = TYPE_ORDER.indexOf(type || "entity");
    return index === -1 ? 99 : index;
  }

  function projectionRankGroups(state) {
    const byRank = new Map();
    for (const type of stateGraphTypes(state)) {
      const rank = typeRankValue(state, type);
      if (!byRank.has(rank)) byRank.set(rank, []);
      byRank.get(rank).push(type);
    }
    return Array.from(byRank.entries())
      .sort((left, right) => left[0] - right[0])
      .map(([rank, types], index) => ({
        id: String(rank),
        rank,
        index,
        label: index === 0 ? "Start" : `Level ${index}`,
        types: types.sort((left, right) => {
          const leftOrder = TYPE_ORDER.indexOf(left);
          const rightOrder = TYPE_ORDER.indexOf(right);
          if (leftOrder !== -1 || rightOrder !== -1) return (leftOrder === -1 ? 999 : leftOrder) - (rightOrder === -1 ? 999 : rightOrder);
          return String(TYPE_LABELS[left] || left).localeCompare(String(TYPE_LABELS[right] || right));
        })
      }));
  }

  function defaultProjectionSelections(state) {
    const result = {};
    for (const group of projectionRankGroups(state)) {
      result[group.id] = "__all__";
    }
    return result;
  }

  function encodeProjectionChoice(types) {
    return types.slice().sort().join("\u001f");
  }

  function decodeProjectionChoice(choice, groupTypes) {
    if (choice === "__none__") return [];
    if (choice === "__all__" || !choice) return groupTypes.slice();
    const allowed = new Set(groupTypes);
    return String(choice).split("\u001f").filter((type) => allowed.has(type));
  }

  function projectionSelectedTypesForGroup(state, group) {
    const auto = (state.projectionMode || "auto") === "auto";
    const choice = auto ? "__all__" : (state.projectionSelections && state.projectionSelections[group.id] || "__all__");
    return new Set(decodeProjectionChoice(choice, group.types));
  }

  function projectionSelectionValue(group, selected) {
    const chosen = group.types.filter((type) => selected.has(type));
    if (!chosen.length) return "__none__";
    if (chosen.length === group.types.length) return "__all__";
    return encodeProjectionChoice(chosen);
  }

  function setProjectionGroupSelection(state, group, selected) {
    const next = new Set(selected || []);
    const required = requiredProjectionTypeForRank(state, group.rank);
    if (required && group.types.includes(required)) next.add(required);
    if (!state.projectionSelections) state.projectionSelections = {};
    state.projectionSelections[group.id] = projectionSelectionValue(group, next);
  }

  function projectionSelectionLabel(state, group) {
    const selected = projectionSelectedTypesForGroup(state, group);
    if (!selected.size) return "None";
    if (selected.size === group.types.length) return "All";
    const labels = group.types
      .filter((type) => selected.has(type))
      .map((type) => TYPE_LABELS[type] || type);
    if (labels.length <= 2) return labels.join(" + ");
    return `${labels.length} selected`;
  }

  function projectionTypesFromSelections(state) {
    const selected = new Set();
    const selections = state.projectionSelections || {};
    for (const group of projectionRankGroups(state)) {
      const choice = selections[group.id] || "__all__";
      for (const type of decodeProjectionChoice(choice, group.types)) selected.add(type);
    }
    return selected;
  }

  function setProjectionSelectionsFromTypes(state, types) {
    const selected = new Set(types || []);
    const next = {};
    for (const group of projectionRankGroups(state)) {
      const chosen = group.types.filter((type) => selected.has(type));
      if (!chosen.length) {
        next[group.id] = "__none__";
      } else if (chosen.length === group.types.length) {
        next[group.id] = "__all__";
      } else {
        next[group.id] = encodeProjectionChoice(chosen);
      }
    }
    state.projectionSelections = next;
  }

  function applyProjectionSelections(browser, state) {
    state.enabledTypes = projectionTypesFromSelections(state);
    refreshGraphControlState(browser, state);
  }

  function ensureFocusFilters(browser, state, nodeId) {
    const node = state.nodesById.get(nodeId);
    const type = node && (node.type || "entity");
    if (!type || state.enabledTypes.has(type)) return false;
    state.enabledTypes.add(type);
    if (state.projectionMode === "custom") {
      const group = projectionRankGroups(state).find((item) => item.types.includes(type));
      if (group) {
        const current = state.projectionSelections && state.projectionSelections[group.id] || "__all__";
        const selected = new Set(decodeProjectionChoice(current, group.types));
        selected.add(type);
        if (!state.projectionSelections) state.projectionSelections = {};
        state.projectionSelections[group.id] = selected.size === group.types.length
          ? "__all__"
          : encodeProjectionChoice(group.types.filter((candidate) => selected.has(candidate)));
      }
    }
    refreshGraphControlState(browser, state);
    return true;
  }

  function focusViewTypes(state, nodeId) {
    const fallback = focusRequiredTypes(state, nodeId);
    if (!state.nodesById.has(nodeId)) return fallback;
    const allTypes = new Set(stateGraphTypes(state));
    const graphEdges = stateGraphEdges(state);
    const focusState = Object.assign({}, state, {
      selectedId: nodeId,
      enabledTypes: allTypes
    });
    const graph = buildNeighborhood(
      nodeId,
      state.nodesById,
      graphEdges,
      stateGraphAdjacency(state),
      (node) => node && (node.id === nodeId || isSubfilterEnabled(node, state)),
      (node) => Boolean(node),
      activeTraversal(focusState),
      state.showSecondaryLinks
    );
    const types = new Set((graph.nodes || []).map((node) => node.type || "entity"));
    return types.size ? types : fallback;
  }

  function resetEntityTypesToFocusView(browser, state, nodeId) {
    state.enabledTypes = focusViewTypes(state, nodeId);
    state.projectionMode = "auto";
    state.projectionSelections = defaultProjectionSelections(state);
    refreshGraphControlState(browser, state);
  }

  function enableAllEntityTypes(browser, state) {
    const types = stateGraphTypes(state);
    state.enabledTypes = new Set(types);
    state.projectionMode = "custom";
    state.projectionSelections = defaultProjectionSelections(state);
    refreshGraphControlState(browser, state, types);
  }

  function relationshipControls(browser) {
    return browser.querySelector("[data-relationship-projection-controls]") || browser;
  }

  function refreshGraphControlState(browser, state, types) {
    refreshTypeFilterState(relationshipControls(browser), state, types || stateGraphTypes(state));
  }

  function resetGraphFilters(browser, state) {
    state.enabledTypes = new Set(stateGraphTypes(state));
    state.projectionMode = "auto";
    state.projectionSelections = defaultProjectionSelections(state);
    resetSubfilters(state);
    state.activeSubfilterType = "";
    state.activeSubfilterTypes = [];
    state.typeSearchType = "";
    refreshGraphControlState(browser, state);
  }

  function resetGraphFiltersToAll(browser, state) {
    const nodes = stateGraphNodes(state);
    state.enabledTypes = new Set(stateGraphTypes(state));
    state.projectionMode = "auto";
    state.projectionSelections = defaultProjectionSelections(state);
    state.subfilters = createSubfilters(nodes, {});
    state.statusFilter = createStatusFilter(nodes, {});
    state.activeSubfilterType = "";
    state.activeSubfilterTypes = [];
    state.typeSearchType = "";
    state.graphPage = 0;
    refreshGraphControlState(browser, state);
  }

  function childLayerSubfilterTypes(state) {
    const graph = state.visibleGraph;
    const selected = state.nodesById.get(state.selectedId || "");
    if (!graph || !selected) return [];
    const selectedRank = typeRank(selected);
    const candidates = graph.nodes.filter((node) => {
      if (!node || node.id === selected.id) return false;
      const distance = graph.distances && graph.distances.get(node.id);
      return distance != null && distance > 0 && typeRank(node) > selectedRank;
    });
    if (!candidates.length) return [];
    const nearestRank = Math.min(...candidates.map((node) => typeRank(node)));
    const seen = new Set(candidates
      .filter((node) => typeRank(node) === nearestRank)
      .map((node) => node.type || "entity"));
    return stateGraphTypes(state).filter((type) => seen.has(type));
  }

  function syncActiveSubfilterType(state) {
    const active = state.nodesById.get(state.activeId || "");
    let types = [];
    if (active && active.id !== state.selectedId) {
      types = [active.type || "entity"];
    } else {
      types = childLayerSubfilterTypes(state);
      if (!types.length && active) types = [active.type || "entity"];
    }
    state.activeSubfilterTypes = types;
    state.activeSubfilterType = types[0] || "";
  }

  function allEntityTypesEnabled(state) {
    const types = stateGraphTypes(state);
    return types.length > 0 && types.every((type) => state.enabledTypes.has(type));
  }

  function allStatusesEnabled(state) {
    const filter = state.statusFilter;
    return Boolean(filter && filter.values && filter.values.length)
      && filter.values.every((value) => filter.enabled && filter.enabled.has(value));
  }

  function allProjectionLevelsSelected(state) {
    const selections = Object.values(state.projectionSelections || {});
    return selections.length > 0 && selections.every((value) => value === "__all__");
  }

  function graphViewIsActive(state) {
    return Boolean(
      state.activeViewPinned ||
      state.selectedId !== state.rootId ||
      state.activeId !== state.selectedId ||
      state.isolatedRootId ||
      state.searchQuery ||
      state.typeSearchType ||
      state.showSecondaryLinks ||
      state.graphPage > 0 ||
      !allEntityTypesEnabled(state) ||
      !allStatusesEnabled(state) ||
      !allProjectionLevelsSelected(state)
    );
  }

  function refreshGraphActivityState(browser, state) {
    const active = graphViewIsActive(state);
    browser.classList.toggle("is-graph-active", active);
    browser.setAttribute("data-relationship-active-view", active ? "true" : "false");
  }

  function refreshGraphFocusState(browser, state) {
    const focused = Boolean(state.graphFocusActive);
    browser.classList.toggle("is-graph-focused", focused);
    browser.setAttribute("data-relationship-graph-focused", focused ? "true" : "false");
    browser.querySelectorAll("[data-relationship-focus-badge]").forEach((badge) => {
      badge.hidden = !focused;
    });
  }

  function projectionSelectionsSnapshot(state) {
    return Object.assign({}, state.projectionSelections || {});
  }

  function navigationSnapshot(state) {
    return {
      selectedId: state.selectedId,
      activeId: state.activeId,
      enabledTypes: Array.from(state.enabledTypes),
      projectionMode: state.projectionMode || "auto",
      projectionSelections: projectionSelectionsSnapshot(state),
      subfilters: serializeSubfilters(state),
      statusFilter: serializeStatusFilter(state),
      graphPage: state.graphPage,
      showSecondaryLinks: state.showSecondaryLinks,
      searchQuery: state.searchQuery,
      typeSearchType: state.typeSearchType,
      isolatedRootId: state.isolatedRootId || "",
      activeViewPinned: Boolean(state.activeViewPinned)
    };
  }

  function pushNavigationSnapshot(state) {
    state.backStack.push(navigationSnapshot(state));
    state.forwardStack.length = 0;
  }

  function restoreNavigationSnapshot(browser, state, snapshot) {
    if (!snapshot) return;
    if (typeof snapshot === "string") {
      snapshot = {selectedId: snapshot, activeId: snapshot};
    }
    setIsolatedRoot(state, snapshot.isolatedRootId || "");
    if (!state.nodesById.has(snapshot.selectedId)) return;
    if (state.isolatedNodeIds && !state.isolatedNodeIds.has(snapshot.selectedId)) return;
    state.selectedId = snapshot.selectedId;
    state.activeId = state.nodesById.has(snapshot.activeId) ? snapshot.activeId : snapshot.selectedId;
    syncActiveSubfilterType(state);
    state.enabledTypes = new Set(Array.isArray(snapshot.enabledTypes) ? snapshot.enabledTypes : stateGraphTypes(state));
    state.projectionMode = snapshot.projectionMode === "custom" ? "custom" : "auto";
    state.projectionSelections = snapshot.projectionSelections && typeof snapshot.projectionSelections === "object"
      ? Object.assign({}, snapshot.projectionSelections)
      : defaultProjectionSelections(state);
    resetSubfilters(state);
    restoreSubfilters(state, snapshot.subfilters);
    restoreStatusFilter(state, snapshot.statusFilter);
    state.graphPage = Number(snapshot.graphPage) || 0;
    state.showSecondaryLinks = Boolean(snapshot.showSecondaryLinks);
    state.searchQuery = snapshot.searchQuery || "";
    state.typeSearchType = snapshot.typeSearchType || "";
    state.activeViewPinned = Boolean(snapshot.activeViewPinned);
    refreshGraphControlState(browser, state);
    renderRelationshipState(browser, state);
  }

  function serializeStatusFilter(state) {
    return Array.from((state.statusFilter && state.statusFilter.enabled) || []);
  }

  function restoreStatusFilter(state, snapshot) {
    if (!state.statusFilter || !Array.isArray(snapshot)) return;
    state.statusFilter.enabled = new Set(snapshot.map(String).filter((value) => state.statusFilter.values.includes(value)));
  }

  function serializeSubfilters(state) {
    const result = {};
    for (const [type, typeFilters] of Object.entries(state.subfilters || {})) {
      result[type] = {};
      for (const [field, config] of Object.entries(typeFilters)) {
        result[type][field] = Array.from(config.enabled || []);
      }
    }
    return result;
  }

  function restoreSubfilters(state, snapshot) {
    if (!snapshot || typeof snapshot !== "object") return;
    for (const [type, typeFilters] of Object.entries(snapshot)) {
      if (!state.subfilters[type] || typeof typeFilters !== "object") continue;
      for (const [field, values] of Object.entries(typeFilters)) {
        const config = state.subfilters[type][field];
        if (!config || !Array.isArray(values)) continue;
        config.enabled = new Set(values.map(String).filter((value) => config.values.includes(value)));
      }
    }
  }

  function renderFailureStats(stats) {
    if (!stats || typeof stats !== "object") return "";
    const summary = stats.module_summary && typeof stats.module_summary === "object" ? stats.module_summary : {};
    const clusters = Array.isArray(stats.failure_clusters) ? stats.failure_clusters : [];
    const cases = Array.isArray(stats.representative_cases) ? stats.representative_cases : [];
    if (!Object.keys(summary).length && !clusters.length && !cases.length) return "";
    let html = '<div class="relationship-failure-stats">';
    html += '<h4>Failed Test Statistics</h4>';
    if (Object.keys(summary).length) {
      const fields = ["suite", "module", "domain", "status", "pass", "failed", "skipped", "total"];
      html += '<table><tbody>';
      for (const field of fields) {
        if (summary[field] == null || String(summary[field]).trim() === "") continue;
        html += `<tr><th>${esc(field.replaceAll("_", " "))}</th><td>${esc(summary[field])}</td></tr>`;
      }
      html += '</tbody></table>';
    }
    if (clusters.length) {
      html += '<section><h5>Result clusters</h5><div class="relationship-failure-list">';
      for (const cluster of clusters) {
        const resultLabel = cluster.result || "failed";
        html += '<article>';
        html += `<strong>${esc(cluster.family || "cluster")}</strong>`;
        html += `<small>${esc(cluster.failed_count || "0")} ${esc(resultLabel)}</small>`;
        if (cluster.sample_case) html += `<p>${esc(cluster.sample_case)}</p>`;
        if (cluster.sample_message) html += `<code>${esc(cluster.sample_message)}</code>`;
        html += '</article>';
      }
      html += '</div></section>';
    }
    if (cases.length) {
      html += '<section><h5>Representative cases</h5><div class="relationship-failure-list">';
      for (const testCase of cases) {
        html += '<article>';
        html += `<strong>${esc(testCase.test || "test case")}</strong>`;
        const resultLabel = testCase.result ? `${testCase.family || ""} · ${testCase.result}` : testCase.family;
        if (resultLabel) html += `<small>${esc(resultLabel)}</small>`;
        if (testCase.details) html += `<code>${esc(testCase.details)}</code>`;
        html += '</article>';
      }
      html += '</div></section>';
    }
    html += '</div>';
    return html;
  }

  function renderDetail(browser, state) {
    const detail = browser.querySelector("[data-relationship-detail]");
    const nodeId = state.activeId || state.selectedId;
    if (!detail || !nodeId) return;
    const node = state.nodesById.get(nodeId);
    if (!node) return;
    if (!isNodeVisible(node, state)) {
      detail.innerHTML = "<p>No entity types selected. Enable at least one type or use All.</p>";
      return;
    }
    if (state.searchQuery && !searchableTextForState(state, node).includes(String(state.searchQuery).trim().toLowerCase())) {
      detail.innerHTML = "<p>The selected node is outside the current search filter. Pick a matching Focus item or clear the search.</p>";
      return;
    }
    const details = node.details && typeof node.details === "object" ? node.details : {};
    const groups = relatedGroups(node.id, state);
    const detailRows = orderedDetailRows(node, details);
    let html = `<div class="relationship-detail-head"><span class="relationship-node-pill">${esc(nodeTypeLabel(node))}</span>`;
    html += `<span class="report-status-badge ${cssStatus(node.status)}">${esc(node.status || "unknown")}</span></div>`;
    html += `<h3>${esc(node.label || node.id)}</h3>`;
    if (node.summary) html += `<p>${esc(node.summary)}</p>`;
    if (detailRows.length) {
      html += '<dl class="relationship-detail-fields">';
      for (const [key, value] of detailRows) {
        html += `<dt>${esc(detailFieldLabel(key))}</dt><dd>${esc(value)}</dd>`;
      }
      html += "</dl>";
    }
    html += renderFailureStats(node.failure_stats);
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

  function renderRelationshipState(browser, state) {
    const startedAt = performance.now();
    refreshGraphActivityState(browser, state);
    renderGraph(browser, state);
    renderNodeSelect(browser, state);
    renderDetail(browser, state);
    const durationMs = performance.now() - startedAt;
    state.renderVersion = Number(state.renderVersion || 0) + 1;
    state.lastRenderDurationMs = durationMs;
    if (!Array.isArray(state.renderSamples)) state.renderSamples = [];
    state.renderSamples.push({
      version: state.renderVersion,
      durationMs,
      selectedId: state.selectedId,
      nodes: state.visibleGraph && state.visibleGraph.nodes ? state.visibleGraph.nodes.length : 0,
      edges: state.visibleGraph && state.visibleGraph.edges ? state.visibleGraph.edges.length : 0
    });
    if (state.renderSamples.length > 80) {
      state.renderSamples.splice(0, state.renderSamples.length - 80);
    }
  }

  function updateSelectedNodeState(browser, state, nodeId, recordHistory, options) {
    if (!state.nodesById.has(nodeId)) return;
    if (state.isolatedNodeIds && !state.isolatedNodeIds.has(nodeId)) return;
    const resetTypes = Boolean(options && options.resetTypes);
    const preserveFilters = Boolean(options && options.preserveFilters);
    const entityChanged = Boolean(state.selectedId && state.selectedId !== nodeId);
    const resetFiltersToAll = entityChanged && !preserveFilters;
    let preserveTypes = options && Object.prototype.hasOwnProperty.call(options, "preserveTypes")
      ? Boolean(options.preserveTypes)
      : (state.projectionMode || "auto") === "custom";
    if (recordHistory && state.selectedId && state.selectedId !== nodeId) {
      state.backStack.push(navigationSnapshot(state));
      state.forwardStack.length = 0;
    }
    if (resetFiltersToAll) {
      preserveTypes = true;
    } else if (resetTypes) {
      enableAllEntityTypes(browser, state);
    }
    state.selectedId = nodeId;
    state.activeId = nodeId;
    syncActiveSubfilterType(state);
    state.graphPage = 0;
    includeNodeInSubfilters(state, state.nodesById.get(nodeId));
    if (!preserveTypes) {
      resetEntityTypesToFocusView(browser, state, nodeId);
    } else {
      ensureFocusFilters(browser, state, nodeId);
    }
    if (resetFiltersToAll) {
      resetGraphFiltersToAll(browser, state);
      ensureFocusFilters(browser, state, nodeId);
    }
    return true;
  }

  function selectNode(browser, state, nodeId, recordHistory, options) {
    if (!updateSelectedNodeState(browser, state, nodeId, recordHistory, options)) return;
    renderRelationshipState(browser, state);
  }

  function selectTableNode(browser, state, nodeId) {
    if (!state.nodesById.has(nodeId)) return;
    if (state.selectedId !== nodeId || !allEntityTypesEnabled(state)) {
      pushNavigationSnapshot(state);
    }
    resetGraphFiltersToAll(browser, state);
    selectNode(browser, state, nodeId, false, {preserveTypes: true, preserveFilters: true});
  }

  function updateActiveGraphNode(state) {
    if (!state.cy) return;
    state.cy.nodes().removeClass("is-active");
    const active = state.cy.getElementById(state.activeId || "");
    if (active.length) active.addClass("is-active");
  }

  function refreshGraphTheme(state) {
    if (!state.cy) return;
    cachedCytoscapeStyle = null;
    cachedCytoscapeStyleTheme = "";
    state.cy.style(cytoscapeStyle());
    state.cy.resize();
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
    syncActiveSubfilterType(state);
    updateActiveGraphNode(state);
    updateActiveTableRow(browser, state);
    refreshGraphControlState(browser, state);
    renderNodeSelect(browser, state);
    renderDetail(browser, state);
    refreshGraphActivityState(browser, state);
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

  function searchableTextForState(state, node) {
    if (!node) return "";
    if (!state.searchTextById) state.searchTextById = new Map();
    if (!state.searchTextById.has(node.id)) {
      state.searchTextById.set(node.id, searchableText(node));
    }
    return state.searchTextById.get(node.id) || "";
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

  function focusChoiceRank(node, state) {
    if (!node) return 9;
    if (node.id === state.selectedId) return 0;
    if ((node.type || "entity") === "product") return 1;
    const selected = state.nodesById.get(state.selectedId || "");
    if (selected && (node.type || "entity") === (selected.type || "entity")) return 2;
    const targetType = state.typeSearchType || "";
    if (targetType && (node.type || "entity") === targetType) return 3;
    return 4;
  }

  function focusChoiceGroupKey(node, state, degrees) {
    const rank = focusChoiceRank(node, state);
    const degree = degrees && degrees.get(node.id) || 0;
    if (rank === 0) return "00:selected";
    if (rank === 1) return "01:product";
    if (rank === 2) return `02:${node.type || "entity"}`;
    if (rank === 3) return `03:${node.type || "entity"}`;
    return `04:${node.type || "entity"}:${degree ? "linked" : "isolated"}`;
  }

  function focusChoiceGroupLabel(node, state, degrees, count) {
    const rank = focusChoiceRank(node, state);
    const degree = degrees && degrees.get(node.id) || 0;
    const suffix = `(${count || 0})`;
    if (rank === 0) return `Selected element ${suffix}`;
    if (rank === 1) return `Product / root ${suffix}`;
    if (rank === 2) return `${nodeTypeLabel(node)} · current focus type ${suffix}`;
    if (rank === 3) return `${nodeTypeLabel(node)} · focus target ${suffix}`;
    return `${nodeTypeLabel(node)} · ${degree ? "linked" : "no visible links"} ${suffix}`;
  }

  function isPinnedFocusChoice(node, state, query) {
    if (!node || query) return false;
    if (node.id === state.selectedId) return true;
    if ((node.type || "entity") === "product") return true;
    const selected = state.nodesById.get(state.selectedId || "");
    return Boolean(selected && (node.type || "entity") === (selected.type || "entity"));
  }

  function visibleNodeDegreeMap(state) {
    const visibleIds = new Set();
    for (const node of stateGraphNodes(state)) {
      if (isNodeVisible(node, state)) visibleIds.add(node.id);
    }
    const degrees = new Map();
    for (const edge of stateGraphEdges(state)) {
      if (isSecondaryEdge(edge) && !state.showSecondaryLinks) continue;
      if (visibleIds.has(edge.source) && visibleIds.has(edge.target)) {
        degrees.set(edge.source, (degrees.get(edge.source) || 0) + 1);
        degrees.set(edge.target, (degrees.get(edge.target) || 0) + 1);
      }
    }
    // Nodes drawn right now are judged by the edges the canvas really shows, which include the
    // derived links that stand in for hidden layers; otherwise a focus whose own layer is hidden
    // would be reported as having no links while the canvas clearly draws them.
    const graph = state.visibleGraph;
    if (graph && Array.isArray(graph.nodes) && Array.isArray(graph.edges)) {
      const rendered = new Map();
      for (const node of graph.nodes) rendered.set(node.id, 0);
      for (const edge of graph.edges) {
        if (rendered.has(edge.source)) rendered.set(edge.source, rendered.get(edge.source) + 1);
        if (rendered.has(edge.target)) rendered.set(edge.target, rendered.get(edge.target) + 1);
      }
      for (const [id, degree] of rendered) degrees.set(id, degree);
    }
    return degrees;
  }

  function visibleNodeDegree(node, state, degrees) {
    if (!node || !isNodeVisible(node, state)) return 0;
    return (degrees || visibleNodeDegreeMap(state)).get(node.id) || 0;
  }

  function graphRootId(state) {
    let rootId = "";
    let rootRank = Infinity;
    for (const node of stateGraphNodes(state)) {
      const rank = traversalRank(state, node);
      if (rank >= rootRank) continue;
      rootRank = rank;
      rootId = node.id;
    }
    return rootId;
  }

  function focusAncestorIds(state) {
    const ids = new Set();
    let currentId = state.selectedId || "";
    const seen = new Set();
    while (currentId && !seen.has(currentId)) {
      seen.add(currentId);
      const current = state.nodesById.get(currentId);
      if (!current) break;
      const currentRank = traversalRank(state, current);
      let parentId = "";
      let parentRank = 99;
      for (const item of stateGraphAdjacency(state).get(currentId) || []) {
        if (item.edge.target !== currentId || item.edge.source !== item.id) continue;
        if (isSecondaryEdge(item.edge) && !state.showSecondaryLinks) continue;
        const node = state.nodesById.get(item.id);
        if (!node || seen.has(item.id)) continue;
        const rank = traversalRank(state, node);
        if (rank >= currentRank) continue;
        if (!parentId || rank < parentRank) {
          parentId = item.id;
          parentRank = rank;
        }
      }
      if (!parentId) break;
      ids.add(parentId);
      currentId = parentId;
    }
    return ids;
  }

  function focusScopeIds(state) {
    if (!state.focusInGraphOnly) return null;
    const graph = state.visibleGraph;
    if (!graph || !Array.isArray(graph.nodes)) return null;
    const scope = new Set(graph.nodes.map((node) => node.id));
    if (state.selectedId) scope.add(state.selectedId);
    for (const id of focusAncestorIds(state)) scope.add(id);
    return scope;
  }

  function selectableNodes(state, includeSelected, degrees) {
    const query = String(state.searchQuery || "").trim().toLowerCase();
    const scopeIds = focusScopeIds(state);
    const degreeMap = degrees || visibleNodeDegreeMap(state);
    return stateGraphNodes(state)
      .filter((node) => !scopeIds || node.id === state.selectedId || scopeIds.has(node.id))
      .filter((node) => {
        if (includeSelected && node.id === state.selectedId) return isNodeVisible(node, state);
        return isNodeVisible(node, state);
      })
      .filter((node) => isPinnedFocusChoice(node, state, query) || !query || searchableTextForState(state, node).includes(query))
      .sort((left, right) => {
        const leftGroup = focusChoiceGroupKey(left, state, degreeMap);
        const rightGroup = focusChoiceGroupKey(right, state, degreeMap);
        return leftGroup.localeCompare(rightGroup) ||
          searchRank(left, query) - searchRank(right, query) ||
          String(left.label || left.id).localeCompare(String(right.label || right.id));
      });
  }

  function renderNodeSelect(browser, state) {
    const select = browser.querySelector("[data-relationship-node-select]");
    if (!select) return [];
    const includeSelected = !String(state.searchQuery || "").trim();
    const degrees = visibleNodeDegreeMap(state);
    const nodes = selectableNodes(state, includeSelected, degrees);
    state.focusChoiceCount = nodes.length;
    const count = browser.querySelector("[data-relationship-node-count]");
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
    const renderedNodes = nodes.slice(0, MAX_FOCUS_OPTIONS);
    const selectedNode = includeSelected ? state.nodesById.get(state.selectedId || "") : null;
    if (selectedNode && !renderedNodes.some((node) => node.id === selectedNode.id)) {
      renderedNodes.push(selectedNode);
    }
    const groupCounts = new Map();
    for (const node of renderedNodes) {
      const key = focusChoiceGroupKey(node, state, degrees);
      groupCounts.set(key, (groupCounts.get(key) || 0) + 1);
    }
    const groups = new Map();
    for (const node of renderedNodes) {
      const degree = degrees.get(node.id) || 0;
      const key = focusChoiceGroupKey(node, state, degrees);
      const label = focusChoiceGroupLabel(node, state, degrees, groupCounts.get(key) || 0);
      if (!groups.has(label)) {
        const group = document.createElement("optgroup");
        group.label = label;
        groups.set(label, group);
        select.appendChild(group);
      }
      const option = document.createElement("option");
      option.value = node.id;
      const optionLabel = shortText(node.label || node.id, 90);
      option.textContent = degree ? optionLabel : `${optionLabel} · no visible links`;
      option.title = node.label || node.id;
      option.className = degree ? "" : "relationship-option-isolated";
      option.setAttribute("data-relationship-visible-links", String(degree));
      if (node.id === state.selectedId) option.selected = true;
      groups.get(label).appendChild(option);
    }
    if (nodes.length > renderedNodes.length) {
      const option = document.createElement("option");
      option.value = "";
      option.disabled = true;
      option.textContent = `${nodes.length - renderedNodes.length} more matches; narrow search`;
      select.appendChild(option);
    }
    if (selectedNode && Array.from(select.options).some((option) => option.value === state.selectedId)) {
      select.value = state.selectedId;
    }
    return nodes;
  }

  function firstSelectableNode(state) {
    const degrees = visibleNodeDegreeMap(state);
    return selectableNodes(state, false, degrees, false)[0] || selectableNodes(state, true, degrees, false)[0] || null;
  }

  function applySearchUpdate(browser, state, selectFirstMatch) {
    state.searchUpdateTimer = 0;
    renderGraph(browser, state);
    const matches = renderNodeSelect(browser, state);
    const normalized = String(state.searchQuery || "").trim();
    if (selectFirstMatch && normalized && matches.length && matches[0].id !== state.selectedId) {
      selectNode(browser, state, matches[0].id, false);
    } else {
      renderDetail(browser, state);
    }
  }

  function scheduleSearchUpdate(browser, state, selectFirstMatch) {
    if (state.searchUpdateTimer) window.clearTimeout(state.searchUpdateTimer);
    state.searchUpdateTimer = window.setTimeout(() => applySearchUpdate(browser, state, selectFirstMatch), 90);
  }

  function cancelSearchUpdate(state) {
    if (!state.searchUpdateTimer) return;
    window.clearTimeout(state.searchUpdateTimer);
    state.searchUpdateTimer = 0;
  }

  function ensureSelectableFocus(state) {
    const selected = state.nodesById.get(state.selectedId);
    const active = state.nodesById.get(state.activeId || "");
    const selectedVisible = Boolean(selected && state.enabledTypes.size && isNodeVisible(selected, state));
    const activeVisible = Boolean(active && state.enabledTypes.size && isNodeVisible(active, state));
    if (selectedVisible && activeVisible) return;
    const next = firstSelectableNode(state);
    if (next) {
      state.selectedId = next.id;
      state.activeId = next.id;
    } else {
      state.activeId = state.selectedId;
    }
    syncActiveSubfilterType(state);
  }

  function refreshTypeFilterState(container, state, types) {
    const auto = container.querySelector("[data-relationship-projection-auto]");
    const projectionAuto = (state.projectionMode || "auto") === "auto";
    if (auto) auto.checked = projectionAuto;
    const groupsById = new Map(projectionRankGroups(state).map((group) => [group.id, group]));
    container.querySelectorAll("[data-relationship-projection-level]").forEach((control) => {
      const level = control.getAttribute("data-relationship-projection-level") || "";
      const group = groupsById.get(level);
      if (!group) return;
      const selected = projectionSelectedTypesForGroup(state, group);
      const requiredType = requiredProjectionTypeForRank(state, group.rank);
      const summary = control.querySelector("[data-relationship-projection-summary]");
      if (summary) summary.textContent = projectionSelectionLabel(state, group);
      const all = control.querySelector("[data-relationship-projection-all]");
      if (all) {
        all.checked = selected.size === group.types.length;
        all.indeterminate = selected.size > 0 && selected.size < group.types.length;
        all.disabled = group.types.every((type) => requiredType && type === requiredType);
        if (all.parentElement) all.parentElement.classList.toggle("is-disabled", all.disabled);
      }
      control.querySelectorAll("[data-relationship-projection-type]").forEach((checkbox) => {
        const type = checkbox.getAttribute("data-relationship-projection-type") || "";
        checkbox.checked = selected.has(type);
        checkbox.disabled = Boolean(requiredType && type === requiredType);
        if (checkbox.parentElement) checkbox.parentElement.classList.toggle("is-disabled", checkbox.disabled);
      });
    });
    const browser = container.closest && container.closest("[data-relationship-browser]") || container;
    renderStatusFilter(browser, state);
    renderFocusTypeSelect(browser, state);
    renderSubfilterPopover(container, state);
  }

  function subfilterLabel(field) {
    return String(field || "").replaceAll("_", " ");
  }

  function resetTypeSubfilters(state, type) {
    const fresh = createSubfilters(stateGraphNodes(state), state.filterDefaults);
    state.subfilters[type] = fresh[type] || {};
  }

  function enableAllTypeSubfilters(state, type) {
    const typeFilters = state.subfilters[type] || {};
    for (const config of Object.values(typeFilters)) {
      config.enabled = new Set(config.values || []);
    }
  }

  function statusFilterValues(state) {
    const counts = new Map();
    const add = (node) => {
      if (!node) return;
      if (node.id !== state.selectedId && !state.enabledTypes.has(node.type || "entity")) return;
      if (!isNonStatusSubfilterEnabled(node, state)) return;
      const value = fieldValue(node, "status");
      if (!value || !(state.statusFilter && state.statusFilter.values.includes(value))) return;
      counts.set(value, (counts.get(value) || 0) + 1);
    };
    const selected = state.nodesById.get(state.selectedId || "");
    add(selected);
    const seen = new Set(selected ? [selected.id] : []);
    const queue = selected ? [selected.id] : [];
    while (queue.length) {
      const fromId = queue.shift();
      const fromRank = traversalRank(state, state.nodesById.get(fromId));
      for (const item of stateGraphAdjacency(state).get(fromId) || []) {
        if (item.edge.source !== fromId || item.edge.target !== item.id) continue;
        if (isSecondaryEdge(item.edge) && !state.showSecondaryLinks) continue;
        if (seen.has(item.id)) continue;
        const node = state.nodesById.get(item.id);
        if (!node) continue;
        const rank = traversalRank(state, node);
        if (rank <= fromRank && !(rank === 99 && fromRank === 99)) continue;
        seen.add(item.id);
        queue.push(item.id);
        add(node);
      }
    }
    const order = (state.statusFilter && state.statusFilter.values) || [];
    return Array.from(counts.entries()).sort((left, right) => order.indexOf(left[0]) - order.indexOf(right[0]));
  }

  function isStatusValueEnabled(state, value) {
    return Boolean(state.statusFilter && state.statusFilter.enabled.has(value));
  }

  function setStatusValueEnabled(state, value, enabled) {
    if (!state.statusFilter || !state.statusFilter.values.includes(value)) return;
    if (enabled) {
      state.statusFilter.enabled.add(value);
    } else {
      state.statusFilter.enabled.delete(value);
    }
  }

  function renderStatusFilter(browser, state) {
    const container = browser.querySelector("[data-relationship-status-filter]");
    if (!container) return;
    container.querySelectorAll("[data-relationship-status-value], .relationship-status-all").forEach((item) => item.remove());
    const values = statusFilterValues(state);
    if (!values.length) return;
    const rerender = () => {
      state.graphPage = 0;
      ensureSelectableFocus(state);
      refreshGraphControlState(browser, state);
      renderGraph(browser, state);
      renderNodeSelect(browser, state);
      renderDetail(browser, state);
    };
    const enabledCount = values.filter(([value]) => isStatusValueEnabled(state, value)).length;
    const allLabel = document.createElement("label");
    allLabel.className = "relationship-status-all";
    const allCheckbox = document.createElement("input");
    allCheckbox.type = "checkbox";
    allCheckbox.setAttribute("data-relationship-status-all", "");
    allCheckbox.checked = enabledCount === values.length;
    allCheckbox.indeterminate = enabledCount > 0 && enabledCount < values.length;
    allCheckbox.title = "Check to show every status, uncheck to hide all of them and then pick the ones you need";
    allCheckbox.addEventListener("change", () => {
      pushNavigationSnapshot(state);
      for (const [value] of values) setStatusValueEnabled(state, value, allCheckbox.checked);
      rerender();
    });
    const allText = document.createElement("span");
    allText.textContent = "All";
    allLabel.append(allCheckbox, allText);
    container.appendChild(allLabel);
    for (const [value, count] of values) {
      const enabled = isStatusValueEnabled(state, value);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.setAttribute("data-relationship-status-value", value);
      chip.setAttribute("aria-pressed", enabled ? "true" : "false");
      chip.className = `relationship-status-chip report-status-badge ${cssStatus(value)}${enabled ? "" : " is-off"}`;
      chip.title = `${count} ${value} nodes in the enabled layers of the whole graph. Click to ${enabled ? "hide" : "show"} them.`;
      const text = document.createElement("span");
      text.textContent = value;
      const badge = document.createElement("small");
      badge.textContent = String(count);
      chip.append(text, badge);
      chip.addEventListener("click", () => {
        pushNavigationSnapshot(state);
        setStatusValueEnabled(state, value, !enabled);
        rerender();
      });
      container.appendChild(chip);
    }
  }

  function renderFocusTypeSelect(browser, state) {
    const select = browser.querySelector("[data-relationship-focus-type]");
    if (!select) return;
    const types = stateGraphTypes(state);
    select.replaceChildren();
    const any = document.createElement("option");
    any.value = "";
    any.textContent = "Any type";
    select.appendChild(any);
    for (const type of types) {
      const option = document.createElement("option");
      option.value = type;
      option.textContent = TYPE_LABELS[type] || type;
      select.appendChild(option);
    }
    select.value = types.includes(state.typeSearchType) ? state.typeSearchType : "";
  }

  function traversalRank(state, node) {
    if (!node) return 99;
    const ranks = state.traversal && state.traversal.typeRanks || DEFAULT_TYPE_RANKS;
    const value = ranks[node.type || "entity"];
    return Number.isFinite(value) ? value : typeRank(node);
  }

  function focusContent(state) {
    const counts = new Map();
    const totals = new Map();
    const ids = new Set();
    const selected = state.nodesById.get(state.selectedId || "");
    if (!selected) return {counts, totals, ids};
    const add = (node) => {
      const type = node.type || "entity";
      counts.set(type, (counts.get(type) || 0) + 1);
      ids.add(node.id);
    };
    const addTotal = (node) => {
      const type = node.type || "entity";
      totals.set(type, (totals.get(type) || 0) + 1);
    };
    addTotal(selected);
    if (isSubfilterEnabled(selected, state)) add(selected);
    const seen = new Set([selected.id]);
    const queue = [selected.id];
    while (queue.length) {
      const fromId = queue.shift();
      const fromRank = traversalRank(state, state.nodesById.get(fromId));
      for (const item of stateGraphAdjacency(state).get(fromId) || []) {
        if (item.edge.source !== fromId || item.edge.target !== item.id) continue;
        if (isSecondaryEdge(item.edge) && !state.showSecondaryLinks) continue;
        if (seen.has(item.id)) continue;
        const node = state.nodesById.get(item.id);
        if (!node) continue;
        const rank = traversalRank(state, node);
        if (rank <= fromRank && !(rank === 99 && fromRank === 99)) continue;
        seen.add(item.id);
        queue.push(item.id);
        addTotal(node);
        if (isSubfilterEnabled(node, state)) add(node);
      }
    }
    return {counts, totals, ids};
  }

  function typeNodeCount(state, type) {
    const content = state.focusContent || focusContent(state);
    return content.counts.get(type) || 0;
  }

  function typeFocusTotal(state, type) {
    const content = state.focusContent || focusContent(state);
    return content.totals.get(type) || 0;
  }

  function hiddenByFiltersCount(state) {
    const content = state.focusContent || focusContent(state);
    let hidden = 0;
    for (const type of state.enabledTypes) {
      hidden += Math.max(0, (content.totals.get(type) || 0) - (content.counts.get(type) || 0));
    }
    return hidden;
  }

  function activeFilterCount(state) {
    let active = 0;
    for (const typeFilters of Object.values(state.subfilters || {})) {
      for (const [field, config] of Object.entries(typeFilters || {})) {
        if (field === "status") continue;
        const values = config.values || [];
        if (values.length && !values.every((value) => config.enabled.has(value))) active += 1;
      }
    }
    return active;
  }

  function renderSubfilterPopover(container, state) {
    const browser = container.closest && container.closest("[data-relationship-browser]") || container;
    const disclosure = browser.querySelector("[data-relationship-filters]");
    const body = browser.querySelector("[data-relationship-filters-body]");
    const summary = browser.querySelector("[data-relationship-filters-summary]");
    if (!body) return;
    body.replaceChildren();
    const activeTypes = (state.activeSubfilterTypes && state.activeSubfilterTypes.length ? state.activeSubfilterTypes : [state.activeSubfilterType])
      .filter((type, index, items) => type && state.enabledTypes.has(type) && items.indexOf(type) === index)
      .filter((type) => Object.entries(state.subfilters[type] || {}).some(([field, config]) =>
        field !== "status" && config && Array.isArray(config.values) && config.values.length > 0
      ));
    const filterCount = activeFilterCount(state);
    if (summary) {
      summary.textContent = filterCount ? `Filters (${filterCount} active)` : "Filters";
    }
    if (disclosure) {
      disclosure.hidden = !activeTypes.length;
      if (!activeTypes.length) disclosure.open = false;
      disclosure.classList.toggle("is-active", filterCount > 0);
    }
    if (!activeTypes.length) return;
    const rerender = () => {
      renderGraph(browser, state);
      renderNodeSelect(browser, state);
      renderDetail(browser, state);
    };
    const popover = document.createElement("div");
    popover.className = "relationship-subfilter-popover";
    popover.setAttribute("data-relationship-subfilter-popover", activeTypes.join(" "));
    for (const type of activeTypes) {
      const typeFilters = state.subfilters[type] || {};
      const section = document.createElement("section");
      section.className = "relationship-subfilter-section";
      const head = document.createElement("div");
      head.className = "relationship-subfilter-head";
      const title = document.createElement("strong");
      title.textContent = `${TYPE_LABELS[type] || type} filters`;
      head.appendChild(title);
      const actions = document.createElement("span");
      const defaults = document.createElement("button");
      defaults.type = "button";
      defaults.textContent = "Defaults";
      defaults.addEventListener("click", () => {
        pushNavigationSnapshot(state);
        resetTypeSubfilters(state, type);
        state.graphPage = 0;
        ensureSelectableFocus(state);
        refreshTypeFilterState(container, state, stateGraphTypes(state));
        rerender();
      });
      const allValues = document.createElement("button");
      allValues.type = "button";
      allValues.textContent = "All values";
      allValues.addEventListener("click", () => {
        pushNavigationSnapshot(state);
        enableAllTypeSubfilters(state, type);
        state.graphPage = 0;
        ensureSelectableFocus(state);
        refreshTypeFilterState(container, state, stateGraphTypes(state));
        rerender();
      });
      actions.append(defaults, allValues);
      head.appendChild(actions);
      section.appendChild(head);
      const fields = Object.entries(typeFilters).filter(([field]) => field !== "status");
      for (const [field, config] of fields) {
        const group = document.createElement("fieldset");
        const legend = document.createElement("legend");
        legend.textContent = subfilterLabel(field);
        group.appendChild(legend);
        const values = config.values || [];
        if (values.length > 1) {
          const allLabel = document.createElement("label");
          allLabel.className = "relationship-subfilter-all";
          const allCheckbox = document.createElement("input");
          allCheckbox.type = "checkbox";
          allCheckbox.checked = values.every((value) => config.enabled.has(value));
          allCheckbox.indeterminate = !allCheckbox.checked && values.some((value) => config.enabled.has(value));
          allCheckbox.addEventListener("change", () => {
            pushNavigationSnapshot(state);
            config.enabled = allCheckbox.checked ? new Set(values) : new Set();
            state.graphPage = 0;
            ensureSelectableFocus(state);
            refreshTypeFilterState(container, state, stateGraphTypes(state));
            rerender();
          });
          allLabel.appendChild(allCheckbox);
          const allText = document.createElement("span");
          allText.textContent = "All";
          allLabel.appendChild(allText);
          group.appendChild(allLabel);
        }
        for (const value of values) {
          const label = document.createElement("label");
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.checked = config.enabled.has(value);
          checkbox.addEventListener("change", () => {
            pushNavigationSnapshot(state);
            if (checkbox.checked) {
              config.enabled.add(value);
            } else {
              config.enabled.delete(value);
            }
            state.graphPage = 0;
            ensureSelectableFocus(state);
            refreshTypeFilterState(container, state, stateGraphTypes(state));
            rerender();
          });
          label.appendChild(checkbox);
          const text = document.createElement("span");
          text.className = cssStatus(value);
          text.textContent = value;
          label.appendChild(text);
          group.appendChild(label);
        }
        section.appendChild(group);
      }
      popover.appendChild(section);
    }
    body.appendChild(popover);
  }

  function projectionChoiceLabel(types) {
    return types.map((type) => TYPE_LABELS[type] || type).join(" + ");
  }

  function requiredProjectionTypeForRank(state, rank) {
    const selected = state.nodesById && state.nodesById.get(state.selectedId || "");
    if (!selected) return "";
    const selectedRank = typeRankValue(state, selected.type || "entity");
    if (rank !== selectedRank) return "";
    return selected.type || "entity";
  }

  function renderTypeFilters(browser, state) {
    const container = browser.querySelector("[data-relationship-projection-controls]");
    if (!container) return;
    const auto = container.querySelector("[data-relationship-projection-auto]");
    const levels = container.querySelector("[data-relationship-projection-levels]");
    if (!levels) return;
    if (auto) {
      auto.checked = (state.projectionMode || "auto") === "auto";
      auto.addEventListener("change", () => {
        pushNavigationSnapshot(state);
        state.projectionMode = auto.checked ? "auto" : "custom";
        if (state.projectionMode === "auto") {
          resetEntityTypesToFocusView(browser, state, state.selectedId);
        } else {
          applyProjectionSelections(browser, state);
        }
        state.graphPage = 0;
        ensureSelectableFocus(state);
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      });
    }
    levels.replaceChildren();
    const closeProjectionMenus = (except) => {
      levels.querySelectorAll(".relationship-projection-menu").forEach((menu) => {
        if (menu !== except) menu.hidden = true;
      });
      levels.querySelectorAll("[data-relationship-projection-summary]").forEach((button) => {
        const menu = button.closest("[data-relationship-projection-level]") && button.closest("[data-relationship-projection-level]").querySelector(".relationship-projection-menu");
        button.setAttribute("aria-expanded", menu && !menu.hidden ? "true" : "false");
      });
    };
    for (const group of projectionRankGroups(state)) {
      const control = document.createElement("div");
      control.className = "relationship-projection-level";
      control.setAttribute("data-relationship-projection-level", group.id);
      const title = document.createElement("span");
      title.textContent = group.label;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "relationship-projection-summary";
      button.setAttribute("data-relationship-projection-summary", "");
      button.setAttribute("aria-haspopup", "true");
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", `${group.label} visible entity types`);
      const menu = document.createElement("div");
      menu.className = "relationship-projection-menu";
      menu.hidden = true;
      const applyGroupSelection = (selected) => {
        pushNavigationSnapshot(state);
        state.projectionMode = "custom";
        setProjectionGroupSelection(state, group, selected);
        state.graphPage = 0;
        applyProjectionSelections(browser, state);
        ensureSelectableFocus(state);
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      };
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const nextHidden = !menu.hidden;
        closeProjectionMenus(menu);
        menu.hidden = nextHidden;
        button.setAttribute("aria-expanded", menu.hidden ? "false" : "true");
      });
      control.addEventListener("click", (event) => event.stopPropagation());
      const allLabel = document.createElement("label");
      const allCheckbox = document.createElement("input");
      allCheckbox.type = "checkbox";
      allCheckbox.setAttribute("data-relationship-projection-all", "");
      allCheckbox.addEventListener("change", () => {
        applyGroupSelection(allCheckbox.checked ? new Set(group.types) : new Set());
      });
      allLabel.appendChild(allCheckbox);
      const allText = document.createElement("span");
      allText.textContent = "All";
      allLabel.appendChild(allText);
      menu.appendChild(allLabel);
      for (const type of group.types) {
        const optionLabel = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.setAttribute("data-relationship-projection-type", type);
        checkbox.addEventListener("change", () => {
          const selected = projectionSelectedTypesForGroup(state, group);
          if (checkbox.checked) {
            selected.add(type);
          } else {
            selected.delete(type);
          }
          applyGroupSelection(selected);
        });
        optionLabel.appendChild(checkbox);
        const text = document.createElement("span");
        text.textContent = TYPE_LABELS[type] || type;
        optionLabel.appendChild(text);
        menu.appendChild(optionLabel);
      }
      control.append(title, button, menu);
      levels.appendChild(control);
    }
    if (!levels.dataset.relationshipProjectionOutsideClick) {
      levels.dataset.relationshipProjectionOutsideClick = "true";
      document.addEventListener("click", () => closeProjectionMenus(null));
    }
    refreshTypeFilterState(container, state, stateGraphTypes(state));
  }

  function initBrowser(browser) {
    const graph = parseGraph(browser);
    const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
    if (!nodesById.size) return;
    const preferred =
      graph.nodes.find((node) => (node.type || "entity") === "product") ||
      graph.nodes
        .slice()
        .sort((left, right) =>
          typeRank(left) - typeRank(right) ||
          String(left.label || left.id).localeCompare(String(right.label || right.id))
        )[0] ||
      graph.nodes[0];
    const state = {
      nodes: graph.nodes,
      edges: graph.edges,
      nodesById,
      adjacency: buildAdjacency(graph.edges),
      outgoingAdjacency: buildOutgoingAdjacency(graph.edges),
      filterDefaults: graph.filterDefaults || {},
      subfilters: {},
      statusFilter: {values: [], enabled: new Set()},
      activeSubfilterType: "",
      selectedId: preferred.id,
      activeId: preferred.id,
      rootId: preferred.id,
      cy: null,
      backStack: [],
      forwardStack: [],
      searchQuery: "",
      searchTextById: new Map(),
      searchUpdateTimer: 0,
      typeSearchType: "",
      graphInteractive: false,
      graphFocusActive: false,
      graphRenderSignature: "",
      focusGraph: null,
      focusContent: null,
      focusInGraphOnly: false,
      isolatedRootId: "",
      isolatedNodeIds: null,
      scopedEdgesCache: null,
      scopedAdjacencyCache: null,
      canvasViewportListenersAttached: false,
      showSecondaryLinks: false,
      activeViewPinned: false,
      graphPage: 0,
      traversal: traversalConfig(graph.traversal),
      projectionMode: "auto",
      projectionSelections: {},
      enabledTypes: new Set()
    };
    state.enabledTypes = new Set(stateGraphTypes(state));
    state.projectionSelections = defaultProjectionSelections(state);
    resetSubfilters(state);
    syncActiveSubfilterType(state);
    renderTypeFilters(browser, state);
    const secondaryLinks = browser.querySelector("[data-relationship-secondary-links]");
    if (secondaryLinks) {
      secondaryLinks.checked = state.showSecondaryLinks;
      secondaryLinks.addEventListener("change", () => {
        pushNavigationSnapshot(state);
        state.showSecondaryLinks = secondaryLinks.checked;
        state.graphPage = 0;
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      });
    }
    browser.querySelectorAll("[data-relationship-page-prev]").forEach((pagePrev) => {
      pagePrev.addEventListener("click", () => {
        activateGraphFocus(browser, state);
        state.graphPage = Math.max(0, state.graphPage - 1);
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      });
    });
    browser.querySelectorAll("[data-relationship-page-next]").forEach((pageNext) => {
      pageNext.addEventListener("click", () => {
        activateGraphFocus(browser, state);
        state.graphPage += 1;
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      });
    });
    const focusType = browser.querySelector("[data-relationship-focus-type]");
    if (focusType) {
      focusType.addEventListener("change", () => {
        state.typeSearchType = focusType.value || "";
        state.graphPage = 0;
        renderNodeSelect(browser, state);
        refreshGraphControlState(browser, state);
      });
    }
    const focusScope = browser.querySelector("[data-relationship-focus-scope]");
    if (focusScope) {
      focusScope.checked = state.focusInGraphOnly;
      focusScope.title = "When checked, the focus list offers only the nodes drawn on the current graph instead of every node";
      focusScope.addEventListener("change", () => {
        state.focusInGraphOnly = focusScope.checked;
        renderNodeSelect(browser, state);
      });
    }
    const select = browser.querySelector("[data-relationship-node-select]");
    if (select) {
      select.addEventListener("change", () => {
        cancelSearchUpdate(state);
        if (select.value) selectNode(browser, state, select.value, true);
      });
      renderNodeSelect(browser, state);
    }
    const search = browser.querySelector("[data-relationship-search]");
    if (search && select) {
      search.addEventListener("input", () => {
        state.searchQuery = search.value;
        state.graphPage = 0;
        scheduleSearchUpdate(browser, state, false);
      });
      search.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        if (state.searchUpdateTimer) {
          cancelSearchUpdate(state);
          applySearchUpdate(browser, state, false);
        }
        const match = selectableNodes(state, false)[0];
        if (match) {
          event.preventDefault();
          selectNode(browser, state, match.id, true);
        }
      });
    }
    const back = browser.querySelector("[data-relationship-back]");
    const forward = browser.querySelector("[data-relationship-forward]");
    const fit = browser.querySelector("[data-relationship-fit]");
    if (fit) {
      fit.addEventListener("click", () => {
        activateGraphFocus(browser, state);
        fitGraph(state, 40);
      });
    }
    const canvas = browser.querySelector("[data-relationship-canvas]");
    if (canvas) {
      canvas.addEventListener("pointerenter", () => syncGraphViewport(state), {passive: true});
    }
    const routeGraphFocusEvent = (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest("[data-relationship-focus-badge]")) {
        return;
      }
      if (target.closest(".relationship-graph-toolbar")) {
        activateGraphFocus(browser, state);
        return;
      }
      if (target.closest(".relationship-canvas-wrap")) {
        activateGraphFocus(browser, state);
      } else {
        releaseGraphFocus(browser, state);
      }
    };
    ["pointerdown", "mousedown", "touchstart", "click"].forEach((eventName) => {
      browser.addEventListener(eventName, routeGraphFocusEvent, {capture: true});
    });
    browser.querySelectorAll("[data-relationship-focus-badge]").forEach((badge) => {
      badge.addEventListener("click", () => releaseGraphFocus(browser, state));
    });
    const detail = browser.querySelector("[data-relationship-detail]");
    if (detail) {
      const releaseFromDetail = () => {
        releaseGraphFocus(browser, state);
      };
      const releaseFromBrowserDetail = (event) => {
        if (detail.contains(event.target)) {
          releaseGraphFocus(browser, state);
        }
      };
      detail.addEventListener("pointerdown", releaseFromDetail, {capture: true, passive: true});
      detail.addEventListener("mousedown", releaseFromDetail, {capture: true, passive: true});
      detail.addEventListener("wheel", releaseFromDetail, {capture: true, passive: true});
      detail.addEventListener("touchstart", releaseFromDetail, {capture: true, passive: true});
      detail.addEventListener("touchmove", releaseFromDetail, {capture: true, passive: true});
      detail.addEventListener("scroll", releaseFromDetail, {passive: true});
      detail.addEventListener("focusin", releaseFromDetail);
      browser.addEventListener("wheel", releaseFromBrowserDetail, {capture: true, passive: true});
      browser.addEventListener("touchmove", releaseFromBrowserDetail, {capture: true, passive: true});
    }
    const explorer = browser.querySelector(".relationship-explorer-main");
    if (explorer) {
      const handleExplorerScroll = () => {
        syncGraphViewport(state);
      };
      explorer.addEventListener("scroll", handleExplorerScroll, {passive: true});
      explorer.addEventListener("wheel", () => syncGraphViewport(state), {passive: true});
      window.addEventListener("resize", () => syncGraphViewport(state));
    }
    const themeObserver = new MutationObserver(() => refreshGraphTheme(state));
    themeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme"]});
    state.themeObserver = themeObserver;
    if (back) {
      back.addEventListener("click", () => {
        const previous = state.backStack.pop();
        if (!previous) return;
        state.forwardStack.push(navigationSnapshot(state));
        restoreNavigationSnapshot(browser, state, previous);
      });
    }
    if (forward) {
      forward.addEventListener("click", () => {
        const next = state.forwardStack.pop();
        if (!next) return;
        state.backStack.push(navigationSnapshot(state));
        restoreNavigationSnapshot(browser, state, next);
      });
    }
    browser.addEventListener("click", (event) => {
      const tableRow = event.target.closest && event.target.closest("[data-relationship-table-node]");
      if (tableRow) {
        selectTableNode(browser, state, tableRow.getAttribute("data-relationship-table-node"));
        return;
      }
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (nodeElement) {
        selectNode(browser, state, nodeElement.getAttribute("data-node-id"), true);
        return;
      }
      const jump = event.target.closest && event.target.closest("[data-relationship-jump]");
      if (jump) {
        const nodeId = jump.getAttribute("data-relationship-jump");
        selectNode(browser, state, nodeId, true);
      }
    });
    browser.addEventListener("dblclick", (event) => {
      const tableRow = event.target.closest && event.target.closest("[data-relationship-table-node]");
      if (!tableRow) return;
      event.preventDefault();
      selectTableNode(browser, state, tableRow.getAttribute("data-relationship-table-node"));
    });
    browser.addEventListener("keydown", (event) => {
      const nodeElement = event.target.closest && event.target.closest("[data-node-id]");
      if (!nodeElement || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      selectNode(browser, state, nodeElement.getAttribute("data-node-id"), true);
    });
    window.addEventListener("resize", () => fitGraph(state, 40), {passive: true});
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

  function openRelationshipFocus(trigger, nodeId) {
    const section = trigger && trigger.closest ? trigger.closest(".report-root, body") : document;
    const modal = (section || document).querySelector("[data-relationship-modal]");
    if (!modal || !nodeId) return;
    openRelationshipModal(modal);
    const browser = modal.querySelector("[data-relationship-browser]");
    const state = browser && browser.__relationshipState;
    if (state && state.nodesById.has(nodeId)) {
      selectTableNode(browser, state, nodeId);
    }
  }

  function applyRelationshipViewFilters(state, filters) {
    if (!filters || typeof filters !== "object") return;
    const statusValues = new Set();
    let hasStatusFilter = false;
    for (const [type, typeFilters] of Object.entries(filters)) {
      if (!typeFilters || typeof typeFilters !== "object") continue;
      for (const [field, values] of Object.entries(typeFilters)) {
        if (!Array.isArray(values)) continue;
        if (field === "status") {
          hasStatusFilter = true;
          for (const value of values) statusValues.add(String(value));
          continue;
        }
        const stateFilters = state.subfilters && state.subfilters[type];
        const config = stateFilters && stateFilters[field];
        if (!config) continue;
        config.enabled = new Set((config.values || []).filter((value) => values.includes(value)));
      }
    }
    if (hasStatusFilter && state.statusFilter) {
      state.statusFilter.enabled = new Set(state.statusFilter.values.filter((value) => statusValues.has(value)));
    }
  }

  function applyRelationshipView(browser, state, view) {
    const focusId = view && view.focus;
    if (!focusId || !state.nodesById.has(focusId)) return;
    const isolateRoot = view.isolate_root || "";
    const isolatedNodeIds = isolatedIdsForRoot(state, isolateRoot);
    if (isolatedNodeIds && !isolatedNodeIds.has(focusId)) return;
    pushNavigationSnapshot(state);
    setIsolatedRoot(state, isolateRoot);
    resetGraphFilters(browser, state);
    state.activeViewPinned = true;
    const types = stateGraphTypes(state);
    const requested = Array.isArray(view.types) ? view.types.filter((type) => types.includes(type)) : [];
    if (requested.length) {
      state.enabledTypes = new Set(requested);
      state.enabledTypes.add(state.nodesById.get(focusId).type || "entity");
      state.projectionMode = "custom";
      setProjectionSelectionsFromTypes(state, state.enabledTypes);
    }
    applyRelationshipViewFilters(state, view.filters);
    state.graphPage = 0;
    state.searchQuery = "";
    cancelSearchUpdate(state);
    const search = browser.querySelector("[data-relationship-search]");
    if (search) search.value = "";
    updateSelectedNodeState(browser, state, focusId, false, {preserveTypes: true, preserveFilters: true});
    const targetType = view.target_type || "";
    if (targetType && state.enabledTypes.has(targetType)) {
      state.activeSubfilterType = targetType;
      state.activeSubfilterTypes = [targetType];
      state.typeSearchType = targetType;
    }
    refreshGraphControlState(browser, state, types);
    renderRelationshipState(browser, state);
  }

  function openRelationshipView(trigger, view) {
    const section = trigger && trigger.closest ? trigger.closest(".report-root, body") : document;
    const modal = (section || document).querySelector("[data-relationship-modal]");
    if (!modal || !view || !view.focus) return;
    openRelationshipModal(modal);
    const browser = modal.querySelector("[data-relationship-browser]");
    const state = browser && browser.__relationshipState;
    if (state) applyRelationshipView(browser, state, view);
  }

  function closeRelationshipModal(modal) {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("relationship-modal-open");
  }

  document.querySelectorAll("[data-relationship-open]").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = button.closest(".report-relationship-section").querySelector("[data-relationship-modal]");
      openRelationshipModal(modal);
      const browser = modal && modal.querySelector("[data-relationship-browser]");
      const state = browser && browser.__relationshipState;
      if (state) {
        pushNavigationSnapshot(state);
        setIsolatedRoot(state, "");
        resetGraphFiltersToAll(browser, state);
        state.activeViewPinned = false;
        ensureSelectableFocus(state);
        renderGraph(browser, state);
        renderNodeSelect(browser, state);
        renderDetail(browser, state);
      }
    });
  });
  document.querySelectorAll("[data-relationship-open-focus]").forEach((item) => {
    item.addEventListener("click", () => {
      openRelationshipFocus(item, item.getAttribute("data-relationship-open-focus"));
    });
  });
  document.querySelectorAll("[data-relationship-open-view]").forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault();
      let view = null;
      try {
        view = JSON.parse(item.getAttribute("data-relationship-open-view") || "null");
      } catch (error) {
        view = null;
      }
      if (view) openRelationshipView(item, view);
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


def _report_self_test_script() -> str:
    return r"""
<script>
(() => {
  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function parseView(button) {
    try {
      return JSON.parse(button.getAttribute("data-relationship-open-view") || "null");
    } catch (error) {
      return null;
    }
  }

  function metricCount(button) {
    const match = String(button.textContent || "").match(/\d+/);
    return match ? Number(match[0]) : null;
  }

  function activeBrowser() {
    return document.querySelector("[data-relationship-browser]");
  }

  function dumpState() {
    const browser = activeBrowser();
    const state = browser && browser.__relationshipState;
    const graph = state && state.visibleGraph;
    const canvasWrap = browser && browser.querySelector(".relationship-canvas-wrap");
    const canvasStyle = canvasWrap ? window.getComputedStyle(canvasWrap) : null;
    const controlledTypes = browser
      ? Array.from(browser.querySelectorAll("[data-relationship-projection-type]"))
          .map((control) => control.getAttribute("data-relationship-projection-type") || "")
          .filter(Boolean)
      : [];
    return {
      selectedId: state && state.selectedId || "",
      activeId: state && state.activeId || "",
      allTypes: Array.from(new Set(controlledTypes)).sort(),
      enabledTypes: state ? Array.from(state.enabledTypes || []).sort() : [],
      projectionMode: state && state.projectionMode || "",
      projectionSelections: state && state.projectionSelections ? Object.assign({}, state.projectionSelections) : {},
      activeSubfilterType: state && state.activeSubfilterType || "",
      graphReady: browser ? browser.getAttribute("data-relationship-graph-ready") === "true" : false,
      activeView: browser ? browser.getAttribute("data-relationship-active-view") === "true" : false,
      graphFocused: browser ? browser.getAttribute("data-relationship-graph-focused") === "true" : false,
      focusBadgeVisible: Boolean(browser && Array.from(browser.querySelectorAll("[data-relationship-focus-badge]")).some((badge) => !badge.hidden && badge.getBoundingClientRect().width > 0)),
      canvasBackground: canvasStyle ? canvasStyle.backgroundColor : "",
      canvasBoxShadow: canvasStyle ? canvasStyle.boxShadow : "",
      statusValues: state && state.statusFilter ? Array.from(state.statusFilter.values || []).sort() : [],
      statusEnabled: state && state.statusFilter ? Array.from(state.statusFilter.enabled || []).sort() : [],
      nodes: graph && graph.nodes ? graph.nodes.length : 0,
      edges: graph && graph.edges ? graph.edges.length : 0,
      pagination: graph && graph.pagination || null,
      edgeSample: graph && graph.edges ? graph.edges.slice(0, 5) : [],
      renderVersion: state ? Number(state.renderVersion || 0) : 0,
      lastRenderDurationMs: state ? Math.round(Number(state.lastRenderDurationMs || 0)) : 0
    };
  }

  function rectSummary(element) {
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return {
      left: Math.round(rect.left),
      right: Math.round(rect.right),
      top: Math.round(rect.top),
      bottom: Math.round(rect.bottom),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      scrollWidth: element.scrollWidth || 0,
      scrollHeight: element.scrollHeight || 0,
      clientWidth: element.clientWidth || 0,
      clientHeight: element.clientHeight || 0
    };
  }

  function layoutState() {
    const scrolling = document.scrollingElement || document.documentElement;
    const main = document.querySelector("main");
    const toc = document.querySelector(".report-toc");
    const metricTable = document.querySelector(".report-metric-table-wrap");
    const reportTable = document.querySelector(".report-table-wrap");
    const browser = activeBrowser();
    const canvas = browser && browser.querySelector(".relationship-canvas-wrap");
    const detail = browser && browser.querySelector(".relationship-detail");
    return {
      viewport: {
        width: window.innerWidth || 0,
        height: window.innerHeight || 0
      },
      document: {
        scrollWidth: scrolling.scrollWidth || 0,
        scrollHeight: scrolling.scrollHeight || 0,
        clientWidth: scrolling.clientWidth || 0,
        clientHeight: scrolling.clientHeight || 0,
        scrollX: Math.round(window.scrollX || 0),
        scrollY: Math.round(window.scrollY || 0)
      },
      main: rectSummary(main),
      toc: rectSummary(toc),
      metricTable: rectSummary(metricTable),
      reportTable: rectSummary(reportTable),
      graphCanvas: rectSummary(canvas),
      graphDetail: rectSummary(detail)
    };
  }

  function arraysEqual(left, right) {
    const a = Array.from(left || []).sort();
    const b = Array.from(right || []).sort();
    return a.length === b.length && a.every((value, index) => value === b[index]);
  }

  function projectionIsAll(state) {
    const values = Object.values(state.projectionSelections || {});
    return values.length > 0 && values.every((value) => value === "__all__");
  }

  function metricButtons() {
    return Array.from(document.querySelectorAll("[data-relationship-open-view]"))
      .map((button) => ({button, view: parseView(button)}))
      .filter((item) => item.view && item.view.target_type && item.view.filters);
  }

  function viewTargetStatus(view) {
    const targetType = view && view.target_type;
    const statuses = targetType && view.filters && view.filters[targetType]
      ? view.filters[targetType].status
      : null;
    return Array.isArray(statuses) && statuses.length ? statuses[0] : "";
  }

  function graphMetricCandidates() {
    return metricButtons().filter((item) =>
      item.view && item.view.target_type && item.view.filters
      && String(item.view.focus || "").startsWith("product:")
    );
  }

  function preferredGraphMetric() {
    const candidates = graphMetricCandidates();
    return candidates.find((item) => viewTargetStatus(item.view) === "not_failed")
      || candidates[0]
      || null;
  }

  function visibleTargetNode(graph, item) {
    const targetType = item && item.view && item.view.target_type;
    return graph && graph.nodes && graph.nodes.find((node) => node.type === targetType);
  }

  const SELF_TEST_SETTLE_MS = 300;

  function stats(values) {
    const numbers = values.map(Number).filter((value) => Number.isFinite(value));
    if (!numbers.length) return {count: 0, minMs: 0, avgMs: 0, maxMs: 0};
    const total = numbers.reduce((sum, value) => sum + value, 0);
    const rounded = (value) => Math.round(value * 100) / 100;
    return {
      count: numbers.length,
      minMs: rounded(Math.min(...numbers)),
      avgMs: rounded(total / numbers.length),
      maxMs: rounded(Math.max(...numbers))
    };
  }

  async function runMetricButton(item) {
    const startedAt = performance.now();
    const expectedCount = metricCount(item.button);
    const errors = [];
    item.button.click();
    await delay(SELF_TEST_SETTLE_MS);
    const state = dumpState();
    const targetType = item.view.target_type;
    const targetStatus = viewTargetStatus(item.view);
    if (expectedCount != null && state.pagination && state.pagination.total !== expectedCount) {
      errors.push(`pagination total ${state.pagination.total} != metric count ${expectedCount}`);
    }
    if (!state.enabledTypes.includes(targetType)) {
      errors.push(`target type ${targetType} is not enabled`);
    }
    if (targetStatus && !state.statusEnabled.includes(targetStatus)) {
      errors.push(`status ${targetStatus} is not enabled`);
    }
    if (!state.activeView) {
      errors.push("graph active view indicator is not enabled after metric click");
    }
    if (expectedCount && state.nodes > 1 && state.edges <= 0) {
      errors.push(`no graph links rendered for ${targetType}`);
    }
    return {
      title: item.button.getAttribute("title") || String(item.button.textContent || "").trim(),
      targetType,
      targetStatus: targetStatus || "",
      expectedCount,
      state,
      durationMs: Math.round(performance.now() - startedAt),
      pass: errors.length === 0,
      errors
    };
  }

  async function runLayoutAndScroll() {
    const startedAt = performance.now();
    const errors = [];
    const profile = new URLSearchParams(window.location.search || "").get("report-self-test-profile") || "unknown";
    const initial = layoutState();
    const initialGraphState = dumpState();
    const overflowAllowance = 24;
    if (initialGraphState.activeView) {
      errors.push("graph active view indicator is enabled before a graph interaction");
    }
    if (initialGraphState.focusBadgeVisible) {
      errors.push("graph focus badge is visible before a graph interaction");
    }
    if (!initial.main || initial.main.width <= 0) {
      errors.push("main content is not visible");
    }
    if (!initial.toc || initial.toc.width <= 0) {
      errors.push("table of contents is not visible");
    }
    if (initial.main && initial.main.right > initial.viewport.width + overflowAllowance) {
      errors.push(`main content overflows viewport: ${initial.main.right} > ${initial.viewport.width}`);
    }
    if (profile === "mobile") {
      const minimumPanelWidth = Math.min(320, initial.viewport.width - 32);
      if (initial.toc && initial.toc.width < minimumPanelWidth) {
        errors.push(`mobile table of contents is too narrow: ${initial.toc.width} < ${minimumPanelWidth}`);
      }
      if (initial.main && initial.main.width < minimumPanelWidth) {
        errors.push(`mobile main content is too narrow: ${initial.main.width} < ${minimumPanelWidth}`);
      }
      const narrowTocLinks = Array.from(document.querySelectorAll(".report-toc a"))
        .map((link) => rectSummary(link))
        .filter((rect) => rect && rect.width < minimumPanelWidth - 24);
      if (narrowTocLinks.length) {
        errors.push(`${narrowTocLinks.length} mobile table-of-contents links are too narrow`);
      }
    }
    if (initial.document.scrollWidth > initial.viewport.width + overflowAllowance) {
      errors.push(`document horizontal overflow: ${initial.document.scrollWidth} > ${initial.viewport.width}`);
    }
    if (initial.document.scrollHeight <= initial.viewport.height) {
      errors.push("document is not vertically scrollable");
    }
    window.scrollTo(0, Math.min(240, Math.max(0, initial.document.scrollHeight - initial.viewport.height)));
    await delay(0);
    const afterBodyScroll = layoutState();
    if (initial.document.scrollHeight > initial.viewport.height && afterBodyScroll.document.scrollY <= 0) {
      errors.push("document did not scroll vertically");
    }

    const wideTable = document.querySelector(".report-table-wrap, .report-metric-table-wrap");
    let tableScrolled = null;
    if (wideTable && wideTable.scrollWidth > wideTable.clientWidth + 1) {
      wideTable.scrollLeft = 80;
      await delay(0);
      tableScrolled = wideTable.scrollLeft > 0;
      if (!tableScrolled) {
        errors.push("wide table wrapper did not scroll horizontally");
      }
    }

    const metric = preferredGraphMetric();
    let graph = null;
    if (!metric) {
      errors.push("metric graph button not found for layout test");
    } else {
      metric.button.click();
      await delay(SELF_TEST_SETTLE_MS);
      graph = layoutState();
      const current = dumpState();
      if (!current.graphReady) {
        errors.push("graph ready indicator is not enabled after metric click");
      }
      if (!current.activeView) {
        errors.push("graph active view indicator is not enabled after layout metric click");
      }
      if (!graph.graphCanvas || graph.graphCanvas.width < 280 || graph.graphCanvas.height < 280) {
        errors.push("graph canvas is too small after metric click");
      }
      if (graph.graphCanvas && graph.graphCanvas.right > graph.viewport.width + overflowAllowance) {
        errors.push(`graph canvas overflows viewport: ${graph.graphCanvas.right} > ${graph.viewport.width}`);
      }
      if (current.nodes <= 0) {
        errors.push("graph has no visible nodes after metric click");
      }
      if (current.edges <= 0) {
        errors.push("graph has no visible edges after metric click");
      }
    }

    return {
      name: "responsive layout and scroll",
      profile,
      pass: errors.length === 0,
      durationMs: Math.round(performance.now() - startedAt),
      tableScrolled,
      initial,
      afterBodyScroll,
      graph,
      errors
    };
  }

  async function runEntitySwitchReset() {
    const startedAt = performance.now();
    const item = preferredGraphMetric();
    const errors = [];
    if (!item) {
      return {name: "entity switch resets filters", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["graph metric button not found"]};
    }
    item.button.click();
    await delay(SELF_TEST_SETTLE_MS);
    const browser = activeBrowser();
    const state = browser && browser.__relationshipState;
    const graph = state && state.visibleGraph;
    const targetNode = visibleTargetNode(graph, item);
    if (!browser || !state || !targetNode) {
      return {name: "entity switch resets filters", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["target node not visible after metric click"]};
    }
    const focusSelect = browser.querySelector("[data-relationship-node-select]");
    if (!focusSelect) {
      return {name: "entity switch resets filters", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["focus select not found"]};
    }
    focusSelect.value = targetNode.id;
    focusSelect.dispatchEvent(new Event("change", {bubbles: true}));
    await delay(SELF_TEST_SETTLE_MS);
    const next = dumpState();
    if (!arraysEqual(next.enabledTypes, next.allTypes)) {
      errors.push("enabled layers are not All after entity switch");
    }
    if (!arraysEqual(next.statusEnabled, next.statusValues)) {
      errors.push("status filter is not All after entity switch");
    }
    if (!projectionIsAll(next)) {
      errors.push("projection levels are not All after entity switch");
    }
    return {
      name: "entity switch resets filters",
      targetNode: targetNode.id,
      state: next,
      durationMs: Math.round(performance.now() - startedAt),
      pass: errors.length === 0,
      errors
    };
  }

  async function runGraphFocusBadgeRelease() {
    const startedAt = performance.now();
    const item = preferredGraphMetric();
    const errors = [];
    if (!item) {
      return {name: "graph focus badge release", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["graph metric button not found"]};
    }
    item.button.click();
    await delay(SELF_TEST_SETTLE_MS);
    const browser = activeBrowser();
    const state = browser && browser.__relationshipState;
    const graph = state && state.visibleGraph;
    const canvasWrap = browser && browser.querySelector(".relationship-canvas-wrap");
    const badge = browser && browser.querySelector("[data-relationship-focus-badge]");
    const statusFilter = browser && browser.querySelector("[data-relationship-status-filter]");
    const selectionPanel = browser && browser.querySelector(".relationship-selection-panel");
    const explorer = browser && browser.querySelector(".relationship-explorer-main");
    const focusSelect = browser && browser.querySelector("[data-relationship-node-select]");
    const targetNode = visibleTargetNode(graph, item);
    if (!browser || !state || !canvasWrap || !badge || !statusFilter || !selectionPanel || !explorer || !focusSelect || !targetNode) {
      return {name: "graph focus badge release", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["graph controls or target node not visible after metric click"]};
    }
    const initial = dumpState();
    const canvas = browser.querySelector("[data-relationship-canvas]");
    const initialCanvasPointerEvents = canvas ? window.getComputedStyle(canvas).pointerEvents : "";
    if (initialCanvasPointerEvents === "none") {
      errors.push("inactive graph canvas blocks pointer events");
    }
    const pointerDown = (element) => element.dispatchEvent(new PointerEvent("pointerdown", {bubbles: true, composed: true}));
    const mouseDown = (element) => element.dispatchEvent(new MouseEvent("mousedown", {bubbles: true, composed: true}));
    const click = (element) => element.dispatchEvent(new MouseEvent("click", {bubbles: true, composed: true}));
    const canvasRectBeforeFocus = rectSummary(canvasWrap);
    pointerDown(canvasWrap);
    await delay(SELF_TEST_SETTLE_MS);
    const focused = dumpState();
    const canvasRectAfterFocus = rectSummary(canvasWrap);
    if (!focused.graphFocused) {
      errors.push("graph focus flag is not enabled after canvas wrap pointerdown");
    }
    if (!focused.focusBadgeVisible) {
      errors.push("graph focus badge is not visible after canvas wrap pointerdown");
    }
    if (focused.canvasBackground && initial.canvasBackground && focused.canvasBackground !== initial.canvasBackground) {
      errors.push(`graph focus changed canvas background: ${initial.canvasBackground} -> ${focused.canvasBackground}`);
    }
    if (String(focused.canvasBoxShadow || "").includes("inset")) {
      errors.push("graph focus uses an inset canvas shadow");
    }
    if (
      canvasRectBeforeFocus && canvasRectAfterFocus &&
      (
        canvasRectBeforeFocus.clientWidth !== canvasRectAfterFocus.clientWidth ||
        canvasRectBeforeFocus.clientHeight !== canvasRectAfterFocus.clientHeight ||
        canvasRectBeforeFocus.width !== canvasRectAfterFocus.width ||
        canvasRectBeforeFocus.height !== canvasRectAfterFocus.height
      )
    ) {
      errors.push(
        `graph focus changed canvas size: ` +
        `${canvasRectBeforeFocus.width}x${canvasRectBeforeFocus.height}/${canvasRectBeforeFocus.clientWidth}x${canvasRectBeforeFocus.clientHeight} -> ` +
        `${canvasRectAfterFocus.width}x${canvasRectAfterFocus.height}/${canvasRectAfterFocus.clientWidth}x${canvasRectAfterFocus.clientHeight}`
      );
    }
    const pageCount = browser.querySelector("[data-relationship-page-count]");
    const originalPageText = pageCount ? pageCount.textContent : "";
    if (pageCount) pageCount.textContent = "17 nodes";
    const badgeCenterBefore = rectSummary(badge);
    if (pageCount) pageCount.textContent = "1-50 of 480";
    await delay(SELF_TEST_SETTLE_MS);
    const badgeCenterAfter = rectSummary(badge);
    if (pageCount) pageCount.textContent = originalPageText;
    if (badgeCenterBefore && badgeCenterAfter) {
      const beforeX = Math.round(badgeCenterBefore.left + badgeCenterBefore.width / 2);
      const afterX = Math.round(badgeCenterAfter.left + badgeCenterAfter.width / 2);
      if (Math.abs(beforeX - afterX) > 1) {
        errors.push(`graph focus badge moved horizontally: ${beforeX} -> ${afterX}`);
      }
    }
    const pageNext = browser.querySelector("[data-relationship-page-next]");
    if (pageNext && !pageNext.disabled && !pageNext.hidden) {
      click(pageNext);
      await delay(SELF_TEST_SETTLE_MS);
      const focusedAfterPageNext = dumpState();
      if (!focusedAfterPageNext.graphFocused) {
        errors.push("graph focus flag is not enabled after page next click");
      }
    }
    const pagePrev = browser.querySelector("[data-relationship-page-prev]");
    if (pagePrev && !pagePrev.disabled && !pagePrev.hidden) {
      click(pagePrev);
      await delay(SELF_TEST_SETTLE_MS);
      const focusedAfterPagePrev = dumpState();
      if (!focusedAfterPagePrev.graphFocused) {
        errors.push("graph focus flag is not enabled after page prev click");
      }
    }
    pointerDown(statusFilter);
    await delay(SELF_TEST_SETTLE_MS);
    const releasedByStatus = dumpState();
    if (releasedByStatus.graphFocused) {
      errors.push("graph focus flag is still enabled after status filter pointerdown");
    }
    pointerDown(canvasWrap);
    await delay(SELF_TEST_SETTLE_MS);
    if (!dumpState().graphFocused) {
      errors.push("graph focus flag did not re-enable after second canvas wrap pointerdown");
    }
    pointerDown(selectionPanel);
    await delay(SELF_TEST_SETTLE_MS);
    const releasedBySelectionTable = dumpState();
    if (releasedBySelectionTable.graphFocused) {
      errors.push("graph focus flag is still enabled after selection table pointerdown");
    }
    explorer.scrollTop = Math.min(160, Math.max(0, explorer.scrollHeight - explorer.clientHeight));
    explorer.dispatchEvent(new Event("scroll", {bubbles: true}));
    await delay(SELF_TEST_SETTLE_MS);
    mouseDown(canvasWrap);
    click(canvasWrap);
    await delay(SELF_TEST_SETTLE_MS);
    const focusedAfterPartialScroll = dumpState();
    if (!focusedAfterPartialScroll.graphFocused) {
      errors.push("graph focus flag is not enabled after click on scrolled canvas wrap");
    }
    const selectedBeforeRelease = focused.selectedId;
    badge.click();
    await delay(SELF_TEST_SETTLE_MS);
    const released = dumpState();
    if (released.graphFocused) {
      errors.push("graph focus flag is still enabled after badge click");
    }
    if (released.focusBadgeVisible) {
      errors.push("graph focus badge is still visible after badge click");
    }
    if (released.selectedId !== selectedBeforeRelease) {
      errors.push("badge release changed selected node");
    }
    focusSelect.value = targetNode.id;
    focusSelect.dispatchEvent(new Event("change", {bubbles: true}));
    await delay(SELF_TEST_SETTLE_MS);
    const after = dumpState();
    if (!after.activeView) {
      errors.push("active view flag was cleared by node selection");
    }
    return {
      name: "graph focus badge release",
      targetNode: targetNode.id,
      initial,
      focused,
      releasedByStatus,
      releasedBySelectionTable,
      focusedAfterPartialScroll,
      released,
      after,
      durationMs: Math.round(performance.now() - startedAt),
      pass: errors.length === 0,
      errors
    };
  }

  async function runNodeTransitionBenchmark() {
    const startedAt = performance.now();
    const errors = [];
    const browser = activeBrowser();
    const focusSelect = browser && browser.querySelector("[data-relationship-node-select]");
    if (!browser || !focusSelect) {
      return {name: "node transition benchmark", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["graph controls not found"]};
    }
    let item = null;
    let state = null;
    let candidates = [];
    for (const candidate of graphMetricCandidates()) {
      candidate.button.click();
      await delay(SELF_TEST_SETTLE_MS);
      state = browser.__relationshipState;
      const graph = state && state.visibleGraph;
      const targetType = candidate.view.target_type;
      candidates = graph && graph.nodes
        ? graph.nodes.filter((node) => node.type === targetType).slice(0, 12)
        : [];
      if (candidates.length >= 2) {
        item = candidate;
        break;
      }
    }
    if (!item || !state || candidates.length < 2) {
      return {name: "node transition benchmark", pass: false, durationMs: Math.round(performance.now() - startedAt), errors: ["graph metric button not found"]};
    }
    const targetType = item.view.target_type;
    const transitions = [];
    for (const node of candidates) {
      const beforeVersion = Number(state.renderVersion || 0);
      const transitionStartedAt = performance.now();
      focusSelect.value = node.id;
      focusSelect.dispatchEvent(new Event("change", {bubbles: true}));
      const elapsedMs = performance.now() - transitionStartedAt;
      const afterVersion = Number(state.renderVersion || 0);
      if (afterVersion < beforeVersion) {
        errors.push(`render version moved backwards for ${node.id}`);
      }
      transitions.push({
        nodeId: node.id,
        elapsedMs: Math.round(elapsedMs * 100) / 100,
        renderMs: Math.round(Number(state.lastRenderDurationMs || 0) * 100) / 100,
        nodes: state.visibleGraph && state.visibleGraph.nodes ? state.visibleGraph.nodes.length : 0,
        edges: state.visibleGraph && state.visibleGraph.edges ? state.visibleGraph.edges.length : 0
      });
      await delay(0);
    }
    const batchIterations = 80;
    const beforeBatchVersion = Number(state.renderVersion || 0);
    const batchStartedAt = performance.now();
    for (let index = 0; index < batchIterations; index += 1) {
      const node = candidates[index % candidates.length];
      focusSelect.value = node.id;
      focusSelect.dispatchEvent(new Event("change", {bubbles: true}));
    }
    const batchElapsedMs = performance.now() - batchStartedAt;
    const batchRenderCount = Number(state.renderVersion || 0) - beforeBatchVersion;
    if (batchRenderCount <= 0) {
      errors.push("batch did not trigger any graph renders");
    }
    if (batchRenderCount > batchIterations) {
      errors.push(`batch render count ${batchRenderCount} > ${batchIterations}`);
    }
    return {
      name: "node transition benchmark",
      pass: errors.length === 0,
      durationMs: Math.round(performance.now() - startedAt),
      transitionStats: stats(transitions.map((item) => item.elapsedMs)),
      renderStats: stats(transitions.map((item) => item.renderMs)),
      batch: {
        iterations: batchIterations,
        elapsedMs: Math.round(batchElapsedMs * 100) / 100,
        avgMs: Math.round((batchElapsedMs / batchIterations) * 100) / 100,
        renderCount: batchRenderCount
      },
      transitions,
      errors
    };
  }

  async function runAll() {
    const startedAt = performance.now();
    const candidates = graphMetricCandidates();
    const results = [];
    results.push(await runLayoutAndScroll());
    for (const item of candidates) {
      results.push(await runMetricButton(item));
    }
    results.push(await runGraphFocusBadgeRelease());
    results.push(await runEntitySwitchReset());
    results.push(await runNodeTransitionBenchmark());
    return {
      pass: results.every((result) => result.pass),
      total: results.length,
      durationMs: Math.round(performance.now() - startedAt),
      results
    };
  }

  function writeResult(result) {
    let output = document.querySelector("[data-report-self-test-result]");
    if (!output) {
      output = document.createElement("script");
      output.type = "application/json";
      output.setAttribute("data-report-self-test-result", "");
      document.body.appendChild(output);
    }
    output.textContent = JSON.stringify(result, null, 2);
  }

  window.__reportSelfTest = {
    dumpState,
    metricButtons: () => metricButtons().map((item) => ({
      title: item.button.getAttribute("title") || String(item.button.textContent || "").trim(),
      view: item.view,
      count: metricCount(item.button)
    })),
    runAll
  };

  window.addEventListener("load", () => {
    const params = new URLSearchParams(window.location.search || "");
    if (params.get("report-self-test") !== "run") return;
    setTimeout(() => {
      runAll()
        .then(writeResult)
        .catch((error) => writeResult({pass: false, error: String(error && error.stack || error)}));
    }, 200);
  });
})();
</script>
"""
