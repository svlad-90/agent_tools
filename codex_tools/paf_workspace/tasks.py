"""Generic PAF tasks for workspace automation flows."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import SSHLocalClient
from paf.paf_impl import logger


class WorkspaceTask(SSHLocalClient):
    """Base task with workspace parameter helpers."""

    def param(self, name: str, default: str | None = None) -> str | None:
        return self.get_environment().getVariables().get(name, default)

    def workspace_root(self) -> Path:
        return Path(self.param("WORKSPACE_ROOT") or ".").resolve()

    def bool_param(self, name: str, default: bool = False) -> bool:
        value = self.param(name, str(int(default)))
        return str(value).lower() in ("1", "true", "yes", "on")

    def path_param(self, name: str, default: str | None = None) -> Path:
        value = self.param(name, default)
        if value is None:
            self.fail(f"Missing required parameter: {name}")
            raise AssertionError("unreachable")
        path = Path(value)
        if path.is_absolute():
            return path
        return self.workspace_root() / path

    def run_command_param(self, name: str, *, skip_param: str | None = None) -> None:
        if skip_param and self.bool_param(skip_param):
            logger.info(f"Skip command from {name}: {skip_param} is enabled")
            return

        command = self.param(name)
        if not command:
            logger.info(f"Skip command from {name}: parameter is empty")
            return

        timeout = int(self.param(f"{name}_TIMEOUT_SEC", "0") or "0")
        logger.info(f"Run command from {name}")
        self.subprocess_must_succeed(
            command,
            timeout=timeout,
            shell=True,
            substitute_params=True,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param(f"{name}_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                f"{name}_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param(f"{name}_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                f"{name}_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


class check_workspace_environment(WorkspaceTask):
    """Check that required workspace paths and optional tools exist."""

    def __init__(self):
        super().__init__()
        self.set_name(check_workspace_environment.__name__)

    def execute(self):
        root = self.workspace_root()
        self.assertion(root.exists(), f"WORKSPACE_ROOT does not exist: {root}")

        for param in ("PRODUCT_DIR",):
            path = self.path_param(param)
            self.assertion(path.exists(), f"{param} does not exist: {path}")
        if not self.param("HARNESS_CMD"):
            scenario_file = self.path_param("SCENARIO_FILE")
            self.assertion(scenario_file.exists(), f"SCENARIO_FILE does not exist: {scenario_file}")

        paf_root = self.path_param("PAF_ROOT")
        self.assertion((paf_root / "paf_main.py").exists(), f"PAF is incomplete: {paf_root}")


class ensure_runtime_environment(WorkspaceTask):
    """Run a reusable environment check/build command pair."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_runtime_environment.__name__)

    def execute(self):
        check_command = self.param("ENV_CHECK_CMD")
        if check_command:
            check_result = self.exec_subprocess(
                check_command,
                timeout=int(self.param("ENV_CHECK_CMD_TIMEOUT_SEC", "0") or "0"),
                shell=True,
                substitute_params=True,
                communication_mode=CommunicationMode.PIPE_OUTPUT,
                interaction_mode=InteractionMode.IGNORE_INPUT,
                avoid_printing_command=self.bool_param("ENV_CHECK_CMD_HIDE_COMMAND"),
                avoid_printing_command_reason=self.param(
                    "ENV_CHECK_CMD_HIDE_COMMAND_REASON",
                    "The command contains sensitive information",
                ),
                avoid_printing_command_output=self.bool_param("ENV_CHECK_CMD_HIDE_OUTPUT"),
                avoid_printing_command_output_reason=self.param(
                    "ENV_CHECK_CMD_HIDE_OUTPUT_REASON",
                    "The command output contains sensitive information",
                ),
            )
            if check_result.exit_code == 0:
                logger.info("Runtime environment check passed")
                return
            logger.warning("Runtime environment check failed; build/update will be attempted")

        self.run_command_param("ENV_BUILD_CMD", skip_param="SKIP_ENV_BUILD")


class build_product(WorkspaceTask):
    """Build the target product that provides runtime artifacts."""

    def __init__(self):
        super().__init__()
        self.set_name(build_product.__name__)

    def execute(self):
        self.run_command_param("PRODUCT_BUILD_CMD", skip_param="SKIP_PRODUCT_BUILD")


class write_artifact_manifest(WorkspaceTask):
    """Write a small JSON manifest for files produced by the build phase."""

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


class run_xen_harness_scenario(WorkspaceTask):
    """Run the workspace Xen/QEMU harness scenario."""

    def __init__(self):
        super().__init__()
        self.set_name(run_xen_harness_scenario.__name__)

    def execute(self):
        command = self.param("HARNESS_CMD")
        if not command:
            scenario_file = self.path_param("SCENARIO_FILE")
            command = (
                f"cd {self.workspace_root()} && "
                "codex_tools/xen_harness/scripts/run-scenario.sh "
                f"{scenario_file}"
            )
        self.subprocess_must_succeed(
            command,
            timeout=int(self.param("HARNESS_TIMEOUT_SEC", "0") or "0"),
            shell=True,
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("HARNESS_CMD_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "HARNESS_CMD_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param("HARNESS_CMD_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                "HARNESS_CMD_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


class validate_runtime_log(WorkspaceTask):
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
