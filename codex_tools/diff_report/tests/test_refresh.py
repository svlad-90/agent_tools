from __future__ import annotations

import contextlib
import io
import json
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

from codex_tools.diff_report.refresh import (
    diff_line_targets,
    enrich_comments_payload,
    inline_sort_key,
    print_refresh_attention,
)


class RefreshTests(unittest.TestCase):
    def test_diff_line_targets_records_added_and_context_lines(self) -> None:
        targets = diff_line_targets(
            textwrap.dedent(
                """\
                diff --git a/app.py b/app.py
                index 1111111..2222222 100644
                --- a/app.py
                +++ b/app.py
                @@ -1,2 +1,3 @@
                 keep()
                +added()
                 done()
                """
            )
        )

        self.assertEqual("context", targets[("app.py", 1)]["kind"])
        self.assertEqual("keep()", targets[("app.py", 1)]["content"])
        self.assertEqual("add", targets[("app.py", 2)]["kind"])
        self.assertEqual("added()", targets[("app.py", 2)]["content"])
        self.assertEqual("context", targets[("app.py", 3)]["kind"])

    def test_enrich_comments_payload_marks_found_moved_ambiguous_and_not_found(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1,4 +1,5 @@
             def run():
            +    inserted()
                moved()
                duplicate()
                duplicate()
            """
        )
        payload = {
            "inline": [
                {"file": "app.py", "line": 2, "body": "found"},
                {
                    "file": "app.py",
                    "line": 50,
                    "range": {"start": 50, "end": 50},
                    "body": "moved",
                    "target": {"content": "   moved()"},
                },
                {
                    "file": "app.py",
                    "line": 51,
                    "body": "ambiguous",
                    "target": {"content": "   duplicate()"},
                },
                {
                    "file": "app.py",
                    "line": 52,
                    "body": "missing",
                    "target": {"content": "    missing()"},
                },
            ]
        }

        enriched = enrich_comments_payload(diff_text, payload)

        inline = enriched["inline"]
        self.assertEqual(["found", "moved", "ambiguous", "not_found"], [item["target"]["status"] for item in inline])
        self.assertEqual(2, inline[0]["line"])
        self.assertEqual(3, inline[1]["line"])
        self.assertEqual({"start": 3, "end": 3}, inline[1]["range"])
        self.assertEqual(50, inline[1]["target"]["previous_line"])
        self.assertEqual([4, 5], inline[2]["target"]["candidate_lines"])
        self.assertFalse(inline[3]["target"]["found"])

    def test_enrich_comments_payload_moves_when_line_exists_but_content_changed(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1,4 +1,5 @@
             def run():
                new_neighbor()
                keep_target()
                done()
            """
        )
        payload = {
            "inline": [
                {
                    "file": "app.py",
                    "line": 2,
                    "range": {"start": 2, "end": 2},
                    "body": "semantic target",
                    "target": {"content": "   keep_target()"},
                },
            ]
        }

        enriched = enrich_comments_payload(diff_text, payload)

        inline = enriched["inline"]
        self.assertEqual("moved", inline[0]["target"]["status"])
        self.assertEqual(3, inline[0]["line"])
        self.assertEqual({"start": 3, "end": 3}, inline[0]["range"])
        self.assertEqual(2, inline[0]["target"]["previous_line"])

    def test_enrich_comments_payload_refreshes_diagram_code_links_by_content(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1,5 +1,6 @@
             def run():
                new_neighbor()
                keep_target()
                duplicate()
                duplicate()
            """
        )
        payload = {
            "diagrams": {
                "flow": {
                    "title": "Flow",
                    "svg_inline": "<svg></svg>",
                    "code_links": [
                        {
                            "target": "call target",
                            "file": "app.py",
                            "line": 2,
                            "title": "Moved link",
                            "target_info": {"content": "   keep_target()"},
                        },
                        {
                            "target": "ambiguous target",
                            "file": "app.py",
                            "line": 20,
                            "title": "Ambiguous link",
                            "target_info": {"content": "   duplicate()"},
                        },
                    ],
                }
            }
        }

        enriched = enrich_comments_payload(diff_text, payload)

        links = enriched["diagrams"]["flow"]["code_links"]
        self.assertEqual("call target", links[0]["target"])
        self.assertEqual(3, links[0]["line"])
        self.assertEqual("moved", links[0]["target_info"]["status"])
        self.assertEqual(2, links[0]["target_info"]["previous_line"])
        self.assertEqual("ambiguous", links[1]["target_info"]["status"])
        self.assertEqual([4, 5], links[1]["target_info"]["candidate_lines"])

    def test_inline_sort_key_orders_statuses_before_file_line_title(self) -> None:
        items: list[dict[str, Any]] = [
            {"file": "b.py", "line": 1, "title": "b", "target": {"status": "not_found"}},
            {"file": "a.py", "line": 2, "title": "a", "target": {"status": "found"}},
            {"file": "a.py", "line": 1, "title": "a", "target": {"status": "ambiguous"}},
            {"file": "a.py", "line": 1, "title": "b", "target": {"status": "moved"}},
        ]

        ordered = sorted(items, key=inline_sort_key)

        self.assertEqual(["found", "moved", "ambiguous", "not_found"], [item["target"]["status"] for item in ordered])

    def test_print_refresh_attention_reports_moved_and_attention_counts(self) -> None:
        payload = {
            "inline": [
                {"file": "app.py", "line": 3, "title": "Moved", "target": {"status": "moved"}},
                {"file": "app.py", "line": 4, "title": "Ambiguous", "target": {"status": "ambiguous"}},
                {"file": "app.py", "line": 5, "title": "Missing", "target": {"status": "not_found"}},
                {
                    "file": "app.py",
                    "line": 8,
                    "title": "Wide",
                    "range": {"start": 8, "end": 10},
                    "target": {"status": "found"},
                },
                {
                    "file": "app.py",
                    "line": 10,
                    "title": "Overlap",
                    "range": {"start": 10, "end": 11},
                    "target": {"status": "found"},
                },
            ],
            "diagrams": {
                "flow": {
                    "code_links": [
                        {
                            "target": "node",
                            "file": "app.py",
                            "line": 12,
                            "title": "Moved diagram link",
                            "target_info": {"status": "moved"},
                        },
                        {
                            "target": "other",
                            "file": "app.py",
                            "line": 13,
                            "title": "Missing diagram link",
                            "target_info": {"status": "not_found"},
                        },
                    ]
                }
            },
        }
        comments_json = json.dumps(payload, indent=2)
        stdout = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "comments.json"
            with contextlib.redirect_stdout(stdout):
                print_refresh_attention(path, payload, comments_json)

        output = stdout.getvalue()
        self.assertIn("moved=2 auto-updated", output)
        self.assertIn("attention=4", output)
        self.assertIn("ambiguous app.py:4 Ambiguous", output)
        self.assertIn("not_found app.py:5 Missing", output)
        self.assertIn("overlap app.py:8-10 Wide overlaps 10-11 Overlap", output)
        self.assertIn("diagram flow: not_found app.py:13 Missing diagram link", output)


if __name__ == "__main__":
    unittest.main()
