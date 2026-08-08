from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import argparse
import os
import platform
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from .core import TASK_CONTEXT_BUDGET
from .core import TaskSummary
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import read_task_file
from .core import run_task_check


class WorkspaceGui:
    def __init__(self, root: tk.Tk, workspace: Path) -> None:
        self.root = root
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()

        self.root.title(f"Workspace GUI - {self.workspace}")
        self.root.geometry("1180x760")
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
        self.summary_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.summary_var).pack(side=tk.LEFT, padx=12)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, padding=6)
        main.add(left, weight=1)
        columns = ("description", "context", "flags")
        self.task_tree = ttk.Treeview(left, columns=columns, show="tree headings", selectmode="browse")
        self.task_tree.heading("#0", text="Task")
        self.task_tree.heading("description", text="Desc")
        self.task_tree.heading("context", text="Context")
        self.task_tree.heading("flags", text="Flags")
        self.task_tree.column("#0", width=260)
        self.task_tree.column("description", width=70, anchor=tk.E)
        self.task_tree.column("context", width=80, anchor=tk.E)
        self.task_tree.column("flags", width=140)
        self.task_tree.pack(fill=tk.BOTH, expand=True)
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)

        right = ttk.Frame(main, padding=6)
        main.add(right, weight=3)
        actions = ttk.Frame(right)
        actions.pack(side=tk.TOP, fill=tk.X)
        for label, command in (
            ("Open Task", self.open_task),
            ("Open dev/", self.open_dev),
            ("Run task_check", self.run_selected_task_check),
            ("Git status", self.run_selected_git_status),
        ):
            ttk.Button(actions, text=label, command=command).pack(side=tk.LEFT, padx=(0, 6))

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.description_text = self._add_text_tab("Description")
        self.context_text = self._add_text_tab("Context")
        self.checks_text = self._add_text_tab("Checks")
        self.git_text = self._add_text_tab("Git")
        self.log_text = self._add_text_tab("Log")

    def _add_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.notebook)
        text = tk.Text(frame, wrap=tk.WORD, undo=False)
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notebook.add(frame, text=title)
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
            self.task_tree.insert(
                "",
                tk.END,
                iid=str(index),
                text=task.name,
                values=(task.description_tokens, task.context_tokens, ", ".join(flags)),
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
        self._set_text(self.description_text, read_task_file(task, "TASK_DESCRIPTION.md"))
        self._set_text(self.context_text, read_task_file(task, "TASK_CONTEXT.md"))
        self._set_text(self.checks_text, "")
        self._set_text(self.git_text, "")

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
        self._run_background("task_check", lambda: run_task_check(task, self.workspace), self.checks_text)

    def run_selected_git_status(self) -> None:
        task = self._require_task()
        if task is None:
            return
        self._run_background("git status", lambda: render_git_status(task), self.git_text)

    def _run_background(self, label: str, action: Callable[[], str], target: tk.Text) -> None:
        self._append_log(f"start: {label}\n")

        def worker() -> None:
            try:
                result = action()
            except Exception as error:
                result = f"{type(error).__name__}: {error}"
            self.messages.put(("text", f"{id(target)}\n{result}"))
            self.messages.put(("log", f"done: {label}\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_messages(self) -> None:
        targets = {
            str(id(self.checks_text)): self.checks_text,
            str(id(self.git_text)): self.git_text,
        }
        while True:
            try:
                kind, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(payload)
            elif kind == "text":
                target_id, text = payload.split("\n", 1)
                target = targets.get(target_id)
                if target is not None:
                    self._set_text(target, text)
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

    def _append_log(self, text: str) -> None:
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)


def render_git_status(task: TaskSummary) -> str:
    repos = find_dev_git_repos(task)
    if not repos:
        return "No git repositories found under dev/.\n"
    sections = []
    for repo in repos:
        status = git_status(repo)
        lines = [str(repo), status.branch_line]
        if status.error:
            lines.append(f"error: {status.error}")
        elif status.changes:
            lines.extend(status.changes)
        else:
            lines.append("clean")
        sections.append("\n".join(lines))
    return "\n\n".join(sections) + "\n"


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
