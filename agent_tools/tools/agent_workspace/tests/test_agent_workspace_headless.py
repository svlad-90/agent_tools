from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.request import urlopen

from agent_tools.tools.agent_workspace.web_ui import create_server
from agent_tools.tools.task_context import set_slot


def test_agent_workspace_service_and_web_modules_do_not_import_gtk() -> None:
    code = "\n".join(
        [
            "import sys",
            "import agent_tools.tools.agent_workspace.service",
            "import agent_tools.tools.agent_workspace.web_ui",
            "assert 'gi' not in sys.modules, sorted(name for name in sys.modules if name.startswith('gi'))",
        ]
    )

    subprocess.run([sys.executable, "-c", code], check=True)


def test_agent_workspace_web_context_api_returns_slots(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    set_slot(task, "validation", "Run web service smoke.")

    server = create_server(tmp_path, "127.0.0.1", 0)
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


def test_agent_workspace_web_context_api_returns_encoded_slot_markdown(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    set_slot(task, "goal", "Agent Workspace web service goal.")
    set_slot(task, "findings", "drivers/firmware/scmi/scmi.c appears in browser context.")

    server = create_server(tmp_path, "127.0.0.1", 0)
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

    server = create_server(tmp_path, "127.0.0.1", 0)
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
