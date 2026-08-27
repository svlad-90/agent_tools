from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ToolContext:
    workspace: Path


@dataclass(frozen=True)
class ToolResult:
    text: str
    structured_content: JsonObject | None = None
    is_error: bool = False


ToolHandler = Callable[[ToolContext, JsonObject], ToolResult]


@dataclass(frozen=True)
class McpTool:
    name: str
    title: str
    description: str
    input_schema: JsonObject
    handler: ToolHandler

    def descriptor(self) -> JsonObject:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class WorkspaceMcpRegistry:
    def __init__(self, tools: list[McpTool] | None = None) -> None:
        self._tools: dict[str, McpTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: McpTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate MCP tool: {tool.name}")
        self._tools[tool.name] = tool

    def tool_descriptors(self) -> list[JsonObject]:
        return [self._tools[name].descriptor() for name in sorted(self._tools)]

    def call(self, context: ToolContext, name: str, arguments: JsonObject) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(name)
        return tool.handler(context, arguments)


def string_arg(arguments: JsonObject, name: str, default: str | None = None) -> str:
    value = arguments.get(name, default)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def optional_string_arg(arguments: JsonObject, name: str) -> str | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


def int_arg(arguments: JsonObject, name: str, default: int) -> int:
    value = arguments.get(name, default)
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def bool_arg(arguments: JsonObject, name: str, default: bool) -> bool:
    value = arguments.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def string_list_arg(arguments: JsonObject, name: str) -> list[str]:
    value = arguments.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return value


def resolve_workspace_path(workspace: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    resolved = path.resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError(f"path is outside workspace: {value}") from error
    return resolved
