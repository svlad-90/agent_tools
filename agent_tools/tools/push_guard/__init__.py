"""Pre-push validation guard for workspace repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence


ZERO_SHA = "0" * 40
FORBIDDEN_PUSH_PATH_PREFIXES = (
    "agent_tools/paf_workspace/domains/environments/private_envs/",
)


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
    git_path = Path(_run_git(["rev-parse", "--git-path", path], cwd=repo))
    if git_path.is_absolute():
        return git_path
    return repo / git_path


def _stamp_dir(repo: Path) -> Path:
    return _git_path(repo, "codex_push_guard")


def _stamp_path(repo: Path, commit: str) -> Path:
    return _stamp_dir(repo) / f"{commit}.json"


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
        "recorded_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    _stamp_path(repo, commit).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def mark_success(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    commit = _head_commit(repo, args.ref)
    source = args.source or "external validation"

    _record_success(repo, commit, source)
    print(f"push_guard: recorded successful validation for {commit}")
    print(f"push_guard: source: {source}")
    return 0


def status(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    commit = _head_commit(repo, args.ref)
    stamp_path = _stamp_path(repo, commit)

    print(f"push_guard: repo: {repo}")
    print(f"push_guard: commit: {commit}")
    print(f"push_guard: stamp: {stamp_path}")
    if not stamp_path.is_file():
        print("push_guard: status: missing")
        return 1

    payload = json.loads(stamp_path.read_text(encoding="utf-8"))
    print("push_guard: status: recorded")
    print(f"push_guard: recorded_at: {payload.get('recorded_at', '<unknown>')}")
    source = payload.get("source") or payload.get("command") or "<unknown>"
    print(f"push_guard: source: {source}")
    return 0


def _pushed_commits(stdin_text: str, repo: Path) -> list[str]:
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


def _pushed_paths(repo: Path, commits: Sequence[str]) -> set[str]:
    paths: set[str] = set()
    for commit in commits:
        output = _run_git(["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit], cwd=repo)
        paths.update(path for path in output.splitlines() if path)
    return paths


def _forbidden_pushed_paths(repo: Path, commits: Sequence[str]) -> list[str]:
    forbidden: list[str] = []
    for path in sorted(_pushed_paths(repo, commits)):
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_PUSH_PATH_PREFIXES):
            forbidden.append(path)
    return forbidden


def check(args: argparse.Namespace) -> int:
    repo = _repo_root(Path.cwd())
    stdin_text = sys.stdin.read()
    commits = _pushed_commits(stdin_text, repo)
    forbidden_paths = _forbidden_pushed_paths(repo, commits)
    if forbidden_paths:
        print("push_guard: push blocked; private environment files are forbidden:", file=sys.stderr)
        for path in forbidden_paths:
            print(f"  {path}", file=sys.stderr)
        print(
            "Keep private reusable environment overlays under "
            "agent_tools/paf_workspace/domains/environments/private_envs/, "
            "but leave that directory untracked.",
            file=sys.stderr,
        )
        return 1

    missing = [
        commit
        for commit in commits
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
        "  python -m agent_tools.tools.push_guard mark-success "
        "--repo <target-repo> --source <build-or-validation-id>",
        file=sys.stderr,
    )
    if args.allow_override:
        print("push_guard: override enabled; allowing push", file=sys.stderr)
        return 0
    return 1


def install(args: argparse.Namespace) -> int:
    repo = _target_repo(args)
    hook_source = Path(__file__).resolve().with_name("pre-push")
    workspace_root = Path(__file__).resolve().parents[3]
    hooks_dir = _git_path(repo, "hooks")
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_target = hooks_dir / "pre-push"
    hook_text = hook_source.read_text(encoding="utf-8").replace(
        'installed_workspace_root=""',
        f'installed_workspace_root="{workspace_root}"',
    )
    hook_target.write_text(hook_text, encoding="utf-8")
    hook_target.chmod(0o755)
    print(f"push_guard: installed {hook_target}")
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
    mark_parser.set_defaults(func=mark_success)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--repo")
    status_parser.add_argument("--ref", default="HEAD")
    status_parser.set_defaults(func=status)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument(
        "--allow-override",
        action="store_true",
        default=False,
        help="allow push even when validation is missing",
    )
    check_parser.set_defaults(func=check)

    install_parser = subparsers.add_parser("install-hook")
    install_parser.add_argument("--repo")
    install_parser.set_defaults(func=install)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
