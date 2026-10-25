"""Compatibility wrappers for the shared validation policy loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_tools.validation.policy import DEFAULT_POLICY_ROOT
from agent_tools.validation.policy import load_validation_policy
from agent_tools.validation.policy import policy_summary as _policy_summary
from agent_tools.validation.policy import workspace_root_from_env

from .models import CheckConfig
from .models import RepoIdentity


TASK_MARKERS = (
    "TASK_CONTEXT.sqlite3",
    "TASK_DESCRIPTION.md",
    "TASK_CONTEXT.md",
    "TASK_GUARD.yaml",
)


def resolve_task_dir(
    repo: Path,
    *,
    task_dir: Path | None = None,
    workspace: Path | None = None,
) -> Path | None:
    """Resolve an explicit task or infer the task that contains the repository."""
    if task_dir is not None:
        return task_dir.expanduser().resolve()

    workspace = (workspace or workspace_root_from_env()).resolve()
    tasks_root = workspace / "tasks"
    try:
        relative_repo = repo.resolve().relative_to(tasks_root)
    except ValueError:
        return None
    if not relative_repo.parts:
        return None

    candidate = tasks_root / relative_repo.parts[0]
    if any((candidate / marker).is_file() for marker in TASK_MARKERS):
        return candidate
    return None


def load_policy(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> tuple[RepoIdentity | None, tuple[CheckConfig, ...], str]:
    resolved_task = resolve_task_dir(repo, task_dir=task_dir)
    policy = load_validation_policy(repo, task_dir=resolved_task, policy_root=policy_root)
    return policy.repo_identity, policy.checks, policy.policy_hash


def policy_summary(
    repo: Path,
    *,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> dict[str, Any]:
    resolved_task = resolve_task_dir(repo, task_dir=task_dir)
    return _policy_summary(repo, task_dir=resolved_task, policy_root=policy_root)


__all__ = [
    "DEFAULT_POLICY_ROOT",
    "load_policy",
    "policy_summary",
    "resolve_task_dir",
    "workspace_root_from_env",
]
