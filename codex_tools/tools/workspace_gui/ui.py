from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import argparse
import os
import platform
import pty
import queue
import select
import subprocess
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk

from .core import TASK_CONTEXT_BUDGET
from .core import ConsoleChunk
from .core import TaskAction
from .core import TaskSummary
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import load_task_actions
from .core import load_workspace_gui_settings
from .core import parse_console_output
from .core import read_task_file
from .core import render_markdown_chunks
from .core import run_task_action
from .core import run_task_check
from .core import save_workspace_gui_settings


class WorkspaceGui:
    def __init__(self, root: tk.Tk, workspace: Path) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.action_transcripts: dict[Path, str] = {}
        self.task_actions: list[TaskAction] = []
        self.git_repo_options: list[Path] = []
        self.git_repos_loaded_for: Path | None = None
        self.running_actions: set[tuple[str, Path]] = set()
        self.console_process: subprocess.Popen[bytes] | None = None
        self.console_fd: int | None = None
        self.console_task_path: Path | None = None
        default_font_size = int(tkfont.nametofont("TkDefaultFont").cget("size"))
        settings = load_workspace_gui_settings()
        self.font_size = settings.get("font_size", default_font_size)
        self.style = ttk.Style(self.root)
        self.text_font = tkfont.Font(
            family=tkfont.nametofont("TkTextFont").cget("family"),
            size=self.font_size,
        )
        self.fixed_font = tkfont.Font(
            family=tkfont.nametofont("TkFixedFont").cget("family"),
            size=self.font_size,
        )
        self.tree_font = tkfont.Font(
            family=tkfont.nametofont("TkDefaultFont").cget("family"),
            size=self.font_size,
        )
        self.h1_font = tkfont.Font(family=self.text_font.cget("family"), size=self.font_size + 6, weight="bold")
        self.h2_font = tkfont.Font(family=self.text_font.cget("family"), size=self.font_size + 4, weight="bold")
        self.h3_font = tkfont.Font(family=self.text_font.cget("family"), size=self.font_size + 2, weight="bold")

        self.root.title(f"Workspace GUI - {self.workspace}")
        self.root.geometry("1180x760")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._apply_font_size()
        self._build_ui()
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
        ttk.Button(toolbar, text="A-", command=lambda: self.adjust_font_size(-1)).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Button(toolbar, text="A+", command=lambda: self.adjust_font_size(1)).pack(side=tk.LEFT)
        self.summary_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.summary_var).pack(side=tk.LEFT, padx=12)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
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
        self.actions_text = self._add_actions_tab()
        self.console_text = self._add_console_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)

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

    def _add_actions_tab(self) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        toolbar = ttk.Frame(frame)
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
        self.task_actions_frame = ttk.Frame(frame)
        self.task_actions_frame.pack(side=tk.TOP, fill=tk.X)
        text = tk.Text(frame, wrap=tk.WORD, undo=False, font=self.text_font)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(frame, text="Actions")
        self._configure_text_tags(text)
        return text

    def _add_console_tab(self) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        toolbar = ttk.Frame(frame)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Restart", command=self.restart_console).pack(
            side=tk.LEFT,
            padx=2,
            pady=2,
        )
        body = ttk.Frame(frame)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        text = tk.Text(body, wrap=tk.NONE, undo=False, font=self.fixed_font)
        text.bind("<Key>", self._on_console_key)
        text.bind("<Button-1>", lambda _event: text.focus_set())
        scroll_y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
        scroll_x = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=text.xview)
        text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.notebook.add(frame, text="Console")
        self._configure_console_tags(text)
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
        text = self.action_transcripts.get(task.path, "")
        if action_errors:
            text += action_errors
        self._set_text(self.actions_text, text)
        if self.console_task_path is not None and self.console_task_path != task.path:
            self.stop_console()
            self._set_console_text(f"Console ready for {task.path}\n")
        if self._is_console_tab_selected():
            self.start_console(task)

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
            self.start_console(self.selected_task)

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

    def run_selected_task_check(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._run_transcript_background(
            "task_check",
            ("task_check", task.path),
            task.path,
            lambda: run_task_check(task, self.workspace),
            self.actions_text,
        )

    def run_selected_git_status(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._ensure_git_repos_loaded(task)
        repo = self._selected_git_repo()
        if repo is None:
            return
        self._run_transcript_background(
            "git status",
            ("git status", repo),
            task.path,
            lambda: render_git_status(repo),
            self.actions_text,
            detail=self._repo_label(task, repo),
        )

    def scan_selected_git_repos(self) -> None:
        task = self._require_task()
        if task is not None:
            self._ensure_git_repos_loaded(task)

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is None:
            return
        self._run_transcript_background(
            action.label,
            ("task action", task.path / action.action_id),
            task.path,
            lambda: run_task_action(action),
            self.actions_text,
        )

    def reload_selected_task_actions(self) -> None:
        task = self._require_task()
        if task is None:
            return
        action_errors = self._load_task_action_buttons(task)
        text = self.action_transcripts.get(task.path, "")
        if action_errors:
            text += action_errors
        self._set_text(self.actions_text, text)

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
            self._append_action(task.path, "No git repositories found under dev/.\n\n")
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

    def _run_transcript_background(
        self,
        label: str,
        running_key: tuple[str, Path],
        transcript_key: Path,
        action: Callable[[], str],
        target: tk.Text,
        detail: str | None = None,
    ) -> None:
        if running_key in self.running_actions:
            self._append_action(transcript_key, f"running: {label}\n")
            return
        self.running_actions.add(running_key)
        self._append_action(transcript_key, _transcript_header(label, detail))
        self._run_background(label, running_key, action, target, transcript_key)

    def _run_background(
        self,
        label: str,
        running_key: tuple[str, Path],
        action: Callable[[], str],
        target: tk.Text,
        transcript_key: Path,
    ) -> None:
        self._append_action(transcript_key, f"start: {label}\n")

        def worker() -> None:
            try:
                result = action()
            except Exception as error:
                result = f"{type(error).__name__}: {error}"
            self.running_actions.discard(running_key)
            payload = result.rstrip() + f"\n\ndone: {label}\n\n"
            self.messages.put(("append", f"{id(target)}\n{transcript_key}\n{payload}"))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_messages(self) -> None:
        targets = {
            str(id(self.actions_text)): self.actions_text,
        }
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "append":
                target_id, transcript_key, text = payload.split("\n", 2)
                target = targets.get(target_id)
                self._append_action(Path(transcript_key), text, target=target)
            elif kind == "console":
                self._append_console_output(payload)
        self.root.after(100, self._poll_messages)

    def start_console(self, task: TaskSummary) -> None:
        if (
            self.console_process is not None
            and self.console_process.poll() is None
            and self.console_task_path == task.path
        ):
            return
        self.stop_console()
        self.console_task_path = task.path
        self._set_console_text(f"Starting shell in {task.path}\n")
        shell = os.environ.get("SHELL") or "/bin/bash"
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as error:
            self._set_console_text(f"Could not start console: {error}\n")
            return
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        try:
            self.console_process = subprocess.Popen(
                [shell],
                cwd=task.path,
                env=env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                start_new_session=True,
            )
        except OSError as error:
            os.close(master_fd)
            self._set_console_text(f"Could not start {shell}: {error}\n")
            return
        finally:
            os.close(slave_fd)
        self.console_fd = master_fd
        threading.Thread(target=self._read_console, args=(master_fd,), daemon=True).start()
        self.console_text.focus_set()

    def restart_console(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self.stop_console()
        self.start_console(task)

    def stop_console(self) -> None:
        process = self.console_process
        fd = self.console_fd
        self.console_process = None
        self.console_fd = None
        self.console_task_path = None
        if process is not None and process.poll() is None:
            process.terminate()
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                return

    def _read_console(self, fd: int) -> None:
        while True:
            try:
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    process = self.console_process
                    if process is None or process.poll() is not None:
                        break
                    continue
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            chunks = parse_console_output(data.decode(errors="replace"))
            self.messages.put(("console", chunks))

    def _on_console_key(self, event: tk.Event[tk.Misc]) -> str:
        fd = self.console_fd
        if fd is None:
            return "break"
        sequence = self._console_key_sequence(event)
        if sequence:
            try:
                os.write(fd, sequence)
            except OSError:
                return "break"
        return "break"

    def _console_key_sequence(self, event: tk.Event[tk.Misc]) -> bytes:
        keysym = event.keysym
        state = event.state
        if state & 0x4 and keysym.lower() == "c":
            return b"\x03"
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

    def _set_console_text(self, text: str) -> None:
        self.console_text.delete("1.0", tk.END)
        self.console_text.insert(tk.END, text)

    def _append_console_output(self, chunks: list[ConsoleChunk]) -> None:
        for chunk in chunks:
            self.console_text.insert(tk.END, chunk.text, chunk.tags)
        self.console_text.see(tk.END)

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

    def _append_action(self, transcript_key: Path, text: str, target: tk.Text | None = None) -> None:
        self.action_transcripts[transcript_key] = self.action_transcripts.get(transcript_key, "") + text
        if self.selected_task is not None and self.selected_task.path == transcript_key:
            self._set_text(target or self.actions_text, self.action_transcripts[transcript_key])

    def _set_details_default_split(self) -> None:
        height = self.details_pane.winfo_height()
        if height <= 1:
            self.root.after(50, self._set_details_default_split)
            return
        try:
            self.details_pane.sashpos(0, max(120, height // 3))
        except tk.TclError:
            return

    def _on_details_split_double_clicked(self, _event: tk.Event[tk.Misc]) -> str:
        self._set_details_default_split()
        return "break"

    def adjust_font_size(self, delta: int) -> None:
        self.font_size = max(8, min(28, self.font_size + delta))
        self._apply_font_size()
        save_workspace_gui_settings({"font_size": self.font_size})

    def _apply_font_size(self) -> None:
        self.text_font.configure(size=self.font_size)
        self.fixed_font.configure(size=self.font_size)
        self.tree_font.configure(size=self.font_size)
        self.h1_font.configure(size=self.font_size + 6)
        self.h2_font.configure(size=self.font_size + 4)
        self.h3_font.configure(size=self.font_size + 2)
        row_height = self.tree_font.metrics("linespace") + 8
        self.style.configure("Workspace.Treeview", font=self.tree_font, rowheight=row_height)
        for widget_name in (
            "description_text",
            "context_text",
            "actions_text",
        ):
            widget = getattr(self, widget_name, None)
            if isinstance(widget, tk.Text):
                self._configure_text_tags(widget)
        if isinstance(getattr(self, "console_text", None), tk.Text):
            self.console_text.configure(font=self.fixed_font)

    def _is_console_tab_selected(self) -> bool:
        return self.notebook.tab(self.notebook.select(), "text") == "Console"

    def close(self) -> None:
        self.stop_console()
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
