from __future__ import annotations

from email.message import Message
import json
from http import HTTPStatus
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request
from urllib.request import urlopen

import pytest

from agent_tools.agent_workspace.components.web_frontend.api import create_server
from agent_tools.agent_workspace.components.web_frontend.src.web_ui import AgentWorkspaceWebHandler
from agent_tools.agent_workspace.components.web_frontend.src.web_ui import MAX_JSON_BODY_BYTES
from agent_tools.agent_workspace.components.web_frontend.src import web_ui as web_ui_module
from agent_tools.agent_workspace.components.workspace_service.src import service as service_module
from agent_tools.tools.task_context import set_slot


def _create_server_or_skip(workspace: Path):
    try:
        return create_server(workspace, "127.0.0.1", 0)
    except PermissionError as exc:
        pytest.skip(f"web server socket is unavailable in this environment: {exc}")


def test_agent_workspace_service_and_web_modules_do_not_import_gtk() -> None:
    code = "\n".join(
        [
            "import sys",
            "import agent_tools.agent_workspace.components.workspace_service.api",
            "import agent_tools.agent_workspace.components.web_frontend.api",
            "assert 'gi' not in sys.modules, sorted(name for name in sys.modules if name.startswith('gi'))",
        ]
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def test_agent_workspace_web_tasks_api_creates_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        set_slot(Path(command[3]), "goal", "Created through the web API.")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(service_module.subprocess, "run", fake_run)
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks",
            data=json.dumps({"name": "created-task", "privacy": "private"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            status = response.status
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert status == 201
    assert data["task"]["name"] == "created-task"
    assert (tmp_path / "tasks" / "created-task" / "TASK_CONTEXT.sqlite3").is_file()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not-json", "Expecting value"),
        (b"[]", "JSON body must be an object"),
        (json.dumps({"privacy": "public"}).encode("utf-8"), "missing task name"),
    ],
)
def test_agent_workspace_web_tasks_api_rejects_invalid_json_body(
    tmp_path: Path,
    body: bytes,
    message: str,
) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(f"http://{host}:{port}/api/tasks", data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 400
    assert message in data["error"]


def test_agent_workspace_web_tasks_api_rejects_oversized_body(tmp_path: Path) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks",
            data=b"x" * (MAX_JSON_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 413
    assert "exceeds" in data["error"]


def test_agent_workspace_web_tasks_api_reports_creation_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def time_out(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(service_module.subprocess, "run", time_out)
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks",
            data=json.dumps({"name": "slow-task"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 504
    assert data == {"error": "task creation timed out"}


def test_agent_workspace_web_tasks_api_requires_json_content_type(tmp_path: Path) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks",
            data=b'{"name":"cross-origin-task"}',
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 415
    assert data == {"error": "Content-Type must be application/json"}


def test_agent_workspace_web_tasks_api_rejects_lone_surrogate_name(tmp_path: Path) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks",
            data=b'{"name":"\\ud800"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 400
    assert data["error"].startswith("invalid task name:")


def test_agent_workspace_web_tasks_api_rejects_duplicate_content_length(tmp_path: Path) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with socket.create_connection((host, port), timeout=5) as connection:
            connection.sendall(
                b"POST /api/tasks HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 2\r\n"
                b"Content-Length: 2\r\n"
                b"Connection: close\r\n\r\n{}"
            )
            response = connection.makefile("rb").read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.startswith(b"HTTP/1.0 400 Bad Request\r\n")
    assert b"multiple Content-Length headers" in response


def test_agent_workspace_web_tasks_api_times_out_incomplete_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_ui_module, "REQUEST_BODY_TIMEOUT_SECONDS", 0.1)
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with socket.create_connection((host, port), timeout=5) as connection:
            connection.sendall(
                b"POST /api/tasks HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 20\r\n"
                b"Connection: close\r\n\r\n{"
            )
            response = connection.makefile("rb").read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.startswith(b"HTTP/1.0 408 Request Timeout\r\n")
    assert b"request body timed out" in response


@pytest.mark.parametrize(
    ("extra_headers", "status", "message"),
    [
        (b"Transfer-Encoding: chunked\r\nContent-Length: 2\r\n", 400, b"Transfer-Encoding is not supported"),
        (b"Content-Length: " + (b"9" * 1000) + b"\r\n", 413, b"JSON body exceeds"),
        (b"Content-Length: 00002\r\n", 400, b"invalid Content-Length"),
    ],
)
def test_agent_workspace_web_tasks_api_rejects_ambiguous_body_framing(
    tmp_path: Path,
    extra_headers: bytes,
    status: int,
    message: bytes,
) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with socket.create_connection((host, port), timeout=5) as connection:
            connection.sendall(
                b"POST /api/tasks HTTP/1.1\r\n"
                b"Host: localhost\r\n"
                b"Content-Type: application/json\r\n"
                + extra_headers
                + b"Connection: close\r\n\r\n{}"
            )
            response = connection.makefile("rb").read()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert response.startswith(f"HTTP/1.0 {status} ".encode("ascii"))
    assert message in response


def test_agent_workspace_web_context_api_returns_slots(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    set_slot(task, "validation", "Run web service smoke.")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/api/tasks/sample-task/context"
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert [entry["category"] for entry in data["entries"]] == ["validation"]
    assert data["entries"][0]["content"] == "Run web service smoke."
    assert data["markdown"].startswith("```text\n+---")
    assert "| Validation" in data["markdown"]


def test_agent_workspace_web_context_slot_api_updates_one_slot(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks/sample-task/context-slot?category=findings",
            data=json.dumps({"content": "Saved through the web API."}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["slot"]["category"] == "findings"
    assert data["slot"]["content"] == "Saved through the web API."
    assert data["context"]["entries"][0]["content"] == "Saved through the web API."


@pytest.mark.parametrize(
    ("task_name", "query", "payload", "status", "error"),
    [
        ("sample-task", "", {"content": "text"}, 400, "missing category"),
        (
            "sample-task",
            "?category=findings",
            {"content": ["not", "text"]},
            400,
            "context content must be a string",
        ),
        ("missing-task", "?category=findings", {"content": "text"}, 404, "unknown task"),
    ],
)
def test_agent_workspace_web_context_slot_api_rejects_invalid_request(
    tmp_path: Path,
    task_name: str,
    query: str,
    payload: object,
    status: int,
    error: str,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks/{task_name}/context-slot{query}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == status
    assert error in data["error"]


def test_agent_workspace_web_context_slot_api_rejects_unknown_route_before_body(
    tmp_path: Path,
) -> None:
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks/sample-task/extra/context-slot",
            data=b"not-json",
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 404
    assert data == {"error": "not found"}


def test_agent_workspace_web_context_slot_api_reports_database_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")

    def fail_slot_update(*_args: object, **_kwargs: object) -> object:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(service_module, "set_task_context_slot", fail_slot_update)
    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = Request(
            f"http://{host}:{port}/api/tasks/sample-task/context-slot?category=findings",
            data=json.dumps({"content": "text"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(request, timeout=5)
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == 500
    assert data == {"error": "context slot update failed"}


def test_agent_workspace_web_context_api_returns_encoded_slot_markdown(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    set_slot(task, "findings", "drivers/firmware/scmi/scmi.c appears in browser context.")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/api/tasks/sample-task/context?severity=high&status=active&encoded=1"
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["dictionary"] == []
    assert data["entries"][0]["category"] == "findings"
    assert data["markdown"].startswith("```text\n+---")
    assert "| Findings" in data["markdown"]


def test_agent_workspace_web_context_api_returns_encoded_slot_dictionary(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    repeated = "drivers/firmware/scmi/scmi.c"
    set_slot(task, "findings", f"{repeated} appears. {repeated} repeats. {repeated} remains.")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        url = f"http://{host}:{port}/api/tasks/sample-task/context?encoded=1"
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["dictionary"][0]["token"] == "§00"
    assert data["dictionary"][0]["value"] == repeated
    assert "## Task Dictionary" in data["markdown"]
    assert "§00 appears" in data["markdown"]


def test_agent_workspace_web_artifact_api_returns_bounded_preview(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    report = task / "report"
    report.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    (report / "notes.md").write_text("artifact preview", encoding="utf-8")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        label = quote("report/notes.md", safe="")
        with urlopen(
            f"http://{host}:{port}/api/tasks/sample-task/artifact?path={label}",
            timeout=5,
        ) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["label"] == "report/notes.md"
    assert data["content"] == "artifact preview"
    assert data["binary"] is False
    assert data["truncated"] is False


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("", "missing artifact path"),
        (f"?path={quote('../outside.txt', safe='')}", "unknown artifact"),
        ("/extra?path=report%2Fnotes.md", "unknown endpoint"),
    ],
)
def test_agent_workspace_web_artifact_api_rejects_invalid_path(
    tmp_path: Path,
    query: str,
    message: str,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with pytest.raises(HTTPError) as raised:
            urlopen(
                f"http://{host}:{port}/api/tasks/sample-task/artifact{query}",
                timeout=5,
            )
        data = json.loads(raised.value.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert raised.value.code == (404 if query.startswith("/extra") else 400)
    assert message in data["error"]


def test_agent_workspace_web_terminal_lifecycle_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Terminal HTTP task")
    monkeypatch.setattr(
        service_module,
        "shell_command",
        lambda: [
            sys.executable,
            "-u",
            "-c",
            (
                "import time; print('terminal-ready', flush=True); "
                "line = input(); print('terminal-echo:' + line, flush=True); time.sleep(30)"
            ),
        ],
    )
    monkeypatch.setattr(service_module, "shell_environment", lambda env, _task_name: env)

    server = _create_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base_url = f"http://{host}:{port}/api/tasks/sample-task"
        forbidden_request = Request(
            f"{base_url}/terminals",
            data=b"{}",
            headers={"Content-Type": "application/json", "Host": "attacker.example"},
            method="POST",
        )
        with pytest.raises(HTTPError) as raised:
            urlopen(forbidden_request, timeout=5)
        assert raised.value.code == 403

        start_request = Request(
            f"{base_url}/terminals",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(start_request, timeout=5) as response:
            assert response.status == 201
            started = json.loads(response.read().decode("utf-8"))
        session_id = started["session"]["id"]

        with urlopen(f"{base_url}/terminals", timeout=5) as response:
            listed = json.loads(response.read().decode("utf-8"))
        assert [session["id"] for session in listed["sessions"]] == [session_id]

        output: dict[str, object] = {}
        for _attempt in range(50):
            with urlopen(
                f"{base_url}/terminal-output?id={quote(session_id)}&offset=0",
                timeout=5,
            ) as response:
                output = json.loads(response.read().decode("utf-8"))
            if "terminal-ready" in str(output["text"]):
                break
            time.sleep(0.05)
        assert "terminal-ready" in str(output["text"])
        output_offset = int(output["offset"])

        resize_request = Request(
            f"{base_url}/terminal-resize",
            data=json.dumps({"id": session_id, "rows": 32, "columns": 100}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(resize_request, timeout=5) as response:
            resized = json.loads(response.read().decode("utf-8"))
        assert resized["rows"] == 32
        assert resized["columns"] == 100

        input_request = Request(
            f"{base_url}/terminal-input",
            data=json.dumps({"id": session_id, "data": "hello\n", "sequence": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(input_request, timeout=5) as response:
            accepted = json.loads(response.read().decode("utf-8"))
        assert accepted == {"id": session_id, "sequence": 1, "accepted": True}

        with urlopen(input_request, timeout=5) as response:
            retried = json.loads(response.read().decode("utf-8"))
        assert retried == accepted

        echoed: dict[str, object] = {}
        for _attempt in range(50):
            with urlopen(
                f"{base_url}/terminal-output?id={quote(session_id)}&offset={output_offset}",
                timeout=5,
            ) as response:
                echoed = json.loads(response.read().decode("utf-8"))
            if "terminal-echo:hello" in str(echoed["text"]):
                break
            time.sleep(0.05)
        assert "terminal-echo:hello" in str(echoed["text"])

        with pytest.raises(HTTPError) as raised:
            urlopen(
                f"{base_url}/terminal-output?id={quote(session_id)}&offset=not-a-number",
                timeout=5,
            )
        assert raised.value.code == 400

        close_request = Request(
            f"{base_url}/terminals?id={quote(session_id)}",
            method="DELETE",
        )
        with urlopen(close_request, timeout=5) as response:
            closed = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert closed["closed"] is True
    assert closed["session"]["exited"] is True


def test_agent_workspace_web_terminal_start_closes_session_when_response_fails() -> None:
    class FakeService:
        def __init__(self) -> None:
            self.closed: list[tuple[str, str]] = []

        def start_shell_terminal(self, task_name: str) -> dict[str, object]:
            return {"session": {"id": "terminal-1", "task": task_name}, "sessions": []}

        def close_terminal(self, task_name: str, session_id: str) -> dict[str, object]:
            self.closed.append((task_name, session_id))
            return {"closed": True}

    service = FakeService()
    handler = object.__new__(AgentWorkspaceWebHandler)
    handler.workspace_service = service  # type: ignore[assignment]
    handler.log_error = lambda *_args: None  # type: ignore[method-assign]

    def fail_response(_value: object, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        raise BrokenPipeError(status)

    handler._send_json = fail_response  # type: ignore[method-assign]

    with pytest.raises(BrokenPipeError):
        handler._handle_shell_terminal_start("sample-task")

    assert service.closed == [("sample-task", "terminal-1")]


@pytest.mark.parametrize(
    ("endpoint", "body", "message"),
    [
        ("terminal-input", {"data": "x", "sequence": 1}, "missing terminal id"),
        ("terminal-input", {"id": "t1", "data": [], "sequence": 1}, "input must be a string"),
        ("terminal-input", {"id": "t1", "data": "x", "sequence": True}, "positive 64-bit integer"),
        ("terminal-input", {"id": "t1", "data": "x", "sequence": 0}, "positive 64-bit integer"),
        ("terminal-resize", {"id": "t1", "rows": True, "columns": 80}, "integer rows"),
        ("terminal-resize", {"id": "t1", "rows": 24, "columns": "80"}, "integer rows"),
    ],
)
def test_agent_workspace_web_terminal_update_rejects_invalid_payload(
    endpoint: str,
    body: dict[str, object],
    message: str,
) -> None:
    class FakeService:
        def send_terminal_input(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("service must not receive invalid input")

        def resize_terminal(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("service must not receive invalid size")

    handler = object.__new__(AgentWorkspaceWebHandler)
    handler.workspace_service = FakeService()  # type: ignore[assignment]
    errors: list[tuple[HTTPStatus, str]] = []
    handler._send_error = lambda status, text: errors.append((status, text))  # type: ignore[method-assign]

    handler._handle_terminal_update("sample-task", endpoint, body)

    assert errors[0][0] == HTTPStatus.BAD_REQUEST
    assert message in errors[0][1]


def test_agent_workspace_web_terminal_api_rejects_non_loopback_peer() -> None:
    handler = object.__new__(AgentWorkspaceWebHandler)
    handler.headers = Message()
    handler.headers["Host"] = "localhost:8765"
    handler.client_address = ("192.0.2.10", 50000)
    errors: list[tuple[HTTPStatus, str]] = []
    handler._send_error = lambda status, message: errors.append((status, message))  # type: ignore[method-assign]

    assert handler._allow_loopback_terminal_request() is False
    assert errors == [(HTTPStatus.FORBIDDEN, "terminal API is available only from loopback")]
