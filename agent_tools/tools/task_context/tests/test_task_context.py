from __future__ import annotations

import json
from pathlib import Path

from agent_tools.tools.task_context import CONTEXT_FILENAME
from agent_tools.tools.task_context import JOURNAL_FILENAME
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import compact_context
from agent_tools.tools.task_context import filter_entries
from agent_tools.tools.task_context import load_entries
from agent_tools.tools.task_context import main
from agent_tools.tools.task_context import render_entries
from agent_tools.tools.task_context import write_compact_context


def test_add_entry_writes_jsonl_with_metadata(tmp_path: Path) -> None:
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
    lines = (tmp_path / JOURNAL_FILENAME).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["severity"] == "high"
    assert data["labels"] == ["validation", "build-info"]
    assert data["artifacts"] == ["report/validation/latest.json"]


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
    assert "**note/active**" in render_entries(entries, format_name="markdown")
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

    assert main(["compact", "--task", str(tmp_path), "--print"]) == 0
    compact_output = capsys.readouterr().out
    assert "Build validation passed" in compact_output
    assert (tmp_path / CONTEXT_FILENAME).is_file()
