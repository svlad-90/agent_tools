from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
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

from .core import TASK_ACTIONS_FILE
from .core import TASK_ACTION_LOGS_DIR
from .core import AGENT_RUNNING_SPINNER_FRAMES
from .core import AGENT_STATUS_MANUAL_MENU_LABEL
from .core import AGENT_STATUS_MANUAL_TITLE
from .core import AgentModelSettings
from .core import TaskAction
from .core import TaskSummary
from .core import AGENT_WORKSPACE_AGENTS
from .core import AGENT_WORKSPACE_CLAUDE_MODELS
from .core import AGENT_WORKSPACE_LANGUAGES
from .core import AGENT_WORKSPACE_REASONING_EFFORTS
from .core import AGENT_WORKSPACE_THEMES
from .core import PAF_HIDE_TASK_ENV_VAR
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
from .core import clear_task_agent_session
from .core import clear_task_active_agent_run
from .core import codex_model_choices
from .core import discover_tasks
from .core import load_task_agent
from .core import load_task_actions
from .core import load_agent_workspace_settings
from .core import model_choices_with_current
from .core import new_agent_session_id
from .core import normalize_agent
from .core import prepare_ai_agent_launch_command
from .core import read_task_file
from .core import render_markdown_chunks
from .core import reset_task_agent_session
from .core import save_agent_workspace_settings
from .core import save_task_active_agent_run
from .core import save_task_agent
from .core import save_task_agent_session
from .core import session_marks_task_pending_permission
from .core import session_marks_task_running_agent
from .core import session_is_agent
from .core import session_is_running_agent
from .core import session_should_clear_pending_permission
from .core import task_action_log_basename
from .core import task_agent_has_resumable_state
from .core import task_agent_status_text
from .core import task_agent_session_markers
from .core import task_agent_selection_with_resumable_fallback
from .core import task_has_external_active_agent_run
from .core import task_for_path


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
        "confirm_close_running_agents_body": "There are running AI agent terminals.\n\n{sessions}\n\nClosing Agent Workspace will stop the local agent processes. Resumable conversations can be restored on the next launch. Continue?",
        "confirm_close_running_agents_title": "Close Agent Workspace?",
        "confirm_delete_saved_agent_session_body": "This task has a saved {old_agent} session. Switching to {new_agent} will remove the saved resume link for that session. Continue?",
        "confirm_delete_saved_agent_session_title": "Remove saved session?",
        "confirm_switch_agent_body": "{current} is already running for this task.\n\nConfirming will close the current session and start {next} with the same task context.",
        "confirm_switch_agent_title": "Switch AI agent?",
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
        "default_agent": "Default AI agent",
        "default_claude_effort": "Claude effort",
        "default_claude_model": "Claude model",
        "default_codex_model": "Codex model",
        "default_codex_reasoning": "Codex reasoning",
        "diff_reports": "Diff reports",
        "edit": "Edit",
        "install_agent_body": "{agent} is not installed or is not available in PATH.\n\nInstall it, then restart Agent Workspace or update PATH.\n\nSuggested install command:\n{command}",
        "install_agent_title": "AI agent is not installed",
        "language": "Language",
        "logs": "Logs",
        "open_containing_folder": "Open containing folder",
        "other_artifacts": "Other artifacts",
        "updated": "Updated",
        "restore_failed_status": "Could not restore the saved {agent} session for {task}. The saved resume link was removed and the AI-agent console was closed. Run the AI agent again to start a new session.",
        "manual_label_agent": "Agent",
        "manual_label_concept": "Concept",
        "manual_label_copy": "Copy",
        "manual_label_structure": "Structure",
        "manual_label_reset": "Reset",
        "manual_status_agent_running": "an AI agent is currently running for this task",
        "manual_status_external": "an AI agent for this task is running in another window",
        "manual_status_idle": "there is no saved session to continue",
        "manual_status_label_external": "Busy elsewhere",
        "manual_status_label_idle": "Stopped",
        "manual_status_label_running": "Agent running",
        "manual_status_label_session": "Paused",
        "manual_status_section": "AI column statuses",
        "manual_status_session": "the last active AI agent has a saved session that can continue",
        "manual_usage_actions": "put repeatable commands into TASK_ACTIONS.json; you can ask an agent to add the needed button",
        "manual_usage_agent": "choose Codex or Claude Code; the agent starts in the current task context and receives the task path",
        "manual_usage_concept": "the workspace is split into tasks; each task keeps context, artifacts, scripts, and work history",
        "manual_usage_copy": "in Claude Code terminals, hold Shift while selecting text, then copy with Ctrl+Shift+C",
        "manual_usage_reset": "clears only the saved session reference for the selected agent, without deleting CLI history",
        "manual_usage_section": "Basics",
        "manual_usage_structure": "TASK_DESCRIPTION.md, TASK_CONTEXT.md, dev/, scripts/, and report/ keep the work reproducible",
        "manual_usage_task": "create a task for each goal and select it on the left to open its description, context, and terminals",
        "missing_context": "missing context",
        "missing_desc": "missing desc",
        "new": "New",
        "ok": "OK",
        "open_dev": "Open dev folder",
        "open_task": "Open task folder",
        "open_workspace": "Open Workspace",
        "refresh": "Refresh",
        "reload_actions": "Reload actions",
        "reset_ai_agent_session": "Reset session",
        "run_ai_agent": "Run AI agent",
        "ai_agent_running": "AI agent running",
        "restore_ai_agent_session": "Restore AI agent session",
        "run_task_check": "Run task_check",
        "save": "Save",
        "select_task_first": "Select a task first",
        "settings": "Settings",
        "settings_title": "Agent Workspace settings",
        "task_already_exists": "Task already exists",
        "task": "Task",
        "task_agent_status_column": "AI",
        "task_details": "Task Details",
        "task_name": "Task name",
        "tasks": "tasks",
        "text_font_size": "Text font size",
        "theme": "Theme",
        "window_title": "Agent Workspace",
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
        "confirm_close_running_agents_body": "Есть запущенные терминалы ИИ агентов.\n\n{sessions}\n\nЗакрытие Agent Workspace остановит локальные процессы агентов. Восстанавливаемые диалоги можно будет открыть при следующем запуске. Продолжить?",
        "confirm_close_running_agents_title": "Закрыть Agent Workspace?",
        "confirm_delete_saved_agent_session_body": "Для этой задачи сохранена сессия {old_agent}. При переключении на {new_agent} ссылка на продолжение этой сессии будет удалена. Продолжить?",
        "confirm_delete_saved_agent_session_title": "Удалить сохраненную сессию?",
        "confirm_switch_agent_body": "{current} уже запущен для этой задачи.\n\nПодтверждение закроет текущую сессию и запустит {next} с контекстом той же задачи.",
        "confirm_switch_agent_title": "Сменить ИИ агента?",
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
        "default_agent": "ИИ агент по умолчанию",
        "default_claude_effort": "Claude effort",
        "default_claude_model": "Модель Claude",
        "default_codex_model": "Модель Codex",
        "default_codex_reasoning": "Codex reasoning",
        "diff_reports": "Diff-отчеты",
        "edit": "Редактировать",
        "install_agent_body": "{agent} не установлен или недоступен в PATH.\n\nУстанови его, затем перезапусти Agent Workspace или обнови PATH.\n\nПредлагаемая команда установки:\n{command}",
        "install_agent_title": "ИИ агент не установлен",
        "language": "Язык",
        "logs": "Логи",
        "open_containing_folder": "Открыть содержащую папку",
        "other_artifacts": "Другие артефакты",
        "updated": "Обновлено",
        "restore_failed_status": "Не удалось восстановить сохраненную сессию {agent} для задачи {task}. Ссылка на продолжение удалена, консоль ИИ агента закрыта. Запустите ИИ агента еще раз, чтобы начать новую сессию.",
        "manual_label_agent": "Агент",
        "manual_label_concept": "Концепция",
        "manual_label_copy": "Копирование",
        "manual_label_structure": "Структура",
        "manual_label_reset": "Сброс",
        "manual_status_agent_running": "для этой задачи сейчас работает Codex или Claude Code",
        "manual_status_external": "ИИ агент для этой задачи запущен в другом окне",
        "manual_status_idle": "нет сохраненной сессии, которую можно продолжить",
        "manual_status_label_external": "Занято",
        "manual_status_label_idle": "Стоп",
        "manual_status_label_running": "Агент запущен",
        "manual_status_label_session": "Пауза",
        "manual_status_section": "Статусы в колонке ИИ",
        "manual_status_session": "есть сохраненная сессия последнего активного ИИ агента",
        "manual_usage_actions": "повторяемые команды оформляйте в TASK_ACTIONS.json; можно попросить агента добавить нужную кнопку",
        "manual_usage_agent": "выберите Codex или Claude Code; агент запускается в контексте текущей задачи и получает путь к ней",
        "manual_usage_concept": "workspace разбит на задачи; каждая задача хранит контекст, артефакты, скрипты и историю работы",
        "manual_usage_copy": "в терминалах Claude Code выделяйте текст с зажатым Shift, затем копируйте через Ctrl+Shift+C",
        "manual_usage_reset": "сбрасывает только сохраненную ссылку на сессию выбранного агента, не удаляя историю CLI",
        "manual_usage_section": "Основы",
        "manual_usage_structure": "TASK_DESCRIPTION.md, TASK_CONTEXT.md, dev/, scripts/ и report/ держат работу воспроизводимой",
        "manual_usage_task": "создавайте задачу под отдельную цель и выбирайте ее слева, чтобы открыть описание, контекст и терминалы",
        "missing_context": "нет контекста",
        "missing_desc": "нет описания",
        "new": "Новая",
        "ok": "ОК",
        "open_dev": "Открыть dev",
        "open_task": "Открыть папку задачи",
        "open_workspace": "Открыть workspace",
        "refresh": "Обновить",
        "reload_actions": "Обновить actions",
        "reset_ai_agent_session": "Сбросить сессию",
        "run_ai_agent": "Запустить ИИ агента",
        "ai_agent_running": "ИИ агент запущен",
        "restore_ai_agent_session": "Восстановить сессию ИИ агента",
        "run_task_check": "Run task_check",
        "save": "Сохранить",
        "select_task_first": "Сначала выбери задачу",
        "settings": "Настройки",
        "settings_title": "Настройки Agent Workspace",
        "task_already_exists": "Задача уже существует",
        "task": "Задача",
        "task_agent_status_column": "ИИ",
        "task_details": "Детали задачи",
        "task_name": "Имя задачи",
        "tasks": "задач",
        "text_font_size": "Размер шрифта текста",
        "theme": "Тема",
        "window_title": "Agent Workspace",
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
        "confirm_close_running_agents_body": "Є запущені термінали ШІ агентів.\n\n{sessions}\n\nЗакриття Agent Workspace зупинить локальні процеси агентів. Відновлювані діалоги можна буде відкрити під час наступного запуску. Продовжити?",
        "confirm_close_running_agents_title": "Закрити Agent Workspace?",
        "confirm_delete_saved_agent_session_body": "Для цієї задачі збережена сесія {old_agent}. Перемикання на {new_agent} видалить посилання для продовження цієї сесії. Продовжити?",
        "confirm_delete_saved_agent_session_title": "Видалити збережену сесію?",
        "confirm_switch_agent_body": "{current} вже запущено для цієї задачі.\n\nПідтвердження закриє поточну сесію і запустить {next} з контекстом тієї самої задачі.",
        "confirm_switch_agent_title": "Змінити ШІ агента?",
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
        "default_agent": "Типовий ШІ агент",
        "default_claude_effort": "Claude effort",
        "default_claude_model": "Модель Claude",
        "default_codex_model": "Модель Codex",
        "default_codex_reasoning": "Codex reasoning",
        "diff_reports": "Diff-звіти",
        "edit": "Редагувати",
        "install_agent_body": "{agent} не встановлено або він недоступний у PATH.\n\nВстанови його, потім перезапусти Agent Workspace або онови PATH.\n\nЗапропонована команда встановлення:\n{command}",
        "install_agent_title": "ШІ агент не встановлено",
        "language": "Мова",
        "logs": "Логи",
        "open_containing_folder": "Відкрити теку з файлом",
        "other_artifacts": "Інші артефакти",
        "updated": "Оновлено",
        "restore_failed_status": "Не вдалося відновити збережену сесію {agent} для задачі {task}. Посилання для продовження видалено, консоль ШІ агента закрито. Запустіть ШІ агента ще раз, щоб почати нову сесію.",
        "manual_label_agent": "Агент",
        "manual_label_concept": "Концепція",
        "manual_label_copy": "Копіювання",
        "manual_label_structure": "Структура",
        "manual_label_reset": "Скидання",
        "manual_status_agent_running": "для цієї задачі зараз працює Codex або Claude Code",
        "manual_status_external": "ШІ агент для цієї задачі запущений в іншому вікні",
        "manual_status_idle": "немає збереженої сесії, яку можна продовжити",
        "manual_status_label_external": "Зайнято",
        "manual_status_label_idle": "Стоп",
        "manual_status_label_running": "Агент запущений",
        "manual_status_label_session": "Пауза",
        "manual_status_section": "Статуси в колонці ШІ",
        "manual_status_session": "є збережена сесія останнього активного ШІ агента",
        "manual_usage_actions": "повторювані команди оформлюй у TASK_ACTIONS.json; можна попросити агента додати потрібну кнопку",
        "manual_usage_agent": "вибери Codex або Claude Code; агент запускається в контексті поточної задачі й отримує шлях до неї",
        "manual_usage_concept": "workspace розбитий на задачі; кожна задача зберігає контекст, артефакти, скрипти й історію роботи",
        "manual_usage_copy": "у терміналах Claude Code виділяй текст із затиснутим Shift, потім копіюй через Ctrl+Shift+C",
        "manual_usage_reset": "скидає лише збережене посилання на сесію вибраного агента, не видаляючи історію CLI",
        "manual_usage_section": "Основи",
        "manual_usage_structure": "TASK_DESCRIPTION.md, TASK_CONTEXT.md, dev/, scripts/ і report/ тримають роботу відтворюваною",
        "manual_usage_task": "створюй задачу під окрему ціль і вибирай її зліва, щоб відкрити опис, контекст і термінали",
        "missing_context": "немає контексту",
        "missing_desc": "немає опису",
        "new": "Нова",
        "ok": "ОК",
        "open_dev": "Відкрити dev",
        "open_task": "Відкрити папку задачі",
        "open_workspace": "Відкрити workspace",
        "refresh": "Оновити",
        "reload_actions": "Оновити actions",
        "reset_ai_agent_session": "Скинути сесію",
        "run_ai_agent": "Запустити ШІ агента",
        "ai_agent_running": "ШІ агент запущений",
        "restore_ai_agent_session": "Відновити сесію ШІ агента",
        "run_task_check": "Run task_check",
        "save": "Зберегти",
        "select_task_first": "Спочатку вибери задачу",
        "settings": "Налаштування",
        "settings_title": "Налаштування Agent Workspace",
        "task_already_exists": "Задача вже існує",
        "task": "Задача",
        "task_agent_status_column": "ШІ",
        "task_details": "Деталі задачі",
        "task_name": "Назва задачі",
        "tasks": "задач",
        "text_font_size": "Розмір шрифту тексту",
        "theme": "Тема",
        "window_title": "Agent Workspace",
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
class ArtifactEntry:
    group: str
    path: Path
    updated: float


class WorkspaceGtkGui:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.task_actions: list[TaskAction] = []
        self.task_action_errors: list[str] = []
        self.status_message = ""
        self.task_actions_signature: tuple[Path | None, int | None] = (None, None)
        self.task_actions_monitor: Gio.FileMonitor | None = None
        self.task_actions_monitor_path: Path | None = None
        self.artifact_monitors: list[Gio.FileMonitor] = []
        self.artifact_monitor_path: Path | None = None
        self.artifact_sort_column = "name"
        self.artifact_sort_descending = False
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
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.actions_page = box
        self.actions_tab_label = Gtk.Label(label=self._tr("actions"))
        self.notebook.append_page(box, self.actions_tab_label)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(action_row, False, False, 0)
        action_row.pack_start(self._button("run_task_check", self.run_selected_task_check), False, False, 0)
        self.task_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        action_row.pack_start(self.task_actions_box, False, False, 0)
        self.actions_message = Gtk.Label(label="")
        self.actions_message.set_xalign(0)
        box.pack_start(self.actions_message, False, False, 0)

        codex_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(codex_row, False, False, 0)
        self.agent_combo = Gtk.ComboBoxText()
        for agent in AGENT_WORKSPACE_AGENTS:
            self.agent_combo.append_text(agent)
        self.agent_combo.set_active(AGENT_WORKSPACE_AGENTS.index(self.default_agent))
        self.agent_combo.connect("changed", self._on_agent_selected)
        codex_row.pack_start(self.agent_combo, False, False, 0)
        self.run_ai_agent_button = self._button("run_ai_agent", self.run_ai_agent_console)
        self.run_ai_agent_button.set_hexpand(True)
        codex_row.pack_start(self.run_ai_agent_button, True, True, 0)
        self.reset_ai_agent_button = self._button("reset_ai_agent_session", self.reset_ai_agent_session)
        codex_row.pack_start(self.reset_ai_agent_button, False, False, 0)

        self.console_notebook = Gtk.Notebook()
        self.console_notebook.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.console_notebook.connect("button-press-event", self._on_console_notebook_button_press)
        self.console_notebook.connect("switch-page", self._on_console_notebook_switch_page)
        box.pack_start(self.console_notebook, True, True, 0)

    def refresh_tasks(self, *_args: object) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
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
            self._watch_task_artifacts(self.selected_task)
            self._load_task_artifacts(self.selected_task)
        else:
            self.artifact_store.clear()
            self._clear_artifact_monitors()
            self.artifact_monitor_path = None
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
            self._watch_task_artifacts(self.selected_task)
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

    def _reset_actions(self) -> None:
        self.task_actions = []
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
                save_task_agent(task, agent)
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
        reset_task_agent_session(task, agent)
        self._update_codex_button_state()

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
            self._activate_terminal(current.session_id)
            self._update_codex_button_state()
            return
        if decision.action == "keep_current":
            self._set_selected_agent(agent)
            save_task_agent(task, agent)
            return
        if decision.action == "confirm_switch":
            current_agent = decision.current_agent or agent
            if not self._confirm_agent_switch(current_agent, agent):
                self._set_selected_agent(current_agent)
                save_task_agent(task, current_agent)
                return
        if not self._ensure_agent_installed(agent):
            if current is not None:
                self._set_selected_agent(current.kind)
            return
        if current is not None:
            save_task_agent_session(task, current.kind)
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
                label.set_text(_terminal_tab_label(session.kind, shell_index))

    def _show_terminal_tab(self, session: TerminalSession, *, renumber: bool = True) -> None:
        if self.console_notebook.page_num(session.page) < 0:
            tab = self._terminal_tab_widget(session)
            if session_is_agent(session_kind=session.kind):
                self.console_notebook.insert_page(session.page, tab, 0)
            else:
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
        return bool(task_agent_session_markers(task, self.workspace))

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
            self.task_store[row_iter][0] = self._task_agent_status(task)
            self.task_store[row_iter][1] = self._task_label(task)
            self.task_store[row_iter][3] = background
            self.task_store[row_iter][4] = background_set
            self.task_store[row_iter][5] = foreground
            self.task_store[row_iter][6] = foreground_set
            self.task_store[row_iter][7] = weight
            self.task_store[row_iter][8] = weight_set
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
        if self.selected_task is not None and self._artifacts_tab_active():
            self._load_task_artifacts(self.selected_task)
        self._update_ai_agent_button_label()

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
        self._closing = True
        if self.task_actions_monitor is not None:
            self.task_actions_monitor.cancel()
        self._clear_artifact_monitors()
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


def _is_pane_separator_event(pane: Gtk.Paned, event: Gdk.EventButton, tolerance: int = 8) -> bool:
    position = pane.get_position()
    if pane.get_orientation() == Gtk.Orientation.HORIZONTAL:
        return abs(event.x - position) <= tolerance
    return abs(event.y - position) <= tolerance


def _terminal_session_sort_key(kind: str, session_id: int) -> tuple[int, int]:
    return (0 if session_is_agent(session_kind=kind) else 1, session_id)


def _terminal_tab_label(kind: str, shell_index: int) -> str:
    if session_is_agent(session_kind=kind):
        return agent_label(kind)
    return f"{kind} {shell_index}"


def _terminal_tab_text_label(tab: Gtk.Widget | None) -> Gtk.Label | None:
    if isinstance(tab, Gtk.Label):
        return tab
    if isinstance(tab, Gtk.Container):
        for child in tab.get_children():
            if isinstance(child, Gtk.Label):
                return child
    return None


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


def _terminal_clipboard_shortcut(keyval: int, state: int, hardware_keycode: int | None = None) -> str | None:
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


def _copy_terminal_selection(terminal: Vte.Terminal) -> None:
    terminal.grab_focus()
    get_has_selection = getattr(terminal, "get_has_selection", None)
    has_selection = bool(get_has_selection()) if callable(get_has_selection) else True
    try:
        terminal.copy_clipboard_format(Vte.Format.TEXT)
    except (AttributeError, TypeError):
        terminal.copy_clipboard()
    if not has_selection:
        _copy_primary_selection_to_clipboard()


def _copy_primary_selection_to_clipboard() -> None:
    text = _clipboard_text(Gdk.SELECTION_PRIMARY).strip()
    if not text:
        return
    _set_clipboard_text(text)


def _clipboard_text(selection: Gdk.Atom) -> str:
    clipboard = Gtk.Clipboard.get(selection)
    wait_for_text = getattr(clipboard, "wait_for_text", None)
    if not callable(wait_for_text):
        return ""
    return wait_for_text() or ""


def _set_clipboard_text(text: str) -> None:
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(text, -1)
    store = getattr(clipboard, "store", None)
    if callable(store):
        store()


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
        "agent_tools.paf_workspace.task_check",
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


def _terminal_text_tail(terminal: Vte.Terminal, limit: int = 4000) -> str:
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


def _scrolled(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
    scrolled = Gtk.ScrolledWindow()
    scrolled.add(widget)
    return scrolled


def _task_artifact_entries(
    task: TaskSummary,
    *,
    sort_column: str = "name",
    descending: bool = False,
) -> list[ArtifactEntry]:
    entries: list[ArtifactEntry] = []
    for path in _task_artifact_files(task):
        group = _artifact_group(task, path)
        if group is not None:
            entries.append(ArtifactEntry(group, path, _artifact_updated_timestamp(path)))
    result: list[ArtifactEntry] = []
    for group in sorted({entry.group for entry in entries}, key=_artifact_group_sort_key):
        group_entries = [entry for entry in entries if entry.group == group]
        if sort_column == "updated":
            if descending:
                group_entries.sort(
                    key=lambda entry: (-entry.updated, _artifact_relative_label(task, entry.path).casefold())
                )
            else:
                group_entries.sort(
                    key=lambda entry: (entry.updated, _artifact_relative_label(task, entry.path).casefold())
                )
        else:
            group_entries.sort(
                key=lambda entry: (entry.path.name.casefold(), _artifact_relative_label(task, entry.path).casefold()),
                reverse=descending,
            )
        result.extend(group_entries)
    return result


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
    if len(parts) < 1 or parts[0] != "report":
        return None
    if len(parts) >= 2 and parts[1] == "diff":
        return "diff_reports"
    if len(parts) >= 2 and parts[1] == "puml":
        return "diagrams"
    if suffix in _LOG_SUFFIXES:
        return "logs"
    return "artifacts"


def _artifact_group_sort_key(group: str) -> int:
    order = {"logs": 0, "diagrams": 1, "diff_reports": 2, "artifacts": 3}
    return order.get(group, 99)


def _artifact_relative_label(task: TaskSummary, path: Path) -> str:
    try:
        return str(path.relative_to(task.path))
    except ValueError:
        return str(path)


def _artifact_updated_timestamp(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _artifact_updated_label(updated: float) -> str:
    if updated <= 0:
        return ""
    return datetime.fromtimestamp(updated).strftime("%Y-%m-%d %H:%M")


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
    if group == "artifacts":
        return [
            path
            for path in _files_under(task.path / "report")
            if _artifact_group(task, path) == "artifacts"
        ]
    return []


def _artifact_context_action(artifact_path: Path | None, group: str | None) -> str:
    if artifact_path is not None:
        return "artifact"
    if group is not None:
        return "group"
    return "all"


def _artifact_selectable_path(task: TaskSummary, artifact_path: Path) -> Path | None:
    try:
        artifact_path.relative_to(task.path)
    except ValueError:
        return None
    return artifact_path if artifact_path.is_file() else None


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
                    "agent_tools.tools.agent_workspace.actions",
                    "task-check",
                    "--workspace",
                    str(workspace),
                    "--task",
                    str(task.path),
                ]
            ),
        ]
    )


def task_action_shell_command(action: TaskAction) -> str:
    command = action.command if isinstance(action.command, str) else shlex.join(action.command)
    env_values = dict(action.env)
    env_values[PAF_HIDE_TASK_ENV_VAR] = "1"
    env = " ".join(
        f"{key}={shlex.quote(value)}"
        for key, value in sorted(env_values.items())
    )
    prefix = f"{env} " if env else ""
    log_name = task_action_log_basename(action.action_id)
    inner = "\n".join(
        [
            "set -o pipefail",
            "__agent_task_dir=$PWD",
            'while [ "$__agent_task_dir" != "/" ] && [ ! -f "$__agent_task_dir/TASK_DESCRIPTION.md" ]; do',
            '    __agent_task_dir=$(dirname "$__agent_task_dir")',
            "done",
            'if [ ! -f "$__agent_task_dir/TASK_DESCRIPTION.md" ]; then',
            "    __agent_task_dir=$PWD",
            "fi",
            f"__agent_log_dir=\"$__agent_task_dir/{TASK_ACTION_LOGS_DIR.as_posix()}\"",
            'mkdir -p "$__agent_log_dir"',
            f"__agent_log=\"$__agent_log_dir/{log_name}-$(date +%Y%m%d-%H%M%S).log\"",
            'echo "Logging task action to $__agent_log"',
            f"({prefix}{command}) 2>&1 | tee -a \"$__agent_log\"",
            "exit ${PIPESTATUS[0]}",
        ]
    )
    return f"cd {shlex.quote(str(action.cwd))} && bash -lc {shlex.quote(inner)}"


def sys_executable() -> str:
    return sys.executable or "python3"


def _codex_executable() -> str:
    return agent_executable("codex") or "codex"


def _claude_executable() -> str:
    return agent_executable("claude") or "claude"


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
            "agent_session_background": "#4b3713",
            "agent_session_foreground": "#ffe6a3",
            "agent_external_background": "#34383d",
            "agent_external_foreground": "#a8b0ba",
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
        "agent_session_background": "#fff1c2",
        "agent_session_foreground": "#5c3b00",
        "agent_external_background": "#e0e0e0",
        "agent_external_foreground": "#5f6368",
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


def open_containing_folder(path: Path) -> None:
    if sys.platform == "darwin":
        _open_command_or_parent(["open", "-R", str(path)], path)
    elif os.name == "nt":
        _open_command_or_parent(["explorer", f"/select,{path}"], path)
    elif not _show_file_in_freedesktop_file_manager(path):
        open_path(path.parent)


def _open_command_or_parent(command: list[str], path: Path) -> None:
    try:
        subprocess.Popen(command)
    except OSError:
        open_path(path.parent)


def _show_file_in_freedesktop_file_manager(path: Path) -> bool:
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call_sync(
            "org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1",
            "ShowItems",
            GLib.Variant("(ass)", ([path.resolve().as_uri()], "")),
            None,
            Gio.DBusCallFlags.NONE,
            1000,
            None,
        )
    except (GLib.Error, OSError, RuntimeError, ValueError):
        return False
    return True


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

    gui = WorkspaceGtkGui(workspace)
    gui.window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
