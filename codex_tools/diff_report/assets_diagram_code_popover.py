from __future__ import annotations


def diagram_code_popover_helpers() -> str:
    return """  function codeOverlayRoot() {
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

"""
