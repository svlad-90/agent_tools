from __future__ import annotations

import json
import shlex

from agent_tools.tools.commit_msg import DEFAULT_WIDTH
from agent_tools.tools.commit_msg import (
    find_long_lines,
    format_commit_message,
    read_git_identity,
)

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, resolve_workspace_path, string_arg


def commit_msg_tools() -> list[McpTool]:
    return [
        McpTool(
            name="commit_msg_format",
            title="Commit Message Format",
            description=(
                "Use before running git commit instead of hand-wrapping -m "
                "arguments. Formats a title plus body/trailers, validates line "
                "width and Signed-off-by, and returns a shell-safe git commit "
                "command."
            ),
            input_schema=_format_input_schema(),
            handler=_commit_msg_format,
        ),
    ]


def _commit_msg_format(context: ToolContext, arguments: JsonObject) -> ToolResult:
    repo = resolve_workspace_path(context.workspace, string_arg(arguments, "repo", "."))
    title = string_arg(arguments, "title").strip()
    message = string_arg(arguments, "message", "")
    width = int_arg(arguments, "width", DEFAULT_WIDTH)
    add_signoff = bool_arg(arguments, "add_signoff", True)
    check = bool_arg(arguments, "check", True)

    if not title:
        raise ValueError("title must not be empty")
    identity = read_git_identity(repo) if add_signoff else None
    draft = _join_title_and_message(title, message)
    formatted = format_commit_message(draft, width=width, identity=identity)
    long_lines = find_long_lines(formatted, width=width)
    signoff_missing = not _has_trailer(formatted, "Signed-off-by")
    diagnostics = [
        {"line": line_no, "length": length, "text": line}
        for line_no, length, line in long_lines
    ]
    command_args = _commit_command_args(repo, formatted)
    is_error = (check and bool(long_lines)) or signoff_missing
    payload = {
        "message": formatted,
        "command_args": command_args,
        "shell_command": shlex.join(command_args),
        "width": width,
        "long_lines": diagnostics,
        "add_signoff": add_signoff,
        "has_signed_off_by": not signoff_missing,
    }
    if not is_error:
        return ToolResult(
            text=f"{formatted}\nCommand:\n{payload['shell_command']}\n",
            structured_content=payload,
        )
    return ToolResult(
        text=_format_check_failure(
            formatted,
            diagnostics,
            width,
            signoff_missing=signoff_missing,
        ),
        structured_content=payload,
        is_error=True,
    )


def _join_title_and_message(title: str, message: str) -> str:
    body = message.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not body:
        return title + "\n"
    return f"{title}\n\n{body}\n"


def _commit_command_args(repo: object, formatted: str) -> list[str]:
    args = ["git", "-C", str(repo), "commit"]
    for paragraph in _message_paragraphs(formatted):
        args.extend(["-m", paragraph])
    return args


def _message_paragraphs(message: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in message.rstrip().splitlines():
        if line == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _has_trailer(message: str, key: str) -> bool:
    prefix = f"{key}: "
    return any(line.startswith(prefix) for line in _trailer_lines(message))


def _trailer_lines(message: str) -> list[str]:
    lines = message.rstrip().splitlines()
    index = len(lines)
    while index > 0 and _is_trailer_line(lines[index - 1]):
        index -= 1
    if index == len(lines):
        return []
    if index > 0 and lines[index - 1] != "":
        return []
    return lines[index:]


def _is_trailer_line(line: str) -> bool:
    if ": " not in line:
        return False
    key, _value = line.split(": ", 1)
    return bool(key) and all(char.isalnum() or char == "-" for char in key)


def _format_check_failure(
    formatted: str,
    diagnostics: list[JsonObject],
    width: int,
    *,
    signoff_missing: bool,
) -> str:
    lines = ["commit message check failed"]
    if diagnostics:
        lines.extend(
            [
                f"non-trailer line exceeds {width} columns",
                "",
                json.dumps({"long_lines": diagnostics}, ensure_ascii=False, indent=2),
            ]
        )
    if signoff_missing:
        if len(lines) > 1:
            lines.append("")
        lines.append("missing Signed-off-by trailer")
    lines.extend(["", "Formatted message:", formatted.rstrip(), ""])
    return "\n".join(lines)


def _format_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "default": ".",
                "description": "Workspace-relative or absolute path inside the git repository used for sign-off identity.",
            },
            "title": {
                "type": "string",
                "description": "Commit subject/title. This is the only subject line.",
            },
            "message": {
                "type": "string",
                "default": "",
                "description": "Commit body plus trailers. Paragraphs may use \\n.",
            },
            "width": {
                "type": "integer",
                "default": DEFAULT_WIDTH,
                "minimum": 20,
                "description": "Maximum non-trailer body line width after formatting.",
            },
            "add_signoff": {
                "type": "boolean",
                "default": True,
                "description": "Add Signed-off-by from repo git identity.",
            },
            "check": {
                "type": "boolean",
                "default": True,
                "description": "Return isError=true if formatting or required trailers are invalid.",
            },
        },
        "required": ["title"],
        "additionalProperties": False,
    }
