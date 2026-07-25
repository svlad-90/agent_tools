from __future__ import annotations

import unittest

from codex_tools.diff_report.assets import (
    copy_selection_script,
    diagram_script,
    html_header,
    story_script,
    theme_script,
)
from codex_tools.diff_report.assets_diagram_code_popover import diagram_code_popover_helpers
from codex_tools.diff_report.assets_diagram_export import diagram_export_helpers
from codex_tools.diff_report.assets_diagram_notes import diagram_note_helpers
from codex_tools.diff_report.assets_styles import stylesheet


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
            "<style>",
            "</style>",
            "data-settings-modal",
            "data-theme-value=\"light\"",
            "data-text-scale-reset",
            "data-copy-markdown-menu",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, header)

    def test_stylesheet_exposes_layout_theme_and_search_contracts(self) -> None:
        styles = stylesheet()

        expected_fragments = [
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
            ".story-step-strip",
            ".story-page-button",
            ".story-steps",
            "grid-auto-columns: var(--story-step-column-width, 260px)",
            "scroll-behavior: smooth",
            "grid-template-rows: repeat(2, minmax(52px, 1fr))",
            ".diagram-dialog { position: absolute; inset: clamp(8px, 2vh, 24px) clamp(8px, 2vw, 24px);",
            ".diagram-toolbar { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(0, auto);",
            ".diagram-search-tools, .diagram-action-tools { display: inline-flex;",
            ".diagram-action-tools { flex: 0 0 auto; justify-content: flex-end; }",
            ".diagram-code-popover { position: fixed;",
            "width: min(1120px, calc(100vw - 32px)); height: min(86vh, calc(100vh - 32px));",
            'polygon[fill="#FFFFFF"]',
            'path[fill="#FEFECE"]',
            ".summary-artifact-preview .diagram-preview { width: min(760px, 100%); }",
            ".asset-search-match",
            ".asset-search-current",
            ".asset-search-submatch",
            ".code-target-flash-overlay",
            "@media (max-width: 1100px)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, styles)

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
            "const minTextScale = 0.5",
            "const maxTextScale = 2",
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
            "function updateStoryPager(ensureActive)",
            "function moveStoryPage(direction)",
            "storySteps.clientWidth",
            "storySteps.style.setProperty(\"--story-step-column-width\"",
            "storySteps.scrollTo({ left: targetLeft, behavior: \"smooth\" })",
            "Math.floor(Math.floor(activeIndex / 2) / columns)",
            "indexInPage % columns",
            "items[index].style.gridColumn",
            "items[index].style.gridRow",
            "function openStoryArtifact(step)",
            "step.dataset.storyDiagram",
            "step.dataset.storyLog",
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
        self.assertNotIn("lastOpenedStoryIndex", script)

    def test_diagram_script_exposes_search_export_and_code_link_contracts(self) -> None:
        script = diagram_script()

        expected_fragments = [
            "data-diagram-search",
            "scheduleSearch(resetIndex)",
            "setSvgSearchClass(node, \"asset-search-match\", true)",
            "addSvgSearchSubmatches(node, query)",
            "searchInput.select()",
            "activeCodeLinks",
            "const widthScale = availableWidth > 0 ? availableWidth / size.width : 1",
            "const heightScale = availableHeight > 0 ? availableHeight / size.height : 1",
            "initialScale = Math.min(3, widthScale)",
            "function codeOverlayRoot()",
            "positionCodePopover(popover)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_diagram_code_popover_helpers_expose_diff_context_contracts(self) -> None:
        script = diagram_code_popover_helpers()

        expected_fragments = [
            "function codeOverlayRoot()",
            "function closeCodePopover()",
            "function renderCodePopover(targetKey, links)",
            "positionCodePopover(popover)",
            "centerCodeTarget(popover)",
            "function createCodeLinkItem(link)",
            "function renderDiffFileContext(parent, link)",
            "Target file is not present in this rendered diff.",
            "document.querySelectorAll(\"tr[data-file]\")",
            "function targetRangeForLink(link)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_diagram_note_helpers_expose_note_rendering_contracts(self) -> None:
        script = diagram_note_helpers()

        expected_fragments = [
            "function isDiagramNoteTarget(node, notes)",
            "function addDiagramNotes(notes, textNodes)",
            "diagram-note-layer",
            "function diagramNoteMarkerPosition(viewBox, anchor)",
            "function diagramNotePosition(note, viewBox, marker, width, height, index)",
            "function createDiagramNote(note, x, y, width, height, markerPoint, relatedNodes)",
            "diagram-note-hover",
            "function wrapSvgText(textNode, text, maxWidth)",
            "function appendTspan(textNode, text, lineNo)",
            "function safeBBox(node)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_diagram_export_helpers_expose_standalone_export_contracts(self) -> None:
        script = diagram_export_helpers()

        expected_fragments = [
            "function exportOpenedDiagram()",
            "function exportOpenedLog()",
            "inlineReportOverlayStyles(svg, clone)",
            "prepareExportedSvgForViewers(clone)",
            "fixExportedSvgViewportSize(svg)",
            "standaloneDiagramStyle()",
            "standaloneCssRules(rules, includeDarkRules)",
            "standaloneSelector(rule.selectorText, includeDarkRules)",
            "resolveCssVariables(rule.style.cssText)",
            "insertSvgBackground(clone)",
            "removeCodeLinkState(clone)",
            "downloadBlob(safeFileName(activeExportName, \"svg\")",
            "downloadBlob(safeFileName(activeExportName, \"html\")",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)


if __name__ == "__main__":
    unittest.main()
