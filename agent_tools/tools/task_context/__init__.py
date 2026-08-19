"""Structured task context journal and compaction CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Iterable
from typing import Sequence


JOURNAL_FILENAME = "TASK_CONTEXT_LOG.jsonl"
CONTEXT_FILENAME = "TASK_CONTEXT.md"
SEVERITIES = ("note", "low", "mid", "high", "critical")
STATUSES = ("active", "resolved", "stale")
DEFAULT_COMPACT_LIMIT = 40


@dataclass(frozen=True)
class ContextEntry:
    timestamp: str
    severity: str
    labels: tuple[str, ...]
    status: str
    summary: str
    details: str = ""
    source: str = "agent"
    artifacts: tuple[str, ...] = ()

    @classmethod
    def from_json(cls, data: object) -> "ContextEntry":
        if not isinstance(data, dict):
            raise ValueError("entry must be a JSON object")
        timestamp = _required_string(data, "timestamp")
        severity = _validate_choice(_required_string(data, "severity"), SEVERITIES, "severity")
        status = _validate_choice(str(data.get("status", "active")), STATUSES, "status")
        labels = tuple(_string_list(data.get("labels", []), "labels"))
        artifacts = tuple(_string_list(data.get("artifacts", []), "artifacts"))
        return cls(
            timestamp=timestamp,
            severity=severity,
            labels=labels,
            status=status,
            summary=_required_string(data, "summary"),
            details=str(data.get("details", "")),
            source=str(data.get("source", "agent")),
            artifacts=artifacts,
        )

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "labels": list(self.labels),
            "status": self.status,
            "summary": self.summary,
            "source": self.source,
        }
        if self.details:
            data["details"] = self.details
        if self.artifacts:
            data["artifacts"] = list(self.artifacts)
        return data


def journal_path(task_dir: Path) -> Path:
    return task_dir / JOURNAL_FILENAME


def context_path(task_dir: Path) -> Path:
    return task_dir / CONTEXT_FILENAME


def add_entry(
    task_dir: Path,
    *,
    summary: str,
    severity: str,
    labels: Iterable[str] = (),
    status: str = "active",
    details: str = "",
    source: str = "agent",
    artifacts: Iterable[str] = (),
    timestamp: str | None = None,
) -> ContextEntry:
    task_dir = task_dir.resolve()
    if not task_dir.is_dir():
        raise ValueError(f"task directory does not exist: {task_dir}")
    entry = ContextEntry(
        timestamp=timestamp or datetime.now().astimezone().isoformat(timespec="seconds"),
        severity=_validate_choice(severity, SEVERITIES, "severity"),
        labels=tuple(_normalize_token(label, "label") for label in labels),
        status=_validate_choice(status, STATUSES, "status"),
        summary=_non_empty(summary, "summary"),
        details=details.strip(),
        source=_normalize_token(source, "source"),
        artifacts=tuple(artifact.strip() for artifact in artifacts if artifact.strip()),
    )
    path = journal_path(task_dir)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry.to_json(), ensure_ascii=False, sort_keys=True))
        stream.write("\n")
    return entry


def load_entries(task_dir: Path) -> list[ContextEntry]:
    path = journal_path(task_dir)
    if not path.exists():
        return []
    entries: list[ContextEntry] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(ContextEntry.from_json(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return entries


def filter_entries(
    entries: Iterable[ContextEntry],
    *,
    since: str | None = None,
    until: str | None = None,
    severity: str | None = None,
    labels: Iterable[str] = (),
    statuses: Iterable[str] = (),
) -> list[ContextEntry]:
    start = _parse_boundary(since, end_of_day=False) if since else None
    end = _parse_boundary(until, end_of_day=True) if until else None
    severity_values = _severity_filter(severity)
    label_values = {label.casefold() for label in labels}
    status_values = {_validate_choice(status, STATUSES, "status") for status in statuses}
    filtered: list[ContextEntry] = []
    for entry in entries:
        timestamp = _entry_datetime(entry)
        if start is not None and timestamp < start:
            continue
        if end is not None and timestamp > end:
            continue
        if severity_values is not None and entry.severity not in severity_values:
            continue
        if label_values and not label_values.issubset({label.casefold() for label in entry.labels}):
            continue
        if status_values and entry.status not in status_values:
            continue
        filtered.append(entry)
    return sorted(filtered, key=lambda item: item.timestamp)


def render_entries(entries: Iterable[ContextEntry], *, format_name: str = "text") -> str:
    entries = list(entries)
    if format_name == "json":
        return json.dumps([entry.to_json() for entry in entries], ensure_ascii=False, indent=2)
    if format_name == "markdown":
        return "\n".join(_entry_markdown(entry) for entry in entries).rstrip()
    if format_name != "text":
        raise ValueError(f"unknown format: {format_name}")
    return "\n".join(_entry_text(entry) for entry in entries)


def compact_context(
    task_dir: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    severity: str | None = "mid..critical",
    labels: Iterable[str] = (),
    statuses: Iterable[str] = ("active",),
    limit: int = DEFAULT_COMPACT_LIMIT,
) -> str:
    entries = filter_entries(
        load_entries(task_dir),
        since=since,
        until=until,
        severity=severity,
        labels=labels,
        statuses=statuses,
    )
    if limit > 0:
        entries = entries[-limit:]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# Task Context",
        "",
        f"_Generated from `{JOURNAL_FILENAME}` at {now}._",
        "",
        "## Current Working Context",
        "",
    ]
    if entries:
        lines.extend(_entry_markdown(entry) for entry in entries)
    else:
        lines.append("- No matching active context entries.")
    lines.extend(
        [
            "",
            "## Journal Query",
            "",
            "Use `python3 -m agent_tools.tools.task_context query --task <task-dir>` ",
            "to inspect older, resolved, lower-severity, or label-specific entries.",
            "",
        ]
    )
    return "\n".join(lines)


def write_compact_context(task_dir: Path, **kwargs: object) -> str:
    content = compact_context(task_dir, **kwargs)
    context_path(task_dir).write_text(content, encoding="utf-8")
    return content


def _entry_text(entry: ContextEntry) -> str:
    labels = ",".join(entry.labels) if entry.labels else "-"
    return f"{entry.timestamp}\t{entry.severity}\t{entry.status}\t{labels}\t{entry.summary}"


def _entry_markdown(entry: ContextEntry) -> str:
    labels = ", ".join(f"`{label}`" for label in entry.labels) if entry.labels else "`unlabeled`"
    head = f"- **{entry.severity}/{entry.status}** {entry.summary} ({entry.timestamp}; {labels})"
    parts = [head]
    if entry.details:
        parts.append(f"  Details: {entry.details}")
    if entry.artifacts:
        parts.append("  Artifacts: " + ", ".join(f"`{artifact}`" for artifact in entry.artifacts))
    return "\n".join(parts)


def _severity_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    if ".." in value:
        start, end = value.split("..", 1)
        start_index = SEVERITIES.index(_validate_choice(start, SEVERITIES, "severity"))
        end_index = SEVERITIES.index(_validate_choice(end, SEVERITIES, "severity"))
        if start_index > end_index:
            start_index, end_index = end_index, start_index
        return set(SEVERITIES[start_index : end_index + 1])
    return {_validate_choice(value, SEVERITIES, "severity")}


def _parse_boundary(value: str, *, end_of_day: bool) -> datetime:
    if "T" in value:
        timestamp = datetime.fromisoformat(value)
        return timestamp.replace(tzinfo=None) if timestamp.tzinfo is not None else timestamp
    parsed = date.fromisoformat(value)
    suffix = "23:59:59" if end_of_day else "00:00:00"
    return datetime.fromisoformat(f"{parsed.isoformat()}T{suffix}")


def _entry_datetime(entry: ContextEntry) -> datetime:
    timestamp = datetime.fromisoformat(entry.timestamp)
    if timestamp.tzinfo is None:
        return timestamp
    return timestamp.replace(tzinfo=None)


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    result = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field} entries must be strings")
        if item.strip():
            result.append(item.strip())
    return result


def _non_empty(value: str, field: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must not be empty")
    return value


def _normalize_token(value: str, field: str) -> str:
    value = _non_empty(value, field).replace(" ", "-").lower()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    if any(char not in allowed for char in value):
        raise ValueError(f"{field} must contain only letters, digits, underscores, or hyphens")
    return value


def _validate_choice(value: str, choices: Sequence[str], field: str) -> str:
    value = value.strip().lower()
    if value not in choices:
        raise ValueError(f"{field} must be one of: {', '.join(choices)}")
    return value


def _split_csv(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(item.strip() for item in value.split(",") if item.strip())
    return result


def add_command(args: argparse.Namespace) -> int:
    entry = add_entry(
        args.task,
        summary=args.summary,
        severity=args.severity,
        labels=_split_csv(args.label),
        status=args.status,
        details=args.details or "",
        source=args.source,
        artifacts=_split_csv(args.artifact),
        timestamp=args.timestamp,
    )
    print(json.dumps(entry.to_json(), ensure_ascii=False, sort_keys=True))
    return 0


def query_command(args: argparse.Namespace) -> int:
    entries = filter_entries(
        load_entries(args.task),
        since=args.since,
        until=args.until,
        severity=args.severity,
        labels=_split_csv(args.label),
        statuses=_split_csv(args.status),
    )
    rendered = render_entries(entries, format_name=args.format)
    if rendered:
        print(rendered)
    return 0


def compact_command(args: argparse.Namespace) -> int:
    kwargs = {
        "since": args.since,
        "until": args.until,
        "severity": args.severity,
        "labels": _split_csv(args.label),
        "statuses": _split_csv(args.status) or ("active",),
        "limit": args.limit,
    }
    content = compact_context(args.task, **kwargs) if args.dry_run else write_compact_context(args.task, **kwargs)
    if args.dry_run or args.print:
        print(content.rstrip())
    else:
        print(f"task-context: wrote {context_path(args.task)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    add_parser = subparsers.add_parser("add", help="Append one structured context entry.")
    add_parser.add_argument("--task", type=Path, required=True)
    add_parser.add_argument("--severity", choices=SEVERITIES, default="mid")
    add_parser.add_argument("--label", action="append", default=[])
    add_parser.add_argument("--status", choices=STATUSES, default="active")
    add_parser.add_argument("--details", default="")
    add_parser.add_argument("--source", default="agent")
    add_parser.add_argument("--artifact", action="append", default=[])
    add_parser.add_argument("--timestamp")
    add_parser.add_argument("summary")
    add_parser.set_defaults(func=add_command)

    query_parser = subparsers.add_parser("query", help="Query context journal entries.")
    query_parser.add_argument("--task", type=Path, required=True)
    query_parser.add_argument("--since")
    query_parser.add_argument("--until")
    query_parser.add_argument("--severity")
    query_parser.add_argument("--label", action="append", default=[])
    query_parser.add_argument("--status", action="append", default=[])
    query_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    query_parser.set_defaults(func=query_command)

    compact_parser = subparsers.add_parser("compact", help="Regenerate TASK_CONTEXT.md from the journal.")
    compact_parser.add_argument("--task", type=Path, required=True)
    compact_parser.add_argument("--since")
    compact_parser.add_argument("--until")
    compact_parser.add_argument("--severity", default="mid..critical")
    compact_parser.add_argument("--label", action="append", default=[])
    compact_parser.add_argument("--status", action="append", default=["active"])
    compact_parser.add_argument("--limit", type=int, default=DEFAULT_COMPACT_LIMIT)
    compact_parser.add_argument("--dry-run", action="store_true")
    compact_parser.add_argument("--print", action="store_true")
    compact_parser.set_defaults(func=compact_command)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"task-context: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
