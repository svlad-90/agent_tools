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
            "Product architecture",
            'data-diagram-id="flow"',
            'id="diagram-template-flow"',
            'id="log-template-status"',
            "security risk",
            'data-story-diagram="flow"',
            "report-settings-launcher",
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
        ]
        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DiffReportError, re.escape(message)):
                    report_from_payload(payload)

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
