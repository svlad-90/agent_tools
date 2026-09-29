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

from agent_tools.tools.diff_report.agent_diagram import agent_diagram_artifacts
from agent_tools.tools.diff_report.agent_diagram import compile_agent_diagram
from agent_tools.tools.diff_report.agent_diagram import merge_agent_diagram_variant
from agent_tools.tools.diff_report.agent_diagram import parse_agent_diagram_source
from agent_tools.tools.diff_report.agent_diagram import render_plantuml_source_svg
from agent_tools.tools.diff_report.models import DiffReportError


DIFF_REPORT_FEEDBACK_CAPABILITIES = (
    "drawio",
    "agent_diagram",
    "agent_diagram_plantuml",
    "agent_diagram_preview",
)
DIFF_REPORT_FEEDBACK_PORTS = tuple(range(8765, 8770))
_MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_ARTIFACT_ROOTS = ("tasks/*/report/drawio",)


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
        if parsed.path == "/api/v1/agent-diagram/source":
            self._handle_get_agent_diagram_source(parse_qs(parsed.query))
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/artifact":
            self._handle_put_artifact(parse_qs(parsed.query))
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/agent-diagram/source":
            self._handle_put_agent_diagram_source(parse_qs(parsed.query))
            return
        if parsed.path == "/api/v1/agent-diagram/preview":
            self._handle_preview_agent_diagram(parse_qs(parsed.query))
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
                "artifact_roots": list(_ARTIFACT_ROOTS),
            }
        )

    def _handle_get_artifact(self, query: dict[str, list[str]]) -> None:
        try:
            path = self._resolve_artifact(query)
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
            path = self._resolve_artifact(query)
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

    def _handle_get_agent_diagram_source(self, query: dict[str, list[str]]) -> None:
        try:
            comments_path, diagram_key = self._agent_diagram_request(query)
            payload = self._read_comments_payload(comments_path)
            raw_diagram = self._raw_agent_diagram(payload, diagram_key)
            source = self._agent_diagram_source(payload, diagram_key, raw_diagram)
        except (OSError, ValueError, DiffReportError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(
            {
                "ok": True,
                "diagram": diagram_key,
                "value": raw_diagram,
                "source": source,
                "source_format": "json" if "variant_of" in raw_diagram else "plantuml",
            }
        )

    def _handle_put_agent_diagram_source(self, query: dict[str, list[str]]) -> None:
        try:
            comments_path, diagram_key = self._agent_diagram_request(query)
            content_length = self.headers.get("Content-Length")
            size = int(content_length or "0")
            if size < 0 or size > _MAX_ARTIFACT_BYTES:
                self._send_json({"error": "diagram JSON is too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            request_payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(request_payload, dict):
                raise ValueError("request body must be an object")
            payload = self._read_comments_payload(comments_path)
            diagrams = payload.setdefault("diagrams", {})
            if not isinstance(diagrams, dict):
                raise ValueError("comments.diagrams must be an object")
            current_diagram = self._raw_agent_diagram(payload, diagram_key)
            if request_payload.get("source_format") == "plantuml":
                source = request_payload.get("source")
                if not isinstance(source, str):
                    raise ValueError("request source must be a string")
                if "variant_of" in current_diagram:
                    raise ValueError("PlantUML editing is only supported for base agent_diagram entries")
                next_diagram = dict(current_diagram)
                next_diagram["agent_diagram"] = parse_agent_diagram_source(source, diagram_key=diagram_key)
            else:
                if not isinstance(request_payload.get("value"), dict):
                    raise ValueError("request value must be an object")
                next_diagram = request_payload["value"]
            diagrams[diagram_key] = next_diagram
            raw_diagram = self._raw_agent_diagram(payload, diagram_key)
            source, svg = self._render_agent_diagram_entry(payload, comments_path, diagram_key, raw_diagram)
            comments_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (OSError, ValueError, DiffReportError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(
            {
                "ok": True,
                "diagram": diagram_key,
                "comments": self._workspace_relative(comments_path),
                "source": source,
                "svg": svg,
            }
        )

    def _handle_preview_agent_diagram(self, query: dict[str, list[str]]) -> None:
        try:
            _comments_path, diagram_key = self._agent_diagram_request(query)
            content_length = self.headers.get("Content-Length")
            size = int(content_length or "0")
            if size < 0 or size > _MAX_ARTIFACT_BYTES:
                self._send_json({"error": "diagram preview is too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            request_payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(request_payload, dict):
                raise ValueError("request body must be an object")
            if request_payload.get("source_format") == "plantuml":
                source = request_payload.get("source")
                if not isinstance(source, str):
                    raise ValueError("request source must be a string")
                try:
                    agent_raw = parse_agent_diagram_source(source, diagram_key=diagram_key)
                except (ValueError, DiffReportError) as error:
                    diagnostic_svg = self._plantuml_diagnostic_svg(source, diagram_key)
                    payload: dict[str, Any] = {"error": str(error)}
                    if diagnostic_svg:
                        payload.update({"source": source, "svg": diagnostic_svg})
                    self._send_json(payload, HTTPStatus.BAD_REQUEST)
                    return
            else:
                value = request_payload.get("value")
                if not isinstance(value, dict):
                    raise ValueError("request value must be an object")
                if "agent_diagram" in value:
                    agent_raw = value["agent_diagram"]
                else:
                    agent_raw = value
                if not isinstance(agent_raw, dict):
                    raise ValueError("agent_diagram must be an object")
            source, svg = agent_diagram_artifacts(agent_raw, diagram_key=diagram_key)
        except (OSError, ValueError, DiffReportError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json(
            {
                "ok": True,
                "diagram": diagram_key,
                "source": source,
                "svg": svg,
            }
        )

    @staticmethod
    def _plantuml_diagnostic_svg(source: str, diagram_key: str) -> str | None:
        try:
            return render_plantuml_source_svg(source, diagram_key=diagram_key, allow_error_svg=True)
        except DiffReportError:
            return None

    def _agent_diagram_request(self, query: dict[str, list[str]]) -> tuple[Path, str]:
        comments_path = self._resolve_comments_file(query)
        diagram_key = _single_query_value(query, "diagram")
        if diagram_key is None or not diagram_key.strip():
            raise ValueError("diagram is required")
        return comments_path, diagram_key

    def _resolve_comments_file(self, query: dict[str, list[str]]) -> Path:
        raw_task = _single_query_value(query, "task")
        raw_path = _single_query_value(query, "comments")
        if raw_task is None or raw_path is None:
            raise ValueError("task and comments are required")
        task = Path(raw_task)
        comments = Path(raw_path)
        if task.is_absolute() or comments.is_absolute():
            raise ValueError("task and comments must be workspace-relative")
        if ".." in task.parts or ".." in comments.parts:
            raise ValueError("task and comments must not contain '..'")
        if len(task.parts) < 2 or task.parts[0] != "tasks":
            raise ValueError("task must be under tasks/")
        if len(comments.parts) < 3 or comments.parts[:2] != ("report", "diff") or comments.suffix != ".json":
            raise ValueError("comments path must be report/diff/*.json")
        path = (self.server.workspace / task / comments).resolve()
        root = (self.server.workspace / task / "report" / "diff").resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("comments path escapes report/diff/") from error
        return path

    @staticmethod
    def _read_comments_payload(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("comments JSON must be an object")
        return payload

    @staticmethod
    def _raw_agent_diagram(payload: dict[str, Any], diagram_key: str) -> dict[str, Any]:
        diagrams = payload.get("diagrams")
        if not isinstance(diagrams, dict):
            raise ValueError("comments.diagrams must be an object")
        raw_diagram = diagrams.get(diagram_key)
        if not isinstance(raw_diagram, dict):
            raise ValueError("diagram entry must be an object")
        if "agent_diagram" not in raw_diagram and "variant_of" not in raw_diagram:
            raise ValueError("diagram is not an agent_diagram entry")
        return raw_diagram

    def _render_agent_diagram_entry(
        self,
        payload: dict[str, Any],
        comments_path: Path,
        diagram_key: str,
        raw_diagram: dict[str, Any],
    ) -> tuple[str | None, str]:
        if "variant_of" in raw_diagram:
            parent_id = str(raw_diagram["variant_of"])
            parent_raw = self._raw_agent_diagram(payload, parent_id)
            parent_agent = parent_raw.get("agent_diagram")
            if not isinstance(parent_agent, dict):
                raise ValueError("variant parent must define agent_diagram")
            agent_raw = merge_agent_diagram_variant(parent_agent, raw_diagram, diagram_key=diagram_key)
        else:
            agent_raw = raw_diagram.get("agent_diagram")
            if not isinstance(agent_raw, dict):
                raise ValueError("agent_diagram must be an object")
        source, svg = agent_diagram_artifacts(agent_raw, diagram_key=diagram_key)
        if "source" in raw_diagram:
            source_path = (comments_path.parent / str(raw_diagram["source"])).resolve()
            self._write_task_puml_artifact(source_path, comments_path, ".puml", source)
        if "svg" in raw_diagram:
            svg_path = (comments_path.parent / str(raw_diagram["svg"])).resolve()
            self._write_task_puml_artifact(svg_path, comments_path, ".svg", svg)
        return source if "source" in raw_diagram else None, svg

    def _agent_diagram_source(
        self,
        payload: dict[str, Any],
        diagram_key: str,
        raw_diagram: dict[str, Any],
    ) -> str | None:
        if "variant_of" in raw_diagram:
            parent_id = str(raw_diagram["variant_of"])
            parent_raw = self._raw_agent_diagram(payload, parent_id)
            parent_agent = parent_raw.get("agent_diagram")
            if not isinstance(parent_agent, dict):
                raise ValueError("variant parent must define agent_diagram")
            agent_raw = merge_agent_diagram_variant(parent_agent, raw_diagram, diagram_key=diagram_key)
        else:
            agent_raw = raw_diagram.get("agent_diagram")
            if not isinstance(agent_raw, dict):
                raise ValueError("agent_diagram must be an object")
        return compile_agent_diagram(agent_raw, diagram_key=diagram_key)

    def _write_task_puml_artifact(self, path: Path, comments_path: Path, suffix: str, text: str) -> None:
        task_root = comments_path.parents[2]
        root = (task_root / "report" / "puml").resolve()
        if path.suffix != suffix:
            raise ValueError(f"agent_diagram artifact must be {suffix}")
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("agent_diagram artifacts must stay under report/puml/") from error
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _resolve_artifact(
        self,
        query: dict[str, list[str]],
        *,
        path_key: str = "path",
        allowed_root: str | None = None,
        allowed_suffixes: set[str] | None = None,
    ) -> Path:
        raw_task = _single_query_value(query, "task")
        raw_path = _single_query_value(query, path_key)
        if raw_task is None or raw_path is None:
            raise ValueError(f"task and {path_key} are required")
        task = Path(raw_task)
        artifact = Path(raw_path)
        if task.is_absolute() or artifact.is_absolute():
            raise ValueError(f"task and {path_key} must be workspace-relative")
        if ".." in task.parts or ".." in artifact.parts:
            raise ValueError(f"task and {path_key} must not contain '..'")
        if len(task.parts) < 2 or task.parts[0] != "tasks":
            raise ValueError("task must be under tasks/")
        if len(artifact.parts) < 3 or artifact.parts[0] != "report":
            raise ValueError("artifact path must be under report/drawio/")
        root_name = artifact.parts[1]
        allowed_roots = {allowed_root} if allowed_root is not None else {"drawio"}
        if root_name not in allowed_roots:
            roots = " or ".join(f"report/{root}/" for root in sorted(allowed_roots))
            raise ValueError(f"artifact path must be under {roots}")
        if root_name == "drawio":
            suffixes = {".drawio", ".svg"}
        else:
            raise ValueError("unsupported artifact root")
        if allowed_suffixes is not None:
            suffixes = suffixes & allowed_suffixes
        if artifact.suffix not in suffixes:
            suffix_list = " or ".join(sorted(suffixes))
            raise ValueError(f"only {suffix_list} artifacts are writable")
        path = (self.server.workspace / task / artifact).resolve()
        root = (self.server.workspace / task / "report" / root_name).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"artifact path escapes report/{root_name}/") from error
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
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
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
