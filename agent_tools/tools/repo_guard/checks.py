"""Check backends for repo_guard."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from agent_tools.tools.push_guard import FORBIDDEN_ARTIFACT_SUFFIXES
from agent_tools.tools.push_guard import FORBIDDEN_PUSH_PATH_PREFIXES
from agent_tools.tools.push_guard import LARGE_FILE_LIMIT_BYTES
from agent_tools.tools.push_guard import SECRET_PATTERNS
from agent_tools.tools.push_guard import SECRET_SCAN_LIMIT_BYTES

from .git_context import run_git
from .models import CheckConfig
from .models import CheckResult
from .models import GuardContext


def run_check(context: GuardContext, check: CheckConfig) -> CheckResult:
    if check.backend == "builtin":
        return _run_builtin(context, check)
    if check.backend == "command":
        return _run_command_backend(context, check, _resolve_command(context, check))
    if check.backend == "paf":
        return _run_command_backend(context, check, _paf_command(context, check))
    if check.backend == "task_check":
        return _run_command_backend(context, check, _task_check_command(context, check))
    if check.backend == "task_command":
        return _run_command_backend(context, check, _task_command(context, check))
    return _result(
        context,
        check,
        "fail",
        f"unknown backend: {check.backend}",
        returncode=2,
    )


def _run_builtin(context: GuardContext, check: CheckConfig) -> CheckResult:
    if check.check_id == "commit-message":
        return _commit_message_check(context, check)
    if check.check_id == "workspace-file-hygiene":
        return _workspace_file_hygiene(context, check)
    if check.check_id == "python-parse-check-changed":
        return _python_parse_check_changed(context, check)
    if check.check_id == "shell-syntax-changed":
        return _shell_syntax_changed(context, check)
    return _result(
        context,
        check,
        "fail",
        f"unknown builtin check: {check.check_id}",
        returncode=2,
    )


def _commit_message_check(context: GuardContext, check: CheckConfig) -> CheckResult:
    findings: list[str] = []
    for commit in context.commits or context.ref_tips:
        message = run_git(["show", "-s", "--format=%B", commit], cwd=context.repo)
        short_commit = commit[:12]
        for line_number, line in enumerate(message.splitlines(), start=1):
            if len(line) > 72:
                findings.append(f"{short_commit}:{line_number}: line longer than 72 chars")
        if "Signed-off-by:" not in message:
            findings.append(f"{short_commit}: missing Signed-off-by trailer")
    return _result(
        context,
        check,
        "fail" if findings else "pass",
        "commit messages are valid" if not findings else "commit message check failed",
        stderr="\n".join(findings),
        returncode=1 if findings else 0,
    )


def _workspace_file_hygiene(context: GuardContext, check: CheckConfig) -> CheckResult:
    findings: list[str] = []
    for path in context.changed_paths:
        normalized = path.as_posix()
        absolute = context.repo / path
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
            findings.append(f"{normalized}: private path must not be pushed")
            continue
        if not absolute.exists() or not absolute.is_file():
            continue
        suffix = path.suffix.casefold()
        if suffix in FORBIDDEN_ARTIFACT_SUFFIXES:
            findings.append(f"{normalized}: artifact-like suffix {suffix!r} is blocked")
            continue
        try:
            size = absolute.stat().st_size
        except OSError:
            continue
        if size > LARGE_FILE_LIMIT_BYTES:
            findings.append(f"{normalized}: file is larger than {LARGE_FILE_LIMIT_BYTES} bytes")
            continue
        if size > SECRET_SCAN_LIMIT_BYTES:
            continue
        try:
            content = absolute.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(f"{normalized}: content matches secret pattern {pattern.pattern!r}")
                break
    return _result(
        context,
        check,
        "fail" if findings else "pass",
        "changed files pass workspace hygiene" if not findings else "workspace hygiene failed",
        stderr="\n".join(findings),
        returncode=1 if findings else 0,
    )


def _python_parse_check_changed(context: GuardContext, check: CheckConfig) -> CheckResult:
    results: list[CheckResult] = []
    for path in context.changed_paths:
        if path.suffix != ".py" or path.parts[:1] != ("agent_tools",):
            continue
        if not (context.repo / path).is_file():
            continue
        command = [
            sys.executable,
            "-m",
            "agent_tools.tools.code_map",
            "parse-check",
            str(path.relative_to("agent_tools")),
        ]
        results.append(_run_command_backend(context, check, tuple(command)))
    return _aggregate_command_results(context, check, results, "no changed Python files")


def _shell_syntax_changed(context: GuardContext, check: CheckConfig) -> CheckResult:
    results: list[CheckResult] = []
    for path in context.changed_paths:
        if path.suffix == ".sh" and (context.repo / path).is_file():
            results.append(_run_command_backend(context, check, ("bash", "-n", path.as_posix())))
    return _aggregate_command_results(context, check, results, "no changed shell scripts")


def _aggregate_command_results(
    context: GuardContext,
    check: CheckConfig,
    results: list[CheckResult],
    empty_summary: str,
) -> CheckResult:
    if not results:
        return _result(context, check, "pass", empty_summary)
    failed = [result for result in results if result.status != "pass"]
    stdout = "\n".join(_command_detail(result, result.stdout_tail) for result in results if result.stdout_tail)
    stderr = "\n".join(_command_detail(result, result.stderr_tail) for result in results if result.stderr_tail)
    return _result(
        context,
        check,
        "fail" if failed else "pass",
        f"{len(results)} command(s), {len(failed)} failed",
        stdout=stdout,
        stderr=stderr,
        returncode=1 if failed else 0,
        duration=sum(result.duration_sec for result in results),
    )


def _resolve_command(context: GuardContext, check: CheckConfig) -> tuple[str, ...]:
    return tuple(_substitute(part, context) for part in check.command)


def _command_detail(result: CheckResult, text: str) -> str:
    prefix = "$ " + " ".join(result.command)
    return prefix + "\n" + text


def _paf_command(context: GuardContext, check: CheckConfig) -> tuple[str, ...]:
    if check.scenario is None:
        return ("python3", "-c", "import sys; print('missing PAF scenario'); sys.exit(2)")
    command = ["agent_tools/paf_workspace/run-paf.sh", check.scenario]
    if check.profile:
        command.append(check.profile)
    return tuple(command)


def _task_check_command(context: GuardContext, check: CheckConfig) -> tuple[str, ...]:
    task_dir = _check_task_dir(context, check)
    command = [
        sys.executable,
        "-m",
        "agent_tools.paf_workspace.task_check",
        str(task_dir),
        "--workspace",
        str(context.workspace),
    ]
    if check.strict_warnings:
        command.append("--strict-warnings")
    return tuple(command)


def _task_command(context: GuardContext, check: CheckConfig) -> tuple[str, ...]:
    task_dir = _check_task_dir(context, check)
    return tuple(str(task_dir / part) if index == 0 else part for index, part in enumerate(check.command))


def _check_task_dir(context: GuardContext, check: CheckConfig) -> Path:
    if check.task:
        task = Path(check.task)
        return task if task.is_absolute() else context.workspace / "tasks" / task
    if context.task_dir is not None:
        return context.task_dir
    raise ValueError(f"{check.check_id}: task backend requires task_dir or task")


def _run_command_backend(
    context: GuardContext,
    check: CheckConfig,
    command: tuple[str, ...],
) -> CheckResult:
    start = time.monotonic()
    cwd = _command_cwd(context, check)
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    status = "pass" if completed.returncode == 0 else "fail"
    return _result(
        context,
        check,
        status,
        "command passed" if status == "pass" else "command failed",
        command=command,
        cwd=cwd,
        stdout=_tail(completed.stdout),
        stderr=_tail(completed.stderr),
        duration=time.monotonic() - start,
        returncode=completed.returncode,
    )


def _command_cwd(context: GuardContext, check: CheckConfig) -> Path:
    if check.cwd is None:
        return context.repo
    value = _substitute(check.cwd, context)
    path = Path(value)
    return path if path.is_absolute() else context.repo / path


def _substitute(value: str, context: GuardContext) -> str:
    replacements = {
        "{repo}": str(context.repo),
        "{workspace}": str(context.workspace),
        "{task_dir}": str(context.task_dir or ""),
    }
    result = value
    for token, replacement in replacements.items():
        result = result.replace(token, replacement)
    return result


def _result(
    context: GuardContext,
    check: CheckConfig,
    status: str,
    summary: str,
    *,
    command: tuple[str, ...] = (),
    cwd: Path | None = None,
    stdout: str = "",
    stderr: str = "",
    duration: float = 0.0,
    returncode: int = 0,
) -> CheckResult:
    return CheckResult(
        check_id=check.check_id,
        status=status,
        level=check.level,
        backend=check.backend,
        cost=check.cost,
        required=check.required,
        summary=summary,
        command=command,
        cwd=str(cwd or context.repo),
        stdout_tail=stdout,
        stderr_tail=stderr,
        duration_sec=duration,
        returncode=returncode,
    )


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:]
