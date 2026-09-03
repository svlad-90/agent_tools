from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.diff_report.comments_compose import compose_comments_payload_with_diagnostics
from agent_tools.tools.diff_report.comments_template import build_comments_template
from agent_tools.tools.diff_report.core import generate_report
from agent_tools.tools.diff_report.core import generate_report_json
from agent_tools.tools.diff_report.diff_source import load_diff_source
from agent_tools.tools.diff_report.models import DiffReportError

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, optional_string_arg, resolve_workspace_path, string_arg


def diff_report_tools() -> list[McpTool]:
    return [
        McpTool(
            name="diff_report_render",
            title="Diff Report Render",
            description=(
                "Use instead of manually assembling review HTML for a git range or "
                "unified diff. Reads workspace paths, applies optional comments JSON, "
                "and writes the standard GitHub-style diff report artifact."
            ),
            input_schema=_render_input_schema(),
            handler=_diff_report_render,
        ),
        McpTool(
            name="diff_report_render_json",
            title="Diff Report Render JSON",
            description=(
                "Use instead of custom report rendering when a diff_report JSON "
                "payload already exists. Produces the standard HTML dashboard/report "
                "artifact from a workspace-relative JSON file."
            ),
            input_schema=_render_json_input_schema(),
            handler=_diff_report_render_json,
        ),
        McpTool(
            name="diff_report_init_comments",
            title="Diff Report Init Comments",
            description=(
                "Use before writing review findings instead of hand-building comments "
                "JSON. Extracts diff targets from a git range or diff file and writes "
                "a valid starter template."
            ),
            input_schema=_init_comments_input_schema(),
            handler=_diff_report_init_comments,
        ),
        McpTool(
            name="diff_report_compose_findings",
            title="Diff Report Compose Findings",
            description=(
                "Use instead of manually mapping draft findings to diff comments. "
                "Composes canonical comments JSON, reports diagnostics compactly, "
                "and can render the final HTML report in one guarded workflow."
            ),
            input_schema=_compose_findings_input_schema(),
            handler=_diff_report_compose_findings,
        ),
    ]


def _diff_report_render(context: ToolContext, arguments: JsonObject) -> ToolResult:
    output_path = resolve_workspace_path(context.workspace, string_arg(arguments, "output"))
    try:
        generate_report(
            output_path=output_path,
            title=string_arg(arguments, "title", "PR Diff Review"),
            repo_path=_optional_workspace_path(context, arguments, "repo"),
            rev_range=string_arg(arguments, "rev_range", "HEAD^..HEAD"),
            diff_file=_optional_workspace_path(context, arguments, "diff_file"),
            comments_file=_optional_workspace_path(context, arguments, "comments"),
            context=int_arg(arguments, "context_lines", 80),
            display_label=optional_string_arg(arguments, "display_label"),
            refresh_targets=bool_arg(arguments, "refresh_targets", False),
        )
    except (DiffReportError, OSError, json.JSONDecodeError, ValueError) as error:
        return _error_result(error)
    payload: JsonObject = {"output": str(output_path)}
    if bool_arg(arguments, "refresh_targets", False):
        payload["refreshed_comments"] = str(output_path.with_suffix(".json"))
    return _json_result(payload, f"{output_path}\n")


def _diff_report_render_json(context: ToolContext, arguments: JsonObject) -> ToolResult:
    report_json = resolve_workspace_path(context.workspace, string_arg(arguments, "report_json"))
    output_path = resolve_workspace_path(context.workspace, string_arg(arguments, "output"))
    try:
        generate_report_json(
            report_file=report_json,
            output_path=output_path,
            title=optional_string_arg(arguments, "title"),
        )
    except (DiffReportError, OSError, json.JSONDecodeError, ValueError) as error:
        return _error_result(error)
    return _json_result({"output": str(output_path)}, f"{output_path}\n")


def _diff_report_init_comments(context: ToolContext, arguments: JsonObject) -> ToolResult:
    output_comments = resolve_workspace_path(context.workspace, string_arg(arguments, "output_comments"))
    try:
        source = _load_source(context, arguments)
        output_comments.parent.mkdir(parents=True, exist_ok=True)
        output_comments.write_text(
            json.dumps(build_comments_template(source.diff_text), indent=2) + "\n",
            encoding="utf-8",
        )
    except (DiffReportError, OSError, json.JSONDecodeError, ValueError) as error:
        return _error_result(error)
    return _json_result({"output_comments": str(output_comments)}, f"{output_comments}\n")


def _diff_report_compose_findings(context: ToolContext, arguments: JsonObject) -> ToolResult:
    output_comments = resolve_workspace_path(context.workspace, string_arg(arguments, "output_comments"))
    compose_report = _optional_workspace_path(context, arguments, "compose_report")
    output_path = _optional_workspace_path(context, arguments, "output")
    try:
        source = _load_source(context, arguments)
        findings_path = resolve_workspace_path(context.workspace, string_arg(arguments, "findings"))
        findings = json.loads(findings_path.read_text(encoding="utf-8"))
        composed, diagnostics = compose_comments_payload_with_diagnostics(source.diff_text, findings)
        output_comments.parent.mkdir(parents=True, exist_ok=True)
        output_comments.write_text(
            json.dumps(composed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if compose_report is not None:
            compose_report.parent.mkdir(parents=True, exist_ok=True)
            compose_report.write_text(
                json.dumps({"diagnostics": diagnostics}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if output_path is not None:
            generate_report(
                output_path=output_path,
                title=string_arg(arguments, "title", "PR Diff Review"),
                repo_path=_optional_workspace_path(context, arguments, "repo"),
                rev_range=string_arg(arguments, "rev_range", "HEAD^..HEAD"),
                diff_file=_optional_workspace_path(context, arguments, "diff_file"),
                comments_file=output_comments,
                context=int_arg(arguments, "context_lines", 80),
                display_label=optional_string_arg(arguments, "display_label"),
                refresh_targets=bool_arg(arguments, "refresh_targets", False),
            )
    except (DiffReportError, OSError, json.JSONDecodeError, ValueError) as error:
        return _error_result(error)
    payload: JsonObject = {
        "output_comments": str(output_comments),
        "diagnostics": diagnostics,
    }
    paths = [str(output_comments)]
    if compose_report is not None:
        payload["compose_report"] = str(compose_report)
        paths.append(str(compose_report))
    if output_path is not None:
        payload["output"] = str(output_path)
        paths.append(str(output_path))
    text = "\n".join(paths) + "\n"
    is_error = bool(diagnostics)
    if is_error:
        text += f"compose-findings: diagnostics={len(diagnostics)}\n"
    return _json_result(payload, text, is_error=is_error)


def _load_source(context: ToolContext, arguments: JsonObject):
    return load_diff_source(
        _optional_workspace_path(context, arguments, "repo"),
        string_arg(arguments, "rev_range", "HEAD^..HEAD"),
        _optional_workspace_path(context, arguments, "diff_file"),
        int_arg(arguments, "context_lines", 80),
        optional_string_arg(arguments, "display_label"),
    )


def _optional_workspace_path(context: ToolContext, arguments: JsonObject, name: str) -> Path | None:
    value = optional_string_arg(arguments, name)
    if value is None:
        return None
    return resolve_workspace_path(context.workspace, value)


def _json_result(payload: JsonObject, text: str, *, is_error: bool = False) -> ToolResult:
    return ToolResult(text=text, structured_content=payload, is_error=is_error)


def _error_result(error: Exception) -> ToolResult:
    payload = {"error": str(error)}
    return ToolResult(
        text=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        structured_content=payload,
        is_error=True,
    )


def _diff_source_properties() -> JsonObject:
    return {
        "repo": {
            "type": "string",
            "description": "Workspace-relative git repository path used when reading rev_range.",
        },
        "rev_range": {
            "type": "string",
            "description": "Git revision range to render when diff_file is not provided.",
            "default": "HEAD^..HEAD",
        },
        "diff_file": {
            "type": "string",
            "description": "Workspace-relative unified git diff file path; overrides repo/rev_range input.",
        },
        "context_lines": {
            "type": "integer",
            "description": "Number of unchanged context lines around diff hunks.",
            "default": 80,
        },
        "display_label": {
            "type": "string",
            "description": "Optional human-readable source label shown in the report.",
        },
    }


def _render_input_schema() -> JsonObject:
    properties = _diff_source_properties()
    properties.update(
        {
            "comments": {
                "type": "string",
                "description": "Workspace-relative comments JSON path to overlay review findings.",
            },
            "output": {
                "type": "string",
                "description": "Workspace-relative HTML output path, usually under task report/diff/.",
            },
            "title": {
                "type": "string",
                "description": "HTML report title.",
                "default": "PR Diff Review",
            },
            "refresh_targets": {
                "type": "boolean",
                "description": "Refresh comment target metadata beside the rendered report.",
                "default": False,
            },
        }
    )
    return {
        "type": "object",
        "properties": properties,
        "required": ["output"],
        "additionalProperties": False,
    }


def _render_json_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "report_json": {
                "type": "string",
                "description": "Workspace-relative diff_report JSON dashboard/report payload.",
            },
            "output": {
                "type": "string",
                "description": "Workspace-relative HTML output path.",
            },
            "title": {
                "type": "string",
                "description": "Optional HTML report title override.",
            },
        },
        "required": ["report_json", "output"],
        "additionalProperties": False,
    }


def _init_comments_input_schema() -> JsonObject:
    properties = _diff_source_properties()
    properties["output_comments"] = {
        "type": "string",
        "description": "Workspace-relative comments JSON output path, usually under task report/diff/.",
    }
    return {
        "type": "object",
        "properties": properties,
        "required": ["output_comments"],
        "additionalProperties": False,
    }


def _compose_findings_input_schema() -> JsonObject:
    properties = _diff_source_properties()
    properties.update(
        {
            "findings": {
                "type": "string",
                "description": "Workspace-relative draft findings JSON path to compose into comments.",
            },
            "output_comments": {
                "type": "string",
                "description": "Workspace-relative canonical comments JSON output path.",
            },
            "compose_report": {
                "type": "string",
                "description": "Workspace-relative diagnostics JSON output path for unmapped findings.",
            },
            "output": {
                "type": "string",
                "description": "Workspace-relative optional HTML output path to render after composing.",
            },
            "title": {
                "type": "string",
                "description": "HTML report title when output is requested.",
                "default": "PR Diff Review",
            },
            "refresh_targets": {
                "type": "boolean",
                "description": "Refresh comment target metadata beside the rendered report.",
                "default": False,
            },
        }
    )
    return {
        "type": "object",
        "properties": properties,
        "required": ["findings", "output_comments"],
        "additionalProperties": False,
    }
