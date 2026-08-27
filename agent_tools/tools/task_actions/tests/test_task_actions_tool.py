from __future__ import annotations

import json
from pathlib import Path
import sys

from agent_tools.tools.task_actions import list_actions, run_action, show_action


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
