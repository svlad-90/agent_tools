"""Compatibility exports for reusable environment PAF tasks.

New scenarios should import task classes from the environment-specific modules:
`base_tasks`, `zephyr_xen_tasks`, and `act_tasks`.
"""

from __future__ import annotations

from paf_workspace.domains.environments.act_tasks import check_codex_tools_act_image
from paf_workspace.domains.environments.act_tasks import check_codex_tools_act_tools
from paf_workspace.domains.environments.act_tasks import check_moulin_act_image
from paf_workspace.domains.environments.act_tasks import check_moulin_act_tools
from paf_workspace.domains.environments.act_tasks import check_zephyr_xenlib_act_image
from paf_workspace.domains.environments.act_tasks import check_zephyr_xenlib_act_tools
from paf_workspace.domains.environments.act_tasks import ensure_codex_tools_act_image
from paf_workspace.domains.environments.act_tasks import ensure_moulin_act_image
from paf_workspace.domains.environments.act_tasks import ensure_zephyr_xenlib_act_image
from paf_workspace.domains.environments.act_tasks import validate_codex_tools_act
from paf_workspace.domains.environments.act_tasks import validate_moulin_act
from paf_workspace.domains.environments.act_tasks import validate_zephyr_xenlib_act
from paf_workspace.domains.environments.base_tasks import EnvironmentTask
from paf_workspace.domains.environments.base_tasks import check_environment_image
from paf_workspace.domains.environments.base_tasks import ensure_environment_image
from paf_workspace.domains.environments.zephyr_xen_tasks import check_zephyr_xen_tools
from paf_workspace.domains.environments.zephyr_xen_tasks import validate_zephyr_build


__all__ = [
    "EnvironmentTask",
    "ensure_environment_image",
    "check_environment_image",
    "ensure_codex_tools_act_image",
    "check_codex_tools_act_image",
    "ensure_moulin_act_image",
    "check_moulin_act_image",
    "ensure_zephyr_xenlib_act_image",
    "check_zephyr_xenlib_act_image",
    "check_zephyr_xen_tools",
    "validate_zephyr_build",
    "check_codex_tools_act_tools",
    "validate_codex_tools_act",
    "check_moulin_act_tools",
    "validate_moulin_act",
    "check_zephyr_xenlib_act_tools",
    "validate_zephyr_xenlib_act",
]
