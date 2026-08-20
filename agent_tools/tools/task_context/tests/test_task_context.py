from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.task_context import CONTEXT_FILENAME
from agent_tools.tools.task_context import DATABASE_FILENAME
from agent_tools.tools.task_context import LEGACY_JOURNAL_FILENAME
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import compact_context
from agent_tools.tools.task_context import edit_entries
from agent_tools.tools.task_context import filter_entries
from agent_tools.tools.task_context import load_entries
from agent_tools.tools.task_context import main
from agent_tools.tools.task_context import migrate_legacy_journal
from agent_tools.tools.task_context import render_entries
from agent_tools.tools.task_context import write_compact_context


def test_add_entry_writes_sqlite_with_metadata(tmp_path: Path) -> None:
    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:30:00+03:00",
        severity="high",
        labels=("validation", "build info"),
        status="active",
        summary="Docker validation passed",
        details="195 tests passed.",
        source="agent",
        artifacts=("report/validation/latest.json",),
    )

    assert entry.labels == ("validation", "build-info")
    assert (tmp_path / DATABASE_FILENAME).is_file()
    data = load_entries(tmp_path)[0].to_json()
    assert data["severity"] == "high"
    assert data["labels"] == ["validation", "build-info"]
    assert data["artifacts"] == ["report/validation/latest.json"]
    assert isinstance(data["id"], int)


def test_add_entry_rejects_invalid_timestamp(tmp_path: Path) -> None:
    try:
        add_entry(tmp_path, timestamp="not-a-date", severity="mid", summary="Invalid")
    except ValueError as exc:
        assert str(exc) == "timestamp must be an ISO-8601 date-time"
    else:
        raise AssertionError("invalid timestamp was accepted")


def test_migration_rejects_invalid_timestamp(tmp_path: Path) -> None:
    (tmp_path / LEGACY_JOURNAL_FILENAME).write_text(
        '{"severity":"mid","summary":"Invalid","timestamp":"not-a-date"}\n',
        encoding="utf-8",
    )

    try:
        migrate_legacy_journal(tmp_path)
    except ValueError as exc:
        assert f"{LEGACY_JOURNAL_FILENAME}:1" in str(exc)
        assert "timestamp must be an ISO-8601 date-time" in str(exc)
    else:
        raise AssertionError("invalid timestamp was accepted")


def test_query_filters_by_date_severity_label_and_status(tmp_path: Path) -> None:
    add_entry(
        tmp_path,
        timestamp="2026-08-17T08:00:00",
        severity="low",
        labels=("validation",),
        status="active",
        summary="Old low note",
    )
    add_entry(
        tmp_path,
        timestamp="2026-08-18T09:00:00",
        severity="critical",
        labels=("validation", "blocker"),
        status="resolved",
        summary="Resolved blocker",
    )
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("validation", "build"),
        status="active",
        summary="Current validation failure",
    )

    entries = filter_entries(
        load_entries(tmp_path),
        since="2026-08-18",
        severity="mid..critical",
        labels=("validation",),
        statuses=("active",),
    )

    assert [entry.summary for entry in entries] == ["Current validation failure"]

    newest_first_entries = filter_entries(load_entries(tmp_path), newest_first=True)

    assert [entry.summary for entry in newest_first_entries] == [
        "Current validation failure",
        "Resolved blocker",
        "Old low note",
    ]

    selected_severity_entries = filter_entries(load_entries(tmp_path), severity=("low", "critical"))

    assert [entry.summary for entry in selected_severity_entries] == ["Old low note", "Resolved blocker"]


def test_edit_entries_batches_status_labels_artifacts_and_delete(tmp_path: Path) -> None:
    old = add_entry(
        tmp_path,
        timestamp="2026-08-17T08:00:00",
        severity="mid",
        labels=("validation",),
        status="active",
        summary="Old validation",
        artifacts=("report/old.json",),
    )
    current = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("validation", "build"),
        status="active",
        summary="Current validation",
    )

    changed = edit_entries(
        tmp_path,
        labels=("validation",),
        until="2026-08-18",
        set_status="resolved",
        set_severity="low",
        add_labels=("superseded",),
        remove_artifacts=("report/old.json",),
    )

    assert [entry.id for entry in changed] == [old.id]
    entries = load_entries(tmp_path)
    old_entry = next(entry for entry in entries if entry.id == old.id)
    current_entry = next(entry for entry in entries if entry.id == current.id)
    assert old_entry.status == "resolved"
    assert old_entry.severity == "low"
    assert old_entry.labels == ("validation", "superseded")
    assert old_entry.artifacts == ()
    assert current_entry.status == "active"

    deleted = edit_entries(tmp_path, ids=(old.id,), delete=True)

    assert [entry.id for entry in deleted] == [old.id]
    assert [entry.id for entry in load_entries(tmp_path)] == [current.id]


def test_edit_entries_requires_selector_and_operation(tmp_path: Path) -> None:
    add_entry(tmp_path, timestamp="2026-08-19T10:00:00", severity="mid", summary="Current")

    try:
        edit_entries(tmp_path, set_status="resolved")
    except ValueError as exc:
        assert "without --all, --id, or a non-status filter" in str(exc)
    else:
        raise AssertionError("edit without selector was accepted")

    try:
        edit_entries(tmp_path, all_entries=True)
    except ValueError as exc:
        assert "no edit operation" in str(exc)
    else:
        raise AssertionError("edit without operation was accepted")


def test_compact_context_writes_active_high_signal_markdown(tmp_path: Path) -> None:
    add_entry(
        tmp_path,
        timestamp="2026-08-18T09:00:00",
        severity="critical",
        labels=("blocker",),
        status="resolved",
        summary="Old blocker",
    )
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="mid",
        labels=("decision",),
        status="active",
        summary="Use journal as source of truth",
        details="TASK_CONTEXT.md stays compact.",
    )

    content = write_compact_context(tmp_path, severity="mid..critical")

    assert (tmp_path / CONTEXT_FILENAME).read_text(encoding="utf-8") == content
    assert "Use journal as source of truth" in content
    assert "TASK_CONTEXT.md stays compact." in content
    assert "Old blocker" not in content


def test_render_entries_supports_text_markdown_and_json(tmp_path: Path) -> None:
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="note",
        labels=("env",),
        status="active",
        summary="Host has package installed",
    )
    entries = load_entries(tmp_path)

    assert "Host has package installed" in render_entries(entries)
    assert render_entries(entries).split("\t", 1)[0].isdigit()
    assert "**note/active**" in render_entries(entries, format_name="markdown")
    assert "#1 Host has package installed" in render_entries(entries, format_name="markdown")
    assert json.loads(render_entries(entries, format_name="json"))[0]["labels"] == ["env"]


def test_cli_add_query_and_compact(tmp_path: Path, capsys: object) -> None:
    assert (
        main(
            [
                "add",
                "--task",
                str(tmp_path),
                "--timestamp",
                "2026-08-19T10:00:00",
                "--severity",
                "high",
                "--label",
                "validation,build",
                "Build validation passed",
            ]
        )
        == 0
    )
    assert main(["query", "--task", str(tmp_path), "--label", "validation", "--format", "markdown"]) == 0
    query_output = capsys.readouterr().out
    assert "Build validation passed" in query_output

    assert main(["query", "--task", str(tmp_path), "--newest-first"]) == 0
    newest_first_output = capsys.readouterr().out
    assert "Build validation passed" in newest_first_output

    assert main(["compact", "--task", str(tmp_path), "--print"]) == 0
    compact_output = capsys.readouterr().out
    assert "Build validation passed" in compact_output
    assert (tmp_path / CONTEXT_FILENAME).is_file()


def test_cli_edit_dry_run_update_and_delete(tmp_path: Path, capsys: object) -> None:
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("validation",),
        status="active",
        summary="Build validation passed",
    )

    assert (
        main(
            [
                "edit",
                "--task",
                str(tmp_path),
                "--label",
                "validation",
                "--set-status",
                "resolved",
                "--add-label",
                "superseded",
                "--dry-run",
            ]
        )
        == 0
    )
    dry_run_output = capsys.readouterr().out
    assert "would edit 1 entries" in dry_run_output
    assert load_entries(tmp_path)[0].status == "active"

    assert (
        main(
            [
                "edit",
                "--task",
                str(tmp_path),
                "--label",
                "validation",
                "--set-status",
                "resolved",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )
    dry_run_json = json.loads(capsys.readouterr().out)
    assert dry_run_json["action"] == "would edit"
    assert dry_run_json["count"] == 1

    assert (
        main(
            [
                "edit",
                "--task",
                str(tmp_path),
                "--label",
                "validation",
                "--set-status",
                "resolved",
                "--add-label",
                "superseded",
            ]
        )
        == 0
    )
    edit_output = capsys.readouterr().out
    assert "edited 1 entries" in edit_output
    edited_entry = load_entries(tmp_path)[0]
    assert edited_entry.status == "resolved"
    assert edited_entry.labels == ("validation", "superseded")

    assert main(["edit", "--task", str(tmp_path), "--id", str(edited_entry.id), "--delete"]) == 0
    delete_output = capsys.readouterr().out
    assert "deleted 1 entries" in delete_output
    assert load_entries(tmp_path) == []
