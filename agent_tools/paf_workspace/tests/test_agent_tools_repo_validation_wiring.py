from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import jsonschema
import yaml


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
DOMAIN = AGENT_TOOLS_ROOT / "paf_workspace/domains/agent_tools_repo_validation"


def test_agent_tools_repo_validation_profile_uses_environment_domain() -> None:
    profile = yaml.safe_load((DOMAIN / "profiles/agent-tools-repo.yaml").read_text(encoding="utf-8"))

    assert profile["case"]["domain"] == "agent-tools-repo-validation"
    assert {"domain": "environments"} in profile["uses"]
    assert profile["environments"]["agent_workspace_tests"]["image"] == "agent-workspace-tests"
    assert profile["environments"]["agent_workspace_tests"]["container"] == "agent-workspace-tests-workspace"


def test_agent_tools_repo_validation_profiles_match_schema() -> None:
    schema = yaml.safe_load((DOMAIN / "schema.yaml").read_text(encoding="utf-8"))

    for profile_path in sorted((DOMAIN / "profiles").glob("*.yaml")):
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        jsonschema.validate(profile, schema)


def test_agent_tools_repo_validation_scenario_runs_repo_checks_before_push_guard() -> None:
    scenario = ET.parse(DOMAIN / "scenarios/agent-tools-repo.xml")
    task_names = [task.attrib["name"] for task in scenario.findall(".//task")]

    repo_task = "paf_workspace.domains.agent_tools_repo_validation.tasks.repo.validate_agent_tools_repo"
    push_guard_task = "paf_workspace.tasks.record_push_guard_success"
    assert repo_task in task_names
    assert push_guard_task in task_names
    assert task_names.index(repo_task) < task_names.index(push_guard_task)

    scenario_names = {item.attrib["name"] for item in scenario.findall(".//scenario")}
    assert {"check-only", "ensure-only", "validate", "push-guard"} <= scenario_names
