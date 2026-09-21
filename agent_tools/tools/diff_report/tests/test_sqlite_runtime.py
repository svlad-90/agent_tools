from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from agent_tools.tools.diff_report.cli import main
from agent_tools.tools.diff_report.report_json import render_report_json_html, report_from_payload
from agent_tools.tools.diff_report.sqlite_runtime import build_single_html
from agent_tools.tools.diff_report.sqlite_store import create_schema, query_report, read_report, write_report


def sample_report() -> dict:
    return {
        "title": "Inventory",
        "relationship_graph": {
            "nodes": [
                {"id": "scope", "type": "collection", "label": "Inventory"},
                {"id": "part", "type": "component", "label": "Part A"},
            ],
            "edges": [{"source": "scope", "target": "part", "relation": "contains"}],
        },
    }


class SQLiteRuntimeTests(unittest.TestCase):
    def test_store_roundtrip_and_search(self) -> None:
        with closing(sqlite3.connect(":memory:")) as connection:
            create_schema(connection)
            payload = sample_report()
            write_report(connection, payload)

            self.assertEqual(payload["relationship_graph"]["nodes"], read_report(connection)["relationship_graph"]["nodes"])
            self.assertEqual(1, query_report(connection, "search", {"q": "Part", "limit": "1"})["count"])
            with self.assertRaisesRegex(ValueError, "requires q"):
                query_report(connection, "search", {})

    def test_single_html_embeds_database_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "report.sqlite3"
            with closing(sqlite3.connect(database)) as connection:
                create_schema(connection)
                write_report(connection, sample_report())
                connection.commit()
                html = render_report_json_html(report_from_payload(read_report(connection)))
            source = root / "report.html"
            source.write_text(html, encoding="utf-8")
            single = root / "report.single.html"

            build_single_html(source, database, single)

            document = single.read_text(encoding="utf-8")
            self.assertIn("embedded-evidence-load-status", document)
            self.assertIn("window.__diffReportData", document)
            self.assertIn('"data_source":"sqlite"', document)
            self.assertNotIn('"id":"scope"', document)

    def test_cli_writes_sqlite_and_single_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            html = root / "report.html"
            database = root / "report.sqlite3"
            single_html = root / "report.single.html"
            report.write_text(json.dumps(sample_report()), encoding="utf-8")

            status = main([
                "--report-json", str(report), "--output", str(html),
                "--sqlite-output", str(database), "--single-html-output", str(single_html),
            ])

            self.assertEqual(0, status)
            self.assertTrue(database.is_file())
            document = single_html.read_text(encoding="utf-8")
            self.assertIn("embedded-evidence-load-status", document)
            self.assertIn('"data_source":"sqlite"', document)

            self.assertEqual(0, main([
                "--report-json", str(report), "--output", str(html),
                "--sqlite-output", str(database), "--single-html-output", str(single_html),
            ]))
