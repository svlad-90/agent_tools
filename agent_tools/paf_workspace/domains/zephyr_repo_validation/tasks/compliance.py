"""Zephyr compliance validation tasks."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.zephyr_repo_validation.lib import runtime


class validate_zephyr_compliance(EnvironmentTask):
    """Run scoped Zephyr compliance checks for formatting and file hygiene."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_zephyr_compliance.__name__)

    def execute(self):
        container_alias = self.container_alias()
        zephyr = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_ZEPHYR", "") or "",
            container_alias,
        )
        output = self.container_workspace_path(
            self.param("ZEPHYR_REPO_CHECKS_COMPLIANCE_OUTPUT", "compliance.xml") or "",
            container_alias,
        )
        commit_range = self.param("ZEPHYR_REPO_CHECKS_COMMIT_RANGE", "HEAD~1..HEAD")
        modules = self.lines_param("ZEPHYR_REPO_CHECKS_COMPLIANCE_MODULES")
        excludes = self.lines_param("ZEPHYR_REPO_CHECKS_COMPLIANCE_EXCLUDES")
        self.assertion(zephyr, "Missing required parameter: ZEPHYR_REPO_CHECKS_ZEPHYR")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.zephyr_compliance_command(
                runtime.ZephyrCompliance(
                    zephyr=zephyr,
                    commit_range=str(commit_range),
                    output=output,
                    modules=modules,
                    excludes=excludes,
                    jobs=int(self.param("ZEPHYR_REPO_CHECKS_COMPLIANCE_JOBS", "1") or "1"),
                )
            ),
            timeout=int(self.param("ZEPHYR_REPO_CHECKS_COMPLIANCE_TIMEOUT_SEC", "0") or "0"),
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


__all__ = ["validate_zephyr_compliance"]
