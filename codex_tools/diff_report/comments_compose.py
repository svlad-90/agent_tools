from __future__ import annotations

from typing import Any

from .models import DiffReportError
from .refresh import diff_line_targets, enrich_comments_payload


_PASSTHROUGH_KEYS = (
    "commit",
    "summary",
    "summary_blocks",
    "diagrams",
    "logs",
    "story",
)

_INLINE_OPTIONAL_KEYS = (
    "range",
    "diagram",
    "diagram_focus",
    "diagram_notes",
    "log",
    "log_focus",
)


def compose_comments_payload(diff_text: str, findings: dict[str, Any]) -> dict[str, Any]:
    payload, diagnostics = compose_comments_payload_with_diagnostics(diff_text, findings)
    if diagnostics:
        raise DiffReportError(str(diagnostics[0]["message"]))
    return payload


def compose_comments_payload_with_diagnostics(
    diff_text: str,
    findings: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(findings, dict):
        raise DiffReportError("findings JSON must be an object")

    comments: dict[str, Any] = {}
    for key in _PASSTHROUGH_KEYS:
        if key in findings:
            comments[key] = findings[key]

    diagnostics: list[dict[str, Any]] = []
    comments["files"] = file_comments_from_findings(findings.get("files", {}))
    comments["inline"] = inline_comments_from_findings(
        diff_text,
        findings.get("inline", []),
        diagnostics=diagnostics,
    )
    enriched = enrich_comments_payload(diff_text, comments)
    diagnostics.extend(unresolved_target_diagnostics(enriched.get("inline", [])))
    return enriched, diagnostics


def file_comments_from_findings(raw_files: Any) -> dict[str, str]:
    if raw_files is None:
        return {}
    if isinstance(raw_files, dict):
        return {str(file_path): str(body) for file_path, body in raw_files.items() if str(body)}
    if not isinstance(raw_files, list):
        raise DiffReportError("findings.files must be an object or a list")

    comments: dict[str, str] = {}
    for item in raw_files:
        if not isinstance(item, dict):
            raise DiffReportError("findings.files entries must be objects")
        file_path = str(required_finding(item, "file"))
        body = str(required_finding(item, "body"))
        if body:
            comments[file_path] = body
    return comments


def inline_comments_from_findings(
    diff_text: str,
    raw_inline: Any,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if raw_inline is None:
        return []
    if not isinstance(raw_inline, list):
        raise DiffReportError("findings.inline must be a list")

    targets = list(diff_line_targets(diff_text).values())
    comments: list[dict[str, Any]] = []
    for index, item in enumerate(raw_inline):
        if not isinstance(item, dict):
            raise DiffReportError("findings.inline entries must be objects")
        file_path = str(required_finding(item, "file"))
        try:
            line = int(item["line"]) if "line" in item else resolve_finding_line(targets, item, file_path)
        except DiffReportError as error:
            if diagnostics is None:
                raise
            diagnostics.append(finding_diagnostic(index, item, file_path, str(error)))
            continue
        comment = {
            "file": file_path,
            "line": line,
            "title": str(item.get("title", f"Review: {file_path}:{line}")),
            "body": str(item.get("body", "")),
        }
        for key in _INLINE_OPTIONAL_KEYS:
            if key in item:
                comment[key] = item[key]
        comments.append(comment)
    return comments


def unresolved_target_diagnostics(raw_inline: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_inline, list):
        return []

    diagnostics: list[dict[str, Any]] = []
    for index, item in enumerate(raw_inline):
        if not isinstance(item, dict):
            continue
        target = item.get("target", {})
        status = target.get("status") if isinstance(target, dict) else None
        if status not in {"ambiguous", "not_found"}:
            continue
        diagnostic = {
            "index": index,
            "file": item.get("file"),
            "line": item.get("line"),
            "status": status,
            "message": f"inline finding target is {status}",
            "title": item.get("title"),
        }
        if isinstance(target, dict) and "candidate_lines" in target:
            diagnostic["candidate_lines"] = target["candidate_lines"]
        diagnostics.append(diagnostic)
    return diagnostics


def finding_diagnostic(
    index: int,
    item: dict[str, Any],
    file_path: str,
    message: str,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "index": index,
        "file": file_path,
        "status": "unresolved",
        "message": message,
    }
    for key in ("title", "content", "contains", "kind"):
        if key in item:
            diagnostic[key] = item[key]
    return diagnostic


def resolve_finding_line(
    targets: list[dict[str, Any]],
    item: dict[str, Any],
    file_path: str,
) -> int:
    if "content" not in item and "contains" not in item:
        raise DiffReportError(
            f"inline finding for {file_path} must provide line, content, or contains"
        )

    expected_kind = item.get("kind")
    matches: list[dict[str, Any]] = []
    for target in targets:
        if target.get("file") != file_path:
            continue
        if expected_kind is not None and target.get("kind") != expected_kind:
            continue
        content = target.get("content")
        if not isinstance(content, str):
            continue
        if "content" in item and content == str(item["content"]):
            matches.append(target)
        elif "contains" in item and str(item["contains"]) in content:
            matches.append(target)

    if len(matches) == 1:
        return int(matches[0]["line"])
    if not matches:
        raise DiffReportError(f"inline finding target was not found in {file_path}")
    candidate_lines = ", ".join(str(match["line"]) for match in matches)
    raise DiffReportError(
        f"inline finding target is ambiguous in {file_path}; candidate lines: {candidate_lines}"
    )


def required_finding(item: dict[str, Any], key: str) -> Any:
    value = item.get(key)
    if value is None:
        raise DiffReportError(f"findings entry missing required field: {key}")
    return value
