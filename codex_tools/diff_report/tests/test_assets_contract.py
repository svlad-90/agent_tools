from __future__ import annotations

import unittest

from codex_tools.diff_report.assets import (
    copy_selection_script,
    diagram_script,
    html_header,
    story_script,
    theme_script,
)


class AssetContractTests(unittest.TestCase):
    def test_public_assets_reexport_expected_builders(self) -> None:
        self.assertTrue(callable(html_header))
        self.assertTrue(callable(diagram_script))
        self.assertTrue(callable(story_script))
        self.assertTrue(callable(theme_script))
        self.assertTrue(callable(copy_selection_script))

    def test_header_exposes_layout_theme_and_settings_contracts(self) -> None:
        header = html_header("A <report>")

        expected_fragments = [
            "<title>A &lt;report&gt;</title>",
            "--text-scale: 1",
            "--scaled-code-font: calc(var(--screen-code-font) * var(--text-scale))",
            "--floating-control-size: 44px",
            "--floating-content-gutter:",
            "--comment-target-add-bg:",
            "--comment-target-del-bg:",
            "--comment-row-target-bg:",
            ".settings-dialog",
            ".settings-launcher",
            ".to-top-button",
            ".story-steps",
            ".asset-search-match",
            ".asset-search-current",
            ".asset-search-submatch",
            ".code-target-flash-overlay",
            "@media (max-width: 1100px)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, header)

    def test_theme_script_exposes_settings_and_text_scale_contracts(self) -> None:
        script = theme_script()

        expected_fragments = [
            'const themeKey = "codex-diff-report-theme"',
            'const textScaleKey = "codex-diff-report-text-scale"',
            "data-settings-modal",
            "data-settings-toggle",
            "data-settings-close",
            "data-theme-value",
            "data-text-scale-step",
            "data-text-scale-reset",
            "window.requestAnimationFrame(function ()",
            "root.style.setProperty",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_copy_script_exposes_plain_and_markdown_selection_actions(self) -> None:
        script = copy_selection_script()

        expected_fragments = [
            "data-copy-markdown-menu",
            "data-copy-plain-action",
            "data-copy-markdown-action",
            "copyPlainSelection",
            "copyMarkdown",
            "selectedTextWithin",
            "contextmenu",
            "navigator.clipboard.writeText",
            "```diff",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_story_script_exposes_target_and_navigation_contracts(self) -> None:
        script = story_script()

        expected_fragments = [
            'document.querySelectorAll("[data-story-index]")',
            "function setActive(index)",
            "animateWindowScrollToElement",
            "createCodeTargetFlashOverlay",
            "rowsWithIntermediateDeletes",
            "scheduleStoryOffsetUpdate",
            "step.dataset.storyTarget",
            "data-story-top",
            "navStyle.position === \"fixed\"",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_diagram_script_exposes_search_export_and_code_link_contracts(self) -> None:
        script = diagram_script()

        expected_fragments = [
            "function exportOpenedDiagram()",
            "function exportOpenedLog()",
            "inlineReportOverlayStyles(svg, clone)",
            "prepareExportedSvgForViewers(clone)",
            "fixExportedSvgViewportSize(svg)",
            "standaloneDiagramStyle()",
            "standaloneCssRules(rules, includeDarkRules)",
            "data-diagram-search",
            "scheduleSearch(resetIndex)",
            "setSvgSearchClass(node, \"asset-search-match\", true)",
            "addSvgSearchSubmatches(node, query)",
            "searchInput.select()",
            "activeCodeLinks",
            "function codeOverlayRoot()",
            "positionCodePopover(popover)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)


if __name__ == "__main__":
    unittest.main()
