"""PAF tasks for the Zephyr/Xen reusable environment."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.environments.tasks.base import check_environment_image
from paf_workspace.domains.environments.tasks.base import ensure_environment_image


class check_zephyr_xen_tools(EnvironmentTask):
    """Run the Zephyr/Xen toolchain smoke command inside the environment."""

    def __init__(self):
        super().__init__()
        self.set_name(check_zephyr_xen_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_ZEPHYR_XEN_TOOLS_CHECK"):
            logger.info("Skip Zephyr/Xen tools check: SKIP_ZEPHYR_XEN_TOOLS_CHECK is enabled")
            return
        self.docker_subprocess_must_succeed(
            self.container_alias(),
            runtime.ZEPHYR_XEN_TOOL_CHECK_COMMAND,
            timeout=int(self.param("ZEPHYR_XEN_TOOLS_CHECK_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("ZEPHYR_XEN_TOOLS_CHECK_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "ZEPHYR_XEN_TOOLS_CHECK_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param("ZEPHYR_XEN_TOOLS_CHECK_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                "ZEPHYR_XEN_TOOLS_CHECK_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


__all__ = [
    "check_environment_image",
    "ensure_environment_image",
    "check_zephyr_xen_tools",
]
