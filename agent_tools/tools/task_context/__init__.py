"""Transactional task context database and compaction CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from dataclasses import replace
from datetime import date
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import textwrap
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence

from agent_tools.lib.database import TASK_CONTEXT_DATABASE_FILENAME
from agent_tools.lib.database import configure_task_database_schema
from agent_tools.lib.database import connect_task_database
from agent_tools.lib.database import task_database_path

DATABASE_FILENAME = TASK_CONTEXT_DATABASE_FILENAME
LEGACY_JOURNAL_FILENAME = "TASK_CONTEXT_LOG.jsonl"
SEVERITIES = ("note", "low", "mid", "high", "critical")
STATUSES = ("active", "resolved", "stale")
LABELS = (
    "artifact",
    "blocker",
    "bug",
    "build",
    "cli",
    "commit",
    "decision",
    "docs",
    "env",
    "filter",
    "goal",
    "gui",
    "handoff",
    "knowledge",
    "legacy",
    "migration",
    "next-step",
    "policy",
    "push",
    "report",
    "repo",
    "runtime",
    "security",
    "superseded",
    "task-context",
    "test",
    "tooling",
    "ui",
    "user-preference",
    "validation",
)
SLOT_CATEGORIES = (
    "goal",
    "env",
    "decisions",
    "findings",
    "validation",
    "blocker-risk",
    "operational-memory",
    "user-preference",
    "legacy",
)
REQUIRED_SLOT_CATEGORIES = ("goal", "operational-memory")
RECOMMENDED_SLOT_CATEGORIES = ("env", "validation")
DEFAULT_COMPACT_LIMIT = 40
SLOT_MARKDOWN_CARD_WIDTH = 94
DICTIONARY_CODEC_VERSION = 2
DICTIONARY_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
DICTIONARY_AUTO_DISCOVERY_DEFAULT = True
DICTIONARY_MIN_OCCURRENCES = 3
DICTIONARY_MIN_SAVING = 1
DICTIONARY_MIN_TERM_LENGTH = 7
DICTIONARY_MAX_TERM_WORDS = 6
DICTIONARY_STRIP_ARTICLES_DEFAULT = True
DICTIONARY_STATUS_ACTIVE = "active"
DICTIONARY_TOKEN_PREFIX = "§"
DICTIONARY_TOKEN_SUFFIX = ""
DICTIONARY_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])§([0-9A-Za-z]{2,})(?![A-Za-z0-9_])")
TOKENIZER_ENCODING = "o200k_base"
TOKENIZER_MODEL_ENV = "AGENT_TOOLS_TOKENIZER_MODEL"
TOKENIZER_ENCODING_ENV = "AGENT_TOOLS_TOKENIZER_ENCODING"
_TOKENIZER_ENCODING_CACHE: Any | None = None
_TOKENIZER_IMPORT_FAILED = False
TECHNICAL_PATTERNS = (
    re.compile(r"\bCONFIG_[A-Za-z0-9_]+\b"),
    re.compile(r"\b(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_./-]+\b"),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_.]*\(\)"),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:_[A-Za-z0-9_]+)+\b"),
    re.compile(r"\b[A-Z][A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\b"),
    re.compile(
        r"\b(?:[A-Z][A-Za-z0-9_]*|UI|API|CLI|GTK|SQLite|JSON|Markdown)"
        r"(?:\s+(?:[A-Z][A-Za-z0-9_]*|UI|API|CLI|GTK|SQLite|JSON|Markdown)){1,5}\b"
    ),
)
ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
ARTICLE_WORDS = frozenset(("the", "a", "an"))
REPEATED_WORD_RE = re.compile(r"(?u)(?<![\w/-])[\w-]*[^\W\d_][\w-]*(?![\w/-])")
AGENT_WORKSPACE_SETTINGS_FILE = "settings.json"
LEGACY_DICTIONARY_PREVIEW_TEXT = (
    "Agent Workspace renders TASK_CONTEXT.sqlite3 entries. "
    "Agent Workspace Details can show encoded task context. "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates Agent Workspace behavior. "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py covers Agent Workspace settings. "
    "drivers/firmware/scmi/scmi.c calls scmi_send_message() when CONFIG_ARM_SCMI_TRANSPORT_SMC is enabled. "
    "drivers/firmware/scmi/scmi.c keeps scmi_send_message() consistent with CONFIG_ARM_SCMI_TRANSPORT_SMC."
)
DICTIONARY_PREVIEW_TEXT = (
    "Agent Workspace renders TASK_CONTEXT.sqlite3 slots for active tasks. "
    "Agent Workspace keeps task context readable for humans and encoded for agents. "
    "Agent Workspace Details can show encoded task context slots with dictionary aliases. "
    "Agent Workspace Settings includes a Dictionary tab for tuning the task dictionary compiler.\n\n"
    "The task dictionary compiler reads singleton slot content from TASK_CONTEXT.sqlite3. "
    "The task dictionary compiler discovers repeated terms in goal, env, findings, validation, and operational-memory slots, then decides whether an alias "
    "improves encoded context size. The task dictionary compiler must not rely on English semantic word lists. "
    "The task dictionary compiler should work with paths, config symbols, function names, repeated Unicode words, "
    "and repeated technical identifiers.\n\n"
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates Agent Workspace behavior. "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py covers Agent Workspace settings. "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py checks encoded context rendering. "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py verifies Dictionary preview counters.\n\n"
    "tools/task_context/tests/test_task_context.py validates task_context behavior. "
    "tools/task_context/tests/test_task_context.py checks dictionary candidate selection. "
    "tools/task_context/tests/test_task_context.py verifies append-only dictionary ids. "
    "tools/task_context/tests/test_task_context.py tests realistic context compression.\n\n"
    "task_check validates TASK_CONTEXT.sqlite3 before push. task_check reports slot context size using rough "
    "token budget. push_guard runs before git push. push_guard blocks repositories inside tasks/<task>/ when "
    "task_check reports failures. task_check --strict-warnings must pass before push-ready handoff.\n\n"
    "Harness adapter controls workspace policy through Codex and Claude hooks. Harness adapter records session start, "
    "user prompt, tool start, tool finish, Stop, PreCompact, and PostCompact events. Agent Workspace shows harness "
    "debug events in the AI Debug tab and uses the latest harness status icon in the task list.\n\n"
    "persistent append-only dictionary ids are stable task-local identities. persistent append-only dictionary ids "
    "must not be deleted. persistent append-only dictionary ids must not be reused. persistent append-only "
    "dictionary ids keep encoded context stable across compaction and resumed agent sessions.\n\n"
    "Agent policy requires reading current task context slots when task state is needed. Agent policy requires updating "
    "slots in place instead of appending changelog entries. Agent policy requires adding stable domain terms through "
    "dictionary --add. Agent policy requires terse factual durable slot content.\n\n"
    "Dictionary preview shows original chars, encoded body chars, dictionary chars, after chars including dictionary, "
    "and char saving. Dictionary preview also shows original tokens, encoded body tokens, dictionary tokens, body "
    "saving, and net saving. Dictionary preview helps compare min occurrences, min saving, min term length, max term "
    "words, and strip articles.\n\n"
    "The encoded context renderer shows Dictionary before encoded cards. The encoded context renderer keeps the same "
    "ASCII card layout as decoded view. The encoded context renderer replaces selected terms with §00, §01, and "
    "§02 aliases. The encoded context renderer should remain readable even when many repeated technical words are "
    "aliases.\n\n"
    "TASK_CONTEXT.sqlite3 is the only task context source. TASK_CONTEXT.sqlite3 stores singleton slots, encoded slot "
    "content, dictionary references, and append-only dictionary rows. TASK_CONTEXT.sqlite3 replaces legacy generated "
    "TASK_CONTEXT.md and legacy TASK_DESCRIPTION.md files. TASK_CONTEXT.sqlite3 keeps current slot state separate from "
    "temporary legacy import material.\n\n"
    "code_map parse-check validates changed Python files. code_map map helps inspect Python file structure. "
    "code_map symbol-get helps inspect exact function spans. code_map should pass for "
    "agent_workspace/components/gtk_desktop/src/gtk_ui.py, "
    "agent_workspace/components/agent_status/src/status.py, and tools/task_context/__init__.py.\n\n"
    "Docker python:3.12-slim runs task_context pytest. Docker ubuntu:24.04 runs Agent Workspace pytest with GTK, VTE, "
    "and Tk dependencies. Docker validation should include tools/task_context/tests/test_task_context.py and "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py.\n\n"
    "Repeated ordinary words should not be accepted when aliases are token-negative. repeated ordinary words like "
    "dictionary, context, validation, settings, compiler, and preview may appear many times. repeated ordinary words "
    "should still be rejected if §00 plus dictionary line costs more than the original text. Long repeated paths and "
    "long repeated config symbols should be accepted because they reduce encoded body and net context size.\n\n"
    "Agent Workspace Dictionary settings should be global, not per task. Agent Workspace Dictionary settings affect "
    "slot compilation, not display rendering. Agent Workspace Dictionary settings include auto discovery, min "
    "occurrences, min saving, min term length, max term words, strip articles, and preview text. Agent Workspace "
    "Dictionary settings must persist through settings.json.\n\n"
    "The compiler should prefer net savings over alias count. The compiler should not overfit to English phrases. "
    "The compiler should avoid encoding path segments after a full path has already been selected. The compiler "
    "should keep dictionary values flat and must not encode aliases inside dictionary values.\n\n"
    "When min occurrences is 2, Agent Workspace may be selected. When min occurrences is 3, "
    "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py should be selected. When min saving is high, fewer "
    "aliases should be selected. When min saving is low, more aliases can be selected if net saving remains positive.\n\n"
    "This sample intentionally repeats Agent Workspace, task_context, task_check, push_guard, "
    "inject_task_context_prompt, TASK_CONTEXT.sqlite3, agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py, "
    "tools/task_context/tests/test_task_context.py, code_map, Docker ubuntu:24.04, Docker python:3.12-slim, and "
    "task dictionary compiler many times so the compiler preview has enough material for calibration."
)


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
    encoded_summary: str = ""
    encoded_details: str = ""
    codec_version: int = DICTIONARY_CODEC_VERSION

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
            encoded_summary=str(data.get("encoded_summary", "")),
            encoded_details=str(data.get("encoded_details", "")),
            codec_version=int(data.get("codec_version", DICTIONARY_CODEC_VERSION)),
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
        if self.encoded_summary and self.encoded_summary != self.summary:
            data["encoded_summary"] = self.encoded_summary
        if self.encoded_details and self.encoded_details != self.details:
            data["encoded_details"] = self.encoded_details
        if self.codec_version != DICTIONARY_CODEC_VERSION:
            data["codec_version"] = self.codec_version
        return data


@dataclass(frozen=True)
class TaskContextSlot:
    category: str
    content: str
    updated_at: str

    def to_json(self) -> dict[str, object]:
        return {
            "category": self.category,
            "content": self.content,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class DictionaryEntry:
    id: int
    value: str
    created_at: str
    status: str = DICTIONARY_STATUS_ACTIVE

    @property
    def token(self) -> str:
        return dictionary_token(self.id)


@dataclass(frozen=True)
class TaskDictionaryPolicy:
    auto_discovery: bool = DICTIONARY_AUTO_DISCOVERY_DEFAULT
    min_occurrences: int = DICTIONARY_MIN_OCCURRENCES
    min_saving: int = DICTIONARY_MIN_SAVING
    min_term_length: int = DICTIONARY_MIN_TERM_LENGTH
    max_term_words: int = DICTIONARY_MAX_TERM_WORDS
    strip_articles: bool = DICTIONARY_STRIP_ARTICLES_DEFAULT


@dataclass(frozen=True)
class DictionaryPreview:
    dictionary: tuple[DictionaryEntry, ...]
    encoded_text: str
    original_tokens: int
    encoded_tokens: int
    dictionary_tokens: int

    @property
    def token_saving(self) -> int:
        return self.original_tokens - self.encoded_tokens

    @property
    def net_token_saving(self) -> int:
        return self.original_tokens - self.encoded_tokens - self.dictionary_tokens


def database_path(task_dir: Path) -> Path:
    return task_database_path(task_dir)


def legacy_journal_path(task_dir: Path) -> Path:
    return task_dir / LEGACY_JOURNAL_FILENAME


def journal_path(task_dir: Path) -> Path:
    return database_path(task_dir)


def ensure_database(task_dir: Path) -> None:
    task_dir = task_dir.resolve()
    if not task_dir.is_dir():
        raise ValueError(f"task directory does not exist: {task_dir}")
    with connect_task_database(task_dir) as connection:
        configure_task_database_schema(connection)
        _create_schema(connection)
        _migrate_legacy_inputs_to_slots(task_dir, connection)


def load_slots(task_dir: Path, categories: Iterable[str] = ()) -> list[TaskContextSlot]:
    task_dir = task_dir.resolve()
    path = database_path(task_dir)
    ensure_database(task_dir)
    selected_categories = _normalized_slot_categories(categories)
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        _migrate_legacy_inputs_to_slots(task_dir, connection)
        if selected_categories:
            placeholders = ",".join("?" for _item in selected_categories)
            rows = connection.execute(
                f"SELECT category, content, updated_at FROM task_context_slots "
                f"WHERE category IN ({placeholders})",
                tuple(selected_categories),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT category, content, updated_at FROM task_context_slots"
            ).fetchall()
    slots = [TaskContextSlot(category=row[0], content=row[1], updated_at=row[2]) for row in rows]
    order = {category: index for index, category in enumerate(SLOT_CATEGORIES)}
    return sorted(slots, key=lambda slot: order.get(slot.category, len(order)))


def set_slot(
    task_dir: Path,
    category: str,
    content: str,
    *,
    updated_at: str | None = None,
) -> TaskContextSlot:
    task_dir = task_dir.resolve()
    if not task_dir.is_dir():
        raise ValueError(f"task directory does not exist: {task_dir}")
    ensure_database(task_dir)
    slot = TaskContextSlot(
        category=_validate_slot_category(category),
        content=content.strip(),
        updated_at=_validate_timestamp(updated_at or datetime.now().astimezone().isoformat(timespec="seconds")),
    )
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        _migrate_legacy_inputs_to_slots(task_dir, connection)
        connection.execute(
            "INSERT INTO task_context_slots (category, content, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(category) DO UPDATE SET content = excluded.content, updated_at = excluded.updated_at",
            (slot.category, slot.content, slot.updated_at),
        )
        _compile_dictionary(connection)
    return slot


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
    ensure_database(task_dir)
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        decoded_summary, summary_terms = _decode_input_aliases(connection, _non_empty(summary, "summary"))
        decoded_details, details_terms = _decode_input_aliases(connection, details.strip())
        entry = ContextEntry(
            timestamp=_validate_timestamp(timestamp or datetime.now().astimezone().isoformat(timespec="seconds")),
            severity=_validate_choice(severity, SEVERITIES, "severity"),
            labels=_normalized_labels(labels),
            status=_validate_choice(status, STATUSES, "status"),
            summary=decoded_summary,
            details=decoded_details,
            source=_normalize_token(source, "source"),
            artifacts=tuple(artifact.strip() for artifact in artifacts if artifact.strip()),
        )
        entry_id = _insert_entry(connection, entry, protected_terms=summary_terms | details_terms)
        _compile_dictionary(connection)
    return replace(entry, id=entry_id)


def load_entries(task_dir: Path) -> list[ContextEntry]:
    path = database_path(task_dir)
    if not path.exists():
        return []
    entries: list[ContextEntry] = []
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        rows = connection.execute(
            "SELECT id, timestamp, severity, labels, status, summary, details, source, artifacts, "
            "original_summary, original_details, encoded_summary, encoded_details, codec_version "
            "FROM context_entries ORDER BY timestamp, id"
        ).fetchall()
        if any(row[13] != DICTIONARY_CODEC_VERSION for row in rows):
            _compile_dictionary(connection)
            rows = connection.execute(
                "SELECT id, timestamp, severity, labels, status, summary, details, source, artifacts, "
                "original_summary, original_details, encoded_summary, encoded_details, codec_version "
                "FROM context_entries ORDER BY timestamp, id"
            ).fetchall()
    for row in rows:
        data = {
            "id": row[0],
            "timestamp": row[1],
            "severity": row[2],
            "labels": json.loads(row[3]),
            "status": row[4],
            "summary": row[9] or row[5],
            "details": row[10] if row[10] is not None else row[6],
            "source": row[7],
            "artifacts": json.loads(row[8]),
            "encoded_summary": row[11] or row[5],
            "encoded_details": row[12] if row[12] is not None else row[6],
            "codec_version": row[13],
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
    label_values = _normalized_labels(labels)
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
    protected_terms_by_id: dict[int, set[str]] = {}
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        decoded_summary = set_summary
        summary_terms: set[str] = set()
        if set_summary is not None:
            decoded_summary, summary_terms = _decode_input_aliases(connection, _non_empty(set_summary, "summary"))
        decoded_details = set_details
        details_terms: set[str] = set()
        if set_details is not None:
            decoded_details, details_terms = _decode_input_aliases(connection, set_details.strip())
        existing_terms = _load_alias_protected_terms(connection, [entry.id for entry in selected if entry.id is not None])
        for entry in selected:
            if entry.id is None:
                continue
            terms = set(existing_terms.get(entry.id, ()))
            terms.update(summary_terms)
            terms.update(details_terms)
            if set_summary is not None or set_details is not None:
                protected_terms_by_id[entry.id] = terms
    updated = [
        _edited_entry(
            entry,
            set_status=set_status,
            set_severity=set_severity,
            set_summary=decoded_summary,
            set_details=decoded_details,
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
    changed_ids = {entry.id for entry in changed if entry.id is not None}
    for entry in updated:
        if entry.id in protected_terms_by_id and entry.id not in changed_ids:
            changed.append(entry)
            changed_ids.add(entry.id)
    if dry_run or not changed:
        return changed
    _update_entries(task_dir, changed, protected_terms_by_id=protected_terms_by_id)
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
        labels = _normalized_labels(set_labels)
    elif clear_labels:
        labels = ()
    if add_labels:
        labels = _unique((*labels, *_normalized_labels(add_labels)))
    if remove_labels:
        remove_values = set(_normalized_labels(remove_labels))
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


def _update_entries(
    task_dir: Path,
    entries: Sequence[ContextEntry],
    *,
    protected_terms_by_id: Mapping[int, set[str]] | None = None,
) -> None:
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        connection.executemany(
            "UPDATE context_entries SET severity = ?, labels = ?, status = ?, summary = ?, "
            "details = ?, source = ?, artifacts = ?, original_summary = ?, original_details = ? WHERE id = ?",
            [
                (
                    entry.severity,
                    json.dumps(list(entry.labels), ensure_ascii=False),
                    entry.status,
                    entry.summary,
                    entry.details,
                    entry.source,
                    json.dumps(list(entry.artifacts), ensure_ascii=False),
                    entry.summary,
                    entry.details,
                    entry.id,
                )
                for entry in entries
                if entry.id is not None
            ],
        )
        if protected_terms_by_id:
            connection.executemany(
                "UPDATE context_entries SET alias_protected_terms = ? WHERE id = ?",
                [
                    (
                        json.dumps(sorted(protected_terms_by_id[entry.id]), ensure_ascii=False),
                        entry.id,
                    )
                    for entry in entries
                    if entry.id is not None and entry.id in protected_terms_by_id
                ],
            )
        _compile_dictionary(connection)


def _delete_entries(task_dir: Path, entries: Sequence[ContextEntry]) -> None:
    ids = [entry.id for entry in entries if entry.id is not None]
    if not ids:
        return
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        placeholders = ",".join("?" for _entry_id_value in ids)
        connection.execute(f"DELETE FROM context_entries WHERE id IN ({placeholders})", ids)
        _compile_dictionary(connection)


def migrate_legacy_journal(task_dir: Path) -> int:
    task_dir = task_dir.resolve()
    legacy_path = legacy_journal_path(task_dir)
    if database_path(task_dir).exists():
        raise ValueError(f"{DATABASE_FILENAME} already exists; migration is not needed")
    if not legacy_path.is_file():
        raise ValueError(f"{LEGACY_JOURNAL_FILENAME} is missing; there is nothing to migrate")
    entries = _load_legacy_entries(task_dir)
    ensure_database(task_dir)
    with connect_task_database(task_dir) as connection:
        for entry in entries:
            _insert_entry(connection, entry)
        _compile_dictionary(connection)
    legacy_path.unlink()
    return len(entries)


def compile_dictionary(task_dir: Path) -> int:
    ensure_database(task_dir)
    with connect_task_database(task_dir) as connection:
        before = len(_load_dictionary(connection))
        _compile_dictionary(connection)
        after = len(_load_dictionary(connection))
    return after - before


def load_dictionary(task_dir: Path) -> list[DictionaryEntry]:
    path = database_path(task_dir)
    if not path.exists():
        return []
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        return _load_dictionary(connection)


def default_dictionary_policy() -> TaskDictionaryPolicy:
    return TaskDictionaryPolicy()


def dictionary_policy_from_mapping(settings: Mapping[str, object]) -> TaskDictionaryPolicy:
    default = default_dictionary_policy()
    return TaskDictionaryPolicy(
        auto_discovery=_bool_mapping_value(settings, "task_dictionary_auto_discovery", default.auto_discovery),
        min_occurrences=_int_mapping_value(settings, "task_dictionary_min_occurrences", default.min_occurrences, 1, 20),
        min_saving=_int_mapping_value(settings, "task_dictionary_min_saving", default.min_saving, 0, 10_000),
        min_term_length=_int_mapping_value(settings, "task_dictionary_min_term_length", default.min_term_length, 1, 200),
        max_term_words=_int_mapping_value(settings, "task_dictionary_max_term_words", default.max_term_words, 1, 20),
        strip_articles=_bool_mapping_value(settings, "task_dictionary_strip_articles", default.strip_articles),
    )


def load_default_dictionary_policy(path: Path | None = None) -> TaskDictionaryPolicy:
    settings_path = path or _agent_workspace_settings_path()
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_dictionary_policy()
    if not isinstance(data, dict):
        return default_dictionary_policy()
    return dictionary_policy_from_mapping(data)


def preview_dictionary_compile(text: str, policy: TaskDictionaryPolicy | None = None) -> DictionaryPreview:
    policy = policy or load_default_dictionary_policy()
    candidates = _profitable_candidates([text], (), policy)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    dictionary = tuple(
        DictionaryEntry(id=index, value=value, created_at=now)
        for index, value in enumerate(candidates)
    )
    encoded_text, _refs = _encode_text(text, dictionary)
    dictionary_text = "\n".join(f"{entry.token} = {entry.value}" for entry in dictionary)
    return DictionaryPreview(
        dictionary=dictionary,
        encoded_text=encoded_text,
        original_tokens=token_count(text),
        encoded_tokens=token_count(encoded_text),
        dictionary_tokens=token_count(dictionary_text),
    )


def add_dictionary_terms(task_dir: Path, values: Iterable[str]) -> int:
    terms = _unique(_non_empty(value, "dictionary value") for value in values)
    if not terms:
        return 0
    ensure_database(task_dir)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with connect_task_database(task_dir) as connection:
        dictionary = _load_dictionary(connection)
        existing_values = {entry.value for entry in dictionary}
        next_id = max((entry.id for entry in dictionary), default=-1) + 1
        added = 0
        for value in terms:
            if value in existing_values:
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO task_dictionary (id, value, created_at, status) VALUES (?, ?, ?, ?)",
                (next_id, value, now, DICTIONARY_STATUS_ACTIVE),
            )
            if cursor.rowcount:
                existing_values.add(value)
                next_id += 1
                added += 1
        _compile_dictionary(connection)
    return added


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
    label_values = {label.casefold() for label in _normalized_labels(labels)}
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


def render_agent_entries(task_dir: Path, entries: Iterable[ContextEntry], *, format_name: str = "markdown") -> str:
    entries = list(entries)
    dictionary = _dictionary_subset(task_dir, entries)
    if format_name == "json":
        return json.dumps(
            {
                "task_dictionary": [
                    {
                        "id": item.id,
                        "token": item.token,
                        "value": item.value,
                        "status": item.status,
                    }
                    for item in dictionary
                ],
                "entries": [_entry_agent_json(entry) for entry in entries],
            },
            ensure_ascii=False,
            indent=2,
        )
    if format_name == "text":
        return _agent_text(dictionary, entries)
    if format_name != "markdown":
        raise ValueError(f"unknown format: {format_name}")
    return _agent_markdown(dictionary, entries)


def render_slots(
    slots: Iterable[TaskContextSlot],
    *,
    format_name: str = "markdown",
    task_dir: Path | None = None,
) -> str:
    slots = list(slots)
    if format_name == "json":
        return json.dumps([slot.to_json() for slot in slots], ensure_ascii=False, indent=2)
    if format_name == "text":
        return "\n\n".join(_slot_text(slot) for slot in slots).rstrip()
    if format_name in {"markdown", "agent"}:
        if format_name == "agent" and task_dir is not None:
            return _encoded_slots_markdown(task_dir, slots)
        return _slots_markdown_cards(slots)
    raise ValueError(f"unknown format: {format_name}")


def agent_visible_slots(slots: Iterable[TaskContextSlot]) -> list[TaskContextSlot]:
    return [slot for slot in slots if slot.category != "legacy"]


def compact_context(
    task_dir: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    severity: str | None = "mid..critical",
    labels: Iterable[str] = (),
    statuses: Iterable[str] = ("active",),
    limit: int = DEFAULT_COMPACT_LIMIT,
    agent_context: bool = False,
) -> str:
    slots = load_slots(task_dir)
    if agent_context:
        return render_slots(agent_visible_slots(slots), format_name="agent", task_dir=task_dir)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# Task Context",
        "",
        f"_Generated from `{DATABASE_FILENAME}` slots at {now}._",
        "",
        render_slots(slots, format_name="markdown", task_dir=task_dir) or "- No task context slots.",
    ]
    return "\n".join(lines)


def _slot_text(slot: TaskContextSlot) -> str:
    content = slot.content or "(empty)"
    return f"{slot.category}\t{slot.updated_at}\n{content}"


def _slot_markdown(slot: TaskContextSlot) -> str:
    title = slot.category.replace("-", " ").title()
    content = slot.content.strip() or "- Empty."
    return f"## {title}\n\n_Updated: {slot.updated_at}_\n\n{content}"


def _slot_markdown_card(slot: TaskContextSlot) -> str:
    title = slot.category.replace("-", " ").title()
    rows = [
        (title, slot.updated_at),
        ("content", slot.content.strip() or "- Empty."),
    ]
    return _ascii_card(rows)


def _slots_markdown_cards(slots: Sequence[TaskContextSlot]) -> str:
    if not slots:
        return ""
    return "```text\n" + "\n\n".join(_slot_markdown_card(slot) for slot in slots) + "\n```"


def _encoded_slots_markdown(task_dir: Path, slots: Sequence[TaskContextSlot]) -> str:
    if not slots:
        return ""
    dictionary = load_dictionary(task_dir)
    encoded_slots: list[TaskContextSlot] = []
    used_refs: set[int] = set()
    for slot in slots:
        encoded_content, refs = _encode_text(slot.content, dictionary)
        used_refs.update(refs)
        encoded_slots.append(replace(slot, content=encoded_content))
    used_dictionary = [entry for entry in dictionary if entry.id in used_refs]
    parts: list[str] = []
    if used_dictionary:
        parts.append("## Task Dictionary\n\n" + "\n".join(f"- `{item.token}` = {item.value}" for item in used_dictionary))
    parts.append(_slots_markdown_cards(encoded_slots))
    return "\n\n".join(parts).rstrip()


def _ascii_card(rows: Iterable[tuple[str, str]]) -> str:
    border = "+" + "-" * (SLOT_MARKDOWN_CARD_WIDTH - 2) + "+"
    lines = [border]
    for label, value in rows:
        if not label and not value:
            continue
        prefix = f"{label:<12} "
        wrapped = _wrap_card_value(value, SLOT_MARKDOWN_CARD_WIDTH - len(prefix) - 4)
        lines.append(_ascii_card_line(prefix + wrapped[0]))
        for part in wrapped[1:]:
            lines.append(_ascii_card_line(" " * len(prefix) + part))
    lines.append(border)
    return "\n".join(lines)


def _ascii_card_line(text: str) -> str:
    width = SLOT_MARKDOWN_CARD_WIDTH - 4
    return f"| {text[:width].ljust(width)} |"


def _wrap_card_value(value: str, width: int) -> list[str]:
    wrapped: list[str] = []
    for raw_line in value.splitlines() or [""]:
        wrapped.extend(textwrap.wrap(raw_line, width=width) or [""])
    return wrapped or [""]


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


def _entry_agent_json(entry: ContextEntry) -> dict[str, object]:
    data = entry.to_json()
    data["summary"] = entry.encoded_summary or entry.summary
    data["details"] = entry.encoded_details or entry.details
    return data


def _entry_agent_text(entry: ContextEntry) -> str:
    labels = ",".join(entry.labels) if entry.labels else "-"
    entry_id = entry.id if entry.id is not None else "-"
    summary = entry.encoded_summary or entry.summary
    return f"{entry_id}\t{entry.timestamp}\t{entry.severity}\t{entry.status}\t{labels}\t{summary}"


def _entry_agent_markdown(entry: ContextEntry) -> str:
    encoded_summary = entry.encoded_summary or entry.summary
    encoded_details = entry.encoded_details or entry.details
    labels = ", ".join(f"`{label}`" for label in entry.labels) if entry.labels else "`unlabeled`"
    entry_id = f"#{entry.id} " if entry.id is not None else ""
    head = f"- **{entry.severity}/{entry.status}** {entry_id}{encoded_summary} ({entry.timestamp}; {labels})"
    parts = [head]
    if encoded_details:
        parts.append(f"  Details: {encoded_details}")
    if entry.artifacts:
        parts.append("  Artifacts: " + ", ".join(f"`{artifact}`" for artifact in entry.artifacts))
    return "\n".join(parts)


def _agent_text(dictionary: Sequence[DictionaryEntry], entries: Sequence[ContextEntry]) -> str:
    lines: list[str] = []
    if dictionary:
        lines.extend(f"{item.token} = {item.value}" for item in dictionary)
        lines.append("")
    lines.extend(_entry_agent_text(entry) for entry in entries)
    return "\n".join(lines)


def _agent_markdown(dictionary: Sequence[DictionaryEntry], entries: Sequence[ContextEntry]) -> str:
    lines = ["## Task Dictionary", ""]
    if dictionary:
        lines.extend(f"- `{item.token}` = {item.value}" for item in dictionary)
    else:
        lines.append("- No dictionary aliases used by this context slice.")
    lines.extend(["", "## Encoded Context", ""])
    if entries:
        lines.extend(_entry_agent_markdown(entry) for entry in entries)
    else:
        lines.append("- No matching context entries.")
    return "\n".join(lines).rstrip()


def _agent_compact_context(task_dir: Path, entries: Sequence[ContextEntry]) -> str:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# Task Context",
        "",
        f"_Generated from `{DATABASE_FILENAME}` at {now}. Encoded for agent use._",
        "",
    ]
    rendered = _agent_markdown(_dictionary_subset(task_dir, entries), entries)
    lines.append(rendered)
    lines.extend(
        [
            "",
            "Aliases are stable task-local dictionary identifiers. Reuse them when reading "
            "encoded context; do not redefine them.",
            "",
        ]
    )
    return "\n".join(lines)


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
        "CREATE TABLE IF NOT EXISTS task_context_slots ("
        "category TEXT PRIMARY KEY, content TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS context_entries ("
        "id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, severity TEXT NOT NULL, "
        "labels TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL, "
        "details TEXT NOT NULL, source TEXT NOT NULL, artifacts TEXT NOT NULL)"
    )
    existing_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(context_entries)").fetchall()
    }
    for column, definition in (
        ("original_summary", "TEXT"),
        ("original_details", "TEXT"),
        ("encoded_summary", "TEXT"),
        ("encoded_details", "TEXT"),
        ("codec_version", f"INTEGER NOT NULL DEFAULT {DICTIONARY_CODEC_VERSION}"),
        ("alias_protected_terms", "TEXT NOT NULL DEFAULT '[]'"),
    ):
        if column not in existing_columns:
            connection.execute(f"ALTER TABLE context_entries ADD COLUMN {column} {definition}")
    connection.execute(
        "UPDATE context_entries SET original_summary = summary "
        "WHERE original_summary IS NULL OR original_summary = ''"
    )
    connection.execute(
        "UPDATE context_entries SET original_details = details "
        "WHERE original_details IS NULL"
    )
    connection.execute(
        "UPDATE context_entries SET encoded_summary = summary "
        "WHERE encoded_summary IS NULL OR encoded_summary = ''"
    )
    connection.execute(
        "UPDATE context_entries SET encoded_details = details "
        "WHERE encoded_details IS NULL"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_timestamp ON context_entries(timestamp)")
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_severity ON context_entries(severity)")
    connection.execute("CREATE INDEX IF NOT EXISTS context_entries_status ON context_entries(status)")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS task_dictionary ("
        "id INTEGER PRIMARY KEY, value TEXT NOT NULL UNIQUE, "
        "created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active')"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS context_entry_dictionary_refs ("
        "entry_id INTEGER NOT NULL, dictionary_id INTEGER NOT NULL, "
        "PRIMARY KEY (entry_id, dictionary_id))"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS context_entry_dictionary_refs_dictionary "
        "ON context_entry_dictionary_refs(dictionary_id)"
    )


def _migrate_legacy_inputs_to_slots(task_dir: Path, connection: sqlite3.Connection) -> None:
    slot_count = connection.execute("SELECT COUNT(*) FROM task_context_slots").fetchone()[0]
    if slot_count:
        return
    sections: list[str] = []
    for filename, title in (("TASK_DESCRIPTION.md", "TASK_DESCRIPTION.md"), ("TASK_CONTEXT.md", "TASK_CONTEXT.md")):
        path = task_dir / filename
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                sections.append(f"## {title}\n\n{content}")
    rows = connection.execute(
        "SELECT id, timestamp, severity, labels, status, summary, details, source, artifacts, "
        "original_summary, original_details "
        "FROM context_entries WHERE status = 'active' ORDER BY timestamp, id"
    ).fetchall()
    if rows:
        sections.append("## Legacy Active Entries\n\n" + "\n\n".join(_legacy_slot_entry_markdown(row) for row in rows))
    if not sections:
        return
    updated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    connection.execute(
        "INSERT INTO task_context_slots (category, content, updated_at) VALUES (?, ?, ?)",
        ("legacy", "\n\n".join(sections), updated_at),
    )


def _legacy_slot_entry_markdown(row: sqlite3.Row | tuple[object, ...]) -> str:
    labels = json.loads(str(row[3]))
    artifacts = json.loads(str(row[8]))
    label_text = ", ".join(f"`{label}`" for label in labels) if labels else "`unlabeled`"
    summary = str(row[9] or row[5])
    details = str(row[10]) if row[10] is not None else str(row[6])
    parts = [
        f"- **{row[2]}/{row[4]}** #{row[0]} {summary} ({row[1]}; {label_text})",
    ]
    if details:
        parts.append(f"  Details: {details}")
    if artifacts:
        parts.append("  Artifacts: " + ", ".join(f"`{artifact}`" for artifact in artifacts))
    return "\n".join(parts)


def _insert_entry(
    connection: sqlite3.Connection,
    entry: ContextEntry,
    *,
    protected_terms: Iterable[str] = (),
) -> int:
    cursor = connection.execute(
        "INSERT INTO context_entries "
        "(timestamp, severity, labels, status, summary, details, source, artifacts, "
        "original_summary, original_details, encoded_summary, encoded_details, codec_version, alias_protected_terms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry.timestamp,
            entry.severity,
            json.dumps(list(entry.labels), ensure_ascii=False),
            entry.status,
            entry.summary,
            entry.details,
            entry.source,
            json.dumps(list(entry.artifacts), ensure_ascii=False),
            entry.summary,
            entry.details,
            entry.encoded_summary or entry.summary,
            entry.encoded_details or entry.details,
            entry.codec_version,
            json.dumps(sorted(set(protected_terms)), ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def dictionary_token(dictionary_id: int) -> str:
    if dictionary_id < 0:
        raise ValueError("dictionary id must not be negative")
    return f"{DICTIONARY_TOKEN_PREFIX}{_base62(dictionary_id).rjust(2, '0')}{DICTIONARY_TOKEN_SUFFIX}"


def dictionary_id_from_token(token: str) -> int:
    token = token.strip()
    if not token.startswith(DICTIONARY_TOKEN_PREFIX) or not token.endswith(DICTIONARY_TOKEN_SUFFIX):
        raise ValueError("dictionary token must use §id form")
    body = token[len(DICTIONARY_TOKEN_PREFIX) :]
    if DICTIONARY_TOKEN_SUFFIX:
        body = body[: -len(DICTIONARY_TOKEN_SUFFIX)]
    return _base62_decode(body)


def _base62(value: int) -> str:
    if value == 0:
        return "0"
    base = len(DICTIONARY_ID_ALPHABET)
    digits: list[str] = []
    while value:
        value, index = divmod(value, base)
        digits.append(DICTIONARY_ID_ALPHABET[index])
    return "".join(reversed(digits))


def _base62_decode(value: str) -> int:
    if not value:
        raise ValueError("dictionary token is empty")
    base = len(DICTIONARY_ID_ALPHABET)
    result = 0
    for char in value:
        index = DICTIONARY_ID_ALPHABET.find(char)
        if index < 0:
            raise ValueError(f"invalid dictionary token character: {char}")
        result = result * base + index
    return result


def _load_dictionary(connection: sqlite3.Connection) -> list[DictionaryEntry]:
    rows = connection.execute(
        "SELECT id, value, created_at, status FROM task_dictionary ORDER BY id"
    ).fetchall()
    return [
        DictionaryEntry(id=int(row[0]), value=str(row[1]), created_at=str(row[2]), status=str(row[3]))
        for row in rows
    ]


def _decode_input_aliases(connection: sqlite3.Connection, text: str) -> tuple[str, set[str]]:
    dictionary = {entry.id: entry.value for entry in _load_dictionary(connection)}
    used_values: set[str] = set()
    unknown_tokens: list[str] = []

    def replace_match(match: re.Match[str]) -> str:
        token = match.group(0)
        dictionary_id = dictionary_id_from_token(token)
        value = dictionary.get(dictionary_id)
        if value is None:
            unknown_tokens.append(token)
            return token
        used_values.add(value)
        return value

    decoded = DICTIONARY_TOKEN_RE.sub(replace_match, text)
    if unknown_tokens:
        raise ValueError(f"unknown dictionary alias: {', '.join(_unique(unknown_tokens))}")
    return decoded, used_values


def _load_alias_protected_terms(connection: sqlite3.Connection, entry_ids: Iterable[int]) -> dict[int, tuple[str, ...]]:
    ids = [entry_id for entry_id in entry_ids if entry_id is not None]
    if not ids:
        return {}
    placeholders = ",".join("?" for _entry_id_value in ids)
    rows = connection.execute(
        f"SELECT id, alias_protected_terms FROM context_entries WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    result: dict[int, tuple[str, ...]] = {}
    for row in rows:
        try:
            values = json.loads(row[1] or "[]")
        except json.JSONDecodeError:
            values = []
        if isinstance(values, list):
            result[int(row[0])] = tuple(str(value) for value in values if str(value).strip())
        else:
            result[int(row[0])] = ()
    return result


def _dictionary_subset(task_dir: Path, entries: Sequence[ContextEntry]) -> list[DictionaryEntry]:
    entry_ids = [entry.id for entry in entries if entry.id is not None]
    if not entry_ids:
        return []
    with connect_task_database(task_dir) as connection:
        _create_schema(connection)
        placeholders = ",".join("?" for _entry_id_value in entry_ids)
        rows = connection.execute(
            "SELECT DISTINCT d.id, d.value, d.created_at, d.status "
            "FROM task_dictionary d "
            "JOIN context_entry_dictionary_refs r ON r.dictionary_id = d.id "
            f"WHERE r.entry_id IN ({placeholders}) "
            "ORDER BY d.id",
            entry_ids,
        ).fetchall()
    return [
        DictionaryEntry(id=int(row[0]), value=str(row[1]), created_at=str(row[2]), status=str(row[3]))
        for row in rows
    ]


def _compile_dictionary(connection: sqlite3.Connection, policy: TaskDictionaryPolicy | None = None) -> None:
    policy = policy or load_default_dictionary_policy()
    _create_schema(connection)
    rows = connection.execute(
        "SELECT id, original_summary, original_details, alias_protected_terms "
        "FROM context_entries ORDER BY timestamp, id"
    ).fetchall()
    slot_rows = connection.execute(
        "SELECT category, content FROM task_context_slots ORDER BY category"
    ).fetchall()
    corpus = [str(row[1] or "") for row in rows]
    corpus.extend(str(row[2] or "") for row in rows)
    corpus.extend(str(row[0] or "") for row in slot_rows)
    corpus.extend(str(row[1] or "") for row in slot_rows)
    protected_values: set[str] = set()
    for row in rows:
        try:
            values = json.loads(row[3] or "[]")
        except json.JSONDecodeError:
            values = []
        if isinstance(values, list):
            protected_values.update(str(value) for value in values if str(value).strip())
    dictionary = _load_dictionary(connection)
    existing_values = {entry.value for entry in dictionary}
    # Dictionary ids are durable task-local identities. The compiler only appends
    # new values and never deletes, rewrites, or reuses old ids.
    next_id = max((entry.id for entry in dictionary), default=-1) + 1
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for value in _profitable_candidates(corpus, dictionary, policy, protected_values=protected_values):
        if value in existing_values:
            continue
        cursor = connection.execute(
            "INSERT OR IGNORE INTO task_dictionary (id, value, created_at, status) VALUES (?, ?, ?, ?)",
            (next_id, value, now, DICTIONARY_STATUS_ACTIVE),
        )
        if cursor.rowcount:
            existing_values.add(value)
            next_id += 1
    dictionary = _load_dictionary(connection)
    compiled_rows = []
    refs: list[tuple[int, int]] = []
    for row in rows:
        entry_id = int(row[0])
        encoded_summary, summary_refs = _encode_text(str(row[1] or ""), dictionary)
        encoded_details, details_refs = _encode_text(str(row[2] or ""), dictionary)
        compiled_rows.append((encoded_summary, encoded_details, DICTIONARY_CODEC_VERSION, entry_id))
        refs.extend((entry_id, dictionary_id) for dictionary_id in sorted(summary_refs | details_refs))
    connection.executemany(
        "UPDATE context_entries SET encoded_summary = ?, encoded_details = ?, codec_version = ? WHERE id = ?",
        compiled_rows,
    )
    connection.execute("DELETE FROM context_entry_dictionary_refs")
    connection.executemany(
        "INSERT OR IGNORE INTO context_entry_dictionary_refs (entry_id, dictionary_id) VALUES (?, ?)",
        refs,
    )


def _profitable_candidates(
    corpus: Sequence[str],
    dictionary: Sequence[DictionaryEntry],
    policy: TaskDictionaryPolicy,
    *,
    protected_values: Iterable[str] = (),
) -> list[str]:
    if not policy.auto_discovery:
        return []
    text = "\n".join(corpus)
    known = {entry.value for entry in dictionary}
    protected = {value for value in protected_values if value}
    raw_candidates: set[str] = set()
    for pattern in TECHNICAL_PATTERNS:
        raw_candidates.update(match.group(0) for match in pattern.finditer(text))
    raw_candidates.update(_repeated_word_candidates(text, policy))
    raw_candidates.update(_repeated_phrase_candidates(text, policy))
    candidates = {
        value
        for value in (_normalize_candidate(candidate, policy) for candidate in raw_candidates)
        if (
            value
            and value not in known
            and not _looks_like_noise(value, policy)
            and not _candidate_crosses_protected_value(value, protected)
        )
    }
    result: list[str] = []
    blocked = set(known)
    encoded_probe = text
    while candidates:
        token = dictionary_token(len(dictionary) + len(result))
        scored: list[tuple[float, int, int, str]] = []
        for value in candidates - blocked:
            occurrences = _count_occurrences(encoded_probe, value)
            if occurrences < policy.min_occurrences:
                continue
            saving = _candidate_net_saving(value, token, occurrences)
            if saving < policy.min_saving:
                continue
            priority = _candidate_priority(value, saving, occurrences, encoded_probe, candidates)
            scored.append((priority, saving, len(value), value))
        if not scored:
            break
        _priority, _saving, _length, value = max(scored, key=lambda item: (item[0], item[1], item[2], item[3]))
        result.append(value)
        blocked.add(value)
        candidates.remove(value)
        encoded_probe = _replacement_pattern(value).sub(token, encoded_probe)
    return result


def _ranked_candidates(values: Iterable[str]) -> list[str]:
    unique_values = _unique(value for value in values if value)
    return sorted(unique_values, key=lambda value: (-len(value), value.casefold()))


def _repeated_word_candidates(text: str, policy: TaskDictionaryPolicy) -> set[str]:
    candidates: set[str] = set()
    for match in REPEATED_WORD_RE.finditer(text):
        value = match.group(0)
        if len(value) >= policy.min_term_length:
            candidates.add(value)
    return candidates


def _repeated_phrase_candidates(text: str, policy: TaskDictionaryPolicy) -> set[str]:
    if policy.max_term_words < 2:
        return set()
    matches = list(REPEATED_WORD_RE.finditer(text))
    candidates: set[str] = set()
    for index in range(len(matches)):
        words = [matches[index].group(0)]
        previous_end = matches[index].end()
        for next_match in matches[index + 1 : index + policy.max_term_words]:
            separator = text[previous_end : next_match.start()]
            if not separator or not separator.isspace():
                break
            words.append(next_match.group(0))
            previous_end = next_match.end()
            value = " ".join(words)
            if len(value) >= policy.min_term_length and _phrase_candidate_allowed(words, policy):
                candidates.add(value)
    return candidates


def _phrase_candidate_allowed(words: Sequence[str], policy: TaskDictionaryPolicy) -> bool:
    if len(words) < 2:
        return False
    if any(word.casefold() in ARTICLE_WORDS or len(word) < 4 for word in words):
        return False
    if any(_term_like_word(word) for word in words):
        return all(_term_like_word(word) or len(word) >= policy.min_term_length for word in words)
    return all(len(word) >= policy.min_term_length for word in words)


def _term_like_word(word: str) -> bool:
    return any(char in word for char in "_-.") or word[:1].isupper()


def _normalize_candidate(value: str, policy: TaskDictionaryPolicy) -> str:
    value = " ".join(value.strip().split())
    if policy.strip_articles:
        value = ARTICLE_RE.sub("", value)
    value = value.strip(".,;:[]{}")
    return value


def _looks_like_noise(value: str, policy: TaskDictionaryPolicy) -> bool:
    if len(value) < policy.min_term_length:
        return True
    if DICTIONARY_TOKEN_RE.search(value):
        return True
    words = value.split()
    if len(words) > 1 and any(word.casefold() in ARTICLE_WORDS for word in words):
        return True
    return len(words) > policy.max_term_words


def _candidate_crosses_protected_value(value: str, protected_values: set[str]) -> bool:
    for protected in protected_values:
        if value == protected:
            continue
        if protected in value:
            return True
    return False


def _count_occurrences(text: str, value: str) -> int:
    return len(_replacement_pattern(value).findall(text))


def _candidate_net_saving(value: str, token: str, occurrences: int) -> int:
    body_saving = occurrences * (token_count(value) - token_count(token))
    dictionary_cost = token_count(f"{token} = {value}")
    return body_saving - dictionary_cost


def _candidate_priority(
    value: str,
    saving: int,
    occurrences: int,
    text: str,
    candidates: set[str],
) -> float:
    words = value.split()
    word_count = max(1, len(words))
    term_like_count = sum(1 for word in words if _term_like_word(word))
    length_bonus = 1.0 + min(0.6, 0.12 * (word_count - 1))
    term_bonus = 1.0 + min(0.25, 0.05 * term_like_count)
    nested_ratio = _nested_candidate_ratio(value, occurrences, text, candidates)
    nested_penalty = 1.0 - (0.45 * nested_ratio)
    return saving * length_bonus * term_bonus * nested_penalty


def _nested_candidate_ratio(value: str, occurrences: int, text: str, candidates: set[str]) -> float:
    if occurrences <= 0:
        return 0.0
    nested_occurrences = 0
    for candidate in candidates:
        if len(candidate) <= len(value) or value not in candidate:
            continue
        if not _replacement_pattern(value).search(candidate):
            continue
        nested_occurrences = max(nested_occurrences, _count_occurrences(text, candidate))
    return min(1.0, nested_occurrences / occurrences)


def _encode_text(text: str, dictionary: Sequence[DictionaryEntry]) -> tuple[str, set[int]]:
    used: set[int] = set()
    encoded = text
    for entry in sorted(dictionary, key=lambda item: (-len(item.value), item.id)):
        pattern = _replacement_pattern(entry.value)

        def replace_match(_match: re.Match[str]) -> str:
            used.add(entry.id)
            return entry.token

        encoded = pattern.sub(replace_match, encoded)
    return encoded, used


def _replacement_pattern(value: str) -> re.Pattern[str]:
    escaped = re.escape(value)
    prefix = r"(?<![A-Za-z0-9_\[])"
    suffix = r"(?![A-Za-z0-9_(])" if not value.endswith("()") else r"(?![A-Za-z0-9_])"
    article = r"(?:(?:the|a|an)\s+)?" if " " in value else ""
    return re.compile(prefix + article + escaped + suffix)


def _agent_workspace_settings_path() -> Path:
    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE
    return Path.home() / ".config" / "agent_tools" / "agent_workspace" / AGENT_WORKSPACE_SETTINGS_FILE


def _bool_mapping_value(settings: Mapping[str, object], key: str, default: bool) -> bool:
    value = settings.get(key)
    return value if isinstance(value, bool) else default


def _int_mapping_value(settings: Mapping[str, object], key: str, default: int, minimum: int, maximum: int) -> int:
    value = settings.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        return default
    return max(minimum, min(maximum, value))


def token_count(text: str) -> int:
    encoding = _tokenizer_encoding()
    if encoding is None:
        return _rough_token_count(text)
    return len(encoding.encode(text))


def _tokenizer_encoding() -> Any | None:
    global _TOKENIZER_ENCODING_CACHE
    global _TOKENIZER_IMPORT_FAILED
    if _TOKENIZER_ENCODING_CACHE is not None:
        return _TOKENIZER_ENCODING_CACHE
    if _TOKENIZER_IMPORT_FAILED:
        return None
    try:
        import tiktoken
    except ImportError:
        _TOKENIZER_IMPORT_FAILED = True
        return None
    model = os.environ.get(TOKENIZER_MODEL_ENV)
    if model:
        try:
            _TOKENIZER_ENCODING_CACHE = tiktoken.encoding_for_model(model)
            return _TOKENIZER_ENCODING_CACHE
        except KeyError:
            pass
    encoding_name = os.environ.get(TOKENIZER_ENCODING_ENV, TOKENIZER_ENCODING)
    try:
        _TOKENIZER_ENCODING_CACHE = tiktoken.get_encoding(encoding_name)
    except Exception:
        _TOKENIZER_IMPORT_FAILED = True
        return None
    return _TOKENIZER_ENCODING_CACHE


def _rough_token_count(text: str) -> int:
    lexical_tokens = len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))
    char_tokens = (len(text) + 3) // 4
    return max(lexical_tokens, char_tokens)


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


def _normalized_labels(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(_validate_choice(label, LABELS, "label") for label in _normalized_tokens(values, "label"))


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


def _validate_slot_category(value: str) -> str:
    return _validate_choice(value, SLOT_CATEGORIES, "category")


def _normalized_slot_categories(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(_unique(_validate_slot_category(value) for value in values if value.strip()))


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
    categories = _split_csv(args.category) + _split_csv(args.cats)
    rendered = render_slots(load_slots(args.task, categories), format_name=args.format, task_dir=args.task)
    if rendered:
        print(rendered)
    return 0


def slot_command(args: argparse.Namespace) -> int:
    slot = set_slot(args.task, args.category, args.content or "", updated_at=args.updated_at)
    print(render_slots([slot], format_name=args.format, task_dir=args.task))
    return 0


def compile_command(args: argparse.Namespace) -> int:
    added = compile_dictionary(args.task)
    print(f"task-context: compiled dictionary, added {added} aliases")
    return 0


def dictionary_command(args: argparse.Namespace) -> int:
    if args.add:
        added = add_dictionary_terms(args.task, args.add)
        print(f"task-context: added {added} dictionary aliases")
        return 0
    dictionary = load_dictionary(args.task)
    if args.format == "json":
        print(
            json.dumps(
                [
                    {
                        "id": item.id,
                        "token": item.token,
                        "value": item.value,
                        "created_at": item.created_at,
                        "status": item.status,
                    }
                    for item in dictionary
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    for item in dictionary:
        print(f"{item.token}\t{item.status}\t{item.value}")
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
        "agent_context": args.agent_context,
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

    compile_parser = subparsers.add_parser("compile", help="Recompile encoded context and task dictionary.")
    compile_parser.add_argument("--task", type=Path, required=True)
    compile_parser.set_defaults(func=compile_command)

    dictionary_parser = subparsers.add_parser("dictionary", help="Print the persistent task dictionary.")
    dictionary_parser.add_argument("--task", type=Path, required=True)
    dictionary_parser.add_argument("--format", choices=("text", "json"), default="text")
    dictionary_parser.add_argument("--add", action="append", default=[], help="Append a stable dictionary term.")
    dictionary_parser.set_defaults(func=dictionary_command)

    query_parser = subparsers.add_parser("query", help="Query current task context slots.")
    query_parser.add_argument("--task", type=Path, required=True)
    query_parser.add_argument("--category", action="append", default=[])
    query_parser.add_argument("--cats", action="append", default=[], help="Comma-separated category list.")
    query_parser.add_argument("--format", choices=("text", "markdown", "json", "agent"), default="text")
    query_parser.set_defaults(func=query_command)

    slot_parser = subparsers.add_parser("slot", help="Create or replace one current task context slot.")
    slot_parser.add_argument("--task", type=Path, required=True)
    slot_parser.add_argument("--category", choices=SLOT_CATEGORIES, required=True)
    slot_parser.add_argument("--content", default="")
    slot_parser.add_argument("--updated-at")
    slot_parser.add_argument("--format", choices=("text", "markdown", "json", "agent"), default="markdown")
    slot_parser.set_defaults(func=slot_command)

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
    compact_parser.add_argument("--agent-context", action="store_true")
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
