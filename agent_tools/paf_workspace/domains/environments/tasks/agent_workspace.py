"""PAF tasks for the Agent Workspace test environment."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger

from paf_workspace.domains.environments.lib import runtime
from paf_workspace.domains.environments.tasks.base import EnvironmentTask


AGENT_WORKSPACE_TEST_COMMAND = """
set -euo pipefail
export PYTHONPATH=.:agent_tools
python3 -m pytest -q agent_tools/tools/agent_workspace/tests/test_agent_workspace_core.py
python3 -m pytest -q agent_tools/tools/agent_workspace/tests/test_agent_workspace_headless.py
""".strip()


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
        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.workspace_tool_baseline_check_command(self.image_capabilities(image_alias)),
            timeout=int(self.param("AGENT_WORKSPACE_TESTS_TOOLS_CHECK_TIMEOUT_SEC", "0") or "0"),
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
        command = self.param("AGENT_WORKSPACE_TEST_COMMAND", AGENT_WORKSPACE_TEST_COMMAND)
        self.docker_subprocess_must_succeed(
            self.environment_string("agent_workspace_tests", "container", "agent-workspace-tests-workspace"),
            command,
            timeout=int(self.param("AGENT_WORKSPACE_TEST_TIMEOUT_SEC", "0") or "0"),
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )
