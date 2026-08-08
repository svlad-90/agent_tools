from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import argparse
import os
import platform
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk

from .core import TASK_CONTEXT_BUDGET
from .core import TaskSummary
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import read_task_file
from .core import render_markdown_chunks
from .core import run_task_check


class WorkspaceGui:
    def __init__(self, root: tk.Tk, workspace: Path) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.action_transcripts: dict[Path, str] = {}
        self.git_repo_options: list[Path] = []
        self.git_repos_loaded_for: Path | None = None
        self.running_actions: set[tuple[str, Path]] = set()
        self.font_size = int(tkfont.nametofont("TkDefaultFont").cget("size"))
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
        self.description_text = self._add_text_tab("Description")
        self.context_text = self._add_text_tab("Context")
        self.actions_text = self._add_actions_tab()

    def _add_text_tab(
        self,
        title: str,
        button_label: str | None = None,
        button_command: Callable[[], None] | None = None,
    ) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        if button_label is not None and button_command is not None:
            toolbar = ttk.Frame(frame)
            toolbar.pack(side=tk.TOP, fill=tk.X)
            ttk.Button(toolbar, text=button_label, command=button_command).pack(
                side=tk.LEFT,
                padx=2,
                pady=2,
            )
        text = tk.Text(frame, wrap=tk.WORD, undo=False, font=self.text_font)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(frame, text=title)
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
        text = tk.Text(frame, wrap=tk.WORD, undo=False, font=self.text_font)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(frame, text="Actions")
        self._configure_text_tags(text)
        return text

    def refresh_tasks(self) -> None:
        self.tasks = discover_tasks(self.workspace)
        self.task_tree.delete(*self.task_tree.get_children())
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
        over_budget = sum(1 for task in self.tasks if task.context_over_budget)
        self.summary_var.set(f"{len(self.tasks)} tasks, {over_budget} over context budget")
        if self.tasks:
            self.task_tree.selection_set("0")

    def _on_task_selected(self, _event: object) -> None:
        selection = self.task_tree.selection()
        if not selection:
            return
        task = self.tasks[int(selection[0])]
        self.selected_task = task
        self._set_markdown(self.description_text, read_task_file(task, "TASK_DESCRIPTION.md"))
        self._set_markdown(self.context_text, read_task_file(task, "TASK_CONTEXT.md"))
        self._reset_actions_tab(task)
        self._set_text(self.actions_text, self.action_transcripts.get(task.path, ""))

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

    def _reset_actions_tab(self, task: TaskSummary) -> None:
        self.git_repo_options = []
        self.git_repos_loaded_for = None
        self.git_repo_combo.configure(values=(), state=tk.DISABLED)
        self.git_repo_var.set("")

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
        self.root.after(100, self._poll_messages)

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

    def _append_action(self, transcript_key: Path, text: str, target: tk.Text | None = None) -> None:
        self.action_transcripts[transcript_key] = self.action_transcripts.get(transcript_key, "") + text
        if self.selected_task is not None and self.selected_task.path == transcript_key:
            self._set_text(target or self.actions_text, self.action_transcripts[transcript_key])

    def adjust_font_size(self, delta: int) -> None:
        self.font_size = max(8, min(28, self.font_size + delta))
        self._apply_font_size()

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
