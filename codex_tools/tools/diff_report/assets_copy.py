from __future__ import annotations

def copy_selection_script() -> str:
    return """<script>
(function () {
  const menu = document.querySelector("[data-copy-markdown-menu]");
  const plainAction = document.querySelector("[data-copy-plain-action]");
  const action = document.querySelector("[data-copy-markdown-action]");
  let activeMarkdown = "";

  function selectionRange() {
    const selection = window.getSelection ? window.getSelection() : null;
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
      return null;
    }
    return selection.getRangeAt(0);
  }

  function intersects(range, node) {
    try {
      return range.intersectsNode(node);
    } catch (error) {
      return false;
    }
  }

  function rowFile(row) {
    const article = row.closest("article.file[data-file]");
    return article ? article.dataset.file || "" : "";
  }

  function selectedTextWithin(range, node) {
    if (!intersects(range, node)) {
      return "";
    }
    const nodeRange = document.createRange();
    nodeRange.selectNodeContents(node);
    const clipped = range.cloneRange();
    if (clipped.compareBoundaryPoints(Range.START_TO_START, nodeRange) < 0) {
      clipped.setStart(nodeRange.startContainer, nodeRange.startOffset);
    }
    if (clipped.compareBoundaryPoints(Range.END_TO_END, nodeRange) > 0) {
      clipped.setEnd(nodeRange.endContainer, nodeRange.endOffset);
    }
    if (clipped.collapsed) {
      return "";
    }
    const wrapper = document.createElement("div");
    wrapper.appendChild(clipped.cloneContents());
    for (const asset of wrapper.querySelectorAll(".diagram-preview-wrap, .log-preview")) {
      asset.remove();
    }
    return wrapper.textContent.trim();
  }

  function commentText(comment, range) {
    const body = comment.classList.contains("file-comment") ? comment : comment.querySelector(".body");
    return body ? selectedTextWithin(range, body) : "";
  }

  function quoteMarkdown(text) {
    if (!text) {
      return "";
    }
    return text.split(/\\r?\\n/).map(function (line) {
      return line ? "> " + line : ">";
    }).join("\\n");
  }

  function fileHeading(file) {
    return "### `" + String(file).replace(/`/g, "\\\\`") + "`";
  }

  function appendBlank(parts) {
    if (parts.length && parts[parts.length - 1] !== "") {
      parts.push("");
    }
  }

  function openFence(parts, state) {
    if (!state.inFence) {
      appendBlank(parts);
      parts.push("```diff");
      state.inFence = true;
    }
  }

  function closeFence(parts, state) {
    if (state.inFence) {
      parts.push("```");
      state.inFence = false;
    }
  }

  function appendFile(parts, state, file) {
    if (state.file === file) {
      return;
    }
    closeFence(parts, state);
    appendBlank(parts);
    parts.push(fileHeading(file || "diff"));
    state.file = file;
  }

  function buildMarkdown(range) {
    const nodes = Array.from(document.querySelectorAll("article.file .file-comment, article.file tr"));
    const selectedNodes = nodes.filter(function (node) {
      return intersects(range, node);
    });
    if (!selectedNodes.length) {
      return "";
    }

    const parts = [];
    const state = { file: null, inFence: false };
    for (const row of selectedNodes) {
      const file = rowFile(row);
      appendFile(parts, state, file);
      if (row.dataset.diffKind) {
        const code = row.querySelector(".code");
        if (code) {
          openFence(parts, state);
          parts.push(code.textContent);
        }
        continue;
      }

      const comment = row.classList.contains("file-comment")
        ? row
        : row.querySelector(".review-comment");
      if (!comment) {
        continue;
      }
      closeFence(parts, state);
      const title = comment.classList.contains("file-comment") ? null : comment.querySelector(".title");
      appendBlank(parts);
      if (title && intersects(range, title) && title.textContent.trim()) {
        parts.push("> **" + title.textContent.trim() + "**");
        parts.push(">");
      }
      const body = quoteMarkdown(commentText(comment, range));
      if (body) {
        parts.push(body);
      }
    }
    closeFence(parts, state);
    return parts.join("\\n").replace(/\\n{3,}/g, "\\n\\n").trim();
  }

  function hideMenu() {
    if (!menu) {
      return;
    }
    menu.hidden = true;
    activeMarkdown = "";
  }

  function fallbackCopy(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } finally {
      textarea.remove();
    }
  }

  function copyMarkdown(text) {
    if (!text) {
      return Promise.resolve(false);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }).catch(function () {
        fallbackCopy(text);
        return true;
      });
    }
    fallbackCopy(text);
    return Promise.resolve(true);
  }

  function copyPlainSelection() {
    if (menu) {
      menu.hidden = true;
    }
    document.execCommand("copy");
    activeMarkdown = "";
  }

  function showMenu(event, markdown) {
    if (!menu) {
      return;
    }
    activeMarkdown = markdown;
    menu.hidden = false;
    const width = menu.offsetWidth || 178;
    const height = menu.offsetHeight || 76;
    const left = Math.min(event.clientX, window.innerWidth - width - 8);
    const top = Math.min(event.clientY, window.innerHeight - height - 8);
    menu.style.left = Math.max(8, left) + "px";
    menu.style.top = Math.max(8, top) + "px";
  }

  document.addEventListener("contextmenu", function (event) {
    const range = selectionRange();
    const markdown = range ? buildMarkdown(range) : "";
    if (!markdown) {
      hideMenu();
      return;
    }
    event.preventDefault();
    showMenu(event, markdown);
  });

  document.addEventListener("selectionchange", function () {
    if (!selectionRange()) {
      hideMenu();
    }
  });
  document.addEventListener("click", function (event) {
    if (menu && menu.contains(event.target)) {
      return;
    }
    hideMenu();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      hideMenu();
    }
  });
  window.addEventListener("scroll", hideMenu, { passive: true });
  window.addEventListener("resize", hideMenu);

  if (plainAction) {
    plainAction.addEventListener("click", function () {
      copyPlainSelection();
    });
  }
  if (action) {
    action.addEventListener("click", function () {
      const markdown = activeMarkdown;
      hideMenu();
      copyMarkdown(markdown);
    });
  }
}());
</script>
"""
