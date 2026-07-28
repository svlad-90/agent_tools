#!/usr/bin/env python3
"""Format commit messages and verify a rewritten commit series."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args])


def format_message(repo: Path, draft: Path, output: Path, width: int) -> None:
    run(
        [
            sys.executable,
            "-m",
            "codex_tools.commit_msg",
            "--repo",
            str(repo),
            "--width",
            str(width),
            "--output",
            str(output),
            "--check",
            str(draft),
        ]
    )


def expected_signoff(repo: Path) -> str:
    name = git(repo, "config", "user.name").stdout.strip()
    email = git(repo, "config", "user.email").stdout.strip()
    if not name or not email:
        raise SystemExit("git user.name and user.email must be configured")
    return f"Signed-off-by: {name} <{email}>"


def iter_commits(repo: Path, rev_range: str) -> list[tuple[str, str]]:
    hashes = git(repo, "rev-list", "--reverse", rev_range).stdout.splitlines()
    commits: list[tuple[str, str]] = []
    for commit_hash in hashes:
        body = git(repo, "show", "-s", "--format=%B", commit_hash).stdout
        commits.append((commit_hash, body.rstrip("\n")))
    return commits


def check_series(repo: Path, rev_range: str, width: int) -> int:
    signoff = expected_signoff(repo)
    failures: list[str] = []

    for commit_hash, message in iter_commits(repo, rev_range):
        short_hash = commit_hash[:12]
        lines = message.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if len(line) > width:
                failures.append(
                    f"{short_hash}:{line_no}: line is {len(line)} columns: {line}"
                )
        if signoff not in lines:
            failures.append(f"{short_hash}: missing trailer: {signoff}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"commit message check ok: {rev_range}")
    return 0


def write_formatted(repo: Path, draft: Path, output: Path | None, width: int) -> Path:
    if output is not None:
        format_message(repo, draft, output, width)
        return output

    temp = tempfile.NamedTemporaryFile(
        mode="w", prefix="commit-message-", suffix=".txt", delete=False
    )
    temp.close()
    path = Path(temp.name)
    format_message(repo, draft, path, width)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format a commit message and optionally commit/amend/check a series."
    )
    parser.add_argument("--repo", required=True, type=Path, help="Target git repository")
    parser.add_argument("--draft", type=Path, help="Draft commit message file")
    parser.add_argument("--output", type=Path, help="Formatted message output path")
    parser.add_argument("--width", type=int, default=72, help="Maximum line width")
    parser.add_argument("--commit", action="store_true", help="Run git commit -F")
    parser.add_argument("--amend", action="store_true", help="Run git commit --amend -F")
    parser.add_argument(
        "--check-series",
        metavar="BASE..HEAD",
        help="Check line width and Signed-off-by trailers for a revision range",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()

    if args.commit and args.amend:
        raise SystemExit("--commit and --amend are mutually exclusive")

    formatted: Path | None = None
    if args.draft is not None:
        formatted = write_formatted(repo, args.draft.resolve(), args.output, args.width)
        print(formatted)
    elif args.commit or args.amend:
        raise SystemExit("--draft is required with --commit or --amend")

    if args.commit:
        git(repo, "commit", "-F", str(formatted))
    elif args.amend:
        git(repo, "commit", "--amend", "-F", str(formatted))

    if args.check_series:
        return check_series(repo, args.check_series, args.width)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
