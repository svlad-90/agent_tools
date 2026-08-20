"""Transactional task context database and compaction CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
from typing import Iterable
from typing import Sequence


DATABASE_FILENAME = "TASK_CONTEXT.sqlite3"
LEGACY_JOURNAL_FILENAME = "TASK_CONTEXT_LOG.jsonl"
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
    id: int | None = None

    @classmethod
    def from_json(cls, data: object) -> "ContextEntry":
        if not isinstance(data, dict):
            raise ValueError("entry must be a JSON object")
        timestamp = _validate_timestamp(_required_string(data, "timestamp"))
        severity = _validate_choice(_required_string(data, "severity"), SEVERITIES, "severity")
        status = _validate_choice(str(data.get("status", "active")), STATUSES, "status")
        labels = tuple(_string_list(data.get("labels", []), "labels"))
        artifacts = tuple(_string_list(data.get("artifacts", []), "artifacts"))
        entry_id = data.get("id")
        return cls(
            timestamp=timestamp,
            severity=severity,
            labels=labels,
            status=status,
            summary=_required_string(data, "summary"),
            details=str(data.get("details", "")),
            source=str(data.get("source", "agent")),
            artifacts=artifacts,
            id=_entry_id(entry_id) if entry_id is not None else None,
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
        if self.id is not None:
            data["id"] = self.id
        return data


def database_path(task_dir: Path) -> Path:
    return task_dir / DATABASE_FILENAME


def legacy_journal_path(task_dir: Path) -> Path:
    return task_dir / LEGACY_JOURNAL_FILENAME


def journal_path(task_dir: Path) -> Path:
    return database_path(task_dir)


def ensure_database(task_dir: Path) -> None:
    task_dir = task_dir.resolve()
    if not task_dir.is_dir():
        raise ValueError(f"task directory does not exist: {task_dir}")
    with sqlite3.connect(database_path(task_dir)) as connection:
        _create_schema(connection)


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
        timestamp=_validate_timestamp(timestamp or datetime.now().astimezone().isoformat(timespec="seconds")),
        severity=_validate_choice(severity, SEVERITIES, "severity"),
        labels=tuple(_normalize_token(label, "label") for label in labels),
        status=_validate_choice(status, STATUSES, "status"),
        summary=_non_empty(summary, "summary"),
        details=details.strip(),
        source=_normalize_token(source, "source"),
        artifacts=tuple(artifact.strip() for artifact in artifacts if artifact.strip()),
    )
    ensure_database(task_dir)
    with sqlite3.connect(database_path(task_dir)) as connection:
        entry_id = _insert_entry(connection, entry)
    return replace(entry, id=entry_id)


def load_entries(task_dir: Path) -> list[ContextEntry]:
    path = database_path(task_dir)
    if not path.exists():
        return []
    entries: list[ContextEntry] = []
    with sqlite3.connect(path) as connection:
        _create_schema(connection)
        rows = connection.execute(
            "SELECT id, timestamp, severity, labels, status, summary, details, source, artifacts "
            "FROM context_entries ORDER BY timestamp, id"
        ).fetchall()
    for row in rows:
        data = {
            "id": row[0],
            "timestamp": row[1],
            "severity": row[2],
            "labels": json.loads(row[3]),
            "status": row[4],
            "summary": row[5],
            "details": row[6],
            "source": row[7],
            "artifacts": json.loads(row[8]),
        }
        entries.append(ContextEntry.from_json(data))
    return entries


def edit_entries(
    task_dir: Path,
    *,
    ids: Iterable[int] = (),
    since: str | None = None,
    until: str | None = None,
    severity: str | Iterable[str] | None = None,
    labels: Iterable[str] = (),
    statuses: Iterable[str] = ("active",),
    all_entries: bool = False,
    set_status: str | None = None,
    set_severity: str | None = None,
    set_summary: str | None = None,
    set_details: str | None = None,
    set_source: str | None = None,
    set_labels: Iterable[str] | None = None,
    add_labels: Iterable[str] = (),
    remove_labels: Iterable[str] = (),
    clear_labels: bool = False,
    set_artifacts: Iterable[str] | None = None,
    add_artifacts: Iterable[str] = (),
    remove_artifacts: Iterable[str] = (),
    clear_artifacts: bool = False,
    delete: bool = False,
    dry_run: bool = False,
) -> list[ContextEntry]:
    task_dir = task_dir.resolve()
    id_values = {_entry_id(entry_id) for entry_id in ids}
    label_values = tuple(labels)
    status_values = tuple(statuses)
    set_label_values = tuple(set_labels) if set_labels is not None else None
    add_label_values = tuple(add_labels)
    remove_label_values = tuple(remove_labels)
    set_artifact_values = tuple(set_artifacts) if set_artifacts is not None else None
    add_artifact_values = tuple(add_artifacts)
    remove_artifact_values = tuple(remove_artifacts)
    has_selector = bool(id_values or since or until or severity or label_values or all_entries)
    if not has_selector:
        raise ValueError("refusing to edit entries without --all, --id, or a non-status filter")
    operations = [
        set_status is not None,
        set_severity is not None,
        set_summary is not None,
        set_details is not None,
        set_source is not None,
        set_label_values is not None,
        bool(add_label_values),
        bool(remove_label_values),
        clear_labels,
        set_artifact_values is not None,
        bool(add_artifact_values),
        bool(remove_artifact_values),
        clear_artifacts,
        delete,
    ]
    if not any(operations):
        raise ValueError("no edit operation was requested")
    if delete and any(operation for operation in operations[:-1]):
        raise ValueError("--delete cannot be combined with field update operations")
    selected = _select_entries(
        task_dir,
        ids=id_values,
        since=since,
        until=until,
        severity=severity,
        labels=label_values,
        statuses=status_values,
    )
    if delete:
        if dry_run or not selected:
            return selected
        _delete_entries(task_dir, selected)
        return selected
    updated = [
        _edited_entry(
            entry,
            set_status=set_status,
            set_severity=set_severity,
            set_summary=set_summary,
            set_details=set_details,
            set_source=set_source,
            set_labels=set_label_values,
            add_labels=add_label_values,
            remove_labels=remove_label_values,
            clear_labels=clear_labels,
            set_artifacts=set_artifact_values,
            add_artifacts=add_artifact_values,
            remove_artifacts=remove_artifact_values,
            clear_artifacts=clear_artifacts,
        )
        for entry in selected
    ]
    changed = [entry for original, entry in zip(selected, updated) if entry != original]
    if dry_run or not changed:
        return changed
    _update_entries(task_dir, changed)
    return changed


def update_entry_statuses(
    task_dir: Path,
    *,
    new_status: str,
    ids: Iterable[int] = (),
    since: str | None = None,
    until: str | None = None,
    severity: str | Iterable[str] | None = None,
    labels: Iterable[str] = (),
    statuses: Iterable[str] = ("active",),
    all_entries: bool = False,
    dry_run: bool = False,
) -> list[ContextEntry]:
    return edit_entries(
        task_dir,
        ids=ids,
        since=since,
        until=until,
        severity=severity,
        labels=labels,
        statuses=statuses,
        all_entries=all_entries,
        set_status=new_status,
        dry_run=dry_run,
    )


def _select_entries(
    task_dir: Path,
    *,
    ids: set[int],
    since: str | None,
    until: str | None,
    severity: str | Iterable[str] | None,
    labels: Iterable[str],
    statuses: Iterable[str],
) -> list[ContextEntry]:
    entries = load_entries(task_dir)
    if ids:
        return [entry for entry in entries if entry.id in ids]
    return filter_entries(
        entries,
        since=since,
        until=until,
        severity=severity,
        labels=labels,
        statuses=statuses,
    )


def _edited_entry(
    entry: ContextEntry,
    *,
    set_status: str | None,
    set_severity: str | None,
    set_summary: str | None,
    set_details: str | None,
    set_source: str | None,
    set_labels: Iterable[str] | None,
    add_labels: Iterable[str],
    remove_labels: Iterable[str],
    clear_labels: bool,
    set_artifacts: Iterable[str] | None,
    add_artifacts: Iterable[str],
    remove_artifacts: Iterable[str],
    clear_artifacts: bool,
) -> ContextEntry:
    labels = entry.labels
    if set_labels is not None:
        labels = _normalized_tokens(set_labels, "label")
    elif clear_labels:
        labels = ()
    if add_labels:
        labels = _unique((*labels, *_normalized_tokens(add_labels, "label")))
    if remove_labels:
        remove_values = set(_normalized_tokens(remove_labels, "label"))
        labels = tuple(label for label in labels if label not in remove_values)
    artifacts = entry.artifacts
    if set_artifacts is not None:
        artifacts = _normalized_artifacts(set_artifacts)
    elif clear_artifacts:
        artifacts = ()
    if add_artifacts:
        artifacts = _unique((*artifacts, *_normalized_artifacts(add_artifacts)))
    if remove_artifacts:
        remove_artifact_values = set(_normalized_artifacts(remove_artifacts))
        artifacts = tuple(artifact for artifact in artifacts if artifact not in remove_artifact_values)
    return replace(
        entry,
        status=_validate_choice(set_status, STATUSES, "status") if set_status is not None else entry.status,
        severity=(
            _validate_choice(set_severity, SEVERITIES, "severity")
            if set_severity is not None
            else entry.severity
        ),
        summary=_non_empty(set_summary, "summary") if set_summary is not None else entry.summary,
        details=set_details.strip() if set_details is not None else entry.details,
        source=_normalize_token(set_source, "source") if set_source is not None else entry.source,
        labels=labels,
        artifacts=artifacts,
    )


def _update_entries(task_dir: Path, entries: Sequence[ContextEntry]) -> None:
    with sqlite3.connect(database_path(task_dir)) as connection:
        _create_schema(connection)
        connection.executemany(
            "UPDATE context_entries SET severity = ?, labels = ?, status = ?, summary = ?, "
            "details = ?, source = ?, artifacts = ? WHERE id = ?",
            [
                (
                    entry.severity,
                    json.dumps(list(entry.labels), ensure_ascii=False),
                    entry.status,
                    entry.summary,
                    entry.details,
                    entry.source,
                    json.dumps(list(entry.artifacts), ensure_ascii=False),
                    entry.id,
                )
                for entry in entries
                if entry.id is not None
            ],
        )


def _delete_entries(task_dir: Path, entries: Sequence[ContextEntry]) -> None:
    ids = [entry.id for entry in entries if entry.id is not None]
    if not ids:
        return
    with sqlite3.connect(database_path(task_dir)) as connection:
        _create_schema(connection)
        placeholders = ",".join("?" for _entry_id_value in ids)
        connection.execute(f"DELETE FROM context_entries WHERE id IN ({placeholders})", ids)


def migrate_legacy_journal(task_dir: Path) -> int:
    task_dir = task_dir.resolve()
    legacy_path = legacy_journal_path(task_dir)
    if database_path(task_dir).exists():
        raise ValueError(f"{DATABASE_FILENAME} already exists; migration is not needed")
    if not legacy_path.is_file():
        raise ValueError(f"{LEGACY_JOURNAL_FILENAME} is missing; there is nothing to migrate")
    entries = _load_legacy_entries(task_dir)
    ensure_database(task_dir)
    with sqlite3.connect(database_path(task_dir)) as connection:
        for entry in entries:
            _insert_entry(connection, entry)
    legacy_path.unlink()
    return len(entries)


def filter_entries(
    entries: Iterable[ContextEntry],
    *,
    since: str | None = None,
    until: str | None = None,
    severity: str | Iterable[str] | None = None,
    labels: Iterable[str] = (),
    statuses: Iterable[str] = (),
    newest_first: bool = False,
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
    return sorted(filtered, key=lambda item: item.timestamp, reverse=newest_first)


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
        f"_Generated from `{DATABASE_FILENAME}` at {now}._",
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
            "Default agent context comes from active entries only:",
            "",
            "`python3 -m agent_tools.tools.task_context query --task <task-dir> "
            "--severity mid..critical --status active --format markdown`",
            "",
            "Query resolved or stale history only when the user asks or active context "
            "requires historical investigation.",
            "",
        ]
    )
    return "\n".join(lines)


def _entry_text(entry: ContextEntry) -> str:
    labels = ",".join(entry.labels) if entry.labels else "-"
    entry_id = entry.id if entry.id is not None else "-"
    return f"{entry_id}\t{entry.timestamp}\t{entry.severity}\t{entry.status}\t{labels}\t{entry.summary}"


def _entry_markdown(entry: ContextEntry) -> str:
    labels = ", ".join(f"`{label}`" for label in entry.labels) if entry.labels else "`unlabeled`"
    entry_id = f"#{entry.id} " if entry.id is not None else ""
    head = f"- **{entry.severity}/{entry.status}** {entry_id}{entry.summary} ({entry.timestamp}; {labels})"
    parts = [head]
    if entry.details:
        parts.append(f"  Details: {entry.details}")
    if entry.artifacts:
        parts.append("  Artifacts: " + ", ".join(f"`{artifact}`" for artifact in entry.artifacts))
    return "\n".join(parts)


def _severity_filter(value: str | Iterable[str] | None) -> set[str] | None:
    if not value:
        return None
    if not isinstance(value, str):
        return {_validate_choice(item, SEVERITIES, "severity") for item in value}
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


def _validate_timestamp(value: str) -> str:
    value = _non_empty(value, "timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO-8601 date-time") from exc
    return value


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS context_entries ("
        "id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, severity TEXT NOT NULL, "
        "labels TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL, "
        "details TEXT NOT NULL, source TEXT NOT NULL, artifacts TEXT NOT NULL)"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_timestamp ON context_entries(timestamp)")
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_severity ON context_entries(severity)")
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_status ON context_entries(status)")


def _insert_entry(connection: sqlite3.Connection, entry: ContextEntry) -> int:
    cursor = connection.execute(
        "INSERT INTO context_entries "
        "(timestamp, severity, labels, status, summary, details, source, artifacts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry.timestamp,
            entry.severity,
            json.dumps(list(entry.labels), ensure_ascii=False),
            entry.status,
            entry.summary,
            entry.details,
            entry.source,
            json.dumps(list(entry.artifacts), ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def _load_legacy_entries(task_dir: Path) -> list[ContextEntry]:
    path = legacy_journal_path(task_dir)
    entries: list[ContextEntry] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(ContextEntry.from_json(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return entries


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


def _normalized_tokens(values: Iterable[str], field: str) -> tuple[str, ...]:
    return _unique(_normalize_token(value, field) for value in values)


def _normalized_artifacts(values: Iterable[str]) -> tuple[str, ...]:
    return _unique(value.strip() for value in values if value.strip())


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)


def _entry_id(value: object) -> int:
    try:
        entry_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("entry id must be an integer") from exc
    if entry_id <= 0:
        raise ValueError("entry id must be positive")
    return entry_id


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


def _split_ids(values: Sequence[str]) -> list[int]:
    return [_entry_id(value) for value in _split_csv(values)]


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


def migrate_command(args: argparse.Namespace) -> int:
    count = migrate_legacy_journal(args.task)
    print(f"task-context: migrated {count} entries to {database_path(args.task)}")
    return 0


def query_command(args: argparse.Namespace) -> int:
    entries = filter_entries(
        load_entries(args.task),
        since=args.since,
        until=args.until,
        severity=args.severity,
        labels=_split_csv(args.label),
        statuses=_split_csv(args.status),
        newest_first=args.newest_first,
    )
    rendered = render_entries(entries, format_name=args.format)
    if rendered:
        print(rendered)
    return 0


def edit_command(args: argparse.Namespace) -> int:
    entries = edit_entries(
        args.task,
        ids=_split_ids(args.id),
        since=args.since,
        until=args.until,
        severity=args.severity,
        labels=_split_csv(args.label),
        statuses=_split_csv(args.status),
        all_entries=args.all,
        set_status=args.set_status,
        set_severity=args.set_severity,
        set_summary=args.set_summary,
        set_details=args.set_details,
        set_source=args.set_source,
        set_labels=_split_csv(args.set_label) if args.set_label else None,
        add_labels=_split_csv(args.add_label),
        remove_labels=_split_csv(args.remove_label),
        clear_labels=args.clear_labels,
        set_artifacts=_split_csv(args.set_artifact) if args.set_artifact else None,
        add_artifacts=_split_csv(args.add_artifact),
        remove_artifacts=_split_csv(args.remove_artifact),
        clear_artifacts=args.clear_artifacts,
        delete=args.delete,
        dry_run=args.dry_run,
    )
    if args.delete:
        action = "would delete" if args.dry_run else "deleted"
    else:
        action = "would edit" if args.dry_run else "edited"
    if args.format == "json":
        print(
            json.dumps(
                {
                    "action": action,
                    "count": len(entries),
                    "entries": [entry.to_json() for entry in entries],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    rendered = render_entries(entries, format_name=args.format)
    if rendered:
        print(rendered)
    print(f"task-context: {action} {len(entries)} entries")
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
    content = compact_context(args.task, **kwargs)
    print(content.rstrip())
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

    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Import the legacy TASK_CONTEXT_LOG.jsonl journal into SQLite.",
    )
    migrate_parser.add_argument("--task", type=Path, required=True)
    migrate_parser.set_defaults(func=migrate_command)

    query_parser = subparsers.add_parser("query", help="Query task context database entries.")
    query_parser.add_argument("--task", type=Path, required=True)
    query_parser.add_argument("--since")
    query_parser.add_argument("--until")
    query_parser.add_argument("--severity")
    query_parser.add_argument("--label", action="append", default=[])
    query_parser.add_argument("--status", action="append", default=[])
    query_parser.add_argument("--newest-first", action="store_true")
    query_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    query_parser.set_defaults(func=query_command)

    edit_parser = subparsers.add_parser("edit", help="Batch edit or delete task context entries.")
    edit_parser.add_argument("--task", type=Path, required=True)
    edit_parser.add_argument("--id", action="append", default=[])
    edit_parser.add_argument("--since")
    edit_parser.add_argument("--until")
    edit_parser.add_argument("--severity")
    edit_parser.add_argument("--label", action="append", default=[])
    edit_parser.add_argument("--status", action="append", default=[])
    edit_parser.add_argument("--all", action="store_true")
    edit_parser.add_argument("--set-status", choices=STATUSES)
    edit_parser.add_argument("--set-severity", choices=SEVERITIES)
    edit_parser.add_argument("--set-summary")
    edit_parser.add_argument("--set-details")
    edit_parser.add_argument("--set-source")
    edit_parser.add_argument("--set-label", action="append", default=[])
    edit_parser.add_argument("--add-label", action="append", default=[])
    edit_parser.add_argument("--remove-label", action="append", default=[])
    edit_parser.add_argument("--clear-labels", action="store_true")
    edit_parser.add_argument("--set-artifact", action="append", default=[])
    edit_parser.add_argument("--add-artifact", action="append", default=[])
    edit_parser.add_argument("--remove-artifact", action="append", default=[])
    edit_parser.add_argument("--clear-artifacts", action="store_true")
    edit_parser.add_argument("--delete", action="store_true")
    edit_parser.add_argument("--dry-run", action="store_true")
    edit_parser.add_argument("--format", choices=("text", "markdown", "json"), default="text")
    edit_parser.set_defaults(func=edit_command)

    compact_parser = subparsers.add_parser("compact", help="Render compact task context from SQLite.")
    compact_parser.add_argument("--task", type=Path, required=True)
    compact_parser.add_argument("--since")
    compact_parser.add_argument("--until")
    compact_parser.add_argument("--severity", default="mid..critical")
    compact_parser.add_argument("--label", action="append", default=[])
    compact_parser.add_argument("--status", action="append", default=["active"])
    compact_parser.add_argument("--limit", type=int, default=DEFAULT_COMPACT_LIMIT)
    compact_parser.add_argument("--dry-run", action="store_true", help=argparse.SUPPRESS)
    compact_parser.add_argument("--print", action="store_true", help=argparse.SUPPRESS)
    compact_parser.set_defaults(func=compact_command)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"task-context: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
