from __future__ import annotations

import unittest

from codex_tools.tools.diff_report.render_state import (
    active_delete_target_after_line,
    comment_row_kind,
    delete_target_classes,
    target_classes,
    target_classes_for_line,
    target_range_for_line,
)


class RenderStateTests(unittest.TestCase):
    def test_target_range_for_line_finds_containing_range(self) -> None:
        ranges = {"src/app.c": [(10, 12), (20, 20)]}

        self.assertEqual((10, 12), target_range_for_line(ranges, "src/app.c", 11))
        self.assertEqual((20, 20), target_range_for_line(ranges, "src/app.c", 20))
        self.assertIsNone(target_range_for_line(ranges, "src/app.c", 19))
        self.assertIsNone(target_range_for_line(ranges, "src/other.c", 11))

    def test_target_classes_for_line_marks_block_edges(self) -> None:
        self.assertEqual((), target_classes_for_line(None, 10))
        self.assertEqual(
            ("comment-target", "comment-target-start"),
            target_classes_for_line((10, 12), 10),
        )
        self.assertEqual(("comment-target",), target_classes_for_line((10, 12), 11))
        self.assertEqual(
            ("comment-target", "comment-target-end"),
            target_classes_for_line((10, 12), 12),
        )
        self.assertEqual(
            (
                "comment-target",
                "comment-target-start",
                "comment-target-end",
                "comment-target-single",
            ),
            target_classes_for_line((20, 20), 20),
        )

    def test_target_classes_combines_lookup_and_edge_classes(self) -> None:
        ranges = {"src/app.c": [(10, 12)]}

        self.assertEqual(
            ("comment-target", "comment-target-end"),
            target_classes(ranges, "src/app.c", 12),
        )

    def test_active_delete_target_tracks_intermediate_deletes(self) -> None:
        self.assertEqual((10, 12), active_delete_target_after_line((10, 12), 10))
        self.assertIsNone(active_delete_target_after_line((10, 12), 12))
        self.assertIsNone(active_delete_target_after_line(None, 10))

    def test_delete_target_classes_follow_active_target(self) -> None:
        self.assertEqual(("comment-target",), delete_target_classes((10, 12)))
        self.assertEqual((), delete_target_classes(None))

    def test_comment_row_kind_uses_supported_diff_kind_or_context(self) -> None:
        self.assertEqual("add", comment_row_kind("add"))
        self.assertEqual("del", comment_row_kind("del"))
        self.assertEqual("del", comment_row_kind("delete"))
        self.assertEqual("ctx", comment_row_kind("ctx"))
        self.assertEqual("ctx", comment_row_kind("context"))
        self.assertEqual("ctx", comment_row_kind("header"))


if __name__ == "__main__":
    unittest.main()
