"""Shared PAF task helpers for reusable execution environments."""

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

    def lines_param(self, name: str) -> tuple[str, ...]:
        return tuple(line for line in (self.param(name, "") or "").splitlines() if line)

    def environment_value(self, environment: str, key: str, default: object = "") -> object:
        environments = self.get_yaml_config().get("environments", {})
        if not isinstance(environments, dict):
            return default
        config = environments.get(environment, {})
        if not isinstance(config, dict):
            return default
        return config.get(key, default)

    def environment_string(self, environment: str, key: str, default: str = "") -> str:
        value = self.environment_value(environment, key, default)
        return str(value) if value is not None else default

    def environment_list(self, environment: str, key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
        value = self.environment_value(environment, key, list(default))
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str) and value:
            return tuple(line for line in value.splitlines() if line)
        return default

    def image_config(self, alias: str | None = None) -> dict[str, object]:
        from paf import docker_runtime

        return docker_runtime.image_config(self, alias or self.image_alias())

    def image_name(self, alias: str | None = None) -> str:
        image_alias = alias or self.image_alias()
        image = self.image_config(image_alias).get("image")
        self.assertion(isinstance(image, str) and image, f"Image alias is invalid: {image_alias}")
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

    def ensure_image_alias(self, image_alias: str):
        image_config = self.image_config(image_alias)
        image = self.image_name(image_alias)
        if not self.image_exists(image):
            network = str(image_config.get("network") or self.build_network())
            self.subprocess_must_succeed(
                runtime.docker_dns_preflight_command(network=network),
                shell=False,
                communication_mode=CommunicationMode.PIPE_OUTPUT,
                interaction_mode=InteractionMode.IGNORE_INPUT,
            )
        self.ensure_docker_image(image_alias)

    def check_image_alias(self, image_alias: str):
        image = self.image_name(image_alias)
        self.assertion(self.image_exists(image), f"Docker image for alias '{image_alias}' is missing: {image}")

    def docker_tools_check(self, container_alias: str, command: str, timeout_param: str):
        self.docker_subprocess_must_succeed(
            container_alias,
            command,
            timeout=int(self.param(timeout_param, "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    def host_command_check(self, command: str):
        self.subprocess_must_succeed(
            command,
            shell=True,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


class ensure_environment_image(EnvironmentTask):
    """Ensure a Docker image alias declared by PAF YAML is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_environment_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_ENVIRONMENT_IMAGE_ENSURE"):
            logger.info("Skip environment image ensure: SKIP_ENVIRONMENT_IMAGE_ENSURE is enabled")
            return
        aliases = (self.param("ENVIRONMENT_IMAGE_ALIASES", "") or "").split()
        if not aliases:
            aliases = [self.image_alias()]
        for alias in aliases:
            self.ensure_image_alias(alias)


class check_environment_image(EnvironmentTask):
    """Check that a Docker image alias exists without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_environment_image.__name__)

    def execute(self):
        self.check_image_alias(self.image_alias())
