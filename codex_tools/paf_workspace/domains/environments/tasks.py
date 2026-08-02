"""PAF tasks for reusable execution environments."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.tasks import WorkspaceTask


class EnvironmentTask(WorkspaceTask):
    """Base task for environment-domain orchestration."""

    def image_alias(self, default: str = "zephyr-xen") -> str:
        return self.param("ENVIRONMENT_IMAGE_ALIAS", default) or default

    def container_alias(self, default: str = "zephyr-xen-workspace") -> str:
        return self.param("ENVIRONMENT_CONTAINER_ALIAS", default) or default

    def build_network(self, default: str = "host") -> str:
        return self.param("ENVIRONMENT_BUILD_NETWORK", default) or default

    def image_config(self) -> dict[str, object]:
        from paf import docker_runtime

        return docker_runtime.image_config(self, self.image_alias())

    def image_name(self) -> str:
        image = self.image_config().get("image")
        self.assertion(isinstance(image, str) and image, f"Image alias is invalid: {self.image_alias()}")
        return image

    def image_exists(self, image: str) -> bool:
        result = self.exec_subprocess(
            ["docker", "image", "inspect", image],
            shell=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command_output=True,
            avoid_printing_command_output_reason="Docker image inspect output is hidden",
        )
        return result.exit_code == 0


class ensure_environment_image(EnvironmentTask):
    """Ensure a Docker image alias declared by PAF YAML is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_environment_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_ENVIRONMENT_IMAGE_ENSURE"):
            logger.info("Skip environment image ensure: SKIP_ENVIRONMENT_IMAGE_ENSURE is enabled")
            return
        image_config = self.image_config()
        image = self.image_name()
        if not self.image_exists(image):
            network = str(image_config.get("network") or self.build_network())
            self.subprocess_must_succeed(
                runtime.docker_dns_preflight_command(network=network),
                shell=False,
                communication_mode=CommunicationMode.PIPE_OUTPUT,
                interaction_mode=InteractionMode.IGNORE_INPUT,
            )
        self.ensure_docker_image(self.image_alias())


class check_environment_image(EnvironmentTask):
    """Check that a Docker image alias exists without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_environment_image.__name__)

    def execute(self):
        image = self.image_name()
        self.assertion(
            self.image_exists(image),
            f"Docker image for alias '{self.image_alias()}' is missing: {image}",
        )


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


class validate_zephyr_build(EnvironmentTask):
    """Configure and build a Zephyr app inside the Zephyr/Xen environment."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_build.__name__)

    def execute(self):
        zephyr = self.param("ZEPHYR_BUILD_ZEPHYR")
        app = self.param("ZEPHYR_BUILD_APP")
        board = self.param("ZEPHYR_BUILD_BOARD")
        build_dir = self.param("ZEPHYR_BUILD_DIR")
        for field_name, value in (
            ("ZEPHYR_BUILD_ZEPHYR", zephyr),
            ("ZEPHYR_BUILD_APP", app),
            ("ZEPHYR_BUILD_BOARD", board),
            ("ZEPHYR_BUILD_DIR", build_dir),
        ):
            self.assertion(value, f"Missing required parameter: {field_name}")

        build = runtime.ZephyrBuild(
            zephyr=str(zephyr),
            app=str(app),
            board=str(board),
            build_dir=str(build_dir),
            cmake_args=tuple((self.param("ZEPHYR_BUILD_CMAKE_ARGS", "") or "").splitlines()),
        )

        self.docker_subprocess_must_succeed(
            self.container_alias(),
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
