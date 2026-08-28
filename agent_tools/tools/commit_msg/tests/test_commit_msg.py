from __future__ import annotations

import io
import subprocess
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path

from agent_tools.tools.commit_msg import GitIdentity, format_commit_message, main as commit_msg_main
from agent_tools.tools.commit_msg.workflow import (
    check_commits,
    check_repo_identity,
    main as workflow_main,
    pushed_commit_hashes,
)


class CommitMessageComposeTests(unittest.TestCase):
    def test_compose_typical_trailers_and_wraps_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Example Author")
            _git(repo, "config", "user.email", "author@example.com")
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
                    "Example Author <author@example.com>",
                    "--reviewed-by",
                    "Example Reviewer <reviewer@example.com>",
                    "--tested-by",
                    "Example Tester <tester@example.com>",
                    "--acked-by",
                    "Example Acker <acker@example.com>",
                    "--assisted-by",
                    "Codex:gpt-5 cpp-code-map",
                    "--check",
                ],
            )

        message = stdout.getvalue()
        self.assertEqual(0, status)
        self.assertIn(
            "Signed-off-by: Example Author <author@example.com>",
            message,
        )
        self.assertIn("Acked-by: Example Acker <acker@example.com>", message)
        self.assertTrue(message.rstrip().endswith("Assisted-by: Codex:gpt-5 cpp-code-map"))
        self.assertLessEqual(max(len(line) for line in message.splitlines()), 72)

    def test_workflow_can_commit_from_parts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Example Author")
            _git(repo, "config", "user.email", "author@example.com")
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
            "Signed-off-by: Example Author <author@example.com>",
            message,
        )
        self.assertIn("Assisted-by: Codex:gpt-5", message)
        self.assertTrue(message.rstrip().endswith("Assisted-by: Codex:gpt-5"))

    def test_assisted_by_trailer_is_last_for_arbitrary_trailers(self) -> None:
        stdout = io.StringIO()

        status = _run_stdout(
            stdout,
            [
                "--title",
                "tools: order commit trailers",
                "--body",
                "Keep Assisted-by at the end of the trailer block.",
                "--trailer",
                "Assisted-by: Codex:gpt-5 cpp-code-map",
                "--trailer",
                "Signed-off-by: Example Author <author@example.com>",
                "--no-signoff",
            ],
        )

        message = stdout.getvalue()
        self.assertEqual(0, status)
        self.assertTrue(
            message.rstrip().endswith("Assisted-by: Codex:gpt-5 cpp-code-map")
        )

    def test_format_existing_message_keeps_assisted_by_last(self) -> None:
        message = format_commit_message(
            textwrap.dedent(
                """\
                tools: order existing trailers

                Assisted-by: Codex:gpt-5 cpp-code-map
                Signed-off-by: Example Author <author@example.com>
                """
            ),
            identity=None,
        )

        self.assertTrue(
            message.rstrip().endswith("Assisted-by: Codex:gpt-5 cpp-code-map")
        )

    def test_format_existing_message_deduplicates_signoff_with_blank_trailer_gap(self) -> None:
        message = format_commit_message(
            textwrap.dedent(
                """\
                tools: normalize spaced trailers

                Body.

                Signed-off-by: Example Author <author@example.com>

                Assisted-by: Codex:gpt-5
                """
            ),
            identity=GitIdentity("Example Author", "author@example.com"),
        )

        self.assertEqual(1, message.count("Signed-off-by: Example Author <author@example.com>"))
        self.assertTrue(message.rstrip().endswith("Assisted-by: Codex:gpt-5"))

    def test_zephyr_assisted_by_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Example Author")
            _git(repo, "config", "user.email", "author@example.com")
            _commit_file(
                repo,
                "bad",
                textwrap.dedent(
                    """\
                    bad: missing assisted

                    Signed-off-by: Example Author <author@example.com>
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

                    Signed-off-by: Example Author <author@example.com>
                    Assisted-by: Codex:gpt-5 cpp-code-map
                    """
                ),
            )
            good = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _commit_file(
                repo,
                "wrong-order",
                textwrap.dedent(
                    """\
                    bad: assisted is not last

                    Assisted-by: Codex:gpt-5 cpp-code-map
                    Signed-off-by: Example Author <author@example.com>
                    """
                ),
            )
            wrong_order = _git(repo, "rev-parse", "HEAD").stdout.strip()

            self.assertEqual(
                1,
                check_commits(repo, [bad], 72, require_assisted_by=True),
            )
            self.assertEqual(
                0,
                check_commits(repo, [good], 72, require_assisted_by=True),
            )
            self.assertEqual(
                1,
                check_commits(repo, [wrong_order], 72, require_assisted_by=True),
            )

    def test_pre_push_check_ignores_imported_remote_base_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Example Author")
            _git(repo, "config", "user.email", "author@example.com")
            _commit_file(repo, "old-base", "old: base\n")
            old_target = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _git(repo, "update-ref", "refs/remotes/origin/topic", old_target)

            _commit_file(repo, "upstream-base", "upstream: refreshed base\n")
            upstream_base = _git(repo, "rev-parse", "HEAD").stdout.strip()
            _git(repo, "update-ref", "refs/remotes/upstream/base", upstream_base)

            _commit_file(
                repo,
                "topic",
                textwrap.dedent(
                    """\
                    topic: local change

                    Signed-off-by: Example Author <author@example.com>
                    Assisted-by: Codex:gpt-5 cpp-code-map
                    """
                ),
            )
            local_topic = _git(repo, "rev-parse", "HEAD").stdout.strip()
            stdin_text = (
                f"refs/heads/topic {local_topic} "
                f"refs/heads/topic {old_target}\n"
            )

            self.assertEqual(
                [local_topic],
                pushed_commit_hashes(repo, stdin_text),
            )

    def test_identity_check_requires_private_rule_for_xen_troops_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Personal User")
            _git(repo, "config", "user.email", "personal@example.com")
            _git(repo, "remote", "add", "origin", "git@github.com:xen-troops/demo.git")

            self.assertEqual(1, check_repo_identity(repo))

    def test_identity_check_passes_with_matching_private_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            repo.mkdir()
            _git(repo, "init")
            _git(repo, "config", "user.name", "Work User")
            _git(repo, "config", "user.email", "work@example.com")
            _git(repo, "remote", "add", "origin", "https://github.com/xen-troops/demo.git")
            rules = root / "identity-rules.json"
            rules.write_text(
                textwrap.dedent(
                    """\
                    {
                      "rules": [
                        {
                          "github_owner": "xen-troops",
                          "user_name": "Work User",
                          "user_email": "work@example.com"
                        }
                      ]
                    }
                    """
                ),
                encoding="utf-8",
            )
            _git(repo, "config", "agentTools.identityRulesFile", str(rules))

            self.assertEqual(0, check_repo_identity(repo))

    def test_identity_check_mismatch_does_not_print_current_identity(self) -> None:
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo = root / "repo"
            repo.mkdir()
            _git(repo, "init")
            _git(repo, "config", "user.name", "Personal User")
            _git(repo, "config", "user.email", "personal@example.com")
            _git(repo, "remote", "add", "origin", "git@github.com:xen-troops/demo.git")
            rules = root / "identity-rules.json"
            rules.write_text(
                textwrap.dedent(
                    """\
                    {
                      "rules": [
                        {
                          "github_owner": "xen-troops",
                          "user_name": "Work User",
                          "user_email": "work@example.com"
                        }
                      ]
                    }
                    """
                ),
                encoding="utf-8",
            )
            _git(repo, "config", "agentTools.identityRulesFile", str(rules))

            with redirect_stderr(stderr):
                self.assertEqual(1, check_repo_identity(repo))

        err = stderr.getvalue()
        self.assertIn("local git config", err)
        self.assertNotIn("Personal User", err)
        self.assertNotIn("personal@example.com", err)

    def test_identity_check_ignores_unrelated_github_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            _git(repo, "init")
            _git(repo, "config", "user.name", "Personal User")
            _git(repo, "config", "user.email", "personal@example.com")
            _git(repo, "remote", "add", "origin", "git@github.com:example/demo.git")

            self.assertEqual(0, check_repo_identity(repo))


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
