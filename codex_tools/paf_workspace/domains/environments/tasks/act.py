"""PAF tasks for act-based reusable environments."""

from __future__ import annotations

from pathlib import Path

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.domains.environments.tasks.base import EnvironmentTask


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
        self.assertion(
            Path(self.substitute_parameters(repo_root)).is_dir(),
            f"Moulin checkout does not exist: {repo_root}",
        )
        self.subprocess_must_succeed(
            runtime.moulin_act_validate_command(run),
            shell=True,
            timeout=int(self.param("MOULIN_ACT_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


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
