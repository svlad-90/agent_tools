from __future__ import annotations

import io
import subprocess
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from codex_tools.tools.commit_msg import main as commit_msg_main
from codex_tools.tools.commit_msg.workflow import check_commits, main as workflow_main


class CommitMessageComposeTests(unittest.TestCase):
    def test_compose_typical_trailers_and_wraps_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Vladyslav Goncharuk")
            _git(repo, "config", "user.email", "vladyslav_goncharuk@epam.com")
            stdout = io.StringIO()

            status = _run_stdout(
                stdout,
                [
                    "--repo",
                    str(repo),
                    "--title",
                    "drivers: xen: include stddef.h for NULL",
                    "--body",
                    (
                        "Include <stddef.h> directly in sched.c because it uses "
                        "NULL when issuing sched_op hypercalls."
                    ),
                    "--signoff",
                    "Vladyslav Goncharuk <vladyslav_goncharuk@epam.com>",
                    "--reviewed-by",
                    "Oleksii Moisieiev <oleksii_moisieiev@epam.com>",
                    "--tested-by",
                    "Oleksii Moisieiev <oleksii_moisieiev@epam.com>",
                    "--acked-by",
                    "Dmytro Firsov <dmytro_firsov@epam.com>",
                    "--assisted-by",
                    "Codex:gpt-5 cpp-code-map",
                    "--check",
                ],
            )

        message = stdout.getvalue()
        self.assertEqual(0, status)
        self.assertIn(
            "Signed-off-by: Vladyslav Goncharuk <vladyslav_goncharuk@epam.com>",
            message,
        )
        self.assertIn("Acked-by: Dmytro Firsov <dmytro_firsov@epam.com>", message)
        self.assertTrue(message.rstrip().endswith("Assisted-by: Codex:gpt-5 cpp-code-map"))
        self.assertLessEqual(max(len(line) for line in message.splitlines()), 72)

    def test_workflow_can_commit_from_parts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Vladyslav Goncharuk")
            _git(repo, "config", "user.email", "vladyslav_goncharuk@epam.com")
            (repo / "file.txt").write_text("content\n", encoding="utf-8")
            _git(repo, "add", "file.txt")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                status = workflow_main(
                    [
                        "--repo",
                        str(repo),
                        "--title",
                        "tools: compose commit messages",
                        "--body",
                        "Build the commit message from structured CLI parts.",
                        "--signoff",
                        "--assisted-by",
                        "Codex:gpt-5",
                        "--commit",
                    ]
                )

            message = _git(repo, "log", "-1", "--format=%B").stdout

        self.assertEqual(0, status)
        self.assertIn("tools: compose commit messages", message)
        self.assertIn(
            "Signed-off-by: Vladyslav Goncharuk <vladyslav_goncharuk@epam.com>",
            message,
        )
        self.assertIn("Assisted-by: Codex:gpt-5", message)

    def test_zephyr_assisted_by_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Vladyslav Goncharuk")
            _git(repo, "config", "user.email", "vladyslav_goncharuk@epam.com")
            _commit_file(
                repo,
                "bad",
                textwrap.dedent(
                    """\
                    bad: missing assisted

                    Signed-off-by: Vladyslav Goncharuk <vladyslav_goncharuk@epam.com>
                    """
                ),
            )
            bad = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _commit_file(
                repo,
                "good",
                textwrap.dedent(
                    """\
                    good: has assisted

                    Signed-off-by: Vladyslav Goncharuk <vladyslav_goncharuk@epam.com>
                    Assisted-by: Codex:gpt-5 cpp-code-map
                    """
                ),
            )
            good = _git(repo, "rev-parse", "HEAD").stdout.strip()

            self.assertEqual(
                1,
                check_commits(repo, [bad], 72, require_assisted_by=True),
            )
            self.assertEqual(
                0,
                check_commits(repo, [good], 72, require_assisted_by=True),
            )


def _run_stdout(stdout: io.StringIO, argv: list[str]) -> int:
    with redirect_stdout(stdout):
        return commit_msg_main(argv)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _commit_file(repo: Path, content: str, message: str) -> None:
    path = repo / "file.txt"
    path.write_text(content + "\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    message_path = repo / "message.txt"
    message_path.write_text(message, encoding="utf-8")
    _git(repo, "commit", "-F", str(message_path))
