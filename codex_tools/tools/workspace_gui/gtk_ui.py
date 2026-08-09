from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import shlex
import shutil
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Vte

from .core import TASK_CONTEXT_BUDGET
from .core import TaskAction
from .core import TaskSummary
from .core import discover_tasks
from .core import find_dev_git_repos
from .core import git_status
from .core import load_task_actions
from .core import load_workspace_gui_settings
from .core import read_task_file
from .core import save_workspace_gui_settings


@dataclass
class TerminalSession:
    session_id: int
    task_path: Path
    kind: str
    terminal: Vte.Terminal
    page: Gtk.Widget
    child_pid: int | None = None


class WorkspaceGtkGui:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.tasks: list[TaskSummary] = []
        self.selected_task: TaskSummary | None = None
        self.task_actions: list[TaskAction] = []
        self.git_repo_options: list[Path] = []
        self.git_repos_loaded_for: Path | None = None
        self.terminal_sessions: dict[int, TerminalSession] = {}
        self.next_terminal_id = 1

        settings = load_workspace_gui_settings()
        self.text_font_size = int(settings.get("text_font_size", 13))
        self.button_font_size = int(settings.get("button_font_size", 13))
        self.theme = str(settings.get("theme", "light"))
        self.window_geometry = str(settings.get("geometry", "1180x760"))

        self.window = Gtk.Window(title=f"Workspace GUI - {self.workspace}")
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
        toolbar.pack_start(_button("Refresh", self.refresh_tasks), False, False, 0)
        toolbar.pack_start(_button("Open Workspace", lambda *_: open_path(self.workspace)), False, False, 0)
        self.summary_label = Gtk.Label(label="")
        self.summary_label.set_xalign(0)
        toolbar.pack_start(self.summary_label, False, False, 6)

        main = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(main, True, True, 0)

        self.task_store = Gtk.ListStore(str, str, object)
        self.task_view = Gtk.TreeView(model=self.task_store)
        self.task_view.append_column(Gtk.TreeViewColumn("Task", Gtk.CellRendererText(), text=0))
        self.task_view.append_column(Gtk.TreeViewColumn("Task Details", Gtk.CellRendererText(), text=1))
        self.task_view.get_selection().connect("changed", self._on_task_selected)
        self.task_view.connect("row-activated", lambda *_: self.open_task())
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_min_content_width(360)
        task_scroll.add(self.task_view)
        main.pack1(task_scroll, resize=False, shrink=False)

        self.notebook = Gtk.Notebook()
        main.pack2(self.notebook, resize=True, shrink=False)
        self._add_details_tab()
        self._add_actions_tab()

    def _add_details_tab(self) -> None:
        pane = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.description_view = _text_view(self.text_font_size, editable=False)
        self.context_view = _text_view(self.text_font_size, editable=False)
        pane.pack1(_scrolled(self.description_view), resize=True, shrink=False)
        pane.pack2(_scrolled(self.context_view), resize=True, shrink=False)
        GLib.idle_add(lambda: pane.set_position(max(160, pane.get_allocated_height() // 4)) or False)
        self.notebook.append_page(pane, Gtk.Label(label="Details"))

    def _add_actions_tab(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.notebook.append_page(box, Gtk.Label(label="Actions"))

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(toolbar, False, False, 0)
        toolbar.pack_start(_button("Run task_check", self.run_selected_task_check), False, False, 0)
        toolbar.pack_start(_button("Reload actions", self.reload_selected_task_actions), False, False, 0)
        self.git_repo_combo = Gtk.ComboBoxText()
        self.git_repo_combo.set_hexpand(True)
        toolbar.pack_start(self.git_repo_combo, True, True, 0)
        toolbar.pack_start(_button("Scan repos", self.scan_selected_git_repos), False, False, 0)
        toolbar.pack_start(_button("Git status", self.run_selected_git_status), False, False, 0)

        self.task_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(self.task_actions_box, False, False, 0)
        self.actions_message = Gtk.Label(label="")
        self.actions_message.set_xalign(0)
        box.pack_start(self.actions_message, False, False, 0)

        console_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.pack_start(console_toolbar, False, False, 0)
        console_toolbar.pack_start(_button("New", self.new_console), False, False, 0)
        console_toolbar.pack_start(_button("Close", self.close_active_console), False, False, 0)
        console_toolbar.pack_start(_button("Run codex", self.run_codex_console), False, False, 0)

        self.console_notebook = Gtk.Notebook()
        box.pack_start(self.console_notebook, True, True, 0)

    def refresh_tasks(self, *_args: object) -> None:
        selected_name = self.selected_task.name if self.selected_task is not None else None
        self.tasks = discover_tasks(self.workspace)
        self.task_store.clear()
        selected_iter = None
        over_budget = 0
        for task in self.tasks:
            flags = []
            if not task.has_description:
                flags.append("missing desc")
            if not task.has_context:
                flags.append("missing context")
            if task.context_over_budget:
                over_budget += 1
                flags.append(f"context > {TASK_CONTEXT_BUDGET}")
            details = f"desc {task.description_tokens}, context {task.context_tokens}"
            if flags:
                details = f"{details}, {', '.join(flags)}"
            row_iter = self.task_store.append([task.name, details, task])
            if task.name == selected_name:
                selected_iter = row_iter
        self.summary_label.set_text(f"{len(self.tasks)} tasks, {over_budget} over context budget")
        if selected_iter is not None:
            self.task_view.get_selection().select_iter(selected_iter)
        elif self.tasks:
            self.task_view.get_selection().select_path(Gtk.TreePath.new_first())

    def _on_task_selected(self, selection: Gtk.TreeSelection) -> None:
        model, row_iter = selection.get_selected()
        if row_iter is None:
            return
        self.selected_task = model[row_iter][2]
        self._set_text(self.description_view, read_task_file(self.selected_task, "TASK_DESCRIPTION.md"))
        self._set_text(self.context_view, read_task_file(self.selected_task, "TASK_CONTEXT.md"))
        self._reset_actions()
        self._load_task_action_buttons()
        self._refresh_console_tabs_for_task(self.selected_task)

    def open_task(self, *_args: object) -> None:
        if self.selected_task is not None:
            open_path(self.selected_task.path)

    def run_selected_task_check(self, *_args: object) -> None:
        task = self._require_task()
        if task is not None:
            self._send_command_to_task_terminal(task, task_check_shell_command(self.workspace, task))

    def run_selected_git_status(self, *_args: object) -> None:
        task = self._require_task()
        if task is None:
            return
        self._ensure_git_repos_loaded(task)
        repo = self._selected_git_repo()
        if repo is not None:
            self._send_command_to_task_terminal(task, shlex.join(["git", "-C", str(repo), "status", "--short", "--branch"]))

    def scan_selected_git_repos(self, *_args: object) -> None:
        task = self._require_task()
        if task is not None:
            self._refresh_git_repos(task)

    def reload_selected_task_actions(self, *_args: object) -> None:
        self._reset_actions()
        self._load_task_action_buttons()

    def run_custom_task_action(self, action: TaskAction) -> None:
        task = self._require_task()
        if task is not None:
            self._send_command_to_task_terminal(task, task_action_shell_command(action))

    def _reset_actions(self) -> None:
        self.task_actions = []
        self.git_repo_options = []
        self.git_repos_loaded_for = None
        self.git_repo_combo.remove_all()
        for child in self.task_actions_box.get_children():
            self.task_actions_box.remove(child)
        self.actions_message.set_text("")

    def _load_task_action_buttons(self) -> None:
        task = self._require_task(show_dialog=False)
        if task is None:
            return
        actions, errors = load_task_actions(task)
        self.task_actions = actions
        self.actions_message.set_text("\n".join(errors))
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
            self._refresh_git_repos(task)

    def _refresh_git_repos(self, task: TaskSummary) -> None:
        self.git_repo_options = find_dev_git_repos(task)
        self.git_repos_loaded_for = task.path
        self.git_repo_combo.remove_all()
        for repo in self.git_repo_options:
            self.git_repo_combo.append_text(_repo_label(task, repo))
        if self.git_repo_options:
            self.git_repo_combo.set_active(0)
        else:
            self.actions_message.set_text("No git repositories found under dev/.")

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
                return
        self._start_terminal(
            task=task,
            command=codex_console_command(self.workspace, task),
            cwd=self.workspace,
            env=os.environ.copy(),
            kind="codex",
        )

    def close_active_console(self, *_args: object) -> None:
        page_num = self.console_notebook.get_current_page()
        if page_num < 0:
            return
        page = self.console_notebook.get_nth_page(page_num)
        for session_id, session in list(self.terminal_sessions.items()):
            if session.page is page:
                self.console_notebook.remove_page(page_num)
                self.terminal_sessions.pop(session_id, None)
                break

    def _send_command_to_task_terminal(self, task: TaskSummary, command: str) -> None:
        session = self._active_terminal_for_task(task) or self._first_terminal_for_task(task)
        if session is None:
            session_id = self.new_console(task=task)
            session = self.terminal_sessions.get(session_id) if session_id is not None else None
        if session is None:
            return
        self._activate_terminal(session.session_id)
        _feed_terminal(session.terminal, command + "\n")

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
        terminal.connect("button-press-event", self._on_terminal_button_press)
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

    def _current_task_terminal_sessions(self, task: TaskSummary) -> list[TerminalSession]:
        return [
            session
            for session in self.terminal_sessions.values()
            if session.task_path == task.path
        ]

    def _renumber_terminal_tabs(self, task: TaskSummary) -> None:
        for index, session in enumerate(self._current_task_terminal_sessions(task), start=1):
            tab = self.console_notebook.get_tab_label(session.page)
            if isinstance(tab, Gtk.Label):
                tab.set_text(f"{index} {session.kind}")

    def _show_terminal_tab(self, session: TerminalSession) -> None:
        if self.console_notebook.page_num(session.page) < 0:
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

    def _active_terminal_for_task(self, task: TaskSummary) -> TerminalSession | None:
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
        menu = Gtk.Menu()
        copy_item = Gtk.MenuItem(label="Copy")
        paste_item = Gtk.MenuItem(label="Paste")
        copy_item.connect("activate", lambda *_: terminal.copy_clipboard())
        paste_item.connect("activate", lambda *_: terminal.paste_clipboard())
        menu.append(copy_item)
        menu.append(paste_item)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def _require_task(self, show_dialog: bool = True) -> TaskSummary | None:
        if self.selected_task is not None:
            return self.selected_task
        if show_dialog:
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Select a task first",
            )
            dialog.run()
            dialog.destroy()
        return None

    def _set_text(self, view: Gtk.TextView, text: str) -> None:
        view.get_buffer().set_text(text)

    def _apply_window_geometry(self) -> None:
        size = self.window_geometry.split("+", 1)[0]
        if "x" not in size:
            self.window.set_default_size(1180, 760)
            return
        width, height = size.split("x", 1)
        try:
            self.window.set_default_size(int(width), int(height))
        except ValueError:
            self.window.set_default_size(1180, 760)

    def _apply_css(self) -> None:
        colors = _theme_colors(self.theme)
        css = f"""
        * {{ font-size: {self.button_font_size}pt; }}
        textview, treeview, notebook, window {{
            background: {colors['background']};
            color: {colors['foreground']};
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
        terminal.set_color_foreground(_rgba(colors["foreground"]))
        terminal.set_color_background(_rgba(colors["terminal_background"]))

    def close(self, *_args: object) -> None:
        allocation = self.window.get_allocation()
        save_workspace_gui_settings(
            {
                "text_font_size": self.text_font_size,
                "button_font_size": self.button_font_size,
                "theme": self.theme,
                "geometry": f"{allocation.width}x{allocation.height}",
            }
        )
        Gtk.main_quit()


def _button(label: str, callback: object) -> Gtk.Button:
    button = Gtk.Button(label=label)
    button.connect("clicked", callback)
    return button


def _text_view(font_size: int, editable: bool) -> Gtk.TextView:
    view = Gtk.TextView()
    view.set_editable(editable)
    view.set_cursor_visible(editable)
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.modify_font(Pango.FontDescription(f"Monospace {font_size}"))
    return view


def _scrolled(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
    scrolled = Gtk.ScrolledWindow()
    scrolled.add(widget)
    return scrolled


def _repo_label(task: TaskSummary, repo: Path) -> str:
    try:
        return str(repo.relative_to(task.path))
    except ValueError:
        return str(repo)


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
        "--cd",
        str(workspace),
        "--no-alt-screen",
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


def _feed_terminal(terminal: Vte.Terminal, text: str) -> None:
    data = text.encode()
    try:
        terminal.feed_child(data, len(data))
    except TypeError:
        terminal.feed_child(text, len(text))


def _terminal_env(env: dict[str, str]) -> list[str]:
    env.setdefault("TERM", "xterm-256color")
    return [f"{key}={value}" for key, value in env.items()]


def _rgba(color: str) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    rgba.parse(color)
    return rgba


def _theme_colors(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "background": "#202124",
            "text_background": "#111315",
            "terminal_background": "#111315",
            "foreground": "#e8eaed",
        }
    return {
        "background": "#f2f2f2",
        "text_background": "#ffffff",
        "terminal_background": "#ffffff",
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
