from __future__ import annotations

from pathlib import Path
import subprocess

from codex_tools.tools.workspace_gui.core import TASK_CONTEXT_BUDGET
from codex_tools.tools.workspace_gui.core import TaskSummary
from codex_tools.tools.workspace_gui.core import discover_tasks
from codex_tools.tools.workspace_gui.core import find_dev_git_repos
from codex_tools.tools.workspace_gui.core import git_status
from codex_tools.tools.workspace_gui.core import render_markdown_chunks
from codex_tools.tools.workspace_gui.core import rough_token_count
from codex_tools.tools.workspace_gui.core import run_task_check


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
        "| `A` | B |\n"
        "```\n"
        "code()\n"
        "```\n"
    )

    assert [(chunk.text.strip(), chunk.tag) for chunk in chunks if chunk.text.strip()] == [
        ("Title", "h1"),
        ("Section", "h2"),
        ("- item", "list"),
        ("| A | B |", "table"),
        ("code()", "code"),
    ]


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
