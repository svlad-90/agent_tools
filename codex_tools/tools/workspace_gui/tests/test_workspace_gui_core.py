from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

from codex_tools.tools.workspace_gui.core import TASK_CONTEXT_BUDGET
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
from codex_tools.tools.workspace_gui.ui import codex_console_command
from codex_tools.tools.workspace_gui.ui import console_tab_title
from codex_tools.tools.workspace_gui.ui import codex_task_context_message
from codex_tools.tools.workspace_gui.ui import embedded_terminal_command
from codex_tools.tools.workspace_gui.ui import render_git_status
from codex_tools.tools.workspace_gui.ui import task_action_shell_command
from codex_tools.tools.workspace_gui.ui import task_check_shell_command


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
            "geometry": "1200x800+10+20",
        },
        settings_path,
    )

    assert load_workspace_gui_settings(settings_path) == {
        "text_font_size": 17,
        "button_font_size": 14,
        "theme": "dark",
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
            '"theme": "blue", "geometry": "bad"}'
        ),
        encoding="utf-8",
    )

    assert load_workspace_gui_settings(settings_path) == {
        "text_font_size": 28,
        "button_font_size": 8,
    }


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
