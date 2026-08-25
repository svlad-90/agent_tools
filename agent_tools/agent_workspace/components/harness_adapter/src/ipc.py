from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import threading
from typing import Any


WORKSPACE_IPC_ENDPOINT_FILE = ".agent-workspace-ipc.json"
WORKSPACE_IPC_MESSAGE_LIMIT = 64 * 1024


@dataclass(frozen=True)
class WorkspaceIpcEvent:
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class WorkspaceIpcEndpoint:
    host: str
    port: int
    token: str
    pid: int
    updated_at: str


class WorkspaceIpcServer:
    def __init__(
        self,
        workspace: Path,
        server: socketserver.ThreadingTCPServer,
        thread: threading.Thread,
        token: str,
    ) -> None:
        self.workspace = workspace.resolve()
        self.server = server
        self.thread = thread
        self.token = token

    @property
    def endpoint(self) -> WorkspaceIpcEndpoint:
        host, port = self.server.server_address
        return WorkspaceIpcEndpoint(
            host=str(host),
            port=int(port),
            token=self.token,
            pid=os.getpid(),
            updated_at=_now(),
        )

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        try:
            workspace_ipc_endpoint_path(self.workspace).unlink(missing_ok=True)
        except OSError:
            pass


WorkspaceIpcCallback = Callable[[WorkspaceIpcEvent], None]


def start_workspace_ipc_server(workspace: Path, callback: WorkspaceIpcCallback) -> WorkspaceIpcServer | None:
    workspace = workspace.resolve()
    token = secrets.token_urlsafe(24)

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            raw = self.request.recv(WORKSPACE_IPC_MESSAGE_LIMIT + 1)
            if len(raw) > WORKSPACE_IPC_MESSAGE_LIMIT:
                return
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return
            event = _event_from_message(data, token)
            if event is None:
                return
            callback(event)

    try:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    except OSError:
        return None
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    ipc_server = WorkspaceIpcServer(workspace, server, thread, token)
    try:
        save_workspace_ipc_endpoint(workspace, ipc_server.endpoint)
    except OSError:
        server.server_close()
        return None
    thread.start()
    return ipc_server


def notify_workspace_ipc(workspace: Path, event_type: str, payload: dict[str, Any]) -> bool:
    endpoint = load_workspace_ipc_endpoint(workspace)
    if endpoint is None:
        return False
    if endpoint.host != "127.0.0.1" or not _process_is_alive(endpoint.pid):
        return False
    message = json.dumps(
        {
            "token": endpoint.token,
            "type": event_type,
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    try:
        with socket.create_connection((endpoint.host, endpoint.port), timeout=0.2) as connection:
            connection.sendall(message)
    except OSError:
        return False
    return True


def save_workspace_ipc_endpoint(workspace: Path, endpoint: WorkspaceIpcEndpoint) -> None:
    path = workspace_ipc_endpoint_path(workspace)
    path.write_text(
        json.dumps(
            {
                "host": endpoint.host,
                "port": endpoint.port,
                "token": endpoint.token,
                "pid": endpoint.pid,
                "updated_at": endpoint.updated_at,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def load_workspace_ipc_endpoint(workspace: Path) -> WorkspaceIpcEndpoint | None:
    try:
        data = json.loads(workspace_ipc_endpoint_path(workspace).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    host = data.get("host")
    port = data.get("port")
    token = data.get("token")
    pid = data.get("pid")
    updated_at = data.get("updated_at")
    if not isinstance(host, str) or not isinstance(port, int):
        return None
    if not isinstance(token, str) or not token:
        return None
    if not isinstance(pid, int):
        return None
    if not isinstance(updated_at, str):
        updated_at = ""
    return WorkspaceIpcEndpoint(
        host=host,
        port=port,
        token=token,
        pid=pid,
        updated_at=updated_at,
    )


def workspace_ipc_endpoint_path(workspace: Path) -> Path:
    return workspace.resolve() / WORKSPACE_IPC_ENDPOINT_FILE


def _event_from_message(data: object, token: str) -> WorkspaceIpcEvent | None:
    if not isinstance(data, dict):
        return None
    if data.get("token") != token:
        return None
    event_type = data.get("type")
    payload = data.get("payload")
    if not isinstance(event_type, str) or not isinstance(payload, dict):
        return None
    return WorkspaceIpcEvent(event_type=event_type, payload=payload)


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
