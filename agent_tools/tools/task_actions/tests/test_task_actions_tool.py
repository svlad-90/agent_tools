from __future__ import annotations

import json
from pathlib import Path
import sys

from agent_tools.tools.task_actions import add_action
from agent_tools.tools.task_actions import delete_action
from agent_tools.tools.task_actions import list_actions
from agent_tools.tools.task_actions import run_action
from agent_tools.tools.task_actions import show_action
from agent_tools.tools.task_actions import update_action


def test_task_actions_tool_lists_shows_and_runs_with_bindings(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample"
    task.mkdir(parents=True)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "parameter_types": {"profile": {"set": "profiles"}},
                "parameter_sets": {
                    "profiles": {
                        "dev": {"name": "Dev", "flag": "dev-flag"},
                        "release": {"name": "Release", "flag": "release-flag"},
                    }
                },
                "actions": [
                    {
                        "id": "echo",
                        "label": "Echo",
                        "command": [
                            sys.executable,
                            "-c",
                            (
                                "import os; "
                                "print(os.environ['TASK_ACTION_PARAM_PROFILE']); "
                                "print(os.environ['TASK_ACTION_PARAM_PROFILE_FLAG'])"
                            ),
                        ],
                        "cwd": ".",
                        "parameters": [
                            {
                                "name": "profile",
                                "label": "Profile",
                                "type": "profile",
                                "default": "dev",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    listing = list_actions(task)
    shown = show_action(task, "echo")
    result = run_action(task, "echo", {"profile": "release"})

    assert listing["errors"] == []
    assert listing["actions"][0]["id"] == "echo"
    assert shown["action"]["parameters"][0]["name"] == "profile"
    assert result["returncode"] == 0
    assert result["stdout"] == "release\nrelease-flag\n"


def test_task_actions_tool_adds_updates_and_deletes_action(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample"
    task.mkdir(parents=True)

    added = add_action(
        task,
        "build",
        "Build",
        [sys.executable, "-c", "print('old')"],
        cwd=".",
        env={"MODE": "dev"},
    )
    updated = update_action(
        task,
        "build",
        label="Build app",
        command=[sys.executable, "-c", "print('new')"],
        env={"MODE": "release"},
    )
    run = run_action(task, "build")
    deleted = delete_action(task, "build")

    assert added["action"]["id"] == "build"
    assert updated["action"]["label"] == "Build app"
    assert updated["action"]["env"] == {"MODE": "release"}
    assert run["stdout"] == "new\n"
    assert deleted["deleted"] == {"id": "build", "actions": 1, "shortcuts": 0}
    assert list_actions(task)["actions"] == []


def test_task_actions_tool_delete_removes_shortcuts_for_action(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample"
    task.mkdir(parents=True)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "actions": [
                    {
                        "id": "build",
                        "label": "Build",
                        "command": "true",
                    }
                ],
                "shortcuts": [
                    {
                        "id": "build-fast",
                        "label": "Build fast",
                        "action": "build",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    deleted = delete_action(task, "build")

    assert deleted["deleted"] == {"id": "build", "actions": 1, "shortcuts": 1}
    stored = json.loads((task / "TASK_ACTIONS.json").read_text(encoding="utf-8"))
    assert stored["actions"] == []
    assert stored["shortcuts"] == []
