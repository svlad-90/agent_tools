from __future__ import annotations

import unittest

from agent_tools.tools.diff_report.active_comment_trigger import (
    CommentBlock,
    CommentCrossing,
    first_directional_crossing,
    visible_fallback_after_active_hidden,
    visible_content_center_y,
    visible_content_range_y,
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

    def test_visible_content_range_excludes_fixed_bottom_chrome(self) -> None:
        visible_top, visible_bottom = visible_content_range_y(
            scroll_y=1000,
            viewport_height=800,
            safe_top=120,
            safe_bottom=76,
        )

        self.assertEqual((1120, 1724), (visible_top, visible_bottom))

    def test_visible_content_range_clamps_bottom_to_available_height(self) -> None:
        visible_top, visible_bottom = visible_content_range_y(
            scroll_y=1000,
            viewport_height=300,
            safe_top=220,
            safe_bottom=200,
        )

        self.assertEqual((1220, 1220), (visible_top, visible_bottom))

    def test_downward_scroll_triggers_when_top_edge_enters_visible_area(self) -> None:
        crossing = first_directional_crossing(
            100,
            180,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=200,
            current_visible_top_y=80,
            current_visible_bottom_y=280,
            blocks=[CommentBlock(id="a", top=150, bottom=260)],
        )

        self.assertIsNone(crossing)

    def test_downward_scroll_triggers_when_block_appears_from_bottom(self) -> None:
        crossing = first_directional_crossing(
            100,
            240,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=200,
            current_visible_top_y=80,
            current_visible_bottom_y=280,
            blocks=[CommentBlock(id="a", top=240, bottom=320)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="top", progress=0.5), crossing)

    def test_upward_scroll_triggers_when_block_appears_from_top(self) -> None:
        crossing = first_directional_crossing(
            300,
            220,
            scrolling_down=False,
            previous_visible_top_y=200,
            previous_visible_bottom_y=400,
            current_visible_top_y=120,
            current_visible_bottom_y=320,
            blocks=[CommentBlock(id="a", top=40, bottom=160)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="bottom", progress=0.5), crossing)

    def test_already_visible_block_does_not_trigger_again(self) -> None:
        crossing = first_directional_crossing(
            300,
            120,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=200,
            current_visible_top_y=80,
            current_visible_bottom_y=280,
            blocks=[CommentBlock(id="a", top=120, bottom=180)],
        )

        self.assertIsNone(crossing)

    def test_not_yet_visible_block_does_not_trigger(self) -> None:
        crossing = first_directional_crossing(
            300,
            220,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=200,
            current_visible_top_y=80,
            current_visible_bottom_y=280,
            blocks=[CommentBlock(id="a", top=320, bottom=380)],
        )

        self.assertIsNone(crossing)

    def test_block_hidden_under_bottom_chrome_does_not_trigger(self) -> None:
        visible_top, visible_bottom = visible_content_range_y(
            scroll_y=0,
            viewport_height=800,
            safe_top=0,
            safe_bottom=76,
        )
        crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=650,
            current_visible_top_y=visible_top,
            current_visible_bottom_y=visible_bottom,
            blocks=[CommentBlock(id="a", top=740, bottom=790)],
        )

        self.assertIsNone(crossing)

    def test_block_triggers_after_rising_above_bottom_chrome(self) -> None:
        crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=724,
            current_visible_top_y=20,
            current_visible_bottom_y=744,
            blocks=[CommentBlock(id="a", top=740, bottom=790)],
        )

        self.assertEqual(CommentCrossing(id="a", edge="top", progress=0.8), crossing)

    def test_large_downward_jump_chooses_first_block_entering_visible_area(self) -> None:
        crossing = first_directional_crossing(
            100,
            500,
            scrolling_down=True,
            previous_visible_top_y=0,
            previous_visible_bottom_y=200,
            current_visible_top_y=350,
            current_visible_bottom_y=550,
            blocks=[
                CommentBlock(id="late", top=420, bottom=520),
                CommentBlock(id="first", top=360, bottom=410),
            ],
        )

        self.assertEqual("first", crossing.id if crossing else None)
        self.assertEqual("top", crossing.edge if crossing else None)

    def test_large_upward_jump_chooses_first_block_entering_visible_area(self) -> None:
        crossing = first_directional_crossing(
            500,
            100,
            scrolling_down=False,
            previous_visible_top_y=400,
            previous_visible_bottom_y=600,
            current_visible_top_y=50,
            current_visible_bottom_y=250,
            blocks=[
                CommentBlock(id="first", top=200, bottom=240),
                CommentBlock(id="late", top=80, bottom=120),
            ],
        )

        self.assertEqual("first", crossing.id if crossing else None)
        self.assertEqual("bottom", crossing.edge if crossing else None)

    def test_downward_huge_jump_still_detects_visible_overlap(self) -> None:
        crossing = first_directional_crossing(
            300,
            380,
            scrolling_down=True,
            previous_visible_top_y=40,
            previous_visible_bottom_y=140,
            current_visible_top_y=300,
            current_visible_bottom_y=400,
            blocks=[CommentBlock(id="a", top=220, bottom=360)],
        )

        self.assertEqual(
            CommentCrossing(id="a", edge="top", progress=80 / 260),
            crossing,
        )

    def test_upward_huge_jump_still_detects_visible_overlap(self) -> None:
        crossing = first_directional_crossing(
            620,
            540,
            scrolling_down=False,
            previous_visible_top_y=500,
            previous_visible_bottom_y=600,
            current_visible_top_y=240,
            current_visible_bottom_y=340,
            blocks=[CommentBlock(id="a", top=280, bottom=420)],
        )

        self.assertEqual(
            CommentCrossing(id="a", edge="bottom", progress=80 / 260),
            crossing,
        )

    def test_dense_adjacent_lower_comment_triggers_when_it_enters_viewport(self) -> None:
        crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=100,
            previous_visible_bottom_y=460,
            current_visible_top_y=140,
            current_visible_bottom_y=500,
            blocks=[
                CommentBlock(id="active", top=320, bottom=408),
                CommentBlock(id="neighbor", top=462, bottom=540),
            ],
        )

        self.assertEqual(CommentCrossing(id="neighbor", edge="top", progress=0.05), crossing)

    def test_visible_entry_trigger_does_not_wait_for_center(self) -> None:
        crossing = first_directional_crossing(
            420,
            430,
            scrolling_down=True,
            previous_visible_top_y=110,
            previous_visible_bottom_y=450,
            current_visible_top_y=130,
            current_visible_bottom_y=470,
            blocks=[
                CommentBlock(id="previous", top=320, bottom=408),
                CommentBlock(id="dense-neighbor", top=452, bottom=520),
            ],
        )

        self.assertEqual("dense-neighbor", crossing.id if crossing else None)

    def test_downward_scroll_selects_visible_neighbor_when_active_hides_above(self) -> None:
        crossing = visible_fallback_after_active_hidden(
            active=CommentBlock(id="upper", top=100, bottom=180),
            scrolling_down=True,
            current_visible_top_y=181,
            current_visible_bottom_y=560,
            blocks=[
                CommentBlock(id="upper", top=100, bottom=180),
                CommentBlock(id="lower", top=182, bottom=260),
                CommentBlock(id="later", top=320, bottom=400),
            ],
        )

        self.assertEqual(CommentCrossing(id="lower", edge="visible", progress=0.0), crossing)

    def test_upward_scroll_selects_visible_neighbor_when_active_hides_below(self) -> None:
        crossing = visible_fallback_after_active_hidden(
            active=CommentBlock(id="lower", top=500, bottom=580),
            scrolling_down=False,
            current_visible_top_y=120,
            current_visible_bottom_y=499,
            blocks=[
                CommentBlock(id="earlier", top=180, bottom=260),
                CommentBlock(id="upper", top=420, bottom=498),
                CommentBlock(id="lower", top=500, bottom=580),
            ],
        )

        self.assertEqual(CommentCrossing(id="upper", edge="visible", progress=0.0), crossing)

    def test_visible_fallback_ignores_blocks_outside_current_view(self) -> None:
        crossing = visible_fallback_after_active_hidden(
            active=CommentBlock(id="upper", top=100, bottom=180),
            scrolling_down=True,
            current_visible_top_y=181,
            current_visible_bottom_y=300,
            blocks=[
                CommentBlock(id="upper", top=100, bottom=180),
                CommentBlock(id="hidden", top=320, bottom=400),
            ],
        )

        self.assertIsNone(crossing)

    def test_comment_card_entry_handles_already_visible_target_range(self) -> None:
        target_crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=100,
            previous_visible_bottom_y=500,
            current_visible_top_y=140,
            current_visible_bottom_y=540,
            blocks=[CommentBlock(id="lower-target", top=420, bottom=700)],
        )
        card_crossing = first_directional_crossing(
            300,
            340,
            scrolling_down=True,
            previous_visible_top_y=100,
            previous_visible_bottom_y=500,
            current_visible_top_y=140,
            current_visible_bottom_y=540,
            blocks=[CommentBlock(id="lower-card", top=520, bottom=700)],
        )

        self.assertIsNone(target_crossing)
        self.assertEqual(CommentCrossing(id="lower-card", edge="top", progress=0.5), card_crossing)


if __name__ == "__main__":
    unittest.main()
