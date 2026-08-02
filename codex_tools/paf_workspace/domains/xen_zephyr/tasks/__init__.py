"""Compatibility exports for Xen/Zephyr PAF tasks."""

from __future__ import annotations

from paf_workspace.domains.xen_zephyr.tasks.base import XenZephyrTask
from paf_workspace.domains.xen_zephyr.tasks.base import check_workspace_environment
from paf_workspace.domains.xen_zephyr.tasks.build import build_product
from paf_workspace.domains.xen_zephyr.tasks.build import write_artifact_manifest
from paf_workspace.domains.xen_zephyr.tasks.harness import load_harness_scenario
from paf_workspace.domains.xen_zephyr.tasks.harness import prepare_harness_inputs
from paf_workspace.domains.xen_zephyr.tasks.harness import run_harness_command
from paf_workspace.domains.xen_zephyr.tasks.harness import validate_runtime_log


__all__ = [
    "XenZephyrTask",
    "check_workspace_environment",
    "build_product",
    "write_artifact_manifest",
    "load_harness_scenario",
    "prepare_harness_inputs",
    "run_harness_command",
    "validate_runtime_log",
]
