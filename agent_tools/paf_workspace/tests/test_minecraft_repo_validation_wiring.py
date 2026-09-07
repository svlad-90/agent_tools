from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import jsonschema
import yaml

from paf_workspace.domains.minecraft_repo_validation.lib.runtime import MinecraftRepoValidation
from paf_workspace.domains.minecraft_repo_validation.lib.runtime import minecraft_repo_validation_command


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
DOMAIN = AGENT_TOOLS_ROOT / "paf_workspace/domains/minecraft_repo_validation"


def test_minecraft_repo_validation_profile_uses_minecraft_environment() -> None:
    profile = yaml.safe_load((DOMAIN / "profiles/mc-slayerworld.yaml").read_text(encoding="utf-8"))

    assert profile["case"]["domain"] == "minecraft-repo-validation"
    assert {"domain": "environments"} in profile["uses"]
    assert profile["environments"]["minecraft_paper"]["image"] == "minecraft-paper"
    assert profile["environments"]["minecraft_paper"]["container"] == "minecraft-paper-workspace"


def test_minecraft_repo_validation_profiles_match_schema() -> None:
    schema = yaml.safe_load((DOMAIN / "schema.yaml").read_text(encoding="utf-8"))

    for profile_path in sorted((DOMAIN / "profiles").glob("*.yaml")):
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        jsonschema.validate(profile, schema)


def test_minecraft_repo_validation_scenario_runs_repo_checks_before_push_guard() -> None:
    scenario = ET.parse(DOMAIN / "scenarios/mc-slayerworld.xml")
    task_names = [task.attrib["name"] for task in scenario.findall(".//task")]

    repo_task = "paf_workspace.domains.minecraft_repo_validation.tasks.repo.validate_minecraft_repo"
    push_guard_task = "paf_workspace.tasks.record_push_guard_success"
    assert repo_task in task_names
    assert push_guard_task in task_names
    assert task_names.index(repo_task) < task_names.index(push_guard_task)

    scenario_names = {item.attrib["name"] for item in scenario.findall(".//scenario")}
    assert {"check-only", "ensure-only", "validate", "push-guard"} <= scenario_names


def test_minecraft_repo_validation_command_runs_expected_checks() -> None:
    command = minecraft_repo_validation_command(
        MinecraftRepoValidation(
            repo="/workspace/tasks/minecraft_development/dev/mc.slayerworld",
            plugin_dir="/workspace/tasks/minecraft_development/dev/mc.slayerworld/plugins/frontline-factions",
            task_dir="/workspace/tasks/minecraft_development",
        )
    )

    assert "git diff --check" in command
    assert "python3 scripts/validate_configs.py" in command
    assert "python3 scripts/build_server.py --clean --allow-missing-artifacts" in command
    assert 'gradle --project-dir "$PLUGIN_DIR" test jar' in command
    assert "META-INF/services/java.sql.Driver" in command
    assert "org/sqlite/native/Linux/x86_64/libsqlitejdbc.so" in command
    assert "task_check" in command
