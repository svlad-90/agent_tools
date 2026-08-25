"""PAF tasks for the Agent Workspace test environment."""

from __future__ import annotations

import os

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.domains.environments.tasks.base import EnvironmentTask


AGENT_WORKSPACE_TEST_COMMAND = """
set -euo pipefail
export PYTHONPATH=.:agent_tools
export PYTHONUNBUFFERED=1
echo "Agent Workspace component tests: start"
timeout --foreground --signal=INT --kill-after=10s 300s \
  xvfb-run -a python3 -X faulthandler -m pytest -vv --maxfail=1 -ra \
  agent_tools/agent_workspace/components
echo "Agent Workspace component tests: passed"
""".strip()
AGENT_WORKSPACE_TEST_TIMEOUT_SEC = 600
AGENT_WORKSPACE_TESTS_TOOLS_CHECK_TIMEOUT_SEC = 120


class ensure_agent_workspace_tests_image(EnvironmentTask):
    """Ensure the Agent Workspace test image is available."""

    def __init__(self):
        super().__init__()
        self.set_name(ensure_agent_workspace_tests_image.__name__)

    def execute(self):
        if self.bool_param("SKIP_AGENT_WORKSPACE_TESTS_IMAGE_ENSURE"):
            logger.info("Skip Agent Workspace test image ensure")
            return
        self.ensure_image_alias(
            self.environment_string("agent_workspace_tests", "image", "agent-workspace-tests"),
            force_rebuild=self.bool_param("ENVIRONMENT_FORCE_IMAGE_REBUILD"),
        )


class check_agent_workspace_tests_image(EnvironmentTask):
    """Check the Agent Workspace test image without building it."""

    def __init__(self):
        super().__init__()
        self.set_name(check_agent_workspace_tests_image.__name__)

    def execute(self):
        self.check_image_alias(self.environment_string("agent_workspace_tests", "image", "agent-workspace-tests"))


class check_agent_workspace_tests_tools(EnvironmentTask):
    """Run Agent Workspace image dependency smoke checks."""

    def __init__(self):
        super().__init__()
        self.set_name(check_agent_workspace_tests_tools.__name__)

    def execute(self):
        if self.bool_param("SKIP_AGENT_WORKSPACE_TESTS_TOOLS_CHECK"):
            logger.info("Skip Agent Workspace test tool checks")
            return
        container_alias = self.environment_string(
            "agent_workspace_tests",
            "container",
            "agent-workspace-tests-workspace",
        )
        image_alias = self.environment_string("agent_workspace_tests", "image", "agent-workspace-tests")
        timeout = int(
            self.param(
                "AGENT_WORKSPACE_TESTS_TOOLS_CHECK_TIMEOUT_SEC",
                str(AGENT_WORKSPACE_TESTS_TOOLS_CHECK_TIMEOUT_SEC),
            )
        )
        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.workspace_tool_baseline_check_command(self.image_capabilities(image_alias)),
            timeout=timeout,
            substitute_params=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )


class run_agent_workspace_tests(EnvironmentTask):
    """Run Agent Workspace tests inside the reusable GUI-capable image."""

    def __init__(self):
        super().__init__()
        self.set_name(run_agent_workspace_tests.__name__)

    def execute(self):
        command = self.param(
            "AGENT_WORKSPACE_TEST_COMMAND",
            os.environ.get("AGENT_WORKSPACE_TEST_COMMAND", AGENT_WORKSPACE_TEST_COMMAND),
        )
        timeout = int(self.param("AGENT_WORKSPACE_TEST_TIMEOUT_SEC", str(AGENT_WORKSPACE_TEST_TIMEOUT_SEC)))
        self.docker_subprocess_must_succeed(
            self.environment_string("agent_workspace_tests", "container", "agent-workspace-tests-workspace"),
            command,
            timeout=timeout,
            communication_mode=CommunicationMode.USE_PTY,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )
