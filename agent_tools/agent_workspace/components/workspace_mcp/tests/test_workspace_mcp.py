from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys

from agent_tools.agent_workspace.components.workspace_mcp.api import build_workspace_mcp_server
from agent_tools.agent_workspace.components.workspace_mcp.api import workspace_mcp_stdio_config


def test_workspace_mcp_lists_agent_search_tools(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    tools = response["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "agent_search_files",
        "agent_search_show",
        "agent_search_text",
        "task_context_query",
    ]
    assert tools[0]["inputSchema"]["type"] == "object"


def test_workspace_mcp_calls_agent_search_text(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("def target():\n    return 'needle'\n", encoding="utf-8")
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "agent_search_text",
                "arguments": {
                    "query": "needle",
                    "root": ".",
                    "type": ["py"],
                    "max_output_lines": 30,
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is False
    assert "matches=1" in result["content"][0]["text"]
    assert "source.py:2:13" in result["content"][0]["text"]


def test_workspace_mcp_calls_agent_search_text_json(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("needle\n", encoding="utf-8")
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "agent_search_text",
                "arguments": {
                    "query": "needle",
                    "output_format": "json",
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["structuredContent"]["total_matches"] == 1
    assert json.loads(result["content"][0]["text"])["matches"][0]["path"] == "source.txt"


def test_workspace_mcp_calls_agent_search_show(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("one\ntwo\nthree\n", encoding="utf-8")
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "agent_search_show",
                "arguments": {
                    "path": "source.txt",
                    "line": 2,
                    "around": 1,
                },
            },
        }
    )

    assert response is not None
    assert response["result"]["isError"] is False
    assert "source.txt:1:3" in response["result"]["content"][0]["text"]


def test_workspace_mcp_blocks_paths_outside_workspace(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "agent_search_show",
                "arguments": {
                    "path": str(tmp_path.parent / "outside.txt"),
                },
            },
        }
    )

    assert response is not None
    assert response["result"]["isError"] is True
    assert "outside workspace" in response["result"]["content"][0]["text"]


def test_workspace_mcp_stdio_serves_json_lines(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)
    stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 6, "method": "initialize"}) + "\n")
    stdout = io.StringIO()

    server.serve_stdio(stdin, stdout)

    payload = json.loads(stdout.getvalue())
    assert payload["id"] == 6
    assert payload["result"]["serverInfo"]["name"] == "agent_tools_workspace"
    assert "tools" in payload["result"]["capabilities"]


def test_workspace_mcp_stdio_config_points_at_component_module(tmp_path: Path) -> None:
    config = workspace_mcp_stdio_config(tmp_path, python_executable="python")

    assert config["command"] == "python"
    assert config["args"] == [
        "-m",
        "agent_tools.agent_workspace.components.workspace_mcp",
        "--workspace",
        str(tmp_path.resolve()),
    ]
    assert config["env"]["PYTHONPATH"] == str(tmp_path.resolve())


def test_workspace_mcp_config_import_does_not_load_search_runtime() -> None:
    script = """
import importlib.abc
import sys

class BlockRegex(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "regex":
            raise ModuleNotFoundError("blocked regex import")
        return None

sys.meta_path.insert(0, BlockRegex())
from agent_tools.agent_workspace.components.workspace_mcp.api import workspace_mcp_stdio_config
workspace_mcp_stdio_config(__import__("pathlib").Path.cwd())
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_workspace_mcp_initialize_does_not_load_search_runtime() -> None:
    script = """
import importlib.abc
import io
import json
import sys
from pathlib import Path

class BlockRegex(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "regex":
            raise ModuleNotFoundError("blocked regex import")
        return None

sys.meta_path.insert(0, BlockRegex())
from agent_tools.agent_workspace.components.workspace_mcp.api import build_workspace_mcp_server

server = build_workspace_mcp_server(Path.cwd())
stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\\n")
stdout = io.StringIO()
server.serve_stdio(stdin, stdout)
print(stdout.getvalue(), end="")
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"]["serverInfo"]["name"] == "agent_tools_workspace"


def test_workspace_mcp_reports_missing_search_dependency_on_tool_call() -> None:
    script = """
import importlib.abc
import json
import sys
from pathlib import Path

class BlockRegex(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "regex":
            raise ModuleNotFoundError("blocked regex import")
        return None

sys.meta_path.insert(0, BlockRegex())
from agent_tools.agent_workspace.components.workspace_mcp.api import build_workspace_mcp_server

server = build_workspace_mcp_server(Path.cwd())
response = server.handle_message({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "agent_search_files", "arguments": {"query": "runtime.py"}},
})
print(json.dumps(response))
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    result = payload["result"]
    assert result["isError"] is True
    assert "dependency is missing" in result["content"][0]["text"]
    assert "install-agent-tools.py" in result["content"][0]["text"]


def test_workspace_mcp_task_context_tool_survives_missing_search_dependency() -> None:
    script = """
import importlib.abc
import json
import sys
import tempfile
from pathlib import Path

class BlockRegex(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "regex":
            raise ModuleNotFoundError("blocked regex import")
        return None

sys.meta_path.insert(0, BlockRegex())
from agent_tools.agent_workspace.components.workspace_mcp.api import build_workspace_mcp_server
from agent_tools.tools.task_context import set_slot

with tempfile.TemporaryDirectory() as workspace_text:
    workspace = Path(workspace_text)
    task_dir = workspace / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    set_slot(task_dir, "goal", "Read context without search deps.")
    server = build_workspace_mcp_server(workspace)
    tools = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    query = server.handle_message({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "task_context_query",
            "arguments": {
                "task": "tasks/sample",
                "categories": ["goal"],
            },
        },
    })
    search = server.handle_message({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "agent_search_files", "arguments": {"query": "sample"}},
    })
    print(json.dumps({"tools": tools, "query": query, "search": search}))
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    tool_names = [tool["name"] for tool in payload["tools"]["result"]["tools"]]
    assert tool_names == ["task_context_query"]
    assert payload["query"]["result"]["isError"] is False
    assert "Read context without search deps." in payload["query"]["result"]["content"][0]["text"]
    assert payload["search"]["result"]["isError"] is True
    assert "dependency is missing" in payload["search"]["result"]["content"][0]["text"]


def test_workspace_mcp_calls_task_context_query(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    from agent_tools.tools.task_context import set_slot

    set_slot(task_dir, "goal", "Read context through MCP.")
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "task_context_query",
                "arguments": {
                    "task": "tasks/sample",
                    "categories": ["goal"],
                    "format": "json",
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["slots"][0]["category"] == "goal"
    assert result["structuredContent"]["slots"][0]["content"] == "Read context through MCP."


def test_workspace_mcp_task_context_query_blocks_non_task_paths(tmp_path: Path) -> None:
    outside = tmp_path / "not-a-task"
    outside.mkdir()
    server = build_workspace_mcp_server(tmp_path)

    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "task_context_query",
                "arguments": {
                    "task": "not-a-task",
                },
            },
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "workspace tasks/" in result["content"][0]["text"]
