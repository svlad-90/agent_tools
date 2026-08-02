from __future__ import annotations

import textwrap
import unittest

from codex_tools.tools.diff_report.comments_compose import (
    compose_comments_payload,
    compose_comments_payload_with_diagnostics,
)
from codex_tools.tools.diff_report.models import DiffReportError


class CommentsComposeTests(unittest.TestCase):
    def test_compose_comments_payload_resolves_inline_findings_by_content(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1 +1,3 @@
             keep()
            +first()
            +second()
            """
        )
        findings = {
            "summary": "Review summary",
            "files": [{"file": "app.py", "body": "File note"}],
            "inline": [
                {
                    "file": "app.py",
                    "content": "second()",
                    "kind": "add",
                    "title": "Second call",
                    "body": "Inline note",
                }
            ],
        }

        comments = compose_comments_payload(diff_text, findings)

        self.assertEqual("Review summary", comments["summary"])
        self.assertEqual({"app.py": "File note"}, comments["files"])
        self.assertEqual(3, comments["inline"][0]["line"])
        self.assertEqual("Second call", comments["inline"][0]["title"])
        self.assertEqual("found", comments["inline"][0]["target"]["status"])
        self.assertEqual("+second()", comments["inline"][0]["target"]["diff_line"])

    def test_compose_comments_payload_rejects_ambiguous_contains_match(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1 +1,3 @@
             keep()
            +duplicate()
            +duplicate()
            """
        )
        findings = {
            "inline": [
                {
                    "file": "app.py",
                    "contains": "duplicate",
                    "body": "Inline note",
                }
            ]
        }

        with self.assertRaisesRegex(DiffReportError, "ambiguous"):
            compose_comments_payload(diff_text, findings)

    def test_compose_comments_payload_with_diagnostics_keeps_resolved_findings(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -1 +1,4 @@
             keep()
            +resolved()
            +duplicate()
            +duplicate()
            """
        )
        findings = {
            "inline": [
                {"file": "app.py", "contains": "resolved", "body": "Resolved note"},
                {"file": "app.py", "contains": "missing", "body": "Missing note"},
                {"file": "app.py", "contains": "duplicate", "body": "Ambiguous note"},
            ]
        }

        comments, diagnostics = compose_comments_payload_with_diagnostics(diff_text, findings)

        self.assertEqual(1, len(comments["inline"]))
        self.assertEqual("Resolved note", comments["inline"][0]["body"])
        self.assertEqual([1, 2], [diagnostic["index"] for diagnostic in diagnostics])
        self.assertIn("not found", diagnostics[0]["message"])
        self.assertIn("ambiguous", diagnostics[1]["message"])


if __name__ == "__main__":
    unittest.main()
