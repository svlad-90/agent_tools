from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from .registry import JsonObject, ToolContext, ToolResult, WorkspaceMcpRegistry


JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-06-18"


class WorkspaceMcpServer:
    def __init__(self, workspace: Path, registry: WorkspaceMcpRegistry) -> None:
        self.workspace = workspace.resolve()
        self.registry = registry
        self._tools_load_error = ""
        self._tools_loaded = False

    def handle_message(self, message: JsonObject) -> JsonObject | None:
        message_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str):
            return self._error(message_id, -32600, "invalid request")
        if message_id is None:
            return None
        try:
            if method == "initialize":
                return self._response(message_id, self._initialize_result())
            if method == "ping":
                return self._response(message_id, {})
            if method == "tools/list":
                self._ensure_tools_loaded()
                return self._response(message_id, {"resultType": "complete", "tools": self.registry.tool_descriptors()})
            if method == "tools/call":
                self._ensure_tools_loaded()
                return self._response(message_id, self._call_tool(message))
            return self._error(message_id, -32601, f"method not found: {method}")
        except KeyError as error:
            return self._error(message_id, -32602, f"unknown tool: {error.args[0]}")
        except ValueError as error:
            return self._tool_error_response(message_id, str(error))
        except Exception as error:
            return self._tool_error_response(message_id, f"{type(error).__name__}: {error}")

    def serve_stdio(self, stdin: TextIO, stdout: TextIO) -> None:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            response = self._handle_line(line)
            if response is None:
                continue
            stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
            stdout.flush()

    def _handle_line(self, line: str) -> JsonObject | None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            return self._error(None, -32700, f"parse error: {error}")
        if not isinstance(message, dict):
            return self._error(None, -32600, "invalid request")
        return self.handle_message(message)

    def _initialize_result(self) -> JsonObject:
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": {
                "name": "agent_tools_workspace",
                "version": "0.1.0",
            },
            "capabilities": {
                "tools": {},
            },
        }

    def _call_tool(self, message: JsonObject) -> JsonObject:
        params = message.get("params")
        if not isinstance(params, dict):
            raise ValueError("tools/call params must be an object")
        name = params.get("name")
        if not isinstance(name, str):
            raise ValueError("tools/call params.name must be a string")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("tools/call params.arguments must be an object")
        if not self.registry.has_tool(name) and self._tools_load_error:
            raise ValueError(self._tools_load_error)
        result = self.registry.call(ToolContext(self.workspace), name, arguments)
        return self._tool_result_payload(result)

    def _tool_result_payload(self, result: ToolResult) -> JsonObject:
        payload: JsonObject = {
            "resultType": "complete",
            "content": [
                {
                    "type": "text",
                    "text": result.text,
                }
            ],
            "isError": result.is_error,
        }
        if result.structured_content is not None:
            payload["structuredContent"] = result.structured_content
        return payload

    def _response(self, message_id: Any, result: JsonObject) -> JsonObject:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": message_id,
            "result": result,
        }

    def _error(self, message_id: Any, code: int, message: str) -> JsonObject:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": message_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def _tool_error_response(self, message_id: Any, message: str) -> JsonObject:
        return self._response(
            message_id,
            self._tool_result_payload(ToolResult(text=message + "\n", is_error=True)),
        )

    def _ensure_tools_loaded(self) -> None:
        if self._tools_loaded:
            return
        from .commit_msg_tools import commit_msg_tools
        from .knowledge_tools import knowledge_tools
        from .push_guard_tools import push_guard_tools
        from .task_actualize_tools import task_actualize_tools
        from .task_actions_tools import task_actions_tools
        from .task_context_tools import task_context_tools
        from .validate_tools import validate_tools
        from .yaml_map_tools import yaml_map_tools

        for tool in commit_msg_tools():
            self.registry.register(tool)
        for tool in knowledge_tools():
            self.registry.register(tool)
        for tool in push_guard_tools():
            self.registry.register(tool)
        for tool in task_actualize_tools():
            self.registry.register(tool)
        for tool in task_actions_tools():
            self.registry.register(tool)
        for tool in task_context_tools():
            self.registry.register(tool)
        for tool in validate_tools():
            self.registry.register(tool)
        for tool in yaml_map_tools():
            self.registry.register(tool)
        try:
            from .agent_search_tools import agent_search_tools

            for tool in agent_search_tools():
                self.registry.register(tool)
        except ModuleNotFoundError as error:
            dependency = error.name or str(error)
            self._tools_load_error = (
                "workspace MCP search tools are unavailable because a Python "
                f"dependency is missing: {dependency}. Run "
                "`python3 install-agent-tools.py` from the workspace root."
            )
        self._tools_loaded = True


def build_workspace_mcp_server(workspace: Path) -> WorkspaceMcpServer:
    registry = WorkspaceMcpRegistry()
    return WorkspaceMcpServer(workspace, registry)
