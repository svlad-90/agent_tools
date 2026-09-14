from __future__ import annotations

import pytest

pytest.importorskip("paramiko")

from paf.paf_impl import CommunicationMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask


class FakeEnvironmentTask(EnvironmentTask):
    def __init__(self, yaml_config: dict[str, object], params: dict[str, str] | None = None):
        super().__init__()
        self._yaml_config = yaml_config
        self._params = params or {}

    def get_yaml_config(self) -> dict[str, object]:
        return self._yaml_config

    def param(self, name: str, default=None):
        return self._params.get(name, default)


def test_generic_environment_aliases_use_single_profile_environment() -> None:
    task = FakeEnvironmentTask(
        {
            "environments": {
                "zephyr_repo": {
                    "image": "zephyr-repo-checks",
                    "container": "zephyr-repo-checks-workspace",
                    "build_network": "host",
                },
            },
        },
    )

    assert task.environment_key() == "zephyr_repo"
    assert task.image_alias() == "zephyr-repo-checks"
    assert task.container_alias() == "zephyr-repo-checks-workspace"
    assert task.build_network() == "host"


def test_generic_environment_aliases_keep_zephyr_xen_precedence() -> None:
    task = FakeEnvironmentTask(
        {
            "environments": {
                "zephyr_xen": {
                    "image": "zephyr-xen",
                    "container": "zephyr-xen-workspace",
                },
                "zephyr_repo": {
                    "image": "zephyr-repo-checks",
                    "container": "zephyr-repo-checks-workspace",
                },
            },
        },
    )

    assert task.environment_key() == "zephyr_xen"
    assert task.image_alias() == "zephyr-xen"
    assert task.container_alias() == "zephyr-xen-workspace"


def test_communication_mode_param_defaults_to_pipe_output() -> None:
    task = FakeEnvironmentTask({})

    assert task.communication_mode_param("ENVIRONMENT_CONTAINER_COMMAND_USE_PTY") == CommunicationMode.PIPE_OUTPUT


def test_communication_mode_param_uses_pty_when_requested() -> None:
    task = FakeEnvironmentTask({}, {"ENVIRONMENT_CONTAINER_COMMAND_USE_PTY": "1"})

    assert task.communication_mode_param("ENVIRONMENT_CONTAINER_COMMAND_USE_PTY") == CommunicationMode.USE_PTY
