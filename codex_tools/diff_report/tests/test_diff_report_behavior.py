from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from codex_tools.diff_report.core import generate_report
from codex_tools.diff_report.models import DiffReportError


class DiffReportBehaviorTests(unittest.TestCase):
    def test_repo_range_renders_git_metadata_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            self._git(repo, "init")
            self._git(repo, "config", "user.name", "Test Author")
            self._git(repo, "config", "user.email", "author@example.com")
            (repo / "app.py").write_text("print('old')\n", encoding="utf-8")
            self._git(repo, "add", "app.py")
            self._git(repo, "commit", "-m", "base")
            (repo / "app.py").write_text("print('new')\n", encoding="utf-8")
            self._git(repo, "commit", "-am", "change subject", "-m", "Body details.")

            output = Path(temp_dir) / "report.html"
            generate_report(
                output_path=output,
                title="Repo report",
                repo_path=repo,
                rev_range="HEAD^..HEAD",
                context=3,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn("<h1>Repo report</h1>", html)
        self.assertIn("Commit ID", html)
        self.assertIn("Subject", html)
        self.assertIn("change subject", html)
        self.assertIn("Commit Message", html)
        self.assertIn("Body details.", html)
        self.assertIn("Diff Stats", html)
        self.assertIn("Files changed", html)
        self.assertIn("<strong>1</strong>", html)
        self.assertIn("print(&#x27;new&#x27;)", html)

    def test_comment_artifact_and_story_variants_render(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            log_path = root / "runtime.log"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/src/app.py b/src/app.py
                    index 1111111..2222222 100644
                    --- a/src/app.py
                    +++ b/src/app.py
                    @@ -1,3 +1,4 @@
                     def run():
                    +    call()
                         return 1
                    diff --git a/docs/CMakeLists.txt b/docs/CMakeLists.txt
                    new file mode 100644
                    index 0000000..3333333
                    --- /dev/null
                    +++ b/docs/CMakeLists.txt
                    @@ -0,0 +1 @@
                    +add_subdirectory(app)
                    """
                ),
                encoding="utf-8",
            )
            log_path.write_text("boot\nPASS artifact\n", encoding="utf-8")
            comments_path.write_text(
                json.dumps(
                    {
                        "summary": "Plain summary",
                        "vocabulary": {
                            "vCPU": {
                                "definition": "Virtual CPU exposed by Xen.",
                                "aliases": ["vCPUs"],
                            },
                            "event channel": "Xen notification path.",
                            "hypercall": "Controlled call into Xen.",
                        },
                        "summary_blocks": [
                            "String summary block mentions vCPU",
                            {"type": "paragraph", "text": "Paragraph summary block"},
                            {
                                "diagram": "flow",
                                "diagram_focus": "call()",
                                "diagram_notes": [
                                    {"target": "call()", "text": "Call note"},
                                ],
                            },
                            {"log": "runtime", "log_focus": "PASS"},
                        ],
                        "files": {
                            "src/app.py": {
                                "body": "File body",
                                "diagram": "flow",
                                "diagram_focus": "call()",
                                "log": "runtime",
                                "log_focus": "PASS",
                            },
                        },
                        "inline": [
                            {
                                "file": "src/app.py",
                                "line": 2,
                                "range": [1, 3],
                                "title": "Inline title",
                                "body": "Inline body uses a hypercall",
                                "diagram": "flow",
                                "diagram_focus": ["call()"],
                                "diagram_notes": [
                                    {"target": "call()", "text": "Inline note"},
                                ],
                                "log": "runtime",
                                "log_focus": ["PASS"],
                            },
                        ],
                        "diagrams": {
                            "flow": {
                                "title": "Inline SVG diagram",
                                "svg_inline": (
                                    "<svg xmlns='http://www.w3.org/2000/svg'>"
                                    "<text>call()</text></svg>"
                                ),
                                "code_links": [
                                    {
                                        "target": "call()",
                                        "file": "src/app.py",
                                        "line": 2,
                                        "title": "Open call",
                                        "range": {"start": 1, "end": 3},
                                    },
                                ],
                            },
                        },
                        "logs": {
                            "runtime": {
                                "title": "Path runtime log",
                                "path": "runtime.log",
                            },
                        },
                        "story": [
                            {"title": "File step", "body": "Follow the event channel.", "file": "src/app.py"},
                            {"title": "Line step", "file": "src/app.py", "line": 2},
                            {
                                "title": "Comment step",
                                "comment": {"file": "src/app.py", "line": 2},
                            },
                            {
                                "title": "Diagram step",
                                "diagram": "flow",
                                "diagram_focus": "call()",
                                "diagram_zoom": 1.7,
                                "artifact_comment": "This call is the guide point.",
                            },
                            {
                                "title": "Log step",
                                "body": "Read the runtime proof.",
                                "log": "runtime",
                                "log_focus": "PASS",
                                "log_zoom": 1.25,
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            generate_report(
                output_path=output,
                title="Artifact variants",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output.read_text(encoding="utf-8")

        expected_fragments = [
            "String summary block mentions",
            "Paragraph summary block",
            "File body",
            "Inline title",
            "Inline body uses a",
            'class="vocabulary-ref"',
            "vocabulary-popover",
            "Virtual CPU exposed by Xen.",
            "Xen notification path.",
            "Controlled call into Xen.",
            'data-story-body-html="Follow the &lt;span class=&quot;vocabulary-ref-wrap&quot;',
            'data-diagram-id="flow"',
            'data-log-id="runtime"',
            'data-diagram-focus="[&quot;call()&quot;]"',
            'data-log-focus="[&quot;PASS&quot;]"',
            "Call note",
            "Inline note",
            'id="diagram-template-flow"',
            'data-code-links=',
            'id="log-template-runtime"',
            "PASS artifact",
            'data-story-index="4"',
            'data-story-target="line-src-app.py-2"',
            'data-story-diagram="flow"',
            'data-story-diagram-focus="[&quot;call()&quot;]"',
            'data-story-diagram-zoom="1.7"',
            'data-story-artifact-comment="This call is the guide point."',
            'data-story-log="runtime"',
            'data-story-log-focus="[&quot;PASS&quot;]"',
            'data-story-log-zoom="1.25"',
            'data-story-artifact-comment="Read the runtime proof."',
            'data-review-comment-link="comment-src-app.py-2"',
            'data-diff-kind="add"',
            'data-settings-toggle',
            'aria-label="Settings"><span aria-hidden="true"></span></button>',
            'report-settings-launcher',
            'data-settings-modal',
            'role="dialog" aria-modal="true" aria-labelledby="settings-title"',
            "Text scale",
            'data-text-scale-step="-0.1"',
            'data-text-scale-reset',
            'data-text-scale-step="0.1"',
            'data-copy-markdown-menu',
            'data-copy-plain-action',
            'data-copy-markdown-action',
            ">Copy</button>",
            "Copy as Markdown",
            "copyPlainSelection",
            "contextmenu",
            "selectedTextWithin",
            "```diff",
            "navigator.clipboard.writeText",
            'href="#docs-CMakeLists.txt">CMakeLists.txt</a>',
            'id="docs-CMakeLists.txt"',
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self._assert_contains(html, fragment)
        self.assertRegex(
            html,
            r'(?s)id="diagram-search".*data-diagram-search="prev".*data-diagram-search="next"',
        )
        self.assertNotIn("story-controls", html)
        self.assertNotIn("story-settings-launcher", html)
        self.assertNotIn('id="story-counter"', html)
        self.assertNotIn("story-top-inline", html)
        self.assertNotIn("data-theme-toggle", html)
        self.assertNotIn("data-copy-mode-value", html)
        self.assertNotIn("codex-diff-report-copy-mode", html)
        self.assertNotIn("General view", html)
        self.assertNotIn("data-diagram-general", html)
        self.assertIn('data-story-nav="prev"', html)
        self.assertIn('data-story-nav="next"', html)

    def test_review_text_linkifies_complete_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            url = "https://example.test/path?a=1&b=2"
            link = (
                '<a href="https://example.test/path?a=1&amp;b=2" '
                'target="_blank" rel="noopener noreferrer">'
                "https://example.test/path?a=1&amp;b=2</a>"
            )
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/src/app.py b/src/app.py
                    index 1111111..2222222 100644
                    --- a/src/app.py
                    +++ b/src/app.py
                    @@ -1 +1,2 @@
                     keep()
                    +added()
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "summary": f"Summary link: {url}.",
                        "files": {"src/app.py": f"File link: {url})"},
                        "inline": [
                            {
                                "file": "src/app.py",
                                "line": 2,
                                "body": f"Inline link: {url};",
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            generate_report(
                output_path=output,
                title="URL report",
                diff_file=diff_path,
                comments_file=comments_path,
            )
            html = output.read_text(encoding="utf-8")

        self.assertEqual(3, html.count(link))
        self.assertNotIn('href="https://example"', html)

    def test_refresh_targets_records_moved_ambiguous_and_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    index 1111111..2222222 100644
                    --- a/app.py
                    +++ b/app.py
                    @@ -1,4 +1,5 @@
                     def run():
                    +    inserted()
                         moved()
                         duplicate()
                         duplicate()
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "inline": [
                            {
                                "file": "app.py",
                                "line": 50,
                                "range": {"start": 50, "end": 50},
                                "title": "Moved",
                                "body": "Moved body",
                                "target": {"content": "    moved()"},
                            },
                            {
                                "file": "app.py",
                                "line": 51,
                                "title": "Ambiguous",
                                "body": "Ambiguous body",
                                "target": {"content": "    duplicate()"},
                            },
                            {
                                "file": "app.py",
                                "line": 52,
                                "title": "Missing",
                                "body": "Missing body",
                                "target": {"content": "    missing()"},
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), self.assertRaisesRegex(
                DiffReportError,
                "target is not rendered",
            ):
                generate_report(
                    output_path=output,
                    title="Refresh targets",
                    diff_file=diff_path,
                    comments_file=comments_path,
                    refresh_targets=True,
                )

            refreshed = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))

        inline = refreshed["inline"]
        statuses = [item["target"]["status"] for item in inline]
        self.assertEqual(["moved", "ambiguous", "not_found"], statuses)
        self.assertEqual(3, inline[0]["line"])
        self.assertEqual(50, inline[0]["target"]["previous_line"])
        self.assertEqual({"start": 3, "end": 3}, inline[0]["range"])
        self.assertEqual([4, 5], inline[1]["target"]["candidate_lines"])
        self.assertFalse(inline[1]["target"]["found"])
        self.assertFalse(inline[2]["target"]["found"])
        self.assertIn("attention=2", stdout.getvalue())
        self.assertFalse(output.exists())

    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _assert_contains(self, text: str, fragment: str) -> None:
        self.assertTrue(fragment in text, f"missing fragment: {fragment!r}")


if __name__ == "__main__":
    unittest.main()
