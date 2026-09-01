"""Validation receipts for repo_guard."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from .git_context import git_path
from .models import CheckConfig
from .models import CheckResult
from .models import GuardContext


def receipt_root(repo: Path) -> Path:
    return git_path(repo, "agent_tools/repo_guard")


def scope_hash(
    context: GuardContext,
    check: CheckConfig,
    policy_hash: str,
) -> str:
    payload = {
        "check_id": check.check_id,
        "check_config": check.config,
        "commits": context.commits,
        "paths": [path.as_posix() for path in context.changed_paths],
        "policy_hash": policy_hash,
        "repo": str(context.repo),
        "task_dir": str(context.task_dir) if context.task_dir is not None else None,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def check_receipt_path(
    context: GuardContext,
    check: CheckConfig,
    policy_hash: str,
) -> Path:
    commit = context.ref_tips[0] if context.ref_tips else "working-tree"
    return receipt_root(context.repo) / "checks" / commit / f"{check.check_id}-{scope_hash(context, check, policy_hash)}.json"


def run_receipt_path(context: GuardContext, policy_hash: str) -> Path:
    commit = context.ref_tips[0] if context.ref_tips else "working-tree"
    short_hash = hashlib.sha256(policy_hash.encode("utf-8")).hexdigest()[:16]
    return receipt_root(context.repo) / "runs" / commit / f"{context.mode}-{short_hash}.json"


def has_passing_check_receipt(context: GuardContext, check: CheckConfig, policy_hash: str) -> Path | None:
    path = check_receipt_path(context, check, policy_hash)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("status") != "pass":
        return None
    return path


def write_check_receipt(
    context: GuardContext,
    check: CheckConfig,
    policy_hash: str,
    result: CheckResult,
) -> Path:
    path = check_receipt_path(context, check, policy_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "check": _check_payload(check),
        "commit": context.ref_tips[0] if context.ref_tips else "working-tree",
        "commits": list(context.commits),
        "mode": context.mode,
        "paths": [path_value.as_posix() for path_value in context.changed_paths],
        "policy_hash": policy_hash,
        "recorded_at": _now(),
        "repo": str(context.repo),
        "result": _result_payload(result),
        "status": result.status,
        "task_dir": str(context.task_dir) if context.task_dir is not None else None,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_run_receipt(
    context: GuardContext,
    repo_id: str | None,
    policy_hash: str,
    results: tuple[CheckResult, ...],
) -> Path:
    path = run_receipt_path(context, policy_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "pass" if all(result.status == "pass" for result in results) else "fail"
    payload: dict[str, Any] = {
        "commit": context.ref_tips[0] if context.ref_tips else "working-tree",
        "commits": list(context.commits),
        "mode": context.mode,
        "paths": [path_value.as_posix() for path_value in context.changed_paths],
        "policy_hash": policy_hash,
        "recorded_at": _now(),
        "repo": str(context.repo),
        "repo_id": repo_id,
        "results": [_result_payload(result) for result in results],
        "status": status,
        "task_dir": str(context.task_dir) if context.task_dir is not None else None,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _check_payload(check: CheckConfig) -> dict[str, Any]:
    return {
        "backend": check.backend,
        "config": dict(check.config),
        "cost": check.cost,
        "id": check.check_id,
        "level": check.level,
        "required": check.required,
    }


def _result_payload(result: CheckResult) -> dict[str, Any]:
    payload = asdict(result)
    if result.receipt_path is not None:
        payload["receipt_path"] = str(result.receipt_path)
    return payload


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
