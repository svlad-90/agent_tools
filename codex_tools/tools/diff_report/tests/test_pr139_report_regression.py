from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from codex_tools.tools.diff_report.comments_compose import compose_comments_payload
from codex_tools.tools.diff_report.core import generate_report


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "pr139"
FIXTURE_REPORT_ROOT = FIXTURE_ROOT / "report"
FIXTURE_DEV_ROOT = FIXTURE_ROOT / "dev"
FIXTURE_DIFF_DIR = FIXTURE_REPORT_ROOT / "diff"
FIXTURE_BASENAME = "pr139-to-local-working-tree"
PR139_COMPOSE_FINDINGS = FIXTURE_DEV_ROOT / "pr139-compose-smoke-findings.json"


class Pr139ReportRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        missing = [
            path
            for path in (
                FIXTURE_DIFF_DIR / f"{FIXTURE_BASENAME}.patch",
                FIXTURE_DIFF_DIR / f"{FIXTURE_BASENAME}.json",
                FIXTURE_REPORT_ROOT / "puml" / "fdt-review-fix-api-flow.svg",
                FIXTURE_REPORT_ROOT / "runtime" / "pr139-fdt-final-runtime-xen419.log",
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
	            "requestExtraPaint(popover)",
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
            "detailsBody.innerHTML = step.dataset.storyBodyHtml || \"\";",
            "--page-gutter: 8px",
            "--comment-target-ctx-bg: #f4f6f4",
            "--comment-target-add-bg: #d6eedc",
            "--comment-target-del-bg: #f8d5da",
            "--comment-target-overlay: rgba(202,80,16,.045)",
            "--text-scale: 1",
            "--scaled-code-font: calc(var(--screen-code-font) * var(--text-scale))",
            "--diff-num-width: 64px",
            "--comment-gutter-width: 112px",
            "--brand-scale: 1",
            "--brand-mark-size: 172px",
            "--floating-control-size: 44px",
            "--floating-control-gap: 18px",
            "--floating-content-gutter: max(24px, calc((100vw - var(--nav-width) - var(--content-width)) / 2))",
            "--review-nav-top: calc(var(--page-gutter) + var(--brand-height) + 12px)",
            "--story-nav-height: 76px;",
            "html { scrollbar-gutter: stable; }",
            "padding-bottom: var(--story-nav-height);",
            "bottom: calc(var(--page-gutter) + var(--story-nav-height));",
            "main { width: calc(100% - var(--nav-width) - (var(--page-gutter) * 3))",
            "header, section, .file { width: min(100%, var(--content-width));",
            "body.has-diagram-open .report-brand { z-index: 9; }",
            ".review-nav h2 { min-width: 0;",
            "overscroll-behavior: contain;",
            "white-space: nowrap;",
            ".settings-dialog { position: absolute; left: 50%; top: 50%;",
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
            "body.is-resizing-review-nav .story { transition: none; }",
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
            "comment.className = \"asset-story-comment is-collapsed\";",
            "toggle.textContent = \"?\";",
            "function toggleStoryComment(comment, toggle)",
            "const markerRect = toggle.getBoundingClientRect();",
            "comment.classList.toggle(\"is-collapsed\");",
            "comment.style.left = (currentLeft + markerRect.left - nextMarkerRect.left) + \"px\";",
            "function collapseOpenStoryComment(event)",
            "content.querySelector(\".asset-story-comment:not(.is-collapsed)\")",
            "background: var(--comment-bg); color: var(--text);",
            "opacity: 0; visibility: hidden; pointer-events: none;",
            "opacity: 1; visibility: visible; pointer-events: auto;",
            ".diagram-story-nav { position: fixed;",
            "z-index: 1004;",
            "grid-template-columns: minmax(0, 240px) 58px minmax(0, 240px);",
            'data-diagram-story-toggle data-tooltip="Open slide" aria-label="Open slide"',
            ".diagram-story-nav .story-slide-toggle",
            ".diagram-story-nav .story-slide-toggle::before",
            ".diagram-story-nav .story-slide-toggle::after",
            "content: attr(data-tooltip);",
            ".diagram-story-nav .story-slide-toggle:hover::after",
            ".diagram-story-nav .story-slide-toggle.is-open",
            ".diagram-story-nav .story-slide-toggle.is-open::before",
            "--asset-log-scale",
            ".diagram-zoom-stage { transform-origin: 0 0; width: max-content; min-width: 100%; }",
            ".diagram-zoom-stage svg text, .diagram-zoom-stage svg tspan { cursor: text; user-select: text; }",
            ".diagram-scroll.is-preparing-story-view .diagram-zoom-stage",
            "transition: font-size .16s ease;",
            "width: min(1120px, calc(100vw - 32px)); height: min(86vh, calc(100vh - 32px));",
            "font-size: var(--screen-body-font);",
            "svg .asset-search-match { fill: #cf222e !important; stroke: none !important; }",
            "svg .asset-search-submatch { fill: transparent; stroke: #ff4d5e;",
            "svg .asset-search-current { fill: #ff2a3d !important; stroke: none !important; filter: none; font-weight: 800 !important;",
            ".summary-artifact-preview .diagram-preview { width: min(760px, 100%); }",
            ".summary-artifact-preview .diagram-preview-canvas { height: clamp(220px, 26vw, 320px); }",
            "svg text.asset-search-current, svg tspan.asset-search-current",
            ".code-target-flash-overlay { position: absolute; z-index: 5;",
            "function createCodeTargetFlashOverlay(targets)",
            "function rowsWithIntermediateDeletes(rows)",
            "tr.comment-target.add .num, tr.comment-target.add .code { background: linear-gradient(to right, var(--comment-target-overlay), var(--comment-target-overlay)), var(--comment-target-add-bg); }",
            "tr.comment-target.del .num, tr.comment-target.del .code { background: linear-gradient(to right, var(--comment-target-overlay), var(--comment-target-overlay)), var(--comment-target-del-bg); }",
            "tr.comment-row-add { --comment-row-target-bg: var(--comment-target-add-bg); }",
            "tr.comment-row-del { --comment-row-target-bg: var(--comment-target-del-bg); }",
            "tr.comment-row td { background: linear-gradient(to right, transparent calc(var(--diff-num-width) - 1px), var(--border) calc(var(--diff-num-width) - 1px) var(--diff-num-width), transparent var(--diff-num-width)), linear-gradient(to right, transparent calc(var(--comment-gutter-width) - 1px), var(--border) calc(var(--comment-gutter-width) - 1px) var(--comment-gutter-width), transparent var(--comment-gutter-width)), linear-gradient(to right, var(--comment-target-overlay) 0 var(--comment-gutter-width), transparent var(--comment-gutter-width)), linear-gradient(to right, var(--comment-row-target-bg) 0 var(--comment-gutter-width), transparent var(--comment-gutter-width)); padding: 0 !important; box-shadow: inset 4px 0 0 var(--comment-border); }",
            "tr.comment-target-end:has(+ tr.comment-row) .num, tr.comment-target-end:has(+ tr.comment-row) .code { box-shadow: none; }",
            'tr[data-file="\' + cssEscape(file) + \'"][data-new-line="\' + String(rangeStart) + \'"]',
            "function cssEscape(value)",
            "@media (min-width: 1800px)",
            "@media (max-width: 1500px)",
            "@media (max-width: 1280px)",
            ".story-step-strip { display: grid; grid-template-columns: 32px minmax(0, 1fr) 32px;",
            ".story-page-button { display: inline-flex;",
            ".story-steps { display: grid; grid-template-rows: minmax(56px, 1fr);",
            "grid-auto-columns: var(--story-step-column-width, 260px)",
            "scroll-behavior: smooth",
            'polygon[fill="#FFFFFF"]',
            'path[fill="#FFFFFF"]',
            'path[fill="#FEFECE"]',
            'polygon[fill="#2D2D30"]',
            'path[fill="#3B3216"]',
            'ellipse[fill="#FFFFFF"]',
            'ellipse[fill="#D4D4D4"]',
            'polygon[fill="#D4D4D4"]',
            'polygon[fill="#FBFB77"]',
            ".settings-launcher { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(var(--story-nav-height) + 24px);",
            ".to-top-button { position: fixed; right: max(8px, calc(var(--floating-content-gutter) - var(--floating-control-size) - var(--floating-control-gap))); bottom: calc(var(--story-nav-height) + 24px + var(--floating-control-size) + 10px);",
            ".report-settings-launcher { right: 14px; bottom: calc(var(--story-nav-height) + 24px); }",
            ".to-top-button { right: 14px; bottom: calc(var(--story-nav-height) + 24px + var(--floating-control-size) + 12px); }",
            "body.has-left-top .to-top-button { opacity: 1; visibility: visible;",
            "class=\"settings-launcher report-settings-launcher\"",
            ".settings-toggle span, .settings-toggle::before, .settings-toggle::after",
            "header, section, .file, .asset-inventory { width: 100%; margin-left: 0; margin-right: 0; }",
            'setSvgSearchClass(node, "asset-search-match", true)',
            "function closestSvgObjectShape(labelNode)",
            "const sourceArea = Math.max(box.width * box.height, 1);",
            "if (area > Math.max(65000, sourceArea * 28))",
            "function markSvgTextInsideShape(shape, sourceLabel)",
            "asset-focus-contained-text",
            'node.classList.contains("diagram-note-link")',
            "function scheduleSearch(resetIndex)",
            "window.requestAnimationFrame(function ()",
            "addSvgSearchSubmatches(node, query)",
            "parent.insertBefore(underlay, textNode)",
            "function svgTextRangeBox(node, start, length)",
            "searchInput.select()",
            'setSvgSearchClass(current, "asset-search-current", true)',
            'node.style.setProperty("fill", isCurrent ? "#ff2a3d" : "#cf222e", "important")',
            'const textScaleKey = "codex-diff-report-text-scale"',
            "const minTextScale = 0.5",
            "const maxTextScale = 2",
            "let activeTextScale = 1",
            "applyTextScale(activeTextScale + Number(button.dataset.textScaleStep || 0), true)",
            'data-text-scale-step="0.1"',
            "restoreSvgSearchPaint(node)",
            "const widthScale = availableWidth > 0 ? availableWidth / size.width : 1",
            "const heightScale = availableHeight > 0 ? availableHeight / size.height : 1",
	            "initialScale = Math.min(3, widthScale)",
	            "function requestExtraPaint(node)",
            "function parseZoom(value)",
            'event.target.closest("svg text, svg tspan")',
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
            "const collapsed = comment.classList.contains(\"is-collapsed\");",
            "const commentWidth = collapsed ? 46 : Math.min(520, availableWidth);",
            "comment.style.removeProperty(\"width\");",
            "mode === \"log\"",
            "function createAssetStoryComment(nextStoryContext)",
            "comment.classList.add(\"is-positioned\");",
            "content.classList.toggle(\"is-preparing-story-view\", Boolean(nextStoryContext || storyZoom));",
            "codex-review-story-move",
            "codex-review-story-layout",
	            "document.body.classList.add(\"has-diagram-open\")",
	            "requestExtraPaint(modal)",
	            "requestExtraPaint(document.body)",
	            "function updateStoryPager(ensureActive, scrollBehavior)",
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
            "let previousCommentVisibleRange = currentCommentVisibleRange();",
            "let suppressCommentUpdatesForFileJump = false;",
            'document.addEventListener("codex-review-comment-jump-start"',
            'document.addEventListener("codex-review-comment-jump-end"',
            "suppressCommentUpdatesForFileJump || suppressCommentUpdatesForManualJump",
            'setActiveComment(comment, "manual", false)',
            'document.addEventListener("codex-review-file-jump-start"',
            'document.addEventListener("codex-review-file-jump-end"',
            "function currentCommentVisibleRange()",
            "const safeBottom = scrollSafeBottom();",
            "bottom: window.scrollY + Math.max(safeTop, window.innerHeight - safeBottom)",
            "function crossedVisibleEntryBlock(previousRange, currentRange, scrollingDown, box)",
            "const wasVisible = box.bottom > previousRange.top && box.top < previousRange.bottom;",
            "const isVisible = box.bottom > currentRange.top && box.top < currentRange.bottom;",
            "edge: \"top\"",
            "edge: \"bottom\"",
            "edge: \"visible\"",
            "function visibleFallbackAfterActiveHidden(hiddenActive, currentRange, scrollingDown)",
            "if (comment.id === hiddenActive.id)",
            "const rect = comment.getBoundingClientRect();",
            "const isVisible = box.bottom > currentRange.top && box.top < currentRange.bottom;",
            "return best ? { comment: best, edge: \"visible\" } : null;",
            "item.classList.add(\"is-open\")",
	            "function initVocabularyPopovers()",
	            "function requestExtraPaint(node)",
	            "function openVocabularyPopover(wrap)",
            "function toggleVocabularyPopover(wrap)",
            'document.addEventListener("click", function (event)',
            'document.addEventListener("keydown", function (event)',
            'event.target.closest(".vocabulary-ref")',
            'trigger.closest(".vocabulary-ref-wrap")',
            "function isVocabularyPointerInside(wrap, event)",
            "document.addEventListener(\"pointerdown\", function (event)",
	            "wrap.classList.add(\"is-open\");",
	            'wrap.style.setProperty("--vocabulary-popover-left"',
	            "requestExtraPaint(popover)",
	            "document.documentElement.style.setProperty(\"--brand-scale\"",
            "scheduleStoryPagerUpdate(false, \"auto\");",
            "function initStoryPagerResizeObserver()",
            "new ResizeObserver(function ()",
            "storySteps.getBoundingClientRect().width",
            "function moveStoryPage(direction)",
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
            "function navigationTargetElement(target)",
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
            "const isFileJump = element && element.classList && element.classList.contains(\"file-header\");",
            "const isCommentJump = element && element.classList && element.classList.contains(\"review-comment\");",
            "codex-review-file-jump-start",
            "codex-review-file-jump-end",
            "codex-review-comment-jump-start",
            "codex-review-comment-jump-end",
            'element.closest("article.file") || element',
            "if (codeTargets.length)",
            "createCodeTargetFlashOverlay(codeTargets)",
            "clearCodeTargetFlashOverlays();",
            "const groups = contiguousFlashTargetGroups(targets);",
            "for (const group of groups)",
            "createSingleCodeTargetFlashOverlay(group);",
            "function createSingleCodeTargetFlashOverlay(targets)",
            "const documentTop = Math.max(0, box.top + window.scrollY - 3);",
            'overlay.style.height = Math.max(1, box.height + 6) + "px";',
            "function contiguousFlashTargetGroups(targets)",
            "target.previousElementSibling !== previous",
            "let previousCommentCenterY = currentCommentCenterY();",
            "let previousCommentScrollY = window.scrollY;",
            "let lastCommentFlashKey = \"\";",
            "function currentCommentCenterY()",
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
            "const box = targetBlockClientRect(targets);",
            "function targetBlockClientRect(targets)",
            "bottom: box.bottom",
            "function setOpenStep(index)",
            "step.classList.remove(\"is-open\")",
            "steps[index].classList.add(\"is-open\")",
            "function updateStoryMoveButtons()",
            "const storyMoveButtons = Array.from(document.querySelectorAll(\"[data-diagram-story-step]\"));",
            "const storyToggleButtons = Array.from(document.querySelectorAll(\"[data-diagram-story-toggle]\"));",
            "steps[nextIndex].classList.contains(\"is-open\")",
            "function toggleCurrentStorySlide()",
            "const label = open ? \"Close slide\" : \"Open slide\";",
            "button.dataset.tooltip = label;",
            "closeOpenStoryArtifact();",
            "setOpenStep(null);",
            "codex-review-story-artifact",
            ".story-step.is-open",
            ".story-step.is-open .story-step-index",
            "const availableWidth = Math.max(180, contentRect.width - margin * 2);",
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
            "function scrollNavToItem(item)",
            "const hasOwnScroll = nav.scrollHeight > nav.clientHeight + 2 || nav.scrollWidth > nav.clientWidth + 2;",
            "Math.max(bottomPadding, (navRect.height - itemRect.height) / 2)",
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
            "left: 0; right: 0; bottom: 0;",
            ".diagram-story-nav button:disabled",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)

        self.assertEqual(8, html.count("data-story-index="))
        self.assertGreaterEqual(html.count('class="review-comment"'), 10)
        self.assertNotIn("../puml/fdt-review-fix-api-flow.svg", html)
        self.assertNotIn("../runtime/pr139-fdt-final-runtime-xen419.log", html)
        self.assertNotIn("General view", html)
        self.assertNotIn("clipPath", html)
        self.assertNotIn("code-target-flash-shield", html)
        self.assertNotIn("data-diagram-general", html)
        self.assertNotIn("diagram-story-context", html)
        self.assertIn('data-story-nav="prev"', html)
        self.assertIn('data-story-nav="next"', html)
        self.assertNotIn("story-controls", html)
        self.assertNotIn("story-settings-launcher", html)
        self.assertNotIn('id="story-counter"', html)
        self.assertNotIn("story-top-inline", html)
        self.assertNotIn("lastOpenedStoryIndex", html)
        self.assertNotIn(".review-comment::before", html)
        self.assertRegex(
            html,
            r'<tr class="del comment-target" data-diff-kind="del">'
            r'<td class="num">126</td><td class="num"></td><td class="code">-',
        )
        self.assertIn('<tr class="comment-row comment-row-add"><td colspan="3">', html)

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
        shutil.copytree(FIXTURE_REPORT_ROOT, report_root)
        return report_root


if __name__ == "__main__":
    unittest.main()
