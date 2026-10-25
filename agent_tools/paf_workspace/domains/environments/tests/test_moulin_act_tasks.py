from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("paf.paf_impl")

from paf_workspace.domains.environments.tasks.act import check_moulin_act_tools
from paf_workspace.domains.environments.tasks.act import validate_moulin_act


class MoulinTaskRecorder(check_moulin_act_tools, validate_moulin_act):
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.docker_checks: list[tuple[str, str, str]] = []
        self.docker_commands: list[tuple[str, str, dict[str, object]]] = []

    def bool_param(self, _name: str, default: bool = False) -> bool:
        return default

    def param(self, name: str, default: str | None = None) -> str:
        if name == "MOULIN_REPO_ROOT":
            return str(self.repo_root)
        return default or ""

    def environment_string(self, environment: str, key: str, default: str = "") -> str:
        values = {
            ("agent_tools_act", "container"): "agent-tools-act-workspace",
            ("moulin_act", "container"): "moulin-act-workspace",
            ("moulin_act", "image"): "moulin-act",
        }
        return values.get((environment, key), default)

    def image_name(self, alias: str | None = None) -> str:
        return f"{alias}:22.04"

    def lines_param(self, _name: str) -> tuple[str, ...]:
        return ()

    def substitute_parameters(self, value: str) -> str:
        return value

    def assertion(self, condition: bool, message: str) -> None:
        assert condition, message

    def docker_tools_check(self, container: str, command: str, timeout: str) -> None:
        self.docker_checks.append((container, command, timeout))

    def docker_subprocess_must_succeed(self, container: str, command: str, **kwargs: object) -> None:
        self.docker_commands.append((container, command, kwargs))


def test_moulin_tool_check_runs_act_in_driver_container(tmp_path: Path) -> None:
    task = MoulinTaskRecorder(tmp_path)

    check_moulin_act_tools.execute(task)

    assert task.docker_checks[0][0] == "agent-tools-act-workspace"
    assert "act --version" in task.docker_checks[0][1]
    assert task.docker_checks[1][0] == "moulin-act-workspace"


def test_moulin_validation_runs_workflow_in_driver_container(tmp_path: Path) -> None:
    task = MoulinTaskRecorder(tmp_path)

    validate_moulin_act.execute(task)

    assert len(task.docker_commands) == 1
    container, command, kwargs = task.docker_commands[0]
    assert container == "agent-tools-act-workspace"
    assert f"cd {tmp_path}" in command
    assert "act pull_request -j build" in command
    assert "ubuntu-22.04=moulin-act:22.04" in command
    assert kwargs["timeout"] == 0
