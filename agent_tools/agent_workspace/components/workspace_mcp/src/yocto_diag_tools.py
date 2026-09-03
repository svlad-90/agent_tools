from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.yocto_diag import DEFAULT_GRAPH_FILES
from agent_tools.tools.yocto_diag import GraphCopy
from agent_tools.tools.yocto_diag import YoctoInvocation
from agent_tools.tools.yocto_diag import analyze_graph_files
from agent_tools.tools.yocto_diag import bitbake_shell_command
from agent_tools.tools.yocto_diag import quote_words

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


def yocto_diag_tools() -> list[McpTool]:
    return [
        McpTool(
            name="yocto_diag_command",
            title="Yocto Diag Command",
            description=(
                "Use in Yocto tasks instead of hand-writing fragile source/build "
                "commands. Returns a shell-ready BitBake diagnostic command with "
                "quoted arguments and optional graph artifact copying."
            ),
            input_schema=_command_input_schema(),
            handler=_yocto_diag_command,
        ),
        McpTool(
            name="yocto_diag_analyze_graph",
            title="Yocto Diag Analyze Graph",
            description=(
                "Use instead of grepping large BitBake graph files. Reads copied "
                "graph artifacts by prefix and returns a compact dependency summary."
            ),
            input_schema=_analyze_graph_input_schema(),
            handler=_yocto_diag_analyze_graph,
        ),
    ]


def _yocto_diag_command(context: ToolContext, arguments: JsonObject) -> ToolResult:
    try:
        yocto_dir = resolve_workspace_path(context.workspace, string_arg(arguments, "yocto_dir"))
        graph_copy = _graph_copy(context, arguments)
        invocation = YoctoInvocation(
            str(yocto_dir),
            string_arg(arguments, "build_dir", "build-xen-qemu-421"),
            string_arg(arguments, "init_script", "poky/oe-init-build-env"),
        )
        bitbake_args = quote_words(string_arg(arguments, "bitbake_args"))
        command = bitbake_shell_command(invocation, bitbake_args, graph_copy=graph_copy)
    except (OSError, ValueError) as error:
        return _error_result(error)
    payload: JsonObject = {
        "command": command,
        "yocto_dir": str(yocto_dir),
        "build_dir": invocation.build_dir,
        "init_script": invocation.init_script,
        "bitbake_args": bitbake_args,
    }
    if graph_copy is not None:
        payload["graph_copy"] = {
            "output_dir": graph_copy.output_dir,
            "label": graph_copy.label,
            "files": list(graph_copy.files),
        }
    return ToolResult(text=command + "\n", structured_content=payload)


def _yocto_diag_analyze_graph(context: ToolContext, arguments: JsonObject) -> ToolResult:
    try:
        prefix = resolve_workspace_path(context.workspace, string_arg(arguments, "prefix"))
        text = analyze_graph_files(prefix)
    except (OSError, ValueError) as error:
        return _error_result(error)
    return ToolResult(
        text=text,
        structured_content={
            "prefix": str(prefix),
            "summary": text,
        },
    )


def _graph_copy(context: ToolContext, arguments: JsonObject) -> GraphCopy | None:
    output_dir = optional_string_arg(arguments, "graph_output_dir")
    if output_dir is None:
        return None
    files = tuple(string_list_arg(arguments, "graph_files") or DEFAULT_GRAPH_FILES)
    return GraphCopy(
        str(resolve_workspace_path(context.workspace, output_dir)),
        string_arg(arguments, "graph_label", "bitbake-graph"),
        files,
    )


def _error_result(error: Exception) -> ToolResult:
    payload = {"error": str(error)}
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _command_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "yocto_dir": {
                "type": "string",
                "description": "Workspace-relative Yocto checkout path.",
            },
            "build_dir": {
                "type": "string",
                "description": "Yocto build directory passed to the init script.",
                "default": "build-xen-qemu-421",
            },
            "init_script": {
                "type": "string",
                "description": "Init script path relative to yocto_dir.",
                "default": "poky/oe-init-build-env",
            },
            "bitbake_args": {
                "type": "string",
                "description": "BitBake command arguments to quote as shell words.",
            },
            "graph_output_dir": {
                "type": "string",
                "description": "Workspace-relative directory where graph files should be copied on success.",
            },
            "graph_label": {
                "type": "string",
                "description": "Filename prefix for copied graph artifacts.",
                "default": "bitbake-graph",
            },
            "graph_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Graph file basenames to copy from the Yocto build directory.",
                "default": list(DEFAULT_GRAPH_FILES),
            },
        },
        "required": ["yocto_dir", "bitbake_args"],
        "additionalProperties": False,
    }


def _analyze_graph_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "prefix": {
                "type": "string",
                "description": "Workspace-relative graph prefix, without -pn-buildlist/-task-depends.dot suffix.",
            },
        },
        "required": ["prefix"],
        "additionalProperties": False,
    }
