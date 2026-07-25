from __future__ import annotations


def diagram_note_helpers() -> str:
    return """  function isDiagramNoteTarget(node, notes) {
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

"""
