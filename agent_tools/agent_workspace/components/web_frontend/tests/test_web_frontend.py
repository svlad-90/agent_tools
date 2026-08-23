from __future__ import annotations

from agent_tools.agent_workspace.components.test_support.src.helpers import *


def test_agent_workspace_web_server_exposes_tasks_api(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    (task / "TASK_DESCRIPTION.md").write_text("# Description\n", encoding="utf-8")

    server = create_web_server(tmp_path, "127.0.0.1", 0)
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

