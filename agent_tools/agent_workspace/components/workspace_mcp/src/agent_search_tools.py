from __future__ import annotations

import json
from typing import Any

from agent_tools.tools.agent_search.core import file_search, render_file_search, render_file_search_json
from agent_tools.tools.agent_search.core import render_text_search, render_text_search_json, text_search
from agent_tools.tools.agent_search.file_types import FILE_TYPES, expand_extensions
from agent_tools.tools.agent_search.snippets import render_file_snippet, show_file_range

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


def agent_search_tools() -> list[McpTool]:
    return [
        McpTool(
            name="agent_search_text",
            title="Agent Search Text",
            description=(
                "Use instead of raw rg when search results may be large or need structure. "
                "Searches workspace text with gitignore on by default, supports summary, "
                "aggregate, and focused range modes, and caps model-facing output."
            ),
            input_schema=_text_input_schema(),
            handler=_agent_search_text,
        ),
        McpTool(
            name="agent_search_files",
            title="Agent Search Files",
            description=(
                "Use instead of find when matching workspace file names or paths. "
                "Returns bounded summary or aggregate output, supports extension/type "
                "filters, and avoids dumping long path lists into the model."
            ),
            input_schema=_files_input_schema(),
            handler=_agent_search_files,
        ),
        McpTool(
            name="agent_search_show",
            title="Agent Search Show",
            description=(
                "Use instead of sed/head/tail when showing a focused file excerpt. "
                "Validates the workspace path, supports line/range plus surrounding "
                "context, and truncates very long lines."
            ),
            input_schema=_show_input_schema(),
            handler=_agent_search_show,
        ),
    ]


def _agent_search_text(context: ToolContext, arguments: JsonObject) -> ToolResult:
    root = resolve_workspace_path(context.workspace, string_arg(arguments, "root", "."))
    query = string_arg(arguments, "query")
    mode = string_arg(arguments, "mode", "summary")
    output_format = string_arg(arguments, "output_format", "text")
    extensions = expand_extensions([], string_list_arg(arguments, "type"))
    include = [*string_list_arg(arguments, "include"), *(f"*{extension}" for extension in extensions)]
    report = text_search(
        root=root,
        query=query,
        fixed=bool_arg(arguments, "fixed", False),
        case_sensitive=bool_arg(arguments, "case_sensitive", False),
        ignore_case=bool_arg(arguments, "ignore_case", False),
        include=include,
        exclude=string_list_arg(arguments, "exclude"),
        hidden=bool_arg(arguments, "hidden", False),
        use_gitignore=bool_arg(arguments, "use_gitignore", True),
        threads=optional_int_arg(arguments, "threads"),
        max_matches_scanned=int_arg(arguments, "max_matches_scanned", 10_000),
        max_file_bytes=int_arg(arguments, "max_file_bytes", 2_000_000),
        before=int_arg(arguments, "before", int_arg(arguments, "around", 5)),
        after=int_arg(arguments, "after", int_arg(arguments, "around", 5)),
        max_ranges=int_arg(arguments, "max_ranges", 20),
        max_lines=int_arg(arguments, "max_lines", 300),
    )
    if output_format == "json":
        text = render_text_search_json(
            report,
            max_matches=int_arg(arguments, "max_matches_scanned", 10_000),
            max_ranges=int_arg(arguments, "max_ranges", 20),
            max_range_lines=int_arg(arguments, "max_lines", 300),
        )
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    options = _render_options(arguments)
    options["samples"] = int_arg(arguments, "samples", 20)
    options["per_group_samples"] = int_arg(arguments, "per_group_samples", 3)
    return ToolResult(text=render_text_search(report, mode=mode, options=options))


def _agent_search_files(context: ToolContext, arguments: JsonObject) -> ToolResult:
    root = resolve_workspace_path(context.workspace, string_arg(arguments, "root", "."))
    output_format = string_arg(arguments, "output_format", "text")
    report = file_search(
        root=root,
        query=string_arg(arguments, "query"),
        fixed=bool_arg(arguments, "fixed", False),
        case_sensitive=bool_arg(arguments, "case_sensitive", False),
        ignore_case=bool_arg(arguments, "ignore_case", False),
        include=string_list_arg(arguments, "include"),
        exclude=string_list_arg(arguments, "exclude"),
        hidden=bool_arg(arguments, "hidden", False),
        use_gitignore=bool_arg(arguments, "use_gitignore", True),
        threads=optional_int_arg(arguments, "threads"),
        max_files_scanned=int_arg(arguments, "max_files_scanned", 10_000),
        extensions=expand_extensions(string_list_arg(arguments, "ext"), string_list_arg(arguments, "type")),
        scope=string_arg(arguments, "scope", "path"),
    )
    if output_format == "json":
        text = render_file_search_json(report, max_files=int_arg(arguments, "max_files", 30))
        return ToolResult(text=text + "\n", structured_content=json.loads(text))
    return ToolResult(text=render_file_search(report, mode=string_arg(arguments, "mode", "summary"), options=_render_options(arguments)))


def _agent_search_show(context: ToolContext, arguments: JsonObject) -> ToolResult:
    path = resolve_workspace_path(context.workspace, string_arg(arguments, "path"))
    snippet = show_file_range(
        path=path,
        line=optional_int_arg(arguments, "line"),
        line_range=optional_string_arg(arguments, "range"),
        around=int_arg(arguments, "around", 5),
    )
    return ToolResult(text=render_file_snippet(snippet, max_line_chars=int_arg(arguments, "max_line_chars", 240)))


def _render_options(arguments: JsonObject) -> JsonObject:
    return {
        "max_tokens": int_arg(arguments, "max_tokens", 2_000),
        "max_output_lines": int_arg(arguments, "max_output_lines", 120),
        "max_dirs": int_arg(arguments, "max_dirs", 20),
        "max_files": int_arg(arguments, "max_files", 30),
    }


def optional_int_arg(arguments: JsonObject, name: str) -> int | None:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _common_search_properties() -> JsonObject:
    return {
        "root": {"type": "string", "description": "Workspace-relative or absolute directory to search. Default searches the workspace root.", "default": "."},
        "query": {"type": "string", "description": "Text, regex, file-name fragment, or path fragment to search for."},
        "fixed": {"type": "boolean", "description": "Treat query as a literal string instead of a regular expression.", "default": False},
        "case_sensitive": {"type": "boolean", "description": "Force case-sensitive matching.", "default": False},
        "ignore_case": {"type": "boolean", "description": "Force case-insensitive matching.", "default": False},
        "include": {"type": "array", "items": {"type": "string"}, "description": "Glob patterns to include, for example ['*.py']; combined with type/ext filters.", "default": []},
        "exclude": {"type": "array", "items": {"type": "string"}, "description": "Glob patterns or path fragments to exclude before matching.", "default": []},
        "hidden": {"type": "boolean", "description": "Include hidden files and directories.", "default": False},
        "use_gitignore": {"type": "boolean", "description": "Respect .gitignore and common ignore rules. Keep true for compact agent searches.", "default": True},
        "threads": {"type": "integer", "minimum": 1, "description": "Optional worker count. Omit to use the tool default."},
        "type": {"type": "array", "items": {"type": "string", "enum": sorted(FILE_TYPES)}, "description": "Known file type shortcuts such as py, cpp, md, yaml, json, sh, text.", "default": []},
        "max_tokens": {"type": "integer", "minimum": 100, "description": "Approximate output budget for text results. Default keeps output model-friendly.", "default": 2000},
        "max_output_lines": {"type": "integer", "minimum": 1, "description": "Maximum rendered output lines for text mode.", "default": 120},
        "max_dirs": {"type": "integer", "minimum": 1, "description": "Maximum directory groups to show in aggregate output.", "default": 20},
        "max_files": {"type": "integer", "minimum": 1, "description": "Maximum matching files to render in summary/json output.", "default": 30},
        "output_format": {"type": "string", "enum": ["text", "json"], "description": "Use text for model-readable summaries or json for structured consumers.", "default": "text"},
    }


def _text_input_schema() -> JsonObject:
    properties = _common_search_properties()
    properties.update(
        {
            "mode": {"type": "string", "enum": ["summary", "aggregate", "ranges"], "description": "summary gives compact counts/samples, aggregate groups by capture/tree, ranges returns focused line windows.", "default": "summary"},
            "around": {"type": "integer", "minimum": 0, "description": "Default number of context lines before and after each text match.", "default": 5},
            "before": {"type": "integer", "minimum": 0, "description": "Override context lines before each match."},
            "after": {"type": "integer", "minimum": 0, "description": "Override context lines after each match."},
            "max_ranges": {"type": "integer", "minimum": 1, "description": "Maximum focused match ranges to render.", "default": 20},
            "max_lines": {"type": "integer", "minimum": 1, "description": "Maximum total lines rendered for range output.", "default": 300},
            "max_matches_scanned": {"type": "integer", "minimum": 1, "description": "Stop scanning after this many matches to avoid unbounded output.", "default": 10000},
            "max_file_bytes": {"type": "integer", "minimum": 1, "description": "Skip files larger than this many bytes.", "default": 2000000},
            "samples": {"type": "integer", "minimum": 0, "description": "Maximum sample matches in summary output.", "default": 20},
            "per_group_samples": {"type": "integer", "minimum": 0, "description": "Maximum sample matches per aggregate group.", "default": 3},
        }
    )
    return {"type": "object", "properties": properties, "required": ["query"], "additionalProperties": False}


def _files_input_schema() -> JsonObject:
    properties = _common_search_properties()
    properties.update(
        {
            "mode": {"type": "string", "enum": ["summary", "aggregate"], "description": "summary lists bounded matches, aggregate groups matches by directory.", "default": "summary"},
            "ext": {"type": "array", "items": {"type": "string"}, "description": "File suffix filters such as ['.py', '.md']; combined with type filters.", "default": []},
            "scope": {"type": "string", "enum": ["path", "name"], "description": "Match the whole workspace-relative path or only the file name.", "default": "path"},
            "max_files_scanned": {"type": "integer", "minimum": 1, "description": "Stop scanning after this many candidate files.", "default": 10000},
        }
    )
    return {"type": "object", "properties": properties, "required": ["query"], "additionalProperties": False}


def _show_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative or absolute file path under the workspace."},
            "line": {"type": "integer", "minimum": 1, "description": "1-based line number to center the excerpt on."},
            "range": {"type": "string", "description": "Line range formatted as A:B or A-B."},
            "around": {"type": "integer", "minimum": 0, "description": "Context lines to include around line/range.", "default": 5},
            "max_line_chars": {"type": "integer", "minimum": 20, "description": "Maximum characters rendered per line before truncation.", "default": 240},
        },
        "required": ["path"],
        "additionalProperties": False,
    }
