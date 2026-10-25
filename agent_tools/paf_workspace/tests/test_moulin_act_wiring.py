from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
SCENARIO = AGENT_TOOLS_ROOT / "paf_workspace/domains/environments/scenarios/moulin-act.xml"


def test_moulin_act_scenario_prepares_driver_before_validation() -> None:
    scenario = ET.parse(SCENARIO)
    task_names = [task.attrib["name"] for task in scenario.findall(".//task")]

    ensure_driver = "paf_workspace.domains.environments.tasks.act.ensure_agent_tools_act_image"
    ensure_runner = "paf_workspace.domains.environments.tasks.act.ensure_moulin_act_image"
    check_driver = "paf_workspace.domains.environments.tasks.act.check_agent_tools_act_image"
    check_runner = "paf_workspace.domains.environments.tasks.act.check_moulin_act_image"
    validate = "paf_workspace.domains.environments.tasks.act.validate_moulin_act"

    assert task_names.index(ensure_driver) < task_names.index(ensure_runner)
    assert task_names.index(check_driver) < task_names.index(check_runner)
    assert task_names.index(check_runner) < task_names.index(validate)
