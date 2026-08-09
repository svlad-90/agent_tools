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
import select
import shlex
import shutil
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
from .core import TaskAction
from .core import TaskSummary
from .core import WORKSPACE_GUI_THEMES
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import load_task_actions
from .core import load_workspace_gui_settings
from .core import parse_console_output
from .core import read_task_file
from .core import render_markdown_chunks
from .core import save_workspace_gui_settings


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


class WorkspaceGui:
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
        self.next_console_id = 1
        default_font_size = int(tkfont.nametofont("TkDefaultFont").cget("size"))
        settings = load_workspace_gui_settings()
        self.text_font_size = int(settings.get("text_font_size", default_font_size))
        self.button_font_size = int(settings.get("button_font_size", default_font_size))
        self.theme = str(settings.get("theme", "light"))
        self.window_geometry = str(settings.get("geometry", "1180x760"))
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

        self.root.title(f"Workspace GUI - {self.workspace}")
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
        self.task_tree.bind("<Button-3>", self._on_task_context_menu)
        self.task_tree.bind("<Button-2>", self._on_task_context_menu)
        self.task_context_menu = tk.Menu(self.root, tearoff=False)
        self.task_context_menu.add_command(label="Open Task", command=self.open_task)
        self.task_context_menu.add_command(label="Open dev/", command=self.open_dev)

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
        pane = ttk.PanedWindow(frame, orient=tk.VERTICAL)
        pane.pack(fill=tk.BOTH, expand=True)

        actions_frame = ttk.Frame(pane)
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
        ttk.Button(toolbar, text="Git status", command=self.run_selected_git_status).pack(
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

        console_frame = ttk.Frame(pane)
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
        ttk.Button(console_toolbar, text="Run codex", command=self.run_codex_console).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        self.console_notebook = ttk.Notebook(console_frame)
        self.console_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.console_notebook.bind("<<NotebookTabChanged>>", self._on_console_session_tab_changed)
        pane.add(actions_frame, weight=2)
        pane.add(console_frame, weight=1)
        self.notebook.add(frame, text="Actions")

    def _create_console_text(self, parent: ttk.Frame) -> tk.Text:
        text = tk.Text(parent, wrap=tk.WORD, undo=False, font=self.fixed_font)
        text.bind("<Key>", self._on_console_key)
        text.bind("<Button-1>", lambda _event: text.focus_set())
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
                text=task.name,
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
        if self._is_console_tab_selected():
            self.activate_console_for_task(task)

    def _on_task_double_clicked(self, _event: object) -> None:
        self.open_task()

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
        window.title("Workspace GUI settings")
        window.transient(self.root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        text_size_var = tk.IntVar(value=self.text_font_size)
        button_size_var = tk.IntVar(value=self.button_font_size)
        theme_var = tk.StringVar(value=self.theme)

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
            values=WORKSPACE_GUI_THEMES,
            textvariable=theme_var,
            state="readonly",
            width=10,
            font=self.ui_font,
        )
        theme_combo.grid(row=2, column=1, sticky=tk.W, pady=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(
            buttons,
            text="Apply",
            command=lambda: self._apply_settings_values(text_size_var, button_size_var, theme_var),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            buttons,
            text="OK",
            command=lambda: self._close_settings(window, text_size_var, button_size_var, theme_var),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side=tk.LEFT, padx=2)

    def _close_settings(
        self,
        window: tk.Toplevel,
        text_size_var: tk.IntVar,
        button_size_var: tk.IntVar,
        theme_var: tk.StringVar,
    ) -> None:
        self._apply_settings_values(text_size_var, button_size_var, theme_var)
        window.destroy()

    def _apply_settings_values(
        self,
        text_size_var: tk.IntVar,
        button_size_var: tk.IntVar,
        theme_var: tk.StringVar,
    ) -> None:
        try:
            text_font_size = text_size_var.get()
            button_font_size = button_size_var.get()
        except tk.TclError:
            return
        theme = theme_var.get()
        self.text_font_size = max(8, min(28, text_font_size))
        self.button_font_size = max(8, min(28, button_font_size))
        self.theme = theme if theme in WORKSPACE_GUI_THEMES else "light"
        self._apply_font_size()
        self._apply_theme()
        self._save_settings()

    def run_selected_task_check(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._send_command_to_task_console(task, task_check_shell_command(self.workspace, task))

    def run_selected_git_status(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._ensure_git_repos_loaded(task)
        repo = self._selected_git_repo()
        if repo is None:
            return
        self._send_command_to_task_console(task, shlex.join(["git", "-C", str(repo), "status", "--short", "--branch"]))

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
        self.git_repo_options = find_dev_git_repos(task)
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
        return

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
        session = self._writable_console_for_task(task)
        if session is None or session.fd is None:
            messagebox.showerror("Console", "Could not open a writable console for this task.")
            return
        self._activate_console(session.session_id)
        try:
            os.write(session.fd, command.encode() + b"\r")
        except OSError as error:
            messagebox.showerror("Console", f"Could not write to console: {error}")

    def _writable_console_for_task(self, task: TaskSummary) -> ConsoleSession | None:
        active = self._active_console()
        if active is not None and active.task_path == task.path and active.fd is not None:
            if active.process.poll() is None:
                return active
        for session in self._current_task_console_sessions(task):
            if session.fd is not None and session.process.poll() is None:
                return session
        session_id = self.new_console(task)
        if session_id is None:
            return None
        return self.console_sessions.get(session_id)

    def run_codex_console(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._send_command_to_task_console(task, shlex.join(codex_console_command(self.workspace, task)))

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
            self._insert_console_chunk(text, chunk)
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
        if session.process.poll() is None:
            session.process.terminate()
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
        for index, session in enumerate(self._current_task_console_sessions(task), start=1):
            session.title = console_tab_title(index, session.kind)
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
        chunks = [ConsoleChunk(f"\n[process exited with code {return_code}]\n", ())]
        self.messages.put(("console", (session_id, chunks)))

    def _on_console_key(self, event: tk.Event[tk.Misc]) -> str:
        if event.state & 0x4 and event.keysym.lower() == "c":
            return self._on_console_copy_or_interrupt(event)
        if event.state & 0x4 and event.keysym.lower() == "v":
            return self._on_console_paste(event)
        session = self._active_console()
        if session is None:
            return "break"
        sequence = self._console_key_sequence(event)
        if sequence and session.fd is not None:
            try:
                os.write(session.fd, sequence)
            except OSError:
                return "break"
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
        text = self._current_console_text()
        if text is not None:
            text.event_generate("<<Copy>>")

    def _on_console_paste(self, _event: tk.Event[tk.Misc]) -> str:
        self._paste_console_clipboard()
        return "break"

    def _paste_console_clipboard(self) -> None:
        session = self._active_console()
        if session is None:
            return
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return
        try:
            if session.fd is not None:
                os.write(session.fd, text.encode())
        except OSError:
            return

    def _console_key_sequence(self, event: tk.Event[tk.Misc]) -> bytes:
        keysym = event.keysym
        state = event.state
        if state & 0x4 and keysym.lower() == "d":
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
        for chunk in chunks:
            self._insert_console_chunk(session.text, chunk)
        session.text.see(tk.END)

    def _insert_console_chunk(self, widget: tk.Text, chunk: ConsoleChunk) -> None:
        for char in chunk.text:
            if char == "\b":
                if widget.index(tk.END) != "2.0":
                    widget.delete("end-2c", "end-1c")
                continue
            widget.insert(tk.END, char, chunk.tags)

    def _current_console_text(self) -> tk.Text | None:
        session = self._active_console()
        return session.text if session is not None else None

    def _write_to_console(self, session_id: int, data: bytes) -> None:
        session = self.console_sessions.get(session_id)
        if session is None or session.fd is None:
            return
        try:
            os.write(session.fd, data)
        except OSError:
            return

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
        self.style.map(
            "Workspace.Treeview",
            background=[("selected", colors["selection_background"])],
            foreground=[("selected", colors["selection_foreground"])],
        )
        self.task_context_menu.configure(
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
        save_workspace_gui_settings(
            {
                "text_font_size": self.text_font_size,
                "button_font_size": self.button_font_size,
                "theme": self.theme,
                "geometry": self.root.geometry(),
            }
        )

    def _is_console_tab_selected(self) -> bool:
        return self.notebook.tab(self.notebook.select(), "text") == "Actions"

    def close(self) -> None:
        self._save_settings()
        self.stop_all_consoles()
        self.root.destroy()


def render_git_status(repo: Path) -> str:
    status = git_status(repo)
    lines = [str(repo), status.branch_line]
    if status.error:
        lines.append(f"error: {status.error}")
    elif status.changes:
        lines.extend(status.changes)
    else:
        lines.append("clean")
    return "\n".join(lines) + "\n"


def codex_task_context_message(task: TaskSummary, workspace: Path) -> str:
    return (
        f"We are working in workspace task `{task.name}`. "
        f"Workspace: {workspace}. "
        f"Task directory: {task.path}. "
        "Before changing files, read that task's TASK_DESCRIPTION.md and "
        "TASK_CONTEXT.md and treat them as the active task context."
    )


def codex_console_command(workspace: Path, task: TaskSummary) -> list[str]:
    return [
        _codex_executable(),
        "exec",
        "--cd",
        str(workspace),
        "--color",
        "never",
        codex_task_context_message(task, workspace),
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
    return f"{index} {kind}"


def _theme_colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "background": "#202124",
            "foreground": "#e8eaed",
            "text_background": "#111315",
            "selection_background": "#315f86",
            "selection_foreground": "#ffffff",
            "tab_selected_background": "#dfe1e5",
            "tab_selected_foreground": "#202124",
        }
    return {
        "background": "#f4f4f4",
        "foreground": "#202124",
        "text_background": "#ffffff",
        "selection_background": "#4d708f",
        "selection_foreground": "#ffffff",
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
    WorkspaceGui(root, Path(args.workspace))
    root.mainloop()
    return 0
