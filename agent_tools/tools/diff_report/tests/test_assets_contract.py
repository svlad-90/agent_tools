from __future__ import annotations

import unittest

from agent_tools.tools.diff_report.assets import (
    copy_selection_script,
    diagram_script,
    html_header,
    story_script,
    theme_script,
)
from agent_tools.tools.diff_report.assets_diagram_code_popover import diagram_code_popover_helpers
from agent_tools.tools.diff_report.assets_diagram_export import diagram_export_helpers
from agent_tools.tools.diff_report.assets_diagram_notes import diagram_note_helpers
from agent_tools.tools.diff_report.assets_plantuml_svg import (
    PINNED_GRAPHVIZ_DOT_VERSION,
    PINNED_PLANTUML_HEADLESS_JAVA_OPTION,
    PINNED_PLANTUML_RELEASE_DATE,
    PINNED_PLANTUML_VERSION,
    plantuml_preview_svg,
    plantuml_svg_styles,
)
from agent_tools.tools.diff_report.assets_styles import stylesheet


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
            "report-brand-logo",
            "<span class=\"report-brand-title\">Report</span>",
            "data-settings-modal",
            "data-theme-value=\"light\"",
            "data-text-scale-reset",
            "data-copy-markdown-menu",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, header)
        self.assertNotIn(">AI</span>", header)

    def test_stylesheet_exposes_layout_theme_and_search_contracts(self) -> None:
        styles = stylesheet()
        plantuml_styles = plantuml_svg_styles()

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
            ".review-nav h2 { min-width: 0;",
            "overscroll-behavior: contain;",
            "white-space: nowrap;",
            ".general-report .report-table-section { overflow: visible; }",
            ".report-table { width: 100%; min-width: 720px; border-collapse: separate; border-spacing: 0; table-layout: auto; }",
            ".report-table thead { position: sticky; top: 0; z-index: 5; }",
            ".report-table th { position: sticky; top: 0; z-index: 5;",
            '.relationship-canvas[data-graph-interactive="false"] { cursor: default; }',
            "background-clip: padding-box;",
            ".report-toc a.is-current",
            "border-left-color: var(--comment-border);",
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
            ".review-nav-file:not(.is-current) > .review-nav-comments",
            ".review-nav-row { position: relative; display: grid; grid-template-columns: minmax(0, 1fr);",
            ".review-nav-row:hover { background: color-mix(in srgb, var(--button-hover-bg) 44%, transparent);",
            "border-left: 1px solid color-mix(in srgb, var(--comment-border) 38%, transparent);",
            ".review-nav-children .review-nav-children { border-left-color: color-mix(in srgb, var(--comment-border) 38%, transparent);",
            ".review-nav-dir > .review-nav-row { position: relative; margin: 5px 0 2px 0; padding: 2px 4px 2px 8px;",
            "box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 38%, transparent)",
            "text-transform: none;",
            ".review-nav-dir > .review-nav-row::before { content: \"\"; position: absolute; left: -12px; top: 50%; width: 12px;",
            ".review-nav-tree > .review-nav-dir > .review-nav-row::before { display: none; }",
            ".review-nav-dir > .review-nav-row .review-nav-label::after { content: \"/\";",
            ".review-nav-tree > .review-nav-dir > .review-nav-row { margin-top: 10px;",
            ".review-nav-dir .review-nav-dir > .review-nav-row { color: color-mix(in srgb, var(--text) 58%, var(--muted));",
            ".review-nav-dir.is-current-path > .review-nav-row { background: color-mix(in srgb, var(--comment-bg) 16%, var(--panel));",
            ".review-nav-file > .review-nav-row { margin: 2px 0; padding: 4px 7px 4px 9px;",
            "background: transparent; cursor: pointer;",
            "box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 28%, transparent)",
            ".review-nav-file > .review-nav-row::before { content: \"\"; position: absolute; left: -12px; top: 50%; width: 12px;",
            ".review-nav-file-with-comments > .review-nav-row { box-shadow: inset 2px 0 0 color-mix(in srgb, var(--comment-border) 28%, transparent)",
            ".review-nav-file-with-comments > .review-nav-row:hover { background: color-mix(in srgb, var(--button-hover-bg) 68%, transparent);",
            ".review-nav-file.is-current > .review-nav-row { margin: 3px 0 4px; padding: 6px 7px 6px 10px;",
            "background: color-mix(in srgb, var(--comment-bg) 42%, var(--panel));",
            "box-shadow: inset 4px 0 0 var(--comment-border), 0 0 0 1px color-mix(in srgb, var(--comment-border) 24%, transparent);",
            ".review-nav-file > .review-nav-row .review-nav-label { font-weight: 400; }",
            ".review-nav-file.is-current > .review-nav-row a { color: var(--text); text-decoration: none; font-weight: 400; }",
            ".review-nav a { color: var(--text); text-decoration: none; }",
            ".review-nav a:hover { color: var(--text); text-decoration: none; }",
            ".review-nav-comments a { display: grid; grid-template-columns: 3.2em minmax(0, 1fr);",
            "gap: 6px; align-items: center;",
            ".review-nav-line { display: inline-grid; place-items: center;",
            "background: transparent; color: color-mix(in srgb, var(--text) 82%, var(--muted));",
            "color: color-mix(in srgb, var(--text) 82%, var(--muted));",
            ".review-nav-comments a.is-current-comment",
            ".vocabulary-ref-wrap",
            ".vocabulary-ref",
            ".vocabulary-popover { position: absolute;",
            "user-select: text;",
            ".vocabulary-ref-wrap.is-positioned .vocabulary-popover",
            ".vocabulary-ref-wrap.is-open .vocabulary-ref",
            ".vocabulary-ref-wrap.is-open .vocabulary-popover",
            "body.has-pinned-story .story.has-vocabulary-popover, body.has-diagram-open .story.has-vocabulary-popover { overflow: visible; z-index: 1009; }",
            "transition: left .18s ease, right .18s ease, top .18s ease, width .18s ease, max-width .18s ease;",
            "body.has-pinned-story .story, body.has-diagram-open .story { position: fixed;",
            "top: 0; width: auto;",
            ".diagram-dialog { position: absolute; left: clamp(28px, 5vw, 92px);",
            "top: calc(min(var(--story-offset, 0px), 24vh) + 10px);",
            "bottom: calc(var(--story-nav-height) + clamp(8px, 2vh, 24px));",
            ".diagram-toolbar { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(0, auto);",
            ".diagram-search-tools, .diagram-action-tools { display: inline-flex;",
            ".diagram-action-tools { flex: 0 0 auto; justify-content: flex-end; }",
            "--diagram-svg-bg:",
            "--diagram-svg-arrow:",
            "PlantUML SVG contract: PlantUML 1.2020.02",
            ".diagram-preview-canvas svg,\n    .diagram-zoom-stage svg { background: var(--diagram-svg-bg) !important; }",
            ".diagram-preview-canvas svg text:not(.diagram-note-text):not(.diagram-note-marker-text):not(.diagram-code-link-badge-text):not(.asset-focus-match):not(.asset-focus-related-hover)",
            ".diagram-preview-canvas svg line:not(.asset-focus-connector):not(.diagram-code-link-connector):not(.diagram-note-link)",
            ".diagram-preview-canvas svg path:not(.asset-focus-object):not(.asset-focus-connector):not(.diagram-note-box):not(.diagram-note-link):not(.diagram-code-link-connector)",
            ".diagram-preview-canvas svg polyline:not(.asset-focus-connector):not(.diagram-code-link-connector)",
            ".diagram-preview-canvas svg polygon:not(.asset-focus-connector):not(.asset-focus-object):not(.diagram-code-link-connector)",
            "fill: var(--diagram-svg-arrow) !important; stroke: var(--diagram-svg-arrow) !important; stroke-width: 1.4px !important;",
            "svg .asset-focus-connector { stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; filter: none; }",
            "svg polygon.asset-focus-connector { fill: var(--diagram-focus) !important; opacity: .95; filter: none; animation: none; }",
            "svg line.asset-focus-connector, svg path.asset-focus-connector, svg polyline.asset-focus-connector { stroke-dasharray: 8 8; stroke-linecap: round; animation: focus-dash-flow 2.4s linear infinite; }",
            "svg .asset-focus-object { fill: var(--diagram-focus) !important; fill-opacity: .08 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 8 8; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 4px var(--diagram-focus-glow)); animation: focus-dash-flow 2.4s linear infinite; pointer-events: none; }",
            "svg path.asset-focus-object, svg polyline.asset-focus-object, svg line.asset-focus-object { fill: none !important; fill-opacity: 0 !important; pointer-events: none; }",
            "svg .asset-focus-match { fill: var(--diagram-focus) !important; stroke: none !important; filter: none; animation: none; }",
            "svg .asset-focus-related-hover { stroke: var(--diagram-focus) !important; fill: var(--diagram-focus) !important; opacity: 1 !important; filter: none; }",
            "svg text.asset-focus-contained-text",
            "svg .diagram-note-box.asset-focus-object { fill: var(--diagram-note-bg) !important; fill-opacity: 1 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 8 8; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: none; animation: focus-dash-flow 2.4s linear infinite; }",
            "svg .diagram-note-link { fill: none; stroke: var(--diagram-focus); stroke-width: 1.4px; opacity: 0; filter: none; animation: none; }",
            "svg .diagram-note-hover .diagram-note-link, svg .diagram-note-hotspot:hover .diagram-note-link { stroke: var(--diagram-focus); stroke-width: 1.4px; opacity: 0; filter: none; animation: none; }",
            "svg .diagram-note-hover .diagram-note-box.asset-focus-object",
            ".asset-story-comment { position: fixed;",
            "pointer-events: none; user-select: text;",
            ".asset-story-comment.is-positioned",
            ".asset-story-comment.is-collapsed",
            ".asset-story-comment.is-collapsed { width: 46px !important; height: 46px;",
            ".asset-story-comment-toggle",
            "width: 34px; height: 34px;",
            "user-select: none;",
            ".asset-story-comment-content",
            "background: var(--comment-bg); color: var(--text);",
            "opacity: 0; visibility: hidden; pointer-events: none;",
            "opacity: 1; visibility: visible; pointer-events: auto;",
            ".asset-story-comment-body { color: var(--text); font-size: clamp(17px, calc(var(--scaled-code-font) * 1.12), 21px);",
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
            ".diagram-zoom-stage svg text, .diagram-zoom-stage svg tspan { cursor: text; user-select: text; }",
            ".diagram-scroll.is-preparing-story-view .diagram-zoom-stage",
            "transition: font-size .16s ease;",
            "svg .asset-focus-object",
            ".diagram-code-popover { position: fixed;",
            "width: min(1120px, calc(100vw - 32px)); height: min(86vh, calc(100vh - 32px));",
            'polygon[fill="#FFFFFF"]',
            'path[fill="#FFFFFF"]',
            'path[fill="#FEFECE"]',
            'polygon[fill="#2D2D30"]',
            'path[fill="#3B3216"]',
            'ellipse[fill="#FFFFFF"]',
            'ellipse[fill="#D4D4D4"]',
            'polygon[fill="#D4D4D4"]',
            'polygon[fill="#FBFB77"]',
            ".summary-artifact-preview .diagram-preview { width: min(760px, 100%); }",
            "body:has(.general-report) { --brand-height: 110px;",
            ".asset-search-match",
            ".asset-search-current",
            ".asset-search-submatch",
            ".code-target-flash-overlay",
            "@media (max-width: 1100px)",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, styles)
        self.assertNotIn(".code-target-flash-shield", styles)
        self.assertIn(PINNED_PLANTUML_VERSION, plantuml_styles)
        self.assertEqual("1.2020.02", PINNED_PLANTUML_VERSION)
        self.assertEqual("Sun Mar 01 12:22:07 EET 2020", PINNED_PLANTUML_RELEASE_DATE)
        self.assertEqual("-Djava.awt.headless=true", PINNED_PLANTUML_HEADLESS_JAVA_OPTION)
        self.assertEqual("2.43.0", PINNED_GRAPHVIZ_DOT_VERSION)
        self.assertNotIn("asset-focus-connector { stroke: var(--diagram-focus) !important; stroke-width: 3px !important; opacity: .95; filter: drop-shadow", styles)
        self.assertNotIn("asset-focus-object { fill: var(--diagram-svg-box-bg)", styles)
        self.assertNotIn("asset-focus-object { fill: var(--diagram-focus) !important; fill-opacity: .08 !important; stroke: var(--diagram-focus) !important; stroke-width: 4px !important; stroke-dasharray: 10 7; stroke-linecap: round; stroke-linejoin: round; vector-effect: non-scaling-stroke; filter: drop-shadow(0 0 4px rgba(255", styles)
        self.assertNotIn("asset-focus-match { fill: var(--diagram-focus) !important; stroke: none !important; filter: drop-shadow", styles)
        self.assertNotIn("asset-focus-related-hover { stroke: var(--diagram-focus) !important; fill: var(--diagram-focus) !important; opacity: 1 !important; filter: drop-shadow", styles)
        self.assertNotIn("diagram-note-link { fill: none; stroke: var(--diagram-note-link); stroke-width: 1.8px; opacity: .95; filter: drop-shadow", styles)
        self.assertNotIn("diagram-note-box.asset-focus-object { fill: var(--diagram-note-bg) !important; fill-opacity: 1 !important; stroke: var(--diagram-note-link)", styles)
        self.assertNotIn("focus-object-pulse", styles)
        self.assertNotIn("focus-label-pulse", styles)
        self.assertNotIn("focus-arrow-pulse", styles)

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

    def test_story_script_keeps_manual_comment_selection_stable_during_jump(self) -> None:
        script = story_script()

        select_file = script.index("selectFileForCommentLink(link);")
        already_active_return = script.index("if (wasActive)")
        self.assertLess(select_file, already_active_return)
        self.assertIn("suppressCommentUpdatesForFileJump || suppressCommentUpdatesForManualJump", script)
        self.assertIn("if (suppressFileUpdatesForFileJump || suppressFileUpdatesForCommentJump)", script)
        self.assertIn('if (event.target.closest("[data-review-comment-link]"))', script)
        self.assertIn('fileNode.querySelector(\':scope > .review-nav-row a[href^="#"]\')', script)
        self.assertNotIn('fileNode.querySelector(":scope > .review-nav-row a[href^="#"]")', script)

    def test_story_script_exposes_target_and_navigation_contracts(self) -> None:
        script = story_script()

        expected_fragments = [
	            'document.querySelectorAll("[data-story-index]")',
	            "function requestExtraPaint(node)",
            "function initVocabularyPopovers()",
            "function openVocabularyPopover(wrap)",
            "function toggleVocabularyPopover(wrap)",
            'document.addEventListener("click", function (event)',
            'document.addEventListener("keydown", function (event)',
            'event.target.closest(".vocabulary-ref")',
            'trigger.closest(".vocabulary-ref-wrap")',
            "function setStoryVocabularyPopover(wrap, open)",
            "storyPanel.classList.toggle(\"has-vocabulary-popover\", open);",
            "function closeActiveVocabularyPopover(exceptWrap)",
            "function isVocabularyPointerInside(wrap, event)",
            "document.addEventListener(\"pointerdown\", function (event)",
	            "wrap.classList.add(\"is-open\");",
	            'wrap.style.setProperty("--vocabulary-popover-left"',
	            "requestExtraPaint(popover)",
	            "activeWrap.classList.contains(\"is-open\")",
            "function setActive(index)",
            "detailsBody.innerHTML = step.dataset.storyBodyHtml || \"\";",
            "function initReviewNavActiveComment()",
            'document.querySelectorAll(".review-comment[id][data-comment-file]")',
            ".review-nav-comments a.is-current-comment",
            "data-review-comment-link",
            'event.target.closest("[data-review-comment-link]")',
            "event.stopPropagation();",
            "function selectFileForCommentLink(link)",
            'fileNode.querySelector(\':scope > .review-nav-row a[href^="#"]\')',
            "selectFileForCommentLink(link);",
            'setActiveComment(comment, "manual")',
            "let suppressCommentUpdatesForManualJump = false;",
            "let manualJumpCommentId = \"\";",
            'jumpToHash(link.getAttribute("href"), true)',
            'anchor.matches("[data-review-comment-link]")',
            "function clearActiveComment()",
            "function resetCommentTriggerBaseline()",
            "const wasActive = nextId === activeCommentId;",
            "const visualStateMatches = currentLinks.length === 1 && linkAlreadyCurrent;",
            "if (!wasActive || !visualStateMatches)",
            "if (wasActive)",
            "if (flash === false)",
            "flashTargets(comment, scrollContextElement(comment), false)",
            "let previousCommentCenterY = currentCommentCenterY();",
            "let previousCommentVisibleRange = currentCommentVisibleRange();",
            "let previousCommentScrollY = window.scrollY;",
            "let lastCommentFlashKey = \"\";",
            "let suppressCommentUpdatesForFileJump = false;",
            'document.addEventListener("codex-review-comment-jump-start"',
            'document.addEventListener("codex-review-comment-jump-end"',
            "suppressCommentUpdatesForFileJump || suppressCommentUpdatesForManualJump",
            'setActiveComment(comment, "manual", false)',
            'document.addEventListener("codex-review-file-jump-start"',
            'document.addEventListener("codex-review-file-jump-end"',
            "function currentCommentCenterY()",
            "function currentCommentVisibleRange()",
            "const safeBottom = scrollSafeBottom();",
            "bottom: window.scrollY + Math.max(safeTop, window.innerHeight - safeBottom)",
            "function visibleContentCenterY(scrollY, viewportHeight, safeTop, pinnedTop)",
            "viewportHeight * 0.35",
            "function crossedVisibleEntryBlock(previousRange, currentRange, scrollingDown, box)",
            "const wasVisible = box.bottom > previousRange.top && box.top < previousRange.bottom;",
            "const isVisible = box.bottom > currentRange.top && box.top < currentRange.bottom;",
            "const scrollingDown = currentScrollY >= (baseline ? baseline.scrollY : previousCommentScrollY);",
            "edge: \"top\"",
            "edge: \"bottom\"",
            "edge: \"visible\"",
            "function visibleFallbackAfterActiveHidden(hiddenActive, currentRange, scrollingDown)",
            "if (comment.id === hiddenActive.id)",
            "const rect = comment.getBoundingClientRect();",
            "const isVisible = box.bottom > currentRange.top && box.top < currentRange.bottom;",
            "return best ? { comment: best, edge: \"visible\" } : null;",
            "function updateCommentEdges(filePath, baseline)",
            "if (suppressCommentUpdatesForFileJump || suppressCommentUpdatesForManualJump)",
            "const hiddenActive = resetHiddenActiveComment();",
            "const fallback = visibleFallbackAfterActiveHidden(",
            "const targetRect = commentTargetBox(comment);",
            "const commentRect = comment.getBoundingClientRect();",
            "if (targetRect)",
            "top: targetRect.top + window.scrollY",
            "top: commentRect.top + window.scrollY",
            "...boxes.map(function (box)",
            "function commentFlashTargets(comment)",
            'comment.closest("tr.comment-row")',
            "function commentRangeRows(comment)",
            "function commentTargetBox(comment)",
            "return targetBlockClientRect(commentFlashTargets(comment));",
            "item.classList.add(\"is-open\")",
            "function updateStoryPager(ensureActive, scrollBehavior)",
            "function initStoryPagerResizeObserver()",
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
            "let suppressFileUpdatesForFileJump = false;",
            "let suppressFileUpdatesForCommentJump = false;",
            "function clearActivePath()",
            "function markActivePath(item)",
            ".review-nav-dir.is-current-path",
            "function scheduleNavScrollToItem(item)",
            "const row = event.target.closest(\".review-nav-file > .review-nav-row\");",
            "const link = row ? row.querySelector('a[href^=\"#\"]') : null;",
            "jumpToHash(link.getAttribute(\"href\"), true);",
            "if (firstRect.top > probeY)",
            "setActiveFile(null);",
            "window.clearTimeout(navScrollFollowupTimer);",
            "navScrollFollowupTimer = window.setTimeout(function ()",
            "Math.max(topPadding, (navRect.height - itemRect.height) / 2)",
            'document.addEventListener("codex-review-file-link-selected"',
            'document.addEventListener("codex-review-file-jump-start"',
            'document.addEventListener("codex-review-file-jump-end"',
            'document.addEventListener("codex-review-comment-jump-start"',
            'document.addEventListener("codex-review-comment-jump-end"',
            "if (suppressFileUpdatesForFileJump || suppressFileUpdatesForCommentJump)",
            "const nextFile = candidate || fallback;",
            "if (nextFile)",
            "setActiveFile(nextFile);",
            "const navFileRow = event.target.closest(\".review-nav-file .review-nav-row\");",
            'if (event.target.closest("[data-review-comment-link]"))',
            "const navFileLink = navFileRow ? navFileRow.querySelector('a[href^=\"#\"]') : null;",
            "document.dispatchEvent(new CustomEvent(\"codex-review-file-link-selected\"",
            "function scrollNavToItem(item)",
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
            "function navigationTargetElement(target)",
            "function isReviewNavigationTarget(target)",
            'navigationTarget.scrollIntoView({block: "start", inline: "nearest"});',
            'location.pathname + location.search + "#" + targetId',
            'target.querySelector(":scope > .file-header")',
            "function scrollOffsetForElement(element)",
            "function scrollSafeBottom()",
            'document.querySelector(".diagram-story-nav")',
            "return fileHeaderNavigationTop();",
            "function currentStoryHeight()",
            "function fileHeaderNavigationTop()",
            "function fileHeaderStickyTop()",
            "function settleFileHeaderScroll(element, onDone)",
            "element.getBoundingClientRect().top - fileHeaderStickyTop()",
            "function setStoryPinned(storyPinned)",
            'storySentinel.style.height = Math.ceil(story.getBoundingClientRect().height) + "px";',
            'storySentinel.style.height = "0px";',
            "let userScrollIntent = false;",
            "function cancelProgrammaticScrollForUserIntent()",
            "userScrollIntent = true;",
            "window.clearTimeout(activeScrollTimer);",
            "window.clearTimeout(activeScrollEndTimer);",
            "function handleScrollKeyIntent(event)",
            'if (userScrollIntent || window.scrollY > 0)',
            'window.addEventListener("wheel", cancelProgrammaticScrollForUserIntent, { passive: true });',
            'window.addEventListener("touchmove", cancelProgrammaticScrollForUserIntent, { passive: true });',
            'window.addEventListener("keydown", handleScrollKeyIntent, { capture: true });',
            "const isFileJump = element && element.classList && element.classList.contains(\"file-header\");",
            "const isCommentJump = element && element.classList && element.classList.contains(\"review-comment\");",
            "codex-review-file-jump-start",
            "codex-review-file-jump-end",
            "codex-review-comment-jump-start",
            "codex-review-comment-jump-end",
            'element.closest("article.file") || element',
            "createCodeTargetFlashOverlay",
            "if (codeTargets.length)",
            "createCodeTargetFlashOverlay(codeTargets)",
            "clearCodeTargetFlashOverlays();",
            "const groups = contiguousFlashTargetGroups(targets);",
            "for (const group of groups)",
            "createSingleCodeTargetFlashOverlay(group);",
            "function createSingleCodeTargetFlashOverlay(targets)",
            "const box = targetBlockClientRect(targets);",
            "const documentTop = Math.max(0, box.top + window.scrollY - 3);",
            'overlay.style.height = Math.max(1, box.height + 6) + "px";',
            "function contiguousFlashTargetGroups(targets)",
            "target.previousElementSibling !== previous",
            "function targetBlockClientRect(targets)",
            "bottom: box.bottom",
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
        self.assertNotIn("clipPath", script)
        self.assertNotIn("code-target-flash-shield", script)
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
	            "function requestExtraPaint(node)",
	            "function parseZoom(value)",
            "function zoomAtPoint(nextScale, clientX, clientY)",
            "const anchorX = (content.scrollLeft + offsetX) / scale;",
            "content.scrollLeft = Math.max(0, (anchorX * scale) - offsetX);",
            "function applyStoryObjectZoom(target, nextZoom)",
            "function animateScaleTo(targetScale)",
            "function scrollContainerToElement(container, element, options)",
            "tool.hidden = mode !== \"diagram\" && mode !== \"log\"",
            "setScale(scale + 0.1)",
            "setScale(scale - 0.1)",
            "zoomAtPoint(scale + (direction * step), event.clientX, event.clientY);",
            "function handleArtifactWheel(event)",
            "event.shiftKey && !event.ctrlKey",
            "content.scrollLeft += event.deltaX || event.deltaY",
            "modal.addEventListener(\"wheel\", function (event)",
            "content.scrollLeft += event.deltaX;",
            "mode !== \"diagram\" && mode !== \"log\"",
            "collapseOpenStoryComment(event);",
            "event.target.closest(\".asset-story-comment\")",
            "function scheduleFocusedArtifactView(target, storyZoom, storyComment)",
            "content.classList.remove(\"is-preparing-story-view\");",
            "const shouldCenterTarget = Boolean(target && (storyZoom || storyComment));",
            "function positionStoryComment(comment)",
            "const availableWidth = Math.max(180, contentRect.width - margin * 2);",
            "const collapsed = comment.classList.contains(\"is-collapsed\");",
            "const commentWidth = collapsed ? 46 : Math.min(520, availableWidth);",
            "comment.style.removeProperty(\"width\");",
            "mode === \"log\"",
            "function createAssetStoryComment(nextStoryContext)",
            "comment.className = \"asset-story-comment is-collapsed\";",
            "toggle.className = \"asset-story-comment-toggle\";",
            "toggle.textContent = \"?\";",
            "function toggleStoryComment(comment, toggle)",
            "const markerRect = toggle.getBoundingClientRect();",
            "comment.classList.toggle(\"is-collapsed\");",
            "comment.style.left = (currentLeft + markerRect.left - nextMarkerRect.left) + \"px\";",
            "function collapseOpenStoryComment(event)",
            "content.querySelector(\".asset-story-comment:not(.is-collapsed)\")",
            "comment.classList.add(\"is-positioned\");",
            "content.classList.toggle(\"is-preparing-story-view\", Boolean(nextStoryContext || storyZoom));",
            "detail: { status: \"open\", index: nextStoryContext.index }",
	            "detail: { status: \"closed\" }",
	            "requestExtraPaint(modal)",
	            "requestExtraPaint(document.body)",
            "function closestSvgObjectShape(labelNode)",
            "const sourceArea = Math.max(box.width * box.height, 1);",
            "if (area > Math.max(65000, sourceArea * 28))",
            "function markSvgTextInsideShape(shape, sourceLabel)",
            "asset-focus-contained-text",
            'node.classList.contains("diagram-note-link")',
            "codex-review-story-move",
            "asset-focus-object",
            "document.body.classList.add(\"has-diagram-open\")",
	            "document.body.classList.remove(\"has-diagram-open\")",
	            "function codeOverlayRoot()",
	            "positionCodePopover(popover)",
            "requestExtraPaint(popover)",
            'event.target.closest("svg text, svg tspan")',
            "clearCodeLinkHover();\n      return;",
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
            "[\"--diagram-svg-bg\", \"#ffffff\"]",
            "[\"--diagram-svg-arrow\", \"#334155\"]",
            "insertSvgBackground(clone)",
            "removeCodeLinkState(clone)",
            "downloadBlob(safeFileName(activeExportName, \"svg\")",
            "downloadBlob(safeFileName(activeExportName, \"html\")",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, script)

    def test_plantuml_preview_svg_embeds_theme_specific_overrides(self) -> None:
        source = (
            '<svg style="background:#1F1F1F;">'
            '<text fill="#D4D4D4">title</text>'
            '<rect fill="#2D2D30" style="stroke: #D4D4D4;"/>'
            '<path fill="#FFFFFF" style="stroke: #D4D4D4;"/>'
            '<path fill="#3B3216" style="stroke: #D7BA7D;"/>'
            "</svg>"
        )

        light = plantuml_preview_svg(source, "light")
        dark = plantuml_preview_svg(source, "dark")

        self.assertIn("svg { background: #ffffff !important; }", light)
        self.assertIn("fill: #111827 !important; stroke: none !important;", light)
        self.assertIn("fill: #ffffff !important; stroke: #475569 !important;", light)
        self.assertIn("fill: #fff8c5 !important; stroke: #ca5010 !important;", light)
        self.assertIn("svg { background: #1f1f1f !important; }", dark)
        self.assertIn("fill: #d4d4d4 !important; stroke: none !important;", dark)


if __name__ == "__main__":
    unittest.main()
