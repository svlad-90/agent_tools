from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import shlex
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

from .core import TASK_ACTIONS_FILE
from .core import TaskAction
from .core import TaskSummary
from .core import WORKSPACE_GUI_LANGUAGES
from .core import WORKSPACE_GUI_THEMES
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import load_task_actions
from .core import load_workspace_gui_settings
from .core import read_task_file
from .core import render_markdown_chunks
from .core import save_workspace_gui_settings


TRANSLATIONS = {
    "en": {
        "actions": "Actions",
        "add_task": "Add task",
        "artifacts": "Artifacts",
        "button_font_size": "Button font size",
        "cancel": "Cancel",
        "close": "Close",
        "confirm_close_console_body": "The console session will be closed.",
        "confirm_close_console_title": "Close console?",
        "confirm_delete_task_body": "This will permanently delete the task directory.",
        "confirm_delete_task_title": "Delete selected task?",
        "confirm_delete_artifacts_body": "Files will be permanently deleted.",
        "confirm_delete_artifacts_title": "Delete artifacts?",
        "context": "context",
        "delete_all_artifacts": "Delete all task artifacts",
        "delete_artifact": "Delete artifact",
        "delete_artifact_group": "Delete artifact group",
        "delete_artifacts": "Delete artifacts",
        "delete_task": "Delete task",
        "desc": "desc",
        "details": "Details",
        "diagrams": "Diagrams",
        "diff_reports": "Diff reports",
        "edit": "Edit",
        "git_status": "Git status",
        "language": "Language",
        "logs": "Logs",
        "missing_context": "missing context",
        "missing_desc": "missing desc",
        "new": "New",
        "no_git_repos": "No git repositories found under dev/.",
        "ok": "OK",
        "open_dev": "Open dev folder",
        "open_task": "Open task folder",
        "open_workspace": "Open Workspace",
        "refresh": "Refresh",
        "reload_actions": "Reload actions",
        "run_codex": "Run Codex",
        "run_task_check": "Run task_check",
        "save": "Save",
        "scan_repos": "Scan repos",
        "scanning_repos": "Scanning repositories...",
        "select_task_first": "Select a task first",
        "settings": "Settings",
        "settings_title": "Workspace GUI settings",
        "task_already_exists": "Task already exists",
        "task": "Task",
        "task_details": "Task Details",
        "task_name": "Task name",
        "tasks": "tasks",
        "text_font_size": "Text font size",
        "theme": "Theme",
        "window_title": "Workspace GUI",
    },
    "ru": {
        "actions": "Действия",
        "add_task": "Добавить задачу",
        "artifacts": "Артефакты",
        "button_font_size": "Размер шрифта кнопок",
        "cancel": "Отмена",
        "close": "Закрыть",
        "confirm_close_console_body": "Консольная сессия будет закрыта.",
        "confirm_close_console_title": "Закрыть консоль?",
        "confirm_delete_task_body": "Папка задачи будет удалена безвозвратно.",
        "confirm_delete_task_title": "Удалить выбранную задачу?",
        "confirm_delete_artifacts_body": "Файлы будут удалены безвозвратно.",
        "confirm_delete_artifacts_title": "Удалить артефакты?",
        "context": "контекст",
        "delete_all_artifacts": "Удалить все артефакты задачи",
        "delete_artifact": "Удалить артефакт",
        "delete_artifact_group": "Удалить группу артефактов",
        "delete_artifacts": "Удалить артефакты",
        "delete_task": "Удалить задачу",
        "desc": "описание",
        "details": "Детали",
        "diagrams": "Диаграммы",
        "diff_reports": "Diff-отчеты",
        "edit": "Редактировать",
        "git_status": "Git status",
        "language": "Язык",
        "logs": "Логи",
        "missing_context": "нет контекста",
        "missing_desc": "нет описания",
        "new": "Новая",
        "no_git_repos": "В dev/ не найдены git-репозитории.",
        "ok": "OK",
        "open_dev": "Открыть dev",
        "open_task": "Открыть папку задачи",
        "open_workspace": "Открыть workspace",
        "refresh": "Обновить",
        "reload_actions": "Обновить actions",
        "run_codex": "Запустить Codex",
        "run_task_check": "Run task_check",
        "save": "Сохранить",
        "scan_repos": "Сканировать репо",
        "scanning_repos": "Сканирование репозиториев...",
        "select_task_first": "Сначала выбери задачу",
        "settings": "Настройки",
        "settings_title": "Настройки Workspace GUI",
        "task_already_exists": "Задача уже существует",
        "task": "Задача",
        "task_details": "Детали задачи",
        "task_name": "Имя задачи",
        "tasks": "задач",
        "text_font_size": "Размер шрифта текста",
        "theme": "Тема",
        "window_title": "Workspace GUI",
    },
    "uk": {
        "actions": "Дії",
        "add_task": "Додати задачу",
        "artifacts": "Артефакти",
        "button_font_size": "Розмір шрифту кнопок",
        "cancel": "Скасувати",
        "close": "Закрити",
        "confirm_close_console_body": "Консольну сесію буде закрито.",
        "confirm_close_console_title": "Закрити консоль?",
        "confirm_delete_task_body": "Папку задачі буде видалено безповоротно.",
        "confirm_delete_task_title": "Видалити вибрану задачу?",
        "confirm_delete_artifacts_body": "Файли буде видалено безповоротно.",
        "confirm_delete_artifacts_title": "Видалити артефакти?",
        "context": "контекст",
        "delete_all_artifacts": "Видалити всі артефакти задачі",
        "delete_artifact": "Видалити артефакт",
        "delete_artifact_group": "Видалити групу артефактів",
        "delete_artifacts": "Видалити артефакти",
        "delete_task": "Видалити задачу",
        "desc": "опис",
        "details": "Деталі",
        "diagrams": "Діаграми",
        "diff_reports": "Diff-звіти",
        "edit": "Редагувати",
        "git_status": "Git status",
        "language": "Мова",
        "logs": "Логи",
        "missing_context": "немає контексту",
        "missing_desc": "немає опису",
        "new": "Нова",
        "no_git_repos": "У dev/ не знайдено git-репозиторії.",
        "ok": "OK",
        "open_dev": "Відкрити dev",
        "open_task": "Відкрити папку задачі",
        "open_workspace": "Відкрити workspace",
        "refresh": "Оновити",
        "reload_actions": "Оновити actions",
        "run_codex": "Запустити Codex",
        "run_task_check": "Run task_check",
        "save": "Зберегти",
        "scan_repos": "Сканувати репо",
        "scanning_repos": "Сканування репозиторіїв...",
        "select_task_first": "Спочатку вибери задачу",
        "settings": "Налаштування",
        "settings_title": "Налаштування Workspace GUI",
        "task_already_exists": "Задача вже існує",
        "task": "Задача",
        "task_details": "Деталі задачі",
        "task_name": "Назва задачі",
        "tasks": "задач",
        "text_font_size": "Розмір шрифту тексту",
        "theme": "Тема",
        "window_title": "Workspace GUI",
    },
}

CODEX_LANGUAGE_INSTRUCTIONS = {
    "en": "Reply to the user in English.",
    "ru": "Отвечай пользователю на русском языке.",
    "uk": "Відповідай користувачу українською мовою.",
}

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

_ARTIFACT_MONITOR_EVENTS = _TASK_ACTIONS_MONITOR_EVENTS

_LOG_SUFFIXES = {".log"}
_DIAGRAM_SUFFIXES = {".svg", ".png"}
_DIFF_REPORT_SUFFIXES = {".html"}


@dataclass
class TerminalSession:
    session_id: int
    task_path: Path
    kind: str
    terminal: Vte.Terminal
    page: Gtk.Widget
    child_pid: int | None = None


@dataclass(frozen=True)
class ArtifactEntry:
    group: str
    path: Path


class WorkspaceGtkGui:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.task_actions: list[TaskAction] = []
        self.task_action_errors: list[str] = []
        self.repo_status_message = ""
        self.git_repo_options: list[Path] = []
        self.git_repos_loaded_for: Path | None = None
        self.git_repo_cache: dict[Path, list[Path]] = {}
        self.repo_scan_generation = 0
        self.repo_scan_generations: dict[Path, int] = {}
        self.repo_scans_in_progress: set[Path] = set()
        self.pending_git_status_for: Path | None = None
        self.task_actions_signature: tuple[Path | None, int | None] = (None, None)
        self.task_actions_monitor: Gio.FileMonitor | None = None
        self.task_actions_monitor_path: Path | None = None
        self.artifact_monitors: list[Gio.FileMonitor] = []
        self.artifact_monitor_path: Path | None = None
        self.terminal_sessions: dict[int, TerminalSession] = {}
        self.next_terminal_id = 1

        settings = load_workspace_gui_settings()
        self.text_font_size = int(settings.get("text_font_size", 13))
        self.button_font_size = int(settings.get("button_font_size", 13))
        self.theme = str(settings.get("theme", "light"))
        self.language = str(settings.get("language", "ru"))
        self.window_geometry = str(settings.get("geometry", "1180x760"))
        self.last_window_width = 1180
        self.last_window_height = 760
        self.last_window_x = 0
        self.last_window_y = 0
        self.label_widgets: dict[str, Gtk.Widget] = {}
        self.detail_editing: dict[Gtk.TextView, bool] = {}
        self.detail_original_text: dict[Gtk.TextView, str] = {}
        self.detail_filenames: dict[Gtk.TextView, str] = {}

        GLib.set_application_name("Workspace GUI")
        GLib.set_prgname("workspace-gui")
        Gdk.set_program_class("workspace-gui")
        self.window = Gtk.Window(title=f"{self._tr('window_title')} - {self.workspace}")
        self.window.set_wmclass("workspace-gui", "Workspace GUI")
        icon_path = _workspace_gui_runtime_icon_path()
        if icon_path.is_file():
            Gtk.Window.set_default_icon_from_file(str(icon_path))
            self.window.set_icon_from_file(str(icon_path))
        self.window.set_icon_name("workspace-gui")
        self.header_bar = Gtk.HeaderBar(title=f"{self._tr('window_title')} - {self.workspace}")
        self.header_bar.set_show_close_button(True)
        self.window.set_titlebar(self.header_bar)
        self.window.connect("configure-event", self._on_window_configure)
        self.window.connect("destroy", self.close)
        self._apply_window_geometry()
        self._build_ui()
        self._apply_css()
        self.refresh_tasks()

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

        self.task_store = Gtk.ListStore(str, object, str, bool, str, bool, int, bool)
        self.task_view = Gtk.TreeView(model=self.task_store)
        task_renderer = Gtk.CellRendererText()
        self.task_column = Gtk.TreeViewColumn(
            self._tr("task"),
            task_renderer,
            text=0,
            cell_background=2,
            cell_background_set=3,
            foreground=4,
            foreground_set=5,
            weight=6,
            weight_set=7,
        )
        self.task_view.append_column(self.task_column)
        self.task_view.get_selection().connect("changed", self._on_task_selected)
        self.task_view.connect("row-activated", lambda *_: self.open_task())
        self.task_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.task_view.connect("button-press-event", self._on_task_view_button_press)
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_min_content_width(360)
        task_scroll.add(self.task_view)
        main.pack1(task_scroll, resize=False, shrink=False)

        self.notebook = Gtk.Notebook()
        main.pack2(self.notebook, resize=True, shrink=False)
        self._add_details_tab()
        self._add_actions_tab()
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
        self.artifact_store = Gtk.TreeStore(str, str, object, bool)
        self.artifact_view = Gtk.TreeView(model=self.artifact_store)
        name_column = Gtk.TreeViewColumn(self._tr("artifacts"), Gtk.CellRendererText(), text=0)
        name_column.set_expand(True)
        path_column = Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=1)
        path_column.set_expand(False)
        self.artifact_view.append_column(name_column)
        self.artifact_view.append_column(path_column)
        self.artifact_view.connect("row-activated", self._on_artifact_row_activated)
        self.artifact_view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.artifact_view.connect("button-press-event", self._on_artifact_view_button_press)
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.artifact_view)
        self.artifacts_tab_label = Gtk.Label(label=self._tr("artifacts"))
        self.notebook.append_page(scrolled, self.artifacts_tab_label)

    def _add_actions_tab(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.actions_page = box
        self.actions_tab_label = Gtk.Label(label=self._tr("actions"))
        self.notebook.append_page(box, self.actions_tab_label)

        repo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(repo_row, False, False, 0)
        self.git_repo_combo = Gtk.ComboBoxText()
        self.git_repo_combo.set_hexpand(True)
        repo_row.pack_start(self.git_repo_combo, True, True, 0)
        repo_row.pack_start(self._button("scan_repos", self.scan_selected_git_repos), False, False, 0)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(action_row, False, False, 0)
        action_row.pack_start(self._button("run_task_check", self.run_selected_task_check), False, False, 0)
        action_row.pack_start(self._button("git_status", self.run_selected_git_status), False, False, 0)
        self.task_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        action_row.pack_start(self.task_actions_box, False, False, 0)
        self.actions_message = Gtk.Label(label="")
        self.actions_message.set_xalign(0)
        box.pack_start(self.actions_message, False, False, 0)

        codex_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(codex_row, False, False, 0)
        self.run_codex_button = self._button("run_codex", self.run_codex_console)
        self.run_codex_button.set_hexpand(True)
        codex_row.pack_start(self.run_codex_button, True, True, 0)

        self.console_notebook = Gtk.Notebook()
        self.console_notebook.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.console_notebook.connect("button-press-event", self._on_console_notebook_button_press)
        box.pack_start(self.console_notebook, True, True, 0)

    def refresh_tasks(self, *_args: object) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
        self.task_store.clear()
        selected_iter = None
        for task in self.tasks:
            row_iter = self.task_store.append([task.name, task, *_task_row_style(False, self.theme)])
            if task.name == selected_name:
                selected_iter = row_iter
        self._refresh_task_row_styles()
        self.summary_label.set_text(f"{len(self.tasks)} {self._tr('tasks')}")
        if selected_iter is not None:
            self.task_view.get_selection().select_iter(selected_iter)
        elif self.tasks:
            self.task_view.get_selection().select_path(Gtk.TreePath.new_first())

    def _on_task_selected(self, selection: Gtk.TreeSelection) -> None:
        model, row_iter = selection.get_selected()
        if row_iter is None:
            return
        self.selected_task = model[row_iter][1]
        self._leave_detail_edit_mode(self.description_view)
        self._leave_detail_edit_mode(self.context_view)
        self._set_markdown(self.description_view, read_task_file(self.selected_task, "TASK_DESCRIPTION.md"))
        self._set_markdown(self.context_view, read_task_file(self.selected_task, "TASK_CONTEXT.md"))
        self._reset_actions()
        cached_repos = self.git_repo_cache.get(self.selected_task.path)
        if cached_repos is not None:
            self._set_git_repos(self.selected_task, cached_repos)
        self._watch_task_actions(self.selected_task)
        self._watch_task_artifacts(self.selected_task)
        self._load_task_artifacts(self.selected_task)
        self._load_task_action_buttons()
        self._refresh_console_tabs_for_task(self.selected_task)
        if self._actions_tab_active():
            self._ensure_default_console_for_selected_task()
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

    def _load_task_artifacts(self, task: TaskSummary) -> None:
        self.artifact_store.clear()
        groups = {
            "logs": self.artifact_store.append(None, [self._tr("logs"), "", "logs", True]),
            "diagrams": self.artifact_store.append(None, [self._tr("diagrams"), "", "diagrams", True]),
            "diff_reports": self.artifact_store.append(None, [self._tr("diff_reports"), "", "diff_reports", True]),
        }
        for entry in _task_artifact_entries(task):
            rel_path = _artifact_relative_label(task, entry.path)
            self.artifact_store.append(
                groups[entry.group],
                [entry.path.name, rel_path, entry.path, False],
            )
        self.artifact_view.expand_all()

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

    def _watch_task_artifacts(self, task: TaskSummary, *, force: bool = False) -> None:
        if not force and self.artifact_monitor_path == task.path:
            return
        self._clear_artifact_monitors()
        self.artifact_monitor_path = task.path
        for path in _artifact_monitor_dirs(task):
            try:
                monitor = Gio.File.new_for_path(str(path)).monitor_directory(
                    Gio.FileMonitorFlags.NONE,
                    None,
                )
            except GLib.Error:
                continue
            monitor.connect("changed", self._on_task_artifact_dir_changed)
            self.artifact_monitors.append(monitor)

    def _clear_artifact_monitors(self) -> None:
        for monitor in self.artifact_monitors:
            monitor.cancel()
        self.artifact_monitors = []

    def _on_task_artifact_dir_changed(
        self,
        _monitor: Gio.FileMonitor,
        _file: Gio.File,
        _other_file: Gio.File | None,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        if event_type not in _ARTIFACT_MONITOR_EVENTS:
            return
        task = self.selected_task
        if task is not None:
            self._watch_task_artifacts(task, force=True)
            self._load_task_artifacts(task)

    def _on_task_view_button_press(self, tree: Gtk.TreeView, event: Gdk.EventButton) -> bool:
        if event.button != 3:
            return False
        hit = tree.get_path_at_pos(int(event.x), int(event.y))
        if hit is not None:
            path, _column, _cell_x, _cell_y = hit
            tree.get_selection().select_path(path)
        self._task_context_menu().popup_at_pointer(event)
        return True

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
        menu.show_all()
        return menu

    def open_task(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path)

    def open_task_dev(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path / "dev")

    def add_task(self, *_args: object) -> None:
        task_name = self._prompt_task_name()
        if task_name is None:
            return
        task_path = _task_path_for_name(self.workspace, task_name)
        if task_path is None:
            self._show_error(f"Invalid task name: {task_name}")
            return
        if task_path.exists():
            self._show_error(f"{self._tr('task_already_exists')}: {task_path}")
            return
        result = subprocess.run(
            _task_init_command(self.workspace, task_path),
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

    def _prompt_task_name(self) -> str | None:
        dialog = Gtk.Dialog(
            title=self._tr("add_task"),
            transient_for=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(self._tr("cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._tr("ok"), Gtk.ResponseType.OK)
        content = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(12)
        content.add(box)
        label = Gtk.Label(label=self._tr("task_name"))
        label.set_xalign(0)
        entry = Gtk.Entry()
        box.pack_start(label, False, False, 0)
        box.pack_start(entry, False, False, 0)
        dialog.show_all()
        response = dialog.run()
        task_name = entry.get_text().strip()
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not task_name:
            return None
        return task_name

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
            buttons=Gtk.ButtonsType.OK,
            text=message,
        )
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
        for theme in WORKSPACE_GUI_THEMES:
            theme_combo.append_text(theme)
        theme_combo.set_active(WORKSPACE_GUI_THEMES.index(self.theme) if self.theme in WORKSPACE_GUI_THEMES else 0)
        for language in WORKSPACE_GUI_LANGUAGES:
            language_combo.append_text(language)
        language_combo.set_active(
            WORKSPACE_GUI_LANGUAGES.index(self.language)
            if self.language in WORKSPACE_GUI_LANGUAGES
            else 0
        )

        for row, (label, widget) in enumerate(
            (
                (self._tr("text_font_size"), text_size),
                (self._tr("button_font_size"), button_size),
                (self._tr("theme"), theme_combo),
                (self._tr("language"), language_combo),
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
            self._apply_runtime_style()
            self._apply_labels()
            self.refresh_tasks()
            self._save_settings()
        dialog.destroy()

    def run_selected_task_check(self, *_args: object) -> None:
        task = self._require_task()
        if task is not None:
            self._send_command_to_task_terminal(task, task_check_shell_command(self.workspace, task))

    def run_selected_git_status(self, *_args: object) -> None:
        task = self._require_task()
        if task is None:
            return
        repo = self._selected_git_repo()
        if repo is None:
            self.pending_git_status_for = task.path
            self._refresh_git_repos_async(task)
            return
        if repo is not None:
            self._send_command_to_task_terminal(task, shlex.join(["git", "-C", str(repo), "status", "--short", "--branch"]))

    def scan_selected_git_repos(self, *_args: object) -> None:
        task = self._require_task()
        if task is not None:
            self._refresh_git_repos_async(task)

    def reload_selected_task_actions(self, *_args: object) -> None:
        self._load_task_action_buttons()

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is not None:
            self._send_command_to_task_terminal(task, task_action_shell_command(action))

    def _reset_actions(self) -> None:
        self.task_actions = []
        self.git_repo_options = []
        self.git_repos_loaded_for = None
        self.repo_status_message = ""
        self.git_repo_combo.remove_all()
        self._clear_task_action_buttons()
        self._update_actions_message()

    def _clear_task_action_buttons(self) -> None:
        for child in self.task_actions_box.get_children():
            self.task_actions_box.remove(child)

    def _load_task_action_buttons(self) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            self.task_actions_signature = (None, None)
            return
        actions, errors = load_task_actions(task)
        self._clear_task_action_buttons()
        self.task_actions = actions
        self.task_actions_signature = _task_actions_signature(task)
        self.task_action_errors = errors
        self._update_actions_message()
        for action in actions:
            self.task_actions_box.pack_start(
                _button(action.label, lambda _button, item=action: self.run_custom_task_action(item)),
                False,
                False,
                0,
            )
        self.task_actions_box.show_all()

    def _ensure_git_repos_loaded(self, task: TaskSummary) -> None:
        if self.git_repos_loaded_for != task.path:
            cached = self.git_repo_cache.get(task.path)
            if cached is not None:
                self._set_git_repos(task, cached)
                return
            self._refresh_git_repos(task)

    def _refresh_git_repos_async(self, task: TaskSummary) -> None:
        self.repo_scan_generation += 1
        generation = self.repo_scan_generation
        task_path = task.path
        self.repo_scan_generations[task_path] = generation
        self.repo_scans_in_progress.add(task_path)
        self.git_repo_cache[task_path] = []
        if self.selected_task is not None and self.selected_task.path == task_path:
            self.git_repo_options = []
            self.git_repos_loaded_for = task_path
            self.repo_status_message = ""
            self.git_repo_combo.remove_all()
        self._update_actions_message()

        def worker() -> None:
            for repo in _iter_git_repos(task):
                GLib.idle_add(self._append_git_repo_scan_result, task_path, generation, repo)
            GLib.idle_add(self._finish_git_repo_scan_result, task_path, generation)

        threading.Thread(target=worker, daemon=True).start()

    def _append_git_repo_scan_result(
        self,
        task_path: Path,
        generation: int,
        repo: Path,
    ) -> bool:
        if self.repo_scan_generations.get(task_path) != generation:
            return False
        cached = self.git_repo_cache.setdefault(task_path, [])
        if repo not in cached:
            cached.append(repo)
        if self.selected_task is None or self.selected_task.path != task_path:
            return False
        if repo not in self.git_repo_options:
            self.git_repo_options.append(repo)
            self.git_repo_combo.append_text(_repo_label(self.selected_task, repo))
            if len(self.git_repo_options) == 1:
                self.git_repo_combo.set_active(0)
        self.repo_status_message = ""
        self._update_actions_message()
        return False

    def _finish_git_repo_scan_result(self, task_path: Path, generation: int) -> bool:
        if self.repo_scan_generations.get(task_path) != generation:
            return False
        self.repo_scans_in_progress.discard(task_path)
        repos = self.git_repo_cache.get(task_path, [])
        if self.selected_task is not None and self.selected_task.path == task_path:
            if not repos:
                self.repo_status_message = self._tr("no_git_repos")
            self._update_actions_message()
        if self.pending_git_status_for == task_path:
            self.pending_git_status_for = None
            repo = self._selected_git_repo()
            if repo is not None:
                self.run_selected_git_status()
        return False

    def _refresh_git_repos(self, task: TaskSummary) -> None:
        self._set_git_repos(task, find_dev_git_repos(task))

    def _set_git_repos(self, task: TaskSummary, repos: list[Path]) -> None:
        self.git_repo_options = repos
        self.git_repos_loaded_for = task.path
        self.git_repo_combo.remove_all()
        for repo in self.git_repo_options:
            self.git_repo_combo.append_text(_repo_label(task, repo))
        if self.git_repo_options:
            self.git_repo_combo.set_active(0)
            self.repo_status_message = ""
        else:
            self.repo_status_message = self._tr("no_git_repos")
        self._update_actions_message()

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
        task = self.selected_task
        messages: list[str] = []
        if task is not None and task.path in self.repo_scans_in_progress:
            messages.append(self._tr("scanning_repos"))
        if self.repo_status_message:
            messages.append(self.repo_status_message)
        messages.extend(getattr(self, "task_action_errors", []))
        self.actions_message.set_text("\n".join(messages))

    def _selected_git_repo(self) -> Path | None:
        index = self.git_repo_combo.get_active()
        if index < 0 or index >= len(self.git_repo_options):
            return None
        return self.git_repo_options[index]

    def new_console(self, *_args: object, task: TaskSummary | None = None) -> int | None:
        task = task or self._require_task()
        if task is None:
            return None
        shell = os.environ.get("SHELL") or "/bin/bash"
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env["PS1"] = f"{task.name}$ "
        env["PROMPT_COMMAND"] = ""
        return self._start_terminal(
            task=task,
            command=[shell],
            cwd=task.path,
            env=env,
            kind="shell",
        )

    def run_codex_console(self, *_args: object) -> None:
        task = self._require_task()
        if task is None:
            return
        for session in self._current_task_terminal_sessions(task):
            if session.kind == "codex":
                self._activate_terminal(session.session_id)
                self._update_codex_button_state()
                return
        self._start_terminal(
            task=task,
            command=codex_console_command(self.workspace, task, self.language),
            cwd=self.workspace,
            env=os.environ.copy(),
            kind="codex",
        )
        self._update_codex_button_state()

    def close_active_console(self, *_args: object) -> None:
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return
        page = self.console_notebook.get_nth_page(page_num)
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
        )
        self.terminal_sessions[session_id] = session
        self._renumber_terminal_tabs(task)
        if self.selected_task is not None and self.selected_task.path == task.path:
            self._show_terminal_tab(session)
        self._activate_terminal(session_id)
        return session_id

    def _refresh_console_tabs_for_task(self, task: TaskSummary) -> None:
        while self.console_notebook.get_n_pages() > 0:
            self.console_notebook.remove_page(0)
        self._renumber_terminal_tabs(task)
        for session in self._current_task_terminal_sessions(task):
            self._show_terminal_tab(session)
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
            if isinstance(tab, Gtk.Label):
                tab.set_text(_terminal_tab_label(session.kind, shell_index))

    def _show_terminal_tab(self, session: TerminalSession) -> None:
        if self.console_notebook.page_num(session.page) < 0:
            if session.kind == "codex":
                self.console_notebook.insert_page(session.page, Gtk.Label(label=session.kind), 0)
            else:
                self.console_notebook.append_page(session.page, Gtk.Label(label=session.kind))
        session.page.show_all()
        self._renumber_terminal_tabs(self._task_for_path(session.task_path))

    def _activate_terminal(self, session_id: int) -> None:
        session = self.terminal_sessions.get(session_id)
        if session is None:
            return
        self._show_terminal_tab(session)
        page_num = self.console_notebook.page_num(session.page)
        if page_num >= 0:
            self.console_notebook.set_current_page(page_num)
        session.terminal.grab_focus()

    def _on_console_notebook_button_press(self, notebook: Gtk.Notebook, event: Gdk.EventButton) -> bool:
        if event.type != Gdk.EventType.DOUBLE_BUTTON_PRESS or event.button != 1:
            return False
        if self.selected_task is None or not _is_empty_notebook_tab_area(notebook, event):
            return False
        self.new_console(task=self.selected_task)
        return True

    def _close_console_session(self, session: TerminalSession) -> bool:
        if not self._confirm_close_console():
            return False
        task = self._task_for_path(session.task_path)
        page_num = self.console_notebook.page_num(session.page)
        if page_num >= 0:
            self.console_notebook.remove_page(page_num)
        self.terminal_sessions.pop(session.session_id, None)
        session.page.destroy()
        if self.selected_task is not None and self.selected_task.path == task.path:
            self._ensure_default_console_for_selected_task()
        self._update_codex_button_state()
        return True

    def _update_codex_button_state(self) -> None:
        task = self.selected_task
        running = task is not None and any(
            session.kind == "codex"
            for session in self._current_task_terminal_sessions(task)
        )
        context = self.run_codex_button.get_style_context()
        if running:
            context.add_class("codex-running")
        else:
            context.remove_class("codex-running")
        self._refresh_task_row_styles()

    def _refresh_task_row_styles(self) -> None:
        row_iter = self.task_store.get_iter_first()
        while row_iter is not None:
            task = self.task_store[row_iter][1]
            has_codex = any(
                session.kind == "codex" and session.task_path == task.path
                for session in self.terminal_sessions.values()
            )
            background, background_set, foreground, foreground_set, weight, weight_set = _task_row_style(
                has_codex,
                self.theme,
            )
            self.task_store[row_iter][2] = background
            self.task_store[row_iter][3] = background_set
            self.task_store[row_iter][4] = foreground
            self.task_store[row_iter][5] = foreground_set
            self.task_store[row_iter][6] = weight
            self.task_store[row_iter][7] = weight_set
            row_iter = self.task_store.iter_next(row_iter)

    def _actions_tab_active(self) -> bool:
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return False
        return self.notebook.get_nth_page(page_num) is self.actions_page

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
        for task in self.tasks:
            if task.path == task_path:
                return task
        return TaskSummary(task_path.name, task_path, False, False, 0, 0, False)

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
        shortcut = _terminal_clipboard_shortcut(event.keyval, int(event.state))
        if shortcut == "copy":
            terminal.copy_clipboard()
            return True
        if shortcut == "paste":
            terminal.paste_clipboard()
            return True
        return False

    def _terminal_context_menu(self, terminal: Vte.Terminal) -> Gtk.Menu:
        menu = Gtk.Menu()
        copy_item = Gtk.MenuItem(label="Copy")
        paste_item = Gtk.MenuItem(label="Paste")
        select_all_item = Gtk.MenuItem(label="Select all")
        close_item = Gtk.MenuItem(label=self._tr("close"))
        copy_item.set_sensitive(bool(terminal.get_has_selection()))
        copy_item.connect("activate", lambda *_: terminal.copy_clipboard())
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

    def _require_task(self, show_dialog: bool = True) -> TaskSummary | None:
        if self.selected_task is not None:
            return self.selected_task
        if show_dialog:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=self._tr("select_task_first"),
            )
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
        self.task_column.set_title(self._tr("task"))
        self.details_tab_label.set_text(self._tr("details"))
        self.artifacts_tab_label.set_text(self._tr("artifacts"))
        self.actions_tab_label.set_text(self._tr("actions"))
        if self.selected_task is not None:
            self._load_task_artifacts(self.selected_task)

    def _tr(self, key: str) -> str:
        return TRANSLATIONS.get(self.language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

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

    def close(self, *_args: object) -> None:
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
        self._clear_artifact_monitors()
        self._save_settings()
        Gtk.main_quit()

    def _save_settings(self) -> None:
        save_workspace_gui_settings(
            {
                "text_font_size": self.text_font_size,
                "button_font_size": self.button_font_size,
                "theme": self.theme,
                "language": self.language,
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


def _is_pane_separator_event(pane: Gtk.Paned, event: Gdk.EventButton, tolerance: int = 8) -> bool:
    position = pane.get_position()
    if pane.get_orientation() == Gtk.Orientation.HORIZONTAL:
        return abs(event.x - position) <= tolerance
    return abs(event.y - position) <= tolerance


def _is_empty_notebook_tab_area(notebook: Gtk.Notebook, event: Gdk.EventButton) -> bool:
    tab_bottom = 0
    tab_right = 0
    for index in range(notebook.get_n_pages()):
        page = notebook.get_nth_page(index)
        tab = notebook.get_tab_label(page)
        if tab is None:
            continue
        allocation = tab.get_allocation()
        tab_bottom = max(tab_bottom, allocation.y + allocation.height)
        tab_right = max(tab_right, allocation.x + allocation.width)
    if tab_bottom == 0:
        return event.y <= 36
    return event.y <= tab_bottom + 8 and event.x > tab_right + 8


def _terminal_session_sort_key(kind: str, session_id: int) -> tuple[int, int]:
    return (0 if kind == "codex" else 1, session_id)


def _terminal_tab_label(kind: str, shell_index: int) -> str:
    if kind == "codex":
        return "codex"
    return f"{kind} {shell_index}"


def _terminal_clipboard_shortcut(keyval: int, state: int) -> str | None:
    modifiers = int(Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
    if (state & modifiers) != modifiers:
        return None
    if keyval in {Gdk.KEY_c, Gdk.KEY_C}:
        return "copy"
    if keyval in {Gdk.KEY_v, Gdk.KEY_V}:
        return "paste"
    return None


def _task_row_style(has_codex: bool, theme: str) -> tuple[str, bool, str, bool, int, bool]:
    if not has_codex:
        return ("", False, "", False, int(Pango.Weight.NORMAL), False)
    colors = _theme_colors(theme)
    return (
        colors["codex_running_background"],
        True,
        colors["codex_running_foreground"],
        True,
        int(Pango.Weight.BOLD),
        True,
    )


def _task_actions_signature(task: TaskSummary) -> tuple[Path, int | None]:
    path = task.path / TASK_ACTIONS_FILE
    try:
        return (path, path.stat().st_mtime_ns)
    except FileNotFoundError:
        return (path, None)


def _task_path_for_name(workspace: Path, task_name: str) -> Path | None:
    if not task_name or task_name in {".", ".."}:
        return None
    if "/" in task_name or "\\" in task_name:
        return None
    task_path = (workspace / "tasks" / task_name).resolve()
    tasks_root = (workspace / "tasks").resolve()
    try:
        task_path.relative_to(tasks_root)
    except ValueError:
        return None
    return task_path


def _task_init_command(workspace: Path, task_path: Path) -> list[str]:
    return [
        sys_executable(),
        "-m",
        "codex_tools.paf_workspace.task_check",
        str(task_path),
        "--workspace",
        str(workspace),
        "--init-layout",
    ]


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


def _repo_label(task: TaskSummary, repo: Path) -> str:
    try:
        return str(repo.relative_to(task.path))
    except ValueError:
        return str(repo)


def _task_artifact_entries(task: TaskSummary) -> list[ArtifactEntry]:
    entries: list[ArtifactEntry] = []
    for path in _task_artifact_files(task):
        group = _artifact_group(task, path)
        if group is not None:
            entries.append(ArtifactEntry(group, path))
    return sorted(
        entries,
        key=lambda entry: (_artifact_group_sort_key(entry.group), _artifact_relative_label(task, entry.path).casefold()),
    )


def _task_artifact_files(task: TaskSummary) -> Iterator[Path]:
    report = task.path / "report"
    if not report.is_dir():
        return
    for root, dirs, files in os.walk(report):
        dirs.sort()
        for filename in sorted(files, key=str.casefold):
            yield Path(root) / filename


def _artifact_group(task: TaskSummary, path: Path) -> str | None:
    suffix = path.suffix.casefold()
    try:
        rel = path.relative_to(task.path)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "report" and parts[1] == "diff" and suffix in _DIFF_REPORT_SUFFIXES:
        return "diff_reports"
    if len(parts) >= 2 and parts[0] == "report" and parts[1] == "puml" and suffix in _DIAGRAM_SUFFIXES:
        return "diagrams"
    if suffix in _LOG_SUFFIXES:
        return "logs"
    return None


def _artifact_group_sort_key(group: str) -> int:
    order = {"logs": 0, "diagrams": 1, "diff_reports": 2}
    return order.get(group, 99)


def _artifact_relative_label(task: TaskSummary, path: Path) -> str:
    try:
        return str(path.relative_to(task.path))
    except ValueError:
        return str(path)


def _artifact_monitor_dirs(task: TaskSummary) -> list[Path]:
    roots = (task.path / "report", task.path / "report" / "diff", task.path / "report" / "puml")
    dirs: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for current, child_dirs, _files in os.walk(root):
            child_dirs.sort()
            dirs.add(Path(current))
    return sorted(dirs, key=lambda path: str(path).casefold())


def _artifact_delete_paths(
    task: TaskSummary,
    *,
    artifact_path: Path | None = None,
    group: str | None = None,
    delete_all: bool = False,
) -> list[Path]:
    if artifact_path is not None:
        try:
            artifact_path.relative_to(task.path)
        except ValueError:
            return []
        return [artifact_path] if artifact_path.is_file() else []
    if delete_all:
        return _files_under(task.path / "report")
    if group == "logs":
        return [
            path
            for path in _files_under(task.path / "report")
            if path.suffix.casefold() in _LOG_SUFFIXES
        ]
    if group == "diagrams":
        return _files_under(task.path / "report" / "puml")
    if group == "diff_reports":
        return _files_under(task.path / "report" / "diff")
    return []


def _artifact_context_action(artifact_path: Path | None, group: str | None) -> str:
    if artifact_path is not None:
        return "artifact"
    if group is not None:
        return "group"
    return "all"


def _files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for filename in sorted(files, key=str.casefold):
            path = Path(current) / filename
            if path.is_file():
                paths.append(path)
    return paths


def _iter_git_repos(task: TaskSummary) -> Iterator[Path]:
    dev = task.path / "dev"
    if not dev.is_dir():
        return
    for root, dirs, _files in os.walk(dev):
        dirs.sort()
        root_path = Path(root)
        if ".git" in dirs:
            yield root_path
            dirs[:] = []
            continue
        dirs[:] = [name for name in dirs if name != ".git"]


def codex_task_context_message(task: TaskSummary, workspace: Path, language: str = "en") -> str:
    return (
        f"We are working in workspace task `{task.name}`. "
        f"Workspace: {workspace}. "
        f"Task directory: {task.path}. "
        "Before changing files, read that task's TASK_DESCRIPTION.md and "
        "TASK_CONTEXT.md and treat them as the active task context. "
        f"{CODEX_LANGUAGE_INSTRUCTIONS.get(language, CODEX_LANGUAGE_INSTRUCTIONS['en'])}"
    )


def codex_console_command(workspace: Path, task: TaskSummary, language: str = "en") -> list[str]:
    return [
        _codex_executable(),
        "--cd",
        str(workspace),
        "--no-alt-screen",
        codex_task_context_message(task, workspace, language),
    ]


def task_check_shell_command(workspace: Path, task: TaskSummary) -> str:
    return " ".join(
        [
            "cd",
            shlex.quote(str(workspace)),
            "&&",
            shlex.join(
                [
                    sys_executable(),
                    "-m",
                    "codex_tools.paf_workspace.task_check",
                    str(task.path),
                    "--workspace",
                    str(workspace),
                ]
            ),
        ]
    )


def task_action_shell_command(action: TaskAction) -> str:
    command = action.command if isinstance(action.command, str) else shlex.join(action.command)
    env = " ".join(
        f"{key}={shlex.quote(value)}"
        for key, value in sorted(action.env.items())
    )
    prefix = f"{env} " if env else ""
    return f"cd {shlex.quote(str(action.cwd))} && {prefix}{command}"


def sys_executable() -> str:
    return sys.executable or "python3"


def _codex_executable() -> str:
    executable = shutil.which("codex")
    if executable:
        return executable
    local_bin = Path.home() / ".local" / "bin" / "codex"
    if local_bin.is_file():
        return str(local_bin)
    return "codex"


def _feed_terminal(terminal: Vte.Terminal, text: str) -> None:
    data = text.encode()
    attempts = (
        lambda: terminal.feed_child(text),
        lambda: terminal.feed_child(text, len(text)),
        lambda: terminal.feed_child(data),
        lambda: terminal.feed_child(data, len(data)),
    )
    for attempt in attempts:
        try:
            attempt()
            return
        except TypeError:
            continue
    feed_binary = getattr(terminal, "feed_child_binary", None)
    if feed_binary is not None:
        try:
            feed_binary(data)
            return
        except TypeError:
            feed_binary(data, len(data))
            return
    raise TypeError("VTE Terminal.feed_child signature is unsupported")


def _terminal_env(env: dict[str, str]) -> list[str]:
    env.setdefault("TERM", "xterm-256color")
    return [f"{key}={value}" for key, value in env.items()]


def _rgba(color: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    rgba.parse(color)
    return rgba


def _terminal_palette(theme: str) -> tuple[str, ...]:
    if theme == "dark":
        return (
            "#111315",
            "#e06c75",
            "#7ec699",
            "#d19a66",
            "#7aa2f7",
            "#c678dd",
            "#56b6c2",
            "#e8eaed",
            "#5c6370",
            "#ef8088",
            "#98d6ac",
            "#e5c07b",
            "#9ab6ff",
            "#d39aea",
            "#7fd4df",
            "#ffffff",
        )
    return (
        "#202124",
        "#b3261e",
        "#137333",
        "#b06000",
        "#1a5fb4",
        "#8e24aa",
        "#007b83",
        "#f2f2f2",
        "#5f6368",
        "#d93025",
        "#188038",
        "#ea8600",
        "#2f6fbb",
        "#a142f4",
        "#129eaf",
        "#ffffff",
    )


def _theme_colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "background": "#202124",
            "codex_running_background": "#26384d",
            "codex_running_border": "#7aa2f7",
            "codex_running_foreground": "#ffffff",
            "codex_running_glow": "rgba(122, 162, 247, 0.75)",
            "text_background": "#111315",
            "terminal_background": "#111315",
            "control_background": "#2b2f33",
            "control_hover_background": "#343a40",
            "titlebar_background": "#16191d",
            "tab_background": "#202124",
            "tab_selected_background": "#111315",
            "tab_selected_foreground": "#f5f7fa",
            "muted_foreground": "#a8b0ba",
            "selection_background": "#3f6f9f",
            "selection_foreground": "#ffffff",
            "menu_background": "#252a2f",
            "border": "#4a5058",
            "separator": "#6a727c",
            "foreground": "#e8eaed",
        }
    return {
        "background": "#f2f2f2",
        "codex_running_background": "#d9e7ff",
        "codex_running_border": "#2f6fbb",
        "codex_running_foreground": "#14345f",
        "codex_running_glow": "rgba(47, 111, 187, 0.45)",
        "text_background": "#ffffff",
        "terminal_background": "#ffffff",
        "control_background": "#f8f8f8",
        "control_hover_background": "#ffffff",
        "titlebar_background": "#ededed",
        "tab_background": "#e8e8e8",
        "tab_selected_background": "#ffffff",
        "tab_selected_foreground": "#202124",
        "muted_foreground": "#5f6368",
        "selection_background": "#2f6fbb",
        "selection_foreground": "#ffffff",
        "menu_background": "#ffffff",
        "border": "#b8b8b8",
        "separator": "#8c8c8c",
        "foreground": "#202124",
    }


def open_path(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif os.name == "nt":
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        command = ["xdg-open", str(path)]
    try:
        import subprocess

        subprocess.Popen(command)
    except OSError:
        return


def open_artifact_path(path: Path) -> None:
    if path.suffix.casefold() == ".svg":
        command = _svg_open_command(path)
        if command is not None:
            subprocess.Popen(command)
            return
    open_path(path)


def _svg_open_command(path: Path) -> list[str] | None:
    browser = os.environ.get("BROWSER")
    if browser:
        return [*shlex.split(browser), str(path)]
    for executable in ("firefox", "google-chrome", "chromium", "chromium-browser", "xdg-open"):
        resolved = shutil.which(executable)
        if resolved is not None:
            return [resolved, str(path)]
    return None


def _workspace_gui_icon_path() -> Path:
    return Path(__file__).with_name("assets") / "workspace-gui.svg"


def _workspace_gui_runtime_icon_path() -> Path:
    installed = Path.home() / ".local/share/icons/hicolor/256x256/apps/workspace-gui.png"
    if installed.is_file():
        return installed
    return _workspace_gui_icon_path()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the local workspace task dashboard.")
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root. Default: current directory.",
    )
    args = parser.parse_args(argv)

    gui = WorkspaceGtkGui(Path(args.workspace))
    gui.window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
