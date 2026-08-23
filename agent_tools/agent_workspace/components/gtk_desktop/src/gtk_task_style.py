from __future__ import annotations

from gi.repository import Pango

from .gtk_theme import theme_colors


def task_row_style(
    has_agent: bool,
    has_session: bool,
    has_external_agent: bool,
    theme: str,
) -> tuple[str, bool, str, bool, int, bool]:
    colors = theme_colors(theme)
    if has_agent:
        return (
            colors["codex_running_background"],
            True,
            colors["codex_running_foreground"],
            True,
            int(Pango.Weight.BOLD),
            True,
        )
    if has_external_agent:
        return (
            colors["agent_external_background"],
            True,
            colors["agent_external_foreground"],
            True,
            int(Pango.Weight.NORMAL),
            True,
        )
    return (
        "",
        False,
        "",
        False,
        int(Pango.Weight.NORMAL),
        False,
    )
