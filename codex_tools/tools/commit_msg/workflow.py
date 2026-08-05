#!/usr/bin/env python3
"""Format commit messages and verify a rewritten commit series."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from codex_tools.tools.commit_msg import compose_commit_message


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    input: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        input=input,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def module_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{WORKSPACE_ROOT}:{pythonpath}" if pythonpath else str(WORKSPACE_ROOT)
    )
    return env


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args])


def format_message(repo: Path, draft: Path, output: Path, width: int) -> None:
    run(
        [
            sys.executable,
            "-m",
            "codex_tools.tools.commit_msg",
            "--repo",
            str(repo),
            "--width",
            str(width),
            "--output",
            str(output),
            "--check",
            str(draft),
        ],
        env=module_env(),
    )


def format_message_from_parts(
    repo: Path,
    output: Path,
    width: int,
    args: argparse.Namespace,
) -> None:
    draft = compose_commit_message(
        title=args.title,
        body=args.body,
        body_files=args.body_file,
        signoffs=args.signoff,
        assisted_by=args.assisted_by,
        reviewed_by=args.reviewed_by,
        tested_by=args.tested_by,
        acked_by=args.acked_by,
        trailers=args.trailer,
        repo=repo,
    )
    command = [
        sys.executable,
        "-m",
        "codex_tools.tools.commit_msg",
        "--repo",
        str(repo),
        "--width",
        str(width),
        "--output",
        str(output),
        "--check",
        "--no-signoff",
        "-",
    ]
    run(command, cwd=repo, input=draft, env=module_env())


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


def is_zero_sha(value: str) -> bool:
    return value == "0" * 40


def is_zephyr_repo(repo: Path) -> bool:
    return (repo / "Kconfig.zephyr").is_file() and (repo / "west.yml").is_file()


def has_trailer(lines: list[str], key: str) -> bool:
    prefix = f"{key}: "
    return any(line.startswith(prefix) and line[len(prefix) :].strip() for line in lines)


def is_trailer_line(line: str) -> bool:
    if ": " not in line:
        return False
    key, _value = line.split(": ", 1)
    return bool(key) and all(char.isalnum() or char == "-" for char in key)


def has_assisted_by(lines: list[str]) -> bool:
    pattern = re.compile(r"^Assisted-by: [^:\s]+:[^\s]+(?: .+)?$")
    return any(pattern.match(line) for line in lines)


def assisted_by_is_last_trailer(lines: list[str]) -> bool:
    trailer_indexes = [
        index for index, line in enumerate(lines) if is_trailer_line(line)
    ]
    if not trailer_indexes:
        return True
    assisted_indexes = [
        index for index in trailer_indexes if lines[index].startswith("Assisted-by: ")
    ]
    return not assisted_indexes or assisted_indexes[-1] == trailer_indexes[-1]


def pushed_commit_hashes(repo: Path, stdin_text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for line in stdin_text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_sha = fields[1]
        remote_sha = fields[3]
        if is_zero_sha(local_sha):
            continue

        if is_zero_sha(remote_sha):
            rev_args = [local_sha, "--not", "--remotes"]
        else:
            rev_args = [local_sha, "--not", remote_sha, "--remotes"]

        hashes = git(repo, "rev-list", "--reverse", *rev_args).stdout.splitlines()
        for commit_hash in hashes:
            if commit_hash not in seen:
                seen.add(commit_hash)
                result.append(commit_hash)

    if result:
        return result

    head = git(repo, "rev-parse", "--verify", "HEAD").stdout.strip()
    return [head]


def check_series(repo: Path, rev_range: str, width: int) -> int:
    signoff = expected_signoff(repo)
    failures: list[str] = []

    for commit_hash, message in iter_commits(repo, rev_range):
        short_hash = commit_hash[:12]
        lines = message.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if len(line) > width and not is_trailer_line(line):
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


def check_commits(
    repo: Path,
    commit_hashes: list[str],
    width: int,
    *,
    require_assisted_by: bool,
) -> int:
    failures: list[str] = []

    for commit_hash in commit_hashes:
        message = git(repo, "show", "-s", "--format=%B", commit_hash).stdout.rstrip("\n")
        short_hash = commit_hash[:12]
        lines = message.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if len(line) > width and not is_trailer_line(line):
                failures.append(
                    f"{short_hash}:{line_no}: line is {len(line)} columns: {line}"
                )
        if not has_trailer(lines, "Signed-off-by"):
            failures.append(f"{short_hash}: missing Signed-off-by trailer")
        if require_assisted_by and not has_assisted_by(lines):
            failures.append(
                f"{short_hash}: missing Zephyr Assisted-by trailer "
                "(expected: Assisted-by: Agent:Model [tools])"
            )
        if not assisted_by_is_last_trailer(lines):
            failures.append(f"{short_hash}: Assisted-by trailer must be last")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"commit message check ok: {len(commit_hashes)} commit(s)")
    return 0


def check_pre_push(repo: Path, width: int) -> int:
    stdin_text = sys.stdin.read()
    return check_commits(
        repo,
        pushed_commit_hashes(repo, stdin_text),
        width,
        require_assisted_by=is_zephyr_repo(repo),
    )


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


def write_formatted_from_parts(
    repo: Path,
    args: argparse.Namespace,
    output: Path | None,
    width: int,
) -> Path:
    if output is not None:
        format_message_from_parts(repo, output, width, args)
        return output

    temp = tempfile.NamedTemporaryFile(
        mode="w", prefix="commit-message-", suffix=".txt", delete=False
    )
    temp.close()
    path = Path(temp.name)
    format_message_from_parts(repo, path, width, args)
    return path


def has_compose_args(args: argparse.Namespace) -> bool:
    return any(
        (
            args.title,
            args.body,
            args.body_file,
            args.signoff,
            args.assisted_by,
            args.reviewed_by,
            args.tested_by,
            args.acked_by,
            args.trailer,
        )
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Format a commit message and optionally commit/amend/check a series."
    )
    parser.add_argument("--repo", required=True, type=Path, help="Target git repository")
    parser.add_argument("--draft", type=Path, help="Draft commit message file")
    parser.add_argument("--output", type=Path, help="Formatted message output path")
    parser.add_argument("--width", type=int, default=72, help="Maximum line width")
    parser.add_argument("--title", help="Commit subject/title")
    parser.add_argument("--body", action="append", default=[], help="Commit body paragraph")
    parser.add_argument(
        "--body-file",
        action="append",
        default=[],
        type=Path,
        help="Read commit body text from a file",
    )
    parser.add_argument(
        "--signoff",
        nargs="?",
        const="",
        action="append",
        default=[],
        metavar="NAME <EMAIL>",
        help="Add Signed-off-by. Without a value, use repo git identity.",
    )
    parser.add_argument("--assisted-by", action="append", default=[])
    parser.add_argument("--reviewed-by", action="append", default=[])
    parser.add_argument("--tested-by", action="append", default=[])
    parser.add_argument("--acked-by", action="append", default=[])
    parser.add_argument("--trailer", action="append", default=[], metavar="KEY: VALUE")
    parser.add_argument("--commit", action="store_true", help="Run git commit -F")
    parser.add_argument("--amend", action="store_true", help="Run git commit --amend -F")
    parser.add_argument(
        "--check-series",
        metavar="BASE..HEAD",
        help="Check line width and Signed-off-by trailers for a revision range",
    )
    parser.add_argument(
        "--pre-push-check",
        action="store_true",
        help="Read pre-push hook input and check commit messages being pushed",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()

    if args.commit and args.amend:
        raise SystemExit("--commit and --amend are mutually exclusive")

    formatted: Path | None = None
    if args.draft is not None:
        formatted = write_formatted(repo, args.draft.resolve(), args.output, args.width)
        print(formatted)
    elif has_compose_args(args):
        formatted = write_formatted_from_parts(repo, args, args.output, args.width)
        print(formatted)
    elif args.commit or args.amend:
        raise SystemExit("--draft or --title is required with --commit or --amend")

    if args.commit:
        git(repo, "commit", "-F", str(formatted))
    elif args.amend:
        git(repo, "commit", "--amend", "-F", str(formatted))

    if args.check_series:
        return check_series(repo, args.check_series, args.width)
    if args.pre_push_check:
        return check_pre_push(repo, args.width)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
