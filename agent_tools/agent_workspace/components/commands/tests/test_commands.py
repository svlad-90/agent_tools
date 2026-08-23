from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_task_check_shell_command_runs_from_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = task_check_shell_command(tmp_path, summary)
    gtk_command = gtk_task_check_shell_command(tmp_path, summary)

    for command in (command, gtk_command):
        assert command.startswith(f"cd {tmp_path} && ")
        assert "agent_tools.agent_workspace.actions" in command
        assert "task-check" in command
        assert str(task) in command


def test_task_check_windows_command_runs_from_workspace(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    summary = discover_tasks_with_context(task, tmp_path)

    command = task_check_windows_command(tmp_path, summary)

    assert command.startswith("cd /d ")
    assert "agent_tools.agent_workspace.actions" in command
    assert "task-check" in command
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

    assert command.startswith(f"cd {tmp_path / 'scripts'} && bash -lc ")
    assert "report/logs" in command
    assert "unit-$(date +%Y%m%d-%H%M%S).log" in command
    assert "tee -a" in command
    assert "FLAG=" in command
    assert "hello world" in command
    assert f"{PAF_HIDE_TASK_ENV_VAR}=1" in command
    assert "python -m pytest" in command
    assert "exit ${PIPESTATUS[0]}" in command


def test_task_action_windows_command_runs_in_action_cwd(tmp_path: Path) -> None:
    action = TaskAction(
        action_id="unit",
        label="Unit",
        command=("python", "-m", "pytest"),
        cwd=tmp_path / "scripts",
        env={"FLAG": "hello world"},
    )

    command = task_action_windows_command(action)

    assert command.startswith("cd /d ")
    assert "report\\logs" in command or "report/logs" in command
    assert "unit-" in command
    assert "set \"FLAG=hello world\"&&" in command
    assert f"set \"{PAF_HIDE_TASK_ENV_VAR}=1\"&&" in command
    assert "python -m pytest" in command
    assert "2>&1" in command

