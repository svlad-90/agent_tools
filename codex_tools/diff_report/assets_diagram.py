from __future__ import annotations

def diagram_script() -> str:
    return """<script>
(function () {
  const modal = document.getElementById("diagram-modal");
  if (!modal) {
    return;
  }
  const title = document.getElementById("diagram-modal-title");
  const content = document.getElementById("diagram-modal-content");
  const zoomLabel = document.getElementById("diagram-zoom-label");
  const searchInput = document.getElementById("diagram-search");
  const searchCount = document.getElementById("diagram-search-count");
  const exportButton = document.getElementById("diagram-export");
  const storyContext = document.getElementById("diagram-story-context");
  const storyTitle = document.getElementById("diagram-story-title");
  const storyBody = document.getElementById("diagram-story-body");
  const zoomTools = Array.from(document.querySelectorAll("[data-diagram-zoom-tool]"));
  let scale = 1;
  let initialScale = 1;
  let mode = "";
  let activeFocusTerms = [];
  let activeNotes = [];
  let activeCodeLinks = [];
  let activeCodeLinkHoverInstance = "";
  let activeCodeLinkHoverTarget = "";
  let searchMatches = [];
  let searchIndex = -1;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let panStartLeft = 0;
  let panStartTop = 0;
  let activeExportName = "asset";

  function setScale(nextScale) {
    scale = Math.max(0.25, Math.min(4, nextScale));
    if (zoomLabel) {
      zoomLabel.textContent = Math.round(scale * 100) + "%";
    }
    const stage = content.querySelector(".diagram-zoom-stage");
    if (stage) {
      stage.style.transform = "scale(" + scale + ")";
      stage.style.marginRight = ((scale - 1) * stage.scrollWidth) + "px";
      stage.style.marginBottom = ((scale - 1) * stage.scrollHeight) + "px";
    }
  }

  function setInitialDiagramScale() {
    initialScale = 1;
    if (mode !== "diagram") {
      setScale(initialScale);
      return;
    }
    const svg = content.querySelector(".diagram-zoom-stage svg");
    const size = svgNaturalSize(svg);
    if (!size || !size.width || !size.height) {
      setScale(initialScale);
      return;
    }
    const availableWidth = Math.max(0, content.clientWidth - 36);
    const availableHeight = Math.max(0, content.clientHeight - 36);
    if (size.width > availableWidth || size.height > availableHeight) {
      setScale(initialScale);
      return;
    }
    initialScale = Math.min(3, availableWidth / size.width, availableHeight / size.height);
    setScale(initialScale);
  }

  function svgNaturalSize(svg) {
    if (!svg) {
      return null;
    }
    if (svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width && svg.viewBox.baseVal.height) {
      return {
        width: svg.viewBox.baseVal.width,
        height: svg.viewBox.baseVal.height,
      };
    }
    let box;
    try {
      box = svg.getBBox();
    } catch (error) {
      return null;
    }
    return box ? { width: box.width, height: box.height } : null;
  }

  function setMode(nextMode) {
    mode = nextMode;
    content.dataset.mode = mode;
    for (const tool of zoomTools) {
      tool.hidden = mode !== "diagram";
    }
    if (exportButton) {
      exportButton.hidden = mode !== "diagram" && mode !== "log";
      exportButton.textContent = mode === "diagram" ? "Save as SVG" : "Save as HTML";
    }
  }

  function safeFileName(text, extension) {
    const base = String(text || "asset")
      .trim()
      .replace(/[^A-Za-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "asset";
    return base + "." + extension;
  }

  function downloadBlob(filename, type, text) {
    const blob = new Blob([text], { type: type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 0);
  }

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[char];
    });
  }

  function standaloneDiagramStyle() {
    const parts = [standaloneDiagramVariablesStyle()];
    const includeDarkRules = document.documentElement.dataset.theme === "dark";
    for (const sheet of Array.from(document.styleSheets)) {
      let rules;
      try {
        rules = sheet.cssRules;
      } catch (error) {
        continue;
      }
      parts.push(...standaloneCssRules(rules, includeDarkRules));
    }
    return parts.filter(Boolean).join("\\n");
  }

  function standaloneDiagramVariablesStyle() {
    const rootStyle = getComputedStyle(document.documentElement);
    const declarations = Array.from(standaloneDiagramVariableMap(rootStyle), function (entry) {
      return entry[0] + ": " + entry[1] + ";";
    });
    return declarations.length ? "svg { " + declarations.join(" ") + " }" : "";
  }

  function standaloneDiagramVariableMap(rootStyle) {
    const fallback = new Map([
      ["--diagram-bg", "#ffffff"],
      ["--diagram-svg-text", "#111827"],
      ["--diagram-svg-line", "#475569"],
      ["--diagram-svg-box-bg", "#ffffff"],
      ["--diagram-svg-note-bg", "#fff8c5"],
      ["--diagram-focus", "#1d4ed8"],
      ["--diagram-note-bg", "#dbeafe"],
      ["--diagram-note-hover-bg", "#bfdbfe"],
      ["--diagram-note-text", "#111827"],
      ["--diagram-note-link", "#2563eb"],
      ["--diagram-note-marker-bg", "#eff6ff"],
      ["--diagram-link", "#107c10"],
      ["--diagram-link-bg", "#e9f5e9"],
      ["--diagram-link-hover-bg", "#deecf9"],
    ]);
    for (const name of Array.from(fallback.keys())) {
      const value = rootStyle.getPropertyValue(name).trim();
      if (value) {
        fallback.set(name, value);
      }
    }
    return fallback;
  }

  function standaloneCssRules(rules, includeDarkRules) {
    const output = [];
    for (const rule of Array.from(rules)) {
      if (rule.type === CSSRule.STYLE_RULE) {
        const selector = standaloneSelector(rule.selectorText, includeDarkRules);
        if (selector) {
          output.push(selector + " { " + resolveCssVariables(rule.style.cssText) + " }");
        }
      } else if (rule.type === CSSRule.KEYFRAMES_RULE) {
        output.push(rule.cssText);
      } else if (rule.type === CSSRule.MEDIA_RULE) {
        const nested = standaloneCssRules(rule.cssRules, includeDarkRules);
        if (nested.length) {
          output.push("@media " + rule.conditionText + " { " + nested.join("\\n") + " }");
        }
      }
    }
    return output;
  }

  function standaloneSelector(selectorText, includeDarkRules) {
    const selectors = selectorText.split(",").map(function (selector) {
      let next = selector.trim();
      const isDarkRule = next.startsWith(':root[data-theme="dark"]');
      if (isDarkRule && !includeDarkRules) {
        return "";
      }
      if (
        !/animation|keyframes|asset-focus-|diagram-note|diagram-code-link/.test(next)
        && !/\\.diagram-preview-canvas\\s+svg|\\.diagram-zoom-stage\\s+svg/.test(next)
      ) {
        return "";
      }
      next = next.replace(/^:root\\[data-theme="dark"\\]\\s+/, "");
      next = next.replace(/^:root\\s+/, "");
      next = next.replace(/\\.diagram-preview-canvas\\s+svg/g, "svg");
      next = next.replace(/\\.diagram-zoom-stage\\s+svg/g, "svg");
      if (next === "svg") {
        return "";
      }
      return next.includes("svg") ? next : "";
    }).filter(Boolean);
    return selectors.join(", ");
  }

  function resolveCssVariables(text) {
    const values = standaloneDiagramVariableMap(getComputedStyle(document.documentElement));
    return text.replace(/var\\((--[A-Za-z0-9_-]+)(?:,[^)]+)?\\)/g, function (match, name) {
      return values.get(name) || match;
    });
  }

  function inlineReportOverlayStyles(sourceSvg, cloneSvg) {
    const sourceNodes = [sourceSvg].concat(Array.from(sourceSvg.querySelectorAll("*")));
    const cloneNodes = [cloneSvg].concat(Array.from(cloneSvg.querySelectorAll("*")));
    const properties = [
      "fill",
      "stroke",
      "stroke-width",
      "stroke-dasharray",
      "stroke-dashoffset",
      "stroke-linecap",
      "stroke-linejoin",
      "opacity",
      "font",
      "font-family",
      "font-size",
      "font-weight",
      "text-anchor",
      "dominant-baseline",
      "paint-order",
      "filter",
    ];
    sourceNodes.forEach(function (sourceNode, index) {
      const cloneNode = cloneNodes[index];
      if (!cloneNode || !sourceNode.ownerDocument.defaultView) {
        return;
      }
      if (!isReportOverlayNode(sourceNode)) {
        return;
      }
      const computed = sourceNode.ownerDocument.defaultView.getComputedStyle(sourceNode);
      const declarations = [];
      for (const property of properties) {
        if (!canInlineOverlayProperty(sourceNode, property)) {
          continue;
        }
        const value = computed.getPropertyValue(property);
        if (value) {
          declarations.push(property + ": " + value + ";");
        }
      }
      if (declarations.length) {
        const existing = cloneNode.getAttribute("style") || "";
        cloneNode.setAttribute("style", (existing ? existing + "; " : "") + declarations.join(" "));
      }
    });
  }

  function canInlineOverlayProperty(node, property) {
    if (
      property === "opacity"
      && node.classList
      && (node.classList.contains("diagram-note-panel") || node.classList.contains("diagram-note-hotspot"))
    ) {
      return false;
    }
    return true;
  }

  function isReportOverlayNode(node) {
    if (!node || !node.classList) {
      return false;
    }
    for (const className of Array.from(node.classList)) {
      if (
        className.startsWith("asset-focus-")
        || className.startsWith("diagram-note-")
        || className.startsWith("diagram-code-link-")
      ) {
        return true;
      }
    }
    return false;
  }

  function insertSvgBackground(svg) {
    const box = svgViewBox(svg);
    if (!box || box.width <= 0 || box.height <= 0) {
      return;
    }
    const background = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    background.setAttribute("class", "diagram-export-background");
    background.setAttribute("x", String(box.x));
    background.setAttribute("y", String(box.y));
    background.setAttribute("width", String(box.width));
    background.setAttribute("height", String(box.height));
    background.setAttribute("fill", diagramBackgroundColor());
    svg.insertBefore(background, firstDrawableSvgChild(svg));
  }

  function firstDrawableSvgChild(svg) {
    for (const child of Array.from(svg.childNodes)) {
      if (child.nodeType === Node.ELEMENT_NODE && child.tagName.toLowerCase() !== "style") {
        return child;
      }
    }
    return null;
  }

  function svgViewBox(svg) {
    const viewBox = (svg.getAttribute("viewBox") || "").trim().split(/[\\s,]+/).map(Number);
    if (viewBox.length === 4 && viewBox.every(Number.isFinite)) {
      return { x: viewBox[0], y: viewBox[1], width: viewBox[2], height: viewBox[3] };
    }
    const width = parseSvgLength(svg.getAttribute("width"));
    const height = parseSvgLength(svg.getAttribute("height"));
    if (width > 0 && height > 0) {
      return { x: 0, y: 0, width, height };
    }
    const size = svgNaturalSize(svg);
    return size ? { x: 0, y: 0, width: size.width, height: size.height } : null;
  }

  function parseSvgLength(value) {
    const parsed = Number.parseFloat(String(value || ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function diagramBackgroundColor() {
    const contentBackground = getComputedStyle(content).backgroundColor;
    if (contentBackground && contentBackground !== "rgba(0, 0, 0, 0)") {
      return contentBackground;
    }
    const rootBackground = getComputedStyle(document.documentElement).getPropertyValue("--diagram-bg").trim();
    return rootBackground || "#ffffff";
  }

  function removeCodeLinkState(svg) {
    for (const node of svg.querySelectorAll(".diagram-code-link-badge")) {
      node.remove();
    }
    for (const node of svg.querySelectorAll("[data-code-link-instance], [data-code-link-target]")) {
      node.classList.remove(
        "diagram-code-link-target",
        "diagram-code-link-connector",
        "diagram-code-link-hover",
        "diagram-code-link-active"
      );
      node.removeAttribute("data-code-link-instance");
      node.removeAttribute("data-code-link-target");
    }
  }

  function prepareExportedSvgForViewers(svg) {
    fixExportedSvgViewportSize(svg);
    for (const node of svg.querySelectorAll("text, tspan")) {
      node.removeAttribute("textLength");
      node.removeAttribute("lengthAdjust");
    }
  }

  function fixExportedSvgViewportSize(svg) {
    const box = svgViewBox(svg);
    if (!box || box.width <= 0 || box.height <= 0) {
      return;
    }
    const width = Math.round(box.width * 1000) / 1000;
    const height = Math.round(box.height * 1000) / 1000;
    svg.setAttribute("width", width + "px");
    svg.setAttribute("height", height + "px");
    svg.style.width = width + "px";
    svg.style.height = height + "px";
    svg.style.maxWidth = "none";
    svg.style.maxHeight = "none";
    svg.removeAttribute("viewBox");
  }

  function exportOpenedDiagram() {
    const svg = content.querySelector(".diagram-zoom-stage svg");
    if (!svg) {
      return;
    }
    const clone = svg.cloneNode(true);
    inlineReportOverlayStyles(svg, clone);
    removeCodeLinkState(clone);
    prepareExportedSvgForViewers(clone);
    if (!clone.getAttribute("xmlns")) {
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    }
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = standaloneDiagramStyle();
    if (style.textContent) {
      clone.insertBefore(style, clone.firstChild);
    }
    insertSvgBackground(clone);
    const source = new XMLSerializer().serializeToString(clone);
    downloadBlob(safeFileName(activeExportName, "svg"), "image/svg+xml;charset=utf-8", source);
  }

  function exportOpenedLog() {
    const pre = content.querySelector(".log-view-text");
    if (!pre) {
      return;
    }
    const sourceText = pre.dataset.sourceText || pre.textContent || "";
    const safeTitle = escapeHtml(title ? title.textContent : activeExportName);
    const html = "<!doctype html>\\n"
      + "<html lang=\\"en\\">\\n<head>\\n<meta charset=\\"utf-8\\">\\n"
      + "<meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1\\">\\n"
      + "<title>" + safeTitle + "</title>\\n"
      + "<style>body{margin:0;background:#0d1117;color:#e6edf3;}main{padding:24px;}h1{font:700 18px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0 0 16px;}pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;font:14px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;}</style>\\n"
      + "</head>\\n<body><main><h1>" + safeTitle + "</h1><pre>"
      + escapeHtml(sourceText)
      + "</pre></main></body>\\n</html>\\n";
    downloadBlob(safeFileName(activeExportName, "html"), "text/html;charset=utf-8", html);
  }

  function clearSearch() {
    searchMatches = [];
    searchIndex = -1;
    if (searchCount) {
      searchCount.textContent = "";
    }
    if (mode === "log") {
      renderLogView("", activeFocusTerms);
      return;
    }
    for (const node of content.querySelectorAll(".asset-search-match, .asset-search-current")) {
      node.classList.remove("asset-search-match", "asset-search-current");
    }
  }

  function clearFocus() {
    activeFocusTerms = [];
    activeNotes = [];
    for (const node of content.querySelectorAll(".diagram-note-layer")) {
      node.remove();
    }
    for (const node of content.querySelectorAll(".asset-focus-connector")) {
      node.classList.remove("asset-focus-connector", "asset-focus-connector-reverse");
    }
    for (const node of content.querySelectorAll(".asset-focus-match")) {
      node.classList.remove("asset-focus-match", "asset-focus-related-hover");
    }
    for (const node of content.querySelectorAll(".asset-focus-related-hover")) {
      node.classList.remove("asset-focus-related-hover");
    }
    for (const node of content.querySelectorAll(".diagram-code-link-hover")) {
      node.classList.remove("diagram-code-link-hover");
    }
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
    if (mode === "log") {
      renderLogView(searchInput ? searchInput.value : "", activeFocusTerms);
    }
  }

  function parseFocus(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map(String).filter(Boolean);
      }
    } catch (error) {
      return [String(value)];
    }
    return [String(value)];
  }

  function matchesAnyTerm(text, terms) {
    const lowerText = text.toLowerCase();
    return terms.some(function (term) {
      return lowerText.includes(String(term).toLowerCase());
    });
  }

  function markSvgFocusMatch(node) {
    const labelNode = svgTextLabelNode(node);
    labelNode.classList.add("asset-focus-match");
    if (labelNode.querySelectorAll) {
      for (const child of labelNode.querySelectorAll("tspan")) {
        child.classList.add("asset-focus-match");
      }
    }
  }

  function svgLabelLineGroup(node) {
    const labelNode = svgTextLabelNode(node);
    const box = safeBBox(labelNode);
    const parent = labelNode.parentNode;
    if (!box || !parent || !labelNode.tagName || labelNode.tagName.toLowerCase() !== "text") {
      return [labelNode];
    }
    const group = [];
    const x = Number.parseFloat(labelNode.getAttribute("x") || "");
    const centerY = box.y + box.height / 2;
    for (const candidate of parent.querySelectorAll("text")) {
      const candidateBox = safeBBox(candidate);
      if (!candidateBox) {
        continue;
      }
      const candidateX = Number.parseFloat(candidate.getAttribute("x") || "");
      const candidateCenterY = candidateBox.y + candidateBox.height / 2;
      if (
        Number.isFinite(x)
        && Number.isFinite(candidateX)
        && Math.abs(candidateX - x) <= 2
        && Math.abs(candidateCenterY - centerY) <= 22
      ) {
        group.push(candidate);
      }
    }
    return group.length ? group : [labelNode];
  }

  function isSvgConnector(node) {
    if (!node || !node.tagName) {
      return false;
    }
    const tag = node.tagName.toLowerCase();
    return tag === "line" || tag === "polyline" || tag === "polygon" || tag === "path";
  }

  function addSvgFocusConnector(node) {
    const connectors = connectorsForText(node);
    const arrowhead = connectors.find(function (connector) {
      return connector.tagName && connector.tagName.toLowerCase() === "polygon";
    });
    for (const connector of connectors) {
      connector.classList.add("asset-focus-connector");
      if (isReverseConnector(connector, arrowhead)) {
        connector.classList.add("asset-focus-connector-reverse");
      }
    }
  }

  function connectorsForText(node) {
    let current = node.previousElementSibling;
    let inspected = 0;
    const connectors = [];
    while (current && inspected < 5 && connectors.length < 2) {
      if (isSvgConnector(current)) {
        connectors.push(current);
      }
      current = current.previousElementSibling;
      inspected += 1;
    }
    return connectors;
  }

  function isReverseConnector(node, arrowhead) {
    const tag = node.tagName.toLowerCase();
    const points = connectorEndpoints(node, tag);
    if (!points) {
      return false;
    }
    if (arrowhead && node !== arrowhead) {
      const arrowCenter = connectorCenter(arrowhead, "polygon");
      if (arrowCenter) {
        const startDistance = distance(points.start, arrowCenter);
        const endDistance = distance(points.end, arrowCenter);
        return startDistance < endDistance;
      }
    }
    const dx = points.end.x - points.start.x;
    const dy = points.end.y - points.start.y;
    if (Math.abs(dx) >= Math.abs(dy)) {
      return dx < 0;
    }
    return dy < 0;
  }

  function connectorEndpoints(node, tag) {
    if (tag === "line") {
      return {
        start: { x: numberAttr(node, "x1"), y: numberAttr(node, "y1") },
        end: { x: numberAttr(node, "x2"), y: numberAttr(node, "y2") },
      };
    }
    if (tag === "polyline" || tag === "polygon") {
      return endpointsFromNumbers((node.getAttribute("points") || "").match(/-?\\d+(?:\\.\\d+)?/g));
    }
    if (tag === "path") {
      return endpointsFromNumbers((node.getAttribute("d") || "").match(/-?\\d+(?:\\.\\d+)?/g));
    }
    return null;
  }

  function endpointsFromNumbers(rawNumbers) {
    if (!rawNumbers || rawNumbers.length < 4) {
      return null;
    }
    const numbers = rawNumbers.map(Number);
    return {
      start: { x: numbers[0], y: numbers[1] },
      end: { x: numbers[numbers.length - 2], y: numbers[numbers.length - 1] },
    };
  }

  function connectorCenter(node, tag) {
    const endpoints = connectorEndpoints(node, tag);
    if (!endpoints) {
      return null;
    }
    return {
      x: (endpoints.start.x + endpoints.end.x) / 2,
      y: (endpoints.start.y + endpoints.end.y) / 2,
    };
  }

  function distance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function numberAttr(node, name) {
    return Number(node.getAttribute(name) || 0);
  }

  function updateSearch(resetIndex) {
    clearSearch();
    const query = searchInput ? searchInput.value : "";
    if (!query) {
      return;
    }
    if (mode === "diagram") {
      searchDiagram(query);
    } else if (mode === "log") {
      searchLog(query);
    }
    if (!searchMatches.length) {
      if (searchCount) {
        searchCount.textContent = "0";
      }
      return;
    }
    searchIndex = resetIndex ? 0 : Math.max(0, Math.min(searchIndex, searchMatches.length - 1));
    showSearchMatch();
  }

  function searchDiagram(query) {
    const lowerQuery = query.toLowerCase();
    const textNodes = content.querySelectorAll("svg text");
    for (const node of textNodes) {
      if (node.textContent.toLowerCase().includes(lowerQuery)) {
        node.classList.add("asset-search-match");
        searchMatches.push(node);
      }
    }
  }

  function searchLog(query) {
    renderLogView(query, activeFocusTerms);
  }

  function appendSearchParts(parent, text, query) {
    if (!query) {
      parent.appendChild(document.createTextNode(text));
      return;
    }
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    let offset = 0;
    while (true) {
      const matchAt = lowerText.indexOf(lowerQuery, offset);
      if (matchAt === -1) {
        break;
      }
      parent.appendChild(document.createTextNode(text.slice(offset, matchAt)));
      const mark = document.createElement("mark");
      mark.className = "asset-search-match";
      mark.textContent = text.slice(matchAt, matchAt + query.length);
      parent.appendChild(mark);
      searchMatches.push(mark);
      offset = matchAt + query.length;
    }
    parent.appendChild(document.createTextNode(text.slice(offset)));
  }

  function renderLogView(query, focusTerms) {
    const pre = content.querySelector(".log-view-text");
    if (!pre) {
      return;
    }
    const sourceText = pre.dataset.sourceText || pre.textContent;
    pre.dataset.sourceText = sourceText;
    const fragment = document.createDocumentFragment();
    const lines = sourceText.split("\\n");
    lines.forEach(function (line, index) {
      if (matchesAnyTerm(line, focusTerms)) {
        const span = document.createElement("span");
        span.className = "asset-focus-line";
        appendSearchParts(span, line, query);
        fragment.appendChild(span);
      } else {
        appendSearchParts(fragment, line, query);
      }
      if (index < lines.length - 1) {
        fragment.appendChild(document.createTextNode("\\n"));
      }
    });
    pre.replaceChildren(fragment);
  }

  function parseNotes(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function parseCodeLinks(value) {
    if (!value) {
      return [];
    }
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function applyFocusTerms(terms, notes) {
    clearFocus();
    activeFocusTerms = terms;
    activeNotes = notes || [];
    if (mode === "diagram") {
      const focused = [];
      const textNodes = content.querySelectorAll("svg text, svg tspan");
      const focusedLabels = new Set();
      for (const node of textNodes) {
        if (matchesAnyTerm(node.textContent, activeFocusTerms)) {
          const labelNode = svgTextLabelNode(node);
          if (focusedLabels.has(labelNode)) {
            continue;
          }
          const labelLines = svgLabelLineGroup(labelNode);
          for (const labelLine of labelLines) {
            focusedLabels.add(labelLine);
            markSvgFocusMatch(labelLine);
          }
          addSvgFocusConnector(labelNode);
          focused.push(labelNode);
        }
      }
      addDiagramNotes(notes || [], textNodes);
      if (focused[0]) {
        window.setTimeout(function () {
          animateScrollContainerToElement(content, focused[0], 1000);
        }, 40);
      }
    } else if (mode === "log") {
      renderLogView(searchInput ? searchInput.value : "", activeFocusTerms);
      const firstLine = content.querySelector(".asset-focus-line");
      if (firstLine) {
        window.setTimeout(function () {
          animateScrollContainerToElement(content, firstLine, 1000, { horizontal: false });
        }, 40);
      }
    }
  }

  function animateScrollContainerToElement(container, element, durationMs, options) {
    const scrollHorizontal = !options || options.horizontal !== false;
    const startLeft = container.scrollLeft;
    const startTop = container.scrollTop;
    const containerRect = container.getBoundingClientRect();
    const targetRect = elementViewportRect(element);
    const maxLeft = Math.max(0, container.scrollWidth - container.clientWidth);
    const maxTop = Math.max(0, container.scrollHeight - container.clientHeight);
    const targetLeft = scrollHorizontal
      ? clamp(
          startLeft + targetRect.left - containerRect.left - container.clientWidth / 2 + targetRect.width / 2,
          0,
          maxLeft
        )
      : startLeft;
    const targetTop = clamp(
      startTop + targetRect.top - containerRect.top - container.clientHeight / 2 + targetRect.height / 2,
      0,
      maxTop
    );
    const deltaLeft = targetLeft - startLeft;
    const deltaTop = targetTop - startTop;
    const startedAt = performance.now();
    if (!deltaLeft && !deltaTop) {
      return;
    }
    function tick(now) {
      const elapsed = Math.min(1, (now - startedAt) / durationMs);
      const eased = elapsed < 0.5
        ? 4 * elapsed * elapsed * elapsed
        : 1 - Math.pow(-2 * elapsed + 2, 3) / 2;
      container.scrollLeft = startLeft + deltaLeft * eased;
      container.scrollTop = startTop + deltaTop * eased;
      if (elapsed < 1) {
        window.setTimeout(function () {
          tick(performance.now());
        }, 16);
      }
    }
    tick(performance.now());
    window.setTimeout(function () {
      container.scrollLeft = targetLeft;
      container.scrollTop = targetTop;
    }, durationMs + 30);
  }

  function elementViewportRect(element) {
    if (element.ownerSVGElement && typeof element.getBBox === "function") {
      const svgRect = svgElementViewportRect(element);
      if (svgRect) {
        return svgRect;
      }
    }
    return element.getBoundingClientRect();
  }

  function svgElementViewportRect(element) {
    let box;
    let matrix;
    try {
      box = element.getBBox();
      matrix = element.getScreenCTM();
    } catch (error) {
      return null;
    }
    if (!box || !matrix) {
      return null;
    }
    const points = [
      svgPoint(element, box.x, box.y).matrixTransform(matrix),
      svgPoint(element, box.x + box.width, box.y).matrixTransform(matrix),
      svgPoint(element, box.x, box.y + box.height).matrixTransform(matrix),
      svgPoint(element, box.x + box.width, box.y + box.height).matrixTransform(matrix),
    ];
    const xs = points.map(function (point) { return point.x; });
    const ys = points.map(function (point) { return point.y; });
    const left = Math.min.apply(Math, xs);
    const top = Math.min.apply(Math, ys);
    const right = Math.max.apply(Math, xs);
    const bottom = Math.max.apply(Math, ys);
    return {
      left,
      top,
      width: right - left,
      height: bottom - top,
    };
  }

  function svgPoint(element, x, y) {
    const svg = element.ownerSVGElement;
    if (svg && typeof svg.createSVGPoint === "function") {
      const point = svg.createSVGPoint();
      point.x = x;
      point.y = y;
      return point;
    }
    return new DOMPoint(x, y);
  }

  function applyCodeLinks(links) {
    activeCodeLinks = links || [];
    closeCodePopover();
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
    for (const node of content.querySelectorAll(".diagram-code-link-badge")) {
      node.remove();
    }
    for (const node of content.querySelectorAll(".diagram-code-link-target, .diagram-code-link-connector, .diagram-code-link-hover, .diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-target", "diagram-code-link-connector", "diagram-code-link-hover", "diagram-code-link-active");
      delete node.dataset.codeLinkTarget;
      delete node.dataset.codeLinkInstance;
    }
    if (mode !== "diagram" || !activeCodeLinks.length) {
      return;
    }
    const textNodes = content.querySelectorAll("svg text, svg tspan");
    let instanceIndex = 0;
    for (const link of activeCodeLinks) {
      const target = String(link.target || "").toLowerCase();
      if (!target) {
        continue;
      }
      const linkedLabels = new Set();
      for (const node of textNodes) {
        if (!node.textContent.toLowerCase().includes(target)) {
          continue;
        }
        const labelNode = svgTextLabelNode(node);
        if (linkedLabels.has(labelNode)) {
          continue;
        }
        linkedLabels.add(labelNode);
        decorateCodeLinkTarget(labelNode, link, "code-link-" + String(instanceIndex));
        instanceIndex += 1;
      }
    }
  }

  function decorateCodeLinkTarget(node, link, instanceKey) {
    node = svgTextLabelNode(node);
    const targetKey = String(link.target || "");
    const connectors = connectorsForText(node);
    node.classList.add("diagram-code-link-target");
    node.dataset.codeLinkTarget = targetKey;
    node.dataset.codeLinkInstance = instanceKey;
    attachCodeLinkHover(node, targetKey, instanceKey);
    for (const connector of connectors) {
      connector.classList.add("diagram-code-link-connector");
      connector.dataset.codeLinkTarget = targetKey;
      connector.dataset.codeLinkInstance = instanceKey;
      attachCodeLinkHover(connector, targetKey, instanceKey);
    }
    addCodeLinkBadge(node, targetKey, instanceKey);
  }

  function svgTextLabelNode(node) {
    if (node && node.tagName && node.tagName.toLowerCase() === "tspan" && node.parentElement) {
      return node.parentElement;
    }
    return node;
  }

  function attachCodeLinkHover(node, targetKey, instanceKey) {
    node.dataset.codeLinkTarget = targetKey;
    node.dataset.codeLinkInstance = instanceKey;
  }

  function setCodeLinkHover(targetKey, instanceKey, enabled) {
    for (const node of content.querySelectorAll("[data-code-link-instance]")) {
      if (node.dataset.codeLinkInstance === instanceKey) {
        node.classList.toggle(
          "diagram-code-link-hover",
          enabled && node.classList.contains("diagram-code-link-badge")
        );
      }
    }
    setDiagramNoteHoverForTarget(targetKey, enabled);
  }

  function updateCodeLinkHoverFromPointer(event) {
    if (modal.hidden || mode !== "diagram") {
      clearCodeLinkHover();
      return;
    }
    const pointerTarget = document.elementFromPoint(event.clientX, event.clientY);
    const item = pointerTarget ? pointerTarget.closest(".diagram-code-link-badge") : null;
    if (!item || !content.contains(item)) {
      clearCodeLinkHover();
      return;
    }
    const instanceKey = item.dataset.codeLinkInstance || "";
    const targetKey = item.dataset.codeLinkTarget || "";
    if (!instanceKey || instanceKey === activeCodeLinkHoverInstance) {
      return;
    }
    clearCodeLinkHover();
    activeCodeLinkHoverInstance = instanceKey;
    activeCodeLinkHoverTarget = targetKey;
    setCodeLinkHover(targetKey, instanceKey, true);
  }

  function clearCodeLinkHover() {
    if (!activeCodeLinkHoverInstance) {
      return;
    }
    setCodeLinkHover(activeCodeLinkHoverTarget, activeCodeLinkHoverInstance, false);
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
  }

  function setDiagramNoteHoverForTarget(targetKey, enabled) {
    const normalizedTarget = String(targetKey || "").toLowerCase();
    if (!normalizedTarget) {
      return;
    }
    for (const note of content.querySelectorAll("[data-diagram-note-target]")) {
      const noteTarget = String(note.dataset.diagramNoteTarget || "").toLowerCase();
      if (noteTarget && (normalizedTarget.includes(noteTarget) || noteTarget.includes(normalizedTarget))) {
        note.classList.toggle("diagram-note-hover", enabled);
      }
    }
  }

  function addCodeLinkBadge(labelNode, targetKey, instanceKey) {
    const svg = labelNode.ownerSVGElement;
    const box = safeBBox(labelNode);
    if (!svg || !box) {
      return;
    }
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "diagram-code-link-badge");
    group.dataset.codeLinkTarget = targetKey;
    group.dataset.codeLinkInstance = instanceKey;
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = "Open linked diff code";
    group.appendChild(title);
    const badge = codeLinkBadgePlacement(svg, box);
    const x = badge.x;
    const y = badge.y;
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "diagram-code-link-badge-box");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", "28");
    rect.setAttribute("height", "18");
    group.appendChild(rect);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "diagram-code-link-badge-text");
    text.setAttribute("x", String(x + 14));
    text.setAttribute("y", String(y + 9));
    text.textContent = "C";
    group.appendChild(text);
    group.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      activateCodeLink(targetKey, instanceKey);
    });
    attachCodeLinkHover(group, targetKey, instanceKey);
    const parent = labelNode.parentNode || svg;
    parent.appendChild(group);
  }

  function codeLinkBadgePlacement(svg, labelBox) {
    const width = 28;
    const height = 18;
    const gap = 8;
    const candidates = [
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y + labelBox.height / 2 - height / 2 },
      { x: labelBox.x - width - gap, y: labelBox.y + labelBox.height / 2 - height / 2 },
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y + labelBox.height + gap },
      { x: labelBox.x + labelBox.width + gap, y: labelBox.y - height - gap },
    ];
    const occupied = nearbyDiagramNoteBoxes(svg);
    for (const candidate of candidates) {
      const candidateBox = { x: candidate.x - 3, y: candidate.y - 3, width: width + 6, height: height + 6 };
      if (!occupied.some(function (box) { return svgBoxesOverlap(candidateBox, box); })) {
        return candidate;
      }
    }
    return candidates[1];
  }

  function nearbyDiagramNoteBoxes(svg) {
    const boxes = [];
    for (const node of svg.querySelectorAll(".diagram-note-hotspot")) {
      const box = safeBBox(node);
      if (box) {
        boxes.push({ x: box.x - 4, y: box.y - 4, width: box.width + 8, height: box.height + 8 });
      }
    }
    return boxes;
  }

  function svgBoxesOverlap(a, b) {
    return a.x < b.x + b.width
      && a.x + a.width > b.x
      && a.y < b.y + b.height
      && a.y + a.height > b.y;
  }

  function activateCodeLink(targetKey, instanceKey) {
    const links = activeCodeLinks.filter(function (link) {
      return String(link.target || "") === String(targetKey || "");
    });
    if (!links.length) {
      return;
    }
    markActiveCodeLink(instanceKey);
    renderCodePopover(targetKey, links);
  }

  function markActiveCodeLink(instanceKey) {
    for (const node of content.querySelectorAll(".diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-active");
    }
    for (const node of content.querySelectorAll("[data-code-link-instance]")) {
      if (node.dataset.codeLinkInstance === instanceKey) {
        node.classList.add("diagram-code-link-active");
      }
    }
  }

  function codeOverlayRoot() {
    return document.body;
  }

  function closeCodePopover() {
    const overlay = codeOverlayRoot().querySelector(".diagram-code-overlay");
    if (overlay) {
      overlay.remove();
    }
    for (const node of content.querySelectorAll(".diagram-code-link-active")) {
      node.classList.remove("diagram-code-link-active");
    }
    for (const node of content.querySelectorAll(".diagram-code-link-hover")) {
      node.classList.remove("diagram-code-link-hover");
    }
    activeCodeLinkHoverInstance = "";
    activeCodeLinkHoverTarget = "";
  }

  function renderCodePopover(targetKey, links) {
    closeExistingCodePopoverOnly();
    const overlay = document.createElement("div");
    overlay.className = "diagram-code-overlay";
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) {
        closeCodePopover();
      }
    });
    const popover = document.createElement("section");
    popover.className = "diagram-code-popover";
    popover.setAttribute("aria-label", "Code linked from diagram");
    popover.addEventListener("click", function (event) {
      event.stopPropagation();
    });
    const header = document.createElement("div");
    header.className = "diagram-code-popover-header";
    const heading = document.createElement("span");
    heading.className = "diagram-code-popover-title";
    const headingTitle = document.createElement("span");
    headingTitle.textContent = targetKey;
    heading.appendChild(headingTitle);
    const headingFile = document.createElement("span");
    headingFile.className = "diagram-code-popover-file";
    headingFile.textContent = codePopoverLocation(links);
    heading.appendChild(headingFile);
    header.appendChild(heading);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "diagram-code-popover-close";
    close.setAttribute("aria-label", "Close linked code");
    close.textContent = "×";
    close.addEventListener("click", closeCodePopover);
    header.appendChild(close);
    popover.appendChild(header);
    const body = document.createElement("div");
    body.className = "diagram-code-popover-body";
    for (const link of links) {
      body.appendChild(createCodeLinkItem(link));
    }
    popover.appendChild(body);
    overlay.appendChild(popover);
    codeOverlayRoot().appendChild(overlay);
    positionCodePopover(popover);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        positionCodePopover(popover);
        centerCodeTarget(popover);
      });
    });
  }

  function positionCodePopover(popover) {
    const dialog = modal.querySelector(".diagram-dialog");
    const rect = dialog ? dialog.getBoundingClientRect() : modal.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    popover.style.left = centerX + "px";
    popover.style.top = centerY + "px";
    popover.style.maxWidth = Math.max(320, rect.width - 64) + "px";
    popover.style.maxHeight = Math.max(320, rect.height - 64) + "px";
  }

  function codePopoverLocation(links) {
    const first = links && links[0] ? links[0] : {};
    const file = String(first.file || "unknown file");
    return file.split("/").filter(Boolean).pop() || file;
  }

  function centerCodeTarget(popover) {
    const firstTarget = popover.querySelector(".diagram-code-target-line");
    if (!firstTarget) {
      return;
    }
    const scroller = popover.querySelector(".diagram-code-popover-body");
    if (!scroller) {
      return;
    }
    const scrollerRect = scroller.getBoundingClientRect();
    const targetRect = firstTarget.getBoundingClientRect();
    const targetMiddle = (
      scroller.scrollTop
      + targetRect.top
      - scrollerRect.top
      + targetRect.height / 2
    );
    const maxScroll = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
    scroller.scrollTop = Math.min(maxScroll, Math.max(0, targetMiddle - scroller.clientHeight / 2));
  }

  function closeExistingCodePopoverOnly() {
    const overlay = codeOverlayRoot().querySelector(".diagram-code-overlay");
    if (overlay) {
      overlay.remove();
    }
  }

  function createCodeLinkItem(link) {
    const item = document.createElement("div");
    item.className = "diagram-code-link-item";
    const titleNode = document.createElement("span");
    titleNode.className = "diagram-code-link-title";
    titleNode.textContent = String(link.title || link.target || "Code");
    item.appendChild(titleNode);
    const location = document.createElement("span");
    location.className = "diagram-code-link-location";
    location.textContent = String(link.file || "") + ":" + String(link.line || "");
    item.appendChild(location);
    const code = document.createElement("code");
    code.className = "diagram-code-link-code";
    renderDiffFileContext(code, link);
    item.appendChild(code);
    return item;
  }

  function renderDiffFileContext(parent, link) {
    const rows = diffFileRowsForLink(link);
    if (!rows.length) {
      parent.textContent = "Target file is not present in this rendered diff.";
      return;
    }
    const targetRange = targetRangeForLink(link);
    const targetLine = Number(link.line);
    rows.forEach(function (row, index) {
      const line = Number(row.dataset.newLine || 0);
      const span = document.createElement("span");
      span.className = "diagram-code-line";
      if (targetRange && line >= targetRange.start && line <= targetRange.end) {
        span.classList.add("diagram-code-context-line");
      }
      if (Number.isFinite(targetLine) && line === targetLine) {
        span.classList.add("diagram-code-target-line");
      }
      const newLine = row.dataset.newLine || "";
      const code = row.querySelector(".code");
      span.textContent = String(newLine).padStart(5, " ") + "  " + (code ? code.textContent : "");
      parent.appendChild(span);
    });
  }

  function diffFileRowsForLink(link) {
    const filePath = String(link.file || "");
    if (!filePath) {
      return [];
    }
    return Array.from(document.querySelectorAll("tr[data-file]")).filter(function (row) {
      return row.dataset.file === filePath && row.dataset.newLine;
    });
  }

  function targetRangeForLink(link) {
    const filePath = String(link.file || "");
    const startLine = Number((link.range && link.range.start) || link.line);
    const endLine = Number((link.range && link.range.end) || link.line);
    if (!filePath || !Number.isFinite(startLine) || !Number.isFinite(endLine)) {
      return null;
    }
    return { start: Math.min(startLine, endLine), end: Math.max(startLine, endLine) };
  }

  function isDiagramNoteTarget(node, notes) {
    return notes.some(function (note) {
      const target = String(note.target || "").toLowerCase();
      return target && node.textContent.toLowerCase().includes(target);
    });
  }

  function addDiagramNotes(notes, textNodes) {
    if (!notes.length) {
      return;
    }
    const svg = content.querySelector("svg");
    if (!svg) {
      return;
    }
    const layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    layer.setAttribute("class", "diagram-note-layer");
    svg.appendChild(layer);
    const viewBox = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width
      ? svg.viewBox.baseVal
      : { x: 0, y: 0, width: Number(svg.getAttribute("width")) || 900, height: Number(svg.getAttribute("height")) || 900 };
    notes.forEach(function (note, index) {
      const target = findNoteTarget(textNodes, note.target || "");
      if (!target) {
        return;
      }
      const targetBox = safeBBox(target);
      if (!targetBox) {
        return;
      }
      const noteWidth = Math.min(320, Math.max(180, String(note.text || "").length * 4.2 + 24));
      const noteLines = estimateSvgTextLines(String(note.text || ""), noteWidth - 20);
      const noteHeight = Math.max(44, 18 + noteLines * 15);
      const connectors = connectorsForText(target);
      const anchor = labelRightAnchor(targetBox);
      const marker = diagramNoteMarkerPosition(viewBox, anchor);
      const position = diagramNotePosition(note, viewBox, marker, noteWidth, noteHeight, index);
      const x = position.x;
      const y = position.y;
      const group = createDiagramNote(note, x, y, noteWidth, noteHeight, marker, connectors.concat([target]));
      layer.appendChild(group);
      raiseFocusTarget(target, connectors);
    });
  }

  function diagramNoteMarkerPosition(viewBox, anchor) {
    const margin = 18;
    return {
      x: clamp(anchor.x + 18, viewBox.x + margin, viewBox.x + viewBox.width - margin),
      y: clamp(anchor.y, viewBox.y + margin, viewBox.y + viewBox.height - margin),
    };
  }

  function diagramNotePosition(note, viewBox, marker, width, height, index) {
    const margin = 24;
    const maxXOffset = 360;
    const maxYOffset = 220;
    const minX = viewBox.x + margin;
    const maxX = viewBox.x + viewBox.width - width - margin;
    const minY = viewBox.y + margin;
    const maxY = viewBox.y + viewBox.height - height - margin;
    if (Number.isFinite(note.x) && Number.isFinite(note.y)) {
      return {
        x: clamp(Number(note.x), minX, maxX),
        y: clamp(Number(note.y), minY, maxY),
      };
    }
    const rightX = clamp(marker.x + 30, minX, Math.min(maxX, marker.x + maxXOffset));
    const leftX = clamp(marker.x - width - 30, Math.max(minX, marker.x - maxXOffset), maxX);
    const hasRoomRight = rightX >= marker.x + 18;
    const x = hasRoomRight ? rightX : leftX;
    const idealY = marker.y - height / 2 + index * 4;
    const y = clamp(idealY, Math.max(minY, marker.y - maxYOffset), Math.min(maxY, marker.y + maxYOffset));
    return { x, y };
  }

  function clamp(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(max, Math.max(min, value));
  }

  function findNoteTarget(textNodes, targetText) {
    const targets = normalizedDiagramNoteTargets(targetText);
    const seenLabels = new Set();
    for (const node of textNodes) {
      const labelNode = svgTextLabelNode(node);
      if (seenLabels.has(labelNode)) {
        continue;
      }
      seenLabels.add(labelNode);
      const labelText = labelNode.textContent.toLowerCase();
      if (targets.some(function (target) { return labelText.includes(target); })) {
        return labelNode;
      }
    }
    return null;
  }

  function normalizedDiagramNoteTargets(targetText) {
    const rawTarget = String(targetText || "").toLowerCase().trim();
    const targets = rawTarget ? [rawTarget] : [];
    const colonIndex = rawTarget.lastIndexOf(":");
    if (colonIndex >= 0) {
      const labelOnly = rawTarget.slice(colonIndex + 1).trim();
      if (labelOnly) {
        targets.push(labelOnly);
      }
    }
    return targets;
  }

  function labelRightAnchor(box) {
    return {
      x: box.x + box.width + 6,
      y: box.y + box.height / 2,
    };
  }

  function createDiagramNote(note, x, y, width, height, markerPoint, relatedNodes) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("class", "diagram-note-hotspot");
    group.dataset.diagramNoteTarget = String(note.target || "");
    for (const eventName of ["click", "dblclick", "mousedown", "pointerdown"]) {
      group.addEventListener(eventName, stopDiagramNoteEvent);
    }
    const markerX = markerPoint.x;
    const markerY = markerPoint.y;
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    marker.setAttribute("class", "diagram-note-marker");
    marker.setAttribute("cx", String(markerX));
    marker.setAttribute("cy", String(markerY));
    marker.setAttribute("r", "9");
    group.appendChild(marker);
    const markerText = document.createElementNS("http://www.w3.org/2000/svg", "text");
    markerText.setAttribute("class", "diagram-note-marker-text");
    markerText.setAttribute("x", String(markerX));
    markerText.setAttribute("y", String(markerY + 0.5));
    markerText.textContent = "i";
    group.appendChild(markerText);
    const panel = document.createElementNS("http://www.w3.org/2000/svg", "g");
    panel.setAttribute("class", "diagram-note-panel");
    const link = document.createElementNS("http://www.w3.org/2000/svg", "path");
    link.setAttribute("class", "diagram-note-link");
    link.setAttribute("d", noteLinkPath(markerX, markerY, x, y + height / 2));
    panel.appendChild(link);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("class", "diagram-note-box");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", String(width));
    rect.setAttribute("height", String(height));
    panel.appendChild(rect);
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("class", "diagram-note-text");
    text.setAttribute("x", String(x + 10));
    text.setAttribute("y", String(y + 18));
    wrapSvgText(text, String(note.text || ""), width - 20);
    panel.appendChild(text);
    group.appendChild(panel);
    group.addEventListener("mouseenter", function () {
      group.classList.add("diagram-note-hover");
      for (const node of relatedNodes) {
        node.classList.add("asset-focus-related-hover");
      }
    });
    group.addEventListener("mouseleave", function () {
      group.classList.remove("diagram-note-hover");
      for (const node of relatedNodes) {
        node.classList.remove("asset-focus-related-hover");
      }
    });
    for (const node of relatedNodes) {
      node.addEventListener("mouseenter", function () {
        group.classList.add("diagram-note-hover");
        for (const item of relatedNodes) {
          item.classList.add("asset-focus-related-hover");
        }
      });
      node.addEventListener("mouseleave", function () {
        group.classList.remove("diagram-note-hover");
        for (const item of relatedNodes) {
          item.classList.remove("asset-focus-related-hover");
        }
      });
    }
    return group;
  }

  function raiseFocusTarget(target, connectors) {
    const parent = target.parentNode;
    if (!parent) {
      return;
    }
    for (const connector of connectors) {
      if (connector.parentNode === parent) {
        parent.appendChild(connector);
      }
    }
    parent.appendChild(target);
  }

  function boxesOverlap(a, b) {
    return (
      a.x <= b.x + b.width &&
      a.x + a.width >= b.x &&
      a.y <= b.y + b.height &&
      a.y + a.height >= b.y
    );
  }

  function stopDiagramNoteEvent(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  function noteLinkPath(x1, y1, x2, y2) {
    return [
      "M", x1, y1,
      "L", x2, y2,
    ].join(" ");
  }

  function estimateSvgTextLines(text, maxWidth) {
    const words = text.split(/\\s+/).filter(Boolean);
    let line = "";
    let lines = 0;
    for (const word of words) {
      const next = line ? line + " " + word : word;
      if (next.length * 6.4 > maxWidth && line) {
        lines += 1;
        line = word;
      } else {
        line = next;
      }
    }
    return lines + (line ? 1 : 0);
  }

  function wrapSvgText(textNode, text, maxWidth) {
    const words = text.split(/\\s+/);
    let line = "";
    let lineNo = 0;
    for (const word of words) {
      const next = line ? line + " " + word : word;
      if (next.length * 6.4 > maxWidth && line) {
        appendTspan(textNode, line, lineNo);
        line = word;
        lineNo += 1;
      } else {
        line = next;
      }
    }
    if (line) {
      appendTspan(textNode, line, lineNo);
    }
  }

  function appendTspan(textNode, text, lineNo) {
    const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
    tspan.setAttribute("x", textNode.getAttribute("x"));
    tspan.setAttribute("dy", lineNo === 0 ? "0" : "15");
    tspan.textContent = text;
    textNode.appendChild(tspan);
  }

  function safeBBox(node) {
    try {
      return node.getBBox();
    } catch (error) {
      return null;
    }
  }

  function showSearchMatch() {
    for (const node of searchMatches) {
      node.classList.remove("asset-search-current");
    }
    const current = searchMatches[searchIndex];
    if (!current) {
      return;
    }
    current.classList.add("asset-search-current");
    if (mode === "log") {
      animateScrollContainerToElement(content, current, 180, { horizontal: false });
    } else {
      current.scrollIntoView({ block: "center", inline: "center" });
    }
    if (searchCount) {
      searchCount.textContent = (searchIndex + 1) + "/" + searchMatches.length;
    }
  }

  function moveSearch(delta) {
    if (!searchMatches.length) {
      updateSearch(true);
      return;
    }
    searchIndex = (searchIndex + delta + searchMatches.length) % searchMatches.length;
    showSearchMatch();
  }

  function openTemplate(prefix, id, nextMode, focusTerms, notes, nextStoryContext) {
    const template = document.getElementById(prefix + "-template-" + id);
    if (!template) {
      return;
    }
    title.textContent = template.dataset.title || "Diagram";
    activeExportName = template.dataset.title || id || nextMode || "asset";
    setStoryContext(nextStoryContext || null);
    content.innerHTML = "";
    const stage = document.createElement("div");
    stage.className = "diagram-zoom-stage";
    stage.appendChild(template.content.cloneNode(true));
    content.appendChild(stage);
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    setMode(nextMode);
    if (searchInput) {
      searchInput.value = "";
    }
    setInitialDiagramScale();
    applyFocusTerms(focusTerms || [], notes || []);
    applyCodeLinks(nextMode === "diagram" ? parseCodeLinks(template.dataset.codeLinks) : []);
    if (nextMode === "log" && searchInput) {
      searchInput.focus();
    }
  }

  function setStoryContext(nextStoryContext) {
    const contextTitle = nextStoryContext ? String(nextStoryContext.title || "") : "";
    const contextBody = nextStoryContext ? String(nextStoryContext.body || "") : "";
    if (!storyContext || !storyTitle || !storyBody) {
      return;
    }
    storyTitle.textContent = contextTitle;
    storyBody.textContent = contextBody;
    storyContext.hidden = !(contextTitle || contextBody);
  }

  function storyContextFromTrigger(trigger) {
    const triggerTitle = trigger ? trigger.dataset.storyTitle || "" : "";
    const triggerBody = trigger ? trigger.dataset.storyBody || "" : "";
    return {
      title: triggerTitle || document.body.dataset.activeStoryTitle || "",
      body: triggerBody || document.body.dataset.activeStoryBody || "",
    };
  }

  function openDiagram(id, focusTerms, notes, nextStoryContext) {
    openTemplate("diagram", id, "diagram", focusTerms, notes, nextStoryContext);
  }

  function openLog(id, focusTerms, nextStoryContext) {
    openTemplate("log", id, "log", focusTerms, undefined, nextStoryContext);
  }

  function closeDiagram() {
    modal.hidden = true;
    content.innerHTML = "";
    document.body.style.overflow = "";
    scale = 1;
    initialScale = 1;
    setMode("");
    activeFocusTerms = [];
    activeNotes = [];
    activeCodeLinks = [];
    activeExportName = "asset";
    setStoryContext(null);
    closeCodePopover();
    clearSearch();
  }

  document.addEventListener("click", function (event) {
    const preview = event.target.closest("[data-diagram-id]");
    if (preview) {
      openDiagram(
        preview.dataset.diagramId,
        parseFocus(preview.dataset.diagramFocus),
        parseNotes(preview.dataset.diagramNotes),
        storyContextFromTrigger(preview)
      );
      return;
    }
    const logPreview = event.target.closest("[data-log-id]");
    if (logPreview) {
      openLog(
        logPreview.dataset.logId,
        parseFocus(logPreview.dataset.logFocus),
        storyContextFromTrigger(logPreview)
      );
      return;
    }
    if (event.target.closest("[data-diagram-close]")) {
      closeDiagram();
      return;
    }
    const zoom = event.target.closest("[data-diagram-zoom]");
    if (zoom) {
      const action = zoom.dataset.diagramZoom;
      if (action === "in") {
        setScale(scale + 0.25);
      } else if (action === "out") {
        setScale(scale - 0.25);
      } else {
        setScale(initialScale);
      }
      return;
    }
    const search = event.target.closest("[data-diagram-search]");
    if (search) {
      moveSearch(search.dataset.diagramSearch === "prev" ? -1 : 1);
      return;
    }
    if (event.target.closest("[data-asset-export]")) {
      if (mode === "diagram") {
        exportOpenedDiagram();
      } else if (mode === "log") {
        exportOpenedLog();
      }
      return;
    }
    if (event.target.closest(".diagram-code-popover")) {
      event.stopPropagation();
      return;
    }
  });

  document.addEventListener("keydown", function (event) {
    if (modal.hidden) {
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "f") {
      event.preventDefault();
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
      return;
    }
    if (event.key === "Enter" && document.activeElement === searchInput) {
      event.preventDefault();
      moveSearch(event.shiftKey ? -1 : 1);
      return;
    }
    if (event.key === "Escape") {
      if (codeOverlayRoot().querySelector(".diagram-code-overlay")) {
        closeCodePopover();
        return;
      }
      closeDiagram();
    }
  });

  document.addEventListener("pointermove", function (event) {
    updateCodeLinkHoverFromPointer(event);
  });

  document.addEventListener("pointerleave", function () {
    clearCodeLinkHover();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      clearCodeLinkHover();
    }
  });

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      updateSearch(true);
    });
  }

  content.addEventListener("wheel", function (event) {
    clearCodeLinkHover();
    if (!event.ctrlKey || modal.hidden || mode !== "diagram") {
      return;
    }
    event.preventDefault();
    const step = event.deltaY < 0 ? 0.1 : -0.1;
    setScale(scale + step);
  }, { passive: false });

  content.addEventListener("pointerdown", function (event) {
    if (modal.hidden || mode !== "diagram" || event.button !== 0) {
      return;
    }
    if (event.target.closest("button, input")) {
      return;
    }
    if (event.target.closest(".diagram-code-link-badge, .diagram-note-hotspot, .diagram-code-overlay")) {
      return;
    }
    clearCodeLinkHover();
    isPanning = true;
    panStartX = event.clientX;
    panStartY = event.clientY;
    panStartLeft = content.scrollLeft;
    panStartTop = content.scrollTop;
    content.classList.add("is-panning");
    content.setPointerCapture(event.pointerId);
    event.preventDefault();
  });

  content.addEventListener("pointermove", function (event) {
    if (!isPanning) {
      return;
    }
    content.scrollLeft = panStartLeft - (event.clientX - panStartX);
    content.scrollTop = panStartTop - (event.clientY - panStartY);
  });

  function stopPanning(event) {
    if (!isPanning) {
      return;
    }
    isPanning = false;
    content.classList.remove("is-panning");
    if (event && typeof event.pointerId === "number") {
      content.releasePointerCapture(event.pointerId);
    }
  }

  content.addEventListener("pointerup", stopPanning);
  content.addEventListener("pointercancel", stopPanning);
}());
</script>
"""
