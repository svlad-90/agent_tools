"""PAF tasks for validating Minecraft repositories."""

from __future__ import annotations

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode

from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.minecraft_repo_validation.lib import runtime


class validate_minecraft_repo(EnvironmentTask):
    """Run Minecraft repository checks inside the minecraft-paper image."""

    def __init__(self):
        super().__init__()
        self.set_name(validate_minecraft_repo.__name__)

    def execute(self):
        container_alias = self.container_alias("minecraft-paper-workspace")
        repo = self.container_workspace_path(
            self.param("MINECRAFT_VALIDATE_REPO", "") or self.config_string("repo", ""),
            container_alias,
        )
        plugin_dir = self.container_workspace_path(
            self.param("MINECRAFT_VALIDATE_PLUGIN_DIR", "") or self.config_string("plugin_dir", ""),
            container_alias,
        )
        task_dir_param = self.param("MINECRAFT_VALIDATE_TASK_DIR", "") or self.config_string("task_dir", "")
        task_dir = self.container_workspace_path(task_dir_param, container_alias) if task_dir_param else ""
        timeout = int(
            self.param("MINECRAFT_VALIDATE_TIMEOUT_SEC", "")
            or self.config_string("timeout_sec", "900")
        )
        require_sqlite_bundle = self.bool_param(
            "MINECRAFT_VALIDATE_REQUIRE_SQLITE_BUNDLE",
            self.config_bool("require_sqlite_bundle", True),
        )

        self.assertion(repo, "Missing Minecraft repo path")
        self.assertion(plugin_dir, "Missing Minecraft plugin directory")

        self.docker_subprocess_must_succeed(
            container_alias,
            runtime.minecraft_repo_validation_command(
                runtime.MinecraftRepoValidation(
                    repo=repo,
                    plugin_dir=plugin_dir,
                    task_dir=task_dir,
                    require_sqlite_bundle=require_sqlite_bundle,
                )
            ),
            timeout=timeout,
            substitute_params=False,
            communication_mode=CommunicationMode.USE_PTY,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    def config(self) -> dict[str, object]:
        value = self.get_yaml_config().get("minecraft_repo_validation", {})
        return value if isinstance(value, dict) else {}

    def config_string(self, key: str, default: str = "") -> str:
        value = self.config().get(key, default)
        return str(value) if value is not None else default

    def config_bool(self, key: str, default: bool = False) -> bool:
        value = self.config().get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")
