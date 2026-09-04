"""Zephyr build-backed validation tasks."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.zephyr_repo_validation.lib import runtime


def _zephyr_app_path(task: EnvironmentTask, path_text: str, container_alias: str) -> str:
    """Map workspace app paths, but keep Zephyr-relative sample paths intact."""
    if not path_text:
        return ""
    if task.path_param_exists(path_text):
        return task.container_workspace_path(path_text, container_alias)
    return path_text


class validate_zephyr_build(EnvironmentTask):
    """Configure and build a Zephyr app inside the selected environment."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_build.__name__)

    def execute(self):
        container_alias = self.container_alias()
        zephyr = self.container_workspace_path(
            self.param("ZEPHYR_BUILD_ZEPHYR", "") or "",
            container_alias,
        )
        app = _zephyr_app_path(self, self.param("ZEPHYR_BUILD_APP", "") or "", container_alias)
        board = self.param("ZEPHYR_BUILD_BOARD")
        build_dir = self.container_workspace_path(
            self.param("ZEPHYR_BUILD_DIR", "") or "",
            container_alias,
        )
        build_mode = self.param("ZEPHYR_BUILD_MODE", "west")
        for field_name, value in (
            ("ZEPHYR_BUILD_ZEPHYR", zephyr),
            ("ZEPHYR_BUILD_APP", app),
            ("ZEPHYR_BUILD_BOARD", board),
            ("ZEPHYR_BUILD_DIR", build_dir),
        ):
            self.assertion(value, f"Missing required parameter: {field_name}")
        self.assertion(
            build_mode in ("west", "cmake"),
            "ZEPHYR_BUILD_MODE must be either 'west' or 'cmake'",
        )

        build = runtime.ZephyrBuild(
            zephyr=str(zephyr),
            app=str(app),
            board=str(board),
            build_dir=str(build_dir),
            cmake_args=tuple((self.param("ZEPHYR_BUILD_CMAKE_ARGS", "") or "").splitlines()),
            kconfig_options=tuple(
                (self.param("ZEPHYR_BUILD_KCONFIG_OPTIONS", "") or "").splitlines()
            ),
            board_roots=tuple(
                self.container_workspace_path(path, container_alias)
                for path in (self.param("ZEPHYR_BUILD_BOARD_ROOTS", "") or "").splitlines()
            ),
            modules=tuple(
                self.container_workspace_path(path, container_alias)
                for path in (self.param("ZEPHYR_BUILD_MODULES", "") or "").splitlines()
            ),
            export_compile_commands=self.bool_param("ZEPHYR_BUILD_EXPORT_COMPILE_COMMANDS"),
            mode=str(build_mode),
        )

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_validate_command(build),
            timeout=int(self.param("ZEPHYR_BUILD_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("ZEPHYR_BUILD_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "ZEPHYR_BUILD_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param("ZEPHYR_BUILD_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                "ZEPHYR_BUILD_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


__all__ = ["validate_zephyr_build"]
