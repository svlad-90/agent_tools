"""Compatibility wrappers for the shared validation policy loader."""

from __future__ import annotations

from pathlib import Path

from agent_tools.validation.policy import DEFAULT_POLICY_ROOT
from agent_tools.validation.policy import load_validation_policy
from agent_tools.validation.policy import policy_summary
from agent_tools.validation.policy import workspace_root_from_env

from .models import CheckConfig
from .models import RepoIdentity


def load_policy(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> tuple[RepoIdentity | None, tuple[CheckConfig, ...], str]:
    policy = load_validation_policy(repo, task_dir=task_dir, policy_root=policy_root)
    return policy.repo_identity, policy.checks, policy.policy_hash


__all__ = [
    "DEFAULT_POLICY_ROOT",
    "load_policy",
    "policy_summary",
    "workspace_root_from_env",
]
