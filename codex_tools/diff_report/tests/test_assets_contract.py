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
            "--story-nav-height: 76px;",
            "--comment-target-add-bg:",
            "--comment-target-del-bg:",
            "--comment-row-target-bg:",
            "--hunk-text:",
            "html { scrollbar-gutter: stable; }",
            ".settings-dialog",
            ".settings-launcher",
            "body.has-diagram-open .report-brand { z-index: 9; }",
            "body.has-diagram-open .settings-launcher, body.has-diagram-open .to-top-button",
            ".vocabulary-ref-wrap",
            ".vocabulary-ref",
            ".vocabulary-popover",
            ".vocabulary-ref-wrap.is-positioned .vocabulary-popover",
            "z-index: 1010;",
            ".vocabulary-ref-wrap:hover .vocabulary-popover",
            "body.has-pinned-story .story.has-vocabulary-popover, body.has-diagram-open .story.has-vocabulary-popover { overflow: visible; z-index: 1009; }",
            ".review-nav h2 { min-width: 0;",
            ".review-nav-head button { display: inline-flex; flex: 0 0 auto;",
            "white-space: nowrap;",
            ".review-nav-comments a.is-current-comment",
            ".review-nav-comments a.is-current-comment .review-nav-line",
            ".to-top-button",
            ".story-step-strip",
            ".story-page-button",
            ".story-page-button:disabled",
            ".story-steps",
            ".story-steps li { min-width: 0; }",
            "grid-auto-columns: var(--story-step-column-width, 260px)",
            "scroll-behavior: smooth",
            "grid-template-rows: minmax(56px, 1fr)",
            ".story-step.is-open",
            "transition: left .18s ease, right .18s ease, top .18s ease, width .18s ease, max-width .18s ease;",
            "body.has-pinned-story .story, body.has-diagram-open .story { position: fixed;",
            "top: 0; width: auto;",
            ".diagram-dialog { position: absolute; left: clamp(28px, 5vw, 92px);",
            "top: calc(min(var(--story-offset, 0px), 24vh) + 10px);",
            "bottom: calc(var(--story-nav-height) + clamp(8px, 2vh, 24px));",
            ".diagram-toolbar { position: relative; z-index: 2; display: grid; grid-template-columns: minmax(180px, 1fr) minmax(0, auto);",
            "box-shadow: 0 1px 0 color-mix(in srgb, var(--text) 9%, transparent), 0 10px 24px rgba(0, 0, 0, .22);",
            ".diagram-search-tools, .diagram-action-tools { display: inline-flex;",
            ".diagram-action-tools { flex: 0 0 auto; justify-content: flex-end; }",
            ".asset-story-comment { position: fixed;",
            "background: var(--comment-bg); color: var(--text);",
            "opacity: 1; pointer-events: auto;",
            ".asset-story-comment div { color: var(--text); font-size: clamp(17px, calc(var(--scaled-code-font) * 1.12), 21px);",
            ".diagram-story-nav { position: fixed;",
            "left: 0; right: 0; bottom: 0;",
            "grid-template-columns: minmax(0, 240px) 58px minmax(0, 240px);",
            "min-height: var(--story-nav-height);",
            "border-top: 1px solid var(--story-step-active-border);",
            "z-index: 1004;",
            "box-shadow: 0 -16px 36px",
            ".diagram-story-nav button",
            ".diagram-story-nav .story-slide-toggle",
            ".diagram-story-nav .story-slide-toggle::before",
            ".diagram-story-nav .story-slide-toggle::after",
            "content: attr(data-tooltip);",
            ".diagram-story-nav .story-slide-toggle:hover::after",
            ".diagram-story-nav .story-slide-toggle.is-open",
            ".diagram-story-nav .story-slide-toggle.is-open::before",
            "height: 50px;",
            "white-space: nowrap; text-overflow: ellipsis;",
            "background: var(--story-step-active-bg);",
            ".diagram-story-nav button:disabled",
            "--asset-log-scale",
            "color: var(--hunk-text);",
            ".diagram-zoom-stage { transform-origin: 0 0; width: max-content; min-width: 100%; }",
            ".diagram-scroll.is-preparing-story-view .diagram-zoom-stage { visibility: hidden; }",
            ".log-view-text { width: 100%; max-width: 100%; min-width: 0;",
            ".asset-story-comment.is-positioned { opacity: 1; visibility: visible; pointer-events: auto; }",
            "svg .asset-focus-object",
            "focus-object-pulse",
            "focus-label-pulse",
            ".diagram-code-popover { position: fixed;",
            "width: min(1120px, calc(100vw - 32px)); height: min(86vh, calc(100vh - 32px));",
            'polygon[fill="#FFFFFF"]',
            'path[fill="#FEFECE"]',
            ".summary-artifact-preview .diagram-preview { width: min(760px, 100%); }",
            ".asset-search-match",
            ".asset-search-current",
            ".asset-search-submatch",
            ".code-target-flash-overlay { position: absolute; z-index: 7;",
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
        self.assertNotIn("setScale(Math.max(0.6, Math.min(2.5, nextZoom)))", script)

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
            "function updateStoryPager(ensureActive, scrollBehavior)",
            "function initStoryPagerResizeObserver()",
            "function initVocabularyPopovers()",
            "function positionVocabularyPopover(wrap)",
            'document.querySelectorAll(".vocabulary-ref-wrap")',
            "function setStoryVocabularyPopover(wrap, open)",
            "storyPanel.classList.toggle(\"has-vocabulary-popover\", open);",
            'trigger.addEventListener("pointerdown", function (event)',
            "trigger.blur();",
            'wrap.classList.add("is-positioned")',
            "const leftBias = Math.min(72, Math.max(24, popoverWidth * 0.22));",
            'wrap.style.setProperty("--vocabulary-popover-left"',
            "new ResizeObserver(function ()",
            "storySteps.getBoundingClientRect().width",
            "function moveStoryPage(direction)",
            "const storyMoveButtons = Array.from(document.querySelectorAll(\"[data-diagram-story-step]\"));",
            "const storyToggleButtons = Array.from(document.querySelectorAll(\"[data-diagram-story-toggle]\"));",
            "function updateStoryMoveButtons()",
            "function updateStoryToggleButtons()",
            "function toggleCurrentStorySlide()",
            "const label = open ? \"Close slide\" : \"Open slide\";",
            "button.dataset.tooltip = label;",
            "function setOpenStep(index)",
            "step.classList.remove(\"is-open\")",
            "steps[index].classList.add(\"is-open\")",
            "steps[nextIndex].classList.contains(\"is-open\")",
            "closeOpenStoryArtifact();",
            "setOpenStep(null);",
            "codex-review-story-artifact",
            "const hasOwnScroll = nav.scrollHeight > nav.clientHeight + 2 || nav.scrollWidth > nav.clientWidth + 2;",
            "let navScrollRaf = 0;",
            "let navScrollFollowupTimer = 0;",
            "function scheduleNavScrollToItem(item)",
            "window.clearTimeout(navScrollFollowupTimer);",
            "navScrollFollowupTimer = window.setTimeout(function ()",
            "Math.max(topPadding, (navRect.height - itemRect.height) / 2)",
            "function scrollNavToItem(item)",
            "item.classList.add(\"is-open\");",
            "itemToggle.setAttribute(\"aria-expanded\", \"true\");",
            "function initReviewNavActiveComment()",
            'document.querySelectorAll(".review-comment[id][data-comment-file]")',
            "function revealCommentLink(link)",
            "function scrollNavToCommentLink(link)",
            "data-review-comment-link",
            "is-current-comment",
            "flashTargets(comment, scrollContextElement(comment));",
            "function resetHiddenActiveComment()",
            "activeCommentId = \"\";",
            "function currentVisibleComment()",
            "const center = safeTop + Math.max(0, lower - safeTop) / 2;",
            "Math.min(Math.abs(rect.top - center), Math.abs(rect.bottom - center))",
            "storySteps.clientWidth",
            "storySteps.style.setProperty(\"--story-step-column-width\"",
            "storySteps.scrollLeft = targetLeft",
            "function syncStoryScrollLeft(targetLeft)",
            "storySteps.style.scrollBehavior = \"auto\"",
            "storySteps.scrollTo({ left: targetLeft, behavior: \"smooth\" })",
            "let storyPageStart = 0",
            "storyPageStart = Math.min(Math.floor(activeIndex / columns) * columns, maxStart)",
            "const currentStart = Math.max(0, Math.min(storyPageMaxStart, Math.round(storySteps.scrollLeft / storyPageUnitWidth)))",
            "currentStart - storyPageColumns",
            "currentStart + storyPageColumns",
            "const row = 1",
            "items[index].style.gridColumn",
            "items[index].style.gridRow",
            "function openStoryArtifact(step)",
            "function closeOpenStoryArtifact()",
            "modal.querySelector(\"[data-diagram-close]\")",
            "step.dataset.storyDiagram",
            "step.dataset.storyLog",
            "animateWindowScrollToElement",
            "if (codeTargets.length) {",
            "createCodeTargetFlashOverlay",
            "function groupedClientRects(targets)",
            "rect.top - current.bottom > 24",
            "rowsWithIntermediateDeletes",
            "scheduleStoryOffsetUpdate",
            "codex-review-story-layout",
            "step.dataset.storyTarget",
            "data-story-top",
            "storySentinel",
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
            "function parseZoom(value)",
            "function zoomAnchorState(options)",
            "function zoomAnchor(options)",
            "function preserveZoomAnchor(anchorState)",
            "let scaleAnimationTarget = 1;",
            "scaleAnimationTarget = targetScale;",
            "scaleAnimationAnchorState = null;",
            "if (scaleAnimation) {",
            "const delta = scaleAnimationTarget - scale;",
            "contentX: (content.scrollLeft + anchor.x) / (scale || 1)",
            "content.scrollLeft = clamp((anchorState.contentX * scale) - anchorState.x, 0, maxLeft);",
            "function applyStoryObjectZoom(target, nextZoom)",
            "function animateScaleTo(targetScale, anchorState)",
            "function scrollContainerToElement(container, element, options)",
            "tool.hidden = mode !== \"diagram\" && mode !== \"log\"",
            "setScale(scale + 0.1, { animate: true })",
            "setScale(scale - 0.1, { animate: true })",
            "function handleArtifactWheel(event)",
            "event.shiftKey && !event.ctrlKey",
            "content.scrollLeft += event.deltaX || event.deltaY;",
            "modal.addEventListener(\"wheel\", function (event)",
            "content.scrollLeft += event.deltaX;",
            "content.scrollTop += event.deltaY;",
            "mode !== \"diagram\" && mode !== \"log\"",
            "function scheduleFocusedArtifactView(target, storyZoom, storyComment)",
            "const shouldCenterTarget = Boolean(target && (storyZoom || storyComment));",
            "content.classList.remove(\"is-preparing-story-view\");",
            "function positionStoryComment(comment)",
            "const availableWidth = Math.max(180, contentRect.width - margin * 2);",
            "const sideMargin = mode === \"log\" ? margin + 30 : margin;",
            "comment.classList.add(\"is-positioned\");",
            "mode === \"log\"",
            "content.classList.toggle(\"is-preparing-story-view\", Boolean(nextStoryContext || storyZoom));",
            "function createAssetStoryComment(nextStoryContext)",
            "detail: { status: \"open\", index: nextStoryContext.index }",
            "detail: { status: \"closed\" }",
            "function closestSvgObjectShape(labelNode)",
            "codex-review-story-move",
            "asset-focus-object",
            "document.body.classList.add(\"has-diagram-open\")",
            "document.body.classList.remove(\"has-diagram-open\")",
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
