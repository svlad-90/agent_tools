from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
import fcntl
import json
import os
import platform
import pty
import queue
import select
import shlex
import subprocess
import struct
import termios
import threading
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk

from .core import TASK_CONTEXT_BUDGET
from .core import ConsoleChunk
from .core import PAF_HIDE_TASK_ENV_VAR
from .core import TASK_ACTION_LOGS_DIR
from .core import AgentModelSettings
from .core import TaskAction
from .core import TaskSummary
from .core import AGENT_WORKSPACE_AGENTS
from .core import AGENT_WORKSPACE_CLAUDE_MODELS
from .core import AGENT_WORKSPACE_REASONING_EFFORTS
from .core import AGENT_WORKSPACE_THEMES
from .core import AGENT_PERMISSION_MARKER
from .core import agent_executable
from .core import agent_install_command
from .core import agent_label
from .core import ai_agent_launch_state_for_selection
from .core import ai_agent_model_settings
from .core import ai_agent_switch_decision
from .core import ai_agent_task_context_prompt
from .core import agent_workspace_runtime_settings
from .core import agent_output_state_update
from .core import build_ai_agent_console_command
from .core import clear_task_agent_session
from .core import codex_model_choices
from .core import discover_tasks
from .core import load_task_agent
from .core import load_task_actions
from .core import load_agent_workspace_settings
from .core import model_choices_with_current
from .core import normalize_agent
from .core import parse_console_output
from .core import prepare_ai_agent_launch_command
from .core import read_task_file
from .core import render_markdown_chunks
from .core import reset_task_agent_session
from .core import save_agent_workspace_settings
from .core import save_task_agent
from .core import save_task_agent_session
from .core import session_marks_task_pending_permission
from .core import session_is_agent
from .core import session_is_running_agent
from .core import session_should_clear_pending_permission
from .core import task_action_log_basename
from .core import task_for_path
from .core import task_selected_agent_has_resumable_state


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


_AI_AGENT_BUTTON_LABELS = {
    "run_ai_agent": "Запустить ИИ агента",
    "restore_ai_agent_session": "Восстановить сессию ИИ агента",
    "ai_agent_running": "ИИ агент запущен",
}


class AgentWorkspace:
    def __init__(self, root: tk.Tk, workspace: Path) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.task_actions: list[TaskAction] = []
        self.git_repo_options: list[Path] = []
        self.git_repos_loaded_for: Path | None = None
        self.console_sessions: dict[int, ConsoleSession] = {}
        self.active_console_id: int | None = None
        self.console_context_text: tk.Text | None = None
        self.console_context_selection = ""
        self.next_console_id = 1
        self._updating_agent_selection = False
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
        self._apply_font_size()
        self._build_ui()
        self._apply_font_size()
        self._apply_theme()
        self.refresh_tasks()
        self._poll_messages()

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
        columns = ("details",)
        self.task_tree = ttk.Treeview(
            left,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            style="Workspace.Treeview",
        )
        self.task_tree.heading("#0", text="Task")
        self.task_tree.heading("details", text="Task Details")
        self.task_tree.column("#0", width=260)
        self.task_tree.column("details", width=270)
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)
        self.task_tree.bind("<Double-1>", self._on_task_double_clicked)
        self.task_tree.bind("<Return>", self._ignore_task_tree_keyboard_activation)
        self.task_tree.bind("<KP_Enter>", self._ignore_task_tree_keyboard_activation)
        self.task_tree.bind("<space>", self._ignore_task_tree_keyboard_activation)
        self.task_tree.bind("<Button-3>", self._on_task_context_menu)
        self.task_tree.bind("<Button-2>", self._on_task_context_menu)
        self.task_context_menu = tk.Menu(self.root, tearoff=False)
        self.task_context_menu.add_command(label="Open Task", command=self.open_task)
        self.task_context_menu.add_command(label="Open dev/", command=self.open_dev)
        self.console_context_menu = tk.Menu(self.root, tearoff=False)
        self.console_context_menu.add_command(label="Copy", command=self._copy_console_selection)
        self.console_context_menu.add_command(label="Paste", command=self._paste_console_clipboard)

        right = ttk.Frame(main, padding=6)
        main.add(right, weight=3)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.description_text, self.context_text = self._add_details_tab()
        self._add_actions_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)
        self.root.after_idle(self._set_main_default_split)

    def _add_details_tab(self) -> tuple[tk.Text, tk.Text]:
        frame = ttk.Frame(self.notebook)
        details = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        self.details_pane = details
        details.bind("<Double-Button-1>", self._on_details_split_double_clicked)
        details.pack(fill=tk.BOTH, expand=True)
        description_text = self._add_labeled_text_pane(details, "Description")
        context_text = self._add_labeled_text_pane(details, "Context")
        self.notebook.add(frame, text="Details")
        self.root.after_idle(self._set_details_default_split)
        return description_text, context_text

    def _add_labeled_text_pane(self, parent: ttk.PanedWindow, title: str) -> tk.Text:
        frame = ttk.Frame(parent, padding=(0, 0, 0, 4))
        ttk.Label(frame, text=title).pack(side=tk.TOP, anchor=tk.W, padx=2, pady=(0, 2))
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
        self.git_repo_var = tk.StringVar(value="")
        self.git_repo_combo = ttk.Combobox(
            toolbar,
            textvariable=self.git_repo_var,
            state="readonly",
            width=46,
        )
        self.git_repo_combo.pack(side=tk.LEFT, padx=2, pady=2)
        self.git_repo_combo.bind("<<ComboboxSelected>>", self._on_git_repo_selected)
        ttk.Button(toolbar, text="Scan repos", command=self.scan_selected_git_repos).pack(
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
        ttk.Button(console_toolbar, text="New", command=self.new_console).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        ttk.Button(console_toolbar, text="Close", command=self.close_active_console).pack(
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
            text="Запустить ИИ агента",
            command=self.run_ai_agent_console,
        )
        self.run_ai_agent_button.pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.reset_ai_agent_button = ttk.Button(
            console_toolbar,
            text="Сбросить сессию",
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
        self.task_tree.delete(*self.task_tree.get_children())
        task_iids: dict[str, str] = {}
        for index, task in enumerate(self.tasks):
            flags = []
            if not task.has_description:
                flags.append("missing desc")
            if not task.has_context:
                flags.append("missing context")
            if task.context_over_budget:
                flags.append(f"context > {TASK_CONTEXT_BUDGET}")
            details = f"desc {task.description_tokens}, context {task.context_tokens}"
            if flags:
                details = f"{details}, {', '.join(flags)}"
            self.task_tree.insert(
                "",
                tk.END,
                iid=str(index),
                text=self._task_label(task),
                tags=self._task_tags(task),
                values=(details,),
            )
            task_iids[task.name] = str(index)
        over_budget = sum(1 for task in self.tasks if task.context_over_budget)
        self.summary_var.set(f"{len(self.tasks)} tasks, {over_budget} over context budget")
        if self.tasks:
            iid = task_iids.get(selected_name or "", "0")
            self.task_tree.selection_set(iid)
            self.task_tree.focus(iid)
            self.task_tree.see(iid)
        else:
            self.selected_task = None

    def _on_task_selected(self, _event: object) -> None:
        selection = self.task_tree.selection()
        if not selection:
            return
        task = self.tasks[int(selection[0])]
        self.selected_task = task
        self._set_markdown(self.description_text, read_task_file(task, "TASK_DESCRIPTION.md"))
        self._set_markdown(self.context_text, read_task_file(task, "TASK_CONTEXT.md"))
        self._reset_actions_tab(task)
        action_errors = self._load_task_action_buttons(task)
        messages = []
        if action_errors:
            messages.append(action_errors.strip())
        self.actions_message_var.set("\n".join(messages))
        selected_agent = load_task_agent(task, self.default_agent)
        self.agent_var.set(selected_agent)
        self._update_ai_agent_button_label()
        self._refresh_tree_selection_style()
        if self._is_console_tab_selected():
            self.activate_console_for_task(task)

    def _on_task_double_clicked(self, _event: object) -> None:
        self.open_task()

    def _ignore_task_tree_keyboard_activation(self, _event: object) -> str:
        return "break"

    def _on_task_context_menu(self, event: tk.Event[tk.Misc]) -> None:
        row = self.task_tree.identify_row(event.y)
        if not row:
            return
        self.task_tree.selection_set(row)
        self.task_tree.focus(row)
        self._on_task_selected(event)
        self.task_context_menu.tk_popup(event.x_root, event.y_root)
        self.task_context_menu.grab_release()

    def _on_notebook_tab_changed(self, _event: object) -> None:
        if self.selected_task is not None and self._is_console_tab_selected():
            self.activate_console_for_task(self.selected_task)

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
            messagebox.showinfo("Missing dev/", f"{dev} does not exist")

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
        codex_model_values = model_choices_with_current(codex_model_choices(), self.default_codex_model)
        claude_model_values = model_choices_with_current(AGENT_WORKSPACE_CLAUDE_MODELS, self.default_claude_model)

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
        ttk.Label(frame, text="Codex model").grid(row=4, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            frame,
            values=codex_model_values,
            textvariable=codex_model_var,
            state="readonly",
            width=22,
            font=self.ui_font,
        ).grid(
            row=4,
            column=1,
            sticky=tk.W,
            pady=4,
        )
        ttk.Label(frame, text="Codex reasoning").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            frame,
            values=AGENT_WORKSPACE_REASONING_EFFORTS,
            textvariable=codex_reasoning_var,
            state="readonly",
            width=10,
            font=self.ui_font,
        ).grid(row=5, column=1, sticky=tk.W, pady=4)
        ttk.Label(frame, text="Claude model").grid(row=6, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            frame,
            values=claude_model_values,
            textvariable=claude_model_var,
            state="readonly",
            width=22,
            font=self.ui_font,
        ).grid(
            row=6,
            column=1,
            sticky=tk.W,
            pady=4,
        )
        ttk.Label(frame, text="Claude effort").grid(row=7, column=0, sticky=tk.W, pady=4)
        ttk.Combobox(
            frame,
            values=AGENT_WORKSPACE_REASONING_EFFORTS,
            textvariable=claude_effort_var,
            state="readonly",
            width=10,
            font=self.ui_font,
        ).grid(row=7, column=1, sticky=tk.W, pady=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=8, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(
            buttons,
            text="Apply",
            command=lambda: self._apply_settings_values(
                text_size_var,
                button_size_var,
                theme_var,
                default_agent_var,
                codex_model_var,
                codex_reasoning_var,
                claude_model_var,
                claude_effort_var,
            ),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            buttons,
            text="OK",
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
            ),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side=tk.LEFT, padx=2)

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
    ) -> None:
        try:
            text_font_size = text_size_var.get()
            button_font_size = button_size_var.get()
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

    def scan_selected_git_repos(self) -> None:
        task = self._require_task()
        if task is not None:
            self._ensure_git_repos_loaded(task)

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is None:
            return
        self._send_command_to_task_console(task, task_action_shell_command(action))

    def reload_selected_task_actions(self) -> None:
        task = self._require_task()
        if task is None:
            return
        action_errors = self._load_task_action_buttons(task)
        self.actions_message_var.set(action_errors.strip())

    def _reset_actions_tab(self, task: TaskSummary) -> None:
        self.git_repo_options = []
        self.git_repos_loaded_for = None
        self.git_repo_combo.configure(values=(), state=tk.DISABLED)
        self.git_repo_var.set("")
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

    def _ensure_git_repos_loaded(self, task: TaskSummary) -> None:
        if self.git_repos_loaded_for == task.path:
            return
        self._refresh_git_repos(task)

    def _refresh_git_repos(self, task: TaskSummary) -> None:
        completed = subprocess.run(
            [
                sys_executable(),
                "-m",
                "agent_tools.tools.agent_workspace.actions",
                "scan-repos",
                "--workspace",
                str(self.workspace),
                "--task",
                str(task.path),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            self.actions_message_var.set((completed.stderr or completed.stdout).strip())
            return
        self.git_repo_options = [Path(path) for path in json.loads(completed.stdout)]
        self.git_repos_loaded_for = task.path
        labels = [self._repo_label(task, repo) for repo in self.git_repo_options]
        self.git_repo_combo.configure(values=labels)
        if not labels:
            self.git_repo_var.set("")
            self.git_repo_combo.configure(state=tk.DISABLED)
            self.actions_message_var.set("No git repositories found under dev/.")
            return
        self.git_repo_combo.configure(state="readonly")
        self.git_repo_var.set(labels[0])

    def _on_git_repo_selected(self, _event: object) -> None:
        task = self.selected_task
        repo = self._current_git_repo_without_dialog()
        session = self._active_console()
        if task is None or repo is None or session is None:
            return
        if session.kind != "shell" or session.task_path != task.path:
            return
        self._write_to_console(
            session.session_id,
            f"{shlex.join(['cd', str(repo)])}\n".encode(),
            protect_current_line=True,
        )

    def _selected_git_repo(self) -> Path | None:
        if not self.git_repo_options:
            messagebox.showinfo("No repository", "No git repositories found under dev/.")
            return None
        return self._current_git_repo_without_dialog()

    def _current_git_repo_without_dialog(self) -> Path | None:
        if not self.git_repo_options:
            return None
        index = self.git_repo_combo.current()
        if index < 0 or index >= len(self.git_repo_options):
            index = 0
        return self.git_repo_options[index]

    def _repo_label(self, task: TaskSummary, repo: Path) -> str:
        try:
            return str(repo.relative_to(task.path / "dev"))
        except ValueError:
            return str(repo)

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
            messagebox.showerror("Console", "Could not open a writable console for this task.")
            return
        self._activate_console(session.session_id)

        def write_command() -> None:
            if session.fd is None or session.process.poll() is not None:
                return
            try:
                os.write(session.fd, command.encode() + b"\r")
            except OSError as error:
                messagebox.showerror("Console", f"Could not write to console: {error}")

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
        return task_selected_agent_has_resumable_state(task, self.workspace, self.default_agent)

    def _task_for_path(self, path: Path) -> TaskSummary:
        return task_for_path(self.tasks, path)

    def _task_tags(self, task: TaskSummary) -> tuple[str, ...]:
        if self._task_has_resumable_agent_session(task):
            return ("agent-session",)
        return ()

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
        if self._task_has_pending_agent_permission(task):
            return f"{AGENT_PERMISSION_MARKER} {task.name}"
        return task.name

    def _refresh_task_permission_indicators(self) -> None:
        for index, task in enumerate(self.tasks):
            iid = str(index)
            if self.task_tree.exists(iid):
                self.task_tree.item(iid, text=self._task_label(task))

    def _refresh_task_session_indicators(self) -> None:
        for index, task in enumerate(self.tasks):
            iid = str(index)
            if self.task_tree.exists(iid):
                self.task_tree.item(iid, tags=self._task_tags(task))
        self._refresh_tree_selection_style()

    def _refresh_tree_selection_style(self) -> None:
        colors = _theme_colors(self.theme)
        selected_task_has_session = (
            self.selected_task is not None
            and self._task_has_resumable_agent_session(self.selected_task)
        )
        if selected_task_has_session:
            background = colors["agent_session_selected_background"]
            foreground = colors["agent_session_selected_foreground"]
        else:
            background = colors["selection_background"]
            foreground = colors["selection_foreground"]
        self.style.map(
            "Workspace.Treeview",
            background=[("selected", background)],
            foreground=[("selected", foreground)],
        )

    def _set_agent_selection(self, agent: str) -> None:
        self._updating_agent_selection = True
        try:
            self.agent_var.set(normalize_agent(agent))
        finally:
            self._updating_agent_selection = False

    def _confirm_agent_switch(self, current_agent: str, next_agent: str) -> bool:
        return messagebox.askyesno(
            "Switch AI agent?",
            (
                f"{agent_label(current_agent)} is already running for this task.\n\n"
                f"Confirming will close the current session and start {agent_label(next_agent)} "
                "with the same task context."
            ),
        )

    def _ensure_agent_installed(self, agent: str) -> bool:
        if agent_executable(agent):
            return True
        install_command = agent_install_command(agent)
        message = (
            f"{agent_label(agent)} is not installed or is not available in PATH.\n\n"
            f"Install it, then restart Agent Workspace or update PATH.\n\n"
            f"Suggested install command:\n{install_command}"
        )
        messagebox.showerror("AI agent is not installed", message)
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
        return messagebox.askyesno(
            "Close Agent Workspace?",
            (
                "There are running AI agent terminals.\n\n"
                f"{labels}\n\n"
                "Closing Agent Workspace will stop the local agent processes. "
                "Resumable conversations can be restored on the next launch. Continue?"
            ),
        )

    def run_codex_console(self) -> None:
        self._set_agent_selection("codex")
        self.run_ai_agent_console()

    def _start_embedded_terminal_process(
        self,
        task: TaskSummary,
        command: list[str],
        cwd: Path,
        title_prefix: str,
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
            close_fds=True,
        )
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
        )
        self.console_sessions[session_id] = session
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
    ) -> int | None:
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as error:
            messagebox.showerror("Console", f"Could not start console: {error}")
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
            messagebox.showerror("Console", f"Could not start {command[0]}: {error}")
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
        )
        self.console_sessions[session_id] = session
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
        session.permission_pending = False
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
        self._refresh_task_permission_indicators()

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
        chunks = [ConsoleChunk(f"\n[process exited with code {return_code}]\n", ())]
        if session_should_clear_pending_permission(
            session_kind=session.kind,
            permission_pending=session.permission_pending,
        ):
            session.permission_pending = False
            self._refresh_task_permission_indicators()
        self.messages.put(("console", (session_id, chunks)))

    def _on_console_key(self, event: tk.Event[tk.Misc]) -> str:
        shortcut = _tk_control_shortcut(event)
        if shortcut == "c":
            return self._on_console_copy_or_interrupt(event)
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

    def _on_console_copy_or_interrupt(self, _event: tk.Event[tk.Misc]) -> str:
        text = self._current_console_text()
        if text is None:
            return "break"
        try:
            text.selection_get()
        except tk.TclError:
            session = self._active_console()
            if session is not None and session.fd is not None:
                try:
                    os.write(session.fd, b"\x03")
                except OSError:
                    return "break"
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
        if self.selected_task is None:
            messagebox.showinfo("No task", "Select a task first")
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
            text = "".join(chunk.text for chunk in chunks)
            update = agent_output_state_update(
                text,
                exited=session.exited,
                permission_pending=session.permission_pending,
            )
            if update.missing_session:
                session.exited = update.exited
                session.permission_pending = update.permission_pending
                clear_task_agent_session(self._task_for_path(session.task_path), session.kind)
                self._update_ai_agent_button_label()
                self._refresh_task_session_indicators()
                self._refresh_tree_selection_style()
            elif update.permission_requested:
                session.permission_pending = update.permission_pending
                self._refresh_task_permission_indicators()
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
        if session_should_clear_pending_permission(
            session_kind=session.kind,
            permission_pending=session.permission_pending,
        ):
            session.permission_pending = False
            self._refresh_task_permission_indicators()
        if protect_current_line:
            self._set_console_input_floor(session)
        if b"\r" in data or b"\n" in data:
            self._clear_console_input_floor(session)
        try:
            os.write(session.fd, data)
        except OSError:
            return

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
        widget.configure(state=tk.DISABLED)

    def _configure_text_tags(self, widget: tk.Text) -> None:
        widget.configure(font=self.text_font)
        widget.tag_configure("h1", font=self.h1_font, spacing3=6)
        widget.tag_configure("h2", font=self.h2_font, spacing3=5)
        widget.tag_configure("h3", font=self.h3_font, spacing3=4)
        widget.tag_configure("list", font=self.text_font, lmargin1=24, lmargin2=42, spacing1=1)
        widget.tag_configure("code", font=self.fixed_font, lmargin1=12, lmargin2=12)
        widget.tag_configure("table", font=self.fixed_font)
        widget.tag_configure("paragraph", spacing1=1, spacing3=2)

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
    return ai_agent_task_context_prompt(task, workspace)


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
    )


def codex_console_command(
    workspace: Path,
    task: TaskSummary,
    *,
    resume: bool = False,
    resume_session_id: str | None = None,
    model: str = "",
    reasoning_effort: str = "",
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
        "agent_tools.tools.agent_workspace.vte_terminal",
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


def console_paste_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    return " ".join(line.strip() for line in lines if line.strip())


def sys_executable() -> str:
    return sys.executable or "python3"


def _codex_executable() -> str:
    return agent_executable("codex") or "codex"


def _claude_executable() -> str:
    return agent_executable("claude") or "claude"


def _tk_control_shortcut(event: tk.Event[tk.Misc]) -> str | None:
    if not (int(getattr(event, "state", 0)) & 0x4):
        return None
    keycode = getattr(event, "keycode", None)
    if keycode in {54}:
        return "c"
    if keycode in {55}:
        return "v"
    if keycode in {40}:
        return "d"
    keysym = str(getattr(event, "keysym", "")).casefold()
    char = str(getattr(event, "char", "")).casefold()
    for value in (keysym, char):
        if value in {"c", "с", "\x03", "cyrillic_es"}:
            return "c"
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

    root = tk.Tk()
    AgentWorkspace(root, Path(args.workspace))
    root.mainloop()
    return 0
