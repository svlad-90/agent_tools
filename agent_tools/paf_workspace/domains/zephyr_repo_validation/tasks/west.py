"""Zephyr west workspace preparation tasks."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.zephyr_repo_validation.lib import runtime


class prepare_zephyr_west_workspace(EnvironmentTask):
    """Populate west modules for a Zephyr checkout using its own manifest."""

    def __init__(self):
        super().__init__()
        self.set_name(prepare_zephyr_west_workspace.__name__)

    def execute(self):
        container_alias = self.container_alias()
        zephyr = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_ZEPHYR", "") or "",
            container_alias,
        )
        self.assertion(zephyr, "Missing required parameter: ZEPHYR_REPO_CHECKS_ZEPHYR")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_west_update_command(
                runtime.ZephyrWestUpdate(
                    zephyr=zephyr,
                    update_args=tuple(
                        (self.param("ZEPHYR_REPO_CHECKS_WEST_UPDATE_ARGS", "") or "").splitlines()
                    ),
                )
            ),
            timeout=int(self.param("ZEPHYR_REPO_CHECKS_WEST_UPDATE_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


__all__ = ["prepare_zephyr_west_workspace"]
