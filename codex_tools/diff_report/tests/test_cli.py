from __future__ import annotations

import contextlib
import io
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from codex_tools.diff_report.cli import main


class CliTests(unittest.TestCase):
    def test_help_compact_prints_synopsis_without_requiring_output(self) -> None:
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            status = main(["--help-compact"])

        self.assertEqual(0, status)
        self.assertIn("diff_report --repo", stdout.getvalue())

    def test_missing_output_is_argparse_error(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["--diff-file", "change.patch"])

        self.assertEqual(2, raised.exception.code)
        self.assertIn("--output is required", stderr.getvalue())

    def test_generates_report_from_diff_file_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output_path = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    index 1111111..2222222 100644
                    --- a/app.py
                    +++ b/app.py
                    @@ -1 +1,2 @@
                     keep()
                    +added()
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps({"inline": [{"file": "app.py", "line": 2, "body": "CLI note"}]}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                status = main(
                    [
                        "--diff-file",
                        str(diff_path),
                        "--comments",
                        str(comments_path),
                        "--output",
                        str(output_path),
                        "--title",
                        "CLI report",
                    ]
                )

            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(0, status)
        self.assertEqual(f"{output_path}\n", stdout.getvalue())
        self.assertIn("<h1>CLI report</h1>", html)
        self.assertIn("CLI note", html)

    def test_refresh_targets_writes_json_next_to_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output_path = root / "report.html"
            refreshed_path = root / "report.json"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    index 1111111..2222222 100644
                    --- a/app.py
                    +++ b/app.py
                    @@ -1 +1,2 @@
                     keep()
                    +added()
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps({"inline": [{"file": "app.py", "line": 2, "body": "Refresh note"}]}),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                status = main(
                    [
                        "--diff-file",
                        str(diff_path),
                        "--comments",
                        str(comments_path),
                        "--output",
                        str(output_path),
                        "--refresh-targets",
                    ]
                )

            refreshed = json.loads(refreshed_path.read_text(encoding="utf-8"))
            output_exists = output_path.exists()

        self.assertEqual(0, status)
        self.assertTrue(output_exists)
        self.assertEqual("found", refreshed["inline"][0]["target"]["status"])
        self.assertIn("attention=0", stdout.getvalue())
        self.assertIn(str(output_path), stdout.getvalue())

    def test_generation_error_returns_one_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.html"
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                status = main(["--output", str(output_path)])

        self.assertEqual(1, status)
        self.assertIn("--repo is required unless --diff-file is used", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
