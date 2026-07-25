from __future__ import annotations


def diagram_export_helpers() -> str:
    return """  function safeFileName(text, extension) {
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

"""
