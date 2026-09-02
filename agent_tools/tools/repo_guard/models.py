"""Data model for repository validation guard policies and results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_tools.validation.policy import CheckConfig
from agent_tools.validation.policy import JsonObject
from agent_tools.validation.policy import RepoIdentity


@dataclass(frozen=True)
class GuardContext:
    repo: Path
    workspace: Path
    mode: str
    remote_name: str | None
    remote_url: str | None
    commits: tuple[str, ...]
    ref_tips: tuple[str, ...]
    changed_paths: tuple[Path, ...]
    task_dir: Path | None


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: str
    level: str
    backend: str
    cost: str
    required: bool
    summary: str
    command: tuple[str, ...]
    cwd: str | None
    stdout_tail: str
    stderr_tail: str
    duration_sec: float
    returncode: int
    receipt_path: Path | None = None


@dataclass(frozen=True)
class GuardRunResult:
    status: str
    repo_id: str | None
    policy_hash: str
    context: GuardContext
    checks: tuple[CheckResult, ...]
    receipt_path: Path
