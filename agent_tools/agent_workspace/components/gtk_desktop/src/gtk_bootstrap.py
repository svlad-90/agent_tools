from __future__ import annotations

import os
import shutil
import subprocess


def gsettings_value(schema: str, key: str) -> str:
    if shutil.which("gsettings") is None:
        return ""
    try:
        completed = subprocess.run(
            ["gsettings", "get", schema, key],
            text=True,
            capture_output=True,
            timeout=0.5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def gtk_cursor_size() -> int | None:
    cursor_size = os.environ.get("AGENT_WORKSPACE_GTK_CURSOR_SIZE")
    if cursor_size is None:
        cursor_size = os.environ.get("XCURSOR_SIZE")
    if cursor_size is None:
        cursor_size = gsettings_value("org.gnome.desktop.interface", "cursor-size")
    if not cursor_size.isdigit():
        return None
    size = int(cursor_size)
    if os.environ.get("WAYLAND_DISPLAY") and size > 16:
        return max(12, size // 2)
    return size


def gtk_cursor_theme() -> str:
    return (
        os.environ.get("AGENT_WORKSPACE_GTK_CURSOR_THEME")
        or os.environ.get("XCURSOR_THEME")
        or gsettings_value("org.gnome.desktop.interface", "cursor-theme").strip("'\"")
    )


def sync_gtk_environment() -> None:
    os.environ.setdefault("GDK_BACKEND", "x11")
    gdk_backends = [backend.strip() for backend in os.environ.get("GDK_BACKEND", "").split(",")]
    if "x11" not in gdk_backends:
        return
    cursor_size = gtk_cursor_size()
    if cursor_size is not None:
        os.environ["XCURSOR_SIZE"] = str(cursor_size)
    cursor_theme = gtk_cursor_theme()
    if cursor_theme:
        os.environ["XCURSOR_THEME"] = cursor_theme


sync_gtk_environment()
