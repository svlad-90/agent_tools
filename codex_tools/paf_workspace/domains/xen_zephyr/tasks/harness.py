"""PAF runtime harness tasks for the Xen/Zephyr domain."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime as environment_runtime
from paf_workspace.domains.xen_zephyr.lib import runtime as harness_runtime
from paf_workspace.domains.xen_zephyr.tasks.base import XenZephyrTask


class load_harness_scenario(XenZephyrTask):
    """Load and validate the domain YAML Xen/QEMU harness scenario."""

    def __init__(self):
        super().__init__()
        self.set_name(load_harness_scenario.__name__)

    def execute(self):
        scenario = harness_runtime.load_scenario_data(self.harness_config())
        logger.info(f"Loaded Xen/QEMU harness scenario: {scenario.name}")


class prepare_harness_inputs(XenZephyrTask):
    """Prepare and preflight inputs consumed by the Xen/QEMU harness."""

    def __init__(self):
        super().__init__()
        self.set_name(prepare_harness_inputs.__name__)

    def execute(self):
        args = self.harness_args()
        scenario = getattr(args, "scenario_config", None)
        if scenario and scenario.domu_build and not args.skip_build:
            build = environment_runtime.ZephyrBuild(
                zephyr=scenario.domu_build.zephyr,
                app=scenario.domu_build.app,
                board=scenario.domu_build.board,
                build_dir=scenario.domu_build.build_dir,
                cmake_args=scenario.domu_build.cmake_args,
                kconfig_options=scenario.domu_build.kconfig_options,
                board_roots=scenario.domu_build.board_roots,
                modules=scenario.domu_build.modules,
                export_compile_commands=scenario.domu_build.export_compile_commands,
                mode=scenario.domu_build.mode,
            )
            self.docker_subprocess_must_succeed(
                args.container_alias,
                environment_runtime.zephyr_validate_command(build),
                timeout=int(self.param("HARNESS_PREPARE_TIMEOUT_SEC", "0") or "0"),
                communication_mode=CommunicationMode.PIPE_OUTPUT,
                interaction_mode=InteractionMode.IGNORE_INPUT,
                avoid_printing_command=self.bool_param("HARNESS_PREPARE_HIDE_COMMAND"),
                avoid_printing_command_reason=self.param(
                    "HARNESS_PREPARE_HIDE_COMMAND_REASON",
                    "The command contains sensitive information",
                ),
                avoid_printing_command_output=self.bool_param("HARNESS_PREPARE_HIDE_OUTPUT"),
                avoid_printing_command_output_reason=self.param(
                    "HARNESS_PREPARE_HIDE_OUTPUT_REASON",
                    "The command output contains sensitive information",
                ),
            )
            args.skip_build = True
        result = harness_runtime.prepare_inputs(args)
        self.assertion(result == 0, f"Xen/QEMU harness prepare failed: {result}")


class run_harness_command(XenZephyrTask):
    """Run the Xen/QEMU command and evaluate live harness expectations."""

    def __init__(self):
        super().__init__()
        self.set_name(run_harness_command.__name__)

    def execute(self):
        args = self.harness_args()
        args.skip_build = True
        args.skip_preflight = True
        self.prepare_harness_launch_command(args)
        self.log_expanded_command("HARNESS_RUN", harness_runtime.shell_command(args))
        result = harness_runtime.run_prepared_args(args)
        self.assertion(result == 0, f"Xen/QEMU harness run failed: {result}")


class validate_runtime_log(XenZephyrTask):
    """Validate runtime log markers declared by the YAML case profile."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_runtime_log.__name__)

    def execute(self):
        log_path = self.path_param("RUNTIME_LOG_FILE")
        self.assertion(
            log_path.exists(),
            f"RUNTIME_LOG_FILE does not exist: {log_path}",
        )

        validation = self.get_yaml_config().get("validation", {})
        expected = validation.get("expected", [])
        forbidden = validation.get("forbidden", [])
        log_content = log_path.read_text(encoding="utf-8", errors="replace")

        for marker in expected:
            self.assertion(
                marker in log_content,
                f"Expected runtime marker was not found: {marker}",
            )
            logger.info(f"Found expected runtime marker: {marker}")

        for marker in forbidden:
            self.assertion(
                marker not in log_content,
                f"Forbidden runtime marker was found: {marker}",
            )
            logger.info(f"Forbidden runtime marker is absent: {marker}")
