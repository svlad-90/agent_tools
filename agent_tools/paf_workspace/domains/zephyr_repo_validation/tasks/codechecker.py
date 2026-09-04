"""Zephyr CodeChecker validation tasks."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.zephyr_repo_validation.tasks.build import _zephyr_app_path
from paf_workspace.domains.zephyr_repo_validation.lib import runtime


class validate_zephyr_codechecker_diff(EnvironmentTask):
    """Run Zephyr's CodeChecker SCA path on changed source files."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_codechecker_diff.__name__)

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
        commit_range = self.param("ZEPHYR_REPO_CHECKS_COMMIT_RANGE")
        build_mode = self.param("ZEPHYR_BUILD_MODE", "west")
        for field_name, value in (
            ("ZEPHYR_BUILD_ZEPHYR", zephyr),
            ("ZEPHYR_BUILD_APP", app),
            ("ZEPHYR_BUILD_BOARD", board),
            ("ZEPHYR_BUILD_DIR", build_dir),
            ("ZEPHYR_REPO_CHECKS_COMMIT_RANGE", commit_range),
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
            export_compile_commands=True,
            mode=str(build_mode),
        )
        config_file = self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_CONFIG_FILE", ".codechecker.yml")
        mapped_config_file = str(config_file)
        if mapped_config_file.startswith("./"):
            mapped_config_file = f"{zephyr}/{mapped_config_file[2:]}"
        elif mapped_config_file.startswith("."):
            mapped_config_file = f"{zephyr}/{mapped_config_file}"
        elif mapped_config_file and not mapped_config_file.startswith("/"):
            mapped_config_file = self.container_workspace_path(mapped_config_file, container_alias)

        check = runtime.ZephyrCodeCheckerDiff(
            build=build,
            commit_range=str(commit_range),
            file_globs=tuple(
                (self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_FILE_GLOBS", "") or "").splitlines()
            ),
            analyzers=tuple(
                (self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_ANALYZERS", "cppcheck") or "")
                .splitlines()
            ),
            config_file=mapped_config_file,
            jobs=int(self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_JOBS", "1") or "1"),
            export=str(self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_EXPORT", "json") or "json"),
            parse_exit_status=self.bool_param(
                "ZEPHYR_REPO_CHECKS_CODECHECKER_PARSE_EXIT_STATUS",
                default=True,
            ),
        )

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_codechecker_diff_command(check),
            substitute_params=False,
            timeout=int(self.param("ZEPHYR_REPO_CHECKS_CODECHECKER_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("ZEPHYR_REPO_CHECKS_CODECHECKER_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "ZEPHYR_REPO_CHECKS_CODECHECKER_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param(
                "ZEPHYR_REPO_CHECKS_CODECHECKER_HIDE_OUTPUT"
            ),
            avoid_printing_command_output_reason=self.param(
                "ZEPHYR_REPO_CHECKS_CODECHECKER_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


__all__ = ["validate_zephyr_codechecker_diff"]
