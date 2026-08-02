"""Generic PAF tasks for workspace automation flows."""

from __future__ import annotations

from pathlib import Path

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import SSHLocalClient
from paf.paf_impl import logger


class WorkspaceTask(SSHLocalClient):
    """Base task with workspace parameter helpers."""

    def param(self, name: str, default: str | None = None) -> str | None:
        return self.get_environment().getVariables().get(name, default)

    def workspace_root(self) -> Path:
        return Path(self.param("WORKSPACE_ROOT") or ".").resolve()

    def bool_param(self, name: str, default: bool = False) -> bool:
        value = self.param(name, str(int(default)))
        return str(value).lower() in ("1", "true", "yes", "on")

    def path_param(self, name: str, default: str | None = None) -> Path:
        value = self.param(name, default)
        if value is None:
            self.fail(f"Missing required parameter: {name}")
            raise AssertionError("unreachable")
        path = Path(value)
        if path.is_absolute():
            return path
        return self.workspace_root() / path

    def run_command_param(self, name: str, *, skip_param: str | None = None) -> None:
        if skip_param and self.bool_param(skip_param):
            logger.info(f"Skip command from {name}: {skip_param} is enabled")
            return

        command = self.param(name)
        if not command:
            logger.info(f"Skip command from {name}: parameter is empty")
            return

        timeout = int(self.param(f"{name}_TIMEOUT_SEC", "0") or "0")
        logger.info(f"Run command from {name}")
        self.subprocess_must_succeed(
            command,
            timeout=timeout,
            shell=True,
            substitute_params=True,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param(f"{name}_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                f"{name}_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param(f"{name}_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                f"{name}_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )
