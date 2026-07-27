from __future__ import annotations

from .assets_diagram_code_popover import diagram_code_popover_helpers
from .assets_diagram_export import diagram_export_helpers
from .assets_diagram_notes import diagram_note_helpers


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
  let searchRaf = 0;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let panStartLeft = 0;
  let panStartTop = 0;
  let activeExportName = "asset";
  let scaleAnimation = 0;

  function setScale(nextScale, options) {
    const targetScale = Math.max(0.25, Math.min(4, nextScale));
    if (options && options.animate) {
      animateScaleTo(targetScale);
      return;
    }
    if (scaleAnimation) {
      window.cancelAnimationFrame(scaleAnimation);
      scaleAnimation = 0;
    }
    applyScale(targetScale);
  }

  function zoomAtPoint(nextScale, clientX, clientY) {
    const targetScale = Math.max(0.25, Math.min(4, nextScale));
    if (Math.abs(targetScale - scale) < 0.001) {
      return;
    }
    if (mode !== "diagram") {
      setScale(targetScale);
      return;
    }
    const rect = content.getBoundingClientRect();
    const offsetX = clientX - rect.left;
    const offsetY = clientY - rect.top;
    const anchorX = (content.scrollLeft + offsetX) / scale;
    const anchorY = (content.scrollTop + offsetY) / scale;
    setScale(targetScale);
    content.scrollLeft = Math.max(0, (anchorX * scale) - offsetX);
    content.scrollTop = Math.max(0, (anchorY * scale) - offsetY);
  }

  function animateScaleTo(targetScale) {
    if (scaleAnimation) {
      window.cancelAnimationFrame(scaleAnimation);
    }
    const startedAt = performance.now();
    const startScale = scale;
    const durationMs = 160;
    function tick(now) {
      const elapsed = Math.min(1, (now - startedAt) / durationMs);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      applyScale(startScale + (targetScale - startScale) * eased);
      if (elapsed < 1) {
        scaleAnimation = window.requestAnimationFrame(tick);
      } else {
        scaleAnimation = 0;
        applyScale(targetScale);
      }
    }
    scaleAnimation = window.requestAnimationFrame(tick);
  }

  function applyScale(nextScale) {
    scale = nextScale;
    if (zoomLabel) {
      zoomLabel.textContent = Math.round(scale * 100) + "%";
    }
    if (mode === "log") {
      content.style.setProperty("--asset-log-scale", String(scale));
      return;
    }
    content.style.removeProperty("--asset-log-scale");
    const stage = content.querySelector(".diagram-zoom-stage");
    if (stage) {
      stage.style.transform = "scale(" + scale + ")";
      stage.style.marginRight = ((scale - 1) * stage.scrollWidth) + "px";
      stage.style.marginBottom = ((scale - 1) * stage.scrollHeight) + "px";
    }
  }

  function parseZoom(value) {
    const parsed = Number.parseFloat(value || "");
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
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
    const widthScale = availableWidth > 0 ? availableWidth / size.width : 1;
    const heightScale = availableHeight > 0 ? availableHeight / size.height : 1;
    if (size.height > availableHeight || size.width > availableWidth) {
      initialScale = Math.min(3, widthScale);
      setScale(initialScale);
      return;
    }
    initialScale = Math.min(3, widthScale, heightScale);
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
      tool.hidden = mode !== "diagram" && mode !== "log";
    }
    if (exportButton) {
      exportButton.hidden = mode !== "diagram" && mode !== "log";
	      exportButton.textContent = mode === "diagram" ? "Save as SVG" : "Save as HTML";
	    }
	  }

	  function requestExtraPaint(node) {
	    window.requestAnimationFrame(function () {
	      window.requestAnimationFrame(function () {
	        const target = node && node.isConnected ? node : document.body;
	        if (target) {
	          void target.offsetHeight;
	        }
	      });
	    });
	  }
	
	""" + diagram_export_helpers() + """  function clearSearch() {
    searchMatches = [];
    searchIndex = -1;
    if (searchCount) {
      searchCount.textContent = "";
    }
    if (mode === "log") {
      renderLogView("", activeFocusTerms);
      return;
    }
    for (const node of content.querySelectorAll(".asset-search-painted")) {
      restoreSvgSearchPaint(node);
    }
    for (const node of content.querySelectorAll(".asset-search-submatch-layer")) {
      node.remove();
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
    for (const node of content.querySelectorAll(".asset-focus-object")) {
      node.classList.remove("asset-focus-object");
    }
    for (const node of content.querySelectorAll(".asset-focus-match")) {
      node.classList.remove("asset-focus-match", "asset-focus-contained-text", "asset-focus-related-hover");
    }
    for (const node of content.querySelectorAll(".asset-focus-contained-text")) {
      node.classList.remove("asset-focus-contained-text");
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

  function resetArtifactViewport() {
    content.scrollLeft = 0;
    content.scrollTop = 0;
    content.style.removeProperty("--asset-log-scale");
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
    const shape = closestSvgObjectShape(labelNode);
    if (shape) {
      shape.classList.add("asset-focus-object");
      markSvgTextInsideShape(shape, labelNode);
    }
  }

  function markSvgTextInsideShape(shape, sourceLabel) {
    const shapeBox = safeBBox(shape);
    const sourceBox = safeBBox(sourceLabel);
    const parent = shape.parentNode;
    if (!shapeBox || !sourceBox || !parent || !parent.querySelectorAll) {
      return;
    }
    const shapeArea = shapeBox.width * shapeBox.height;
    const sourceArea = Math.max(sourceBox.width * sourceBox.height, 1);
    if (shapeArea > Math.max(120000, sourceArea * 80)) {
      return;
    }
    for (const textNode of parent.querySelectorAll("text")) {
      if (textNode.classList.contains("diagram-code-link-badge-text")
        || textNode.classList.contains("diagram-note-marker-text")) {
        continue;
      }
      const textBox = safeBBox(textNode);
      if (!textBox) {
        continue;
      }
      const center = {
        x: textBox.x + textBox.width / 2,
        y: textBox.y + textBox.height / 2,
      };
      const insideShape = center.x >= shapeBox.x
        && center.x <= shapeBox.x + shapeBox.width
        && center.y >= shapeBox.y
        && center.y <= shapeBox.y + shapeBox.height;
      if (!insideShape) {
        continue;
      }
      textNode.classList.add("asset-focus-match", "asset-focus-contained-text");
      for (const child of textNode.querySelectorAll("tspan")) {
        child.classList.add("asset-focus-match", "asset-focus-contained-text");
      }
    }
  }

  function closestSvgObjectShape(labelNode) {
    const box = safeBBox(labelNode);
    const parent = labelNode.parentNode;
    if (!box || !parent || !parent.querySelectorAll) {
      return null;
    }
    const center = {
      x: box.x + box.width / 2,
      y: box.y + box.height / 2,
    };
    let best = null;
    let bestArea = Infinity;
    for (const candidate of parent.querySelectorAll("rect, polygon, path")) {
      if (candidate.classList.contains("diagram-note-box")
        || candidate.classList.contains("diagram-code-link-badge-box")) {
        continue;
      }
      const candidateBox = safeBBox(candidate);
      if (!candidateBox || candidateBox.width < box.width || candidateBox.height < box.height) {
        continue;
      }
      const containsCenter = center.x >= candidateBox.x
        && center.x <= candidateBox.x + candidateBox.width
        && center.y >= candidateBox.y
        && center.y <= candidateBox.y + candidateBox.height;
      if (!containsCenter) {
        continue;
      }
      const area = candidateBox.width * candidateBox.height;
      if (area < bestArea) {
        best = candidate;
        bestArea = area;
      }
    }
    return best;
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

  function scheduleSearch(resetIndex) {
    if (searchRaf) {
      window.cancelAnimationFrame(searchRaf);
    }
    searchRaf = window.requestAnimationFrame(function () {
      searchRaf = 0;
      updateSearch(resetIndex);
    });
  }

  function searchDiagram(query) {
    const lowerQuery = query.toLowerCase();
    const textNodes = content.querySelectorAll("svg text");
    for (const node of textNodes) {
      if (node.textContent.toLowerCase().includes(lowerQuery)) {
        setSvgSearchClass(node, "asset-search-match", true);
        addSvgSearchSubmatches(node, query);
        searchMatches.push(node);
      }
    }
  }

  function addSvgSearchSubmatches(textNode, query) {
    const parent = textNode.parentNode;
    const svg = textNode.ownerSVGElement;
    if (!parent || !svg || !query) {
      return;
    }
    const namespace = svg.namespaceURI || "http://www.w3.org/2000/svg";
    const underlay = document.createElementNS(namespace, "g");
    underlay.classList.add("asset-search-submatch-layer");
    underlay.setAttribute("pointer-events", "none");
    const candidates = svgSearchTextCandidates(textNode, query);
    for (const candidate of candidates) {
      const lowerText = candidate.textContent.toLowerCase();
      const lowerQuery = query.toLowerCase();
      let index = lowerText.indexOf(lowerQuery);
      while (index !== -1) {
        const box = svgTextRangeBox(candidate, index, query.length);
        if (box) {
          const rect = document.createElementNS(namespace, "rect");
          rect.classList.add("asset-search-submatch");
          rect.setAttribute("x", String(box.x - 2.5));
          rect.setAttribute("y", String(box.y - 2));
          rect.setAttribute("width", String(Math.max(2, box.width + 5)));
          rect.setAttribute("height", String(Math.max(2, box.height + 4)));
          rect.setAttribute("rx", "2");
          rect.setAttribute("ry", "2");
          underlay.appendChild(rect);
        }
        index = lowerText.indexOf(lowerQuery, index + Math.max(1, query.length));
      }
    }
    if (underlay.childNodes.length) {
      parent.insertBefore(underlay, textNode);
    }
  }

  function svgSearchTextCandidates(textNode, query) {
    const children = Array.from(textNode.querySelectorAll("tspan, textPath")).filter(function (node) {
      return node.textContent.toLowerCase().includes(query.toLowerCase());
    });
    return children.length ? children : [textNode];
  }

  function svgTextRangeBox(node, start, length) {
    if (
      typeof node.getExtentOfChar !== "function"
      || typeof node.getNumberOfChars !== "function"
    ) {
      return safeBBox(node);
    }
    let box = null;
    const end = Math.min(start + length, node.getNumberOfChars());
    for (let index = start; index < end; index += 1) {
      try {
        const charBox = node.getExtentOfChar(index);
        if (!isFiniteBox(charBox)) {
          continue;
        }
        box = box ? unionBoxes(box, charBox) : charBox;
      } catch (error) {
        return safeBBox(node);
      }
    }
    return box || safeBBox(node);
  }

  function isFiniteBox(box) {
    return box
      && Number.isFinite(box.x)
      && Number.isFinite(box.y)
      && Number.isFinite(box.width)
      && Number.isFinite(box.height);
  }

  function unionBoxes(a, b) {
    const x1 = Math.min(a.x, b.x);
    const y1 = Math.min(a.y, b.y);
    const x2 = Math.max(a.x + a.width, b.x + b.width);
    const y2 = Math.max(a.y + a.height, b.y + b.height);
    return { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
  }

  function setSvgSearchClass(node, className, enabled) {
    setSvgSearchClassOnNode(node, className, enabled);
    for (const child of node.querySelectorAll("tspan, textPath")) {
      setSvgSearchClassOnNode(child, className, enabled);
    }
  }

  function setSvgSearchClassOnNode(node, className, enabled) {
    node.classList.toggle(className, enabled);
    if (enabled || node.classList.contains("asset-search-match") || node.classList.contains("asset-search-current")) {
      applySvgSearchPaint(node, node.classList.contains("asset-search-current"));
    } else {
      restoreSvgSearchPaint(node);
    }
  }

  function applySvgSearchPaint(node, isCurrent) {
    if (!node.classList.contains("asset-search-painted")) {
      node.dataset.assetSearchStyle = node.hasAttribute("style") ? node.getAttribute("style") : "";
      node.classList.add("asset-search-painted");
    }
    node.style.setProperty("fill", isCurrent ? "#ff2a3d" : "#cf222e", "important");
    node.style.setProperty("stroke", "none", "important");
    node.style.setProperty("filter", "none", "important");
  }

  function restoreSvgSearchPaint(node) {
    if (!node.classList.contains("asset-search-painted")) {
      return;
    }
    const previousStyle = node.dataset.assetSearchStyle || "";
    if (previousStyle) {
      node.setAttribute("style", previousStyle);
    } else {
      node.removeAttribute("style");
    }
    delete node.dataset.assetSearchStyle;
    node.classList.remove("asset-search-painted");
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
    let focusTarget = null;
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
        focusTarget = focused[0];
      }
    } else if (mode === "log") {
      renderLogView(searchInput ? searchInput.value : "", activeFocusTerms);
      const firstLine = content.querySelector(".asset-focus-line");
      if (firstLine) {
        focusTarget = firstLine;
      }
    }
    return focusTarget;
  }

  function applyStoryObjectZoom(target, nextZoom) {
    if (!nextZoom) {
      return;
    }
    if (mode === "diagram") {
      setScale(nextZoom);
    }
  }

  function scheduleFocusedArtifactView(target, storyZoom, storyComment) {
    const shouldCenterTarget = Boolean(target && (storyZoom || storyComment));
    window.requestAnimationFrame(function () {
      applyStoryObjectZoom(target, storyZoom || 0);
      window.requestAnimationFrame(function () {
        if (shouldCenterTarget) {
          scrollContainerToElement(content, target, { horizontal: mode !== "log" });
        }
        positionStoryComment(storyComment);
        content.classList.remove("is-preparing-story-view");
      });
    });
  }

  function positionStoryComment(comment) {
    if (!comment) {
      return;
    }
    const margin = 18;
    const contentRect = content.getBoundingClientRect();
    const availableWidth = Math.max(180, contentRect.width - margin * 2);
    const commentWidth = Math.min(520, availableWidth);
    comment.style.width = commentWidth + "px";
    const sideMargin = mode === "log" ? margin + 30 : margin;
    const left = mode === "log"
      ? contentRect.right - commentWidth - sideMargin
      : contentRect.left + margin;
    const top = contentRect.top + margin;
    placeStoryComment(comment, left, top);
  }

  function placeStoryComment(comment, left, top) {
    const margin = 18;
    const contentRect = content.getBoundingClientRect();
    const maxLeft = Math.max(contentRect.left + margin, contentRect.right - comment.offsetWidth - margin);
    const maxTop = Math.max(contentRect.top + margin, contentRect.bottom - comment.offsetHeight - margin);
    comment.style.left = clamp(left, contentRect.left + margin, maxLeft) + "px";
    comment.style.top = clamp(top, contentRect.top + margin, maxTop) + "px";
    comment.classList.add("is-positioned");
  }

  function clamp(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(max, Math.max(min, value));
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

  function scrollContainerToElement(container, element, options) {
    const scrollHorizontal = !options || options.horizontal !== false;
    const containerRect = container.getBoundingClientRect();
    const targetRect = elementViewportRect(element);
    const maxLeft = Math.max(0, container.scrollWidth - container.clientWidth);
    const maxTop = Math.max(0, container.scrollHeight - container.clientHeight);
    if (scrollHorizontal) {
      container.scrollLeft = clamp(
        container.scrollLeft + targetRect.left - containerRect.left - container.clientWidth / 2 + targetRect.width / 2,
        0,
        maxLeft
      );
    }
    container.scrollTop = clamp(
      container.scrollTop + targetRect.top - containerRect.top - container.clientHeight / 2 + targetRect.height / 2,
      0,
      maxTop
    );
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

""" + diagram_code_popover_helpers() + diagram_note_helpers() + """  function showSearchMatch() {
    for (const node of searchMatches) {
      setSvgSearchClass(node, "asset-search-current", false);
    }
    const current = searchMatches[searchIndex];
    if (!current) {
      return;
    }
    setSvgSearchClass(current, "asset-search-current", true);
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

  function openTemplate(prefix, id, nextMode, focusTerms, notes, nextStoryContext, storyZoom) {
    const template = document.getElementById(prefix + "-template-" + id);
    if (!template) {
      return;
    }
    title.textContent = template.dataset.title || "Diagram";
    activeExportName = template.dataset.title || id || nextMode || "asset";
    content.innerHTML = "";
    resetArtifactViewport();
    content.classList.toggle("is-preparing-story-view", Boolean(nextStoryContext || storyZoom));
    const storyComment = createAssetStoryComment(nextStoryContext || null);
    if (storyComment) {
      content.appendChild(storyComment);
    }
    const stage = document.createElement("div");
    stage.className = "diagram-zoom-stage";
    stage.appendChild(template.content.cloneNode(true));
    content.appendChild(stage);
    modal.hidden = false;
    document.body.classList.add("has-diagram-open");
    document.dispatchEvent(new CustomEvent("codex-review-story-layout"));
    if (nextStoryContext && Number.isInteger(nextStoryContext.index)) {
      document.dispatchEvent(new CustomEvent("codex-review-story-artifact", {
        detail: { status: "open", index: nextStoryContext.index },
      }));
    }
    document.body.style.overflow = "hidden";
    setMode(nextMode);
    if (searchInput) {
      searchInput.value = "";
    }
    setInitialDiagramScale();
    const focusTarget = applyFocusTerms(focusTerms || [], notes || []);
	    applyCodeLinks(nextMode === "diagram" ? parseCodeLinks(template.dataset.codeLinks) : []);
	    scheduleFocusedArtifactView(focusTarget, storyZoom || 0, storyComment);
	    requestExtraPaint(modal);
	    if (nextMode === "log" && searchInput) {
	      searchInput.focus();
	    }
  }

  function createAssetStoryComment(nextStoryContext) {
    const commentText = nextStoryContext ? String(nextStoryContext.artifactComment || "") : "";
    if (!commentText) {
      return null;
    }
    const comment = document.createElement("div");
    comment.className = "asset-story-comment";
    const label = document.createElement("strong");
    label.textContent = nextStoryContext.title || "Story note";
    const body = document.createElement("div");
    body.textContent = commentText;
    comment.appendChild(label);
    comment.appendChild(body);
    return comment;
  }

  function storyContextFromTrigger(trigger) {
    const triggerTitle = trigger ? trigger.dataset.storyTitle || "" : "";
    const triggerBody = trigger ? trigger.dataset.storyBody || "" : "";
    const artifactComment = trigger ? trigger.dataset.artifactComment || "" : "";
    const storyIndex = trigger && trigger.dataset.storyIndex ? Number(trigger.dataset.storyIndex) : null;
    return {
      title: triggerTitle,
      body: triggerBody,
      artifactComment: artifactComment,
      index: storyIndex,
    };
  }

  function openDiagram(id, focusTerms, notes, nextStoryContext, storyZoom) {
    openTemplate("diagram", id, "diagram", focusTerms, notes, nextStoryContext, storyZoom);
    if (searchInput) {
      window.setTimeout(function () {
        searchInput.focus();
        searchInput.select();
      }, 0);
    }
  }

  function openLog(id, focusTerms, nextStoryContext, storyZoom) {
    openTemplate("log", id, "log", focusTerms, undefined, nextStoryContext, storyZoom);
  }

  function closeDiagram() {
    modal.hidden = true;
    content.innerHTML = "";
    content.style.removeProperty("--asset-log-scale");
    document.body.style.overflow = "";
    document.body.classList.remove("has-diagram-open");
    document.dispatchEvent(new CustomEvent("codex-review-story-layout"));
	    document.dispatchEvent(new CustomEvent("codex-review-story-artifact", {
	      detail: { status: "closed" },
	    }));
	    requestExtraPaint(document.body);
	    scale = 1;
    initialScale = 1;
    setMode("");
    activeFocusTerms = [];
    activeNotes = [];
    activeCodeLinks = [];
    activeExportName = "asset";
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
        storyContextFromTrigger(preview),
        parseZoom(preview.dataset.diagramZoom)
      );
      return;
    }
    const logPreview = event.target.closest("[data-log-id]");
    if (logPreview) {
      openLog(
        logPreview.dataset.logId,
        parseFocus(logPreview.dataset.logFocus),
        storyContextFromTrigger(logPreview),
        parseZoom(logPreview.dataset.logZoom)
      );
      return;
    }
    if (event.target.closest("[data-diagram-close]")) {
      closeDiagram();
      return;
    }
    const storyMove = event.target.closest("[data-diagram-story-step]");
    if (storyMove) {
      if (storyMove.disabled || storyMove.getAttribute("aria-disabled") === "true") {
        return;
      }
      document.dispatchEvent(new CustomEvent("codex-review-story-move", {
        detail: { direction: storyMove.dataset.diagramStoryStep === "prev" ? -1 : 1 },
      }));
      return;
    }
    const zoom = event.target.closest("[data-diagram-zoom]");
    if (zoom) {
      const action = zoom.dataset.diagramZoom;
      if (action === "in") {
        setScale(scale + 0.1);
      } else if (action === "out") {
        setScale(scale - 0.1);
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
      scheduleSearch(true);
    });
  }

  function handleArtifactWheel(event) {
    clearCodeLinkHover();
    if (modal.hidden || (mode !== "diagram" && mode !== "log")) {
      return false;
    }
    if (event.shiftKey && !event.ctrlKey) {
      event.preventDefault();
      content.scrollLeft += event.deltaX || event.deltaY;
      return true;
    }
    if (!event.ctrlKey) {
      return false;
    }
    event.preventDefault();
    const direction = event.deltaY < 0 ? 1 : -1;
    const step = Math.max(0.06, Math.min(0.18, Math.abs(event.deltaY) / 600));
    zoomAtPoint(scale + (direction * step), event.clientX, event.clientY);
    return true;
  }

  content.addEventListener("wheel", function (event) {
    handleArtifactWheel(event);
  }, { passive: false });

  modal.addEventListener("wheel", function (event) {
    if (modal.hidden || content.contains(event.target) || (mode !== "diagram" && mode !== "log")) {
      return;
    }
    if (handleArtifactWheel(event)) {
      return;
    }
    event.preventDefault();
    content.scrollLeft += event.deltaX;
    content.scrollTop += event.deltaY;
  }, { passive: false });

  content.addEventListener("pointerdown", function (event) {
    if (modal.hidden || mode !== "diagram" || event.button !== 0) {
      return;
    }
    if (event.target.closest("button, input")) {
      return;
    }
    if (event.target.closest("svg text, svg tspan")) {
      clearCodeLinkHover();
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
