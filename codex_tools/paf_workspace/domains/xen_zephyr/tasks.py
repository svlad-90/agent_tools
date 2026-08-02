"""PAF tasks owned by the Xen/Zephyr domain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from paf import docker_runtime
from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime as environment_runtime
from paf_workspace.tasks import WorkspaceTask
from .lib import runtime as harness_runtime


class XenZephyrTask(WorkspaceTask):
    """Base task for Xen/Zephyr domain orchestration."""

    def harness_config(self) -> dict[str, object]:
        xen_zephyr = self.get_yaml_config().get("xen_zephyr", {})
        if not isinstance(xen_zephyr, dict):
            self.fail("YAML xen_zephyr section must be an object")
            raise AssertionError("unreachable")
        harness = xen_zephyr.get("harness")
        if not isinstance(harness, dict):
            self.fail("YAML xen_zephyr.harness section is required")
            raise AssertionError("unreachable")
        return harness

    def harness_args(self):
        config = self.harness_config()
        scenario = harness_runtime.load_scenario_data(config)

        product_dir = self.param("PRODUCT_DIR")
        product_path = self.path_param("PRODUCT_DIR") if product_dir else None
        log_file = config.get("log_file")
        log_path = self.path_param("RUNTIME_LOG_FILE") if self.param("RUNTIME_LOG_FILE") else None
        if log_path is None and isinstance(log_file, str):
            log_path = self.path_param_from_text(log_file)

        container_alias = self.harness_container_alias(config)
        container_workdir = self.container_workdir(container_alias)

        return harness_runtime.args_from_scenario(
            scenario,
            root=self.workspace_root(),
            product_dir=product_path,
            log_file=log_path,
            command=config.get("command") if isinstance(config.get("command"), str) else None,
            container_alias=container_alias,
            container_workdir=container_workdir,
            qemu_bin=config.get("qemu_bin") if isinstance(config.get("qemu_bin"), str) else None,
            xen_dtb=config.get("xen_dtb") if isinstance(config.get("xen_dtb"), str) else None,
            fail_on_timeout=bool(config.get("fail_on_timeout", False)),
            no_stop_on_match=bool(config.get("no_stop_on_match", False)),
        )

    def harness_container_alias(self, config: dict[str, object]) -> str:
        container = config.get("container")
        if isinstance(container, str) and container:
            return container
        return self.param("XEN_ZEPHYR_RUNTIME_CONTAINER", "zephyr-xen-workspace") or "zephyr-xen-workspace"

    def container_workdir(self, container_alias: str) -> str:
        config = docker_runtime.container_config(self, container_alias)
        workdir = config.get("workdir")
        if isinstance(workdir, str) and workdir:
            return workdir
        return "/home/builder/workspace"

    def prepare_harness_launch_command(self, args) -> None:
        if args.container_alias:
            args.launch_command = docker_runtime.docker_run_command(
                self,
                args.container_alias,
                harness_runtime.command_with_exports(args),
            )

    def path_param_from_text(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return self.workspace_root() / path

    def load_string_tuple(self, value: object, field: str) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            self.fail(f"YAML {field} must be a list of strings")
            raise AssertionError("unreachable")
        return tuple(value)

    def log_expanded_command(self, label: str, command: str) -> None:
        logger.info(f"{label} command after parameters substitution:")
        logger.info(f"cd {self.workspace_root()}")
        logger.info(command)

    def run_domain_command(
        self,
        command: str,
        *,
        timeout_param: str,
        hide_prefix: str,
        substitute_params: bool = True,
    ) -> None:
        self.subprocess_must_succeed(
            command,
            timeout=int(self.param(timeout_param, "0") or "0"),
            shell=True,
            substitute_params=substitute_params,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param(f"{hide_prefix}_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                f"{hide_prefix}_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param(f"{hide_prefix}_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                f"{hide_prefix}_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


class check_workspace_environment(XenZephyrTask):
    """Check workspace paths required by the Xen/Zephyr PAF domain."""

    def __init__(self):
        super().__init__()
        self.set_name(check_workspace_environment.__name__)

    def execute(self):
        root = self.workspace_root()
        self.assertion(root.exists(), f"WORKSPACE_ROOT does not exist: {root}")

        product_dir = self.path_param("PRODUCT_DIR")
        self.assertion(product_dir.exists(), f"PRODUCT_DIR does not exist: {product_dir}")

        paf_root = self.path_param("PAF_ROOT")
        self.assertion((paf_root / "paf_main.py").exists(), f"PAF is incomplete: {paf_root}")


class build_product(XenZephyrTask):
    """Build the product that provides Xen/Zephyr runtime artifacts."""

    def __init__(self):
        super().__init__()
        self.set_name(build_product.__name__)

    def execute(self):
        if self.bool_param("SKIP_PRODUCT_BUILD"):
            logger.info("Skip product build: SKIP_PRODUCT_BUILD is enabled")
            return
        command = self.param("PRODUCT_BUILD_CMD")
        if not command:
            logger.info("Skip product build: PRODUCT_BUILD_CMD is empty")
            return
        self.run_domain_command(
            command,
            timeout_param="PRODUCT_BUILD_CMD_TIMEOUT_SEC",
            hide_prefix="PRODUCT_BUILD_CMD",
        )


class write_artifact_manifest(XenZephyrTask):
    """Write a manifest for product artifacts consumed by the runtime harness."""

    def __init__(self):
        super().__init__()
        self.set_name(write_artifact_manifest.__name__)

    def execute(self):
        manifest_path = self.path_param("ARTIFACT_MANIFEST")
        artifact_names = self.param("ARTIFACTS", "") or ""
        artifacts = []
        root = self.workspace_root()

        for name in artifact_names.split():
            path = self.path_param(f"ARTIFACT_{name}")
            self.assertion(path.exists(), f"Artifact {name} does not exist: {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                stored_path = str(path.relative_to(root))
            except ValueError:
                stored_path = str(path)
            artifacts.append(
                {
                    "name": name,
                    "path": stored_path,
                    "sha256": digest,
                    "producer": self.param(
                        f"ARTIFACT_{name}_PRODUCER",
                        self.param("PRODUCT_NAME", "unknown"),
                    ),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"artifacts": artifacts}, indent=2) + "\n")
        logger.info(f"Wrote artifact manifest: {manifest_path}")


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
