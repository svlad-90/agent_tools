from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from agent_tools.agent_workspace.components.markdown.api import rough_token_count

from .common import trim
from .models import AgentSearchError, FileMatch, FileSearchReport, TextMatch, TextSearchReport


def render_text_search(report: TextSearchReport, *, mode: str, options: dict[str, Any]) -> str:
    if mode == "summary":
        return cap_output(render_text_summary(report, options), int(options["max_tokens"]), int(options["max_output_lines"]))
    if mode == "aggregate":
        return cap_output(render_text_aggregate(report, options), int(options["max_tokens"]), int(options["max_output_lines"]))
    if mode == "ranges":
        return cap_output(render_text_ranges(report), int(options["max_tokens"]), int(options["max_output_lines"]))
    raise AgentSearchError(f"unsupported text mode: {mode}")


def render_file_search(report: FileSearchReport, *, mode: str, options: dict[str, Any]) -> str:
    if mode == "summary":
        return cap_output(render_file_summary(report, options), int(options["max_tokens"]), int(options["max_output_lines"]))
    if mode == "aggregate":
        return cap_output(render_file_aggregate(report, options), int(options["max_tokens"]), int(options["max_output_lines"]))
    raise AgentSearchError(f"unsupported file mode: {mode}")


def render_text_search_json(
    report: TextSearchReport,
    *,
    max_matches: int = 200,
    max_ranges: int = 20,
    max_range_lines: int = 300,
) -> str:
    payload = text_report_payload(
        report,
        max_matches=max_matches,
        max_ranges=max_ranges,
        max_range_lines=max_range_lines,
    )
    return json.dumps(payload, indent=2, sort_keys=True)


def render_file_search_json(report: FileSearchReport, *, max_files: int = 200) -> str:
    return json.dumps(file_report_payload(report, max_files=max_files), indent=2, sort_keys=True)


def render_text_summary(report: TextSearchReport, options: dict[str, Any]) -> str:
    rel_matches = [(m.path.relative_to(report.root), m) for m in report.matches]
    by_file = Counter(rel.as_posix() for rel, _m in rel_matches)
    by_dir = Counter((rel.parent.as_posix() if rel.parent.as_posix() != "." else ".") for rel, _m in rel_matches)
    lines = [
        f"query={report.query!r} mode=summary elapsed={report.elapsed_seconds:.4f}s",
        f"matches={len(report.matches)} files={len(by_file)} dirs={len(by_dir)} scanned_files={report.files_scanned} skipped_files={report.files_skipped}",
    ]
    if report.truncated:
        lines.append("truncated: match scan limit reached")
    lines.extend(counter_lines("top-dirs", by_dir, int(options["max_dirs"])))
    lines.extend(counter_lines("top-files", by_file, int(options["max_files"])))
    lines.append("samples:")
    ranked = rank_text_matches(report.matches, report.root)
    for match in ranked[: int(options["samples"])]:
        lines.append(match_line(match, report.root, max_chars=180))
    if ranked:
        best = ranked[0].path.as_posix()
        lines.append(f"next: rerun with `text {report.query!r} {best} --mode ranges --around 5` for local context")
    return "\n".join(lines) + "\n"


def render_text_aggregate(report: TextSearchReport, options: dict[str, Any]) -> str:
    tree = group_text_matches(report)
    lines = [
        f"query={report.query!r} mode=aggregate elapsed={report.elapsed_seconds:.4f}s",
        f"matches={len(report.matches)} scanned_files={report.files_scanned}",
    ]
    append_group_lines(
        lines,
        tree,
        report.root,
        max_groups=int(options["max_files"]),
        per_group_samples=int(options["per_group_samples"]),
    )
    return "\n".join(lines) + "\n"


def render_text_ranges(report: TextSearchReport) -> str:
    lines = [
        f"query={report.query!r} mode=ranges elapsed={report.elapsed_seconds:.4f}s",
        f"matches={len(report.matches)} ranges={len(report.ranges)} scanned_files={report.files_scanned}",
    ]
    for snippet in report.ranges:
        rel = snippet.path.relative_to(report.root).as_posix()
        match_text = ",".join(str(line) for line in snippet.match_lines)
        lines.append(f"{rel}:{snippet.start}:{snippet.end} matches={match_text}")
        match_set = set(snippet.match_lines)
        for line_no, text in snippet.lines:
            prefix = ">" if line_no in match_set else " "
            lines.append(f"{prefix} {line_no:5d}  {trim(text, 220)}")
    return "\n".join(lines) + "\n"


def render_file_summary(report: FileSearchReport, options: dict[str, Any]) -> str:
    by_dir = Counter(
        (match.path.relative_to(report.root).parent.as_posix() if match.path.relative_to(report.root).parent.as_posix() != "." else ".")
        for match in report.matches
    )
    by_ext = Counter(match.path.suffix or "<none>" for match in report.matches)
    lines = [
        f"query={report.query!r} mode=files-summary elapsed={report.elapsed_seconds:.4f}s",
        f"matches={len(report.matches)} scanned_files={report.files_scanned}",
    ]
    if report.truncated:
        lines.append("truncated: file scan limit reached")
    lines.extend(counter_lines("by-extension", by_ext, 20))
    lines.extend(counter_lines("top-dirs", by_dir, int(options["max_dirs"])))
    lines.append("files:")
    for match in report.matches[: int(options["max_files"])]:
        rel = match.path.relative_to(report.root).as_posix()
        lines.append(f"{match.score:02d} {rel} reason={match.reason}")
    return "\n".join(lines) + "\n"


def render_file_aggregate(report: FileSearchReport, options: dict[str, Any]) -> str:
    grouped: dict[str, list[FileMatch]] = defaultdict(list)
    for match in report.matches:
        rel = match.path.relative_to(report.root)
        key = rel.parent.as_posix() if rel.parent.as_posix() != "." else "."
        grouped[key].append(match)
    lines = [
        f"query={report.query!r} mode=files-aggregate elapsed={report.elapsed_seconds:.4f}s",
        f"matches={len(report.matches)} scanned_files={report.files_scanned}",
    ]
    for directory, matches in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[: int(options["max_dirs"])]:
        lines.append(f"{directory} files={len(matches)}")
        for match in matches[: int(options["max_files"])]:
            lines.append(f"  {match.path.name} score={match.score} reason={match.reason}")
    return "\n".join(lines) + "\n"


def group_text_matches(report: TextSearchReport) -> dict[str, Any]:
    root: dict[str, Any] = {"matches": [], "children": {}}
    for match in report.matches:
        path = match.path.relative_to(report.root)
        group_values = ordered_group_values(match)
        if not group_values:
            group_values = [
                ("dir", path.parent.as_posix() if path.parent.as_posix() != "." else "."),
                ("file", path.name),
            ]
        node = root
        for label, value in group_values:
            key = f"{label}={value}"
            node = node["children"].setdefault(key, {"matches": [], "children": {}})
        node["matches"].append(match)
    return root


def ordered_group_values(match: TextMatch) -> list[tuple[str, str]]:
    parsed: list[tuple[int, str, str]] = []
    fallback_order = 1_000_000
    for name, values in match.groups.items():
        for value_index, value in enumerate(values):
            order, label = group_order_and_label(name)
            parsed.append((order + value_index, label, value))
            if order == fallback_order:
                fallback_order += 1
    parsed.sort(key=lambda item: item[0])
    return [(label, value) for _order, label, value in parsed]


def group_order_and_label(name: str) -> tuple[int, str]:
    upper = name.upper()
    if upper == "GV":
        return 1_000_000, "GV"
    if upper.startswith("GV_"):
        suffix = name[3:]
        if suffix.isdigit():
            return int(suffix), name
    parts = name.split("_", 2)
    if len(parts) == 3 and parts[0].lower() in {"as", "tree", "g"} and parts[1].isdigit():
        return int(parts[1]), parts[2]
    return 1_000_000, name


def append_group_lines(
    lines: list[str],
    node: dict[str, Any],
    root: Path,
    *,
    max_groups: int,
    per_group_samples: int,
    depth: int = 0,
    group_counter: list[int] | None = None,
) -> None:
    if group_counter is None:
        group_counter = [0]
    children = sorted(node["children"].items(), key=lambda item: (-node_match_count(item[1]), item[0]))
    for key, child in children:
        if group_counter[0] >= max_groups:
            lines.append(f"{'  ' * depth}... groups truncated")
            return
        group_counter[0] += 1
        lines.append(f"{'  ' * depth}{key} matches={node_match_count(child)}")
        samples = child["matches"][:per_group_samples]
        for match in samples:
            lines.append(f"{'  ' * (depth + 1)}{match_line(match, root, max_chars=140)}")
        append_group_lines(
            lines,
            child,
            root,
            max_groups=max_groups,
            per_group_samples=per_group_samples,
            depth=depth + 1,
            group_counter=group_counter,
        )


def node_match_count(node: dict[str, Any]) -> int:
    return len(node["matches"]) + sum(node_match_count(child) for child in node["children"].values())


def rank_text_matches(matches: tuple[TextMatch, ...], root: Path) -> list[TextMatch]:
    by_file = Counter(match.path for match in matches)

    def key(match: TextMatch) -> tuple[int, str, int]:
        rel = match.path.relative_to(root).as_posix()
        score = min(5, by_file[match.path])
        stripped = match.text.strip()
        if stripped.startswith(("def ", "class ", "async def ")):
            score += 5
        if "test" in rel:
            score += 1
        return (-score, rel, match.line)

    return sorted(matches, key=key)


def counter_lines(title: str, counter: Counter[str], limit: int) -> list[str]:
    lines = [f"{title}:"]
    for key, value in counter.most_common(limit):
        lines.append(f"  {value:5d}  {key}")
    return lines


def match_line(match: TextMatch, root: Path, *, max_chars: int) -> str:
    rel = match.path.relative_to(root).as_posix()
    return f"{rel}:{match.line}:{match.column}: {trim(match.text.strip(), max_chars)}"


def cap_output(text: str, max_tokens: int, max_lines: int) -> str:
    lines = text.splitlines()
    truncated = False
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    while rough_token_count("\n".join(lines)) > max_tokens and len(lines) > 1:
        lines.pop()
        truncated = True
    if truncated:
        lines.append("truncated: output budget reached; rerun with narrower query or higher limits")
    return "\n".join(lines) + "\n"


def text_report_payload(
    report: TextSearchReport,
    *,
    max_matches: int,
    max_ranges: int,
    max_range_lines: int,
) -> dict[str, Any]:
    selected_matches = report.matches[:max_matches]
    selected_ranges = report.ranges[:max_ranges]
    selected_range_line_count = 0
    range_payloads = []
    for snippet in selected_ranges:
        remaining = max(0, max_range_lines - selected_range_line_count)
        selected_lines = snippet.lines[:remaining]
        selected_range_line_count += len(selected_lines)
        range_payloads.append(
            {
                "path": str(snippet.path.relative_to(report.root)),
                "start": snippet.start,
                "end": snippet.end,
                "match_lines": list(snippet.match_lines),
                "lines": [{"line": line_no, "text": text} for line_no, text in selected_lines],
                "truncated": len(selected_lines) < len(snippet.lines),
            }
        )
        if selected_range_line_count >= max_range_lines:
            break
    return {
        "root": str(report.root),
        "query": report.query,
        "elapsed_seconds": report.elapsed_seconds,
        "files_scanned": report.files_scanned,
        "files_skipped": report.files_skipped,
        "truncated": report.truncated or len(selected_matches) < len(report.matches) or len(range_payloads) < len(report.ranges),
        "total_matches": len(report.matches),
        "total_ranges": len(report.ranges),
        "matches": [
            {
                "path": str(match.path.relative_to(report.root)),
                "line": match.line,
                "column": match.column,
                "text": match.text,
                "groups": match.groups,
            }
            for match in selected_matches
        ],
        "ranges": range_payloads,
    }


def file_report_payload(report: FileSearchReport, *, max_files: int) -> dict[str, Any]:
    selected_matches = report.matches[:max_files]
    return {
        "root": str(report.root),
        "query": report.query,
        "elapsed_seconds": report.elapsed_seconds,
        "files_scanned": report.files_scanned,
        "truncated": report.truncated or len(selected_matches) < len(report.matches),
        "total_matches": len(report.matches),
        "matches": [
            {
                "path": str(match.path.relative_to(report.root)),
                "score": match.score,
                "reason": match.reason,
            }
            for match in selected_matches
        ],
    }
