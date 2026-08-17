from __future__ import annotations

import json
from pathlib import Path

from .comments import comments_from_payload, load_comments, load_comments_payload
from .diff_source import load_diff_source
from .models import DiffReportError
from .report_json import load_report_json, render_report_json_html
from .render import render_html_report
from .refresh import enrich_comments_payload, print_refresh_attention


def compact_help() -> str:
    return "\n".join(
        [
            "diff_report --repo <git_repo> --range HEAD^..HEAD --output report.html [--comments comments.json]",
            "diff_report --diff-file diff.patch --output report.html [--comments comments.json]",
            "diff_report --diff-file diff.patch --output report.html --comments comments.json --refresh-targets",
            "diff_report --diff-file diff.patch --init-comments comments.json",
            "diff_report --diff-file diff.patch --findings findings.json --output-comments comments.json",
            "diff_report --diff-file diff.patch --findings findings.json --output-comments comments.json --output report.html [--compose-report diagnostics.json]",
            "",
            "comments.json schema:",
            "{",
            '  "commit": {"id": "optional commit id", "message": "optional full commit message"},',
            '  "summary": "optional markdown-free text",',
            '  "files": {"path/to/file.py": "file-level comment"},',
            '  "inline": [',
            '    {"file": "path/to/file.py", "line": 42, "range": {"start": 42, "end": 45}, "body": "comment", "title": "optional", "diagram": "optional-id", "diagram_focus": ["important SVG text"], "diagram_notes": [{"text": "note", "target": "SVG text"}], "log": "optional-log-id", "log_focus": ["important log line text"]}',
            "  ],",
            '  "diagrams": {"optional-id": {"title": "Diagram title", "svg": "report/puml/diagram.svg", "code_links": [{"target": "SVG arrow label", "file": "path/to/file.py", "line": 42, "title": "Code target"}]}},',
            '  "logs": {"optional-log-id": {"title": "Runtime log", "path": "report/runtime/test.log"}},',
            '  "story": [{"title": "Narrative step", "body": "why this matters", "comment": {"file": "path/to/file.py", "line": 42}}]',
            "}",
        ]
    )


def generate_report(
    *,
    output_path: Path,
    title: str,
    repo_path: Path | None = None,
    rev_range: str = "HEAD^..HEAD",
    diff_file: Path | None = None,
    comments_file: Path | None = None,
    context: int = 80,
    display_label: str | None = None,
    refresh_targets: bool = False,
) -> None:
    source = load_diff_source(repo_path, rev_range, diff_file, context, display_label)
    comments = load_comments(comments_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_comments = comments
    if refresh_targets:
        comments_output_path = output_path.with_suffix(".json")
        comments_payload = load_comments_payload(comments_file)
        comments_payload = enrich_comments_payload(source.diff_text, comments_payload)
        comments_json = json.dumps(comments_payload, indent=2, ensure_ascii=False) + "\n"
        comments_output_path.write_text(comments_json, encoding="utf-8")
        print_refresh_attention(comments_output_path, comments_payload, comments_json)
        rendered_comments = comments_from_payload(
            comments_payload,
            base_dir=comments_output_path.parent,
        )
    output_path.write_text(
        render_html_report(title, source, rendered_comments),
        encoding="utf-8",
    )


def generate_report_json(
    *,
    report_file: Path,
    output_path: Path,
    title: str | None = None,
) -> None:
    report = load_report_json(report_file)
    if title is not None:
        report = type(report)(
            title=title,
            comments=report.comments,
            metrics=report.metrics,
            status_cards=report.status_cards,
            heatmaps=report.heatmaps,
            tables=report.tables,
            timeline=report.timeline,
            artifacts=report.artifacts,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report_json_html(report), encoding="utf-8")
