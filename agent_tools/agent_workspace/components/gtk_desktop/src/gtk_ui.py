from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import re
import shutil
import subprocess
import sys
import threading

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

from agent_tools.tools.task_context import DictionaryPreview
from agent_tools.tools.task_context import STATUSES as TASK_CONTEXT_STATUSES
from agent_tools.tools.task_context import TaskDictionaryPolicy
from agent_tools.tools.task_context import TaskContextSlot
from agent_tools.tools.task_context import filter_entries as _filter_task_context_entries
from agent_tools.tools.task_context import load_entries as _load_task_context_entries
from agent_tools.tools.task_context import preview_dictionary_compile
from agent_tools.tools.task_context import set_slot as _set_task_context_slot
from agent_tools.tools.front_desk_bell import reset_workspace_pending_iterations

from ...artifacts.api import ArtifactEntry
from ...artifacts.api import artifact_context_action as _artifact_context_action
from ...artifacts.api import artifact_delete_paths as _artifact_delete_paths
from ...artifacts.api import artifact_group as _artifact_group
from ...artifacts.api import artifact_group_sort_key as _artifact_group_sort_key
from ...artifacts.api import artifact_relative_label as _artifact_relative_label
from ...artifacts.api import artifact_selectable_path as _artifact_selectable_path
from ...artifacts.api import artifact_updated_label as _artifact_updated_label
from ...artifacts.api import artifact_updated_timestamp as _artifact_updated_timestamp
from ...artifacts.api import files_under as _files_under
from ...artifacts.api import task_artifact_entries as _task_artifact_entries
from ...artifacts.api import task_artifact_files as _task_artifact_files
from ...agent_runtime.api import ai_agent_environment
from ...agent_runtime.api import ai_agent_launch_state_for_selection
from ...agent_runtime.api import ai_agent_switch_decision
from ...agent_runtime.api import ai_agent_task_context_prompt
from ...agent_runtime.api import build_ai_agent_console_command
from ...agent_runtime.api import prepare_ai_agent_launch_command
from ...commands.api import task_action_shell_command
from ...commands.api import task_check_shell_command
from ...task_actions.api import add_task_shortcut as _add_task_shortcut
from ...task_actions.api import bindings_for_action_run
from ...task_actions.api import delete_parameter_set_value as _delete_parameter_set_value
from ...task_actions.api import delete_task_shortcut as _delete_task_shortcut
from ...task_actions.api import field_type_enum_values as _field_type_enum_values
from ...task_actions.api import json_list_entry_index as _json_list_entry_index
from ...task_actions.api import move_action_parameter_entry as _move_action_parameter_entry
from ...task_actions.api import move_id_before as _move_id_before
from ...task_actions.api import move_id_relative as _move_id_relative
from ...task_actions.api import move_json_list_entry as _move_json_list_entry
from ...task_actions.api import move_json_list_entry_before as _move_json_list_entry_before
from ...task_actions.api import move_json_mapping_entry as _move_json_mapping_entry
from ...task_actions.api import parameter_button_label
from ...task_actions.api import parameter_dialog_field_names as _parameter_dialog_field_names
from ...task_actions.api import parameter_field_type as _parameter_field_type
from ...task_actions.api import parameter_value_id_from_name as _parameter_value_id_from_name
from ...task_actions.api import parameter_values
from ...task_actions.api import reorder_action_parameter_entries as _reorder_action_parameter_entries
from ...task_actions.api import reorder_json_list_by_ids as _reorder_json_list_by_ids
from ...task_actions.api import reorder_json_list_subset_by_ids as _reorder_json_list_subset_by_ids
from ...task_actions.api import reorder_json_mapping_by_ids as _reorder_json_mapping_by_ids
from ...task_actions.api import reorder_task_action_data as _reorder_task_action_data
from ...task_actions.api import selected_parameter_value
from ...task_actions.api import set_task_action_drag_selection as _set_task_action_drag_selection
from ...task_actions.api import shortcut_id_from_label as _shortcut_id_from_label
from ...task_actions.api import shortcuts_for_action
from ...task_actions.api import task_action_code_path
from ...task_actions.api import task_action_drag_selection_id as _task_action_drag_selection_id
from ...task_actions.api import task_action_menu_state
from ...task_actions.api import task_parameter_menu_state
from ...task_actions.api import task_reorder_order_for_drag_edges as _task_reorder_order_for_drag_edges
from ...task_actions.api import task_shortcut_menu_state
from ...task_actions.api import upsert_parameter_set_value as _upsert_parameter_set_value
from ...task_actions.api import TASK_ACTIONS_FILE
from ...task_actions.api import TaskAction
from ...task_actions.api import TaskActionParameter
from ...task_actions.api import TaskActionsConfig
from ...task_actions.api import bind_task_action_parameters
from ...task_actions.api import load_task_actions
from ...task_actions.api import load_task_actions_config
from ...task_actions.api import load_task_actions_data
from ...task_actions.api import save_task_actions_data
from ...agent_status.api import AGENT_RUNNING_SPINNER_FRAMES
from ...agent_status.api import agent_output_state_update
from ...agent_status.api import agent_status_tooltip_text
from ...agent_status.api import analyze_agent_output
from ...agent_status.api import session_is_agent
from ...agent_status.api import session_is_running_agent
from ...agent_status.api import session_marks_task_pending_permission
from ...agent_status.api import session_marks_task_running_agent
from ...agent_status.api import session_should_clear_pending_permission
from ...agent_status.api import task_agent_status_text
from ...agent_status.api import task_for_path
from ...settings.api import AgentModelSettings
from ...task_sessions.api import TaskSessionDiscoveryState
from ...task_catalog.api import TaskSummary
from ...settings.api import AGENT_WORKSPACE_AGENTS
from ...settings.api import AGENT_WORKSPACE_LANGUAGES
from ...settings.api import AGENT_WORKSPACE_REASONING_EFFORTS
from ...settings.api import AGENT_WORKSPACE_THEMES
from ...localization.api import AGENT_STATUS_MANUAL_MENU_LABEL
from ...localization.api import AGENT_STATUS_MANUAL_TITLE
from ...process_runtime.api import acquire_agent_workspace_lock
from ...settings.api import agent_executable
from ...settings.api import agent_install_command
from ...settings.api import agent_label
from ...settings.api import ai_agent_model_settings
from ...settings.api import agent_workspace_runtime_settings
from ...process_runtime.api import install_agent_workspace_exception_logger
from ...task_sessions.api import clear_task_agent_session
from ...task_sessions.api import clear_task_active_agent_run
from ...settings.api import claude_model_choices_info
from ...settings.api import codex_model_choices_info
from ...task_catalog.api import discover_tasks
from ...task_sessions.api import load_task_agent
from ...settings.api import load_agent_workspace_settings
from ...process_runtime.api import log_agent_workspace_exception
from ...settings.api import model_choices_with_current
from ...task_sessions.api import new_agent_session_id
from ...settings.api import normalize_agent
from ...task_catalog.api import read_task_file
from ...task_sessions.api import reconcile_task_agent_run_session
from ...task_sessions.api import resolve_task_agent_sessions
from ...task_sessions.api import reset_task_agent_session
from ...settings.api import save_agent_workspace_settings
from ...task_sessions.api import save_task_active_agent_run
from ...task_sessions.api import save_task_agent
from ...task_sessions.api import save_task_agent_session
from ...task_sessions.api import task_agent_has_resumable_state
from ...task_sessions.api import task_agent_session_markers
from ...task_sessions.api import task_agent_selection_with_resumable_fallback
from ...task_sessions.api import task_has_external_active_agent_run
from ...task_context.api import load_task_context_slots as _load_task_context_slots
from ...task_context.api import render_task_context_slots as _render_task_context_slots
from ...task_context.api import task_goal_slot_markdown as _task_goal_slot_markdown
from ...markdown.api import render_markdown_chunks
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
from .gtk_task_style import task_row_style as _task_row_style
from .gtk_theme import theme_colors as _theme_colors
from .gtk_widgets import button as _button
from .gtk_widgets import compact_button as _compact_button
from .gtk_widgets import flow_box as _flow_box
from .gtk_widgets import flow_box_add as _flow_box_add
from .gtk_widgets import remove_style_class_recursive as _remove_style_class_recursive
from .gtk_widgets import set_widget_opacity_recursive as _set_widget_opacity_recursive
from .gtk_widgets import task_action_drag_icon as _task_action_drag_icon
from ...localization.api import CODEX_LANGUAGE_INSTRUCTIONS
from ...localization.api import TRANSLATIONS
from ...localization.api import ui_string as _ui_string
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
TASK_CONTEXT_DEFAULT_STATUS_FILTER = ("active",)


def _codex_executable() -> str:
    return agent_executable("codex") or "codex"


def _claude_executable() -> str:
    return agent_executable("claude") or "claude"


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
        self.task_action_play_buttons: dict[str, Gtk.Button] = {}
        self.task_action_item_widgets: dict[str, Gtk.Widget] = {}
        self.task_action_reflow_source_id: int | None = None
        self.global_task_parameter_box: Gtk.FlowBox | None = None
        self.task_action_errors: list[str] = []
        self.status_message = ""
        self.task_actions_signature: tuple[Path | None, int | None] = (None, None)
        self.task_actions_monitor: Gio.FileMonitor | None = None
        self.task_actions_monitor_path: Path | None = None
        self.artifact_sort_column = "name"
        self.artifact_sort_descending = False
        self.task_agent_session_marker_cache: dict[Path, tuple[str, ...]] = {}
        self.task_session_discovery = TaskSessionDiscoveryState()
        self.terminal_sessions: dict[int, TerminalSession] = {}
        self.last_active_terminal_by_task: dict[Path, int] = {}
        self.last_active_console_page_by_task: dict[Path, str] = {}
        self.next_terminal_id = 1
        self._refreshing_console_tabs = False
        self._updating_agent_selection = False
        self._updating_task_selection = False
        self._agent_spinner_index = 0
        self._closing = False
        self.active_main_page: Gtk.Widget | None = None

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
        self.inject_task_context_prompt = settings.inject_task_context_prompt
        self.task_dictionary_auto_discovery = settings.task_dictionary_auto_discovery
        self.task_dictionary_min_occurrences = settings.task_dictionary_min_occurrences
        self.task_dictionary_min_saving = settings.task_dictionary_min_saving
        self.task_dictionary_min_term_length = settings.task_dictionary_min_term_length
        self.task_dictionary_max_term_words = settings.task_dictionary_max_term_words
        self.task_dictionary_strip_articles = settings.task_dictionary_strip_articles
        self.task_dictionary_preview_text = settings.task_dictionary_preview_text
        self.window_geometry = settings.window_geometry
        self.main_split_ratio = settings.main_split_ratio
        self.details_split_ratio = settings.details_split_ratio
        self.actions_split_ratio = settings.actions_split_ratio
        self._updating_pane_positions = False
        self._pane_layout_ready = False
        self._initial_pane_layout_source_id: int | None = None
        self._pane_settings_save_source_id: int | None = None
        self.last_window_width = 1180
        self.last_window_height = 760
        self.last_window_x = 0
        self.last_window_y = 0
        self.label_widgets: dict[str, Gtk.Widget] = {}
        self.detail_editing: dict[Gtk.TextView, bool] = {}
        self.detail_original_text: dict[Gtk.TextView, str] = {}
        self.detail_filenames: dict[Gtk.TextView, str] = {}
        self.task_context_filter_since: str | None = None
        self.task_context_filter_until: str | None = None
        self.task_context_since_button: Gtk.Button | None = None
        self.task_context_until_button: Gtk.Button | None = None
        self.task_context_severity_checks: dict[str, Gtk.CheckButton] = {}
        self.task_context_status_checks: dict[str, Gtk.CheckButton] = {}
        self.task_context_label_checks: dict[str, Gtk.CheckButton] = {}
        self.task_context_filter_all_checks: dict[str, Gtk.CheckButton] = {}
        self.task_context_label_box: Gtk.Box | None = None
        self.task_context_date_popover: Gtk.Popover | None = None
        self._updating_task_context_checks = False
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
        self.window.connect("map-event", self._on_window_mapped)
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
        main.connect("notify::position", self._on_main_pane_position_changed)
        main.connect("size-allocate", self._on_main_pane_size_allocate)
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
        self.active_main_page = self.actions_page
        self.notebook.connect("switch-page", self._on_main_notebook_switch_page)

    def _add_details_tab(self) -> None:
        pane = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.details_page = pane
        self.details_pane = pane
        pane.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pane.connect("button-press-event", self._on_details_pane_button_press)
        pane.connect("notify::position", self._on_details_pane_position_changed)
        pane.connect("size-allocate", self._on_details_pane_size_allocate)
        self.description_view = _text_view(self.text_font_size, editable=False)
        self.context_view = _text_view(self.text_font_size, editable=False)
        self._register_detail_view(self.description_view, "goal")
        self.context_view.connect("button-release-event", self._on_context_view_button_release)
        pane.pack1(_scrolled(self.description_view), resize=True, shrink=False)
        context_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        context_box.set_border_width(4)
        context_box.pack_start(self._task_context_filter_bar(), False, False, 0)
        context_box.pack_start(_scrolled(self.context_view), True, True, 0)
        pane.pack2(context_box, resize=True, shrink=False)
        self.details_tab_label = Gtk.Label(label=self._tr("details"))
        self.notebook.append_page(pane, self.details_tab_label)

    def _task_context_filter_bar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.get_style_context().add_class("task-context-filter-bar")

        self.task_context_since_button = self._button("context_filter_since_any", self._choose_task_context_since)
        self.task_context_until_button = self._button("context_filter_until_any", self._choose_task_context_until)
        box.pack_start(self.task_context_since_button, False, False, 0)
        box.pack_start(self.task_context_until_button, False, False, 0)

        box.pack_start(
            self._task_context_check_menu(
                "severity",
                self._tr("context_filter_levels"),
                ("note", "low", "mid", "high", "critical"),
                self.task_context_severity_checks,
            ),
            False,
            False,
            0,
        )
        box.pack_start(
            self._task_context_check_menu(
                "status",
                self._tr("context_filter_statuses"),
                TASK_CONTEXT_STATUSES,
                self.task_context_status_checks,
            ),
            False,
            False,
            0,
        )
        label_button = Gtk.MenuButton(label=self._tr("context_filter_labels"))
        label_popover = Gtk.Popover()
        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        label_box.set_border_width(8)
        label_popover.add(label_box)
        label_button.set_popover(label_popover)
        self.task_context_label_box = label_box
        box.pack_start(label_button, False, False, 0)

        self.task_context_encoded_check = Gtk.CheckButton(label="Encoded")
        self.task_context_encoded_check.connect("toggled", self._on_task_context_filter_changed)
        box.pack_start(self.task_context_encoded_check, False, False, 0)
        box.pack_start(self._button("context_filter_clear", self._clear_task_context_filters), False, False, 0)
        self._update_task_context_date_buttons()
        return box

    def _task_context_check_menu(
        self,
        group: str,
        label: str,
        values: tuple[str, ...],
        target: dict[str, Gtk.CheckButton],
    ) -> Gtk.Widget:
        button = Gtk.MenuButton(label=label)
        popover = Gtk.Popover()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content.set_border_width(8)
        all_check = Gtk.CheckButton(label=self._tr("context_filter_select_all"))
        all_check.set_active(True)
        all_check.connect("toggled", self._on_task_context_all_toggled, group, target)
        self.task_context_filter_all_checks[group] = all_check
        content.pack_start(all_check, False, False, 0)
        for value in values:
            check = Gtk.CheckButton(label=value)
            check.set_active(value in self._task_context_default_group_values(group, values))
            check.connect("toggled", self._on_task_context_item_toggled, group, target)
            target[value] = check
            content.pack_start(check, False, False, 0)
        self._update_task_context_all_check(group, target)
        popover.add(content)
        content.show_all()
        button.set_popover(popover)
        return button

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
        self.actions_pane = actions_pane
        actions_pane.set_wide_handle(True)
        actions_pane.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        actions_pane.connect("button-press-event", self._on_actions_pane_button_press)
        actions_pane.connect("size-allocate", self._on_actions_pane_size_allocate)
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
        self.task_actions_box.connect("size-allocate", self._on_task_actions_box_size_allocate)
        self._connect_task_reorder_box(self.task_actions_box, "action")

        parameter_frame = Gtk.Frame(label=self._s("action.parameters"))
        controls_box.pack_start(parameter_frame, False, False, 0)
        parameter_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        parameter_content.set_border_width(2)
        parameter_frame.add(parameter_content)
        self.task_action_parameter_box = _flow_box()
        self.task_action_parameter_box.set_size_request(-1, 20)
        self.task_action_parameter_box.set_sort_func(self._task_parameter_flow_sort)
        self._connect_task_reorder_box(self.task_action_parameter_box, "parameter")
        parameter_content.pack_start(self.task_action_parameter_box, True, True, 0)

        shortcuts_frame = Gtk.Frame(label=self._s("action.shortcuts"))
        controls_box.pack_start(shortcuts_frame, False, False, 0)
        shortcuts_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        shortcuts_content.set_border_width(2)
        shortcuts_frame.add(shortcuts_content)
        self.task_shortcuts_box = _flow_box()
        self.task_shortcuts_box.set_size_request(-1, 20)
        self.task_shortcuts_box.set_sort_func(self._task_shortcut_flow_sort)
        self._connect_task_reorder_box(self.task_shortcuts_box, "shortcut")
        shortcuts_content.pack_start(self.task_shortcuts_box, True, True, 0)
        self.save_task_shortcut_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.save_task_shortcut_box.set_size_request(-1, 20)
        shortcuts_content.pack_end(self.save_task_shortcut_box, False, False, 0)

        global_parameter_frame = Gtk.Frame(label=self._s("action.global_parameters"))
        controls_box.pack_start(global_parameter_frame, False, False, 0)
        global_parameter_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        global_parameter_content.set_border_width(2)
        global_parameter_frame.add(global_parameter_content)
        self.global_task_parameter_box = _flow_box()
        self.global_task_parameter_box.set_size_request(-1, 20)
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
        self._on_actions_pane_position_changed(actions_pane, None)
        self._ensure_ai_agent_console_page()

    def _on_actions_pane_position_changed(self, pane: Gtk.Paned, _param: object | None) -> None:
        if self.actions_controls_box is None:
            return
        position = pane.get_position()
        opacity = max(0.0, min(1.0, position / 90.0))
        self.actions_controls_box.set_opacity(opacity)
        if self._pane_layout_ready and not self._updating_pane_positions:
            self.actions_split_ratio = _pane_position_ratio(pane)
            self._schedule_pane_settings_save()

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

    def _add_framed_action_group(self, parent: Gtk.Box, title: str, *, expand: bool) -> Gtk.Box:
        frame = Gtk.Frame(label=title)
        parent.pack_start(frame, expand, expand, 0)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content.set_border_width(2)
        frame.add(content)
        return content

    def refresh_tasks(self, *_args: object) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
        self._invalidate_task_session_marker_cache()
        self._start_task_session_discovery()
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
        if self._details_tab_active():
            self._refresh_selected_task_details(leave_edit=True)
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

    def _refresh_selected_task_details(self, *, leave_edit: bool = False) -> None:
        if self.selected_task is None:
            return
        editing_description = getattr(self, "detail_editing", {}).get(self.description_view, False)
        if leave_edit or not editing_description:
            if leave_edit:
                self._leave_detail_edit_mode(self.description_view)
            self._set_markdown(self.description_view, _task_goal_slot_markdown(self.selected_task.path))
        self._render_task_context_details()

    def _render_task_context_details(self) -> None:
        if self.selected_task is None:
            self._set_markdown(self.context_view, "")
            return
        try:
            slots = _load_task_context_slots(self.selected_task.path)
        except ValueError as exc:
            self._set_markdown(self.context_view, f"# {self._tr('context_journal_error')}\n\n{exc}\n")
            return
        self._refresh_task_context_label_filter([])
        if not slots:
            self._set_markdown(self.context_view, f"# {self._tr('context_journal')}\n\n- {self._tr('context_filter_no_matches')}\n")
            return
        body = _render_task_context_slots(
            [slot for slot in slots if slot.category != "goal"],
            format_name="agent" if self.task_context_encoded_check.get_active() else "markdown",
            task_dir=self.selected_task.path,
        )
        self._set_markdown(self.context_view, f"# {self._tr('context_journal')}\n\n{body}\n")

    def _on_task_context_filter_changed(self, *_args: object) -> None:
        if self.selected_task is not None:
            self._render_task_context_details()

    def _clear_task_context_filters(self, *_args: object) -> None:
        self.task_context_filter_since = None
        self.task_context_filter_until = None
        self._update_task_context_date_buttons()
        for group, checks in (
            ("severity", self.task_context_severity_checks),
            ("status", self.task_context_status_checks),
            ("label", self.task_context_label_checks),
        ):
            self._set_task_context_group_checks_to_default(group, checks)
        self._on_task_context_filter_changed()

    def _task_context_filter_since_value(self) -> str | None:
        return self.task_context_filter_since

    def _task_context_filter_until_value(self) -> str | None:
        return self.task_context_filter_until

    def _task_context_filter_severity_value(self) -> tuple[str, ...] | None:
        return self._task_context_filter_group_values(self.task_context_severity_checks)

    def _task_context_filter_status_values(self) -> tuple[str, ...] | None:
        return self._task_context_filter_group_values(self.task_context_status_checks)

    def _task_context_filter_label_values(self) -> tuple[str, ...] | None:
        return self._task_context_filter_group_values(self.task_context_label_checks)

    def _task_context_filter_group_values(self, checks: dict[str, Gtk.CheckButton]) -> tuple[str, ...] | None:
        if not checks:
            return None
        values = tuple(value for value, check in checks.items() if check.get_active())
        if len(values) == len(checks):
            return None
        return values

    def _refresh_task_context_label_filter(self, entries: object) -> None:
        label_box = getattr(self, "task_context_label_box", None)
        if label_box is None:
            return
        labels = sorted({label for entry in entries for label in entry.labels}, key=str.casefold)
        selected_values = self._task_context_filter_label_values()
        selected = set(labels if selected_values is None else selected_values)
        if labels == list(self.task_context_label_checks):
            return
        for child in list(label_box.get_children()):
            label_box.remove(child)
        self.task_context_label_checks.clear()
        if labels:
            all_check = Gtk.CheckButton(label=self._tr("context_filter_select_all"))
            all_check.connect("toggled", self._on_task_context_all_toggled, "label", self.task_context_label_checks)
            self.task_context_filter_all_checks["label"] = all_check
            label_box.pack_start(all_check, False, False, 0)
        if not labels:
            label = Gtk.Label(label=self._tr("context_filter_no_labels"))
            label.set_xalign(0)
            label_box.pack_start(label, False, False, 0)
        for value in labels:
            check = Gtk.CheckButton(label=value)
            check.set_active(value in selected)
            check.connect("toggled", self._on_task_context_item_toggled, "label", self.task_context_label_checks)
            self.task_context_label_checks[value] = check
            label_box.pack_start(check, False, False, 0)
        self._update_task_context_all_check("label", self.task_context_label_checks)
        label_box.show_all()

    def _on_task_context_all_toggled(
        self,
        check: Gtk.CheckButton,
        group: str,
        target: dict[str, Gtk.CheckButton],
    ) -> None:
        if self._updating_task_context_checks:
            return
        self._set_task_context_group_checks(group, target, check.get_active())
        self._on_task_context_filter_changed()

    def _on_task_context_item_toggled(
        self,
        _check: Gtk.CheckButton,
        group: str,
        target: dict[str, Gtk.CheckButton],
    ) -> None:
        if self._updating_task_context_checks:
            return
        self._update_task_context_all_check(group, target)
        self._on_task_context_filter_changed()

    def _set_task_context_group_checks(
        self,
        group: str,
        target: dict[str, Gtk.CheckButton],
        active: bool,
    ) -> None:
        self._updating_task_context_checks = True
        try:
            for check in target.values():
                check.set_active(active)
            self._update_task_context_all_check(group, target)
        finally:
            self._updating_task_context_checks = False

    def _set_task_context_group_checks_to_default(
        self,
        group: str,
        target: dict[str, Gtk.CheckButton],
    ) -> None:
        selected = set(self._task_context_default_group_values(group, tuple(target)))
        self._updating_task_context_checks = True
        try:
            for value, check in target.items():
                check.set_active(value in selected)
            self._update_task_context_all_check(group, target)
        finally:
            self._updating_task_context_checks = False

    def _task_context_default_group_values(self, group: str, values: tuple[str, ...]) -> tuple[str, ...]:
        if group == "status":
            return tuple(value for value in values if value in TASK_CONTEXT_DEFAULT_STATUS_FILTER)
        return values

    def _update_task_context_all_check(
        self,
        group: str,
        target: dict[str, Gtk.CheckButton],
    ) -> None:
        all_check = self.task_context_filter_all_checks.get(group)
        if all_check is None:
            return
        total = len(target)
        selected = sum(1 for check in target.values() if check.get_active())
        self._updating_task_context_checks = True
        try:
            all_check.set_inconsistent(0 < selected < total)
            all_check.set_active(total > 0 and selected == total)
        finally:
            self._updating_task_context_checks = False

    def _choose_task_context_since(self, *_args: object) -> None:
        self._choose_task_context_date("since")

    def _choose_task_context_until(self, *_args: object) -> None:
        self._choose_task_context_date("until")

    def _choose_task_context_date(self, boundary: str) -> None:
        if self.task_context_date_popover is not None:
            self.task_context_date_popover.popdown()
        current = self.task_context_filter_since if boundary == "since" else self.task_context_filter_until
        parent = self.task_context_since_button if boundary == "since" else self.task_context_until_button
        if parent is None:
            return
        popover = Gtk.Popover.new(parent)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(8)
        calendar = Gtk.Calendar()
        if current:
            year, month, day = (int(part) for part in current.split("-", 2))
            calendar.select_month(month - 1, year)
            calendar.select_day(day)
        box.pack_start(calendar, False, False, 0)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        clear_button = Gtk.Button(label=self._tr("context_filter_clear_date"))
        ok_button = Gtk.Button(label=self._tr("ok"))
        buttons.pack_start(clear_button, True, True, 0)
        buttons.pack_start(ok_button, True, True, 0)
        box.pack_start(buttons, False, False, 0)
        popover.add(box)

        def apply_date(*_args: object) -> None:
            year, month, day = calendar.get_date()
            value = f"{year:04d}-{month + 1:02d}-{day:02d}"
            if boundary == "since":
                self.task_context_filter_since = value
            else:
                self.task_context_filter_until = value
            popover.popdown()
            self._update_task_context_date_buttons()
            self._on_task_context_filter_changed()

        def clear_date(*_args: object) -> None:
            if boundary == "since":
                self.task_context_filter_since = None
            else:
                self.task_context_filter_until = None
            popover.popdown()
            self._update_task_context_date_buttons()
            self._on_task_context_filter_changed()

        ok_button.connect("clicked", apply_date)
        clear_button.connect("clicked", clear_date)
        calendar.connect("day-selected-double-click", apply_date)
        popover.connect("closed", lambda *_args: setattr(self, "task_context_date_popover", None))
        self.task_context_date_popover = popover
        popover.show_all()
        popover.popup()

    def _update_task_context_date_buttons(self) -> None:
        if self.task_context_since_button is not None:
            label = self.task_context_filter_since or self._tr("context_filter_any_date")
            self.task_context_since_button.set_label(self._tr("context_filter_since_value").format(value=label))
        if self.task_context_until_button is not None:
            label = self.task_context_filter_until or self._tr("context_filter_any_date")
            self.task_context_until_button.set_label(self._tr("context_filter_until_value").format(value=label))

    def _on_main_notebook_switch_page(
        self,
        _notebook: Gtk.Notebook,
        page: Gtk.Widget,
        _page_num: int,
    ) -> None:
        previous_page = getattr(self, "active_main_page", None)
        if previous_page is self.actions_page and page is not self.actions_page:
            self._remember_current_console_tab()
        self.active_main_page = page
        if page is self.actions_page:
            self._load_task_action_buttons()
            self._ensure_default_console_for_selected_task()
            self._restore_last_console_page_for_selected_task()
        elif page is getattr(self, "details_page", None) and self.selected_task is not None:
            self._refresh_selected_task_details()
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
        view.connect("populate-popup", self._on_detail_view_populate_popup)

    def _on_detail_view_button_press(self, view: Gtk.TextView, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        self._detail_context_menu(view).popup_at_pointer(event)
        return True

    def _on_detail_view_populate_popup(self, view: Gtk.TextView, menu: Gtk.Menu) -> None:
        for child in menu.get_children():
            menu.remove(child)
        self._populate_detail_context_menu(menu, view)
        menu.show_all()

    def _detail_context_menu(self, view: Gtk.TextView) -> Gtk.Menu:
        menu = Gtk.Menu()
        self._populate_detail_context_menu(menu, view)
        menu.show_all()
        return menu

    def _populate_detail_context_menu(self, menu: Gtk.Menu, view: Gtk.TextView) -> None:
        editing = self.detail_editing.get(view, False)
        is_description = self.detail_filenames.get(view) == "goal"
        buffer = view.get_buffer()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        readonly_items = (
            (self._tr("copy"), lambda *_: buffer.copy_clipboard(clipboard)),
            (self._tr("select_all"), lambda *_: buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())),
        )
        for label, callback in readonly_items:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", callback)
            menu.append(item)
        if is_description:
            menu.append(Gtk.SeparatorMenuItem())
            if editing:
                items = (
                    (self._tr("save"), lambda *_: self._save_detail_view(view)),
                    (self._tr("cancel"), lambda *_: self._cancel_detail_edit(view)),
                )
            else:
                items = ((self._tr("edit"), lambda *_: self._edit_detail_view(view)),)
            for label, callback in items:
                item = Gtk.MenuItem(label=label)
                item.set_sensitive(self.selected_task is not None)
                item.connect("activate", callback)
                menu.append(item)

    def _edit_detail_view(self, view: Gtk.TextView) -> None:
        if self.selected_task is None:
            return
        filename = self.detail_filenames[view]
        if filename == "goal":
            slots = _load_task_context_slots(self.selected_task.path, ("goal",))
            text = slots[0].content if slots else ""
        else:
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
        text = _text_buffer_text(view.get_buffer())
        if filename == "goal":
            _set_task_context_slot(self.selected_task.path, "goal", text)
        else:
            path = self.selected_task.path / filename
            path.write_text(text, encoding="utf-8")
        self.detail_editing[view] = False
        view.set_editable(False)
        view.set_cursor_visible(False)
        if filename == "goal":
            self._set_markdown(view, _task_goal_slot_markdown(self.selected_task.path))
        else:
            self._set_markdown(view, path.read_text(encoding="utf-8", errors="replace"))
        self.refresh_tasks()

    def _cancel_detail_edit(self, view: Gtk.TextView) -> None:
        text = self.detail_original_text.get(view, "")
        self.detail_editing[view] = False
        view.set_editable(False)
        view.set_cursor_visible(False)
        if self.selected_task is not None and self.detail_filenames.get(view) == "goal":
            self._set_markdown(view, _task_goal_slot_markdown(self.selected_task.path))
        else:
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
        dialog.set_default_size(920, 760)
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        notebook = Gtk.Notebook()
        content.add(notebook)
        general_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        general_grid.set_border_width(12)
        dictionary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dictionary_box.set_border_width(12)
        dictionary_grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        notebook.append_page(general_grid, Gtk.Label(label="General"))
        notebook.append_page(dictionary_box, Gtk.Label(label="Dictionary"))

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
        codex_available = agent_executable("codex") is not None
        claude_available = agent_executable("claude") is not None
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
        codex_models = codex_model_choices_info(use_cli=False) if codex_available else None
        claude_models = claude_model_choices_info() if claude_available else None
        if codex_models is not None:
            _set_combo_text_choices(
                codex_model_combo,
                model_choices_with_current(codex_models.choices, self.default_codex_model),
                self.default_codex_model,
            )
        if claude_models is not None:
            _set_combo_text_choices(
                claude_model_combo,
                model_choices_with_current(claude_models.choices, self.default_claude_model),
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
        dictionary_auto = Gtk.CheckButton()
        dictionary_auto.set_active(self.task_dictionary_auto_discovery)
        dictionary_strip_articles = Gtk.CheckButton()
        dictionary_strip_articles.set_active(self.task_dictionary_strip_articles)
        dictionary_min_occurrences = Gtk.SpinButton.new_with_range(1, 20, 1)
        dictionary_min_occurrences.set_value(self.task_dictionary_min_occurrences)
        dictionary_min_saving = Gtk.SpinButton.new_with_range(0, 10_000, 1)
        dictionary_min_saving.set_value(self.task_dictionary_min_saving)
        dictionary_min_term_length = Gtk.SpinButton.new_with_range(1, 200, 1)
        dictionary_min_term_length.set_value(self.task_dictionary_min_term_length)
        dictionary_max_term_words = Gtk.SpinButton.new_with_range(1, 20, 1)
        dictionary_max_term_words.set_value(self.task_dictionary_max_term_words)
        preview_input = _text_view(self.text_font_size, editable=True)
        preview_input.get_buffer().set_text(self.task_dictionary_preview_text)
        preview_output = _text_view(self.text_font_size, editable=False)
        preview_metrics = _text_view(self.text_font_size, editable=False)
        preview_input_scrolled = _scrolled(preview_input)
        preview_input_scrolled.set_hexpand(True)
        preview_input_scrolled.set_vexpand(True)
        preview_input_scrolled.set_min_content_height(360)
        preview_output_scrolled = _scrolled(preview_output)
        preview_output_scrolled.set_hexpand(True)
        preview_output_scrolled.set_vexpand(True)
        preview_output_scrolled.set_min_content_height(260)
        preview_metrics_scrolled = _scrolled(preview_metrics)
        preview_metrics_scrolled.set_hexpand(True)
        preview_metrics_scrolled.set_vexpand(False)
        preview_metrics_scrolled.set_min_content_height(130)
        preview_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        preview_paned.set_hexpand(True)
        preview_paned.set_vexpand(True)
        preview_input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_input_box.set_hexpand(True)
        preview_input_box.set_vexpand(True)
        preview_output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_output_box.set_hexpand(True)
        preview_output_box.set_vexpand(True)
        preview_metrics_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_metrics_box.set_hexpand(True)
        preview_metrics_box.set_vexpand(False)
        preview_label = Gtk.Label(label="Preview text")
        preview_label.set_xalign(0)
        preview_output_label = Gtk.Label(label="Compiler preview")
        preview_output_label.set_xalign(0)
        preview_metrics_label = Gtk.Label(label="Savings")
        preview_metrics_label.set_xalign(0)
        preview_input_box.pack_start(preview_label, False, False, 0)
        preview_input_box.pack_start(preview_input_scrolled, True, True, 0)
        preview_output_box.pack_start(preview_output_label, False, False, 0)
        preview_output_box.pack_start(preview_output_scrolled, True, True, 0)
        preview_metrics_box.pack_start(preview_metrics_label, False, False, 0)
        preview_metrics_box.pack_start(preview_metrics_scrolled, False, False, 0)
        preview_paned.pack1(preview_input_box, True, False)
        preview_paned.pack2(preview_output_box, True, False)

        def dictionary_policy() -> TaskDictionaryPolicy:
            return TaskDictionaryPolicy(
                auto_discovery=dictionary_auto.get_active(),
                min_occurrences=int(dictionary_min_occurrences.get_value()),
                min_saving=int(dictionary_min_saving.get_value()),
                min_term_length=int(dictionary_min_term_length.get_value()),
                max_term_words=int(dictionary_max_term_words.get_value()),
                strip_articles=dictionary_strip_articles.get_active(),
            )

        def update_dictionary_preview(*_ignored: object) -> None:
            text = _text_buffer_text(preview_input.get_buffer())
            preview = preview_dictionary_compile(text, dictionary_policy())
            preview_output.get_buffer().set_text(_dictionary_preview_text(text, preview))
            preview_metrics.get_buffer().set_text(_dictionary_preview_metrics_text(text, preview))

        general_rows: list[tuple[str, Gtk.Widget]] = [
            (self._tr("text_font_size"), text_size),
            (self._tr("button_font_size"), button_size),
            (self._tr("theme"), theme_combo),
            (self._tr("language"), language_combo),
            (self._tr("default_agent"), default_agent_combo),
        ]
        if codex_models is not None:
            general_rows.extend(
                [
                    (self._tr("default_codex_model"), codex_model_combo),
                    (self._tr("default_codex_reasoning"), codex_reasoning_combo),
                ]
            )
        if claude_models is not None:
            general_rows.extend(
                [
                    (self._tr("default_claude_model"), claude_model_combo),
                    (self._tr("default_claude_effort"), claude_effort_combo),
                ]
            )
        for row, (label, widget) in enumerate(general_rows):
            label_widget = Gtk.Label(label=label)
            label_widget.set_xalign(0)
            if isinstance(widget, Gtk.Label):
                widget.set_xalign(0)
            general_grid.attach(label_widget, 0, row, 1, 1)
            general_grid.attach(widget, 1, row, 1, 1)

        dictionary_box.pack_start(dictionary_grid, False, False, 0)
        dictionary_box.pack_start(preview_paned, True, True, 0)
        dictionary_box.pack_start(preview_metrics_box, False, False, 0)
        row = 0
        dictionary_heading = Gtk.Label(label="Task dictionary compiler")
        dictionary_heading.set_xalign(0)
        dictionary_grid.attach(dictionary_heading, 0, row, 2, 1)
        for label, widget in (
            ("Auto-discover aliases", dictionary_auto),
            ("Strip English articles", dictionary_strip_articles),
            ("Min occurrences", dictionary_min_occurrences),
            ("Min saving", dictionary_min_saving),
            ("Min term length", dictionary_min_term_length),
            ("Max term words", dictionary_max_term_words),
        ):
            row += 1
            label_widget = Gtk.Label(label=label)
            label_widget.set_xalign(0)
            dictionary_grid.attach(label_widget, 0, row, 1, 1)
            dictionary_grid.attach(widget, 1, row, 1, 1)
        for widget in (
            dictionary_auto,
            dictionary_strip_articles,
            dictionary_min_occurrences,
            dictionary_min_saving,
            dictionary_min_term_length,
            dictionary_max_term_words,
        ):
            signal = "toggled" if isinstance(widget, Gtk.CheckButton) else "value-changed"
            widget.connect(signal, update_dictionary_preview)
        preview_input.get_buffer().connect("changed", update_dictionary_preview)
        update_dictionary_preview()

        dialog.show_all()
        settings_open = {"value": True}
        if codex_available:
            def refresh_codex_models() -> None:
                info = codex_model_choices_info(use_cli=True)

                def apply_codex_models() -> bool:
                    if not settings_open["value"]:
                        return False
                    current = codex_model_combo.get_active_text() or self.default_codex_model
                    _set_combo_text_choices(
                        codex_model_combo,
                        model_choices_with_current(info.choices, current),
                        current,
                    )
                    return False

                GLib.idle_add(apply_codex_models)

            threading.Thread(target=refresh_codex_models, daemon=True).start()
        text_size.grab_focus()
        response = dialog.run()
        settings_open["value"] = False
        if response == Gtk.ResponseType.OK:
            self.text_font_size = int(text_size.get_value())
            self.button_font_size = int(button_size.get_value())
            self.theme = theme_combo.get_active_text() or self.theme
            self.language = language_combo.get_active_text() or self.language
            self.default_agent = normalize_agent(default_agent_combo.get_active_text())
            if codex_available:
                self.default_codex_model = codex_model_combo.get_active_text() or ""
                self.default_codex_reasoning = codex_reasoning_combo.get_active_text() or ""
            if claude_available:
                self.default_claude_model = claude_model_combo.get_active_text() or ""
                self.default_claude_effort = claude_effort_combo.get_active_text() or ""
            self.task_dictionary_auto_discovery = dictionary_auto.get_active()
            self.task_dictionary_min_occurrences = int(dictionary_min_occurrences.get_value())
            self.task_dictionary_min_saving = int(dictionary_min_saving.get_value())
            self.task_dictionary_min_term_length = int(dictionary_min_term_length.get_value())
            self.task_dictionary_max_term_words = int(dictionary_max_term_words.get_value())
            self.task_dictionary_strip_articles = dictionary_strip_articles.get_active()
            self.task_dictionary_preview_text = _text_buffer_text(preview_input.get_buffer())
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
        self.task_action_play_buttons = {}
        self._clear_task_action_buttons()
        self._clear_task_action_parameters()
        self._update_actions_message()

    def _clear_task_action_buttons(self) -> None:
        for child in self.task_actions_box.get_children():
            self.task_actions_box.remove(child)
        self.task_action_item_widgets = {}
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
        self.task_action_play_buttons = {}
        self.task_action_item_widgets = {}
        self.task_actions_signature = _task_actions_signature(task)
        self.task_action_errors = config.errors
        self._update_actions_message()
        for action in self.task_base_actions:
            self.task_action_item_widgets[action.action_id] = self._task_action_button(action, shortcut=False)
        self._schedule_task_action_reflow()
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

    def _on_task_actions_box_size_allocate(self, *_args: object) -> None:
        self._schedule_task_action_reflow()

    def _schedule_task_action_reflow(self) -> None:
        if self.task_action_reflow_source_id is None:
            self.task_action_reflow_source_id = GLib.idle_add(self._reflow_task_action_buttons)

    def _reflow_task_action_buttons(self) -> bool:
        self.task_action_reflow_source_id = None
        if not hasattr(self, "task_actions_box"):
            return False
        for widget in self.task_action_item_widgets.values():
            parent = widget.get_parent()
            if isinstance(parent, Gtk.Container):
                parent.remove(widget)
        for row in self.task_actions_box.get_children():
            self.task_actions_box.remove(row)
        width = max(1, self.task_actions_box.get_allocated_width() - self.task_actions_box.get_border_width() * 2)
        row: Gtk.Box | None = None
        row_width = 0
        for widget in self._task_action_reorder_children():
            _minimum_width, natural_width = widget.get_preferred_width()
            next_width = natural_width if row_width == 0 else row_width + 3 + natural_width
            if row is not None and next_width > width:
                row = None
                row_width = 0
            if row is None:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                row.set_halign(Gtk.Align.START)
                self.task_actions_box.pack_start(row, False, False, 0)
            row.pack_start(widget, False, False, 0)
            row_width = natural_width if row_width == 0 else row_width + 3 + natural_width
        self.task_actions_box.show_all()
        self._update_task_action_button_selection()
        return False

    def _task_action_reorder_children(self) -> list[Gtk.Widget]:
        order = self.task_action_reorder_preview if self.task_reorder_group == "action" else None
        action_ids = order or self._task_action_order()
        return [self.task_action_item_widgets[action_id] for action_id in action_ids if action_id in self.task_action_item_widgets]

    def _task_action_button(self, action: TaskAction, *, shortcut: bool) -> Gtk.Widget:
        button = _compact_button(action.label, lambda _button, item=action: self._on_task_action_clicked(item))
        button.set_size_request(-1, 20)
        button.set_focus_on_click(False)
        button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        if shortcut:
            button.set_tooltip_text(self._s("action.shortcut_tooltip"))
            button.connect("button-press-event", self._on_task_shortcut_button_press, action)
            return button
        button.connect("button-press-event", self._on_task_action_button_press, action)
        button.get_style_context().add_class("task-action-label-button")
        self.task_action_buttons[action.action_id] = button
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        setattr(row, "_task_reorder_id", action.action_id)
        row.pack_start(button, False, False, 0)
        play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU)
        play.set_size_request(20, 20)
        play.set_relief(Gtk.ReliefStyle.NONE)
        play.set_focus_on_click(False)
        play.set_no_show_all(True)
        play.set_visible(False)
        play.set_sensitive(False)
        play.set_tooltip_text(self._s("action.play_tooltip"))
        play.get_style_context().add_class("task-action-play-button")
        play.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        play.connect("clicked", self._on_task_action_play_clicked, action)
        play.connect("button-press-event", self._on_task_action_play_button_press, action)
        self.task_action_play_buttons[action.action_id] = play
        row.pack_start(play, False, False, 0)
        row.show_all()
        if not self.task_action_reorder_mode:
            return row
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        setattr(event_box, "_task_reorder_id", action.action_id)
        event_box.add(row)
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
        item_a = _reorder_child_id(child_a)
        item_b = _reorder_child_id(child_b)
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
            play = self.task_action_play_buttons.get(action_id)
            if action_id == selected_id:
                context.add_class("task-action-selected")
                if play is not None:
                    play.get_style_context().add_class("task-action-selected")
                    play.set_visible(True)
                    play.set_sensitive(True)
            else:
                context.remove_class("task-action-selected")
                if play is not None:
                    play.get_style_context().remove_class("task-action-selected")
                    play.set_visible(False)
                    play.set_sensitive(False)

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
        if (
            not self.task_action_reorder_mode
            and event.type == Gdk.EventType.BUTTON_PRESS
            and event.button == 1
        ):
            self._on_task_action_clicked(action)
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
        children = self._task_action_reorder_children() if box is self.task_actions_box else _reorder_box_children(box)
        for child in children:
            item_id = _reorder_child_id(child)
            if not item_id or item_id == self.task_action_drag_source_id:
                continue
            allocation = child.get_allocation()
            parent = child.get_parent()
            parent_allocation = parent.get_allocation() if isinstance(parent, Gtk.Widget) and parent is not box else None
            allocation_x = allocation.x + (parent_allocation.x if parent_allocation is not None else 0)
            allocation_y = allocation.y + (parent_allocation.y if parent_allocation is not None else 0)
            center_y = allocation_y + allocation.height / 2
            row = next((entry for entry in rows if abs(entry[0] - center_y) <= max(1, allocation.height / 2)), None)
            if row is None:
                row = (center_y, {})
                rows.append(row)
            row[1][item_id] = allocation_x + allocation.width / 2
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
        if (
            not self.task_action_reorder_mode
            and event.type == Gdk.EventType.BUTTON_PRESS
            and event.button == 1
        ):
            self._on_task_action_play_clicked(button, action)
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
            button.set_size_request(-1, 20)
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
            no_parameters = _compact_button(self._s("action.no_parameters"), None, max_width_chars=18)
            no_parameters.set_size_request(-1, 20)
            no_parameters.set_sensitive(False)
            _flow_box_add(self.task_action_parameter_box, no_parameters)
        for parameter in local_parameters:
            button = _compact_button(self._parameter_button_label(parameter), None, max_width_chars=18)
            button.set_size_request(-1, 20)
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
        shortcut_button.set_size_request(-1, 20)
        shortcut_button.connect("clicked", lambda _button: self._save_selected_action_as_shortcut())
        self.save_task_shortcut_box.pack_start(shortcut_button, False, False, 0)
        self.task_action_parameter_box.show_all()
        self.task_shortcuts_box.show_all()
        self.save_task_shortcut_box.show_all()

    def _shortcuts_for_action(self, action: TaskAction) -> list[TaskAction]:
        return shortcuts_for_action(action, self.task_shortcuts)

    def _parameter_button_label(self, parameter: TaskActionParameter) -> str:
        return parameter_button_label(parameter, self.task_action_config, self.selected_task_action_bindings)

    def _selected_parameter_value(self, parameter: TaskActionParameter) -> str:
        config = self.task_action_config
        global_bindings = config.global_parameter_bindings if config is not None else {}
        return selected_parameter_value(parameter, self.selected_task_action_bindings, global_bindings)

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
        if not parameter.global_name:
            return

        def mutator(data: dict[str, object]) -> bool:
            globals_data = data.setdefault("global_parameters", {})
            if not isinstance(globals_data, dict):
                return False
            definition = globals_data.get(parameter.global_name)
            if isinstance(definition, dict):
                definition["value"] = selected
            else:
                globals_data[parameter.global_name] = {
                    "label": parameter.label,
                    "type": parameter.parameter_type,
                    "value": selected,
                }
            return True

        self._mutate_task_actions_data(mutator, reload_on_no_change=True)

    def _run_selected_task_action(self) -> None:
        action = self.selected_task_action
        if action is not None:
            self._run_task_action_with_current_bindings(action)

    def _run_task_action_with_current_bindings(self, action: TaskAction) -> None:
        config = self.task_action_config
        if config is None:
            return
        selected_id = self.selected_task_action.action_id if self.selected_task_action is not None else None
        bindings = bindings_for_action_run(action, selected_id, self.selected_task_action_bindings)
        bound = bind_task_action_parameters(action, config.parameter_sets, bindings, config.global_parameter_bindings)
        self.run_custom_task_action(bound)

    def _parameter_values(self, parameter: TaskActionParameter) -> dict[str, dict[str, str]]:
        return parameter_values(parameter, self.task_action_config)

    def _task_parameter_context_menu(self, parameter: TaskActionParameter) -> Gtk.Menu:
        menu = Gtk.Menu()
        selected = self._selected_parameter_value(parameter)
        state = task_parameter_menu_state(selected, self.task_action_reorder_mode)
        add_item = Gtk.MenuItem(label=self._s("action.add_value", set_name=parameter.set_name))
        add_item.connect("activate", lambda _item: self._edit_parameter_set_value(parameter, None, None))
        duplicate_item = Gtk.MenuItem(label=self._s("action.duplicate_value", value=state.selected_value))
        duplicate_item.connect(
            "activate",
            lambda _item: self._edit_parameter_set_value(
                parameter,
                None,
                self._parameter_values(parameter).get(state.selected_value, {}),
            ),
        )
        edit_item = Gtk.MenuItem(label=self._s("action.edit_value", value=state.selected_value))
        edit_item.connect(
            "activate",
            lambda _item: self._edit_parameter_set_value(
                parameter,
                state.selected_value,
                self._parameter_values(parameter).get(state.selected_value, {}),
            ),
        )
        delete_item = Gtk.MenuItem(label=self._s("action.delete_value", value=state.selected_value))
        delete_item.connect("activate", lambda _item: self._delete_parameter_set_value(parameter, state.selected_value))
        reorder_item = Gtk.MenuItem(label=self._s(state.reorder_label_key))
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
        state = task_action_menu_state(
            task.path if task is not None else None,
            self._task_action_code_path(action),
            self.task_action_reorder_mode,
        )
        menu = Gtk.Menu()
        run_item = Gtk.MenuItem(label=self._s("action.run"))
        run_item.connect("activate", lambda _item: self._run_task_action_with_current_bindings(action))
        open_item = Gtk.MenuItem(label=self._s("action.open_actions_file"))
        if state.actions_file is not None:
            open_item.connect("activate", lambda _item, path=state.actions_file: open_text_file(path))
        else:
            open_item.set_sensitive(False)
        edit_item = Gtk.MenuItem(label=self._s("action.edit"))
        if state.code_path is not None:
            edit_item.connect("activate", lambda _item, path=state.code_path: self._edit_action_code_file(path))
        else:
            edit_item.set_sensitive(False)
        reorder_item = Gtk.MenuItem(label=self._s(state.reorder_label_key))
        reorder_item.connect("activate", lambda _item: self._set_task_action_reorder_mode(not self.task_action_reorder_mode))
        menu.append(run_item)
        menu.append(open_item)
        menu.append(edit_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(reorder_item)
        menu.show_all()
        return menu

    def _task_action_code_path(self, action: TaskAction) -> Path | None:
        return task_action_code_path(action)

    def _edit_action_code_file(self, path: Path) -> None:
        try:
            open_text_file(path)
        except OSError as error:
            self._show_error(self._s("action.cannot_open_code"), str(error))

    def _task_shortcut_context_menu(self, action: TaskAction) -> Gtk.Menu:
        state = task_shortcut_menu_state(self.task_action_reorder_mode)
        menu = Gtk.Menu()
        run_item = Gtk.MenuItem(label=self._s("action.run"))
        run_item.connect("activate", lambda _item: self.run_custom_task_action(action))
        delete_item = Gtk.MenuItem(label=self._s("action.delete_shortcut"))
        delete_item.connect("activate", lambda _item: self._delete_task_shortcut(action))
        reorder_item = Gtk.MenuItem(label=self._s(state.reorder_label_key))
        reorder_item.connect("activate", lambda _item: self._set_task_action_reorder_mode(not self.task_action_reorder_mode))
        menu.append(run_item)
        menu.append(delete_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(reorder_item)
        menu.show_all()
        return menu

    def _move_task_action(self, action: TaskAction, offset: int) -> None:
        self._mutate_task_actions_data(
            lambda data: isinstance(data.get("actions"), list)
            and _move_json_list_entry(data["actions"], "id", action.action_id, offset)
        )

    def _move_task_action_before(self, source_id: str, target_id: str) -> None:
        self._mutate_task_actions_data(
            lambda data: isinstance(data.get("actions"), list)
            and _move_json_list_entry_before(data["actions"], "id", source_id, target_id)
        )

    def _save_task_action_order(self, order: list[str]) -> None:
        self._save_task_order_group("action", order)

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
            self._schedule_task_action_reflow()
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
        self._save_task_order_group("shortcut", order)

    def _save_task_parameter_order(self, order: list[str]) -> None:
        self._save_task_order_group("parameter", order)

    def _save_global_task_parameter_order(self, order: list[str]) -> None:
        self._save_task_order_group("global_parameter", order)

    def _save_task_order_group(self, group: str, order: list[str]) -> None:
        action = self.selected_task_action
        selected_action_id = action.action_id if action is not None else None
        self._mutate_task_actions_data(
            lambda data: _reorder_task_action_data(data, group, order, selected_action_id=selected_action_id)
        )

    def _mutate_task_actions_data(
        self,
        mutator: Callable[[dict[str, object]], bool],
        *,
        reload_actions: bool = True,
        reload_on_no_change: bool = False,
    ) -> bool:
        task = self._require_task(show_dialog=False)
        if task is None:
            return False
        data, errors = load_task_actions_data(task)
        if errors:
            self.task_action_errors = errors
            self._update_actions_message()
            return False
        if not mutator(data):
            if reload_actions and reload_on_no_change:
                self._load_task_action_buttons()
            return False
        save_task_actions_data(task, data)
        if reload_actions:
            self._load_task_action_buttons()
        return True

    def _set_task_action_reorder_mode(self, enabled: bool) -> None:
        self.task_action_reorder_mode = enabled
        self._load_task_action_buttons()

    def _move_task_shortcut(self, action: TaskAction, offset: int) -> None:
        self._mutate_task_actions_data(
            lambda data: isinstance(data.get("shortcuts"), list)
            and _move_json_list_entry(data["shortcuts"], "id", action.action_id, offset)
        )

    def _move_task_parameter(self, parameter: TaskActionParameter, offset: int) -> None:
        if parameter.global_name:
            self._move_global_task_parameter(parameter.global_name, offset)
            return
        action = self.selected_task_action
        if action is None:
            return
        self._mutate_task_actions_data(
            lambda data: _move_action_parameter_entry(data, action.action_id, parameter.name, offset)
        )

    def _move_global_task_parameter(self, global_name: str, offset: int) -> None:
        self._mutate_task_actions_data(
            lambda data: isinstance(data.get("global_parameters"), dict)
            and _move_json_mapping_entry(data["global_parameters"], global_name, offset)
        )

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
        field_names = _parameter_dialog_field_names(
            data,
            parameter.parameter_type,
            set(fields),
            list(self._parameter_values(parameter).values()),
        )
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
                if _upsert_parameter_set_value(data, parameter.set_name, value_id, new_id, value) is not None:
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
        self._mutate_task_actions_data(
            lambda data: _delete_parameter_set_value(data, parameter.set_name, value_id),
            reload_on_no_change=True,
        )

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
                action_id = action.base_action_id or action.action_id
                bindings = dict(self.selected_task_action_bindings)
                self._mutate_task_actions_data(
                    lambda data: _add_task_shortcut(data, shortcut_id, label, action_id, bindings)
                )
        dialog.destroy()

    def _delete_task_shortcut(self, action: TaskAction) -> None:
        self._mutate_task_actions_data(lambda data: _delete_task_shortcut(data, action.action_id))

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
            prompt_suffix=CODEX_LANGUAGE_INSTRUCTIONS.get(self.language, CODEX_LANGUAGE_INSTRUCTIONS["en"]),
            inject_task_context=self.inject_task_context_prompt,
            include_task_check=True,
        )
        run_id = new_agent_session_id()
        env = ai_agent_environment(os.environ.copy(), task, self.workspace, agent, launch.session_state, run_id=run_id)
        for session in self._current_task_terminal_sessions(task):
            if session.kind == agent:
                self._activate_terminal(session.session_id)
                self._update_codex_button_state()
                return
        self._start_terminal(
            task=task,
            command=launch.command,
            cwd=self.workspace,
            env=env,
            kind=agent,
            run_id=run_id,
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
        run_id: str | None = None,
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
            run_id=run_id if session_is_agent(session_kind=kind) else None,
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
        if not self._restore_last_console_page(task):
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
        task = getattr(self, "selected_task", None)
        page_memory = getattr(self, "last_active_console_page_by_task", None)
        if page_memory is None:
            page_memory = {}
            self.last_active_console_page_by_task = page_memory
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return
        page = self.console_notebook.get_nth_page(page_num)
        if task is not None and page is getattr(self, "ai_agent_page", None):
            page_memory[task.path] = "ai-agent"
            return
        session = self._session_for_page(page)
        if session is not None:
            self.last_active_terminal_by_task[session.task_path] = session.session_id
            page_memory[session.task_path] = f"session:{session.session_id}"

    def _restore_last_console_page_for_selected_task(self) -> None:
        task = self.selected_task
        if task is None:
            return
        self._restore_last_console_page(task)

    def _activate_ai_agent_console_page(self, task: TaskSummary, *, remember: bool) -> bool:
        ai_agent_page = getattr(self, "ai_agent_page", None)
        if ai_agent_page is None:
            return False
        page_num = self.console_notebook.page_num(ai_agent_page)
        if page_num < 0:
            return False
        self.console_notebook.set_current_page(page_num)
        if remember:
            page_memory = getattr(self, "last_active_console_page_by_task", None)
            if page_memory is None:
                page_memory = {}
                self.last_active_console_page_by_task = page_memory
            page_memory[task.path] = "ai-agent"
        return True

    def _restore_last_console_page(self, task: TaskSummary) -> bool:
        page_marker = getattr(self, "last_active_console_page_by_task", {}).get(task.path)
        if page_marker == "ai-agent":
            return self._activate_ai_agent_console_page(task, remember=False)
        elif page_marker is not None and page_marker.startswith("session:"):
            try:
                session_id = int(page_marker.removeprefix("session:"))
            except ValueError:
                session_id = None
            if session_id is not None and session_id in self.terminal_sessions:
                self._activate_visible_terminal(session_id, remember=False)
                return True
        session_id = self.last_active_terminal_by_task.get(task.path)
        if session_id is not None:
            self._activate_visible_terminal(session_id, remember=False)
            return session_id in self.terminal_sessions
        return False

    def _on_console_notebook_switch_page(
        self,
        _notebook: Gtk.Notebook,
        page: Gtk.Widget,
        _page_num: int,
        ) -> None:
        if self._refreshing_console_tabs:
            return
        page_memory = getattr(self, "last_active_console_page_by_task", None)
        if page_memory is None:
            page_memory = {}
            self.last_active_console_page_by_task = page_memory
        task = getattr(self, "selected_task", None)
        if page is getattr(self, "ai_agent_page", None) and task is not None:
            page_memory[task.path] = "ai-agent"
            return
        session = self._session_for_page(page)
        if session is not None:
            self.last_active_terminal_by_task[session.task_path] = session.session_id
            page_memory[session.task_path] = f"session:{session.session_id}"

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
        page_memory = getattr(self, "last_active_console_page_by_task", {})
        if page_memory.get(session.task_path) == f"session:{session.session_id}":
            page_memory.pop(session.task_path, None)
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

    def _start_task_session_discovery(self) -> None:
        discovery = getattr(self, "task_session_discovery", None)
        if discovery is None:
            discovery = TaskSessionDiscoveryState()
            self.task_session_discovery = discovery
        for task in discovery.plan(self.tasks):
            worker = threading.Thread(
                target=self._resolve_task_agent_sessions_in_background,
                args=(task,),
                daemon=True,
            )
            worker.start()

    def _resolve_task_agent_sessions_in_background(self, task: TaskSummary) -> None:
        try:
            resolve_task_agent_sessions(task, self.workspace)
        except Exception as exc:  # pragma: no cover - defensive UI background path
            log_agent_workspace_exception(self.workspace, "gtk-session-discovery", type(exc), exc, exc.__traceback__)
        GLib.idle_add(self._finish_task_session_discovery, task.path)

    def _finish_task_session_discovery(self, task_path: Path) -> bool:
        self.task_session_discovery.finish(task_path)
        task = self._task_for_path(task_path)
        self._invalidate_task_session_marker_cache(task)
        self._refresh_task_row_styles()
        if self.selected_task is not None and self.selected_task.path == task_path:
            self._set_selected_agent(
                task_agent_selection_with_resumable_fallback(
                    task,
                    self.workspace,
                    self.default_agent,
                )
            )
            self._update_codex_button_state()
        return False

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
            updates = [
                (0, str(self._task_agent_status(task))),
                (1, str(self._task_label(task))),
                (3, str(background)),
                (4, bool(background_set)),
                (5, str(foreground)),
                (6, bool(foreground_set)),
                (7, int(weight)),
                (8, bool(weight_set)),
            ]
            changed = [
                (column, value)
                for column, value in updates
                if self.task_store[row_iter][column] != value
            ]
            if changed:
                self.task_store.set(
                    row_iter,
                    [column for column, _value in changed],
                    [value for _column, value in changed],
                )
            row_iter = self.task_store.iter_next(row_iter)
        self._ensure_selected_task_is_selectable()

    def _refresh_task_agent_status_cells(self) -> None:
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            task = self.task_store[row_iter][2]
            status = str(self._task_agent_status(task))
            if self.task_store[row_iter][0] != status:
                self.task_store.set(row_iter, [0], [status])
            row_iter = self.task_store.iter_next(row_iter)

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
            self._refresh_task_agent_status_cells()
        return True

    def _actions_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.actions_page

    def _details_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is getattr(self, "details_page", None)

    def _artifacts_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.artifacts_page

    def _ensure_default_console_for_selected_task(self) -> None:
        task = self.selected_task
        if task is None or self._current_task_terminal_sessions(task):
            return
        had_console_choice = (
            task.path in getattr(self, "last_active_console_page_by_task", {})
            or task.path in self.last_active_terminal_by_task
        )
        self.new_console(task=task)
        if not had_console_choice:
            self._activate_ai_agent_console_page(task, remember=True)

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
        if hasattr(self, "tasks") and hasattr(self, "workspace"):
            task = self._task_for_path(session.task_path)
            reconcile_task_agent_run_session(task, self.workspace, session.kind, session.run_id)
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
        copy_item = Gtk.MenuItem(label=self._tr("copy"))
        paste_item = Gtk.MenuItem(label=self._tr("paste"))
        select_all_item = Gtk.MenuItem(label=self._tr("select_all"))
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
        discovery = getattr(self, "task_session_discovery", None)
        if discovery is not None and discovery.is_pending(task):
            return f"⚙ {task.name}"
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
        if view is getattr(self, "context_view", None):
            self._mark_context_entry_links(view)

    def _mark_context_entry_links(self, view: Gtk.TextView) -> None:
        buffer = view.get_buffer()
        tag_table = buffer.get_tag_table()
        link_tag = tag_table.lookup("journal_link")
        if link_tag is None:
            link_tag = buffer.create_tag("journal_link", foreground="#9ecbff", underline=Pango.Underline.SINGLE)
        text = _text_buffer_text(buffer)
        for match in re.finditer(r"(?<![\w/-])#(\d+)\b", text):
            start = buffer.get_iter_at_offset(match.start())
            end = buffer.get_iter_at_offset(match.end())
            buffer.apply_tag(link_tag, start, end)

    def _on_context_view_button_release(self, view: Gtk.TextView, event: Gdk.EventButton) -> bool:
        if event.button != 1:
            return False
        buffer = view.get_buffer()
        x, y = view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, int(event.x), int(event.y))
        result = view.get_iter_at_location(x, y)
        if isinstance(result, tuple):
            cursor_iter = next(item for item in result if hasattr(item, "get_tags"))
        else:
            cursor_iter = result
        for tag in cursor_iter.get_tags():
            if tag.props.name == "journal_link":
                entry_id = _context_entry_reference_at_iter(buffer, cursor_iter)
                if entry_id is not None:
                    return self._scroll_context_view_to_entry(entry_id)
        return False

    def _scroll_context_view_to_entry(self, entry_id: int, *, allow_refilter: bool = True) -> bool:
        buffer = self.context_view.get_buffer()
        text = _text_buffer_text(buffer)
        for pattern in (rf"(?m)^\| #{entry_id} \[", rf"(?m)^#{entry_id} \["):
            match = re.search(pattern, text)
            if match is None:
                continue
            start = buffer.get_iter_at_offset(match.start())
            end = buffer.get_iter_at_offset(match.start() + len(f"#{entry_id}"))
            buffer.select_range(start, end)
            self.context_view.scroll_to_iter(start, 0.15, True, 0.0, 0.1)
            return True
        if allow_refilter and self._show_context_entry_in_full_journal(entry_id):
            return self._scroll_context_view_to_entry(entry_id, allow_refilter=False)
        return False

    def _show_context_entry_in_full_journal(self, entry_id: int) -> bool:
        if self.selected_task is None:
            return False
        try:
            entries = _load_task_context_entries(self.selected_task.path)
        except ValueError:
            return False
        if not any(entry.id == entry_id for entry in entries):
            return False
        self.task_context_filter_since = None
        self.task_context_filter_until = None
        self._update_task_context_date_buttons()
        self._set_task_context_group_checks("severity", self.task_context_severity_checks, True)
        self._set_task_context_group_checks("status", self.task_context_status_checks, True)
        self._set_task_context_group_checks("label", self.task_context_label_checks, True)
        self._render_task_context_details()
        return True

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

    def _on_main_pane_position_changed(self, pane: Gtk.Paned, _param: object | None) -> None:
        if self._pane_layout_ready and not self._updating_pane_positions:
            self.main_split_ratio = _pane_position_ratio(pane)
            self._schedule_pane_settings_save()

    def _on_main_pane_size_allocate(self, pane: Gtk.Paned, _allocation: Gtk.Allocation) -> None:
        self._set_pane_position_ratio(pane, self.main_split_ratio, minimum=360)

    def _on_details_pane_button_press(self, _pane: Gtk.Paned, event: Gdk.EventButton) -> bool:
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and _is_pane_separator_event(self.details_pane, event):
            self._set_details_default_split()
            return True
        return False

    def _on_details_pane_position_changed(self, pane: Gtk.Paned, _param: object | None) -> None:
        if self._pane_layout_ready and not self._updating_pane_positions:
            self.details_split_ratio = _pane_position_ratio(pane)
            self._schedule_pane_settings_save()

    def _on_details_pane_size_allocate(self, pane: Gtk.Paned, _allocation: Gtk.Allocation) -> None:
        self._set_pane_position_ratio(pane, self.details_split_ratio)

    def _on_actions_pane_button_press(self, _pane: Gtk.Paned, event: Gdk.EventButton) -> bool:
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and _is_pane_separator_event(self.actions_pane, event):
            self._set_actions_default_split()
            return True
        return False

    def _on_actions_pane_size_allocate(self, pane: Gtk.Paned, _allocation: Gtk.Allocation) -> None:
        self._set_pane_position_ratio(pane, self.actions_split_ratio)

    def _set_main_default_split(self) -> bool:
        self.main_split_ratio = 0.25
        self._set_pane_position_ratio(self.main_pane, self.main_split_ratio, minimum=360)
        return False

    def _apply_main_split_ratio(self) -> bool:
        self._set_pane_position_ratio(self.main_pane, self.main_split_ratio, minimum=360)
        return False

    def _set_details_default_split(self) -> bool:
        self.details_split_ratio = 0.25
        self._set_pane_position_ratio(self.details_pane, self.details_split_ratio)
        return False

    def _apply_details_split_ratio(self) -> bool:
        self._set_pane_position_ratio(self.details_pane, self.details_split_ratio)
        return False

    def _apply_saved_split_ratios(self) -> bool:
        self._initial_pane_layout_source_id = None
        self._set_pane_position_ratio(self.main_pane, self.main_split_ratio, minimum=360)
        self._set_pane_position_ratio(self.details_pane, self.details_split_ratio)
        self._set_pane_position_ratio(self.actions_pane, self.actions_split_ratio)
        self._pane_layout_ready = True
        self._on_actions_pane_position_changed(self.actions_pane, None)
        return False

    def _schedule_initial_pane_layout(self) -> None:
        if self._pane_layout_ready:
            return
        source_id = getattr(self, "_initial_pane_layout_source_id", None)
        if source_id is not None:
            GLib.source_remove(source_id)
        self._initial_pane_layout_source_id = GLib.idle_add(self._apply_saved_split_ratios)

    def _set_actions_default_split(self) -> bool:
        self.actions_split_ratio = 0.38
        self._set_pane_position_ratio(self.actions_pane, self.actions_split_ratio)
        return False

    def _set_pane_position_ratio(self, pane: Gtk.Paned, ratio: float, *, minimum: int = 1) -> None:
        size = _pane_allocated_size(pane)
        if size <= 1:
            return
        position = max(minimum, int(round(size * ratio)))
        self._updating_pane_positions = True
        try:
            pane.set_position(position)
        finally:
            self._updating_pane_positions = False

    def _schedule_pane_settings_save(self) -> None:
        source_id = getattr(self, "_pane_settings_save_source_id", None)
        if source_id is not None:
            GLib.source_remove(source_id)
        self._pane_settings_save_source_id = GLib.timeout_add(350, self._save_pane_settings)

    def _save_pane_settings(self) -> bool:
        self._pane_settings_save_source_id = None
        if not getattr(self, "_closing", False):
            self._save_settings()
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

    def _on_window_mapped(self, *_args: object) -> bool:
        self._schedule_initial_pane_layout()
        return False

    def _on_window_configure(self, _window: Gtk.Window, event: Gdk.EventConfigure) -> bool:
        if event.width > 1 and event.height > 1:
            self.last_window_width = event.width
            self.last_window_height = event.height
            self.last_window_x = event.x
            self.last_window_y = event.y
            self._schedule_initial_pane_layout()
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
        button.task-action-play-button {{
            padding-left: 2px;
            padding-right: 2px;
            min-width: 20px;
        }}
        button.task-action-label-button,
        button.task-action-play-button {{
            outline-width: 0;
            outline-offset: 0;
        }}
        button.task-action-label-button:focus,
        button.task-action-play-button:focus {{
            outline-style: none;
            outline-width: 0;
        }}
        button.task-action-selected {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
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
            self._set_markdown(self.description_view, _task_goal_slot_markdown(self.selected_task.path))
            self._render_task_context_details()
        for session in self.terminal_sessions.values():
            self._apply_terminal_theme(session.terminal)
        self._refresh_task_row_styles()

    def _on_window_delete_event(self, *_args: object) -> bool:
        return not self._confirm_close_with_running_agents()

    def close(self, *_args: object) -> None:
        if self._closing:
            return
        self._closing = True
        source_id = getattr(self, "_pane_settings_save_source_id", None)
        if source_id is not None:
            GLib.source_remove(source_id)
            self._pane_settings_save_source_id = None
        source_id = getattr(self, "_initial_pane_layout_source_id", None)
        if source_id is not None:
            GLib.source_remove(source_id)
            self._initial_pane_layout_source_id = None
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
                "inject_task_context_prompt": self.inject_task_context_prompt,
                "task_dictionary_auto_discovery": self.task_dictionary_auto_discovery,
                "task_dictionary_min_occurrences": self.task_dictionary_min_occurrences,
                "task_dictionary_min_saving": self.task_dictionary_min_saving,
                "task_dictionary_min_term_length": self.task_dictionary_min_term_length,
                "task_dictionary_max_term_words": self.task_dictionary_max_term_words,
                "task_dictionary_strip_articles": self.task_dictionary_strip_articles,
                "task_dictionary_preview_text": self.task_dictionary_preview_text,
                "geometry": (
                    f"{self.last_window_width}x{self.last_window_height}"
                    f"+{self.last_window_x}+{self.last_window_y}"
                ),
                "main_split_ratio": self.main_split_ratio,
                "details_split_ratio": self.details_split_ratio,
                "actions_split_ratio": self.actions_split_ratio,
            }
        )


def _is_pane_separator_event(pane: Gtk.Paned, event: Gdk.EventButton, tolerance: int = 8) -> bool:
    get_handle_window = getattr(pane, "get_handle_window", None)
    if callable(get_handle_window):
        try:
            handle_window = get_handle_window()
            if handle_window is not None and event.window == handle_window:
                return True
        except (AttributeError, TypeError):
            pass
    position = pane.get_position()
    if pane.get_orientation() == Gtk.Orientation.HORIZONTAL:
        return abs(event.x - position) <= tolerance
    return abs(event.y - position) <= tolerance


def _pane_allocated_size(pane: Gtk.Paned) -> int:
    if pane.get_orientation() == Gtk.Orientation.HORIZONTAL:
        return pane.get_allocated_width()
    return pane.get_allocated_height()


def _pane_position_ratio(pane: Gtk.Paned) -> float:
    size = _pane_allocated_size(pane)
    if size <= 1:
        return 0.5
    return max(0.05, min(0.95, pane.get_position() / size))


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


def _reorder_box_children(box: Gtk.Widget) -> list[Gtk.Widget]:
    reorder_children = getattr(box, "reorder_children", None)
    if callable(reorder_children):
        return list(reorder_children())
    if isinstance(box, Gtk.Container):
        return list(box.get_children())
    return []


def _reorder_child_id(child: Gtk.Widget) -> str:
    item_id = getattr(child, "_task_reorder_id", "")
    if isinstance(item_id, str) and item_id:
        return item_id
    get_child = getattr(child, "get_child", None)
    if callable(get_child):
        inner_id = getattr(get_child(), "_task_reorder_id", "")
        if isinstance(inner_id, str):
            return inner_id
    return ""


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


def _context_entry_reference_at_iter(buffer: Gtk.TextBuffer, cursor_iter: Gtk.TextIter) -> int | None:
    text = _text_buffer_text(buffer)
    offset = cursor_iter.get_offset()
    for match in re.finditer(r"(?<![\w/-])#(\d+)\b", text):
        if match.start() <= offset <= match.end():
            return int(match.group(1))
    return None


def _scrolled(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
    scrolled = Gtk.ScrolledWindow()
    scrolled.add(widget)
    return scrolled


def _dictionary_preview_text(text: str, preview: DictionaryPreview) -> str:
    dictionary_lines = [f"{entry.token} = {entry.value}" for entry in preview.dictionary]
    dictionary_body = "\n".join(dictionary_lines)
    dictionary_text = dictionary_body if dictionary_body else "(empty)"
    return (
        "Dictionary\n"
        f"{dictionary_text}\n\n"
        "Encoded text\n"
        f"{preview.encoded_text}"
    )


def _dictionary_preview_metrics_text(text: str, preview: DictionaryPreview) -> str:
    dictionary_body = "\n".join(f"{entry.token} = {entry.value}" for entry in preview.dictionary)
    dictionary_chars = len(dictionary_body)
    encoded_total_chars = len(preview.encoded_text) + dictionary_chars
    char_saving = len(text) - encoded_total_chars
    encoded_total_tokens = preview.encoded_tokens + preview.dictionary_tokens
    token_saving = preview.original_tokens - encoded_total_tokens
    return (
        f"Original chars: {len(text)}\n"
        f"Encoded chars: {encoded_total_chars}\n"
        f"Char saving: {char_saving}\n"
        f"% saving: {_dictionary_preview_percent(char_saving, len(text))}\n"
        f"Original tokens: {preview.original_tokens}\n"
        f"Encoded tokens: {encoded_total_tokens}\n"
        f"Saving tokens: {token_saving}\n"
        f"% saving: {_dictionary_preview_percent(token_saving, preview.original_tokens)}"
    )


def _dictionary_preview_percent(saving: int, original: int) -> str:
    if original <= 0:
        return "0.0%"
    return f"{saving / original * 100:.1f}%"




def ai_agent_task_context_message(task: TaskSummary, workspace: Path, language: str = "en") -> str:
    language_instruction = CODEX_LANGUAGE_INSTRUCTIONS.get(language, CODEX_LANGUAGE_INSTRUCTIONS["en"]) if language else ""
    settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
    return ai_agent_task_context_prompt(
        task,
        workspace,
        language_instruction,
        inject_task_context=settings.inject_task_context_prompt,
    )


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
    combo.remove_all()
    for index, choice in enumerate(choices):
        combo.append_text(choice)
        if choice == current:
            active_index = index
    if choices:
        combo.set_active(active_index)


def _rgba(color: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    rgba.parse(color)
    return rgba


def _agent_workspace_icon_path() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "agent-workspace.svg"


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

    reset_workspace_pending_iterations(workspace)
    gui = WorkspaceGtkGui(workspace)
    gui.window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
