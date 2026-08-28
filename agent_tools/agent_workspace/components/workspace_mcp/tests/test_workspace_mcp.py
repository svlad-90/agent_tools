from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

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
        "commit_msg_format",
        "knowledge_get_topic",
        "knowledge_list_topics",
        "knowledge_search_topics",
        "knowledge_set_topic",
        "push_guard_check",
        "push_guard_check_staged",
        "push_guard_install_hook",
        "push_guard_mark_success",
        "push_guard_status",
        "task_actions_add",
        "task_actions_delete",
        "task_actions_list",
        "task_actions_run",
        "task_actions_show",
        "task_actions_update",
        "task_context_add_entry",
        "task_context_compact",
        "task_context_compile_dictionary",
        "task_context_dictionary",
        "task_context_edit_entries",
        "task_context_migrate_legacy",
        "task_context_query",
        "task_context_set_slot",
        "validate_changed",
        "validate_task",
        "yaml_map_file",
        "yaml_map_item_insert",
        "yaml_map_parse_check",
        "yaml_map_path_delete",
        "yaml_map_path_get",
        "yaml_map_path_set",
        "yaml_map_project",
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
    assert tool_names == [
        "commit_msg_format",
        "knowledge_get_topic",
        "knowledge_list_topics",
        "knowledge_search_topics",
        "knowledge_set_topic",
        "push_guard_check",
        "push_guard_check_staged",
        "push_guard_install_hook",
        "push_guard_mark_success",
        "push_guard_status",
        "task_actions_add",
        "task_actions_delete",
        "task_actions_list",
        "task_actions_run",
        "task_actions_show",
        "task_actions_update",
        "task_context_add_entry",
        "task_context_compact",
        "task_context_compile_dictionary",
        "task_context_dictionary",
        "task_context_edit_entries",
        "task_context_migrate_legacy",
        "task_context_query",
        "task_context_set_slot",
        "validate_changed",
        "validate_task",
        "yaml_map_file",
        "yaml_map_item_insert",
        "yaml_map_parse_check",
        "yaml_map_path_delete",
        "yaml_map_path_get",
        "yaml_map_path_set",
        "yaml_map_project",
    ]
    assert payload["query"]["result"]["isError"] is False
    assert "Read context without search deps." in payload["query"]["result"]["content"][0]["text"]
    assert payload["search"]["result"]["isError"] is True
    assert "dependency is missing" in payload["search"]["result"]["content"][0]["text"]


def test_workspace_mcp_knowledge_set_get_list_and_search(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from agent_tools.tools import knowledge

    public_dir = tmp_path / "knowledge" / "topics"
    private_dir = tmp_path / "private" / "topics"
    public_dir.mkdir(parents=True)
    private_dir.mkdir(parents=True)
    monkeypatch.setattr(knowledge, "PUBLIC_TOPICS_DIR", public_dir)
    monkeypatch.setenv("AGENT_TOOLS_PRIVATE_KNOWLEDGE_DIR", str(private_dir))
    server = build_workspace_mcp_server(tmp_path)

    set_response = _mcp_call(
        server,
        "knowledge_set_topic",
        {
            "topic": "agent_tools",
            "finding": "MCP knowledge finding",
            "scope": "private",
        },
    )
    assert set_response["result"]["isError"] is False
    assert set_response["result"]["structuredContent"]["scope"] == "private"

    list_response = _mcp_call(server, "knowledge_list_topics", {"scope": "all"})
    assert list_response["result"]["structuredContent"]["topics"] == [
        {
            "scope": "private",
            "topic": "agent_tools",
            "path": str(private_dir / "agent_tools.md"),
        }
    ]

    get_response = _mcp_call(
        server,
        "knowledge_get_topic",
        {"topic": "agent_tools", "scope": "all", "with_header": True},
    )
    assert "# private:agent_tools" in get_response["result"]["content"][0]["text"]
    assert "MCP knowledge finding" in get_response["result"]["content"][0]["text"]

    search_response = _mcp_call(
        server,
        "knowledge_search_topics",
        {"query": "knowledge", "scope": "private"},
    )
    assert search_response["result"]["isError"] is False
    matches = search_response["result"]["structuredContent"]["matches"]
    assert matches[0]["topic"] == "agent_tools"
    assert matches[0]["line"] == 3


def test_workspace_mcp_knowledge_rejects_invalid_topic(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(server, "knowledge_get_topic", {"topic": "../bad"})

    assert response["result"]["isError"] is True
    assert "topic must match" in response["result"]["content"][0]["text"]


def test_workspace_mcp_knowledge_search_reports_no_matches(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from agent_tools.tools import knowledge

    topics_dir = tmp_path / "knowledge" / "topics"
    topics_dir.mkdir(parents=True)
    (topics_dir / "agent_tools.md").write_text("# agent_tools\n\n- finding\n", encoding="utf-8")
    monkeypatch.setattr(knowledge, "PUBLIC_TOPICS_DIR", topics_dir)
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "knowledge_search_topics",
        {"query": "missing", "scope": "public"},
    )

    assert response["result"]["isError"] is True
    assert response["result"]["structuredContent"]["matches"] == []


def test_workspace_mcp_commit_msg_formats_title_body_and_trailers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "commit_msg_format",
        {
            "repo": "repo",
            "title": "agent_workspace: expose commit messages over MCP",
            "message": (
                "Format commit messages from a separate title and a longer "
                "body text so agents can pass paragraphs without manually "
                "wrapping them.\n\n"
                "Assisted-by: Codex:gpt-5 code-map\n"
                "Reviewed-by: Example Reviewer <reviewer@example.com>"
            ),
        },
    )

    result = response["result"]
    message = result["structuredContent"]["message"]
    command_args = result["structuredContent"]["command_args"]
    assert result["isError"] is False
    assert message.startswith("agent_workspace: expose commit messages over MCP\n\n")
    assert "Signed-off-by: Example Author <author@example.com>" in message
    assert message.rstrip().endswith("Assisted-by: Codex:gpt-5 code-map")
    assert max(len(line) for line in message.splitlines()) <= 72
    assert command_args[:4] == ["git", "-C", str(repo), "commit"]
    assert command_args[4:] == [
        "-m",
        "agent_workspace: expose commit messages over MCP",
        "-m",
        (
            "Format commit messages from a separate title and a longer body text so\n"
            "agents can pass paragraphs without manually wrapping them."
        ),
        "-m",
        (
            "Reviewed-by: Example Reviewer <reviewer@example.com>\n"
            "Signed-off-by: Example Author <author@example.com>\n"
            "Assisted-by: Codex:gpt-5 code-map"
        ),
    ]
    assert "git -C" in result["structuredContent"]["shell_command"]


def test_workspace_mcp_commit_msg_reports_check_failures(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "commit_msg_format",
        {
            "title": "x" * 73,
            "message": "Body.",
            "add_signoff": False,
        },
    )

    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["long_lines"][0]["line"] == 1
    assert result["structuredContent"]["has_signed_off_by"] is False
    assert "commit message check failed" in result["content"][0]["text"]
    assert "missing Signed-off-by trailer" in result["content"][0]["text"]


def test_workspace_mcp_commit_msg_requires_signoff_trailer(tmp_path: Path) -> None:
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "commit_msg_format",
        {
            "title": "tools: require signoff",
            "message": "This mentions Signed-off-by: in prose only.",
            "add_signoff": False,
        },
    )

    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["long_lines"] == []
    assert result["structuredContent"]["has_signed_off_by"] is False


def test_workspace_mcp_push_guard_marks_status_and_checks_push(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.delenv("AGENT_TOOLS_WORKSPACE_ROOT", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    (repo / "tracked.txt").write_text("ok\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "Initial")
    commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    server = build_workspace_mcp_server(tmp_path)

    missing = _mcp_call(server, "push_guard_status", {"repo": "repo"})
    assert missing["result"]["isError"] is True
    assert missing["result"]["structuredContent"]["recorded"] is False

    blocked = _mcp_call(server, "push_guard_check", {"repo": "repo"})
    assert blocked["result"]["isError"] is True
    assert blocked["result"]["structuredContent"]["missing_validation"] == [commit]

    marked = _mcp_call(
        server,
        "push_guard_mark_success",
        {"repo": "repo", "source": "workspace_mcp test"},
    )
    assert marked["result"]["isError"] is False
    assert marked["result"]["structuredContent"]["commit"] == commit

    recorded = _mcp_call(server, "push_guard_status", {"repo": "repo"})
    assert recorded["result"]["isError"] is False
    assert recorded["result"]["structuredContent"]["recorded"] is True

    allowed = _mcp_call(server, "push_guard_check", {"repo": "repo"})
    assert allowed["result"]["isError"] is False
    assert allowed["result"]["structuredContent"]["blocked"] is False


def test_workspace_mcp_push_guard_checks_staged_files(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.delenv("AGENT_TOOLS_WORKSPACE_ROOT", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    artifact = repo / "download.zip"
    artifact.write_text("artifact\n", encoding="utf-8")
    _git(repo, "add", "download.zip")
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(server, "push_guard_check_staged", {"repo": "repo"})

    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["findings"] == [
        {
            "path": "download.zip",
            "reason": "artifact-like file suffix '.zip' is blocked",
        }
    ]


def test_workspace_mcp_push_guard_installs_hooks(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(server, "push_guard_install_hook", {"repo": "repo"})

    result = response["result"]
    assert result["isError"] is False
    for hook in result["structuredContent"]["hooks"]:
        hook_path = Path(hook)
        assert hook_path.is_file()
        assert hook_path.stat().st_mode & 0o111


def test_workspace_mcp_task_actions_lists_shows_and_runs(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample"
    task.mkdir(parents=True)
    (task / "TASK_ACTIONS.json").write_text(
        json.dumps(
            {
                "parameter_types": {"profile": {"set": "profiles"}},
                "parameter_sets": {"profiles": {"dev": {"name": "Dev"}}},
                "actions": [
                    {
                        "id": "echo",
                        "label": "Echo",
                        "command": [sys.executable, "-c", "print('ok')"],
                        "cwd": ".",
                        "parameters": [
                            {
                                "name": "profile",
                                "label": "Profile",
                                "type": "profile",
                                "default": "dev",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = build_workspace_mcp_server(tmp_path)

    listed = _mcp_call(server, "task_actions_list", {"task": "tasks/sample"})
    shown = _mcp_call(server, "task_actions_show", {"task": "tasks/sample", "action": "echo"})
    run = _mcp_call(
        server,
        "task_actions_run",
        {"task": "tasks/sample", "action": "echo", "bindings": {"profile": "dev"}},
    )

    assert listed["result"]["isError"] is False
    assert listed["result"]["structuredContent"]["actions"][0]["id"] == "echo"
    assert shown["result"]["structuredContent"]["action"]["parameters"][0]["name"] == "profile"
    assert run["result"]["isError"] is False
    assert run["result"]["structuredContent"]["stdout"] == "ok\n"


def test_workspace_mcp_task_actions_adds_updates_and_deletes(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample"
    task.mkdir(parents=True)
    server = build_workspace_mcp_server(tmp_path)

    added = _mcp_call(
        server,
        "task_actions_add",
        {
            "task": "tasks/sample",
            "action": "smoke",
            "label": "Smoke",
            "command": [sys.executable, "-c", "print('old')"],
            "env": {"MODE": "dev"},
        },
    )
    updated = _mcp_call(
        server,
        "task_actions_update",
        {
            "task": "tasks/sample",
            "action": "smoke",
            "label": "Smoke test",
            "command": [sys.executable, "-c", "print('new')"],
            "env": {"MODE": "release"},
        },
    )
    run = _mcp_call(server, "task_actions_run", {"task": "tasks/sample", "action": "smoke"})
    deleted = _mcp_call(server, "task_actions_delete", {"task": "tasks/sample", "action": "smoke"})

    assert added["result"]["isError"] is False
    assert added["result"]["structuredContent"]["action"]["id"] == "smoke"
    assert updated["result"]["structuredContent"]["action"]["label"] == "Smoke test"
    assert updated["result"]["structuredContent"]["action"]["env"] == {"MODE": "release"}
    assert run["result"]["structuredContent"]["stdout"] == "new\n"
    assert deleted["result"]["structuredContent"]["deleted"] == {
        "id": "smoke",
        "actions": 1,
        "shortcuts": 0,
    }


def test_workspace_mcp_task_actions_rejects_non_task_path(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(server, "task_actions_list", {"task": "outside"})

    assert response["result"]["isError"] is True
    assert "workspace tasks/" in response["result"]["content"][0]["text"]


def test_workspace_mcp_yaml_map_inspects_and_edits_with_hash_guard(tmp_path: Path) -> None:
    source = tmp_path / "config.yaml"
    source.write_text(
        "root:\n"
        "  enabled: true\n"
        "  items:\n"
        "    - one\n",
        encoding="utf-8",
    )
    server = build_workspace_mcp_server(tmp_path)

    mapped = _mcp_call(server, "yaml_map_file", {"path": "config.yaml"})
    project = _mcp_call(server, "yaml_map_project", {"path": ".", "output_format": "json"})
    parsed = _mcp_call(server, "yaml_map_parse_check", {"path": "config.yaml"})
    snapshot = _mcp_call(
        server,
        "yaml_map_path_get",
        {"path": "config.yaml", "yaml_path": "root.items", "output_format": "json"},
    )
    items_hash = snapshot["result"]["structuredContent"]["value_hash"]
    inserted = _mcp_call(
        server,
        "yaml_map_item_insert",
        {
            "path": "config.yaml",
            "yaml_path": "root.items",
            "expect_hash": items_hash,
            "value": "two",
            "output_format": "json",
        },
    )
    enabled = _mcp_call(
        server,
        "yaml_map_path_get",
        {"path": "config.yaml", "yaml_path": "root.enabled", "output_format": "json"},
    )
    enabled_hash = enabled["result"]["structuredContent"]["value_hash"]
    changed = _mcp_call(
        server,
        "yaml_map_path_set",
        {
            "path": "config.yaml",
            "yaml_path": "root.enabled",
            "expect_hash": enabled_hash,
            "value": False,
            "output_format": "json",
        },
    )
    deleted = _mcp_call(
        server,
        "yaml_map_path_delete",
        {
            "path": "config.yaml",
            "yaml_path": "root.items[0]",
            "expect_hash": "stale",
            "output_format": "json",
        },
    )

    assert mapped["result"]["isError"] is False
    assert "config.yaml" in mapped["result"]["content"][0]["text"]
    assert project["result"]["structuredContent"]["entries"][0]["file_path"] == "config.yaml"
    assert parsed["result"]["isError"] is False
    assert inserted["result"]["structuredContent"]["changed"] is True
    assert changed["result"]["structuredContent"]["changed"] is True
    assert deleted["result"]["isError"] is True
    assert deleted["result"]["structuredContent"]["code"] == "hash-mismatch"
    assert "enabled: false" in source.read_text(encoding="utf-8")
    assert "- two" in source.read_text(encoding="utf-8")


def test_workspace_mcp_validate_changed_writes_receipt_and_marks_push_guard(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.delenv("AGENT_TOOLS_WORKSPACE_ROOT", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initial")
    (repo / "README.md").write_text("base\nchanged\n", encoding="utf-8")
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "validate_changed",
        {
            "repo": "repo",
            "receipt": "report/validation/latest.json",
            "mark_push_guard": True,
        },
    )

    result = response["result"]
    payload = result["structuredContent"]
    assert result["isError"] is False
    assert payload["status"] == "pass"
    assert payload["changed_files"] == ["README.md"]
    assert payload["push_guard_marked"] is True
    assert (repo / "report" / "validation" / "latest.json").is_file()


def test_workspace_mcp_validate_changed_reports_guard_failures(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initial")
    (repo / "debug.zip").write_text("artifact\n", encoding="utf-8")
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(server, "validate_changed", {"repo": "repo"})

    result = response["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["status"] == "fail"
    assert "artifact-like file suffix '.zip' is blocked" in result["content"][0]["text"]


def test_workspace_mcp_validate_task_writes_task_receipt(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from agent_tools.tools import validate as validate_tool

    repo = tmp_path / "repo"
    task_dir = repo / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.name", "Example Author")
    _git(repo, "config", "user.email", "author@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "Initial")
    monkeypatch.setattr(validate_tool, "_changed_files", lambda _repo: [])
    monkeypatch.setattr(validate_tool, "_validation_commands", lambda _repo, _changed, _task: [])
    server = build_workspace_mcp_server(tmp_path)

    response = _mcp_call(
        server,
        "validate_task",
        {"repo": "repo", "task_dir": "tasks/sample"},
    )

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["task_dir"] == str(task_dir.resolve())
    assert (task_dir / "report" / "validation" / "latest.json").is_file()


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


def test_workspace_mcp_task_context_slot_and_journal_flow(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    server = build_workspace_mcp_server(tmp_path)

    slot_response = _mcp_call(
        server,
        "task_context_set_slot",
        {
            "task": "tasks/sample",
            "category": "goal",
            "content": "Exercise full task_context MCP.",
            "format": "json",
        },
    )
    assert slot_response["result"]["isError"] is False
    assert slot_response["result"]["structuredContent"]["slots"][0]["category"] == "goal"

    entry_response = _mcp_call(
        server,
        "task_context_add_entry",
            {
                "task": "tasks/sample",
                "summary": "MCP entry",
                "severity": "high",
                "labels": ["tooling"],
                "details": "Created through MCP.",
            },
        )
    assert entry_response["result"]["isError"] is False
    entry_id = entry_response["result"]["structuredContent"]["entry"]["id"]

    edit_response = _mcp_call(
        server,
        "task_context_edit_entries",
        {
            "task": "tasks/sample",
            "ids": [entry_id],
            "set_status": "resolved",
            "format": "json",
        },
    )
    assert edit_response["result"]["structuredContent"]["count"] == 1
    assert edit_response["result"]["structuredContent"]["entries"][0]["status"] == "resolved"

    compact_response = _mcp_call(
        server,
        "task_context_compact",
        {
            "task": "tasks/sample",
            "statuses": ["resolved"],
            "limit": 5000,
        },
    )
    assert "Exercise full task_context MCP." in compact_response["result"]["content"][0]["text"]


def test_workspace_mcp_task_context_dictionary_and_migrate(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "sample"
    task_dir.mkdir(parents=True)
    server = build_workspace_mcp_server(tmp_path)
    legacy_entry = {
        "timestamp": "2026-01-02T03:04:05+00:00",
        "severity": "mid",
        "labels": ["legacy"],
        "status": "active",
        "summary": "Legacy entry",
    }
    (task_dir / "TASK_CONTEXT_LOG.jsonl").write_text(json.dumps(legacy_entry) + "\n", encoding="utf-8")

    migrate_response = _mcp_call(server, "task_context_migrate_legacy", {"task": "tasks/sample"})
    assert migrate_response["result"]["structuredContent"]["migrated"] == 1

    add_response = _mcp_call(
        server,
        "task_context_dictionary",
        {"task": "tasks/sample", "add": ["Agent Workspace"]},
    )
    assert add_response["result"]["structuredContent"]["added"] == 1

    list_response = _mcp_call(
        server,
        "task_context_dictionary",
        {"task": "tasks/sample", "format": "json"},
    )
    dictionary = list_response["result"]["structuredContent"]["dictionary"]
    assert dictionary[0]["value"] == "Agent Workspace"

    compile_response = _mcp_call(server, "task_context_compile_dictionary", {"task": "tasks/sample"})
    assert compile_response["result"]["isError"] is False
    assert "compiled dictionary" in compile_response["result"]["content"][0]["text"]


def _mcp_call(server: Any, name: str, arguments: dict[str, object]) -> dict[str, Any]:
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    assert response is not None
    return response


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
