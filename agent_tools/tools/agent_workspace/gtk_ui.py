from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import shlex
import shutil
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Vte

from .artifacts import ArtifactEntry
from .artifacts import artifact_context_action as _artifact_context_action
from .artifacts import artifact_delete_paths as _artifact_delete_paths
from .artifacts import artifact_group as _artifact_group
from .artifacts import artifact_group_sort_key as _artifact_group_sort_key
from .artifacts import artifact_relative_label as _artifact_relative_label
from .artifacts import artifact_selectable_path as _artifact_selectable_path
from .artifacts import artifact_updated_label as _artifact_updated_label
from .artifacts import artifact_updated_timestamp as _artifact_updated_timestamp
from .artifacts import files_under as _files_under
from .artifacts import task_artifact_entries as _task_artifact_entries
from .artifacts import task_artifact_files as _task_artifact_files
from .task_action_model import field_type_enum_values as _field_type_enum_values
from .task_action_model import json_list_entry_index as _json_list_entry_index
from .task_action_model import move_action_parameter_entry as _move_action_parameter_entry
from .task_action_model import move_id_before as _move_id_before
from .task_action_model import move_id_relative as _move_id_relative
from .task_action_model import move_json_list_entry as _move_json_list_entry
from .task_action_model import move_json_list_entry_before as _move_json_list_entry_before
from .task_action_model import move_json_mapping_entry as _move_json_mapping_entry
from .task_action_model import parameter_field_order as _parameter_field_order
from .task_action_model import parameter_field_type as _parameter_field_type
from .task_action_model import parameter_type_fields as _parameter_type_fields
from .task_action_model import parameter_value_id_from_name as _parameter_value_id_from_name
from .task_action_model import reorder_action_parameter_entries as _reorder_action_parameter_entries
from .task_action_model import reorder_json_list_by_ids as _reorder_json_list_by_ids
from .task_action_model import reorder_json_list_subset_by_ids as _reorder_json_list_subset_by_ids
from .task_action_model import reorder_json_mapping_by_ids as _reorder_json_mapping_by_ids
from .task_action_model import set_task_action_drag_selection as _set_task_action_drag_selection
from .task_action_model import shortcut_id_from_label as _shortcut_id_from_label
from .task_action_model import task_action_drag_selection_id as _task_action_drag_selection_id
from .task_action_model import task_reorder_order_for_drag_edges as _task_reorder_order_for_drag_edges
from .task_action_model import unique_parameter_value_id as _unique_parameter_value_id
from .core import TASK_ACTIONS_FILE
from .core import AGENT_RUNNING_SPINNER_FRAMES
from .core import AGENT_STATUS_MANUAL_MENU_LABEL
from .core import AGENT_STATUS_MANUAL_TITLE
from .core import AgentModelSettings
from .core import TaskAction
from .core import TaskActionParameter
from .core import TaskActionsConfig
from .core import TaskSummary
from .core import AGENT_WORKSPACE_AGENTS
from .core import AGENT_WORKSPACE_CLAUDE_MODELS
from .core import AGENT_WORKSPACE_LANGUAGES
from .core import AGENT_WORKSPACE_REASONING_EFFORTS
from .core import AGENT_WORKSPACE_THEMES
from .core import acquire_agent_workspace_lock
from .core import agent_executable
from .core import agent_install_command
from .core import agent_label
from .core import agent_status_tooltip_text
from .core import ai_agent_launch_state_for_selection
from .core import ai_agent_model_settings
from .core import ai_agent_switch_decision
from .core import ai_agent_task_context_prompt
from .core import analyze_agent_output
from .core import agent_workspace_runtime_settings
from .core import install_agent_workspace_exception_logger
from .core import agent_output_state_update
from .core import build_ai_agent_console_command
from .core import bind_task_action_parameters
from .core import clear_task_agent_session
from .core import clear_task_active_agent_run
from .core import codex_model_choices
from .core import discover_tasks
from .core import load_task_agent
from .core import load_task_actions
from .core import load_task_actions_config
from .core import load_task_actions_data
from .core import load_agent_workspace_settings
from .core import model_choices_with_current
from .core import new_agent_session_id
from .core import normalize_agent
from .core import prepare_ai_agent_launch_command
from .core import read_task_file
from .core import render_markdown_chunks
from .core import reset_task_agent_session
from .core import save_agent_workspace_settings
from .core import save_task_actions_data
from .core import save_task_active_agent_run
from .core import save_task_agent
from .core import save_task_agent_session
from .core import session_marks_task_pending_permission
from .core import session_marks_task_running_agent
from .core import session_is_agent
from .core import session_is_running_agent
from .core import session_should_clear_pending_permission
from .core import task_agent_has_resumable_state
from .core import task_agent_status_text
from .core import task_agent_session_markers
from .core import task_agent_selection_with_resumable_fallback
from .core import task_has_external_active_agent_run
from .core import task_for_path
from .commands import claude_executable as _claude_executable
from .commands import codex_executable as _codex_executable
from .commands import task_action_shell_command
from .commands import task_check_shell_command
from .gtk_terminal import feed_terminal as _feed_terminal
from .gtk_terminal import terminal_env as _terminal_env
from .gtk_terminal import terminal_palette as _terminal_palette
from .gtk_terminal_ui import clipboard_text as _clipboard_text
from .gtk_terminal_ui import copy_primary_selection_to_clipboard as _copy_primary_selection_to_clipboard
from .gtk_terminal_ui import copy_terminal_selection as _copy_terminal_selection
from .gtk_terminal_ui import set_clipboard_text as _set_clipboard_text
from .gtk_terminal_ui import terminal_clipboard_shortcut as _terminal_clipboard_shortcut
from .gtk_terminal_ui import terminal_session_sort_key as _terminal_session_sort_key
from .gtk_terminal_ui import terminal_tab_label as _terminal_tab_label
from .gtk_terminal_ui import terminal_tab_text_label as _terminal_tab_text_label
from .gtk_terminal_ui import terminal_text_tail as _terminal_text_tail
from .gtk_task_helpers import task_actions_signature as _task_actions_signature
from .gtk_task_helpers import task_init_command as _task_init_command
from .gtk_task_helpers import task_path_for_name as _task_path_for_name
from .gtk_theme import theme_colors as _theme_colors
from .gtk_i18n import CODEX_LANGUAGE_INSTRUCTIONS
from .gtk_i18n import TRANSLATIONS
from .gtk_i18n import ui_string as _ui_string
from .gtk_open import _open_command_or_parent
from .gtk_open import _show_file_in_freedesktop_file_manager
from .gtk_open import _svg_open_command
from .gtk_open import open_artifact_path
from .gtk_open import open_containing_folder
from .gtk_open import open_path
from .gtk_open import open_text_file


_TASK_ACTION_DRAG_TARGET = "application/x-agent-workspace-task-action"
_TASK_REORDER_FRAME_DELAY_MS = 16


_TASK_ACTIONS_MONITOR_EVENTS = {
    event
    for event in (
        getattr(Gio.FileMonitorEvent, "CHANGED", None),
        getattr(Gio.FileMonitorEvent, "CHANGES_DONE_HINT", None),
        getattr(Gio.FileMonitorEvent, "CREATED", None),
        getattr(Gio.FileMonitorEvent, "DELETED", None),
        getattr(Gio.FileMonitorEvent, "MOVED_IN", None),
        getattr(Gio.FileMonitorEvent, "MOVED_OUT", None),
        getattr(Gio.FileMonitorEvent, "RENAMED", None),
    )
    if event is not None
}

AGENT_BUSY_IDLE_DELAY_MS = 1800


@dataclass
class TerminalSession:
    session_id: int
    task_path: Path
    kind: str
    terminal: Vte.Terminal
    page: Gtk.Widget
    child_pid: int | None = None
    permission_pending: bool = False
    exited: bool = False
    busy: bool = False
    run_id: str | None = None
    output_generation: int = 0
    permission_signature: str | None = None
    ignored_permission_signature: str | None = None


@dataclass(frozen=True)
class NewTaskRequest:
    name: str
    privacy: str


class WorkspaceGtkGui:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.task_actions: list[TaskAction] = []
        self.task_base_actions: list[TaskAction] = []
        self.task_shortcuts: list[TaskAction] = []
        self.task_action_config: TaskActionsConfig | None = None
        self.selected_task_action: TaskAction | None = None
        self.selected_task_action_bindings: dict[str, str] = {}
        self.task_action_buttons: dict[str, Gtk.Button] = {}
        self.global_task_parameter_box: Gtk.FlowBox | None = None
        self.task_action_errors: list[str] = []
        self.status_message = ""
        self.task_actions_signature: tuple[Path | None, int | None] = (None, None)
        self.task_actions_monitor: Gio.FileMonitor | None = None
        self.task_actions_monitor_path: Path | None = None
        self.artifact_sort_column = "name"
        self.artifact_sort_descending = False
        self.task_agent_session_marker_cache: dict[Path, tuple[str, ...]] = {}
        self.terminal_sessions: dict[int, TerminalSession] = {}
        self.last_active_terminal_by_task: dict[Path, int] = {}
        self.next_terminal_id = 1
        self._refreshing_console_tabs = False
        self._updating_agent_selection = False
        self._updating_task_selection = False
        self._agent_spinner_index = 0
        self._closing = False

        settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
        self.text_font_size = settings.text_font_size
        self.button_font_size = settings.button_font_size
        self.theme = settings.theme
        self.language = settings.language
        self.default_agent = settings.default_agent
        self.default_codex_model = settings.default_codex_model
        self.default_codex_reasoning = settings.default_codex_reasoning
        self.default_claude_model = settings.default_claude_model
        self.default_claude_effort = settings.default_claude_effort
        self.window_geometry = settings.window_geometry
        self.last_window_width = 1180
        self.last_window_height = 760
        self.last_window_x = 0
        self.last_window_y = 0
        self.label_widgets: dict[str, Gtk.Widget] = {}
        self.detail_editing: dict[Gtk.TextView, bool] = {}
        self.detail_original_text: dict[Gtk.TextView, str] = {}
        self.detail_filenames: dict[Gtk.TextView, str] = {}
        self.ai_agent_page: Gtk.Box | None = None
        self.ai_agent_tab_label: Gtk.Label | None = None
        self.ai_agent_terminal_box: Gtk.Box | None = None
        self.ai_agent_placeholder: Gtk.Label | None = None
        self.actions_controls_box: Gtk.Box | None = None
        self.task_reorder_group: str | None = None
        self.task_action_drag_source_id: str | None = None
        self.task_action_drag_pointer_offset_x: float | None = None
        self.task_action_drag_source_width: int = 1
        self.task_action_drag_last_box_x: float | None = None
        self.task_action_drag_icon: Gtk.Widget | None = None
        self.task_action_reorder_preview: list[str] | None = None
        self.task_action_reorder_committed = False
        self.task_reorder_sort_source_id: int | None = None
        self.task_reorder_pending_sort_groups: set[str] = set()
        self.task_action_run_tokens: dict[str, int] = {}
        self.task_action_reorder_mode = False

        GLib.set_application_name("Agent Workspace")
        GLib.set_prgname("agent-workspace")
        Gdk.set_program_class("agent-workspace")
        self.window = Gtk.Window(title=f"{self._tr('window_title')} - {self.workspace}")
        self.window.set_wmclass("agent-workspace", "Agent Workspace")
        icon_path = _agent_workspace_runtime_icon_path()
        if icon_path.is_file():
            Gtk.Window.set_default_icon_from_file(str(icon_path))
            self.window.set_icon_from_file(str(icon_path))
        self.window.set_icon_name("agent-workspace")
        self.header_bar = Gtk.HeaderBar(title=f"{self._tr('window_title')} - {self.workspace}")
        self.header_bar.set_show_close_button(True)
        self.window.set_titlebar(self.header_bar)
        self.window.connect("configure-event", self._on_window_configure)
        self.window.connect("key-press-event", self._on_window_key_press)
        self.window.connect("delete-event", self._on_window_delete_event)
        self.window.connect("destroy", self.close)
        self._apply_window_geometry()
        self._build_ui()
        self._apply_css()
        self.refresh_tasks()
        GLib.timeout_add(120, self._animate_agent_status)

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_border_width(6)
        root.pack_start(toolbar, False, False, 0)
        toolbar.pack_start(self._button("settings", self.open_settings), False, False, 0)
        self.summary_label = Gtk.Label(label="")
        self.summary_label.set_xalign(0)
        toolbar.pack_start(self.summary_label, False, False, 6)

        main = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_pane = main
        main.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        main.connect("button-press-event", self._on_main_pane_button_press)
        root.pack_start(main, True, True, 0)

        self.task_store = Gtk.ListStore(str, str, object, str, bool, str, bool, int, bool)
        self.task_view = Gtk.TreeView(model=self.task_store)
        self.task_view.set_enable_search(False)
        status_renderer = Gtk.CellRendererText()
        status_renderer.set_property("xalign", 0.5)
        self.task_status_header = Gtk.Label(label=self._tr("task_agent_status_column"))
        self.task_status_header.show()
        self.task_status_column = Gtk.TreeViewColumn("", status_renderer, text=0)
        self.task_status_column.set_widget(self.task_status_header)
        self.task_status_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.task_status_column.set_fixed_width(92)
        self.task_view.append_column(self.task_status_column)
        task_renderer = Gtk.CellRendererText()
        self.task_column = Gtk.TreeViewColumn(
            self._tr("task"),
            task_renderer,
            text=1,
            cell_background=3,
            cell_background_set=4,
            foreground=5,
            foreground_set=6,
            weight=7,
            weight_set=8,
        )
        self.task_view.append_column(self.task_column)
        self.task_view.get_selection().connect("changed", self._on_task_selected)
        self.task_view.connect("key-press-event", self._on_task_view_key_press)
        self.task_view.connect("row-activated", lambda *_: self.open_task())
        self.task_view.set_has_tooltip(True)
        self.task_view.connect("query-tooltip", self._on_task_view_query_tooltip)
        self.task_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.task_view.connect("button-press-event", self._on_task_view_button_press)
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_min_content_width(360)
        task_scroll.add(self.task_view)
        main.pack1(task_scroll, resize=False, shrink=False)

        self.notebook = Gtk.Notebook()
        main.pack2(self.notebook, resize=True, shrink=False)
        self._add_actions_tab()
        self._add_details_tab()
        self._add_artifacts_tab()
        self.notebook.connect("switch-page", self._on_main_notebook_switch_page)
        GLib.idle_add(self._set_main_default_split)

    def _add_details_tab(self) -> None:
        pane = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.details_pane = pane
        pane.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pane.connect("button-press-event", self._on_details_pane_button_press)
        self.description_view = _text_view(self.text_font_size, editable=False)
        self.context_view = _text_view(self.text_font_size, editable=False)
        self._register_detail_view(self.description_view, "TASK_DESCRIPTION.md")
        self._register_detail_view(self.context_view, "TASK_CONTEXT.md")
        pane.pack1(_scrolled(self.description_view), resize=True, shrink=False)
        pane.pack2(_scrolled(self.context_view), resize=True, shrink=False)
        GLib.idle_add(self._set_details_default_split)
        self.details_tab_label = Gtk.Label(label=self._tr("details"))
        self.notebook.append_page(pane, self.details_tab_label)

    def _add_artifacts_tab(self) -> None:
        self.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
        self.artifact_view = Gtk.TreeView(model=self.artifact_store)
        name_column = Gtk.TreeViewColumn(self._tr("artifacts"), Gtk.CellRendererText(), text=0)
        self.artifact_name_column = name_column
        name_column.set_expand(False)
        name_column.set_clickable(True)
        name_column.connect("clicked", lambda _column: self._set_artifact_sort("name"))
        updated_column = Gtk.TreeViewColumn(self._tr("updated"), Gtk.CellRendererText(), text=4)
        self.artifact_updated_column = updated_column
        updated_column.set_expand(False)
        updated_column.set_clickable(True)
        updated_column.connect("clicked", lambda _column: self._set_artifact_sort("updated"))
        self.artifact_view.append_column(name_column)
        self.artifact_view.append_column(updated_column)
        self._update_artifact_sort_indicators()
        self.artifact_view.connect("row-activated", self._on_artifact_row_activated)
        self.artifact_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.artifact_view.connect("button-press-event", self._on_artifact_view_button_press)
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.artifact_view)
        self.artifacts_page = scrolled
        self.artifacts_tab_label = Gtk.Label(label=self._tr("artifacts"))
        self.notebook.append_page(scrolled, self.artifacts_tab_label)

    def _add_actions_tab(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_border_width(3)
        box.get_style_context().add_class("actions-panel")
        self.actions_page = box
        self.actions_tab_label = Gtk.Label(label=self._tr("actions"))
        self.notebook.append_page(box, self.actions_tab_label)

        actions_pane = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        actions_pane.set_wide_handle(True)
        box.pack_start(actions_pane, True, True, 0)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        controls_box.set_border_width(0)
        self.actions_controls_box = controls_box
        controls_scrolled = Gtk.ScrolledWindow()
        controls_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        controls_scrolled.set_overlay_scrolling(False)
        controls_scrolled.add(controls_box)
        actions_pane.pack1(controls_scrolled, resize=False, shrink=True)
        actions_pane.connect("notify::position", self._on_actions_pane_position_changed)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        top_row.set_border_width(0)
        controls_box.pack_start(top_row, False, False, 0)

        self.task_actions_box = self._add_framed_action_group(top_row, self._s("actions.group"), expand=True)
        self.task_actions_box.set_sort_func(self._task_action_flow_sort)
        self._connect_task_reorder_box(self.task_actions_box, "action")

        parameter_frame = Gtk.Frame(label=self._s("action.parameters"))
        controls_box.pack_start(parameter_frame, False, False, 0)
        parameter_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        parameter_content.set_border_width(2)
        parameter_frame.add(parameter_content)
        self.task_action_parameter_box = _flow_box()
        self.task_action_parameter_box.set_sort_func(self._task_parameter_flow_sort)
        self._connect_task_reorder_box(self.task_action_parameter_box, "parameter")
        parameter_content.pack_start(self.task_action_parameter_box, True, True, 0)

        shortcuts_frame = Gtk.Frame(label=self._s("action.shortcuts"))
        controls_box.pack_start(shortcuts_frame, False, False, 0)
        shortcuts_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        shortcuts_content.set_border_width(2)
        shortcuts_frame.add(shortcuts_content)
        self.task_shortcuts_box = _flow_box(border_width=2)
        self.task_shortcuts_box.set_sort_func(self._task_shortcut_flow_sort)
        self._connect_task_reorder_box(self.task_shortcuts_box, "shortcut")
        shortcuts_content.pack_start(self.task_shortcuts_box, True, True, 0)
        self.save_task_shortcut_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        shortcuts_content.pack_end(self.save_task_shortcut_box, False, False, 0)

        global_parameter_frame = Gtk.Frame(label=self._s("action.global_parameters"))
        controls_box.pack_start(global_parameter_frame, False, False, 0)
        global_parameter_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        global_parameter_content.set_border_width(2)
        global_parameter_frame.add(global_parameter_content)
        self.global_task_parameter_box = _flow_box()
        self.global_task_parameter_box.set_sort_func(self._global_task_parameter_flow_sort)
        self._connect_task_reorder_box(self.global_task_parameter_box, "global_parameter")
        global_parameter_content.pack_start(self.global_task_parameter_box, True, True, 0)

        self.actions_message = Gtk.Label(label="")
        self.actions_message.set_xalign(0)
        controls_box.pack_start(self.actions_message, False, False, 0)

        self.console_notebook = Gtk.Notebook()
        self.console_notebook.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.console_notebook.connect("button-press-event", self._on_console_notebook_button_press)
        self.console_notebook.connect("switch-page", self._on_console_notebook_switch_page)
        actions_pane.pack2(self.console_notebook, resize=True, shrink=False)
        actions_pane.set_position(210)
        self._on_actions_pane_position_changed(actions_pane, None)
        self._ensure_ai_agent_console_page()

    def _on_actions_pane_position_changed(self, pane: Gtk.Paned, _param: object | None) -> None:
        if self.actions_controls_box is None:
            return
        position = pane.get_position()
        opacity = max(0.0, min(1.0, position / 90.0))
        self.actions_controls_box.set_opacity(opacity)

    def _ensure_ai_agent_console_page(self) -> None:
        if not hasattr(self, "ai_agent_page"):
            self.ai_agent_page = None
        if not hasattr(self, "ai_agent_terminal_box"):
            self.ai_agent_terminal_box = None
        if not hasattr(self, "default_agent"):
            return
        if self.ai_agent_page is None:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            control_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            control_row.set_border_width(2)
            page.pack_start(control_row, False, False, 0)
            self.agent_combo = Gtk.ComboBoxText()
            for agent in AGENT_WORKSPACE_AGENTS:
                self.agent_combo.append_text(agent)
            self.agent_combo.set_active(AGENT_WORKSPACE_AGENTS.index(self.default_agent))
            self.agent_combo.connect("changed", self._on_agent_selected)
            control_row.pack_start(self.agent_combo, False, False, 0)
            self.run_ai_agent_button = self._button("run_ai_agent", self.run_ai_agent_console)
            self.run_ai_agent_button.set_hexpand(True)
            control_row.pack_start(self.run_ai_agent_button, True, True, 0)
            self.reset_ai_agent_button = self._button("reset_ai_agent_session", self.reset_ai_agent_session)
            control_row.pack_start(self.reset_ai_agent_button, False, False, 0)
            self.ai_agent_terminal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.ai_agent_placeholder = Gtk.Label(label="")
            self.ai_agent_placeholder.set_xalign(0)
            self.ai_agent_terminal_box.pack_start(self.ai_agent_placeholder, True, True, 0)
            page.pack_start(self.ai_agent_terminal_box, True, True, 0)
            self.ai_agent_page = page
        if self.console_notebook.page_num(self.ai_agent_page) < 0:
            self.ai_agent_tab_label = Gtk.Label(label=self._s("console.ai_agent"))
            self.console_notebook.insert_page(self.ai_agent_page, self.ai_agent_tab_label, 0)
        self.ai_agent_page.show_all()

    def _set_ai_agent_terminal_page(self, page: Gtk.Widget) -> None:
        if self.ai_agent_terminal_box is None:
            return
        for child in list(self.ai_agent_terminal_box.get_children()):
            self.ai_agent_terminal_box.remove(child)
        self.ai_agent_terminal_box.pack_start(page, True, True, 0)
        self.ai_agent_terminal_box.show_all()

    def _clear_ai_agent_terminal_page(self) -> None:
        if self.ai_agent_terminal_box is None:
            return
        for child in list(self.ai_agent_terminal_box.get_children()):
            self.ai_agent_terminal_box.remove(child)
        self.ai_agent_placeholder = Gtk.Label(label="")
        self.ai_agent_placeholder.set_xalign(0)
        self.ai_agent_terminal_box.pack_start(self.ai_agent_placeholder, True, True, 0)
        self.ai_agent_terminal_box.show_all()

    def _add_framed_action_group(self, parent: Gtk.Box, title: str, *, expand: bool) -> Gtk.FlowBox:
        frame = Gtk.Frame(label=title)
        parent.pack_start(frame, expand, expand, 0)
        content = _flow_box(border_width=2)
        frame.add(content)
        return content

    def refresh_tasks(self, *_args: object) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
        self._invalidate_task_session_marker_cache()
        self.task_store.clear()
        for task in self.tasks:
            self.task_store.append(
                [self._task_agent_status(task), self._task_label(task), task, *_task_row_style(False, False, False, self.theme)]
            )
        self._refresh_task_row_styles()
        self.summary_label.set_text(f"{len(self.tasks)} {self._tr('tasks')}")
        self._set_task_selection(self._selectable_task_iter(selected_name))

    def _on_task_selected(self, selection: Gtk.TreeSelection) -> None:
        if self._updating_task_selection:
            return
        model, row_iter = selection.get_selected()
        if row_iter is None:
            return
        task = model[row_iter][2]
        if self._task_is_external_active(task):
            self._set_task_selection(self._selectable_task_iter(self.selected_task.name if self.selected_task else None))
            return
        self._remember_current_console_tab()
        self.selected_task = task
        self._leave_detail_edit_mode(self.description_view)
        self._leave_detail_edit_mode(self.context_view)
        self._set_markdown(self.description_view, read_task_file(self.selected_task, "TASK_DESCRIPTION.md"))
        self._set_markdown(self.context_view, read_task_file(self.selected_task, "TASK_CONTEXT.md"))
        self._reset_actions()
        self._watch_task_actions(self.selected_task)
        if self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)
        else:
            self.artifact_store.clear()
        self._load_task_action_buttons()
        self._set_selected_agent(
            task_agent_selection_with_resumable_fallback(
                self.selected_task,
                self.workspace,
                self.default_agent,
            )
        )
        self._refresh_console_tabs_for_task(self.selected_task)
        if self._actions_tab_active():
            self._ensure_default_console_for_selected_task()
        self._update_codex_button_state()

    def _selectable_task_iter(self, preferred_name: str | None) -> object | None:
        first_selectable = None
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            task = self.task_store[row_iter][2]
            if not self._task_is_external_active(task):
                if first_selectable is None:
                    first_selectable = row_iter
                if preferred_name and task.name == preferred_name:
                    return row_iter
            row_iter = self.task_store.iter_next(row_iter)
        return first_selectable

    def _set_task_selection(self, row_iter: object | None) -> None:
        selection = self.task_view.get_selection()
        self._updating_task_selection = True
        try:
            selection.unselect_all()
            if row_iter is None:
                self._clear_selected_task_view()
                return
            selection.select_iter(row_iter)
        finally:
            self._updating_task_selection = False
        self._on_task_selected(selection)

    def _clear_selected_task_view(self) -> None:
        self.selected_task = None
        if hasattr(self, "description_view"):
            self._set_markdown(self.description_view, "")
        if hasattr(self, "context_view"):
            self._set_markdown(self.context_view, "")
        if hasattr(self, "task_actions_box"):
            self._reset_actions()
        if hasattr(self, "artifact_store"):
            self.artifact_store.clear()
        if hasattr(self, "agent_combo"):
            self._set_selected_agent(self.default_agent)
        if hasattr(self, "run_ai_agent_button"):
            self._update_codex_button_state()

    def _on_main_notebook_switch_page(
        self,
        _notebook: Gtk.Notebook,
        page: Gtk.Widget,
        _page_num: int,
    ) -> None:
        if page is self.actions_page:
            self._load_task_action_buttons()
            self._ensure_default_console_for_selected_task()
        elif page is self.artifacts_page and self.selected_task is not None:
            self._load_task_artifacts(self.selected_task)

    def _load_task_artifacts(self, task: TaskSummary) -> None:
        self.artifact_store.clear()
        groups = {
            "logs": self.artifact_store.append(None, [self._tr("logs"), "", "logs", True, ""]),
            "diagrams": self.artifact_store.append(None, [self._tr("diagrams"), "", "diagrams", True, ""]),
            "diff_reports": self.artifact_store.append(None, [self._tr("diff_reports"), "", "diff_reports", True, ""]),
            "artifacts": self.artifact_store.append(None, [self._tr("other_artifacts"), "", "artifacts", True, ""]),
        }
        for entry in _task_artifact_entries(
            task,
            sort_column=self.artifact_sort_column,
            descending=self.artifact_sort_descending,
        ):
            rel_path = _artifact_relative_label(task, entry.path)
            self.artifact_store.append(
                groups[entry.group],
                [entry.path.name, rel_path, entry.path, False, _artifact_updated_label(entry.updated)],
            )
        self.artifact_view.expand_all()

    def _refresh_selected_task_artifacts(self, *_args: object) -> None:
        if self.selected_task is not None:
            self._load_task_artifacts(self.selected_task)

    def _set_artifact_sort(self, sort_column: str) -> None:
        if self.artifact_sort_column == sort_column:
            self.artifact_sort_descending = not self.artifact_sort_descending
        else:
            self.artifact_sort_column = sort_column
            self.artifact_sort_descending = sort_column == "updated"
        self._update_artifact_sort_indicators()
        if self.selected_task is not None and self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)

    def _update_artifact_sort_indicators(self) -> None:
        columns = {
            "name": self.artifact_name_column,
            "updated": self.artifact_updated_column,
        }
        for key, column in columns.items():
            active = key == self.artifact_sort_column
            column.set_sort_indicator(active)
            if active:
                order = Gtk.SortType.DESCENDING if self.artifact_sort_descending else Gtk.SortType.ASCENDING
                column.set_sort_order(order)

    def _on_artifact_row_activated(
        self,
        _view: Gtk.TreeView,
        tree_path: Gtk.TreePath,
        _column: Gtk.TreeViewColumn,
    ) -> None:
        row_iter = self.artifact_store.get_iter(tree_path)
        is_group = bool(self.artifact_store[row_iter][3])
        artifact_path = self.artifact_store[row_iter][2]
        if is_group or artifact_path is None:
            return
        open_artifact_path(artifact_path)

    def _on_artifact_view_button_press(self, tree: Gtk.TreeView, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        hit = tree.get_path_at_pos(int(event.x), int(event.y))
        if hit is not None:
            path, _column, _cell_x, _cell_y = hit
            tree.get_selection().select_path(path)
        else:
            tree.get_selection().unselect_all()
        self._artifact_context_menu().popup_at_pointer(event)
        return True

    def _artifact_context_menu(self) -> Gtk.Menu:
        task = self.selected_task
        menu = Gtk.Menu()
        group: str | None = None
        artifact_path: Path | None = None
        model, row_iter = self.artifact_view.get_selection().get_selected()
        if row_iter is not None:
            is_group = bool(model[row_iter][3])
            value = model[row_iter][2]
            if is_group and isinstance(value, str):
                group = value
            elif isinstance(value, Path):
                artifact_path = value
                if task is not None:
                    group = _artifact_group(task, artifact_path)
        action = _artifact_context_action(artifact_path, group)
        selectable_artifact = (
            _artifact_selectable_path(task, artifact_path)
            if task is not None and artifact_path is not None
            else None
        )
        if selectable_artifact is not None:
            open_folder_item = Gtk.MenuItem(label=self._tr("open_containing_folder"))
            open_folder_item.connect("activate", lambda *_: open_containing_folder(selectable_artifact))
            menu.append(open_folder_item)
            menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label=self._tr("refresh"))
        refresh_item.connect("activate", self._refresh_selected_task_artifacts)
        refresh_item.set_sensitive(task is not None)
        menu.append(refresh_item)
        menu.append(Gtk.SeparatorMenuItem())
        if action == "artifact":
            item = Gtk.MenuItem(label=self._tr("delete_artifact"))
            item.connect("activate", lambda *_: self._delete_artifacts(artifact_path=artifact_path))
        elif action == "group":
            item = Gtk.MenuItem(label=self._tr("delete_artifact_group"))
            item.connect("activate", lambda *_: self._delete_artifacts(group=group))
        else:
            item = Gtk.MenuItem(label=self._tr("delete_all_artifacts"))
            item.connect("activate", lambda *_: self._delete_artifacts(delete_all=True))
        item.set_sensitive(task is not None)
        menu.append(item)
        menu.show_all()
        return menu

    def _delete_artifacts(
        self,
        *,
        artifact_path: Path | None = None,
        group: str | None = None,
        delete_all: bool = False,
    ) -> None:
        task = self.selected_task
        if task is None:
            return
        paths = _artifact_delete_paths(task, artifact_path=artifact_path, group=group, delete_all=delete_all)
        if not paths or not self._confirm_delete_artifacts(paths):
            return
        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except IsADirectoryError:
                continue
        self._load_task_artifacts(task)

    def _confirm_delete_artifacts(self, paths: list[Path]) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_delete_artifacts_title"),
        )
        preview = "\n".join(str(path) for path in paths[:8])
        if len(paths) > 8:
            preview = f"{preview}\n..."
        dialog.format_secondary_text(f"{self._tr('confirm_delete_artifacts_body')}\n{preview}")
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("delete_artifacts"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _on_task_view_button_press(self, tree: Gtk.TreeView, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        hit = tree.get_path_at_pos(int(event.x), int(event.y))
        if hit is not None:
            path, _column, _cell_x, _cell_y = hit
            tree.get_selection().select_path(path)
        self._task_context_menu().popup_at_pointer(event)
        return True

    def _on_task_view_query_tooltip(
        self,
        tree: Gtk.TreeView,
        x: int,
        y: int,
        _keyboard_mode: bool,
        tooltip: Gtk.Tooltip,
    ) -> bool:
        hit = tree.get_path_at_pos(x, y)
        if hit is None:
            return False
        _path, column, _cell_x, _cell_y = hit
        if column is not self.task_status_column:
            return False
        model = tree.get_model()
        row_iter = model.get_iter(_path)
        tooltip_text = agent_status_tooltip_text(str(model[row_iter][0]))
        if not tooltip_text:
            return False
        tooltip.set_text(tooltip_text)
        return True

    def _on_task_view_key_press(self, _tree: Gtk.TreeView, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_F1:
            self.open_agent_status_manual()
            return True
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter, Gdk.KEY_space}:
            return True
        modifiers = int(Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.META_MASK)
        if int(event.state) & modifiers:
            return False
        return Gdk.keyval_to_unicode(event.keyval) != 0

    def _task_context_menu(self) -> Gtk.Menu:
        has_task = self.selected_task is not None
        menu = Gtk.Menu()
        items = (
            (self._tr("refresh"), self.refresh_tasks, True),
            (self._tr("open_workspace"), lambda *_: open_path(self.workspace), True),
            (self._tr("open_task"), self.open_task, has_task),
            (self._tr("open_dev"), self.open_task_dev, has_task),
            (self._tr("add_task"), self.add_task, True),
            (self._tr("delete_task"), self.delete_selected_task, has_task),
        )
        for index, (label, callback, sensitive) in enumerate(items):
            if index in (2, 4):
                menu.append(Gtk.SeparatorMenuItem())
            item = Gtk.MenuItem(label=label)
            item.set_sensitive(sensitive)
            item.connect("activate", callback)
            menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())
        manual_item = Gtk.MenuItem(label=AGENT_STATUS_MANUAL_MENU_LABEL)
        manual_item.connect("activate", self.open_agent_status_manual)
        menu.append(manual_item)
        menu.show_all()
        return menu

    def open_agent_status_manual(self, *_args: object) -> None:
        dialog = Gtk.Dialog(
            title=AGENT_STATUS_MANUAL_TITLE,
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(18)
        content.add(box)

        title = Gtk.Label()
        title.set_markup(f"<b>{AGENT_STATUS_MANUAL_TITLE}</b>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        subtitle = Gtk.Label(label=self._tr("manual_status_section"))
        subtitle.set_xalign(0)
        basics_title = Gtk.Label()
        basics_title.set_markup(f"<b>{self._tr('manual_usage_section')}</b>")
        basics_title.set_xalign(0)
        box.pack_start(basics_title, False, False, 0)

        usage_grid = Gtk.Grid()
        usage_grid.set_column_spacing(14)
        usage_grid.set_row_spacing(8)
        box.pack_start(usage_grid, False, False, 2)
        for row, (name, description) in enumerate(self._manual_usage_entries()):
            name_label = Gtk.Label()
            name_label.set_markup(f"<b>{name}</b>")
            name_label.set_xalign(0)
            description_label = Gtk.Label(label=description)
            description_label.set_xalign(0)
            usage_grid.attach(name_label, 0, row, 1, 1)
            usage_grid.attach(description_label, 1, row, 1, 1)

        subtitle.set_markup(f"<b>{self._tr('manual_status_section')}</b>")
        subtitle.set_xalign(0)
        box.pack_start(subtitle, False, False, 0)
        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(8)
        box.pack_start(grid, False, False, 2)
        for row, (marker, label, description) in enumerate(self._manual_status_entries()):
            display_marker = AGENT_RUNNING_SPINNER_FRAMES[self._agent_spinner_index] if marker.startswith("▷") else marker
            marker_label = Gtk.Label(label=display_marker)
            marker_label.set_width_chars(4)
            marker_label.set_xalign(0.5)
            name_label = Gtk.Label()
            name_label.set_markup(f"<b>{label}</b>")
            name_label.set_xalign(0)
            description_label = Gtk.Label(label=description)
            description_label.set_xalign(0)
            grid.attach(marker_label, 0, row, 1, 1)
            grid.attach(name_label, 1, row, 1, 1)
            grid.attach(description_label, 2, row, 1, 1)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def _manual_usage_entries(self) -> tuple[tuple[str, str], ...]:
        return (
            (self._tr("manual_label_concept"), self._tr("manual_usage_concept")),
            (self._tr("task"), self._tr("manual_usage_task")),
            (self._tr("manual_label_agent"), self._tr("manual_usage_agent")),
            (self._tr("manual_label_copy"), self._tr("manual_usage_copy")),
            (self._tr("manual_label_structure"), self._tr("manual_usage_structure")),
            (self._tr("actions"), self._tr("manual_usage_actions")),
            (self._tr("manual_label_reset"), self._tr("manual_usage_reset")),
        )

    def _manual_status_entries(self) -> tuple[tuple[str, str, str], ...]:
        return (
            ("Ⅱ", self._tr("manual_status_label_session"), self._tr("manual_status_session")),
            ("□", self._tr("manual_status_label_idle"), self._tr("manual_status_idle")),
            ("▷", self._tr("manual_status_label_running"), self._tr("manual_status_agent_running")),
            ("×", self._tr("manual_status_label_external"), self._tr("manual_status_external")),
        )

    def open_task(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path)

    def open_task_dev(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path / "dev")

    def add_task(self, *_args: object) -> None:
        request = self._prompt_task_name()
        if request is None:
            return
        task_path = _task_path_for_name(self.workspace, request.name)
        if task_path is None:
            self._show_error(f"Invalid task name: {request.name}")
            return
        if task_path.exists():
            self._show_error(f"{self._tr('task_already_exists')}: {task_path}")
            return
        result = subprocess.run(
            _task_init_command(self.workspace, task_path, privacy=request.privacy),
            cwd=self.workspace,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self._show_error((result.stderr or result.stdout or "task init failed").strip())
            return
        self.selected_task = TaskSummary(task_path.name, task_path, False, False, 0, 0, False)
        self.refresh_tasks()

    def delete_selected_task(self, *_args: object) -> None:
        task = self._require_task()
        if task is None or not self._confirm_delete_task(task):
            return
        self._close_sessions_for_task(task)
        shutil.rmtree(task.path)
        self.selected_task = None
        self.refresh_tasks()

    def _prompt_task_name(self) -> NewTaskRequest | None:
        dialog = Gtk.Dialog(
            title=self._tr("add_task"),
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)
        content.add(box)
        label = Gtk.Label(label=self._tr("task_name"))
        label.set_xalign(0)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(label, False, False, 0)
        box.pack_start(entry, False, False, 0)

        privacy_label = Gtk.Label(label=self._tr("task_privacy"))
        privacy_label.set_xalign(0)
        public_radio = Gtk.RadioButton.new_with_label_from_widget(
            None,
            self._tr("task_privacy_public"),
        )
        private_radio = Gtk.RadioButton.new_with_label_from_widget(
            public_radio,
            self._tr("task_privacy_private"),
        )
        public_radio.set_active(True)
        box.pack_start(privacy_label, False, False, 0)
        box.pack_start(public_radio, False, False, 0)
        box.pack_start(private_radio, False, False, 0)

        dialog.show_all()
        response = dialog.run()
        task_name = entry.get_text().strip()
        privacy = "private" if private_radio.get_active() else "public"
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not task_name:
            return None
        return NewTaskRequest(name=task_name, privacy=privacy)

    def _confirm_delete_task(self, task: TaskSummary) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_delete_task_title"),
        )
        dialog.format_secondary_text(f"{self._tr('confirm_delete_task_body')}\n{task.path}")
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("delete_task"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _show_error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.NONE,
            text=message,
        )
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        dialog.run()
        dialog.destroy()

    def _close_sessions_for_task(self, task: TaskSummary) -> None:
        for session_id, session in list(self.terminal_sessions.items()):
            if session.task_path != task.path:
                continue
            page_num = self.console_notebook.page_num(session.page)
            if page_num >= 0:
                self.console_notebook.remove_page(page_num)
            self.terminal_sessions.pop(session_id, None)
            if session.run_id is not None:
                clear_task_active_agent_run(
                    self._task_for_path(session.task_path),
                    run_id=session.run_id,
                    agent=session.kind,
                )
            session.page.destroy()
        self._update_codex_button_state()

    def _register_detail_view(self, view: Gtk.TextView, filename: str) -> None:
        self.detail_editing[view] = False
        self.detail_original_text[view] = ""
        self.detail_filenames[view] = filename
        view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        view.connect("button-press-event", self._on_detail_view_button_press)

    def _on_detail_view_button_press(self, view: Gtk.TextView, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        self._detail_context_menu(view).popup_at_pointer(event)
        return True

    def _detail_context_menu(self, view: Gtk.TextView) -> Gtk.Menu:
        editing = self.detail_editing.get(view, False)
        menu = Gtk.Menu()
        items = (
            (self._tr("edit"), lambda *_: self._edit_detail_view(view), self.selected_task is not None and not editing),
            (self._tr("save"), lambda *_: self._save_detail_view(view), editing),
            (self._tr("cancel"), lambda *_: self._cancel_detail_edit(view), editing),
        )
        for label, callback, sensitive in items:
            item = Gtk.MenuItem(label=label)
            item.set_sensitive(sensitive)
            item.connect("activate", callback)
            menu.append(item)
        menu.show_all()
        return menu

    def _edit_detail_view(self, view: Gtk.TextView) -> None:
        if self.selected_task is None:
            return
        filename = self.detail_filenames[view]
        text = read_task_file(self.selected_task, filename)
        self.detail_original_text[view] = text
        self.detail_editing[view] = True
        view.set_editable(True)
        view.set_cursor_visible(True)
        view.get_buffer().set_text(text)
        view.grab_focus()

    def _save_detail_view(self, view: Gtk.TextView) -> None:
        if self.selected_task is None:
            return
        filename = self.detail_filenames[view]
        path = self.selected_task.path / filename
        path.write_text(_text_buffer_text(view.get_buffer()), encoding="utf-8")
        self.detail_editing[view] = False
        view.set_editable(False)
        view.set_cursor_visible(False)
        self._set_markdown(view, path.read_text(encoding="utf-8", errors="replace"))
        self.refresh_tasks()

    def _cancel_detail_edit(self, view: Gtk.TextView) -> None:
        text = self.detail_original_text.get(view, "")
        self.detail_editing[view] = False
        view.set_editable(False)
        view.set_cursor_visible(False)
        self._set_markdown(view, text)

    def _leave_detail_edit_mode(self, view: Gtk.TextView) -> None:
        self.detail_editing[view] = False
        view.set_editable(False)
        view.set_cursor_visible(False)

    def open_settings(self, *_args: object) -> None:
        dialog = Gtk.Dialog(
            title=self._tr("settings_title"),
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_border_width(12)
        content.add(grid)

        text_size = Gtk.SpinButton.new_with_range(8, 28, 1)
        text_size.set_value(self.text_font_size)
        button_size = Gtk.SpinButton.new_with_range(8, 28, 1)
        button_size.set_value(self.button_font_size)
        theme_combo = Gtk.ComboBoxText()
        language_combo = Gtk.ComboBoxText()
        default_agent_combo = Gtk.ComboBoxText()
        codex_model_combo = Gtk.ComboBoxText()
        codex_reasoning_combo = Gtk.ComboBoxText()
        claude_model_combo = Gtk.ComboBoxText()
        claude_effort_combo = Gtk.ComboBoxText()
        for theme in AGENT_WORKSPACE_THEMES:
            theme_combo.append_text(theme)
        theme_combo.set_active(AGENT_WORKSPACE_THEMES.index(self.theme) if self.theme in AGENT_WORKSPACE_THEMES else 0)
        for language in AGENT_WORKSPACE_LANGUAGES:
            language_combo.append_text(language)
        language_combo.set_active(
            AGENT_WORKSPACE_LANGUAGES.index(self.language)
            if self.language in AGENT_WORKSPACE_LANGUAGES
            else 0
        )
        for agent in AGENT_WORKSPACE_AGENTS:
            default_agent_combo.append_text(agent)
        default_agent_combo.set_active(
            AGENT_WORKSPACE_AGENTS.index(self.default_agent)
            if self.default_agent in AGENT_WORKSPACE_AGENTS
            else 0
        )
        for effort in AGENT_WORKSPACE_REASONING_EFFORTS:
            codex_reasoning_combo.append_text(effort)
            claude_effort_combo.append_text(effort)
        _set_combo_text_choices(
            codex_model_combo,
            model_choices_with_current(codex_model_choices(), self.default_codex_model),
            self.default_codex_model,
        )
        _set_combo_text_choices(
            claude_model_combo,
            model_choices_with_current(AGENT_WORKSPACE_CLAUDE_MODELS, self.default_claude_model),
            self.default_claude_model,
        )
        codex_reasoning_combo.set_active(
            AGENT_WORKSPACE_REASONING_EFFORTS.index(self.default_codex_reasoning)
            if self.default_codex_reasoning in AGENT_WORKSPACE_REASONING_EFFORTS
            else 0
        )
        claude_effort_combo.set_active(
            AGENT_WORKSPACE_REASONING_EFFORTS.index(self.default_claude_effort)
            if self.default_claude_effort in AGENT_WORKSPACE_REASONING_EFFORTS
            else 0
        )

        for row, (label, widget) in enumerate(
            (
                (self._tr("text_font_size"), text_size),
                (self._tr("button_font_size"), button_size),
                (self._tr("theme"), theme_combo),
                (self._tr("language"), language_combo),
                (self._tr("default_agent"), default_agent_combo),
                (self._tr("default_codex_model"), codex_model_combo),
                (self._tr("default_codex_reasoning"), codex_reasoning_combo),
                (self._tr("default_claude_model"), claude_model_combo),
                (self._tr("default_claude_effort"), claude_effort_combo),
            )
        ):
            label_widget = Gtk.Label(label=label)
            label_widget.set_xalign(0)
            grid.attach(label_widget, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.text_font_size = int(text_size.get_value())
            self.button_font_size = int(button_size.get_value())
            self.theme = theme_combo.get_active_text() or self.theme
            self.language = language_combo.get_active_text() or self.language
            self.default_agent = normalize_agent(default_agent_combo.get_active_text())
            self.default_codex_model = codex_model_combo.get_active_text() or ""
            self.default_codex_reasoning = codex_reasoning_combo.get_active_text() or ""
            self.default_claude_model = claude_model_combo.get_active_text() or ""
            self.default_claude_effort = claude_effort_combo.get_active_text() or ""
            if self.selected_task is None:
                self._set_selected_agent(self.default_agent)
            self._apply_runtime_style()
            self._apply_labels()
            self.refresh_tasks()
            self._save_settings()
        dialog.destroy()

    def run_selected_task_check(self, *_args: object) -> None:
        task = self._require_task()
        if task is not None:
            self._send_command_to_task_terminal(task, task_check_shell_command(self.workspace, task))

    def reload_selected_task_actions(self, *_args: object) -> None:
        self._load_task_action_buttons()

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is not None:
            self.notebook.set_current_page(0)
            self._send_command_to_task_terminal(task, task_action_shell_command(action))

    def select_custom_task_action(self, action: TaskAction) -> None:
        self.selected_task_action = action
        self.selected_task_action_bindings = dict(action.bindings or {})
        self._update_task_action_button_selection()
        self._render_task_action_parameters()

    def _reset_actions(self) -> None:
        self.task_actions = []
        self.task_base_actions = []
        self.task_shortcuts = []
        self.task_action_config = None
        self.selected_task_action = None
        self.selected_task_action_bindings = {}
        self.task_action_buttons = {}
        self._clear_task_action_buttons()
        self._clear_task_action_parameters()
        self._update_actions_message()

    def _clear_task_action_buttons(self) -> None:
        for child in self.task_actions_box.get_children():
            self.task_actions_box.remove(child)
        if self.global_task_parameter_box is not None:
            for child in self.global_task_parameter_box.get_children():
                self.global_task_parameter_box.remove(child)
        for child in self.task_shortcuts_box.get_children():
            self.task_shortcuts_box.remove(child)
        for child in self.save_task_shortcut_box.get_children():
            self.save_task_shortcut_box.remove(child)

    def _clear_task_action_parameters(self) -> None:
        for child in self.task_action_parameter_box.get_children():
            self.task_action_parameter_box.remove(child)
        for child in self.save_task_shortcut_box.get_children():
            self.save_task_shortcut_box.remove(child)

    def _load_task_action_buttons(self) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            self.task_actions_signature = (None, None)
            return
        selected_action_id = self.selected_task_action.action_id if self.selected_task_action is not None else None
        selected_bindings = dict(self.selected_task_action_bindings)
        config = load_task_actions_config(task)
        self._clear_task_action_buttons()
        self._clear_task_action_parameters()
        self.task_action_config = config
        self.task_actions = config.actions
        self.task_base_actions = config.base_actions
        self.task_shortcuts = [action for action in config.actions if action.is_shortcut]
        self.task_action_buttons = {}
        self.task_actions_signature = _task_actions_signature(task)
        self.task_action_errors = config.errors
        self._update_actions_message()
        for action in self.task_base_actions:
            _flow_box_add(self.task_actions_box, self._task_action_button(action, shortcut=False))
        self._render_global_task_parameters()
        selected_action = next(
            (action for action in self.task_base_actions if action.action_id == selected_action_id),
            self.task_base_actions[0] if self.task_base_actions else None,
        )
        if selected_action is not None:
            self.selected_task_action = selected_action
            parameter_names = {parameter.name for parameter in selected_action.parameters}
            self.selected_task_action_bindings = dict(selected_action.bindings or {})
            self.selected_task_action_bindings.update(
                {
                    name: value
                    for name, value in selected_bindings.items()
                    if name in parameter_names
                }
            )
            self._update_task_action_button_selection()
            self._render_task_action_parameters()
        else:
            self.selected_task_action = None
            self.selected_task_action_bindings = {}
        self.task_actions_box.show_all()
        if self.global_task_parameter_box is not None:
            self.global_task_parameter_box.show_all()
        self.task_shortcuts_box.show_all()
        self.task_action_parameter_box.show_all()

    def _task_action_button(self, action: TaskAction, *, shortcut: bool) -> Gtk.Widget:
        button = _compact_button(action.label, lambda _button, item=action: self._on_task_action_clicked(item))
        button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        if shortcut:
            button.set_tooltip_text(self._s("action.shortcut_tooltip"))
            button.connect("button-press-event", self._on_task_shortcut_button_press, action)
            return button
        button.connect("button-press-event", self._on_task_action_button_press, action)
        self.task_action_buttons[action.action_id] = button
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        row.pack_start(button, True, True, 0)
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU)
        play.set_relief(Gtk.ReliefStyle.NONE)
        play.set_focus_on_click(False)
        play.set_tooltip_text(self._s("action.play_tooltip"))
        play.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        play.connect("clicked", self._on_task_action_play_clicked, action)
        play.connect("button-press-event", self._on_task_action_play_button_press, action)
        row.pack_start(play, False, False, 0)
        row.show_all()
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        setattr(event_box, "_task_reorder_id", action.action_id)
        event_box.add(row)
        if self.task_action_reorder_mode:
            event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            event_box.connect("button-press-event", self._on_task_reorder_button_press, action.action_id)
            button.connect("button-press-event", self._on_task_reorder_button_press, action.action_id)
            target = Gtk.TargetEntry.new(_TASK_ACTION_DRAG_TARGET, Gtk.TargetFlags.SAME_APP, 0)
            for source_widget in (event_box, button):
                source_widget.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [target], Gdk.DragAction.MOVE)
                source_widget.connect("drag-begin", self._on_task_reorder_drag_begin, "action", action.action_id, action.label)
                source_widget.connect("drag-end", self._on_task_reorder_drag_end)
                source_widget.connect("drag-data-get", self._on_task_reorder_drag_data_get, "action", action.action_id)
            event_box.get_style_context().add_class("task-action-reorder")
        return event_box

    def _task_action_flow_sort(self, child_a: Gtk.FlowBoxChild, child_b: Gtk.FlowBoxChild) -> int:
        return self._task_reorder_flow_sort("action", self._task_action_order(), child_a, child_b)

    def _task_parameter_flow_sort(self, child_a: Gtk.FlowBoxChild, child_b: Gtk.FlowBoxChild) -> int:
        return self._task_reorder_flow_sort("parameter", self._task_parameter_order(), child_a, child_b)

    def _global_task_parameter_flow_sort(self, child_a: Gtk.FlowBoxChild, child_b: Gtk.FlowBoxChild) -> int:
        return self._task_reorder_flow_sort("global_parameter", self._global_task_parameter_order(), child_a, child_b)

    def _task_shortcut_flow_sort(self, child_a: Gtk.FlowBoxChild, child_b: Gtk.FlowBoxChild) -> int:
        return self._task_reorder_flow_sort("shortcut", self._task_shortcut_order(), child_a, child_b)

    def _task_reorder_flow_sort(
        self,
        group: str,
        default_order: list[str],
        child_a: Gtk.FlowBoxChild,
        child_b: Gtk.FlowBoxChild,
    ) -> int:
        order = self.task_action_reorder_preview if self.task_reorder_group == group else default_order
        order = order or default_order
        index = {item_id: position for position, item_id in enumerate(order)}
        item_a = getattr(child_a.get_child(), "_task_reorder_id", "")
        item_b = getattr(child_b.get_child(), "_task_reorder_id", "")
        return index.get(item_a, len(index)) - index.get(item_b, len(index))

    def _task_action_order(self) -> list[str]:
        return [action.action_id for action in self.task_base_actions]

    def _task_parameter_order(self) -> list[str]:
        action = self.selected_task_action
        if action is None:
            return []
        return [parameter.name for parameter in action.parameters if not parameter.global_name]

    def _global_task_parameter_order(self) -> list[str]:
        return [parameter.global_name for parameter in self._global_task_parameters() if parameter.global_name]

    def _task_shortcut_order(self) -> list[str]:
        action = self.selected_task_action
        if action is None:
            return []
        return [shortcut.action_id for shortcut in self._shortcuts_for_action(action)]

    def _task_reorderable_widget(self, widget: Gtk.Widget, *, group: str, item_id: str, label: str) -> Gtk.Widget:
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        setattr(event_box, "_task_reorder_id", item_id)
        event_box.add(widget)
        if not self.task_action_reorder_mode:
            return event_box
        event_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        event_box.connect("button-press-event", self._on_task_reorder_button_press, item_id)
        widget.connect("button-press-event", self._on_task_reorder_button_press, item_id)
        target = Gtk.TargetEntry.new(_TASK_ACTION_DRAG_TARGET, Gtk.TargetFlags.SAME_APP, 0)
        for source_widget in (event_box, widget):
            source_widget.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [target], Gdk.DragAction.MOVE)
            source_widget.connect("drag-begin", self._on_task_reorder_drag_begin, group, item_id, label)
            source_widget.connect("drag-end", self._on_task_reorder_drag_end)
            source_widget.connect("drag-data-get", self._on_task_reorder_drag_data_get, group, item_id)
        event_box.get_style_context().add_class("task-action-reorder")
        return event_box

    def _connect_task_reorder_box(self, box: Gtk.FlowBox, group: str) -> None:
        target = Gtk.TargetEntry.new(_TASK_ACTION_DRAG_TARGET, Gtk.TargetFlags.SAME_APP, 0)
        box.drag_dest_set(Gtk.DestDefaults.DROP, [target], Gdk.DragAction.MOVE)
        box.connect("drag-motion", self._on_task_reorder_box_drag_motion, group)
        box.connect("drag-leave", self._on_task_reorder_drag_leave)
        box.connect("drag-data-received", self._on_task_reorder_box_drag_data_received, group)

    def _update_task_action_button_selection(self) -> None:
        selected_id = self.selected_task_action.action_id if self.selected_task_action is not None else None
        for action_id, button in self.task_action_buttons.items():
            context = button.get_style_context()
            if action_id == selected_id:
                context.add_class("task-action-selected")
            else:
                context.remove_class("task-action-selected")

    def _on_task_action_clicked(self, action: TaskAction) -> None:
        if action.is_shortcut:
            self.run_custom_task_action(action)
            return
        self.select_custom_task_action(action)

    def _on_task_action_button_press(
        self,
        button: Gtk.Button,
        event: Gdk.EventButton,
        action: TaskAction,
    ) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button in {2, 3}:
            self._task_action_context_menu(action).popup_at_widget(
                button,
                Gdk.Gravity.SOUTH_WEST,
                Gdk.Gravity.NORTH_WEST,
                event,
            )
            return True
        return False

    def _on_task_reorder_button_press(
        self,
        widget: Gtk.Widget,
        event: Gdk.EventButton,
        item_id: str,
    ) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.task_action_drag_source_id = item_id
            self.task_action_drag_pointer_offset_x = float(event.x)
            self.task_action_drag_source_width = max(1, widget.get_allocated_width())
        return False

    def _on_task_reorder_drag_begin(
        self,
        widget: Gtk.Widget,
        context: Gdk.DragContext,
        group: str,
        item_id: str,
        label: str,
    ) -> None:
        self.task_reorder_group = group
        self.task_action_drag_source_id = item_id
        self.task_action_drag_last_box_x = None
        self.task_action_drag_source_width = max(1, widget.get_allocated_width())
        if self.task_action_drag_pointer_offset_x is None:
            self.task_action_drag_pointer_offset_x = self.task_action_drag_source_width / 2
        self.task_action_reorder_preview = self._task_reorder_order(group)
        self.task_action_reorder_committed = False
        self.task_action_drag_icon = _task_action_drag_icon(label)
        Gtk.drag_set_icon_widget(context, self.task_action_drag_icon, 18, 14)
        widget.set_opacity(0.45)
        widget.get_style_context().add_class("task-action-dragging")

    def _on_task_reorder_drag_end(self, widget: Gtk.Widget, _context: Gdk.DragContext) -> None:
        widget.set_opacity(1.0)
        widget.get_style_context().remove_class("task-action-dragging")
        self._clear_task_reorder_highlights()
        if self.task_action_drag_icon is not None:
            self.task_action_drag_icon.destroy()
            self.task_action_drag_icon = None
        if self.task_action_reorder_preview is not None and not self.task_action_reorder_committed:
            self.task_action_reorder_preview = None
            self._task_reorder_invalidate_sort()
        self.task_reorder_group = None
        self.task_action_drag_source_id = None
        self.task_action_drag_pointer_offset_x = None
        self.task_action_drag_source_width = 1
        self.task_action_drag_last_box_x = None
        self.task_action_reorder_preview = None
        self.task_action_reorder_committed = False

    def _on_task_reorder_drag_leave(
        self,
        widget: Gtk.Widget,
        _context: Gdk.DragContext,
        _time: int,
    ) -> None:
        return

    def _on_task_reorder_box_drag_motion(
        self,
        box: Gtk.FlowBox,
        context: Gdk.DragContext,
        x: int,
        y: int,
        time: int,
        group: str,
    ) -> bool:
        source_id = self.task_action_drag_source_id
        if self.task_reorder_group != group or not source_id:
            return False
        if self.task_action_reorder_preview is None:
            self.task_action_reorder_preview = self._task_reorder_order(group)
        last_x = self.task_action_drag_last_box_x
        self.task_action_drag_last_box_x = float(x)
        if last_x is None:
            Gdk.drag_status(context, Gdk.DragAction.MOVE, time)
            return True
        offset = self.task_action_drag_pointer_offset_x
        if offset is None:
            offset = self.task_action_drag_source_width / 2
        dragged_left = x - offset
        dragged_right = dragged_left + self.task_action_drag_source_width
        next_order = _task_reorder_order_for_drag_edges(
            self.task_action_reorder_preview,
            source_id,
            self._task_reorder_box_target_centers(box, y),
            dragged_left=dragged_left,
            dragged_right=dragged_right,
            moving_right=x >= last_x,
        )
        if next_order is not None:
            self.task_action_reorder_preview = next_order
            self._task_reorder_invalidate_sort()
        Gdk.drag_status(context, Gdk.DragAction.MOVE, time)
        return True

    def _task_reorder_box_target_centers(self, box: Gtk.FlowBox, y: int) -> dict[str, float]:
        rows: list[tuple[float, dict[str, float]]] = []
        for child in box.get_children():
            widget = child.get_child()
            item_id = getattr(widget, "_task_reorder_id", "")
            if not item_id or item_id == self.task_action_drag_source_id:
                continue
            allocation = child.get_allocation()
            center_y = allocation.y + allocation.height / 2
            row = next((entry for entry in rows if abs(entry[0] - center_y) <= max(1, allocation.height / 2)), None)
            if row is None:
                row = (center_y, {})
                rows.append(row)
            row[1][item_id] = allocation.x + allocation.width / 2
        if not rows:
            return {}
        _row_y, centers = min(rows, key=lambda row: abs(y - row[0]))
        return centers

    def _clear_task_reorder_highlights(self) -> None:
        for box in (
            self.task_actions_box,
            self.task_action_parameter_box,
            self.global_task_parameter_box,
            self.task_shortcuts_box,
        ):
            if box is not None:
                _remove_style_class_recursive(box, "task-action-dragging")
                _set_widget_opacity_recursive(box, 1.0)

    def _on_task_reorder_drag_data_get(
        self,
        _button: Gtk.Button,
        _context: Gdk.DragContext,
        selection: Gtk.SelectionData,
        _info: int,
        _time: int,
        group: str,
        item_id: str,
    ) -> None:
        _set_task_action_drag_selection(selection, f"{group}:{item_id}")

    def _on_task_reorder_drag_data_received(
        self,
        _button: Gtk.Button,
        _context: Gdk.DragContext,
        _x: int,
        _y: int,
        selection: Gtk.SelectionData,
        _info: int,
        _time: int,
        group: str,
        target_id: str,
    ) -> None:
        payload = _task_action_drag_selection_id(selection)
        source_group, _, source_id = payload.partition(":")
        if source_group != group:
            return
        if source_id and source_id != target_id:
            if self.task_action_reorder_preview is None:
                self.task_action_reorder_preview = self._task_reorder_order(group)
                _move_id_relative(self.task_action_reorder_preview, source_id, target_id, after=False)
            self._save_task_reorder_order(group, self.task_action_reorder_preview)
            self.task_action_reorder_committed = True

    def _on_task_reorder_box_drag_data_received(
        self,
        _box: Gtk.FlowBox,
        _context: Gdk.DragContext,
        _x: int,
        _y: int,
        selection: Gtk.SelectionData,
        _info: int,
        _time: int,
        group: str,
    ) -> None:
        payload = _task_action_drag_selection_id(selection)
        source_group, _, _source_id = payload.partition(":")
        if source_group != group or self.task_action_reorder_preview is None:
            return
        self._save_task_reorder_order(group, self.task_action_reorder_preview)
        self.task_action_reorder_committed = True

    def _on_task_action_play_clicked(self, button: Gtk.Button, action: TaskAction) -> None:
        token = self.task_action_run_tokens.get(action.action_id)
        if token is not None:
            self.task_action_run_tokens.pop(action.action_id, None)
            self._set_task_action_play_state(button, armed=False, fired=True)
            self._run_task_action_with_current_bindings(action)
            GLib.timeout_add(180, self._clear_task_action_play_flash, button)
            return
        token = self.task_action_run_tokens.get(action.action_id, 0) + 1
        self.task_action_run_tokens[action.action_id] = token
        self._set_task_action_play_state(button, armed=True, fired=False)
        GLib.timeout_add(500, self._disarm_task_action_play_button, action.action_id, token, button)

    def _on_task_action_play_button_press(
        self,
        button: Gtk.Button,
        event: Gdk.EventButton,
        action: TaskAction,
    ) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button in {2, 3}:
            self._task_action_context_menu(action).popup_at_widget(
                button,
                Gdk.Gravity.SOUTH_WEST,
                Gdk.Gravity.NORTH_WEST,
                event,
            )
            return True
        return False

    def _disarm_task_action_play_button(self, action_id: str, token: int, button: Gtk.Button) -> bool:
        if self.task_action_run_tokens.get(action_id) == token:
            self.task_action_run_tokens.pop(action_id, None)
            self._set_task_action_play_state(button, armed=False, fired=False)
        return False

    def _clear_task_action_play_flash(self, button: Gtk.Button) -> bool:
        self._set_task_action_play_state(button, armed=False, fired=False)
        return False

    def _set_task_action_play_state(self, button: Gtk.Button, *, armed: bool, fired: bool) -> None:
        context = button.get_style_context()
        if armed:
            context.add_class("task-action-run-armed")
        else:
            context.remove_class("task-action-run-armed")
        if fired:
            context.add_class("task-action-run-fired")
        else:
            context.remove_class("task-action-run-fired")

    def _on_task_shortcut_button_press(
        self,
        button: Gtk.Button,
        event: Gdk.EventButton,
        action: TaskAction,
    ) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button in {2, 3}:
            self._task_shortcut_context_menu(action).popup_at_widget(
                button,
                Gdk.Gravity.SOUTH_WEST,
                Gdk.Gravity.NORTH_WEST,
                event,
            )
            return True
        return False

    def _render_global_task_parameters(self) -> None:
        if self.global_task_parameter_box is None:
            return
        for child in self.global_task_parameter_box.get_children():
            self.global_task_parameter_box.remove(child)
        for parameter in self._global_task_parameters():
            button = _compact_button(self._parameter_button_label(parameter), None, max_width_chars=18)
            button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            button.connect("clicked", self._on_task_parameter_clicked, parameter)
            button.connect("button-press-event", self._on_task_parameter_button_press, parameter)
            item_id = parameter.global_name or parameter.name
            _flow_box_add(
                self.global_task_parameter_box,
                self._task_reorderable_widget(
                    button,
                    group="global_parameter",
                    item_id=item_id,
                    label=self._parameter_button_label(parameter),
                ),
            )
        self.global_task_parameter_box.show_all()

    def _global_task_parameters(self) -> list[TaskActionParameter]:
        parameters: list[TaskActionParameter] = []
        seen: set[str] = set()
        for action in self.task_base_actions:
            for parameter in action.parameters:
                if parameter.global_name and parameter.global_name not in seen:
                    parameters.append(parameter)
                    seen.add(parameter.global_name)
        if self.task_action_config is not None:
            order = {name: index for index, name in enumerate(self.task_action_config.global_parameter_bindings)}
            parameters.sort(key=lambda parameter: order.get(parameter.global_name or "", len(order)))
        return parameters

    def _render_task_action_parameters(self) -> None:
        self._clear_task_action_parameters()
        for child in self.task_shortcuts_box.get_children():
            self.task_shortcuts_box.remove(child)
        action = self.selected_task_action
        if action is None:
            self.task_action_parameter_box.show_all()
            return
        local_parameters = [parameter for parameter in action.parameters if not parameter.global_name]
        if not local_parameters:
            no_parameters = Gtk.Label(label=self._s("action.no_parameters"))
            no_parameters.set_margin_start(4)
            _flow_box_add(self.task_action_parameter_box, no_parameters)
        for parameter in local_parameters:
            button = _compact_button(self._parameter_button_label(parameter), None, max_width_chars=18)
            button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            button.connect("clicked", self._on_task_parameter_clicked, parameter)
            button.connect("button-press-event", self._on_task_parameter_button_press, parameter)
            _flow_box_add(
                self.task_action_parameter_box,
                self._task_reorderable_widget(
                    button,
                    group="parameter",
                    item_id=parameter.name,
                    label=self._parameter_button_label(parameter),
                ),
            )
        for shortcut in self._shortcuts_for_action(action):
            shortcut_button = self._task_action_button(shortcut, shortcut=True)
            _flow_box_add(
                self.task_shortcuts_box,
                self._task_reorderable_widget(
                    shortcut_button,
                    group="shortcut",
                    item_id=shortcut.action_id,
                    label=shortcut.label,
                ),
            )
        shortcut_button = _compact_button(self._s("action.save_shortcut"), None, max_width_chars=24)
        shortcut_button.connect("clicked", lambda _button: self._save_selected_action_as_shortcut())
        self.save_task_shortcut_box.pack_start(shortcut_button, False, False, 0)
        self.task_action_parameter_box.show_all()
        self.task_shortcuts_box.show_all()
        self.save_task_shortcut_box.show_all()

    def _shortcuts_for_action(self, action: TaskAction) -> list[TaskAction]:
        return [
            shortcut
            for shortcut in self.task_shortcuts
            if shortcut.base_action_id == (action.base_action_id or action.action_id)
        ]

    def _parameter_button_label(self, parameter: TaskActionParameter) -> str:
        selected = self._selected_parameter_value(parameter)
        config = self.task_action_config
        values = config.parameter_sets.get(parameter.set_name, {}) if config is not None else {}
        label = values.get(selected, {}).get("name") or values.get(selected, {}).get("label", selected)
        return f"{parameter.label}: {label}"

    def _selected_parameter_value(self, parameter: TaskActionParameter) -> str:
        config = self.task_action_config
        if parameter.global_name and config is not None:
            selected = config.global_parameter_bindings.get(parameter.global_name)
            if selected:
                return selected
        return self.selected_task_action_bindings.get(parameter.name) or parameter.default

    def _on_task_parameter_clicked(self, button: Gtk.Button, parameter: TaskActionParameter) -> None:
        menu = Gtk.Menu()
        values = self._parameter_values(parameter)
        if not values:
            item = Gtk.MenuItem(label=self._s("action.no_values"))
            item.set_sensitive(False)
            menu.append(item)
        for value_id, fields in values.items():
            label = fields.get("label", value_id)
            item = Gtk.MenuItem(label=label)
            item.connect("activate", lambda _item, selected=value_id: self._select_task_parameter(parameter, selected))
            menu.append(item)
        menu.show_all()
        menu.popup_at_widget(button, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def _on_task_parameter_button_press(
        self,
        button: Gtk.Button,
        event: Gdk.EventButton,
        parameter: TaskActionParameter,
    ) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button in {2, 3}:
            self._task_parameter_context_menu(parameter).popup_at_widget(
                button,
                Gdk.Gravity.SOUTH_WEST,
                Gdk.Gravity.NORTH_WEST,
                event,
            )
            return True
        return False

    def _select_task_parameter(self, parameter: TaskActionParameter, selected: str) -> None:
        if parameter.global_name:
            self._select_global_task_parameter(parameter, selected)
            return
        self.selected_task_action_bindings[parameter.name] = selected
        self._render_task_action_parameters()
        self._update_task_action_button_selection()

    def _select_global_task_parameter(self, parameter: TaskActionParameter, selected: str) -> None:
        task = self._require_task(show_dialog=False)
        if task is None or not parameter.global_name:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        globals_data = data.setdefault("global_parameters", {})
        if isinstance(globals_data, dict):
            definition = globals_data.get(parameter.global_name)
            if isinstance(definition, dict):
                definition["value"] = selected
            else:
                globals_data[parameter.global_name] = {
                    "label": parameter.label,
                    "type": parameter.parameter_type,
                    "value": selected,
                }
            save_task_actions_data(task, data)
        self._load_task_action_buttons()

    def _run_selected_task_action(self) -> None:
        action = self.selected_task_action
        if action is not None:
            self._run_task_action_with_current_bindings(action)

    def _run_task_action_with_current_bindings(self, action: TaskAction) -> None:
        config = self.task_action_config
        if config is None:
            return
        selected_id = self.selected_task_action.action_id if self.selected_task_action is not None else None
        bindings = self.selected_task_action_bindings if selected_id == action.action_id else dict(action.bindings or {})
        bound = bind_task_action_parameters(action, config.parameter_sets, bindings, config.global_parameter_bindings)
        self.run_custom_task_action(bound)

    def _parameter_values(self, parameter: TaskActionParameter) -> dict[str, dict[str, str]]:
        config = self.task_action_config
        if config is None:
            return {}
        return config.parameter_sets.get(parameter.set_name, {})

    def _task_parameter_context_menu(self, parameter: TaskActionParameter) -> Gtk.Menu:
        menu = Gtk.Menu()
        selected = self._selected_parameter_value(parameter)
        add_item = Gtk.MenuItem(label=self._s("action.add_value", set_name=parameter.set_name))
        add_item.connect("activate", lambda _item: self._edit_parameter_set_value(parameter, None, None))
        duplicate_item = Gtk.MenuItem(label=self._s("action.duplicate_value", value=selected))
        duplicate_item.connect(
            "activate",
            lambda _item: self._edit_parameter_set_value(
                parameter,
                None,
                self._parameter_values(parameter).get(selected, {}),
            ),
        )
        edit_item = Gtk.MenuItem(label=self._s("action.edit_value", value=selected))
        edit_item.connect(
            "activate",
            lambda _item: self._edit_parameter_set_value(
                parameter,
                selected,
                self._parameter_values(parameter).get(selected, {}),
            ),
        )
        delete_item = Gtk.MenuItem(label=self._s("action.delete_value", value=selected))
        delete_item.connect("activate", lambda _item: self._delete_parameter_set_value(parameter, selected))
        reorder_key = "action.stop_reorder_actions" if self.task_action_reorder_mode else "action.reorder_actions"
        reorder_item = Gtk.MenuItem(label=self._s(reorder_key))
        reorder_item.connect("activate", lambda _item: self._set_task_action_reorder_mode(not self.task_action_reorder_mode))
        menu.append(add_item)
        menu.append(duplicate_item)
        menu.append(edit_item)
        menu.append(delete_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(reorder_item)
        menu.show_all()
        return menu

    def _task_action_context_menu(self, action: TaskAction) -> Gtk.Menu:
        task = self._require_task(show_dialog=False)
        actions_file = task.path / TASK_ACTIONS_FILE if task is not None else None
        code_path = self._task_action_code_path(action)
        menu = Gtk.Menu()
        run_item = Gtk.MenuItem(label=self._s("action.run"))
        run_item.connect("activate", lambda _item: self._run_task_action_with_current_bindings(action))
        open_item = Gtk.MenuItem(label=self._s("action.open_actions_file"))
        if actions_file is not None:
            open_item.connect("activate", lambda _item, path=actions_file: open_text_file(path))
        else:
            open_item.set_sensitive(False)
        edit_item = Gtk.MenuItem(label=self._s("action.edit"))
        if code_path is not None:
            edit_item.connect("activate", lambda _item, path=code_path: self._edit_action_code_file(path))
        else:
            edit_item.set_sensitive(False)
        reorder_key = "action.stop_reorder_actions" if self.task_action_reorder_mode else "action.reorder_actions"
        reorder_item = Gtk.MenuItem(label=self._s(reorder_key))
        reorder_item.connect("activate", lambda _item: self._set_task_action_reorder_mode(not self.task_action_reorder_mode))
        menu.append(run_item)
        menu.append(open_item)
        menu.append(edit_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(reorder_item)
        menu.show_all()
        return menu

    def _task_action_code_path(self, action: TaskAction) -> Path | None:
        command = action.command
        if isinstance(command, str):
            try:
                tokens = shlex.split(command)
            except ValueError:
                return None
        else:
            tokens = list(command)
        if not tokens:
            return None
        script_index = 1 if tokens[0] in {"bash", "sh", "python", "python3"} and len(tokens) > 1 else 0
        candidate = Path(tokens[script_index])
        if not candidate.is_absolute():
            candidate = action.cwd / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(action.cwd.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def _edit_action_code_file(self, path: Path) -> None:
        try:
            open_text_file(path)
        except OSError as error:
            self._show_error(self._s("action.cannot_open_code"), str(error))

    def _task_shortcut_context_menu(self, action: TaskAction) -> Gtk.Menu:
        menu = Gtk.Menu()
        run_item = Gtk.MenuItem(label=self._s("action.run"))
        run_item.connect("activate", lambda _item: self.run_custom_task_action(action))
        delete_item = Gtk.MenuItem(label=self._s("action.delete_shortcut"))
        delete_item.connect("activate", lambda _item: self._delete_task_shortcut(action))
        reorder_key = "action.stop_reorder_actions" if self.task_action_reorder_mode else "action.reorder_actions"
        reorder_item = Gtk.MenuItem(label=self._s(reorder_key))
        reorder_item.connect("activate", lambda _item: self._set_task_action_reorder_mode(not self.task_action_reorder_mode))
        menu.append(run_item)
        menu.append(delete_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(reorder_item)
        menu.show_all()
        return menu

    def _move_task_action(self, action: TaskAction, offset: int) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        actions = data.get("actions")
        if isinstance(actions, list) and _move_json_list_entry(actions, "id", action.action_id, offset):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _move_task_action_before(self, source_id: str, target_id: str) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        actions = data.get("actions")
        if isinstance(actions, list) and _move_json_list_entry_before(actions, "id", source_id, target_id):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _save_task_action_order(self, order: list[str]) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        actions = data.get("actions")
        if isinstance(actions, list) and _reorder_json_list_by_ids(actions, "id", order):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _task_reorder_order(self, group: str) -> list[str]:
        if group == "action":
            return self._task_action_order()
        if group == "parameter":
            return self._task_parameter_order()
        if group == "global_parameter":
            return self._global_task_parameter_order()
        if group == "shortcut":
            return self._task_shortcut_order()
        return []

    def _task_reorder_invalidate_sort(self) -> None:
        group = self.task_reorder_group
        if not group:
            return
        self.task_reorder_pending_sort_groups.add(group)
        if self.task_reorder_sort_source_id is None:
            self.task_reorder_sort_source_id = GLib.timeout_add(
                _TASK_REORDER_FRAME_DELAY_MS,
                self._flush_task_reorder_sort,
            )

    def _flush_task_reorder_sort(self) -> bool:
        groups = set(self.task_reorder_pending_sort_groups)
        self.task_reorder_pending_sort_groups.clear()
        self.task_reorder_sort_source_id = None
        for group in groups:
            self._invalidate_task_reorder_group_sort(group)
        return False

    def _invalidate_task_reorder_group_sort(self, group: str) -> None:
        if group == "action":
            self.task_actions_box.invalidate_sort()
        elif group == "parameter":
            self.task_action_parameter_box.invalidate_sort()
        elif group == "global_parameter" and self.global_task_parameter_box is not None:
            self.global_task_parameter_box.invalidate_sort()
        elif group == "shortcut":
            self.task_shortcuts_box.invalidate_sort()

    def _save_task_reorder_order(self, group: str, order: list[str]) -> None:
        if group == "action":
            self._save_task_action_order(order)
        elif group == "parameter":
            self._save_task_parameter_order(order)
        elif group == "global_parameter":
            self._save_global_task_parameter_order(order)
        elif group == "shortcut":
            self._save_task_shortcut_order(order)

    def _save_task_shortcut_order(self, order: list[str]) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        shortcuts = data.get("shortcuts")
        if isinstance(shortcuts, list) and _reorder_json_list_subset_by_ids(shortcuts, "id", order):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _save_task_parameter_order(self, order: list[str]) -> None:
        action = self.selected_task_action
        task = self._require_task(show_dialog=False)
        if action is None or task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        if _reorder_action_parameter_entries(data, action.action_id, order):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _save_global_task_parameter_order(self, order: list[str]) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        global_parameters = data.get("global_parameters")
        if isinstance(global_parameters, dict) and _reorder_json_mapping_by_ids(global_parameters, order):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _set_task_action_reorder_mode(self, enabled: bool) -> None:
        self.task_action_reorder_mode = enabled
        self._load_task_action_buttons()

    def _move_task_shortcut(self, action: TaskAction, offset: int) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        shortcuts = data.get("shortcuts")
        if isinstance(shortcuts, list) and _move_json_list_entry(shortcuts, "id", action.action_id, offset):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _move_task_parameter(self, parameter: TaskActionParameter, offset: int) -> None:
        if parameter.global_name:
            self._move_global_task_parameter(parameter.global_name, offset)
            return
        action = self.selected_task_action
        task = self._require_task(show_dialog=False)
        if action is None or task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        if _move_action_parameter_entry(data, action.action_id, parameter.name, offset):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _move_global_task_parameter(self, global_name: str, offset: int) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        global_parameters = data.get("global_parameters")
        if isinstance(global_parameters, dict) and _move_json_mapping_entry(global_parameters, global_name, offset):
            save_task_actions_data(task, data)
            self._load_task_action_buttons()

    def _edit_parameter_set_value(
        self,
        parameter: TaskActionParameter,
        value_id: str | None,
        initial: dict[str, str] | None,
    ) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        fields = dict(initial or {})
        dialog = Gtk.Dialog(
            title=f"{'Edit' if value_id else 'Add'} {parameter.set_name}",
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("save"), Gtk.ResponseType.OK)
        grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        grid.set_border_width(10)
        content = dialog.get_content_area()
        content.pack_start(grid, True, True, 0)
        field_getters: dict[str, Callable[[], str]] = {}
        known_fields = _parameter_type_fields(data, parameter.parameter_type) or {"name"}
        for value in self._parameter_values(parameter).values():
            known_fields.update(value)
        field_names = _parameter_field_order(parameter.parameter_type, set(fields) | known_fields)
        for row, field_name in enumerate(field_names):
            editor, getter = self._parameter_field_editor(
                data,
                parameter.parameter_type,
                field_name,
                fields.get(field_name, ""),
            )
            field_getters[field_name] = getter
            grid.attach(Gtk.Label(label=field_name), 0, row, 1, 1)
            grid.attach(editor, 1, row, 1, 1)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name_text = field_getters.get("name", lambda: "")().strip()
            new_id = _parameter_value_id_from_name(name_text or value_id or parameter.set_name)
            if new_id:
                value: dict[str, str] = {}
                for field_name, getter in field_getters.items():
                    text = getter()
                    if text:
                        value[field_name] = text
                parameter_sets = data.setdefault("parameter_sets", {})
                if isinstance(parameter_sets, dict):
                    set_values = parameter_sets.setdefault(parameter.set_name, {})
                    if isinstance(set_values, dict):
                        if value_id != new_id:
                            new_id = _unique_parameter_value_id(new_id, set_values)
                        if value_id and value_id != new_id:
                            set_values.pop(value_id, None)
                        set_values[new_id] = value
                        save_task_actions_data(task, data)
                        self._load_task_action_buttons()
        dialog.destroy()

    def _parameter_field_editor(
        self,
        data: dict[str, object],
        parameter_type: str,
        field_name: str,
        value: str,
    ) -> tuple[Gtk.Widget, Callable[[], str]]:
        field_type = _parameter_field_type(data, parameter_type, field_name)
        enum_values = _field_type_enum_values(data, field_type)
        if enum_values is not None:
            combo = Gtk.ComboBoxText()
            active_index = 0
            values = enum_values if value in enum_values else [value, *enum_values] if value else enum_values
            for index, item in enumerate(values):
                combo.append_text(item)
                if item == value:
                    active_index = index
            if values:
                combo.set_active(active_index)
            return combo, lambda: combo.get_active_text() or ""

        if field_type in {"file", "folder"}:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            entry = Gtk.Entry()
            entry.set_text(value)
            row.pack_start(entry, True, True, 0)
            browse = Gtk.Button(label=self._s("action.browse"))
            browse.connect("clicked", lambda _button: self._choose_parameter_path(entry, field_type))
            row.pack_start(browse, False, False, 0)
            return row, lambda: entry.get_text()

        entry = Gtk.Entry()
        entry.set_text(value)
        return entry, lambda: entry.get_text()

    def _choose_parameter_path(self, entry: Gtk.Entry, field_type: str) -> None:
        action = Gtk.FileChooserAction.SELECT_FOLDER if field_type == "folder" else Gtk.FileChooserAction.OPEN
        dialog = Gtk.FileChooserDialog(
            title=self._s("action.choose_folder") if field_type == "folder" else self._s("action.choose_file"),
            transient_for=self.window,
            action=action,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        current = entry.get_text().strip()
        if current:
            current_path = Path(current).expanduser()
            if current_path.exists():
                if current_path.is_dir():
                    dialog.set_current_folder(str(current_path))
                else:
                    dialog.set_filename(str(current_path))
        if dialog.run() == Gtk.ResponseType.OK:
            selected = dialog.get_filename()
            if selected:
                entry.set_text(selected)
        dialog.destroy()

    def _delete_parameter_set_value(self, parameter: TaskActionParameter, value_id: str) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        parameter_sets = data.get("parameter_sets")
        if isinstance(parameter_sets, dict):
            set_values = parameter_sets.get(parameter.set_name)
            if isinstance(set_values, dict):
                set_values.pop(value_id, None)
                save_task_actions_data(task, data)
        self._load_task_action_buttons()

    def _save_selected_action_as_shortcut(self) -> None:
        action = self.selected_task_action
        task = self._require_task(show_dialog=False)
        if action is None or task is None:
            return
        dialog = Gtk.Dialog(title=self._s("action.save_shortcut_title"), transient_for=self.window, flags=Gtk.DialogFlags.MODAL)
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("save"), Gtk.ResponseType.OK)
        grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        grid.set_border_width(10)
        dialog.get_content_area().pack_start(grid, True, True, 0)
        label_entry = Gtk.Entry()
        label_entry.set_text(action.label)
        id_entry = Gtk.Entry()
        id_entry.set_text(_shortcut_id_from_label(action.label))
        grid.attach(Gtk.Label(label="label"), 0, 0, 1, 1)
        grid.attach(label_entry, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="id"), 0, 1, 1, 1)
        grid.attach(id_entry, 1, 1, 1, 1)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            shortcut_id = id_entry.get_text().strip()
            label = label_entry.get_text().strip()
            if shortcut_id and label:
                data, errors = load_task_actions_data(task)
                if not errors:
                    shortcuts = data.setdefault("shortcuts", [])
                    if isinstance(shortcuts, list):
                        shortcuts.append(
                            {
                                "id": shortcut_id,
                                "label": label,
                                "action": action.base_action_id or action.action_id,
                                "bindings": dict(self.selected_task_action_bindings),
                            }
                        )
                        save_task_actions_data(task, data)
                        self._load_task_action_buttons()
        dialog.destroy()

    def _delete_task_shortcut(self, action: TaskAction) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return
        shortcuts = data.get("shortcuts")
        if isinstance(shortcuts, list):
            data["shortcuts"] = [
                entry for entry in shortcuts if not (isinstance(entry, dict) and entry.get("id") == action.action_id)
            ]
            save_task_actions_data(task, data)
        self._load_task_action_buttons()

    def _watch_task_actions(self, task: TaskSummary) -> None:
        if self.task_actions_monitor_path == task.path:
            return
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
            self.task_actions_monitor = None
        self.task_actions_monitor_path = task.path
        try:
            monitor = Gio.File.new_for_path(str(task.path)).monitor_directory(
                Gio.FileMonitorFlags.NONE,
                None,
            )
        except GLib.Error as error:
            self.task_action_errors = [str(error)]
            self._update_actions_message()
            return
        monitor.connect("changed", self._on_task_actions_dir_changed)
        self.task_actions_monitor = monitor

    def _on_task_actions_dir_changed(
        self,
        _monitor: Gio.FileMonitor,
        file: Gio.File,
        _other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        if event_type not in _TASK_ACTIONS_MONITOR_EVENTS:
            return
        if file.get_basename() != TASK_ACTIONS_FILE:
            return
        task = self.selected_task
        if task is None:
            return
        signature = _task_actions_signature(task)
        if signature == self.task_actions_signature:
            return
        self._load_task_action_buttons()

    def _update_actions_message(self) -> None:
        messages: list[str] = []
        if self.status_message:
            messages.append(self.status_message)
        messages.extend(getattr(self, "task_action_errors", []))
        self.actions_message.set_text("\n".join(messages))

    def _set_status_message(self, message: str) -> None:
        self.status_message = message
        self._update_actions_message()

    def new_console(self, *_args: object, task: TaskSummary | None = None) -> int | None:
        task = task or self._require_task()
        if task is None:
            return None
        shell = os.environ.get("SHELL") or "/bin/bash"
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env["PS1"] = f"{task.name}$ "
        env["PROMPT_COMMAND"] = ""
        command = [shell]
        return self._start_terminal(
            task=task,
            command=command,
            cwd=task.path,
            env=env,
            kind="shell",
        )

    def _selected_agent(self) -> str:
        return normalize_agent(self.agent_combo.get_active_text())

    def _set_selected_agent(self, agent: str) -> None:
        agent = normalize_agent(agent)
        self._updating_agent_selection = True
        try:
            self.agent_combo.set_active(AGENT_WORKSPACE_AGENTS.index(agent))
        finally:
            self._updating_agent_selection = False

    def _on_agent_selected(self, *_args: object) -> None:
        if self._updating_agent_selection:
            return
        task = self.selected_task
        if task is not None:
            agent = self._selected_agent()
            current = self._running_agent_session(task)
            if current is None or current.kind == agent:
                old_agent = load_task_agent(task, self.default_agent)
                if old_agent != agent and task_agent_has_resumable_state(task, self.workspace, old_agent):
                    if not self._confirm_saved_agent_session_delete(old_agent, agent):
                        self._set_selected_agent(old_agent)
                        return
                    clear_task_agent_session(task, old_agent)
                    self._invalidate_task_session_marker_cache(task)
                save_task_agent(task, agent)
                self._invalidate_task_session_marker_cache(task)
                self._update_codex_button_state()
                return
            self._switch_task_agent(task, agent, start_if_changed=True)

    def run_ai_agent_console(self, *_args: object) -> None:
        task = self._require_task()
        if task is None:
            return
        agent = self._selected_agent()
        self._switch_task_agent(task, agent, start_if_changed=True)

    def reset_ai_agent_session(self, *_args: object) -> None:
        task = self._require_task()
        if task is None:
            return
        agent = self._selected_agent()
        if not self._confirm_agent_session_reset(agent):
            return
        for session in self._current_task_terminal_sessions(task):
            if session.kind == agent and session_is_agent(session_kind=session.kind):
                self._close_console_session(session, confirm=False, ensure_default=False)
                break
        reset_task_agent_session(task, agent)
        self._invalidate_task_session_marker_cache(task)
        self._update_codex_button_state()
        self._refresh_task_row_styles()

    def _agent_model(self, agent: str) -> str:
        return self._agent_model_settings(agent).model

    def _agent_reasoning_effort(self, agent: str) -> str:
        return self._agent_model_settings(agent).reasoning_effort

    def _agent_model_settings(self, agent: str) -> AgentModelSettings:
        return ai_agent_model_settings(
            agent,
            codex_model=self.default_codex_model,
            codex_reasoning=self.default_codex_reasoning,
            claude_model=self.default_claude_model,
            claude_effort=self.default_claude_effort,
        )

    def _switch_task_agent(self, task: TaskSummary, agent: str, *, start_if_changed: bool) -> None:
        agent = normalize_agent(agent)
        current = self._running_agent_session(task)
        decision = ai_agent_switch_decision(
            agent,
            current_agent=current.kind if current is not None else None,
            start_if_changed=start_if_changed,
        )
        agent = decision.agent
        if decision.action == "activate_current":
            save_task_agent_session(task, agent)
            self._invalidate_task_session_marker_cache(task)
            self._activate_terminal(current.session_id)
            self._update_codex_button_state()
            return
        if decision.action == "keep_current":
            self._set_selected_agent(agent)
            save_task_agent(task, agent)
            self._invalidate_task_session_marker_cache(task)
            return
        if decision.action == "confirm_switch":
            current_agent = decision.current_agent or agent
            if not self._confirm_agent_switch(current_agent, agent):
                self._set_selected_agent(current_agent)
                save_task_agent(task, current_agent)
                self._invalidate_task_session_marker_cache(task)
                return
        if not self._ensure_agent_installed(agent):
            if current is not None:
                self._set_selected_agent(current.kind)
            return
        if current is not None:
            save_task_agent_session(task, current.kind)
            self._invalidate_task_session_marker_cache(task)
            self._close_console_session(current, confirm=False, ensure_default=False)
        launch = prepare_ai_agent_launch_command(
            task,
            self.workspace,
            agent,
            codex_model=self.default_codex_model,
            codex_reasoning=self.default_codex_reasoning,
            claude_model=self.default_claude_model,
            claude_effort=self.default_claude_effort,
            codex_executable=_codex_executable(),
            claude_executable=_claude_executable(),
            prompt_suffix=f"Отвечай пользователю на {self.language} языке.",
        )
        for session in self._current_task_terminal_sessions(task):
            if session.kind == agent:
                self._activate_terminal(session.session_id)
                self._update_codex_button_state()
                return
        self._start_terminal(
            task=task,
            command=launch.command,
            cwd=self.workspace,
            env=os.environ.copy(),
            kind=agent,
        )
        self._update_codex_button_state()

    def _running_agent_session(self, task: TaskSummary) -> TerminalSession | None:
        for session in self._current_task_terminal_sessions(task):
            if session_is_running_agent(session_kind=session.kind, exited=session.exited):
                return session
        return None

    def _running_agent_sessions(self) -> list[TerminalSession]:
        return [
            session
            for session in self.terminal_sessions.values()
            if session_is_running_agent(session_kind=session.kind, exited=session.exited)
        ]

    def _confirm_agent_switch(self, current_agent: str, next_agent: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_switch_agent_title"),
        )
        dialog.format_secondary_text(
            self._tr("confirm_switch_agent_body").format(
                current=agent_label(current_agent),
                next=agent_label(next_agent),
            )
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _confirm_saved_agent_session_delete(self, old_agent: str, new_agent: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_delete_saved_agent_session_title"),
        )
        dialog.format_secondary_text(
            self._tr("confirm_delete_saved_agent_session_body").format(
                old_agent=agent_label(old_agent),
                new_agent=agent_label(new_agent),
            )
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _confirm_agent_session_reset(self, agent: str) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_reset_agent_session_title"),
        )
        dialog.format_secondary_text(
            self._tr("confirm_reset_agent_session_body").format(
                agent=agent_label(agent),
            )
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("confirm_reset_agent_session_button"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _ensure_agent_installed(self, agent: str) -> bool:
        if agent_executable(agent):
            return True
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("install_agent_title"),
        )
        dialog.format_secondary_text(
            self._tr("install_agent_body").format(
                agent=agent_label(agent),
                command=agent_install_command(agent),
            )
        )
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        dialog.run()
        dialog.destroy()
        return False

    def _confirm_close_with_running_agents(self) -> bool:
        sessions = self._running_agent_sessions()
        if not sessions:
            return True
        labels = ", ".join(
            f"{agent_label(session.kind)} ({session.task_path.name})"
            for session in sessions[:5]
        )
        if len(sessions) > 5:
            labels += f", and {len(sessions) - 5} more"
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_close_running_agents_title"),
        )
        dialog.format_secondary_text(
            self._tr("confirm_close_running_agents_body").format(sessions=labels)
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def run_codex_console(self, *_args: object) -> None:
        self._set_selected_agent("codex")
        self.run_ai_agent_console()

    def close_active_console(self, *_args: object) -> None:
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return
        page = self.console_notebook.get_nth_page(page_num)
        session = self._session_for_page(page)
        if session is not None:
            self._close_console_session(session)
            return
        for session_id, session in list(self.terminal_sessions.items()):
            if session.page is page:
                self._close_console_session(session)
                break

    def _send_command_to_task_terminal(self, task: TaskSummary, command: str) -> None:
        session = self._active_shell_for_task(task) or self._first_terminal_for_task(task)
        if session is None:
            session_id = self.new_console(task=task)
            if session_id is not None:
                GLib.timeout_add(250, self._send_command_to_session_once, session_id, command + "\n")
            return
        self._activate_terminal(session.session_id)
        GLib.timeout_add(50, self._send_command_to_session_once, session.session_id, command + "\n")

    def _send_command_to_session_once(self, session_id: int, command: str) -> bool:
        session = self.terminal_sessions.get(session_id)
        if session is not None:
            self._activate_terminal(session_id)
            _feed_terminal(session.terminal, command)
        return False

    def _start_terminal(
        self,
        task: TaskSummary,
        command: list[str],
        cwd: Path,
        env: dict[str, str],
        kind: str,
    ) -> int:
        session_id = self.next_terminal_id
        self.next_terminal_id += 1
        terminal = Vte.Terminal()
        terminal.set_scrollback_lines(20_000)
        terminal.set_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        self._apply_terminal_theme(terminal)
        terminal.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        terminal.connect("button-press-event", self._on_terminal_button_press)
        terminal.connect("popup-menu", self._on_terminal_popup_menu)
        terminal.connect("key-press-event", self._on_terminal_key_press)
        terminal.connect("contents-changed", self._on_terminal_contents_changed)
        terminal.connect("child-exited", self._on_terminal_child_exited)
        terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            str(cwd),
            command,
            _terminal_env(env),
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None,
            None,
        )
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(terminal)
        session = TerminalSession(
            session_id=session_id,
            task_path=task.path,
            kind=kind,
            terminal=terminal,
            page=scrolled,
            busy=session_is_agent(session_kind=kind),
            run_id=new_agent_session_id() if session_is_agent(session_kind=kind) else None,
        )
        self.terminal_sessions[session_id] = session
        if session.run_id is not None:
            save_task_active_agent_run(task, kind, session.run_id)
        self._renumber_terminal_tabs(task)
        if self.selected_task is not None and self.selected_task.path == task.path:
            self._show_terminal_tab(session)
        self._activate_terminal(session_id)
        return session_id

    def _on_terminal_child_exited(self, terminal: Vte.Terminal, _status: int) -> None:
        session = self._session_for_terminal(terminal)
        if session is None:
            return
        session.exited = True
        session.busy = False
        session.permission_pending = False
        session.permission_signature = None
        session.ignored_permission_signature = None
        if session.run_id is not None:
            clear_task_active_agent_run(
                self._task_for_path(session.task_path),
                run_id=session.run_id,
                agent=session.kind,
            )
        self._update_codex_button_state()
        self._refresh_task_row_styles()

    def _refresh_console_tabs_for_task(self, task: TaskSummary) -> None:
        last_active_session_id = self.last_active_terminal_by_task.get(task.path)
        self._refreshing_console_tabs = True
        try:
            while self.console_notebook.get_n_pages() > 0:
                self.console_notebook.remove_page(0)
            self._ensure_ai_agent_console_page()
            self._clear_ai_agent_terminal_page()
            self._renumber_terminal_tabs(task)
            for session in self._current_task_terminal_sessions(task):
                self._show_terminal_tab(session, renumber=False)
            self._renumber_terminal_tabs(task)
        finally:
            self._refreshing_console_tabs = False
        if last_active_session_id is not None:
            self._activate_visible_terminal(last_active_session_id, remember=False)
        else:
            page_num = self.console_notebook.get_current_page()
            if page_num >= 0:
                session = self._session_for_page(self.console_notebook.get_nth_page(page_num))
                if session is not None:
                    self._activate_visible_terminal(session.session_id, remember=False)
        self._update_codex_button_state()

    def _current_task_terminal_sessions(self, task: TaskSummary) -> list[TerminalSession]:
        return sorted(
            [
                session
                for session in self.terminal_sessions.values()
                if session.task_path == task.path
            ],
            key=lambda session: _terminal_session_sort_key(session.kind, session.session_id),
        )

    def _renumber_terminal_tabs(self, task: TaskSummary) -> None:
        shell_index = 0
        for session in self._current_task_terminal_sessions(task):
            if session.kind == "shell":
                shell_index += 1
            tab = self.console_notebook.get_tab_label(session.page)
            label = _terminal_tab_text_label(tab)
            if label is not None:
                label.set_text(_terminal_tab_label(session.kind, shell_index, language=self.language))

    def _show_terminal_tab(self, session: TerminalSession, *, renumber: bool = True) -> None:
        if session_is_agent(session_kind=session.kind):
            self._ensure_ai_agent_console_page()
            self._set_ai_agent_terminal_page(session.page)
            if self.console_notebook.page_num(self.ai_agent_page) >= 0:
                self.console_notebook.set_current_page(self.console_notebook.page_num(self.ai_agent_page))
            session.page.show_all()
            return
        if self.console_notebook.page_num(session.page) < 0:
            tab = self._terminal_tab_widget(session)
            self.console_notebook.append_page(session.page, tab)
        session.page.show_all()
        if renumber:
            self._renumber_terminal_tabs(self._task_for_path(session.task_path))

    def _terminal_tab_widget(self, session: TerminalSession) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label=session.kind)
        close_button = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.set_focus_on_click(False)
        close_button.set_tooltip_text(self._tr("close"))
        close_button.connect("clicked", lambda *_: self._close_console_session(session))
        box.pack_start(label, True, True, 0)
        box.pack_start(close_button, False, False, 0)
        box.show_all()
        return box

    def _activate_terminal(self, session_id: int) -> None:
        session = self.terminal_sessions.get(session_id)
        if session is None:
            return
        self._show_terminal_tab(session)
        self._activate_visible_terminal(session_id, remember=True)

    def _activate_visible_terminal(self, session_id: int, *, remember: bool) -> None:
        session = self.terminal_sessions.get(session_id)
        if session is None:
            return
        page_num = self.console_notebook.page_num(session.page)
        if page_num >= 0:
            self.console_notebook.set_current_page(page_num)
            if remember:
                self.last_active_terminal_by_task[session.task_path] = session.session_id
        elif session_is_agent(session_kind=session.kind) and self.ai_agent_page is not None:
            agent_page_num = self.console_notebook.page_num(self.ai_agent_page)
            if agent_page_num >= 0:
                self.console_notebook.set_current_page(agent_page_num)
                if remember:
                    self.last_active_terminal_by_task[session.task_path] = session.session_id
        session.terminal.grab_focus()

    def _remember_current_console_tab(self) -> None:
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return
        page = self.console_notebook.get_nth_page(page_num)
        session = self._session_for_page(page)
        if session is not None:
            self.last_active_terminal_by_task[session.task_path] = session.session_id

    def _on_console_notebook_switch_page(
        self,
        _notebook: Gtk.Notebook,
        page: Gtk.Widget,
        _page_num: int,
    ) -> None:
        if self._refreshing_console_tabs:
            return
        session = self._session_for_page(page)
        if session is not None:
            self.last_active_terminal_by_task[session.task_path] = session.session_id

    def _on_console_notebook_button_press(self, notebook: Gtk.Notebook, event: Gdk.EventButton) -> bool:
        if event.type != Gdk.EventType.DOUBLE_BUTTON_PRESS or event.button != 1:
            return False
        if self.selected_task is None:
            return False
        if not _notebook_event_in_empty_tab_area(notebook, event):
            return False
        self.new_console(task=self.selected_task)
        return True

    def _close_console_session(
        self,
        session: TerminalSession,
        *,
        confirm: bool = True,
        ensure_default: bool = True,
    ) -> bool:
        if confirm and not self._confirm_close_console():
            return False
        task = self._task_for_path(session.task_path)
        page_num = self.console_notebook.page_num(session.page)
        if page_num >= 0:
            self.console_notebook.remove_page(page_num)
        else:
            ai_agent_terminal_box = getattr(self, "ai_agent_terminal_box", None)
            if (
                session_is_agent(session_kind=session.kind)
                and ai_agent_terminal_box is not None
                and session.page in ai_agent_terminal_box.get_children()
            ):
                ai_agent_terminal_box.remove(session.page)
                self._clear_ai_agent_terminal_page()
        self.terminal_sessions.pop(session.session_id, None)
        if self.last_active_terminal_by_task.get(session.task_path) == session.session_id:
            self.last_active_terminal_by_task.pop(session.task_path, None)
        session.permission_pending = False
        session.permission_signature = None
        session.ignored_permission_signature = None
        session.busy = False
        session.exited = True
        if session.run_id is not None:
            clear_task_active_agent_run(
                self._task_for_path(session.task_path),
                run_id=session.run_id,
                agent=session.kind,
            )
        session.page.destroy()
        if ensure_default and self.selected_task is not None and self.selected_task.path == task.path:
            self._ensure_default_console_for_selected_task()
        self._update_codex_button_state()
        return True

    def _close_all_terminal_sessions(self) -> None:
        for session in list(self.terminal_sessions.values()):
            self._disconnect_terminal_callbacks(session.terminal)
            self._close_console_session(session, confirm=False, ensure_default=False)

    def _disconnect_terminal_callbacks(self, terminal: Vte.Terminal) -> None:
        disconnect = getattr(terminal, "disconnect_by_func", None)
        if disconnect is None:
            return
        for callback in (
            self._on_terminal_button_press,
            self._on_terminal_popup_menu,
            self._on_terminal_key_press,
            self._on_terminal_contents_changed,
            self._on_terminal_child_exited,
        ):
            try:
                disconnect(callback)
            except (TypeError, ValueError, RuntimeError):
                pass

    def _update_codex_button_state(self) -> None:
        task = self.selected_task
        running = task is not None and self._running_agent_session(task) is not None
        context = self.run_ai_agent_button.get_style_context()
        if running:
            context.add_class("codex-running")
        else:
            context.remove_class("codex-running")
        self._update_ai_agent_button_label()
        self._refresh_task_row_styles()

    def _update_ai_agent_button_label(self) -> None:
        task = self.selected_task
        running_agent = None
        agent = self._selected_agent()
        if task is not None:
            current = self._running_agent_session(task)
            running_agent = current.kind if current is not None else None
        state = ai_agent_launch_state_for_selection(
            task,
            self.workspace,
            agent,
            running_agent=running_agent,
        )
        self.run_ai_agent_button.set_label(self._tr(state.label_key))
        self.reset_ai_agent_button.set_sensitive(state.reset_enabled)

    def _task_has_resumable_agent_session(self, task: TaskSummary) -> bool:
        return bool(self._task_agent_session_markers(task))

    def _task_agent_session_markers(self, task: TaskSummary) -> tuple[str, ...]:
        cache = getattr(self, "task_agent_session_marker_cache", None)
        if cache is None:
            cache = {}
            self.task_agent_session_marker_cache = cache
        if task.path not in cache:
            cache[task.path] = task_agent_session_markers(task, self.workspace)
        return cache[task.path]

    def _invalidate_task_session_marker_cache(self, task: TaskSummary | None = None) -> None:
        cache = getattr(self, "task_agent_session_marker_cache", None)
        if cache is None:
            return
        if task is None:
            cache.clear()
            return
        cache.pop(task.path, None)

    def _task_running_agent_kinds(self, task: TaskSummary) -> tuple[str, ...]:
        local_agents = tuple(
            session.kind
            for session in self._current_task_terminal_sessions(task)
            if session_is_running_agent(session_kind=session.kind, exited=session.exited)
        )
        if local_agents:
            return local_agents
        return ()

    def _task_agent_status(self, task: TaskSummary) -> str:
        running_agents = self._task_running_agent_kinds(task)
        has_busy_agent = any(
            session.busy
            for session in self._current_task_terminal_sessions(task)
            if session_is_running_agent(session_kind=session.kind, exited=session.exited)
        )
        return task_agent_status_text(
            task,
            self.workspace,
            permission_pending=self._task_has_pending_agent_permission(task),
            running_agents=running_agents,
            external_active=self._task_is_external_active(task),
            spinner_frame=AGENT_RUNNING_SPINNER_FRAMES[self._agent_spinner_index] if has_busy_agent else "",
            session_markers=self._task_agent_session_markers(task),
        )

    def _set_agent_session_busy(self, session: TerminalSession, busy: bool) -> None:
        if not session_is_agent(session_kind=session.kind) or session.exited:
            return
        if session.busy == busy:
            return
        session.busy = busy
        self._refresh_task_row_styles()

    def _schedule_agent_idle_after_output(self, session: TerminalSession) -> None:
        if not session_is_agent(session_kind=session.kind) or session.exited or session.permission_pending:
            return
        session.output_generation += 1
        generation = session.output_generation
        GLib.timeout_add(
            AGENT_BUSY_IDLE_DELAY_MS,
            self._mark_agent_idle_if_output_quiet,
            session.session_id,
            generation,
        )

    def _mark_agent_idle_if_output_quiet(self, session_id: int, expected_generation: int) -> bool:
        session = self.terminal_sessions.get(session_id)
        if session is None or session.output_generation != expected_generation:
            return False
        if session.exited or session.permission_pending:
            return False
        self._set_agent_session_busy(session, False)
        return False

    def _handle_agent_restore_failed(self, session: TerminalSession) -> None:
        task = self._task_for_path(session.task_path)
        clear_task_agent_session(task, session.kind)
        self._invalidate_task_session_marker_cache(task)
        self._set_status_message(
            self._tr("restore_failed_status").format(
                agent=agent_label(session.kind),
                task=task.name,
            )
        )
        self._close_console_session(session, confirm=False, ensure_default=False)
        self._update_codex_button_state()
        self._refresh_task_row_styles()

    def _refresh_task_row_styles(self) -> None:
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            task = self.task_store[row_iter][2]
            has_agent = any(
                session_marks_task_running_agent(
                    session_kind=session.kind,
                    session_task_path=session.task_path,
                    exited=session.exited,
                    task_path=task.path,
                )
                for session in self.terminal_sessions.values()
            )
            has_session = self._task_has_resumable_agent_session(task)
            has_external_agent = self._task_is_external_active(task)
            background, background_set, foreground, foreground_set, weight, weight_set = _task_row_style(
                has_agent,
                has_session,
                has_external_agent,
                self.theme,
            )
            self.task_store.set(
                row_iter,
                [0, 1, 3, 4, 5, 6, 7, 8],
                [
                    str(self._task_agent_status(task)),
                    str(self._task_label(task)),
                    str(background),
                    bool(background_set),
                    str(foreground),
                    bool(foreground_set),
                    int(weight),
                    bool(weight_set),
                ],
            )
            row_iter = self.task_store.iter_next(row_iter)
        self._ensure_selected_task_is_selectable()

    def _task_is_external_active(self, task: TaskSummary) -> bool:
        return task_has_external_active_agent_run(task, self._local_agent_run_ids())

    def _ensure_selected_task_is_selectable(self) -> None:
        if self.selected_task is not None and self._task_is_external_active(self.selected_task):
            self._set_task_selection(self._selectable_task_iter(None))

    def _local_agent_run_ids(self) -> set[str]:
        return {
            session.run_id
            for session in getattr(self, "terminal_sessions", {}).values()
            if session.run_id is not None
        }

    def _animate_agent_status(self) -> bool:
        if self._closing:
            return False
        self._agent_spinner_index = (self._agent_spinner_index + 1) % len(AGENT_RUNNING_SPINNER_FRAMES)
        if self._running_agent_sessions():
            self._refresh_task_row_styles()
        return True

    def _actions_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.actions_page

    def _artifacts_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.artifacts_page

    def _ensure_default_console_for_selected_task(self) -> None:
        task = self.selected_task
        if task is None or self._current_task_terminal_sessions(task):
            return
        self.new_console(task=task)

    def _active_shell_for_task(self, task: TaskSummary) -> TerminalSession | None:
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return None
        page = self.console_notebook.get_nth_page(page_num)
        for session in self._current_task_terminal_sessions(task):
            if session.page is page and session.kind == "shell":
                return session
        return None

    def _first_terminal_for_task(self, task: TaskSummary) -> TerminalSession | None:
        for session in self._current_task_terminal_sessions(task):
            if session.kind == "shell":
                return session
        return None

    def _task_for_path(self, task_path: Path) -> TaskSummary:
        return task_for_path(self.tasks, task_path)

    def _on_terminal_button_press(self, terminal: Vte.Terminal, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        self._terminal_context_menu(terminal).popup_at_pointer(event)
        return True

    def _on_terminal_popup_menu(self, terminal: Vte.Terminal) -> bool:
        self._terminal_context_menu(terminal).popup_at_widget(
            terminal,
            Gdk.Gravity.SOUTH_WEST,
            Gdk.Gravity.NORTH_WEST,
            None,
        )
        return True

    def _on_terminal_key_press(self, terminal: Vte.Terminal, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_F1:
            self.open_agent_status_manual()
            return True
        session = self._session_for_terminal(terminal)
        submitted_input = event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}
        shortcut = _terminal_clipboard_shortcut(
            event.keyval,
            int(event.state),
            getattr(event, "hardware_keycode", None),
        )
        if shortcut == "copy":
            _copy_terminal_selection(terminal)
            return True
        if shortcut == "paste":
            if session is not None and session_is_agent(session_kind=session.kind):
                if session_should_clear_pending_permission(
                    session_kind=session.kind,
                    permission_pending=session.permission_pending,
                ):
                    session.ignored_permission_signature = session.permission_signature
                    session.permission_signature = None
                    session.permission_pending = False
                    self._refresh_task_row_styles()
                self._set_agent_session_busy(session, True)
            terminal.paste_clipboard()
            return True
        if (
            session is not None
            and session_is_agent(session_kind=session.kind)
            and submitted_input
        ):
            if session_should_clear_pending_permission(
                session_kind=session.kind,
                permission_pending=session.permission_pending,
            ):
                session.ignored_permission_signature = session.permission_signature
                session.permission_signature = None
                session.permission_pending = False
                self._refresh_task_row_styles()
            self._set_agent_session_busy(session, True)
        return False

    def _on_terminal_contents_changed(self, terminal: Vte.Terminal) -> None:
        session = self._session_for_terminal(terminal)
        if session is None or not session_is_agent(session_kind=session.kind):
            return
        tail = _terminal_text_tail(terminal)
        analysis = analyze_agent_output(tail)
        if (
            session.ignored_permission_signature is not None
            and analysis.permission_signature != session.ignored_permission_signature
        ):
            session.ignored_permission_signature = None
        update = agent_output_state_update(
            tail,
            exited=session.exited,
            permission_pending=session.permission_pending,
        )
        if update.missing_session:
            self._handle_agent_restore_failed(session)
            return
        if update.permission_requested:
            if analysis.permission_signature != session.ignored_permission_signature:
                session.permission_signature = analysis.permission_signature
                session.permission_pending = update.permission_pending
                session.busy = False
                self._refresh_task_row_styles()
            else:
                self._schedule_agent_idle_after_output(session)
            return
        self._schedule_agent_idle_after_output(session)

    def _terminal_context_menu(self, terminal: Vte.Terminal) -> Gtk.Menu:
        menu = Gtk.Menu()
        copy_item = Gtk.MenuItem(label="Copy")
        paste_item = Gtk.MenuItem(label="Paste")
        select_all_item = Gtk.MenuItem(label="Select all")
        close_item = Gtk.MenuItem(label=self._tr("close"))
        copy_item.set_sensitive(True)
        copy_item.connect("activate", lambda *_: _copy_terminal_selection(terminal))
        paste_item.connect("activate", lambda *_: terminal.paste_clipboard())
        select_all_item.connect("activate", lambda *_: terminal.select_all())
        session = self._session_for_terminal(terminal)
        close_item.set_sensitive(session is not None)
        close_item.connect("activate", lambda *_: self._close_console_session(session) if session is not None else None)
        menu.append(copy_item)
        menu.append(paste_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(select_all_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(close_item)
        menu.show_all()
        return menu

    def _session_for_terminal(self, terminal: Vte.Terminal) -> TerminalSession | None:
        for session in self.terminal_sessions.values():
            if session.terminal is terminal:
                return session
        return None

    def _session_for_page(self, page: Gtk.Widget) -> TerminalSession | None:
        ai_agent_page = getattr(self, "ai_agent_page", None)
        if ai_agent_page is not None and page is ai_agent_page:
            task = self.selected_task
            if task is None:
                return None
            ai_agent_terminal_box = getattr(self, "ai_agent_terminal_box", None)
            children = ai_agent_terminal_box.get_children() if ai_agent_terminal_box is not None else []
            for session in self._current_task_terminal_sessions(task):
                if session_is_agent(session_kind=session.kind) and session.page in children:
                    return session
            return None
        for session in self.terminal_sessions.values():
            if session.page is page:
                return session
        return None

    def _task_has_pending_agent_permission(self, task: TaskSummary) -> bool:
        return any(
            session_marks_task_pending_permission(
                session_kind=session.kind,
                session_task_path=session.task_path,
                permission_pending=session.permission_pending,
                exited=session.exited,
                task_path=task.path,
            )
            for session in self.terminal_sessions.values()
        )

    def _task_label(self, task: TaskSummary) -> str:
        return task.name

    def _require_task(self, show_dialog: bool = True) -> TaskSummary | None:
        if self.selected_task is not None and not self._task_is_external_active(self.selected_task):
            return self.selected_task
        if show_dialog:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.NONE,
                text=self._tr("select_task_first"),
            )
            dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
            dialog.run()
            dialog.destroy()
        return None

    def _confirm_close_console(self) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("confirm_close_console_title"),
        )
        dialog.format_secondary_text(self._tr("confirm_close_console_body"))
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("close"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _set_text(self, view: Gtk.TextView, text: str) -> None:
        view.get_buffer().set_text(text)

    def _set_markdown(self, view: Gtk.TextView, text: str) -> None:
        buffer = view.get_buffer()
        self._ensure_markdown_tags(buffer)
        buffer.set_text("")
        for chunk in render_markdown_chunks(text):
            end = buffer.get_end_iter()
            buffer.insert_with_tags_by_name(end, chunk.text, chunk.tag)

    def _ensure_markdown_tags(self, buffer: Gtk.TextBuffer) -> None:
        tag_table = buffer.get_tag_table()
        if tag_table.lookup("paragraph") is not None:
            _update_text_tag(tag_table.lookup("paragraph"), font=f"Sans {self.text_font_size}")
            _update_text_tag(tag_table.lookup("h1"), font=f"Sans Bold {self.text_font_size + 6}")
            _update_text_tag(tag_table.lookup("h2"), font=f"Sans Bold {self.text_font_size + 4}")
            _update_text_tag(tag_table.lookup("h3"), font=f"Sans Bold {self.text_font_size + 2}")
            _update_text_tag(tag_table.lookup("list"), font=f"Sans {self.text_font_size}")
            _update_text_tag(tag_table.lookup("code"), font=f"Monospace {self.text_font_size}")
            _update_text_tag(tag_table.lookup("table"), font=f"Monospace {self.text_font_size}")
            return
        buffer.create_tag("paragraph", font=f"Sans {self.text_font_size}")
        buffer.create_tag("h1", font=f"Sans Bold {self.text_font_size + 6}", pixels_above_lines=8)
        buffer.create_tag("h2", font=f"Sans Bold {self.text_font_size + 4}", pixels_above_lines=6)
        buffer.create_tag("h3", font=f"Sans Bold {self.text_font_size + 2}", pixels_above_lines=4)
        buffer.create_tag(
            "list",
            font=f"Sans {self.text_font_size}",
            left_margin=24,
            indent=-12,
        )
        buffer.create_tag(
            "code",
            font=f"Monospace {self.text_font_size}",
            left_margin=12,
            right_margin=12,
        )
        buffer.create_tag(
            "table",
            font=f"Monospace {self.text_font_size}",
            left_margin=12,
            right_margin=12,
        )

    def _button(self, label_key: str, callback: object) -> Gtk.Button:
        button = _button(self._tr(label_key), callback)
        self.label_widgets[label_key] = button
        return button

    def _apply_labels(self) -> None:
        title = f"{self._tr('window_title')} - {self.workspace}"
        self.window.set_title(title)
        self.header_bar.set_title(title)
        for key, widget in self.label_widgets.items():
            if isinstance(widget, Gtk.Button):
                widget.set_label(self._tr(key))
        self.task_status_header.set_text(self._tr("task_agent_status_column"))
        self.task_column.set_title(self._tr("task"))
        self.artifact_name_column.set_title(self._tr("artifacts"))
        self.artifact_updated_column.set_title(self._tr("updated"))
        self._update_artifact_sort_indicators()
        self.details_tab_label.set_text(self._tr("details"))
        self.artifacts_tab_label.set_text(self._tr("artifacts"))
        self.actions_tab_label.set_text(self._tr("actions"))
        if self.ai_agent_tab_label is not None:
            self.ai_agent_tab_label.set_text(self._s("console.ai_agent"))
        if self.selected_task is not None and self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)
        self._update_ai_agent_button_label()

    def _tr(self, key: str) -> str:
        return TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    def _s(self, key: str, **kwargs: object) -> str:
        return _ui_string(self.language, key, **kwargs)

    def _on_main_pane_button_press(self, _pane: Gtk.Paned, event: Gdk.EventButton) -> bool:
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and _is_pane_separator_event(self.main_pane, event):
            self._set_main_default_split()
            return True
        return False

    def _on_details_pane_button_press(self, _pane: Gtk.Paned, event: Gdk.EventButton) -> bool:
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and _is_pane_separator_event(self.details_pane, event):
            self._set_details_default_split()
            return True
        return False

    def _set_main_default_split(self) -> bool:
        width = self.main_pane.get_allocated_width()
        self.main_pane.set_position(max(360, width // 4))
        return False

    def _set_details_default_split(self) -> bool:
        height = self.details_pane.get_allocated_height()
        self.details_pane.set_position(max(160, height // 4))
        return False

    def _apply_window_geometry(self) -> None:
        parts = self.window_geometry.replace("-", "+-").split("+")
        size = parts[0]
        if "x" not in size:
            self.window.set_default_size(1180, 760)
            return
        width, height = size.split("x", 1)
        try:
            self.last_window_width = int(width)
            self.last_window_height = int(height)
            self.window.set_default_size(self.last_window_width, self.last_window_height)
            if len(parts) >= 3:
                self.last_window_x = int(parts[1])
                self.last_window_y = int(parts[2])
                self.window.move(self.last_window_x, self.last_window_y)
        except ValueError:
            self.window.set_default_size(1180, 760)

    def _on_window_configure(self, _window: Gtk.Window, event: Gdk.EventConfigure) -> bool:
        if event.width > 1 and event.height > 1:
            self.last_window_width = event.width
            self.last_window_height = event.height
            self.last_window_x = event.x
            self.last_window_y = event.y
        return False

    def _on_window_key_press(self, _window: Gtk.Window, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_F1:
            self.open_agent_status_manual()
            return True
        return False

    def _apply_css(self) -> None:
        colors = _theme_colors(self.theme)
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", self.theme == "dark")
        css = f"""
        * {{ font-size: {self.button_font_size}pt; }}
        window, headerbar, box, paned, scrolledwindow, notebook {{
            background: {colors['background']};
            color: {colors['foreground']};
        }}
        headerbar {{
            background: {colors['titlebar_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
        }}
        button, combobox, combobox box, entry {{
            background: {colors['control_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
        }}
        button:hover {{
            background: {colors['control_hover_background']};
        }}
        .actions-panel frame {{
            padding: 1px;
        }}
        .actions-panel button {{
            padding: 1px 6px;
            min-height: 0;
            min-width: 0;
        }}
        .actions-panel flowboxchild {{
            padding: 0;
            margin: 0;
        }}
        button.task-action-selected {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
            box-shadow: 0 0 5px {colors['codex_running_glow']};
        }}
        button.task-action-run-armed {{
            background: #8a6d1f;
            color: #fff4cf;
            border-color: #f2c94c;
            box-shadow: 0 0 6px #f2c94c;
        }}
        button.task-action-run-fired {{
            background: #1f7a3a;
            color: #eafff0;
            border-color: #35d06f;
            box-shadow: 0 0 7px #35d06f;
        }}
        button.task-action-dragging,
        .task-action-dragging button {{
            background: #64501d;
            border-color: #f2c94c;
            box-shadow: none;
        }}
        button.task-action-drag-icon {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: #f2c94c;
            box-shadow: 0 0 10px #f2c94c;
            padding: 3px 10px;
        }}
        button.codex-running {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
            box-shadow: 0 0 8px {colors['codex_running_glow']};
        }}
        notebook tab {{
            background: {colors['tab_background']};
            color: {colors['muted_foreground']};
            padding: 6px 10px;
        }}
        notebook tab:checked {{
            background: {colors['tab_selected_background']};
            color: {colors['tab_selected_foreground']};
        }}
        notebook stack {{
            background: {colors['terminal_background']};
            color: {colors['foreground']};
        }}
        paned > separator {{
            background: {colors['separator']};
            min-width: 3px;
            min-height: 3px;
        }}
        scrolledwindow, notebook {{
            border: 1px solid {colors['border']};
        }}
        treeview {{
            background: {colors['text_background']};
            color: {colors['foreground']};
        }}
        treeview:selected {{
            background: {colors['selection_background']};
            color: {colors['selection_foreground']};
        }}
        menu, menuitem {{
            background: {colors['menu_background']};
            color: {colors['foreground']};
        }}
        menuitem:hover {{
            background: {colors['selection_background']};
            color: {colors['selection_foreground']};
        }}
        textview text {{
            background: {colors['text_background']};
            color: {colors['foreground']};
            font-family: monospace;
            font-size: {self.text_font_size}pt;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _apply_terminal_theme(self, terminal: Vte.Terminal) -> None:
        colors = _theme_colors(self.theme)
        terminal.set_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        terminal.set_colors(
            _rgba(colors["foreground"]),
            _rgba(colors["terminal_background"]),
            [_rgba(color) for color in _terminal_palette(self.theme)],
        )

    def _apply_runtime_style(self) -> None:
        self._apply_css()
        self.description_view.modify_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        self.context_view.modify_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        if self.selected_task is not None:
            self._set_markdown(self.description_view, read_task_file(self.selected_task, "TASK_DESCRIPTION.md"))
            self._set_markdown(self.context_view, read_task_file(self.selected_task, "TASK_CONTEXT.md"))
        for session in self.terminal_sessions.values():
            self._apply_terminal_theme(session.terminal)
        self._refresh_task_row_styles()

    def _on_window_delete_event(self, *_args: object) -> bool:
        return not self._confirm_close_with_running_agents()

    def close(self, *_args: object) -> None:
        if self._closing:
            return
        self._closing = True
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
        self._close_all_terminal_sessions()
        self._save_settings()
        Gtk.main_quit()

    def _save_settings(self) -> None:
        save_agent_workspace_settings(
            {
                "text_font_size": self.text_font_size,
                "button_font_size": self.button_font_size,
                "theme": self.theme,
                "language": self.language,
                "default_agent": self.default_agent,
                "default_codex_model": self.default_codex_model,
                "default_codex_reasoning": self.default_codex_reasoning,
                "default_claude_model": self.default_claude_model,
                "default_claude_effort": self.default_claude_effort,
                "geometry": (
                    f"{self.last_window_width}x{self.last_window_height}"
                    f"+{self.last_window_x}+{self.last_window_y}"
                ),
            }
        )


def _button(label: str, callback: object) -> Gtk.Button:
    button = Gtk.Button(label=label)
    button.connect("clicked", callback)
    return button


def _compact_button(label: str, callback: object | None, *, max_width_chars: int = 22) -> Gtk.Button:
    button = Gtk.Button()
    text = Gtk.Label(label=label)
    text.set_ellipsize(Pango.EllipsizeMode.END)
    text.set_max_width_chars(max_width_chars)
    text.set_width_chars(min(max_width_chars, max(4, min(len(label), max_width_chars))))
    button.add(text)
    button.set_tooltip_text(label)
    button.set_size_request(-1, 26)
    if callback is not None:
        button.connect("clicked", callback)
    return button


def _flow_box(
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


def _flow_box_add(box: Gtk.FlowBox, widget: Gtk.Widget) -> None:
    box.add(widget)


def _remove_style_class_recursive(widget: Gtk.Widget, class_name: str) -> None:
    widget.get_style_context().remove_class(class_name)
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            _remove_style_class_recursive(child, class_name)


def _set_widget_opacity_recursive(widget: Gtk.Widget, opacity: float) -> None:
    widget.set_opacity(opacity)
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            _set_widget_opacity_recursive(child, opacity)


def _task_action_drag_icon(label: str) -> Gtk.Button:
    button = Gtk.Button(label=label)
    button.set_relief(Gtk.ReliefStyle.NORMAL)
    button.set_focus_on_click(False)
    button.get_style_context().add_class("task-action-drag-icon")
    button.set_opacity(0.9)
    button.show_all()
    return button


def _is_pane_separator_event(pane: Gtk.Paned, event: Gdk.EventButton, tolerance: int = 8) -> bool:
    position = pane.get_position()
    if pane.get_orientation() == Gtk.Orientation.HORIZONTAL:
        return abs(event.x - position) <= tolerance
    return abs(event.y - position) <= tolerance


def _notebook_event_in_empty_tab_area(notebook: Gtk.Notebook, event: Gdk.EventButton) -> bool:
    rects = _notebook_tab_rects(notebook)
    if not rects:
        return False
    if any(_rect_contains(rect, event.x, event.y) for rect in rects):
        return False
    allocation = notebook.get_allocation()
    tab_pos = notebook.get_tab_pos()
    if tab_pos in {Gtk.PositionType.TOP, Gtk.PositionType.BOTTOM}:
        min_y = min(rect[1] for rect in rects)
        max_y = max(rect[1] + rect[3] for rect in rects)
        return 0 <= event.x < allocation.width and min_y <= event.y < max_y
    min_x = min(rect[0] for rect in rects)
    max_x = max(rect[0] + rect[2] for rect in rects)
    return min_x <= event.x < max_x and 0 <= event.y < allocation.height


def _notebook_tab_rects(notebook: Gtk.Notebook) -> list[tuple[float, float, float, float]]:
    rects = []
    for page_index in range(notebook.get_n_pages()):
        page = notebook.get_nth_page(page_index)
        tab = notebook.get_tab_label(page)
        if tab is None or not tab.get_visible():
            continue
        translated = tab.translate_coordinates(notebook, 0, 0)
        if translated is None:
            continue
        allocation = tab.get_allocation()
        rects.append((translated[0], translated[1], allocation.width, allocation.height))
    return rects


def _rect_contains(rect: tuple[float, float, float, float], x: float, y: float) -> bool:
    rect_x, rect_y, width, height = rect
    return rect_x <= x < rect_x + width and rect_y <= y < rect_y + height


def _task_row_style(
    has_agent: bool,
    has_session: bool,
    has_external_agent: bool,
    theme: str,
) -> tuple[str, bool, str, bool, int, bool]:
    colors = _theme_colors(theme)
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


def _update_text_tag(tag: Gtk.TextTag | None, **properties: object) -> None:
    if tag is None:
        return
    for name, value in properties.items():
        tag.set_property(name.replace("_", "-"), value)


def _text_view(font_size: int, editable: bool) -> Gtk.TextView:
    view = Gtk.TextView()
    view.set_editable(editable)
    view.set_cursor_visible(editable)
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.modify_font(Pango.FontDescription(f"Monospace {font_size}"))
    return view


def _text_buffer_text(buffer: Gtk.TextBuffer) -> str:
    start = buffer.get_start_iter()
    end = buffer.get_end_iter()
    return buffer.get_text(start, end, True)


def _scrolled(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
    scrolled = Gtk.ScrolledWindow()
    scrolled.add(widget)
    return scrolled


def ai_agent_task_context_message(task: TaskSummary, workspace: Path, language: str = "en") -> str:
    language_instruction = CODEX_LANGUAGE_INSTRUCTIONS.get(language, CODEX_LANGUAGE_INSTRUCTIONS["en"])
    return ai_agent_task_context_prompt(task, workspace, language_instruction)


def codex_task_context_message(task: TaskSummary, workspace: Path, language: str = "en") -> str:
    return ai_agent_task_context_message(task, workspace, language)


def ai_agent_console_command(
    workspace: Path,
    task: TaskSummary,
    agent: str,
    language: str = "en",
    *,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
) -> list[str]:
    return build_ai_agent_console_command(
        workspace,
        ai_agent_task_context_message(task, workspace, language),
        agent,
        codex_executable=_codex_executable(),
        claude_executable=_claude_executable(),
        resume=resume,
        resume_session_id=resume_session_id,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def codex_console_command(
    workspace: Path,
    task: TaskSummary,
    language: str = "en",
    *,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
) -> list[str]:
    return build_ai_agent_console_command(
        workspace,
        ai_agent_task_context_message(task, workspace, language),
        "codex",
        codex_executable=_codex_executable(),
        claude_executable=_claude_executable(),
        resume=resume,
        resume_session_id=resume_session_id,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def _set_combo_text_choices(combo: Gtk.ComboBoxText, choices: tuple[str, ...], current: str) -> None:
    active_index = 0
    for index, choice in enumerate(choices):
        combo.append_text(choice)
        if choice == current:
            active_index = index
    combo.set_active(active_index)


def _rgba(color: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    rgba.parse(color)
    return rgba


def _agent_workspace_icon_path() -> Path:
    return Path(__file__).with_name("assets") / "agent-workspace.svg"


def _agent_workspace_runtime_icon_path() -> Path:
    installed = Path.home() / ".local/share/icons/hicolor/256x256/apps/agent-workspace.png"
    if installed.is_file():
        return installed
    return _agent_workspace_icon_path()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the local workspace task dashboard.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root. Default: current directory.",
    )
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    install_agent_workspace_exception_logger(workspace, "gtk")
    workspace_lock = acquire_agent_workspace_lock(workspace)
    if workspace_lock is None:
        print(f"Agent Workspace is already running for {workspace.resolve()}", file=sys.stderr)
        return 0

    gui = WorkspaceGtkGui(workspace)
    gui.window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
