"""repo_guard policy runner."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .checks import run_check
from .git_context import changed_paths
from .git_context import head_commit
from .git_context import pushed_commits
from .git_context import pushed_ref_tips
from .git_context import repo_root
from .git_context import validation_commits
from .models import CheckConfig
from .models import CheckResult
from .models import GuardContext
from .models import GuardRunResult
from .policy import load_policy
from .policy import workspace_root_from_env
from .receipts import has_passing_check_receipt
from .receipts import write_check_receipt
from .receipts import write_run_receipt


NON_HEAVY_COSTS = {"cheap", "medium"}


def validate(
    repo_path: Path,
    *,
    task_dir: Path | None = None,
    include_heavy: bool = False,
    policy_root: Path | None = None,
) -> GuardRunResult:
    repo = repo_root(repo_path)
    commits = validation_commits(repo)
    paths = set(changed_paths(repo, commits))
    paths.update(changed_paths(repo))
    context = GuardContext(
        repo=repo,
        workspace=workspace_root_from_env(),
        mode="validate",
        remote_name=None,
        remote_url=None,
        commits=commits,
        ref_tips=(head_commit(repo),),
        changed_paths=tuple(sorted(paths, key=lambda path: path.as_posix().casefold())),
        task_dir=task_dir,
    )
    return _run_context(context, include_heavy=include_heavy, policy_root=policy_root)


def pre_push(
    repo_path: Path,
    *,
    remote_name: str | None,
    remote_url: str | None,
    stdin_text: str,
    task_dir: Path | None = None,
    policy_root: Path | None = None,
) -> GuardRunResult:
    repo = repo_root(repo_path)
    commits = pushed_commits(stdin_text, repo)
    context = GuardContext(
        repo=repo,
        workspace=workspace_root_from_env(),
        mode="pre-push",
        remote_name=remote_name,
        remote_url=remote_url,
        commits=commits,
        ref_tips=pushed_ref_tips(stdin_text, repo),
        changed_paths=changed_paths(repo, commits),
        task_dir=task_dir,
    )
    return _run_context(context, include_heavy=False, policy_root=policy_root)


def _run_context(
    context: GuardContext,
    *,
    include_heavy: bool,
    policy_root: Path | None,
) -> GuardRunResult:
    repo_identity, checks, policy_hash = load_policy(
        context.repo,
        task_dir=context.task_dir,
        policy_root=policy_root,
    )
    results: list[CheckResult] = []
    for check in checks:
        if _should_require_receipt(context, check, include_heavy):
            results.append(_receipt_required_result(context, check, policy_hash))
            continue
        result = run_check(context, check)
        if result.status == "pass":
            receipt_path = write_check_receipt(context, check, policy_hash, result)
            result = replace(result, receipt_path=receipt_path)
        results.append(result)
    run_receipt = write_run_receipt(
        context,
        repo_identity.repo_id if repo_identity is not None else None,
        policy_hash,
        tuple(results),
    )
    status = "pass" if all(not result.required or result.status == "pass" for result in results) else "fail"
    return GuardRunResult(
        status=status,
        repo_id=repo_identity.repo_id if repo_identity is not None else None,
        policy_hash=policy_hash,
        context=context,
        checks=tuple(results),
        receipt_path=run_receipt,
    )


def _should_require_receipt(context: GuardContext, check: CheckConfig, include_heavy: bool) -> bool:
    if check.cost != "heavy":
        return False
    if include_heavy:
        return False
    return context.mode == "pre-push"


def _receipt_required_result(
    context: GuardContext,
    check: CheckConfig,
    policy_hash: str,
) -> CheckResult:
    receipt = has_passing_check_receipt(context, check, policy_hash)
    if receipt is not None:
        return CheckResult(
            check_id=check.check_id,
            status="pass",
            level=check.level,
            backend=check.backend,
            cost=check.cost,
            required=check.required,
            summary="heavy check receipt is current",
            command=(),
            cwd=str(context.repo),
            stdout_tail="",
            stderr_tail="",
            duration_sec=0.0,
            returncode=0,
            receipt_path=receipt,
        )
    return CheckResult(
        check_id=check.check_id,
        status="fail",
        level=check.level,
        backend=check.backend,
        cost=check.cost,
        required=check.required,
        summary="heavy check requires a current validation receipt",
        command=(
            "python3",
            "-m",
            "agent_tools.tools.repo_guard",
            "validate",
            "--repo",
            str(context.repo),
            "--include-heavy",
        ),
        cwd=str(context.repo),
        stdout_tail="",
        stderr_tail=(
            f"{check.check_id}: run repo_guard validate --include-heavy "
            "before pushing this commit"
        ),
        duration_sec=0.0,
        returncode=1,
    )


def compact_report(result: GuardRunResult) -> str:
    lines = [
        f"repo_guard: {result.status}",
        f"repo_guard: repo: {result.context.repo}",
        f"repo_guard: repo_id: {result.repo_id or '<unmatched>'}",
        f"repo_guard: receipt: {result.receipt_path}",
    ]
    for check in result.checks:
        lines.append(f"{check.status}\t{check.check_id}\t{check.summary}")
        detail = check.stderr_tail.strip() or check.stdout_tail.strip()
        if check.status != "pass" and detail:
            lines.extend(f"  {line}" for line in detail.splitlines()[:8])
    return "\n".join(lines)


def check_ids(result: GuardRunResult) -> Sequence[str]:
    return tuple(check.check_id for check in result.checks)
