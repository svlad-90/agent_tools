"""PAF tasks for reusable execution environments."""

from __future__ import annotations

from pathlib import Path

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


class ensure_codex_tools_act_image(EnvironmentTask):
    """Ensure the Codex tools act driver image is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_codex_tools_act_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_CODEX_TOOLS_ACT_IMAGE_ENSURE"):
            logger.info("Skip Codex tools act image ensure: SKIP_CODEX_TOOLS_ACT_IMAGE_ENSURE is enabled")
            return
        self.ensure_image_alias(self.environment_string("codex_tools_act", "image", "codex-tools-act"))


class check_codex_tools_act_image(EnvironmentTask):
    """Check the Codex tools act driver image without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_codex_tools_act_image.__name__)

    def execute(self):
        self.check_image_alias(self.environment_string("codex_tools_act", "image", "codex-tools-act"))


class ensure_moulin_act_image(EnvironmentTask):
    """Ensure the Moulin act runner image is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_moulin_act_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_MOULIN_ACT_IMAGE_ENSURE"):
            logger.info("Skip Moulin act image ensure: SKIP_MOULIN_ACT_IMAGE_ENSURE is enabled")
            return
        self.ensure_image_alias(self.environment_string("moulin_act", "image", "moulin-act"))


class check_moulin_act_image(EnvironmentTask):
    """Check the Moulin act runner image without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_moulin_act_image.__name__)

    def execute(self):
        self.check_image_alias(self.environment_string("moulin_act", "image", "moulin-act"))


class ensure_zephyr_xenlib_act_image(EnvironmentTask):
    """Ensure the zephyr-xenlib act runner image is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_zephyr_xenlib_act_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_ZEPHYR_XENLIB_ACT_IMAGE_ENSURE"):
            logger.info("Skip zephyr-xenlib act image ensure: SKIP_ZEPHYR_XENLIB_ACT_IMAGE_ENSURE is enabled")
            return
        self.ensure_image_alias(self.environment_string("zephyr_xenlib_act", "image", "zephyr-xenlib-act"))


class check_zephyr_xenlib_act_image(EnvironmentTask):
    """Check the zephyr-xenlib act runner image without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_zephyr_xenlib_act_image.__name__)

    def execute(self):
        self.check_image_alias(self.environment_string("zephyr_xenlib_act", "image", "zephyr-xenlib-act"))


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


class check_codex_tools_act_tools(EnvironmentTask):
    """Run Codex tools act driver smoke checks inside its Docker image."""

    def __init__(self):
        super().__init__()
        self.set_name(check_codex_tools_act_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_CODEX_TOOLS_ACT_TOOLS_CHECK"):
            logger.info("Skip Codex tools act tools check: SKIP_CODEX_TOOLS_ACT_TOOLS_CHECK is enabled")
            return
        self.docker_tools_check(
            self.environment_string("codex_tools_act", "container", "codex-tools-act-workspace"),
            runtime.CODEX_TOOLS_ACT_TOOL_CHECK_COMMAND,
            "CODEX_TOOLS_ACT_TOOLS_CHECK_TIMEOUT_SEC",
        )


class validate_codex_tools_act(EnvironmentTask):
    """Run the Codex tools GitHub Actions workflow through act."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_codex_tools_act.__name__)

    def execute(self):
        run = runtime.CodexToolsActRun(
            workflow=self.param(
                "CODEX_TOOLS_ACT_WORKFLOW",
                self.environment_string("codex_tools_act", "workflow", ".github/workflows/diff-report.yml"),
            ),
            runner_image=self.param(
                "CODEX_TOOLS_ACT_RUNNER_IMAGE",
                self.environment_string("codex_tools_act", "runner_image", "ghcr.io/catthehacker/ubuntu:act-latest"),
            ),
            extra_args=self.lines_param("CODEX_TOOLS_ACT_ARGS"),
        )
        self.docker_subprocess_must_succeed(
            self.environment_string("codex_tools_act", "container", "codex-tools-act-workspace"),
            runtime.codex_tools_act_validate_command(run),
            timeout=int(self.param("CODEX_TOOLS_ACT_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


class check_moulin_act_tools(EnvironmentTask):
    """Run Moulin act runner smoke checks."""

    def __init__(self):
        super().__init__()
        self.set_name(check_moulin_act_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_MOULIN_ACT_TOOLS_CHECK"):
            logger.info("Skip Moulin act tools check: SKIP_MOULIN_ACT_TOOLS_CHECK is enabled")
            return
        self.host_command_check("act --version")
        self.docker_tools_check(
            self.environment_string("moulin_act", "container", "moulin-act-workspace"),
            runtime.ACT_RUNNER_TOOL_CHECK_COMMAND,
            "MOULIN_ACT_TOOLS_CHECK_TIMEOUT_SEC",
        )


class validate_moulin_act(EnvironmentTask):
    """Run Moulin's GitHub Actions build job through act."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_moulin_act.__name__)

    def execute(self):
        repo_root = self.param(
            "MOULIN_REPO_ROOT",
            self.environment_string("moulin_act", "repo_root", "${WORKSPACE_ROOT}/moulin-svlad-90"),
        )
        run = runtime.MoulinActRun(
            repo_root=repo_root,
            runner_image=self.image_name(self.environment_string("moulin_act", "image", "moulin-act")),
            extra_args=self.lines_param("MOULIN_ACT_ARGS"),
        )
        self.assertion(Path(self.substitute_parameters(repo_root)).is_dir(), f"Moulin checkout does not exist: {repo_root}")
        self.subprocess_must_succeed(
            runtime.moulin_act_validate_command(run),
            shell=True,
            timeout=int(self.param("MOULIN_ACT_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


class check_zephyr_xenlib_act_tools(EnvironmentTask):
    """Run zephyr-xenlib act runner smoke checks."""

    def __init__(self):
        super().__init__()
        self.set_name(check_zephyr_xenlib_act_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_ZEPHYR_XENLIB_ACT_TOOLS_CHECK"):
            logger.info("Skip zephyr-xenlib act tools check: SKIP_ZEPHYR_XENLIB_ACT_TOOLS_CHECK is enabled")
            return
        self.host_command_check("act --version")
        self.docker_tools_check(
            self.environment_string("zephyr_xenlib_act", "container", "zephyr-xenlib-act-workspace"),
            runtime.ZEPHYR_XENLIB_ACT_TOOL_CHECK_COMMAND,
            "ZEPHYR_XENLIB_ACT_TOOLS_CHECK_TIMEOUT_SEC",
        )


class validate_zephyr_xenlib_act(EnvironmentTask):
    """Run zephyr-xenlib's GitHub Actions build workflow through act."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_xenlib_act.__name__)

    def execute(self):
        repo_root = self.param(
            "ZEPHYR_XENLIB_REPO_ROOT",
            self.environment_string(
                "zephyr_xenlib_act",
                "repo_root",
                "${WORKSPACE_ROOT}/zephyr-xenlib-builders/dev/zephyr-xenlib",
            ),
        )
        token_file = self.param(
            "ZEPHYR_XENLIB_TOKEN_FILE",
            self.environment_string("zephyr_xenlib_act", "token_file", str(Path.home() / "Projects/token")),
        )
        run = runtime.ZephyrXenlibActRun(
            repo_root=repo_root,
            runner_image=self.image_name(self.environment_string("zephyr_xenlib_act", "image", "zephyr-xenlib-act")),
            token_file=token_file,
            targets=self.lines_param("ZEPHYR_XENLIB_ACT_TARGETS")
            or self.environment_list("zephyr_xenlib_act", "targets"),
            project=self.param(
                "ZEPHYR_XENLIB_ACT_PROJECT",
                self.environment_string("zephyr_xenlib_act", "project", "zephyr-dom0-xt"),
            ),
            extra_args=self.lines_param("ZEPHYR_XENLIB_ACT_ARGS"),
        )
        self.assertion(
            Path(self.substitute_parameters(repo_root)).is_dir(),
            f"zephyr-xenlib checkout does not exist: {repo_root}",
        )
        self.subprocess_must_succeed(
            runtime.zephyr_xenlib_act_validate_command(run),
            shell=True,
            timeout=int(self.param("ZEPHYR_XENLIB_ACT_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("ZEPHYR_XENLIB_ACT_HIDE_COMMAND"),
            avoid_printing_command_reason="The command can reference a token file path",
            avoid_printing_command_output=self.bool_param("ZEPHYR_XENLIB_ACT_HIDE_OUTPUT"),
            avoid_printing_command_output_reason="The command output can contain workflow secrets",
        )
