from __future__ import annotations

from .gtk_bootstrap import sync_gtk_environment


sync_gtk_environment()

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Vte

from ...agent_status.api import session_is_agent
from ...localization.api import ui_string


def terminal_session_sort_key(kind: str, session_id: int) -> tuple[int, int]:
    return (0 if session_is_agent(session_kind=kind) else 1, session_id)


def terminal_tab_label(kind: str, shell_index: int, *, language: str = "en") -> str:
    if session_is_agent(session_kind=kind):
        return ui_string(language, "console.ai_agent")
    if kind == "shell":
        return f"{ui_string(language, 'console.shell')} {shell_index}"
    return f"{kind} {shell_index}"


def terminal_tab_text_label(tab: Gtk.Widget | None) -> Gtk.Label | None:
    if isinstance(tab, Gtk.Label):
        return tab
    if isinstance(tab, Gtk.Container):
        for child in tab.get_children():
            if isinstance(child, Gtk.Label):
                return child
    return None


def terminal_clipboard_shortcut(keyval: int, state: int, hardware_keycode: int | None = None) -> str | None:
    modifiers = int(Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
    if (state & modifiers) != modifiers:
        return None
    if hardware_keycode in {54}:
        return "copy"
    if hardware_keycode in {55}:
        return "paste"
    char = chr(Gdk.keyval_to_unicode(keyval)).casefold() if Gdk.keyval_to_unicode(keyval) else ""
    key_name = Gdk.keyval_name(keyval) or ""
    key_name = key_name.casefold()
    if char in {"c", "с"} or key_name in {"c", "cyrillic_es"}:
        return "copy"
    if char in {"v", "м"} or key_name in {"v", "cyrillic_em"}:
        return "paste"
    return None


def copy_terminal_selection(terminal: Vte.Terminal) -> None:
    terminal.grab_focus()
    get_has_selection = getattr(terminal, "get_has_selection", None)
    has_selection = bool(get_has_selection()) if callable(get_has_selection) else True
    try:
        terminal.copy_clipboard_format(Vte.Format.TEXT)
    except (AttributeError, TypeError):
        terminal.copy_clipboard()
    if not has_selection:
        copy_primary_selection_to_clipboard()


def copy_primary_selection_to_clipboard() -> None:
    text = clipboard_text(Gdk.SELECTION_PRIMARY).strip()
    if not text:
        return
    set_clipboard_text(text)


def clipboard_text(selection: Gdk.Atom) -> str:
    clipboard = Gtk.Clipboard.get(selection)
    wait_for_text = getattr(clipboard, "wait_for_text", None)
    if not callable(wait_for_text):
        return ""
    return wait_for_text() or ""


def set_clipboard_text(text: str) -> None:
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)
    store = getattr(clipboard, "store", None)
    if callable(store):
        store()


def terminal_text_tail(terminal: Vte.Terminal, limit: int = 4000) -> str:
    def include_all(*_args: object) -> bool:
        return True

    try:
        result = terminal.get_text(include_all, None)
    except TypeError:
        result = terminal.get_text(include_all)
    if isinstance(result, tuple):
        text = result[0]
    else:
        text = result
    if not isinstance(text, str):
        return ""
    return text[-limit:]
