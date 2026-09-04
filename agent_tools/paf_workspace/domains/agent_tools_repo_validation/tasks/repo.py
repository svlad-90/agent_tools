"""PAF tasks for validating the Agent Tools repository."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.agent_tools_repo_validation.lib import runtime
from paf_workspace.domains.environments.tasks.base import EnvironmentTask


class validate_agent_tools_repo(EnvironmentTask):
    """Run Agent Tools repo checks inside the GUI-capable workspace image."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_agent_tools_repo.__name__)

    def execute(self):
        container_alias = self.container_alias("agent-workspace-tests-workspace")
        repo = self.container_workspace_path(
            self.param("AGENT_TOOLS_VALIDATE_REPO", "") or self.config_string("repo", "."),
            container_alias,
        )
        task_dir_param = self.param("AGENT_TOOLS_VALIDATE_TASK_DIR", "") or self.config_string("task_dir", "")
        task_dir = self.container_workspace_path(task_dir_param, container_alias) if task_dir_param else ""
        scope = self.param("AGENT_TOOLS_VALIDATE_SCOPE", "") or self.config_string("scope", "all")
        base_ref = self.param("AGENT_TOOLS_VALIDATE_BASE_REF", "") or self.config_string("base_ref", "HEAD")
        pytest_targets = self.lines_param("AGENT_TOOLS_VALIDATE_PYTEST_TARGETS") or self.config_list(
            "pytest_targets",
            ("agent_tools",),
        )
        timeout = int(
            self.param("AGENT_TOOLS_VALIDATE_TIMEOUT_SEC", "")
            or self.config_string("timeout_sec", "900")
        )
        require_real_gtk = self.bool_param(
            "AGENT_TOOLS_VALIDATE_REQUIRE_REAL_GTK",
            self.config_bool("require_real_gtk", True),
        )

        self.assertion(scope in ("all", "changed"), "AGENT_TOOLS_VALIDATE_SCOPE must be 'all' or 'changed'")
        self.assertion(repo, "Missing Agent Tools repo path")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.agent_tools_repo_validation_command(
                runtime.AgentToolsRepoValidation(
                    repo=repo,
                    task_dir=task_dir,
                    scope=str(scope),
                    base_ref=str(base_ref),
                    pytest_targets=tuple(pytest_targets),
                    require_real_gtk=require_real_gtk,
                )
            ),
            timeout=timeout,
            substitute_params=False,
            communication_mode=CommunicationMode.USE_PTY,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    def config(self) -> dict[str, object]:
        value = self.get_yaml_config().get("agent_tools_repo_validation", {})
        return value if isinstance(value, dict) else {}

    def config_string(self, key: str, default: str = "") -> str:
        value = self.config().get(key, default)
        return str(value) if value is not None else default

    def config_bool(self, key: str, default: bool = False) -> bool:
        value = self.config().get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    def config_list(self, key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
        value = self.config().get(key, list(default))
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str) and value:
            return tuple(line for line in value.splitlines() if line)
        return default


__all__ = ["validate_agent_tools_repo"]

