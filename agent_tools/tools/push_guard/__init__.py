"""Pre-push validation guard for workspace repositories."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Sequence


ZERO_SHA = "0" * 40
FORBIDDEN_PUSH_PATH_PREFIXES = (
    "agent_tools/paf_workspace/domains/environments/private_envs/",
    "agent_tools/knowledge/private/",
)
FORBIDDEN_ARTIFACT_SUFFIXES = {
    ".7z",
    ".deb",
    ".db",
    ".gz",
    ".iso",
    ".log",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".xz",
    ".zip",
}
LARGE_FILE_LIMIT_BYTES = 5 * 1024 * 1024
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)
SECRET_SCAN_LIMIT_BYTES = 1024 * 1024


@dataclass(frozen=True)
class PushedFileFinding:
    path: str
    reason: str


def _run_git(args: Sequence[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _repo_root(cwd: Path) -> Path:
    return Path(_run_git(["rev-parse", "--show-toplevel"], cwd=cwd))


def _git_path(repo: Path, path: str) -> Path:
    return git_path(repo, path)


def git_path(repo: Path, path: str) -> Path:
    git_path = Path(_run_git(["rev-parse", "--git-path", path], cwd=repo))
    if git_path.is_absolute():
        return git_path
    return repo / git_path


def _stamp_dir(repo: Path) -> Path:
    return _git_path(repo, "codex_push_guard")


def _stamp_path(repo: Path, commit: str) -> Path:
    return _stamp_dir(repo) / f"{commit}.json"


def _config_path(repo: Path) -> Path:
    return _git_path(repo, "agent_tools/push_guard/config.json")


def _head_commit(repo: Path, ref: str) -> str:
    return _run_git(["rev-parse", "--verify", ref], cwd=repo)


def _target_repo(args: argparse.Namespace) -> Path:
    if getattr(args, "repo", None):
        return _repo_root(Path(args.repo).expanduser().resolve())
    return _repo_root(Path.cwd())


def _record_success(repo: Path, commit: str, source: str) -> None:
    stamp_dir = _stamp_dir(repo)
    stamp_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "commit": commit,
        "source": source,
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    _stamp_path(repo, commit).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_config(repo: Path) -> dict[str, object]:
    path = _config_path(repo)
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"push_guard: config must be a JSON object: {path}")
    return payload


def _write_config(repo: Path, config: dict[str, object]) -> None:
    path = _config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _repo_guard_enabled(repo: Path) -> bool:
    return bool(_load_config(repo).get("repo_guard_enabled", True))


def _set_repo_guard_enabled(args: argparse.Namespace, *, enabled: bool) -> int:
    repo = _target_repo(args)
    config = _load_config(repo)
    config["repo_guard_enabled"] = enabled
    _write_config(repo, config)
    print(f"push_guard: repo_guard_enabled: {str(enabled).lower()}")
    print(f"push_guard: config: {_config_path(repo)}")
    return 0


def mark_success(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    commit = _head_commit(repo, args.ref)
    if args.receipt:
        source = _validated_receipt_source(repo, commit, Path(args.receipt).expanduser().resolve())
    else:
        source = args.source or "external validation"

    _record_success(repo, commit, source)
    print(f"push_guard: recorded successful validation for {commit}")
    print(f"push_guard: source: {source}")
    return 0


def enable_repo_guard(args: argparse.Namespace) -> int:
    return _set_repo_guard_enabled(args, enabled=True)


def disable_repo_guard(args: argparse.Namespace) -> int:
    return _set_repo_guard_enabled(args, enabled=False)


def status(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    commit = _head_commit(repo, args.ref)
    stamp_path = _stamp_path(repo, commit)

    print(f"push_guard: repo: {repo}")
    print(f"push_guard: commit: {commit}")
    print(f"push_guard: stamp: {stamp_path}")
    print(f"push_guard: repo_guard_enabled: {str(_repo_guard_enabled(repo)).lower()}")
    if not stamp_path.is_file():
        print("push_guard: status: missing")
        return 1

    payload = json.loads(stamp_path.read_text(encoding="utf-8"))
    print("push_guard: status: recorded")
    print(f"push_guard: recorded_at: {payload.get('recorded_at', '<unknown>')}")
    source = payload.get("source") or payload.get("command") or "<unknown>"
    print(f"push_guard: source: {source}")
    return 0


def _pushed_ref_tips(stdin_text: str, repo: Path) -> list[str]:
    commits: list[str] = []
    for line in stdin_text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_sha = fields[1]
        if local_sha == ZERO_SHA:
            continue
        commits.append(local_sha)
    if commits:
        return commits
    return [_head_commit(repo, "HEAD")]


def _pushed_commits(stdin_text: str, repo: Path) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for line in stdin_text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_sha = fields[1]
        remote_sha = fields[3]
        if local_sha == ZERO_SHA:
            continue

        if remote_sha == ZERO_SHA:
            rev_args = [local_sha, "--not", "--remotes"]
        else:
            rev_args = [local_sha, "--not", remote_sha, "--remotes"]

        hashes = _run_git(["rev-list", "--reverse", *rev_args], cwd=repo).splitlines()
        for commit in hashes:
            if commit not in seen:
                seen.add(commit)
                result.append(commit)

    if result:
        return result
    return [_head_commit(repo, "HEAD")]


def _pushed_paths(repo: Path, commits: Sequence[str]) -> set[str]:
    paths: set[str] = set()
    for commit in commits:
        output = _run_git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit], cwd=repo)
        paths.update(path for path in output.splitlines() if path)
    return paths


def _staged_paths(repo: Path) -> list[str]:
    output = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRT"], cwd=repo)
    return [path for path in output.splitlines() if path]


def _task_check_report_for_repo(repo: Path) -> str | None:
    workspace_value = os.environ.get("AGENT_TOOLS_WORKSPACE_ROOT")
    if not workspace_value:
        return None
    workspace = Path(workspace_value).resolve()
    try:
        relative_repo = repo.resolve().relative_to(workspace / "tasks")
    except ValueError:
        return None
    if not relative_repo.parts:
        return None
    task_dir = workspace / "tasks" / relative_repo.parts[0]
    if not _looks_like_task_dir(task_dir):
        return None
    from agent_tools.paf_workspace.task_check import check_task
    from agent_tools.paf_workspace.task_check import render_text

    checks = check_task(task_dir, workspace=workspace)
    if not any(check.status in {"FAIL", "WARN"} for check in checks):
        return None
    return render_text(task_dir, checks, errors_only=False)


def _looks_like_task_dir(task_dir: Path) -> bool:
    return any(
        (task_dir / filename).is_file()
        for filename in ("TASK_CONTEXT.sqlite3", "TASK_DESCRIPTION.md", "TASK_CONTEXT.md")
    )


def _forbidden_pushed_paths(repo: Path, commits: Sequence[str]) -> list[str]:
    forbidden: list[str] = []
    for path in sorted(_pushed_paths(repo, commits)):
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
            forbidden.append(path)
    return forbidden


def _guarded_pushed_file_findings(repo: Path, commits: Sequence[str]) -> list[PushedFileFinding]:
    findings: list[PushedFileFinding] = []
    for commit in commits:
        for path in sorted(_pushed_paths(repo, [commit])):
            normalized = path.replace("\\", "/")
            if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
                findings.append(PushedFileFinding(path, "private path must not be pushed"))
                continue
            suffix = Path(path).suffix.casefold()
            if suffix in FORBIDDEN_ARTIFACT_SUFFIXES:
                findings.append(PushedFileFinding(path, f"artifact-like file suffix '{suffix}' is blocked"))
                continue
            size = _git_object_size(repo, commit, path)
            if size is not None and size > LARGE_FILE_LIMIT_BYTES:
                findings.append(PushedFileFinding(path, f"file is larger than {LARGE_FILE_LIMIT_BYTES} bytes"))
                continue
            secret_reason = _secret_finding_reason(repo, commit, path, size)
            if secret_reason is not None:
                findings.append(PushedFileFinding(path, secret_reason))
    return _dedupe_findings(findings)


def _guarded_staged_file_findings(repo: Path) -> list[PushedFileFinding]:
    findings: list[PushedFileFinding] = []
    for path in sorted(_staged_paths(repo)):
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
            findings.append(PushedFileFinding(path, "private path must not be committed"))
            continue
        suffix = Path(path).suffix.casefold()
        if suffix in FORBIDDEN_ARTIFACT_SUFFIXES:
            findings.append(PushedFileFinding(path, f"artifact-like file suffix '{suffix}' is blocked"))
            continue
        size = _git_index_object_size(repo, path)
        if size is not None and size > LARGE_FILE_LIMIT_BYTES:
            findings.append(PushedFileFinding(path, f"file is larger than {LARGE_FILE_LIMIT_BYTES} bytes"))
            continue
        secret_reason = _secret_finding_reason(repo, None, path, size)
        if secret_reason is not None:
            findings.append(PushedFileFinding(path, secret_reason))
    return _dedupe_findings(findings)


def _git_object_size(repo: Path, commit: str, path: str) -> int | None:
    try:
        output = _run_git(["cat-file", "-s", f"{commit}:{path}"], cwd=repo)
    except subprocess.CalledProcessError:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def _git_index_object_size(repo: Path, path: str) -> int | None:
    try:
        output = _run_git(["cat-file", "-s", f":{path}"], cwd=repo)
    except subprocess.CalledProcessError:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def _secret_finding_reason(repo: Path, commit: str | None, path: str, size: int | None) -> str | None:
    if size is not None and size > SECRET_SCAN_LIMIT_BYTES:
        return None
    try:
        object_ref = f"{commit}:{path}" if commit is not None else f":{path}"
        content = _run_git(["show", object_ref], cwd=repo)
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return None
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            return f"content matches secret pattern {pattern.pattern!r}"
    return None


def _dedupe_findings(findings: list[PushedFileFinding]) -> list[PushedFileFinding]:
    seen: set[tuple[str, str]] = set()
    result: list[PushedFileFinding] = []
    for finding in findings:
        key = (finding.path, finding.reason)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _validated_receipt_source(repo: Path, commit: str, receipt: Path) -> str:
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    if payload.get("status") != "pass":
        raise SystemExit(f"push_guard: receipt status is not pass: {receipt}")
    receipt_commit = payload.get("commit")
    if receipt_commit != commit:
        raise SystemExit(
            f"push_guard: receipt commit {receipt_commit!r} does not match target commit {commit!r}: {receipt}"
        )
    try:
        display = receipt.relative_to(repo)
    except ValueError:
        display = receipt
    return f"validation receipt: {display}"


def _print_guarded_findings(findings: Sequence[PushedFileFinding], *, action: str) -> None:
    print(f"push_guard: {action} blocked; guarded files are forbidden:", file=sys.stderr)
    for finding in findings:
        print(f"  {finding.path}: {finding.reason}", file=sys.stderr)
    print(
        "Move private knowledge/environment files to ignored private paths, "
        "remove generated artifacts from the commit, or use an explicit human-reviewed override.",
        file=sys.stderr,
    )
    workspace_root = os.environ.get("AGENT_TOOLS_WORKSPACE_ROOT")
    if workspace_root:
        print(
            "After fixing the files, run validation with:\n"
            f"  PYTHONPATH={workspace_root} python3 -m agent_tools.tools.validate changed",
            file=sys.stderr,
        )


def _repo_guard_report(
    repo: Path,
    *,
    remote_name: str | None,
    remote_url: str | None,
    stdin_text: str,
) -> str | None:
    if not _repo_guard_enabled(repo):
        return None
    from agent_tools.tools.repo_guard.runner import compact_report
    from agent_tools.tools.repo_guard.runner import pre_push

    result = pre_push(
        repo,
        remote_name=remote_name,
        remote_url=remote_url,
        stdin_text=stdin_text,
    )
    if result.status == "pass":
        return None
    return compact_report(result)


def check(args: argparse.Namespace) -> int:
    repo = _repo_root(Path.cwd())
    stdin_text = sys.stdin.read()
    commits = _pushed_commits(stdin_text, repo)
    ref_tips = _pushed_ref_tips(stdin_text, repo)
    findings = _guarded_pushed_file_findings(repo, commits)
    task_check_report = _task_check_report_for_repo(repo)
    repo_guard_report = _repo_guard_report(
        repo,
        remote_name=getattr(args, "remote_name", None),
        remote_url=getattr(args, "remote_url", None),
        stdin_text=stdin_text,
    )
    if findings:
        _print_guarded_findings(findings, action="push")
    if task_check_report:
        print("push_guard: push blocked by task_check:", file=sys.stderr)
        print(task_check_report, file=sys.stderr)
    if repo_guard_report:
        print("push_guard: push blocked by repo_guard:", file=sys.stderr)
        print(repo_guard_report, file=sys.stderr)
    if findings or task_check_report or repo_guard_report:
        if args.allow_override:
            print("push_guard: override enabled; allowing push", file=sys.stderr)
            return 0
        return 1

    missing = [
        commit
        for commit in ref_tips
        if not _stamp_path(repo, commit).is_file()
    ]
    if not missing:
        return 0

    print("push_guard: push blocked; missing successful validation:", file=sys.stderr)
    for commit in missing:
        print(f"  {commit}", file=sys.stderr)
    print(
        "Run the repository build through:\n"
        "  agent_tools/paf_workspace/run-paf.sh <scenario-file> <scenario> "
        "--parameter PUSH_GUARD_REPO=<target-repo>\n"
        "or record an already successful external validation with:\n"
        f"  {_pythonpath_prefix()}python3 -m agent_tools.tools.validate changed --mark-push-guard\n"
        "or:\n"
        f"  {_pythonpath_prefix()}python3 -m agent_tools.tools.push_guard mark-success "
        "--repo <target-repo> --receipt <validation-receipt.json>",
        file=sys.stderr,
    )
    if args.allow_override:
        print("push_guard: override enabled; allowing push", file=sys.stderr)
        return 0
    return 1


def check_staged(args: argparse.Namespace) -> int:
    repo = _repo_root(Path.cwd())
    findings = _guarded_staged_file_findings(repo)
    task_check_report = _task_check_report_for_repo(repo)
    if findings:
        _print_guarded_findings(findings, action="commit")
    if task_check_report:
        print("push_guard: commit blocked by task_check:", file=sys.stderr)
        print(task_check_report, file=sys.stderr)
    if args.allow_override:
        if findings or task_check_report:
            print("push_guard: override enabled; allowing commit", file=sys.stderr)
            return 0
        return 0
    if not findings and not task_check_report:
        return 0
    return 1


def _pythonpath_prefix() -> str:
    workspace_root = os.environ.get("AGENT_TOOLS_WORKSPACE_ROOT")
    if not workspace_root:
        return ""
    return f"PYTHONPATH={workspace_root} "


def install(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    return _install_repo_hooks(repo)


def _install_repo_hooks(repo: Path) -> int:
    return install_repo_hooks(repo)


def install_repo_hooks(repo: Path) -> int:
    hook_dir = Path(__file__).resolve().parent
    workspace_root = Path(__file__).resolve().parents[3]
    hooks_dir = _git_path(repo, "hooks")
    hooks_dir.mkdir(parents=True, exist_ok=True)
    config = _load_config(repo)
    config["repo_guard_enabled"] = True
    _write_config(repo, config)
    for hook_name in ("pre-push", "pre-commit"):
        hook_source = hook_dir / hook_name
        hook_target = hooks_dir / hook_name
        hook_text = hook_source.read_text(encoding="utf-8").replace(
            'installed_workspace_root=""',
            f'installed_workspace_root="{workspace_root}"',
        )
        hook_target.write_text(hook_text, encoding="utf-8")
        hook_target.chmod(0o755)
        print(f"push_guard: installed {hook_target}")
    return 0


def missing_repo_hooks(repo: Path) -> tuple[Path, ...]:
    missing = []
    for hook_name in ("pre-push", "pre-commit"):
        hook_path = git_path(repo, f"hooks/{hook_name}")
        if not hook_path.is_file():
            missing.append(hook_path)
    return tuple(missing)


def install_registered_hooks(args: argparse.Namespace) -> int:
    from agent_tools.tools.repo_registry import validate_repo_registry

    workspace = Path(args.workspace).expanduser().resolve()
    task_dir = Path(args.task_dir).expanduser().resolve()
    try:
        validation = validate_repo_registry(task_dir, workspace=workspace)
    except ValueError as error:
        print(f"push_guard: {error}", file=sys.stderr)
        return 1
    if validation.errors:
        for error in validation.errors:
            print(f"push_guard: invalid repo-registry entry: {error}", file=sys.stderr)
        return 1
    if not validation.repositories:
        print(
            "push_guard: repo-registry is empty; no hooks installed. "
            "Record repositories in the task context repo-registry slot.",
            file=sys.stderr,
        )
        return 1

    installed = 0
    for repo in validation.repositories:
        _install_repo_hooks(repo)
        installed += 1
    print(f"push_guard: installed hooks for {installed} registered repo(s)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    mark_parser = subparsers.add_parser("mark-success")
    mark_parser.add_argument("--repo")
    mark_parser.add_argument("--ref", default="HEAD")
    mark_parser.add_argument(
        "--source",
        help="description of the external build or validation that succeeded",
    )
    mark_parser.add_argument("--receipt", help="validation receipt JSON to verify and record")
    mark_parser.set_defaults(func=mark_success)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--repo")
    status_parser.add_argument("--ref", default="HEAD")
    status_parser.set_defaults(func=status)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("remote_name", nargs="?")
    check_parser.add_argument("remote_url", nargs="?")
    check_parser.add_argument(
        "--allow-override",
        action="store_true",
        default=False,
        help="allow push even when validation is missing",
    )
    check_parser.set_defaults(func=check)

    staged_parser = subparsers.add_parser("check-staged")
    staged_parser.add_argument(
        "--allow-override",
        action="store_true",
        default=False,
        help="allow commit even when staged guarded files are present",
    )
    staged_parser.set_defaults(func=check_staged)

    install_parser = subparsers.add_parser("install-hook")
    install_parser.add_argument("--repo")
    install_parser.set_defaults(func=install)

    install_registered_parser = subparsers.add_parser("install-registered-hooks")
    install_registered_parser.add_argument("--workspace", required=True)
    install_registered_parser.add_argument("--task-dir", required=True)
    install_registered_parser.set_defaults(func=install_registered_hooks)

    enable_repo_guard_parser = subparsers.add_parser("enable-repo-guard")
    enable_repo_guard_parser.add_argument("--repo")
    enable_repo_guard_parser.set_defaults(func=enable_repo_guard)

    disable_repo_guard_parser = subparsers.add_parser("disable-repo-guard")
    disable_repo_guard_parser.add_argument("--repo")
    disable_repo_guard_parser.set_defaults(func=disable_repo_guard)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
