"""Shared PAF task helpers for reusable execution environments."""

from __future__ import annotations

from pathlib import Path

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.domains.environments.lib.capabilities import normalize_capabilities
from paf_workspace.tasks import WorkspaceTask


class EnvironmentTask(WorkspaceTask):
    """Base task for environment-domain orchestration."""

    def image_alias(self, default: str = "zephyr-xen") -> str:
        profile_default = self.environment_string("zephyr_xen", "image", default)
        return self.param("ENVIRONMENT_IMAGE_ALIAS", profile_default) or profile_default

    def container_alias(self, default: str = "zephyr-xen-workspace") -> str:
        profile_default = self.environment_string("zephyr_xen", "container", default)
        return self.param("ENVIRONMENT_CONTAINER_ALIAS", profile_default) or profile_default

    def build_network(self, default: str = "host") -> str:
        profile_default = self.environment_string("zephyr_xen", "build_network", default)
        return self.param("ENVIRONMENT_BUILD_NETWORK", profile_default) or profile_default

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

    def image_capabilities(self, alias: str | None = None) -> tuple[str, ...]:
        config = self.image_config(alias)
        return normalize_capabilities(config.get("capabilities"))

    def container_config(self, alias: str | None = None) -> dict[str, object]:
        from paf import docker_runtime

        return docker_runtime.container_config(self, alias or self.container_alias())

    def container_workspace_path(self, path_text: str, container_alias: str) -> str:
        if not path_text:
            return ""
        workspace = self.workspace_root()
        host_path = Path(path_text)
        if not host_path.is_absolute():
            host_path = workspace / host_path
        host_path = host_path.resolve()
        config = self.container_config(container_alias)
        for mount in config.get("mounts", []):
            if not isinstance(mount, dict):
                continue
            source = mount.get("source")
            target = mount.get("target")
            if not isinstance(source, str) or not isinstance(target, str):
                continue
            try:
                relative = host_path.relative_to(Path(source).resolve())
            except ValueError:
                continue
            return str(Path(target) / relative)
        return str(host_path)

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

    def build_image_alias(self, image_alias: str):
        image_config = self.image_config(image_alias)
        image = self.image_name(image_alias)
        dockerfile = image_config.get("dockerfile")
        context = image_config.get("context")
        self.assertion(dockerfile and context, f"Image alias has no Dockerfile/context: {image_alias}")

        network = str(image_config.get("network") or self.build_network())
        self.subprocess_must_succeed(
            runtime.docker_dns_preflight_command(network=network),
            shell=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

        build_cmd = ["docker", "build", "-t", image, "-f", str(dockerfile)]
        if network:
            build_cmd.extend(["--network", network])
        if image_config.get("target"):
            build_cmd.extend(["--target", str(image_config["target"])])
        build_args = image_config.get("build_args", {})
        self.assertion(isinstance(build_args, dict), "docker image build_args must be an object")
        for key, value in build_args.items():
            build_cmd.extend(["--build-arg", f"{key}={value}"])
        build_cmd.append(str(context))

        self.subprocess_must_succeed(
            build_cmd,
            shell=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    def ensure_image_alias(self, image_alias: str, force_rebuild: bool = False):
        image_config = self.image_config(image_alias)
        image = self.image_name(image_alias)
        if force_rebuild:
            self.build_image_alias(image_alias)
            return
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
        force_rebuild = self.bool_param("ENVIRONMENT_FORCE_IMAGE_REBUILD")
        for alias in aliases:
            self.ensure_image_alias(alias, force_rebuild=force_rebuild)


class check_environment_image(EnvironmentTask):
    """Check that a Docker image alias exists without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_environment_image.__name__)

    def execute(self):
        self.check_image_alias(self.image_alias())


class check_workspace_tool_baseline(EnvironmentTask):
    """Run the capability-derived workspace tool baseline inside a container."""

    def __init__(self):
        super().__init__()
        self.set_name(check_workspace_tool_baseline.__name__)

    def execute(self):
        if self.bool_param("SKIP_WORKSPACE_TOOL_BASELINE_CHECK"):
            logger.info("Skip workspace tool baseline check: SKIP_WORKSPACE_TOOL_BASELINE_CHECK is enabled")
            return
        container_alias = self.container_alias()
        container_config = self.container_config(container_alias)
        image_alias = str(container_config.get("image") or self.image_alias())
        capabilities = self.image_capabilities(image_alias)
        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.workspace_tool_baseline_check_command(capabilities),
            timeout=int(self.param("WORKSPACE_TOOL_BASELINE_CHECK_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


class check_cpp_code_map_tools(EnvironmentTask):
    """Run cpp_code_map smoke and optional source parse inside a container."""

    def __init__(self):
        super().__init__()
        self.set_name(check_cpp_code_map_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_CPP_CODE_MAP_TOOLS_CHECK"):
            logger.info("Skip cpp_code_map tools check: SKIP_CPP_CODE_MAP_TOOLS_CHECK is enabled")
            return
        container_alias = self.container_alias()
        source = self.container_workspace_path(
            self.param("CPP_CODE_MAP_SOURCE", "") or "",
            container_alias,
        )
        compile_db = self.container_workspace_path(
            self.param("CPP_CODE_MAP_COMPILE_DB", "") or "",
            container_alias,
        )
        report = self.container_workspace_path(
            self.param("CPP_CODE_MAP_REPORT", "") or "",
            container_alias,
        )
        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.cpp_code_map_check_command(
                source=source,
                compile_db=compile_db,
                symbol=self.param("CPP_CODE_MAP_SYMBOL", "") or "",
                report=report,
            ),
            timeout=int(self.param("CPP_CODE_MAP_TOOLS_CHECK_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )
