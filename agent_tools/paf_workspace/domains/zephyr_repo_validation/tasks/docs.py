"""Zephyr documentation validation tasks."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.zephyr_repo_validation.lib import runtime


class validate_zephyr_docs_coverage(EnvironmentTask):
    """Generate Zephyr Doxygen coverage JSON inside the selected environment."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_docs_coverage.__name__)

    def execute(self):
        container_alias = self.container_alias()
        zephyr = self.container_workspace_path(
            self.param("ZEPHYR_DOCS_ZEPHYR", "") or "",
            container_alias,
        )
        build_dir = self.container_workspace_path(
            self.param("ZEPHYR_DOCS_BUILD_DIR", "") or "",
            container_alias,
        )
        for field_name, value in (
            ("ZEPHYR_DOCS_ZEPHYR", zephyr),
            ("ZEPHYR_DOCS_BUILD_DIR", build_dir),
        ):
            self.assertion(value, f"Missing required parameter: {field_name}")

        docs = runtime.ZephyrDocsCoverage(
            zephyr=str(zephyr),
            build_dir=str(build_dir),
        )

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_docs_coverage_command(docs),
            timeout=int(self.param("ZEPHYR_DOCS_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
            avoid_printing_command=self.bool_param("ZEPHYR_DOCS_HIDE_COMMAND"),
            avoid_printing_command_reason=self.param(
                "ZEPHYR_DOCS_HIDE_COMMAND_REASON",
                "The command contains sensitive information",
            ),
            avoid_printing_command_output=self.bool_param("ZEPHYR_DOCS_HIDE_OUTPUT"),
            avoid_printing_command_output_reason=self.param(
                "ZEPHYR_DOCS_HIDE_OUTPUT_REASON",
                "The command output contains sensitive information",
            ),
        )


class validate_zephyr_docs_diff(EnvironmentTask):
    """Compare Zephyr Doxygen coverage and top-level group outputs."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_docs_diff.__name__)

    def execute(self):
        container_alias = self.container_alias()
        zephyr = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_ZEPHYR", "") or "",
            container_alias,
        )
        reference = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_REFERENCE", "") or "",
            container_alias,
        )
        comparison = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_COMPARISON", "") or "",
            container_alias,
        )
        xml_dir = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_XML_DIR", "") or "",
            container_alias,
        )
        summary = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_SUMMARY", "") or "",
            container_alias,
        )
        reference_prefix = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_REFERENCE_PREFIX", "") or "",
            container_alias,
        )
        comparison_prefix = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_DOCS_COMPARISON_PREFIX", "") or "",
            container_alias,
        )
        for field_name, value in (
            ("ZEPHYR_REPO_CHECKS_ZEPHYR", zephyr),
            ("ZEPHYR_REPO_CHECKS_DOCS_REFERENCE", reference),
            ("ZEPHYR_REPO_CHECKS_DOCS_COMPARISON", comparison),
            ("ZEPHYR_REPO_CHECKS_DOCS_XML_DIR", xml_dir),
            ("ZEPHYR_REPO_CHECKS_DOCS_SUMMARY", summary),
        ):
            self.assertion(value, f"Missing required parameter: {field_name}")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_docs_diff_command(
                runtime.ZephyrDocsDiff(
                    zephyr=zephyr,
                    reference_coverage=reference,
                    comparison_coverage=comparison,
                    xml_dir=xml_dir,
                    summary=summary,
                    reference_prefix=reference_prefix,
                    comparison_prefix=comparison_prefix,
                    warn_paths=self.lines_param("ZEPHYR_REPO_CHECKS_DOCS_WARN_PATHS"),
                )
            ),
            timeout=int(self.param("ZEPHYR_REPO_CHECKS_DOCS_DIFF_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


__all__ = ["validate_zephyr_docs_coverage", "validate_zephyr_docs_diff"]
