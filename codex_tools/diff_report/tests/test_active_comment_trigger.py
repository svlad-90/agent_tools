from __future__ import annotations

import unittest

from codex_tools.diff_report.active_comment_trigger import (
    block_contains_center,
    CommentBlock,
    CommentCrossing,
    containing_block_at_center,
    first_directional_crossing,
    visible_content_center_y,
)


class ActiveCommentTriggerTests(unittest.TestCase):
    def test_unpinned_visible_content_center_uses_viewport_center(self) -> None:
        center = visible_content_center_y(
            scroll_y=1000,
            viewport_height=800,
            safe_top=700,
            pinned_top=False,
        )

        self.assertEqual(1400, center)

    def test_pinned_visible_content_center_accounts_for_reasonable_top_inset(self) -> None:
        center = visible_content_center_y(
            scroll_y=1000,
            viewport_height=800,
            safe_top=160,
            pinned_top=True,
        )

        self.assertEqual(1480, center)

    def test_pinned_visible_content_center_clamps_oversized_safe_top(self) -> None:
        center = visible_content_center_y(
            scroll_y=1000,
            viewport_height=800,
            safe_top=760,
            pinned_top=True,
        )

        self.assertEqual(1540, center)

    def test_downward_scroll_triggers_on_top_edge(self) -> None:
        crossing = first_directional_crossing(
            100,
            180,
            scrolling_down=True,
            blocks=[CommentBlock(id="a", top=150, bottom=260)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="top", progress=0.625), crossing)

    def test_downward_scroll_does_not_trigger_on_bottom_edge(self) -> None:
        crossing = first_directional_crossing(
            100,
            240,
            scrolling_down=True,
            blocks=[CommentBlock(id="a", top=20, bottom=180)],
        )

        self.assertIsNone(crossing)

    def test_upward_scroll_triggers_on_bottom_edge(self) -> None:
        crossing = first_directional_crossing(
            300,
            220,
            scrolling_down=False,
            blocks=[CommentBlock(id="a", top=120, bottom=260)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="bottom", progress=0.5), crossing)

    def test_upward_scroll_does_not_trigger_on_top_edge(self) -> None:
        crossing = first_directional_crossing(
            300,
            120,
            scrolling_down=False,
            blocks=[CommentBlock(id="a", top=180, bottom=420)],
        )

        self.assertIsNone(crossing)

    def test_layout_shift_during_downward_scroll_does_not_trigger_bottom_edge(self) -> None:
        crossing = first_directional_crossing(
            300,
            220,
            scrolling_down=True,
            blocks=[CommentBlock(id="a", top=120, bottom=260)],
        )

        self.assertIsNone(crossing)

    def test_large_downward_jump_chooses_first_top_edge_crossed(self) -> None:
        crossing = first_directional_crossing(
            100,
            500,
            scrolling_down=True,
            blocks=[
                CommentBlock(id="late", top=420, bottom=520),
                CommentBlock(id="first", top=180, bottom=260),
            ],
        )

        self.assertEqual("first", crossing.id if crossing else None)
        self.assertEqual("top", crossing.edge if crossing else None)

    def test_large_upward_jump_chooses_first_bottom_edge_crossed(self) -> None:
        crossing = first_directional_crossing(
            500,
            100,
            scrolling_down=False,
            blocks=[
                CommentBlock(id="first", top=420, bottom=460),
                CommentBlock(id="late", top=180, bottom=260),
            ],
        )

        self.assertEqual("first", crossing.id if crossing else None)
        self.assertEqual("bottom", crossing.edge if crossing else None)

    def test_downward_scroll_triggers_when_block_becomes_fully_visible_before_center(self) -> None:
        crossing = first_directional_crossing(
            300,
            380,
            scrolling_down=True,
            previous_visible_top_y=40,
            previous_visible_bottom_y=640,
            current_visible_top_y=120,
            current_visible_bottom_y=720,
            blocks=[CommentBlock(id="a", top=500, bottom=700)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="visible", progress=0.75), crossing)

    def test_upward_scroll_triggers_when_block_becomes_fully_visible_before_center(self) -> None:
        crossing = first_directional_crossing(
            620,
            540,
            scrolling_down=False,
            previous_visible_top_y=500,
            previous_visible_bottom_y=1100,
            current_visible_top_y=420,
            current_visible_bottom_y=1020,
            blocks=[CommentBlock(id="a", top=440, bottom=900)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="visible", progress=0.75), crossing)

    def test_already_fully_visible_block_does_not_trigger_without_center_crossing(self) -> None:
        crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=100,
            previous_visible_bottom_y=700,
            current_visible_top_y=140,
            current_visible_bottom_y=740,
            blocks=[CommentBlock(id="a", top=420, bottom=620)],
        )

        self.assertIsNone(crossing)

    def test_center_crossing_wins_when_it_happens_before_full_visibility(self) -> None:
        crossing = first_directional_crossing(
            300,
            620,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=600,
            current_visible_top_y=320,
            current_visible_bottom_y=920,
            blocks=[CommentBlock(id="a", top=360, bottom=880)],
        )

        self.assertEqual("top", crossing.edge if crossing else None)

    def test_containing_block_fallback_selects_dense_neighbor_at_center(self) -> None:
        crossing = first_directional_crossing(
            420,
            430,
            scrolling_down=True,
            previous_visible_top_y=110,
            previous_visible_bottom_y=710,
            current_visible_top_y=130,
            current_visible_bottom_y=730,
            blocks=[
                CommentBlock(id="previous", top=320, bottom=408),
                CommentBlock(id="dense-neighbor", top=410, bottom=470),
            ],
        )

        self.assertIsNone(crossing)
        self.assertEqual(
            CommentCrossing(id="dense-neighbor", edge="center", progress=0.0),
            containing_block_at_center(
                430,
                blocks=[
                    CommentBlock(id="previous", top=320, bottom=408),
                    CommentBlock(id="dense-neighbor", top=410, bottom=470),
                ],
            ),
        )

    def test_center_fallback_keeps_active_dense_block_while_center_remains_inside(self) -> None:
        active = CommentBlock(id="active", top=410, bottom=470)
        neighbor = CommentBlock(id="neighbor", top=472, bottom=540)

        self.assertIsNone(
            first_directional_crossing(
                430,
                440,
                scrolling_down=True,
                previous_visible_top_y=130,
                previous_visible_bottom_y=730,
                current_visible_top_y=140,
                current_visible_bottom_y=740,
                blocks=[active, neighbor],
            )
        )
        self.assertTrue(block_contains_center(active, 440))
        self.assertNotEqual(
            "neighbor",
            containing_block_at_center(440, blocks=[active, neighbor]).id,
        )


if __name__ == "__main__":
    unittest.main()
