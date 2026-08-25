from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import fcntl
import os
import platform
import pty
import queue
import re
import select
import subprocess
import struct
import termios
import threading
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk

from ...task_catalog.api import TASK_CONTEXT_BUDGET
from ...agent_status.api import AGENT_RUNNING_SPINNER_FRAMES
from ...agent_status.api import agent_output_state_update
from ...agent_status.api import agent_status_tooltip_text
from ...agent_status.api import analyze_agent_output
from ...agent_status.api import session_is_agent
from ...agent_status.api import session_is_running_agent
from ...agent_status.api import session_marks_task_pending_permission
from ...agent_status.api import session_should_clear_pending_permission
from ...agent_status.api import task_agent_status_text
from ...agent_status.api import task_for_path
from ...agent_runtime.api import ai_agent_environment
from ...agent_runtime.api import ai_agent_launch_state_for_selection
from ...agent_runtime.api import ai_agent_switch_decision
from ...agent_runtime.api import ai_agent_task_context_prompt
from ...agent_runtime.api import build_ai_agent_console_command
from ...agent_runtime.api import prepare_ai_agent_launch_command
from ...settings.api import AgentModelSettings
from ...task_sessions.api import TaskSessionDiscoveryState
from ...task_catalog.api import TaskSummary
from ...settings.api import AGENT_WORKSPACE_AGENTS
from ...settings.api import AGENT_WORKSPACE_REASONING_EFFORTS
from ...settings.api import AGENT_WORKSPACE_THEMES
from ...settings.api import agent_executable
from ...settings.api import agent_install_command
from ...settings.api import agent_label
from ...settings.api import ai_agent_model_settings
from ...settings.api import agent_workspace_runtime_settings
from ...console_output.api import ConsoleChunk
from ...console_output.api import parse_console_output
from ...localization.api import AGENT_STATUS_MANUAL_ENTRIES
from ...localization.api import AGENT_STATUS_MANUAL_MENU_LABEL
from ...localization.api import AGENT_STATUS_MANUAL_SUBTITLE
from ...localization.api import AGENT_STATUS_MANUAL_TITLE
from ...localization.api import AGENT_STATUS_MANUAL_USAGE_ENTRIES
from ...localization.api import AGENT_STATUS_MANUAL_USAGE_TITLE
from ...process_runtime.api import install_agent_workspace_exception_logger
from ...process_runtime.api import log_agent_workspace_exception
from ...task_sessions.api import clear_task_agent_session
from ...task_sessions.api import clear_task_active_agent_run
from ...settings.api import claude_model_choices_info
from ...settings.api import codex_model_choices_info
from ...task_catalog.api import discover_tasks
from ...task_sessions.api import load_task_agent
from ...settings.api import load_agent_workspace_settings
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
from ...commands.api import sys_executable
from ...commands.api import task_action_shell_command
from ...commands.api import task_check_shell_command
from ...markdown.api import render_markdown_chunks
from ...task_actions.api import TaskAction
from ...task_actions.api import load_task_actions
from agent_tools.tools.task_context import filter_entries as _filter_task_context_entries
from agent_tools.tools.task_context import load_entries as _load_task_context_entries
from ...localization.api import AI_AGENT_BUTTON_LABELS as _AI_AGENT_BUTTON_LABELS
from ...localization.api import tk_string
from ...task_context.api import load_task_context_slots as _load_task_context_slots
from ...task_context.api import render_task_context_slots as _render_task_context_slots
from ...task_context.api import task_goal_slot_markdown as _task_goal_slot_markdown


def _codex_executable() -> str:
    return agent_executable("codex") or "codex"


def _claude_executable() -> str:
    return agent_executable("claude") or "claude"


@dataclass
class ConsoleSession:
    session_id: int
    title: str
    task_path: Path
    kind: str
    frame: ttk.Frame
    text: tk.Text | None
    process: subprocess.Popen[bytes]
    fd: int | None
    chunks: list[ConsoleChunk]
    input_floor_mark: str | None = None
    permission_pending: bool = False
    exited: bool = False
    busy: bool = False
    run_id: str | None = None
    output_generation: int = 0
    permission_signature: str | None = None
    ignored_permission_signature: str | None = None


class HoverTooltip:
    def __init__(self, widget: tk.Widget) -> None:
        self.widget = widget
        self.after_id: str | None = None
        self.window: tk.Toplevel | None = None

    def schedule(self, text: str, x_root: int, y_root: int) -> None:
        self.cancel()
        self.after_id = self.widget.after(550, lambda: self.show(text, x_root, y_root))

    def show(self, text: str, x_root: int, y_root: int) -> None:
        self.after_id = None
        self.hide()
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x_root + 12}+{y_root + 14}")
        label = ttk.Label(window, text=text, padding=(6, 3), relief=tk.SOLID, borderwidth=1)
        label.pack()
        self.window = window

    def cancel(self) -> None:
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide()

    def hide(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


_AI_AGENT_SESSION_DELETE_TITLE = tk_string("delete_saved_session_title")
_AI_AGENT_SESSION_DELETE_BODY = tk_string("delete_saved_session_body")
_AI_AGENT_RESTORE_FAILED_MESSAGE = tk_string("restore_failed_message")
AGENT_BUSY_IDLE_DELAY_MS = 1800


class AgentWorkspace:
    def __init__(self, root: tk.Tk, workspace: Path) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.task_actions: list[TaskAction] = []
        self.console_sessions: dict[int, ConsoleSession] = {}
        self.active_console_id: int | None = None
        self.console_context_text: tk.Text | None = None
        self.console_context_selection = ""
        self.next_console_id = 1
        self._updating_agent_selection = False
        self._updating_task_selection = False
        self._agent_spinner_index = 0
        self.task_session_discovery = TaskSessionDiscoveryState()
        default_font_size = int(tkfont.nametofont("TkDefaultFont").cget("size"))
        settings = agent_workspace_runtime_settings(
            load_agent_workspace_settings(),
            default_font_size=default_font_size,
        )
        self.text_font_size = settings.text_font_size
        self.button_font_size = settings.button_font_size
        self.theme = settings.theme
        self.default_agent = settings.default_agent
        self.default_codex_model = settings.default_codex_model
        self.default_codex_reasoning = settings.default_codex_reasoning
        self.default_claude_model = settings.default_claude_model
        self.default_claude_effort = settings.default_claude_effort
        self.codex_animations_enabled = settings.codex_animations_enabled
        self.claude_animations_enabled = settings.claude_animations_enabled
        self.limited_bash_output_tokens = settings.limited_bash_output_tokens
        self.inject_task_context_prompt = settings.inject_task_context_prompt
        self.task_dictionary_auto_discovery = settings.task_dictionary_auto_discovery
        self.task_dictionary_min_occurrences = settings.task_dictionary_min_occurrences
        self.task_dictionary_min_saving = settings.task_dictionary_min_saving
        self.task_dictionary_min_term_length = settings.task_dictionary_min_term_length
        self.task_dictionary_max_term_words = settings.task_dictionary_max_term_words
        self.task_dictionary_strip_articles = settings.task_dictionary_strip_articles
        self.task_dictionary_preview_text = settings.task_dictionary_preview_text
        self.window_geometry = settings.window_geometry
        self.style = ttk.Style(self.root)
        self.text_font = tkfont.Font(
            family=tkfont.nametofont("TkTextFont").cget("family"),
            size=self.text_font_size,
        )
        self.fixed_font = tkfont.Font(
            family=tkfont.nametofont("TkFixedFont").cget("family"),
            size=self.text_font_size,
        )
        self.tree_font = tkfont.Font(
            family=tkfont.nametofont("TkDefaultFont").cget("family"),
            size=self.text_font_size,
        )
        self.button_font = tkfont.Font(
            family=tkfont.nametofont("TkDefaultFont").cget("family"),
            size=self.button_font_size,
        )
        self.ui_font = tkfont.Font(
            family=tkfont.nametofont("TkDefaultFont").cget("family"),
            size=self.button_font_size,
        )
        self.h1_font = tkfont.Font(family=self.text_font.cget("family"), size=self.text_font_size + 6, weight="bold")
        self.h2_font = tkfont.Font(family=self.text_font.cget("family"), size=self.text_font_size + 4, weight="bold")
        self.h3_font = tkfont.Font(family=self.text_font.cget("family"), size=self.text_font_size + 2, weight="bold")

        self.root.title(f"Agent Workspace - {self.workspace}")
        self.root.geometry(self.window_geometry)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind_all("<F1>", self._open_manual_from_key)
        self._apply_font_size()
        self._build_ui()
        self._apply_font_size()
        self._apply_theme()
        self.refresh_tasks()
        self._poll_messages()
        self._animate_agent_status()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_tasks).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Open Workspace", command=lambda: open_path(self.workspace)).pack(
            side=tk.LEFT,
            padx=(6, 0),
        )
        ttk.Button(toolbar, text="Settings", command=self.open_settings).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        self.summary_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.summary_var).pack(side=tk.LEFT, padx=12)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane = main
        main.bind("<Double-Button-1>", self._on_main_split_double_clicked)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, padding=6)
        main.add(left, weight=1)
        columns = ("agent_status", "details")
        self.task_tree = ttk.Treeview(
            left,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            style="Workspace.Treeview",
        )
        self.task_tree.heading("#0", text="Task")
        self.task_tree.heading("agent_status", text=tk_string("task_agent_status_column"))
        self.task_tree.heading("details", text="Task Details")
        self.task_tree.column("#0", width=250)
        self.task_tree.column("agent_status", width=92, minwidth=72, anchor=tk.CENTER, stretch=False)
        self.task_tree.column("details", width=240)
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)
        self.task_tree.bind("<Double-1>", self._on_task_double_clicked)
        self.task_tree.bind("<Key>", self._on_task_tree_key)
        self.task_tree.bind("<Button-3>", self._on_task_context_menu)
        self.task_tree.bind("<Button-2>", self._on_task_context_menu)
        self.task_status_tooltip = HoverTooltip(self.task_tree)
        self.task_tree.bind("<Motion>", self._on_task_tree_motion)
        self.task_tree.bind("<Leave>", self._hide_task_status_tooltip)
        self.task_tree.bind("<ButtonPress>", self._hide_task_status_tooltip, add=True)
        self.task_context_menu = tk.Menu(self.root, tearoff=False)
        self.task_context_menu.add_command(label="Open Task", command=self.open_task)
        self.task_context_menu.add_command(label="Open dev/", command=self.open_dev)
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label=AGENT_STATUS_MANUAL_MENU_LABEL, command=self.open_agent_status_manual)
        self.console_context_menu = tk.Menu(self.root, tearoff=False)
        self.console_context_menu.add_command(label="Copy", command=self._copy_console_selection)
        self.console_context_menu.add_command(label="Paste", command=self._paste_console_clipboard)

        right = ttk.Frame(main, padding=6)
        main.add(right, weight=3)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self._add_actions_tab()
        self.encoded_context_var = tk.BooleanVar(value=False)
        self.description_text, self.context_text = self._add_details_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)
        self.root.after_idle(self._set_main_default_split)

    def _add_details_tab(self) -> tuple[tk.Text, tk.Text]:
        frame = ttk.Frame(self.notebook)
        details = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        self.details_pane = details
        details.bind("<Double-Button-1>", self._on_details_split_double_clicked)
        details.pack(fill=tk.BOTH, expand=True)
        description_text = self._add_labeled_text_pane(details, "Description")
        context_text = self._add_labeled_text_pane(
            details,
            "Context",
            controls=self._task_context_controls,
        )
        context_text.tag_bind("journal_link", "<Button-1>", self._on_context_entry_link_clicked)
        context_text.tag_bind("journal_link", "<Enter>", lambda _event: context_text.configure(cursor="hand2"))
        context_text.tag_bind("journal_link", "<Leave>", lambda _event: context_text.configure(cursor=""))
        self.notebook.add(frame, text="Details")
        self.root.after_idle(self._set_details_default_split)
        return description_text, context_text

    def _task_context_controls(self, parent: ttk.Frame) -> None:
        ttk.Checkbutton(
            parent,
            text="Encoded",
            variable=self.encoded_context_var,
            command=self._refresh_context_details,
        ).pack(side=tk.RIGHT, padx=2)

    def _add_labeled_text_pane(
        self,
        parent: ttk.PanedWindow,
        title: str,
        *,
        controls: object | None = None,
    ) -> tk.Text:
        frame = ttk.Frame(parent, padding=(0, 0, 0, 4))
        header = ttk.Frame(frame)
        header.pack(side=tk.TOP, fill=tk.X, padx=2, pady=(0, 2))
        ttk.Label(header, text=title).pack(side=tk.LEFT, anchor=tk.W)
        if callable(controls):
            controls(header)
        body = ttk.Frame(frame)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        text = tk.Text(body, wrap=tk.WORD, undo=False, font=self.text_font)
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        parent.add(frame, weight=1)
        self._configure_text_tags(text)
        return text

    def _add_actions_tab(self) -> None:
        frame = ttk.Frame(self.notebook)

        actions_frame = ttk.Frame(frame)
        actions_frame.pack(side=tk.TOP, fill=tk.X)
        toolbar = ttk.Frame(actions_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Run task_check", command=self.run_selected_task_check).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        ttk.Button(toolbar, text="Reload actions", command=self.reload_selected_task_actions).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.task_actions_frame = ttk.Frame(actions_frame)
        self.task_actions_frame.pack(side=tk.TOP, fill=tk.X)
        self.actions_message_var = tk.StringVar(value="")
        ttk.Label(actions_frame, textvariable=self.actions_message_var).pack(
            side=tk.TOP,
            anchor=tk.W,
            padx=2,
            pady=(2, 4),
        )

        console_frame = ttk.Frame(frame)
        console_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        console_toolbar = ttk.Frame(console_frame)
        console_toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(console_toolbar, text=tk_string("new"), command=self.new_console).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        ttk.Button(console_toolbar, text=tk_string("close"), command=self.close_active_console).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.agent_var = tk.StringVar(value=self.default_agent)
        self.agent_combo = ttk.Combobox(
            console_toolbar,
            values=AGENT_WORKSPACE_AGENTS,
            textvariable=self.agent_var,
            state="readonly",
            width=10,
        )
        self.agent_combo.pack(side=tk.LEFT, padx=2, pady=2)
        self.agent_combo.bind("<<ComboboxSelected>>", self._on_agent_selected)
        self.run_ai_agent_button = ttk.Button(
            console_toolbar,
            text=_AI_AGENT_BUTTON_LABELS["run_ai_agent"],
            command=self.run_ai_agent_console,
        )
        self.run_ai_agent_button.pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.reset_ai_agent_button = ttk.Button(
            console_toolbar,
            text=tk_string("reset_session"),
            command=self.reset_ai_agent_session,
        )
        self.reset_ai_agent_button.pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.console_notebook = ttk.Notebook(console_frame)
        self.console_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.console_notebook.bind("<<NotebookTabChanged>>", self._on_console_session_tab_changed)
        self.console_notebook.bind("<Double-1>", self._on_console_notebook_double_clicked)
        self.notebook.add(frame, text="Actions")

    def _create_console_text(self, parent: ttk.Frame) -> tk.Text:
        text = tk.Text(parent, wrap=tk.WORD, undo=False, font=self.fixed_font)
        text.bind("<Key>", self._on_console_key)
        text.bind("<Button-1>", lambda _event: text.focus_set())
        text.bind("<Button-3>", self._on_console_context_menu)
        text.bind("<Button-2>", self._on_console_context_menu)
        scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll_y.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self._configure_console_tags(text)
        self._apply_text_theme(text, _theme_colors(self.theme))
        return text

    def refresh_tasks(self) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
        self._start_task_session_discovery()
        self.task_tree.delete(*self.task_tree.get_children())
        task_iids: dict[str, str] = {}
        for index, task in enumerate(self.tasks):
            flags = []
            if not task.has_context:
                flags.append("missing context db")
            if task.context_over_budget:
                flags.append(f"context > {TASK_CONTEXT_BUDGET}")
            details = f"context {task.context_tokens}"
            if flags:
                details = f"{details}, {', '.join(flags)}"
            self.task_tree.insert(
                "",
                tk.END,
                iid=str(index),
                text=self._task_label(task),
                tags=self._task_tags(task),
                values=(self._task_agent_status(task), details),
            )
            task_iids[task.name] = str(index)
        over_budget = sum(1 for task in self.tasks if task.context_over_budget)
        self.summary_var.set(f"{len(self.tasks)} tasks, {over_budget} over context budget")
        iid = self._selectable_task_iid(selected_name, task_iids)
        self._set_task_tree_selection(iid)

    def _on_task_selected(self, _event: object) -> None:
        if self._updating_task_selection:
            return
        selection = self.task_tree.selection()
        if not selection:
            return
        task = self.tasks[int(selection[0])]
        if self._task_is_external_active(task):
            self._set_task_tree_selection(self._selectable_task_iid(self.selected_task.name if self.selected_task else None))
            return
        self.selected_task = task
        if self._is_details_tab_selected():
            self._set_markdown(self.description_text, _task_goal_slot_markdown(task.path))
            self._refresh_context_details()
        self._reset_actions_tab(task)
        action_errors = self._load_task_action_buttons(task)
        messages = []
        if action_errors:
            messages.append(action_errors.strip())
        self.actions_message_var.set("\n".join(messages))
        selected_agent = task_agent_selection_with_resumable_fallback(
            task,
            self.workspace,
            self.default_agent,
        )
        self.agent_var.set(selected_agent)
        self._update_ai_agent_button_label()
        self._refresh_tree_selection_style()
        if self._is_console_tab_selected():
            self.activate_console_for_task(task)

    def _refresh_context_details(self) -> None:
        if self.selected_task is None:
            if hasattr(self, "context_text"):
                self._set_markdown(self.context_text, "")
            return
        try:
            slots = _load_task_context_slots(self.selected_task.path)
            body = _render_task_context_slots(
                [slot for slot in slots if slot.category != "goal"],
                format_name="agent" if self.encoded_context_var.get() else "markdown",
                task_dir=self.selected_task.path,
            )
        except (OSError, ValueError) as exc:
            body = f"# Context Journal Error\n\n{exc}\n"
        if not body:
            body = "- No matching context entries."
        self._set_markdown(self.context_text, body)

    def _selectable_task_iid(
        self,
        preferred_name: str | None,
        task_iids: dict[str, str] | None = None,
    ) -> str | None:
        task_iids = task_iids or {task.name: str(index) for index, task in enumerate(self.tasks)}
        if preferred_name:
            preferred_iid = task_iids.get(preferred_name)
            if preferred_iid is not None and not self._task_is_external_active(self.tasks[int(preferred_iid)]):
                return preferred_iid
        for index, task in enumerate(self.tasks):
            if not self._task_is_external_active(task):
                return str(index)
        return None

    def _set_task_tree_selection(self, iid: str | None) -> None:
        self._updating_task_selection = True
        try:
            self.task_tree.selection_remove(*self.task_tree.selection())
            if iid is None:
                self._clear_selected_task_view()
                return
            self.task_tree.selection_set(iid)
            self.task_tree.focus(iid)
            self.task_tree.see(iid)
        finally:
            self._updating_task_selection = False
        self._on_task_selected(object())

    def _clear_selected_task_view(self) -> None:
        self.selected_task = None
        if hasattr(self, "description_text"):
            self._set_markdown(self.description_text, "")
        if hasattr(self, "context_text"):
            self._set_markdown(self.context_text, "")
        self.task_actions = []
        if hasattr(self, "task_actions_frame"):
            for child in self.task_actions_frame.winfo_children():
                child.destroy()
        if hasattr(self, "actions_message_var"):
            self.actions_message_var.set("")
        if hasattr(self, "agent_var"):
            self.agent_var.set(self.default_agent)
        if hasattr(self, "run_ai_agent_button"):
            self._update_ai_agent_button_label()

    def _on_task_double_clicked(self, _event: object) -> None:
        self.open_task()

    def _ignore_task_tree_keyboard_activation(self, _event: object) -> str:
        return "break"

    def _on_task_tree_key(self, event: tk.Event[ttk.Treeview]) -> str | None:
        keysym = str(getattr(event, "keysym", ""))
        if keysym in {
            "Up",
            "Down",
            "Left",
            "Right",
            "Home",
            "End",
            "Prior",
            "Next",
            "Tab",
            "ISO_Left_Tab",
            "F1",
        }:
            return None
        return "break"

    def _on_task_tree_motion(self, event: tk.Event[ttk.Treeview]) -> None:
        column = self.task_tree.identify_column(event.x)
        region = self.task_tree.identify_region(event.x, event.y)
        row = self.task_tree.identify_row(event.y)
        if column == "#1" and region == "cell" and row:
            values = self.task_tree.item(row, "values")
            status_text = str(values[0]) if values else ""
            tooltip_text = agent_status_tooltip_text(status_text)
            if tooltip_text:
                self.task_status_tooltip.schedule(tooltip_text, event.x_root, event.y_root)
            else:
                self.task_status_tooltip.cancel()
        else:
            self.task_status_tooltip.cancel()

    def _hide_task_status_tooltip(self, _event: object | None = None) -> None:
        self.task_status_tooltip.cancel()

    def _on_task_context_menu(self, event: tk.Event[tk.Misc]) -> None:
        row = self.task_tree.identify_row(event.y)
        if row:
            self.task_tree.selection_set(row)
            self.task_tree.focus(row)
            self._on_task_selected(event)
        self.task_context_menu.tk_popup(event.x_root, event.y_root)
        self.task_context_menu.grab_release()

    def _open_manual_from_key(self, _event: object) -> str:
        self.open_agent_status_manual()
        return "break"

    def open_agent_status_manual(self) -> None:
        colors = _theme_colors(self.theme)
        window = tk.Toplevel(self.root)
        window.title(AGENT_STATUS_MANUAL_TITLE)
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(background=colors["background"])

        frame = ttk.Frame(window, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)
        title_font = tkfont.Font(family=self.ui_font.actual("family"), size=self.button_font_size + 3, weight="bold")
        body_font = tkfont.Font(family=self.ui_font.actual("family"), size=self.button_font_size)
        marker_font = tkfont.Font(family=self.ui_font.actual("family"), size=self.button_font_size + 5, weight="bold")

        tk.Label(
            frame,
            text=AGENT_STATUS_MANUAL_TITLE,
            font=title_font,
            background=colors["background"],
            foreground=colors["foreground"],
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W)
        tk.Label(
            frame,
            text=AGENT_STATUS_MANUAL_SUBTITLE,
            font=body_font,
            background=colors["background"],
            foreground=colors["muted_foreground"],
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(2, 12))

        tk.Label(
            frame,
            text=AGENT_STATUS_MANUAL_USAGE_TITLE,
            font=body_font,
            background=colors["background"],
            foreground=colors["foreground"],
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

        row = 3
        for name, description in AGENT_STATUS_MANUAL_USAGE_ENTRIES:
            tk.Label(
                frame,
                text=name,
                font=body_font,
                background=colors["background"],
                foreground=colors["foreground"],
            ).grid(row=row, column=0, sticky=tk.W, pady=3)
            tk.Label(
                frame,
                text=description,
                font=body_font,
                background=colors["background"],
                foreground=colors["muted_foreground"],
            ).grid(row=row, column=1, columnspan=2, sticky=tk.W, padx=(12, 0), pady=3)
            row += 1

        tk.Label(
            frame,
            text=AGENT_STATUS_MANUAL_SUBTITLE,
            font=body_font,
            background=colors["background"],
            foreground=colors["foreground"],
        ).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(14, 6))
        row += 1

        for marker, label, description in AGENT_STATUS_MANUAL_ENTRIES:
            display_marker = AGENT_RUNNING_SPINNER_FRAMES[self._agent_spinner_index] if marker.startswith("▸") else marker
            tk.Label(
                frame,
                text=display_marker,
                width=4,
                anchor=tk.CENTER,
                font=marker_font,
                background=colors["text_background"],
                foreground=colors["foreground"],
                padx=8,
                pady=4,
            ).grid(row=row, column=0, sticky=tk.NSEW, pady=4)
            tk.Label(
                frame,
                text=label,
                font=body_font,
                background=colors["background"],
                foreground=colors["foreground"],
            ).grid(row=row, column=1, sticky=tk.W, padx=(12, 8), pady=4)
            tk.Label(
                frame,
                text=description,
                font=body_font,
                background=colors["background"],
                foreground=colors["muted_foreground"],
            ).grid(row=row, column=2, sticky=tk.W, pady=4)
            row += 1

        close_button = ttk.Button(frame, text=tk_string("ok"), command=window.destroy)
        close_button.grid(row=row, column=0, columnspan=3, sticky=tk.E, pady=(16, 0))
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        x = root_x + max((self.root.winfo_width() - width) // 2, 0)
        y = root_y + max((self.root.winfo_height() - height) // 2, 0)
        window.geometry(f"+{x}+{y}")
        window.grab_set()
        close_button.focus_set()

    def _on_notebook_tab_changed(self, _event: object) -> None:
        if self.selected_task is None:
            return
        if self._is_details_tab_selected():
            self._set_markdown(self.description_text, _task_goal_slot_markdown(self.selected_task.path))
            self._refresh_context_details()
        elif self._is_console_tab_selected():
            self.activate_console_for_task(self.selected_task)

    def _is_details_tab_selected(self) -> bool:
        try:
            return self.notebook.tab(self.notebook.select(), "text") == "Details"
        except tk.TclError:
            return False

    def open_task(self) -> None:
        task = self._require_task()
        if task is not None:
            open_path(task.path)

    def open_dev(self) -> None:
        task = self._require_task()
        if task is None:
            return
        dev = task.path / "dev"
        if dev.exists():
            open_path(dev)
        else:
            messagebox.showinfo(tk_string("no_dev_title"), tk_string("no_dev_body", dev=dev))

    def open_settings(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Agent Workspace settings")
        window.transient(self.root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        text_size_var = tk.IntVar(value=self.text_font_size)
        button_size_var = tk.IntVar(value=self.button_font_size)
        theme_var = tk.StringVar(value=self.theme)
        default_agent_var = tk.StringVar(value=self.default_agent)
        codex_model_var = tk.StringVar(value=self.default_codex_model)
        codex_reasoning_var = tk.StringVar(value=self.default_codex_reasoning)
        claude_model_var = tk.StringVar(value=self.default_claude_model)
        claude_effort_var = tk.StringVar(value=self.default_claude_effort)
        limited_bash_output_tokens_var = tk.IntVar(value=self.limited_bash_output_tokens)
        codex_available = agent_executable("codex") is not None
        claude_available = agent_executable("claude") is not None
        codex_models = codex_model_choices_info(use_cli=False) if codex_available else None
        claude_models = claude_model_choices_info() if claude_available else None
        codex_model_values = (
            model_choices_with_current(codex_models.choices, self.default_codex_model)
            if codex_models is not None
            else ()
        )
        claude_model_values = (
            model_choices_with_current(claude_models.choices, self.default_claude_model)
            if claude_models is not None
            else ()
        )

        ttk.Label(frame, text="Text font size").grid(row=0, column=0, sticky=tk.W, pady=4)
        tk.Spinbox(
            frame,
            from_=8,
            to=28,
            textvariable=text_size_var,
            width=6,
            font=self.ui_font,
        ).grid(row=0, column=1, sticky=tk.W, pady=4)
        ttk.Label(frame, text="Button font size").grid(row=1, column=0, sticky=tk.W, pady=4)
        tk.Spinbox(
            frame,
            from_=8,
            to=28,
            textvariable=button_size_var,
            width=6,
            font=self.ui_font,
        ).grid(row=1, column=1, sticky=tk.W, pady=4)
        ttk.Label(frame, text="Theme").grid(row=2, column=0, sticky=tk.W, pady=4)
        theme_combo = ttk.Combobox(
            frame,
            values=AGENT_WORKSPACE_THEMES,
            textvariable=theme_var,
            state="readonly",
            width=10,
            font=self.ui_font,
        )
        theme_combo.grid(row=2, column=1, sticky=tk.W, pady=4)
        ttk.Label(frame, text="Default AI agent").grid(row=3, column=0, sticky=tk.W, pady=4)
        agent_combo = ttk.Combobox(
            frame,
            values=AGENT_WORKSPACE_AGENTS,
            textvariable=default_agent_var,
            state="readonly",
            width=10,
            font=self.ui_font,
        )
        agent_combo.grid(row=3, column=1, sticky=tk.W, pady=4)
        row = 4
        ttk.Label(frame, text="Bash output limit, tokens").grid(row=row, column=0, sticky=tk.W, pady=4)
        tk.Spinbox(
            frame,
            from_=100,
            to=200_000,
            increment=100,
            textvariable=limited_bash_output_tokens_var,
            width=10,
            font=self.ui_font,
        ).grid(row=row, column=1, sticky=tk.W, pady=4)
        row += 1
        if codex_models is not None:
            ttk.Label(frame, text="Codex model").grid(row=row, column=0, sticky=tk.W, pady=4)
            codex_model_combo = ttk.Combobox(
                frame,
                values=codex_model_values,
                textvariable=codex_model_var,
                state="readonly",
                width=22,
                font=self.ui_font,
            )
            codex_model_combo.grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1
            ttk.Label(frame, text="Codex reasoning").grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Combobox(
                frame,
                values=AGENT_WORKSPACE_REASONING_EFFORTS,
                textvariable=codex_reasoning_var,
                state="readonly",
                width=10,
                font=self.ui_font,
            ).grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1
        if claude_models is not None:
            ttk.Label(frame, text="Claude model").grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Combobox(
                frame,
                values=claude_model_values,
                textvariable=claude_model_var,
                state="readonly",
                width=22,
                font=self.ui_font,
            ).grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1
            ttk.Label(frame, text="Claude effort").grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Combobox(
                frame,
                values=AGENT_WORKSPACE_REASONING_EFFORTS,
                textvariable=claude_effort_var,
                state="readonly",
                width=10,
                font=self.ui_font,
            ).grid(row=row, column=1, sticky=tk.W, pady=4)
            row += 1

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(
            buttons,
            text=tk_string("apply"),
            command=lambda: self._apply_settings_values(
                text_size_var,
                button_size_var,
                theme_var,
                default_agent_var,
                codex_model_var,
                codex_reasoning_var,
                claude_model_var,
                claude_effort_var,
                limited_bash_output_tokens_var,
            ),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            buttons,
            text=tk_string("ok"),
            command=lambda: self._close_settings(
                window,
                text_size_var,
                button_size_var,
                theme_var,
                default_agent_var,
                codex_model_var,
                codex_reasoning_var,
                claude_model_var,
                claude_effort_var,
                limited_bash_output_tokens_var,
            ),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text=tk_string("cancel"), command=window.destroy).pack(side=tk.LEFT, padx=2)
        if codex_models is not None:
            def refresh_codex_models() -> None:
                info = codex_model_choices_info(use_cli=True)

                def apply_codex_models() -> None:
                    if not window.winfo_exists():
                        return
                    current = codex_model_var.get().strip()
                    codex_model_combo.configure(values=model_choices_with_current(info.choices, current))

                self.root.after(0, apply_codex_models)

            threading.Thread(target=refresh_codex_models, daemon=True).start()

    def _close_settings(
        self,
        window: tk.Toplevel,
        text_size_var: tk.IntVar,
        button_size_var: tk.IntVar,
        theme_var: tk.StringVar,
        default_agent_var: tk.StringVar,
        codex_model_var: tk.StringVar,
        codex_reasoning_var: tk.StringVar,
        claude_model_var: tk.StringVar,
        claude_effort_var: tk.StringVar,
        limited_bash_output_tokens_var: tk.IntVar,
    ) -> None:
        self._apply_settings_values(
            text_size_var,
            button_size_var,
            theme_var,
            default_agent_var,
            codex_model_var,
            codex_reasoning_var,
            claude_model_var,
            claude_effort_var,
            limited_bash_output_tokens_var,
        )
        window.destroy()

    def _apply_settings_values(
        self,
        text_size_var: tk.IntVar,
        button_size_var: tk.IntVar,
        theme_var: tk.StringVar,
        default_agent_var: tk.StringVar,
        codex_model_var: tk.StringVar,
        codex_reasoning_var: tk.StringVar,
        claude_model_var: tk.StringVar,
        claude_effort_var: tk.StringVar,
        limited_bash_output_tokens_var: tk.IntVar,
    ) -> None:
        try:
            text_font_size = text_size_var.get()
            button_font_size = button_size_var.get()
            limited_bash_output_tokens = limited_bash_output_tokens_var.get()
        except tk.TclError:
            return
        theme = theme_var.get()
        self.text_font_size = max(8, min(28, text_font_size))
        self.button_font_size = max(8, min(28, button_font_size))
        self.theme = theme if theme in AGENT_WORKSPACE_THEMES else "light"
        self.default_agent = normalize_agent(default_agent_var.get())
        self.default_codex_model = codex_model_var.get().strip()
        self.default_codex_reasoning = (
            codex_reasoning_var.get() if codex_reasoning_var.get() in AGENT_WORKSPACE_REASONING_EFFORTS else ""
        )
        self.default_claude_model = claude_model_var.get().strip()
        self.default_claude_effort = (
            claude_effort_var.get() if claude_effort_var.get() in AGENT_WORKSPACE_REASONING_EFFORTS else ""
        )
        self.limited_bash_output_tokens = max(100, min(200_000, limited_bash_output_tokens))
        if self.selected_task is None:
            self._set_agent_selection(self.default_agent)
        self._apply_font_size()
        self._apply_theme()
        self._save_settings()

    def _on_agent_selected(self, _event: object | None = None) -> None:
        if self._updating_agent_selection:
            return
        task = self.selected_task
        if task is None:
            return
        agent = normalize_agent(self.agent_var.get())
        self._set_agent_selection(agent)
        current = self._running_agent_session(task)
        if current is None or current.kind == agent:
            old_agent = load_task_agent(task, self.default_agent)
            if old_agent != agent and task_agent_has_resumable_state(task, self.workspace, old_agent):
                if not self._confirm_saved_agent_session_delete(old_agent, agent):
                    self._set_agent_selection(old_agent)
                    return
                clear_task_agent_session(task, old_agent)
            save_task_agent(task, agent)
            self._update_ai_agent_button_label()
            self._refresh_task_session_indicators()
            self._refresh_tree_selection_style()
            return
        self._switch_task_agent(task, agent, start_if_changed=True)

    def run_selected_task_check(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._send_command_to_task_console(task, task_check_shell_command(self.workspace, task))

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is None:
            return
        self.notebook.select(0)
        self._send_command_to_task_console(task, task_action_shell_command(action))

    def reload_selected_task_actions(self) -> None:
        task = self._require_task()
        if task is None:
            return
        action_errors = self._load_task_action_buttons(task)
        self.actions_message_var.set(action_errors.strip())

    def _reset_actions_tab(self, task: TaskSummary) -> None:
        self.task_actions = []

    def _load_task_action_buttons(self, task: TaskSummary) -> str:
        for child in self.task_actions_frame.winfo_children():
            child.destroy()
        actions, errors = load_task_actions(task)
        self.task_actions = actions
        for action in actions:
            ttk.Button(
                self.task_actions_frame,
                text=action.label,
                command=lambda item=action: self.run_custom_task_action(item),
            ).pack(side=tk.LEFT, padx=2, pady=2)
        if not errors:
            return ""
        return "\n".join(errors) + "\n\n"

    def _poll_messages(self) -> None:
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "console":
                if (
                    not isinstance(payload, tuple)
                    or len(payload) != 2
                    or not isinstance(payload[0], int)
                    or not isinstance(payload[1], list)
                ):
                    continue
                session_id, chunks = payload
                self._append_console_output(session_id, chunks)
        self.root.after(100, self._poll_messages)

    def activate_console_for_task(self, task: TaskSummary) -> None:
        self._refresh_console_tabs_for_task(task)
        for session in self._current_task_console_sessions(task):
            if session.process.poll() is None:
                self._activate_console(session.session_id)
                return
        self.new_console(task)

    def new_console(self, task: TaskSummary | None = None) -> int | None:
        task = task or self._require_task()
        if task is None:
            return None
        shell = os.environ.get("SHELL") or "/bin/bash"
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        env["PS1"] = f"{task.name}$ "
        env["PROMPT_COMMAND"] = ""
        return self._start_console_process(
            task=task,
            command=[shell],
            cwd=task.path,
            env=env,
            title_prefix="shell",
            startup_text=f"Starting shell in {task.path}\n",
        )

    def _send_command_to_task_console(self, task: TaskSummary, command: str) -> None:
        session, created = self._writable_console_for_task(task)
        if session is None or session.fd is None:
            messagebox.showerror(tk_string("console_title"), tk_string("console_write_unavailable"))
            return
        self._activate_console(session.session_id)

        def write_command() -> None:
            if session.fd is None or session.process.poll() is not None:
                return
            try:
                os.write(session.fd, command.encode() + b"\r")
            except OSError as error:
                messagebox.showerror(tk_string("console_title"), tk_string("console_write_failed", error=error))

        if created:
            self.root.after(250, write_command)
            return
        write_command()

    def _writable_console_for_task(self, task: TaskSummary) -> tuple[ConsoleSession | None, bool]:
        active = self._active_console()
        if active is not None and active.task_path == task.path and active.fd is not None:
            if active.process.poll() is None:
                return active, False
        for session in self._current_task_console_sessions(task):
            if session.fd is not None and session.process.poll() is None:
                return session, False
        session_id = self.new_console(task)
        if session_id is None:
            return None, False
        return self.console_sessions.get(session_id), True

    def run_ai_agent_console(self) -> None:
        task = self._require_task()
        if task is None:
            return
        agent = normalize_agent(self.agent_var.get())
        self._switch_task_agent(task, agent, start_if_changed=True)

    def reset_ai_agent_session(self) -> None:
        task = self._require_task()
        if task is None:
            return
        agent = normalize_agent(self.agent_var.get())
        if not self._confirm_agent_session_reset(agent):
            return
        for session in self._current_task_console_sessions(task):
            if session.kind == agent and session_is_agent(session_kind=session.kind):
                self.stop_console(session.session_id)
                break
        reset_task_agent_session(task, agent)
        self._update_ai_agent_button_label()
        self._refresh_task_session_indicators()
        self._refresh_tree_selection_style()

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
            self._activate_console(current.session_id)
            return
        if decision.action == "keep_current":
            self._set_agent_selection(agent)
            save_task_agent(task, agent)
            return
        if decision.action == "confirm_switch":
            current_agent = decision.current_agent or agent
            if not self._confirm_agent_switch(current_agent, agent):
                self._set_agent_selection(current_agent)
                save_task_agent(task, current_agent)
                return
        if not self._ensure_agent_installed(agent):
            if current is not None:
                self._set_agent_selection(current.kind)
            return
        if current is not None:
            save_task_agent_session(task, current.kind)
            self.stop_console(current.session_id)
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
            inject_task_context=self.inject_task_context_prompt,
            codex_animations_enabled=self.codex_animations_enabled,
            claude_animations_enabled=self.claude_animations_enabled,
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
        )
        self._update_ai_agent_button_label()
        self._refresh_task_session_indicators()
        for session in self._current_task_console_sessions(task):
            if session.kind != agent:
                continue
            if session.process.poll() is None:
                self._activate_console(session.session_id)
                return
            self.stop_console(session.session_id)
            break
        self._start_embedded_terminal_process(
            task=task,
            command=launch.command,
            cwd=self.workspace,
            title_prefix=agent,
            env=env,
            run_id=run_id,
        )

    def _update_ai_agent_button_label(self) -> None:
        task = self.selected_task
        running_agent = None
        agent = normalize_agent(self.agent_var.get())
        if task is not None:
            current = self._running_agent_session(task)
            running_agent = current.kind if current is not None else None
        state = ai_agent_launch_state_for_selection(
            task,
            self.workspace,
            agent,
            running_agent=running_agent,
        )
        self.run_ai_agent_button.configure(text=_AI_AGENT_BUTTON_LABELS[state.label_key])
        self.reset_ai_agent_button.configure(state=tk.NORMAL if state.reset_enabled else tk.DISABLED)

    def _task_has_resumable_agent_session(self, task: TaskSummary) -> bool:
        return bool(task_agent_session_markers(task, self.workspace))

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
            log_agent_workspace_exception(self.workspace, "tk-session-discovery", type(exc), exc, exc.__traceback__)
        self.root.after(0, lambda task_path=task.path: self._finish_task_session_discovery(task_path))

    def _finish_task_session_discovery(self, task_path: Path) -> None:
        self.task_session_discovery.finish(task_path)
        task = self._task_for_path(task_path)
        if self.selected_task is not None and self.selected_task.path == task_path:
            self._set_selected_agent(
                task_agent_selection_with_resumable_fallback(
                    task,
                    self.workspace,
                    self.default_agent,
                )
            )
            self._update_ai_agent_button_label()
        self._refresh_task_session_indicators()

    def _task_for_path(self, path: Path) -> TaskSummary:
        return task_for_path(self.tasks, path)

    def _task_tags(self, task: TaskSummary) -> tuple[str, ...]:
        if self._task_is_external_active(task):
            return ("agent-external-active",)
        return ()

    def _task_is_external_active(self, task: TaskSummary) -> bool:
        return task_has_external_active_agent_run(task, self._local_agent_run_ids())

    def _local_agent_run_ids(self) -> set[str]:
        return {
            session.run_id
            for session in getattr(self, "console_sessions", {}).values()
            if session.run_id is not None
        }

    def _task_running_agent_kinds(self, task: TaskSummary) -> tuple[str, ...]:
        local_agents = tuple(
            session.kind
            for session in self._current_task_console_sessions(task)
            if session_is_running_agent(
                session_kind=session.kind,
                exited=session.exited,
            )
            and session.process.poll() is None
        )
        if local_agents:
            return local_agents
        return ()

    def _task_has_busy_agent(self, task: TaskSummary) -> bool:
        return any(
            session.busy
            for session in self._current_task_console_sessions(task)
            if session_is_running_agent(
                session_kind=session.kind,
                exited=session.exited,
            )
            and session.process.poll() is None
        )

    def _set_agent_session_busy(self, session: ConsoleSession, busy: bool) -> None:
        if not session_is_agent(session_kind=session.kind) or session.exited:
            return
        if session.busy == busy:
            return
        session.busy = busy
        self._refresh_task_session_indicators()

    def _schedule_agent_idle_after_output(self, session: ConsoleSession) -> None:
        if not session_is_agent(session_kind=session.kind) or session.exited or session.permission_pending:
            return
        session.output_generation += 1
        generation = session.output_generation
        self.root.after(
            AGENT_BUSY_IDLE_DELAY_MS,
            lambda session_id=session.session_id, expected_generation=generation: (
                self._mark_agent_idle_if_output_quiet(session_id, expected_generation)
            ),
        )

    def _mark_agent_idle_if_output_quiet(self, session_id: int, expected_generation: int) -> None:
        session = self.console_sessions.get(session_id)
        if session is None or session.output_generation != expected_generation:
            return
        if session.exited or session.permission_pending or session.process.poll() is not None:
            return
        self._set_agent_session_busy(session, False)

    def _agent_session_output_tail(self, session: ConsoleSession) -> str:
        text = "".join(chunk.text for chunk in session.chunks[-300:])
        return text[-8000:]

    def _handle_agent_restore_failed(self, session: ConsoleSession) -> None:
        task = self._task_for_path(session.task_path)
        clear_task_agent_session(task, session.kind)
        self.actions_message_var.set(
            _AI_AGENT_RESTORE_FAILED_MESSAGE.format(
                agent=agent_label(session.kind),
                task=task.name,
            )
        )
        self.stop_console(session.session_id)
        self._update_ai_agent_button_label()
        self._refresh_task_session_indicators()
        self._refresh_tree_selection_style()

    def _running_agent_session(self, task: TaskSummary) -> ConsoleSession | None:
        for session in self._current_task_console_sessions(task):
            if session_is_running_agent(
                session_kind=session.kind,
                exited=session.exited,
            ) and session.process.poll() is None:
                return session
        return None

    def _running_agent_sessions(self) -> list[ConsoleSession]:
        return [
            session
            for session in self.console_sessions.values()
            if session_is_running_agent(
                session_kind=session.kind,
                exited=session.exited,
            )
            and session.process.poll() is None
        ]

    def _task_has_pending_agent_permission(self, task: TaskSummary) -> bool:
        return any(
            session_marks_task_pending_permission(
                session_kind=session.kind,
                session_task_path=session.task_path,
                permission_pending=session.permission_pending,
                exited=session.exited,
                task_path=task.path,
            )
            and session.process.poll() is None
            for session in self.console_sessions.values()
        )

    def _task_label(self, task: TaskSummary) -> str:
        discovery = getattr(self, "task_session_discovery", None)
        if discovery is not None and discovery.is_pending(task):
            return f"◆ {task.name}"
        return task.name

    def _task_agent_status(self, task: TaskSummary) -> str:
        return task_agent_status_text(
            task,
            self.workspace,
            permission_pending=self._task_has_pending_agent_permission(task),
            running_agents=self._task_running_agent_kinds(task),
            external_active=self._task_is_external_active(task),
            spinner_frame=(
                AGENT_RUNNING_SPINNER_FRAMES[self._agent_spinner_index]
                if self._task_has_busy_agent(task)
                else ""
            ),
        )

    def _refresh_task_permission_indicators(self) -> None:
        for index, task in enumerate(self.tasks):
            iid = str(index)
            if self.task_tree.exists(iid):
                self.task_tree.item(iid, text=self._task_label(task))
                values = list(self.task_tree.item(iid, "values"))
                if values:
                    values[0] = self._task_agent_status(task)
                    self.task_tree.item(iid, values=tuple(values))

    def _refresh_task_session_indicators(self) -> None:
        for index, task in enumerate(self.tasks):
            iid = str(index)
            if self.task_tree.exists(iid):
                self.task_tree.item(iid, text=self._task_label(task))
                self.task_tree.item(iid, tags=self._task_tags(task))
                values = list(self.task_tree.item(iid, "values"))
                if values:
                    values[0] = self._task_agent_status(task)
                    self.task_tree.item(iid, values=tuple(values))
        self._ensure_selected_task_is_selectable()
        self._refresh_tree_selection_style()

    def _ensure_selected_task_is_selectable(self) -> None:
        if self.selected_task is not None and self._task_is_external_active(self.selected_task):
            self._set_task_tree_selection(self._selectable_task_iid(None))

    def _animate_agent_status(self) -> None:
        self._agent_spinner_index = (self._agent_spinner_index + 1) % len(AGENT_RUNNING_SPINNER_FRAMES)
        if self._running_agent_sessions():
            self._refresh_task_session_indicators()
        self.root.after(120, self._animate_agent_status)

    def _refresh_tree_selection_style(self) -> None:
        colors = _theme_colors(self.theme)
        self.style.map(
            "Workspace.Treeview",
            background=[("selected", colors["selection_background"])],
            foreground=[("selected", colors["selection_foreground"])],
        )

    def _set_agent_selection(self, agent: str) -> None:
        self._updating_agent_selection = True
        try:
            self.agent_var.set(normalize_agent(agent))
        finally:
            self._updating_agent_selection = False

    def _confirm_agent_switch(self, current_agent: str, next_agent: str) -> bool:
        return self._confirm_dialog(
            tk_string("confirm_switch_agent_title"),
            tk_string(
                "confirm_switch_agent_body",
                current=agent_label(current_agent),
                next=agent_label(next_agent),
            ),
        )

    def _confirm_saved_agent_session_delete(self, old_agent: str, new_agent: str) -> bool:
        return self._confirm_dialog(
            _AI_AGENT_SESSION_DELETE_TITLE,
            _AI_AGENT_SESSION_DELETE_BODY.format(
                old_agent=agent_label(old_agent),
                new_agent=agent_label(new_agent),
            ),
        )

    def _confirm_agent_session_reset(self, agent: str) -> bool:
        return self._confirm_dialog(
            tk_string("confirm_reset_agent_session_title"),
            tk_string("confirm_reset_agent_session_body", agent=agent_label(agent)),
            confirm_label=tk_string("reset_session"),
        )

    def _ensure_agent_installed(self, agent: str) -> bool:
        if agent_executable(agent):
            return True
        install_command = agent_install_command(agent)
        message = tk_string(
            "ai_agent_not_installed_body",
            agent=agent_label(agent),
            install_command=install_command,
        )
        messagebox.showerror(tk_string("ai_agent_not_installed_title"), message)
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
            labels += tk_string("close_running_agents_more", count=len(sessions) - 5)
        return self._confirm_dialog(
            tk_string("close_running_agents_title"),
            tk_string("close_running_agents_body", sessions=labels),
        )

    def _confirm_dialog(self, title: str, body: str, confirm_label: str | None = None) -> bool:
        confirm_label = confirm_label or tk_string("continue")
        window = tk.Toplevel(self.root)
        window.title(title)
        window.transient(self.root)
        window.resizable(False, False)
        result = tk.BooleanVar(value=False)

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=body, justify=tk.LEFT, wraplength=620).pack(fill=tk.X)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(14, 0))

        def close(value: bool) -> None:
            result.set(value)
            window.destroy()

        cancel_button = ttk.Button(buttons, text=tk_string("cancel"), command=lambda: close(False))
        cancel_button.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(buttons, text=confirm_label, command=lambda: close(True)).pack(side=tk.RIGHT)
        window.protocol("WM_DELETE_WINDOW", lambda: close(False))
        window.bind("<Escape>", lambda _event: close(False))
        window.bind("<Return>", lambda _event: close(True))
        window.update_idletasks()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        width = window.winfo_width()
        height = window.winfo_height()
        x = root_x + max((root_width - width) // 2, 0)
        y = root_y + max((root_height - height) // 2, 0)
        window.geometry(f"+{x}+{y}")
        window.grab_set()
        cancel_button.focus_set()
        window.wait_window()
        return bool(result.get())

    def run_codex_console(self) -> None:
        self._set_agent_selection("codex")
        self.run_ai_agent_console()

    def _start_embedded_terminal_process(
        self,
        task: TaskSummary,
        command: list[str],
        cwd: Path,
        title_prefix: str,
        env: dict[str, str] | None = None,
        run_id: str | None = None,
    ) -> int | None:
        session_id = self.next_console_id
        self.next_console_id += 1
        frame = tk.Frame(self.console_notebook, container=True)
        self.console_notebook.add(frame, text=title_prefix)
        self.console_notebook.select(frame)
        frame.update_idletasks()
        process = subprocess.Popen(
            embedded_terminal_command(
                socket_id=frame.winfo_id(),
                cwd=cwd,
                command=command,
                font_size=self.text_font_size,
                theme=self.theme,
            ),
            cwd=self.workspace,
            env=env,
            close_fds=True,
        )
        session_run_id = run_id if session_is_agent(session_kind=title_prefix) else None
        session = ConsoleSession(
            session_id=session_id,
            title=title_prefix,
            task_path=task.path,
            kind=title_prefix,
            frame=frame,
            text=None,
            process=process,
            fd=None,
            chunks=[],
            busy=session_is_agent(session_kind=title_prefix),
            run_id=session_run_id,
        )
        self.console_sessions[session_id] = session
        if session.run_id is not None:
            save_task_active_agent_run(task, title_prefix, session.run_id)
        self._renumber_console_tabs(task)
        if self.selected_task is not None and self.selected_task.path == task.path:
            self._show_console_tab(session)
        self._activate_console(session_id)
        return session_id

    def _start_console_process(
        self,
        task: TaskSummary,
        command: list[str],
        cwd: Path,
        env: dict[str, str],
        title_prefix: str,
        startup_text: str,
        run_id: str | None = None,
    ) -> int | None:
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as error:
            messagebox.showerror(tk_string("console_title"), tk_string("console_start_failed", error=error))
            return None
        _set_pty_size(slave_fd, rows=30, columns=120)
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                preexec_fn=lambda: _make_controlling_terminal(slave_fd),
            )
        except OSError as error:
            os.close(master_fd)
            messagebox.showerror(
                tk_string("console_title"),
                tk_string("console_start_command_failed", command=command[0], error=error),
            )
            return None
        finally:
            os.close(slave_fd)

        session_id = self.next_console_id
        self.next_console_id += 1
        title = title_prefix
        frame = ttk.Frame(self.console_notebook)
        text = self._create_console_text(frame)
        session = ConsoleSession(
            session_id=session_id,
            title=title,
            task_path=task.path,
            kind=title_prefix,
            frame=frame,
            text=text,
            process=process,
            fd=master_fd,
            chunks=[ConsoleChunk(startup_text, ())],
            busy=session_is_agent(session_kind=title_prefix),
            run_id=run_id if session_is_agent(session_kind=title_prefix) else None,
        )
        self.console_sessions[session_id] = session
        if session.run_id is not None:
            save_task_active_agent_run(task, title_prefix, session.run_id)
        self._renumber_console_tabs(task)
        for chunk in session.chunks:
            self._insert_console_chunk(session, chunk)
        if self.selected_task is not None and self.selected_task.path == task.path:
            self._show_console_tab(session)
        self._activate_console(session_id)
        threading.Thread(
            target=self._read_console,
            args=(session_id, master_fd),
            daemon=True,
        ).start()
        return session_id

    def close_active_console(self) -> None:
        session = self._active_console()
        if session is not None:
            self.stop_console(session.session_id)

    def stop_console(self, session_id: int) -> None:
        session = self.console_sessions.pop(session_id, None)
        if session is None:
            return
        if self.console_context_text is session.text:
            self.console_context_text = None
            self.console_context_selection = ""
        if session.process.poll() is None:
            session.process.terminate()
        if session.run_id is not None:
            clear_task_active_agent_run(
                self._task_for_path(session.task_path),
                run_id=session.run_id,
                agent=session.kind,
            )
        session.permission_pending = False
        session.permission_signature = None
        session.ignored_permission_signature = None
        session.busy = False
        session.exited = True
        if session.fd is not None:
            try:
                os.close(session.fd)
            except OSError:
                pass
        self._forget_console_tab(session)
        session.frame.destroy()
        if self.active_console_id == session_id:
            self.active_console_id = None
            task = self.selected_task
            if task is not None:
                self._renumber_console_tabs(task)
                next_session = next(iter(self._current_task_console_sessions(task)), None)
                if next_session is not None:
                    self._activate_console(next_session.session_id)
        elif self.selected_task is not None:
            self._renumber_console_tabs(self.selected_task)
        self._update_ai_agent_button_label()
        self._refresh_task_session_indicators()

    def stop_all_consoles(self) -> None:
        for session_id in list(self.console_sessions):
            self.stop_console(session_id)

    def _refresh_console_tabs_for_task(self, task: TaskSummary) -> None:
        for tab_id in self.console_notebook.tabs():
            self.console_notebook.forget(tab_id)
        self._renumber_console_tabs(task)
        for session in self._current_task_console_sessions(task):
            self._show_console_tab(session)
        active = self._active_console()
        if active is not None and active.task_path != task.path:
            self.active_console_id = None

    def _current_task_console_sessions(self, task: TaskSummary) -> list[ConsoleSession]:
        return [
            session
            for session in self.console_sessions.values()
            if session.task_path == task.path
        ]

    def _renumber_console_tabs(self, task: TaskSummary) -> None:
        shell_index = 0
        for session in self._current_task_console_sessions(task):
            if session.kind == "shell":
                shell_index += 1
            session.title = console_tab_title(shell_index, session.kind)
            if str(session.frame) in self.console_notebook.tabs():
                self.console_notebook.tab(session.frame, text=session.title)

    def _show_console_tab(self, session: ConsoleSession) -> None:
        if str(session.frame) not in self.console_notebook.tabs():
            self.console_notebook.add(session.frame, text=session.title)

    def _forget_console_tab(self, session: ConsoleSession) -> None:
        if str(session.frame) in self.console_notebook.tabs():
            self.console_notebook.forget(session.frame)

    def _on_console_session_tab_changed(self, _event: object) -> None:
        session = self._session_for_selected_console_tab()
        if session is not None:
            self.active_console_id = session.session_id

    def _on_console_notebook_double_clicked(self, _event: object) -> str:
        task = self.selected_task
        if task is not None:
            self.new_console(task)
        return "break"

    def _active_console(self) -> ConsoleSession | None:
        session = self._session_for_selected_console_tab()
        if session is not None:
            self.active_console_id = session.session_id
            return session
        if self.active_console_id is None:
            return None
        return self.console_sessions.get(self.active_console_id)

    def _activate_console(self, session_id: int) -> None:
        session = self.console_sessions.get(session_id)
        if session is None:
            return
        self.active_console_id = session_id
        self._show_console_tab(session)
        self.console_notebook.select(session.frame)
        if session.text is not None:
            session.text.see(tk.END)
            session.text.focus_set()
        else:
            session.frame.focus_set()

    def _session_for_selected_console_tab(self) -> ConsoleSession | None:
        try:
            selected = self.console_notebook.select()
        except tk.TclError:
            return None
        if not selected:
            return None
        for session in self.console_sessions.values():
            if str(session.frame) == selected:
                return session
        return None

    def _read_console(self, session_id: int, fd: int) -> None:
        while True:
            try:
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    session = self.console_sessions.get(session_id)
                    if session is None or session.process.poll() is not None:
                        break
                    continue
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            chunks = parse_console_output(data.decode(errors="replace"))
            self.messages.put(("console", (session_id, chunks)))
        session = self.console_sessions.get(session_id)
        if session is None:
            return
        return_code = session.process.poll()
        if return_code is None:
            try:
                return_code = session.process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                return
        session.exited = True
        session.busy = False
        if session.run_id is not None:
            clear_task_active_agent_run(
                self._task_for_path(session.task_path),
                run_id=session.run_id,
                agent=session.kind,
            )
        chunks = [ConsoleChunk(f"\n[process exited with code {return_code}]\n", ())]
        if session_should_clear_pending_permission(
            session_kind=session.kind,
            permission_pending=session.permission_pending,
        ):
            session.permission_pending = False
            session.permission_signature = None
            session.ignored_permission_signature = None
            self._refresh_task_permission_indicators()
        self.messages.put(("console", (session_id, chunks)))

    def _on_console_key(self, event: tk.Event[tk.Misc]) -> str:
        shortcut = _tk_control_shortcut(event)
        if shortcut == "interrupt":
            return self._on_console_interrupt(event)
        if shortcut == "copy":
            return self._on_console_copy(event)
        if shortcut == "v":
            return self._on_console_paste(event)
        session = self._active_console()
        if session is None:
            return "break"
        sequence = self._console_key_sequence(event)
        if sequence and session.fd is not None:
            self._write_to_console(
                session.session_id,
                sequence,
                protect_current_line=sequence != b"\r",
            )
        return "break"

    def _on_console_interrupt(self, _event: tk.Event[tk.Misc]) -> str:
        session = self._active_console()
        if session is not None and session.fd is not None:
            self._write_to_console(session.session_id, b"\x03")
        return "break"

    def _on_console_copy_or_interrupt(self, _event: tk.Event[tk.Misc]) -> str:
        text = self._current_console_text()
        if text is None:
            return "break"
        try:
            text.selection_get()
        except tk.TclError:
            session = self._active_console()
            if session is not None and session.fd is not None:
                self._write_to_console(session.session_id, b"\x03")
            return "break"
        text.event_generate("<<Copy>>")
        return "break"

    def _on_console_copy(self, _event: tk.Event[tk.Misc]) -> str:
        self._copy_console_selection()
        return "break"

    def _copy_console_selection(self) -> None:
        text = self.console_context_text or self._current_console_text()
        if text is None:
            return
        selected_text = self.console_context_selection
        if not selected_text:
            try:
                selected_text = text.selection_get()
            except tk.TclError:
                return
        self.root.clipboard_clear()
        self.root.clipboard_append(selected_text)

    def _on_console_paste(self, _event: tk.Event[tk.Misc]) -> str:
        self._paste_console_clipboard()
        return "break"

    def _paste_console_clipboard(self) -> None:
        session = self._session_for_console_text(self.console_context_text) or self._active_console()
        if session is None:
            return
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        try:
            if session.fd is not None:
                text = console_paste_text(text)
                self._write_to_console(
                    session.session_id,
                    text.encode(),
                    protect_current_line=bool(text),
                )
        except OSError:
            return

    def _on_console_context_menu(self, event: tk.Event[tk.Misc]) -> str:
        widget = event.widget
        if isinstance(widget, tk.Text):
            self.console_context_text = widget
            try:
                self.console_context_selection = widget.selection_get()
            except tk.TclError:
                self.console_context_selection = ""
            widget.focus_set()
            session = self._session_for_console_text(widget)
            if session is not None:
                self._activate_console(session.session_id)
        self.console_context_menu.post(event.x_root, event.y_root)
        return "break"

    def _hide_console_context_menu(self, _event: tk.Event[tk.Misc]) -> None:
        self.console_context_menu.unpost()

    def _session_for_console_text(self, text: tk.Text | None) -> ConsoleSession | None:
        if text is None:
            return None
        for session in self.console_sessions.values():
            if session.text is text:
                return session
        return None

    def _console_key_sequence(self, event: tk.Event[tk.Misc]) -> bytes:
        keysym = event.keysym
        state = event.state
        if _tk_control_shortcut(event) == "d":
            return b"\x04"
        special = {
            "Return": b"\r",
            "BackSpace": b"\x7f",
            "Tab": b"\t",
            "Escape": b"\x1b",
            "Up": b"\x1b[A",
            "Down": b"\x1b[B",
            "Right": b"\x1b[C",
            "Left": b"\x1b[D",
            "Home": b"\x1b[H",
            "End": b"\x1b[F",
            "Delete": b"\x1b[3~",
        }
        if keysym in special:
            return special[keysym]
        char = getattr(event, "char", "")
        return char.encode() if char else b""

    def _require_task(self) -> TaskSummary | None:
        if self.selected_task is None or self._task_is_external_active(self.selected_task):
            messagebox.showinfo(tk_string("no_task_title"), tk_string("no_task_body"))
            return None
        return self.selected_task

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def _append_console_output(self, session_id: int, chunks: list[ConsoleChunk]) -> None:
        session = self.console_sessions.get(session_id)
        if session is None or session.text is None:
            return
        session.chunks.extend(chunks)
        if session_is_agent(session_kind=session.kind):
            if hasattr(self, "tasks") and hasattr(self, "workspace"):
                task = self._task_for_path(session.task_path)
                reconcile_task_agent_run_session(task, self.workspace, session.kind, session.run_id)
            text = self._agent_session_output_tail(session)
            analysis = analyze_agent_output(text)
            if (
                session.ignored_permission_signature is not None
                and analysis.permission_signature != session.ignored_permission_signature
            ):
                session.ignored_permission_signature = None
            update = agent_output_state_update(
                text,
                exited=session.exited,
                permission_pending=session.permission_pending,
            )
            if update.missing_session:
                self._handle_agent_restore_failed(session)
                return
            elif update.permission_requested:
                if analysis.permission_signature != session.ignored_permission_signature:
                    session.permission_signature = analysis.permission_signature
                    session.permission_pending = update.permission_pending
                    session.busy = False
                    self._refresh_task_session_indicators()
                else:
                    self._schedule_agent_idle_after_output(session)
            elif session.exited:
                self._update_ai_agent_button_label()
                self._refresh_task_session_indicators()
            else:
                self._schedule_agent_idle_after_output(session)
        for chunk in chunks:
            self._insert_console_chunk(session, chunk)
        session.text.see(tk.END)

    def _insert_console_chunk(self, session: ConsoleSession, chunk: ConsoleChunk) -> None:
        widget = session.text
        if widget is None:
            return
        for char in chunk.text:
            if char == "\r":
                widget.delete("end-1c linestart", "end-1c")
                self._clear_console_input_floor(session)
                continue
            if char == "\b":
                delete_start = widget.index("end-2c")
                if self._console_can_delete_at(session, delete_start):
                    widget.delete("end-2c", "end-1c")
                continue
            widget.insert(tk.END, char, chunk.tags)
            if char == "\n":
                self._clear_console_input_floor(session)

    def _current_console_text(self) -> tk.Text | None:
        session = self._active_console()
        return session.text if session is not None else None

    def _write_to_console(
        self,
        session_id: int,
        data: bytes,
        protect_current_line: bool = False,
    ) -> None:
        session = self.console_sessions.get(session_id)
        if session is None or session.fd is None:
            return
        submitted_input = b"\r" in data or b"\n" in data or data in {b"\x03", b"\x04"}
        if submitted_input and session_should_clear_pending_permission(
            session_kind=session.kind,
            permission_pending=session.permission_pending,
        ):
            session.ignored_permission_signature = session.permission_signature
            session.permission_signature = None
            session.permission_pending = False
            self._refresh_task_session_indicators()
        if protect_current_line:
            self._set_console_input_floor(session)
        if b"\r" in data or b"\n" in data:
            self._clear_console_input_floor(session)
        try:
            os.write(session.fd, data)
        except OSError:
            return
        if session_is_agent(session_kind=session.kind) and submitted_input:
            self._set_agent_session_busy(session, True)

    def _set_console_input_floor(self, session: ConsoleSession) -> None:
        if session.text is None or session.input_floor_mark is not None:
            return
        mark = f"console_input_floor_{session.session_id}"
        session.text.mark_set(mark, "end-1c")
        session.text.mark_gravity(mark, tk.LEFT)
        session.input_floor_mark = mark

    def _clear_console_input_floor(self, session: ConsoleSession) -> None:
        if session.text is None or session.input_floor_mark is None:
            session.input_floor_mark = None
            return
        session.text.mark_unset(session.input_floor_mark)
        session.input_floor_mark = None

    def _console_can_delete_at(self, session: ConsoleSession, index: str) -> bool:
        widget = session.text
        if widget is None or widget.compare(index, "<", "1.0"):
            return False
        if session.input_floor_mark is not None:
            return bool(widget.compare(index, ">=", session.input_floor_mark))
        return bool(widget.compare(index, ">=", "end-1c linestart"))

    def _set_markdown(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        for chunk in render_markdown_chunks(text):
            widget.insert(tk.END, chunk.text, chunk.tag)
        if widget is getattr(self, "context_text", None):
            self._mark_context_entry_links(widget)
        widget.configure(state=tk.DISABLED)

    def _mark_context_entry_links(self, widget: tk.Text) -> None:
        widget.tag_remove("journal_link", "1.0", tk.END)
        text = widget.get("1.0", tk.END)
        for match in re.finditer(r"(?<![\w/-])#(\d+)\b", text):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            widget.tag_add("journal_link", start, end)

    def _on_context_entry_link_clicked(self, event: tk.Event[tk.Misc]) -> str:
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return "break"
        index = widget.index(f"@{event.x},{event.y}")
        entry_id = _context_entry_reference_at_index(widget, index)
        if entry_id is not None:
            self._scroll_context_text_to_entry(entry_id)
        return "break"

    def _scroll_context_text_to_entry(self, entry_id: int, *, allow_refilter: bool = True) -> bool:
        widget = self.context_text
        text = widget.get("1.0", tk.END)
        for pattern in (rf"(?m)^\| #{entry_id} \[", rf"(?m)^#{entry_id} \["):
            match = re.search(pattern, text)
            if match is None:
                continue
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.start() + len(f'#{entry_id}')}c"
            widget.configure(state=tk.NORMAL)
            widget.tag_remove(tk.SEL, "1.0", tk.END)
            widget.tag_add(tk.SEL, start, end)
            widget.see(start)
            widget.configure(state=tk.DISABLED)
            return True
        if allow_refilter and self._show_context_entry_in_full_journal(entry_id):
            return self._scroll_context_text_to_entry(entry_id, allow_refilter=False)
        return False

    def _show_context_entry_in_full_journal(self, entry_id: int) -> bool:
        return False

    def _configure_text_tags(self, widget: tk.Text) -> None:
        widget.configure(font=self.text_font)
        widget.tag_configure("h1", font=self.h1_font, spacing3=6)
        widget.tag_configure("h2", font=self.h2_font, spacing3=5)
        widget.tag_configure("h3", font=self.h3_font, spacing3=4)
        widget.tag_configure("list", font=self.text_font, lmargin1=24, lmargin2=42, spacing1=1)
        widget.tag_configure("code", font=self.fixed_font, lmargin1=12, lmargin2=12)
        widget.tag_configure("table", font=self.fixed_font)
        widget.tag_configure("paragraph", spacing1=1, spacing3=2)
        widget.tag_configure("journal_link", foreground="#0b5cad", underline=True)

    def _configure_console_tags(self, widget: tk.Text) -> None:
        widget.tag_configure("console_bold", font=self.fixed_font)
        colors = {
            "console_fg_black": "#202124",
            "console_fg_red": "#b3261e",
            "console_fg_green": "#137333",
            "console_fg_yellow": "#b06000",
            "console_fg_blue": "#174ea6",
            "console_fg_magenta": "#9c27b0",
            "console_fg_cyan": "#007b83",
            "console_fg_white": "#f1f3f4",
            "console_fg_bright_black": "#5f6368",
            "console_fg_bright_red": "#d93025",
            "console_fg_bright_green": "#188038",
            "console_fg_bright_yellow": "#f9ab00",
            "console_fg_bright_blue": "#1a73e8",
            "console_fg_bright_magenta": "#c61aff",
            "console_fg_bright_cyan": "#00acc1",
            "console_fg_bright_white": "#ffffff",
        }
        for tag, color in colors.items():
            widget.tag_configure(tag, foreground=color)

    def _set_details_default_split(self) -> None:
        height = self.details_pane.winfo_height()
        if height <= 1:
            self.root.after(50, self._set_details_default_split)
            return
        try:
            self.details_pane.sashpos(0, max(120, height // 4))
        except tk.TclError:
            return

    def _on_details_split_double_clicked(self, _event: tk.Event[tk.Misc]) -> str:
        self._set_details_default_split()
        return "break"

    def _set_main_default_split(self) -> None:
        width = self.main_pane.winfo_width()
        if width <= 1:
            self.root.after(50, self._set_main_default_split)
            return
        try:
            self.main_pane.sashpos(0, max(260, width // 3))
        except tk.TclError:
            return

    def _on_main_split_double_clicked(self, _event: tk.Event[tk.Misc]) -> str:
        self._set_main_default_split()
        return "break"

    def adjust_font_size(self, delta: int) -> None:
        self.text_font_size = max(8, min(28, self.text_font_size + delta))
        self._apply_font_size()
        self._save_settings()

    def _apply_font_size(self) -> None:
        self.text_font.configure(size=self.text_font_size)
        self.fixed_font.configure(size=self.text_font_size)
        self.tree_font.configure(size=self.text_font_size)
        self.button_font.configure(size=self.button_font_size)
        self.ui_font.configure(size=self.button_font_size)
        self.h1_font.configure(size=self.text_font_size + 6)
        self.h2_font.configure(size=self.text_font_size + 4)
        self.h3_font.configure(size=self.text_font_size + 2)
        row_height = self.tree_font.metrics("linespace") + 8
        tab_padding_y = max(4, self.button_font_size // 3)
        self.style.configure("Workspace.Treeview", font=self.tree_font, rowheight=row_height)
        self.style.configure("TButton", font=self.button_font)
        self.style.configure("TLabel", font=self.ui_font)
        self.style.configure("TNotebook.Tab", font=self.ui_font, padding=(8, tab_padding_y))
        self.style.configure("TCombobox", font=self.ui_font)
        self.style.configure("TEntry", font=self.ui_font)
        for widget_name in (
            "description_text",
            "context_text",
        ):
            widget = getattr(self, widget_name, None)
            if isinstance(widget, tk.Text):
                self._configure_text_tags(widget)
        for session in getattr(self, "console_sessions", {}).values():
            if session.text is not None:
                session.text.configure(font=self.fixed_font)
                self._configure_console_tags(session.text)

    def _apply_theme(self) -> None:
        colors = _theme_colors(self.theme)
        self.root.configure(background=colors["background"])
        self.style.configure("TFrame", background=colors["background"])
        self.style.configure("TLabel", background=colors["background"], foreground=colors["foreground"])
        self.style.configure("TNotebook", background=colors["background"])
        self.style.configure("TNotebook.Tab", background=colors["background"], foreground=colors["foreground"])
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", colors["tab_selected_background"])],
            foreground=[("selected", colors["tab_selected_foreground"])],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=colors["text_background"],
            foreground=colors["foreground"],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=colors["text_background"],
            foreground=colors["foreground"],
        )
        self.style.configure(
            "Workspace.Treeview",
            background=colors["text_background"],
            fieldbackground=colors["text_background"],
            foreground=colors["foreground"],
        )
        self.task_tree.tag_configure(
            "agent-session",
            background=colors["agent_session_background"],
            foreground=colors["agent_session_foreground"],
        )
        self.task_tree.tag_configure(
            "agent-external-active",
            background=colors["agent_external_background"],
            foreground=colors["agent_external_foreground"],
        )
        self._refresh_tree_selection_style()
        self.task_context_menu.configure(
            background=colors["text_background"],
            foreground=colors["foreground"],
        )
        self.console_context_menu.configure(
            background=colors["text_background"],
            foreground=colors["foreground"],
        )
        for widget_name in (
            "description_text",
            "context_text",
        ):
            widget = getattr(self, widget_name, None)
            if isinstance(widget, tk.Text):
                self._apply_text_theme(widget, colors)
        for session in getattr(self, "console_sessions", {}).values():
            if session.text is not None:
                self._apply_text_theme(session.text, colors)

    def _apply_text_theme(self, widget: tk.Text, colors: dict[str, str]) -> None:
        widget.configure(
            background=colors["text_background"],
            foreground=colors["foreground"],
            insertbackground=colors["foreground"],
            selectbackground=colors["selection_background"],
            selectforeground=colors["selection_foreground"],
        )

    def _save_settings(self) -> None:
        save_agent_workspace_settings(
            {
                "text_font_size": self.text_font_size,
                "button_font_size": self.button_font_size,
                "theme": self.theme,
                "default_agent": self.default_agent,
                "default_codex_model": self.default_codex_model,
                "default_codex_reasoning": self.default_codex_reasoning,
                "default_claude_model": self.default_claude_model,
                "default_claude_effort": self.default_claude_effort,
                "codex_animations_enabled": self.codex_animations_enabled,
                "claude_animations_enabled": self.claude_animations_enabled,
                "limited_bash_output_tokens": self.limited_bash_output_tokens,
                "inject_task_context_prompt": self.inject_task_context_prompt,
                "task_dictionary_auto_discovery": self.task_dictionary_auto_discovery,
                "task_dictionary_min_occurrences": self.task_dictionary_min_occurrences,
                "task_dictionary_min_saving": self.task_dictionary_min_saving,
                "task_dictionary_min_term_length": self.task_dictionary_min_term_length,
                "task_dictionary_max_term_words": self.task_dictionary_max_term_words,
                "task_dictionary_strip_articles": self.task_dictionary_strip_articles,
                "task_dictionary_preview_text": self.task_dictionary_preview_text,
                "geometry": self.root.geometry(),
            }
        )

    def _is_console_tab_selected(self) -> bool:
        return self.notebook.tab(self.notebook.select(), "text") == "Actions"

    def close(self) -> None:
        if not self._confirm_close_with_running_agents():
            return
        self._save_settings()
        self.stop_all_consoles()
        self.root.destroy()

def ai_agent_task_context_message(task: TaskSummary, workspace: Path) -> str:
    settings = agent_workspace_runtime_settings(load_agent_workspace_settings(), default_font_size=13)
    return ai_agent_task_context_prompt(
        task,
        workspace,
        inject_task_context=settings.inject_task_context_prompt,
    )


def codex_task_context_message(task: TaskSummary, workspace: Path) -> str:
    return ai_agent_task_context_message(task, workspace)


def ai_agent_console_command(
    workspace: Path,
    task: TaskSummary,
    agent: str,
    *,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
    codex_animations_enabled: bool = False,
    claude_animations_enabled: bool = False,
) -> list[str]:
    return build_ai_agent_console_command(
        workspace,
        ai_agent_task_context_message(task, workspace),
        agent,
        codex_executable=_codex_executable(),
        claude_executable=_claude_executable(),
        resume=resume,
        resume_session_id=resume_session_id,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_animations_enabled=codex_animations_enabled,
        claude_animations_enabled=claude_animations_enabled,
    )


def codex_console_command(
    workspace: Path,
    task: TaskSummary,
    *,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
    codex_animations_enabled: bool = False,
) -> list[str]:
    return build_ai_agent_console_command(
        workspace,
        ai_agent_task_context_message(task, workspace),
        "codex",
        codex_executable=_codex_executable(),
        claude_executable=_claude_executable(),
        resume=resume,
        resume_session_id=resume_session_id,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_animations_enabled=codex_animations_enabled,
    )


def embedded_terminal_command(
    socket_id: int,
    cwd: Path,
    command: list[str],
    font_size: int,
    theme: str,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "agent_tools.agent_workspace.components.vte_terminal.api",
        "--socket-id",
        str(socket_id),
        "--cwd",
        str(cwd),
        "--font-size",
        str(font_size),
        "--theme",
        theme,
        "--",
        *command,
    ]


def console_paste_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    return " ".join(line.strip() for line in lines if line.strip())


def _context_entry_reference_at_index(widget: tk.Text, index: str) -> int | None:
    text = widget.get("1.0", tk.END)
    offset_count = widget.count("1.0", index, "chars")
    if not offset_count:
        return None
    offset = int(offset_count[0])
    for match in re.finditer(r"(?<![\w/-])#(\d+)\b", text):
        if match.start() <= offset <= match.end():
            return int(match.group(1))
    return None


def _tk_control_shortcut(event: tk.Event[tk.Misc]) -> str | None:
    state = int(getattr(event, "state", 0))
    if not (state & 0x4):
        return None
    shift = bool(state & 0x1)
    keycode = getattr(event, "keycode", None)
    if keycode in {54}:
        return "copy" if shift else "interrupt"
    if keycode in {55}:
        return "v"
    if keycode in {40}:
        return "d"
    keysym = str(getattr(event, "keysym", "")).casefold()
    char = str(getattr(event, "char", "")).casefold()
    for value in (keysym, char):
        if value in {"c", "с", "\x03", "cyrillic_es"}:
            return "copy" if shift else "interrupt"
        if value in {"v", "м", "\x16", "cyrillic_em"}:
            return "v"
        if value in {"d", "в", "\x04", "cyrillic_ve"}:
            return "d"
    return None


def _set_pty_size(fd: int, rows: int, columns: int) -> None:
    try:
        size = struct.pack("HHHH", rows, columns, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
    except OSError:
        return


def _make_controlling_terminal(fd: int) -> None:
    os.setsid()
    try:
        fcntl.ioctl(fd, termios.TIOCSCTTY, 0)
    except OSError:
        return


def console_tab_title(index: int, kind: str) -> str:
    if session_is_agent(session_kind=kind):
        return agent_label(kind)
    return f"{kind} {index}"


def _theme_colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "background": "#202124",
            "foreground": "#e8eaed",
            "text_background": "#111315",
            "selection_background": "#315f86",
            "selection_foreground": "#ffffff",
            "agent_session_background": "#4b3713",
            "agent_session_foreground": "#ffe6a3",
            "agent_session_selected_background": "#704d12",
            "agent_session_selected_foreground": "#fff2c4",
            "agent_external_background": "#34383d",
            "agent_external_foreground": "#a8b0ba",
            "tab_selected_background": "#dfe1e5",
            "tab_selected_foreground": "#202124",
        }
    return {
        "background": "#f4f4f4",
        "foreground": "#202124",
        "text_background": "#ffffff",
        "selection_background": "#4d708f",
        "selection_foreground": "#ffffff",
        "agent_session_background": "#fff1c2",
        "agent_session_foreground": "#5c3b00",
        "agent_session_selected_background": "#f4c45f",
        "agent_session_selected_foreground": "#2f2100",
        "agent_external_background": "#e0e0e0",
        "agent_external_foreground": "#5f6368",
        "tab_selected_background": "#ffffff",
        "tab_selected_foreground": "#202124",
    }


def _transcript_header(label: str, detail: str | None = None) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    suffix = f" [{detail}]" if detail else ""
    return f"## {label}{suffix} at {timestamp}\n\n"


def open_path(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        command = ["open", str(path)]
    elif system == "Windows":
        command = ["explorer", str(path)]
    else:
        command = ["xdg-open", str(path)]
    subprocess.Popen(command, cwd=str(path if path.is_dir() else path.parent))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the local workspace task dashboard.")
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace root. Default: current directory.",
    )
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    install_agent_workspace_exception_logger(workspace, "tk")
    root = tk.Tk()

    def report_callback_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: object,
    ) -> None:
        log_agent_workspace_exception(workspace, "tk-callback", exc_type, exc_value, exc_traceback)

    root.report_callback_exception = report_callback_exception  # type: ignore[method-assign]
    AgentWorkspace(root, workspace)
    root.mainloop()
    return 0
