from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from codex_tools.diff_report.comments_compose import compose_comments_payload
from codex_tools.diff_report.core import generate_report


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
TASK_REPORT_ROOT = WORKSPACE_ROOT / "codex-tools-diff-report-enhancements" / "report"
TASK_DEV_ROOT = WORKSPACE_ROOT / "codex-tools-diff-report-enhancements" / "dev"
FIXTURE_DIFF_DIR = TASK_REPORT_ROOT / "diff"
FIXTURE_BASENAME = "pr139-to-local-working-tree"
PR139_COMPOSE_FINDINGS = TASK_DEV_ROOT / "pr139-compose-smoke-findings.json"


class Pr139ReportRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        missing = [
            path
            for path in (
                FIXTURE_DIFF_DIR / f"{FIXTURE_BASENAME}.patch",
                FIXTURE_DIFF_DIR / f"{FIXTURE_BASENAME}.json",
                TASK_REPORT_ROOT / "puml" / "fdt-review-fix-api-flow.svg",
                TASK_REPORT_ROOT / "runtime" / "pr139-fdt-final-runtime-xen419.log",
                PR139_COMPOSE_FINDINGS,
            )
            if not path.exists()
        ]
        if missing:
            self.fail("missing PR 139 report fixture files: " + ", ".join(str(path) for path in missing))

    def test_pr139_report_renders_current_supported_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_root = self._copy_fixture_report(Path(temp_dir))
            output_path = report_root / "diff" / "regenerated.html"

            generate_report(
                output_path=output_path,
                title="PR 139 to local working tree",
                diff_file=report_root / "diff" / f"{FIXTURE_BASENAME}.patch",
                comments_file=report_root / "diff" / f"{FIXTURE_BASENAME}.json",
            )

            html = output_path.read_text(encoding="utf-8")

        expected_fragments = [
            "<h1>PR 139 to local working tree</h1>",
            "Commit Message",
            "summary-artifact-preview",
            'data-diagram-id="fdt-review-fix-api-flow"',
            'data-log-id="fdt-api-runtime"',
            'id="story"',
            'id="diagram-modal"',
            'id="diagram-export"',
            'data-asset-export',
            'id="diagram-template-fdt-review-fix-api-flow"',
            'data-code-links=',
            'id="log-template-fdt-api-runtime"',
            "FDT PROBE PASS",
            "store raw FDT address",
            "get_xen_fdt_ptr(&amp;size)",
            'id="comment-arch-arm64-core-xen-fdt.c-29"',
            'data-comment-file="arch/arm64/core/xen/fdt.c"',
            'id="line-arch-arm64-core-xen-fdt.c-29"',
            "Public runtime accessor implementation",
            ".diagram-code-overlay { position: fixed; inset: 0; z-index: 1002;",
            "function codeOverlayRoot()",
            "codeOverlayRoot().appendChild(overlay)",
            "positionCodePopover(popover)",
            "function exportOpenedDiagram()",
            "function exportOpenedLog()",
            "inlineReportOverlayStyles(svg, clone)",
            "prepareExportedSvgForViewers(clone)",
            "fixExportedSvgViewportSize(svg)",
            'svg.style.maxWidth = "none"',
            'svg.removeAttribute("viewBox")',
            'if (next === "svg")',
            'node.removeAttribute("textLength")',
            "standaloneDiagramStyle()",
            "standaloneDiagramVariablesStyle()",
            "standaloneDiagramVariableMap(rootStyle)",
            "resolveCssVariables(rule.style.cssText)",
            "document.styleSheets",
            "standaloneCssRules(rules, includeDarkRules)",
            "standaloneSelector(rule.selectorText, includeDarkRules)",
            "canInlineOverlayProperty(sourceNode, property)",
            "insertSvgBackground(clone)",
            'class", "diagram-export-background"',
            "removeCodeLinkState(clone)",
            "Save as SVG",
            "Save as HTML",
            "let storyOffsetRaf = 0",
            "Math.ceil(story.getBoundingClientRect().top)",
            "const currentHeight = Math.ceil(story.getBoundingClientRect().height)",
            "scheduleStoryOffsetUpdate()",
            "--page-gutter: 8px",
            "--comment-target-bg: #e9f5ec",
            "--text-scale: 1",
            "--scaled-code-font: calc(var(--screen-code-font) * var(--text-scale))",
            "--brand-mark-size: 172px",
            "--floating-control-size: 44px",
            "--floating-control-gap: 18px",
            "--floating-content-gutter: max(24px, calc((100vw - var(--nav-width) - var(--content-width)) / 2))",
            "--review-nav-top: calc(var(--page-gutter) + var(--brand-height) + 12px)",
            "main { width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3))",
            "header, section, .file { width: min(100%, var(--content-width));",
            ".settings-dialog { position: absolute; left: 50%; top: 50%;",
            "font-size: var(--screen-body-font);",
            "svg .asset-search-match { fill: #cf222e !important; stroke: none !important; }",
            "svg .asset-search-submatch { fill: rgba(255,42,61,.26); stroke: #ff2a3d;",
            "svg .asset-search-submatch-text { fill: #ff2a3d !important;",
            "svg .asset-search-current { fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important;",
            "svg text.asset-search-current, svg tspan.asset-search-current",
            "@media (min-width: 1800px)",
            "@media (max-width: 1500px)",
            "@media (max-width: 1280px)",
            ".story-steps { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }",
            ".settings-launcher { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(24px + var(--floating-control-size) + 10px);",
            ".to-top-button { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: 24px;",
            "body.has-left-top .to-top-button, body.has-left-top .report-settings-launcher",
            "class=\"settings-launcher report-settings-launcher\"",
            ".settings-toggle span, .settings-toggle::before, .settings-toggle::after",
            "header, section, .file, .asset-inventory { width: 100%; margin-left: 0; margin-right: 0; }",
            'setSvgSearchClass(node, "asset-search-match", true)',
            "addSvgSearchSubmatches(node, query)",
            "svgSearchSubmatchText(candidate, index, query.length, query)",
            "parent.insertBefore(underlay, textNode)",
            "parent.insertBefore(overlay, textNode.nextSibling)",
            "function svgTextRangeStart(node, start)",
            "function svgTextRangeBox(node, start, length)",
            "searchInput.select()",
            'setSvgSearchClass(current, "asset-search-current", true)',
            'node.style.setProperty("fill", isCurrent ? "#ff2a3d" : "#cf222e", "important")',
            'const textScaleKey = "codex-diff-report-text-scale"',
            'data-text-scale-step="0.1"',
            "restoreSvgSearchPaint(node)",
            'item.scrollIntoView({ block: "nearest", inline: "nearest" })',
            'navStyle.position === "fixed"',
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)

        self.assertEqual(8, html.count("data-story-index="))
        self.assertGreaterEqual(html.count('class="review-comment"'), 10)
        self.assertNotIn("../puml/fdt-review-fix-api-flow.svg", html)
        self.assertNotIn("../runtime/pr139-fdt-final-runtime-xen419.log", html)
        self.assertNotIn("General view", html)
        self.assertNotIn("data-diagram-general", html)
        self.assertNotIn('data-story-nav="prev"', html)
        self.assertNotIn('data-story-nav="next"', html)
        self.assertNotIn("story-controls", html)
        self.assertNotIn("story-settings-launcher", html)
        self.assertNotIn('id="story-counter"', html)
        self.assertNotIn("story-top-inline", html)

    def test_report_without_story_keeps_top_button_and_shared_story_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output_path = root / "report.html"
            diff_path.write_text(
                "\n".join(
                    [
                        "diff --git a/example.txt b/example.txt",
                        "index 83db48f..f735c2d 100644",
                        "--- a/example.txt",
                        "+++ b/example.txt",
                        "@@ -1 +1 @@",
                        "-old",
                        "+new",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            comments_path.write_text('{"summary": "No story report"}\n', encoding="utf-8")

            generate_report(
                output_path=output_path,
                title="No story report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn('class="to-top-button"', html)
        self.assertIn("data-story-top", html)
        self.assertIn('const steps = Array.from(document.querySelectorAll("[data-story-index]"));', html)
        self.assertIn("if (!steps.length)", html)
        self.assertNotIn('id="story"', html)

    def test_refresh_targets_preserves_pr139_inline_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_root = self._copy_fixture_report(Path(temp_dir))
            output_path = report_root / "diff" / "refreshed.html"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                generate_report(
                    output_path=output_path,
                    title="PR 139 to local working tree",
                    diff_file=report_root / "diff" / f"{FIXTURE_BASENAME}.patch",
                    comments_file=report_root / "diff" / f"{FIXTURE_BASENAME}.json",
                    refresh_targets=True,
                )

            refreshed_path = output_path.with_suffix(".json")
            refreshed = json.loads(refreshed_path.read_text(encoding="utf-8"))
            inline = refreshed["inline"]

        self.assertIn("attention=0", stdout.getvalue())
        self.assertEqual(10, len(inline))
        for item in inline:
            with self.subTest(file=item["file"], line=item["line"]):
                target = item.get("target")
                self.assertIsInstance(target, dict)
                self.assertEqual(item["file"], target["file"])
                self.assertTrue(target["found"])
                self.assertEqual("found", target["status"])
                self.assertIn(target["kind"], {"add", "context"})
                self.assertGreaterEqual(target["line"], item["range"]["start"])
                self.assertLessEqual(target["line"], item["range"]["end"])

    def test_pr139_findings_compose_into_renderable_comments(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report_root = self._copy_fixture_report(Path(temp_dir))
            diff_path = report_root / "diff" / f"{FIXTURE_BASENAME}.patch"
            comments_path = report_root / "diff" / "compose-smoke.json"
            output_path = report_root / "diff" / "compose-smoke.html"
            diff_text = diff_path.read_text(encoding="utf-8")
            findings = json.loads(PR139_COMPOSE_FINDINGS.read_text(encoding="utf-8"))
            comments = compose_comments_payload(diff_text, findings)
            comments_path.write_text(
                json.dumps(comments, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            generate_report(
                output_path=output_path,
                title="PR139 Compose Smoke",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertEqual(2, len(comments["inline"]))
        self.assertEqual(["found", "found"], [item["target"]["status"] for item in comments["inline"]])
        self.assertIn("Review: preserve raw FDT address handoff", html)
        self.assertIn("Review: publish copied FDT size", html)
        self.assertIn('id="comment-arch-arm64-core-reset.S-127"', html)
        self.assertIn('id="comment-arch-arm64-core-xen-fdt.c-56"', html)

    def _copy_fixture_report(self, temp_root: Path) -> Path:
        report_root = temp_root / "report"
        shutil.copytree(TASK_REPORT_ROOT, report_root)
        return report_root


if __name__ == "__main__":
    unittest.main()
