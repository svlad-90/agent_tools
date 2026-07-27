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


def visible_content_range_y(
    *,
    scroll_y: float,
    viewport_height: float,
    safe_top: float,
    safe_bottom: float,
) -> tuple[float, float]:
    """Return document Y range not covered by fixed top/bottom chrome."""
    top_inset = max(0.0, min(safe_top, viewport_height))
    bottom_inset = max(0.0, min(safe_bottom, max(0.0, viewport_height - top_inset)))
    return (
        scroll_y + top_inset,
        scroll_y + max(top_inset, viewport_height - bottom_inset),
    )


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
    """Return the first comment block that enters the visible area."""
    best: CommentCrossing | None = None
    for block in blocks:
        crossings = [
            _block_visible_entry_crossing(
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


def visible_fallback_after_active_hidden(
    *,
    active: CommentBlock | None,
    scrolling_down: bool,
    blocks: list[CommentBlock],
    current_visible_top_y: float,
    current_visible_bottom_y: float,
) -> CommentCrossing | None:
    """Return the nearest already-visible neighbor after the active block hides."""
    if active is None:
        return None
    visible_blocks = [
        block
        for block in blocks
        if block.id != active.id
        and block.bottom > current_visible_top_y
        and block.top < current_visible_bottom_y
    ]
    if scrolling_down:
        candidates = [block for block in visible_blocks if block.top >= active.top]
        if not candidates:
            return None
        block = min(candidates, key=lambda item: (item.top, item.bottom))
        return CommentCrossing(id=block.id, edge="visible", progress=0.0)
    candidates = [block for block in visible_blocks if block.bottom <= active.bottom]
    if not candidates:
        return None
    block = max(candidates, key=lambda item: (item.bottom, item.top))
    return CommentCrossing(id=block.id, edge="visible", progress=0.0)


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


def _block_visible_entry_crossing(
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
    was_visible = block.bottom > previous_visible_top_y and block.top < previous_visible_bottom_y
    is_visible = block.bottom > current_visible_top_y and block.top < current_visible_bottom_y
    if was_visible or not is_visible:
        return None
    if scrolling_down:
        if previous_visible_bottom_y <= block.top < current_visible_bottom_y:
            return CommentCrossing(
                id=block.id,
                edge="top",
                progress=(block.top - previous_visible_bottom_y)
                / (current_visible_bottom_y - previous_visible_bottom_y or 1),
            )
        return CommentCrossing(id=block.id, edge="visible", progress=0.0)
    if current_visible_top_y < block.bottom <= previous_visible_top_y:
        return CommentCrossing(
            id=block.id,
            edge="bottom",
            progress=(previous_visible_top_y - block.bottom)
            / (previous_visible_top_y - current_visible_top_y or 1),
        )
    return CommentCrossing(id=block.id, edge="visible", progress=0.0)
