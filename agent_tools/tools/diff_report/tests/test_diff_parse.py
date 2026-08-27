from __future__ import annotations

import textwrap
import unittest

from agent_tools.tools.diff_report.diff_parse import (
    DiffLine,
    file_from_diff_header,
    is_diff_metadata,
    iter_diff_lines,
)


class DiffParseTests(unittest.TestCase):
    def test_iter_diff_lines_tracks_file_hunks_and_line_numbers(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            index 1111111..2222222 100644
            --- a/app.py
            +++ b/app.py
            @@ -10,3 +10,4 @@
             keep()
            -old()
            +new()
             done()
            """
        )

        lines = list(iter_diff_lines(diff_text))

        self.assertEqual(
            [
                ("file", "app.py", None, None, None),
                ("metadata", "app.py", None, None, None),
                ("metadata", "app.py", None, None, None),
                ("metadata", "app.py", None, None, None),
                ("hunk", "app.py", 10, 10, None),
                ("context", "app.py", 10, 10, "keep()"),
                ("delete", "app.py", 11, None, "old()"),
                ("add", "app.py", None, 11, "new()"),
                ("context", "app.py", 12, 12, "done()"),
            ],
            [
                (line.kind, line.file_path, line.old_line, line.new_line, line.content)
                for line in lines
            ],
        )

    def test_iter_diff_lines_keeps_header_lines_before_first_hunk(self) -> None:
        diff_text = textwrap.dedent(
            """\
            diff --git a/app.py b/app.py
            custom header
            @@ -1 +1 @@
            -old
            +new
            """
        )

        lines = list(iter_diff_lines(diff_text))

        self.assertEqual("header", lines[1].kind)
        self.assertEqual("custom header", lines[1].raw)

    def test_iter_diff_lines_ignores_format_patch_footer_after_hunk(self) -> None:
        diff_text = (
            textwrap.dedent(
                """\
                diff --git a/app.py b/app.py
                index 1111111..2222222 100644
                --- a/app.py
                +++ b/app.py
                @@ -1 +1 @@
                -old
                +new
                """
            )
            + "-- \n"
            + "2.53.0\n"
        )

        lines = list(iter_diff_lines(diff_text))

        self.assertEqual(
            ["file", "metadata", "metadata", "metadata", "hunk", "delete", "add"],
            [line.kind for line in lines],
        )

    def test_iter_diff_lines_keeps_footer_like_deleted_line_inside_hunk(self) -> None:
        diff_text = (
            textwrap.dedent(
                """\
                diff --git a/app.py b/app.py
                @@ -1,2 +1 @@
                """
            )
            + "-- \n"
            + " keep\n"
        )

        lines = list(iter_diff_lines(diff_text))

        self.assertEqual("delete", lines[2].kind)
        self.assertEqual("- ", lines[2].content)
        self.assertEqual("context", lines[3].kind)

    def test_metadata_and_header_helpers_match_git_diff_headers(self) -> None:
        self.assertEqual("new/path.py", file_from_diff_header("diff --git a/old/path.py b/new/path.py"))
        self.assertEqual("not a git header", file_from_diff_header("not a git header"))

        for line in (
            "--- a/app.py",
            "+++ b/app.py",
            "index 1111111..2222222 100644",
            "new file mode 100644",
            "deleted file mode 100644",
            "similarity index 88%",
            "rename from old.py",
            "rename to new.py",
            "old mode 100755",
            "new mode 100644",
        ):
            with self.subTest(line=line):
                self.assertTrue(is_diff_metadata(line))

        self.assertFalse(is_diff_metadata(" context()"))

    def test_diff_line_is_frozen_value_object(self) -> None:
        line = DiffLine(kind="context", raw=" keep()", file_path="app.py", old_line=1, new_line=1)

        with self.assertRaises(Exception):
            line.kind = "add"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
