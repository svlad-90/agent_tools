from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommentBlock:
    id: str
    top: float
    bottom: float


@dataclass(frozen=True)
class CommentCrossing:
    id: str
    edge: str
    progress: float


def visible_content_center_y(
    *,
    scroll_y: float,
    viewport_height: float,
    safe_top: float,
    pinned_top: bool,
) -> float:
    """Return the document Y coordinate of the visible content area's center."""
    top_inset = 0.0
    if pinned_top:
        max_top_inset = max(0.0, viewport_height * 0.35)
        top_inset = min(max(0.0, safe_top), max_top_inset)
    return scroll_y + top_inset + max(0.0, viewport_height - top_inset) / 2


def first_directional_crossing(
    previous_center_y: float,
    current_center_y: float,
    *,
    scrolling_down: bool,
    blocks: list[CommentBlock],
    previous_visible_top_y: float | None = None,
    previous_visible_bottom_y: float | None = None,
    current_visible_top_y: float | None = None,
    current_visible_bottom_y: float | None = None,
) -> CommentCrossing | None:
    """Return the first comment trigger reached while scrolling."""
    best: CommentCrossing | None = None
    for block in blocks:
        crossings = [
            _block_crossing(previous_center_y, current_center_y, scrolling_down, block),
            _block_fully_visible_crossing(
                previous_visible_top_y,
                previous_visible_bottom_y,
                current_visible_top_y,
                current_visible_bottom_y,
                scrolling_down,
                block,
            ),
        ]
        for crossing in crossings:
            if crossing is not None and (best is None or crossing.progress < best.progress):
                best = crossing
    return best


def containing_block_at_center(
    center_y: float,
    *,
    blocks: list[CommentBlock],
) -> CommentCrossing | None:
    """Return the comment block that currently contains the visible center."""
    for block in blocks:
        if block.top <= center_y <= block.bottom:
            return CommentCrossing(id=block.id, edge="center", progress=0.0)
    return None


def block_contains_center(block: CommentBlock, center_y: float) -> bool:
    """Return whether an already active block still owns the center point."""
    return block.top <= center_y <= block.bottom


def _block_crossing(
    previous_center_y: float,
    current_center_y: float,
    scrolling_down: bool,
    block: CommentBlock,
) -> CommentCrossing | None:
    if scrolling_down:
        if previous_center_y <= block.top < current_center_y:
            return CommentCrossing(
                id=block.id,
                edge="top",
                progress=(block.top - previous_center_y)
                / (current_center_y - previous_center_y or 1),
            )
        return None
    if current_center_y < block.bottom <= previous_center_y:
        return CommentCrossing(
            id=block.id,
            edge="bottom",
            progress=(previous_center_y - block.bottom)
            / (previous_center_y - current_center_y or 1),
        )
    return None


def _block_fully_visible_crossing(
    previous_visible_top_y: float | None,
    previous_visible_bottom_y: float | None,
    current_visible_top_y: float | None,
    current_visible_bottom_y: float | None,
    scrolling_down: bool,
    block: CommentBlock,
) -> CommentCrossing | None:
    if (
        previous_visible_top_y is None
        or previous_visible_bottom_y is None
        or current_visible_top_y is None
        or current_visible_bottom_y is None
    ):
        return None
    is_fully_visible = block.top >= current_visible_top_y and block.bottom <= current_visible_bottom_y
    if not is_fully_visible:
        return None
    was_fully_visible = block.top >= previous_visible_top_y and block.bottom <= previous_visible_bottom_y
    if was_fully_visible:
        return None
    if scrolling_down:
        if previous_visible_bottom_y < block.bottom <= current_visible_bottom_y:
            return CommentCrossing(
                id=block.id,
                edge="visible",
                progress=(block.bottom - previous_visible_bottom_y)
                / (current_visible_bottom_y - previous_visible_bottom_y or 1),
            )
        return None
    if current_visible_top_y <= block.top < previous_visible_top_y:
        return CommentCrossing(
            id=block.id,
            edge="visible",
            progress=(previous_visible_top_y - block.top)
            / (previous_visible_top_y - current_visible_top_y or 1),
        )
    return None
