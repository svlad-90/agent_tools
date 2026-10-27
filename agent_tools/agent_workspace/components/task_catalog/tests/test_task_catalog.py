from __future__ import annotations

import agent_tools.agent_workspace.components.task_catalog.src.catalog as catalog_module
from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.task_catalog.api import task_init_command
from agent_tools.agent_workspace.components.task_catalog.api import task_path_for_name


def test_task_catalog_validates_new_task_path(tmp_path: Path) -> None:
    assert task_path_for_name(tmp_path, "sample-task") == tmp_path / "tasks" / "sample-task"
    assert task_path_for_name(tmp_path, "") is None
    assert task_path_for_name(tmp_path, "..") is None
    assert task_path_for_name(tmp_path, "../outside") is None
    assert task_path_for_name(tmp_path, "nested/task") is None
    assert task_path_for_name(tmp_path, ".hidden") is None
    assert task_path_for_name(tmp_path, "CON") is None
    assert task_path_for_name(tmp_path, "nul.txt") is None
    assert task_path_for_name(tmp_path, "task:name") is None
    assert task_path_for_name(tmp_path, "task ") is None
    assert task_path_for_name(tmp_path, "task.") is None
    assert task_path_for_name(tmp_path, "task\x00name") is None
    assert task_path_for_name(tmp_path, "x" * 256) is None
    assert task_path_for_name(tmp_path, "task-\ud800") is None


def test_task_catalog_builds_private_init_command(tmp_path: Path) -> None:
    task_path = tmp_path / "tasks" / "sample-task"

    command = task_init_command(tmp_path, task_path, privacy="private")

    assert command[:3] == [sys.executable, "-m", "agent_tools.paf_workspace.task_check"]
    assert command[3:] == [
        str(task_path),
        "--workspace",
        str(tmp_path),
        "--init-layout",
        "--privacy",
        "private",
    ]


def test_discover_tasks_reports_description_context_and_budget(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    add_entry(
        task,
        severity="high",
        status="active",
        summary="Large active context",
        details="word " * (TASK_CONTEXT_BUDGET + 1),
    )

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["sample-task"]
    assert tasks[0].has_description
    assert tasks[0].has_context
    assert tasks[0].description_tokens == 0
    assert tasks[0].context_over_budget


def test_discover_tasks_ignores_legacy_slot_for_context_budget(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Goal.")
    set_slot(task, "operational-memory", "Current.")
    set_slot(task, "legacy", "word " * (TASK_CONTEXT_BUDGET + 1))

    tasks = discover_tasks(tmp_path)

    assert len(tasks) == 1
    assert not tasks[0].context_over_budget


def test_discover_tasks_can_skip_context_token_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    ensure_task_context_database(task)

    def fail_context_tokens(_task_path: Path) -> int:
        raise AssertionError("context token budget should be skipped")

    monkeypatch.setattr(catalog_module, "_task_context_tokens", fail_context_tokens)

    tasks = discover_tasks(tmp_path, include_context_tokens=False)

    assert len(tasks) == 1
    assert tasks[0].context_tokens == 0
    assert not tasks[0].context_over_budget


def test_discover_tasks_does_not_create_front_door_bell_for_existing_task(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    ensure_task_context_database(task)

    tasks = discover_tasks(tmp_path)

    front_door = task / "front_door_bell.py"
    assert len(tasks) == 1
    assert not front_door.exists()


def test_discover_tasks_sorts_names_case_insensitively(tmp_path: Path) -> None:
    for name in ("beta", "Alpha"):
        task = tmp_path / "tasks" / name
        task.mkdir(parents=True)
        ensure_task_context_database(task)

    tasks = discover_tasks(tmp_path)

    assert [entry.name for entry in tasks] == ["Alpha", "beta"]


def test_run_task_check_returns_text_report(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    for rel_path in ("dev", "Dockerfile", "scripts", "report/diff", "report/puml"):
        (task / rel_path).mkdir(parents=True, exist_ok=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")
    ensure_task_context_database(task)

    report = run_task_check(discover_tasks(tmp_path)[0], tmp_path)

    assert "Summary:" in report
    assert "PASS task-description" not in report
