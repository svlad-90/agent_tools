from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urlparse
import webbrowser

from ...process_runtime.api import acquire_agent_workspace_lock
from ...process_runtime.api import install_agent_workspace_exception_logger
from ...harness_adapter.api import clear_harness_debug_events
from ...workspace_service.api import AgentWorkspaceService
from ...workspace_service.api import TaskContextFilters
from .ui_contract import web_settings_ui_tree


MAX_JSON_BODY_BYTES = 64 * 1024
REQUEST_BODY_TIMEOUT_SECONDS = 5


class _RequestBodyTooLarge(ValueError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the Agent Workspace browser UI.")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Workspace root. Default: current directory.")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host. Default: 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port. Use 0 for an ephemeral port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser tab.")
    args = parser.parse_args(argv)

    workspace = args.workspace.resolve()
    install_agent_workspace_exception_logger(workspace, "web")
    lock = acquire_agent_workspace_lock(workspace)
    if lock is None:
        print("Agent Workspace is already running for this workspace.", file=sys.stderr)
        return 1
    clear_harness_debug_events(workspace)
    server = create_server(workspace, args.host, args.port)
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"Agent Workspace web UI: {url}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
        lock.close()
    return 0


def create_server(workspace: Path, host: str, port: int) -> ThreadingHTTPServer:
    service = AgentWorkspaceService(workspace)

    class Handler(AgentWorkspaceWebHandler):
        workspace_service = service

    return _AgentWorkspaceWebServer((host, port), Handler, service)


class _AgentWorkspaceWebServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        workspace_service: AgentWorkspaceService,
    ) -> None:
        self.workspace_service = workspace_service
        super().__init__(server_address, handler_class)

    def server_close(self) -> None:
        try:
            self.workspace_service.shutdown()
        finally:
            super().server_close()


class AgentWorkspaceWebHandler(BaseHTTPRequestHandler):
    workspace_service: AgentWorkspaceService
    server_version = "AgentWorkspaceWeb/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(_INDEX_HTML)
            return
        if parsed.path == "/api/tasks":
            self._send_json({"tasks": self.workspace_service.tasks()})
            return
        if parsed.path == "/api/ui-contract/settings":
            self._send_json(web_settings_ui_tree().to_json())
            return
        if parsed.path.startswith("/api/tasks/"):
            self._handle_task_api(parsed.path, parse_qs(parsed.query))
            return
        self._send_error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        is_task_creation = parsed.path == "/api/tasks"
        path_parts = [unquote(part) for part in parsed.path.split("/") if part]
        context_task_name = (
            path_parts[2]
            if len(path_parts) == 4
            and path_parts[:2] == ["api", "tasks"]
            and path_parts[3] == "context-slot"
            else None
        )
        terminal_task_name = (
            path_parts[2]
            if len(path_parts) == 4
            and path_parts[:2] == ["api", "tasks"]
            and path_parts[3] == "terminals"
            else None
        )
        if not is_task_creation and context_task_name is None and terminal_task_name is None:
            self._send_error(HTTPStatus.NOT_FOUND, "not found")
            return
        if terminal_task_name is not None and not self._allow_loopback_terminal_request():
            return
        content_types = self.headers.get_all("Content-Type", failobj=[])
        if len(content_types) != 1 or self.headers.get_content_type() != "application/json":
            self._send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json")
            return
        try:
            body = self._read_json_body()
        except _RequestBodyTooLarge as error:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(error))
            return
        except TimeoutError:
            self.close_connection = True
            self._send_error(HTTPStatus.REQUEST_TIMEOUT, "request body timed out")
            return
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        if context_task_name is not None:
            self._handle_context_slot_update(context_task_name, parse_qs(parsed.query), body)
            return
        if terminal_task_name is not None:
            self._handle_shell_terminal_start(terminal_task_name)
            return
        self._handle_task_creation(body)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) != 4 or parts[:2] != ["api", "tasks"] or parts[3] != "terminals":
            self._send_error(HTTPStatus.NOT_FOUND, "not found")
            return
        if not self._allow_loopback_terminal_request():
            return
        session_id = _query_value(parse_qs(parsed.query), "id")
        if not session_id:
            self._send_error(HTTPStatus.BAD_REQUEST, "missing terminal id")
            return
        try:
            result = self.workspace_service.close_terminal(parts[2], session_id)
        except KeyError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        except (OSError, RuntimeError) as error:
            self.log_error("terminal close failed: %s", error)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "terminal close failed")
            return
        self._send_json(result)

    def _handle_task_creation(self, body: dict[str, Any]) -> None:
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            self._send_error(HTTPStatus.BAD_REQUEST, "missing task name")
            return
        privacy = body.get("privacy", "public")
        if not isinstance(privacy, str):
            self._send_error(HTTPStatus.BAD_REQUEST, "task privacy must be a string")
            return
        try:
            created = self.workspace_service.create_task(name, privacy=privacy)
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        except subprocess.TimeoutExpired as error:
            self.log_error("task creation timed out: %s", error)
            self._send_error(HTTPStatus.GATEWAY_TIMEOUT, "task creation timed out")
            return
        except (OSError, RuntimeError) as error:
            self.log_error("task creation failed: %s", error)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "task creation failed")
            return
        self._send_json(created, status=HTTPStatus.CREATED)

    def _handle_shell_terminal_start(self, task_name: str) -> None:
        try:
            result = self.workspace_service.start_shell_terminal(task_name)
        except KeyError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        except (OSError, RuntimeError) as error:
            self.log_error("terminal start failed: %s", error)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "terminal start failed")
            return
        try:
            self._send_json(result, status=HTTPStatus.CREATED)
        except Exception:
            session = result.get("session")
            session_id = session.get("id") if isinstance(session, dict) else None
            if isinstance(session_id, str):
                try:
                    self.workspace_service.close_terminal(task_name, session_id)
                except Exception as cleanup_error:
                    self.log_error("terminal cleanup after response failure failed: %s", cleanup_error)
            raise

    def _handle_context_slot_update(
        self,
        task_name: str,
        query: dict[str, list[str]],
        body: dict[str, Any],
    ) -> None:
        category = _query_value(query, "category")
        if not category:
            self._send_error(HTTPStatus.BAD_REQUEST, "missing category")
            return
        content = body.get("content")
        if not isinstance(content, str):
            self._send_error(HTTPStatus.BAD_REQUEST, "context content must be a string")
            return
        try:
            result = self.workspace_service.save_task_context_slot(task_name, category, content)
        except KeyError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        except (OSError, RuntimeError, sqlite3.Error) as error:
            self.log_error("context slot update failed: %s", error)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "context slot update failed")
            return
        self._send_json(result)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)

    def _handle_task_api(self, path: str, query: dict[str, list[str]]) -> None:
        parts = [unquote(part) for part in path.split("/") if part]
        if len(parts) < 3:
            self._send_error(HTTPStatus.NOT_FOUND, "missing task name")
            return
        task_name = parts[2]
        endpoint = parts[3] if len(parts) > 3 else "snapshot"
        try:
            if endpoint == "snapshot":
                self._send_json(
                    self.workspace_service.task_snapshot(
                        task_name,
                        context_filters=_context_filters(query),
                        encoded_context=_query_bool(query, "encoded"),
                    )
                )
                return
            if endpoint == "context":
                self._send_json(
                    self.workspace_service.task_context(
                        task_name,
                        filters=_context_filters(query),
                        encoded=_query_bool(query, "encoded"),
                    )
                )
                return
            if endpoint == "actions":
                self._send_json(self.workspace_service.task_actions(task_name))
                return
            if endpoint == "ai-debug":
                self._send_json({"events": self.workspace_service.ai_debug_events(task_name)})
                return
            if endpoint == "artifacts":
                self._send_json({"artifacts": self.workspace_service.task_artifacts(task_name)})
                return
            if endpoint == "artifact":
                if len(parts) != 4:
                    self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                    return
                label = _query_value(query, "path")
                if not label:
                    self._send_error(HTTPStatus.BAD_REQUEST, "missing artifact path")
                    return
                try:
                    artifact = self.workspace_service.artifact_content(task_name, label)
                except OSError as error:
                    self.log_error("artifact preview failed: %s", error)
                    self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "artifact preview failed")
                    return
                self._send_json(artifact)
                return
            if endpoint == "terminals":
                if len(parts) != 4:
                    self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                    return
                if not self._allow_loopback_terminal_request():
                    return
                self._send_json({"sessions": self.workspace_service.terminal_sessions(task_name)})
                return
            if endpoint == "terminal-output":
                if len(parts) != 4:
                    self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                    return
                if not self._allow_loopback_terminal_request():
                    return
                session_id = _query_value(query, "id")
                if not session_id:
                    self._send_error(HTTPStatus.BAD_REQUEST, "missing terminal id")
                    return
                offset = _query_nonnegative_int(query, "offset")
                self._send_json(
                    self.workspace_service.terminal_output(
                        task_name,
                        session_id,
                        offset=offset,
                    )
                )
                return
            if endpoint == "task-check-command":
                self._send_json({"command": self.workspace_service.task_check_command(task_name)})
                return
            if endpoint == "action-command":
                action_id = _query_value(query, "id")
                if not action_id:
                    self._send_error(HTTPStatus.BAD_REQUEST, "missing action id")
                    return
                self._send_json({"command": self.workspace_service.task_action_command(task_name, action_id)})
                return
        except KeyError as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")

    def _allow_loopback_terminal_request(self) -> bool:
        host_values = self.headers.get_all("Host", failobj=[])
        peer_host = self.client_address[0]
        if len(host_values) == 1 and _is_loopback_host(peer_host) and _is_loopback_authority(host_values[0]):
            return True
        self._send_error(HTTPStatus.FORBIDDEN, "terminal API is available only from loopback")
        return False

    def _send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)

    def _read_json_body(self) -> dict[str, Any]:
        if self.headers.get_all("Transfer-Encoding", failobj=[]):
            raise ValueError("Transfer-Encoding is not supported")
        raw_lengths = self.headers.get_all("Content-Length", failobj=[])
        if not raw_lengths:
            raise ValueError("missing Content-Length")
        if len(raw_lengths) != 1:
            raise ValueError("multiple Content-Length headers")
        raw_length = raw_lengths[0]
        if not raw_length or not raw_length.isascii() or not raw_length.isdigit():
            raise ValueError("invalid Content-Length")
        if len(raw_length) > 1 and raw_length.startswith("0"):
            raise ValueError("invalid Content-Length")
        maximum_length = str(MAX_JSON_BODY_BYTES)
        if len(raw_length) > len(maximum_length) or (
            len(raw_length) == len(maximum_length) and raw_length > maximum_length
        ):
            raise _RequestBodyTooLarge(f"JSON body exceeds {MAX_JSON_BODY_BYTES} bytes")
        length = int(raw_length)
        previous_timeout = self.connection.gettimeout()
        self.connection.settimeout(REQUEST_BODY_TIMEOUT_SECONDS)
        try:
            raw_bytes = self.rfile.read(length)
        finally:
            self.connection.settimeout(previous_timeout)
        if len(raw_bytes) != length:
            self.close_connection = True
            raise ValueError("incomplete request body")
        raw_body = raw_bytes.decode("utf-8")
        value = json.loads(raw_body)
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value


def _context_filters(query: dict[str, list[str]]) -> TaskContextFilters:
    severity = _query_tuple(query, "severity")
    statuses = _query_tuple(query, "status")
    return TaskContextFilters(
        since=_query_value(query, "since"),
        until=_query_value(query, "until"),
        severity=severity or None,
        statuses=statuses or None,
        labels=_query_tuple(query, "label"),
        newest_first=not _query_bool(query, "oldest_first"),
    )


def _is_loopback_authority(value: str) -> bool:
    try:
        parsed = urlparse(f"//{value}")
        hostname = parsed.hostname
    except ValueError:
        return False
    if hostname is None or parsed.path or parsed.query or parsed.fragment:
        return False
    return _is_loopback_host(hostname)


def _is_loopback_host(value: str) -> bool:
    normalized = value.rstrip(".").casefold()
    if normalized == "localhost":
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_loopback


def _query_tuple(query: dict[str, list[str]], key: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw_value in query.get(key, []):
        values.extend(item.strip() for item in raw_value.split(","))
    return tuple(value for value in values if value)


def _query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key, [])
    if not values:
        return None
    value = values[-1].strip()
    return value or None


def _query_bool(query: dict[str, list[str]], key: str) -> bool:
    value = _query_value(query, key)
    return value is not None and value.casefold() not in {"0", "false", "no", "off"}


def _query_nonnegative_int(query: dict[str, list[str]], key: str) -> int:
    value = _query_value(query, key)
    if value is None:
        return 0
    if not value or len(value) > 20 or not value.isascii() or not value.isdigit():
        raise ValueError(f"invalid {key}")
    return int(value)


_INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Workspace</title>
<style>
:root { color-scheme: dark; --bg:#111315; --panel:#1d2024; --line:#373d45; --text:#eceff4; --muted:#aeb7c2; --accent:#f05a28; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
button, select { font:inherit; color:var(--text); background:#2a2f36; border:1px solid #4a515c; border-radius:4px; padding:6px 10px; }
label { color:var(--muted); }
input[type="text"] { font:inherit; color:var(--text); background:#11151a; border:1px solid #4a515c; border-radius:4px; padding:6px 8px; min-width:150px; }
button:hover { border-color:var(--accent); }
.app { display:grid; grid-template-columns:280px 1fr; min-height:100vh; }
.sidebar { border-right:1px solid var(--line); background:#171a1e; display:flex; flex-direction:column; min-width:0; }
.title { padding:12px 14px; border-bottom:1px solid var(--line); font-weight:700; }
.tasks { overflow:auto; padding:6px; }
.task { width:100%; text-align:left; margin:0 0 4px; display:block; }
.task.active { border-color:var(--accent); background:#3a2a24; }
.task small { display:block; color:var(--muted); margin-top:2px; }
.main { min-width:0; display:grid; grid-template-rows:auto 1fr; }
.toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; padding:10px 12px; border-bottom:1px solid var(--line); background:#191c20; }
.toolbar h1 { margin:0; font-size:18px; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.toolbar .group { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.content { display:grid; grid-template-columns:1fr 1fr; grid-template-rows:minmax(220px, 40vh) 1fr; gap:1px; background:var(--line); min-height:0; }
.pane { background:var(--panel); min-width:0; min-height:0; display:flex; flex-direction:column; }
.pane h2 { margin:0; padding:8px 10px; border-bottom:1px solid var(--line); font-size:14px; color:var(--muted); }
.pane pre { margin:0; padding:10px; overflow:auto; white-space:pre-wrap; font:13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; flex:1; }
.pane pre a { color:#9ecbff; text-decoration:underline; }
.wide { grid-column:1 / 3; }
.list { overflow:auto; padding:8px; }
.item { border:1px solid var(--line); border-radius:4px; padding:8px; margin:0 0 8px; background:#16191d; }
.item strong { display:block; }
.muted { color:var(--muted); }
.error { color:#ffb4a6; }
@media (max-width: 900px) {
  .app { grid-template-columns:1fr; }
  .sidebar { max-height:36vh; border-right:0; border-bottom:1px solid var(--line); }
  .content { grid-template-columns:1fr; grid-template-rows:auto; }
  .wide { grid-column:auto; }
}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="title">Agent Workspace</div>
    <div id="tasks" class="tasks"></div>
  </aside>
  <main class="main">
    <div class="toolbar">
      <h1 id="taskTitle">No task selected</h1>
      <span class="group">
        <label><input id="encoded" type="checkbox"> Encoded</label>
        <label>Severity <input id="severity" type="text" value="mid,high,critical"></label>
        <label>Status <input id="status" type="text" value="active"></label>
        <label>Labels <input id="labels" type="text" placeholder="comma-separated"></label>
      </span>
      <button id="taskCheckCommand">Task check command</button>
      <button id="refresh">Refresh</button>
    </div>
    <section class="content">
      <div class="pane"><h2>Description</h2><pre id="description"></pre></div>
      <div class="pane"><h2>Context</h2><pre id="context"></pre></div>
      <div class="pane"><h2>Actions</h2><div id="actions" class="list"></div></div>
      <div class="pane"><h2>Artifacts</h2><div id="artifacts" class="list"></div></div>
      <div class="pane wide"><h2>AI Debug</h2><pre id="aiDebug"></pre></div>
      <div class="pane wide"><h2>Task Check</h2><pre id="taskCheck"></pre></div>
    </section>
  </main>
</div>
<script>
let selectedTask = null;
async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}
function text(id, value) { document.getElementById(id).textContent = value || ""; }
function contextQuery() {
  const params = new URLSearchParams();
  if (document.getElementById("encoded").checked) params.set("encoded", "1");
  addCsvParam(params, "severity", document.getElementById("severity").value);
  addCsvParam(params, "status", document.getElementById("status").value);
  addCsvParam(params, "label", document.getElementById("labels").value);
  return params.toString();
}
function addCsvParam(params, key, raw) {
  const value = String(raw || "").split(",").map(item => item.trim()).filter(Boolean).join(",");
  if (value) params.set(key, value);
}
async function loadTasks() {
  const data = await getJson("/api/tasks");
  const box = document.getElementById("tasks");
  box.innerHTML = "";
  for (const task of data.tasks) {
    const button = document.createElement("button");
    button.className = "task" + (task.name === selectedTask ? " active" : "");
    button.innerHTML = `<strong>${escapeHtml(task.name)}</strong><small>${task.context_tokens} context tokens</small>`;
    button.onclick = () => { selectedTask = task.name; loadSnapshot(); loadTasks(); };
    box.appendChild(button);
  }
  if (!selectedTask && data.tasks.length) {
    selectedTask = data.tasks[0].name;
    await loadSnapshot();
    await loadTasks();
  }
}
async function loadSnapshot() {
  if (!selectedTask) return;
  const data = await getJson(`/api/tasks/${encodeURIComponent(selectedTask)}?${contextQuery()}`);
  text("taskTitle", data.task.name);
  text("description", data.description);
  renderContext(data.context.markdown || "-");
  text("taskCheck", data.task_check || "-");
  renderActions(data.actions.actions || [], data.actions.errors || []);
  renderAiDebug(data.ai_debug || []);
  renderArtifacts(data.artifacts || []);
}
async function showTaskCheckCommand() {
  if (!selectedTask) return;
  const data = await getJson(`/api/tasks/${encodeURIComponent(selectedTask)}/task-check-command`);
  await copyOrShow(data.command);
}
async function copyOrShow(value) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(value);
  }
  alert(value);
}
function renderActions(actions, errors) {
  const box = document.getElementById("actions");
  box.innerHTML = "";
  for (const error of errors) box.appendChild(item("Config error", error));
  for (const action of actions) {
    const node = item(action.label, action.id);
    const command = document.createElement("button");
    command.textContent = "Command";
    command.onclick = async () => {
      const data = await getJson(`/api/tasks/${encodeURIComponent(selectedTask)}/action-command?id=${encodeURIComponent(action.id)}`);
      await copyOrShow(data.command);
    };
    node.appendChild(command);
    box.appendChild(node);
  }
  if (!box.children.length) box.appendChild(item("No actions", ""));
}
function renderArtifacts(artifacts) {
  const box = document.getElementById("artifacts");
  box.innerHTML = "";
  for (const artifact of artifacts) box.appendChild(item(artifact.label, `${artifact.group} ${artifact.updated_label}`));
  if (!box.children.length) box.appendChild(item("No artifacts", ""));
}
function renderAiDebug(events) {
  if (!events.length) {
    text("aiDebug", "No AI hook events.");
    return;
  }
  text("aiDebug", events.map(event => {
    const tool = event.tool_name ? ` tool=${event.tool_name}` : "";
    const detail = event.tool_detail ? ` :: ${event.tool_detail}` : "";
    const outcome = event.outcome ? ` ${event.outcome}` : "";
    const kind = event.outcome === "injected" ? "INJECT" : event.status_event.startsWith("tool_") ? "TOOL" : event.outcome === "blocked" ? "BLOCK" : "HOOK";
    return `${event.updated_at} ${event.icon} ${kind} ${event.agent_type}/${event.session_id} ${event.hook_event || event.status_event}${tool}${outcome}: ${event.message}${detail}`;
  }).join("\\n"));
}
function item(title, body) {
  const node = document.createElement("div");
  node.className = "item";
  node.innerHTML = `<strong>${escapeHtml(title)}</strong><span class="muted">${escapeHtml(body || "")}</span>`;
  return node;
}
function renderContext(value) {
  document.getElementById("context").innerHTML = contextHtml(value || "");
}
function contextHtml(value) {
  return String(value || "").split("\\n").map(contextLineHtml).join("\\n");
}
function contextLineHtml(value) {
  const escaped = escapeHtml(value);
  const header = escaped.match(/^(\\| )#(\\d+)( \\[.*)$/);
  if (header) {
    return `${header[1]}<a id="ctx-entry-${header[2]}" href="#ctx-entry-${header[2]}">#${header[2]}</a>${linkContextRefs(header[3])}`;
  }
  return linkContextRefs(escaped);
}
function linkContextRefs(escapedText) {
  return escapedText.replace(/(^|[^\\w/-])#(\\d+)\\b/g, (_match, prefix, id) => `${prefix}<a href="#ctx-entry-${id}">#${id}</a>`);
}
async function followContextLink(event) {
  const link = event.target.closest("a[href^='#ctx-entry-']");
  if (!link) return;
  const targetId = link.getAttribute("href").slice(1);
  if (document.getElementById(targetId)) return;
  event.preventDefault();
  document.getElementById("severity").value = "note,low,mid,high,critical";
  document.getElementById("status").value = "active,resolved,stale";
  document.getElementById("labels").value = "";
  await loadSnapshot();
  const target = document.getElementById(targetId);
  if (target) target.scrollIntoView({block:"start"});
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
document.getElementById("refresh").onclick = () => { loadTasks(); loadSnapshot(); };
document.getElementById("encoded").onchange = loadSnapshot;
document.getElementById("severity").onchange = loadSnapshot;
document.getElementById("status").onchange = loadSnapshot;
document.getElementById("labels").onchange = loadSnapshot;
document.getElementById("taskCheckCommand").onclick = showTaskCheckCommand;
document.getElementById("context").onclick = followContextLink;
loadTasks().catch(error => alert(error.message));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
