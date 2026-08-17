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
class GenericReport:
    title: str
    comments: ReviewComments
    metrics: tuple[ReportMetric, ...] = ()
    status_cards: tuple[ReportStatusCard, ...] = ()
    heatmaps: tuple[ReportHeatmap, ...] = ()
    tables: tuple[ReportTable, ...] = ()
    timeline: tuple[ReportTimelineItem, ...] = ()
    artifacts: tuple[ReportArtifact, ...] = ()


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
    parts.append("  <ol>\n")
    for label, href in items:
        parts.append(f'    <li><a href="{_esc(href)}">{_esc(label)}</a></li>\n')
    parts.append("  </ol>\n</nav>\n")
    return "".join(parts)


def _report_toc_items(report: GenericReport) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = [("Top", "#report-top")]
    if report.comments.summary or report.comments.summary_blocks:
        items.append(("Summary", "#summary-section"))
    if report.metrics:
        items.append(("Metrics", "#report-metrics"))
    if report.status_cards:
        items.append(("Status Cards", "#report-status-cards"))
    if report.heatmaps:
        items.append(("Heatmaps", "#report-heatmaps"))
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
  document.addEventListener("click", (event) => {
    const link = event.target.closest && event.target.closest(".report-toc a[href^='#']");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    const target = document.getElementById(href.slice(1));
    if (!target) return;
    event.preventDefault();
    event.stopPropagation();
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
