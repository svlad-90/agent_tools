from __future__ import annotations

from agent_tools.agent_workspace.components.desktop_integration.api.gtk_bootstrap import sync_gtk_environment


sync_gtk_environment()

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk
from gi.repository import Pango


def button(label: str, callback: object) -> Gtk.Button:
    widget = Gtk.Button(label=label)
    widget.connect("clicked", callback)
    return widget


def compact_button(
    label: str,
    callback: object | None,
    *,
    max_width_chars: int = 22,
    tooltip: bool = True,
) -> Gtk.Button:
    widget = Gtk.Button()
    text = Gtk.Label(label=label)
    text.set_ellipsize(Pango.EllipsizeMode.END)
    text.set_max_width_chars(max_width_chars)
    text.set_width_chars(min(max_width_chars, max(4, min(len(label), max_width_chars))))
    widget.add(text)
    if tooltip:
        widget.set_tooltip_text(label)
    widget.set_size_request(-1, 26)
    if callback is not None:
        widget.connect("clicked", callback)
    return widget


def flow_box(
    *,
    border_width: int = 0,
    orientation: Gtk.Orientation = Gtk.Orientation.HORIZONTAL,
    max_children_per_line: int = 24,
) -> Gtk.FlowBox:
    box = Gtk.FlowBox()
    box.set_selection_mode(Gtk.SelectionMode.NONE)
    box.set_orientation(orientation)
    box.set_column_spacing(3)
    box.set_row_spacing(2)
    box.set_min_children_per_line(1)
    box.set_max_children_per_line(max_children_per_line)
    box.set_border_width(border_width)
    return box


def flow_box_add(box: Gtk.FlowBox, widget: Gtk.Widget) -> None:
    box.add(widget)


def remove_style_class_recursive(widget: Gtk.Widget, class_name: str) -> None:
    widget.get_style_context().remove_class(class_name)
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            remove_style_class_recursive(child, class_name)


def set_widget_opacity_recursive(widget: Gtk.Widget, opacity: float) -> None:
    widget.set_opacity(opacity)
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            set_widget_opacity_recursive(child, opacity)


def task_action_drag_icon(label: str) -> Gtk.Button:
    widget = Gtk.Button(label=label)
    widget.set_relief(Gtk.ReliefStyle.NORMAL)
    widget.set_focus_on_click(False)
    widget.get_style_context().add_class("task-action-drag-icon")
    widget.set_opacity(0.9)
    widget.show_all()
    return widget
