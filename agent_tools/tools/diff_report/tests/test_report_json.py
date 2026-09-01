from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from agent_tools.tools.diff_report.models import DiffReportError
from agent_tools.tools.diff_report.report_json import (
    render_report_json_html,
    report_from_payload,
)


class ReportJsonTests(unittest.TestCase):
    def test_renders_dashboard_widgets_and_shared_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_path = root / "status.log"
            log_path.write_text("security risk\ncts pending\n", encoding="utf-8")
            payload = {
                "title": "Gen5 CDD/VSR Dashboard",
                "summary_blocks": [
                    {"type": "text", "body": "Current focus is security."},
                    {"type": "diagram", "diagram": "flow", "diagram_focus": "VSR"},
                    {"type": "log", "log": "status", "log_focus": "risk"},
                ],
                "metrics": [
                    {"label": "VSR rows", "value": 115, "status": "covered_candidate"},
                    {"label": "Risks", "value": 4, "status": "risk", "note": "Security first pass"},
                ],
                "status_cards": {
                    "title": "Processing progress",
                    "note": "AI processing status of the analysis pipeline.",
                    "cards": [
                        {
                            "title": "security",
                            "status": "risk",
                            "body": "SELinux and KeyMint need production evidence.",
                            "metric_tables": [
                                {
                                    "columns": [
                                        {"key": "metric", "label": "Metric"},
                                        {"key": "available", "label": "available"},
                                        {"key": "overall", "label": "overall"},
                                    ],
                                    "rows": [
                                        {
                                            "cells": {
                                                "metric": {
                                                    "text": "CTS->CDD/VSR candidates",
                                                    "graph_view": {
                                                        "focus": "product:gen5",
                                                        "types": ["product", "cts_module"],
                                                        "target_type": "cts_module",
                                                    },
                                                },
                                                "available": {
                                                    "text": "129 (11.5%)",
                                                    "status": "covered_candidate",
                                                    "graph_view": {
                                                        "focus": "product:gen5",
                                                        "types": ["product", "cts_module"],
                                                        "target_type": "cts_module",
                                                        "filters": {"cts_module": {"status": ["covered_candidate"]}},
                                                    },
                                                },
                                                "overall": {
                                                    "text": "1119",
                                                    "graph_view": {
                                                        "focus": "product:gen5",
                                                        "types": ["product", "cts_module"],
                                                        "target_type": "cts_module",
                                                    },
                                                },
                                            }
                                        }
                                    ],
                                }
                            ],
                            "metrics": [
                                {
                                    "label": "candidate coverage",
                                    "value": "129 (11.5%) / 990 (88.5%) / 1119",
                                    "parts": [
                                        {"label": "available", "value": "129 (11.5%)", "status": "covered_candidate"},
                                        {"label": "not available", "value": "990 (88.5%)", "status": "unknown"},
                                        {"label": "overall", "value": "1119", "status": "unknown"},
                                    ],
                                }
                            ],
                            "links": [{"label": "Security pass", "href": "../domains/security/VSR_SECURITY_PASS.md"}],
                        }
                    ],
                },
                "heatmaps": [
                    {
                        "title": "Domain Heatmap",
                        "rows": [
                            {"domain": "security", "status": "risk", "total": 10},
                            {"domain": "storage_update", "status": "covered_candidate", "total": 4},
                        ],
                    }
                ],
                "tables": [
                    {
                        "title": "Requirement Queue",
                        "columns": ["id", "domain", "status", "evidence"],
                        "rows": [
                            {
                                "id": "VSR-3.10-023",
                                "domain": "security",
                                "status": "risk",
                                "evidence": {"text": "Open diagram", "diagram": "flow"},
                            }
                        ],
                    }
                ],
                "timeline": [
                    {"time": "2026-08-17", "title": "Security pass created", "status": "risk"}
                ],
                "relationship_graph": {
                    "title": "Requirement Traceability",
                    "status_order": ["risk", "unknown"],
                    "traversal": {
                        "terminal_types": ["cdd", "test", "artifact"],
                        "pass_through_types": ["domain", "vsr", "hal"],
                        "edge_direction": "both",
                        "relation_traversal": {"domain_has_test_result": "fallback"},
                    },
                    "nodes": [
                        {
                            "id": "vsr:VSR-1",
                            "type": "vsr",
                            "label": "AIDL for HALs",
                            "status": "risk",
                            "summary": "HALs must use AIDL.",
                            "details": {"current_status": "HIDL remains."},
                        },
                        {
                            "id": "hal:audio@6.0",
                            "type": "hal",
                            "label": "audio@6.0",
                            "status": "risk",
                        },
                    ],
                    "edges": [
                        {
                            "source": "vsr:VSR-1",
                            "target": "hal:audio@6.0",
                            "relation": "maps_to_hal",
                        }
                    ],
                },
                "artifacts": [
                    {
                        "title": "Product architecture",
                        "path": "../analysis/product/architecture/PRODUCT_ARCHITECTURE.md",
                        "kind": "markdown",
                        "note": "evidence",
                    }
                ],
                "diagrams": {
                    "flow": {
                        "title": "Requirement flow",
                        "svg_inline": "<svg xmlns='http://www.w3.org/2000/svg'><text>VSR</text></svg>",
                    }
                },
                "logs": {"status": {"title": "Status log", "path": "status.log"}},
                "story": [
                    {
                        "title": "Start with security",
                        "body": "This is the highest-risk domain.",
                        "diagram": "flow",
                    }
                ],
            }

            report = report_from_payload(payload, base_dir=root)
            html = render_report_json_html(report)

        expected = [
            "<h1>Gen5 CDD/VSR Dashboard</h1>",
            "Current focus is security.",
            "report-metric-grid",
            "VSR rows",
            "Security first pass",
            "report-card status-risk",
            "<h2>Processing progress</h2>",
            "report-status-cards-note",
            "report-card-metric-parts",
            "report-card-metric-part status-covered-candidate",
            "available",
            "129 (11.5%)",
            "report-card-table",
            "<th>available</th>",
            "CTS-&gt;CDD/VSR candidates",
            "&quot;target_type&quot;: &quot;cts_module&quot;",
            "AI processing status of the analysis pipeline.",
            '<a href="#report-status-cards">Processing progress</a>',
            "SELinux and KeyMint need production evidence.",
            "Domain Heatmap",
            "report-heatmap-cell status-risk",
            "Requirement Queue",
            'data-report-table-filter="report-table-1"',
            "VSR-3.10-023",
            "Security pass created",
            "Requirement Traceability",
            'id="report-relationship-graph"',
            'data-relationship-browser',
            'data-relationship-defer',
            'data-relationship-open',
            'data-relationship-modal',
            'data-relationship-close',
            'data-relationship-graph-data',
            "relationship-selection-table",
            "data-relationship-selection-body",
            "data-relationship-selection-count",
            "relationship-preview",
            'data-relationship-projection-controls',
            'data-relationship-projection-levels',
            "relationship-control-label",
            'data-relationship-fit',
            "AIDL for HALs",
            "maps_to_hal",
            "The Cytoscape Consortium",
            "cytoscape({",
            "wheelSensitivity",
            "function fitGraph(state, padding)",
            "function setGraphInteractive(browser, state, interactive)",
            "state.cy.userZoomingEnabled(state.graphInteractive);",
            'canvas.setAttribute("data-graph-interactive", state.graphInteractive ? "true" : "false");',
            "function graphTypes(nodes)",
            "function selectableNodes(state, includeSelected, degrees)",
            "function searchMatcher(state)",
            "function nodeSearchText(node, state, degrees)",
            "function renderSearchResults(browser, state, degrees)",
            "function focusChoiceRank(node, state)",
            "function focusChoiceGroupKey(node, state, degrees)",
            "function focusChoiceGroupLabel(node, state, degrees, count)",
            "function childLayerSubfilterTypes(state)",
            "function visibleNodeDegreeMap(state)",
            "function visibleNodeDegree(node, state, degrees)",
            "function applySearchUpdate(browser, state, selectFirstMatch)",
            "function scheduleSearchUpdate(browser, state, selectFirstMatch)",
            "MAX_FOCUS_OPTIONS",
            "function graphRenderSignature(graph)",
            "function buildAdjacency(edges)",
            "canvas.replaceChildren();",
            "canvasViewportListenersAttached",
            "function detailFieldLabel(key)",
            "function orderedDetailRows(node, details)",
            'requirement_text: "Description"',
            "Source CDD text is not available for this graph node.",
            "function updateActiveGraphNode(state)",
            "function activateNode(browser, state, nodeId)",
            "function focusRequiredTypes(state, nodeId)",
            "function focusHasSecondaryLinks(state)",
            "function updateSecondaryLinkControl(browser, state)",
            "function ensureFocusFilters(browser, state, nodeId)",
            "function projectionRankGroups(state)",
            "function projectionTypesFromSelections(state)",
            "function setProjectionSelectionsFromTypes(state, types)",
            "function applyProjectionSelections(browser, state)",
            "function focusViewTypes(state, nodeId)",
            "function resetEntityTypesToFocusView(browser, state, nodeId)",
            "function enableAllEntityTypes(browser, state)",
            "function resetGraphFilters(browser, state)",
            "function resetGraphFiltersToAll(browser, state)",
            "function allEntityTypesEnabled(state)",
            "function navigationSnapshot(state)",
            "function serializeSubfilters(state)",
            "function restoreSubfilters(state, snapshot)",
            "function restoreNavigationSnapshot(browser, state, snapshot)",
            "function pushNavigationSnapshot(state)",
            "state.backStack.push(navigationSnapshot(state));",
            "state.forwardStack.push(navigationSnapshot(state));",
            "function selectTableNode(browser, state, nodeId)",
            "const resetTypes = Boolean(options && options.resetTypes);",
            'Object.prototype.hasOwnProperty.call(options, "preserveTypes")',
            '(state.projectionMode || "auto") === "custom"',
            "if (resetTypes) {",
            "enableAllEntityTypes(browser, state);",
            "resetEntityTypesToFocusView(browser, state, nodeId);",
            'selectTableNode(browser, state, tableRow.getAttribute("data-relationship-table-node"));',
            "state.visibleNodeIds = new Set(graph.nodes.map((node) => node.id));",
            "function renderSelectionTable(browser, state)",
            "function visibleGraphDegree(nodeId, graph)",
            "badge.className = `report-status-badge ${cssStatus(value.status)}`;",
            "function renderNodeSelect(browser, state)",
            'if (targetType && (node.type || "entity") === targetType) return 3;',
            'return `${nodeTypeLabel(node)} · focus target ${suffix}`;',
            "function refreshTypeFilterState(container, state, types)",
            "function renderSubfilterPopover(container, state)",
            "data-relationship-subfilter-popover",
            "function projectionSelectedTypesForGroup(state, group)",
            "function setProjectionGroupSelection(state, group, selected)",
            "function syncActiveSubfilterType(state)",
            "relationship-subfilter-popover",
            "filterDefaults: graph.filterDefaults || {}",
            "function searchMatcher(state)",
            "function renderSearchResults(browser, state, degrees)",
            "function singleEnabledType(state)",
            "function buildTypeListGraph(state)",
            "function buildPlainListGraph(state)",
            "listMode: true",
            "function graphSourceSignature(state)",
            "function focusGraphForState(state, nodeVisible, contextNodeVisible, graphEdges, graphAdjacency)",
            "state.focusGraphCache = {signature: sourceSignature, graph};",
            "const contextNodeVisible = (node) => nodeInScope(state, node);",
            "const visibleChildRank = Math.min(...candidateDescendants.map((id) => rankOf(nodesById.get(id))));",
            "const shownDescendants = candidateDescendants.filter((id) => rankOf(nodesById.get(id)) === visibleChildRank);",
            "nodeVisible(node) || (ancestry.has(id) && contextNodeVisible(node))",
            "contextIds: new Set(ancestry)",
            "const contextIds = graph.contextIds || new Set(selectedNode ? [selectedId] : []);",
            "const nodes = graph.listMode && !graph.stickyContext ? pageNodes : contextNodes.concat(pageNodes);",
            "function statusChipScopeGraphForState(state)",
            "is-list-item",
            "function buildHierarchicalLayout(nodes, width, height, selectedId, traversal, compareNodes)",
            "const columnCounts = rows.map((row) => Math.max(1, Math.ceil(Math.sqrt(row.nodes.length))));",
            "const colIndex = index % cols;",
            "const rowIndex = Math.floor(index / cols);",
            "rankTop += Math.max(0, rowSpan - 1) * rowHeight + rankGap;",
            "function hierarchyNodePosition(node, graph)",
            "return position ? {x: position.x, y: position.y} : undefined;",
            "function listNodePosition(index, graph, node)",
            "position: graph.listMode ? listNodePosition(index, graph, node) : hierarchyNodePosition(node, graph)",
            "graph.listLayout = {",
            "graph.hierarchyLayout = buildHierarchicalLayout(",
            "positions: (node) => presetPositions.get(node.id()) || {x: 0, y: 0}",
            "if (position) node.position(position);",
            'name: "preset"',
            "listMode: graph.listMode",
            "function capGraph(graph, state, limit, page)",
            'browser.querySelectorAll("[data-relationship-page-controls]").forEach((controls) => {',
            'browser.querySelectorAll("[data-relationship-page-prev]").forEach((pagePrev) => {',
            'browser.querySelectorAll("[data-relationship-page-next]").forEach((pageNext) => {',
            "function traversalConfig(rawTraversal)",
            "function activeTraversal(state)",
            "DEFAULT_TYPE_RANKS",
            "type_ranks",
            "focused_context",
            "DEFAULT_TERMINAL_TYPES",
            "terminal_types",
            "pass_through_types",
            "edge_direction",
            "relation_traversal",
            "relationTraversal",
            "function renderFailureStats(stats)",
            "data-relationship-status-filter",
            "function createStatusFilter(nodes, defaults, statusOrder)",
            '"status_order"',
            "function serializeStatusFilter(state)",
            "function restoreStatusFilter(state, snapshot)",
            "function statusFilterValues(state)",
            "function isStatusValueEnabled(state, value)",
            "function setStatusValueEnabled(state, value, enabled)",
            "function renderStatusFilter(browser, state)",
            "data-relationship-status-value",
            "data-relationship-status-all",
            "relationship-status-all",
            "allCheckbox.indeterminate = enabledCount > 0 && enabledCount < values.length;",
            "relationship-status-chip",
            "data-relationship-search-help",
            "data-relationship-search-help-popover",
            "data-relationship-search-regex",
            "data-relationship-search-results",
            "data-relationship-plain-list",
            "state.plainListMode",
            "browser.__relationshipSelectNode",
            "relationship-search-result",
            "relationship-search-status",
            "highlightSearchMatch(item.label, item.displayMatch)",
            "function graphRootId(state)",
            "if (!value) continue;",
            "if (selectedId && node.id === selectedId) return true;",
            "function focusContent(state)",
            "function traversalRank(state, node)",
            "state.searchRegex",
            "function focusCandidateLabel(node, state, degrees)",
            "function clearSearch(browser, state)",
            "function typeNodeCount(state, type)",
            "function typeFocusTotal(state, type)",
            "function hiddenByFiltersCount(state)",
            "Only the focus is drawn:",
            "function activeFilterCount(state)",
            "data-relationship-projection-level",
            "relationship-control-bar",
            "label.hidden = !available;",
            "Failed Test Statistics",
            "function openRelationshipFocus(trigger, nodeId)",
            'document.querySelectorAll("[data-relationship-open-focus]")',
            "selectTableNode(browser, state, nodeId);",
            "function openRelationshipModal(modal, options)",
            "resetGraphFiltersToAll(browser, state);",
            "function closeRelationshipModal(modal)",
            "enabledTypes: new Set()",
            "state.enabledTypes = new Set(stateGraphTypes(state));",
            "graphInteractive: false",
            'canvas.addEventListener("pointerdown"',
            'browser.addEventListener(eventName, routeGraphFocusEvent, {capture: true});',
            "function releaseGraphFocus(browser, state)",
            'detail.addEventListener("pointerdown", releaseFromDetail, {capture: true, passive: true});',
            'detail.addEventListener("scroll", releaseFromDetail, {passive: true});',
            'browser.addEventListener("wheel", releaseFromBrowserDetail, {capture: true, passive: true});',
            'explorer.addEventListener("scroll", handleExplorerScroll, {passive: true});',
            'setGraphInteractive(browser, state, false);',
            "search.addEventListener(\"keydown\"",
            "selectNode(browser, state, matches[0].id, false)",
            'state.cy.on("tap", "node", (event) => {',
            "selectNode(browser, state, nodeId, true)",
            "data-relationship-table-node",
            '"outline-color": link',
            'const includeSelected = !String(state.searchQuery || "").trim();',
            "canvas.setAttribute(\"data-empty-graph\", \"true\")",
            "No entity types selected.",
            "relationship-projection-levels",
            "relationship-option-isolated",
            "no visible links",
            "isolated",
            'aria-label="Back">←</button>',
            'aria-label="Forward">→</button>',
            "document.body.classList.add(\"relationship-modal-open\")",
            'document.querySelectorAll("[data-relationship-browser]:not([data-relationship-defer])").forEach(initBrowser);',
            "Product architecture",
            'data-diagram-id="flow"',
            'id="diagram-template-flow"',
            'id="log-template-status"',
            "security risk",
            'data-story-diagram="flow"',
            "report-settings-launcher",
            '<nav class="report-toc"',
            '<a href="#report-table-1">Requirement Queue</a>',
            'id="report-top"',
            'id="summary-section"',
            'id="report-metrics"',
            'id="report-status-cards"',
            'id="report-heatmaps"',
            'id="report-timeline"',
            'id="report-relationship-graph"',
            'id="report-artifacts"',
            'id="report-diagrams"',
            'id="report-logs"',
            'document.addEventListener("click", (event) => {',
            "function setActiveToc(id, reveal)",
            "function currentReadableTocId()",
            "const probeY = 112;",
            "if (rect.top > probeY)",
            'entry.link.setAttribute("aria-current", "location");',
            'window.addEventListener("scroll", scheduleActiveTocUpdate, {passive: true});',
            'let pendingTocId = "";',
            "if (pendingTocId) {",
            'document.documentElement.dataset.tocLockUntil = String(Date.now() + 1800);',
            'setActiveToc(id, true);',
            'target.scrollIntoView({block: "start", inline: "nearest"});',
            "function isSecondaryEdge(edge)",
            "function isFallbackTraversalEdge(edge, traversal)",
            "function buildNeighborhood(selectedId, nodesById, edges, adjacency, nodeVisible, contextNodeVisible, traversal, includeSecondaryLinks)",
            "regularCandidates.length",
            "fallbackDescendants.length",
            "const shownDescendants = candidateDescendants.filter((id) => rankOf(nodesById.get(id)) === visibleChildRank);",
            "data-relationship-secondary-links",
            "Shortcuts",
            "data-relationship-page-controls",
            "data-relationship-page-prev",
            "data-relationship-page-next",
            "function updateGraphPageControls(browser, state, pagination)",
            "capGraph(focusGraph, state, 25, state.graphPage)",
            "const visibleGraph = state.visibleGraph || {edges: []};",
            "const traversedEdgeKeys = new Set();",
            "const traversedEdgesByKey = new Map();",
            "const visibleEdges = Array.from(traversedEdgesByKey.values()).filter((edge) => {",
            "data-relationship-jump",
            "data-relationship-jump-visible",
            "focus to show",
        ]
        for fragment in expected:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)
        self.assertNotIn('data-relationship-projection-auto', html)
        self.assertNotIn(">Auto</span>", html)
        self.assertNotIn("relationship-projection-auto", html)

    def test_validates_widget_shapes(self) -> None:
        invalid_payloads = [
            ({"title": "Broken", "metrics": {}}, "report.metrics must be a list"),
            (
                {"title": "Broken", "status_cards": {"title": 5, "cards": []}},
                "report.status_cards.title must be a string",
            ),
            (
                {"title": "Broken", "status_cards": [{"status": "risk"}]},
                "report.status_cards[0].title is required",
            ),
            (
                {
                    "title": "Broken",
                    "status_cards": [{"title": "bad", "metrics": [{"label": "rows", "parts": "bad"}]}],
                },
                "report.metrics[0].parts must be a list",
            ),
            (
                {
                    "title": "Broken",
                    "status_cards": [{"title": "bad", "metric_tables": {"columns": [], "rows": []}}],
                },
                "report.status_cards[0].metric_tables[0].columns must contain at least one column",
            ),
            (
                {"title": "Broken", "tables": [{"columns": [], "rows": []}]},
                "report.tables[0].columns must be a non-empty list",
            ),
            ({"title": "Broken", "timeline": ["bad"]}, "report.timeline[0] must be an object"),
            ({"title": "Broken", "toc_groups": {}}, "report.toc_groups must be a list"),
            (
                {"title": "Broken", "toc_groups": [{"title": "Overview", "items": []}]},
                "report.toc_groups[0].items must be a non-empty list",
            ),
            (
                {"title": "Broken", "toc_groups": [{"title": "Overview", "items": [{"label": "Top", "href": "top"}]}]},
                "report.toc_groups[0].items[0].href must start with #",
            ),
            ({"title": "Broken", "relationship_graph": []}, "report.relationship_graph must be an object"),
            (
                {"title": "Broken", "relationship_graph": {"nodes": [], "edges": []}},
                "report.relationship_graph.nodes must be a non-empty list",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [{"source": "a", "target": "missing"}],
                    },
                },
                "report.relationship_graph.edges[0].target references missing node missing",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [],
                        "status_order": "risk",
                    },
                },
                "report.relationship_graph.status_order must be a string list",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [],
                        "traversal": {"terminal_types": "cdd"},
                    },
                },
                "report.relationship_graph.traversal.terminal_types must be a string list",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [],
                        "traversal": {"edge_direction": "sideways"},
                    },
                },
                "report.relationship_graph.traversal.edge_direction must be both, forward, reverse, or focused_context",
            ),
            (
                {
                    "title": "Broken",
                    "relationship_graph": {
                        "nodes": [{"id": "a", "label": "A"}],
                        "edges": [],
                        "traversal": {"relation_traversal": {"related_to": "sideways"}},
                    },
                },
                "report.relationship_graph.traversal.relation_traversal values must be both, forward, reverse, none, or fallback",
            ),
        ]
        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DiffReportError, re.escape(message)):
                    report_from_payload(payload)

    def test_renders_metric_tables_with_graph_views(self) -> None:
        payload = {
            "title": "Dashboard",
            "metric_tables": [
                {
                    "title": "Metrics",
                    "note": "Passed and failed items per entity type.",
                    "columns": [
                        {"key": "name", "label": "Name"},
                        {"key": "passed", "label": "Passed items"},
                        {"key": "failed", "label": "Failed items"},
                    ],
                    "rows": [
                        {
                            "cells": {
                                "name": {
                                    "text": "CDD",
                                    "graph_view": {
                                        "focus": "product:gen5",
                                        "types": ["product", "cdd"],
                                        "target_type": "cdd",
                                        "label": "Product to CDD",
                                    },
                                },
                                "passed": {
                                    "text": "12 · 10.4%",
                                    "status": "pass",
                                    "graph_view": {
                                        "focus": "product:gen5",
                                        "types": ["product", "cdd"],
                                        "target_type": "cdd",
                                        "filters": {"cdd": {"status": ["covered_candidate"]}},
                                    },
                                },
                                "failed": {"text": "0 · 0.0%", "status": "fail", "note": "no reviewed gap"},
                            }
                        }
                    ],
                },
                {
                    "title": "Per domain metrics",
                    "columns": ["name", {"key": "cdd_passed", "label": "CDD", "sublabel": "passed · failed"}],
                    "rows": [{"cells": {"name": "graphics", "cdd_passed": 4}}],
                },
                {
                    "title": "Custom scopes",
                    "columns": ["name", "status"],
                    "rows": [{"cells": {"name": "Security review", "status": "open"}}],
                },
            ],
            "relationship_graph": {
                "title": "Traceability",
                "nodes": [
                    {"id": "product:gen5", "type": "product", "label": "Gen5"},
                    {"id": "cdd:1", "type": "cdd", "label": "CDD 1", "status": "covered_candidate"},
                ],
                "edges": [{"source": "product:gen5", "target": "cdd:1", "relation": "product_contains_cdd"}],
            },
        }

        html = render_report_json_html(report_from_payload(payload))

        expected = [
            'id="report-metric-tables"',
            'id="report-metric-table-2"',
            'id="report-metric-table-3"',
            "report-metric-table-note",
            "Passed and failed items per entity type.",
            "<th>Passed items</th>",
            '<small class="report-metric-table-sublabel">passed · failed</small>',
            "report-metric-table-sublabel",
            '<th scope="row">',
            'class="status-pass"',
            "report-metric-cell-link",
            "data-relationship-open-view=",
            "&quot;focus&quot;: &quot;product:gen5&quot;",
            "&quot;target_type&quot;: &quot;cdd&quot;",
            "report-metric-cell-note",
            "<a href=\"#report-metric-tables\">Metrics</a>",
            "<a href=\"#report-metric-table-2\">Per domain metrics</a>",
            "<a href=\"#report-metric-table-3\">Custom scopes</a>",
            "function applyRelationshipViewFilters(state, filters)",
            "function applyRelationshipView(browser, state, view)",
            "updateSelectedNodeState(browser, state, focusId, false, {preserveTypes: true, preserveFilters: true, preservePlainList: Boolean(view.plain_list)});",
            "function openRelationshipView(trigger, view)",
            'document.querySelectorAll("[data-relationship-open-view]")',
            "state.typeSearchType = targetType;",
            "relationship-preview-row",
            "<button type=\"button\" title=\"Open graph for cdd\" data-relationship-open-view=",
            "&quot;types&quot;: [&quot;product&quot;, &quot;cdd&quot;]",
            "<button type=\"button\" class=\"status-covered-candidate\" title=\"Open graph for covered_candidate\" data-relationship-open-view=",
            "&quot;filters&quot;: {&quot;cdd&quot;: {&quot;status&quot;: [&quot;covered_candidate&quot;]}}",
        ]
        for fragment in expected:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)
        self.assertIn(">graphics<", html)
        self.assertIn(">4<", html)
        graph_index = html.index('<section class="report-relationship-section" id="report-relationship-graph"')
        metrics_index = html.index('<section class="report-metric-table-section" id="report-metric-tables"')
        per_domain_index = html.index('<section class="report-metric-table-section" id="report-metric-table-2"')
        custom_scopes_index = html.index('<section class="report-metric-table-section" id="report-metric-table-3"')
        self.assertLess(graph_index, metrics_index)
        self.assertLess(metrics_index, per_domain_index)
        self.assertLess(per_domain_index, custom_scopes_index)

    def test_validates_metric_table_shapes(self) -> None:
        invalid_payloads = [
            ({"title": "Broken", "metric_tables": "x"}, "report.metric_tables must be a list"),
            (
                {"title": "Broken", "metric_tables": [{"title": "M", "columns": []}]},
                "report.metric_tables[0].columns must contain at least one column",
            ),
            (
                {"title": "Broken", "metric_tables": [{"columns": ["name"], "rows": ["bad"]}]},
                "report.metric_tables[0].rows[0] must be an object",
            ),
            (
                {
                    "title": "Broken",
                    "metric_tables": [
                        {"columns": ["name"], "rows": [{"cells": {"name": {"graph_view": {"types": ["cdd"]}}}}]}
                    ],
                },
                "report.metric_tables[0].rows[0].cells.name.graph_view.focus is required",
            ),
            (
                {
                    "title": "Broken",
                    "metric_tables": [
                        {
                            "columns": ["name"],
                            "rows": [{"cells": {"name": {"graph_view": {"focus": "a", "types": "cdd"}}}}],
                        }
                    ],
                },
                "report.metric_tables[0].rows[0].cells.name.graph_view.types must be a string list",
            ),
            (
                {
                    "title": "Broken",
                    "metric_tables": [
                        {
                            "columns": ["name"],
                            "rows": [
                                {
                                    "cells": {
                                        "name": {
                                            "graph_view": {"focus": "a", "filters": {"cdd": {"status": "pass"}}}
                                        }
                                    }
                                }
                            ],
                        }
                    ],
                },
                "report.metric_tables[0].rows[0].cells.name.graph_view.filters.cdd.status must be a string list",
            ),
        ]
        for payload, message in invalid_payloads:
            with self.subTest(message=message):
                with self.assertRaisesRegex(DiffReportError, re.escape(message)):
                    report_from_payload(payload)

    def test_renders_grouped_toc_when_requested(self) -> None:
        payload = {
            "title": "Dashboard",
            "metrics": [{"label": "Risks", "value": 2}],
            "tables": [
                {"title": "Top Blockers", "columns": ["domain"], "rows": [{"domain": "security"}]},
                {"title": "Security VSR Rows", "columns": ["id"], "rows": [{"id": "VSR-1"}]},
            ],
            "toc_groups": [
                {
                    "title": "Overview",
                    "items": [
                        {"label": "Top", "href": "#report-top"},
                        {"label": "Metrics", "href": "#report-metrics"},
                    ],
                },
                {
                    "title": "VSR Rows",
                    "open": False,
                    "items": [{"label": "Security", "href": "#report-table-2"}],
                },
            ],
        }

        html = render_report_json_html(report_from_payload(payload))

        self.assertIn('<div class="report-toc-tree">', html)
        self.assertIn('<summary>Overview</summary>', html)
        self.assertIn('<details class="report-toc-group">', html)
        self.assertIn('<a href="#report-table-2">Security</a>', html)
        self.assertIn('const group = entry.link.closest(".report-toc-group");', html)

    def test_loads_from_file_relative_artifacts(self) -> None:
        from agent_tools.tools.diff_report.report_json import load_report_json

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "runtime.log").write_text("PASS\n", encoding="utf-8")
            report_path = root / "dashboard.json"
            report_path.write_text(
                json.dumps(
                    {
                        "title": "Dashboard",
                        "logs": {"runtime": {"title": "Runtime", "path": "runtime.log"}},
                        "summary_blocks": [{"type": "log", "log": "runtime"}],
                    }
                ),
                encoding="utf-8",
            )

            report = load_report_json(report_path)

        self.assertEqual("Dashboard", report.title)
        self.assertEqual("PASS\n", report.comments.logs["runtime"].text)
