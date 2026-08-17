from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from agent_tools.tools.diff_report.models import DiffReportError
from agent_tools.tools.diff_report.report_json import (
    render_report_json_html,
    report_from_payload,
)


class ReportJsonTests(unittest.TestCase):
    def test_renders_dashboard_widgets_and_shared_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_path = root / "status.log"
            log_path.write_text("security risk\ncts pending\n", encoding="utf-8")
            payload = {
                "title": "Gen5 CDD/VSR Dashboard",
                "summary_blocks": [
                    {"type": "text", "body": "Current focus is security."},
                    {"type": "diagram", "diagram": "flow", "diagram_focus": "VSR"},
                    {"type": "log", "log": "status", "log_focus": "risk"},
                ],
                "metrics": [
                    {"label": "VSR rows", "value": 115, "status": "covered_candidate"},
                    {"label": "Risks", "value": 4, "status": "risk", "note": "Security first pass"},
                ],
                "status_cards": [
                    {
                        "title": "security",
                        "status": "risk",
                        "body": "SELinux and KeyMint need production evidence.",
                        "metrics": [{"label": "rows", "value": 10}],
                        "links": [{"label": "Security pass", "href": "../domains/security/VSR_SECURITY_PASS.md"}],
                    }
                ],
                "heatmaps": [
                    {
                        "title": "Domain Heatmap",
                        "rows": [
                            {"domain": "security", "status": "risk", "total": 10},
                            {"domain": "storage_update", "status": "covered_candidate", "total": 4},
                        ],
                    }
                ],
                "tables": [
                    {
                        "title": "Requirement Queue",
                        "columns": ["id", "domain", "status", "evidence"],
                        "rows": [
                            {
                                "id": "VSR-3.10-023",
                                "domain": "security",
                                "status": "risk",
                                "evidence": {"text": "Open diagram", "diagram": "flow"},
                            }
                        ],
                    }
                ],
                "timeline": [
                    {"time": "2026-08-17", "title": "Security pass created", "status": "risk"}
                ],
                "relationship_graph": {
                    "title": "Requirement Traceability",
                    "nodes": [
                        {
                            "id": "vsr:VSR-1",
                            "type": "vsr",
                            "label": "AIDL for HALs",
                            "status": "risk",
                            "summary": "HALs must use AIDL.",
                            "details": {"current_status": "HIDL remains."},
                        },
                        {
                            "id": "hal:audio@6.0",
                            "type": "hal",
                            "label": "audio@6.0",
                            "status": "risk",
                        },
                    ],
                    "edges": [
                        {
                            "source": "vsr:VSR-1",
                            "target": "hal:audio@6.0",
                            "relation": "maps_to_hal",
                        }
                    ],
                },
                "artifacts": [
                    {
                        "title": "Product architecture",
                        "path": "../analysis/product/architecture/PRODUCT_ARCHITECTURE.md",
                        "kind": "markdown",
                        "note": "evidence",
                    }
                ],
                "diagrams": {
                    "flow": {
                        "title": "Requirement flow",
                        "svg_inline": "<svg xmlns='http://www.w3.org/2000/svg'><text>VSR</text></svg>",
                    }
                },
                "logs": {"status": {"title": "Status log", "path": "status.log"}},
                "story": [
                    {
                        "title": "Start with security",
                        "body": "This is the highest-risk domain.",
                        "diagram": "flow",
                    }
                ],
            }

            report = report_from_payload(payload, base_dir=root)
            html = render_report_json_html(report)

        expected = [
            "<h1>Gen5 CDD/VSR Dashboard</h1>",
            "Current focus is security.",
            "report-metric-grid",
            "VSR rows",
            "Security first pass",
            "report-card status-risk",
            "SELinux and KeyMint need production evidence.",
            "Domain Heatmap",
            "report-heatmap-cell status-risk",
            "Requirement Queue",
            'data-report-table-filter="report-table-1"',
            "VSR-3.10-023",
            "Security pass created",
            "Requirement Traceability",
            'id="report-relationship-graph"',
            'data-relationship-browser',
            'data-relationship-graph-data',
            'data-relationship-fit',
            "AIDL for HALs",
            "maps_to_hal",
            "The Cytoscape Consortium",
            "cytoscape({",
            "wheelSensitivity",
            'document.createElement("optgroup")',
            "Product architecture",
            'data-diagram-id="flow"',
            'id="diagram-template-flow"',
            'id="log-template-status"',
            "security risk",
            'data-story-diagram="flow"',
            "report-settings-launcher",
            '<nav class="report-toc"',
            '<a href="#report-table-1">Requirement Queue</a>',
            'id="report-top"',
            'id="summary-section"',
            'id="report-metrics"',
            'id="report-status-cards"',
            'id="report-heatmaps"',
            'id="report-timeline"',
            'id="report-relationship-graph"',
            'id="report-artifacts"',
            'id="report-diagrams"',
            'id="report-logs"',
            'document.addEventListener("click", (event) => {',
            "function setActiveToc(id, reveal)",
            "function currentReadableTocId()",
            "const probeY = 112;",
            "if (rect.top > probeY)",
            'entry.link.setAttribute("aria-current", "location");',
            'window.addEventListener("scroll", scheduleActiveTocUpdate, {passive: true});',
            'setActiveToc(href.slice(1), true);',
            'target.scrollIntoView({block: "start", inline: "nearest"});',
            "function buildNeighborhood(selectedId, depth, nodesById, edges)",
            "data-relationship-jump",
        ]
        for fragment in expected:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)

    def test_validates_widget_shapes(self) -> None:
        invalid_payloads = [
            ({"title": "Broken", "metrics": {}}, "report.metrics must be a list"),
            (
                {"title": "Broken", "status_cards": [{"status": "risk"}]},
                "report.status_cards[0].title is required",
            ),
            (
                {"title": "Broken", "tables": [{"columns": [], "rows": []}]},
                "report.tables[0].columns must be a non-empty list",
            ),
            ({"title": "Broken", "timeline": ["bad"]}, "report.timeline[0] must be an object"),
            ({"title": "Broken", "toc_groups": {}}, "report.toc_groups must be a list"),
            (
                {"title": "Broken", "toc_groups": [{"title": "Overview", "items": []}]},
                "report.toc_groups[0].items must be a non-empty list",
            ),
            (
                {"title": "Broken", "toc_groups": [{"title": "Overview", "items": [{"label": "Top", "href": "top"}]}]},
                "report.toc_groups[0].items[0].href must start with #",
            ),
            ({"title": "Broken", "relationship_graph": []}, "report.relationship_graph must be an object"),
            (
                {"title": "Broken", "relationship_graph": {"nodes": [], "edges": []}},
                "report.relationship_graph.nodes must be a non-empty list",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [{"source": "a", "target": "missing"}],
                    },
                },
                "report.relationship_graph.edges[0].target references missing node missing",
            ),
        ]
        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DiffReportError, re.escape(message)):
                    report_from_payload(payload)

    def test_renders_grouped_toc_when_requested(self) -> None:
        payload = {
            "title": "Dashboard",
            "metrics": [{"label": "Risks", "value": 2}],
            "tables": [
                {"title": "Top Blockers", "columns": ["domain"], "rows": [{"domain": "security"}]},
                {"title": "Security VSR Rows", "columns": ["id"], "rows": [{"id": "VSR-1"}]},
            ],
            "toc_groups": [
                {
                    "title": "Overview",
                    "items": [
                        {"label": "Top", "href": "#report-top"},
                        {"label": "Metrics", "href": "#report-metrics"},
                    ],
                },
                {
                    "title": "VSR Rows",
                    "open": False,
                    "items": [{"label": "Security", "href": "#report-table-2"}],
                },
            ],
        }

        html = render_report_json_html(report_from_payload(payload))

        self.assertIn('<div class="report-toc-tree">', html)
        self.assertIn('<summary>Overview</summary>', html)
        self.assertIn('<details class="report-toc-group">', html)
        self.assertIn('<a href="#report-table-2">Security</a>', html)
        self.assertIn('const group = entry.link.closest(".report-toc-group");', html)

    def test_loads_from_file_relative_artifacts(self) -> None:
        from agent_tools.tools.diff_report.report_json import load_report_json

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "runtime.log").write_text("PASS\n", encoding="utf-8")
            report_path = root / "dashboard.json"
            report_path.write_text(
                json.dumps(
                    {
                        "title": "Dashboard",
                        "logs": {"runtime": {"title": "Runtime", "path": "runtime.log"}},
                        "summary_blocks": [{"type": "log", "log": "runtime"}],
                    }
                ),
                encoding="utf-8",
            )

            report = load_report_json(report_path)

        self.assertEqual("Dashboard", report.title)
        self.assertEqual("PASS\n", report.comments.logs["runtime"].text)
