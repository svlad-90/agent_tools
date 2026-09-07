from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import jsonschema
import yaml

from paf_workspace.domains.juce_repo_validation.lib.runtime import JuceRepoValidation
from paf_workspace.domains.juce_repo_validation.lib.runtime import juce_repo_validation_command


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
DOMAIN = AGENT_TOOLS_ROOT / "paf_workspace/domains/juce_repo_validation"


def test_juce_repo_validation_profile_uses_juce_environment() -> None:
    profile = yaml.safe_load((DOMAIN / "profiles/looprigger.yaml").read_text(encoding="utf-8"))

    assert profile["case"]["domain"] == "juce-repo-validation"
    assert {"domain": "environments"} in profile["uses"]
    assert profile["environments"]["juce_dev"]["image"] == "juce-dev"
    assert profile["environments"]["juce_dev"]["container"] == "juce-dev-workspace"


def test_juce_repo_validation_profiles_match_schema() -> None:
    schema = yaml.safe_load((DOMAIN / "schema.yaml").read_text(encoding="utf-8"))

    for profile_path in sorted((DOMAIN / "profiles").glob("*.yaml")):
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        jsonschema.validate(profile, schema)


def test_juce_repo_validation_scenario_runs_repo_checks_before_push_guard() -> None:
    scenario = ET.parse(DOMAIN / "scenarios/looprigger.xml")
    task_names = [task.attrib["name"] for task in scenario.findall(".//task")]

    repo_task = "paf_workspace.domains.juce_repo_validation.tasks.repo.validate_juce_repo"
    push_guard_task = "paf_workspace.tasks.record_push_guard_success"
    assert repo_task in task_names
    assert push_guard_task in task_names
    assert task_names.index(repo_task) < task_names.index(push_guard_task)

    scenario_names = {item.attrib["name"] for item in scenario.findall(".//scenario")}
    assert {"check-only", "ensure-only", "validate", "push-guard"} <= scenario_names


def test_juce_repo_validation_command_runs_expected_checks() -> None:
    command = juce_repo_validation_command(
        JuceRepoValidation(
            repo="/workspace/tasks/livelooping/dev/LoopRigger",
            build_dir="/workspace/tasks/livelooping/dev/LoopRigger/build-linux-juce",
            cmake_args=("-DLIVELOOPING_BUILD_JUCE_APP=ON",),
            task_dir="/workspace/tasks/livelooping",
        )
    )

    assert "git diff --check" in command
    assert "cmake -S . -B \"$BUILD_DIR\" -G Ninja" in command
    assert "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON" in command
    assert "-DLIVELOOPING_BUILD_JUCE_APP=ON" in command
    assert "cmake --build \"$BUILD_DIR\"" in command
    assert "ctest --test-dir \"$BUILD_DIR\" --output-on-failure" in command
    assert "task_check" in command
