from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import jsonschema
import yaml


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
ZEPHYR_DOMAIN = AGENT_TOOLS_ROOT / "paf_workspace/domains/zephyr_repo_validation"
ENVIRONMENTS_DOMAIN = AGENT_TOOLS_ROOT / "paf_workspace/domains/environments"


def test_zephyr_repo_validation_profile_uses_environment_domain() -> None:
    profile = yaml.safe_load(
        (ZEPHYR_DOMAIN / "profiles/zephyr-repo-checks.yaml").read_text(encoding="utf-8")
    )

    assert profile["case"]["domain"] == "zephyr-repo-validation"
    assert {"domain": "environments"} in profile["uses"]
    assert profile["environments"]["zephyr_repo"]["image"] == "zephyr-repo-checks"
    assert profile["environments"]["zephyr_repo"]["container"] == "zephyr-repo-checks-workspace"


def test_zephyr_repo_validation_profiles_match_schema() -> None:
    schema = yaml.safe_load((ZEPHYR_DOMAIN / "schema.yaml").read_text(encoding="utf-8"))

    for profile_path in sorted((ZEPHYR_DOMAIN / "profiles").glob("*.yaml")):
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        jsonschema.validate(profile, schema)


def test_zephyr_repo_validation_scenario_owns_repo_check_tasks() -> None:
    scenario = ET.parse(ZEPHYR_DOMAIN / "scenarios/zephyr-repo-checks.xml")
    task_names = {task.attrib["name"] for task in scenario.findall(".//task")}

    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.docs.validate_zephyr_docs_coverage"
        in task_names
    )
    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.docs.validate_zephyr_docs_diff"
        in task_names
    )
    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.compliance.validate_zephyr_compliance"
        in task_names
    )
    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.codechecker."
        "validate_zephyr_codechecker_diff"
        in task_names
    )
    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.west."
        "prepare_zephyr_west_workspace"
        in task_names
    )
    assert (
        "paf_workspace.domains.zephyr_repo_validation.tasks.build.validate_zephyr_build"
        in task_names
    )
    assert all(".domains.environments.tasks.zephyr_repo" not in name for name in task_names)

    scenario_names = {scenario.attrib["name"] for scenario in scenario.findall(".//scenario")}
    assert "west-update" in scenario_names
    assert "compliance-with-west-update" in scenario_names


def test_environment_domain_no_longer_exposes_zephyr_repo_validation_scenario() -> None:
    assert not (ENVIRONMENTS_DOMAIN / "scenarios/zephyr-docs.xml").exists()

    zephyr_xen_tasks = (ENVIRONMENTS_DOMAIN / "tasks/zephyr_xen.py").read_text(encoding="utf-8")
    assert "validate_zephyr_docs_coverage" not in zephyr_xen_tasks
    assert "validate_zephyr_build" not in zephyr_xen_tasks
