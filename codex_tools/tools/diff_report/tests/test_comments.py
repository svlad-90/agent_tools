from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codex_tools.tools.diff_report.comments import (
    comment_line_range,
    comments_from_payload,
    load_comments,
    normalize_svg,
)
from codex_tools.tools.diff_report.models import DiffReportError


class CommentsTests(unittest.TestCase):
    def test_load_comments_resolves_relative_assets_and_normalizes_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "diagram.svg").write_text(
                "<?xml version='1.0'?><svg><text>flow</text></svg>",
                encoding="utf-8",
            )
            (root / "runtime.log").write_text("boot\nPASS\n", encoding="utf-8")
            comments_path = root / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "commit": {"id": "abc123", "message": "Subject\n\nBody"},
                        "summary": "Summary text",
                        "vocabulary": {
                            "vCPU": {
                                "definition": "Virtual CPU exposed by Xen to the guest.",
                                "aliases": ["vCPUs", "virtual CPU"],
                            },
                            "hypercall": "Controlled guest call into Xen.",
                        },
                        "summary_blocks": [
                            "plain block",
                            {"type": "paragraph", "text": "paragraph block"},
                            {"diagram": "flow", "diagram_focus": "flow"},
                            {"log": "runtime", "log_focus": ["PASS"]},
                        ],
                        "files": {
                            "app.py": {
                                "body": "file note",
                                "diagram": "flow",
                                "diagram_focus": ["flow"],
                                "diagram_notes": [{"target": "flow", "text": "diagram note"}],
                                "log": "runtime",
                                "log_focus": "PASS",
                            },
                        },
                        "inline": [
                            {
                                "file": "app.py",
                                "line": 2,
                                "range": {"start": 1, "end": 3},
                                "body": "inline note",
                                "title": "Inline",
                                "diagram": "flow",
                                "diagram_focus": "flow",
                                "log": "runtime",
                                "log_focus": "PASS",
                            },
                        ],
                        "diagrams": {"flow": {"svg": "diagram.svg"}},
                        "logs": {"runtime": {"path": "runtime.log"}},
                        "story": [
                            {
                                "title": "Step",
                                "diagram": "flow",
                                "diagram_focus": "flow",
                                "diagram_zoom": 1.8,
                                "artifact_comment": "Look at this object.",
                            },
                            {
                                "title": "Log Step",
                                "log": "runtime",
                                "log_focus": "PASS",
                                "log_zoom": 1.3,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            comments = load_comments(comments_path)

        self.assertEqual("abc123", comments.commit_id)
        self.assertEqual("Subject\n\nBody", comments.commit_message)
        self.assertEqual("Summary text", comments.summary)
        self.assertEqual("vCPU", comments.vocabulary[0].term)
        self.assertEqual("Virtual CPU exposed by Xen to the guest.", comments.vocabulary[0].definition)
        self.assertEqual(("vCPUs", "virtual CPU"), comments.vocabulary[0].aliases)
        self.assertEqual("hypercall", comments.vocabulary[1].term)
        self.assertEqual("Controlled guest call into Xen.", comments.vocabulary[1].definition)
        self.assertEqual("file note", comments.file_comments["app.py"])
        self.assertEqual(("flow",), comments.file_diagram_focus["app.py"])
        self.assertEqual(("PASS",), comments.file_log_focus["app.py"])
        self.assertIn("<svg>", comments.diagrams["flow"].svg)
        self.assertEqual("boot\nPASS\n", comments.logs["runtime"].text)
        self.assertEqual(4, len(comments.summary_blocks))
        self.assertEqual("Step", comments.story[0].title)
        self.assertEqual(("flow",), comments.story[0].diagram_focus)
        self.assertEqual(1.8, comments.story[0].diagram_zoom)
        self.assertEqual("Look at this object.", comments.story[0].artifact_comment)
        self.assertEqual(("PASS",), comments.story[1].log_focus)
        self.assertEqual(1.3, comments.story[1].log_zoom)
        inline = comments.inline_comments[("app.py", 2)][0]
        self.assertEqual((1, 3), inline.line_range)
        self.assertEqual(("flow",), inline.diagram_focus)
        self.assertEqual(("PASS",), inline.log_focus)

    def test_comment_line_range_accepts_object_and_array_forms(self) -> None:
        self.assertEqual((2, 4), comment_line_range({"start": 2, "end": 4}, line=3))
        self.assertEqual((2, 4), comment_line_range([2, 4], line=3))
        self.assertIsNone(comment_line_range(None, line=3))

    def test_comment_line_range_rejects_invalid_ranges(self) -> None:
        cases = [
            ({"start": 4, "end": 2}, 3),
            ([2, 4], 5),
            ("2-4", 3),
        ]
        for raw_range, line in cases:
            with self.subTest(raw_range=raw_range, line=line):
                with self.assertRaises(DiffReportError):
                    comment_line_range(raw_range, line=line)

    def test_comments_from_payload_rejects_invalid_schema_and_unknown_assets(self) -> None:
        cases = [
            ({"files": []}, "comments.files must be an object"),
            ({"inline": {}}, "comments.inline must be a list"),
            ({"inline": [{"file": "app.py", "line": 1, "body": ""}]}, "non-empty body"),
            (
                {"inline": [{"file": "app.py", "line": 1, "title": "", "body": "note"}]},
                "non-empty title",
            ),
            ({"inline": [{"file": "app.py", "line": 1, "body": "note", "diagram": "missing"}]}, "unknown diagram"),
            ({"inline": [{"file": "app.py", "line": 1, "body": "note", "log": "missing"}]}, "unknown log"),
            ({"story": [{"title": "No target"}]}, "must target"),
            ({"summary_blocks": [{"type": "unknown"}]}, "unknown summary block type"),
            ({"vocabulary": []}, "comments.vocabulary must be an object"),
            ({"vocabulary": {"vCPU": {}}}, "definition"),
            ({"vocabulary": {"vCPU": {"definition": "Virtual CPU", "aliases": {}}}}, "aliases"),
        ]
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DiffReportError, message):
                    comments_from_payload(payload)

    def test_normalize_svg_rejects_non_svg_and_script_tags(self) -> None:
        with self.assertRaisesRegex(DiffReportError, "does not look like SVG"):
            normalize_svg("<html></html>", source="inline")
        with self.assertRaisesRegex(DiffReportError, "must not contain script"):
            normalize_svg("<svg><script>alert(1)</script></svg>", source="inline")


if __name__ == "__main__":
    unittest.main()
