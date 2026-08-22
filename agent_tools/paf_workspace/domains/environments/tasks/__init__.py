"""Compatibility exports for reusable environment PAF tasks.

New scenarios should import task classes from the environment-specific modules:
`tasks.base`, `tasks.zephyr_xen`, and `tasks.act`.
"""

from __future__ import annotations

from paf_workspace.domains.environments.tasks.act import check_agent_tools_act_image
from paf_workspace.domains.environments.tasks.act import check_agent_tools_act_tools
from paf_workspace.domains.environments.tasks.act import check_moulin_act_image
from paf_workspace.domains.environments.tasks.act import check_moulin_act_tools
from paf_workspace.domains.environments.tasks.act import check_zephyr_xenlib_act_image
from paf_workspace.domains.environments.tasks.act import check_zephyr_xenlib_act_tools
from paf_workspace.domains.environments.tasks.act import ensure_agent_tools_act_image
from paf_workspace.domains.environments.tasks.act import ensure_moulin_act_image
from paf_workspace.domains.environments.tasks.act import ensure_zephyr_xenlib_act_image
from paf_workspace.domains.environments.tasks.act import validate_agent_tools_act
from paf_workspace.domains.environments.tasks.act import validate_moulin_act
from paf_workspace.domains.environments.tasks.act import validate_zephyr_xenlib_act
from paf_workspace.domains.environments.tasks.agent_workspace import check_agent_workspace_tests_image
from paf_workspace.domains.environments.tasks.agent_workspace import check_agent_workspace_tests_tools
from paf_workspace.domains.environments.tasks.agent_workspace import ensure_agent_workspace_tests_image
from paf_workspace.domains.environments.tasks.agent_workspace import run_agent_workspace_tests
from paf_workspace.domains.environments.tasks.base import EnvironmentTask
from paf_workspace.domains.environments.tasks.base import check_cpp_code_map_tools
from paf_workspace.domains.environments.tasks.base import check_environment_image
from paf_workspace.domains.environments.tasks.base import check_workspace_tool_baseline
from paf_workspace.domains.environments.tasks.base import ensure_environment_image
from paf_workspace.domains.environments.tasks.base import run_container_command
from paf_workspace.domains.environments.tasks.zephyr_xen import check_zephyr_xen_tools
from paf_workspace.domains.environments.tasks.zephyr_xen import validate_zephyr_build


__all__ = [
    "EnvironmentTask",
    "ensure_environment_image",
    "check_environment_image",
    "check_workspace_tool_baseline",
    "check_cpp_code_map_tools",
    "run_container_command",
    "ensure_agent_workspace_tests_image",
    "check_agent_workspace_tests_image",
    "check_agent_workspace_tests_tools",
    "run_agent_workspace_tests",
    "ensure_agent_tools_act_image",
    "check_agent_tools_act_image",
    "ensure_moulin_act_image",
    "check_moulin_act_image",
    "ensure_zephyr_xenlib_act_image",
    "check_zephyr_xenlib_act_image",
    "check_zephyr_xen_tools",
    "validate_zephyr_build",
    "check_agent_tools_act_tools",
    "validate_agent_tools_act",
    "check_moulin_act_tools",
    "validate_moulin_act",
    "check_zephyr_xenlib_act_tools",
    "validate_zephyr_xenlib_act",
]
