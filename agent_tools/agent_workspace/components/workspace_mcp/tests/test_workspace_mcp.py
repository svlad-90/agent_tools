from __future__ import annotations

import io
import json
from pathlib import Path

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
