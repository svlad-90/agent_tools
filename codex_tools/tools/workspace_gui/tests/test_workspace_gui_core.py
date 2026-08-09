from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

from codex_tools.tools.workspace_gui.core import TASK_CONTEXT_BUDGET
from codex_tools.tools.workspace_gui.core import ConsoleChunk
from codex_tools.tools.workspace_gui.core import TaskAction
from codex_tools.tools.workspace_gui.core import TaskSummary
from codex_tools.tools.workspace_gui.core import discover_tasks
from codex_tools.tools.workspace_gui.core import find_dev_git_repos
from codex_tools.tools.workspace_gui.core import git_status
from codex_tools.tools.workspace_gui.core import load_task_actions
from codex_tools.tools.workspace_gui.core import load_workspace_gui_settings
from codex_tools.tools.workspace_gui.core import parse_console_output
from codex_tools.tools.workspace_gui.core import render_markdown_chunks
from codex_tools.tools.workspace_gui.core import rough_token_count
from codex_tools.tools.workspace_gui.core import save_workspace_gui_settings
from codex_tools.tools.workspace_gui.core import run_task_action
from codex_tools.tools.workspace_gui.core import run_task_check
from codex_tools.tools.workspace_gui.gtk_ui import WorkspaceGtkGui
from codex_tools.tools.workspace_gui.gtk_ui import TRANSLATIONS as GTK_TRANSLATIONS
from codex_tools.tools.workspace_gui.gtk_ui import codex_task_context_message as gtk_codex_task_context_message
from codex_tools.tools.workspace_gui.gtk_ui import task_action_shell_command as gtk_task_action_shell_command
from codex_tools.tools.workspace_gui.gtk_ui import _artifact_monitor_dirs as gtk_artifact_monitor_dirs
from codex_tools.tools.workspace_gui.gtk_ui import _is_pane_separator_event as gtk_is_pane_separator_event
from codex_tools.tools.workspace_gui.gtk_ui import _task_artifact_entries as gtk_task_artifact_entries
from codex_tools.tools.workspace_gui.gtk_ui import _iter_git_repos as gtk_iter_git_repos
from codex_tools.tools.workspace_gui.gtk_ui import _task_init_command as gtk_task_init_command
from codex_tools.tools.workspace_gui.gtk_ui import _task_actions_signature as gtk_task_actions_signature
from codex_tools.tools.workspace_gui.gtk_ui import _task_path_for_name as gtk_task_path_for_name
from codex_tools.tools.workspace_gui.gtk_ui import _terminal_palette as gtk_terminal_palette
from codex_tools.tools.workspace_gui.gtk_ui import _terminal_session_sort_key as gtk_terminal_session_sort_key
from codex_tools.tools.workspace_gui.gtk_ui import _theme_colors as gtk_theme_colors
from codex_tools.tools.workspace_gui.ui import codex_console_command
from codex_tools.tools.workspace_gui.ui import console_paste_text
from codex_tools.tools.workspace_gui.ui import console_tab_title
from codex_tools.tools.workspace_gui.ui import ConsoleSession
from codex_tools.tools.workspace_gui.ui import codex_task_context_message
from codex_tools.tools.workspace_gui.ui import embedded_terminal_command
from codex_tools.tools.workspace_gui.ui import render_git_status
from codex_tools.tools.workspace_gui.ui import task_action_shell_command
from codex_tools.tools.workspace_gui.ui import task_check_shell_command
from codex_tools.tools.workspace_gui.ui import WorkspaceGui


class FakeConsoleText:
    def __init__(self, text: str) -> None:
        self.text = text
        self.marks: dict[str, int] = {}

    def index(self, index: str) -> str:
        return str(self._offset(index))

    def insert(self, index: str, text: str, _tags: tuple[str, ...] = ()) -> None:
        offset = self._offset(index)
        self.text = self.text[:offset] + text + self.text[offset:]

    def delete(self, start: str, end: str) -> None:
        start_offset = self._offset(start)
        end_offset = self._offset(end)
        self.text = self.text[:start_offset] + self.text[end_offset:]
        for mark, offset in list(self.marks.items()):
            if offset > end_offset:
                self.marks[mark] = offset - (end_offset - start_offset)
            elif offset > start_offset:
                self.marks[mark] = start_offset

    def compare(self, left: str, operator: str, right: str) -> bool:
        left_offset = self._offset(left)
        right_offset = self._offset(right)
        if operator == "<":
            return left_offset < right_offset
        if operator == ">=":
            return left_offset >= right_offset
        raise AssertionError(f"unsupported compare operator {operator!r}")

    def mark_set(self, mark: str, index: str) -> None:
        self.marks[mark] = self._offset(index)

    def mark_gravity(self, _mark: str, _gravity: str) -> None:
        return

    def mark_unset(self, mark: str) -> None:
        self.marks.pop(mark, None)

    def _offset(self, index: str) -> int:
        if index in self.marks:
            return self.marks[index]
        if index == "end":
            return len(self.text)
        if index == "end-1c":
            return len(self.text)
        if index == "end-2c":
            return max(0, len(self.text) - 1)
        if index == "end-1c linestart":
            return self.text.rfind("\n") + 1
        if index == "1.0":
            return 0
        if index.isdigit():
            return int(index)
        raise AssertionError(f"unsupported index {index!r}")


class FakePane:
    def __init__(self, orientation: object, position: int) -> None:
        self.orientation = orientation
        self.position = position

    def get_orientation(self) -> object:
        return self.orientation

    def get_position(self) -> int:
        return self.position


class FakePaneEvent:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def test_discover_tasks_reports_description_context_and_budget(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n\nshort\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text("word " * (TASK_CONTEXT_BUDGET + 1), encoding="utf-8")

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["sample-task"]
    assert tasks[0].has_description
    assert tasks[0].has_context
    assert tasks[0].description_tokens > 0
    assert tasks[0].context_over_budget


def test_discover_tasks_sorts_names_case_insensitively(tmp_path: Path) -> None:
    for name in ("beta", "Alpha"):
        task = tmp_path / "tasks" / name
        task.mkdir(parents=True)
        (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["Alpha", "beta"]


def test_run_task_check_returns_text_report(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    for rel_path in ("dev", "Dockerfile", "scripts", "report/diff", "report/puml"):
        (task / rel_path).mkdir(parents=True, exist_ok=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")

    report = run_task_check(discover_tasks(tmp_path)[0], tmp_path)

    assert "Summary:" in report
    assert "PASS task-description" in report


def test_find_dev_git_repos_and_status(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    repo = task / "dev" / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)

    repos = find_dev_git_repos(discover_tasks_with_context(task, tmp_path))
    status = git_status(repo)

    assert repos == [repo]
    assert status.error is None
    assert status.branch_line.startswith("##")


def test_gtk_iter_git_repos_yields_nested_repos(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    repo = task / "dev" / "repo"
    nested_repo = task / "dev" / "container" / "nested"
    (repo / ".git").mkdir(parents=True)
    (nested_repo / ".git").mkdir(parents=True)
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert list(gtk_iter_git_repos(summary)) == [nested_repo, repo]


def test_gtk_task_artifact_entries_groups_task_outputs(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    (task / "report" / "diff").mkdir(parents=True)
    (task / "report" / "puml").mkdir(parents=True)
    (task / "report" / "runtime.log").write_text("log", encoding="utf-8")
    (task / "report" / "diff" / "review.html").write_text("<html>", encoding="utf-8")
    (task / "report" / "puml" / "flow.svg").write_text("<svg>", encoding="utf-8")
    (task / "report" / "notes.md").write_text("notes", encoding="utf-8")
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    entries = gtk_task_artifact_entries(summary)

    assert [(entry.group, entry.path.name) for entry in entries] == [
        ("logs", "runtime.log"),
        ("diagrams", "flow.svg"),
        ("diff_reports", "review.html"),
    ]
    assert gtk_artifact_monitor_dirs(summary) == [
        task / "report",
        task / "report" / "diff",
        task / "report" / "puml",
    ]


def test_rough_token_count_uses_words_and_character_fallback() -> None:
    assert rough_token_count("one two three") == 4
    assert rough_token_count("x" * 20) == 5


def test_render_markdown_chunks_formats_common_blocks() -> None:
    chunks = render_markdown_chunks(
        "# Title\n\n"
        "## Section\n"
        "- `item`\n"
        "| Role | Path |\n"
        "| --- | --- |\n"
        "| `HAL` | dev/hal |\n"
        "\n```"
        "\n"
        "code()\n"
        "```\n"
    )

    rendered = [(chunk.text.strip(), chunk.tag) for chunk in chunks if chunk.text.strip()]

    assert rendered == [
        ("Title", "h1"),
        ("Section", "h2"),
        ("- item", "list"),
        (
            "+----------------------------------------------------------------------------------------------+\n"
            "| Row 1                                                                                        |\n"
            "| Role: HAL                                                                                    |\n"
            "| Path: dev/hal                                                                                |\n"
            "+----------------------------------------------------------------------------------------------+",
            "table",
        ),
        ("code()", "code"),
    ]


def test_render_git_status_reports_one_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)

    report = render_git_status(repo)

    assert str(repo) in report
    assert report.count("##") == 1


def test_codex_task_context_message_points_at_selected_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    message = codex_task_context_message(summary, tmp_path)

    assert "workspace task `sample-task`" in message
    assert f"Workspace: {tmp_path}" in message
    assert f"Task directory: {task}" in message
    assert "TASK_DESCRIPTION.md" in message
    assert "TASK_CONTEXT.md" in message


def test_codex_console_command_passes_prompt_and_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = codex_console_command(tmp_path, summary)

    assert command[-4:] == [
        "--cd",
        str(tmp_path),
        "--no-alt-screen",
        codex_task_context_message(summary, tmp_path),
    ]


def test_embedded_terminal_command_uses_vte_launcher(tmp_path: Path) -> None:
    command = embedded_terminal_command(
        socket_id=42,
        cwd=tmp_path,
        command=["codex", "--cd", str(tmp_path)],
        font_size=16,
        theme="dark",
    )

    assert command[1:] == [
        "-m",
        "codex_tools.tools.workspace_gui.vte_terminal",
        "--socket-id",
        "42",
        "--cwd",
        str(tmp_path),
        "--font-size",
        "16",
        "--theme",
        "dark",
        "--",
        "codex",
        "--cd",
        str(tmp_path),
    ]


def test_task_check_shell_command_runs_from_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = task_check_shell_command(tmp_path, summary)

    assert command.startswith(f"cd {tmp_path} && ")
    assert "codex_tools.paf_workspace.task_check" in command
    assert str(task) in command


def test_task_action_shell_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = task_action_shell_command(action)

    assert command == f"cd {tmp_path / 'scripts'} && FLAG='hello world' python -m pytest"


def test_gtk_task_action_shell_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = gtk_task_action_shell_command(action)

    assert command == f"cd {tmp_path / 'scripts'} && FLAG='hello world' python -m pytest"


def test_gtk_pane_separator_hit_test_uses_orientation() -> None:
    from gi.repository import Gtk

    horizontal = FakePane(Gtk.Orientation.HORIZONTAL, 100)
    vertical = FakePane(Gtk.Orientation.VERTICAL, 200)

    assert gtk_is_pane_separator_event(horizontal, FakePaneEvent(105, 40))
    assert not gtk_is_pane_separator_event(horizontal, FakePaneEvent(120, 100))
    assert gtk_is_pane_separator_event(vertical, FakePaneEvent(40, 205))
    assert not gtk_is_pane_separator_event(vertical, FakePaneEvent(200, 220))


def test_gtk_task_path_for_name_stays_under_tasks(tmp_path: Path) -> None:
    assert gtk_task_path_for_name(tmp_path, "sample-task") == tmp_path / "tasks" / "sample-task"
    assert gtk_task_path_for_name(tmp_path, "") is None
    assert gtk_task_path_for_name(tmp_path, "..") is None
    assert gtk_task_path_for_name(tmp_path, "../outside") is None
    assert gtk_task_path_for_name(tmp_path, "nested/task") is None


def test_gtk_task_init_command_uses_task_check_layout(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks" / "sample-task"

    command = gtk_task_init_command(tmp_path, task_path)

    assert command[:3] == [sys.executable, "-m", "codex_tools.paf_workspace.task_check"]
    assert command[3:] == [
        str(task_path),
        "--workspace",
        str(tmp_path),
        "--init-layout",
    ]


def test_gtk_task_actions_signature_tracks_file_mtime(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = TaskSummary("sample-task", task, True, True, 1, 1, False)

    assert gtk_task_actions_signature(summary) == (task / "TASK_ACTIONS.json", None)

    actions_file = task / "TASK_ACTIONS.json"
    actions_file.write_text('{"actions": []}', encoding="utf-8")

    assert gtk_task_actions_signature(summary)[0] == actions_file
    assert gtk_task_actions_signature(summary)[1] is not None


def test_console_tab_title_uses_stack_index_before_kind() -> None:
    assert console_tab_title(1, "shell") == "1 shell"
    assert console_tab_title(2, "codex") == "2 codex"


def test_workspace_gui_settings_persist_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"

    save_workspace_gui_settings(
        {
            "text_font_size": 17,
            "button_font_size": 14,
            "theme": "dark",
            "language": "ru",
            "geometry": "1200x800+10+20",
        },
        settings_path,
    )

    assert load_workspace_gui_settings(settings_path) == {
        "text_font_size": 17,
        "button_font_size": 14,
        "theme": "dark",
        "language": "ru",
        "geometry": "1200x800+10+20",
    }


def test_workspace_gui_settings_migrate_old_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"font_size": 17}', encoding="utf-8")

    assert load_workspace_gui_settings(settings_path) == {"text_font_size": 17}


def test_workspace_gui_settings_clamp_bad_font_size(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        (
            '{"text_font_size": 100, "button_font_size": 4, '
            '"theme": "blue", "language": "bad", "geometry": "bad"}'
        ),
        encoding="utf-8",
    )

    assert load_workspace_gui_settings(settings_path) == {
        "text_font_size": 28,
        "button_font_size": 8,
    }


def test_gtk_theme_colors_cover_widget_css_keys() -> None:
    required = {
        "background",
        "border",
        "codex_running_background",
        "codex_running_border",
        "codex_running_foreground",
        "codex_running_glow",
        "control_background",
        "control_hover_background",
        "foreground",
        "menu_background",
        "muted_foreground",
        "separator",
        "selection_background",
        "selection_foreground",
        "tab_background",
        "tab_selected_background",
        "tab_selected_foreground",
        "terminal_background",
        "text_background",
        "titlebar_background",
    }

    assert required <= set(gtk_theme_colors("dark"))
    assert required <= set(gtk_theme_colors("light"))


def test_gtk_dark_terminal_palette_uses_readable_blue() -> None:
    palette = gtk_terminal_palette("dark")

    assert len(palette) == 16
    assert palette[4] == "#7aa2f7"
    assert "#0000ff" not in palette


def test_gtk_terminal_session_sort_key_keeps_codex_first() -> None:
    entries = [("shell", 1), ("codex", 3), ("shell", 2)]

    assert sorted(entries, key=lambda item: gtk_terminal_session_sort_key(item[0], item[1])) == [
        ("codex", 3),
        ("shell", 1),
        ("shell", 2),
    ]


def test_gtk_codex_prompt_includes_selected_language(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    message = gtk_codex_task_context_message(summary, tmp_path, "uk")

    assert "Відповідай користувачу українською мовою." in message


def test_gtk_translates_codex_and_repo_scan_labels() -> None:
    assert GTK_TRANSLATIONS["ru"]["run_codex"] == "Запустить Codex"
    assert GTK_TRANSLATIONS["ru"]["scanning_repos"] == "Сканирование репозиториев..."


def test_gtk_markdown_tags_are_configured() -> None:
    from gi.repository import Gtk

    gui = object.__new__(WorkspaceGtkGui)
    gui.text_font_size = 13
    buffer = Gtk.TextBuffer()

    gui._ensure_markdown_tags(buffer)

    assert buffer.get_tag_table().lookup("h1") is not None
    assert buffer.get_tag_table().lookup("list") is not None
    assert buffer.get_tag_table().lookup("table") is not None


def test_parse_console_output_preserves_color_tags() -> None:
    chunks = parse_console_output("\x1b[01;32muser\x1b[00m:\x1b[34m~/task\x1b[00m$ \r\n")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [
        ("user", ("console_bold", "console_fg_green")),
        (":", ()),
        ("~/task", ("console_fg_blue",)),
        ("$ \n", ()),
    ]


def test_parse_console_output_keeps_backspace_control() -> None:
    chunks = parse_console_output("abc\b \b")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("abc\b \b", ())]


def test_parse_console_output_keeps_carriage_return_control() -> None:
    chunks = parse_console_output("prompt old\rprompt new")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("prompt old\rprompt new", ())]


def test_console_paste_text_normalizes_newlines_without_trailing_enter() -> None:
    assert console_paste_text("one\r\ntwo\r\n") == "one two"
    assert console_paste_text("one\rtwo\n\n") == "one two"
    assert console_paste_text("\n  one  \n\n  two\t\n") == "one two"


def test_console_renderer_does_not_backspace_past_input_floor() -> None:
    gui = object.__new__(WorkspaceGui)
    text = FakeConsoleText("task$ ")
    session = ConsoleSession(
        session_id=1,
        title="1 shell",
        task_path=Path("/tmp/task"),
        kind="shell",
        frame=None,  # type: ignore[arg-type]
        text=text,  # type: ignore[arg-type]
        process=None,  # type: ignore[arg-type]
        fd=None,
        chunks=[],
    )

    gui._set_console_input_floor(session)
    gui._insert_console_chunk(session, ConsoleChunk("abc\b \b\b \b\b \b\b \b", ()))

    assert text.text == "task$ "


def test_parse_console_output_drops_terminal_title_sequence() -> None:
    chunks = parse_console_output("\x1b]0;user@host:~/task\x07task$ ")

    assert [(chunk.text, chunk.tags) for chunk in chunks] == [("task$ ", ())]


def test_load_task_actions_and_run_command(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    scripts = task / "scripts"
    scripts.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "unit",
                        "label": "Unit tests",
                        "command": [
                            sys.executable,
                            "-c",
                            "import os; print(os.environ['SAMPLE_FLAG'])",
                        ],
                        "cwd": "scripts",
                        "env": {"SAMPLE_FLAG": "ok"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))
    report = run_task_action(actions[0])

    assert errors == []
    assert actions[0].label == "Unit tests"
    assert actions[0].cwd == scripts.resolve()
    assert "ok" in report
    assert "exit code: 0" in report


def test_load_task_actions_rejects_escaping_cwd(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "bad",
                        "label": "Bad",
                        "command": "echo bad",
                        "cwd": "..",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    actions, errors = load_task_actions(discover_tasks_with_context(task, tmp_path))

    assert actions == []
    assert "cwd escapes task" in errors[0]


def discover_tasks_with_context(task: Path, workspace: Path) -> TaskSummary:
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    (task / "TASK_CONTEXT.md").write_text(_task_context(), encoding="utf-8")
    return discover_tasks(workspace)[0]


def _task_context() -> str:
    return """# Task Context

## Goal

-

## Repositories

-

## Environment

-

## Knowledge

-

## Build/Product

-

## Validation Status

| Level | Status |
| --- | --- |
| static | not run |
| build | not run |
| runtime | not run |
| review | not run |

## Tool Failures

-

## Decisions

-

## Blockers

-

## Next Steps

-
"""
