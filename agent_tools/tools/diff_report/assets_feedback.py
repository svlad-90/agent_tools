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

  function agentDiagramUrl(diagram) {
    return (
      `http://127.0.0.1:${feedbackServer.port}/api/v1/agent-diagram/source`
      + `?task=${encodeURIComponent(diagram.commentsTask)}`
      + `&comments=${encodeURIComponent(diagram.commentsPath)}`
      + `&diagram=${encodeURIComponent(diagram.commentsDiagram)}`
    );
  }

  function agentDiagramPreviewUrl(diagram) {
    return (
      `http://127.0.0.1:${feedbackServer.port}/api/v1/agent-diagram/preview`
      + `?task=${encodeURIComponent(diagram.commentsTask)}`
      + `&comments=${encodeURIComponent(diagram.commentsPath)}`
      + `&diagram=${encodeURIComponent(diagram.commentsDiagram)}`
    );
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

  function feedbackHas(capability) {
    return Boolean(feedbackServer && feedbackServer.data.capabilities.includes(capability));
  }

  function feedbackHasDrawio() {
    return feedbackHas("drawio");
  }

  function feedbackHasAgentDiagram() {
    return feedbackHas("agent_diagram");
  }

  function feedbackHasAgentDiagramPreview() {
    return feedbackHas("agent_diagram_preview");
  }

  function hideFeedbackStatus() {
    for (const badge of document.querySelectorAll("[data-feedback-capability='diagram-feedback']")) {
      badge.remove();
    }
  }

  function showFeedbackStatus(result) {
    const diagramCapabilities = result.data.capabilities.filter(function (capability) {
      return capability === "drawio"
        || capability === "agent_diagram"
        || capability === "agent_diagram_plantuml"
        || capability === "agent_diagram_preview";
    });
    if (!diagramCapabilities.length) {
      hideFeedbackStatus();
      return;
    }
    const launcher = document.querySelector(".settings-launcher");
    if (!launcher) {
      return;
    }
    let badge = document.querySelector("[data-feedback-capability='diagram-feedback']");
    if (!badge) {
      badge = document.createElement("button");
      badge.type = "button";
      badge.className = "feedback-status";
      badge.dataset.feedbackCapability = "diagram-feedback";
      launcher.insertAdjacentElement("beforebegin", badge);
    }
    badge.textContent = "diagram feedback";
    badge.title = `Diff report feedback server is available on port ${result.port}: ${diagramCapabilities.join(", ")}`;
  }

  function updateEditButton() {
    if (!editButton) {
      return;
    }
    const canEditDrawio = Boolean(
      feedbackHasDrawio()
      && activeDiagram
      && activeDiagram.renderer === "drawio"
      && activeDiagram.sourceTask
      && activeDiagram.sourcePath
      && activeDiagram.svgTask
      && activeDiagram.svgPath
    );
    const canEditAgentDiagram = Boolean(
      feedbackHasAgentDiagram()
      && activeDiagram
      && activeDiagram.commentsTask
      && activeDiagram.commentsPath
      && activeDiagram.commentsDiagram
    );
    const canEdit = canEditDrawio || canEditAgentDiagram;
    editButton.hidden = !canEdit;
    editButton.disabled = !canEdit;
    editButton.textContent = canEditAgentDiagram ? "Edit" : "Edit";
    editButton.title = canEditAgentDiagram
      ? "Edit this agent_diagram diagram and re-render the SVG"
      : (canEditDrawio ? "Edit this diagram with diagrams.net" : "");
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

  function ensureAgentDiagramEditorShell() {
    let shell = document.getElementById("plantuml-editor-shell");
    if (shell) {
      return shell;
    }
    shell = document.createElement("div");
    shell.id = "plantuml-editor-shell";
    shell.className = "plantuml-editor-shell";
    shell.hidden = true;
    shell.innerHTML = [
      '<div class="plantuml-editor-backdrop" data-plantuml-cancel></div>',
      '<div class="plantuml-editor-dialog" role="dialog" aria-modal="true" aria-labelledby="plantuml-editor-title">',
      '  <div class="plantuml-editor-toolbar">',
      '    <h2 id="plantuml-editor-title">Edit agent_diagram</h2>',
      '    <div class="plantuml-editor-actions">',
      '      <span class="plantuml-editor-status" data-plantuml-status></span>',
      '      <button type="button" data-plantuml-preview>Validate / Preview</button>',
      '      <button type="button" data-plantuml-save>Save</button>',
      '      <button type="button" data-plantuml-cancel>Close</button>',
      '    </div>',
      '  </div>',
      '  <div class="agent-diagram-editor-form" data-agent-diagram-form></div>',
      '  <div class="plantuml-editor-workspace">',
      '    <textarea class="plantuml-editor-source" spellcheck="false" data-plantuml-source></textarea>',
      '    <div class="plantuml-editor-preview" data-plantuml-preview-panel hidden></div>',
      '  </div>',
      '</div>',
    ].join("");
    document.body.appendChild(shell);
    shell.addEventListener("click", function (event) {
      if (event.target.closest("[data-plantuml-cancel]")) {
        closeAgentDiagramEditor();
        return;
      }
      if (event.target.closest("[data-plantuml-save]")) {
        saveAgentDiagramEditor().catch(function (error) {
          handleAgentDiagramEditorError(error, "Save failed");
          window.alert(`Unable to save agent_diagram JSON: ${error.message || error}`);
        });
      }
      if (event.target.closest("[data-plantuml-preview]")) {
        previewAgentDiagramEditor().catch(function (error) {
          handleAgentDiagramEditorError(error, "Preview failed");
        });
      }
    });
    shell.addEventListener("input", function (event) {
      if (event.target.closest("[data-plantuml-source]")) {
        validateAgentDiagramEditor();
        highlightPlantumlPreviewFromCursor();
      }
    });
    shell.addEventListener("keyup", function (event) {
      if (event.target.closest("[data-plantuml-source]")) {
        highlightPlantumlPreviewFromCursor();
      }
    });
    shell.addEventListener("mouseup", function (event) {
      if (event.target.closest("[data-plantuml-source]")) {
        highlightPlantumlPreviewFromCursor();
      }
    });
    document.addEventListener("selectionchange", function () {
      if (!editorState || editorState.sourceFormat !== "plantuml") {
        return;
      }
      if (document.activeElement && document.activeElement.matches("[data-plantuml-source]")) {
        highlightPlantumlPreviewFromCursor();
      }
    });
    return shell;
  }

  function cloneJson(value) {
    return JSON.parse(JSON.stringify(value || {}));
  }

  function updateAgentDiagramJsonPreview() {
    const shell = document.getElementById("plantuml-editor-shell");
    if (!shell || !editorState || !editorState.draft) {
      return;
    }
    const textarea = shell.querySelector("[data-plantuml-source]");
    if (textarea) {
      textarea.value = JSON.stringify(editorState.draft, null, 2);
    }
  }

  function renderAgentDiagramForm() {
    const shell = ensureAgentDiagramEditorShell();
    const title = shell.querySelector("#plantuml-editor-title");
    if (title && editorState) {
      title.textContent = editorState.sourceFormat === "plantuml"
        ? "Edit agent_diagram PlantUML"
        : "Edit agent_diagram JSON";
    }
    const form = shell.querySelector("[data-agent-diagram-form]");
    if (!form || !editorState || !editorState.draft) {
      return;
    }
    form.innerHTML = "";
    const toolbar = document.createElement("div");
    toolbar.className = "agent-diagram-json-toolbar";
    if (editorState.sourceFormat === "plantuml") {
      toolbar.appendChild(schemaButton("Reset from JSON", function () {
        setPlantumlEditorText(editorState.sourceText || "");
      }));
      const badge = document.createElement("span");
      badge.className = "agent-diagram-schema-badge";
      badge.textContent = "PlantUML -> JSON";
      toolbar.appendChild(badge);
      form.appendChild(toolbar);
      const validation = document.createElement("div");
      validation.className = "agent-diagram-validation";
      validation.dataset.agentDiagramValidation = "true";
      validation.textContent = feedbackHasAgentDiagramPreview()
        ? "Edit the generated PlantUML subset; Save will translate it back to agent_diagram JSON."
        : "Edit and Save are available. Restart Agent Workspace to enable PlantUML preview.";
      form.appendChild(validation);
      updatePlantumlPreviewControl();
      return;
    }
    const type = agentDiagramEntryType(editorState.draft);
    toolbar.appendChild(schemaButton("Format", function () {
      setAgentDiagramText(editorState.draft);
    }));
    if (type !== "variant") {
      toolbar.appendChild(schemaButton("Add node/type", function () { addAgentDiagramSnippet("node"); }));
      toolbar.appendChild(schemaButton("Add edge/relation", function () { addAgentDiagramSnippet("edge"); }));
    }
    toolbar.appendChild(schemaButton("Add note", function () { addAgentDiagramSnippet("note"); }));
    toolbar.appendChild(schemaButton("Add focus", function () { addAgentDiagramSnippet("focus"); }));
    if (type === "sequence_flow") {
      toolbar.appendChild(schemaButton("Add message", function () { addAgentDiagramSnippet("message"); }));
      toolbar.appendChild(schemaButton("Add block", function () { addAgentDiagramSnippet("block"); }));
    }
    const badge = document.createElement("span");
    badge.className = "agent-diagram-schema-badge";
    badge.textContent = type || "variant";
    toolbar.appendChild(badge);
    form.appendChild(toolbar);
    const validation = document.createElement("div");
    validation.className = "agent-diagram-validation";
    validation.dataset.agentDiagramValidation = "true";
    form.appendChild(validation);
    updatePlantumlPreviewControl();
    updateAgentDiagramJsonPreview();
    validateAgentDiagramEditor();
  }

  function schemaButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function setAgentDiagramText(value) {
    const shell = ensureAgentDiagramEditorShell();
    const textarea = shell.querySelector("[data-plantuml-source]");
    editorState.draft = value;
    textarea.value = JSON.stringify(value, null, 2);
    validateAgentDiagramEditor();
  }

  function setPlantumlEditorText(value) {
    const shell = ensureAgentDiagramEditorShell();
    const textarea = shell.querySelector("[data-plantuml-source]");
    textarea.value = value || "";
  }

  function currentAgentDiagramText() {
    const shell = ensureAgentDiagramEditorShell();
    return shell.querySelector("[data-plantuml-source]").value;
  }

  function updatePlantumlPreviewControl() {
    const shell = document.getElementById("plantuml-editor-shell");
    if (!shell) {
      return;
    }
    const preview = shell.querySelector("[data-plantuml-preview]");
    if (!preview) {
      return;
    }
    const canPreview = Boolean(editorState)
      && editorState.sourceFormat === "plantuml"
      && feedbackHasAgentDiagramPreview();
    preview.hidden = !canPreview;
    preview.disabled = !canPreview;
  }

  function parseAgentDiagramEditor() {
    const value = JSON.parse(currentAgentDiagramText());
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("top-level diagram entry must be an object");
    }
    return value;
  }

  function validateAgentDiagramEditor() {
    const shell = document.getElementById("plantuml-editor-shell");
    if (!shell) {
      return false;
    }
    if (editorState && editorState.sourceFormat === "plantuml") {
      const save = shell.querySelector("[data-plantuml-save]");
      if (save) {
        save.disabled = false;
      }
      updatePlantumlPreviewControl();
      return true;
    }
    const validation = shell.querySelector("[data-agent-diagram-validation]");
    let messages = [];
    try {
      const value = parseAgentDiagramEditor();
      messages = validateAgentDiagramEntry(value);
      if (!messages.length) {
        editorState.draft = value;
      }
    } catch (error) {
      messages = [error.message || String(error)];
    }
    if (validation) {
      validation.textContent = messages.length ? messages.join("; ") : "Valid supported agent_diagram JSON";
      validation.classList.toggle("is-error", Boolean(messages.length));
    }
    const save = shell.querySelector("[data-plantuml-save]");
    if (save) {
      save.disabled = Boolean(messages.length);
    }
    return !messages.length;
  }

  function agentDiagramEntryType(entry) {
    if (entry && entry.variant_of) {
      return "variant";
    }
    return entry && entry.agent_diagram && entry.agent_diagram.type ? entry.agent_diagram.type : "";
  }

  function addAgentDiagramSnippet(kind) {
    let entry;
    try {
      entry = parseAgentDiagramEditor();
    } catch (_error) {
      validateAgentDiagramEditor();
      return;
    }
    if (entry.variant_of) {
      if (kind === "note") {
        (entry.notes || (entry.notes = [])).push({ of: "", position: "right", text: "" });
      } else if (kind === "focus") {
        (entry.focus || (entry.focus = [])).push("");
      }
      setAgentDiagramText(entry);
      return;
    }
    const spec = entry.agent_diagram;
    if (!spec || typeof spec !== "object") {
      return;
    }
    const type = spec.type || "component_graph";
    if (kind === "node") {
      if (type === "class_model") {
        (spec.classes || (spec.classes = [])).push({ id: "", label: "", kind: "class", fields: [], methods: [] });
      } else if (type === "sequence_flow") {
        (spec.participants || (spec.participants = [])).push({ id: "", label: "", kind: "participant" });
      } else {
        (spec.nodes || (spec.nodes = [])).push({ id: "", label: "", kind: "component" });
      }
    } else if (kind === "edge") {
      if (type === "class_model") {
        (spec.relationships || (spec.relationships = [])).push({ from: "", to: "", kind: "association" });
      } else {
        (spec.edges || (spec.edges = [])).push({ from: "", to: "", label: "" });
      }
    } else if (kind === "note") {
      (spec.notes || (spec.notes = [])).push({ of: "", position: "right", text: "" });
    } else if (kind === "focus") {
      (spec.focus || (spec.focus = [])).push("");
    } else if (kind === "message" && type === "sequence_flow") {
      (spec.steps || (spec.steps = [])).push({ from: "", to: "", message: "", kind: "sync" });
    } else if (kind === "block" && type === "sequence_flow") {
      (spec.steps || (spec.steps = [])).push({ loop: { condition: "", steps: [] } });
    }
    setAgentDiagramText(entry);
  }

  function validateAgentDiagramEntry(entry) {
    const errors = [];
    const entryKeys = entry.variant_of
      ? ["variant_of", "title", "source", "svg", "focus", "notes"]
      : ["title", "source", "svg", "agent_diagram"];
    rejectUnknownKeys(entry, entryKeys, "entry", errors);
    if (entry.variant_of) {
      validateArray(entry.focus, "entry.focus", errors, validateFocusItem);
      validateArray(entry.notes, "entry.notes", errors, validateNote);
      return errors;
    }
    if (!entry.agent_diagram || typeof entry.agent_diagram !== "object" || Array.isArray(entry.agent_diagram)) {
      errors.push("entry.agent_diagram must be an object");
      return errors;
    }
    validateAgentDiagramSpec(entry.agent_diagram, errors);
    return errors;
  }

  function validateAgentDiagramSpec(spec, errors) {
    const type = spec.type;
    if (!["component_graph", "sequence_flow", "class_model"].includes(type)) {
      errors.push("agent_diagram.type must be component_graph, sequence_flow, or class_model");
      return;
    }
    if (type === "component_graph") {
      rejectUnknownKeys(spec, ["type", "title", "direction", "layout", "groups", "nodes", "edges", "focus", "notes", "annotations"], "agent_diagram", errors);
      validateArray(spec.groups, "groups", errors, validateGroup);
      validateArray(spec.nodes, "nodes", errors, validateComponentNode);
      validateArray(spec.edges, "edges", errors, validateComponentEdge);
    } else if (type === "sequence_flow") {
      rejectUnknownKeys(spec, ["type", "title", "participants", "steps", "focus", "notes", "annotations"], "agent_diagram", errors);
      validateArray(spec.participants, "participants", errors, validateParticipant);
      validateArray(spec.steps, "steps", errors, validateSequenceStep);
    } else {
      rejectUnknownKeys(spec, ["type", "title", "packages", "classes", "types", "relationships", "edges", "focus", "notes", "annotations"], "agent_diagram", errors);
      validateArray(spec.packages, "packages", errors, validateGroup);
      validateArray(spec.classes || spec.types, "classes", errors, validateClassNode);
      validateArray(spec.relationships || spec.edges, "relationships", errors, validateClassRelationship);
    }
    validateArray(spec.focus, "focus", errors, validateFocusItem);
    validateArray(spec.notes || spec.annotations, "notes", errors, validateNote);
  }

  function rejectUnknownKeys(value, allowed, path, errors) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return;
    }
    for (const key of Object.keys(value)) {
      if (!allowed.includes(key)) {
        errors.push(`${path}.${key} is not supported`);
      }
    }
  }

  function validateArray(value, path, errors, validator) {
    if (value === undefined) {
      return;
    }
    if (!Array.isArray(value)) {
      errors.push(`${path} must be an array`);
      return;
    }
    value.forEach(function (item, index) {
      validator(item, `${path}[${index}]`, errors);
    });
  }

  function validateGroup(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["id", "label"], path, errors);
  }

  function validateComponentNode(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["id", "label", "kind", "type", "group", "focus", "code"], path, errors);
    validateCode(item.code, `${path}.code`, errors);
  }

  function validateComponentEdge(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["from", "to", "label", "direction", "dashed", "focus", "code"], path, errors);
    validateCode(item.code, `${path}.code`, errors);
  }

  function validateParticipant(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["id", "label", "kind", "type", "focus", "code"], path, errors);
    validateCode(item.code, `${path}.code`, errors);
  }

  function validateSequenceStep(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["from", "to", "message", "label", "kind", "type", "activate", "deactivate", "focus", "code", "note", "of", "position", "text", "alt", "opt", "loop", "par", "group"], path, errors);
    validateCode(item.code, `${path}.code`, errors);
    for (const key of ["alt", "par"]) {
      if (item[key] !== undefined) {
        validateArray(item[key], `${path}.${key}`, errors, function (branch, branchPath, branchErrors) {
          if (!mustObject(branch, branchPath, branchErrors)) {
            return;
          }
          rejectUnknownKeys(branch, ["condition", "label", "steps"], branchPath, branchErrors);
          validateArray(branch.steps, `${branchPath}.steps`, branchErrors, validateSequenceStep);
        });
      }
    }
    for (const key of ["opt", "loop", "group"]) {
      if (item[key] !== undefined) {
        if (!mustObject(item[key], `${path}.${key}`, errors)) {
          return;
        }
        rejectUnknownKeys(item[key], ["condition", "label", "title", "steps"], `${path}.${key}`, errors);
        validateArray(item[key].steps, `${path}.${key}.steps`, errors, validateSequenceStep);
      }
    }
  }

  function validateClassNode(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["id", "label", "kind", "type", "package", "fields", "methods", "focus", "code"], path, errors);
    validateArray(item.fields, `${path}.fields`, errors, validateStringItem);
    validateArray(item.methods, `${path}.methods`, errors, validateStringItem);
    validateCode(item.code, `${path}.code`, errors);
  }

  function validateClassRelationship(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["from", "to", "kind", "type", "label", "focus", "code"], path, errors);
    validateCode(item.code, `${path}.code`, errors);
  }

  function validateFocusItem(item, path, errors) {
    if (typeof item === "string") {
      return;
    }
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["from", "to", "label", "message"], path, errors);
  }

  function validateNote(item, path, errors) {
    if (!mustObject(item, path, errors)) {
      return;
    }
    rejectUnknownKeys(item, ["of", "position", "text", "note"], path, errors);
  }

  function validateCode(code, path, errors) {
    if (code === undefined) {
      return;
    }
    if (!mustObject(code, path, errors)) {
      return;
    }
    rejectUnknownKeys(code, ["file", "line", "title", "range"], path, errors);
  }

  function mustObject(value, path, errors) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      errors.push(`${path} must be an object`);
      return false;
    }
    return true;
  }

  function validateStringItem(item, path, errors) {
    if (typeof item !== "string") {
      errors.push(`${path} must be a string`);
    }
  }

  function setAgentDiagramEditorStatus(text) {
    const shell = ensureAgentDiagramEditorShell();
    const status = shell.querySelector("[data-plantuml-status]");
    if (status) {
      status.textContent = text || "";
    }
  }

  async function readAgentDiagram(diagram) {
    const response = await fetch(agentDiagramUrl(diagram), { method: "GET", mode: "cors" });
    if (!response.ok) {
      throw new Error(`read failed: HTTP ${response.status}`);
    }
    return response.json();
  }

  async function writeAgentDiagram(diagram, value) {
    const body = value && value.source_format === "plantuml" ? value : { value };
    const response = await fetch(agentDiagramUrl(diagram), {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      let message = `write failed: HTTP ${response.status}`;
      let diagnosticSvg = "";
      try {
        const errorData = await response.json();
        if (errorData && errorData.error) {
          message = errorData.error;
        }
        if (errorData && errorData.svg) {
          diagnosticSvg = errorData.svg;
        }
      } catch (_error) {
        // Keep the HTTP status fallback.
      }
      const error = new Error(message);
      error.svg = diagnosticSvg;
      throw error;
    }
    return response.json();
  }

  async function previewAgentDiagram(diagram, value) {
    if (!feedbackHasAgentDiagramPreview()) {
      throw new Error("Preview endpoint is not available; restart Agent Workspace so the feedback server reloads.");
    }
    const body = value && value.source_format === "plantuml" ? value : { value };
    const response = await fetch(agentDiagramPreviewUrl(diagram), {
      method: "POST",
      mode: "cors",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      let message = `preview failed: HTTP ${response.status}`;
      let diagnosticSvg = "";
      try {
        const errorData = await response.json();
        if (errorData && errorData.error) {
          message = errorData.error;
        }
        if (errorData && errorData.svg) {
          diagnosticSvg = errorData.svg;
        }
      } catch (_error) {
        // Keep the HTTP status fallback.
      }
      if (response.status === 404 && message === "not found") {
        message = "Preview endpoint is not available; restart Agent Workspace so the feedback server reloads.";
      }
      const error = new Error(message);
      error.svg = diagnosticSvg;
      throw error;
    }
    return response.json();
  }

  async function previewAgentDiagramEditor() {
    if (!editorState || !editorState.diagram) {
      return;
    }
    if (!feedbackHasAgentDiagramPreview()) {
      throw new Error("Preview endpoint is not available; restart Agent Workspace so the feedback server reloads.");
    }
    let value;
    if (editorState.sourceFormat === "plantuml") {
      value = { source_format: "plantuml", source: currentAgentDiagramText() };
    } else {
      if (!validateAgentDiagramEditor()) {
        throw new Error("Fix JSON validation errors before preview.");
      }
      value = parseAgentDiagramEditor();
    }
    setAgentDiagramEditorStatus("Rendering preview...");
    setAgentDiagramPreviewPending();
    const rendered = await previewAgentDiagram(editorState.diagram, value);
    setAgentDiagramPreviewSvg(rendered.svg || "");
    setAgentDiagramEditorStatus("Preview ready");
  }

  function setAgentDiagramPreviewPending() {
    const shell = ensureAgentDiagramEditorShell();
    const panel = shell.querySelector("[data-plantuml-preview-panel]");
    if (!panel) {
      return;
    }
    panel.hidden = false;
    panel.classList.remove("is-error");
    panel.classList.add("is-pending");
    panel.textContent = "Rendering preview...";
  }

  function setAgentDiagramPreviewSvg(svg) {
    const shell = ensureAgentDiagramEditorShell();
    const panel = shell.querySelector("[data-plantuml-preview-panel]");
    if (!panel) {
      return;
    }
    panel.hidden = false;
    panel.classList.remove("is-error");
    panel.classList.remove("is-pending");
    panel.innerHTML = svg || "";
    installPlantumlPreviewTrace(panel);
    highlightPlantumlPreviewFromCursor();
  }

  function installPlantumlPreviewTrace(panel) {
    const svg = panel.querySelector("svg");
    if (!svg) {
      return;
    }
    svg.addEventListener("click", function (event) {
      const trace = resolvePlantumlPreviewTrace(event.target, svg);
      if (!trace) {
        setAgentDiagramEditorStatus("Preview ready");
        return;
      }
      if (selectPlantumlSourceTrace(trace)) {
        setAgentDiagramEditorStatus("Selected source for preview element");
      } else {
        setAgentDiagramEditorStatus("No matching PlantUML source line found");
      }
    });
  }

  function resolvePlantumlPreviewTrace(target, svg) {
    if (!target || !svg.contains(target)) {
      return null;
    }
    let element = target.nodeType === Node.ELEMENT_NODE ? target : target.parentElement;
    while (element && element !== svg) {
      const edgeId = plantumlPreviewEdgeId(element);
      if (edgeId) {
        const parts = edgeId.split(/-+>|--?>/);
        if (parts.length === 2 && parts[0] && parts[1]) {
          return { kind: "edge", from: parts[0], to: parts[1] };
        }
      }
      const commentAlias = plantumlPreviewCommentAlias(element);
      if (commentAlias) {
        return { kind: "alias", value: commentAlias };
      }
      if (element.tagName && element.tagName.toLowerCase() === "text") {
        const text = element.textContent.trim();
        if (text) {
          return { kind: "text", value: text };
        }
      }
      element = element.parentElement;
    }
    const nearbyText = nearestPlantumlPreviewText(target, svg);
    return nearbyText ? { kind: "text", value: nearbyText } : null;
  }

  function plantumlPreviewEdgeId(element) {
    const rawId = element.getAttribute && element.getAttribute("id");
    if (!rawId || !rawId.includes("->")) {
      return "";
    }
    const textarea = document.createElement("textarea");
    textarea.innerHTML = rawId;
    return textarea.value;
  }

  function plantumlPreviewCommentAlias(element) {
    let sibling = element.previousSibling;
    let scanned = 0;
    while (sibling && scanned < 6) {
      if (sibling.nodeType === Node.COMMENT_NODE) {
        const match = sibling.data.match(/\b(?:entity|class|interface|database|actor|component|participant|boundary|control|collections|queue|cluster)\s+([A-Za-z0-9_.:-]+)/);
        if (match) {
          return match[1];
        }
      } else if (sibling.nodeType === Node.ELEMENT_NODE) {
        scanned += 1;
      }
      sibling = sibling.previousSibling;
    }
    return "";
  }

  function nearestPlantumlPreviewText(target, svg) {
    if (!target || !target.getBoundingClientRect) {
      return "";
    }
    const box = target.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    let best = null;
    for (const text of svg.querySelectorAll("text")) {
      const label = text.textContent.trim();
      if (!label) {
        continue;
      }
      const textBox = text.getBoundingClientRect();
      const textX = textBox.left + textBox.width / 2;
      const textY = textBox.top + textBox.height / 2;
      const distance = Math.abs(textX - x) + Math.abs(textY - y);
      if (!best || distance < best.distance) {
        best = { distance, label };
      }
    }
    return best && best.distance < 180 ? best.label : "";
  }

  function selectPlantumlSourceTrace(trace) {
    const shell = ensureAgentDiagramEditorShell();
    const textarea = shell.querySelector("[data-plantuml-source]");
    if (!textarea) {
      return false;
    }
    const source = textarea.value;
    const range = findPlantumlSourceTraceRange(source, trace);
    if (!range) {
      return false;
    }
    textarea.focus();
    textarea.setSelectionRange(range.start, range.end);
    const before = source.slice(0, range.start);
    const line = before.split("\n").length;
    const lineHeight = parseFloat(window.getComputedStyle(textarea).lineHeight) || 20;
    textarea.scrollTop = Math.max(0, (line - 4) * lineHeight);
    highlightPlantumlPreviewTrace(trace);
    return true;
  }

  function highlightPlantumlPreviewFromCursor() {
    if (!editorState || editorState.sourceFormat !== "plantuml") {
      return;
    }
    const shell = document.getElementById("plantuml-editor-shell");
    if (!shell) {
      return;
    }
    const textarea = shell.querySelector("[data-plantuml-source]");
    if (!textarea) {
      return;
    }
    if (textarea.selectionStart !== textarea.selectionEnd) {
      const source = textarea.value;
      const selection = source.slice(textarea.selectionStart, textarea.selectionEnd);
      for (const line of selection.split("\n")) {
        const selectedTrace = plantumlTraceFromSourceLine(line);
        if (selectedTrace && highlightPlantumlPreviewTrace(selectedTrace)) {
          return;
        }
      }
    }
    const line = currentTextareaLine(textarea);
    const trace = plantumlTraceFromSourceLine(line);
    highlightPlantumlPreviewTrace(trace);
  }

  function currentTextareaLine(textarea) {
    const source = textarea.value;
    const cursor = textarea.selectionStart || 0;
    const start = source.lastIndexOf("\n", Math.max(0, cursor - 1)) + 1;
    let end = source.indexOf("\n", cursor);
    if (end === -1) {
      end = source.length;
    }
    return source.slice(start, end);
  }

  function plantumlTraceFromSourceLine(line) {
    const trimmed = String(line || "").trim();
    if (!trimmed || trimmed.startsWith("'") || trimmed.startsWith("@") || trimmed === "}") {
      return null;
    }
    if (/^(skinparam|top to bottom direction|left to right direction)\b/.test(trimmed)) {
      return null;
    }
    const edge = trimmed.match(/^([A-Za-z0-9_.:-]+)\s+[-.#A-Za-z0-9\\[\\]]*(?:--?|\\.\\.?|=+)>+\s*([A-Za-z0-9_.:-]+)/);
    if (edge) {
      return { kind: "edge", from: edge[1], to: edge[2] };
    }
    const alias = trimmed.match(/\bas\s+([A-Za-z0-9_.:-]+)/);
    if (alias) {
      return { kind: "alias", value: alias[1] };
    }
    const packageAlias = trimmed.match(/^package\s+"[^"]+"\s+as\s+([A-Za-z0-9_.:-]+)/);
    if (packageAlias) {
      return { kind: "alias", value: packageAlias[1] };
    }
    const quoted = trimmed.match(/"([^"]+)"/);
    if (quoted) {
      return { kind: "text", value: quoted[1] };
    }
    const label = trimmed.match(/:\s*(.+)$/);
    if (label) {
      return { kind: "text", value: label[1].trim() };
    }
    return { kind: "text", value: trimmed };
  }

  function highlightPlantumlPreviewTrace(trace) {
    const shell = document.getElementById("plantuml-editor-shell");
    if (!shell) {
      return false;
    }
    const panel = shell.querySelector("[data-plantuml-preview-panel]");
    const svg = panel ? panel.querySelector("svg") : null;
    if (!svg) {
      return false;
    }
    clearPlantumlPreviewHighlight(svg);
    if (!trace) {
      return false;
    }
    const elements = findPlantumlPreviewElements(svg, trace);
    for (const element of elements) {
      element.classList.add("plantuml-source-match");
      element.classList.add(`plantuml-source-match-${trace.kind}`);
    }
    if (trace.kind === "alias") {
      addPlantumlPreviewOverlay(svg, elements);
    }
    if (elements.length) {
      scrollPlantumlPreviewToElements(panel, elements);
    }
    return Boolean(elements.length);
  }

  function scrollPlantumlPreviewToElements(panel, elements) {
    const boxes = [];
    for (const element of elements) {
      if (!element.getBoundingClientRect) {
        continue;
      }
      const box = element.getBoundingClientRect();
      if (box.width || box.height) {
        boxes.push(box);
      }
    }
    if (!boxes.length) {
      return;
    }
    const left = Math.min(...boxes.map(function (box) { return box.left; }));
    const top = Math.min(...boxes.map(function (box) { return box.top; }));
    const right = Math.max(...boxes.map(function (box) { return box.right; }));
    const bottom = Math.max(...boxes.map(function (box) { return box.bottom; }));
    const panelBox = panel.getBoundingClientRect();
    const targetX = (left + right) / 2;
    const targetY = (top + bottom) / 2;
    const panelX = panelBox.left + panelBox.width / 2;
    const panelY = panelBox.top + panelBox.height / 2;
    panel.scrollLeft += targetX - panelX;
    panel.scrollTop += targetY - panelY;
  }

  function clearPlantumlPreviewHighlight(svg) {
    for (const element of svg.querySelectorAll(".plantuml-source-match")) {
      element.classList.remove(
        "plantuml-source-match",
        "plantuml-source-match-alias",
        "plantuml-source-match-edge",
        "plantuml-source-match-text"
      );
    }
    for (const element of svg.querySelectorAll(".plantuml-source-overlay")) {
      element.remove();
    }
  }

  function findPlantumlPreviewElements(svg, trace) {
    if (trace.kind === "edge") {
      return findPlantumlPreviewEdgeElements(svg, trace.from, trace.to);
    }
    if (trace.kind === "alias") {
      return findPlantumlPreviewAliasElements(svg, trace.value);
    }
    if (trace.kind === "text") {
      return findPlantumlPreviewTextElements(svg, trace.value);
    }
    return [];
  }

  function findPlantumlPreviewEdgeElements(svg, from, to) {
    const matches = [];
    const wanted = `${from}->${to}`;
    const encodedWanted = `${from}-&gt;${to}`;
    for (const element of svg.querySelectorAll("[id]")) {
      const rawId = element.getAttribute("id") || "";
      const id = plantumlDecodeText(rawId);
      if (id === wanted || rawId === encodedWanted) {
        matches.push(element);
        let sibling = element.nextElementSibling;
        let scanned = 0;
        while (sibling && scanned < 3) {
          matches.push(sibling);
          sibling = sibling.nextElementSibling;
          scanned += 1;
        }
        break;
      }
    }
    return matches;
  }

  function findPlantumlPreviewAliasElements(svg, alias) {
    const walker = document.createTreeWalker(svg, NodeFilter.SHOW_COMMENT);
    let node = walker.nextNode();
    while (node) {
      const match = node.data.match(/\b(?:entity|class|interface|database|actor|component|participant|boundary|control|collections|queue|cluster)\s+([A-Za-z0-9_.:-]+)/);
      if (match && match[1] === alias) {
        const matches = [];
        let sibling = node.nextSibling;
        let objectBox = null;
        while (sibling && sibling.nodeType !== Node.COMMENT_NODE) {
          if (sibling.nodeType === Node.ELEMENT_NODE) {
            const box = plantumlElementBox(sibling);
            if (box && !objectBox) {
              objectBox = box;
            }
            if (box && objectBox && !plantumlBoxesAreNear(objectBox, box)) {
              break;
            }
            matches.push(sibling);
            if (box) {
              objectBox = unionPlantumlBoxes(objectBox, box);
            }
          }
          sibling = sibling.nextSibling;
        }
        return matches.length ? matches : findPlantumlPreviewTextElements(svg, alias);
      }
      node = walker.nextNode();
    }
    return findPlantumlPreviewTextElements(svg, alias);
  }

  function findPlantumlPreviewTextElements(svg, value) {
    const needle = normalizeTraceText(value);
    if (!needle) {
      return [];
    }
    const matches = [];
    for (const text of svg.querySelectorAll("text")) {
      const label = normalizeTraceText(text.textContent);
      if (label && (label.includes(needle) || needle.includes(label))) {
        matches.push(text);
      }
    }
    return matches;
  }

  function plantumlDecodeText(value) {
    const textarea = document.createElement("textarea");
    textarea.innerHTML = value || "";
    return textarea.value;
  }

  function plantumlElementBox(element) {
    if (!element.getBBox) {
      return null;
    }
    try {
      const box = element.getBBox();
      return box && (box.width || box.height) ? box : null;
    } catch (_error) {
      return null;
    }
  }

  function unionPlantumlBoxes(first, second) {
    if (!first) {
      return second;
    }
    const left = Math.min(first.x, second.x);
    const top = Math.min(first.y, second.y);
    const right = Math.max(first.x + first.width, second.x + second.width);
    const bottom = Math.max(first.y + first.height, second.y + second.height);
    return { x: left, y: top, width: right - left, height: bottom - top };
  }

  function plantumlBoxesAreNear(first, second) {
    const horizontalGap = Math.max(0, Math.max(first.x, second.x) - Math.min(first.x + first.width, second.x + second.width));
    const verticalGap = Math.max(0, Math.max(first.y, second.y) - Math.min(first.y + first.height, second.y + second.height));
    return horizontalGap <= 28 && verticalGap <= 18;
  }

  function addPlantumlPreviewOverlay(svg, elements) {
    const boxes = [];
    for (const element of elements) {
      if (!element.getBBox) {
        continue;
      }
      try {
        const box = element.getBBox();
        if (box.width || box.height) {
          boxes.push(box);
        }
      } catch (_error) {
        // Some SVG nodes can refuse getBBox while detached or hidden.
      }
    }
    if (!boxes.length) {
      return;
    }
    const left = Math.min(...boxes.map(function (box) { return box.x; }));
    const top = Math.min(...boxes.map(function (box) { return box.y; }));
    const right = Math.max(...boxes.map(function (box) { return box.x + box.width; }));
    const bottom = Math.max(...boxes.map(function (box) { return box.y + box.height; }));
    const padding = 7;
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.classList.add("plantuml-source-overlay");
    rect.classList.add("is-alias-overlay");
    rect.setAttribute("x", String(left - padding));
    rect.setAttribute("y", String(top - padding));
    rect.setAttribute("width", String(right - left + padding * 2));
    rect.setAttribute("height", String(bottom - top + padding * 2));
    rect.setAttribute("rx", "8");
    rect.setAttribute("ry", "8");
    svg.appendChild(rect);
  }

  function findPlantumlSourceTraceRange(source, trace) {
    const lines = source.split(/\n/);
    const candidates = [];
    if (trace.kind === "edge") {
      candidates.push(function (line) {
        return line.includes(trace.from)
          && line.includes(trace.to)
          && (line.includes("->") || line.includes("-->") || line.includes("--"));
      });
    } else if (trace.kind === "alias") {
      const alias = trace.value;
      candidates.push(function (line) {
        return new RegExp("\\bas\\s+" + escapeRegExp(alias) + "\\b").test(line)
          || new RegExp("\\b" + escapeRegExp(alias) + "\\b").test(line);
      });
    } else if (trace.kind === "text") {
      const value = trace.value.replace(/^"|"$/g, "");
      candidates.push(function (line) { return line.includes(value); });
      candidates.push(function (line) { return normalizeTraceText(line).includes(normalizeTraceText(value)); });
    }
    let offset = 0;
    for (const line of lines) {
      if (candidates.some(function (predicate) { return predicate(line); })) {
        return { start: offset, end: offset + line.length };
      }
      offset += line.length + 1;
    }
    return null;
  }

  function normalizeTraceText(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9_]+/g, " ").trim();
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function setAgentDiagramPreviewError(message) {
    const shell = ensureAgentDiagramEditorShell();
    const panel = shell.querySelector("[data-plantuml-preview-panel]");
    if (!panel) {
      return;
    }
    panel.hidden = false;
    panel.classList.add("is-error");
    panel.classList.remove("is-pending");
    panel.textContent = message;
  }

  function handleAgentDiagramEditorError(error, prefix) {
    const message = error && error.message ? error.message : String(error || "");
    const line = extractPlantumlErrorLine(message);
    const sourceLine = line ? "" : extractPlantumlErrorSourceLine(message);
    const suffix = line ? ` at line ${line}` : (sourceLine ? " at matching line" : "");
    setAgentDiagramEditorStatus(`${prefix}${suffix}: ${message}`);
    if (error && error.svg) {
      setAgentDiagramPreviewSvg(error.svg);
    } else {
      setAgentDiagramPreviewError(message);
    }
    if (line) {
      selectPlantumlSourceLine(line);
    } else if (sourceLine) {
      selectPlantumlSourceLineText(sourceLine);
    }
  }

  function extractPlantumlErrorLine(message) {
    const text = String(message || "");
    const patterns = [
      /\bline\s+(\d+)\b/i,
      /\bat\s+line\s+(\d+)\b/i,
      /\berror\s+line\s+(\d+)\b/i,
      /\bLine:\s*(\d+)\b/i,
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        const line = Number.parseInt(match[1], 10);
        if (Number.isFinite(line) && line > 0) {
          return line;
        }
      }
    }
    return 0;
  }

  function extractPlantumlErrorSourceLine(message) {
    const text = String(message || "");
    const markerMatch = text.match(/\bPlantUML line(?:\s+in\s+[^:]+)?:\s*(.+)$/i);
    if (markerMatch && markerMatch[1].trim()) {
      return markerMatch[1].trim();
    }
    const unsupportedMatch = text.match(/\bunsupported\s+.+?\s+line(?:\s+in\s+[^:]+)?:\s*(.+)$/i);
    if (unsupportedMatch && unsupportedMatch[1].trim()) {
      return unsupportedMatch[1].trim();
    }
    return "";
  }

  function selectPlantumlSourceLine(lineNumber) {
    const shell = ensureAgentDiagramEditorShell();
    const textarea = shell.querySelector("[data-plantuml-source]");
    if (!textarea || !lineNumber) {
      return false;
    }
    const source = textarea.value;
    const lines = source.split("\n");
    const index = Math.max(0, Math.min(lines.length - 1, lineNumber - 1));
    let start = 0;
    for (let i = 0; i < index; i += 1) {
      start += lines[i].length + 1;
    }
    const end = start + lines[index].length;
    textarea.focus();
    textarea.setSelectionRange(start, end);
    const lineHeight = parseFloat(window.getComputedStyle(textarea).lineHeight) || 20;
    textarea.scrollTop = Math.max(0, (index - 4) * lineHeight);
    return true;
  }

  function selectPlantumlSourceLineText(lineText) {
    const shell = ensureAgentDiagramEditorShell();
    const textarea = shell.querySelector("[data-plantuml-source]");
    const needle = String(lineText || "").trim();
    if (!textarea || !needle) {
      return false;
    }
    const lines = textarea.value.split("\n");
    let offset = 0;
    for (let index = 0; index < lines.length; index += 1) {
      if (lines[index].trim() === needle || lines[index].includes(needle)) {
        textarea.focus();
        textarea.setSelectionRange(offset, offset + lines[index].length);
        const lineHeight = parseFloat(window.getComputedStyle(textarea).lineHeight) || 20;
        textarea.scrollTop = Math.max(0, (index - 4) * lineHeight);
        return true;
      }
      offset += lines[index].length + 1;
    }
    return false;
  }

  async function openAgentDiagramEditor() {
    if (!activeDiagram || !feedbackServer) {
      window.alert("agent_diagram editing is not ready for this diagram yet.");
      return;
    }
    editButton.disabled = true;
    editButton.textContent = "Opening...";
    setEditStatus("Reading JSON...");
    try {
      const source = await readAgentDiagram(activeDiagram);
      const isBaseAgentDiagram = Boolean(source.value && source.value.agent_diagram && !source.value.variant_of);
      if (isBaseAgentDiagram && !source.source_format) {
        throw new Error("feedback server is too old for PlantUML editing; restart Agent Workspace so the server reloads");
      }
      const shell = ensureAgentDiagramEditorShell();
      const textarea = shell.querySelector("[data-plantuml-source]");
      editorState = {
        diagram: activeDiagram,
        source,
        draft: cloneJson(source.value),
        sourceFormat: source.source_format || "json",
        sourceText: source.source || "",
      };
      shell.hidden = false;
      document.body.classList.add("has-plantuml-editor-open");
      setEditStatus("Editor open");
      setAgentDiagramEditorStatus("Ready");
      renderAgentDiagramForm();
      textarea.value = editorState.sourceFormat === "plantuml"
        ? (editorState.sourceText || "")
        : JSON.stringify(editorState.draft, null, 2);
      if (editorState.sourceFormat === "plantuml" && feedbackHasAgentDiagramPreview()) {
        setAgentDiagramPreviewPending();
        window.setTimeout(function () {
          previewAgentDiagramEditor().catch(function (error) {
            handleAgentDiagramEditorError(error, "Preview failed");
          });
        }, 0);
      }
    } catch (error) {
      window.alert(`Unable to open agent_diagram editor: ${error.message || error}`);
      editButton.disabled = false;
      editButton.textContent = "Edit";
      setEditStatus("Open failed");
    }
  }

  function closeAgentDiagramEditor() {
    const shell = document.getElementById("plantuml-editor-shell");
    if (shell) {
      shell.hidden = true;
    }
    document.body.classList.remove("has-plantuml-editor-open");
    editorState = null;
    updateEditButton();
    setEditStatus("");
  }

  async function saveAgentDiagramEditor() {
    if (!editorState || !editorState.diagram) {
      return;
    }
    const diagram = editorState.diagram;
    if (editorState.sourceFormat === "plantuml") {
      setAgentDiagramEditorStatus("Saving PlantUML as JSON...");
      const rendered = await writeAgentDiagram(diagram, {
        source_format: "plantuml",
        source: currentAgentDiagramText(),
      });
      updateRenderedDiagram(diagram.diagramId, rendered.svg);
      setAgentDiagramEditorStatus("Saved");
      closeAgentDiagramEditor();
      return;
    }
    if (!validateAgentDiagramEditor()) {
      throw new Error("Fix JSON validation errors before saving.");
    }
    const value = parseAgentDiagramEditor();
    editorState.draft = value;
    setAgentDiagramEditorStatus("Saving JSON...");
    const rendered = await writeAgentDiagram(diagram, value);
    updateRenderedDiagram(diagram.diagramId, rendered.svg);
    setAgentDiagramEditorStatus("Saved");
    closeAgentDiagramEditor();
  }

  function openDiagramEditor() {
    if (!activeDiagram) {
      return;
    }
    if (activeDiagram.commentsTask && activeDiagram.commentsPath && activeDiagram.commentsDiagram) {
      openAgentDiagramEditor();
      return;
    }
    openDrawioEditor();
  }

  function postDrawio(message) {
    if (!editorState || !editorState.frame || !editorState.frame.contentWindow) {
      return;
    }
    editorState.frame.contentWindow.postMessage(JSON.stringify(message), drawioOrigin);
  }

  function parseDrawioMessage(event) {
    if (!editorState || !editorState.frame || event.source !== editorState.frame.contentWindow || event.origin !== drawioOrigin) {
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
  window.codexOpenDiagramEditor = function (event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    openDiagramEditor();
  };
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
      openDiagramEditor();
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
