from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock
from pathlib import Path

from agent_tools.tools.diff_report.core import generate_report
from agent_tools.tools.diff_report.drawio_graph import drawio_graph_artifacts
from agent_tools.tools.diff_report.drawio_graph import drawio_graph_svg
from agent_tools.tools.diff_report.drawio_graph import drawio_graph_xml
from agent_tools.tools.diff_report.models import DiffReportError


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
        self.assertIn('<section class="review-nav" id="review-comments">', html)
        self.assertIn("<h2>Files Changed</h2>", html)
        self.assertIn('href="#app.py">app.py</a>', html)

    def test_diff_report_without_comments_keeps_changed_file_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/deep/path/app.py b/deep/path/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/deep/path/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    diff --git a/deep/path/tests/test_app.py b/deep/path/tests/test_app.py
                    new file mode 100644
                    index 0000000..329ae20
                    --- /dev/null
                    +++ b/deep/path/tests/test_app.py
                    @@ -0,0 +1 @@
                    +def test_app(): pass
                    """
                ),
                encoding="utf-8",
            )

            generate_report(
                output_path=output,
                title="Plain diff report",
                diff_file=diff_path,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn('<section class="review-nav" id="review-comments">', html)
        self.assertIn("<h2>Files Changed</h2>", html)
        self.assertIn('<span class="review-nav-label">deep/path</span>', html)
        self.assertIn('href="#deep-path-app.py">app.py</a>', html)
        self.assertIn('href="#deep-path-tests-test_app.py">test_app.py</a>', html)
        self.assertIn("review-nav-node review-nav-file", html)

    def test_empty_diff_report_omits_diff_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "empty.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text("", encoding="utf-8")
            comments_path.write_text('{"summary": "Teaching summary"}\n', encoding="utf-8")

            generate_report(
                output_path=output,
                title="Teaching report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn("Teaching summary", html)
        self.assertNotIn("Diff Stats", html)
        self.assertNotIn('<table class="diff"', html)

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
                    diff --git a/deep/path/app2.py b/deep/path/app2.py
                    new file mode 100644
                    index 0000000..4444444
                    --- /dev/null
                    +++ b/deep/path/app2.py
                    @@ -0,0 +1 @@
                    +value = 2
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
            'href="#deep-path-app2.py">app2.py</a>',
            '<span class="review-nav-label">deep/path</span>',
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self._assert_contains(html, fragment)
        self.assertRegex(
            html,
            r'(?s)id="diagram-search".*data-diagram-search="prev".*data-diagram-search="next"',
        )
        self.assertRegex(
            html,
            r'(?s)<li class="review-nav-node review-nav-file review-nav-file-with-comments">.*?'
            r'href="#src-app.py">app.py</a>',
        )
        self.assertRegex(
            html,
            r'(?s)<li class="review-nav-node review-nav-file">.*?'
            r'href="#docs-CMakeLists.txt">CMakeLists.txt</a>',
        )
        self.assertNotIn("review-nav-toggle", html)
        self.assertNotIn("review-nav-toggle-spacer", html)
        self.assertNotIn("data-review-nav-reset", html)
        self.assertNotIn("review-nav-passthrough", html)
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

    def test_non_plantuml_diagram_keeps_its_own_svg_styles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    """
                ),
                encoding="utf-8",
            )
            drawio_svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                "<style>.line-red { stroke: #b91c1c; }</style>"
                '<path class="line-red" d="M 0 0 L 10 10"/>'
                "</svg>"
            )
            plantuml_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><text>x</text></svg>'
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [
                            {"type": "diagram", "diagram": "drawio"},
                            {"type": "diagram", "diagram": "plantuml"},
                        ],
                        "diagrams": {
                            "drawio": {
                                "title": "Draw.io diagram",
                                "renderer": "drawio",
                                "svg_inline": drawio_svg,
                            },
                            "plantuml": {
                                "title": "PlantUML diagram",
                                "svg_inline": plantuml_svg,
                            },
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            generate_report(
                output_path=output,
                title="Renderer report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn('id="diagram-template-drawio"', html)
        self.assertIn(".line-red { stroke: #b91c1c; }", html)
        self.assertNotIn('id="diagram-template-drawio" data-title="Draw.io diagram"><svg class="plantuml-diagram"', html)
        self.assertIn('id="diagram-template-plantuml"', html)
        self.assertIn('<svg class="plantuml-diagram"', html)

    def test_drawio_source_defaults_to_drawio_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = root / "tasks" / "demo"
            diff_dir = task / "report" / "diff"
            drawio_dir = task / "report" / "drawio"
            diff_dir.mkdir(parents=True)
            drawio_dir.mkdir(parents=True)
            diff_path = root / "change.patch"
            comments_path = diff_dir / "comments.json"
            output = diff_dir / "report.html"
            source_path = drawio_dir / "pipeline.drawio"
            svg_path = drawio_dir / "pipeline.svg"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    """
                ),
                encoding="utf-8",
            )
            source_path.write_text("<mxfile />", encoding="utf-8")
            svg_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><text>x</text></svg>',
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "pipeline"}],
                        "diagrams": {
                            "pipeline": {
                                "title": "Pipeline",
                                "source": "../drawio/pipeline.drawio",
                                "svg": "../drawio/pipeline.svg",
                            },
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            generate_report(
                output_path=output,
                title="Draw.io default report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output.read_text(encoding="utf-8")

        self.assertIn('data-diagram-renderer="drawio"', html)
        self.assertIn('data-diagram-source-task="tasks/demo"', html)
        self.assertIn('data-diagram-source-path="report/drawio/pipeline.drawio"', html)
        self.assertIn('data-diagram-svg-path="report/drawio/pipeline.svg"', html)
        self.assertNotIn('<svg class="plantuml-diagram"', html)

    def test_drawio_graph_renders_with_layered_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "pipeline"}],
                        "diagrams": {
                            "pipeline": {
                                "title": "Generated draw.io graph",
                                "drawio_graph": {
                                    "nodes": [
                                        {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                                        {"id": "parser", "label": "Parser", "rank": 1, "lane": 0},
                                        {"id": "normalizer", "label": "Normalizer", "rank": 1, "lane": 1},
                                        {"id": "writer", "label": "Writer", "rank": 2, "lane": 0},
                                    ],
                                    "edges": [
                                        {"from": "input", "to": "parser", "label": "reads"},
                                        {"from": "parser", "to": "normalizer", "label": "normalizes"},
                                        {"from": "normalizer", "to": "writer", "label": "emits"},
                                    ],
                                },
                            },
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.drawio_graph._drawio_export_executable",
                return_value=None,
            ):
                generate_report(
                    output_path=output,
                    title="Generated draw.io graph report",
                    diff_file=diff_path,
                    comments_file=comments_path,
                )

            html = output.read_text(encoding="utf-8")

        self.assertIn('data-diagram-renderer="drawio"', html)
        self.assertIn('id="diagram-template-pipeline"', html)
        self.assertIn("Parser", html)
        self.assertIn("emits", html)
        self.assertIn('marker-end="url(#drawio-graph-arrow)"', html)
        self.assertIn('<path d="M 192.0 224.0 L 240.0 224.0"/>', html)
        self.assertIn('<rect x="175.0" y="205.0" width="82" height="18"', html)
        self.assertNotIn('<svg class="plantuml-diagram"', html)

    def test_drawio_graph_can_delegate_layout_to_graphviz(self) -> None:
        if shutil.which("dot") is None:
            self.skipTest("Graphviz dot is not available")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "pipeline"}],
                        "diagrams": {
                            "pipeline": {
                                "title": "Graphviz draw.io graph",
                                "drawio_graph": {
                                    "layout_engine": "graphviz",
                                    "nodes": [
                                        {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                                        {"id": "parser", "label": "Parser", "rank": 1, "lane": 0},
                                        {"id": "writer", "label": "Writer", "rank": 2, "lane": 0},
                                    ],
                                    "edges": [
                                        {"from": "input", "to": "parser", "label": "reads"},
                                        {"from": "parser", "to": "writer", "label": "emits"},
                                    ],
                                },
                            },
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.drawio_graph._drawio_export_executable",
                return_value=None,
            ):
                generate_report(
                    output_path=output,
                    title="Graphviz draw.io graph report",
                    diff_file=diff_path,
                    comments_file=comments_path,
                )

            html = output.read_text(encoding="utf-8")

        self.assertIn('data-diagram-renderer="drawio"', html)
        self.assertIn('marker-end="url(#drawio-graph-arrow)"', html)
        self.assertIn("Parser", html)
        self.assertIn("emits", html)
        self.assertNotIn("Generated by graphviz", html)

    def test_drawio_graph_writes_editable_artifacts_when_paths_are_declared(self) -> None:
        if shutil.which("dot") is None:
            self.skipTest("Graphviz dot is not available")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task = root / "tasks" / "demo"
            diff_dir = task / "report" / "diff"
            diff_dir.mkdir(parents=True)
            diff_path = root / "change.patch"
            comments_path = diff_dir / "comments.json"
            output = diff_dir / "report.html"
            diff_path.write_text(
                textwrap.dedent(
                    """\
                    diff --git a/app.py b/app.py
                    new file mode 100644
                    index 0000000..2f9a147
                    --- /dev/null
                    +++ b/app.py
                    @@ -0,0 +1 @@
                    +print('new')
                    """
                ),
                encoding="utf-8",
            )
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "pipeline"}],
                        "diagrams": {
                            "pipeline": {
                                "title": "Editable graph",
                                "source": "../drawio/pipeline.drawio",
                                "svg": "../drawio/pipeline.svg",
                                "drawio_graph": {
                                    "layout_engine": "graphviz",
                                    "nodes": [
                                        {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                                        {"id": "parser", "label": "Parser", "rank": 1, "lane": 0},
                                    ],
                                    "edges": [{"from": "input", "to": "parser", "label": "reads"}],
                                },
                            },
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.drawio_graph._drawio_export_executable",
                return_value=None,
            ):
                generate_report(
                    output_path=output,
                    title="Editable generated draw.io graph report",
                    diff_file=diff_path,
                    comments_file=comments_path,
                )

            html = output.read_text(encoding="utf-8")
            source = task / "report" / "drawio" / "pipeline.drawio"
            svg = task / "report" / "drawio" / "pipeline.svg"
            source_exists = source.is_file()
            svg_exists = svg.is_file()
            source_text = source.read_text(encoding="utf-8") if source_exists else ""
            svg_text = svg.read_text(encoding="utf-8") if svg_exists else ""

        self.assertTrue(source_exists)
        self.assertTrue(svg_exists)
        self.assertIn("<mxfile>", source_text)
        self.assertIn('marker-end="url(#drawio-graph-arrow)"', svg_text)
        self.assertNotIn("Generated by graphviz", svg_text)
        self.assertIn('data-diagram-source-task="tasks/demo"', html)
        self.assertIn('data-diagram-source-path="report/drawio/pipeline.drawio"', html)
        self.assertIn('data-diagram-svg-path="report/drawio/pipeline.svg"', html)

    def test_drawio_graph_xml_uses_graphviz_geometry(self) -> None:
        if shutil.which("dot") is None:
            self.skipTest("Graphviz dot is not available")
        xml = drawio_graph_xml(
            {
                "layout_engine": "graphviz",
                "nodes": [
                    {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                    {"id": "parser", "label": "Parser", "rank": 1, "lane": 0},
                    {"id": "writer", "label": "Writer", "rank": 2, "lane": 0},
                ],
                "edges": [
                    {"from": "input", "to": "parser", "label": "reads"},
                    {"from": "parser", "to": "writer", "label": "emits"},
                ],
            },
            diagram_key="pipeline",
        )

        self.assertIn('<mxCell id="node-parser"', xml)
        self.assertIn('x="0" y="132"', xml)
        self.assertIn("exitX=0.500;exitY=1.000", xml)
        self.assertIn("entryX=0.500;entryY=0.000", xml)
        self.assertNotIn('x="32" y="188"', xml)

    def test_drawio_graph_xml_can_hide_nonessential_edges(self) -> None:
        xml = drawio_graph_xml(
            {
                "nodes": [
                    {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                    {"id": "writer", "label": "Writer", "rank": 1, "lane": 0},
                    {"id": "audit", "label": "Audit", "rank": 2, "lane": 0},
                ],
                "edges": [
                    {"from": "input", "to": "writer", "label": "writes"},
                    {"from": "writer", "to": "audit", "label": "noisy feedback", "render": False},
                ],
            },
            diagram_key="pipeline",
        )

        self.assertIn("writes", xml)
        self.assertNotIn("noisy feedback", xml)

    def test_drawio_graph_xml_can_hide_edge_label_without_hiding_edge(self) -> None:
        xml = drawio_graph_xml(
            {
                "nodes": [
                    {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                    {"id": "writer", "label": "Writer", "rank": 1, "lane": 0},
                ],
                "edges": [{"from": "input", "to": "writer", "label": "noisy label", "show_label": False}],
            },
            diagram_key="pipeline",
        )

        self.assertIn('edge="1"', xml)
        self.assertIn('source="node-input"', xml)
        self.assertNotIn("noisy label", xml)

    def test_drawio_graph_svg_prefers_drawio_cli_export_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_drawio = bin_dir / "drawio"
            fake_drawio.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import pathlib
                    import sys

                    output = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
                    source = pathlib.Path(sys.argv[-1])
                    assert source.read_text(encoding="utf-8").startswith("<mxfile>")
                    fmt = sys.argv[sys.argv.index("--format") + 1]
                    if fmt == "xml":
                        output.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                    else:
                        output.write_text(
                            '<svg xmlns="http://www.w3.org/2000/svg"><text>exported by drawio</text></svg>',
                            encoding="utf-8",
                        )
                    """
                ),
                encoding="utf-8",
            )
            fake_drawio.chmod(0o755)
            path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

            with mock.patch.dict(os.environ, {"PATH": path}):
                svg = drawio_graph_svg(
                    {
                        "nodes": [
                            {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                            {"id": "writer", "label": "Writer", "rank": 1, "lane": 0},
                        ],
                        "edges": [{"from": "input", "to": "writer", "label": "writes"}],
                    },
                    diagram_key="pipeline",
                )

        self.assertIn("exported by drawio", svg)
        self.assertNotIn("drawio-graph-arrow", svg)

    def test_drawio_graph_artifacts_use_drawio_cli_layout_xml_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_drawio = bin_dir / "drawio"
            fake_drawio.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import pathlib
                    import sys

                    output = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
                    source = pathlib.Path(sys.argv[-1])
                    fmt = sys.argv[sys.argv.index("--format") + 1]
                    if fmt == "xml":
                        xml = source.read_text(encoding="utf-8").replace(
                            "<mxfile>",
                            '<mxfile host="fake-drawio">',
                            1,
                        )
                        output.write_text(xml, encoding="utf-8")
                    else:
                        assert 'host="fake-drawio"' in source.read_text(encoding="utf-8")
                        output.write_text(
                            '<svg xmlns="http://www.w3.org/2000/svg"><text>laid out source</text></svg>',
                            encoding="utf-8",
                        )
                    """
                ),
                encoding="utf-8",
            )
            fake_drawio.chmod(0o755)
            path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")

            with mock.patch.dict(os.environ, {"PATH": path}):
                source_xml, svg = drawio_graph_artifacts(
                    {
                        "nodes": [
                            {"id": "input", "label": "Input", "rank": 0, "lane": 0},
                            {"id": "writer", "label": "Writer", "rank": 1, "lane": 0},
                        ],
                        "edges": [{"from": "input", "to": "writer", "label": "writes"}],
                    },
                    diagram_key="pipeline",
                )

        self.assertIn('host="fake-drawio"', source_xml)
        self.assertIn("laid out source", svg)

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
