from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from .gtk_bootstrap import sync_gtk_environment


sync_gtk_environment()

import gi

gi.require_version("Vte", "2.91")

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Vte


CodexTerminalMouseState = Literal["idle", "active"]
_INTERACTION_BUTTONS = {1, 2, 3}


class CodexTerminalMouseStateMachine:
    """Owns the Codex VTE mouse overlay state."""

    profile_area = "codex-terminal-mouse"

    def __init__(
        self,
        terminal: Vte.Terminal,
        record_profile_event: Callable[[str, str], None],
        *,
        profile_area: str | None = None,
        overlay: Gtk.Overlay | None = None,
        event_box: Gtk.EventBox | None = None,
    ) -> None:
        self.terminal = terminal
        self.record_profile_event = record_profile_event
        if profile_area is not None:
            self.profile_area = profile_area
        self.overlay = overlay if overlay is not None else Gtk.Overlay()
        self.event_box = event_box if event_box is not None else Gtk.EventBox()
        self.state: CodexTerminalMouseState = "idle"
        self.event_box.set_visible_window(True)
        self.event_box.set_app_paintable(True)
        self.event_box.set_above_child(True)
        self.event_box.set_sensitive(True)
        self.event_box.set_opacity(0.0)
        self.event_box.set_halign(Gtk.Align.FILL)
        self.event_box.set_valign(Gtk.Align.FILL)
        self.event_box.set_hexpand(True)
        self.event_box.set_vexpand(True)
        self.event_box.set_size_request(1, 1)
        self.event_box.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_HINT_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.PROXIMITY_IN_MASK
            | Gdk.EventMask.PROXIMITY_OUT_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.terminal.add_events(
            Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.FOCUS_CHANGE_MASK
        )
        self.overlay.add(self.terminal)
        self.overlay.add_overlay(self.event_box)
        self.event_box.connect("motion-notify-event", self.on_proxy_passive_pointer_event)
        self.event_box.connect("enter-notify-event", self.on_proxy_passive_pointer_event)
        self.event_box.connect("leave-notify-event", self.on_proxy_passive_pointer_event)
        self.event_box.connect("proximity-in-event", self.on_proxy_passive_pointer_event)
        self.event_box.connect("proximity-out-event", self.on_proxy_passive_pointer_event)
        self.event_box.connect("button-press-event", self.on_proxy_button_press)
        self.event_box.connect("button-release-event", self.on_proxy_button_release)
        self.event_box.connect("scroll-event", self.on_proxy_scroll)
        self.terminal.connect("button-release-event", self.on_terminal_button_release)
        self.terminal.connect("leave-notify-event", self.on_terminal_leave_notify)
        self.terminal.connect("focus-in-event", self.on_terminal_focus_in)
        self.terminal.connect("focus-out-event", self.on_terminal_focus_out)

    @property
    def widget(self) -> Gtk.Widget:
        return self.overlay

    def activate(self) -> None:
        if self.state == "active":
            return
        self.state = "active"
        self._disable_proxy()
        self.terminal.grab_focus()

    def deactivate(self) -> None:
        if self.state == "idle":
            return
        self.state = "idle"
        self._enable_proxy()

    def _enable_proxy(self) -> None:
        self.event_box.show()
        self.event_box.set_sensitive(True)
        self.event_box.set_above_child(True)

    def _disable_proxy(self) -> None:
        self.event_box.set_above_child(False)
        self.event_box.set_sensitive(False)
        self.event_box.hide()

    def on_proxy_event(self, _event_widget: Gtk.Widget, event: Gdk.Event) -> bool:
        event_type = getattr(event, "type", None)
        if _is_passive_pointer_event(event):
            return self.on_proxy_passive_pointer_event(_event_widget, event)
        if event_type == Gdk.EventType.BUTTON_PRESS:
            return self.on_proxy_button_press(_event_widget, event)
        if event_type == Gdk.EventType.BUTTON_RELEASE:
            return self.on_proxy_button_release(_event_widget, event)
        if event_type == Gdk.EventType.SCROLL:
            return self.on_proxy_scroll(_event_widget, event)
        return False

    def on_proxy_passive_pointer_event(self, _event_widget: Gtk.Widget, event: Gdk.Event) -> bool:
        if self.state == "active" and _is_pointer_event(event):
            self.record_profile_event(self.profile_area, _gdk_event_profile_name(event))
            return True
        if self.state != "idle" or not _is_passive_pointer_event(event):
            return False
        self.record_profile_event(self.profile_area, _gdk_event_profile_name(event))
        return True

    def on_proxy_button_press(self, _event_widget: Gtk.Widget, event: Gdk.Event) -> bool:
        if _event_button(event) not in _INTERACTION_BUTTONS:
            return False
        if self.state != "active":
            self.state = "active"
            self._disable_proxy()
            self.record_profile_event(self.profile_area, "activate-button-press")
        self.terminal.grab_focus()
        return True

    def on_proxy_button_release(self, _event_widget: Gtk.Widget, event: Gdk.Event) -> bool:
        if _event_button(event) not in _INTERACTION_BUTTONS:
            return False
        if self.state == "active":
            self.record_profile_event(self.profile_area, "keep-active-proxy-button-release")
        return True

    def on_proxy_scroll(self, _event_widget: Gtk.Widget, _event: Gdk.Event) -> bool:
        self.record_profile_event(self.profile_area, "activate-scroll")
        self.activate()
        return True

    def on_terminal_button_release(self, _terminal: Vte.Terminal, _event: Gdk.Event) -> bool:
        return False

    def on_terminal_leave_notify(self, _terminal: Vte.Terminal, event: Gdk.Event) -> bool:
        return False

    def on_terminal_focus_in(self, _terminal: Vte.Terminal, _event: Gdk.Event) -> bool:
        if self.state != "active":
            self.state = "active"
            self._disable_proxy()
            self.record_profile_event(self.profile_area, "activate-focus-in")
        return False

    def on_terminal_focus_out(self, _terminal: Vte.Terminal, _event: Gdk.Event) -> bool:
        if self.state == "active":
            self.record_profile_event(self.profile_area, "deactivate-focus-out")
            self.deactivate()
        return False


def _is_passive_pointer_event(event: Gdk.Event) -> bool:
    event_type = getattr(event, "type", None)
    if event_type in {
        Gdk.EventType.ENTER_NOTIFY,
        Gdk.EventType.LEAVE_NOTIFY,
        Gdk.EventType.PROXIMITY_IN,
        Gdk.EventType.PROXIMITY_OUT,
    }:
        return True
    if event_type != Gdk.EventType.MOTION_NOTIFY:
        return False
    return not _button1_pressed(event)


def _is_pointer_event(event: Gdk.Event) -> bool:
    return getattr(event, "type", None) in {
        Gdk.EventType.ENTER_NOTIFY,
        Gdk.EventType.LEAVE_NOTIFY,
        Gdk.EventType.PROXIMITY_IN,
        Gdk.EventType.PROXIMITY_OUT,
        Gdk.EventType.MOTION_NOTIFY,
    }


def _button1_pressed(event: Gdk.Event) -> bool:
    return bool(int(getattr(event, "state", 0)) & int(Gdk.ModifierType.BUTTON1_MASK))


def _event_button(event: Gdk.Event) -> int:
    try:
        return int(getattr(event, "button", 0))
    except (TypeError, ValueError):
        return 0


def _gdk_event_profile_name(event: Gdk.Event) -> str:
    event_type = getattr(event, "type", None)
    name = getattr(event_type, "value_nick", None) or str(event_type)
    return f"drop-{name}"
