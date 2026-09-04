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
import time

from agent_tools.agent_workspace.components.desktop_integration.api.gtk_bootstrap import gtk_cursor_size
from agent_tools.agent_workspace.components.desktop_integration.api.gtk_bootstrap import gtk_cursor_theme
from agent_tools.agent_workspace.components.desktop_integration.api.gtk_bootstrap import sync_gtk_environment


sync_gtk_environment()

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

from ...artifacts.api import ArtifactEntry
from ...artifacts.api import artifact_context_action as _artifact_context_action
from ...artifacts.api import artifact_delete_paths as _artifact_delete_paths
from ...artifacts.api import artifact_group as _artifact_group
from ...artifacts.api import artifact_group_folder as _artifact_group_folder
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
from ...harness_adapter.api import AgentType
from ...harness_adapter.api import HarnessDebugEvent
from ...harness_adapter.api import HarnessStatusEvent
from ...harness_adapter.api import WorkspaceIpcEvent
from ...harness_adapter.api import WorkspaceIpcServer
from ...harness_adapter.api import clear_harness_debug_events
from ...harness_adapter.api import load_harness_debug_events
from ...harness_adapter.api import load_latest_harness_debug_events_by_task
from ...harness_adapter.api import record_harness_status
from ...harness_adapter.api import start_workspace_ipc_server
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
from ...agent_status.api import agent_output_reports_missing_session
from ...agent_status.api import agent_status_tooltip_text
from ...agent_status.api import AGENT_PROMPT_MARKER
from ...agent_status.api import AGENT_RUNNING_READY_MARKER
from ...agent_status.api import AGENT_TOOL_MARKER
from ...agent_status.api import session_is_agent
from ...agent_status.api import session_is_running_agent
from ...agent_status.api import session_marks_task_pending_permission
from ...agent_status.api import session_marks_task_running_agent
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
from ...process_runtime.api import abort_agent_workspace_with_stack_dump
from ...process_runtime.api import acquire_agent_workspace_lock
from ...settings.api import agent_executable
from ...settings.api import agent_install_command
from ...settings.api import agent_label
from ...settings.api import ai_agent_model_settings
from ...settings.api import agent_workspace_runtime_settings
from ...settings.api import apply_agent_workspace_mcp_trust
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
from ...settings.api import run_agent_workspace_update_check
from ...settings.api import run_agent_workspace_update
from ...settings.api import save_agent_workspace_settings
from ...settings.api import remember_agent_workspace
from ...settings.api import workspace_mcp_configurable_tool_groups
from ...settings.api import workspace_mcp_enabled_groups_for_runtime
from ...settings.api import workspace_mcp_required_tool_groups
from ...settings.api import workspace_mcp_tool_group_tooltip
from ...settings.api import workspace_mcp_tool_groups
from ...workspace_config.api import ensure_agent_workspace
from ...workspace_config.api import resolve_agent_workspace_startup
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
from .codex_terminal_mouse import CodexTerminalMouseStateMachine
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

# X11 core event type codes. Gdk.Window.add_filter sees native events before
# they are translated to populated Gdk.Event instances.
_X11_MOTION_NOTIFY = 6
_X11_ENTER_NOTIFY = 7
_X11_LEAVE_NOTIFY = 8
_X11_PASSIVE_POINTER_EVENT_TYPES = {
    _X11_MOTION_NOTIFY,
    _X11_ENTER_NOTIFY,
    _X11_LEAVE_NOTIFY,
}

AGENT_RESTORE_OUTPUT_CHECK_MS = 1000
AGENT_RESTORE_OUTPUT_CHECK_WINDOW_SECONDS = 12.0
TASK_CONTEXT_DEFAULT_STATUS_FILTER = ("active",)


def _codex_executable() -> str:
    return agent_executable("codex") or "codex"


def _claude_executable() -> str:
    return agent_executable("claude") or "claude"


def _apply_mcp_trusted_check_toggle(
    check: Gtk.CheckButton,
    confirmed_mcp_trusted: bool,
    confirm_enable: Callable[[], bool],
    confirm_disable: Callable[[], bool],
    apply_trust: Callable[[bool], None],
) -> bool:
    requested_mcp_trusted = check.get_active()
    if requested_mcp_trusted == confirmed_mcp_trusted:
        return confirmed_mcp_trusted
    confirm = confirm_enable if requested_mcp_trusted else confirm_disable
    if confirm():
        try:
            apply_trust(requested_mcp_trusted)
        except OSError:
            check.set_active(confirmed_mcp_trusted)
            raise
        return requested_mcp_trusted
    check.set_active(confirmed_mcp_trusted)
    return confirmed_mcp_trusted


@dataclass
class TerminalSession:
    session_id: int
    task_path: Path
    kind: str
    terminal: Vte.Terminal
    page: Gtk.Widget
    terminal_mouse: CodexTerminalMouseStateMachine | None = None
    child_pid: int | None = None
    permission_pending: bool = False
    exited: bool = False
    busy: bool = False
    run_id: str | None = None
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
        self.task_action_reflow_width: int | None = None
        self.task_action_reflow_layout: tuple[int, tuple[tuple[str, ...], ...]] | None = None
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
        self._closing = False
        self.hover_suppressed_widget_ids: set[int] = set()
        self.codex_terminal_window_filters: dict[int, list[tuple[object, object]]] = {}
        self.profiling_enabled = False
        self.profiling_counts: dict[tuple[str, str], int] = {}
        self.profiling_draw_area: dict[str, float] = {}
        self.profiling_previous_draw_area: dict[str, float] = {}
        self.profiling_previous_counts: dict[tuple[str, str], int] = {}
        self.profiling_allocations: dict[str, tuple[int, int]] = {}
        self.profiling_output_view: Gtk.TextView | None = None
        self.profiling_refresh_source_id: int | None = None
        self.profiling_paused_for_settings = False
        self.settings_update_running = False
        self.harness_debug_snapshot_signature: tuple[int, int] | None = None
        self.harness_debug_latest_by_task: dict[Path, HarnessDebugEvent] = {}
        self.workspace_ipc_server: WorkspaceIpcServer | None = None
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
        self.codex_animations_enabled = settings.codex_animations_enabled
        self.claude_animations_enabled = settings.claude_animations_enabled
        self.limited_bash_output_tokens = settings.limited_bash_output_tokens
        self.limited_bash_head_tokens = settings.limited_bash_head_tokens
        self.limited_bash_tail_tokens = settings.limited_bash_tail_tokens
        self.limited_bash_heartbeat_seconds = settings.limited_bash_heartbeat_seconds
        self.limited_bash_heartbeat_tokens = settings.limited_bash_heartbeat_tokens
        self.system_prompt = settings.system_prompt
        self.inject_task_context_prompt = settings.inject_task_context_prompt
        self.mcp_enabled_groups = settings.mcp_enabled_groups
        self.mcp_trusted = settings.mcp_trusted
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
        raw_settings = load_agent_workspace_settings()
        recent_workspaces = raw_settings.get("recent_workspaces")
        self.recent_workspaces = [
            item for item in recent_workspaces if isinstance(item, str)
        ] if isinstance(recent_workspaces, list) else [str(self.workspace)]
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
        self.ai_debug_page: Gtk.Widget | None = None
        self.ai_debug_store: Gtk.ListStore | None = None
        self.ai_debug_tree: Gtk.TreeView | None = None
        self.ai_debug_tab_label: Gtk.Label | None = None
        self.ai_debug_columns: dict[str, Gtk.TreeViewColumn] = {}
        self.ai_debug_last_signature: tuple[object, ...] = ()
        self.ai_debug_refresh_source_id: int | None = None
        self.actions_controls_box: Gtk.Box | None = None
        self.workspace_actions_box: Gtk.Box | None = None
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
        self.workspace_ipc_server = start_workspace_ipc_server(self.workspace, self._on_workspace_ipc_event)
        self._apply_window_geometry()
        self._build_ui()
        self._apply_css()
        self.refresh_tasks()
        self.ai_debug_refresh_source_id = GLib.timeout_add_seconds(1, self._refresh_ai_debug_if_visible)
        GLib.timeout_add_seconds(1, self._animate_agent_status)

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(root)
        self._profile_widget("window", self.window)
        self._profile_widget("root", root)
        self._disable_codex_console_boundary_tracking(self.window)
        self._disable_codex_console_boundary_tracking(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_border_width(6)
        root.pack_start(toolbar, False, False, 0)
        self._profile_widget("toolbar", toolbar)
        workspace_menu_button = Gtk.MenuButton(label=self._tr("workspace_menu"))
        workspace_menu_popover = Gtk.Popover()
        workspace_menu_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        workspace_menu_content.set_border_width(8)
        open_workspace_button = self._button("open_workspace_action", self.open_workspace_dialog)
        create_workspace_button = self._button("create_workspace_action", self.create_workspace_dialog)
        workspace_menu_content.pack_start(open_workspace_button, False, False, 0)
        workspace_menu_content.pack_start(create_workspace_button, False, False, 0)
        workspace_menu_popover.add(workspace_menu_content)
        workspace_menu_content.show_all()
        workspace_menu_button.set_popover(workspace_menu_popover)
        self._disable_action_hover_tracking(workspace_menu_button)
        self.label_widgets["workspace_menu"] = workspace_menu_button
        toolbar.pack_start(workspace_menu_button, False, False, 0)
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
        self._disable_codex_console_boundary_tracking(main)
        root.pack_start(main, True, True, 0)

        self.task_store = Gtk.ListStore(str, str, object, str, bool, str, bool, int, bool)
        self.task_view = Gtk.TreeView(model=self.task_store)
        self.task_view.set_enable_search(False)
        self.task_view.set_hover_selection(False)
        self.task_view.set_hover_expand(False)
        self.task_view.set_rubber_banding(False)
        self._disable_tree_hover_tracking(self.task_view)
        status_renderer = Gtk.CellRendererText()
        status_renderer.set_property("xalign", 0.5)
        status_renderer.set_property("font-desc", Pango.FontDescription(f"DejaVu Sans Mono {self.text_font_size}"))
        status_renderer.set_fixed_height_from_font(1)
        self.task_status_header = Gtk.Label(label=self._tr("task_agent_status_column"))
        self.task_status_header.show()
        self.task_status_column = Gtk.TreeViewColumn("", status_renderer, text=0)
        self.task_status_column.set_widget(self.task_status_header)
        self.task_status_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.task_status_column.set_fixed_width(92)
        self.task_view.append_column(self.task_status_column)
        task_renderer = Gtk.CellRendererText()
        task_renderer.set_fixed_height_from_font(1)
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
        self.task_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.task_view.connect("button-press-event", self._on_task_view_button_press)
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_overlay_scrolling(False)
        task_scroll.set_min_content_width(360)
        task_scroll.add(self.task_view)
        main.pack1(task_scroll, resize=False, shrink=False)
        self._profile_widget("main-pane", main)
        self._profile_widget("task-scroll", task_scroll)
        self._profile_widget("task-scroll-vbar", task_scroll.get_vscrollbar())
        self._profile_widget("task-view", self.task_view)

        self.notebook = Gtk.Notebook()
        main.pack2(self.notebook, resize=True, shrink=False)
        self._profile_widget("main-notebook", self.notebook)
        self._add_actions_tab()
        self._add_details_tab()
        self._add_artifacts_tab()
        self.active_main_page = self.actions_page
        self.notebook.connect("switch-page", self._on_main_notebook_switch_page)

    def _add_details_tab(self) -> None:
        context_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        context_box.set_border_width(4)
        self.details_page = context_box
        self.context_view = _text_view(self.text_font_size, editable=False)
        self.context_view.connect("button-release-event", self._on_context_view_button_release)
        self._profile_widget("details-pane", context_box)
        self._profile_widget("context-view", self.context_view)
        context_box.pack_start(self._task_context_filter_bar(), False, False, 0)
        context_box.pack_start(_scrolled(self.context_view), True, True, 0)
        self.details_tab_label = Gtk.Label(label=self._tr("context_journal"))
        self.notebook.append_page(context_box, self.details_tab_label)

    def _task_context_filter_bar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.get_style_context().add_class("task-context-filter-bar")
        self.task_context_encoded_check = Gtk.CheckButton(label=self._tr("context_view_encoded"))
        self.task_context_encoded_check.connect("toggled", self._on_task_context_filter_changed)
        self._disable_action_hover_tracking(self.task_context_encoded_check)
        box.pack_start(self.task_context_encoded_check, False, False, 0)
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
        self._disable_action_hover_tracking(button)
        self._disable_action_hover_tracking(all_check)
        self.task_context_filter_all_checks[group] = all_check
        content.pack_start(all_check, False, False, 0)
        for value in values:
            check = Gtk.CheckButton(label=value)
            check.set_active(value in self._task_context_default_group_values(group, values))
            check.connect("toggled", self._on_task_context_item_toggled, group, target)
            self._disable_action_hover_tracking(check)
            target[value] = check
            content.pack_start(check, False, False, 0)
        self._update_task_context_all_check(group, target)
        popover.add(content)
        content.show_all()
        button.set_popover(popover)
        return button

    def _add_artifacts_tab(self) -> None:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        page.set_border_width(3)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        page.pack_start(controls, False, False, 0)
        self.artifact_extension_filter_value = "all"
        self.artifact_filter_was_active = False
        self.artifact_extension_filter = Gtk.Button(label=self._tr("artifact_extension_all"))
        self.artifact_extension_filter.connect("clicked", self._on_artifact_extension_filter_clicked)
        self._disable_action_hover_tracking(self.artifact_extension_filter)
        controls.pack_start(self.artifact_extension_filter, False, False, 0)
        self.artifact_text_filter = Gtk.SearchEntry()
        self.artifact_text_filter.set_placeholder_text(self._tr("artifact_filter_placeholder"))
        self.artifact_text_filter.connect("search-changed", self._on_artifact_filter_changed)
        controls.pack_start(self.artifact_text_filter, True, True, 0)
        self.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
        self.artifact_view = Gtk.TreeView(model=self.artifact_store)
        self.artifact_view.set_enable_search(False)
        self.artifact_view.set_hover_selection(False)
        self.artifact_view.set_hover_expand(False)
        self.artifact_view.set_rubber_banding(False)
        self._disable_tree_hover_tracking(self.artifact_view)
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
        scrolled.set_overlay_scrolling(False)
        scrolled.add(self.artifact_view)
        page.pack_start(scrolled, True, True, 0)
        self.artifacts_page = page
        self.artifacts_scrolled = scrolled
        self._profile_widget("artifacts-page", page)
        self._profile_widget("artifacts-page-vbar", scrolled.get_vscrollbar())
        self._profile_widget("artifact-view", self.artifact_view)
        self.artifacts_tab_label = Gtk.Label(label=self._tr("artifacts"))
        self.notebook.append_page(page, self.artifacts_tab_label)

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
        self._profile_widget("actions-page", box)
        self._profile_widget("actions-pane", actions_pane)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        controls_box.set_border_width(0)
        self.actions_controls_box = controls_box
        controls_scrolled = Gtk.ScrolledWindow()
        controls_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        controls_scrolled.set_overlay_scrolling(False)
        controls_scrolled.add(controls_box)
        actions_pane.pack1(controls_scrolled, resize=False, shrink=True)
        actions_pane.connect("notify::position", self._on_actions_pane_position_changed)
        self._profile_widget("actions-controls-scroll", controls_scrolled)
        self._profile_widget("actions-controls", controls_box)

        self.workspace_actions_box = self._add_framed_action_group(
            controls_box,
            self._s("actions.workspace_group"),
            expand=False,
        )
        self._profile_widget("workspace-actions-box", self.workspace_actions_box)

        self.task_actions_box = self._add_framed_action_group(controls_box, self._s("actions.group"), expand=False)
        self.task_actions_box.connect("size-allocate", self._on_task_actions_box_size_allocate)
        self._connect_task_reorder_box(self.task_actions_box, "action")
        self._profile_widget("task-actions-box", self.task_actions_box)

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
        self.console_notebook.get_style_context().add_class("console-notebook")
        self.console_notebook.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.console_notebook.connect("button-press-event", self._on_console_notebook_button_press)
        self.console_notebook.connect("switch-page", self._on_console_notebook_switch_page)
        actions_pane.pack2(self.console_notebook, resize=True, shrink=False)
        self._profile_widget("console-notebook", self.console_notebook)
        self._on_actions_pane_position_changed(actions_pane, None)
        self._ensure_ai_agent_console_page()
        self._ensure_ai_debug_page()

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

    def _ensure_ai_debug_page(self) -> None:
        if not hasattr(self, "ai_debug_page"):
            self.ai_debug_page = None
        if self.ai_debug_page is None:
            self.ai_debug_store = Gtk.ListStore(str, str, str, str, str, str, str, str)
            self.ai_debug_tree = Gtk.TreeView(model=self.ai_debug_store)
            self.ai_debug_tree.set_enable_search(False)
            self.ai_debug_tree.connect("row-activated", self._on_ai_debug_row_activated)
            self._profile_widget("ai-debug-tree", self.ai_debug_tree)
            self.ai_debug_columns = {}
            for key, column_index, width in (
                ("ai_debug_column_time", 1, 180),
                ("", 2, 38),
                ("ai_debug_column_type", 3, 80),
                ("ai_debug_column_hook", 4, 150),
                ("ai_debug_column_tool", 5, 120),
                ("ai_debug_column_result", 6, 90),
            ):
                renderer = Gtk.CellRendererText()
                renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
                title = self._tr(key) if key else ""
                column = Gtk.TreeViewColumn(title, renderer, text=column_index)
                column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                column.set_fixed_width(width)
                self.ai_debug_tree.append_column(column)
                if key:
                    self.ai_debug_columns[key] = column
            content_renderer = Gtk.CellRendererText()
            content_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            content_column = Gtk.TreeViewColumn(self._tr("ai_debug_column_content"), content_renderer, text=7)
            content_column.set_expand(True)
            self.ai_debug_tree.append_column(content_column)
            self.ai_debug_columns["ai_debug_column_content"] = content_column
            self.ai_debug_page = _scrolled(self.ai_debug_tree)
            self._profile_widget("ai-debug-page", self.ai_debug_page)
        if self.console_notebook.page_num(self.ai_debug_page) < 0:
            self.ai_debug_tab_label = Gtk.Label(label=self._tr("ai_debug_tab"))
            self.console_notebook.insert_page(self.ai_debug_page, self.ai_debug_tab_label, 1)
        self.ai_debug_page.show_all()

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
        if self._ai_debug_tab_active():
            self._refresh_ai_debug()
        if self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)
        else:
            self.artifact_store.clear()
        if self._actions_tab_active():
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
        ordered_slots = [slot for slot in slots if slot.category == "goal"]
        ordered_slots.extend(slot for slot in slots if slot.category != "goal")
        body = _render_task_context_slots(
            ordered_slots,
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
            self._disable_action_hover_tracking(all_check)
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
            self._disable_action_hover_tracking(check)
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
        self._disable_action_hover_tracking(clear_button)
        self._disable_action_hover_tracking(ok_button)
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
        had_rows = self.artifact_store.iter_n_children(None) > 0
        expanded_groups = self._artifact_expanded_group_ids()
        focus_identity = self._artifact_focus_identity()
        scroll_value = self._artifact_scroll_value()
        entries = _task_artifact_entries(
            task,
            sort_column=self.artifact_sort_column,
            descending=self.artifact_sort_descending,
        )
        self._refresh_artifact_extension_filter(task, entries)
        filter_active = self._artifact_filter_active()
        filter_was_cleared = getattr(self, "artifact_filter_was_active", False) and not filter_active
        self.artifact_filter_was_active = filter_active
        self.artifact_store.clear()
        filtered_group_counts = dict.fromkeys(("logs", "diagrams", "diff_reports", "artifacts"), 0)
        groups = {
            "logs": self.artifact_store.append(None, [self._tr("logs"), "", "logs", True, ""]),
            "diagrams": self.artifact_store.append(None, [self._tr("diagrams"), "", "diagrams", True, ""]),
            "diff_reports": self.artifact_store.append(None, [self._tr("diff_reports"), "", "diff_reports", True, ""]),
            "artifacts": self.artifact_store.append(None, [self._tr("other_artifacts"), "", "artifacts", True, ""]),
        }
        for entry in self._filtered_artifact_entries(task, entries):
            filtered_group_counts[entry.group] += 1
            rel_path = _artifact_relative_label(task, entry.path)
            self.artifact_store.append(
                groups[entry.group],
                [entry.path.name, rel_path, entry.path, False, _artifact_updated_label(entry.updated)],
            )
        if filter_active:
            self._expand_artifact_groups_with_matches(groups, filtered_group_counts)
        elif filter_was_cleared:
            self.artifact_view.expand_all()
        elif had_rows:
            self._restore_artifact_expanded_groups(groups, expanded_groups)
        else:
            self.artifact_view.expand_all()
        self._restore_artifact_tree_position(focus_identity, scroll_value)

    def _filtered_artifact_entries(self, task: TaskSummary, entries: list[ArtifactEntry]) -> list[ArtifactEntry]:
        extension = self._artifact_extension_filter_value()
        if extension is not None:
            entries = [entry for entry in entries if entry.path.suffix.casefold() == extension]
        query = self._artifact_text_filter_query()
        if query:
            entries = [
                entry
                for entry in entries
                if query in entry.path.name.casefold()
                or query in _artifact_relative_label(task, entry.path).casefold()
            ]
        return entries

    def _artifact_text_filter_query(self) -> str:
        text_filter = getattr(self, "artifact_text_filter", None)
        if text_filter is None:
            return ""
        return text_filter.get_text().strip().casefold()

    def _artifact_extension_filter_value(self) -> str | None:
        active_id = getattr(self, "artifact_extension_filter_value", "all")
        if active_id == "all":
            return None
        return active_id

    def _artifact_filter_active(self) -> bool:
        return bool(self._artifact_text_filter_query()) or self._artifact_extension_filter_value() is not None

    def _refresh_artifact_extension_filter(self, task: TaskSummary, entries: list[ArtifactEntry]) -> None:
        extension_filter = getattr(self, "artifact_extension_filter", None)
        if extension_filter is None:
            return
        current = self._artifact_extension_filter_value()
        extensions = sorted(
            {
                entry.path.suffix.casefold()
                for entry in entries
                if entry.path.suffix
            }
        )
        if current not in extensions:
            current = None
            self.artifact_extension_filter_value = "all"
        label = current or self._tr("artifact_extension_all")
        extension_filter.set_label(label)
        if not isinstance(extension_filter, Gtk.Widget):
            self.artifact_extension_filter_menu = list(extensions)
            return
        menu = Gtk.Menu()
        group: list[Gtk.RadioMenuItem] = []
        all_item = Gtk.RadioMenuItem.new_with_label(group, self._tr("artifact_extension_all"))
        group = all_item.get_group()
        all_item.set_active(current is None)
        all_item.connect("activate", self._on_artifact_extension_selected, "all")
        menu.append(all_item)
        for extension in extensions:
            item = Gtk.RadioMenuItem.new_with_label(group, extension)
            item.set_active(extension == current)
            item.connect("activate", self._on_artifact_extension_selected, extension)
            menu.append(item)
        menu.show_all()
        self.artifact_extension_filter_menu = menu

    def _on_artifact_extension_filter_clicked(self, button: Gtk.Button) -> None:
        menu = getattr(self, "artifact_extension_filter_menu", None)
        if menu is None and self.selected_task is not None:
            entries = _task_artifact_entries(
                self.selected_task,
                sort_column=self.artifact_sort_column,
                descending=self.artifact_sort_descending,
            )
            self._refresh_artifact_extension_filter(self.selected_task, entries)
            menu = getattr(self, "artifact_extension_filter_menu", None)
        if menu is not None:
            menu.popup_at_widget(button, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def _on_artifact_extension_selected(self, item: Gtk.RadioMenuItem, extension: str) -> None:
        if not item.get_active():
            return
        if self.artifact_extension_filter_value == extension:
            return
        self.artifact_extension_filter_value = extension
        if self.selected_task is not None and self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)

    def _on_artifact_filter_changed(self, *_args: object) -> None:
        if self.selected_task is not None and self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)

    def _artifact_scroll_adjustment(self) -> Gtk.Adjustment | None:
        scrolled = getattr(self, "artifacts_scrolled", None)
        if scrolled is None:
            return None
        return scrolled.get_vadjustment()

    def _artifact_scroll_value(self) -> float | None:
        vadjustment = self._artifact_scroll_adjustment()
        if vadjustment is None:
            return None
        return vadjustment.get_value()

    def _artifact_focus_identity(self) -> tuple[str, str] | None:
        tree_path, _column = self.artifact_view.get_cursor()
        if tree_path is None:
            return None
        try:
            row_iter = self.artifact_store.get_iter(tree_path)
        except (TypeError, ValueError):
            return None
        return self._artifact_row_identity(row_iter)

    def _artifact_row_identity(self, row_iter: Gtk.TreeIter) -> tuple[str, str] | None:
        is_group = bool(self.artifact_store[row_iter][3])
        value = self.artifact_store[row_iter][2]
        if is_group and isinstance(value, str):
            return ("group", value)
        if isinstance(value, Path):
            return ("artifact", str(value))
        return None

    def _artifact_expanded_group_ids(self) -> set[str]:
        expanded: set[str] = set()
        row_iter = self.artifact_store.get_iter_first()
        while row_iter is not None:
            value = self.artifact_store[row_iter][2]
            if isinstance(value, str) and self.artifact_view.row_expanded(self.artifact_store.get_path(row_iter)):
                expanded.add(value)
            row_iter = self.artifact_store.iter_next(row_iter)
        return expanded

    def _restore_artifact_expanded_groups(
        self,
        groups: dict[str, Gtk.TreeIter],
        expanded_groups: set[str],
    ) -> None:
        for group, row_iter in groups.items():
            tree_path = self.artifact_store.get_path(row_iter)
            if group in expanded_groups:
                self.artifact_view.expand_row(tree_path, False)
            else:
                self.artifact_view.collapse_row(tree_path)

    def _expand_artifact_groups_with_matches(
        self,
        groups: dict[str, Gtk.TreeIter],
        group_counts: dict[str, int],
    ) -> None:
        for group, row_iter in groups.items():
            tree_path = self.artifact_store.get_path(row_iter)
            if group_counts.get(group, 0) > 0:
                self.artifact_view.expand_row(tree_path, False)
            else:
                self.artifact_view.collapse_row(tree_path)

    def _restore_artifact_tree_position(
        self,
        focus_identity: tuple[str, str] | None,
        scroll_value: float | None,
    ) -> None:
        tree_path = self._artifact_tree_path_for_identity(focus_identity)
        if tree_path is not None:
            self.artifact_view.get_selection().select_path(tree_path)
            self.artifact_view.set_cursor(tree_path)
            self.artifact_view.scroll_to_cell(tree_path, None, False, 0.0, 0.0)
            return
        if scroll_value is not None:
            GLib.idle_add(self._restore_artifact_scroll_value, scroll_value)

    def _artifact_tree_path_for_identity(
        self,
        focus_identity: tuple[str, str] | None,
    ) -> Gtk.TreePath | None:
        if focus_identity is None:
            return None
        row_iter = self.artifact_store.get_iter_first()
        while row_iter is not None:
            tree_path = self._artifact_tree_path_for_identity_from_iter(row_iter, focus_identity)
            if tree_path is not None:
                return tree_path
            row_iter = self.artifact_store.iter_next(row_iter)
        return None

    def _artifact_tree_path_for_identity_from_iter(
        self,
        row_iter: Gtk.TreeIter,
        focus_identity: tuple[str, str],
    ) -> Gtk.TreePath | None:
        if self._artifact_row_identity(row_iter) == focus_identity:
            return self.artifact_store.get_path(row_iter)
        child_iter = self.artifact_store.iter_children(row_iter)
        while child_iter is not None:
            tree_path = self._artifact_tree_path_for_identity_from_iter(child_iter, focus_identity)
            if tree_path is not None:
                return tree_path
            child_iter = self.artifact_store.iter_next(child_iter)
        return None

    def _restore_artifact_scroll_value(self, scroll_value: float) -> bool:
        vadjustment = self._artifact_scroll_adjustment()
        if vadjustment is None:
            return False
        upper = vadjustment.get_upper()
        page_size = vadjustment.get_page_size()
        lower = vadjustment.get_lower()
        vadjustment.set_value(max(lower, min(scroll_value, upper - page_size)))
        return False

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
        if is_group and isinstance(artifact_path, str) and self.selected_task is not None:
            folder = _artifact_group_folder(self.selected_task, artifact_path)
            if folder is not None:
                open_path(folder)
            return
        if artifact_path is None:
            return
        open_artifact_path(artifact_path)

    def _on_artifact_view_button_press(self, tree: Gtk.TreeView, event: Gdk.EventButton) -> bool:
        if event.button == 1 and self._toggle_artifact_group_expander_at_pos(tree, event):
            return True
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

    def _toggle_artifact_group_expander_at_pos(self, tree: Gtk.TreeView, event: Gdk.EventButton) -> bool:
        if int(event.x) > 32:
            return False
        hit = tree.get_path_at_pos(int(event.x), int(event.y))
        if hit is None:
            return False
        tree_path, _column, _cell_x, _cell_y = hit
        row_iter = self.artifact_store.get_iter(tree_path)
        if not bool(self.artifact_store[row_iter][3]):
            return False
        if tree.row_expanded(tree_path):
            tree.collapse_row(tree_path)
        else:
            tree.expand_row(tree_path, False)
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
        self._record_profile_event("task-view", "tooltip")
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
            display_marker = AGENT_RUNNING_READY_MARKER if marker.startswith(AGENT_RUNNING_READY_MARKER) else marker
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
            ("●", self._tr("manual_status_label_waiting"), self._tr("manual_status_waiting")),
            ("Ⅱ", self._tr("manual_status_label_session"), self._tr("manual_status_session")),
            ("□", self._tr("manual_status_label_idle"), self._tr("manual_status_idle")),
            (AGENT_PROMPT_MARKER, self._tr("manual_status_label_prompt"), self._tr("manual_status_prompt")),
            (AGENT_TOOL_MARKER, self._tr("manual_status_label_tool"), self._tr("manual_status_tool")),
            ("○", self._tr("manual_status_label_interrupted"), self._tr("manual_status_interrupted")),
            ("×", self._tr("manual_status_label_external"), self._tr("manual_status_external")),
        )

    def open_task(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path)

    def open_task_dev(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path / "dev")

    def open_workspace_dialog(self, *_args: object) -> None:
        workspace = self._choose_workspace_folder("open_workspace_dialog")
        if workspace is not None:
            self._switch_workspace(workspace)

    def create_workspace_dialog(self, *_args: object) -> None:
        workspace = self._choose_workspace_folder("create_workspace_dialog")
        if workspace is not None:
            self._switch_workspace(workspace)

    def _choose_workspace_folder(self, title_key: str) -> Path | None:
        dialog = Gtk.FileChooserDialog(
            title=self._tr(title_key),
            parent=self.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        dialog.set_current_folder(str(self.workspace))
        response = dialog.run()
        filename = dialog.get_filename() if response == Gtk.ResponseType.OK else None
        dialog.destroy()
        return Path(filename).resolve() if filename else None

    def _switch_workspace(self, workspace: Path) -> bool:
        new_workspace = workspace.resolve()
        if new_workspace == self.workspace:
            return True
        if not self._confirm_close_with_running_agents():
            return False
        self._close_all_terminal_sessions()
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
            self.task_actions_monitor = None
            self.task_actions_monitor_path = None
        workspace_ipc_server = getattr(self, "workspace_ipc_server", None)
        if workspace_ipc_server is not None:
            workspace_ipc_server.close()
            self.workspace_ipc_server = None
        try:
            ensure_agent_workspace(new_workspace)
        except (OSError, ValueError) as exc:
            self._show_error(self._tr("workspace_switch_failed"), str(exc))
            self.workspace_ipc_server = start_workspace_ipc_server(self.workspace, self._on_workspace_ipc_event)
            return False
        updated_settings = remember_agent_workspace(new_workspace)
        recent_workspaces = updated_settings.get("recent_workspaces")
        self.recent_workspaces = [
            item for item in recent_workspaces if isinstance(item, str)
        ] if isinstance(recent_workspaces, list) else [str(new_workspace)]
        self.workspace = new_workspace
        self.workspace_ipc_server = start_workspace_ipc_server(self.workspace, self._on_workspace_ipc_event)
        self.task_agent_session_marker_cache.clear()
        self.harness_debug_snapshot_signature = None
        self.harness_debug_latest_by_task = {}
        self.last_active_terminal_by_task.clear()
        self.last_active_console_page_by_task.clear()
        self._clear_selected_task_view()
        self._apply_labels()
        self.refresh_tasks()
        return True

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
        cancel_button = dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        ok_button = dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        cancel_button.connect("clicked", lambda *_: dialog.response(Gtk.ResponseType.CANCEL))
        ok_button.connect("clicked", lambda *_: dialog.response(Gtk.ResponseType.OK))
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

    def _confirm_mcp_trust_enable(self) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("settings_mcp_trust_confirm_title"),
        )
        dialog.format_secondary_text(self._tr("settings_mcp_trust_confirm_body"))
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("settings_mcp_trust_confirm_button"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def _confirm_mcp_trust_disable(self) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=self._tr("settings_mcp_trust_disable_confirm_title"),
        )
        dialog.format_secondary_text(self._tr("settings_mcp_trust_disable_confirm_body"))
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("settings_mcp_trust_disable_confirm_button"), Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

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

    def _disable_tree_hover_tracking(self, tree: Gtk.TreeView) -> None:
        tree.set_hover_selection(False)
        tree.set_hover_expand(False)
        tree.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        tree.connect("motion-notify-event", self._consume_tree_hover_event)
        tree.connect("enter-notify-event", self._consume_tree_hover_event)
        tree.connect("leave-notify-event", self._consume_tree_hover_event)

    def _consume_tree_hover_event(self, _tree: Gtk.TreeView, _event: Gdk.Event) -> bool:
        return True

    def _disable_action_hover_tracking(self, widget: Gtk.Widget) -> None:
        if not hasattr(self, "hover_suppressed_widget_ids"):
            self.hover_suppressed_widget_ids = set()
        key = id(widget)
        if key in self.hover_suppressed_widget_ids:
            return
        self.hover_suppressed_widget_ids.add(key)
        widget.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        widget.connect("event", self._consume_action_hover_event)
        widget.connect("motion-notify-event", self._consume_action_hover_event)
        widget.connect("enter-notify-event", self._consume_action_hover_event)
        widget.connect("leave-notify-event", self._consume_action_hover_event)

    def _disable_button_hover_tracking_recursive(self, widget: Gtk.Widget) -> None:
        if isinstance(widget, (Gtk.Button, Gtk.SpinButton)):
            self._disable_action_hover_tracking(widget)
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                self._disable_button_hover_tracking_recursive(child)

    def _consume_action_hover_event(self, _widget: Gtk.Widget, event: Gdk.Event) -> bool:
        return getattr(event, "type", None) in {
            Gdk.EventType.MOTION_NOTIFY,
            Gdk.EventType.ENTER_NOTIFY,
            Gdk.EventType.LEAVE_NOTIFY,
        }

    def _disable_terminal_passive_pointer_tracking(self, widget: Gtk.Widget) -> None:
        widget.connect("event", self._consume_terminal_passive_pointer_event)
        widget.connect("motion-notify-event", self._consume_terminal_passive_pointer_event)
        widget.connect("enter-notify-event", self._consume_terminal_passive_pointer_event)
        widget.connect("leave-notify-event", self._consume_terminal_passive_pointer_event)
        widget.connect("proximity-in-event", self._consume_terminal_passive_pointer_event)
        widget.connect("proximity-out-event", self._consume_terminal_passive_pointer_event)

    def _consume_terminal_passive_pointer_event(self, _widget: Gtk.Widget, event: Gdk.Event) -> bool:
        if not self._is_passive_pointer_event(event):
            return False
        self._record_profile_event("codex-terminal-pointer-filter", self._gdk_event_profile_name(event))
        return True

    def _is_passive_pointer_event(self, event: Gdk.Event) -> bool:
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
        return not (int(getattr(event, "state", 0)) & int(Gdk.ModifierType.BUTTON1_MASK))

    def _gdk_event_profile_name(self, event: Gdk.Event) -> str:
        event_type = getattr(event, "type", None)
        name = getattr(event_type, "value_nick", None) or str(event_type)
        return f"drop-{name}"

    def _native_event_type(self, native_event: object) -> int | None:
        event_type = getattr(native_event, "type", None)
        if event_type is None:
            return None
        try:
            return int(event_type)
        except (TypeError, ValueError):
            return None

    def _is_native_passive_pointer_event(self, native_event: object) -> bool:
        event_type = self._native_event_type(native_event)
        return event_type in _X11_PASSIVE_POINTER_EVENT_TYPES

    def _install_codex_terminal_window_filter(self, terminal: Vte.Terminal) -> None:
        window = terminal.get_window()
        if window is None:
            return
        key = id(terminal)
        if key in self.codex_terminal_window_filters:
            return
        callback = self._filter_codex_terminal_window_event
        installed: list[tuple[object, object]] = []
        for filtered_window in self._terminal_gdk_windows(window):
            add_filter = getattr(filtered_window, "add_filter", None)
            if add_filter is None:
                continue
            try:
                add_filter(callback, None)
            except (TypeError, RuntimeError):
                continue
            installed.append((filtered_window, callback))
        if installed:
            self.codex_terminal_window_filters[key] = installed

    def _terminal_gdk_windows(self, window: object) -> list[object]:
        windows = [window]
        get_children = getattr(window, "get_children", None)
        if get_children is None:
            return windows
        try:
            children = get_children()
        except (TypeError, RuntimeError):
            return windows
        for child in children or []:
            windows.extend(self._terminal_gdk_windows(child))
        return windows

    def _remove_codex_terminal_window_filter(self, terminal: Vte.Terminal) -> None:
        filters = getattr(self, "codex_terminal_window_filters", None)
        if filters is None:
            return
        entries = filters.pop(id(terminal), None)
        if not entries:
            return
        for window, callback in entries:
            remove_filter = getattr(window, "remove_filter", None)
            if remove_filter is None:
                continue
            try:
                remove_filter(callback, None)
            except (TypeError, RuntimeError):
                pass

    def _filter_codex_terminal_window_event(self, native_event: object, event: Gdk.Event, _data: object) -> object:
        if self._is_native_passive_pointer_event(native_event):
            self._record_profile_event("codex-vte-native-filter", f"drop-x11-{self._native_event_type(native_event)}")
            return Gdk.FilterReturn.REMOVE
        if self._is_passive_pointer_event(event):
            self._record_profile_event("codex-vte-gdk-filter", self._gdk_event_profile_name(event))
            return Gdk.FilterReturn.REMOVE
        return Gdk.FilterReturn.CONTINUE

    def _disable_codex_console_boundary_tracking(self, widget: Gtk.Widget) -> None:
        widget.connect("event", self._consume_codex_console_boundary_event)
        widget.connect("motion-notify-event", self._consume_codex_console_boundary_event)
        widget.connect("enter-notify-event", self._consume_codex_console_boundary_event)
        widget.connect("leave-notify-event", self._consume_codex_console_boundary_event)
        widget.connect("proximity-in-event", self._consume_codex_console_boundary_event)
        widget.connect("proximity-out-event", self._consume_codex_console_boundary_event)

    def _consume_codex_console_boundary_event(self, widget: Gtk.Widget, event: Gdk.Event) -> bool:
        event_type = getattr(event, "type", None)
        if event_type not in {
            Gdk.EventType.MOTION_NOTIFY,
            Gdk.EventType.ENTER_NOTIFY,
            Gdk.EventType.LEAVE_NOTIFY,
            Gdk.EventType.PROXIMITY_IN,
            Gdk.EventType.PROXIMITY_OUT,
        }:
            return False
        if event_type == Gdk.EventType.MOTION_NOTIFY and int(getattr(event, "state", 0)) & int(Gdk.ModifierType.BUTTON1_MASK):
            return False
        return self._event_is_over_active_codex_console(widget, event)

    def _active_codex_terminal_session(self) -> TerminalSession | None:
        console_notebook = getattr(self, "console_notebook", None)
        if console_notebook is None:
            return None
        page_num = console_notebook.get_current_page()
        if page_num < 0:
            return None
        page = console_notebook.get_nth_page(page_num)
        session = self._session_for_page(page)
        if session is None or session.kind != "codex":
            return None
        return session

    def _event_is_over_active_codex_console(self, widget: Gtk.Widget, event: Gdk.Event) -> bool:
        session = self._active_codex_terminal_session()
        if session is None:
            return False
        if widget is session.terminal or widget is session.page:
            return True
        try:
            translated = session.page.translate_coordinates(widget, 0, 0)
        except (AttributeError, TypeError, RuntimeError):
            return False
        if translated is None:
            return False
        allocation = session.page.get_allocation()
        x = float(getattr(event, "x", -1))
        y = float(getattr(event, "y", -1))
        return translated[0] <= x < translated[0] + allocation.width and translated[1] <= y < translated[1] + allocation.height

    def _profile_widget(self, name: str, widget: Gtk.Widget) -> None:
        try:
            widget.connect("draw", self._on_profile_draw, name)
            widget.connect("size-allocate", self._on_profile_size_allocate, name)
        except (TypeError, RuntimeError):
            return

    def _on_profile_draw(self, _widget: Gtk.Widget, context: object, name: str) -> bool:
        self._record_profile_event(name, "draw")
        if self.profiling_enabled and hasattr(context, "clip_extents"):
            try:
                x1, y1, x2, y2 = context.clip_extents()
            except Exception:
                return False
            self.profiling_draw_area[name] = self.profiling_draw_area.get(name, 0.0) + max(0.0, x2 - x1) * max(0.0, y2 - y1)
        return False

    def _on_profile_size_allocate(self, _widget: Gtk.Widget, allocation: Gdk.Rectangle, name: str) -> None:
        current = (allocation.width, allocation.height)
        previous = self.profiling_allocations.get(name)
        self.profiling_allocations[name] = current
        self._record_profile_event(name, "size")
        if previous is not None and current != previous:
            self._record_profile_event(name, "resize")

    def _record_profile_event(self, name: str, event: str) -> None:
        if not getattr(self, "profiling_enabled", False) or getattr(self, "profiling_paused_for_settings", False):
            return
        key = (name, event)
        self.profiling_counts[key] = self.profiling_counts.get(key, 0) + 1

    def _set_profiling_enabled(self, enabled: bool) -> None:
        self.profiling_enabled = enabled
        self.profiling_previous_counts = dict(self.profiling_counts)
        self.profiling_previous_draw_area = dict(self.profiling_draw_area)
        if enabled and self.profiling_refresh_source_id is None:
            self.profiling_refresh_source_id = GLib.timeout_add_seconds(1, self._refresh_profiling_tick)
        elif not enabled and self.profiling_refresh_source_id is not None:
            GLib.source_remove(self.profiling_refresh_source_id)
            self.profiling_refresh_source_id = None
        self._refresh_profiling_output()

    def _clear_profiling_counts(self) -> None:
        self.profiling_counts.clear()
        self.profiling_previous_counts.clear()
        self.profiling_draw_area.clear()
        self.profiling_previous_draw_area.clear()
        self.profiling_allocations.clear()
        self._refresh_profiling_output()

    def _abort_with_stack_dump(self) -> None:
        abort_agent_workspace_with_stack_dump(self.workspace, "gtk")

    def _refresh_profiling_tick(self) -> bool:
        if self._closing or not self.profiling_enabled or self.profiling_paused_for_settings:
            self.profiling_refresh_source_id = None
            return False
        self._refresh_profiling_output()
        return True

    def _pause_profiling_for_settings(self) -> None:
        if not self.profiling_enabled:
            self.profiling_paused_for_settings = False
            return
        self.profiling_paused_for_settings = True
        if self.profiling_refresh_source_id is not None:
            GLib.source_remove(self.profiling_refresh_source_id)
            self.profiling_refresh_source_id = None

    def _resume_profiling_after_settings(self) -> None:
        if not self.profiling_paused_for_settings:
            return
        self.profiling_paused_for_settings = False
        if self.profiling_enabled and self.profiling_refresh_source_id is None:
            self.profiling_refresh_source_id = GLib.timeout_add_seconds(1, self._refresh_profiling_tick)

    def _refresh_profiling_output(self) -> None:
        view = self.profiling_output_view
        if view is None:
            return
        rows: list[tuple[int, int, int, int, int, str, str]] = []
        for (area, event), total in self.profiling_counts.items():
            previous = self.profiling_previous_counts.get((area, event), 0)
            draw_area = 0
            if event == "draw":
                draw_area = int(
                    (
                        self.profiling_draw_area.get(area, 0.0)
                        - self.profiling_previous_draw_area.get(area, 0.0)
                    )
                    / 1_000
                )
            delta = total - previous
            average_draw_area = int(draw_area / delta) if event == "draw" and delta > 0 else 0
            allocation = self.profiling_allocations.get(area, (0, 0))
            allocation_area = max(0, allocation[0]) * max(0, allocation[1])
            average_draw_percent = (
                int(round(average_draw_area * 100_000_000 / allocation_area))
                if event == "draw" and allocation_area > 0
                else 0
            )
            rows.append((delta, total, draw_area, average_draw_area, average_draw_percent, area, event))
        rows.sort(key=lambda row: (-row[0], -row[2], row[5], row[6]))
        lines = [
            f"{self._tr('settings_profiling_status')}: "
            f"{self._tr('settings_profiling_on') if self.profiling_enabled else self._tr('settings_profiling_off')}",
            "",
            f"{'last/s':>8}  {'total':>8}  {'kpx/s':>8}  {'avg-kpx':>8}  {'avg%':>6}  {'area':<28}  event",
        ]
        if rows:
            lines.extend(
                f"{delta:8d}  {total:8d}  {draw_area:8d}  {average_draw_area:8d}  "
                f"{average_draw_percent / 1000:5.1f}%  {area:<28}  {event}"
                for delta, total, draw_area, average_draw_area, average_draw_percent, area, event in rows
            )
        else:
            lines.append(self._tr("settings_profiling_empty"))
        view.get_buffer().set_text("\n".join(lines))
        self.profiling_previous_counts = dict(self.profiling_counts)
        self.profiling_previous_draw_area = dict(self.profiling_draw_area)

    def open_settings(self, *_args: object) -> None:
        self._pause_profiling_for_settings()
        dialog = Gtk.Dialog(
            title=self._tr("settings_title"),
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.set_resizable(True)
        dialog.set_default_size(820, 560)
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        content.add(notebook)
        general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        general_box.set_border_width(12)
        general_scrolled = _scrolled(general_box)
        general_scrolled.set_hexpand(True)
        general_scrolled.set_vexpand(True)
        dictionary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dictionary_box.set_border_width(12)
        dictionary_scrolled = _scrolled(dictionary_box)
        dictionary_scrolled.set_hexpand(True)
        dictionary_scrolled.set_vexpand(True)
        dictionary_grid = Gtk.Grid(column_spacing=10, row_spacing=8)
        mcp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        mcp_box.set_border_width(12)
        mcp_scrolled = _scrolled(mcp_box)
        mcp_scrolled.set_hexpand(True)
        mcp_scrolled.set_vexpand(True)
        mcp_trusted_check = Gtk.CheckButton(label=self._tr("settings_mcp_trusted"))
        mcp_trusted_check.set_active(self.mcp_trusted)
        mcp_trusted_note = Gtk.Label(label=self._tr("settings_mcp_trusted_note"))
        mcp_trusted_note.set_xalign(0)
        mcp_trusted_note.set_line_wrap(True)
        confirmed_mcp_trusted = self.mcp_trusted
        updating_mcp_trusted_check = False

        def on_mcp_trusted_toggled(check: Gtk.CheckButton) -> None:
            nonlocal confirmed_mcp_trusted, updating_mcp_trusted_check
            if updating_mcp_trusted_check:
                return
            updating_mcp_trusted_check = True
            try:
                try:
                    new_mcp_trusted = _apply_mcp_trusted_check_toggle(
                        check,
                        confirmed_mcp_trusted,
                        self._confirm_mcp_trust_enable,
                        self._confirm_mcp_trust_disable,
                        lambda trusted: apply_agent_workspace_mcp_trust(trusted=trusted),
                    )
                except OSError as error:
                    check.set_active(confirmed_mcp_trusted)
                    self._show_error(f"{self._tr('settings_mcp_trust_failed')}: {error}")
                    return
                if new_mcp_trusted != confirmed_mcp_trusted:
                    confirmed_mcp_trusted = new_mcp_trusted
                    self.mcp_trusted = confirmed_mcp_trusted
                    self._save_settings()
            finally:
                updating_mcp_trusted_check = False

        mcp_trusted_check.connect("toggled", on_mcp_trusted_toggled)
        mcp_group_checks: dict[str, Gtk.CheckButton] = {}
        mcp_groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        mcp_groups_heading = Gtk.Label()
        mcp_groups_heading.set_xalign(0)
        mcp_groups_heading.set_markup(f"<b>{GLib.markup_escape_text(self._tr('settings_mcp_tools'))}</b>")
        enabled_mcp_groups = set(self.mcp_enabled_groups)
        for group_id, fallback_label in workspace_mcp_required_tool_groups():
            label = TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(
                f"settings_mcp_group_{group_id}",
                fallback_label,
            )
            tooltip = TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(
                f"settings_mcp_group_{group_id}_tooltip",
                workspace_mcp_tool_group_tooltip(group_id),
            )
            check = Gtk.CheckButton(label=label)
            check.set_active(True)
            check.set_sensitive(False)
            check.set_tooltip_text(tooltip)
            mcp_groups_box.pack_start(check, False, False, 0)
        for group_id, fallback_label in workspace_mcp_configurable_tool_groups():
            label = TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(
                f"settings_mcp_group_{group_id}",
                fallback_label,
            )
            tooltip = TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(
                f"settings_mcp_group_{group_id}_tooltip",
                workspace_mcp_tool_group_tooltip(group_id),
            )
            check = Gtk.CheckButton(label=label)
            check.set_active(group_id in enabled_mcp_groups)
            check.set_tooltip_text(tooltip)
            mcp_group_checks[group_id] = check
            mcp_groups_box.pack_start(check, False, False, 0)
        mcp_box.pack_start(mcp_trusted_check, False, False, 0)
        mcp_box.pack_start(mcp_trusted_note, False, False, 0)
        mcp_box.pack_start(mcp_groups_heading, False, False, 0)
        mcp_box.pack_start(mcp_groups_box, False, False, 0)
        profiling_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        profiling_box.set_border_width(12)
        profiling_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        profiling_enabled = Gtk.CheckButton(label=self._tr("settings_profiling_enable"))
        profiling_enabled.set_active(self.profiling_enabled)
        profiling_clear = Gtk.Button(label=self._tr("settings_profiling_clear"))
        profiling_crash = Gtk.Button(label=self._tr("settings_profiling_crash_dump"))
        profiling_controls.pack_start(profiling_enabled, False, False, 0)
        profiling_controls.pack_start(profiling_clear, False, False, 0)
        profiling_controls.pack_start(profiling_crash, False, False, 0)
        profiling_output = _text_view(self.text_font_size, editable=False)
        profiling_output.set_monospace(True)
        profiling_output_scrolled = _scrolled(profiling_output)
        profiling_output_scrolled.set_hexpand(True)
        profiling_output_scrolled.set_vexpand(True)
        profiling_note = Gtk.Label(label=self._tr("settings_profiling_note"))
        profiling_note.set_xalign(0)
        profiling_note.set_line_wrap(True)
        profiling_box.pack_start(profiling_controls, False, False, 0)
        profiling_box.pack_start(profiling_note, False, False, 0)
        profiling_box.pack_start(profiling_output_scrolled, True, True, 0)
        text_size = Gtk.SpinButton.new_with_range(8, 28, 1)
        text_size.set_value(self.text_font_size)
        button_size = Gtk.SpinButton.new_with_range(8, 28, 1)
        button_size.set_value(self.button_font_size)
        theme_combo = Gtk.ComboBoxText()
        language_combo = Gtk.ComboBoxText()
        default_agent_combo = Gtk.ComboBoxText()
        codex_model_combo = Gtk.ComboBoxText()
        codex_reasoning_combo = Gtk.ComboBoxText()
        codex_animations_check = Gtk.CheckButton()
        codex_animations_check.set_active(self.codex_animations_enabled)
        limited_bash_head_tokens = Gtk.SpinButton.new_with_range(100, 200_000, 100)
        limited_bash_head_tokens.set_value(self.limited_bash_head_tokens)
        limited_bash_tail_tokens = Gtk.SpinButton.new_with_range(100, 200_000, 100)
        limited_bash_tail_tokens.set_value(self.limited_bash_tail_tokens)
        limited_bash_heartbeat_seconds = Gtk.SpinButton.new_with_range(1, 300, 1)
        limited_bash_heartbeat_seconds.set_value(self.limited_bash_heartbeat_seconds)
        limited_bash_heartbeat_tokens = Gtk.SpinButton.new_with_range(0, 200_000, 100)
        limited_bash_heartbeat_tokens.set_value(self.limited_bash_heartbeat_tokens)
        system_prompt_view = _text_view(self.text_font_size, editable=True)
        system_prompt_view.get_buffer().set_text(self.system_prompt)
        system_prompt_scrolled = _scrolled(system_prompt_view)
        system_prompt_scrolled.set_hexpand(True)
        system_prompt_scrolled.set_vexpand(False)
        system_prompt_scrolled.set_min_content_height(96)
        settings_update_check_button = Gtk.Button(label=self._tr("settings_check_updates"))
        settings_update_button = Gtk.Button(label=self._tr("settings_apply_update"))
        settings_update_button.set_no_show_all(True)
        settings_update_button.set_visible(False)
        settings_update_status = Gtk.Label(label=self._tr("settings_update_idle"))
        settings_update_status.set_xalign(0)
        settings_update_status.set_line_wrap(True)
        settings_update_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        settings_update_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_update_box.set_border_width(12)
        settings_update_box.set_hexpand(True)
        settings_update_box.set_vexpand(True)
        settings_update_controls.pack_start(settings_update_check_button, False, False, 0)
        settings_update_controls.pack_start(settings_update_button, False, False, 0)
        settings_update_box.pack_start(settings_update_controls, False, False, 0)
        settings_update_box.pack_start(settings_update_status, False, False, 0)
        settings_open = {"value": True}
        notebook.append_page(general_scrolled, Gtk.Label(label=self._tr("settings_dictionary_general")))
        notebook.append_page(dictionary_scrolled, Gtk.Label(label=self._tr("settings_dictionary_dictionary")))
        notebook.append_page(mcp_scrolled, Gtk.Label(label=self._tr("settings_mcp")))
        notebook.append_page(settings_update_box, Gtk.Label(label=self._tr("settings_updates")))
        notebook.append_page(profiling_box, Gtk.Label(label=self._tr("settings_profiling")))
        active_text_view: dict[str, Gtk.TextView | None] = {"view": None}

        def set_passive_text_view_active(view: Gtk.TextView, active: bool) -> None:
            view.set_can_focus(active)
            view.set_cursor_visible(active and view.get_editable())

        def deactivate_passive_text_view() -> None:
            view = active_text_view["view"]
            if view is not None:
                set_passive_text_view_active(view, False)
            active_text_view["view"] = None

        def activate_passive_text_view(view: Gtk.TextView) -> None:
            current = active_text_view["view"]
            if current is not view:
                deactivate_passive_text_view()
            active_text_view["view"] = view
            set_passive_text_view_active(view, True)
            view.grab_focus()

        def scroll_outer_settings_page(outer: Gtk.ScrolledWindow, event: Gdk.Event) -> bool:
            adjustment = outer.get_vadjustment()
            direction = getattr(event, "direction", None)
            step = adjustment.get_step_increment() or 32.0
            amount = 0.0
            if direction == Gdk.ScrollDirection.UP:
                amount = -step * 3.0
            elif direction == Gdk.ScrollDirection.DOWN:
                amount = step * 3.0
            elif direction == Gdk.ScrollDirection.SMOOTH and hasattr(event, "get_scroll_deltas"):
                _ok, _delta_x, delta_y = event.get_scroll_deltas()
                amount = float(delta_y) * step * 3.0
            if amount == 0.0:
                return False
            lower = adjustment.get_lower()
            upper = adjustment.get_upper() - adjustment.get_page_size()
            adjustment.set_value(max(lower, min(upper, adjustment.get_value() + amount)))
            return True

        def on_passive_text_button_press(view: Gtk.TextView, _event: Gdk.Event) -> bool:
            activate_passive_text_view(view)
            return False

        def on_passive_text_focus_out(view: Gtk.TextView, _event: Gdk.Event) -> bool:
            if active_text_view["view"] is view:
                deactivate_passive_text_view()
            return False

        def on_passive_text_scroll(
            _widget: Gtk.Widget,
            event: Gdk.Event,
            view: Gtk.TextView,
            outer: Gtk.ScrolledWindow,
        ) -> bool:
            if active_text_view["view"] is view:
                return False
            return scroll_outer_settings_page(outer, event)

        def register_passive_text_view(view: Gtk.TextView, scrolled: Gtk.ScrolledWindow, outer: Gtk.ScrolledWindow) -> None:
            set_passive_text_view_active(view, False)
            view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            scrolled.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            view.connect("button-press-event", on_passive_text_button_press)
            view.connect("focus-out-event", on_passive_text_focus_out)
            view.connect("scroll-event", on_passive_text_scroll, view, outer)
            scrolled.connect("scroll-event", on_passive_text_scroll, view, outer)

        def on_settings_control_scroll(_widget: Gtk.Widget, event: Gdk.Event, outer: Gtk.ScrolledWindow) -> bool:
            scroll_outer_settings_page(outer, event)
            return True

        def register_outer_scroll_control(widget: Gtk.Widget, outer: Gtk.ScrolledWindow) -> None:
            widget.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            widget.connect("scroll-event", on_settings_control_scroll, outer)

        def on_settings_dialog_button_press(widget: Gtk.Widget, event: Gdk.Event) -> bool:
            if getattr(event, "window", None) is widget.get_window():
                deactivate_passive_text_view()
                return False

            def deactivate_if_focus_left_text_view() -> bool:
                view = active_text_view["view"]
                if view is not None and dialog.get_focus() is not view:
                    deactivate_passive_text_view()
                return False

            GLib.idle_add(deactivate_if_focus_left_text_view)
            return False

        general_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        dictionary_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        mcp_box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        general_box.connect("button-press-event", on_settings_dialog_button_press)
        dictionary_box.connect("button-press-event", on_settings_dialog_button_press)
        mcp_box.connect("button-press-event", on_settings_dialog_button_press)
        register_passive_text_view(system_prompt_view, system_prompt_scrolled, general_scrolled)
        for widget in (
            text_size,
            button_size,
            theme_combo,
            language_combo,
            default_agent_combo,
            codex_model_combo,
            codex_reasoning_combo,
            limited_bash_head_tokens,
            limited_bash_tail_tokens,
            limited_bash_heartbeat_seconds,
            limited_bash_heartbeat_tokens,
        ):
            register_outer_scroll_control(widget, general_scrolled)

        def run_settings_update_check(*_ignored: object) -> None:
            if self.settings_update_running:
                return
            self.settings_update_running = True
            settings_update_check_button.set_sensitive(False)
            settings_update_button.set_sensitive(False)
            settings_update_button.set_visible(False)
            settings_update_status.set_text(self._tr("settings_update_check_running"))

            def worker() -> None:
                try:
                    result = run_agent_workspace_update_check()
                    if result.update_available:
                        status_text = self._tr("settings_update_available").format(
                            current=result.current_version,
                            latest=result.latest_version,
                        )
                    elif result.ok:
                        status_text = self._tr("settings_update_none")
                    else:
                        status_text = (
                            self._tr("settings_update_check_failed").format(code=result.returncode)
                            + "\n"
                            + _tail_text(result.output, 2_000)
                        )
                    update_available = result.update_available
                except Exception as error:
                    status_text = (
                        self._tr("settings_update_check_failed").format(code=1)
                        + f"\n{type(error).__name__}: {error}"
                    )
                    update_available = False

                def apply_result() -> bool:
                    self.settings_update_running = False
                    if not settings_open["value"]:
                        return False
                    settings_update_check_button.set_sensitive(True)
                    settings_update_button.set_sensitive(update_available)
                    settings_update_button.set_visible(update_available)
                    settings_update_status.set_text(status_text)
                    return False

                GLib.idle_add(apply_result)

            threading.Thread(target=worker, daemon=True).start()

        def run_settings_update(*_ignored: object) -> None:
            if self.settings_update_running:
                return
            confirm = Gtk.MessageDialog(
                transient_for=dialog,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text=self._tr("settings_update_confirm_title"),
            )
            confirm.format_secondary_text(self._tr("settings_update_confirm_body"))
            confirm.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
            confirm.add_button(self._tr("settings_apply_update"), Gtk.ResponseType.OK)
            response = confirm.run()
            confirm.destroy()
            if response != Gtk.ResponseType.OK:
                return
            self.settings_update_running = True
            settings_update_check_button.set_sensitive(False)
            settings_update_button.set_sensitive(False)
            settings_update_status.set_text(self._tr("settings_update_running"))

            def worker() -> None:
                update_ok = False
                try:
                    result = run_agent_workspace_update()
                    update_ok = result.ok
                    status_text = (
                        self._tr("settings_update_done")
                        if result.ok
                        else self._tr("settings_update_failed").format(code=result.returncode)
                        + "\n"
                        + _tail_text(result.output, 2_000)
                    )
                except Exception as error:
                    status_text = self._tr("settings_update_failed").format(code=1) + f"\n{type(error).__name__}: {error}"

                def apply_result() -> bool:
                    self.settings_update_running = False
                    if not settings_open["value"]:
                        return False
                    settings_update_check_button.set_sensitive(True)
                    settings_update_button.set_sensitive(True)
                    settings_update_status.set_text(status_text)
                    if update_ok:
                        settings_open["value"] = False
                        dialog.response(Gtk.ResponseType.CANCEL)
                        self.window.destroy()
                    return False

                GLib.idle_add(apply_result)

            threading.Thread(target=worker, daemon=True).start()

        settings_update_check_button.connect("clicked", run_settings_update_check)
        settings_update_button.connect("clicked", run_settings_update)
        claude_model_combo = Gtk.ComboBoxText()
        claude_effort_combo = Gtk.ComboBoxText()
        for widget in (claude_model_combo, claude_effort_combo):
            register_outer_scroll_control(widget, general_scrolled)
        claude_animations_check = Gtk.CheckButton()
        claude_animations_check.set_active(self.claude_animations_enabled)
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
        for widget in (
            dictionary_min_occurrences,
            dictionary_min_saving,
            dictionary_min_term_length,
            dictionary_max_term_words,
        ):
            register_outer_scroll_control(widget, dictionary_scrolled)
        preview_input = _text_view(self.text_font_size, editable=True)
        preview_input.get_buffer().set_text(self.task_dictionary_preview_text)
        preview_output = _text_view(self.text_font_size, editable=False)
        preview_metrics = Gtk.Label()
        preview_metrics.set_xalign(0)
        preview_metrics.set_selectable(True)
        preview_metrics.set_margin_top(4)
        preview_metrics.modify_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        preview_input_scrolled = _scrolled(preview_input)
        preview_input_scrolled.set_hexpand(True)
        preview_input_scrolled.set_vexpand(True)
        preview_input_scrolled.set_min_content_height(220)
        preview_output_scrolled = _scrolled(preview_output)
        preview_output_scrolled.set_hexpand(True)
        preview_output_scrolled.set_vexpand(True)
        preview_output_scrolled.set_min_content_height(180)
        register_passive_text_view(preview_input, preview_input_scrolled, dictionary_scrolled)
        register_passive_text_view(preview_output, preview_output_scrolled, dictionary_scrolled)
        preview_input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_input_box.set_hexpand(True)
        preview_input_box.set_vexpand(True)
        preview_output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_output_box.set_hexpand(True)
        preview_output_box.set_vexpand(True)
        preview_metrics_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_metrics_box.set_hexpand(True)
        preview_metrics_box.set_vexpand(False)
        preview_label = Gtk.Label(label=self._tr("settings_dictionary_preview_text"))
        preview_label.set_xalign(0)
        preview_output_label = Gtk.Label(label=self._tr("settings_dictionary_preview"))
        preview_output_label.set_xalign(0)
        preview_metrics_label = Gtk.Label(label=self._tr("settings_dictionary_savings"))
        preview_metrics_label.set_xalign(0)
        preview_input_box.pack_start(preview_label, False, False, 0)
        preview_input_box.pack_start(preview_input_scrolled, True, True, 0)
        preview_output_box.pack_start(preview_output_label, False, False, 0)
        preview_output_box.pack_start(preview_output_scrolled, True, True, 0)
        preview_metrics_box.pack_start(preview_metrics_label, False, False, 0)
        preview_metrics_box.pack_start(preview_metrics, False, False, 0)

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
            preview_output.get_buffer().set_text(_dictionary_preview_text(text, preview, language=self.language))
            preview_metrics.set_text(_dictionary_preview_metrics_text(text, preview, language=self.language))

        def add_settings_section(title: str, rows: list[tuple[str, Gtk.Widget]]) -> None:
            section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            section_box.set_hexpand(True)
            heading = Gtk.Label()
            heading.set_xalign(0)
            heading.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
            grid = Gtk.Grid(column_spacing=10, row_spacing=8)
            grid.set_hexpand(True)
            for row, (label, widget) in enumerate(rows):
                label_widget = Gtk.Label(label=label)
                label_widget.set_xalign(0)
                if isinstance(widget, Gtk.Label):
                    widget.set_xalign(0)
                grid.attach(label_widget, 0, row, 1, 1)
                grid.attach(widget, 1, row, 1, 1)
            section_box.pack_start(heading, False, False, 0)
            section_box.pack_start(grid, False, False, 0)
            general_box.pack_start(section_box, False, False, 0)

        add_settings_section(
            self._tr("settings_section_ui"),
            [
                (self._tr("text_font_size"), text_size),
                (self._tr("button_font_size"), button_size),
                (self._tr("theme"), theme_combo),
                (self._tr("language"), language_combo),
            ],
        )
        add_settings_section(
            self._tr("settings_section_agent_context"),
            [
                (self._tr("default_agent"), default_agent_combo),
                (self._tr("system_prompt"), system_prompt_scrolled),
            ],
        )
        codex_rows: list[tuple[str, Gtk.Widget]] = []
        if codex_models is not None:
            codex_rows.extend(
                [
                    (self._tr("default_codex_model"), codex_model_combo),
                    (self._tr("default_codex_reasoning"), codex_reasoning_combo),
                ]
            )
        codex_rows.append((self._tr("codex_animations_enabled"), codex_animations_check))
        add_settings_section(agent_label("codex"), codex_rows)
        claude_rows: list[tuple[str, Gtk.Widget]] = []
        if claude_models is not None:
            claude_rows.extend(
                [
                    (self._tr("default_claude_model"), claude_model_combo),
                    (self._tr("default_claude_effort"), claude_effort_combo),
                ]
            )
        claude_rows.append((self._tr("claude_animations_enabled"), claude_animations_check))
        add_settings_section(agent_label("claude"), claude_rows)
        add_settings_section(
            self._tr("settings_section_bash_output"),
            [
                (self._tr("limited_bash_head_tokens"), limited_bash_head_tokens),
                (self._tr("limited_bash_tail_tokens"), limited_bash_tail_tokens),
                (
                    self._tr("limited_bash_heartbeat_seconds"),
                    limited_bash_heartbeat_seconds,
                ),
                (
                    self._tr("limited_bash_heartbeat_tokens"),
                    limited_bash_heartbeat_tokens,
                ),
            ],
        )

        dictionary_box.pack_start(dictionary_grid, False, False, 0)
        dictionary_box.pack_start(preview_input_box, True, True, 0)
        dictionary_box.pack_start(preview_output_box, True, True, 0)
        dictionary_box.pack_start(preview_metrics_box, False, False, 0)
        row = 0
        dictionary_heading = Gtk.Label(label=self._tr("settings_dictionary_compiler"))
        dictionary_heading.set_xalign(0)
        dictionary_grid.attach(dictionary_heading, 0, row, 2, 1)
        for label, widget in (
            (self._tr("settings_dictionary_auto_discover"), dictionary_auto),
            (self._tr("settings_dictionary_strip_articles"), dictionary_strip_articles),
            (self._tr("settings_dictionary_min_occurrences"), dictionary_min_occurrences),
            (self._tr("settings_dictionary_min_saving"), dictionary_min_saving),
            (self._tr("settings_dictionary_min_term_length"), dictionary_min_term_length),
            (self._tr("settings_dictionary_max_term_words"), dictionary_max_term_words),
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
        self.profiling_output_view = profiling_output
        profiling_enabled.connect("toggled", lambda button: self._set_profiling_enabled(button.get_active()))
        profiling_clear.connect("clicked", lambda _button: self._clear_profiling_counts())
        profiling_crash.connect("clicked", lambda _button: self._abort_with_stack_dump())
        self._refresh_profiling_output()
        self._disable_button_hover_tracking_recursive(dialog)

        dialog.show_all()
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
        if self.profiling_output_view is profiling_output:
            self.profiling_output_view = None
        self._resume_profiling_after_settings()
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
            self.codex_animations_enabled = codex_animations_check.get_active()
            self.claude_animations_enabled = claude_animations_check.get_active()
            self.limited_bash_head_tokens = int(limited_bash_head_tokens.get_value())
            self.limited_bash_tail_tokens = int(limited_bash_tail_tokens.get_value())
            self.limited_bash_heartbeat_seconds = int(limited_bash_heartbeat_seconds.get_value())
            self.limited_bash_heartbeat_tokens = int(limited_bash_heartbeat_tokens.get_value())
            self.limited_bash_output_tokens = self.limited_bash_head_tokens
            self.system_prompt = _text_buffer_text(system_prompt_view.get_buffer())
            self.mcp_enabled_groups = tuple(
                group_id
                for group_id, check in mcp_group_checks.items()
                if check.get_active()
            )
            self.mcp_trusted = confirmed_mcp_trusted
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
        self.task_action_reflow_layout = None
        workspace_actions_box = getattr(self, "workspace_actions_box", None)
        if workspace_actions_box is not None:
            for child in workspace_actions_box.get_children():
                workspace_actions_box.remove(child)
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
        self._render_workspace_action_buttons()
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
        if self.workspace_actions_box is not None:
            self.workspace_actions_box.show_all()
        if self.global_task_parameter_box is not None:
            self.global_task_parameter_box.show_all()
        self.task_shortcuts_box.show_all()
        self.task_action_parameter_box.show_all()

    def _on_task_actions_box_size_allocate(self, _widget: Gtk.Widget, allocation: Gdk.Rectangle) -> None:
        width = max(1, allocation.width - self.task_actions_box.get_border_width() * 2)
        if width == self.task_action_reflow_width and self.task_action_reflow_layout is not None:
            return
        self.task_action_reflow_width = width
        self._schedule_task_action_reflow()

    def _schedule_task_action_reflow(self) -> None:
        if self.task_action_reflow_source_id is None:
            self.task_action_reflow_source_id = GLib.idle_add(self._reflow_task_action_buttons)

    def _reflow_task_action_buttons(self) -> bool:
        self.task_action_reflow_source_id = None
        if not hasattr(self, "task_actions_box"):
            return False
        width = max(1, self.task_actions_box.get_allocated_width() - self.task_actions_box.get_border_width() * 2)
        layout_rows: list[tuple[str, ...]] = []
        row_ids: list[str] = []
        row_width = 0
        widgets: list[tuple[str, Gtk.Widget, int]] = []
        order = self.task_action_reorder_preview if self.task_reorder_group == "action" else None
        for action_id in order or self._task_action_order():
            widget = self.task_action_item_widgets.get(action_id)
            if widget is None:
                continue
            _minimum_width, natural_width = widget.get_preferred_width()
            next_width = natural_width if row_width == 0 else row_width + 3 + natural_width
            if row_ids and next_width > width:
                layout_rows.append(tuple(row_ids))
                row_ids = []
                row_width = 0
            row_ids.append(action_id)
            row_width = natural_width if row_width == 0 else row_width + 3 + natural_width
            widgets.append((action_id, widget, natural_width))
        if row_ids:
            layout_rows.append(tuple(row_ids))
        layout = (width, tuple(layout_rows))
        self.task_action_reflow_width = width
        if layout == self.task_action_reflow_layout:
            return False
        self.task_action_reflow_layout = layout
        for action_id in self._task_action_order():
            widget = self.task_action_item_widgets.get(action_id)
            if widget is None:
                continue
            parent = widget.get_parent()
            if isinstance(parent, Gtk.Container):
                parent.remove(widget)
        for row in self.task_actions_box.get_children():
            self.task_actions_box.remove(row)
        row: Gtk.Box | None = None
        row_width = 0
        for _action_id, widget, natural_width in widgets:
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

    def _render_workspace_action_buttons(self) -> None:
        workspace_actions_box = getattr(self, "workspace_actions_box", None)
        if workspace_actions_box is None:
            return
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        row.set_halign(Gtk.Align.START)
        for action_id in self._workspace_action_order():
            widget = self.task_action_item_widgets.get(action_id)
            if widget is None:
                continue
            parent = widget.get_parent()
            if isinstance(parent, Gtk.Container):
                parent.remove(widget)
            row.pack_start(widget, False, False, 0)
        if row.get_children():
            workspace_actions_box.pack_start(row, False, False, 0)

    def _task_action_reorder_children(self) -> list[Gtk.Widget]:
        order = self.task_action_reorder_preview if self.task_reorder_group == "action" else None
        action_ids = order or self._task_action_order()
        return [self.task_action_item_widgets[action_id] for action_id in action_ids if action_id in self.task_action_item_widgets]

    def _task_action_button(self, action: TaskAction, *, shortcut: bool) -> Gtk.Widget:
        button = _compact_button(
            action.label,
            lambda _button, item=action: self._on_task_action_clicked(item),
            tooltip=False,
        )
        if action.description:
            button.set_tooltip_text(action.description)
        button.set_size_request(-1, 20)
        button.set_focus_on_click(False)
        button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._disable_action_hover_tracking(button)
        if shortcut:
            button.connect("button-press-event", self._on_task_shortcut_button_press, action)
            return button
        button.connect("button-press-event", self._on_task_action_button_press, action)
        button.get_style_context().add_class("task-action-label-button")
        if action.source == "workspace":
            button.get_style_context().add_class("workspace-task-action")
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
        play.get_style_context().add_class("task-action-play-button")
        play.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._disable_action_hover_tracking(play)
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
        return [action.action_id for action in self.task_base_actions if action.source != "workspace"]

    def _workspace_action_order(self) -> list[str]:
        return [action.action_id for action in self.task_base_actions if action.source == "workspace"]

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
                    play.set_visible(True)
                    play.set_sensitive(True)
            else:
                context.remove_class("task-action-selected")
                if play is not None:
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
            button = _compact_button(self._parameter_button_label(parameter), None, max_width_chars=18, tooltip=False)
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
            no_parameters = _compact_button(self._s("action.no_parameters"), None, max_width_chars=18, tooltip=False)
            no_parameters.set_size_request(-1, 20)
            no_parameters.set_sensitive(False)
            _flow_box_add(self.task_action_parameter_box, no_parameters)
        for parameter in local_parameters:
            button = _compact_button(self._parameter_button_label(parameter), None, max_width_chars=18, tooltip=False)
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
        shortcut_button = _compact_button(self._s("action.save_shortcut"), None, max_width_chars=24, tooltip=False)
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
            self.task_action_reflow_layout = None
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
        grid.attach(Gtk.Label(label=self._s("action.shortcut_label")), 0, 0, 1, 1)
        grid.attach(label_entry, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label=self._s("action.shortcut_id")), 0, 1, 1, 1)
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
        self._refresh_task_row_style_for_task(task.path)

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
            system_prompt=self.system_prompt,
            codex_animations_enabled=self.codex_animations_enabled,
            claude_animations_enabled=self.claude_animations_enabled,
            workspace_mcp_enabled_groups=workspace_mcp_enabled_groups_for_runtime(self.mcp_enabled_groups),
            workspace_mcp_trusted=self.mcp_trusted,
            include_task_check=True,
        )
        run_id = new_agent_session_id()
        env = ai_agent_environment(
            os.environ.copy(),
            task,
            self.workspace,
            agent,
            launch.session_state,
            run_id=run_id,
            limited_bash_output_tokens=self.limited_bash_output_tokens,
            limited_bash_head_tokens=self.limited_bash_head_tokens,
            limited_bash_tail_tokens=self.limited_bash_tail_tokens,
            limited_bash_heartbeat_seconds=self.limited_bash_heartbeat_seconds,
            limited_bash_heartbeat_tokens=self.limited_bash_heartbeat_tokens,
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
        self._configure_terminal_rendering(terminal)
        if kind == "codex":
            self._configure_codex_terminal_pointer_rendering(terminal)
        self._apply_terminal_theme(terminal)
        self._profile_widget(f"vte-{kind}-{session_id}", terminal)
        terminal.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        terminal.connect("button-press-event", self._on_terminal_button_press)
        terminal.connect("popup-menu", self._on_terminal_popup_menu)
        terminal.connect("key-press-event", self._on_terminal_key_press)
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
        scrolled.get_style_context().add_class("terminal-page")
        terminal_child: Gtk.Widget = terminal
        terminal_mouse: CodexTerminalMouseStateMachine | None = None
        if kind in {"codex", "claude"}:
            terminal_mouse = CodexTerminalMouseStateMachine(
                terminal,
                self._record_profile_event,
                profile_area=f"{kind}-terminal-mouse",
            )
            terminal_child = terminal_mouse.widget
        scrolled.add(terminal_child)
        if terminal_mouse is not None:
            self._profile_widget(f"terminal-proxy-{kind}-{session_id}", terminal_child)
        self._profile_widget(f"terminal-page-{kind}-{session_id}", scrolled)
        session = TerminalSession(
            session_id=session_id,
            task_path=task.path,
            kind=kind,
            terminal=terminal,
            page=scrolled,
            terminal_mouse=terminal_mouse,
            busy=session_is_agent(session_kind=kind),
            run_id=run_id if session_is_agent(session_kind=kind) else None,
        )
        self.terminal_sessions[session_id] = session
        if session.run_id is not None:
            save_task_active_agent_run(task, kind, session.run_id)
        if session_is_agent(session_kind=kind):
            GLib.timeout_add(
                AGENT_RESTORE_OUTPUT_CHECK_MS,
                self._check_agent_restore_output,
                session_id,
                time.monotonic() + AGENT_RESTORE_OUTPUT_CHECK_WINDOW_SECONDS,
            )
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
        self._refresh_task_row_style_for_task(session.task_path)

    def _refresh_console_tabs_for_task(self, task: TaskSummary) -> None:
        self._refreshing_console_tabs = True
        try:
            self._ensure_ai_agent_console_page()
            if getattr(self, "ai_debug_page", None) is not None:
                self._ensure_ai_debug_page()
            self._clear_ai_agent_terminal_page()
            page_num = self.console_notebook.get_n_pages() - 1
            while page_num >= 0:
                page = self.console_notebook.get_nth_page(page_num)
                session = self._session_for_page(page)
                if session is not None and session.task_path != task.path:
                    self.console_notebook.remove_page(page_num)
                page_num -= 1
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
                    return
            session = self._first_terminal_for_task(task)
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
        session_page_visible = False
        if page_num >= 0:
            self.console_notebook.set_current_page(page_num)
            session_page_visible = True
            if remember:
                self.last_active_terminal_by_task[session.task_path] = session.session_id
        elif session_is_agent(session_kind=session.kind) and self.ai_agent_page is not None:
            agent_page_num = self.console_notebook.page_num(self.ai_agent_page)
            if agent_page_num >= 0:
                self.console_notebook.set_current_page(agent_page_num)
                if remember:
                    self.last_active_terminal_by_task[session.task_path] = session.session_id
        session.terminal.grab_focus()
        if session_page_visible:
            self._on_visible_terminal_session_changed(session)

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
            self._deactivate_agent_terminal_mouse()
            return
        if task is not None and page is getattr(self, "ai_debug_page", None):
            page_memory[task.path] = "ai-debug"
            self._refresh_ai_debug()
            self._deactivate_agent_terminal_mouse()
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

    def _activate_ai_debug_page(self, task: TaskSummary, *, remember: bool) -> bool:
        ai_debug_page = getattr(self, "ai_debug_page", None)
        if ai_debug_page is None:
            return False
        page_num = self.console_notebook.page_num(ai_debug_page)
        if page_num < 0:
            return False
        self.console_notebook.set_current_page(page_num)
        self._refresh_ai_debug()
        if remember:
            page_memory = getattr(self, "last_active_console_page_by_task", None)
            if page_memory is None:
                page_memory = {}
                self.last_active_console_page_by_task = page_memory
            page_memory[task.path] = "ai-debug"
        return True

    def _refresh_ai_debug_if_visible(self) -> bool:
        if self._closing:
            self.ai_debug_refresh_source_id = None
            return False
        if self.selected_task is not None and self._ai_debug_tab_active():
            self._refresh_ai_debug()
        return True

    def _on_workspace_ipc_event(self, event: WorkspaceIpcEvent) -> None:
        _ = event

    def _refresh_ai_debug(self) -> None:
        task = self.selected_task
        store = getattr(self, "ai_debug_store", None)
        tree = getattr(self, "ai_debug_tree", None)
        if task is None or store is None or tree is None:
            return
        events = self._ai_debug_events_for_task(task)
        signature = (str(task.path), tuple(event.event_id for event in events))
        if signature == getattr(self, "ai_debug_last_signature", ()):
            return
        selection = tree.get_selection()
        selected_id: str | None = None
        _model, selected_iter = selection.get_selected()
        if selected_iter is not None:
            selected_id = store[selected_iter][0]
        visible_anchor_id = self._ai_debug_visible_anchor_id(tree, store)
        restore_id = _ai_debug_restore_event_id(
            [str(event.event_id) for event in events],
            selected_id=selected_id,
            visible_anchor_id=visible_anchor_id,
        )
        self.ai_debug_last_signature = signature
        store.clear()
        restore_path: Gtk.TreePath | None = None
        for event in events:
            row_iter = store.append(_harness_debug_event_row(event, language=self.language))
            event_id = str(event.event_id)
            if restore_id is not None and event_id == restore_id:
                restore_path = store.get_path(row_iter)
        if restore_path is not None:
            if restore_id == selected_id:
                selection.select_path(restore_path)
            tree.scroll_to_cell(restore_path, None, False, 0.0, 0.0)

    def _ai_debug_visible_anchor_id(self, tree: Gtk.TreeView, store: Gtk.ListStore) -> str | None:
        visible_range = tree.get_visible_range()
        if visible_range is None:
            return None
        start_path, _end_path = visible_range
        row_iter = store.get_iter(start_path)
        if row_iter is None:
            return None
        return str(store[row_iter][0])

    def _ai_debug_events_for_task(self, task: TaskSummary) -> list[HarnessDebugEvent]:
        return load_harness_debug_events(task.path)

    def _on_ai_debug_row_activated(
        self,
        tree: Gtk.TreeView,
        path: Gtk.TreePath,
        _column: Gtk.TreeViewColumn,
    ) -> None:
        task = self.selected_task
        model = tree.get_model()
        if task is None or model is None:
            return
        row_iter = model.get_iter(path)
        if row_iter is None:
            return
        event_id = str(model[row_iter][0])
        event = next((event for event in self._ai_debug_events_for_task(task) if str(event.event_id) == event_id), None)
        if event is None:
            return
        self._show_ai_debug_event_details(event)

    def _show_ai_debug_event_details(self, event: HarnessDebugEvent) -> None:
        dialog = Gtk.Dialog(
            title=self._tr("ai_debug_details_title"),
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(self._tr("close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(720, 420)
        content = dialog.get_content_area()
        content.set_border_width(12)
        view = _text_view(self.text_font_size, editable=False)
        self._set_text(view, _harness_debug_event_details_text(event, language=self.language))
        content.pack_start(_scrolled(view), True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def _restore_last_console_page(self, task: TaskSummary) -> bool:
        page_marker = getattr(self, "last_active_console_page_by_task", {}).get(task.path)
        if page_marker == "ai-agent":
            return self._activate_ai_agent_console_page(task, remember=False)
        if page_marker == "ai-debug":
            return self._activate_ai_debug_page(task, remember=False)
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
            self._deactivate_agent_terminal_mouse()
            page_memory[task.path] = "ai-agent"
            return
        if page is getattr(self, "ai_debug_page", None) and task is not None:
            self._deactivate_agent_terminal_mouse()
            page_memory[task.path] = "ai-debug"
            self._refresh_ai_debug()
            return
        session = self._session_for_page(page)
        if session is not None:
            self.last_active_terminal_by_task[session.task_path] = session.session_id
            page_memory[session.task_path] = f"session:{session.session_id}"
            self._on_visible_terminal_session_changed(session)

    def _on_visible_terminal_session_changed(self, session: TerminalSession) -> None:
        for known_session in getattr(self, "terminal_sessions", {}).values():
            terminal_mouse = known_session.terminal_mouse
            if terminal_mouse is None:
                continue
            if known_session.session_id != session.session_id:
                terminal_mouse.deactivate()

    def _deactivate_agent_terminal_mouse(self) -> None:
        for session in getattr(self, "terminal_sessions", {}).values():
            if session.terminal_mouse is None:
                continue
            session.terminal_mouse.deactivate()

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
        if session.terminal_mouse is not None:
            session.terminal_mouse.deactivate()
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
        self._remove_codex_terminal_window_filter(session.terminal)
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
        self._remove_codex_terminal_window_filter(terminal)
        disconnect = getattr(terminal, "disconnect_by_func", None)
        if disconnect is None:
            return
        for callback in (
            self._on_terminal_button_press,
            self._on_terminal_popup_menu,
            self._on_terminal_key_press,
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
        if task is not None:
            self._refresh_task_row_style_for_task(task.path)

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
        self._refresh_task_row_style_for_task(task_path)
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
        harness_icon = self._task_harness_status_icon(task)
        if running_agents and harness_icon:
            return harness_icon
        return task_agent_status_text(
            task,
            self.workspace,
            permission_pending=self._task_has_pending_agent_permission(task),
            running_agents=running_agents,
            external_active=self._task_is_external_active(task),
            spinner_frame="",
            session_markers=self._task_agent_session_markers(task),
        )

    def _task_harness_status_icon(self, task: TaskSummary) -> str:
        event = self._latest_harness_debug_event_by_task().get(task.path)
        return event.icon if event is not None else ""

    def _latest_harness_debug_event_by_task(self) -> dict[Path, HarnessDebugEvent]:
        path = self.workspace / ".agent-workspace-harness-debug.jsonl"
        try:
            stat = path.stat()
            signature = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            signature = None
        if not hasattr(self, "harness_debug_snapshot_signature"):
            self.harness_debug_snapshot_signature = None
        if not hasattr(self, "harness_debug_latest_by_task"):
            self.harness_debug_latest_by_task = {}
        if signature == self.harness_debug_snapshot_signature:
            return self.harness_debug_latest_by_task
        if signature is None:
            self.harness_debug_latest_by_task = {}
        else:
            self.harness_debug_latest_by_task = load_latest_harness_debug_events_by_task(self.workspace)
        self.harness_debug_snapshot_signature = signature
        return self.harness_debug_latest_by_task

    def _invalidate_harness_debug_snapshot(self) -> None:
        self.harness_debug_snapshot_signature = None
        old_cache = getattr(self, "harness_status_icon_cache", None)
        if old_cache is not None:
            old_cache.clear()

    def _record_agent_interrupt(self, session: TerminalSession) -> None:
        if not session_is_agent(session_kind=session.kind):
            return
        session.busy = False
        try:
            agent_type = AgentType(session.kind)
        except ValueError:
            return
        record_harness_status(
            session.task_path,
            agent_type=agent_type,
            session_id=session.run_id,
            event=HarnessStatusEvent.HOOK_OBSERVED,
            icon="○",
            message="Agent interrupt requested.",
            tool_name="terminal",
            outcome="interrupted",
        )
        self._invalidate_harness_debug_snapshot()
        self._refresh_task_row_style_for_task(session.task_path)

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
        self._refresh_task_row_style_for_task(task.path)

    def _refresh_task_row_styles(self) -> None:
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            self._refresh_task_row_style_for_iter(row_iter)
            row_iter = self.task_store.iter_next(row_iter)
        self._ensure_selected_task_is_selectable()

    def _refresh_task_row_style_for_task(self, task_path: Path) -> None:
        if not hasattr(self, "task_store"):
            return
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            task = self.task_store[row_iter][2]
            if task.path == task_path:
                self._refresh_task_row_style_for_iter(row_iter)
                self._ensure_selected_task_is_selectable()
                return
            row_iter = self.task_store.iter_next(row_iter)

    def _refresh_task_row_style_for_iter(self, row_iter: Gtk.TreeIter) -> None:
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
        if self._running_agent_sessions():
            self._refresh_task_agent_status_cells()
        return True

    def _actions_tab_active(self) -> bool:
        notebook = getattr(self, "notebook", None)
        if notebook is None:
            return False
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.actions_page

    def _ai_debug_tab_active(self) -> bool:
        if not self._actions_tab_active():
            return False
        console_notebook = getattr(self, "console_notebook", None)
        if console_notebook is None:
            return False
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return False
        return self.console_notebook.get_nth_page(page_num) is getattr(self, "ai_debug_page", None)

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
        if event.keyval == Gdk.KEY_Escape and session is not None:
            self._record_agent_interrupt(session)
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
            terminal.paste_clipboard()
            return True
        if session is not None and session_is_agent(session_kind=session.kind) and submitted_input:
            self._invalidate_harness_debug_snapshot()
            self._refresh_task_agent_status_cells()
        return False

    def _check_agent_restore_output(self, session_id: int, until: float) -> bool:
        session = self.terminal_sessions.get(session_id)
        if session is None or session.exited or not session_is_agent(session_kind=session.kind):
            return False
        if time.monotonic() > until:
            return False
        if hasattr(self, "tasks") and hasattr(self, "workspace"):
            task = self._task_for_path(session.task_path)
            reconcile_task_agent_run_session(task, self.workspace, session.kind, session.run_id)
        if agent_output_reports_missing_session(_terminal_text_tail(session.terminal)):
            self._handle_agent_restore_failed(session)
            return False
        return True

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
            return f"{AGENT_TOOL_MARKER} {task.name}"
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
        self._disable_action_hover_tracking(button)
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
        self.details_tab_label.set_text(self._tr("context_journal"))
        self.artifacts_tab_label.set_text(self._tr("artifacts"))
        self.actions_tab_label.set_text(self._tr("actions"))
        if self.ai_agent_tab_label is not None:
            self.ai_agent_tab_label.set_text(self._s("console.ai_agent"))
        if self.ai_debug_tab_label is not None:
            self.ai_debug_tab_label.set_text(self._tr("ai_debug_tab"))
        if self.task_context_encoded_check is not None:
            self.task_context_encoded_check.set_label(self._tr("context_view_encoded"))
        for key, column in getattr(self, "ai_debug_columns", {}).items():
            column.set_title(self._tr(key))
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
            cursor_size = gtk_cursor_size()
            if cursor_size is not None:
                settings.set_property("gtk-cursor-theme-size", cursor_size)
            cursor_theme = gtk_cursor_theme()
            if cursor_theme:
                settings.set_property("gtk-cursor-theme-name", cursor_theme)
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
        button:hover,
        button:prelight,
        button:focus {{
            background: {colors['control_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
        }}
        checkbutton:hover,
        checkbutton:prelight,
        checkbutton:focus,
        spinbutton:hover,
        spinbutton:prelight,
        spinbutton:focus {{
            background: {colors['control_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
        }}
        .actions-panel frame {{
            padding: 1px;
        }}
        .actions-panel button {{
            padding: 1px 6px;
            min-height: 0;
            min-width: 0;
        }}
        .actions-panel button:hover,
        .actions-panel button:prelight {{
            background: {colors['control_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
        }}
        .actions-panel flowboxchild {{
            padding: 0;
            margin: 0;
        }}
        .actions-panel flowboxchild:hover,
        .actions-panel flowboxchild:prelight,
        .actions-panel eventbox:hover,
        .actions-panel eventbox:prelight {{
            background: transparent;
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
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
            box-shadow: none;
        }}
        button.task-action-label-button:hover,
        button.task-action-label-button:prelight,
        button.task-action-label-button:focus,
        button.task-action-label-button:active,
        button.task-action-play-button:hover,
        button.task-action-play-button:prelight,
        button.task-action-play-button:focus,
        button.task-action-play-button:active {{
            background: {colors['control_background']};
            color: {colors['foreground']};
            border-color: {colors['border']};
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
        }}
        button.task-action-label-button:focus,
        button.task-action-play-button:focus {{
            outline-style: none;
            outline-width: 0;
        }}
        button.workspace-task-action {{
            border-style: dashed;
            border-color: {colors['muted']};
        }}
        button.task-action-selected {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
        }}
        button.task-action-selected:hover,
        button.task-action-selected:prelight,
        button.task-action-selected:focus,
        button.task-action-selected:active {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
        }}
        button.task-action-run-armed {{
            background: #8a6d1f;
            color: #fff4cf;
            border-color: #f2c94c;
            box-shadow: 0 0 6px #f2c94c;
        }}
        button.task-action-run-armed:hover,
        button.task-action-run-armed:prelight,
        button.task-action-run-armed:focus,
        button.task-action-run-armed:active {{
            background: #8a6d1f;
            color: #fff4cf;
            border-color: #f2c94c;
            box-shadow: 0 0 6px #f2c94c;
            outline-style: none;
            outline-width: 0;
        }}
        button.task-action-run-fired {{
            background: #1f7a3a;
            color: #eafff0;
            border-color: #35d06f;
            box-shadow: 0 0 7px #35d06f;
        }}
        button.task-action-run-fired:hover,
        button.task-action-run-fired:prelight,
        button.task-action-run-fired:focus,
        button.task-action-run-fired:active {{
            background: #1f7a3a;
            color: #eafff0;
            border-color: #35d06f;
            box-shadow: 0 0 7px #35d06f;
            outline-style: none;
            outline-width: 0;
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
        button.codex-running:hover,
        button.codex-running:prelight,
        button.codex-running:focus,
        button.codex-running:active {{
            background: {colors['codex_running_background']};
            color: {colors['codex_running_foreground']};
            border-color: {colors['codex_running_border']};
            box-shadow: 0 0 8px {colors['codex_running_glow']};
            outline-style: none;
            outline-width: 0;
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
        notebook.console-notebook,
        notebook.console-notebook:hover,
        notebook.console-notebook:prelight,
        notebook.console-notebook:focus,
        scrolledwindow.terminal-page,
        scrolledwindow.terminal-page:hover,
        scrolledwindow.terminal-page:prelight,
        scrolledwindow.terminal-page:focus,
        vte,
        vte:hover,
        vte:prelight,
        vte:focus,
        terminal-screen,
        terminal-screen:hover,
        terminal-screen:prelight,
        terminal-screen:focus {{
            background: {colors['terminal_background']};
            color: {colors['foreground']};
            box-shadow: none;
            outline-style: none;
            outline-width: 0;
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
        treeview:hover,
        treeview:prelight {{
            background: {colors['text_background']};
            color: {colors['foreground']};
        }}
        treeview:selected {{
            background: {colors['selection_background']};
            color: {colors['selection_foreground']};
        }}
        treeview:selected:hover,
        treeview:selected:prelight {{
            background: {colors['selection_background']};
            color: {colors['selection_foreground']};
        }}
        menu, menuitem {{
            background: {colors['menu_background']};
            color: {colors['foreground']};
        }}
        menuitem:hover,
        menuitem:prelight {{
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

    def _configure_terminal_rendering(self, terminal: Vte.Terminal) -> None:
        terminal.set_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        terminal.set_cursor_blink_mode(Vte.CursorBlinkMode.OFF)
        set_text_blink_mode = getattr(terminal, "set_text_blink_mode", None)
        if set_text_blink_mode is not None:
            set_text_blink_mode(Vte.TextBlinkMode.NEVER)
        set_enable_bidi = getattr(terminal, "set_enable_bidi", None)
        if set_enable_bidi is not None:
            set_enable_bidi(False)
        set_enable_shaping = getattr(terminal, "set_enable_shaping", None)
        if set_enable_shaping is not None:
            set_enable_shaping(False)
        terminal.set_redraw_on_allocate(False)
        set_rewrap_on_resize = getattr(terminal, "set_rewrap_on_resize", None)
        if set_rewrap_on_resize is not None:
            set_rewrap_on_resize(False)

    def _configure_codex_terminal_pointer_rendering(self, terminal: Vte.Terminal) -> None:
        set_mouse_autohide = getattr(terminal, "set_mouse_autohide", None)
        if set_mouse_autohide is not None:
            set_mouse_autohide(False)
        set_allow_hyperlink = getattr(terminal, "set_allow_hyperlink", None)
        if set_allow_hyperlink is not None:
            set_allow_hyperlink(False)

    def _configure_agent_terminal_event_mask(self, terminal: Vte.Terminal) -> None:
        motion_masks = (
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_HINT_MASK
            | Gdk.EventMask.BUTTON_MOTION_MASK
            | Gdk.EventMask.BUTTON2_MOTION_MASK
            | Gdk.EventMask.BUTTON3_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.PROXIMITY_IN_MASK
            | Gdk.EventMask.PROXIMITY_OUT_MASK
        )
        required_masks = (
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
        )
        try:
            terminal.set_events((terminal.get_events() | required_masks) & ~motion_masks)
        except (AttributeError, TypeError, RuntimeError):
            pass
        window = terminal.get_window()
        if window is None:
            return
        try:
            window.set_events((window.get_events() | required_masks) & ~motion_masks)
        except (AttributeError, TypeError, RuntimeError):
            pass

    def _on_agent_terminal_realize(self, terminal: Vte.Terminal) -> None:
        self._configure_agent_terminal_event_mask(terminal)

    def _apply_runtime_style(self) -> None:
        self._apply_css()
        self.context_view.modify_font(Pango.FontDescription(f"Monospace {self.text_font_size}"))
        if self.selected_task is not None:
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
        source_id = getattr(self, "ai_debug_refresh_source_id", None)
        if source_id is not None:
            GLib.source_remove(source_id)
            self.ai_debug_refresh_source_id = None
        workspace_ipc_server = getattr(self, "workspace_ipc_server", None)
        if workspace_ipc_server is not None:
            workspace_ipc_server.close()
            self.workspace_ipc_server = None
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
        self._close_all_terminal_sessions()
        self._save_settings()
        Gtk.main_quit()

    def _save_settings(self) -> None:
        mcp_enabled_groups = agent_workspace_runtime_settings(
            {"mcp_enabled_groups": list(self.mcp_enabled_groups)},
            default_font_size=self.text_font_size,
        ).mcp_enabled_groups
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
                "codex_animations_enabled": self.codex_animations_enabled,
                "claude_animations_enabled": self.claude_animations_enabled,
                "limited_bash_output_tokens": self.limited_bash_output_tokens,
                "limited_bash_head_tokens": self.limited_bash_head_tokens,
                "limited_bash_tail_tokens": self.limited_bash_tail_tokens,
                "limited_bash_heartbeat_seconds": self.limited_bash_heartbeat_seconds,
                "limited_bash_heartbeat_tokens": self.limited_bash_heartbeat_tokens,
                "system_prompt": self.system_prompt,
                "inject_task_context_prompt": self.inject_task_context_prompt,
                "mcp_enabled_groups": list(mcp_enabled_groups),
                "mcp_trusted": self.mcp_trusted,
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
                "last_workspace": str(self.workspace),
                "recent_workspaces": self.recent_workspaces,
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
    scrolled.set_overlay_scrolling(False)
    scrolled.add(widget)
    return scrolled


def _dictionary_preview_text(text: str, preview: DictionaryPreview, *, language: str = "en") -> str:
    dictionary_lines = [f"{entry.token} = {entry.value}" for entry in preview.dictionary]
    dictionary_body = "\n".join(dictionary_lines)
    dictionary_text = dictionary_body if dictionary_body else _gtk_text(language, "dictionary_empty")
    return (
        f"{_gtk_text(language, 'settings_dictionary_dictionary')}\n"
        f"{dictionary_text}\n\n"
        f"{_gtk_text(language, 'settings_dictionary_encoded_text')}\n"
        f"{preview.encoded_text}"
    )


def _dictionary_preview_metrics_text(text: str, preview: DictionaryPreview, *, language: str = "en") -> str:
    dictionary_body = "\n".join(f"{entry.token} = {entry.value}" for entry in preview.dictionary)
    dictionary_chars = len(dictionary_body)
    encoded_total_chars = len(preview.encoded_text) + dictionary_chars
    char_saving = len(text) - encoded_total_chars
    encoded_total_tokens = preview.encoded_tokens + preview.dictionary_tokens
    token_saving = preview.original_tokens - encoded_total_tokens
    return (
        f"{_gtk_text(language, 'settings_dictionary_original_chars')}: {len(text)}\n"
        f"{_gtk_text(language, 'settings_dictionary_encoded_chars')}: {encoded_total_chars}\n"
        f"{_gtk_text(language, 'settings_dictionary_saving_chars')}: {char_saving}\n"
        f"{_gtk_text(language, 'settings_dictionary_saving_percent')}: {_dictionary_preview_percent(char_saving, len(text))}\n"
        f"{_gtk_text(language, 'settings_dictionary_original_tokens')}: {preview.original_tokens}\n"
        f"{_gtk_text(language, 'settings_dictionary_encoded_tokens')}: {encoded_total_tokens}\n"
        f"{_gtk_text(language, 'settings_dictionary_saving_tokens')}: {token_saving}\n"
        f"{_gtk_text(language, 'settings_dictionary_saving_percent')}: {_dictionary_preview_percent(token_saving, preview.original_tokens)}"
    )


def _dictionary_preview_percent(saving: int, original: int) -> str:
    if original <= 0:
        return "0.0%"
    return f"{saving / original * 100:.1f}%"


def _harness_debug_events_text(events: list[HarnessDebugEvent], *, session_id: str | None = None, language: str = "en") -> str:
    if not events:
        if session_id:
            return _gtk_text(language, "ai_debug_message_no_events_session").format(session=session_id)
        return _gtk_text(language, "ai_debug_message_no_events")
    lines = [_gtk_text(language, "ai_debug_session_filter").format(session=session_id or "all"), ""]
    for event in events:
        tool = f" tool={event.tool_name}" if event.tool_name else ""
        detail = f" :: {event.tool_detail}" if event.tool_detail else ""
        outcome = f" {_harness_debug_event_outcome(event, language=language)}" if event.outcome else ""
        hook = event.hook_event or event.status_event.value
        kind = _harness_debug_event_kind(event, language=language)
        message = _harness_debug_event_message(event, language=language)
        lines.append(
            f"{event.updated_at} {event.icon} {kind} {event.agent_type.value}/{event.session_id} "
            f"{hook}{tool}{outcome}: {message}{detail}"
        )
    return "\n".join(lines)


def _harness_debug_event_details_text(event: HarnessDebugEvent, *, language: str = "en") -> str:
    message = _harness_debug_event_message(event, language=language)
    outcome = _harness_debug_event_outcome(event, language=language) or event.outcome
    tool_detail = event.tool_detail.strip() or _gtk_text(language, "ai_debug_details_no_tool_detail")
    return "\n".join(
        (
            f"{_gtk_text(language, 'ai_debug_details_time')}: {event.updated_at}",
            f"{_gtk_text(language, 'ai_debug_details_agent')}: {event.agent_type.value}",
            f"{_gtk_text(language, 'ai_debug_details_session')}: {event.session_id}",
            f"{_gtk_text(language, 'ai_debug_details_event_id')}: {event.event_id}",
            f"{_gtk_text(language, 'ai_debug_details_hook')}: {event.hook_event or event.status_event.value}",
            f"{_gtk_text(language, 'ai_debug_details_status')}: {event.status_event.value}",
            f"{_gtk_text(language, 'ai_debug_details_result')}: {outcome}",
            f"{_gtk_text(language, 'ai_debug_details_message')}: {message}",
            f"{_gtk_text(language, 'ai_debug_details_tool')}: {event.tool_name or '-'}",
            "",
            f"{_gtk_text(language, 'ai_debug_details_tool_detail')}:",
            tool_detail,
        )
    )


def _harness_debug_event_row(event: HarnessDebugEvent, *, language: str = "en") -> tuple[str, str, str, str, str, str, str, str]:
    hook = event.hook_event or event.status_event.value
    kind = _harness_debug_event_kind(event, language=language)
    return (
        str(event.event_id),
        event.updated_at,
        event.icon,
        kind,
        hook,
        event.tool_name,
        _harness_debug_event_outcome(event, language=language),
        _harness_debug_event_message(event, language=language),
    )


def _ai_debug_restore_event_id(
    event_ids: list[str],
    *,
    selected_id: str | None,
    visible_anchor_id: str | None,
) -> str | None:
    for candidate in (selected_id, visible_anchor_id):
        if candidate is not None and candidate in event_ids:
            return candidate
    return None


def _harness_debug_event_kind(event: HarnessDebugEvent, *, language: str = "en") -> str:
    if event.outcome == "injected":
        return _gtk_text(language, "ai_debug_kind_inject")
    if event.status_event.value.startswith("tool_"):
        return _gtk_text(language, "ai_debug_kind_tool")
    if event.outcome == "blocked":
        return _gtk_text(language, "ai_debug_kind_block")
    return _gtk_text(language, "ai_debug_kind_hook")


def _harness_debug_event_message(event: HarnessDebugEvent, *, language: str = "en") -> str:
    key_by_status = {
        "compact_checkpoint": "ai_debug_message_compact_checkpoint",
        "compact_finished": "ai_debug_message_compact_finished",
        "journal_required": (
            "ai_debug_message_journal_required_compact"
            if event.hook_event == "pre_compact"
            else "ai_debug_message_journal_required"
        ),
        "session_ended": "ai_debug_message_session_ended",
        "session_started": "ai_debug_message_session_started",
        "stop_allowed": "ai_debug_message_stop_allowed",
        "task_check_failed": "ai_debug_message_task_check_failed",
        "task_unresolved": "ai_debug_message_task_unresolved",
        "tool_finished": "ai_debug_message_tool_finished",
        "tool_started": "ai_debug_message_tool_started",
        "user_prompt_received": "ai_debug_message_user_prompt_received",
    }
    key = key_by_status.get(event.status_event.value)
    if key is None and event.status_event.value == "hook_observed":
        return _gtk_text(language, "ai_debug_message_hook_observed").format(
            hook=event.hook_event or event.status_event.value
        )
    if key is None:
        return event.message
    return _gtk_text(language, key)


def _harness_debug_event_outcome(event: HarnessDebugEvent, *, language: str = "en") -> str:
    if not event.outcome:
        return ""
    return _gtk_text(language, f"ai_debug_outcome_{event.outcome}")


def _gtk_text(language: str, key: str) -> str:
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))




def ai_agent_task_context_message(task: TaskSummary, workspace: Path, language: str = "en") -> str:
    language_instruction = CODEX_LANGUAGE_INSTRUCTIONS.get(language, CODEX_LANGUAGE_INSTRUCTIONS["en"]) if language else ""
    settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
    return ai_agent_task_context_prompt(
        task,
        workspace,
        language_instruction,
        inject_task_context=settings.inject_task_context_prompt,
        system_prompt=settings.system_prompt,
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
    codex_animations_enabled: bool = False,
    claude_animations_enabled: bool = False,
) -> list[str]:
    settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
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
        codex_animations_enabled=codex_animations_enabled,
        claude_animations_enabled=claude_animations_enabled,
        workspace_mcp_enabled_groups=workspace_mcp_enabled_groups_for_runtime(settings.mcp_enabled_groups),
        workspace_mcp_trusted=settings.mcp_trusted,
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
    codex_animations_enabled: bool = False,
) -> list[str]:
    settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
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
        codex_animations_enabled=codex_animations_enabled,
        workspace_mcp_enabled_groups=workspace_mcp_enabled_groups_for_runtime(settings.mcp_enabled_groups),
        workspace_mcp_trusted=settings.mcp_trusted,
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


def _tail_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return "...\n" + text[-limit:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the local workspace task dashboard.")
    parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace root. Default: last opened workspace or current directory.",
    )
    args = parser.parse_args(argv)
    workspace = resolve_agent_workspace_startup(Path(args.workspace) if args.workspace else None)
    install_agent_workspace_exception_logger(workspace, "gtk")
    workspace_lock = acquire_agent_workspace_lock(workspace)
    if workspace_lock is None:
        print(f"Agent Workspace is already running for {workspace.resolve()}", file=sys.stderr)
        return 0

    clear_harness_debug_events(workspace)
    gui = WorkspaceGtkGui(workspace)
    gui.window.show_all()
    gui._disable_button_hover_tracking_recursive(gui.window)
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
