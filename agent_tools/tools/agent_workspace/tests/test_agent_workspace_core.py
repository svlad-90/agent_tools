from __future__ import annotations

from datetime import datetime
from importlib import resources
from pathlib import Path
import json
import os
import sys

from agent_tools.tools.agent_workspace.core import TASK_CONTEXT_BUDGET
from agent_tools.tools.agent_workspace.core import AGENT_STATUS_MANUAL_ENTRIES
from agent_tools.tools.agent_workspace.core import AGENT_STATUS_MANUAL_MENU_LABEL
from agent_tools.tools.agent_workspace.core import AGENT_STATUS_MANUAL_TITLE
from agent_tools.tools.agent_workspace.core import AGENT_STATUS_MANUAL_USAGE_ENTRIES
from agent_tools.tools.agent_workspace.core import ConsoleChunk
from agent_tools.tools.agent_workspace.core import PAF_HIDE_TASK_ENV_VAR
from agent_tools.tools.agent_workspace.core import TaskAction
from agent_tools.tools.agent_workspace.core import TaskActionParameter
from agent_tools.tools.agent_workspace.core import TaskActionsConfig
from agent_tools.tools.agent_workspace.core import TaskSummary
from agent_tools.tools.agent_workspace.core import load_task_actions_config
from agent_tools.tools.agent_workspace.core import agent_executable
from agent_tools.tools.agent_workspace.core import agent_install_command
from agent_tools.tools.agent_workspace.core import agent_status_tooltip_text
from agent_tools.tools.agent_workspace.core import ai_agent_launch_state
from agent_tools.tools.agent_workspace.core import ai_agent_launch_state_for_selection
from agent_tools.tools.agent_workspace.core import ai_agent_model_settings
from agent_tools.tools.agent_workspace.core import ai_agent_switch_decision
from agent_tools.tools.agent_workspace.core import ai_agent_task_context_prompt
from agent_tools.tools.agent_workspace.core import agent_output_reports_missing_session
from agent_tools.tools.agent_workspace.core import agent_output_reports_turn_complete
from agent_tools.tools.agent_workspace.core import agent_output_requests_permission
from agent_tools.tools.agent_workspace.core import agent_output_state_update
from agent_tools.tools.agent_workspace.core import agent_workspace_runtime_settings
from agent_tools.tools.agent_workspace.core import agent_workspace_setting_or_default
from agent_tools.tools.agent_workspace.core import analyze_agent_output
from agent_tools.tools.agent_workspace.core import acquire_agent_workspace_lock
from agent_tools.tools.agent_workspace.core import build_ai_agent_console_command
from agent_tools.tools.agent_workspace.core import clear_task_agent_session
from agent_tools.tools.agent_workspace.core import clear_task_active_agent_run
from agent_tools.tools.agent_workspace.core import codex_model_choices
from agent_tools.tools.agent_workspace.core import codex_session_id_exists
from agent_tools.tools.agent_workspace.core import discover_tasks
from agent_tools.tools.agent_workspace.core import find_latest_claude_session_id
from agent_tools.tools.agent_workspace.core import find_latest_codex_session_id
from agent_tools.tools.agent_workspace.core import find_task_agent_session_id
from agent_tools.tools.agent_workspace.core import load_task_agent
from agent_tools.tools.agent_workspace.core import load_task_active_agent_run
from agent_tools.tools.agent_workspace.core import load_task_agent_session
from agent_tools.tools.agent_workspace.core import load_task_actions
from agent_tools.tools.agent_workspace.core import load_agent_workspace_settings
from agent_tools.tools.agent_workspace.core import load_task_state
from agent_tools.tools.agent_workspace.core import log_agent_workspace_exception
from agent_tools.tools.agent_workspace.core import parse_console_output
from agent_tools.tools.agent_workspace.core import prepare_task_agent_session
from agent_tools.tools.agent_workspace.core import prepare_ai_agent_launch_command
from agent_tools.tools.agent_workspace.core import render_markdown_chunks
from agent_tools.tools.agent_workspace.core import reset_task_agent_session
from agent_tools.tools.agent_workspace.core import rough_token_count
from agent_tools.tools.agent_workspace.core import save_agent_workspace_settings
from agent_tools.tools.agent_workspace.core import save_task_active_agent_run
from agent_tools.tools.agent_workspace.core import save_task_agent
from agent_tools.tools.agent_workspace.core import save_task_agent_session
from agent_tools.tools.agent_workspace.core import save_task_state
from agent_tools.tools.agent_workspace.core import run_task_action
from agent_tools.tools.agent_workspace.core import run_task_check
from agent_tools.tools.agent_workspace.core import session_marks_task_pending_permission
from agent_tools.tools.agent_workspace.core import session_marks_task_running_agent
from agent_tools.tools.agent_workspace.core import session_is_agent
from agent_tools.tools.agent_workspace.core import session_is_running_agent
from agent_tools.tools.agent_workspace.core import session_should_clear_pending_permission
from agent_tools.tools.agent_workspace.core import task_agent_status_text
from agent_tools.tools.agent_workspace.core import task_agent_session_markers
from agent_tools.tools.agent_workspace.core import task_agent_selection_with_resumable_fallback
from agent_tools.tools.agent_workspace.core import task_agent_has_resumable_state
from agent_tools.tools.agent_workspace.core import task_agent_session_id_is_valid
from agent_tools.tools.agent_workspace.core import task_for_path
from agent_tools.tools.agent_workspace.core import task_has_external_active_agent_run
from agent_tools.tools.agent_workspace.core import task_has_valid_agent_session
from agent_tools.tools.agent_workspace.core import task_status_label
from agent_tools.tools.agent_workspace.core import task_selected_agent_has_resumable_state
from agent_tools.tools.agent_workspace.core import task_state_path
from agent_tools.tools.agent_workspace import core as core_module
from agent_tools.tools.agent_workspace import gtk_open as gtk_open_module
from agent_tools.tools.agent_workspace import gtk_terminal_ui as gtk_terminal_ui_module
from agent_tools.tools.agent_workspace import gtk_ui as gtk_ui_module
from agent_tools.tools.agent_workspace import install_desktop as install_desktop_module
from agent_tools.tools.agent_workspace.gtk_ui import WorkspaceGtkGui
from agent_tools.tools.agent_workspace.gtk_ui import TerminalSession
from agent_tools.tools.agent_workspace.gtk_ui import TRANSLATIONS as GTK_TRANSLATIONS
from agent_tools.tools.agent_workspace.gtk_ui import ai_agent_console_command as gtk_ai_agent_console_command
from agent_tools.tools.agent_workspace.gtk_ui import codex_task_context_message as gtk_codex_task_context_message
from agent_tools.tools.agent_workspace.gtk_ui import task_action_shell_command as gtk_task_action_shell_command
from agent_tools.tools.agent_workspace.gtk_ui import task_check_shell_command as gtk_task_check_shell_command
from agent_tools.tools.agent_workspace.gtk_ui import _artifact_context_action as gtk_artifact_context_action
from agent_tools.tools.agent_workspace.gtk_ui import _artifact_delete_paths as gtk_artifact_delete_paths
from agent_tools.tools.agent_workspace.gtk_ui import _artifact_selectable_path as gtk_artifact_selectable_path
from agent_tools.tools.agent_workspace.gtk_ui import _artifact_updated_label as gtk_artifact_updated_label
from agent_tools.tools.agent_workspace.gtk_ui import _is_pane_separator_event as gtk_is_pane_separator_event
from agent_tools.tools.agent_workspace.gtk_ui import _notebook_event_in_empty_tab_area as gtk_notebook_event_in_empty_tab_area
from agent_tools.tools.agent_workspace.gtk_ui import open_containing_folder as gtk_open_containing_folder
from agent_tools.tools.agent_workspace.gtk_ui import _svg_open_command as gtk_svg_open_command
from agent_tools.tools.agent_workspace.gtk_ui import _task_artifact_entries as gtk_task_artifact_entries
from agent_tools.tools.agent_workspace.gtk_ui import _task_init_command as gtk_task_init_command
from agent_tools.tools.agent_workspace.gtk_ui import _task_actions_signature as gtk_task_actions_signature
from agent_tools.tools.agent_workspace.gtk_ui import _task_path_for_name as gtk_task_path_for_name
from agent_tools.tools.agent_workspace.gtk_ui import _task_row_style as gtk_task_row_style
from agent_tools.tools.agent_workspace.gtk_ui import _copy_terminal_selection as gtk_copy_terminal_selection
from agent_tools.tools.agent_workspace.gtk_ui import _terminal_clipboard_shortcut as gtk_terminal_clipboard_shortcut
from agent_tools.tools.agent_workspace.gtk_ui import _terminal_palette as gtk_terminal_palette
from agent_tools.tools.agent_workspace.gtk_ui import _terminal_session_sort_key as gtk_terminal_session_sort_key
from agent_tools.tools.agent_workspace.gtk_ui import _terminal_tab_label as gtk_terminal_tab_label
from agent_tools.tools.agent_workspace.gtk_ui import _terminal_text_tail as gtk_terminal_text_tail
from agent_tools.tools.agent_workspace.gtk_ui import _theme_colors as gtk_theme_colors
from agent_tools.tools.agent_workspace.gtk_ui import _set_task_action_drag_selection as gtk_set_task_action_drag_selection
from agent_tools.tools.agent_workspace.gtk_ui import _task_action_drag_selection_id as gtk_task_action_drag_selection_id
from agent_tools.tools.agent_workspace.gtk_ui import _agent_workspace_icon_path as gtk_agent_workspace_icon_path
from agent_tools.tools.agent_workspace.gtk_ui import _agent_workspace_runtime_icon_path as gtk_agent_workspace_runtime_icon_path
from agent_tools.tools.agent_workspace.ui import codex_console_command
from agent_tools.tools.agent_workspace.ui import console_paste_text
from agent_tools.tools.agent_workspace.ui import console_tab_title
from agent_tools.tools.agent_workspace.ui import ConsoleSession
from agent_tools.tools.agent_workspace.ui import codex_task_context_message
from agent_tools.tools.agent_workspace.ui import embedded_terminal_command
from agent_tools.tools.agent_workspace.ui import ai_agent_console_command
from agent_tools.tools.agent_workspace.ui import task_action_shell_command
from agent_tools.tools.agent_workspace.ui import task_check_shell_command
from agent_tools.tools.agent_workspace.ui import _tk_control_shortcut
from agent_tools.tools.agent_workspace.ui import AgentWorkspace
from agent_tools.tools.agent_workspace.actions import main as actions_main
from agent_tools.tools.agent_workspace.task_action_files import task_action_code_path
from agent_tools.tools.agent_workspace.task_action_menu import task_action_menu_state
from agent_tools.tools.agent_workspace.task_action_menu import task_parameter_menu_state
from agent_tools.tools.agent_workspace.task_action_menu import task_reorder_label_key
from agent_tools.tools.agent_workspace.task_action_menu import task_shortcut_menu_state
from agent_tools.tools.agent_workspace.task_action_model import add_task_shortcut
from agent_tools.tools.agent_workspace.task_action_model import delete_parameter_set_value
from agent_tools.tools.agent_workspace.task_action_model import delete_task_shortcut
from agent_tools.tools.agent_workspace.task_action_model import parameter_dialog_field_names
from agent_tools.tools.agent_workspace.task_action_model import reorder_task_action_data
from agent_tools.tools.agent_workspace.task_action_model import upsert_parameter_set_value
from agent_tools.tools.agent_workspace.task_action_state import bindings_for_action_run
from agent_tools.tools.agent_workspace.task_action_state import parameter_button_label
from agent_tools.tools.agent_workspace.task_action_state import parameter_values
from agent_tools.tools.agent_workspace.task_action_state import selected_parameter_value
from agent_tools.tools.agent_workspace.task_action_state import shortcuts_for_action
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
    def __init__(self, orientation: object, position: int) -> None:
        self.orientation = orientation
        self.position = position

    def get_orientation(self) -> object:
        return self.orientation

    def get_position(self) -> int:
        return self.position


class FakePaneEvent:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class FakeGtkKeyEvent:
    def __init__(self, keyval: int, state: int = 0, hardware_keycode: int | None = None) -> None:
        self.keyval = keyval
        self.state = state
        self.hardware_keycode = hardware_keycode


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


def test_discover_tasks_reports_description_context_and_budget(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n\nshort\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text("word " * (TASK_CONTEXT_BUDGET + 1), encoding="utf-8")

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["sample-task"]
    assert tasks[0].has_description
    assert tasks[0].has_context
    assert tasks[0].description_tokens > 0
    assert tasks[0].context_over_budget


def test_discover_tasks_sorts_names_case_insensitively(tmp_path: Path) -> None:
    for name in ("beta", "Alpha"):
        task = tmp_path / "tasks" / name
        task.mkdir(parents=True)
        (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["Alpha", "beta"]


def test_run_task_check_returns_text_report(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    for rel_path in ("dev", "Dockerfile", "scripts", "report/diff", "report/puml"):
        (task / rel_path).mkdir(parents=True, exist_ok=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")

    report = run_task_check(discover_tasks(tmp_path)[0], tmp_path)

    assert "Summary:" in report
    assert "PASS task-description" not in report


def test_agent_workspace_actions_task_check_uses_compact_output(tmp_path: Path, capsys: object) -> None:
    task = tmp_path / "tasks" / "sample-task"
    for rel_path in ("dev", "Dockerfile", "scripts", "report/diff", "report/puml"):
        (task / rel_path).mkdir(parents=True, exist_ok=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")

    exit_code = actions_main(["task-check", "--workspace", str(tmp_path), "--task", str(task)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Summary:" in captured.out
    assert "PASS task-description" not in captured.out


def test_task_table_keyboard_activation_is_ignored() -> None:
    tk_gui = object.__new__(AgentWorkspace)
    gtk_gui = object.__new__(WorkspaceGtkGui)
    ctrl = int(Gdk.ModifierType.CONTROL_MASK)

    assert tk_gui._ignore_task_tree_keyboard_activation(object()) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="Return")) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="a", char="a")) == "break"
    assert tk_gui._on_task_tree_key(FakeTkKeyEvent(keysym="Down")) is None
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_Return))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_KP_Enter))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_space))
    assert gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_a))
    assert not gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_a, state=ctrl))
    assert not gtk_gui._on_task_view_key_press(object(), FakeGtkKeyEvent(Gdk.KEY_Down))


def test_gtk_task_artifact_entries_groups_task_outputs(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    (task / "report" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "diff" / "review.html").write_text("<html>", encoding="utf-8")
    (task / "report" / "diff" / "review.diff").write_text("diff", encoding="utf-8")
    (task / "report" / "diff" / "comments.json").write_text("{}", encoding="utf-8")
    (task / "report" / "puml" / "flow.svg").write_text("<svg>", encoding="utf-8")
    (task / "report" / "puml" / "flow.puml").write_text("@startuml", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    entries = gtk_task_artifact_entries(summary)

    assert [(entry.group, entry.path.name) for entry in entries] == [
        ("logs", "runtime.log"),
        ("diagrams", "flow.puml"),
        ("diagrams", "flow.svg"),
        ("diff_reports", "comments.json"),
        ("diff_reports", "review.diff"),
        ("diff_reports", "review.html"),
        ("artifacts", "notes.md"),
    ]

def test_gtk_task_artifact_entries_can_sort_by_updated_time(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report").mkdir(parents=True)
    older = task / "report" / "a-notes.md"
    newer = task / "report" / "b-notes.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert [entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="name")] == [
        "a-notes.md",
        "b-notes.md",
    ]
    assert [
        entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="updated", descending=True)
    ] == [
        "b-notes.md",
        "a-notes.md",
    ]
    assert [
        entry.path.name for entry in gtk_task_artifact_entries(summary, sort_column="updated", descending=False)
    ] == [
        "a-notes.md",
        "b-notes.md",
    ]


def test_gtk_artifact_sort_column_click_toggles_indicator() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui.artifact_name_column = FakeGtkTreeColumn()
    gui.artifact_updated_column = FakeGtkTreeColumn()
    gui.selected_task = None
    gui._artifacts_tab_active = lambda: False

    gui._update_artifact_sort_indicators()

    assert gui.artifact_name_column.sort_indicator is True
    assert gui.artifact_name_column.sort_order == Gtk.SortType.ASCENDING
    assert gui.artifact_updated_column.sort_indicator is False

    gui._set_artifact_sort("updated")

    assert gui.artifact_name_column.sort_indicator is False
    assert gui.artifact_updated_column.sort_indicator is True
    assert gui.artifact_updated_column.sort_order == Gtk.SortType.DESCENDING

    gui._set_artifact_sort("updated")

    assert gui.artifact_updated_column.sort_order == Gtk.SortType.ASCENDING


def test_gtk_artifact_manual_refresh_loads_selected_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    calls: list[TaskSummary] = []
    gui._load_task_artifacts = lambda task: calls.append(task)  # type: ignore[method-assign]

    gui._refresh_selected_task_artifacts()

    assert calls == [summary]


def test_gtk_artifact_delete_paths_include_hidden_group_files(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    files = {
        "report/runtime.log": "log",
        "report/notes.md": "notes",
        "report/diff/review.html": "<html>",
        "report/diff/review.diff": "diff",
        "report/diff/comments.json": "{}",
        "report/puml/flow.svg": "<svg>",
        "report/puml/flow.puml": "@startuml",
    }
    for rel_path, content in files.items():
        (task / rel_path).write_text(content, encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    def rels(paths: list[Path]) -> list[str]:
        return sorted(str(path.relative_to(task)) for path in paths)

    assert gtk_artifact_delete_paths(summary, artifact_path=task / "report" / "runtime.log") == [
        task / "report" / "runtime.log"
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="logs")) == ["report/runtime.log"]
    assert rels(gtk_artifact_delete_paths(summary, group="diagrams")) == [
        "report/puml/flow.puml",
        "report/puml/flow.svg",
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="diff_reports")) == [
        "report/diff/comments.json",
        "report/diff/review.diff",
        "report/diff/review.html",
    ]
    assert rels(gtk_artifact_delete_paths(summary, group="artifacts")) == ["report/notes.md"]
    assert rels(gtk_artifact_delete_paths(summary, delete_all=True)) == sorted(files)


def test_gtk_artifact_context_action_matches_clicked_area(tmp_path: Path) -> None:
    artifact = tmp_path / "tasks" / "sample-task" / "report" / "runtime.log"

    assert gtk_artifact_context_action(artifact, "logs") == "artifact"
    assert gtk_artifact_context_action(None, "logs") == "group"
    assert gtk_artifact_context_action(None, None) == "all"


def test_gtk_artifact_selectable_path_stays_inside_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    artifact_dir = task / "report" / "diff"
    artifact_dir.mkdir(parents=True)
    artifact_path = artifact_dir / "review.html"
    artifact_path.write_text("<html>", encoding="utf-8")
    outside = tmp_path / "outside.html"
    outside.write_text("outside", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert gtk_artifact_selectable_path(summary, artifact_path) == artifact_path
    assert gtk_artifact_selectable_path(summary, artifact_dir) is None
    assert gtk_artifact_selectable_path(summary, outside) is None


def test_gtk_artifact_updated_label_formats_timestamp() -> None:
    assert gtk_artifact_updated_label(0) == ""
    assert gtk_artifact_updated_label(100) == datetime.fromtimestamp(100).strftime("%Y-%m-%d %H:%M")


def test_gtk_open_containing_folder_falls_back_to_parent_on_linux(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "report" / "review.html"
    artifact_path.parent.mkdir()
    artifact_path.write_text("<html>", encoding="utf-8")
    calls: list[Path] = []

    monkeypatch.setattr(gtk_open_module.sys, "platform", "linux")
    monkeypatch.setattr(gtk_open_module, "_show_file_in_freedesktop_file_manager", lambda _path: False)
    monkeypatch.setattr(gtk_open_module, "open_path", lambda path: calls.append(path))

    gtk_open_containing_folder(artifact_path)

    assert calls == [artifact_path.parent]


def test_rough_token_count_uses_words_and_character_fallback() -> None:
    assert rough_token_count("one two three") == 4
    assert rough_token_count("x" * 20) == 5


def test_render_markdown_chunks_formats_common_blocks() -> None:
    chunks = render_markdown_chunks(
        "# Title\n\n"
        "## Section\n"
        "- `item`\n"
        "| Role | Path |\n"
        "| --- | --- |\n"
        "| `HAL` | dev/hal |\n"
        "\n```"
        "\n"
        "code()\n"
        "```\n"
    )

    rendered = [(chunk.text.strip(), chunk.tag) for chunk in chunks if chunk.text.strip()]

    assert rendered == [
        ("Title", "h1"),
        ("Section", "h2"),
        ("- item", "list"),
        (
            "+----------------------------------------------------------------------------------------------+\n"
            "| Row 1                                                                                        |\n"
            "| Role: HAL                                                                                    |\n"
            "| Path: dev/hal                                                                                |\n"
            "+----------------------------------------------------------------------------------------------+",
            "table",
        ),
        ("code()", "code"),
    ]


def test_codex_task_context_message_points_at_selected_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    message = codex_task_context_message(summary, tmp_path)

    assert "workspace task `sample-task`" in message
    assert f"Workspace: {tmp_path}" in message
    assert f"Task directory: {task}" in message
    assert "TASK_DESCRIPTION.md" in message
    assert "TASK_CONTEXT.md" in message


def test_core_ai_agent_task_context_prompt_supports_optional_suffix(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    plain = ai_agent_task_context_prompt(summary, tmp_path)
    suffixed = ai_agent_task_context_prompt(summary, tmp_path, "Reply in Russian.")

    assert plain.endswith("treat them as the active task context.")
    assert "Reply in Russian." not in plain
    assert suffixed.endswith("treat them as the active task context. Reply in Russian.")


def test_codex_console_command_passes_prompt_and_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary)

    assert command[-4:] == [
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        codex_task_context_message(summary, tmp_path),
    ]


def test_core_ai_agent_command_builder_handles_codex_and_claude(tmp_path: Path) -> None:
    prompt = "task prompt"

    codex_command = build_ai_agent_console_command(
        tmp_path,
        prompt,
        "codex",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        model="gpt-5.5",
        reasoning_effort="medium",
    )
    claude_command = build_ai_agent_console_command(
        tmp_path,
        prompt,
        "claude",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        resume=True,
        resume_session_id="019feba2-e25e-76e1-9468-aa399758268f",
        model="sonnet",
        reasoning_effort="low",
    )

    assert codex_command == [
        "codex-bin",
        "--model",
        "gpt-5.5",
        "-c",
        'model_reasoning_effort="medium"',
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        prompt,
    ]
    assert claude_command == [
        "claude-bin",
        "--permission-mode",
        "auto",
        "--model",
        "sonnet",
        "--effort",
        "low",
        "--resume",
        "019feba2-e25e-76e1-9468-aa399758268f",
    ]


def test_prepare_ai_agent_launch_command_builds_command_from_session_and_model_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)

    launch = prepare_ai_agent_launch_command(
        summary,
        tmp_path,
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
        codex_executable="codex-bin",
        claude_executable="claude-bin",
        prompt_suffix="Reply in Russian.",
    )

    assert launch.session_state.resume
    assert launch.session_state.session_id == session_id
    assert launch.model_settings.model == "gpt-5.5"
    assert launch.model_settings.reasoning_effort == "medium"
    assert launch.command == [
        "codex-bin",
        "--model",
        "gpt-5.5",
        "-c",
        'model_reasoning_effort="medium"',
        "resume",
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        session_id,
    ]


def test_codex_console_command_can_resume_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    command = codex_console_command(tmp_path, summary, resume=True, resume_session_id=session_id)

    assert command[-5:] == [
        "resume",
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        session_id,
    ]
    assert codex_task_context_message(summary, tmp_path) not in command


def test_codex_console_command_uses_model_and_reasoning(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary, model="gpt-5.5", reasoning_effort="low")

    assert command[:5] == [command[0], "--model", "gpt-5.5", "-c", 'model_reasoning_effort="low"']


def test_codex_console_command_resume_last_keeps_model_options_and_omits_prompt(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary, resume=True, model="gpt-5.5", reasoning_effort="medium")

    assert command[:5] == [command[0], "--model", "gpt-5.5", "-c", 'model_reasoning_effort="medium"']
    assert command[-5:] == ["resume", "--cd", str(tmp_path), "--no-alt-screen", "--last"]
    assert codex_task_context_message(summary, tmp_path) not in command


def test_gtk_and_tk_codex_command_builders_match(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    tk_command = ai_agent_console_command(
        tmp_path,
        summary,
        "codex",
        model="gpt-5.5",
        reasoning_effort="medium",
    )
    gtk_command = gtk_ai_agent_console_command(
        tmp_path,
        summary,
        "codex",
        model="gpt-5.5",
        reasoning_effort="medium",
    )

    assert gtk_command[:-1] == tk_command[:-1]
    assert "--permission-mode" not in tk_command
    assert "--permission-mode" not in gtk_command
    assert "workspace task `sample-task`" in gtk_command[-1]
    assert "workspace task `sample-task`" in tk_command[-1]


def test_ai_agent_console_command_supports_claude(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude")

    assert command[0].endswith("claude")
    assert command[1:3] == ["--permission-mode", "auto"]
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_uses_claude_model_and_effort(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude", model="sonnet", reasoning_effort="low")

    assert command[:7] == [command[0], "--permission-mode", "auto", "--model", "sonnet", "--effort", "low"]
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_starts_claude_when_resume_has_no_session_id(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = ai_agent_console_command(tmp_path, summary, "claude", resume=True)

    assert command[0].endswith("claude")
    assert command[1:3] == ["--permission-mode", "auto"]
    assert "--continue" not in command
    assert "workspace task `sample-task`" in command[-1]


def test_ai_agent_console_command_can_use_claude_session_id(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    first_command = ai_agent_console_command(tmp_path, summary, "claude", resume_session_id=session_id)
    resume_command = ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        resume=True,
        resume_session_id=session_id,
    )

    assert first_command[:5] == [first_command[0], "--permission-mode", "auto", "--session-id", session_id]
    assert "workspace task `sample-task`" in first_command[-1]
    assert resume_command == [resume_command[0], "--permission-mode", "auto", "--resume", session_id]


def test_gtk_and_tk_claude_command_builders_match(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    tk_command = ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        resume=True,
        resume_session_id=session_id,
        model="sonnet",
        reasoning_effort="medium",
    )
    gtk_command = gtk_ai_agent_console_command(
        tmp_path,
        summary,
        "claude",
        resume=True,
        resume_session_id=session_id,
        model="sonnet",
        reasoning_effort="medium",
    )

    assert gtk_command == tk_command


def test_embedded_terminal_command_uses_vte_launcher(tmp_path: Path) -> None:
    command = embedded_terminal_command(
        socket_id=42,
        cwd=tmp_path,
        command=["codex", "--cd", str(tmp_path)],
        font_size=16,
        theme="dark",
    )

    assert command[1:] == [
        "-m",
        "agent_tools.tools.agent_workspace.vte_terminal",
        "--socket-id",
        "42",
        "--cwd",
        str(tmp_path),
        "--font-size",
        "16",
        "--theme",
        "dark",
        "--",
        "codex",
        "--cd",
        str(tmp_path),
    ]


def test_task_check_shell_command_runs_from_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = task_check_shell_command(tmp_path, summary)
    gtk_command = gtk_task_check_shell_command(tmp_path, summary)

    for command in (command, gtk_command):
        assert command.startswith(f"cd {tmp_path} && ")
        assert "agent_tools.tools.agent_workspace.actions" in command
        assert "task-check" in command
        assert str(task) in command


def test_task_action_shell_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = task_action_shell_command(action)

    assert command.startswith(f"cd {tmp_path / 'scripts'} && bash -lc ")
    assert "report/logs" in command
    assert "unit-$(date +%Y%m%d-%H%M%S).log" in command
    assert "tee -a" in command
    assert "FLAG=" in command
    assert "hello world" in command
    assert f"{PAF_HIDE_TASK_ENV_VAR}=1" in command
    assert "python -m pytest" in command
    assert "exit ${PIPESTATUS[0]}" in command


def test_gtk_task_action_shell_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = gtk_task_action_shell_command(action)

    assert command.startswith(f"cd {tmp_path / 'scripts'} && bash -lc ")
    assert "report/logs" in command
    assert "unit-$(date +%Y%m%d-%H%M%S).log" in command
    assert "tee -a" in command
    assert "FLAG=" in command
    assert "hello world" in command
    assert f"{PAF_HIDE_TASK_ENV_VAR}=1" in command
    assert "python -m pytest" in command
    assert "exit ${PIPESTATUS[0]}" in command


def test_gtk_pane_separator_hit_test_uses_orientation() -> None:
    from gi.repository import Gtk

    horizontal = FakePane(Gtk.Orientation.HORIZONTAL, 100)
    vertical = FakePane(Gtk.Orientation.VERTICAL, 200)

    assert gtk_is_pane_separator_event(horizontal, FakePaneEvent(105, 40))
    assert not gtk_is_pane_separator_event(horizontal, FakePaneEvent(120, 100))
    assert gtk_is_pane_separator_event(vertical, FakePaneEvent(40, 205))
    assert not gtk_is_pane_separator_event(vertical, FakePaneEvent(200, 220))


def test_gtk_task_path_for_name_stays_under_tasks(tmp_path: Path) -> None:
    assert gtk_task_path_for_name(tmp_path, "sample-task") == tmp_path / "tasks" / "sample-task"
    assert gtk_task_path_for_name(tmp_path, "") is None
    assert gtk_task_path_for_name(tmp_path, "..") is None
    assert gtk_task_path_for_name(tmp_path, "../outside") is None
    assert gtk_task_path_for_name(tmp_path, "nested/task") is None


def test_gtk_task_init_command_uses_task_check_layout(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks" / "sample-task"

    command = gtk_task_init_command(tmp_path, task_path)

    assert command[:3] == [sys.executable, "-m", "agent_tools.paf_workspace.task_check"]
    assert command[3:] == [
        str(task_path),
        "--workspace",
        str(tmp_path),
        "--init-layout",
    ]

    private_command = gtk_task_init_command(tmp_path, task_path, privacy="private")
    assert private_command == command + ["--privacy", "private"]


def test_gtk_task_actions_signature_tracks_file_mtime(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert gtk_task_actions_signature(summary) == (task / "TASK_ACTIONS.json", None)

    actions_file = task / "TASK_ACTIONS.json"
    actions_file.write_text('{"actions": []}', encoding="utf-8")

    assert gtk_task_actions_signature(summary)[0] == actions_file
    assert gtk_task_actions_signature(summary)[1] is not None


def test_console_tab_title_numbers_shells_only() -> None:
    assert console_tab_title(1, "shell") == "shell 1"
    assert console_tab_title(2, "shell") == "shell 2"
    assert console_tab_title(0, "codex") == "Codex"
    assert console_tab_title(0, "claude") == "Claude Code"


def test_agent_workspace_settings_persist_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"

    save_agent_workspace_settings(
        {
            "text_font_size": 17,
            "button_font_size": 14,
            "theme": "dark",
            "language": "ru",
            "default_agent": "claude",
            "default_codex_model": "gpt-5.5",
            "default_codex_reasoning": "medium",
            "default_claude_model": "sonnet",
            "default_claude_effort": "low",
            "geometry": "1200x800+10+20",
        },
        settings_path,
    )

    assert load_agent_workspace_settings(settings_path) == {
        "text_font_size": 17,
        "button_font_size": 14,
        "theme": "dark",
        "language": "ru",
        "default_agent": "claude",
        "default_codex_model": "gpt-5.5",
        "default_codex_reasoning": "medium",
        "default_claude_model": "sonnet",
        "default_claude_effort": "low",
        "geometry": "1200x800+10+20",
    }


def test_agent_workspace_settings_migrate_old_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"font_size": 17}', encoding="utf-8")

    assert load_agent_workspace_settings(settings_path) == {"text_font_size": 17}


def test_agent_workspace_setting_or_default_treats_blank_as_missing() -> None:
    settings = {
        "default_codex_model": "",
        "default_codex_reasoning": " ",
        "default_claude_model": " sonnet ",
    }

    assert agent_workspace_setting_or_default(settings, "default_codex_model", "gpt-5.5") == "gpt-5.5"
    assert agent_workspace_setting_or_default(settings, "default_codex_reasoning", "medium") == "medium"
    assert agent_workspace_setting_or_default(settings, "default_claude_model", "opus") == "sonnet"
    assert agent_workspace_setting_or_default(settings, "default_claude_effort", "medium") == "medium"


def test_agent_workspace_runtime_settings_normalizes_ui_defaults() -> None:
    settings = agent_workspace_runtime_settings(
        {
            "text_font_size": 17,
            "button_font_size": 15,
            "theme": "dark",
            "language": "en",
            "default_agent": "claude",
            "default_codex_model": "",
            "default_codex_reasoning": " ",
            "default_claude_model": "",
            "default_claude_effort": "",
            "geometry": "1280x900+1+2",
        },
        default_font_size=13,
    )

    assert settings.text_font_size == 17
    assert settings.button_font_size == 15
    assert settings.theme == "dark"
    assert settings.language == "en"
    assert settings.default_agent == "claude"
    assert settings.default_codex_model == "gpt-5.5"
    assert settings.default_codex_reasoning == "medium"
    assert settings.default_claude_model == "sonnet"
    assert settings.default_claude_effort == "medium"
    assert settings.window_geometry == "1280x900+1+2"


def test_agent_workspace_runtime_settings_falls_back_for_invalid_values() -> None:
    settings = agent_workspace_runtime_settings(
        {
            "text_font_size": "17",
            "button_font_size": "15",
            "theme": "blue",
            "language": "bad",
            "default_agent": "bad",
            "geometry": 42,
        },
        default_font_size=13,
        default_language="uk",
    )

    assert settings.text_font_size == 13
    assert settings.button_font_size == 13
    assert settings.theme == "light"
    assert settings.language == "uk"
    assert settings.default_agent == "codex"
    assert settings.window_geometry == "1180x760"


def test_ai_agent_model_settings_selects_per_agent_defaults() -> None:
    codex_settings = ai_agent_model_settings(
        "codex",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
    )
    claude_settings = ai_agent_model_settings(
        "claude",
        codex_model="gpt-5.5",
        codex_reasoning="medium",
        claude_model="sonnet",
        claude_effort="low",
    )

    assert codex_settings.model == "gpt-5.5"
    assert codex_settings.reasoning_effort == "medium"
    assert claude_settings.model == "sonnet"
    assert claude_settings.reasoning_effort == "low"


def test_ai_agent_model_settings_preserves_blank_values() -> None:
    settings = ai_agent_model_settings(
        "unknown",
        codex_model="",
        codex_reasoning="",
        claude_model="sonnet",
        claude_effort="medium",
    )

    assert settings.model == ""
    assert settings.reasoning_effort == ""


def test_ai_agent_launch_state_prefers_running_over_restore() -> None:
    state = ai_agent_launch_state(running=True, resumable=True)

    assert state.label_key == "ai_agent_running"
    assert state.reset_enabled


def test_ai_agent_launch_state_allows_reset_for_running_agent_without_resume() -> None:
    state = ai_agent_launch_state(running=True, resumable=False)

    assert state.label_key == "ai_agent_running"
    assert state.reset_enabled


def test_ai_agent_launch_state_reports_restore_only_when_resumable() -> None:
    restore_state = ai_agent_launch_state(running=False, resumable=True)
    new_state = ai_agent_launch_state(running=False, resumable=False)

    assert restore_state.label_key == "restore_ai_agent_session"
    assert restore_state.reset_enabled
    assert new_state.label_key == "run_ai_agent"
    assert not new_state.reset_enabled


def test_ai_agent_launch_state_for_selection_handles_missing_task(tmp_path: Path) -> None:
    state = ai_agent_launch_state_for_selection(
        None,
        tmp_path,
        "codex",
        running_agent="codex",
    )

    assert state.label_key == "run_ai_agent"
    assert not state.reset_enabled


def test_ai_agent_launch_state_for_selection_prefers_matching_running_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)

    running_state = ai_agent_launch_state_for_selection(
        summary,
        tmp_path,
        "codex",
        running_agent="codex",
    )
    other_agent_state = ai_agent_launch_state_for_selection(
        summary,
        tmp_path,
        "codex",
        running_agent="claude",
    )

    assert running_state.label_key == "ai_agent_running"
    assert running_state.reset_enabled
    assert other_agent_state.label_key == "restore_ai_agent_session"
    assert other_agent_state.reset_enabled


def test_ai_agent_switch_decision_handles_no_current_agent() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent=None,
        start_if_changed=True,
    )

    assert decision.action == "start_selected"
    assert decision.agent == "claude"
    assert decision.current_agent is None


def test_ai_agent_switch_decision_activates_matching_current_agent() -> None:
    decision = ai_agent_switch_decision(
        "codex",
        current_agent="codex",
        start_if_changed=True,
    )

    assert decision.action == "activate_current"
    assert decision.agent == "codex"
    assert decision.current_agent == "codex"


def test_ai_agent_switch_decision_keeps_current_when_selection_only() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent="codex",
        start_if_changed=False,
    )

    assert decision.action == "keep_current"
    assert decision.agent == "codex"
    assert decision.current_agent == "codex"


def test_ai_agent_switch_decision_confirms_switch_when_starting_changed_agent() -> None:
    decision = ai_agent_switch_decision(
        "claude",
        current_agent="codex",
        start_if_changed=True,
    )

    assert decision.action == "confirm_switch"
    assert decision.agent == "claude"
    assert decision.current_agent == "codex"


def test_agent_workspace_settings_clamp_bad_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        (
            '{"text_font_size": 100, "button_font_size": 4, '
            '"theme": "blue", "language": "bad", "default_agent": "bad", '
            '"default_codex_reasoning": "bad", "default_claude_effort": "bad", "geometry": "bad"}'
        ),
        encoding="utf-8",
    )

    assert load_agent_workspace_settings(settings_path) == {
        "text_font_size": 28,
        "button_font_size": 8,
    }


def test_task_agent_state_persists_per_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    assert load_task_agent(summary, "claude") == "claude"

    save_task_agent(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"


def test_task_agent_session_state_preserves_agent_selection(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "codex", session_id=session_id)
    session = load_task_agent_session(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"
    assert session.resume is True
    assert session.session_id == session_id


def test_find_task_agent_session_id_is_scoped_to_agent_type(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    claude_session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert find_task_agent_session_id(summary, workspace, "claude") == claude_session_id
    assert find_task_agent_session_id(summary, workspace, "codex") is None


def test_clear_task_agent_session_clears_current_saved_agent_type(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    claude_session_id = "019feba2-e25e-76e1-9468-aa3997582690"

    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert clear_task_agent_session(summary, "claude")

    assert load_task_agent_session(summary, "claude").session_id is None


def test_save_task_agent_session_keeps_only_latest_agent_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    claude_session_id = "019feba2-e25e-76e1-9468-aa3997582690"

    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id=claude_session_id)

    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "codex").session_id is None
    assert load_task_agent_session(summary, "claude").session_id == claude_session_id


def test_task_active_agent_run_tracks_external_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)

    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    active = load_task_active_agent_run(summary)
    assert active is not None
    assert active.agent == "codex"
    assert task_has_external_active_agent_run(summary, set())
    assert not task_has_external_active_agent_run(summary, {"run-1"})
    assert not clear_task_active_agent_run(summary, run_id="other")
    assert clear_task_active_agent_run(summary, run_id="run-1", agent="codex")
    assert load_task_active_agent_run(summary) is None


def test_task_active_agent_run_clears_non_workspace_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: False)

    assert load_task_active_agent_run(summary) is None
    assert "active_agent_run" not in load_task_state(summary)


def test_task_active_agent_run_accepts_legacy_live_workspace_owner(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_state(
        summary,
        {
            "active_agent_run": {
                "agent": "codex",
                "owner_pid": os.getpid(),
                "run_id": "run-1",
            }
        },
    )
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr(core_module, "_current_boot_id", lambda: "current-boot")
    monkeypatch.setattr(core_module, "_process_start_time_ticks", lambda _pid: 100)
    monkeypatch.setattr(core_module, "_process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) - 10)

    active = load_task_active_agent_run(summary)

    assert active is not None
    assert active.run_id == "run-1"
    assert task_has_external_active_agent_run(summary, set())


def test_task_active_agent_run_clears_reused_pid_after_reboot(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr(core_module, "_process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) + 10)

    assert load_task_active_agent_run(summary) is None
    assert "active_agent_run" not in load_task_state(summary)


def test_tk_selectable_task_iid_skips_external_active_tasks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (locked_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (open_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    save_task_active_agent_run(locked, "codex", "external-run", owner_pid=os.getpid())
    gui = object.__new__(AgentWorkspace)
    gui.tasks = [locked, open_task]
    gui.console_sessions = {}

    assert gui._selectable_task_iid("locked-task") == "1"
    assert gui._selectable_task_iid("open-task") == "1"

    save_task_active_agent_run(open_task, "claude", "second-external-run", owner_pid=os.getpid())
    assert gui._selectable_task_iid(None) is None


def test_tk_refresh_tasks_selects_open_task_when_previous_is_locked(tmp_path: Path, monkeypatch) -> None:
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (locked_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (open_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    tree = FakeTkTaskTree()
    gui = object.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.selected_task = locked
    gui.task_tree = tree
    gui.summary_var = FakeStringVar("")
    gui.tasks = []
    gui._task_label = lambda task: task.name
    gui._task_tags = lambda _task: ()
    gui._task_agent_status = lambda _task: "□"
    gui._task_is_external_active = lambda task: task.path == locked.path
    gui._on_task_selected = lambda _event: None
    monkeypatch.setattr(core_module, "discover_tasks", lambda _workspace: [locked, open_task])

    gui.refresh_tasks()

    assert gui.tasks == [locked, open_task]
    assert tree.rows["0"]["text"] == "locked-task"
    assert tree.rows["1"]["text"] == "open-task"
    assert tree.selection() == ("1",)
    assert tree.focus_iid == "1"
    assert tree.seen_iids == ["1"]
    assert gui.summary_var.get() == "2 tasks, 0 over context budget"


def test_tk_refresh_tasks_clears_selection_when_all_tasks_locked(tmp_path: Path, monkeypatch) -> None:
    first_path = tmp_path / "tasks" / "first-task"
    second_path = tmp_path / "tasks" / "second-task"
    first_path.mkdir(parents=True)
    second_path.mkdir(parents=True)
    (first_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (first_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (second_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (second_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = discover_tasks(tmp_path)
    tree = FakeTkTaskTree()
    tree.selection_set("stale")
    gui = object.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.selected_task = tasks[0]
    gui.task_tree = tree
    gui.summary_var = FakeStringVar("")
    gui.tasks = []
    gui._task_label = lambda task: task.name
    gui._task_tags = lambda _task: ()
    gui._task_agent_status = lambda _task: "×"
    gui._task_is_external_active = lambda _task: True
    gui._clear_selected_task_view = lambda: setattr(gui, "selected_task", None)
    gui._on_task_selected = lambda _event: None
    monkeypatch.setattr(core_module, "discover_tasks", lambda _workspace: tasks)

    gui.refresh_tasks()

    assert tree.selection() == ()
    assert gui.selected_task is None


def test_gtk_selectable_task_iter_skips_external_active_tasks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (locked_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (open_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    save_task_active_agent_run(locked, "codex", "external-run", owner_pid=os.getpid())
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_store = FakeGtkTaskStore([["", "locked-task", locked], ["", "open-task", open_task]])
    gui.terminal_sessions = {}

    assert gui._selectable_task_iter("locked-task") == 1
    assert gui._selectable_task_iter("open-task") == 1

    save_task_active_agent_run(open_task, "claude", "second-external-run", owner_pid=os.getpid())
    assert gui._selectable_task_iter(None) is None


def test_gtk_task_agent_status_shows_external_legacy_workspace_lock(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "locked-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_state(
        summary,
        {
            "active_agent_run": {
                "agent": "codex",
                "owner_pid": os.getpid(),
                "run_id": "external-run",
            }
        },
    )
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr(core_module, "_current_boot_id", lambda: "current-boot")
    monkeypatch.setattr(core_module, "_process_start_time_ticks", lambda _pid: 100)
    monkeypatch.setattr(core_module, "_process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) - 10)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.terminal_sessions = {}
    gui._agent_spinner_index = 0
    gui._local_agent_run_ids = lambda: set()

    assert gui._task_agent_status(summary) == "×"

    gui._local_agent_run_ids = lambda: {"external-run"}
    assert gui._task_agent_status(summary) != "×"


def test_gtk_refresh_task_row_styles_uses_batch_store_set(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_store = FakeGtkTaskStore([["", "", summary, "", False, "", False, 0, False]])
    gui.terminal_sessions = {}
    gui.theme = "dark"
    gui.selected_task = None
    gui._task_has_resumable_agent_session = lambda _task: False
    gui._task_is_external_active = lambda _task: False
    gui._task_agent_status = lambda _task: "□"
    gui._task_label = lambda task: task.name
    gui._ensure_selected_task_is_selectable = lambda: None

    gui._refresh_task_row_styles()

    assert len(gui.task_store.set_calls) == 1
    row_iter, columns, values = gui.task_store.set_calls[0]
    assert row_iter == 0
    assert columns == [0, 1, 3, 4, 5, 6, 7, 8]
    assert values == ["□", "sample-task", "", False, "", False, int(Pango.Weight.NORMAL), False]


def test_gtk_animate_agent_status_reuses_session_marker_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    calls: list[Path] = []

    def session_markers(task: TaskSummary, _workspace: Path) -> tuple[str, ...]:
        calls.append(task.path)
        return ("Ⅱ",)

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.task_store = FakeGtkTaskStore([["", "", summary, "", False, "", False, 0, False]])
    gui.terminal_sessions = {}
    gui.theme = "dark"
    gui.selected_task = None
    gui._closing = False
    gui._agent_spinner_index = 0
    gui._task_is_external_active = lambda _task: False
    gui._task_has_pending_agent_permission = lambda _task: False
    gui._running_agent_sessions = lambda: [object()]
    gui._current_task_terminal_sessions = lambda _task: ()
    gui._task_label = lambda task: task.name
    gui._ensure_selected_task_is_selectable = lambda: None
    monkeypatch.setattr(gtk_ui_module, "task_agent_session_markers", session_markers)

    assert gui._animate_agent_status()
    assert gui._animate_agent_status()

    assert calls == [summary.path]


def test_gtk_refresh_tasks_selects_open_task_when_previous_is_locked(tmp_path: Path, monkeypatch) -> None:
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (locked_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (open_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    locked = tasks["locked-task"]
    open_task = tasks["open-task"]
    selected_iters: list[object | None] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.selected_task = locked
    gui.task_store = FakeGtkTaskStore([])
    gui.summary_label = FakeGtkLabel()
    gui.theme = "dark"
    gui.tasks = []
    gui._task_agent_status = lambda _task: "□"
    gui._task_label = lambda task: task.name
    gui._refresh_task_row_styles = lambda: None
    gui._set_task_selection = lambda row_iter: selected_iters.append(row_iter)
    gui._tr = lambda key: {"tasks": "tasks"}[key]
    gui._task_is_external_active = lambda task: task.path == locked.path
    monkeypatch.setattr(gtk_ui_module, "discover_tasks", lambda _workspace: [locked, open_task])

    gui.refresh_tasks()

    assert gui.tasks == [locked, open_task]
    assert gui.summary_label.text == "2 tasks"
    assert gui.task_store.rows[0][2] == locked
    assert gui.task_store.rows[1][2] == open_task
    assert selected_iters == [1]


def test_gtk_refresh_tasks_clears_selection_when_all_tasks_locked(tmp_path: Path, monkeypatch) -> None:
    first_path = tmp_path / "tasks" / "first-task"
    second_path = tmp_path / "tasks" / "second-task"
    first_path.mkdir(parents=True)
    second_path.mkdir(parents=True)
    (first_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (first_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (second_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (second_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = discover_tasks(tmp_path)
    selected_iters: list[object | None] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.selected_task = tasks[0]
    gui.task_store = FakeGtkTaskStore([])
    gui.summary_label = FakeGtkLabel()
    gui.theme = "dark"
    gui.tasks = []
    gui._task_agent_status = lambda _task: "×"
    gui._task_label = lambda task: task.name
    gui._refresh_task_row_styles = lambda: None
    gui._set_task_selection = lambda row_iter: selected_iters.append(row_iter)
    gui._tr = lambda key: {"tasks": "tasks"}[key]
    gui._task_is_external_active = lambda _task: True
    monkeypatch.setattr(gtk_ui_module, "discover_tasks", lambda _workspace: tasks)

    gui.refresh_tasks()

    assert selected_iters == [None]


def test_gtk_task_selection_rejects_external_active_task(tmp_path: Path) -> None:
    open_path = tmp_path / "tasks" / "open-task"
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path.mkdir(parents=True)
    locked_path.mkdir(parents=True)
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (open_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (locked_path / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    open_task = tasks["open-task"]
    locked_task = tasks["locked-task"]
    model = FakeGtkTaskStore([[None, "locked-task", locked_task]])
    selection = FakeGtkSelection(model, 0)
    fallbacks: list[object | None] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._updating_task_selection = False
    gui.selected_task = open_task
    gui._task_is_external_active = lambda task: task.path == locked_task.path
    gui._selectable_task_iter = lambda preferred_name: ("fallback", preferred_name)
    gui._set_task_selection = lambda row_iter: fallbacks.append(row_iter)
    gui._remember_current_console_tab = lambda: (_ for _ in ()).throw(AssertionError("locked task should not switch"))

    gui._on_task_selected(selection)  # type: ignore[arg-type]

    assert gui.selected_task == open_task
    assert fallbacks == [("fallback", "open-task")]


def test_gtk_require_task_rejects_external_active_task_without_dialog(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "locked-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui._task_is_external_active = lambda _task: True

    assert gui._require_task(show_dialog=False) is None

    gui._task_is_external_active = lambda _task: False
    assert gui._require_task(show_dialog=False) == summary


def test_clear_task_agent_session_removes_empty_session_map(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert clear_task_agent_session(summary, "claude")

    data = json.loads((task / ".agent-workspace-state.json").read_text(encoding="utf-8"))
    assert data == {"agent": "claude"}


def test_reset_task_agent_session_preserves_selected_agent(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert reset_task_agent_session(summary, "claude")

    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "claude").session_id is None


def test_reset_task_agent_session_clears_active_run_for_selected_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    assert reset_task_agent_session(summary, "codex")

    assert load_task_agent(summary, "claude") == "codex"
    assert load_task_active_agent_run(summary) is None


def test_reset_task_agent_session_keeps_other_agent_active_run(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    monkeypatch.setattr(core_module, "_process_is_agent_workspace_owner", lambda _pid: True)
    save_task_active_agent_run(summary, "codex", "run-1", owner_pid=os.getpid())

    assert not reset_task_agent_session(summary, "claude")

    active = load_task_active_agent_run(summary)
    assert active is not None
    assert active.agent == "codex"
    assert active.run_id == "run-1"
    assert load_task_agent(summary, "codex") == "claude"


def test_reset_task_agent_session_selects_agent_even_without_saved_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    assert not reset_task_agent_session(summary, "claude")

    assert load_task_agent(summary, "codex") == "claude"


def test_tk_agent_model_and_effort_are_selected_per_agent() -> None:
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.default_codex_model = "gpt-5.5"
    gui.default_codex_reasoning = "medium"
    gui.default_claude_model = "sonnet"
    gui.default_claude_effort = "low"

    assert gui._agent_model("codex") == "gpt-5.5"
    assert gui._agent_reasoning_effort("codex") == "medium"
    assert gui._agent_model("claude") == "sonnet"
    assert gui._agent_reasoning_effort("claude") == "low"


def test_gtk_agent_model_and_effort_are_selected_per_agent() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.default_codex_model = "gpt-5.5"
    gui.default_codex_reasoning = "medium"
    gui.default_claude_model = "sonnet"
    gui.default_claude_effort = "low"

    assert gui._agent_model("codex") == "gpt-5.5"
    assert gui._agent_reasoning_effort("codex") == "medium"
    assert gui._agent_model("claude") == "sonnet"
    assert gui._agent_reasoning_effort("claude") == "low"


def test_tk_ai_agent_button_label_reflects_resumable_session(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.workspace = tmp_path
    gui.agent_var = FakeStringVar("claude")
    gui.run_ai_agent_button = FakeButton()
    gui.reset_ai_agent_button = FakeButton()
    gui._running_agent_session = lambda selected_task: None  # type: ignore[method-assign]

    gui._update_ai_agent_button_label()
    assert gui.run_ai_agent_button.text == "Запустить ИИ агента"
    assert gui.reset_ai_agent_button.state == "disabled"

    gui.agent_var = FakeStringVar("codex")
    codex_home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(codex_home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = codex_home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    gui.workspace = tmp_path
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "Восстановить сессию ИИ агента"
    assert gui.reset_ai_agent_button.state == "normal"

    gui.agent_var = FakeStringVar("claude")
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "Запустить ИИ агента"
    assert gui.reset_ai_agent_button.state == "disabled"

    gui.agent_var = FakeStringVar("codex")
    gui._running_agent_session = lambda selected_task: type("Session", (), {"kind": "codex"})()  # type: ignore[method-assign]
    gui._update_ai_agent_button_label()

    assert gui.run_ai_agent_button.text == "ИИ агент запущен"
    assert gui.reset_ai_agent_button.state == "normal"


def test_tk_agent_selection_warns_before_dropping_saved_session(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=session_id)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.workspace = tmp_path
    gui.default_agent = "codex"
    gui.agent_var = FakeStringVar("claude")
    gui._updating_agent_selection = False
    gui._running_agent_session = lambda selected_task: None  # type: ignore[method-assign]
    gui._confirm_saved_agent_session_delete = lambda old_agent, new_agent: False  # type: ignore[method-assign]
    gui._update_ai_agent_button_label = lambda: None  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: None  # type: ignore[method-assign]
    gui._refresh_tree_selection_style = lambda: None  # type: ignore[method-assign]

    gui._on_agent_selected()

    assert gui.agent_var.get() == "codex"
    assert load_task_agent_session(summary, "codex").session_id == session_id

    gui.agent_var = FakeStringVar("claude")
    gui._confirm_saved_agent_session_delete = lambda old_agent, new_agent: True  # type: ignore[method-assign]
    gui._on_agent_selected()

    assert gui.agent_var.get() == "claude"
    assert load_task_agent(summary, "codex") == "claude"
    assert load_task_agent_session(summary, "codex").session_id is None


def test_gtk_reset_agent_session_requires_confirmation(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "codex", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._require_task = lambda: summary  # type: ignore[method-assign]
    gui._selected_agent = lambda: "codex"  # type: ignore[method-assign]
    gui._current_task_terminal_sessions = lambda selected_task: []  # type: ignore[method-assign]
    gui._confirm_agent_session_reset = lambda agent: False  # type: ignore[method-assign]
    gui._invalidate_task_session_marker_cache = lambda task=None: None  # type: ignore[method-assign]
    gui._update_codex_button_state = lambda: None  # type: ignore[method-assign]
    gui._refresh_task_row_styles = lambda: None  # type: ignore[method-assign]

    gui.reset_ai_agent_session()

    assert load_task_agent_session(summary, "codex").session_id == "019feba2-e25e-76e1-9468-aa399758268f"

    gui._confirm_agent_session_reset = lambda agent: True  # type: ignore[method-assign]

    gui.reset_ai_agent_session()

    assert load_task_agent_session(summary, "codex").session_id is None


def test_tk_task_double_click_opens_task_folder(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    calls: list[Path] = []
    gui.open_task = lambda: calls.append(summary.path)  # type: ignore[method-assign]

    gui._on_task_double_clicked(None)

    assert calls == [summary.path]


def test_tk_custom_action_selects_actions_tab_before_running(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    action = TaskAction("sample", "Sample", "printf ok", task, {})
    selected_pages: list[int] = []
    sent: list[tuple[TaskSummary, str]] = []
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    gui.notebook = type("Notebook", (), {"select": lambda self, page: selected_pages.append(page)})()
    gui._send_command_to_task_console = lambda selected_task, command: sent.append((selected_task, command))  # type: ignore[method-assign]

    gui.run_custom_task_action(action)

    assert selected_pages == [0]
    assert sent and sent[0][0] == summary
    assert "printf ok" in sent[0][1]


def test_tk_console_notebook_double_click_adds_shell_console(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.selected_task = summary
    calls: list[TaskSummary] = []
    gui.new_console = lambda selected_task=None: calls.append(selected_task) or 1  # type: ignore[method-assign]

    result = gui._on_console_notebook_double_clicked(None)

    assert result == "break"
    assert calls == [summary]


def test_task_session_highlight_uses_each_tasks_saved_agent(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.workspace = tmp_path
    gui.default_agent = "codex"
    gui.agent_var = FakeStringVar("codex")

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = home / ".codex" / "sessions" / f"{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    save_task_agent(summary, "codex")
    save_task_agent_session(summary, "codex", session_id=session_id)

    assert gui._task_has_resumable_agent_session(summary)


def test_task_session_highlight_uses_any_saved_agent_session(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    gui = AgentWorkspace.__new__(AgentWorkspace)
    gui.workspace = workspace
    gui.default_agent = "codex"
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert gui._task_has_resumable_agent_session(summary)


def test_find_latest_codex_session_id_matches_task_prompt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    session_file = sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl"
    session_file.write_text(
        json.dumps(
            {
                "payload": {
                    "content": [
                        {
                            "text": codex_task_context_message(summary, workspace),
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    assert find_latest_codex_session_id(summary, workspace, home=home) == session_id


def test_find_latest_claude_session_id_matches_task_prompt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    old_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    new_session_id = "019feba2-e25e-76e1-9468-aa3997582690"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    old_file = sessions / f"{old_session_id}.jsonl"
    new_file = sessions / f"{new_session_id}.jsonl"
    other_file = sessions / "019feba2-e25e-76e1-9468-aa3997582691.jsonl"
    old_file.write_text(json.dumps({"message": {"content": prompt}, "sessionId": old_session_id}), encoding="utf-8")
    new_file.write_text(json.dumps({"message": {"content": prompt}, "sessionId": new_session_id}), encoding="utf-8")
    other_file.write_text('{"message": {"content": "other task"}}', encoding="utf-8")
    os.utime(old_file, (100, 100))
    os.utime(new_file, (200, 200))
    os.utime(other_file, (300, 300))

    assert find_latest_claude_session_id(summary, workspace, home=home) == new_session_id


def test_codex_session_id_validation_uses_local_session_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".codex" / "sessions" / "2026" / "08" / "10"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent_session(summary, "codex", session_id=session_id)
    assert not task_agent_session_id_is_valid(summary, workspace, "codex", home=home)
    assert not codex_session_id_exists(session_id, home=home)

    (sessions / f"rollout-2026-08-10T15-25-48-{session_id}.jsonl").write_text("{}", encoding="utf-8")

    assert codex_session_id_exists(session_id, home=home)
    assert task_agent_session_id_is_valid(summary, workspace, "codex", home=home)


def test_task_has_valid_agent_session_checks_any_agent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)

    assert not task_has_valid_agent_session(summary, workspace)

    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa399758268f")

    assert task_has_valid_agent_session(summary, workspace)
    assert not task_agent_session_id_is_valid(summary, workspace, "codex")


def test_task_selected_agent_has_resumable_state_uses_saved_agent(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"

    save_task_agent(summary, "claude")
    save_task_agent_session(summary, "claude", session_id=session_id)

    assert task_selected_agent_has_resumable_state(summary, workspace, "codex")
    clear_task_agent_session(summary, "claude")
    assert not task_selected_agent_has_resumable_state(summary, workspace, "codex")


def test_task_agent_session_markers_show_latest_resumable_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert task_agent_session_markers(summary, workspace, home=home) == ("Ⅱ",)
    assert not task_agent_has_resumable_state(summary, workspace, "codex", home=home)


def test_task_agent_status_text_combines_permission_running_and_saved_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=True,
            running_agents=("codex",),
            spinner_frame="▷",
            home=home,
        )
        == "▷"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            spinner_frame="▷",
            home=home,
        )
        == "▷"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            spinner_frame="",
            home=home,
        )
        == "▷"
    )


def test_task_agent_status_text_shows_saved_sessions_only_when_no_agent_is_running(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)
    save_task_agent_session(summary, "claude", session_id="019feba2-e25e-76e1-9468-aa3997582690")

    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=(),
            external_active=True,
            spinner_frame="▷",
            home=home,
        )
        == "×"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=("codex",),
            external_active=True,
            spinner_frame="▷",
            home=home,
        )
        == "×"
    )
    assert (
        task_agent_status_text(
            summary,
            workspace,
            permission_pending=False,
            running_agents=(),
            external_active=False,
            spinner_frame="▷",
            home=home,
        )
        == "Ⅱ"
    )


def test_task_agent_selection_with_resumable_fallback_prefers_saved_session_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    codex_session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    codex_session_file = home / ".codex" / "sessions" / f"{codex_session_id}.jsonl"
    codex_session_file.parent.mkdir(parents=True)
    codex_session_file.write_text("{}", encoding="utf-8")
    save_task_agent_session(summary, "codex", session_id=codex_session_id)

    assert task_agent_selection_with_resumable_fallback(summary, workspace, "claude", home=home) == "codex"


def test_agent_status_tooltip_explains_visible_markers_compactly() -> None:
    assert agent_status_tooltip_text("Ⅱ") == "Сессию можно продолжить"
    assert agent_status_tooltip_text("□") == "Нет сохраненной сессии"
    assert agent_status_tooltip_text("▷") == "Агент запущен"
    assert agent_status_tooltip_text("×") == "Задача занята другим окном"


def test_agent_status_manual_entries_are_structured_for_popup() -> None:
    assert AGENT_STATUS_MANUAL_MENU_LABEL == "Manual"
    assert AGENT_STATUS_MANUAL_TITLE == "Manual"
    assert [entry[0] for entry in AGENT_STATUS_MANUAL_USAGE_ENTRIES] == [
        "Концепция",
        "Задачи",
        "Агент",
        "Копирование",
        "Структура",
        "Действия",
        "Сброс",
    ]
    assert [entry[0] for entry in AGENT_STATUS_MANUAL_ENTRIES] == ["Ⅱ", "□", "▷", "×"]
    assert all(len(entry) == 3 for entry in AGENT_STATUS_MANUAL_ENTRIES)


def test_task_status_label_prefixes_permission_and_agent_session_markers() -> None:
    assert task_status_label("sample-task", permission_pending=False) == "sample-task"
    assert (
        task_status_label(
            "sample-task",
            permission_pending=True,
            session_markers=("Ⅱ",),
        )
        == "Ⅱ sample-task"
    )


def test_task_for_path_returns_existing_or_fallback_summary(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    missing_path = tmp_path / "tasks" / "missing-task"

    assert task_for_path([summary], task) is summary
    fallback = task_for_path([summary], missing_path)

    assert fallback.name == "missing-task"
    assert fallback.path == missing_path
    assert not fallback.has_description
    assert not fallback.has_context
    assert fallback.description_tokens == 0
    assert fallback.context_tokens == 0
    assert not fallback.context_over_budget


def test_claude_resume_flag_uses_latest_matching_local_session(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    (sessions / f"{session_id}.jsonl").write_text(
        json.dumps({"message": {"content": prompt}, "sessionId": session_id}),
        encoding="utf-8",
    )

    save_task_agent_session(summary, "claude")

    assert task_agent_has_resumable_state(summary, workspace, "claude", home=home)
    assert not task_agent_session_id_is_valid(summary, workspace, "claude")
    assert find_task_agent_session_id(summary, workspace, "claude", home=home) == session_id


def test_prepare_task_agent_session_persists_discovered_claude_session_id(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    task = workspace / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, workspace)
    home = tmp_path / "home"
    sessions = home / ".claude" / "projects" / "-tmp-workspace"
    sessions.mkdir(parents=True)
    session_id = "019feba2-e25e-76e1-9468-aa399758268f"
    prompt = ai_agent_task_context_prompt(summary, workspace)
    (sessions / f"{session_id}.jsonl").write_text(
        json.dumps({"message": {"content": prompt}, "sessionId": session_id}),
        encoding="utf-8",
    )
    save_task_agent_session(summary, "claude")

    prepared = prepare_task_agent_session(summary, workspace, "claude", home=home)

    assert prepared.agent == "claude"
    assert prepared.resume
    assert prepared.session_id == session_id
    assert load_task_agent_session(summary, "claude").session_id == session_id


def test_agent_executable_checks_path_and_local_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("agent_tools.tools.agent_workspace.core.shutil.which", lambda command: None)
    monkeypatch.setattr("agent_tools.tools.agent_workspace.core.Path.home", lambda: tmp_path)

    assert agent_executable("claude") is None

    local_claude = tmp_path / ".local" / "bin" / "claude"
    local_claude.parent.mkdir(parents=True)
    local_claude.write_text("#!/bin/sh\n", encoding="utf-8")

    assert agent_executable("claude") == str(local_claude)


def test_agent_install_commands_are_available() -> None:
    assert agent_install_command("codex") == "npm install -g @openai/codex"
    assert agent_install_command("claude") == "npm install -g @anthropic-ai/claude-code"


def test_codex_model_choices_loads_model_cache_slugs(tmp_path: Path) -> None:
    cache = tmp_path / "models_cache.json"
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.6-sol"},
                    {"slug": "gpt-5.5"},
                    {"slug": "gpt-5.5"},
                    {"display_name": "missing slug"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert codex_model_choices(cache) == ("", "gpt-5.6-sol", "gpt-5.5")


def test_agent_output_requests_permission_ignores_approval_prompts() -> None:
    assert not agent_output_requests_permission("Command requires approval before running.")
    assert not agent_output_requests_permission("Do you want to allow this command? yes/no")
    assert not agent_output_requests_permission("\x1b[31mPermission required\x1b[0m")
    assert not agent_output_requests_permission(
        "Would you like to run the following command?\n\n"
        "  Environment: local\n\n"
        "  $ true\n\n"
        "› 1. Yes, proceed (y)\n"
        "  2. Yes, and don't ask again for commands that start with `true` (p)\n"
        "  3. No, and tell Codex what to do differently (esc)\n"
    )
    assert not agent_output_requests_permission("Build completed successfully.")


def test_analyze_agent_output_reports_missing_session_and_permission() -> None:
    analysis = analyze_agent_output(
        "\x1b]0;title\x07No conversation found with session ID: "
        "71ca3372-3c10-4501-ad2a-145c5b9305de\r"
        "Would you like to run the following command?"
    )

    assert analysis.missing_session
    assert not analysis.requests_permission
    assert analysis.permission_signature is None
    assert not analysis.turn_complete


def test_agent_output_requests_permission_ignores_choice_prompt() -> None:
    analysis = analyze_agent_output("Allow this command to run? [y/N]")

    assert not analysis.requests_permission
    assert analysis.permission_signature is None


def test_agent_output_permission_scanner_ignores_large_terminal_tail() -> None:
    tail = ("normal output \x1b[31mwith color\x1b[0m\n" * 400) + "Allow this command to run? [y/N]\n"

    analysis = analyze_agent_output(tail)

    assert not analysis.requests_permission
    assert analysis.permission_signature is None


def test_agent_output_reports_turn_complete_for_completion_summaries() -> None:
    assert agent_output_reports_turn_complete("Done.\n")
    assert agent_output_reports_turn_complete("Tokens used: 12,345\n")
    assert agent_output_reports_turn_complete("Cost: $0.10\n")
    assert not agent_output_reports_turn_complete("Would you like to run the following command?")


def test_agent_output_state_update_prioritizes_missing_session() -> None:
    update = agent_output_state_update(
        "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de\n"
        "Would you like to run the following command?",
        exited=False,
        permission_pending=True,
    )

    assert update.missing_session
    assert update.exited
    assert not update.permission_requested
    assert not update.permission_pending


def test_agent_output_state_update_does_not_mark_permission_prompts() -> None:
    update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=False,
        permission_pending=False,
    )
    pending_update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=False,
        permission_pending=True,
    )
    exited_update = agent_output_state_update(
        "Would you like to run the following command?",
        exited=True,
        permission_pending=False,
    )

    assert not update.permission_requested
    assert not update.permission_pending
    assert not pending_update.permission_requested
    assert pending_update.permission_pending
    assert not exited_update.permission_requested
    assert exited_update.exited


def test_session_is_running_agent_requires_known_agent_and_live_session() -> None:
    assert session_is_running_agent(session_kind="codex", exited=False)
    assert session_is_running_agent(session_kind="claude", exited=False)
    assert not session_is_running_agent(session_kind="shell", exited=False)
    assert not session_is_running_agent(session_kind="codex", exited=True)


def test_session_is_agent_accepts_supported_agent_kinds_only() -> None:
    assert session_is_agent(session_kind="codex")
    assert session_is_agent(session_kind="claude")
    assert not session_is_agent(session_kind="shell")
    assert not session_is_agent(session_kind="")


def test_session_should_clear_pending_permission_only_for_pending_agent() -> None:
    assert session_should_clear_pending_permission(session_kind="codex", permission_pending=True)
    assert session_should_clear_pending_permission(session_kind="claude", permission_pending=True)
    assert not session_should_clear_pending_permission(session_kind="shell", permission_pending=True)
    assert not session_should_clear_pending_permission(session_kind="codex", permission_pending=False)


def test_session_marks_task_running_agent_requires_live_agent_for_task() -> None:
    task_path = Path("/tmp/workspace/tasks/sample-task")

    assert session_marks_task_running_agent(
        session_kind="claude",
        session_task_path=task_path,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="shell",
        session_task_path=task_path,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="codex",
        session_task_path=task_path,
        exited=True,
        task_path=task_path,
    )
    assert not session_marks_task_running_agent(
        session_kind="codex",
        session_task_path=task_path / "other",
        exited=False,
        task_path=task_path,
    )


def test_session_marks_task_pending_permission_only_for_live_agent_task() -> None:
    task_path = Path("/tmp/workspace/tasks/sample-task")

    assert session_marks_task_pending_permission(
        session_kind="claude",
        session_task_path=task_path,
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="shell",
        session_task_path=task_path,
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="codex",
        session_task_path=task_path,
        permission_pending=True,
        exited=True,
        task_path=task_path,
    )
    assert not session_marks_task_pending_permission(
        session_kind="codex",
        session_task_path=task_path / "other",
        permission_pending=True,
        exited=False,
        task_path=task_path,
    )


def test_agent_output_reports_missing_session_detects_cli_error() -> None:
    assert agent_output_reports_missing_session(
        "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de"
    )
    assert not agent_output_reports_missing_session("Conversation resumed.")


def test_gtk_running_agent_ignores_exited_agent_terminal(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = TerminalSession(1, summary.path, "claude", object(), object(), exited=True)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {1: session}
    gui._current_task_terminal_sessions = lambda selected_task: [session]  # type: ignore[method-assign]

    assert gui._running_agent_session(summary) is None
    assert gui._running_agent_sessions() == []


def test_gtk_agent_button_style_ignores_exited_agent_terminal(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = TerminalSession(1, summary.path, "claude", object(), object(), exited=True)
    button = FakeGtkButton()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.run_ai_agent_button = button
    gui.terminal_sessions = {1: session}
    gui._current_task_terminal_sessions = lambda selected_task: [session]  # type: ignore[method-assign]
    gui._update_ai_agent_button_label = lambda: None  # type: ignore[method-assign]
    gui._refresh_task_row_styles = lambda: None  # type: ignore[method-assign]

    gui._update_codex_button_state()

    assert "codex-running" not in button.style_context.classes


def test_gtk_close_console_session_clears_agent_state(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = FakeFrame()
    session = TerminalSession(1, summary.path, "claude", object(), page, busy=True, permission_pending=True)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {1: session}
    gui.last_active_terminal_by_task = {summary.path: session.session_id}
    gui.selected_task = None
    gui.console_notebook = type("Notebook", (), {"page_num": lambda self, page: -1})()
    gui._task_for_path = lambda task_path: summary  # type: ignore[method-assign]
    gui._update_codex_button_state = lambda: None  # type: ignore[method-assign]

    assert gui._close_console_session(session, confirm=False, ensure_default=False)

    assert session.session_id not in gui.terminal_sessions
    assert not session.permission_pending
    assert not session.busy
    assert session.exited
    assert page.destroyed
    assert summary.path not in gui.last_active_terminal_by_task


def test_gtk_close_disposes_terminal_sessions_before_quit(monkeypatch: object, tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    terminal = FakeSignalTerminal()
    page = FakeFrame()
    session = TerminalSession(1, summary.path, "shell", terminal, page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._closing = False
    gui.task_actions_monitor = None
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {summary.path: session.session_id}
    gui.selected_task = None
    gui.console_notebook = type("Notebook", (), {"page_num": lambda self, page: -1})()
    gui._save_settings = lambda: None  # type: ignore[method-assign]
    gui._task_for_path = lambda task_path: summary  # type: ignore[method-assign]
    gui._update_codex_button_state = lambda: None  # type: ignore[method-assign]
    main_quit_called = []
    monkeypatch.setattr(gtk_ui_module.Gtk, "main_quit", lambda: main_quit_called.append(True))

    gui.close()

    assert session.session_id not in gui.terminal_sessions
    assert page.destroyed
    assert terminal.disconnected
    assert main_quit_called == [True]


def test_gtk_console_notebook_switch_remembers_active_task_terminal(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = object()
    session = TerminalSession(7, summary.path, "shell", object(), page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {}
    gui._refreshing_console_tabs = False

    gui._on_console_notebook_switch_page(object(), page, 0)  # type: ignore[arg-type]

    assert gui.last_active_terminal_by_task == {summary.path: session.session_id}


def test_gtk_console_notebook_refresh_switch_does_not_replace_active_task_terminal(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = object()
    session = TerminalSession(7, summary.path, "codex", object(), page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {summary.path: 3}
    gui._refreshing_console_tabs = True

    gui._on_console_notebook_switch_page(object(), page, 0)  # type: ignore[arg-type]

    assert gui.last_active_terminal_by_task == {summary.path: 3}


def test_gtk_remember_current_console_tab_uses_visible_page_for_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    pages = [object(), object()]
    session = TerminalSession(8, summary.path, "shell", object(), pages[1])
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {}
    gui.console_notebook = FakeGtkConsoleNotebook(pages, current_page=1)

    gui._remember_current_console_tab()

    assert gui.last_active_terminal_by_task == {summary.path: session.session_id}


def test_gtk_activate_visible_terminal_can_restore_without_replacing_memory(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = object()
    terminal = type("Terminal", (), {"grab_focus": lambda self: None})()
    session = TerminalSession(8, summary.path, "shell", terminal, page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {summary.path: 3}
    gui.console_notebook = FakeGtkConsoleNotebook([page], current_page=0)

    gui._activate_visible_terminal(session.session_id, remember=False)

    assert gui.console_notebook.get_current_page() == 0
    assert gui.last_active_terminal_by_task == {summary.path: 3}


def test_gtk_refresh_console_tabs_restores_last_focused_tab_per_task(tmp_path: Path) -> None:
    task_one = tmp_path / "tasks" / "one"
    task_two = tmp_path / "tasks" / "two"
    task_one.mkdir(parents=True)
    task_two.mkdir(parents=True)
    (task_one / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task_one / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task_two / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task_two / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    summary_one = tasks["one"]
    summary_two = tasks["two"]

    class Terminal:
        def __init__(self) -> None:
            self.focused = False

        def grab_focus(self) -> None:
            self.focused = True

    task_one_agent_page = object()
    task_one_shell_page = object()
    task_two_shell_page = object()
    task_one_agent = TerminalSession(1, summary_one.path, "codex", Terminal(), task_one_agent_page)
    task_one_shell = TerminalSession(2, summary_one.path, "shell", Terminal(), task_one_shell_page)
    task_two_shell = TerminalSession(3, summary_two.path, "shell", Terminal(), task_two_shell_page)

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {
        task_one_agent.session_id: task_one_agent,
        task_one_shell.session_id: task_one_shell,
        task_two_shell.session_id: task_two_shell,
    }
    gui.last_active_terminal_by_task = {}
    gui._refreshing_console_tabs = False
    gui.console_notebook = FakeGtkConsoleNotebook([task_one_agent_page, task_one_shell_page], current_page=1)
    gui._renumber_terminal_tabs = lambda _task: None
    gui._update_codex_button_state = lambda: None

    def show_terminal_tab(session: TerminalSession, *, renumber: bool = True) -> None:
        if gui.console_notebook.page_num(session.page) >= 0:
            return
        if session.kind in {"codex", "claude"}:
            gui.console_notebook.insert_page(session.page, None, 0)
        else:
            gui.console_notebook.append_page(session.page, None)

    gui._show_terminal_tab = show_terminal_tab

    gui._remember_current_console_tab()
    gui._refresh_console_tabs_for_task(summary_two)
    gui._remember_current_console_tab()
    gui._refresh_console_tabs_for_task(summary_one)

    assert gui.console_notebook.pages == [task_one_agent_page, task_one_shell_page]
    assert gui.console_notebook.get_current_page() == 1
    assert task_one_shell.terminal.focused
    assert gui.last_active_terminal_by_task == {
        summary_one.path: task_one_shell.session_id,
        summary_two.path: task_two_shell.session_id,
    }


def test_gtk_task_selection_remembers_current_tab_before_switching(tmp_path: Path) -> None:
    task_one = tmp_path / "tasks" / "one"
    task_two = tmp_path / "tasks" / "two"
    task_one.mkdir(parents=True)
    task_two.mkdir(parents=True)
    (task_one / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task_one / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task_two / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task_two / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    tasks = {task.name: task for task in discover_tasks(tmp_path)}
    summary_one = tasks["one"]
    summary_two = tasks["two"]

    class Terminal:
        def __init__(self) -> None:
            self.focused = False

        def grab_focus(self) -> None:
            self.focused = True

    task_one_agent_page = object()
    task_one_shell_page = object()
    task_two_shell_page = object()
    task_one_agent = TerminalSession(1, summary_one.path, "codex", Terminal(), task_one_agent_page)
    task_one_shell = TerminalSession(2, summary_one.path, "shell", Terminal(), task_one_shell_page)
    task_two_shell = TerminalSession(3, summary_two.path, "shell", Terminal(), task_two_shell_page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.default_agent = "codex"
    gui._updating_task_selection = False
    gui.selected_task = summary_one
    gui.description_view = object()
    gui.context_view = object()
    gui.terminal_sessions = {
        task_one_agent.session_id: task_one_agent,
        task_one_shell.session_id: task_one_shell,
        task_two_shell.session_id: task_two_shell,
    }
    gui.last_active_terminal_by_task = {}
    gui._refreshing_console_tabs = False
    gui.console_notebook = FakeGtkConsoleNotebook([task_one_agent_page, task_one_shell_page], current_page=1)
    gui.ai_agent_page = task_one_agent_page
    gui.ai_agent_terminal_box = None
    gui._ensure_ai_agent_console_page = lambda: None
    gui._clear_ai_agent_terminal_page = lambda: None
    gui._task_is_external_active = lambda _task: False
    gui._leave_detail_edit_mode = lambda _view: None
    gui._set_markdown = lambda _view, _text: None
    gui._reset_actions = lambda: None
    gui._watch_task_actions = lambda _task: None
    gui._load_task_artifacts = lambda _task: (_ for _ in ()).throw(AssertionError("inactive artifacts tab should not load"))
    gui._artifacts_tab_active = lambda: False
    artifact_events: list[str] = []
    gui.artifact_store = type("ArtifactStore", (), {"clear": lambda self: artifact_events.append("store")})()
    gui._load_task_action_buttons = lambda: None
    gui._set_selected_agent = lambda _agent: None
    gui._renumber_terminal_tabs = lambda _task: None
    gui._actions_tab_active = lambda: False
    gui._update_codex_button_state = lambda: None

    def show_terminal_tab(session: TerminalSession, *, renumber: bool = True) -> None:
        if gui.console_notebook.page_num(session.page) >= 0:
            return
        if session.kind in {"codex", "claude"}:
            gui.console_notebook.insert_page(session.page, None, 0)
        else:
            gui.console_notebook.append_page(session.page, None)

    gui._show_terminal_tab = show_terminal_tab
    selection = FakeGtkSelection(FakeGtkTaskStore([[None, "two", summary_two]]), 0)

    gui._on_task_selected(selection)  # type: ignore[arg-type]

    assert gui.selected_task == summary_two
    assert gui.console_notebook.pages == [task_two_shell_page]
    assert gui.console_notebook.get_current_page() == 0
    assert task_two_shell.terminal.focused
    assert gui.last_active_terminal_by_task == {summary_one.path: task_one_shell.session_id}
    assert artifact_events == ["store"]


def test_gtk_task_action_selection_shows_only_selected_play_button(tmp_path: Path) -> None:
    build = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
    )
    test = TaskAction(
        action_id="test",
        label="Test",
        command=("scripts/test.sh",),
        cwd=tmp_path,
        env={},
    )
    build_button = FakeGtkButton()
    test_button = FakeGtkButton()
    build_play = FakeGtkButton()
    test_play = FakeGtkButton()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task_action = build
    gui.task_action_buttons = {"build": build_button, "test": test_button}
    gui.task_action_play_buttons = {"build": build_play, "test": test_play}

    gui._update_task_action_button_selection()

    assert "task-action-selected" in build_button.style_context.classes
    assert "task-action-selected" not in test_button.style_context.classes
    assert build_play.visible
    assert build_play.sensitive
    assert not test_play.visible
    assert not test_play.sensitive

    gui.selected_task_action = test
    gui._update_task_action_button_selection()

    assert not build_play.visible
    assert not build_play.sensitive
    assert test_play.visible
    assert test_play.sensitive


def test_gtk_main_notebook_switch_loads_artifacts_lazily(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.actions_page = object()
    gui.artifacts_page = object()
    calls: list[tuple[str, TaskSummary]] = []
    gui._load_task_artifacts = lambda task: calls.append(("load", task))
    gui._load_task_action_buttons = lambda: calls.append(("actions", summary))
    gui._ensure_default_console_for_selected_task = lambda: calls.append(("console", summary))

    gui._on_main_notebook_switch_page(object(), gui.artifacts_page, 1)  # type: ignore[arg-type]

    assert calls == [("load", summary)]


def test_gtk_terminal_text_tail_reads_recent_text() -> None:
    terminal = FakeGtkTextTerminal("a" * 5000 + "requires approval")

    tail = gtk_terminal_text_tail(terminal)

    assert len(tail) == 4000
    assert tail.endswith("requires approval")


def test_gtk_theme_colors_cover_widget_css_keys() -> None:
    required = {
        "background",
        "border",
        "codex_running_background",
        "codex_running_border",
        "codex_running_foreground",
        "codex_running_glow",
        "control_background",
        "control_hover_background",
        "foreground",
        "menu_background",
        "muted_foreground",
        "separator",
        "selection_background",
        "selection_foreground",
        "tab_background",
        "tab_selected_background",
        "tab_selected_foreground",
        "terminal_background",
        "text_background",
        "titlebar_background",
    }

    assert required <= set(gtk_theme_colors("dark"))
    assert required <= set(gtk_theme_colors("light"))


def test_gtk_dark_terminal_palette_uses_readable_blue() -> None:
    palette = gtk_terminal_palette("dark")

    assert len(palette) == 16
    assert palette[4] == "#7aa2f7"
    assert "#0000ff" not in palette


def test_gtk_terminal_session_sort_key_keeps_agents_first() -> None:
    entries = [("shell", 1), ("claude", 4), ("codex", 3), ("shell", 2)]

    assert sorted(entries, key=lambda item: gtk_terminal_session_sort_key(item[0], item[1])) == [
        ("codex", 3),
        ("claude", 4),
        ("shell", 1),
        ("shell", 2),
    ]


def test_gtk_terminal_tab_label_numbers_shells_only() -> None:
    assert gtk_terminal_tab_label("codex", 0) == "AI agent"
    assert gtk_terminal_tab_label("claude", 0) == "AI agent"
    assert gtk_terminal_tab_label("shell", 1) == "shell 1"
    assert gtk_terminal_tab_label("shell", 2) == "shell 2"
    assert gtk_terminal_tab_label("codex", 0, language="ru") == "ИИ агент"
    assert gtk_terminal_tab_label("shell", 1, language="ru") == "терминал 1"


def test_gtk_notebook_empty_tab_area_excludes_existing_tabs() -> None:
    notebook = FakeGtkNotebook([FakeGtkTabWidget(0, 0, 80, 28), FakeGtkTabWidget(80, 0, 90, 28)])

    assert gtk_notebook_event_in_empty_tab_area(notebook, FakeGtkNotebookEvent(220, 12))  # type: ignore[arg-type]
    assert not gtk_notebook_event_in_empty_tab_area(notebook, FakeGtkNotebookEvent(40, 12))  # type: ignore[arg-type]
    assert not gtk_notebook_event_in_empty_tab_area(notebook, FakeGtkNotebookEvent(220, 80))  # type: ignore[arg-type]


def test_gtk_terminal_clipboard_shortcut_requires_ctrl_shift() -> None:
    from gi.repository import Gdk

    ctrl_shift = int(Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
    ctrl = int(Gdk.ModifierType.CONTROL_MASK)

    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_c, ctrl_shift) == "copy"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_C, ctrl_shift) == "copy"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_v, ctrl_shift) == "paste"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_V, ctrl_shift) == "paste"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_Cyrillic_es, ctrl_shift) == "copy"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_Cyrillic_em, ctrl_shift) == "paste"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_x, ctrl_shift, hardware_keycode=54) == "copy"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_x, ctrl_shift, hardware_keycode=55) == "paste"
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_c, ctrl) is None
    assert gtk_terminal_clipboard_shortcut(Gdk.KEY_x, ctrl_shift) is None


def test_gtk_copy_terminal_selection_uses_vte_text_copy() -> None:
    terminal = FakeGtkCopyTerminal()

    gtk_copy_terminal_selection(terminal)  # type: ignore[arg-type]

    assert terminal.focused
    assert terminal.formatted_copies == 1
    assert terminal.plain_copies == 0


def test_gtk_copy_terminal_selection_falls_back_to_plain_copy() -> None:
    terminal = FakeGtkCopyTerminal(formatted_supported=False)

    gtk_copy_terminal_selection(terminal)  # type: ignore[arg-type]

    assert terminal.focused
    assert terminal.formatted_copies == 0
    assert terminal.plain_copies == 1


def test_gtk_copy_terminal_selection_falls_back_to_primary_selection(monkeypatch) -> None:
    terminal = FakeGtkCopyTerminal(has_selection=False, text="visible terminal output")
    copied: list[str] = []
    monkeypatch.setattr(gtk_terminal_ui_module, "clipboard_text", lambda _selection: "Claude selection")
    monkeypatch.setattr(gtk_terminal_ui_module, "set_clipboard_text", copied.append)

    gtk_copy_terminal_selection(terminal)  # type: ignore[arg-type]

    assert terminal.focused
    assert terminal.formatted_copies == 1
    assert terminal.plain_copies == 0
    assert copied == ["Claude selection"]


def test_gtk_copy_terminal_selection_ignores_empty_primary_selection(monkeypatch) -> None:
    terminal = FakeGtkCopyTerminal(has_selection=False, text="visible terminal output")
    copied: list[str] = []
    monkeypatch.setattr(gtk_terminal_ui_module, "clipboard_text", lambda _selection: "\n")
    monkeypatch.setattr(gtk_terminal_ui_module, "set_clipboard_text", copied.append)

    gtk_copy_terminal_selection(terminal)  # type: ignore[arg-type]

    assert terminal.focused
    assert terminal.formatted_copies == 1
    assert terminal.plain_copies == 0
    assert copied == []


def test_tk_control_shortcuts_work_on_cyrillic_layout() -> None:
    ctrl = 0x4
    ctrl_shift = 0x4 | 0x1

    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="Cyrillic_es")) == "interrupt"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl_shift, keysym="Cyrillic_es")) == "copy"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, char="м")) == "v"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="Cyrillic_ve")) == "d"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="x", keycode=54)) == "interrupt"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl_shift, keysym="x", keycode=54)) == "copy"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=ctrl, keysym="x", keycode=55)) == "v"
    assert _tk_control_shortcut(FakeTkKeyEvent(state=0, keysym="Cyrillic_es")) is None


def test_tk_ctrl_c_writes_interrupt_to_console() -> None:
    writes: list[tuple[int, bytes]] = []
    session = type("Session", (), {"session_id": 7, "fd": object()})()
    gui = object.__new__(AgentWorkspace)
    gui._active_console = lambda: session  # type: ignore[method-assign]
    gui._write_to_console = lambda session_id, data: writes.append((session_id, data))  # type: ignore[method-assign]

    assert gui._on_console_key(FakeTkKeyEvent(state=0x4, keysym="Cyrillic_es")) == "break"
    assert writes == [(7, b"\x03")]


def test_gtk_task_row_style_highlights_codex_tasks() -> None:
    from gi.repository import Pango

    assert gtk_task_row_style(False, False, False, "dark") == (
        "",
        False,
        "",
        False,
        int(Pango.Weight.NORMAL),
        False,
    )
    assert gtk_task_row_style(False, True, False, "dark") == (
        "",
        False,
        "",
        False,
        int(Pango.Weight.NORMAL),
        False,
    )
    assert gtk_task_row_style(False, False, True, "dark") == (
        "#34383d",
        True,
        "#a8b0ba",
        True,
        int(Pango.Weight.NORMAL),
        True,
    )
    assert gtk_task_row_style(True, True, True, "dark") == (
        "#26384d",
        True,
        "#ffffff",
        True,
        int(Pango.Weight.BOLD),
        True,
    )


def test_gtk_codex_prompt_includes_selected_language(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    message = gtk_codex_task_context_message(summary, tmp_path, "uk")

    assert "Відповідай користувачу українською мовою." in message


def test_gtk_translates_agent_and_manual_labels() -> None:
    assert GTK_TRANSLATIONS["ru"]["run_ai_agent"] == "Запустить ИИ агента"
    assert GTK_TRANSLATIONS["ru"]["ai_agent_running"] == "ИИ агент запущен"
    assert GTK_TRANSLATIONS["ru"]["restore_ai_agent_session"] == "Восстановить сессию ИИ агента"
    assert GTK_TRANSLATIONS["ru"]["reset_ai_agent_session"] == "Сбросить сессию"
    assert GTK_TRANSLATIONS["ru"]["default_agent"] == "ИИ агент по умолчанию"
    assert GTK_TRANSLATIONS["ru"]["default_claude_model"] == "Модель Claude"
    assert GTK_TRANSLATIONS["ru"]["default_codex_model"] == "Модель Codex"
    assert GTK_TRANSLATIONS["ru"]["ok"] == "ОК"
    assert GTK_TRANSLATIONS["uk"]["ok"] == "ОК"
    assert "закроет текущую сессию" in GTK_TRANSLATIONS["ru"]["confirm_switch_agent_body"]
    assert "ссылка на продолжение" in GTK_TRANSLATIONS["ru"]["confirm_delete_saved_agent_session_body"]
    assert "ссылка на продолжение сессии будет удалена" in GTK_TRANSLATIONS["ru"]["confirm_reset_agent_session_body"]
    assert GTK_TRANSLATIONS["ru"]["confirm_reset_agent_session_button"] == "Сбросить сессию"
    assert "остановит локальные процессы" in GTK_TRANSLATIONS["ru"]["confirm_close_running_agents_body"]
    assert "Предлагаемая команда установки" in GTK_TRANSLATIONS["ru"]["install_agent_body"]
    assert GTK_TRANSLATIONS["ru"]["delete_artifacts"] == "Удалить артефакты"
    assert GTK_TRANSLATIONS["ru"]["open_containing_folder"] == "Открыть содержащую папку"
    assert GTK_TRANSLATIONS["ru"]["other_artifacts"] == "Другие артефакты"
    assert GTK_TRANSLATIONS["ru"]["updated"] == "Обновлено"
    assert GTK_TRANSLATIONS["uk"]["manual_usage_section"] == "Основи"
    assert GTK_TRANSLATIONS["uk"]["manual_status_section"] == "Статуси в колонці ШІ"
    assert GTK_TRANSLATIONS["uk"]["task_agent_status_column"] == "ШІ"
    assert GTK_TRANSLATIONS["uk"]["run_ai_agent"] == "Запустити ШІ агента"
    assert GTK_TRANSLATIONS["uk"]["manual_label_reset"] == "Скидання"
    assert "workspace розбитий на задачі" in GTK_TRANSLATIONS["uk"]["manual_usage_concept"]
    assert "контексті поточної задачі" in GTK_TRANSLATIONS["uk"]["manual_usage_agent"]
    assert "Shift" in GTK_TRANSLATIONS["uk"]["manual_usage_copy"]
    assert "TASK_ACTIONS.json" in GTK_TRANSLATIONS["uk"]["manual_usage_actions"]


def test_agent_workspace_string_json_files_are_package_resources() -> None:
    package_files = resources.files("agent_tools.tools.agent_workspace")
    for filename in (
        "gtk_language_instructions.json",
        "gtk_translations.json",
        "gtk_ui_strings.json",
        "tk_strings.json",
        "workspace_strings.json",
    ):
        content = package_files.joinpath(filename).read_text(encoding="utf-8")
        assert isinstance(json.loads(content), dict)


def test_gtk_svg_open_command_prefers_browser(monkeypatch: object, tmp_path: Path) -> None:
    path = tmp_path / "flow.svg"
    monkeypatch.setenv("BROWSER", "firefox --new-tab")  # type: ignore[attr-defined]

    assert gtk_svg_open_command(path) == ["firefox", "--new-tab", str(path)]


def test_gtk_svg_open_command_uses_browser_before_xdg_open(monkeypatch: object, tmp_path: Path) -> None:
    path = tmp_path / "flow.svg"
    monkeypatch.delenv("BROWSER", raising=False)  # type: ignore[attr-defined]

    def fake_which(executable: str) -> str | None:
        if executable in {"firefox", "xdg-open"}:
            return f"/usr/bin/{executable}"
        return None

    monkeypatch.setattr("agent_tools.tools.agent_workspace.gtk_open.shutil.which", fake_which)  # type: ignore[attr-defined]

    assert gtk_svg_open_command(path) == ["/usr/bin/firefox", str(path)]


def test_gtk_open_text_file_prefers_editor(monkeypatch: object, tmp_path: Path) -> None:
    path = tmp_path / "TASK_ACTIONS.json"
    calls: list[list[str]] = []
    monkeypatch.setenv("EDITOR", "nano --wait")  # type: ignore[attr-defined]
    monkeypatch.setattr(gtk_open_module.subprocess, "Popen", lambda command: calls.append(command))  # type: ignore[attr-defined]

    gtk_open_module.open_text_file(path)

    assert calls == [["nano", "--wait", str(path)]]


def test_gtk_agent_workspace_icon_is_packaged() -> None:
    icon_path = gtk_agent_workspace_icon_path()

    assert icon_path.name == "agent-workspace.svg"
    assert icon_path.is_file()


def test_agent_workspace_desktop_uses_icon_name() -> None:
    desktop = Path(__file__).resolve().parents[4] / "agent-workspace.desktop"
    content = desktop.read_text(encoding="utf-8")

    assert "Icon=agent-workspace\n" in content
    assert "StartupWMClass=agent-workspace\n" in content


def test_agent_workspace_desktop_entry_uses_current_workspace_path(tmp_path: Path) -> None:
    content = install_desktop_module._desktop_entry(tmp_path)

    assert f"Exec={tmp_path / 'agent-workspace'}\n" in content
    assert f"Path={tmp_path}\n" in content
    assert "/Projects/new_dev" not in content


def test_gtk_agent_workspace_runtime_icon_falls_back_to_packaged_icon(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)  # type: ignore[attr-defined]

    assert gtk_agent_workspace_runtime_icon_path() == gtk_agent_workspace_icon_path()


def test_gtk_markdown_tags_are_configured() -> None:
    from gi.repository import Gtk

    gui = object.__new__(WorkspaceGtkGui)
    gui.text_font_size = 13
    buffer = Gtk.TextBuffer()

    gui._ensure_markdown_tags(buffer)

    assert buffer.get_tag_table().lookup("h1") is not None
    assert buffer.get_tag_table().lookup("list") is not None
    assert buffer.get_tag_table().lookup("table") is not None


def test_parse_console_output_preserves_color_tags() -> None:
    chunks = parse_console_output("\x1b[01;32muser\x1b[00m:\x1b[34m~/task\x1b[00m$ \r\n")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [
        ("user", ("console_bold", "console_fg_green")),
        (":", ()),
        ("~/task", ("console_fg_blue",)),
        ("$ \n", ()),
    ]


def test_parse_console_output_keeps_backspace_control() -> None:
    chunks = parse_console_output("abc\b \b")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("abc\b \b", ())]


def test_parse_console_output_keeps_carriage_return_control() -> None:
    chunks = parse_console_output("prompt old\rprompt new")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("prompt old\rprompt new", ())]


def test_console_paste_text_normalizes_newlines_without_trailing_enter() -> None:
    assert console_paste_text("one\r\ntwo\r\n") == "one two"
    assert console_paste_text("one\rtwo\n\n") == "one two"
    assert console_paste_text("\n  one  \n\n  two\t\n") == "one two"


def test_console_renderer_does_not_backspace_past_input_floor() -> None:
    gui = object.__new__(AgentWorkspace)
    text = FakeConsoleText("task$ ")
    session = ConsoleSession(
        session_id=1,
        title="1 shell",
        task_path=Path("/tmp/task"),
        kind="shell",
        frame=None,  # type: ignore[arg-type]
        text=text,  # type: ignore[arg-type]
        process=None,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
    )

    gui._set_console_input_floor(session)
    gui._insert_console_chunk(session, ConsoleChunk("abc\b \b\b \b\b \b\b \b", ()))

    assert text.text == "task$ "


def test_parse_console_output_drops_terminal_title_sequence() -> None:
    chunks = parse_console_output("\x1b]0;user@host:~/task\x07task$ ")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("task$ ", ())]


def test_log_agent_workspace_exception_writes_traceback_to_workspace_root(tmp_path: Path) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        log_agent_workspace_exception(tmp_path, "test", type(error), error, error.__traceback__)

    log_path = tmp_path / "agent-workspace-crash.log"
    content = log_path.read_text(encoding="utf-8")
    assert "Agent Workspace test exception" in content
    assert "RuntimeError: boom" in content


def test_agent_workspace_lock_allows_single_running_instance(tmp_path: Path) -> None:
    first = acquire_agent_workspace_lock(tmp_path)
    assert first is not None
    try:
        assert acquire_agent_workspace_lock(tmp_path) is None
    finally:
        first.close()

    second = acquire_agent_workspace_lock(tmp_path)
    assert second is not None
    second.close()


def test_tk_agent_output_missing_session_wins_over_permission_prompt(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "claude", session_id="71ca3372-3c10-4501-ad2a-145c5b9305de")
    session = ConsoleSession(
        session_id=1,
        title="Claude",
        task_path=summary.path,
        kind="claude",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=None,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    handled: list[int] = []
    gui._handle_agent_restore_failed = lambda failed_session: handled.append(failed_session.session_id)  # type: ignore[method-assign]

    gui._append_console_output(
        1,
        [
            ConsoleChunk(
                "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de\n"
                "Would you like to run the following command?",
                (),
            )
        ],
    )

    assert handled == [1]


def test_gtk_agent_restore_failure_clears_session_closes_console_and_sets_status(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "claude", session_id="71ca3372-3c10-4501-ad2a-145c5b9305de")
    page = FakeFrame()
    session = TerminalSession(1, summary.path, "claude", object(), page, busy=True, permission_pending=True)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {1: session}
    gui.last_active_terminal_by_task = {summary.path: session.session_id}
    gui.selected_task = summary
    gui.console_notebook = type("Notebook", (), {"page_num": lambda self, page: -1})()
    gui._task_for_path = lambda task_path: summary  # type: ignore[method-assign]
    gui._tr = lambda key: GTK_TRANSLATIONS["ru"][key]  # type: ignore[method-assign]
    gui._set_status_message = lambda message: setattr(gui, "status_message", message)  # type: ignore[method-assign]
    gui._update_codex_button_state = lambda: None  # type: ignore[method-assign]
    gui._refresh_task_row_styles = lambda: None  # type: ignore[method-assign]

    gui._handle_agent_restore_failed(session)

    assert session.session_id not in gui.terminal_sessions
    assert page.destroyed
    assert not load_task_agent_session(summary, "claude").resume
    assert "Не удалось восстановить сохраненную сессию Claude Code" in gui.status_message


def test_tk_answered_permission_prompt_does_not_keep_ignored_signature(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    read_fd, write_fd = os.pipe()
    prompt = "Would you like to run the following command?"
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=True),  # type: ignore[arg-type]
        fd=write_fd,
        chunks=[ConsoleChunk(prompt, ())],
        busy=False,
        permission_pending=True,
        permission_signature=prompt,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    gui._refresh_task_session_indicators = lambda: None  # type: ignore[method-assign]
    gui._schedule_agent_idle_after_output = lambda active_session: None  # type: ignore[method-assign]

    try:
        gui._write_to_console(1, b"y\r")
        gui._append_console_output(1, [ConsoleChunk("\nAccepted\n", ())])
    finally:
        os.close(read_fd)
        os.close(write_fd)

    assert not session.permission_pending
    assert session.ignored_permission_signature is None


def test_tk_agent_busy_clears_after_quiet_output_without_completion_text(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=None,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=True),  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        busy=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    calls = {"status": 0}
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    session.output_generation = 7
    gui._mark_agent_idle_if_output_quiet(1, 7)

    assert not session.busy
    assert calls == {"status": 1}


def test_tk_agent_output_refreshes_status_when_process_exits(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=FakeFrame(),  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=FakeProcess(running=False),  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        exited=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    calls = {"button": 0, "status": 0}
    gui._update_ai_agent_button_label = lambda: calls.__setitem__("button", calls["button"] + 1)  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    gui._append_console_output(1, [ConsoleChunk("[process exited with code 0]\n", ())])

    assert calls == {"button": 1, "status": 1}


def test_tk_stop_console_refreshes_full_agent_status(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    frame = FakeFrame()
    process = FakeProcess(running=True)
    session = ConsoleSession(
        session_id=1,
        title="Codex",
        task_path=summary.path,
        kind="codex",
        frame=frame,  # type: ignore[arg-type]
        text=FakeConsoleText(""),
        process=process,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
        busy=True,
        permission_pending=True,
    )
    gui = object.__new__(AgentWorkspace)
    gui.console_sessions = {1: session}
    gui.console_context_text = None
    gui.console_context_selection = ""
    gui.active_console_id = None
    gui.selected_task = None
    calls = {"button": 0, "status": 0}
    gui._forget_console_tab = lambda closed: None  # type: ignore[method-assign]
    gui._update_ai_agent_button_label = lambda: calls.__setitem__("button", calls["button"] + 1)  # type: ignore[method-assign]
    gui._refresh_task_session_indicators = lambda: calls.__setitem__("status", calls["status"] + 1)  # type: ignore[method-assign]

    gui.stop_console(1)

    assert process.terminated
    assert frame.destroyed
    assert session.exited
    assert not session.busy
    assert not session.permission_pending
    assert calls == {"button": 1, "status": 1}


def test_load_task_actions_and_run_command(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    scripts = task / "scripts"
    scripts.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "unit",
                        "label": "Unit tests",
                        "command": [
                            sys.executable,
                            "-c",
                            (
                                "import os; "
                                "print(os.environ['SAMPLE_FLAG']); "
                                f"print(os.environ['{PAF_HIDE_TASK_ENV_VAR}'])"
                            ),
                        ],
                        "cwd": "scripts",
                        "env": {"SAMPLE_FLAG": "ok"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))
    report = run_task_action(actions[0])

    assert errors == []
    assert actions[0].label == "Unit tests"
    assert actions[0].cwd == scripts.resolve()
    assert "ok" in report
    assert "\n1\n" in report
    assert "exit code: 0" in report


def test_gtk_task_action_code_path_resolves_shell_wrapper(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "open-board-webcam.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    action = TaskAction(
        action_id="webcam",
        label="Open board webcam",
        command=("bash", "scripts/open-board-webcam.sh"),
        cwd=tmp_path,
        env={},
    )
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._task_action_code_path(action) == script.resolve()


def test_task_action_code_path_rejects_invalid_or_escaping_commands(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.sh"
    outside.write_text("#!/bin/sh\n", encoding="utf-8")

    assert task_action_code_path(
        TaskAction(
            action_id="outside",
            label="Outside",
            command=("bash", str(outside)),
            cwd=tmp_path,
            env={},
        )
    ) is None
    assert task_action_code_path(
        TaskAction(
            action_id="invalid",
            label="Invalid",
            command="'unterminated",
            cwd=tmp_path,
            env={},
        )
    ) is None


def test_task_action_state_helpers_resolve_shortcuts_parameters_and_bindings(tmp_path: Path) -> None:
    parameter = TaskActionParameter(
        name="profile",
        label="Profile",
        parameter_type="choice",
        set_name="profiles",
        default="dev",
    )
    global_parameter = TaskActionParameter(
        name="profile",
        label="Profile",
        parameter_type="choice",
        set_name="profiles",
        default="dev",
        global_name="active_profile",
    )
    action = TaskAction(
        action_id="build",
        label="Build",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
        parameters=(parameter,),
        bindings={"profile": "release"},
    )
    shortcut = TaskAction(
        action_id="build-release",
        label="Build release",
        command=("scripts/build.sh",),
        cwd=tmp_path,
        env={},
        base_action_id="build",
        is_shortcut=True,
    )
    other_shortcut = TaskAction(
        action_id="test-release",
        label="Test release",
        command=("scripts/test.sh",),
        cwd=tmp_path,
        env={},
        base_action_id="test",
        is_shortcut=True,
    )
    config = TaskActionsConfig(
        actions=[action],
        base_actions=[action],
        parameter_sets={
            "profiles": {
                "dev": {"label": "Dev"},
                "release": {"name": "Release"},
            }
        },
        global_parameter_bindings={"active_profile": "release"},
        errors=[],
    )

    assert shortcuts_for_action(action, [shortcut, other_shortcut]) == [shortcut]
    assert parameter_values(parameter, config) == config.parameter_sets["profiles"]
    assert selected_parameter_value(parameter, {}, config.global_parameter_bindings) == "dev"
    assert selected_parameter_value(parameter, {"profile": "release"}, {}) == "release"
    assert selected_parameter_value(global_parameter, {}, config.global_parameter_bindings) == "release"
    assert parameter_button_label(parameter, config, {"profile": "release"}) == "Profile: Release"
    assert parameter_button_label(parameter, config, {"profile": "missing"}) == "Profile: missing"
    assert bindings_for_action_run(action, "build", {"profile": "dev"}) == {"profile": "dev"}
    assert bindings_for_action_run(action, "other", {"profile": "dev"}) == {"profile": "release"}


def test_task_action_parameter_set_helpers_upsert_rename_and_delete() -> None:
    data: dict[str, object] = {
        "parameter_sets": {
            "profiles": {
                "dev": {"name": "Dev"},
                "release": {"name": "Release"},
            }
        }
    }

    assert upsert_parameter_set_value(data, "profiles", "dev", "release", {"name": "Release copy"}) == "release_2"
    assert data["parameter_sets"] == {
        "profiles": {
            "release": {"name": "Release"},
            "release_2": {"name": "Release copy"},
        }
    }
    assert upsert_parameter_set_value(data, "profiles", "release_2", "prod", {"name": "Prod"}) == "prod"
    assert data["parameter_sets"] == {
        "profiles": {
            "release": {"name": "Release"},
            "prod": {"name": "Prod"},
        }
    }
    assert delete_parameter_set_value(data, "profiles", "release")
    assert not delete_parameter_set_value(data, "profiles", "missing")
    assert data["parameter_sets"] == {"profiles": {"prod": {"name": "Prod"}}}


def test_task_action_parameter_set_helpers_reject_malformed_data() -> None:
    malformed_sets: dict[str, object] = {"parameter_sets": []}
    malformed_values: dict[str, object] = {"parameter_sets": {"profiles": []}}

    assert upsert_parameter_set_value(malformed_sets, "profiles", None, "dev", {"name": "Dev"}) is None
    assert upsert_parameter_set_value(malformed_values, "profiles", None, "dev", {"name": "Dev"}) is None
    assert not delete_parameter_set_value(malformed_sets, "profiles", "dev")
    assert not delete_parameter_set_value(malformed_values, "profiles", "dev")


def test_task_action_shortcut_helpers_add_and_delete() -> None:
    data: dict[str, object] = {
        "shortcuts": [
            {"id": "copy-rpi5", "label": "Copy RPI5", "action": "copy", "bindings": {"board": "rpi5"}},
        ]
    }

    assert add_task_shortcut(data, "copy-rpi6", "Copy RPI6", "copy", {"board": "rpi6"})
    assert data["shortcuts"] == [
        {"id": "copy-rpi5", "label": "Copy RPI5", "action": "copy", "bindings": {"board": "rpi5"}},
        {"id": "copy-rpi6", "label": "Copy RPI6", "action": "copy", "bindings": {"board": "rpi6"}},
    ]
    assert delete_task_shortcut(data, "copy-rpi5")
    assert data["shortcuts"] == [
        {"id": "copy-rpi6", "label": "Copy RPI6", "action": "copy", "bindings": {"board": "rpi6"}},
    ]
    assert not delete_task_shortcut(data, "missing")


def test_task_action_shortcut_helpers_reject_malformed_data() -> None:
    data: dict[str, object] = {"shortcuts": {}}

    assert not add_task_shortcut(data, "copy", "Copy", "copy", {})
    assert not delete_task_shortcut(data, "copy")
    assert data == {"shortcuts": {}}


def test_task_action_parameter_dialog_field_names_merge_schema_initial_and_existing_values() -> None:
    data: dict[str, object] = {
        "parameter_types": {
            "board": {
                "fields": {
                    "name": {"type": "string"},
                    "host": {"type": "string"},
                    "user": {"type": "string"},
                }
            }
        }
    }

    assert parameter_dialog_field_names(
        data,
        "board",
        {"password_file"},
        [{"deployment_folder_name": "lab"}, {"host": "10.0.0.2"}],
    ) == ["name", "host", "password_file", "user", "deployment_folder_name"]
    assert parameter_dialog_field_names({}, "custom", set(), []) == ["name"]


def test_load_task_actions_resolves_parameter_sets_and_shortcuts(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    scripts = task / "scripts"
    scripts.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "parameter_types": {
                    "board": {
                        "set": "boards",
                        "fields": {
                            "name": {"type": "string"},
                            "host": {"type": "string"},
                        },
                    }
                },
                "parameter_sets": {
                    "boards": {
                        "rpi5": {
                            "name": "RPI5",
                            "host": "10.13.64.242",
                        },
                        "rpi6": {
                            "name": "RPI6",
                            "host": "10.13.64.243",
                        }
                    }
                },
                "global_parameters": {
                    "board": {
                        "label": "Board",
                        "type": "board",
                        "value": "rpi6",
                    }
                },
                "actions": [
                    {
                        "id": "copy",
                        "label": "Copy",
                        "command": ["printf", "ok"],
                        "cwd": ".",
                        "parameters": [
                            {
                                "name": "board",
                                "label": "Board",
                                "type": "board",
                                "default": "rpi5",
                                "global": "board",
                            }
                        ],
                    }
                ],
                "shortcuts": [
                    {
                        "id": "copy-rpi5",
                        "label": "Copy RPI5",
                        "action": "copy",
                        "bindings": {"board": "rpi5"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_task_actions_config(discover_tasks_with_context(task, tmp_path))
    shortcut = next(action for action in config.actions if action.action_id == "copy-rpi5")

    assert config.errors == []
    assert config.global_parameter_bindings == {"board": "rpi6"}
    assert [action.action_id for action in config.base_actions] == ["copy"]
    assert config.base_actions[0].parameters[0].global_name == "board"
    assert shortcut.is_shortcut
    assert shortcut.base_action_id == "copy"
    assert shortcut.env["TASK_ACTION_PARAM_BOARD"] == "rpi6"
    assert shortcut.env["TASK_ACTION_PARAM_BOARD_HOST"] == "10.13.64.243"


def test_gtk_action_ui_string_ids_support_language_fallback() -> None:
    assert gtk_ui_module._ui_string("ru", "action.parameters") == "Параметры"
    assert gtk_ui_module._ui_string("ru", "console.ai_agent") == "ИИ агент"
    assert gtk_ui_module._ui_string("ru", "console.shell") == "терминал"
    assert gtk_ui_module._ui_string("missing", "action.parameters") == "Parameters"
    assert gtk_ui_module._ui_string("ru", "action.add_value", set_name="boards") == "Добавить boards"


def test_task_action_menu_state_helpers_select_labels_and_paths(tmp_path: Path) -> None:
    code_path = tmp_path / "scripts" / "build.sh"

    assert task_reorder_label_key(False) == "action.reorder_actions"
    assert task_reorder_label_key(True) == "action.stop_reorder_actions"
    assert task_parameter_menu_state("rpi5", True).selected_value == "rpi5"
    assert task_parameter_menu_state("rpi5", True).reorder_label_key == "action.stop_reorder_actions"

    action_state = task_action_menu_state(tmp_path, code_path, False)
    assert action_state.actions_file == tmp_path / "TASK_ACTIONS.json"
    assert action_state.code_path == code_path
    assert action_state.reorder_label_key == "action.reorder_actions"

    missing_task_state = task_action_menu_state(None, None, True)
    assert missing_task_state.actions_file is None
    assert missing_task_state.code_path is None
    assert missing_task_state.reorder_label_key == "action.stop_reorder_actions"
    assert task_shortcut_menu_state(False).reorder_label_key == "action.reorder_actions"


def test_gtk_json_reorder_helpers_move_actions_parameters_and_shortcuts() -> None:
    data: dict[str, object] = {
        "actions": [
            {"id": "full"},
            {
                "id": "copy",
                "parameters": [
                    {"name": "board"},
                    {"name": "source"},
                    {"name": "target"},
                ],
            },
        ],
        "shortcuts": [
            {"id": "copy-a"},
            {"id": "copy-b"},
        ],
        "global_parameters": {
            "board": {"value": "rpi5"},
            "image": {"value": "full_ufs_gz"},
        },
    }

    actions = data["actions"]
    shortcuts = data["shortcuts"]
    globals_data = data["global_parameters"]
    assert isinstance(actions, list)
    assert isinstance(shortcuts, list)
    assert isinstance(globals_data, dict)

    assert gtk_ui_module._move_json_list_entry(actions, "id", "copy", -1)
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]
    assert gtk_ui_module._move_json_list_entry_before(actions, "id", "full", "copy")
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["full", "copy"]

    assert gtk_ui_module._move_action_parameter_entry(data, "copy", "target", -1)
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    parameters = copy_action["parameters"]
    assert isinstance(parameters, list)
    assert [entry["name"] for entry in parameters if isinstance(entry, dict)] == ["board", "target", "source"]

    assert gtk_ui_module._move_json_list_entry(shortcuts, "id", "copy-a", 1)
    assert [entry["id"] for entry in shortcuts if isinstance(entry, dict)] == ["copy-b", "copy-a"]

    assert gtk_ui_module._move_json_mapping_entry(globals_data, "image", -1)
    assert list(globals_data) == ["image", "board"]
    assert gtk_ui_module._reorder_json_mapping_by_ids(globals_data, ["board", "image"])
    assert list(globals_data) == ["board", "image"]
    assert not gtk_ui_module._reorder_json_mapping_by_ids(globals_data, ["board", "image"])

    preview_order = ["full", "copy", "clean"]
    assert gtk_ui_module._move_id_before(preview_order, "clean", "copy")
    assert preview_order == ["full", "clean", "copy"]
    assert gtk_ui_module._move_id_relative(preview_order, "full", "clean", after=True)
    assert preview_order == ["clean", "full", "copy"]
    assert not gtk_ui_module._move_id_relative(preview_order, "clean", "full", after=False)
    assert preview_order == ["clean", "full", "copy"]
    assert not gtk_ui_module._move_id_relative(preview_order, "copy", "full", after=True)
    assert preview_order == ["clean", "full", "copy"]
    assert gtk_ui_module._reorder_json_list_by_ids(actions, "id", ["copy", "full"])
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]
    assert gtk_ui_module._reorder_action_parameter_entries(data, "copy", ["source", "target", "board"])
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    reordered_parameters = copy_action["parameters"]
    assert isinstance(reordered_parameters, list)
    assert [entry["name"] for entry in reordered_parameters if isinstance(entry, dict)] == ["source", "target", "board"]
    shortcut_entries: list[object] = [
        {"id": "other-a"},
        {"id": "copy-a"},
        {"id": "copy-b"},
        {"id": "other-b"},
    ]
    assert gtk_ui_module._reorder_json_list_subset_by_ids(shortcut_entries, "id", ["copy-b", "copy-a"])
    assert [entry["id"] for entry in shortcut_entries if isinstance(entry, dict)] == [
        "other-a",
        "copy-b",
        "copy-a",
        "other-b",
    ]


def test_task_action_order_helper_reorders_supported_groups() -> None:
    data: dict[str, object] = {
        "actions": [
            {"id": "full"},
            {
                "id": "copy",
                "parameters": [
                    {"name": "board"},
                    {"name": "source"},
                    {"name": "target"},
                ],
            },
        ],
        "shortcuts": [
            {"id": "other-a"},
            {"id": "copy-a"},
            {"id": "copy-b"},
            {"id": "other-b"},
        ],
        "global_parameters": {
            "board": {"value": "rpi5"},
            "image": {"value": "full_ufs_gz"},
        },
    }

    assert reorder_task_action_data(data, "action", ["copy", "full"])
    actions = data["actions"]
    assert isinstance(actions, list)
    assert [entry["id"] for entry in actions if isinstance(entry, dict)] == ["copy", "full"]

    assert reorder_task_action_data(data, "shortcut", ["copy-b", "copy-a"])
    shortcuts = data["shortcuts"]
    assert isinstance(shortcuts, list)
    assert [entry["id"] for entry in shortcuts if isinstance(entry, dict)] == [
        "other-a",
        "copy-b",
        "copy-a",
        "other-b",
    ]

    assert reorder_task_action_data(data, "parameter", ["target", "source", "board"], selected_action_id="copy")
    copy_action = next(entry for entry in actions if isinstance(entry, dict) and entry.get("id") == "copy")
    assert isinstance(copy_action, dict)
    parameters = copy_action["parameters"]
    assert isinstance(parameters, list)
    assert [entry["name"] for entry in parameters if isinstance(entry, dict)] == ["target", "source", "board"]

    assert reorder_task_action_data(data, "global_parameter", ["image", "board"])
    global_parameters = data["global_parameters"]
    assert isinstance(global_parameters, dict)
    assert list(global_parameters) == ["image", "board"]

    assert not reorder_task_action_data(data, "parameter", ["board", "source", "target"])
    assert not reorder_task_action_data(data, "missing", [])


def test_gtk_task_actions_mutator_handles_save_reload_noop_and_errors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_path = tmp_path / "tasks" / "sample"
    task_path.mkdir(parents=True)
    task = discover_tasks_with_context(task_path, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = task
    gui.task_action_errors = []
    reloads: list[str] = []
    saved: list[dict[str, object]] = []

    gui._require_task = lambda show_dialog=True: gui.selected_task  # type: ignore[method-assign]
    gui._load_task_action_buttons = lambda: reloads.append("reload")  # type: ignore[method-assign]
    gui._update_actions_message = lambda: reloads.append("error")  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module, "load_task_actions_data", lambda _task: ({"actions": []}, []))
    monkeypatch.setattr(gtk_ui_module, "save_task_actions_data", lambda _task, data: saved.append(dict(data)))

    assert gui._mutate_task_actions_data(lambda data: data.setdefault("changed", True) is True)
    assert saved == [{"actions": [], "changed": True}]
    assert reloads == ["reload"]

    reloads.clear()
    assert not gui._mutate_task_actions_data(lambda _data: False)
    assert reloads == []
    assert not gui._mutate_task_actions_data(lambda _data: False, reload_on_no_change=True)
    assert reloads == ["reload"]

    monkeypatch.setattr(gtk_ui_module, "load_task_actions_data", lambda _task: ({}, ["broken"]))
    assert not gui._mutate_task_actions_data(lambda _data: True)
    assert gui.task_action_errors == ["broken"]
    assert reloads == ["reload", "error"]


def test_gtk_task_action_drag_reorder_sequence_moves_one_slot_at_a_time() -> None:
    order = ["full", "copy", "clean", "webcam"]

    assert gtk_ui_module._move_id_relative(order, "full", "copy", after=True)
    assert order == ["copy", "full", "clean", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "clean", after=True)
    assert order == ["copy", "clean", "full", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "webcam", after=True)
    assert order == ["copy", "clean", "webcam", "full"]

    assert gtk_ui_module._move_id_relative(order, "full", "webcam", after=False)
    assert order == ["copy", "clean", "full", "webcam"]
    assert gtk_ui_module._move_id_relative(order, "full", "clean", after=False)
    assert order == ["copy", "full", "clean", "webcam"]


def test_gtk_task_reorder_edges_do_not_oscillate_after_swap() -> None:
    centers = {
        "copy": 100.0,
        "clean": 200.0,
    }
    order = ["full", "copy", "clean"]

    next_order = gtk_ui_module._task_reorder_order_for_drag_edges(
        order,
        "full",
        centers,
        dragged_left=61.0,
        dragged_right=101.0,
        moving_right=True,
    )
    assert next_order == ["copy", "full", "clean"]

    assert (
        gtk_ui_module._task_reorder_order_for_drag_edges(
            next_order,
            "full",
            centers,
            dragged_left=61.0,
            dragged_right=101.0,
            moving_right=True,
        )
        is None
    )
    assert (
        gtk_ui_module._task_reorder_order_for_drag_edges(
            next_order,
            "full",
            centers,
            dragged_left=101.0,
            dragged_right=141.0,
            moving_right=False,
        )
        is None
    )
    assert gtk_ui_module._task_reorder_order_for_drag_edges(
        next_order,
        "full",
        centers,
        dragged_left=99.0,
        dragged_right=139.0,
        moving_right=False,
    ) == ["full", "copy", "clean"]


def test_gtk_task_action_drag_selection_uses_custom_target_payload() -> None:
    selection = FakeGtkDragSelection()

    gtk_set_task_action_drag_selection(selection, "parameter:source")

    assert selection.data == b"parameter:source"
    assert gtk_task_action_drag_selection_id(selection) == "parameter:source"


def test_load_task_actions_rejects_escaping_cwd(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "command": "echo bad",
                        "cwd": "..",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))

    assert actions == []
    assert "cwd escapes task" in errors[0]


def discover_tasks_with_context(task: Path, workspace: Path) -> TaskSummary:
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    return discover_tasks(workspace)[0]


def _task_context() -> str:
    return """# Task Context

## Goal

-

## Repositories

-

## Environment

-

## Knowledge

-

## Build/Product

-

## Validation Status

| Level | Status |
| --- | --- |
| static | not run |
| build | not run |
| runtime | not run |
| review | not run |

## Tool Failures

-

## Decisions

-

## Blockers

-

## Next Steps

-
"""
