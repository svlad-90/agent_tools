"""Git context helpers for repo_guard."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Sequence


ZERO_SHA = "0" * 40
_GITHUB_RE = re.compile(
    r"(?:github\.com[:/])(?P<owner>[^/\s:]+)/(?P<name>[^/\s]+?)(?:\.git)?$"
)


def run_git(args: Sequence[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def repo_root(path: Path) -> Path:
    return Path(run_git(["rev-parse", "--show-toplevel"], cwd=path))


def git_path(repo: Path, path: str) -> Path:
    git_path_value = Path(run_git(["rev-parse", "--git-path", path], cwd=repo))
    if git_path_value.is_absolute():
        return git_path_value
    return repo / git_path_value


def head_commit(repo: Path, ref: str = "HEAD") -> str:
    return run_git(["rev-parse", "--verify", ref], cwd=repo)


def remote_urls(repo: Path) -> dict[str, str]:
    try:
        output = run_git(["remote", "-v"], cwd=repo)
    except subprocess.CalledProcessError:
        return {}
    result: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        result.setdefault(parts[0], parts[1])
    return result


def current_branch(repo: Path) -> str:
    return run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=repo)


def pre_push_dry_run_stdin(repo: Path, *, remote_name: str = "origin") -> str:
    branch = current_branch(repo)
    local_sha = head_commit(repo)
    local_ref = f"refs/heads/{branch}"
    remote_ref = f"refs/heads/{branch}"
    remote_sha = ZERO_SHA
    upstream = _upstream_ref(repo)
    if upstream is not None:
        upstream_remote, upstream_branch = _split_upstream(upstream)
        if upstream_remote == remote_name:
            remote_ref = f"refs/heads/{upstream_branch}"
            remote_sha = head_commit(repo, upstream)
    return f"{local_ref} {local_sha} {remote_ref} {remote_sha}\n"


def normalize_remote_url(url: str) -> str:
    value = url.strip()
    value = value.removeprefix("git@")
    value = value.removeprefix("ssh://git@")
    value = value.removeprefix("https://")
    value = value.removeprefix("http://")
    return value.removesuffix(".git")


def github_slug(url: str) -> tuple[str, str] | None:
    normalized = normalize_remote_url(url)
    match = _GITHUB_RE.search(normalized)
    if not match:
        return None
    return match.group("owner"), match.group("name")


def _upstream_ref(repo: Path) -> str | None:
    try:
        return run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=repo)
    except subprocess.CalledProcessError:
        return None


def _split_upstream(upstream: str) -> tuple[str, str]:
    remote, _, branch = upstream.partition("/")
    if not branch:
        return remote, remote
    return remote, branch


def pushed_ref_tips(stdin_text: str, repo: Path) -> tuple[str, ...]:
    commits: list[str] = []
    for line in stdin_text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_sha = fields[1]
        if local_sha != ZERO_SHA:
            commits.append(local_sha)
    if commits:
        return tuple(commits)
    return (head_commit(repo),)


def pushed_commits(stdin_text: str, repo: Path) -> tuple[str, ...]:
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
        for commit in run_git(["rev-list", "--reverse", *rev_args], cwd=repo).splitlines():
            if commit not in seen:
                seen.add(commit)
                result.append(commit)
    if result:
        return tuple(result)
    return (head_commit(repo),)


def changed_paths(repo: Path, commits: Sequence[str] = ()) -> tuple[Path, ...]:
    paths: set[Path] = set()
    if commits:
        for commit in commits:
            output = run_git(
                ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit],
                cwd=repo,
            )
            paths.update(Path(line) for line in output.splitlines() if line)
    else:
        tracked = run_git(["diff", "--name-only", "HEAD"], cwd=repo)
        untracked = run_git(["ls-files", "--others", "--exclude-standard"], cwd=repo)
        paths.update(Path(line) for line in tracked.splitlines() if line)
        paths.update(Path(line) for line in untracked.splitlines() if line)
    return tuple(sorted(paths, key=lambda path: path.as_posix().casefold()))


def validation_commits(repo: Path) -> tuple[str, ...]:
    output = run_git(["rev-list", "--reverse", "HEAD", "--not", "--remotes"], cwd=repo)
    commits = tuple(line for line in output.splitlines() if line)
    if commits:
        return commits
    return (head_commit(repo),)
