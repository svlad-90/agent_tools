from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlparse


DIFF_REPORT_FEEDBACK_CAPABILITIES = ("drawio",)
DIFF_REPORT_FEEDBACK_PORTS = tuple(range(8765, 8770))
_MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"


@dataclass(frozen=True)
class DiffReportFeedbackServerHandle:
    server: ThreadingHTTPServer
    thread: threading.Thread
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class DiffReportFeedbackServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], workspace: Path) -> None:
        super().__init__(server_address, DiffReportFeedbackRequestHandler)
        self.workspace = workspace.resolve()
        self.capabilities = DIFF_REPORT_FEEDBACK_CAPABILITIES


class DiffReportFeedbackRequestHandler(BaseHTTPRequestHandler):
    server: DiffReportFeedbackServer

    def do_OPTIONS(self) -> None:
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/handshake":
            self._handle_handshake()
            return
        if parsed.path == "/api/v1/artifact":
            self._handle_get_artifact(parse_qs(parsed.query))
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/artifact":
            self._handle_put_artifact(parse_qs(parsed.query))
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _handle_handshake(self) -> None:
        self._send_json(
            {
                "ok": True,
                "workspace": str(self.server.workspace),
                "capabilities": list(self.server.capabilities),
                "artifact_roots": ["tasks/*/report/drawio"],
            }
        )

    def _handle_get_artifact(self, query: dict[str, list[str]]) -> None:
        try:
            path = self._resolve_drawio_artifact(query)
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        if not path.is_file():
            self._send_json({"error": "artifact not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            data = path.read_bytes()
        except OSError as error:
            self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_bytes(data, self._content_type(path))

    def _handle_put_artifact(self, query: dict[str, list[str]]) -> None:
        try:
            path = self._resolve_drawio_artifact(query)
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        content_length = self.headers.get("Content-Length")
        try:
            size = int(content_length or "0")
        except ValueError:
            self._send_json({"error": "invalid Content-Length"}, HTTPStatus.BAD_REQUEST)
            return
        if size < 0 or size > _MAX_ARTIFACT_BYTES:
            self._send_json({"error": "artifact is too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            data = self.rfile.read(size)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as error:
            self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json({"ok": True, "path": self._workspace_relative(path), "bytes": len(data)})

    def _resolve_drawio_artifact(self, query: dict[str, list[str]]) -> Path:
        raw_task = _single_query_value(query, "task")
        raw_path = _single_query_value(query, "path")
        if raw_task is None or raw_path is None:
            raise ValueError("task and path are required")
        task = Path(raw_task)
        artifact = Path(raw_path)
        if task.is_absolute() or artifact.is_absolute():
            raise ValueError("task and path must be workspace-relative")
        if ".." in task.parts or ".." in artifact.parts:
            raise ValueError("task and path must not contain '..'")
        if len(task.parts) < 2 or task.parts[0] != "tasks":
            raise ValueError("task must be under tasks/")
        if len(artifact.parts) < 3 or artifact.parts[:2] != ("report", "drawio"):
            raise ValueError("artifact path must be under report/drawio/")
        if artifact.suffix not in {".drawio", ".svg"}:
            raise ValueError("only .drawio and .svg artifacts are writable")
        path = (self.server.workspace / task / artifact).resolve()
        root = (self.server.workspace / task / "report" / "drawio").resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("artifact path escapes report/drawio/") from error
        return path

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"), _JSON_CONTENT_TYPE, status)

    def _send_empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self._send_cors_headers()
        self.end_headers()

    def _send_bytes(
        self,
        data: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    @staticmethod
    def _content_type(path: Path) -> str:
        if path.suffix == ".svg":
            return "image/svg+xml; charset=utf-8"
        return "application/xml; charset=utf-8"

    def _workspace_relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.server.workspace).as_posix()
        except ValueError:
            return str(path)


def start_diff_report_feedback_server(workspace: Path, port: int | None = None) -> DiffReportFeedbackServerHandle:
    ports = (port,) if port is not None else DIFF_REPORT_FEEDBACK_PORTS
    last_error: OSError | None = None
    for candidate in ports:
        try:
            server = DiffReportFeedbackServer(("127.0.0.1", candidate), workspace)
        except OSError as error:
            last_error = error
            continue
        break
    else:
        if last_error is not None:
            raise last_error
        raise OSError("no diff report feedback ports configured")
    thread = threading.Thread(target=server.serve_forever, name="diff-report-feedback", daemon=True)
    thread.start()
    host, bound_port = server.server_address[:2]
    return DiffReportFeedbackServerHandle(server, thread, str(host), int(bound_port))


def _single_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]
