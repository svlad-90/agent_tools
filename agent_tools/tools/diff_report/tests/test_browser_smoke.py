from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from agent_tools.tools.diff_report.cli import main
from agent_tools.tools.diff_report.core import generate_report


def _browser() -> str | None:
    configured = os.environ.get("DIFF_REPORT_BROWSER")
    if configured:
        return configured
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


@unittest.skipUnless(_browser(), "Chrome-compatible browser is not available")
class BrowserSmokeTests(unittest.TestCase):
    def test_report_json_self_test_runs_in_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(
                [
                    "--report-json",
                    str(report_json),
                    "--output",
                    str(output),
                    "--report-test-mode",
                ]
            )

            self.assertEqual(0, status)
            result = _evaluate_in_browser(
                output,
                "window.__reportSelfTest.runAll()",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("pass"), result)
        self.assertGreaterEqual(int(result.get("total", 0)), 1)

    def test_story_bar_pinning_does_not_jump_during_manual_scroll(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(_long_diff(), encoding="utf-8")
            comments_path.write_text(json.dumps(_story_comments()), encoding="utf-8")
            generate_report(
                output_path=output,
                title="Synthetic scroll report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  window.scrollTo(0, 1400);
                  window.dispatchEvent(new WheelEvent("wheel", {deltaY: 1400, bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 180));
                  const afterWait = window.scrollY;
                  const sentinel = document.querySelector(".story-sentinel");
                  const sentinelHeight = sentinel ? sentinel.getBoundingClientRect().height : 0;
                  const pinned = document.body.classList.contains("has-pinned-story");
                  window.scrollTo(0, 900);
                  await new Promise(resolve => setTimeout(resolve, 80));
                  return {
                    afterWait,
                    afterManual: window.scrollY,
                    pinned,
                    sentinelHeight
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertGreaterEqual(result.get("afterWait", 0), 1000, result)
        self.assertGreaterEqual(result.get("afterManual", 0), 850, result)
        self.assertTrue(result.get("pinned"), result)
        self.assertGreater(result.get("sentinelHeight", 0), 0, result)

    def test_story_navigation_can_be_hidden_and_restored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(_long_diff(), encoding="utf-8")
            comments_path.write_text(json.dumps(_story_comments()), encoding="utf-8")
            generate_report(
                output_path=output,
                title="Synthetic story controls report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  const nav = document.querySelector(".diagram-story-nav");
                  const hide = document.querySelector("[data-story-nav-hide]");
                  const show = document.querySelector("[data-story-nav-show]");
                  if (!nav || !hide || !show) {
                    return {pass: false, reason: "controls missing"};
                  }
                  const visibleBottom = getComputedStyle(document.body).paddingBottom;
                  hide.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const hiddenStyle = getComputedStyle(nav);
                  const hidden = {
                    bodyClass: document.body.classList.contains("story-nav-hidden"),
                    ariaHidden: nav.getAttribute("aria-hidden"),
                    visible: hiddenStyle.visibility,
                    pointerEvents: hiddenStyle.pointerEvents,
                    showHiddenAttr: show.hidden,
                    bottomPadding: getComputedStyle(document.body).paddingBottom,
                  };
                  show.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const restoredStyle = getComputedStyle(nav);
                  return {
                    pass: true,
                    visibleBottom,
                    hidden,
                    restored: {
                      bodyClass: document.body.classList.contains("story-nav-hidden"),
                      ariaHidden: nav.getAttribute("aria-hidden"),
                      visible: restoredStyle.visibility,
                      pointerEvents: restoredStyle.pointerEvents,
                      showHiddenAttr: show.hidden,
                      bottomPadding: getComputedStyle(document.body).paddingBottom,
                    },
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("pass"), result)
        self.assertEqual("true", result["hidden"]["ariaHidden"], result)
        self.assertEqual("hidden", result["hidden"]["visible"], result)
        self.assertEqual("none", result["hidden"]["pointerEvents"], result)
        self.assertTrue(result["hidden"]["bodyClass"], result)
        self.assertFalse(result["hidden"]["showHiddenAttr"], result)
        self.assertEqual("0px", result["hidden"]["bottomPadding"], result)
        self.assertEqual("false", result["restored"]["ariaHidden"], result)
        self.assertEqual("visible", result["restored"]["visible"], result)
        self.assertNotEqual("none", result["restored"]["pointerEvents"], result)
        self.assertFalse(result["restored"]["bodyClass"], result)
        self.assertTrue(result["restored"]["showHiddenAttr"], result)
        self.assertEqual(result["visibleBottom"], result["restored"]["bottomPadding"], result)

    def test_mobile_page_scrolls_over_relationship_graph_and_selection_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  const scrollOver = async (selector) => {
                    const element = document.querySelector(selector);
                    if (!element) {
                      return {selector, found: false};
                    }
                    element.scrollIntoView({block: "center", inline: "nearest"});
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    const before = window.scrollY;
                    const event = new WheelEvent("wheel", {deltaY: 360, bubbles: true, cancelable: true});
                    element.dispatchEvent(event);
                    if (!event.defaultPrevented) {
                      window.scrollBy(0, 360);
                    }
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    return {
                      selector,
                      found: true,
                      before,
                      after: window.scrollY,
                      prevented: event.defaultPrevented,
                    };
                  };
                  const canvas = await scrollOver(".relationship-canvas");
                  const table = await scrollOver(".relationship-selection-table");
                  return {canvas, table};
                })()""",
                await_promise=True,
                viewport={"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True},
            )

        self.assertIsInstance(result, dict)
        for key in ("canvas", "table"):
            with self.subTest(key=key):
                item = result[key]
                self.assertTrue(item.get("found"), result)
                self.assertFalse(item.get("prevented"), result)
                self.assertGreater(item.get("after", 0), item.get("before", 0), result)

    def test_mobile_contents_nav_does_not_capture_page_scroll(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(() => {
                  const toc = document.querySelector(".report-toc");
                  if (!toc) {
                    return {pass: false, reason: "toc missing"};
                  }
                  const style = getComputedStyle(toc);
                  return {
                    pass: style.position === "static" &&
                      style.overflowY === "visible" &&
                      style.maxHeight === "none" &&
                      style.touchAction === "pan-y",
                    position: style.position,
                    overflowY: style.overflowY,
                    maxHeight: style.maxHeight,
                    touchAction: style.touchAction,
                  };
                })()""",
                viewport={"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True},
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("pass"), result)

    def test_relationship_preview_chips_open_matching_graph_views(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  const previewButtons = Array.from(document.querySelectorAll(".relationship-preview-row button"));
                  const typeButton = previewButtons.find((button) => /component\s+60/.test(button.textContent || ""));
                  const statusButton = previewButtons.find((button) => /not_failed\s+60/.test(button.textContent || ""));
                  if (!typeButton || !statusButton) {
                    return {pass: false, reason: "preview buttons missing", labels: previewButtons.map((button) => button.textContent)};
                  }
                  typeButton.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const browser = document.querySelector("[data-relationship-browser]");
                  const typeState = browser && browser.__relationshipState;
                  const typeResult = typeState ? {
                    modalOpen: !document.querySelector("[data-relationship-modal]").hidden,
                    selectedId: typeState.selectedId,
                    enabledTypes: Array.from(typeState.enabledTypes).sort(),
                    targetType: typeState.typeSearchType,
                    rendered: typeState.visibleGraph ? typeState.visibleGraph.nodes.length : 0,
                  } : null;
                  statusButton.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const statusState = browser && browser.__relationshipState;
                  const statusResult = statusState ? {
                    enabledStatuses: Array.from(statusState.statusFilter.enabled).sort(),
                    rendered: statusState.visibleGraph ? statusState.visibleGraph.nodes.length : 0,
                    edges: statusState.visibleGraph ? statusState.visibleGraph.edges.length : 0,
                    plainListMode: Boolean(statusState.plainListMode),
                  } : null;
                  return {typeResult, statusResult};
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertIn("typeResult", result)
        self.assertEqual("product:test", result["typeResult"]["selectedId"], result)
        self.assertEqual(["component", "product"], result["typeResult"]["enabledTypes"], result)
        self.assertEqual("component", result["typeResult"]["targetType"], result)
        self.assertGreater(result["typeResult"]["rendered"], 1, result)
        self.assertEqual(["not_failed"], result["statusResult"]["enabledStatuses"], result)
        self.assertTrue(result["statusResult"]["plainListMode"], result)
        self.assertEqual(0, result["statusResult"]["edges"], result)
        self.assertGreater(result["statusResult"]["rendered"], 1, result)

    def test_relationship_search_is_global_ranked_and_highlighted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  document.querySelector("[data-relationship-open]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const browser = document.querySelector("[data-relationship-browser]");
                  const state = browser && browser.__relationshipState;
                  const search = document.querySelector("[data-relationship-search]");
                  const regex = document.querySelector("[data-relationship-search-regex]");
                  const focusSelect = document.querySelector("[data-relationship-node-select]");
                  const focusType = document.querySelector("[data-relationship-focus-type]");
                  const focusScope = document.querySelector("[data-relationship-focus-scope]");
                  const renderedBefore = state.visibleGraph.nodes.length;
                  const regexDefault = regex.checked;
                  regex.checked = false;
                  regex.dispatchEvent(new Event("change", {bubbles: true}));
                  search.value = "component";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const results = Array.from(document.querySelectorAll("[data-relationship-search-result]"));
                  const labels = results.slice(0, 3).map((button) => button.textContent || "");
                  const firstStatusChip = results[0] && results[0].querySelector(".relationship-search-status");
                  const firstStatusText = firstStatusChip ? firstStatusChip.textContent || "" : "";
                  const marked = document.querySelectorAll(".relationship-search-result mark").length;
                  const renderedAfterTextSearch = state.visibleGraph.nodes.length;
                  search.value = "not_failed";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const plainStatusResults = Array.from(document.querySelectorAll("[data-relationship-search-result]"));
                  regex.checked = true;
                  regex.dispatchEvent(new Event("change", {bubbles: true}));
                  search.value = "^not_failed.*Component 5";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const regexResults = Array.from(document.querySelectorAll("[data-relationship-search-result]"));
                  const firstRegex = regexResults[0] ? regexResults[0].textContent || "" : "";
                  const queryBeforeSelection = search.value;
                  const selectedResultId = regexResults[0] ? regexResults[0].getAttribute("data-relationship-search-result") : "";
                  if (regexResults[0]) regexResults[0].click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const selectionClosedSearch = search.value === queryBeforeSelection && document.querySelector("[data-relationship-search-results]").hidden;
                  search.focus();
                  search.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const selectedSearchRow = selectedResultId
                    ? document.querySelector(`[data-relationship-search-result="${CSS.escape(selectedResultId)}"]`)
                    : null;
                  const selectionReopenedAtSelected = Boolean(
                    selectedSearchRow &&
                    selectedSearchRow.classList.contains("is-selected") &&
                    !document.querySelector("[data-relationship-search-results]").hidden
                  );
                  search.focus();
                  search.value = "component";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const changedTextKeptVisibleAnchor = state.searchAnchorResultId === selectedResultId && Boolean(
                    document.querySelector(`[data-relationship-search-result="${CSS.escape(selectedResultId)}"].is-selected`)
                  );
                  document.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const clearedByEscape = search.value === "" && !document.querySelector("[data-relationship-modal]").hidden;
                  document.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  return {
                    noLegacyControls: !focusSelect && !focusType && !focusScope,
                    regexDefault,
                    labels,
                    firstStatusText,
                    marked,
                    renderedBefore,
                    renderedAfterTextSearch,
                    plainStatusResultCount: plainStatusResults.length,
                    firstRegex,
                    selectedId: state.selectedId,
                    selectionClosedSearch,
                    selectionReopenedAtSelected,
                    changedTextKeptVisibleAnchor,
                    clearedByEscape,
                    closedBySecondEscape: document.querySelector("[data-relationship-modal]").hidden,
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result["noLegacyControls"], result)
        self.assertTrue(result["regexDefault"], result)
        self.assertTrue(result["labels"], result)
        self.assertTrue(result["labels"][0].startswith("not_failed"), result)
        self.assertEqual("not_failed", result["firstStatusText"], result)
        self.assertGreater(result["marked"], 0, result)
        self.assertEqual(result["renderedBefore"], result["renderedAfterTextSearch"], result)
        self.assertEqual(0, result["plainStatusResultCount"], result)
        self.assertIn("Component 5", result["firstRegex"], result)
        self.assertEqual("component:5", result["selectedId"], result)
        self.assertTrue(result["selectionClosedSearch"], result)
        self.assertTrue(result["selectionReopenedAtSelected"], result)
        self.assertTrue(result["changedTextKeptVisibleAnchor"], result)
        self.assertTrue(result["clearedByEscape"], result)
        self.assertTrue(result["closedBySecondEscape"], result)

    def test_relationship_plain_search_matches_type_name_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_plain_search_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  document.querySelector("[data-relationship-open]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const search = document.querySelector("[data-relationship-search]");
                  const regex = document.querySelector("[data-relationship-search-regex]");
                  const results = document.querySelector("[data-relationship-search-results]");
                  regex.checked = false;
                  regex.dispatchEvent(new Event("change", {bubbles: true}));
                  search.value = "CDD Andr";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const plainRows = Array.from(results.querySelectorAll("[data-relationship-search-result]"));
                  const firstPlain = plainRows[0];
                  search.value = "fail";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const plainStatusCount = results.querySelectorAll("[data-relationship-search-result]").length;
                  regex.checked = true;
                  regex.dispatchEvent(new Event("change", {bubbles: true}));
                  search.value = "^fail.*CDD.*Android";
                  search.dispatchEvent(new Event("input", {bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 140));
                  const regexRows = Array.from(results.querySelectorAll("[data-relationship-search-result]"));
                  return {
                    plainCount: plainRows.length,
                    plainStatus: firstPlain && firstPlain.querySelector(".relationship-search-status").textContent,
                    plainText: firstPlain && firstPlain.querySelector(".relationship-search-result-text").textContent,
                    plainTitle: firstPlain && firstPlain.title,
                    plainStatusCount,
                    regexCount: regexRows.length,
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertEqual(1, result["plainCount"], result)
        self.assertEqual("fail", result["plainStatus"], result)
        self.assertIn("CDD", result["plainText"], result)
        self.assertIn("Android audio routing", result["plainText"], result)
        self.assertNotIn("fail", result["plainTitle"], result)
        self.assertEqual(0, result["plainStatusCount"], result)
        self.assertEqual(1, result["regexCount"], result)

    def test_relationship_plain_list_keeps_status_and_level_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_plain_list_order_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  document.querySelector("[data-relationship-open]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const browser = document.querySelector("[data-relationship-browser]");
                  const plain = document.querySelector("[data-relationship-plain-list]");
                  if (!browser || !plain) {
                    return {pass: false, reason: "relationship browser or plain list checkbox missing"};
                  }
                  const normalState = browser.__relationshipState;
                  const normalGraph = normalState && normalState.visibleGraph;
                  const normalStatusValues = normalState.statusFilter.values.filter((value) => normalState.statusFilter.enabled.has(value));
                  const normalRankMap = normalState.traversal.typeRanks;
                  const normalNodes = normalGraph.nodes.map((node) => ({
                    id: node.id,
                    type: node.type,
                    status: node.status,
                    label: node.label,
                    statusRank: normalStatusValues.indexOf(node.status),
                    typeRank: normalRankMap[node.type] ?? 99,
                    position: normalGraph.hierarchyLayout.positions.get(node.id),
                  }));
                  const normalContext = normalNodes.filter((node) => node.id === normalState.selectedId);
                  const normalExpected = normalContext.concat(
                    normalNodes.filter((node) => node.id !== normalState.selectedId).sort((left, right) =>
                      left.statusRank - right.statusRank ||
                      left.typeRank - right.typeRank ||
                      String(left.type).localeCompare(String(right.type)) ||
                      String(left.label).localeCompare(String(right.label))
                    )
                  );
                  const normalVisualGroups = new Map();
                  for (const node of normalNodes.filter((node) => node.id !== normalState.selectedId)) {
                    const key = `${node.statusRank}:${node.typeRank}`;
                    if (!normalVisualGroups.has(key)) normalVisualGroups.set(key, []);
                    normalVisualGroups.get(key).push(node);
                  }
                  const normalVisualPass = Array.from(normalVisualGroups.values()).every((group) => {
                    const expectedGroup = group.slice().sort((left, right) =>
                      String(left.type).localeCompare(String(right.type)) ||
                      String(left.label).localeCompare(String(right.label))
                    );
                    const visualGroup = group.slice().sort((left, right) =>
                      Math.round(left.position.y) - Math.round(right.position.y) ||
                      Math.round(left.position.x) - Math.round(right.position.x)
                    );
                    return JSON.stringify(visualGroup.map((node) => node.id)) === JSON.stringify(expectedGroup.map((node) => node.id));
                  });
                  plain.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const state = browser.__relationshipState;
                  const graph = state && state.visibleGraph;
                  const statusValues = state.statusFilter.values.filter((value) => state.statusFilter.enabled.has(value));
                  const rankMap = state.traversal.typeRanks;
                  const nodes = graph.nodes.map((node) => ({
                    id: node.id,
                    type: node.type,
                    status: node.status,
                    label: node.label,
                    statusRank: statusValues.indexOf(node.status),
                    typeRank: rankMap[node.type] ?? 99,
                  }));
                  const expected = nodes.slice().sort((left, right) =>
                    left.statusRank - right.statusRank ||
                    left.typeRank - right.typeRank ||
                    String(left.type).localeCompare(String(right.type)) ||
                    String(left.label).localeCompare(String(right.label))
                  );
                  const startLevel = document.querySelector('[data-relationship-projection-level="0"]');
                  const startAll = startLevel && startLevel.querySelector("[data-relationship-projection-all]");
                  const startAllDisabledInPlainList = Boolean(startAll && startAll.disabled);
                  const failChipBeforeAllNone = browser.querySelector('[data-relationship-status-value="fail"]');
                  if (failChipBeforeAllNone) failChipBeforeAllNone.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  if (startAll && startAll.checked) startAll.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  for (const level of Array.from(document.querySelectorAll("[data-relationship-projection-level]"))) {
                    const checkbox = level.querySelector("[data-relationship-projection-all]");
                    if (checkbox && checkbox.checked) {
                      checkbox.click();
                      await new Promise(resolve => requestAnimationFrame(resolve));
                    }
                  }
                  const plainListVisibleAtAllNone = Boolean(browser.querySelector("[data-relationship-plain-list]"));
                  const statusChipCountAtAllNone = browser.querySelectorAll("[data-relationship-status-value]").length;
                  const domainCheckbox = document.querySelector('[data-relationship-projection-type="domain"]');
                  if (domainCheckbox && !domainCheckbox.checked) domainCheckbox.click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const afterStartNoneState = browser.__relationshipState;
                  const afterStartNoneGraph = afterStartNoneState.visibleGraph;
                  const afterStartNoneTypes = afterStartNoneGraph.nodes.map((node) => node.type);
                  const failChipAfterAllNone = browser.querySelector('[data-relationship-status-value="fail"]');
                  return {
                    pass: JSON.stringify(nodes.map((node) => node.id)) === JSON.stringify(expected.map((node) => node.id)),
                    normalPass: JSON.stringify(normalNodes.map((node) => node.id)) === JSON.stringify(normalExpected.map((node) => node.id)),
                    normalVisualPass,
                    plainListMode: Boolean(state.plainListMode),
                    edges: graph.edges.length,
                    statusValues,
                    startAllDisabledInPlainList,
                    afterStartNonePlainListMode: Boolean(afterStartNoneState.plainListMode),
                    afterStartNoneTypes,
                    plainListVisibleAtAllNone,
                    statusChipCountAtAllNone,
                    failChipEnabledAfterAllNone: Boolean(failChipAfterAllNone && failChipAfterAllNone.getAttribute("aria-pressed") === "true"),
                    normalNodes,
                    normalExpected,
                    nodes,
                    expected,
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("plainListMode"), result)
        self.assertEqual(0, result.get("edges"), result)
        self.assertEqual(["not_failed", "fail"], result.get("statusValues"), result)
        self.assertTrue(result.get("normalPass"), result)
        self.assertTrue(result.get("normalVisualPass"), result)
        self.assertTrue(result.get("pass"), result)
        self.assertFalse(result.get("startAllDisabledInPlainList"), result)
        self.assertTrue(result.get("afterStartNonePlainListMode"), result)
        self.assertNotIn("product", result.get("afterStartNoneTypes"), result)
        self.assertIn("domain", result.get("afterStartNoneTypes"), result)
        self.assertTrue(result.get("plainListVisibleAtAllNone"), result)
        self.assertEqual(0, result.get("statusChipCountAtAllNone"), result)
        self.assertTrue(result.get("failChipEnabledAfterAllNone"), result)

    def test_relationship_pagination_keeps_status_groups_contiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_paginated_status_order_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  document.querySelector("[data-relationship-open]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const browser = document.querySelector("[data-relationship-browser]");
                  const state = browser.__relationshipState;
                  const initialPageCount = state.visibleGraph.pagination.pageCount;
                  const firstPage = state.visibleGraph.nodes.filter((node) => node.id !== state.selectedId).map((node) => node.status);
                  browser.querySelector("[data-relationship-page-next]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const secondPage = state.visibleGraph.nodes.filter((node) => node.id !== state.selectedId).map((node) => node.status);
                  const firstUnknown = firstPage.indexOf("unknown");
                  const lastNotFailed = firstPage.lastIndexOf("not_failed");
                  browser.querySelector('[data-relationship-status-value="unknown"]').click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const unknownChip = browser.querySelector('[data-relationship-status-value="unknown"]');
                  const filteredStatuses = state.visibleGraph.nodes.filter((node) => node.id !== state.selectedId).map((node) => node.status);
                  return {
                    pageCount: initialPageCount,
                    firstPage,
                    secondPage,
                    statusGroupsAreContiguous: lastNotFailed === -1 || firstUnknown === -1 || lastNotFailed < firstUnknown,
                    noNotFailedOnSecondPage: !secondPage.includes("not_failed"),
                    unknownChipVisibleAfterDisable: Boolean(unknownChip),
                    unknownChipOffAfterDisable: Boolean(unknownChip && unknownChip.classList.contains("is-off")),
                    noUnknownAfterDisable: !filteredStatuses.includes("unknown"),
                  };
                })()""",
                await_promise=True,
            )

        self.assertEqual(3, result.get("pageCount"), result)
        self.assertTrue(result.get("statusGroupsAreContiguous"), result)
        self.assertTrue(result.get("noNotFailedOnSecondPage"), result)
        self.assertTrue(result.get("unknownChipVisibleAfterDisable"), result)
        self.assertTrue(result.get("unknownChipOffAfterDisable"), result)
        self.assertTrue(result.get("noUnknownAfterDisable"), result)

    def test_relationship_selection_table_header_does_not_overlap_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(["--report-json", str(report_json), "--output", str(output)])
            self.assertEqual(0, status)

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  document.querySelector("[data-relationship-open]").click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const main = document.querySelector(".relationship-explorer-main");
                  const control = document.querySelector(".relationship-control-bar");
                  const panel = document.querySelector(".relationship-selection-panel");
                  const tableBox = document.querySelector(".relationship-selection-table");
                  const heading = document.querySelector(".relationship-selection-table-head");
                  const header = document.querySelector(".relationship-selection-table thead");
                  const firstRow = document.querySelector(".relationship-selection-table tbody tr");
                  if (!main || !control || !panel || !tableBox || !heading || !header || !firstRow) {
                    return {pass: false, reason: "selection table parts missing"};
                  }
                  panel.scrollIntoView({block: "start"});
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  main.scrollTop += 42;
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const mainRect = main.getBoundingClientRect();
                  const controlRect = control.getBoundingClientRect();
                  const headingRect = heading.getBoundingClientRect();
                  const headerRect = header.getBoundingClientRect();
                  const tableBoxRect = tableBox.getBoundingClientRect();
                  const firstRowRect = firstRow.getBoundingClientRect();
                  const firstCellStyle = getComputedStyle(firstRow.cells[0]);
                  const visibleTableRows = [...document.querySelectorAll(".relationship-selection-table tr")]
                    .map(row => row.getBoundingClientRect())
                    .filter(rect => rect.bottom > mainRect.top && rect.top < mainRect.bottom);
                  const controlOverlapsRows = visibleTableRows.some(rect =>
                    rect.bottom > controlRect.top + 1 && rect.top < controlRect.bottom - 1
                  );
                  const tableBorderCrossesVisibleRows = visibleTableRows.some(rect =>
                    tableBoxRect.bottom > rect.top + 1 && tableBoxRect.bottom < rect.bottom - 1
                  );
                  return {
                    pass: firstRowRect.top >= headerRect.bottom - 1 && !controlOverlapsRows && !tableBorderCrossesVisibleRows,
                    controlPosition: getComputedStyle(control).position,
                    panelAlignContent: getComputedStyle(panel).alignContent,
                    tableAlignSelf: getComputedStyle(tableBox).alignSelf,
                    headingPosition: getComputedStyle(heading).position,
                    headerPosition: getComputedStyle(header).position,
                    mainTop: Math.round(mainRect.top),
                    controlTop: Math.round(controlRect.top),
                    controlBottom: Math.round(controlRect.bottom),
                    tableBottom: Math.round(tableBoxRect.bottom),
                    headingBottom: Math.round(headingRect.bottom),
                    headerBottom: Math.round(headerRect.bottom),
                    firstRowTop: Math.round(firstRowRect.top),
                    firstCellBorderBottom: firstCellStyle.borderBottomWidth,
                    firstCellLineHeight: firstCellStyle.lineHeight,
                    controlOverlapsRows,
                    tableBorderCrossesVisibleRows,
                  };
                })()""",
                await_promise=True,
                viewport={"width": 1440, "height": 720, "deviceScaleFactor": 1, "mobile": False},
            )

        self.assertTrue(result.get("pass"), result)
        self.assertEqual("static", result.get("controlPosition"), result)
        self.assertEqual("start", result.get("panelAlignContent"), result)
        self.assertEqual("start", result.get("tableAlignSelf"), result)
        self.assertEqual("static", result.get("headingPosition"), result)
        self.assertEqual("static", result.get("headerPosition"), result)
        self.assertEqual("0px", result.get("firstCellBorderBottom"), result)


def _generic_report_payload() -> dict[str, object]:
    rows = [{"id": f"row-{index:03d}", "status": "not_failed"} for index in range(1, 80)]
    component_nodes = [
        {
            "id": f"component:{index}",
            "type": "component",
            "label": f"Component {index}",
            "status": "not_failed",
        }
        for index in range(1, 61)
    ]
    component_edges = [
        {"source": "product:test", "target": f"component:{index}", "relation": "contains"}
        for index in range(1, 61)
    ]
    return {
        "title": "Synthetic dashboard",
        "summary_blocks": [{"type": "text", "body": "Synthetic browser smoke report."}],
        "metric_tables": [
            {
                "title": "Metrics",
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "passed", "label": "Passed"},
                ],
                "rows": [
                    {
                        "cells": {
                            "name": {
                                "text": "Components",
                                "graph_view": {
                                    "focus": "product:test",
                                    "types": ["product", "component"],
                                    "target_type": "component",
                                },
                            },
                            "passed": {
                                "text": "60",
                                "status": "not_failed",
                                "graph_view": {
                                    "focus": "product:test",
                                    "types": ["product", "component"],
                                    "target_type": "component",
                                    "filters": {"component": {"status": ["not_failed"]}},
                                },
                            },
                        }
                    }
                ],
            }
        ],
        "tables": [{"title": "Synthetic rows", "columns": ["id", "status"], "rows": rows}],
        "relationship_graph": {
            "title": "Synthetic graph",
            "nodes": [
                {"id": "product:test", "type": "product", "label": "Test product", "status": "not_failed"},
                *component_nodes,
            ],
            "edges": component_edges,
        },
    }


def _plain_search_payload() -> dict[str, object]:
    return {
        "title": "Synthetic search report",
        "summary_blocks": [{"type": "text", "body": "Synthetic relationship search report."}],
        "metric_tables": [
            {
                "title": "Metrics",
                "columns": [{"key": "name", "label": "Name"}],
                "rows": [{"cells": {"name": {"text": "Open graph", "graph_view": {"focus": "product:test"}}}}],
            }
        ],
        "relationship_graph": {
            "title": "Synthetic graph",
            "nodes": [
                {"id": "product:test", "type": "product", "label": "Test product", "status": "not_failed"},
                {
                    "id": "cdd:audio",
                    "type": "cdd",
                    "label": "CDD · Android audio routing",
                    "status": "fail",
                    "summary": "Synthetic audio behavior requirement.",
                },
            ],
            "edges": [{"source": "product:test", "target": "cdd:audio", "relation": "contains"}],
        },
    }


def _plain_list_order_payload() -> dict[str, object]:
    nodes = [
        {"id": "vsr:gamma", "type": "vsr", "label": "Gamma VSR", "status": "fail"},
        {"id": "domain:beta", "type": "domain", "label": "Beta domain", "status": "not_failed"},
        {"id": "cdd:alpha", "type": "cdd", "label": "Alpha CDD", "status": "fail"},
        {"id": "domain:alpha", "type": "domain", "label": "Alpha domain", "status": "fail"},
        {"id": "vsr:alpha", "type": "vsr", "label": "Alpha VSR", "status": "not_failed"},
        {"id": "product:test", "type": "product", "label": "Test product", "status": "not_failed"},
        {"id": "cdd:beta", "type": "cdd", "label": "Beta CDD", "status": "not_failed"},
        {"id": "domain:gamma", "type": "domain", "label": "Gamma domain", "status": "fail"},
    ]
    return {
        "title": "Synthetic plain list report",
        "summary_blocks": [{"type": "text", "body": "Synthetic plain list sorting report."}],
        "metric_tables": [
            {
                "title": "Metrics",
                "columns": [{"key": "name", "label": "Name"}],
                "rows": [{"cells": {"name": {"text": "Open graph", "graph_view": {"focus": "product:test"}}}}],
            }
        ],
        "relationship_graph": {
            "title": "Synthetic graph",
            "traversal": {"type_ranks": {"product": 0, "domain": 1, "cdd": 2, "vsr": 3}},
            "status_order": ["not_failed", "fail"],
            "nodes": nodes,
            "edges": [
                {"source": "product:test", "target": node["id"], "relation": "contains"}
                for node in nodes
                if node["id"] != "product:test"
            ],
        },
    }


def _paginated_status_order_payload() -> dict[str, object]:
    unknown_nodes = [
        {"id": f"cdd:{index:03d}", "type": "cdd", "label": f"CDD {index:03d}", "status": "unknown"}
        for index in range(1, 56)
    ]
    not_failed_nodes = [
        {"id": f"cts:{index:03d}", "type": "cts_module", "label": f"CTS {index:03d}", "status": "not_failed"}
        for index in range(1, 21)
    ]
    nodes = [
        {"id": "product:test", "type": "product", "label": "Test product", "status": "not_failed"},
        *unknown_nodes,
        *not_failed_nodes,
    ]
    return {
        "title": "Synthetic paginated status report",
        "summary_blocks": [{"type": "text", "body": "Synthetic pagination status sorting report."}],
        "metric_tables": [
            {
                "title": "Metrics",
                "columns": [{"key": "name", "label": "Name"}],
                "rows": [{"cells": {"name": {"text": "Open graph", "graph_view": {"focus": "product:test"}}}}],
            }
        ],
        "relationship_graph": {
            "title": "Synthetic graph",
            "traversal": {"type_ranks": {"product": 0, "cdd": 1, "cts_module": 2}},
            "status_order": ["not_failed", "unknown"],
            "nodes": nodes,
            "edges": [
                {"source": "product:test", "target": node["id"], "relation": "contains"}
                for node in nodes
                if node["id"] != "product:test"
            ],
        },
    }


def _story_comments() -> dict[str, object]:
    return {
        "summary": "Synthetic story scroll report.",
        "diagrams": {
            "flow": {
                "title": "Synthetic flow",
                "svg_inline": (
                    '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120" '
                    'viewBox="0 0 240 120"><rect x="24" y="24" width="192" height="72" '
                    'rx="8" fill="#eef6ff" stroke="#0969da"/><text x="120" y="68" '
                    'font-size="18" text-anchor="middle">Synthetic flow</text></svg>'
                ),
            }
        },
        "inline": [
            {
                "file": "src/demo.c",
                "line": 120,
                "title": "Late line",
                "body": "This comment forces a long page.",
            }
        ],
        "story": [
            {"title": "Top", "body": "Start at the file.", "file": "src/demo.c"},
            {
                "title": "Late comment",
                "body": "Jump near the end.",
                "comment": {"file": "src/demo.c", "line": 120},
                "diagram": "flow",
            },
        ],
    }


def _long_diff() -> str:
    added_lines = "\n".join(f"+int demo_{index:03d}(void) {{ return {index}; }}" for index in range(1, 181))
    return (
        "diff --git a/src/demo.c b/src/demo.c\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/src/demo.c\n"
        "@@ -0,0 +1,180 @@\n"
        f"{added_lines}\n"
    )


def _evaluate_in_browser(
    html: Path,
    expression: str,
    *,
    await_promise: bool = False,
    viewport: dict[str, object] | None = None,
) -> object:
    browser = _browser()
    if not browser:
        raise unittest.SkipTest("Chrome-compatible browser is not available")
    profile_dir = Path(tempfile.mkdtemp(prefix="diff-report-browser-test-"))
    process = subprocess.Popen(
        [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-crash-reporter",
            "--disable-crashpad",
            f"--user-data-dir={profile_dir}",
            "--remote-debugging-port=0",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        port = _wait_for_debug_port(profile_dir)
        targets = _browser_json(port, "/json/list")
        target = next(item for item in targets if isinstance(item, dict) and item.get("type") == "page")
        with _CdpConnection(target["webSocketDebuggerUrl"]) as cdp:
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call(
                "Emulation.setDeviceMetricsOverride",
                viewport or {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False},
            )
            cdp.call("Page.navigate", {"url": html.resolve().as_uri()})
            _wait_for_page_ready(cdp)
            result = cdp.call(
                "Runtime.evaluate",
                {"expression": expression, "awaitPromise": await_promise, "returnByValue": True},
            )
            value = result.get("result", {}).get("result", {})
            if value.get("subtype") == "error":
                raise AssertionError(value.get("description") or value)
            return value.get("value")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        shutil.rmtree(profile_dir, ignore_errors=True)


def _wait_for_page_ready(cdp: "_CdpConnection") -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = cdp.call("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
        if response.get("result", {}).get("result", {}).get("value") == "complete":
            return
        time.sleep(0.05)
    raise RuntimeError("page did not finish loading")


def _wait_for_debug_port(profile_dir: Path) -> int:
    port_file = profile_dir / "DevToolsActivePort"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if port_file.is_file():
            return int(port_file.read_text(encoding="utf-8").splitlines()[0])
        time.sleep(0.05)
    raise RuntimeError("Chrome DevTools port file was not created")


def _browser_json(port: int, path: str) -> object:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class _CdpConnection:
    def __init__(self, websocket_url: str) -> None:
        prefix = "ws://"
        if not websocket_url.startswith(prefix):
            raise ValueError(f"unsupported DevTools websocket URL: {websocket_url}")
        host_port, self.path = websocket_url[len(prefix) :].split("/", 1)
        self.path = "/" + self.path
        self.host, port = host_port.split(":", 1)
        self.port = int(port)
        self.sock: socket.socket | None = None
        self.next_id = 1

    def __enter__(self) -> "_CdpConnection":
        raw = socket.create_connection((self.host, self.port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        raw.sendall(request.encode("ascii"))
        response = raw.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raw.close()
            raise RuntimeError("DevTools websocket handshake failed")
        self.sock = raw
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        message_id = self.next_id
        self.next_id += 1
        self._send_json({"id": message_id, "method": method, "params": params or {}})
        while True:
            message = self._recv_json()
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message

    def _send_json(self, payload: dict[str, object]) -> None:
        self._send_frame(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _recv_json(self) -> dict[str, object]:
        while True:
            opcode, payload = self._recv_frame()
            if opcode == 1:
                return json.loads(payload.decode("utf-8"))
            if opcode == 9:
                self._send_frame(payload, opcode=10)

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126])
            header.extend(struct.pack("!H", length))
        else:
            header.extend([0x80 | 127])
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_frame(self) -> tuple[int, bytes]:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        first, second = self._read_exact(2)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise RuntimeError("websocket closed")
            chunks.extend(chunk)
        return bytes(chunks)
