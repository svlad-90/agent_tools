from __future__ import annotations


def feedback_script() -> str:
    return r"""<script>
(function () {
  const ports = [8765, 8766, 8767, 8768, 8769];
  const timeoutMs = 350;
  const feedbackPollMs = 2000;
  const drawioOrigin = "https://embed.diagrams.net";
  const drawioUrl = drawioOrigin + "/?embed=1&proto=json&spin=1&saveAndExit=1&noSaveBtn=0&noExitBtn=0";
  let feedbackServer = null;
  let activeDiagram = null;
  let editorState = null;
  let feedbackProbeInFlight = false;

  const editButton = document.getElementById("diagram-edit");
  const editStatus = document.getElementById("diagram-edit-status");

  function withTimeout(promise, timeoutMs) {
    const timeout = new Promise((_, reject) => {
      window.setTimeout(() => reject(new Error("timeout")), timeoutMs);
    });
    return Promise.race([promise, timeout]);
  }

  async function handshake(port) {
    const url = `http://127.0.0.1:${port}/api/v1/handshake`;
    const response = await withTimeout(fetch(url, { method: "GET", mode: "cors" }), timeoutMs);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    if (!data || data.ok !== true || !Array.isArray(data.capabilities)) {
      throw new Error("invalid handshake");
    }
    return { port, data };
  }

  function artifactUrl(artifact) {
    return `http://127.0.0.1:${feedbackServer.port}/api/v1/artifact?task=${encodeURIComponent(artifact.task)}&path=${encodeURIComponent(artifact.path)}`;
  }

  async function readArtifact(task, path) {
    const response = await fetch(artifactUrl({ task, path }), { method: "GET", mode: "cors" });
    if (!response.ok) {
      throw new Error(`read failed: HTTP ${response.status}`);
    }
    return response.text();
  }

  async function writeArtifact(task, path, text, contentType) {
    const response = await fetch(artifactUrl({ task, path }), {
      method: "PUT",
      mode: "cors",
      headers: { "Content-Type": contentType || "text/plain; charset=utf-8" },
      body: text,
    });
    if (!response.ok) {
      throw new Error(`write failed: HTTP ${response.status}`);
    }
    return response.json();
  }

  function feedbackHasDrawio() {
    return Boolean(feedbackServer && feedbackServer.data.capabilities.includes("drawio"));
  }

  function hideFeedbackStatus() {
    for (const badge of document.querySelectorAll("[data-feedback-capability='drawio']")) {
      badge.remove();
    }
  }

  function showFeedbackStatus(result) {
    if (!result.data.capabilities.includes("drawio")) {
      hideFeedbackStatus();
      return;
    }
    const launcher = document.querySelector(".settings-launcher");
    if (!launcher) {
      return;
    }
    let badge = document.querySelector("[data-feedback-capability='drawio']");
    if (!badge) {
      badge = document.createElement("button");
      badge.type = "button";
      badge.className = "feedback-status";
      badge.dataset.feedbackCapability = "drawio";
      launcher.insertAdjacentElement("beforebegin", badge);
    }
    badge.textContent = "draw.io feedback";
    badge.title = `Diff report feedback server is available on port ${result.port}`;
  }

  function updateEditButton() {
    if (!editButton) {
      return;
    }
    const canEdit = Boolean(
      feedbackHasDrawio()
      && activeDiagram
      && activeDiagram.renderer === "drawio"
      && activeDiagram.sourceTask
      && activeDiagram.sourcePath
      && activeDiagram.svgTask
      && activeDiagram.svgPath
    );
    editButton.hidden = !canEdit;
    editButton.disabled = !canEdit;
    editButton.textContent = "Edit";
    editButton.title = canEdit ? "Edit this diagram with diagrams.net" : "";
    if (editStatus) {
      editStatus.textContent = "";
    }
  }

  function setEditStatus(text) {
    if (editStatus) {
      editStatus.textContent = text || "";
    }
  }

  function ensureEditorShell() {
    let shell = document.getElementById("drawio-editor-shell");
    if (shell) {
      return shell;
    }
    shell = document.createElement("div");
    shell.id = "drawio-editor-shell";
    shell.className = "drawio-editor-shell";
    shell.hidden = true;
    shell.innerHTML = [
      '<div class="drawio-editor-backdrop" data-drawio-cancel></div>',
      '<div class="drawio-editor-dialog" role="dialog" aria-modal="true" aria-labelledby="drawio-editor-title">',
      '  <div class="drawio-editor-toolbar">',
      '    <h2 id="drawio-editor-title">Edit diagram</h2>',
      '    <div class="drawio-editor-actions">',
      '      <span class="drawio-editor-status" data-drawio-status></span>',
      '      <button type="button" data-drawio-cancel>Close</button>',
      '    </div>',
      '  </div>',
      '  <iframe class="drawio-editor-frame" title="diagrams.net editor" sandbox="allow-scripts allow-forms allow-same-origin allow-popups allow-downloads"></iframe>',
      '</div>',
    ].join("");
    document.body.appendChild(shell);
    shell.addEventListener("click", function (event) {
      if (event.target.closest("[data-drawio-cancel]")) {
        closeDrawioEditor();
      }
    });
    return shell;
  }

  function setEditorStatus(text) {
    const shell = ensureEditorShell();
    const status = shell.querySelector("[data-drawio-status]");
    if (status) {
      status.textContent = text || "";
    }
  }

  async function openDrawioEditor() {
    if (!activeDiagram || !feedbackServer) {
      window.alert("Draw.io editing is not ready for this diagram yet.");
      return;
    }
    editButton.disabled = true;
    editButton.textContent = "Opening...";
    setEditStatus("Reading source...");
    try {
      const xml = await readArtifact(activeDiagram.sourceTask, activeDiagram.sourcePath);
      const shell = ensureEditorShell();
      const frame = shell.querySelector("iframe");
      editorState = {
        diagram: activeDiagram,
        frame,
        xml,
        savingXml: "",
      };
      shell.hidden = false;
      document.body.classList.add("has-drawio-editor-open");
      setEditStatus("Editor open");
      setEditorStatus("Loading editor...");
      frame.src = drawioUrl;
    } catch (error) {
      window.alert(`Unable to open draw.io editor: ${error.message || error}`);
      editButton.disabled = false;
      editButton.textContent = "Edit";
      setEditStatus("Open failed");
    }
  }

  function closeDrawioEditor() {
    const shell = document.getElementById("drawio-editor-shell");
    if (shell) {
      const frame = shell.querySelector("iframe");
      if (frame) {
        frame.removeAttribute("src");
      }
      shell.hidden = true;
    }
    document.body.classList.remove("has-drawio-editor-open");
    editorState = null;
    updateEditButton();
    setEditStatus("");
  }

  function postDrawio(message) {
    if (!editorState || !editorState.frame || !editorState.frame.contentWindow) {
      return;
    }
    editorState.frame.contentWindow.postMessage(JSON.stringify(message), drawioOrigin);
  }

  function parseDrawioMessage(event) {
    if (!editorState || event.source !== editorState.frame.contentWindow || event.origin !== drawioOrigin) {
      return null;
    }
    if (typeof event.data === "string") {
      try {
        return JSON.parse(event.data);
      } catch (_error) {
        return null;
      }
    }
    return event.data && typeof event.data === "object" ? event.data : null;
  }

  function svgDataUri(svg) {
    return "data:image/svg+xml;base64," + window.btoa(unescape(encodeURIComponent(svg)));
  }

  function decodeDataUri(data) {
    if (typeof data !== "string" || !data.startsWith("data:image/svg+xml")) {
      return "";
    }
    const comma = data.indexOf(",");
    if (comma < 0) {
      return "";
    }
    const meta = data.slice(0, comma).toLowerCase();
    const payload = data.slice(comma + 1);
    if (meta.includes(";base64")) {
      try {
        return decodeURIComponent(escape(window.atob(payload)));
      } catch (_error) {
        return "";
      }
    }
    try {
      return decodeURIComponent(payload);
    } catch (_error) {
      return payload;
    }
  }

  function exportedSvg(message) {
    if (typeof message.svg === "string" && message.svg.trim()) {
      return sanitizeDrawioSvg(message.svg);
    }
    return sanitizeDrawioSvg(decodeDataUri(message.data));
  }

  function replaceLightDarkColors(text) {
    let result = "";
    let index = 0;
    const marker = "light-dark(";
    while (index < text.length) {
      const start = text.indexOf(marker, index);
      if (start < 0) {
        result += text.slice(index);
        break;
      }
      result += text.slice(index, start);
      let pos = start + marker.length;
      let depth = 1;
      let comma = -1;
      while (pos < text.length && depth > 0) {
        const char = text[pos];
        if (char === "(") {
          depth += 1;
        } else if (char === ")") {
          depth -= 1;
        } else if (char === "," && depth === 1 && comma < 0) {
          comma = pos;
        }
        pos += 1;
      }
      if (depth !== 0 || comma < 0) {
        result += text.slice(start, pos);
      } else {
        result += text.slice(start + marker.length, comma).trim();
      }
      index = pos;
    }
    return result;
  }

  function sanitizeDrawioSvg(svg) {
    if (typeof svg !== "string" || !svg.trim()) {
      return "";
    }
    return replaceLightDarkColors(svg)
      .replace(/\s*color-scheme\s*:\s*light\s+dark\s*;?/gi, "")
      .replace(/@supports\s*\(color:\s*[^)]*\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/gi, "");
  }

  function updateRenderedDiagram(diagramId, svg) {
    const template = document.getElementById("diagram-template-" + diagramId);
    if (template) {
      template.innerHTML = svg;
    }
    const uri = svgDataUri(svg);
    for (const preview of document.querySelectorAll("[data-diagram-id]")) {
      if (preview.dataset.diagramId !== diagramId) {
        continue;
      }
      for (const img of preview.querySelectorAll(".diagram-preview-canvas img")) {
        img.src = uri;
      }
    }
    const opened = document.querySelector("#diagram-modal:not([hidden]) .diagram-zoom-stage");
    if (opened && activeDiagram && activeDiagram.diagramId === diagramId) {
      opened.innerHTML = svg;
    }
  }

  async function saveDrawio(xml, svg) {
    if (!editorState || !editorState.diagram) {
      return;
    }
    const diagram = editorState.diagram;
    setEditorStatus("Saving...");
    await writeArtifact(diagram.sourceTask, diagram.sourcePath, xml, "application/xml; charset=utf-8");
    await writeArtifact(diagram.svgTask, diagram.svgPath, svg, "image/svg+xml; charset=utf-8");
    updateRenderedDiagram(diagram.diagramId, svg);
    setEditorStatus("Saved");
    closeDrawioEditor();
  }

  function handleDrawioMessage(event) {
    const message = parseDrawioMessage(event);
    if (!message) {
      return;
    }
    if (message.event === "init") {
      setEditorStatus("Loading diagram...");
      postDrawio({
        action: "load",
        autosave: 0,
        modified: "unsavedChanges",
        saveAndExit: "1",
        xml: editorState.xml,
      });
      return;
    }
    if (message.event === "save") {
      editorState.savingXml = message.xml || editorState.xml;
      setEditorStatus("Exporting SVG...");
      postDrawio({
        action: "export",
        format: "svg",
        embedImages: true,
        xml: editorState.savingXml,
      });
      return;
    }
    if (message.event === "export") {
      const svg = exportedSvg(message);
      if (!svg) {
        window.alert("draw.io did not return SVG data");
        setEditorStatus("Export failed");
        return;
      }
      saveDrawio(editorState.savingXml || editorState.xml, svg).catch(function (error) {
        window.alert(`Unable to save diagram: ${error.message || error}`);
        setEditorStatus("Save failed");
      });
      return;
    }
    if (message.event === "exit") {
      closeDrawioEditor();
    }
  }

  async function discoverFeedbackServer() {
    if (feedbackProbeInFlight) {
      return;
    }
    feedbackProbeInFlight = true;
    updateEditButton();
    try {
      const probePorts = feedbackServer
        ? [feedbackServer.port].concat(ports.filter(function (port) { return port !== feedbackServer.port; }))
        : ports;
      for (const port of probePorts) {
        try {
          const result = await handshake(port);
          feedbackServer = result;
          showFeedbackStatus(result);
          updateEditButton();
          return;
        } catch (_error) {
          continue;
        }
      }
      feedbackServer = null;
      hideFeedbackStatus();
      updateEditButton();
    } finally {
      feedbackProbeInFlight = false;
    }
  }

  function startFeedbackDiscovery() {
    discoverFeedbackServer();
    window.setInterval(discoverFeedbackServer, feedbackPollMs);
    window.addEventListener("focus", discoverFeedbackServer);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) {
        discoverFeedbackServer();
      }
    });
  }

  document.addEventListener("codex-review-diagram-opened", function (event) {
    activeDiagram = event.detail || null;
    updateEditButton();
  });
  document.addEventListener("codex-review-diagram-closed", function () {
    activeDiagram = null;
    updateEditButton();
  });
  window.codexOpenDrawioEditor = function (event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    openDrawioEditor();
  };
  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-diagram-edit]")) {
      event.preventDefault();
      event.stopPropagation();
      openDrawioEditor();
    }
  }, true);
  window.addEventListener("message", handleDrawioMessage);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startFeedbackDiscovery, { once: true });
  } else {
    startFeedbackDiscovery();
  }
})();
</script>
"""
