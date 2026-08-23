"""Run workspace validation checks and write a compact receipt."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Sequence

from agent_tools.tools.push_guard import FORBIDDEN_ARTIFACT_SUFFIXES
from agent_tools.tools.push_guard import FORBIDDEN_PUSH_PATH_PREFIXES
from agent_tools.tools.push_guard import LARGE_FILE_LIMIT_BYTES
from agent_tools.tools.push_guard import SECRET_PATTERNS
from agent_tools.tools.push_guard import SECRET_SCAN_LIMIT_BYTES


@dataclass(frozen=True)
class ValidationCommand:
    name: str
    command: list[str]
    cwd: Path


@dataclass(frozen=True)
class ValidationResult:
    name: str
    command: list[str]
    cwd: str
    status: str
    duration_sec: float
    returncode: int
    stdout_tail: str
    stderr_tail: str


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    changed_parser = subparsers.add_parser("changed", help="Validate changed files in the repository.")
    _add_common_args(changed_parser)
    changed_parser.set_defaults(func=validate_changed)

    task_parser = subparsers.add_parser("task", help="Validate changed files and one task directory.")
    task_parser.add_argument("task_dir")
    _add_common_args(task_parser)
    task_parser.set_defaults(func=validate_task)

    args = parser.parse_args(argv)
    return int(args.func(args))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="Repository root or path inside it. Default: current directory.")
    parser.add_argument(
        "--receipt",
        help="Receipt output path. Default: <task>/report/validation/latest.json or report/validation/latest.json.",
    )
    parser.add_argument("--mark-push-guard", action="store_true", help="Record push_guard success when checks pass.")


def validate_changed(args: argparse.Namespace) -> int:
    repo = _repo_root(Path(args.repo).expanduser().resolve())
    changed = _changed_files(repo)
    receipt = Path(args.receipt).expanduser().resolve() if args.receipt else repo / "report" / "validation" / "latest.json"
    return _run_validation(repo, changed, None, receipt, mark_push_guard=args.mark_push_guard)


def validate_task(args: argparse.Namespace) -> int:
    repo = _repo_root(Path(args.repo).expanduser().resolve())
    task_arg = Path(args.task_dir).expanduser()
    task_dir = task_arg.resolve() if task_arg.is_absolute() else (repo / task_arg).resolve()
    changed = _changed_files(repo)
    receipt = (
        Path(args.receipt).expanduser().resolve()
        if args.receipt
        else task_dir / "report" / "validation" / "latest.json"
    )
    return _run_validation(repo, changed, task_dir, receipt, mark_push_guard=args.mark_push_guard)


def _run_validation(
    repo: Path,
    changed: list[Path],
    task_dir: Path | None,
    receipt: Path,
    *,
    mark_push_guard: bool,
) -> int:
    commands = _validation_commands(repo, changed, task_dir)
    results = [_guard_changed_files(repo, changed), *[_run_command(command) for command in commands]]
    status = "pass" if all(result.status == "pass" for result in results) else "fail"
    payload = {
        "repo": str(repo),
        "commit": _git(["rev-parse", "HEAD"], cwd=repo),
        "status": status,
        "task_dir": str(task_dir) if task_dir is not None else None,
        "changed_files": [str(path) for path in changed],
        "commands": [asdict(result) for result in results],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"validate: {status}: {receipt}")
    for result in results:
        print(f"  {result.status}\t{result.name}\t{result.duration_sec:.2f}s")
    if status != "pass":
        return 1
    if mark_push_guard:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "agent_tools.tools.push_guard",
                "mark-success",
                "--repo",
                str(repo),
                "--receipt",
                str(receipt),
            ],
            cwd=repo,
            check=True,
        )
    return 0


def _validation_commands(repo: Path, changed: list[Path], task_dir: Path | None) -> list[ValidationCommand]:
    commands: list[ValidationCommand] = []
    for path in changed:
        if path.suffix == ".py" and path.parts[:1] == ("agent_tools",):
            commands.append(
                ValidationCommand(
                    f"parse-check {path}",
                    [sys.executable, "-m", "agent_tools.tools.code_map", "parse-check", str(path.relative_to("agent_tools"))],
                    repo,
                )
            )
        elif path.suffix == ".sh":
            commands.append(ValidationCommand(f"bash -n {path}", ["bash", "-n", str(path)], repo))
        elif path.suffix == ".desktop" and shutil.which("desktop-file-validate"):
            commands.append(ValidationCommand(f"desktop-file-validate {path}", ["desktop-file-validate", str(path)], repo))
    if any(path.parts[:3] == ("agent_tools", "tools", "agent_workspace") for path in changed):
        commands.append(
            ValidationCommand(
                "pytest agent_workspace",
                [sys.executable, "-m", "pytest", "-q", "agent_tools/tools/agent_workspace/components"],
                repo,
            )
        )
    if task_dir is not None:
        task_workspace = _task_workspace(task_dir, repo)
        commands.append(
            ValidationCommand(
                "task_check strict",
                [
                    sys.executable,
                    "-m",
                    "agent_tools.paf_workspace.task_check",
                    _display_path(task_dir, repo),
                    "--workspace",
                    str(task_workspace),
                    "--strict-warnings",
                ],
                repo,
            )
        )
    return _dedupe_commands(commands)


def _dedupe_commands(commands: list[ValidationCommand]) -> list[ValidationCommand]:
    seen: set[tuple[Path, tuple[str, ...]]] = set()
    result: list[ValidationCommand] = []
    for command in commands:
        key = (command.cwd, tuple(command.command))
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return result


def _run_command(command: ValidationCommand) -> ValidationResult:
    start = time.monotonic()
    completed = subprocess.run(
        command.command,
        cwd=command.cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    duration = time.monotonic() - start
    return ValidationResult(
        name=command.name,
        command=command.command,
        cwd=str(command.cwd),
        status="pass" if completed.returncode == 0 else "fail",
        duration_sec=round(duration, 3),
        returncode=completed.returncode,
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _guard_changed_files(repo: Path, changed: list[Path]) -> ValidationResult:
    findings: list[str] = []
    for path in changed:
        normalized = path.as_posix()
        absolute = repo / path
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
            findings.append(f"{normalized}: private path must not be committed")
            continue
        if not absolute.exists() or not absolute.is_file():
            continue
        suffix = path.suffix.casefold()
        if suffix in FORBIDDEN_ARTIFACT_SUFFIXES:
            findings.append(f"{normalized}: artifact-like file suffix '{suffix}' is blocked")
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
    return ValidationResult(
        name="guard changed files",
        command=["internal", "guard-changed-files"],
        cwd=str(repo),
        status="fail" if findings else "pass",
        duration_sec=0.0,
        returncode=1 if findings else 0,
        stdout_tail="",
        stderr_tail="\n".join(findings),
    )


def _changed_files(repo: Path) -> list[Path]:
    tracked = _git(["diff", "--name-only", "HEAD"], cwd=repo)
    untracked = _git(["ls-files", "--others", "--exclude-standard"], cwd=repo)
    paths = {Path(line) for output in (tracked, untracked) for line in output.splitlines() if line}
    return sorted(paths, key=lambda path: str(path).casefold())


def _repo_root(path: Path) -> Path:
    return Path(_git(["rev-parse", "--show-toplevel"], cwd=path))


def _display_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _task_workspace(task_dir: Path, fallback: Path) -> Path:
    for parent in task_dir.parents:
        if parent.name == "tasks":
            return parent.parent
    return fallback


def _git(args: Sequence[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _tail(text: str, *, limit: int = 4000) -> str:
    return text[-limit:]


if __name__ == "__main__":
    raise SystemExit(main())
