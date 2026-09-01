"""GTK process bootstrap helpers shared by desktop frontends."""

from __future__ import annotations

import os
import shutil
import subprocess


def gsettings_value(schema: str, key: str) -> str:
    executable = shutil.which("gsettings")
    if not executable:
        return ""
    try:
        result = subprocess.run(
            [executable, "get", schema, key],
            check=False,
            capture_output=True,
            text=True,
            timeout=0.5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def gtk_cursor_size() -> int | None:
    raw_size = os.environ.get("AGENT_WORKSPACE_GTK_CURSOR_SIZE") or os.environ.get("XCURSOR_SIZE")
    if raw_size is None:
        raw_size = gsettings_value("org.gnome.desktop.interface", "cursor-size")
    try:
        size = int(raw_size)
    except (TypeError, ValueError):
        return None
    if os.environ.get("WAYLAND_DISPLAY") and size > 16:
        return max(12, size // 2)
    return size


def gtk_cursor_theme() -> str:
    theme = os.environ.get("AGENT_WORKSPACE_GTK_CURSOR_THEME") or os.environ.get("XCURSOR_THEME")
    if not theme:
        theme = gsettings_value("org.gnome.desktop.interface", "cursor-theme")
    return theme.strip("'\"")


def sync_gtk_environment() -> None:
    os.environ.setdefault("GDK_BACKEND", "x11")
    if os.environ.get("GDK_BACKEND") != "x11":
        return
    cursor_size = gtk_cursor_size()
    if cursor_size is not None:
        os.environ["XCURSOR_SIZE"] = str(cursor_size)
    cursor_theme = gtk_cursor_theme()
    if cursor_theme:
        os.environ["XCURSOR_THEME"] = cursor_theme


sync_gtk_environment()
