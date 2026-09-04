"""PAF tasks for Zephyr repository validation."""

from paf_workspace.domains.zephyr_repo_validation.tasks.build import validate_zephyr_build
from paf_workspace.domains.zephyr_repo_validation.tasks.codechecker import (
    validate_zephyr_codechecker_diff,
)
from paf_workspace.domains.zephyr_repo_validation.tasks.compliance import validate_zephyr_compliance
from paf_workspace.domains.zephyr_repo_validation.tasks.docs import validate_zephyr_docs_coverage
from paf_workspace.domains.zephyr_repo_validation.tasks.docs import validate_zephyr_docs_diff
from paf_workspace.domains.zephyr_repo_validation.tasks.west import prepare_zephyr_west_workspace

__all__ = [
    "prepare_zephyr_west_workspace",
    "validate_zephyr_build",
    "validate_zephyr_codechecker_diff",
    "validate_zephyr_compliance",
    "validate_zephyr_docs_coverage",
    "validate_zephyr_docs_diff",
]
