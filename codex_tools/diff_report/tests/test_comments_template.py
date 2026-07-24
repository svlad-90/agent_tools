from __future__ import annotations

import textwrap
import unittest

from codex_tools.diff_report.comments_template import build_comments_template


class CommentsTemplateTests(unittest.TestCase):
    def test_build_comments_template_targets_added_lines(self) -> None:
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

        template = build_comments_template(diff_text, title_prefix="Check")

        self.assertEqual({}, template["files"])
        self.assertEqual([], template["inline"])
        self.assertEqual(["app.py"], template["_template"]["files"])
        added_lines = template["_template"]["added_lines"]
        self.assertEqual(2, len(added_lines))
        self.assertEqual("Check: app.py:2", added_lines[0]["title"])
        self.assertEqual("", added_lines[0]["body"])
        self.assertEqual("found", added_lines[0]["target"]["status"])
        self.assertEqual("+first()", added_lines[0]["target"]["diff_line"])
        self.assertEqual("second()", added_lines[1]["target"]["content"])


if __name__ == "__main__":
    unittest.main()
