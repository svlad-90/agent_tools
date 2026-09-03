from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import json
import os
import sys
import threading
from urllib.request import urlopen

from agent_tools.agent_workspace.components.localization.api import AGENT_STATUS_MANUAL_ENTRIES
from agent_tools.agent_workspace.components.localization.api import AGENT_STATUS_MANUAL_MENU_LABEL
from agent_tools.agent_workspace.components.localization.api import AGENT_STATUS_MANUAL_TITLE
from agent_tools.agent_workspace.components.localization.api import AGENT_STATUS_MANUAL_USAGE_ENTRIES
from agent_tools.agent_workspace.components.console_output.api import ConsoleChunk
from agent_tools.agent_workspace.components.task_sessions.api import TaskSessionDiscoveryState
from agent_tools.agent_workspace.components.task_sessions.api import AgentSessionState
from agent_tools.agent_workspace.components.agent_status.api import agent_status_tooltip_text
from agent_tools.agent_workspace.components.agent_runtime.api import ai_agent_environment
from agent_tools.agent_workspace.components.agent_runtime.api import ai_agent_launch_state
from agent_tools.agent_workspace.components.agent_runtime.api import ai_agent_launch_state_for_selection
from agent_tools.agent_workspace.components.agent_runtime.api import ai_agent_switch_decision
from agent_tools.agent_workspace.components.agent_runtime.api import ai_agent_task_context_prompt
from agent_tools.agent_workspace.components.agent_runtime.api import build_ai_agent_console_command
from agent_tools.agent_workspace.components.agent_runtime.api import prepare_ai_agent_launch_command
from agent_tools.agent_workspace.components.agent_runtime.api import task_check_prompt_suffix
from agent_tools.agent_workspace.components.agent_status.api import agent_output_reports_missing_session
from agent_tools.agent_workspace.components.agent_status.api import agent_output_reports_turn_complete
from agent_tools.agent_workspace.components.agent_status.api import agent_output_requests_permission
from agent_tools.agent_workspace.components.agent_status.api import agent_output_state_update
from agent_tools.agent_workspace.components.agent_status.api import analyze_agent_output
from agent_tools.agent_workspace.components.process_runtime.api import acquire_agent_workspace_lock
from agent_tools.agent_workspace.components.task_sessions.api import clear_task_agent_session
from agent_tools.agent_workspace.components.task_sessions.api import clear_task_active_agent_run
from agent_tools.agent_workspace.components.task_sessions.api import codex_session_id_exists
from agent_tools.agent_workspace.components.task_sessions.api import find_latest_claude_session_id
from agent_tools.agent_workspace.components.task_sessions.api import find_latest_codex_session_id
from agent_tools.agent_workspace.components.task_sessions.api import find_task_agent_session_id
from agent_tools.agent_workspace.components.task_sessions.api import load_task_agent
from agent_tools.agent_workspace.components.task_sessions.api import load_task_active_agent_run
from agent_tools.agent_workspace.components.task_sessions.api import load_task_agent_run_session_id
from agent_tools.agent_workspace.components.task_sessions.api import load_task_agent_session
from agent_tools.agent_workspace.components.task_sessions.api import load_task_state
from agent_tools.agent_workspace.components.process_runtime.api import log_agent_workspace_exception
from agent_tools.agent_workspace.components.console_output.api import parse_console_output
from agent_tools.agent_workspace.components.task_sessions.api import prepare_task_agent_session
from agent_tools.agent_workspace.components.task_sessions.api import reconcile_task_agent_run_session
from agent_tools.agent_workspace.components.task_sessions.api import resolve_task_agent_sessions
from agent_tools.agent_workspace.components.task_sessions.api import reset_task_agent_session
from agent_tools.agent_workspace.components.task_sessions.api import save_task_active_agent_run
from agent_tools.agent_workspace.components.task_sessions.api import save_task_agent_run_session_id
from agent_tools.agent_workspace.components.task_sessions.api import save_task_agent
from agent_tools.agent_workspace.components.task_sessions.api import save_task_agent_session
from agent_tools.agent_workspace.components.task_sessions.api import save_task_state
from agent_tools.agent_workspace.components.agent_status.api import session_marks_task_pending_permission
from agent_tools.agent_workspace.components.agent_status.api import session_marks_task_running_agent
from agent_tools.agent_workspace.components.agent_status.api import session_is_agent
from agent_tools.agent_workspace.components.agent_status.api import session_is_running_agent
from agent_tools.agent_workspace.components.agent_status.api import session_should_clear_pending_permission
from agent_tools.agent_workspace.components.agent_status.api import task_agent_status_text
from agent_tools.agent_workspace.components.task_sessions.api import task_agent_session_markers
from agent_tools.agent_workspace.components.task_sessions.api import task_agents_needing_session_discovery
from agent_tools.agent_workspace.components.task_sessions.api import task_agent_selection_with_resumable_fallback
from agent_tools.agent_workspace.components.task_sessions.api import task_agent_has_resumable_state
from agent_tools.agent_workspace.components.task_sessions.api import task_needs_session_discovery
from agent_tools.agent_workspace.components.task_sessions.api import task_agent_session_id_is_valid
from agent_tools.agent_workspace.components.agent_status.api import task_for_path
from agent_tools.agent_workspace.components.task_sessions.api import task_has_external_active_agent_run
from agent_tools.agent_workspace.components.task_sessions.api import task_has_valid_agent_session
from agent_tools.agent_workspace.components.agent_status.api import task_status_label
from agent_tools.agent_workspace.components.task_sessions.api import task_selected_agent_has_resumable_state
from agent_tools.agent_workspace.components.task_sessions.api import task_state_path
from agent_tools.agent_workspace.components.commands.api import task_action_windows_command
from agent_tools.agent_workspace.components.commands.api import task_check_windows_command
from agent_tools.agent_workspace.components.localization.api import catalog_text as localization_catalog_text
from agent_tools.agent_workspace.components.markdown.api import render_markdown_chunks
from agent_tools.agent_workspace.components.markdown.api import rough_token_count
from agent_tools.agent_workspace.components.settings.api import agent_executable
from agent_tools.agent_workspace.components.settings.api import agent_install_command
from agent_tools.agent_workspace.components.settings.api import agent_workspace_root
from agent_tools.agent_workspace.components.settings.api import agent_workspace_install_root
from agent_tools.agent_workspace.components.settings.api import agent_workspace_runtime_settings
from agent_tools.agent_workspace.components.settings.api import agent_workspace_setting_or_default
from agent_tools.agent_workspace.components.settings.api import agent_workspace_update_commands
from agent_tools.agent_workspace.components.settings.api import AGENT_WORKSPACE_DEFAULT_LIMITED_BASH_OUTPUT_TOKENS
from agent_tools.agent_workspace.components.settings.api import AGENT_WORKSPACE_RELEASES_API
from agent_tools.agent_workspace.components.settings.api import AGENT_WORKSPACE_RELEASES_LATEST_URL
from agent_tools.agent_workspace.components.settings.api import ai_agent_model_settings
from agent_tools.agent_workspace.components.settings.api import apply_agent_workspace_mcp_trust
from agent_tools.agent_workspace.components.settings.api import claude_model_choices_info
from agent_tools.agent_workspace.components.settings.api import codex_model_choices
from agent_tools.agent_workspace.components.settings.api import codex_model_choices_info
from agent_tools.agent_workspace.components.task_catalog.api import TASK_CONTEXT_BUDGET
from agent_tools.agent_workspace.components.task_catalog.api import TaskSummary
from agent_tools.agent_workspace.components.task_catalog.api import discover_tasks
from agent_tools.agent_workspace.components.task_catalog.api import run_task_check
from agent_tools.agent_workspace.components.settings.api import load_agent_workspace_settings
from agent_tools.agent_workspace.components.settings.api import run_agent_workspace_update_check
from agent_tools.agent_workspace.components.settings.api import run_agent_workspace_update
from agent_tools.agent_workspace.components.settings.api import save_agent_workspace_settings
from agent_tools.agent_workspace.components.settings.api import remember_agent_workspace
from agent_tools.agent_workspace.components.settings.api import task_dictionary_policy_from_runtime_settings
from agent_tools.agent_workspace.components.settings.api import workspace_mcp_configurable_tool_groups
from agent_tools.agent_workspace.components.settings.api import workspace_mcp_enabled_groups_for_runtime
from agent_tools.agent_workspace.components.settings.api import workspace_mcp_required_tool_groups
from agent_tools.agent_workspace.components.settings.api import workspace_mcp_tool_group_tooltip
from agent_tools.agent_workspace.components.settings.api import workspace_mcp_tool_groups
from agent_tools.agent_workspace.components.workspace_config.api import AGENT_WORKSPACE_SCHEMA_VERSION
from agent_tools.agent_workspace.components.workspace_config.api import create_agent_workspace
from agent_tools.agent_workspace.components.workspace_config.api import load_agent_workspace_manifest
from agent_tools.agent_workspace.components.workspace_config.api import resolve_agent_workspace_startup
from agent_tools.agent_workspace.components.task_context.api import context_entry_cards_markdown
from agent_tools.agent_workspace.components.task_context.api import encoded_context_entries_markdown
from agent_tools.agent_workspace.components.task_context.api import task_context_details_markdown
from agent_tools.agent_workspace.components.task_actions.api import PAF_HIDE_TASK_ENV_VAR
from agent_tools.agent_workspace.components.task_actions.api import TaskAction
from agent_tools.agent_workspace.components.task_actions.api import TaskActionParameter
from agent_tools.agent_workspace.components.task_actions.api import TaskActionsConfig
from agent_tools.agent_workspace.components.task_actions.api import load_task_actions
from agent_tools.agent_workspace.components.task_actions.api import load_task_actions_config
from agent_tools.agent_workspace.components.task_actions.api import run_task_action
from agent_tools.agent_workspace.components.workspace_service.api import AgentWorkspaceService
from agent_tools.agent_workspace.components.workspace_service.api import TaskContextFilters
from agent_tools.agent_workspace.components.web_frontend.api import create_server as create_web_server
from agent_tools.agent_workspace.components.workspace_composition.src import entrypoints as agent_workspace_main_module
from agent_tools.agent_workspace.components.gtk_desktop.src import gtk_open as gtk_open_module
from agent_tools.agent_workspace.components.gtk_desktop.src import gtk_terminal_ui as gtk_terminal_ui_module
from agent_tools.agent_workspace.components.gtk_desktop.src import gtk_ui as gtk_ui_module
from agent_tools.agent_workspace.components.desktop_integration.api import desktop_entry
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import WorkspaceGtkGui
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import TerminalSession
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import TRANSLATIONS as GTK_TRANSLATIONS
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import ai_agent_console_command as gtk_ai_agent_console_command
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import codex_task_context_message as gtk_codex_task_context_message
from agent_tools.agent_workspace.components.commands.api import task_action_shell_command as gtk_task_action_shell_command
from agent_tools.agent_workspace.components.commands.api import task_check_shell_command as gtk_task_check_shell_command
from agent_tools.agent_workspace.components.artifacts.api import artifact_context_action as gtk_artifact_context_action
from agent_tools.agent_workspace.components.artifacts.api import artifact_delete_paths as gtk_artifact_delete_paths
from agent_tools.agent_workspace.components.artifacts.api import artifact_selectable_path as gtk_artifact_selectable_path
from agent_tools.agent_workspace.components.artifacts.api import artifact_updated_label as gtk_artifact_updated_label
from agent_tools.agent_workspace.components.artifacts.api import task_artifact_entries as gtk_task_artifact_entries
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _is_pane_separator_event as gtk_is_pane_separator_event
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _notebook_event_in_empty_tab_area as gtk_notebook_event_in_empty_tab_area
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _pane_position_ratio as gtk_pane_position_ratio
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_open import open_containing_folder as gtk_open_containing_folder
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_open import _svg_open_command as gtk_svg_open_command
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_task_helpers import task_init_command as gtk_task_init_command
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_task_helpers import task_actions_signature as gtk_task_actions_signature
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _dictionary_preview_text as gtk_dictionary_preview_text
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _dictionary_preview_metrics_text as gtk_dictionary_preview_metrics_text
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import ContextEntry
from agent_tools.tools.task_context import DICTIONARY_PREVIEW_TEXT
from agent_tools.tools.task_context import LEGACY_DICTIONARY_PREVIEW_TEXT
from agent_tools.tools.task_context import ensure_database as ensure_task_context_database
from agent_tools.tools.task_context import load_entries as load_task_context_entries
from agent_tools.tools.task_context import preview_dictionary_compile
from agent_tools.tools.task_context import set_slot
from agent_tools.tools.task_context import TaskDictionaryPolicy
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_task_helpers import task_path_for_name as gtk_task_path_for_name
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_task_style import task_row_style as gtk_task_row_style
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal_ui import copy_terminal_selection as gtk_copy_terminal_selection
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal_ui import terminal_clipboard_shortcut as gtk_terminal_clipboard_shortcut
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal import terminal_palette as gtk_terminal_palette
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal_ui import terminal_session_sort_key as gtk_terminal_session_sort_key
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal_ui import terminal_tab_label as gtk_terminal_tab_label
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_terminal_ui import terminal_text_tail as gtk_terminal_text_tail
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_theme import theme_colors as gtk_theme_colors
from agent_tools.agent_workspace.components.task_actions.api import set_task_action_drag_selection as gtk_set_task_action_drag_selection
from agent_tools.agent_workspace.components.task_actions.api import task_action_drag_selection_id as gtk_task_action_drag_selection_id
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _agent_workspace_icon_path as gtk_agent_workspace_icon_path
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _agent_workspace_runtime_icon_path as gtk_agent_workspace_runtime_icon_path
from agent_tools.agent_workspace.components.tk_frontend.api import codex_console_command
from agent_tools.agent_workspace.components.tk_frontend.api import console_paste_text
from agent_tools.agent_workspace.components.tk_frontend.api import console_tab_title
from agent_tools.agent_workspace.components.tk_frontend.api import ConsoleSession
from agent_tools.agent_workspace.components.tk_frontend.api import codex_task_context_message
from agent_tools.agent_workspace.components.tk_frontend.api import embedded_terminal_command
from agent_tools.agent_workspace.components.tk_frontend.api import ai_agent_console_command
from agent_tools.agent_workspace.components.tk_frontend.api import task_action_shell_command
from agent_tools.agent_workspace.components.tk_frontend.api import task_check_shell_command
from agent_tools.agent_workspace.components.tk_frontend.src.ui import _tk_control_shortcut
from agent_tools.agent_workspace.components.tk_frontend.src.ui import AgentWorkspace
from agent_tools.agent_workspace.components.workspace_composition.src.actions import main as actions_main
from agent_tools.agent_workspace.components.task_actions.api import add_task_shortcut
from agent_tools.agent_workspace.components.task_actions.api import bindings_for_action_run
from agent_tools.agent_workspace.components.task_actions.api import delete_parameter_set_value
from agent_tools.agent_workspace.components.task_actions.api import delete_task_shortcut
from agent_tools.agent_workspace.components.task_actions.api import parameter_button_label
from agent_tools.agent_workspace.components.task_actions.api import parameter_dialog_field_names
from agent_tools.agent_workspace.components.task_actions.api import parameter_values
from agent_tools.agent_workspace.components.task_actions.api import reorder_task_action_data
from agent_tools.agent_workspace.components.task_actions.api import selected_parameter_value
from agent_tools.agent_workspace.components.task_actions.api import shortcuts_for_action
from agent_tools.agent_workspace.components.task_actions.api import task_action_code_path
from agent_tools.agent_workspace.components.task_actions.api import task_action_menu_state
from agent_tools.agent_workspace.components.task_actions.api import task_parameter_menu_state
from agent_tools.agent_workspace.components.task_actions.api import task_reorder_label_key
from agent_tools.agent_workspace.components.task_actions.api import task_shortcut_menu_state
from agent_tools.agent_workspace.components.task_actions.api import upsert_parameter_set_value
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango


class FakeConsoleText:
    def __init__(self, text: str) -> None:
        self.text = text
        self.marks: dict[str, int] = {}

    def index(self, index: str) -> str:
        return str(self._offset(index))

    def insert(self, index: str, text: str, _tags: tuple[str, ...] = ()) -> None:
        offset = self._offset(index)
        self.text = self.text[:offset] + text + self.text[offset:]

    def delete(self, start: str, end: str) -> None:
        start_offset = self._offset(start)
        end_offset = self._offset(end)
        self.text = self.text[:start_offset] + self.text[end_offset:]
        for mark, offset in list(self.marks.items()):
            if offset > end_offset:
                self.marks[mark] = offset - (end_offset - start_offset)
            elif offset > start_offset:
                self.marks[mark] = start_offset

    def compare(self, left: str, operator: str, right: str) -> bool:
        left_offset = self._offset(left)
        right_offset = self._offset(right)
        if operator == "<":
            return left_offset < right_offset
        if operator == ">=":
            return left_offset >= right_offset
        raise AssertionError(f"unsupported compare operator {operator!r}")

    def mark_set(self, mark: str, index: str) -> None:
        self.marks[mark] = self._offset(index)

    def mark_gravity(self, _mark: str, _gravity: str) -> None:
        return

    def mark_unset(self, mark: str) -> None:
        self.marks.pop(mark, None)

    def see(self, _index: str) -> None:
        return

    def _offset(self, index: str) -> int:
        if index in self.marks:
            return self.marks[index]
        if index == "end":
            return len(self.text)
        if index == "end-1c":
            return len(self.text)
        if index == "end-2c":
            return max(0, len(self.text) - 1)
        if index == "end-1c linestart":
            return self.text.rfind("\n") + 1
        if index == "1.0":
            return 0
        if index.isdigit():
            return int(index)
        raise AssertionError(f"unsupported index {index!r}")


class FakePane:
    def __init__(
        self,
        orientation: object,
        position: int,
        width: int = 400,
        height: int = 300,
        handle_window: object | None = None,
    ) -> None:
        self.orientation = orientation
        self.position = position
        self.width = width
        self.height = height
        self.handle_window = handle_window

    def get_orientation(self) -> object:
        return self.orientation

    def get_position(self) -> int:
        return self.position

    def get_allocated_width(self) -> int:
        return self.width

    def get_allocated_height(self) -> int:
        return self.height

    def get_handle_window(self) -> object | None:
        return self.handle_window


class FakePaneEvent:
    def __init__(self, x: float, y: float, window: object | None = None) -> None:
        self.x = x
        self.y = y
        self.window = window


class FakeGtkKeyEvent:
    def __init__(self, keyval: int, state: int = 0, hardware_keycode: int | None = None) -> None:
        self.keyval = keyval
        self.state = state
        self.hardware_keycode = hardware_keycode


class FakeGtkButtonEvent:
    def __init__(self, button: int, event_type: object | None = None) -> None:
        self.button = button
        self.type = event_type if event_type is not None else Gdk.EventType.BUTTON_PRESS
        self.x = 0


class FakeTkKeyEvent:
    def __init__(
        self,
        state: int = 0,
        keysym: str = "",
        char: str = "",
        keycode: int | None = None,
    ) -> None:
        self.state = state
        self.keysym = keysym
        self.char = char
        self.keycode = keycode


class FakeGtkTerminal:
    def __init__(self) -> None:
        self.fed: list[object] = []

    def feed_child(self, data: object, *_args: object) -> None:
        self.fed.append(data)


class FakeGtkTextTerminal:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self, *_args: object) -> tuple[str, None]:
        return self.text, None


class FakeGtkCopyTerminal:
    def __init__(
        self,
        *,
        formatted_supported: bool = True,
        has_selection: bool = True,
        text: str = "",
    ) -> None:
        self.formatted_supported = formatted_supported
        self.has_selection = has_selection
        self.text = text
        self.focused = False
        self.formatted_copies = 0
        self.plain_copies = 0

    def grab_focus(self) -> None:
        self.focused = True

    def get_has_selection(self) -> bool:
        return self.has_selection

    def get_text(self, *_args: object) -> tuple[str, None]:
        return self.text, None

    def copy_clipboard_format(self, _format: object) -> None:
        if not self.formatted_supported:
            raise AttributeError("copy_clipboard_format")
        self.formatted_copies += 1

    def copy_clipboard(self) -> None:
        self.plain_copies += 1


class FakeGtkStyleContext:
    def __init__(self) -> None:
        self.classes: set[str] = set()

    def add_class(self, name: str) -> None:
        self.classes.add(name)

    def remove_class(self, name: str) -> None:
        self.classes.discard(name)


class FakeGtkButton:
    def __init__(self) -> None:
        self.text = ""
        self.sensitive = False
        self.opacity = 1.0
        self.visible = False
        self.style_context = FakeGtkStyleContext()

    def get_style_context(self) -> FakeGtkStyleContext:
        return self.style_context

    def set_label(self, text: str) -> None:
        self.text = text

    def set_sensitive(self, value: bool) -> None:
        self.sensitive = value

    def set_opacity(self, value: float) -> None:
        self.opacity = value

    def set_visible(self, value: bool) -> None:
        self.visible = value


class FakeGtkTreeColumn:
    def __init__(self) -> None:
        self.title = ""
        self.sort_indicator = False
        self.sort_order = None

    def set_title(self, text: str) -> None:
        self.title = text

    def set_sort_indicator(self, value: bool) -> None:
        self.sort_indicator = value

    def set_sort_order(self, value: object) -> None:
        self.sort_order = value


class FakeGtkLabel:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class FakeButton:
    def __init__(self) -> None:
        self.text = ""
        self.state = ""

    def configure(self, **kwargs: object) -> None:
        text = kwargs.get("text")
        if isinstance(text, str):
            self.text = text
        state = kwargs.get("state")
        if isinstance(state, str):
            self.state = state


class FakeProcess:
    def __init__(self, running: bool = True) -> None:
        self.running = running
        self.terminated = False

    def poll(self) -> int | None:
        return None if self.running else 0

    def terminate(self) -> None:
        self.terminated = True
        self.running = False


class FakeFrame:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True


class FakeSignalTerminal:
    def __init__(self) -> None:
        self.disconnected: list[object] = []

    def disconnect_by_func(self, callback: object) -> None:
        self.disconnected.append(callback)


class FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeTkTaskTree:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}
        self.selection_iids: list[str] = []
        self.focus_iid: str | None = None
        self.seen_iids: list[str] = []

    def get_children(self) -> tuple[str, ...]:
        return tuple(self.rows)

    def delete(self, *iids: str) -> None:
        for iid in iids:
            self.rows.pop(iid, None)
            if iid in self.selection_iids:
                self.selection_iids.remove(iid)

    def insert(
        self,
        parent: str,
        index: object,
        *,
        iid: str,
        text: str,
        tags: tuple[str, ...],
        values: tuple[object, ...],
    ) -> None:
        self.rows[iid] = {
            "parent": parent,
            "index": index,
            "text": text,
            "tags": tags,
            "values": values,
        }

    def selection(self) -> tuple[str, ...]:
        return tuple(self.selection_iids)

    def selection_remove(self, *iids: str) -> None:
        for iid in iids:
            if iid in self.selection_iids:
                self.selection_iids.remove(iid)

    def selection_set(self, iid: str) -> None:
        self.selection_iids = [iid]

    def focus(self, iid: str) -> None:
        self.focus_iid = iid

    def see(self, iid: str) -> None:
        self.seen_iids.append(iid)


class FakeGtkTaskStore:
    def __init__(self, rows: list[list[object]]) -> None:
        self.rows = rows
        self.set_calls: list[tuple[int, list[int], list[object]]] = []

    def clear(self) -> None:
        self.rows.clear()

    def append(self, row: list[object]) -> None:
        self.rows.append(row)

    def get_iter_first(self) -> int | None:
        return 0 if self.rows else None

    def iter_next(self, row_iter: int) -> int | None:
        next_iter = row_iter + 1
        return next_iter if next_iter < len(self.rows) else None

    def set(self, row_iter: int, columns: list[int], values: list[object]) -> None:
        self.set_calls.append((row_iter, columns, values))
        for column, value in zip(columns, values):
            self.rows[row_iter][column] = value

    def __getitem__(self, row_iter: int) -> list[object]:
        return self.rows[row_iter]


class FakeGtkCheckButton:
    def __init__(self, active: bool = False) -> None:
        self.active = active
        self.inconsistent = False

    def set_active(self, active: bool) -> None:
        self.active = active

    def get_active(self) -> bool:
        return self.active

    def set_inconsistent(self, inconsistent: bool) -> None:
        self.inconsistent = inconsistent


class FakeGtkSelection:
    def __init__(self, model: object, row_iter: object | None) -> None:
        self.model = model
        self.row_iter = row_iter

    def get_selected(self) -> tuple[object, object | None]:
        return self.model, self.row_iter


class FakeGtkDragSelection:
    def __init__(self) -> None:
        self.target = "application/x-agent-workspace-task-action"
        self.data: bytes | None = None

    def get_target(self) -> str:
        return self.target

    def set(self, target: str, _format: int, data: bytes) -> None:
        assert target == self.target
        self.data = data

    def get_data(self) -> bytes | None:
        return self.data


class FakeGtkNotebookEvent:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class FakeGtkAllocation:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


class FakeGtkTabWidget:
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        self.x = x
        self.y = y
        self.allocation = FakeGtkAllocation(width, height)

    def get_visible(self) -> bool:
        return True

    def translate_coordinates(self, _notebook: object, _x: float, _y: float) -> tuple[float, float]:
        return self.x, self.y

    def get_allocation(self) -> FakeGtkAllocation:
        return self.allocation


class FakeGtkNotebook:
    def __init__(self, tabs: list[FakeGtkTabWidget]) -> None:
        self.tabs = tabs
        self.pages = [object() for _tab in tabs]
        self.allocation = FakeGtkAllocation(500, 300)

    def get_n_pages(self) -> int:
        return len(self.pages)

    def get_nth_page(self, index: int) -> object:
        return self.pages[index]

    def get_tab_label(self, page: object) -> FakeGtkTabWidget:
        return self.tabs[self.pages.index(page)]

    def get_allocation(self) -> FakeGtkAllocation:
        return self.allocation

    def get_tab_pos(self) -> Gtk.PositionType:
        return Gtk.PositionType.TOP


class FakeGtkConsoleNotebook:
    def __init__(self, pages: list[object], current_page: int = 0) -> None:
        self.pages = pages
        self.current_page = current_page

    def get_n_pages(self) -> int:
        return len(self.pages)

    def get_current_page(self) -> int:
        return self.current_page

    def get_nth_page(self, index: int) -> object:
        return self.pages[index]

    def page_num(self, page: object) -> int:
        try:
            return self.pages.index(page)
        except ValueError:
            return -1

    def set_current_page(self, index: int) -> None:
        self.current_page = index

    def remove_page(self, index: int) -> None:
        del self.pages[index]
        if not self.pages:
            self.current_page = -1
        elif self.current_page >= len(self.pages):
            self.current_page = len(self.pages) - 1

    def append_page(self, page: object, _tab: object | None = None) -> int:
        self.pages.append(page)
        if self.current_page < 0:
            self.current_page = 0
        return len(self.pages) - 1

    def insert_page(self, page: object, _tab: object | None, index: int) -> int:
        self.pages.insert(index, page)
        if self.current_page < 0:
            self.current_page = 0
        elif index <= self.current_page:
            self.current_page += 1
        return index

    def get_tab_label(self, _page: object) -> object | None:
        return None



def discover_tasks_with_context(task: Path, workspace: Path) -> TaskSummary:
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)
    return discover_tasks(workspace)[0]


__all__ = [name for name in globals() if not name.startswith("__")]
