"""Data model for repository validation guard policies and results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Mapping


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class RepoIdentity:
    repo_id: str
    names: tuple[str, ...]
    github_repos: tuple[str, ...]
    allow_forks: bool
    characteristic_files: tuple[str, ...]
    verify_command: tuple[str, ...] | None
    policy_path: Path | None


@dataclass(frozen=True)
class CheckConfig:
    check_id: str
    level: str
    backend: str
    cost: str
    required: bool
    command: tuple[str, ...]
    cwd: str | None
    scenario: str | None
    profile: str | None
    task: str | None
    strict_warnings: bool
    config: Mapping[str, Any]
    policy_path: Path | None


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
