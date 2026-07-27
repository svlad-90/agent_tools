from __future__ import annotations

import unittest

from codex_tools.diff_report.models import DiffReportError, InlineComment, ReviewComments
from codex_tools.diff_report.render_diff import diff_row, render_diff


class RenderDiffTests(unittest.TestCase):
    def test_diff_row_escapes_values_and_adds_line_attributes(self) -> None:
        row = diff_row(
            "add",
            "",
            "3",
            '+print("<x>")',
            "src/app.py",
            3,
            ("comment-target",),
        )

        self.assertIn('class="add comment-target"', row)
        self.assertIn('id="line-src-app.py-3"', row)
        self.assertIn('data-file="src/app.py"', row)
        self.assertIn('+print(&quot;&lt;x&gt;&quot;)', row)

    def test_render_diff_uses_callbacks_for_file_and_inline_assets(self) -> None:
        comments = ReviewComments(
            summary="",
            diagrams={},
            logs={},
            story=[],
            file_comments={"src/app.py": "File note"},
            file_diagrams={},
            file_logs={},
            file_diagram_focus={},
            file_log_focus={},
            file_diagram_notes={},
            inline_comments={
                ("src/app.py", 2): [
                    InlineComment(
                        file_path="src/app.py",
                        line=2,
                        title="Line note",
                        body="Body",
                        line_range=(2, 2),
                    )
                ]
            },
        )
        diff_text = "\n".join(
            [
                "diff --git a/src/app.py b/src/app.py",
                "index 1111111..2222222 100644",
                "--- a/src/app.py",
                "+++ b/src/app.py",
                "@@ -1 +1,2 @@",
                " unchanged",
                "+added",
                "",
            ]
        )

        html = render_diff(
            diff_text,
            comments,
            render_file_comment_assets=lambda file_path: f"<span>{file_path}</span>",
            render_inline_comment_assets=lambda comment: f"<em>{comment.title}</em>",
        )

        self.assertIn('<article class="file" id="src-app.py"', html)
        self.assertIn("<strong>File review note:</strong> File note<span>src/app.py</span>", html)
        self.assertIn(
            '<tr class="add comment-target comment-target-start comment-target-end comment-target-single"',
            html,
        )
        self.assertIn('<tr class="comment-row comment-row-add"><td colspan="3">', html)
        self.assertIn('<em>Line note</em>', html)

    def test_render_diff_rejects_inline_comment_without_rendered_target_line(self) -> None:
        comments = ReviewComments(
            summary="",
            diagrams={},
            logs={},
            story=[],
            file_comments={},
            file_diagrams={},
            file_logs={},
            file_diagram_focus={},
            file_log_focus={},
            file_diagram_notes={},
            inline_comments={
                ("src/app.py", 30): [
                    InlineComment(file_path="src/app.py", line=30, title="Missing", body="Body")
                ]
            },
        )
        diff_text = "\n".join(
            [
                "diff --git a/src/app.py b/src/app.py",
                "--- a/src/app.py",
                "+++ b/src/app.py",
                "@@ -1 +1 @@",
                "+added",
                "",
            ]
        )

        with self.assertRaisesRegex(DiffReportError, "target is not rendered"):
            render_diff(diff_text, comments)

    def test_render_diff_rejects_inline_comment_range_with_missing_end_line(self) -> None:
        comments = ReviewComments(
            summary="",
            diagrams={},
            logs={},
            story=[],
            file_comments={},
            file_diagrams={},
            file_logs={},
            file_diagram_focus={},
            file_log_focus={},
            file_diagram_notes={},
            inline_comments={
                ("src/app.py", 1): [
                    InlineComment(
                        file_path="src/app.py",
                        line=1,
                        title="Partial range",
                        body="Body",
                        line_range=(1, 4),
                    )
                ]
            },
        )
        diff_text = "\n".join(
            [
                "diff --git a/src/app.py b/src/app.py",
                "--- a/src/app.py",
                "+++ b/src/app.py",
                "@@ -1 +1,2 @@",
                "+added",
                "+more",
                "",
            ]
        )

        with self.assertRaisesRegex(DiffReportError, "range is not fully rendered"):
            render_diff(diff_text, comments)

    def test_render_diff_rejects_overlapping_inline_comment_ranges(self) -> None:
        comments = ReviewComments(
            summary="",
            diagrams={},
            logs={},
            story=[],
            file_comments={},
            file_diagrams={},
            file_logs={},
            file_diagram_focus={},
            file_log_focus={},
            file_diagram_notes={},
            inline_comments={
                ("src/app.py", 3): [
                    InlineComment(
                        file_path="src/app.py",
                        line=3,
                        title="First block",
                        body="Body",
                        line_range=(2, 4),
                    )
                ],
                ("src/app.py", 5): [
                    InlineComment(
                        file_path="src/app.py",
                        line=5,
                        title="Second block",
                        body="Body",
                        line_range=(4, 5),
                    )
                ],
            },
        )
        diff_text = "\n".join(
            [
                "diff --git a/src/app.py b/src/app.py",
                "--- a/src/app.py",
                "+++ b/src/app.py",
                "@@ -1 +1,5 @@",
                "+one",
                "+two",
                "+three",
                "+four",
                "+five",
                "",
            ]
        )

        with self.assertRaisesRegex(
            DiffReportError,
            "inline comment ranges overlap in diff: src/app.py:2-4 .*src/app.py:4-5",
        ):
            render_diff(diff_text, comments)


if __name__ == "__main__":
    unittest.main()
