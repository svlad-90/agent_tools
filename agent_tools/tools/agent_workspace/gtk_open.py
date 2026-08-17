from __future__ import annotations

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys

from gi.repository import Gio
from gi.repository import GLib


def open_path(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif os.name == "nt":
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        command = ["xdg-open", str(path)]
    try:
        subprocess.Popen(command)
    except OSError:
        return


def open_text_file(path: Path) -> None:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        try:
            subprocess.Popen([*shlex.split(editor), str(path)])
            return
        except (OSError, ValueError):
            pass
    for executable in ("gnome-text-editor", "gedit", "kate", "code", "xdg-open"):
        if shutil.which(executable):
            try:
                subprocess.Popen([executable, str(path)])
                return
            except OSError:
                continue


def open_containing_folder(path: Path) -> None:
    if sys.platform == "darwin":
        _open_command_or_parent(["open", "-R", str(path)], path)
    elif os.name == "nt":
        _open_command_or_parent(["explorer", f"/select,{path}"], path)
    elif not _show_file_in_freedesktop_file_manager(path):
        open_path(path.parent)


def _open_command_or_parent(command: list[str], path: Path) -> None:
    try:
        subprocess.Popen(command)
    except OSError:
        open_path(path.parent)


def _show_file_in_freedesktop_file_manager(path: Path) -> bool:
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            "org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1",
            "ShowItems",
            GLib.Variant("(ass)", ([path.resolve().as_uri()], "")),
            None,
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        )
    except (GLib.Error, OSError, RuntimeError, ValueError):
        return False
    return True


def open_artifact_path(path: Path) -> None:
    if path.suffix.casefold() == ".svg":
        command = _svg_open_command(path)
        if command is not None:
            subprocess.Popen(command)
            return
    open_path(path)


def _svg_open_command(path: Path) -> list[str] | None:
    browser = os.environ.get("BROWSER")
    if browser:
        return [*shlex.split(browser), str(path)]
    for executable in ("firefox", "google-chrome", "chromium", "chromium-browser", "xdg-open"):
        resolved = shutil.which(executable)
        if resolved is not None:
            return [resolved, str(path)]
    return None
