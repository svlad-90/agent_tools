from __future__ import annotations

import argparse
import os
from pathlib import Path

from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_bootstrap import sync_gtk_environment


sync_gtk_environment()

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Vte


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Embed a VTE terminal into a Tk XEmbed socket.")
    parser.add_argument("--socket-id", required=True, type=int)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--font-size", required=True, type=int)
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("missing command")

    plug = Gtk.Plug.new(args.socket_id)
    terminal = Vte.Terminal()
    terminal.set_scrollback_lines(20_000)
    terminal.set_font(Pango.FontDescription(f"Monospace {args.font_size}"))
    _apply_theme(terminal, args.theme)
    plug.add(terminal)
    plug.show_all()

    terminal.spawn_async(
        Vte.PtyFlags.DEFAULT,
        str(Path(args.cwd)),
        command,
        _terminal_env(),
        GLib.SpawnFlags.DEFAULT,
        None,
        None,
        -1,
        None,
        None,
        None,
    )
    terminal.grab_focus()
    terminal.connect("child-exited", lambda *_args: Gtk.main_quit())
    Gtk.main()
    return 0


def _terminal_env() -> list[str]:
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    return [f"{key}={value}" for key, value in env.items()]


def _apply_theme(terminal: Vte.Terminal, theme: str) -> None:
    if theme == "dark":
        foreground = "#e8eaed"
        background = "#111315"
    else:
        foreground = "#202124"
        background = "#ffffff"
    terminal.set_color_foreground(_rgba(foreground))
    terminal.set_color_background(_rgba(background))


def _rgba(color: str) -> object:
    rgba = Gdk.RGBA()
    rgba.parse(color)
    return rgba


if __name__ == "__main__":
    raise SystemExit(main())
