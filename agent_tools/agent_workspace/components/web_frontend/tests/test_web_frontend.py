from __future__ import annotations

import pytest

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def _create_web_server_or_skip(workspace: Path):
    try:
        return create_web_server(workspace, "127.0.0.1", 0)
    except PermissionError as exc:
        pytest.skip(f"web server socket is unavailable in this environment: {exc}")


def test_agent_workspace_web_server_exposes_tasks_api(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")

    server = _create_web_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urlopen(f"http://{host}:{port}/api/tasks", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        with urlopen(f"http://{host}:{port}/", timeout=5) as response:
            html = response.read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["tasks"][0]["name"] == "sample-task"
    assert "Agent Workspace" in html
    assert "AI Debug" in html


def test_agent_workspace_web_server_exposes_settings_ui_contract(tmp_path: Path) -> None:
    server = _create_web_server_or_skip(tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        with urlopen(f"http://{host}:{port}/api/ui-contract/settings", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert data["schema"] == "agent-workspace-ui-tree-v1"
    assert data["view"] == "settings"
    assert data["root_id"] == "settings.dialog"
    node_ids = {node["id"] for node in data["nodes"]}
    assert "settings.limited_bash_head_tokens" in node_ids
    assert "settings.limited_bash_heartbeat_tokens" in node_ids
