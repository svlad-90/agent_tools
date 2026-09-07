"""PAF tasks for validating JUCE/CMake repositories."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.juce_repo_validation.lib import runtime


class validate_juce_repo(EnvironmentTask):
    """Run JUCE/CMake repository checks inside the juce-dev image."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_juce_repo.__name__)

    def execute(self):
        container_alias = self.container_alias("juce-dev-workspace")
        repo = self.container_workspace_path(
            self.param("JUCE_VALIDATE_REPO", "") or self.config_string("repo", ""),
            container_alias,
        )
        build_dir = self.container_workspace_path(
            self.param("JUCE_VALIDATE_BUILD_DIR", "") or self.config_string("build_dir", "build-juce"),
            container_alias,
        )
        task_dir_param = self.param("JUCE_VALIDATE_TASK_DIR", "") or self.config_string("task_dir", "")
        task_dir = self.container_workspace_path(task_dir_param, container_alias) if task_dir_param else ""
        timeout = int(
            self.param("JUCE_VALIDATE_TIMEOUT_SEC", "")
            or self.config_string("timeout_sec", "900")
        )

        self.assertion(repo, "Missing JUCE repo path")
        self.assertion(build_dir, "Missing JUCE build directory")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.juce_repo_validation_command(
                runtime.JuceRepoValidation(
                    repo=repo,
                    build_dir=build_dir,
                    cmake_args=self.lines_param("JUCE_VALIDATE_CMAKE_ARGS") or self.config_list("cmake_args"),
                    build_args=self.lines_param("JUCE_VALIDATE_BUILD_ARGS") or self.config_list("build_args"),
                    ctest_args=self.lines_param("JUCE_VALIDATE_CTEST_ARGS") or self.config_list("ctest_args"),
                    task_dir=task_dir,
                )
            ),
            timeout=timeout,
            substitute_params=False,
            communication_mode=CommunicationMode.USE_PTY,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    def config(self) -> dict[str, object]:
        value = self.get_yaml_config().get("juce_repo_validation", {})
        return value if isinstance(value, dict) else {}

    def config_string(self, key: str, default: str = "") -> str:
        value = self.config().get(key, default)
        return str(value) if value is not None else default

    def config_list(self, key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
        value = self.config().get(key, list(default))
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str) and value:
            return tuple(line for line in value.splitlines() if line)
        return default


__all__ = ["validate_juce_repo"]
