from __future__ import annotations

import re
import subprocess
import sys
import textwrap
import time

import pytest

from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _harness_debug_event_row
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _harness_debug_event_details_text
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _harness_debug_events_text
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _ai_debug_restore_event_id
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import Vte
from agent_tools.agent_workspace.components.gtk_desktop.src.gtk_ui import _apply_mcp_trusted_check_toggle
from agent_tools.agent_workspace.components.gtk_desktop.src.codex_terminal_mouse import CodexTerminalMouseStateMachine
from agent_tools.agent_workspace.components.harness_adapter.api import AgentType
from agent_tools.agent_workspace.components.harness_adapter.api import HarnessDebugEvent
from agent_tools.agent_workspace.components.harness_adapter.api import HarnessStatusEvent
from agent_tools.agent_workspace.components.test_support.src.helpers import *


def _drain_gtk_events() -> None:
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


class FakeCheckButton:
    def __init__(self, active: bool = False) -> None:
        self.active = active

    def get_active(self) -> bool:
        return self.active

    def set_active(self, active: bool) -> None:
        self.active = active


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


def test_gtk_artifact_group_double_click_opens_group_folder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    calls: list[Path] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary

    class Store:
        def get_iter(self, _tree_path: object) -> int:
            return 0

        def __getitem__(self, _row_iter: int) -> list[object]:
            return ["Logs", "", "logs", True, ""]

    gui.artifact_store = Store()
    monkeypatch.setattr(gtk_ui_module, "open_path", lambda path: calls.append(path))

    gui._on_artifact_row_activated(object(), object(), object())  # type: ignore[arg-type]

    assert calls == [task / "report" / "logs"]


class FakeArtifactTreeView:
    def __init__(self) -> None:
        self.expanded_paths: set[str] = set()
        self.expand_all_calls = 0
        self.expand_row_calls: list[str] = []
        self.collapse_row_calls: list[str] = []
        self.cursor_path: str | None = None
        self.selected_paths: list[str] = []
        self.set_cursor_calls: list[str] = []
        self.scroll_to_cell_calls: list[str] = []

    def row_expanded(self, tree_path: Gtk.TreePath) -> bool:
        return tree_path.to_string() in self.expanded_paths

    def get_cursor(self) -> tuple[Gtk.TreePath | None, None]:
        if self.cursor_path is None:
            return None, None
        return Gtk.TreePath.new_from_string(self.cursor_path), None

    def get_selection(self) -> object:
        view = self

        class Selection:
            def select_path(self, tree_path: Gtk.TreePath) -> None:
                view.selected_paths.append(tree_path.to_string())

        return Selection()

    def set_cursor(self, tree_path: Gtk.TreePath) -> None:
        value = tree_path.to_string()
        self.cursor_path = value
        self.set_cursor_calls.append(value)

    def scroll_to_cell(
        self,
        tree_path: Gtk.TreePath,
        _column: object,
        _use_align: bool,
        _row_align: float,
        _col_align: float,
    ) -> None:
        self.scroll_to_cell_calls.append(tree_path.to_string())

    def expand_all(self) -> None:
        self.expand_all_calls += 1

    def expand_row(self, tree_path: Gtk.TreePath, _open_all: bool) -> None:
        value = tree_path.to_string()
        self.expanded_paths.add(value)
        self.expand_row_calls.append(value)

    def collapse_row(self, tree_path: Gtk.TreePath) -> None:
        value = tree_path.to_string()
        self.expanded_paths.discard(value)
        self.collapse_row_calls.append(value)

    def get_path_at_pos(self, _x: int, _y: int) -> tuple[Gtk.TreePath, None, int, int]:
        return Gtk.TreePath.new_from_string("0"), None, 0, 0


class FakeArtifactButtonEvent:
    def __init__(self, button: int, x: float = 8.0, y: float = 8.0) -> None:
        self.button = button
        self.x = x
        self.y = y


def test_gtk_artifact_load_expands_groups_on_first_load(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.expand_all_calls == 1


def test_gtk_artifact_expander_click_toggles_group() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_store.append(None, ["Logs", "", "logs", True, ""])
    tree = FakeArtifactTreeView()

    assert gui._toggle_artifact_group_expander_at_pos(tree, FakeArtifactButtonEvent(1))
    assert tree.expand_row_calls == ["0"]

    assert gui._toggle_artifact_group_expander_at_pos(tree, FakeArtifactButtonEvent(1))
    assert tree.collapse_row_calls == ["0"]


def test_gtk_artifact_expander_click_ignores_group_label_area() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_store.append(None, ["Logs", "", "logs", True, ""])
    tree = FakeArtifactTreeView()

    assert not gui._toggle_artifact_group_expander_at_pos(tree, FakeArtifactButtonEvent(1, x=64.0))
    assert tree.expand_row_calls == []


def test_gtk_artifact_load_preserves_collapsed_groups(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "puml" / "flow.svg").write_text("<svg>", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)
    gui.artifact_view.expand_all_calls = 0
    gui.artifact_view.expanded_paths = {"1"}
    gui.artifact_view.expand_row_calls.clear()
    gui.artifact_view.collapse_row_calls.clear()

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.expand_all_calls == 0
    assert gui.artifact_view.expand_row_calls == ["1"]
    assert set(gui.artifact_view.collapse_row_calls) == {"0", "2", "3"}


def test_gtk_artifact_load_restores_existing_focus(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    artifact = task / "report" / "logs" / "runtime.log"
    artifact.write_text("log", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)
    gui.artifact_view.cursor_path = "0:0"
    gui.artifact_view.selected_paths.clear()
    gui.artifact_view.set_cursor_calls.clear()
    gui.artifact_view.scroll_to_cell_calls.clear()

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.selected_paths == ["0:0"]
    assert gui.artifact_view.set_cursor_calls == ["0:0"]
    assert gui.artifact_view.scroll_to_cell_calls == ["0:0"]


class FakeArtifactAdjustment:
    def __init__(self, value: float, upper: float = 100.0, page_size: float = 20.0) -> None:
        self.value = value
        self.upper = upper
        self.page_size = page_size
        self.set_values: list[float] = []

    def get_value(self) -> float:
        return self.value

    def get_lower(self) -> float:
        return 0.0

    def get_upper(self) -> float:
        return self.upper

    def get_page_size(self) -> float:
        return self.page_size

    def set_value(self, value: float) -> None:
        self.set_values.append(value)


class FakeArtifactPage:
    def __init__(self, adjustment: FakeArtifactAdjustment) -> None:
        self.adjustment = adjustment

    def get_vadjustment(self) -> FakeArtifactAdjustment:
        return self.adjustment


class FakeArtifactTextFilter:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


class FakeArtifactExtensionFilter:
    def __init__(self) -> None:
        self.label = ""

    def set_label(self, label: str) -> None:
        self.label = label


def test_gtk_artifact_load_restores_scroll_when_focus_disappears(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    artifact = task / "report" / "logs" / "runtime.log"
    artifact.write_text("log", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifacts_scrolled = FakeArtifactPage(FakeArtifactAdjustment(42.0))
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module.GLib, "idle_add", lambda callback, *args: callback(*args))

    gui._load_task_artifacts(summary)
    gui.artifacts_scrolled.adjustment.set_values.clear()
    gui.artifact_view.cursor_path = "0:0"
    artifact.unlink()

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.set_cursor_calls == []
    assert gui.artifacts_scrolled.adjustment.set_values == [42.0]


def test_gtk_artifact_text_filter_matches_names_and_relative_paths(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "diff" / "review.html").write_text("<html>", encoding="utf-8")
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_text_filter = FakeArtifactTextFilter("diff")
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)

    diff_iter = gui.artifact_store.iter_nth_child(None, 2)
    assert gui.artifact_store.iter_n_children(diff_iter) == 1
    assert gui.artifact_store[gui.artifact_store.iter_children(diff_iter)][0] == "review.html"

    gui.artifact_text_filter = FakeArtifactTextFilter("runtime")
    gui._load_task_artifacts(summary)

    logs_iter = gui.artifact_store.iter_nth_child(None, 0)
    assert gui.artifact_store.iter_n_children(logs_iter) == 1
    assert gui.artifact_store[gui.artifact_store.iter_children(logs_iter)][0] == "runtime.log"


def test_gtk_artifact_filter_expands_groups_with_matches(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_text_filter = FakeArtifactTextFilter("runtime")
    gui.artifact_extension_filter_value = "all"
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.expand_row_calls == ["0"]
    assert set(gui.artifact_view.collapse_row_calls) == {"1", "2", "3"}


def test_gtk_artifact_load_expands_all_when_filter_is_cleared(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_text_filter = FakeArtifactTextFilter("runtime")
    gui.artifact_extension_filter_value = "all"
    gui.artifact_filter_was_active = False
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)
    gui.artifact_view.expand_all_calls = 0
    gui.artifact_text_filter = FakeArtifactTextFilter("")

    gui._load_task_artifacts(summary)

    assert gui.artifact_view.expand_all_calls == 1


def test_gtk_artifact_extension_filter_limits_rows(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "logs").mkdir(parents=True)
    (task / "report" / "diff" / "review.html").write_text("<html>", encoding="utf-8")
    (task / "report" / "logs" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_text_filter = FakeArtifactTextFilter("")
    gui.artifact_extension_filter = FakeArtifactExtensionFilter()
    gui.artifact_extension_filter_value = ".md"
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)

    artifacts_iter = gui.artifact_store.iter_nth_child(None, 3)
    assert gui.artifact_store.iter_n_children(artifacts_iter) == 1
    assert gui.artifact_store[gui.artifact_store.iter_children(artifacts_iter)][0] == "notes.md"
    assert gui.artifact_store.iter_n_children(gui.artifact_store.iter_nth_child(None, 0)) == 0
    assert gui.artifact_extension_filter.label == ".md"
    assert gui.artifact_extension_filter_menu is not None


def test_gtk_artifact_extension_filter_resets_missing_extension(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report").mkdir(parents=True)
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.artifact_store = Gtk.TreeStore(str, str, object, bool, str)
    gui.artifact_view = FakeArtifactTreeView()
    gui.artifact_text_filter = FakeArtifactTextFilter("")
    gui.artifact_extension_filter = FakeArtifactExtensionFilter()
    gui.artifact_extension_filter_value = ".html"
    gui.artifact_sort_column = "name"
    gui.artifact_sort_descending = False
    gui._tr = lambda key: key  # type: ignore[method-assign]

    gui._load_task_artifacts(summary)

    assert gui.artifact_extension_filter_value == "all"
    assert gui.artifact_extension_filter.label == "artifact_extension_all"
    assert gui.artifact_store.iter_n_children(gui.artifact_store.iter_nth_child(None, 3)) == 1


def test_gtk_dictionary_preview_shows_char_counts_with_dictionary() -> None:
    path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
    text = f"{path} validates settings. {path} validates preview. {path} validates counts."
    preview = preview_dictionary_compile(
        text,
        TaskDictionaryPolicy(min_occurrences=3, min_term_length=7, min_saving=1),
    )
    dictionary_chars = len("\n".join(f"{entry.token} = {entry.value}" for entry in preview.dictionary))
    after_chars = len(preview.encoded_text) + dictionary_chars
    encoded_tokens = preview.encoded_tokens + preview.dictionary_tokens
    saving_tokens = preview.original_tokens - encoded_tokens

    preview_content = gtk_dictionary_preview_text(text, preview)
    metrics_content = gtk_dictionary_preview_metrics_text(text, preview)
    ru_metrics_content = gtk_dictionary_preview_metrics_text(text, preview, language="ru")

    assert "Savings" not in preview_content
    assert f"Original chars: {len(text)}" in metrics_content
    assert f"Encoded chars: {after_chars}" in metrics_content
    assert f"Char saving: {len(text) - after_chars}" in metrics_content
    assert "Dictionary chars" not in metrics_content
    assert "Encoded body chars" not in metrics_content
    assert f"Original tokens: {preview.original_tokens}" in metrics_content
    assert f"Encoded tokens: {encoded_tokens}" in metrics_content
    assert f"Saving tokens: {saving_tokens}" in metrics_content
    assert f"Символов до: {len(text)}" in ru_metrics_content
    assert "Original chars" not in ru_metrics_content
    assert "% saving:" in metrics_content


def test_gtk_ai_debug_event_row_splits_columns() -> None:
    row = _harness_debug_event_row(
        HarnessDebugEvent(
            event_id=7,
            task_dir=Path("/tmp/task"),
            agent_type=AgentType.CODEX,
            session_id="s1",
            hook_event="pre_tool_use",
            status_event=HarnessStatusEvent.TOOL_STARTED,
            icon="◆",
            message="Tool use started.",
            tool_name="Bash",
            tool_detail="python3 -m pytest",
            outcome="started",
            updated_at="2026-08-23T19:20:00+03:00",
        )
    )

    assert row == (
        "7",
        "2026-08-23T19:20:00+03:00",
        "◆",
        "TOOL",
        "pre_tool_use",
        "Bash",
        "started",
        "Tool use started.",
    )


def test_gtk_ai_debug_event_details_include_tool_command_without_output() -> None:
    text = _harness_debug_event_details_text(
        HarnessDebugEvent(
            event_id=7,
            task_dir=Path("/tmp/task"),
            agent_type=AgentType.CODEX,
            session_id="s1",
            hook_event="pre_tool_use",
            status_event=HarnessStatusEvent.TOOL_STARTED,
            icon="◆",
            message="Tool use started.",
            tool_name="Bash",
            tool_detail="python3 -m pytest tests/test_example.py",
            outcome="started",
            updated_at="2026-08-23T19:20:00+03:00",
        ),
        language="ru",
    )

    assert "Команда / аргументы:" in text
    assert "python3 -m pytest tests/test_example.py" in text
    assert "stdout" not in text.lower()
    assert "stderr" not in text.lower()


def test_gtk_ai_debug_event_row_uses_selected_language() -> None:
    row = _harness_debug_event_row(
        HarnessDebugEvent(
            event_id=8,
            task_dir=Path("/tmp/task"),
            agent_type=AgentType.CODEX,
            session_id="s1",
            hook_event="pre_tool_use",
            status_event=HarnessStatusEvent.TOOL_STARTED,
            icon="◆",
            message="Tool use started.",
            tool_name="Bash",
            tool_detail="python3 -m pytest",
            outcome="started",
            updated_at="2026-08-23T19:20:00+03:00",
        ),
        language="ru",
    )

    assert row[3] == "ТУЛЗА"
    assert row[6] == "начато"
    assert row[7] == "Вызов инструмента начат."
    assert "Нет событий хуков ИИ для сессии s1." == _harness_debug_events_text([], session_id="s1", language="ru")


def test_gtk_ai_debug_event_row_keeps_large_event_id_as_string() -> None:
    row = _harness_debug_event_row(
        HarnessDebugEvent(
            event_id=1787503705134248638,
            task_dir=Path("/tmp/task"),
            agent_type=AgentType.CODEX,
            session_id="s1",
            hook_event="post_tool_use",
            status_event=HarnessStatusEvent.TOOL_FINISHED,
            icon="▸",
            message="Tool use finished.",
            tool_name="Bash",
            tool_detail="",
            outcome="finished",
            updated_at="2026-08-23T19:20:01+03:00",
        )
    )

    assert row[0] == "1787503705134248638"


class FakeNotebook:
    def __init__(self, pages: list[object], current_page: int) -> None:
        self.pages = pages
        self.current_page = current_page

    def get_current_page(self) -> int:
        return self.current_page

    def get_nth_page(self, page_num: int) -> object:
        return self.pages[page_num]


def test_gtk_ai_debug_refresh_tick_skips_hidden_ai_debug_tab() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._closing = False
    gui.selected_task = object()
    refreshes: list[str] = []
    gui._refresh_ai_debug = lambda: refreshes.append("refresh")  # type: ignore[method-assign]

    assert gui._refresh_ai_debug_if_visible() is True
    assert refreshes == []

    assert gui._refresh_ai_debug_if_visible() is True
    assert refreshes == []


def test_gtk_ai_debug_refresh_tick_runs_for_visible_ai_debug_tab() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._closing = False
    gui.selected_task = object()
    gui.actions_page = object()
    gui.ai_debug_page = object()
    gui.notebook = FakeNotebook([gui.actions_page], 0)
    gui.console_notebook = FakeNotebook([object(), gui.ai_debug_page], 1)
    refreshes: list[str] = []
    gui._refresh_ai_debug = lambda: refreshes.append("refresh")  # type: ignore[method-assign]

    assert gui._refresh_ai_debug_if_visible() is True
    assert refreshes == ["refresh"]


def test_gtk_ai_debug_refresh_tick_stops_on_close() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._closing = True
    gui.selected_task = object()
    gui.ai_debug_refresh_source_id = 88

    assert gui._refresh_ai_debug_if_visible() is False

    assert gui.ai_debug_refresh_source_id is None


def test_gtk_task_action_reflow_skips_unchanged_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeActionWidget:
        def __init__(self, width: int) -> None:
            self.width = width
            self.parent: object | None = None

        def get_preferred_width(self) -> tuple[int, int]:
            return (self.width, self.width)

        def get_parent(self) -> object | None:
            return self.parent

    class FakeRow:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.children: list[FakeActionWidget] = []

        def set_halign(self, _align: object) -> None:
            return

        def pack_start(self, widget: FakeActionWidget, *_args: object) -> None:
            widget.parent = self
            self.children.append(widget)

    class FakeActionsBox:
        def __init__(self, width: int) -> None:
            self.width = width
            self.children: list[FakeRow] = []
            self.pack_count = 0
            self.remove_count = 0
            self.show_count = 0

        def get_allocated_width(self) -> int:
            return self.width

        def get_border_width(self) -> int:
            return 0

        def get_children(self) -> list[FakeRow]:
            return list(self.children)

        def pack_start(self, row: FakeRow, *_args: object) -> None:
            self.pack_count += 1
            self.children.append(row)

        def remove(self, row: FakeRow) -> None:
            self.remove_count += 1
            self.children.remove(row)

        def show_all(self) -> None:
            self.show_count += 1

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_action_reflow_source_id = 99
    gui.task_action_reflow_layout = None
    gui.task_reorder_group = None
    gui.task_action_reorder_preview = []
    gui.task_action_item_widgets = {
        "a": FakeActionWidget(10),
        "b": FakeActionWidget(10),
    }
    gui._task_action_order = lambda: ["a", "b"]  # type: ignore[method-assign]
    gui._update_task_action_button_selection = lambda: None  # type: ignore[method-assign]
    gui.task_actions_box = FakeActionsBox(width=100)
    monkeypatch.setattr(gtk_ui_module.Gtk, "Box", FakeRow)

    assert gui._reflow_task_action_buttons() is False

    assert gui.task_action_reflow_source_id is None
    assert gui.task_actions_box.pack_count == 1
    assert gui.task_actions_box.show_count == 1

    assert gui._reflow_task_action_buttons() is False

    assert gui.task_actions_box.pack_count == 1
    assert gui.task_actions_box.remove_count == 0
    assert gui.task_actions_box.show_count == 1

    gui.task_actions_box.width = 15

    assert gui._reflow_task_action_buttons() is False

    assert gui.task_actions_box.pack_count == 3
    assert gui.task_actions_box.remove_count == 1
    assert gui.task_actions_box.show_count == 2


def test_gtk_task_action_order_separates_workspace_actions() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_base_actions = [
        TaskAction(
            action_id="workspace:validate",
            label="Validate",
            command=("true",),
            cwd=Path("."),
            env={},
            source="workspace",
        ),
        TaskAction(
            action_id="workspace:validate-push",
            label="Validate push",
            command=("true",),
            cwd=Path("."),
            env={},
            source="workspace",
        ),
        TaskAction(
            action_id="workspace:task-check",
            label="Task check",
            command=("true",),
            cwd=Path("."),
            env={},
            source="workspace",
        ),
        TaskAction(
            action_id="build",
            label="Build",
            command=("true",),
            cwd=Path("."),
            env={},
        ),
    ]

    assert gui._workspace_action_order() == [
        "workspace:validate",
        "workspace:validate-push",
        "workspace:task-check",
    ]
    assert gui._task_action_order() == ["build"]


def test_gtk_task_action_button_uses_action_description_as_tooltip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FakeActionButton:
        def __init__(self) -> None:
            self.tooltip = ""
            self.style_context = FakeGtkStyleContext()

        def set_tooltip_text(self, text: str) -> None:
            self.tooltip = text

        def get_tooltip_text(self) -> str:
            return self.tooltip

        def set_size_request(self, *_args: object) -> None:
            return

        def set_focus_on_click(self, _value: bool) -> None:
            return

        def add_events(self, _events: object) -> None:
            return

        def connect(self, *_args: object) -> None:
            return

        def get_style_context(self) -> FakeGtkStyleContext:
            return self.style_context

        def set_relief(self, _relief: object) -> None:
            return

        def set_no_show_all(self, _value: bool) -> None:
            return

        def set_visible(self, _value: bool) -> None:
            return

        def set_sensitive(self, _value: bool) -> None:
            return

    class FakeActionRow:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.children: list[FakeActionButton] = []

        def pack_start(self, child: FakeActionButton, *_args: object) -> None:
            self.children.append(child)

        def show_all(self) -> None:
            return

        def get_children(self) -> list[FakeActionButton]:
            return list(self.children)

    action = TaskAction(
        action_id="workspace:install-repo-hooks",
        label="Install/update repo hooks",
        command=("true",),
        cwd=tmp_path,
        env={},
        source="workspace",
        description="Install hooks from repo-registry.",
    )
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_action_reorder_mode = False
    gui.task_action_buttons = {}
    gui.task_action_play_buttons = {}
    gui._on_task_action_clicked = lambda _action: None  # type: ignore[method-assign]
    gui._on_task_action_button_press = lambda *_args: False  # type: ignore[method-assign]
    gui._on_task_action_play_clicked = lambda *_args: None  # type: ignore[method-assign]
    gui._on_task_action_play_button_press = lambda *_args: False  # type: ignore[method-assign]
    gui._disable_action_hover_tracking = lambda _button: None  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module, "_compact_button", lambda *_args, **_kwargs: FakeActionButton())
    monkeypatch.setattr(gtk_ui_module.Gtk, "Box", FakeActionRow)
    monkeypatch.setattr(gtk_ui_module.Gtk.Button, "new_from_icon_name", lambda *_args: FakeActionButton())

    row = gui._task_action_button(action, shortcut=False)
    label_button = row.get_children()[0]

    assert label_button.get_tooltip_text() == "Install hooks from repo-registry."


def test_gtk_workspace_action_renderer_keeps_task_actions_out(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeActionWidget:
        def __init__(self) -> None:
            self.parent: object | None = None

        def get_parent(self) -> object | None:
            return self.parent

    class FakeRow:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.children: list[FakeActionWidget] = []

        def set_halign(self, _align: object) -> None:
            return

        def pack_start(self, widget: FakeActionWidget, *_args: object) -> None:
            widget.parent = self
            self.children.append(widget)

        def get_children(self) -> list[FakeActionWidget]:
            return list(self.children)

    class FakeActionsBox:
        def __init__(self) -> None:
            self.children: list[FakeRow] = []

        def pack_start(self, row: FakeRow, *_args: object) -> None:
            self.children.append(row)

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    workspace_validate = FakeActionWidget()
    workspace_task_check = FakeActionWidget()
    build = FakeActionWidget()
    gui.workspace_actions_box = FakeActionsBox()
    gui.task_action_item_widgets = {
        "workspace:validate": workspace_validate,
        "workspace:task-check": workspace_task_check,
        "build": build,
    }
    gui._workspace_action_order = lambda: ["workspace:validate", "workspace:task-check"]  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module.Gtk, "Box", FakeRow)

    gui._render_workspace_action_buttons()

    assert len(gui.workspace_actions_box.children) == 1
    assert gui.workspace_actions_box.children[0].children == [workspace_validate, workspace_task_check]
    assert build.parent is None


def test_gtk_task_action_size_allocate_skips_unchanged_width(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeActionsBox:
        def get_border_width(self) -> int:
            return 0

    class FakeAllocation:
        def __init__(self, width: int) -> None:
            self.width = width

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_actions_box = FakeActionsBox()
    gui.task_action_reflow_width = None
    gui.task_action_reflow_layout = None
    gui.task_action_reflow_source_id = None
    idle_callbacks: list[object] = []
    monkeypatch.setattr(gtk_ui_module.GLib, "idle_add", lambda callback: idle_callbacks.append(callback) or 77)

    gui._on_task_actions_box_size_allocate(gui.task_actions_box, FakeAllocation(100))

    assert gui.task_action_reflow_width == 100
    assert gui.task_action_reflow_source_id == 77
    assert idle_callbacks == [gui._reflow_task_action_buttons]

    gui.task_action_reflow_source_id = None
    gui.task_action_reflow_layout = (100, (("a",),))

    gui._on_task_actions_box_size_allocate(gui.task_actions_box, FakeAllocation(100))

    assert len(idle_callbacks) == 1
    assert gui.task_action_reflow_source_id is None

    gui._on_task_actions_box_size_allocate(gui.task_actions_box, FakeAllocation(120))

    assert gui.task_action_reflow_width == 120
    assert gui.task_action_reflow_source_id == 77
    assert len(idle_callbacks) == 2


def test_gtk_terminal_rendering_disables_blink_and_rewrap() -> None:
    class FakeTerminal:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def set_font(self, value: object) -> None:
            self.calls.append(("font", value))

        def set_cursor_blink_mode(self, value: object) -> None:
            self.calls.append(("cursor_blink", value))

        def set_text_blink_mode(self, value: object) -> None:
            self.calls.append(("text_blink", value))

        def set_enable_bidi(self, value: object) -> None:
            self.calls.append(("bidi", value))

        def set_enable_shaping(self, value: object) -> None:
            self.calls.append(("shaping", value))

        def set_redraw_on_allocate(self, value: object) -> None:
            self.calls.append(("redraw_on_allocate", value))

        def set_rewrap_on_resize(self, value: object) -> None:
            self.calls.append(("rewrap_on_resize", value))

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.text_font_size = 13
    terminal = FakeTerminal()

    gui._configure_terminal_rendering(terminal)  # type: ignore[arg-type]

    assert ("cursor_blink", Vte.CursorBlinkMode.OFF) in terminal.calls
    assert ("text_blink", Vte.TextBlinkMode.NEVER) in terminal.calls
    assert ("bidi", False) in terminal.calls
    assert ("shaping", False) in terminal.calls
    assert ("redraw_on_allocate", False) in terminal.calls
    assert ("rewrap_on_resize", False) in terminal.calls


def test_gtk_codex_terminal_pointer_rendering_disables_vte_mouse_state_churn() -> None:
    class FakeTerminal:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def set_mouse_autohide(self, value: bool) -> None:
            self.calls.append(("mouse_autohide", value))

        def set_allow_hyperlink(self, value: bool) -> None:
            self.calls.append(("allow_hyperlink", value))

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    terminal = FakeTerminal()

    gui._configure_codex_terminal_pointer_rendering(terminal)  # type: ignore[arg-type]

    assert terminal.calls == [
        ("mouse_autohide", False),
        ("allow_hyperlink", False),
    ]


def test_gtk_agent_terminal_event_mask_ignores_plain_pointer_motion() -> None:
    class FakeWindow:
        def __init__(self) -> None:
            self.events = (
                Gdk.EventMask.POINTER_MOTION_MASK
                | Gdk.EventMask.ENTER_NOTIFY_MASK
                | Gdk.EventMask.LEAVE_NOTIFY_MASK
            )

        def get_events(self) -> object:
            return self.events

        def set_events(self, events: object) -> None:
            self.events = events

    class FakeTerminal(FakeWindow):
        def __init__(self) -> None:
            super().__init__()
            self.window = FakeWindow()

        def get_window(self) -> FakeWindow:
            return self.window

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    terminal = FakeTerminal()

    gui._configure_agent_terminal_event_mask(terminal)  # type: ignore[arg-type]

    motion_masks = (
        Gdk.EventMask.POINTER_MOTION_MASK
        | Gdk.EventMask.POINTER_MOTION_HINT_MASK
        | Gdk.EventMask.ENTER_NOTIFY_MASK
        | Gdk.EventMask.LEAVE_NOTIFY_MASK
    )
    required_masks = (
        Gdk.EventMask.BUTTON_PRESS_MASK
        | Gdk.EventMask.BUTTON_RELEASE_MASK
        | Gdk.EventMask.BUTTON1_MOTION_MASK
    )
    assert terminal.events & motion_masks == 0
    assert terminal.window.events & motion_masks == 0
    assert terminal.events & required_masks == required_masks
    assert terminal.window.events & required_masks == required_masks


def test_gtk_button_helper_disables_hover_tracking() -> None:
    class FakeButton:
        def __init__(self) -> None:
            self.events: list[object] = []
            self.connections: list[tuple[str, object]] = []

        def add_events(self, events: object) -> None:
            self.events.append(events)

        def connect(self, signal: str, callback: object) -> None:
            self.connections.append((signal, callback))

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.label_widgets = {}
    gui._tr = lambda key: key  # type: ignore[method-assign]
    button = FakeButton()
    original_button = gtk_ui_module._button
    gtk_ui_module._button = lambda _label, _callback: button  # type: ignore[assignment]
    try:
        assert gui._button("settings", object()) is button
    finally:
        gtk_ui_module._button = original_button  # type: ignore[assignment]

    assert button.events
    assert not (int(button.events[0]) & int(Gdk.EventMask.POINTER_MOTION_MASK))
    assert ("event", gui._consume_action_hover_event) in button.connections
    assert ("motion-notify-event", gui._consume_action_hover_event) in button.connections
    assert gui.label_widgets["settings"] is button


def test_gtk_hover_filter_consumes_motion_enter_leave_only() -> None:
    class FakeEvent:
        def __init__(self, event_type: object, state: int = 0) -> None:
            self.type = event_type
            self.state = state

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._consume_action_hover_event(None, FakeEvent(Gdk.EventType.ENTER_NOTIFY)) is True
    assert gui._consume_action_hover_event(None, FakeEvent(Gdk.EventType.LEAVE_NOTIFY)) is True
    assert gui._consume_action_hover_event(None, FakeEvent(Gdk.EventType.MOTION_NOTIFY)) is True
    assert gui._consume_action_hover_event(None, FakeEvent(Gdk.EventType.BUTTON_PRESS)) is False


def test_gtk_terminal_passive_pointer_filter_preserves_selection_drag() -> None:
    class FakeEvent:
        def __init__(self, event_type: object, state: int = 0) -> None:
            self.type = event_type
            self.state = state

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.ENTER_NOTIFY)) is True
    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.LEAVE_NOTIFY)) is True
    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.PROXIMITY_IN)) is True
    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.PROXIMITY_OUT)) is True
    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.MOTION_NOTIFY)) is True
    assert (
        gui._consume_terminal_passive_pointer_event(
            None,
            FakeEvent(Gdk.EventType.MOTION_NOTIFY, int(Gdk.ModifierType.BUTTON1_MASK)),
        )
        is False
    )
    assert gui._consume_terminal_passive_pointer_event(None, FakeEvent(Gdk.EventType.BUTTON_PRESS)) is False


def test_codex_terminal_mouse_state_machine_controls_overlay() -> None:
    class FakeOverlay:
        def __init__(self) -> None:
            self.children: list[object] = []
            self.overlay_children: list[object] = []

        def add(self, child: object) -> None:
            self.children.append(child)

        def add_overlay(self, child: object) -> None:
            self.overlay_children.append(child)

    class FakeEventBox:
        def __init__(self) -> None:
            self.above_child: list[bool] = []
            self.sensitive: list[bool] = []
            self.visible: list[bool] = []
            self.children: list[object] = []
            self.connected: list[str] = []

        def set_above_child(self, value: bool) -> None:
            self.above_child.append(value)

        def set_sensitive(self, value: bool) -> None:
            self.sensitive.append(value)

        def hide(self) -> None:
            self.visible.append(False)

        def show(self) -> None:
            self.visible.append(True)

        def set_visible_window(self, _value: bool) -> None:
            pass

        def set_app_paintable(self, _value: bool) -> None:
            pass

        def set_halign(self, _value: object) -> None:
            pass

        def set_opacity(self, _value: float) -> None:
            pass

        def set_valign(self, _value: object) -> None:
            pass

        def set_hexpand(self, _value: bool) -> None:
            pass

        def set_vexpand(self, _value: bool) -> None:
            pass

        def set_size_request(self, _width: int, _height: int) -> None:
            pass

        def add_events(self, _events: object) -> None:
            pass

        def connect(self, signal: str, _callback: object) -> None:
            self.connected.append(signal)

    class FakeTerminal:
        def __init__(self) -> None:
            self.focus_count = 0
            self.connected: list[str] = []

        def grab_focus(self) -> None:
            self.focus_count += 1

        def add_events(self, _events: object) -> None:
            pass

        def connect(self, signal: str, _callback: object) -> None:
            self.connected.append(signal)

    class FakeEvent:
        def __init__(self, event_type: object, *, button: int = 0, state: int = 0) -> None:
            self.type = event_type
            self.button = button
            self.state = state

    overlay = FakeOverlay()
    event_box = FakeEventBox()
    terminal = FakeTerminal()
    events: list[tuple[str, str]] = []
    mouse = CodexTerminalMouseStateMachine(
        terminal,  # type: ignore[arg-type]
        lambda area, event: events.append((area, event)),
        overlay=overlay,  # type: ignore[arg-type]
        event_box=event_box,  # type: ignore[arg-type]
    )
    motion = FakeEvent(Gdk.EventType.MOTION_NOTIFY)
    drag_motion = FakeEvent(Gdk.EventType.MOTION_NOTIFY, state=int(Gdk.ModifierType.BUTTON1_MASK))
    left_press = FakeEvent(Gdk.EventType.BUTTON_PRESS, button=1)
    left_release = FakeEvent(Gdk.EventType.BUTTON_RELEASE, button=1)
    leave = FakeEvent(Gdk.EventType.LEAVE_NOTIFY)

    assert mouse.state == "idle"
    assert mouse.widget is overlay
    assert overlay.children == [terminal]
    assert overlay.overlay_children == [event_box]
    assert event_box.above_child == [True]
    assert event_box.sensitive == [True]
    assert event_box.visible == []
    assert event_box.children == []
    assert "button-press-event" in event_box.connected
    assert "button-release-event" in event_box.connected
    assert "motion-notify-event" in event_box.connected
    assert "focus-in-event" in terminal.connected
    assert "focus-out-event" in terminal.connected

    assert mouse.on_proxy_passive_pointer_event(event_box, motion) is True  # type: ignore[arg-type]
    assert events == [("codex-terminal-mouse", "drop-motion-notify")]

    assert mouse.on_proxy_button_press(event_box, left_press) is True  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert terminal.focus_count == 1
    assert event_box.above_child == [True, False]
    assert event_box.sensitive == [True, False]
    assert event_box.visible == [False]

    assert mouse.on_proxy_passive_pointer_event(event_box, drag_motion) is True  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert event_box.above_child == [True, False]
    assert event_box.sensitive == [True, False]
    assert event_box.visible == [False]

    assert mouse.on_terminal_button_release(terminal, left_release) is False  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert event_box.above_child == [True, False]

    assert mouse.on_terminal_leave_notify(terminal, leave) is False  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert event_box.above_child == [True, False]

    assert mouse.on_proxy_button_release(event_box, left_release) is True  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert event_box.above_child == [True, False]

    mouse.deactivate()
    assert mouse.state == "idle"
    assert event_box.above_child == [True, False, True]
    assert event_box.sensitive == [True, False, True]
    assert event_box.visible == [False, True]

    assert mouse.on_terminal_focus_in(terminal, leave) is False  # type: ignore[arg-type]
    assert mouse.state == "active"
    assert event_box.above_child == [True, False, True, False]
    assert event_box.sensitive == [True, False, True, False]
    assert event_box.visible == [False, True, False]

    assert mouse.on_terminal_focus_out(terminal, leave) is False  # type: ignore[arg-type]
    assert mouse.state == "idle"
    assert event_box.above_child == [True, False, True, False, True]
    assert event_box.sensitive == [True, False, True, False, True]
    assert event_box.visible == [False, True, False, True]


def test_codex_terminal_mouse_state_machine_receives_realized_gtk_button_signals() -> None:
    if Gdk.Display.get_default() is None:
        pytest.skip("real GTK event delivery requires DISPLAY")

    script = textwrap.dedent(
        """
        import sys

        import gi

        gi.require_version("Gdk", "3.0")
        gi.require_version("Gtk", "3.0")

        from gi.repository import Gdk
        from gi.repository import GLib
        from gi.repository import Gtk

        from agent_tools.agent_workspace.components.gtk_desktop.src.codex_terminal_mouse import (
            CodexTerminalMouseStateMachine,
        )

        def drain():
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

        terminal = Gtk.Label(label="terminal")
        records = []
        mouse = CodexTerminalMouseStateMachine(terminal, lambda area, event: records.append((area, event)))
        window = Gtk.Window()
        window.set_default_size(240, 120)
        window.add(mouse.widget)
        window.show_all()
        drain()

        event_window = mouse.event_box.get_window()
        if event_window is None:
            print("event window is missing")
            sys.exit(2)

        allocation = mouse.event_box.get_allocation()
        press = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        press.button = 1
        release = Gdk.Event.new(Gdk.EventType.BUTTON_RELEASE)
        release.button = 1

        press_ok = mouse.event_box.emit("button-press-event", press)
        drain()
        release_ok = mouse.event_box.emit("button-release-event", release)
        drain()
        window.destroy()
        drain()

        print(
            f"press_ok={press_ok} release_ok={release_ok} state={mouse.state} "
            f"allocation={allocation.width}x{allocation.height} "
            f"event_box_visible={mouse.event_box.get_visible()} "
            f"event_box_sensitive={mouse.event_box.get_sensitive()} "
            f"event_window={event_window is not None} records={records!r}"
        )
        expected = [
            ("codex-terminal-mouse", "activate-button-press"),
            ("codex-terminal-mouse", "keep-active-proxy-button-release"),
        ]
        sys.exit(
            0
            if (
                press_ok
                and release_ok
                and mouse.state == "active"
                and not mouse.event_box.get_visible()
                and not mouse.event_box.get_sensitive()
                and allocation.width > 0
                and allocation.height > 0
                and all(item in records for item in expected)
            )
            else 3
        )
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_gtk_codex_terminal_window_filter_removes_passive_pointer_events() -> None:
    class FakeNativeEvent:
        def __init__(self, event_type: int) -> None:
            self.type = event_type

    class FakeEvent:
        def __init__(self, event_type: object, state: int = 0) -> None:
            self.type = event_type
            self.state = state

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.ENTER_NOTIFY), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.LEAVE_NOTIFY), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.PROXIMITY_IN), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.PROXIMITY_OUT), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.MOTION_NOTIFY), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(FakeNativeEvent(6), FakeEvent(Gdk.EventType.NOTHING), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(FakeNativeEvent(7), FakeEvent(Gdk.EventType.NOTHING), None) == Gdk.FilterReturn.REMOVE
    assert gui._filter_codex_terminal_window_event(FakeNativeEvent(8), FakeEvent(Gdk.EventType.NOTHING), None) == Gdk.FilterReturn.REMOVE
    assert (
        gui._filter_codex_terminal_window_event(
            None,
            FakeEvent(Gdk.EventType.MOTION_NOTIFY, int(Gdk.ModifierType.BUTTON1_MASK)),
            None,
        )
        == Gdk.FilterReturn.CONTINUE
    )
    assert gui._filter_codex_terminal_window_event(None, FakeEvent(Gdk.EventType.BUTTON_PRESS), None) == Gdk.FilterReturn.CONTINUE


def test_gtk_codex_terminal_window_filter_installs_and_removes() -> None:
    class FakeWindow:
        def __init__(self, children: list[object] | None = None) -> None:
            self.filters: list[tuple[object, object]] = []
            self.children = children or []

        def add_filter(self, callback: object, data: object) -> None:
            self.filters.append((callback, data))

        def remove_filter(self, callback: object, data: object) -> None:
            self.filters.remove((callback, data))

        def get_children(self) -> list[object]:
            return self.children

    class FakeTerminal:
        def __init__(self) -> None:
            self.child_window = FakeWindow()
            self.window = FakeWindow([self.child_window])

        def get_window(self) -> FakeWindow:
            return self.window

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.codex_terminal_window_filters = {}
    terminal = FakeTerminal()

    gui._install_codex_terminal_window_filter(terminal)  # type: ignore[arg-type]
    gui._install_codex_terminal_window_filter(terminal)  # type: ignore[arg-type]

    assert len(terminal.window.filters) == 1
    assert len(terminal.child_window.filters) == 1
    assert len(gui.codex_terminal_window_filters) == 1

    gui._remove_codex_terminal_window_filter(terminal)  # type: ignore[arg-type]

    assert terminal.window.filters == []
    assert terminal.child_window.filters == []
    assert gui.codex_terminal_window_filters == {}


def test_gtk_codex_console_boundary_filter_is_codex_scoped() -> None:
    class FakeAllocation:
        width = 100
        height = 80

    class FakePage:
        def translate_coordinates(self, _widget: object, _x: int, _y: int) -> tuple[int, int]:
            return (10, 20)

        def get_allocation(self) -> FakeAllocation:
            return FakeAllocation()

    class FakeEvent:
        def __init__(self, event_type: object, x: int = 0, y: int = 0, state: int = 0) -> None:
            self.type = event_type
            self.x = x
            self.y = y
            self.state = state

    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    session = TerminalSession(1, Path("/tmp/task"), "codex", object(), FakePage())  # type: ignore[arg-type]
    gui._active_codex_terminal_session = lambda: session  # type: ignore[method-assign]

    assert gui._event_is_over_active_codex_console(object(), FakeEvent(Gdk.EventType.ENTER_NOTIFY, 15, 25))
    assert gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.ENTER_NOTIFY, 15, 25))
    assert gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.LEAVE_NOTIFY, 15, 25))
    assert gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.PROXIMITY_IN, 15, 25))
    assert gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.PROXIMITY_OUT, 15, 25))
    assert gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.MOTION_NOTIFY, 15, 25))
    assert not gui._consume_codex_console_boundary_event(
        object(),
        FakeEvent(Gdk.EventType.MOTION_NOTIFY, 15, 25, int(Gdk.ModifierType.BUTTON1_MASK)),
    )
    assert not gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.ENTER_NOTIFY, 500, 25))

    gui._active_codex_terminal_session = lambda: None  # type: ignore[method-assign]

    assert not gui._consume_codex_console_boundary_event(object(), FakeEvent(Gdk.EventType.ENTER_NOTIFY, 15, 25))


def test_gtk_abort_with_stack_dump_uses_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, str]] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    monkeypatch.setattr(
        gtk_ui_module,
        "abort_agent_workspace_with_stack_dump",
        lambda workspace, frontend: calls.append((workspace, frontend)),
    )

    gui._abort_with_stack_dump()

    assert calls == [(tmp_path, "gtk")]


def test_gtk_record_agent_interrupt_sets_circle_icon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    recorded: list[dict[str, object]] = []
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.harness_status_icon_cache = {task_dir: (1.0, "◆")}
    gui._refresh_task_row_style_for_task = lambda task_path: recorded.append({"refresh": task_path})  # type: ignore[method-assign]
    monkeypatch.setattr(gtk_ui_module, "record_harness_status", lambda *args, **kwargs: recorded.append(kwargs))
    session = TerminalSession(
        session_id=1,
        task_path=task_dir,
        kind="codex",
        terminal=None,  # type: ignore[arg-type]
        page=None,  # type: ignore[arg-type]
        busy=True,
        run_id="run-1",
    )

    gui._record_agent_interrupt(session)

    assert session.busy is False
    assert gui.harness_status_icon_cache == {}
    assert recorded[0]["icon"] == "○"
    assert recorded[0]["outcome"] == "interrupted"
    assert recorded[-1] == {"refresh": task_dir}


def test_gtk_task_agent_status_prefers_latest_harness_session_start_icon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    summary = discover_tasks_with_context(task_dir, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.harness_status_icon_cache = {}
    gui.terminal_sessions = {
        1: TerminalSession(
            session_id=1,
            task_path=summary.path,
            kind="codex",
            terminal=None,  # type: ignore[arg-type]
            page=None,  # type: ignore[arg-type]
            busy=False,
            run_id="run-1",
        )
    }
    gui._current_task_terminal_sessions = lambda task: list(gui.terminal_sessions.values())  # type: ignore[method-assign]
    gui._task_has_pending_agent_permission = lambda task: False  # type: ignore[method-assign]
    gui._task_is_external_active = lambda task: False  # type: ignore[method-assign]
    gui._task_agent_session_markers = lambda task: ()  # type: ignore[method-assign]
    monkeypatch.setattr(
        gtk_ui_module,
        "load_harness_debug_events",
        lambda task_path, limit=1: [
            HarnessDebugEvent(
                event_id=1,
                task_dir=summary.path,
                agent_type=AgentType.CODEX,
                session_id="run-1",
                hook_event="session_start",
                status_event=HarnessStatusEvent.SESSION_STARTED,
                icon="●",
                message="Context injected at session start.",
                tool_name="",
                tool_detail="",
                outcome="injected",
                updated_at="2026-08-24T10:21:59+03:00",
            )
        ],
    )

    assert gui._task_agent_status(summary) == "●"


def test_gtk_task_agent_status_ignores_harness_icon_after_agent_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    summary = discover_tasks_with_context(task_dir, tmp_path)
    save_task_agent_session(summary, "codex")
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.harness_status_icon_cache = {}
    gui.terminal_sessions = {
        1: TerminalSession(
            session_id=1,
            task_path=summary.path,
            kind="codex",
            terminal=None,  # type: ignore[arg-type]
            page=None,  # type: ignore[arg-type]
            exited=True,
            busy=False,
            run_id="run-1",
        )
    }
    gui._current_task_terminal_sessions = lambda task: list(gui.terminal_sessions.values())  # type: ignore[method-assign]
    gui._task_has_pending_agent_permission = lambda task: False  # type: ignore[method-assign]
    gui._task_is_external_active = lambda task: False  # type: ignore[method-assign]
    gui._task_agent_session_markers = lambda task: ("Ⅱ",)  # type: ignore[method-assign]
    monkeypatch.setattr(
        gtk_ui_module,
        "load_harness_debug_events",
        lambda task_path, limit=1: [
            HarnessDebugEvent(
                event_id=1,
                task_dir=summary.path,
                agent_type=AgentType.CODEX,
                session_id="run-1",
                hook_event="session_start",
                status_event=HarnessStatusEvent.SESSION_STARTED,
                icon="●",
                message="Context injected at session start.",
                tool_name="",
                tool_detail="",
                outcome="injected",
                updated_at="2026-08-24T10:21:59+03:00",
            )
        ],
    )

    assert gui._task_agent_status(summary) == "Ⅱ"


def test_gtk_ai_debug_store_accepts_large_event_id() -> None:
    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    store = Gtk.ListStore(str, str, str, str, str, str, str, str)
    row = _harness_debug_event_row(
        HarnessDebugEvent(
            event_id=1787503705134248638,
            task_dir=Path("/tmp/task"),
            agent_type=AgentType.CODEX,
            session_id="s1",
            hook_event="pre_tool_use",
            status_event=HarnessStatusEvent.TOOL_STARTED,
            icon="◆",
            message="Tool use started.",
            tool_name="Bash",
            tool_detail="",
            outcome="started",
            updated_at="2026-08-23T19:20:02+03:00",
        )
    )

    row_iter = store.append(row)

    assert store[row_iter][0] == "1787503705134248638"


def test_gtk_ai_debug_restore_prefers_selected_row() -> None:
    assert (
        _ai_debug_restore_event_id(
            ["1", "2", "3"],
            selected_id="2",
            visible_anchor_id="1",
        )
        == "2"
    )


def test_gtk_ai_debug_restore_uses_visible_anchor_without_selection() -> None:
    assert (
        _ai_debug_restore_event_id(
            ["1", "2", "3"],
            selected_id=None,
            visible_anchor_id="2",
        )
        == "2"
    )
    assert (
        _ai_debug_restore_event_id(
            ["1", "2", "3"],
            selected_id="9",
            visible_anchor_id="8",
        )
        is None
    )


def test_gtk_task_context_status_filter_defaults_to_active_only() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)

    assert gui._task_context_default_group_values("status", ("active", "resolved", "stale")) == ("active",)
    assert gui._task_context_default_group_values("severity", ("mid", "high")) == ("mid", "high")


def test_gtk_clear_task_context_filters_restores_active_status_default() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_context_filter_since = "2026-08-19"
    gui.task_context_filter_until = "2026-08-20"
    gui.task_context_severity_checks = {
        "mid": FakeGtkCheckButton(False),
        "high": FakeGtkCheckButton(True),
    }
    gui.task_context_status_checks = {
        "active": FakeGtkCheckButton(False),
        "resolved": FakeGtkCheckButton(True),
        "stale": FakeGtkCheckButton(True),
    }
    gui.task_context_label_checks = {
        "validation": FakeGtkCheckButton(False),
        "ui": FakeGtkCheckButton(True),
    }
    gui.task_context_filter_all_checks = {
        "severity": FakeGtkCheckButton(),
        "status": FakeGtkCheckButton(),
        "label": FakeGtkCheckButton(),
    }
    gui._updating_task_context_checks = False
    gui._update_task_context_date_buttons = lambda: None
    changed_calls: list[str] = []
    gui._on_task_context_filter_changed = lambda: changed_calls.append("changed")

    gui._clear_task_context_filters()

    assert gui.task_context_filter_since is None
    assert gui.task_context_filter_until is None
    assert {value: check.get_active() for value, check in gui.task_context_severity_checks.items()} == {
        "mid": True,
        "high": True,
    }
    assert {value: check.get_active() for value, check in gui.task_context_status_checks.items()} == {
        "active": True,
        "resolved": False,
        "stale": False,
    }
    assert {value: check.get_active() for value, check in gui.task_context_label_checks.items()} == {
        "validation": True,
        "ui": True,
    }
    assert gui.task_context_filter_all_checks["status"].get_active() is False
    assert gui.task_context_filter_all_checks["status"].inconsistent is True
    assert changed_calls == ["changed"]


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


def test_gtk_pane_separator_hit_test_uses_orientation() -> None:
    from gi.repository import Gtk

    horizontal = FakePane(Gtk.Orientation.HORIZONTAL, 100)
    vertical = FakePane(Gtk.Orientation.VERTICAL, 200)

    assert gtk_is_pane_separator_event(horizontal, FakePaneEvent(105, 40))
    assert not gtk_is_pane_separator_event(horizontal, FakePaneEvent(120, 100))
    assert gtk_is_pane_separator_event(vertical, FakePaneEvent(40, 205))
    assert not gtk_is_pane_separator_event(vertical, FakePaneEvent(200, 220))
    handle = object()
    assert gtk_is_pane_separator_event(FakePane(Gtk.Orientation.VERTICAL, 200, handle_window=handle), FakePaneEvent(0, 0, handle))


def test_gtk_pane_position_ratio_uses_orientation() -> None:
    from gi.repository import Gtk

    horizontal = FakePane(Gtk.Orientation.HORIZONTAL, 100, width=400, height=900)
    vertical = FakePane(Gtk.Orientation.VERTICAL, 225, width=800, height=300)

    assert gtk_pane_position_ratio(horizontal) == 0.25
    assert gtk_pane_position_ratio(vertical) == 0.75


def test_gtk_saved_split_ratios_do_not_require_removed_details_pane() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._initial_pane_layout_source_id = 1
    gui.main_pane = object()  # type: ignore[assignment]
    gui.actions_pane = object()  # type: ignore[assignment]
    gui.main_split_ratio = 0.25
    gui.actions_split_ratio = 0.38
    calls: list[tuple[object, float, int]] = []
    gui._set_pane_position_ratio = (  # type: ignore[method-assign]
        lambda pane, ratio, minimum=1: calls.append((pane, ratio, minimum))
    )
    gui._on_actions_pane_position_changed = lambda pane, param: None  # type: ignore[method-assign]

    assert gui._apply_saved_split_ratios() is False
    assert calls == [
        (gui.main_pane, 0.25, 360),
        (gui.actions_pane, 0.38, 1),
    ]
    assert gui._pane_layout_ready is True


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


def test_gtk_selectable_task_iter_skips_external_active_tasks(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("agent_tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    locked_path = tmp_path / "tasks" / "locked-task"
    open_path = tmp_path / "tasks" / "open-task"
    locked_path.mkdir(parents=True)
    open_path.mkdir(parents=True)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(locked_path)
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(open_path)
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
    monkeypatch.setattr("agent_tools.agent_workspace.components.task_sessions.src.sessions._process_is_agent_workspace_owner", lambda _pid: True)
    monkeypatch.setattr("agent_tools.agent_workspace.components.task_sessions.src.sessions._current_boot_id", lambda: "current-boot")
    monkeypatch.setattr("agent_tools.agent_workspace.components.task_sessions.src.sessions._process_start_time_ticks", lambda _pid: 100)
    monkeypatch.setattr("agent_tools.agent_workspace.components.task_sessions.src.sessions._process_start_time_epoch", lambda _pid: os.path.getmtime(task_state_path(summary)) - 10)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.terminal_sessions = {}
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
    assert columns == [0, 1, 7]
    assert values == ["□", "sample-task", int(Pango.Weight.NORMAL)]


def test_gtk_refresh_task_row_styles_skips_unchanged_store_values(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_store = FakeGtkTaskStore(
        [
            ["□", "sample-task", summary, "", False, "", False, int(Pango.Weight.NORMAL), False],
        ]
    )
    gui.terminal_sessions = {}
    gui.theme = "dark"
    gui.selected_task = None
    gui._task_has_resumable_agent_session = lambda _task: False
    gui._task_is_external_active = lambda _task: False
    gui._task_agent_status = lambda _task: "□"
    gui._task_label = lambda task: task.name
    gui._ensure_selected_task_is_selectable = lambda: None

    gui._refresh_task_row_styles()

    assert gui.task_store.set_calls == []


def test_gtk_task_label_shows_session_discovery_pending_marker(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_session_discovery = TaskSessionDiscoveryState(pending={summary.path})

    assert gui._task_label(summary) == "◆ sample-task"

    gui.task_session_discovery.finish(summary.path)

    assert gui._task_label(summary) == "sample-task"


def test_gtk_animate_agent_status_updates_only_status_column(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.task_store = FakeGtkTaskStore(
        [
            ["□", "sample-task", summary, "#111", True, "#eee", True, 700, True],
        ]
    )
    gui.terminal_sessions = {}
    gui._closing = False
    gui._running_agent_sessions = lambda: [object()]
    gui._task_agent_status = lambda _task: "▸"

    assert gui._animate_agent_status()

    assert gui.task_store.set_calls == [(0, [0], ["▸"])]
    assert gui.task_store.rows[0][1:] == [
        "sample-task",
        summary,
        "#111",
        True,
        "#eee",
        True,
        700,
        True,
    ]


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
    ensure_task_context_database(locked_path)
    (open_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(open_path)
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
    ensure_task_context_database(first_path)
    (second_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(second_path)
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
    ensure_task_context_database(open_path)
    (locked_path / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(locked_path)
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


def test_gtk_save_settings_persists_mcp_options(monkeypatch: object, tmp_path: Path) -> None:
    saved: list[dict[str, object]] = []
    monkeypatch.setattr(gtk_ui_module, "save_agent_workspace_settings", lambda settings: saved.append(settings))
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.text_font_size = 13
    gui.button_font_size = 12
    gui.theme = "dark"
    gui.language = "en"
    gui.default_agent = "codex"
    gui.default_codex_model = "gpt-5.5"
    gui.default_codex_reasoning = "medium"
    gui.default_claude_model = "sonnet"
    gui.default_claude_effort = "medium"
    gui.codex_animations_enabled = False
    gui.claude_animations_enabled = False
    gui.limited_bash_output_tokens = 2000
    gui.limited_bash_head_tokens = 2000
    gui.limited_bash_tail_tokens = 3000
    gui.limited_bash_heartbeat_seconds = 15
    gui.limited_bash_heartbeat_tokens = 700
    gui.system_prompt = "Use workspace policy."
    gui.inject_task_context_prompt = True
    gui.mcp_enabled_groups = ("search", "python")
    gui.mcp_trusted = True
    gui.task_dictionary_auto_discovery = True
    gui.task_dictionary_min_occurrences = 2
    gui.task_dictionary_min_saving = 12
    gui.task_dictionary_min_term_length = 5
    gui.task_dictionary_max_term_words = 3
    gui.task_dictionary_strip_articles = True
    gui.task_dictionary_preview_text = "Agent Workspace"
    gui.last_window_width = 1200
    gui.last_window_height = 800
    gui.last_window_x = 10
    gui.last_window_y = 20
    gui.main_split_ratio = 0.4
    gui.details_split_ratio = 0.6
    gui.actions_split_ratio = 0.3
    gui.workspace = tmp_path
    gui.recent_workspaces = [str(tmp_path)]

    gui._save_settings()

    assert saved[0]["mcp_enabled_groups"] == [
        "search",
        "python",
        "task_context",
        "task_actions",
        "commit_messages",
        "validation",
    ]
    assert saved[0]["mcp_trusted"] is True
    assert saved[0]["limited_bash_head_tokens"] == 2000
    assert saved[0]["limited_bash_tail_tokens"] == 3000
    assert saved[0]["limited_bash_heartbeat_seconds"] == 15
    assert saved[0]["limited_bash_heartbeat_tokens"] == 700


def test_gtk_mcp_trust_toggle_confirm_applies_requested_state() -> None:
    check = FakeCheckButton(active=True)
    applied: list[bool] = []

    confirmed = _apply_mcp_trusted_check_toggle(
        check,
        False,
        lambda: True,
        lambda: False,
        applied.append,
    )

    assert confirmed is True
    assert check.get_active() is True
    assert applied == [True]


def test_gtk_mcp_trust_toggle_confirm_reverts_rejected_state_without_apply() -> None:
    check = FakeCheckButton(active=False)
    applied: list[bool] = []

    confirmed = _apply_mcp_trusted_check_toggle(
        check,
        True,
        lambda: False,
        lambda: False,
        applied.append,
    )

    assert confirmed is True
    assert check.get_active() is True
    assert applied == []


def test_gtk_mcp_trust_toggle_apply_failure_reverts_requested_state() -> None:
    check = FakeCheckButton(active=False)

    def fail_apply(_trusted: bool) -> None:
        raise OSError("cannot write config")

    with pytest.raises(OSError, match="cannot write config"):
        _apply_mcp_trusted_check_toggle(
            check,
            True,
            lambda: False,
            lambda: True,
            fail_apply,
        )

    assert check.get_active() is True


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


def test_gtk_console_notebook_switch_deactivates_agent_terminal_mouse(tmp_path: Path) -> None:
    class FakeAgentMouse:
        def __init__(self) -> None:
            self.deactivate_count = 0

        def deactivate(self) -> None:
            self.deactivate_count += 1

    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    codex_page = object()
    claude_page = object()
    shell_page = object()
    codex_mouse = FakeAgentMouse()
    claude_mouse = FakeAgentMouse()
    codex_session = TerminalSession(
        7,
        summary.path,
        "codex",
        object(),  # type: ignore[arg-type]
        codex_page,  # type: ignore[arg-type]
        terminal_mouse=codex_mouse,  # type: ignore[arg-type]
    )
    claude_session = TerminalSession(
        9,
        summary.path,
        "claude",
        object(),  # type: ignore[arg-type]
        claude_page,  # type: ignore[arg-type]
        terminal_mouse=claude_mouse,  # type: ignore[arg-type]
    )
    shell_session = TerminalSession(8, summary.path, "shell", object(), shell_page)  # type: ignore[arg-type]
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {
        codex_session.session_id: codex_session,
        claude_session.session_id: claude_session,
        shell_session.session_id: shell_session,
    }
    gui.last_active_terminal_by_task = {}
    gui._refreshing_console_tabs = False
    gui.last_active_console_page_by_task = {}

    gui._on_console_notebook_switch_page(object(), codex_page, 0)  # type: ignore[arg-type]

    assert codex_mouse.deactivate_count == 0
    assert claude_mouse.deactivate_count == 1

    gui._on_console_notebook_switch_page(object(), shell_page, 1)  # type: ignore[arg-type]

    assert codex_mouse.deactivate_count == 1
    assert claude_mouse.deactivate_count == 2

    gui._on_console_notebook_switch_page(object(), codex_page, 0)  # type: ignore[arg-type]

    assert codex_mouse.deactivate_count == 1
    assert claude_mouse.deactivate_count == 3


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
    ensure_task_context_database(task_one)
    (task_two / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task_two)
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
    ensure_task_context_database(task_one)
    (task_two / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task_two)
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
    gui.language = "en"
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
    gui._details_tab_active = lambda: False
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
    assert gui.console_notebook.pages == [task_one_agent_page, task_two_shell_page]
    assert gui.console_notebook.get_current_page() == 1
    assert task_two_shell.terminal.focused
    assert gui.last_active_terminal_by_task == {summary_one.path: task_one_shell.session_id}
    assert artifact_events == ["store"]


def test_gtk_task_selection_refreshes_details_only_when_details_tab_is_active(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    selection = FakeGtkSelection(FakeGtkTaskStore([[None, "sample-task", summary]]), 0)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.workspace = tmp_path
    gui.language = "en"
    gui.default_agent = "codex"
    gui._updating_task_selection = False
    gui.selected_task = None
    gui.terminal_sessions = {}
    gui.last_active_terminal_by_task = {}
    gui._refreshing_console_tabs = False
    gui.console_notebook = FakeGtkConsoleNotebook([])
    gui.ai_agent_page = object()
    gui.ai_agent_terminal_box = None
    gui._ensure_ai_agent_console_page = lambda: None
    gui._clear_ai_agent_terminal_page = lambda: None
    gui._task_is_external_active = lambda _task: False
    gui._remember_current_console_tab = lambda: None
    gui._reset_actions = lambda: None
    gui._watch_task_actions = lambda _task: None
    gui._artifacts_tab_active = lambda: False
    gui.artifact_store = type("ArtifactStore", (), {"clear": lambda self: None})()
    gui._load_task_action_buttons = lambda: None
    gui._set_selected_agent = lambda _agent: None
    gui._renumber_terminal_tabs = lambda _task: None
    gui._refresh_console_tabs_for_task = lambda _task: None
    gui._actions_tab_active = lambda: False
    gui._update_codex_button_state = lambda: None
    gui._show_terminal_tab = lambda _session, renumber=True: None
    calls: list[str] = []
    gui._refresh_selected_task_details = lambda leave_edit=False: calls.append(f"details:{leave_edit}")  # type: ignore[method-assign]

    gui._details_tab_active = lambda: False
    gui._on_task_selected(selection)  # type: ignore[arg-type]

    assert calls == []

    gui._details_tab_active = lambda: True
    gui._on_task_selected(selection)  # type: ignore[arg-type]

    assert calls == ["details:True"]


def test_gtk_task_context_journal_renders_goal_first(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "findings", "Finding body")
    set_slot(task, "goal", "Goal body")
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.language = "en"
    gui.task_context_encoded_check = FakeGtkCheckButton(False)
    gui.context_view = object()
    gui._refresh_task_context_label_filter = lambda _entries: None
    rendered: list[str] = []
    gui._set_markdown = lambda _view, text: rendered.append(text)

    gui._render_task_context_details()

    assert rendered
    assert rendered[0].index("| Goal") < rendered[0].index("| Findings")
    assert "Goal body" in rendered[0]
    assert "Finding body" in rendered[0]


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


def test_gtk_main_notebook_switch_refreshes_details_tab(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.actions_page = object()
    gui.details_page = object()
    gui.artifacts_page = object()
    calls: list[str] = []
    gui._load_task_action_buttons = lambda: calls.append("actions")
    gui._ensure_default_console_for_selected_task = lambda: calls.append("console")
    gui._restore_last_console_page_for_selected_task = lambda: calls.append("restore")
    gui._load_task_artifacts = lambda _task: calls.append("artifacts")
    gui._refresh_selected_task_details = lambda: calls.append("details")

    gui._on_main_notebook_switch_page(object(), gui.details_page, 1)  # type: ignore[arg-type]

    assert calls == ["details"]


def test_gtk_main_notebook_restores_actions_console_tab_after_details(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = object()
    session = TerminalSession(9, summary.path, "shell", object(), page)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.actions_page = object()
    gui.details_page = object()
    gui.artifacts_page = object()
    gui.active_main_page = gui.actions_page
    gui.terminal_sessions = {session.session_id: session}
    gui.last_active_terminal_by_task = {}
    gui.console_notebook = FakeGtkConsoleNotebook([page], current_page=0)
    calls: list[tuple[str, int | None]] = []
    gui._load_task_action_buttons = lambda: calls.append(("actions", None))
    gui._ensure_default_console_for_selected_task = lambda: calls.append(("console", None))
    gui._load_task_artifacts = lambda _task: calls.append(("artifacts", None))
    gui._activate_visible_terminal = lambda session_id, *, remember: calls.append(("restore", session_id))
    gui._refresh_selected_task_details = lambda: None

    gui._on_main_notebook_switch_page(object(), gui.details_page, 1)  # type: ignore[arg-type]
    gui._on_main_notebook_switch_page(object(), gui.actions_page, 0)  # type: ignore[arg-type]

    assert gui.last_active_terminal_by_task == {summary.path: session.session_id}
    assert calls == [("actions", None), ("console", None), ("restore", session.session_id)]


def test_gtk_main_notebook_restores_ai_agent_tab_after_details(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    ai_page = object()
    shell_page = object()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.actions_page = object()
    gui.details_page = object()
    gui.artifacts_page = object()
    gui.active_main_page = gui.actions_page
    gui.ai_agent_page = ai_page
    gui.terminal_sessions = {}
    gui.last_active_terminal_by_task = {summary.path: 12}
    gui.last_active_console_page_by_task = {}
    gui.console_notebook = FakeGtkConsoleNotebook([ai_page, shell_page], current_page=0)
    calls: list[str] = []
    gui._load_task_action_buttons = lambda: calls.append("actions")
    gui._ensure_default_console_for_selected_task = lambda: calls.append("console")
    gui._load_task_artifacts = lambda _task: calls.append("artifacts")
    gui._activate_visible_terminal = lambda _session_id, *, remember: calls.append("restore")
    gui._refresh_selected_task_details = lambda: None

    gui._on_main_notebook_switch_page(object(), gui.details_page, 1)  # type: ignore[arg-type]
    gui.console_notebook.set_current_page(1)
    gui._on_main_notebook_switch_page(object(), gui.actions_page, 0)  # type: ignore[arg-type]

    assert gui.console_notebook.get_current_page() == 0
    assert gui.last_active_console_page_by_task == {summary.path: "ai-agent"}
    assert calls == ["actions", "console"]


def test_gtk_initial_default_console_keeps_ai_agent_tab_active(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    ai_page = object()
    shell_page = object()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.ai_agent_page = ai_page
    gui.console_notebook = FakeGtkConsoleNotebook([ai_page, shell_page], current_page=0)
    gui.last_active_terminal_by_task = {}
    gui.last_active_console_page_by_task = {}
    gui._current_task_terminal_sessions = lambda _task: []  # type: ignore[method-assign]

    def new_console(*_args: object, task: TaskSummary | None = None) -> int:
        gui.console_notebook.set_current_page(1)
        gui.last_active_terminal_by_task[summary.path] = 42
        return 42

    gui.new_console = new_console  # type: ignore[method-assign]

    gui._ensure_default_console_for_selected_task()

    assert gui.console_notebook.get_current_page() == 0
    assert gui.last_active_console_page_by_task == {summary.path: "ai-agent"}


def test_gtk_default_console_does_not_override_saved_shell_tab(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    ai_page = object()
    shell_page = object()
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.selected_task = summary
    gui.ai_agent_page = ai_page
    gui.console_notebook = FakeGtkConsoleNotebook([ai_page, shell_page], current_page=0)
    gui.last_active_terminal_by_task = {summary.path: 41}
    gui.last_active_console_page_by_task = {summary.path: "session:41"}
    gui._current_task_terminal_sessions = lambda _task: []  # type: ignore[method-assign]

    def new_console(*_args: object, task: TaskSummary | None = None) -> int:
        gui.console_notebook.set_current_page(1)
        return 42

    gui.new_console = new_console  # type: ignore[method-assign]

    gui._ensure_default_console_for_selected_task()

    assert gui.console_notebook.get_current_page() == 1
    assert gui.last_active_console_page_by_task == {summary.path: "session:41"}


def test_gtk_terminal_text_tail_reads_recent_text() -> None:
    terminal = FakeGtkTextTerminal("a" * 5000 + "requires approval")

    tail = gtk_terminal_text_tail(terminal)

    assert len(tail) == 4000
    assert tail.endswith("requires approval")


def test_gtk_theme_colors_cover_widget_css_keys() -> None:
    source = Path(gtk_ui_module.__file__).read_text(encoding="utf-8")
    required = set(re.findall(r"colors\['([^']+)'\]", source))

    assert required <= set(gtk_theme_colors("dark"))
    assert required <= set(gtk_theme_colors("light"))


def test_gtk_ui_uses_system_cursor_theme_instead_of_pixbuf_workaround() -> None:
    source = Path(gtk_ui_module.__file__).read_text(encoding="utf-8")

    assert "GdkPixbuf" not in source
    assert "new_from_pixbuf" not in source
    assert "set_cursor(cursor)" not in source


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
    assert GTK_TRANSLATIONS["ru"]["system_prompt"] == "Системный промпт"
    assert GTK_TRANSLATIONS["ru"]["settings_updates"] == "Обновления"
    assert GTK_TRANSLATIONS["ru"]["settings_check_updates"] == "Проверить доступные обновления"
    assert GTK_TRANSLATIONS["ru"]["settings_apply_update"] == "Обновить"
    assert GTK_TRANSLATIONS["ru"]["settings_update_running"] == "Обновление Agent Workspace..."
    assert GTK_TRANSLATIONS["ru"]["settings_update_confirm_title"] == "Обновить Agent Workspace?"
    assert "закроется" in GTK_TRANSLATIONS["ru"]["settings_update_confirm_body"]
    assert GTK_TRANSLATIONS["ru"]["settings_mcp_trust_confirm_title"] == "Доверять MCP-утилитам Agent Workspace?"
    assert "перезапустите" in GTK_TRANSLATIONS["ru"]["settings_mcp_trust_confirm_body"]
    assert GTK_TRANSLATIONS["ru"]["settings_mcp_trust_confirm_button"] == "Доверять MCP"
    assert GTK_TRANSLATIONS["ru"]["settings_mcp_trust_disable_confirm_title"] == (
        "Перестать доверять MCP-утилитам Agent Workspace?"
    )
    assert "старые настройки доверия MCP" in GTK_TRANSLATIONS["ru"]["settings_mcp_trust_disable_confirm_body"]
    assert GTK_TRANSLATIONS["ru"]["settings_mcp_trust_disable_confirm_button"] == "Убрать доверие MCP"
    assert GTK_TRANSLATIONS["ru"]["codex_animations_enabled"] == "Анимации Codex"
    assert GTK_TRANSLATIONS["ru"]["claude_animations_enabled"] == "Анимации Claude"
    assert GTK_TRANSLATIONS["ru"]["limited_bash_output_tokens"] == "Лимит вывода Bash, токены"
    assert GTK_TRANSLATIONS["ru"]["limited_bash_head_tokens"] == "Бюджет начала Bash, токены"
    assert GTK_TRANSLATIONS["ru"]["limited_bash_tail_tokens"] == "Бюджет конца Bash, токены"
    assert GTK_TRANSLATIONS["ru"]["limited_bash_heartbeat_seconds"] == "Интервал heartbeat Bash, секунды"
    assert GTK_TRANSLATIONS["ru"]["limited_bash_heartbeat_tokens"] == "Бюджет heartbeat Bash, токены"
    assert GTK_TRANSLATIONS["ru"]["ok"] == "ОК"
    assert GTK_TRANSLATIONS["ru"]["ai_debug_tab"] == "ИИ дебаг"
    assert GTK_TRANSLATIONS["ru"]["ai_debug_column_tool"] == "Инструмент"
    assert GTK_TRANSLATIONS["ru"]["context_view_encoded"] == "Закодировано"
    assert GTK_TRANSLATIONS["ru"]["settings_dictionary_preview_text"] == "Текст для проверки"
    assert GTK_TRANSLATIONS["uk"]["ok"] == "ОК"
    assert "закроет текущую сессию" in GTK_TRANSLATIONS["ru"]["confirm_switch_agent_body"]
    assert "ссылка на продолжение" in GTK_TRANSLATIONS["ru"]["confirm_delete_saved_agent_session_body"]
    assert "ссылка на продолжение сессии будет удалена" in GTK_TRANSLATIONS["ru"]["confirm_reset_agent_session_body"]
    assert GTK_TRANSLATIONS["ru"]["confirm_reset_agent_session_button"] == "Сбросить сессию"
    assert "остановит локальные процессы" in GTK_TRANSLATIONS["ru"]["confirm_close_running_agents_body"]
    assert "Предлагаемая команда установки" in GTK_TRANSLATIONS["ru"]["install_agent_body"]
    assert GTK_TRANSLATIONS["ru"]["delete_artifacts"] == "Удалить артефакты"
    assert GTK_TRANSLATIONS["ru"]["open_containing_folder"] == "Открыть содержащую папку"
    assert GTK_TRANSLATIONS["ru"]["open_workspace_dialog"] == "Открыть workspace"
    assert GTK_TRANSLATIONS["ru"]["create_workspace_dialog"] == "Создать workspace"
    assert GTK_TRANSLATIONS["ru"]["workspace_switch_failed"] == "Не удалось переключить workspace"
    assert GTK_TRANSLATIONS["ru"]["other_artifacts"] == "Другие артефакты"
    assert GTK_TRANSLATIONS["ru"]["updated"] == "Обновлено"
    assert GTK_TRANSLATIONS["uk"]["manual_usage_section"] == "Основи"
    assert GTK_TRANSLATIONS["uk"]["manual_status_section"] == "Статуси в колонці ШІ"
    assert GTK_TRANSLATIONS["ru"]["manual_status_label_waiting"] == "Ожидает"
    assert GTK_TRANSLATIONS["ru"]["manual_status_label_prompt"] == "Активен"
    assert GTK_TRANSLATIONS["ru"]["manual_status_label_tool"] == "Работа"
    assert GTK_TRANSLATIONS["ru"]["manual_status_label_interrupted"] == "Прервано"
    assert GTK_TRANSLATIONS["uk"]["task_agent_status_column"] == "ШІ"
    assert GTK_TRANSLATIONS["uk"]["ai_debug_tab"] == "ШІ дебаг"
    assert GTK_TRANSLATIONS["uk"]["settings_dictionary_preview_text"] == "Текст для перевірки"
    assert GTK_TRANSLATIONS["uk"]["run_ai_agent"] == "Запустити ШІ агента"
    assert GTK_TRANSLATIONS["uk"]["manual_label_reset"] == "Скидання"
    assert "workspace розбитий на задачі" in GTK_TRANSLATIONS["uk"]["manual_usage_concept"]
    assert "контексті поточної задачі" in GTK_TRANSLATIONS["uk"]["manual_usage_agent"]
    assert "Shift" in GTK_TRANSLATIONS["uk"]["manual_usage_copy"]
    assert "TASK_ACTIONS.json" in GTK_TRANSLATIONS["uk"]["manual_usage_actions"]


def test_gtk_manual_status_entries_cover_harness_status_icons() -> None:
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui._tr = lambda key: GTK_TRANSLATIONS["ru"][key]  # type: ignore[method-assign]

    assert [entry[0] for entry in gui._manual_status_entries()] == ["●", "Ⅱ", "□", "▸", "◆", "○", "×"]


def test_agent_workspace_string_json_files_are_package_resources() -> None:
    for filename in (
        "gtk_language_catalog.json",
        "gtk_translation_catalog.json",
        "gtk_ui_catalog.json",
        "tk_catalog.json",
        "workspace_catalog.json",
    ):
        content = localization_catalog_text(filename)
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

    monkeypatch.setattr(
        "agent_tools.agent_workspace.components.gtk_desktop.src.gtk_open.shutil.which",
        fake_which,
    )

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


def test_gtk_agent_restore_output_check_clears_missing_session(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    save_task_agent_session(summary, "codex", session_id="71ca3372-3c10-4501-ad2a-145c5b9305de")
    page = FakeFrame()
    terminal = FakeGtkTextTerminal(
        "No conversation found with session ID: 71ca3372-3c10-4501-ad2a-145c5b9305de"
    )
    session = TerminalSession(1, summary.path, "codex", terminal, page)
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

    assert not gui._check_agent_restore_output(session.session_id, time.monotonic() + 10)

    assert session.session_id not in gui.terminal_sessions
    assert page.destroyed
    assert not load_task_agent_session(summary, "codex").resume


def test_gtk_agent_restore_output_check_ignores_permission_prompt(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)
    page = FakeFrame()
    terminal = FakeGtkTextTerminal("Allow this command to run? [y/N]")
    session = TerminalSession(1, summary.path, "codex", terminal, page, busy=True)
    gui = WorkspaceGtkGui.__new__(WorkspaceGtkGui)
    gui.terminal_sessions = {1: session}
    gui._refresh_task_row_styles = lambda: pytest.fail("permission prompt should not refresh rows")  # type: ignore[method-assign]

    assert gui._check_agent_restore_output(session.session_id, time.monotonic() + 10)

    assert session.busy
    assert not session.permission_pending
