from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

from agent_tools.tools.task_context import DATABASE_FILENAME
from agent_tools.tools.task_context import DICTIONARY_CODEC_VERSION
from agent_tools.tools.task_context import DICTIONARY_PREVIEW_TEXT
from agent_tools.tools.task_context import LEGACY_JOURNAL_FILENAME
from agent_tools.tools.task_context import TaskDictionaryPolicy
from agent_tools.tools.task_context import add_entry
from agent_tools.tools.task_context import add_dictionary_terms
from agent_tools.tools.task_context import compact_context
from agent_tools.tools.task_context import dictionary_token
from agent_tools.tools.task_context import edit_entries
from agent_tools.tools.task_context import filter_entries
from agent_tools.tools.task_context import load_dictionary
from agent_tools.tools.task_context import load_entries
from agent_tools.tools.task_context import main
from agent_tools.tools.task_context import migrate_legacy_journal
from agent_tools.tools.task_context import preview_dictionary_compile
from agent_tools.tools.task_context import render_agent_entries
from agent_tools.tools.task_context import render_entries
from agent_tools.tools.task_context import load_slots
from agent_tools.tools.task_context import set_slot
from agent_tools.tools.task_context import token_count
import agent_tools.tools.task_context as task_context_module
from agent_tools.tools.task_context import _candidate_net_saving


def test_add_entry_writes_sqlite_with_metadata(tmp_path: Path) -> None:
    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:30:00+03:00",
        severity="high",
        labels=("validation", "build"),
        status="active",
        summary="Docker validation passed",
        details="195 tests passed.",
        source="agent",
        artifacts=("report/validation/latest.json",),
    )

    assert entry.labels == ("validation", "build")
    assert (tmp_path / DATABASE_FILENAME).is_file()
    data = load_entries(tmp_path)[0].to_json()
    assert data["severity"] == "high"
    assert data["labels"] == ["validation", "build"]
    assert data["artifacts"] == ["report/validation/latest.json"]
    assert isinstance(data["id"], int)


def test_add_entry_rejects_invalid_timestamp(tmp_path: Path) -> None:
    try:
        add_entry(tmp_path, timestamp="not-a-date", severity="mid", summary="Invalid")
    except ValueError as exc:
        assert str(exc) == "timestamp must be an ISO-8601 date-time"
    else:
        raise AssertionError("invalid timestamp was accepted")


def test_add_entry_rejects_unknown_label(tmp_path: Path) -> None:
    try:
        add_entry(tmp_path, severity="mid", labels=("surprise-label",), summary="Invalid label")
    except ValueError as exc:
        assert "label must be one of:" in str(exc)
    else:
        raise AssertionError("unknown label was accepted")


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

    try:
        filter_entries(load_entries(tmp_path), labels=("surprise-label",))
    except ValueError as exc:
        assert "label must be one of:" in str(exc)
    else:
        raise AssertionError("unknown label filter was accepted")

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


def test_compact_context_renders_active_high_signal_markdown(tmp_path: Path) -> None:
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
        details="Only active sqlite entries are rendered.",
    )

    content = compact_context(tmp_path, severity="mid..critical")

    assert "Use journal as source of truth" in content
    assert "Only active sqlite entries are rendered." in content
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


def test_dictionary_tokens_use_base62_with_two_character_minimum() -> None:
    assert dictionary_token(0) == "§00"
    assert dictionary_token(1) == "§01"
    assert dictionary_token(10) == "§0a"
    assert dictionary_token(61) == "§0Z"
    assert dictionary_token(62) == "§10"


def test_load_entries_recompiles_old_dictionary_codec(tmp_path: Path) -> None:
    repeated = "drivers/firmware/scmi/scmi.c"
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{repeated} starts early",
        details=f"{repeated} calls scmi_send_message() before {repeated} is ready.",
    )

    with sqlite3.connect(tmp_path / DATABASE_FILENAME) as connection:
        connection.execute(
            "UPDATE context_entries SET encoded_summary = ?, encoded_details = ?, codec_version = ?",
            ("[00] starts early", "[00] records old encoded text.", 1),
        )

    agent_context = render_agent_entries(tmp_path, load_entries(tmp_path), format_name="markdown")

    assert "§00" in agent_context
    assert "[00]" not in _encoded_context_body(agent_context)
    with sqlite3.connect(tmp_path / DATABASE_FILENAME) as connection:
        codec_versions = {row[0] for row in connection.execute("SELECT codec_version FROM context_entries")}
    assert codec_versions == {DICTIONARY_CODEC_VERSION}


def _encoded_context_body(agent_context: str) -> str:
    return agent_context.split("## Encoded Context", 1)[1]


def test_dictionary_compiler_keeps_decoded_default_and_agent_subset(tmp_path: Path) -> None:
    repeated = "drivers/firmware/scmi/scmi.c"
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{repeated} sends SCMI messages",
        details=f"{repeated} calls scmi_send_message() before {repeated} is ready.",
    )
    add_entry(
        tmp_path,
        timestamp="2026-08-19T11:00:00",
        severity="mid",
        labels=("decision",),
        summary=f"Keep {repeated} as the source of truth",
    )

    entries = load_entries(tmp_path)
    dictionary = load_dictionary(tmp_path)

    assert dictionary
    assert dictionary[0].id == 0
    assert dictionary[0].token == "§00"
    assert repeated in render_entries(entries, format_name="markdown")
    agent_context = render_agent_entries(tmp_path, entries, format_name="markdown")
    assert "## Task Dictionary" in agent_context
    assert f"`§00` = {dictionary[0].value}" in agent_context
    assert "§00" in agent_context
    assert repeated in agent_context
    assert repeated not in _encoded_context_body(agent_context)


def test_add_entry_decodes_input_aliases_before_saving_original_fields(tmp_path: Path) -> None:
    add_dictionary_terms(tmp_path, ("Agent Workspace", "TASK_CONTEXT.sqlite3"))

    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("decision",),
        summary="§00 reads §01",
        details="§00 keeps §01 readable.",
    )
    loaded = load_entries(tmp_path)[0]
    decoded = render_entries([loaded], format_name="markdown")
    encoded = render_agent_entries(tmp_path, [loaded], format_name="markdown")

    assert entry.summary == "Agent Workspace reads TASK_CONTEXT.sqlite3"
    assert entry.details == "Agent Workspace keeps TASK_CONTEXT.sqlite3 readable."
    assert loaded.summary == entry.summary
    assert "§00" not in decoded
    assert "§01" not in decoded
    assert "§00 reads §01" in encoded
    assert "§00 keeps §01 readable." in encoded


def test_add_entry_rejects_unknown_input_alias(tmp_path: Path) -> None:
    add_dictionary_terms(tmp_path, ("Agent Workspace",))

    try:
        add_entry(tmp_path, severity="high", summary="§zz should fail")
    except ValueError as exc:
        assert "unknown dictionary alias: §zz" in str(exc)
    else:
        raise AssertionError("unknown dictionary alias was accepted")


def test_edit_entries_decodes_input_aliases_before_saving_original_fields(tmp_path: Path) -> None:
    add_dictionary_terms(tmp_path, ("Agent Workspace", "TASK_CONTEXT.sqlite3"))
    entry = add_entry(tmp_path, timestamp="2026-08-19T10:00:00", severity="mid", summary="Initial")

    changed = edit_entries(tmp_path, ids=(entry.id,), set_details="§00 updates §01")
    loaded = load_entries(tmp_path)[0]

    assert changed[0].details == "Agent Workspace updates TASK_CONTEXT.sqlite3"
    assert loaded.details == "Agent Workspace updates TASK_CONTEXT.sqlite3"
    assert "§00 updates §01" in render_agent_entries(tmp_path, [loaded], format_name="markdown")


def test_edit_entries_records_alias_protection_when_decoded_text_is_unchanged(tmp_path: Path) -> None:
    add_dictionary_terms(tmp_path, ("Agent Workspace", "TASK_CONTEXT.sqlite3"))
    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="mid",
        summary="Agent Workspace backend reads TASK_CONTEXT.sqlite3",
    )

    changed = edit_entries(tmp_path, ids=(entry.id,), set_summary="§00 backend reads §01")

    assert [item.id for item in changed] == [entry.id]
    assert load_entries(tmp_path)[0].summary == "Agent Workspace backend reads TASK_CONTEXT.sqlite3"


def test_input_alias_compositions_do_not_create_new_phrase_aliases(tmp_path: Path) -> None:
    add_dictionary_terms(tmp_path, ("Agent Workspace", "TASK_CONTEXT.sqlite3"))
    details = " ".join("§00 backend reads §01." for _index in range(5))

    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("decision",),
        summary="§00 backend reads §01",
        details=details,
    )
    values = {entry.value for entry in load_dictionary(tmp_path)}
    loaded = load_entries(tmp_path)[0]

    assert "Agent Workspace backend" not in values
    assert "Agent Workspace backend reads TASK_CONTEXT.sqlite3" not in values
    assert loaded.summary == "Agent Workspace backend reads TASK_CONTEXT.sqlite3"
    assert "§00 backend reads §01" in render_agent_entries(tmp_path, [loaded], format_name="markdown")


def test_dictionary_compiler_skips_unprofitable_candidates(tmp_path: Path) -> None:
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="mid",
        labels=("decision",),
        summary="Task context stays readable",
        details="Task context is a short generic phrase. The compiler should not encode it.",
    )
    add_entry(
        tmp_path,
        timestamp="2026-08-19T11:00:00",
        severity="mid",
        labels=("decision",),
        summary="CONFIG_ONCE appears once",
    )

    assert load_dictionary(tmp_path) == []
    agent_context = render_agent_entries(tmp_path, load_entries(tmp_path), format_name="markdown")
    assert "No dictionary aliases used" in agent_context
    assert "§00" not in agent_context


def test_dictionary_preview_uses_policy_and_reports_savings() -> None:
    path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
    text = f"{path} validates Agent Workspace. {path} covers Agent Workspace settings."

    preview = preview_dictionary_compile(
        text,
        TaskDictionaryPolicy(min_occurrences=2, min_saving=0, min_term_length=4),
    )

    assert preview.dictionary
    assert preview.dictionary[0].token == "§00"
    assert path in {entry.value for entry in preview.dictionary}
    assert path not in preview.encoded_text
    assert "§00" in preview.encoded_text
    assert preview.original_tokens > preview.encoded_tokens
    assert preview.net_token_saving == preview.original_tokens - preview.encoded_tokens - preview.dictionary_tokens


def test_dictionary_preview_respects_disabled_auto_discovery() -> None:
    path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
    text = f"{path} validates Agent Workspace. {path} covers Agent Workspace settings."

    preview = preview_dictionary_compile(text, TaskDictionaryPolicy(auto_discovery=False))

    assert preview.dictionary == ()
    assert preview.encoded_text == text
    assert preview.dictionary_tokens == 0


def test_token_count_falls_back_when_tiktoken_is_unavailable(monkeypatch: object) -> None:
    monkeypatch.setitem(sys.modules, "tiktoken", None)
    monkeypatch.setattr(task_context_module, "_TOKENIZER_ENCODING_CACHE", None)
    monkeypatch.setattr(task_context_module, "_TOKENIZER_IMPORT_FAILED", False)

    assert token_count("one two three") == 4
    assert task_context_module._TOKENIZER_IMPORT_FAILED is True


def test_token_count_uses_tiktoken_when_available(monkeypatch: object) -> None:
    class FakeEncoding:
        def encode(self, text: str) -> list[str]:
            return text.split()

    fake_tiktoken = SimpleNamespace(
        get_encoding=lambda name: FakeEncoding(),
        encoding_for_model=lambda name: FakeEncoding(),
    )
    monkeypatch.setitem(sys.modules, "tiktoken", fake_tiktoken)
    monkeypatch.setenv("AGENT_TOOLS_TOKENIZER_ENCODING", "fake")
    monkeypatch.delenv("AGENT_TOOLS_TOKENIZER_MODEL", raising=False)
    monkeypatch.setattr(task_context_module, "_TOKENIZER_ENCODING_CACHE", None)
    monkeypatch.setattr(task_context_module, "_TOKENIZER_IMPORT_FAILED", False)

    preview = preview_dictionary_compile("one two three", TaskDictionaryPolicy(auto_discovery=False))

    assert token_count("one two three") == 3
    assert preview.original_tokens == 3
    assert preview.encoded_tokens == 3


def test_dictionary_candidate_formula_uses_net_token_delta() -> None:
    path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
    config = "CONFIG_ARM_SCMI_TRANSPORT_SMC"

    assert _candidate_net_saving(path, "§00", 3) > 0
    assert _candidate_net_saving(config, "§00", 3) > 0
    assert _candidate_net_saving("dictionary", "§00", 3) < 0
    assert _candidate_net_saving("context", "§00", 3) < 0

    accepted = preview_dictionary_compile(
        f"{path} {path} {path}",
        TaskDictionaryPolicy(min_occurrences=3, min_term_length=7, min_saving=1),
    )
    rejected = preview_dictionary_compile(
        "dictionary dictionary dictionary",
        TaskDictionaryPolicy(min_occurrences=3, min_term_length=7, min_saving=1),
    )

    assert [entry.value for entry in accepted.dictionary] == [path]
    assert rejected.dictionary == ()


def test_dictionary_candidate_selection_uses_marginal_encoded_body() -> None:
    path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
    text = f"{path} {path} {path} test_agent_workspace"

    preview = preview_dictionary_compile(
        text,
        TaskDictionaryPolicy(min_occurrences=1, min_term_length=7, min_saving=1),
    )
    values = [entry.value for entry in preview.dictionary]

    assert path in values
    assert "test_agent_workspace" not in values


def test_dictionary_preview_discovers_profitable_terms_without_semantic_lists() -> None:
    text = """
agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates CONFIG_ARM_SCMI_TRANSPORT_SMC.
agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py checks CONFIG_ARM_SCMI_TRANSPORT_SMC.
agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py covers CONFIG_ARM_SCMI_TRANSPORT_SMC.
dictionary dictionary dictionary context context context encoded encoded encoded
"""

    preview = preview_dictionary_compile(text, TaskDictionaryPolicy())
    values = {entry.value for entry in preview.dictionary}

    assert {"agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py", "CONFIG_ARM_SCMI_TRANSPORT_SMC"} <= values
    assert {"dictionary", "context", "encoded"}.isdisjoint(values)
    assert not any(" " in value and value.casefold().startswith(("the ", "a ", "an ")) for value in values)


def test_dictionary_preview_calibrates_large_journal_sample_for_model_tokens() -> None:
    sample = """
summary  Global task dictionary compiler settings and preview added
details  Added global Agent Workspace settings for task dictionary compiler policy: auto discovery, min occurrences, min saving, min term length, max term words, strip articles, and preview text. GTK Settings uses separate General and Dictionary tabs. Dictionary tab places compiler controls at the top and a horizontal split preview area below that expands to the bottom of the dialog: Preview text on the left, Compiler preview on the right. Default preview text is longer and includes repeated paths/config/function names so compression is visible. Display rendering stays decoded/encoded as before; settings affect journal compilation. Tk preserves the new settings keys when saving. Validation: code_map parse-check passed for changed [0c]/[08] Python files; Docker ubuntu:24.04 [0c] pytest passed 212 tests; Docker xvfb GTK Settings smoke passed; Docker python:3.12-slim [08] pytest passed 26 tests; [0b] --workspace /home/vladyslav-goncharuk/Documents/Projects --strict-warnings passed 13/0/0.
labels   #task-context #gui #validation
summary  Agent Workspace can show encoded task context with dictionary
details  Agent Workspace Details encoded-context toggle renders encoded context for humans. GTK encoded view keeps current journal filters, renders Dictionary first, then the same ASCII card layout as decoded view with encoded summary/details containing plain §id aliases. Tk/core encoded markdown also renders Dictionary before entries and uses plain §id aliases. Validation: code_map parse-check passed for changed Agent Workspace Python files; Docker ubuntu:24.04 Agent Workspace pytest passed, 212 tests; task_check --strict-warnings for current task passed.
labels   #gui #task-context #validation
summary  task_check now gates current context size and push
details  Added task_check slot context-size FAIL using rough token budget 25,600, about 10% of 256K context. Agent Workspace feeds task_check FAIL reports into new/resumed prompts through existing include_task_check path. push_guard pre-push now blocks repositories inside tasks/<task>/ when task_check reports issues. Docker validation passed: python:3.12-slim with git ran paf_workspace/tests/test_task_check.py, tools/push_guard/tests/test_push_guard.py, tools/task_context/tests/test_task_context.py -> 47 passed; ubuntu:24.04 with tkinter/GTK/VTE ran agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py -> 210 passed. code_map parse-check passed for changed Python files.
labels   #task-context #tooling #validation
summary  Current task context system state and policy
details  Current state: task_context uses SQLite-only slot context, agent format, persistent append-only dictionary ids rendered as §00, decoded UI default, encoded agent output with selected dictionary subset, named-entity-only compiler, dictionary --add for stable agent-supplied terms, and Agent Workspace hook policy for supported harnesses. Agent policy: read current slots, update relevant slots in place, add stable terms through dictionary --add, write terse durable notes. Validation now includes Docker pytest for task_context, task_check, push_guard, and Agent Workspace suites plus code_map parse-check; see validation slot.
labels   #task-context #handoff #policy #validation
"""
    text = "\n".join(sample for _index in range(3))

    preview = preview_dictionary_compile(text, TaskDictionaryPolicy())
    values = {entry.value for entry in preview.dictionary}

    assert len(preview.dictionary) >= 4
    assert preview.net_token_saving >= 50
    assert preview.encoded_tokens + preview.dictionary_tokens < preview.original_tokens
    assert {
        "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py",
        "tools/task_context/tests/test_task_context.py",
        "home/vladyslav-goncharuk/Documents/Projects",
    } <= values
    assert {"context", "encoded", "settings"}.isdisjoint(values)
    assert "test_agent_workspace" not in values


def test_dictionary_preview_default_agent_workspace_sample_uses_repeated_phrases() -> None:
    preview = preview_dictionary_compile(DICTIONARY_PREVIEW_TEXT, TaskDictionaryPolicy())
    values = {entry.value for entry in preview.dictionary}
    dictionary_chars = len("\n".join(f"{entry.token} = {entry.value}" for entry in preview.dictionary))

    assert len(preview.dictionary) >= 4
    assert preview.net_token_saving >= 50
    assert len(DICTIONARY_PREVIEW_TEXT) - len(preview.encoded_text) - dictionary_chars >= 700
    assert {
        "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py",
        "tools/task_context/tests/test_task_context.py",
        "TASK_CONTEXT.sqlite3",
    } <= values
    assert {"context", "validation", "settings", "compiler"}.isdisjoint(values)


def test_dictionary_preview_reaches_expected_technical_text_savings() -> None:
    text = """
Agent Workspace stores active task context in TASK_CONTEXT.sqlite3. Agent Workspace reads TASK_CONTEXT.sqlite3 before launching Codex. Agent Workspace injects active task context when inject_task_context_prompt is enabled. Agent Workspace renders encoded task context in Agent Workspace Details.

agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates Agent Workspace prompt injection. agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates Agent Workspace Details. agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py validates dictionary preview metrics.

tools/task_context/tests/test_task_context.py validates task_context dictionary compilation. tools/task_context/tests/test_task_context.py validates append-only dictionary ids. tools/task_context/tests/test_task_context.py validates codec migration from bracket aliases to paragraph-sign aliases.

task_check --strict-warnings validates TASK_CONTEXT.sqlite3 slot context size. task_check --strict-warnings runs before push_guard. task_check --strict-warnings blocks stale context when current slots exceed the rough token budget.

push_guard runs before git push. push_guard blocks repositories inside tasks/<task>/ when task_check reports failures. push_guard keeps task-local workspace state out of public repository payloads.

code_map parse-check validates tools/task_context/__init__.py. code_map parse-check validates agent_workspace/components/agent_status/src/status.py. code_map parse-check validates agent_workspace/components/gtk_desktop/src/gtk_ui.py. code_map parse-check validates agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py.

Docker python:3.12-slim runs tools/task_context/tests/test_task_context.py. Docker ubuntu:24.04 runs agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py with GTK, VTE, and Tk dependencies. Docker validation records exact command results in task context.

persistent append-only dictionary ids keep stable entity identity. persistent append-only dictionary ids must not be deleted. persistent append-only dictionary ids must not be reused. paragraph-sign aliases such as §00 reduce encoded context size compared with bracketed aliases.
""".strip()

    preview = preview_dictionary_compile(text, TaskDictionaryPolicy())
    values = {entry.value for entry in preview.dictionary}
    dictionary_chars = len("\n".join(f"{entry.token} = {entry.value}" for entry in preview.dictionary))
    encoded_chars = len(preview.encoded_text) + dictionary_chars
    char_saving_percent = (len(text) - encoded_chars) / len(text)
    encoded_tokens = preview.encoded_tokens + preview.dictionary_tokens
    token_saving_percent = (preview.original_tokens - encoded_tokens) / preview.original_tokens

    assert 0.20 <= char_saving_percent <= 0.30
    assert 0.10 <= token_saving_percent <= 0.30
    assert len(preview.dictionary) >= 4
    assert {
        "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py",
        "tools/task_context/tests/test_task_context.py",
        "code_map parse-check validates",
        "task_check --strict-warnings",
    } <= values
    assert {"context", "active", "encoded", "dictionary"}.isdisjoint(values)


def test_dictionary_candidate_priority_prefers_nested_longer_phrase() -> None:
    text = ("Agent Workspace Dictionary settings update. " * 5) + ("Dictionary settings update. " * 2)

    preview = preview_dictionary_compile(
        text,
        TaskDictionaryPolicy(min_occurrences=2, min_saving=1, min_term_length=7, max_term_words=4),
    )
    values = {entry.value for entry in preview.dictionary}

    assert "Agent Workspace Dictionary settings" in values
    assert "Dictionary settings" not in values
    assert preview.net_token_saving > 0


def test_dictionary_compiler_reads_global_agent_workspace_policy(tmp_path: Path) -> None:
    config_root = tmp_path / "config"
    settings_path = config_root / "agent_tools" / "agent_workspace" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"task_dictionary_auto_discovery": false}\n', encoding="utf-8")
    old_config_root = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = str(config_root)
    try:
        path = "agent_workspace/components/gtk_desktop/tests/test_gtk_desktop.py"
        add_entry(
            tmp_path,
            timestamp="2026-08-19T10:00:00",
            severity="high",
            labels=("test",),
            summary=f"{path} validates Agent Workspace",
            details=f"{path} covers Agent Workspace settings and {path} covers dictionary settings.",
        )
    finally:
        if old_config_root is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = old_config_root

    assert load_dictionary(tmp_path) == []


def test_dictionary_compiler_removes_english_articles_from_candidate_values(tmp_path: Path) -> None:
    component = "Agent Workspace GTK UI"
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("gui",),
        summary=f"the {component} reads task context",
        details=(
            f"the {component} refreshes details and the {component} keeps decoded text visible. "
            f"the {component} updates labels."
        ),
    )

    dictionary = load_dictionary(tmp_path)
    agent_context = render_agent_entries(tmp_path, load_entries(tmp_path), format_name="markdown")

    assert dictionary[0].value == component
    assert f"`§00` = {component}" in agent_context
    assert "the §00" not in agent_context
    assert component not in _encoded_context_body(agent_context)


def test_dictionary_compiler_renders_only_aliases_used_by_selected_entries(tmp_path: Path) -> None:
    scmi_path = "drivers/firmware/scmi/scmi.c"
    xen_path = "drivers/xen/xenbus/xenbus_probe.c"
    scmi = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{scmi_path} sends SCMI messages",
        details=f"{scmi_path} calls scmi_send_message() before {scmi_path} is ready.",
    )
    xen = add_entry(
        tmp_path,
        timestamp="2026-08-19T11:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{xen_path} probes XenStore",
        details=f"{xen_path} waits for xenbus and {xen_path} records backend state.",
    )

    dictionary = load_dictionary(tmp_path)
    assert {item.value for item in dictionary} >= {scmi_path, xen_path}

    scmi_context = render_agent_entries(tmp_path, [entry for entry in load_entries(tmp_path) if entry.id == scmi.id])
    xen_context = render_agent_entries(tmp_path, [entry for entry in load_entries(tmp_path) if entry.id == xen.id])

    assert scmi_path in scmi_context
    assert xen_path not in scmi_context
    assert xen_path in xen_context
    assert scmi_path not in xen_context


def test_dictionary_compiler_flat_aliases_do_not_encode_dictionary_values(tmp_path: Path) -> None:
    phrase = "Agent Workspace GTK UI"
    path = "agent_workspace/gtk_ui.py"
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("gui",),
        summary=f"{phrase} uses {path}",
        details=f"{phrase} refreshes {path}; {path} renders {phrase}.",
    )

    agent_context = render_agent_entries(tmp_path, load_entries(tmp_path), format_name="markdown")
    dictionary_section = agent_context.split("## Encoded Context", 1)[0]

    assert "§00" in _encoded_context_body(agent_context)
    assert "§" not in dictionary_section.replace("`§00`", "").replace("`§01`", "")


def test_dictionary_compiler_reduces_realistic_agent_context_size(tmp_path: Path) -> None:
    scmi_path = "drivers/firmware/scmi/scmi.c"
    config = "CONFIG_ARM_SCMI_TRANSPORT_SMC"
    function = "scmi_send_message()"
    for index in range(5):
        add_entry(
            tmp_path,
            timestamp=f"2026-08-19T10:0{index}:00",
            severity="high",
            labels=("bug",),
            summary=f"{scmi_path} checks {config} before {function}",
            details=(
                f"{scmi_path} calls {function}; {config} changes the path through "
                f"{scmi_path}; {function} must stay consistent with {config}."
            ),
        )

    entries = load_entries(tmp_path)
    decoded = render_entries(entries, format_name="markdown")
    encoded = render_agent_entries(tmp_path, entries, format_name="markdown")

    dictionary_values = {item.value for item in load_dictionary(tmp_path)}
    assert dictionary_values >= {scmi_path, config, function}
    assert not any("changes the path through" in value for value in dictionary_values)
    assert scmi_path not in _encoded_context_body(encoded)
    assert config not in _encoded_context_body(encoded)
    assert function not in _encoded_context_body(encoded)
    assert len(encoded) < int(len(decoded) * 0.75)


def test_dictionary_compiler_does_not_redefine_stable_alias_ids(tmp_path: Path) -> None:
    first = "drivers/firmware/scmi/scmi.c"
    second = "drivers/xen/xenbus/xenbus_probe.c"
    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{first} starts early",
        details=f"{first} calls scmi_send_message() and {first} records state.",
    )
    first_dictionary = load_dictionary(tmp_path)
    first_id = next(item.id for item in first_dictionary if item.value == first)

    edit_entries(
        tmp_path,
        ids=(entry.id,),
        set_summary=f"{second} starts early",
        set_details=f"{second} waits for xenbus and {second} records state.",
    )
    dictionary = load_dictionary(tmp_path)

    assert next(item.id for item in dictionary if item.value == first) == first_id
    assert next(item.id for item in dictionary if item.value == second) != first_id


def test_dictionary_compiler_never_reuses_ids_after_entry_deletion(tmp_path: Path) -> None:
    first = "drivers/firmware/scmi/scmi.c"
    second = "drivers/xen/xenbus/xenbus_probe.c"
    entry = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{first} starts early",
        details=f"{first} calls scmi_send_message() and {first} records state.",
    )

    assert [(item.id, item.value) for item in load_dictionary(tmp_path)] == [(0, first)]

    edit_entries(tmp_path, ids=(entry.id,), delete=True)
    dictionary_after_delete = load_dictionary(tmp_path)

    assert [(item.id, item.value) for item in dictionary_after_delete] == [(0, first)]
    assert "No dictionary aliases used" in render_agent_entries(tmp_path, load_entries(tmp_path))

    add_entry(
        tmp_path,
        timestamp="2026-08-19T11:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{second} starts early",
        details=f"{second} waits for xenbus and {second} records state.",
    )
    dictionary = load_dictionary(tmp_path)

    assert (0, first) in [(item.id, item.value) for item in dictionary]
    assert (1, second) in [(item.id, item.value) for item in dictionary]
    assert "§01" in render_agent_entries(tmp_path, load_entries(tmp_path))
    assert "§00" not in _encoded_context_body(render_agent_entries(tmp_path, load_entries(tmp_path)))


def test_dictionary_accepts_agent_supplied_terms(tmp_path: Path) -> None:
    term = "XenStore frontend"
    add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary=f"{term} starts early",
        details=f"{term} waits for backend state.",
    )

    assert load_dictionary(tmp_path) == []

    assert add_dictionary_terms(tmp_path, (term, term)) == 1
    dictionary = load_dictionary(tmp_path)
    agent_context = render_agent_entries(tmp_path, load_entries(tmp_path))

    assert [(item.id, item.value) for item in dictionary] == [(0, term)]
    assert "§00" in _encoded_context_body(agent_context)
    assert term not in _encoded_context_body(agent_context)


def test_dictionary_recompiles_all_entries_after_edit_and_delete(tmp_path: Path) -> None:
    repeated = "CONFIG_ARM_SCMI_TRANSPORT_SMC"
    first = add_entry(
        tmp_path,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("build",),
        summary=f"{repeated} enables SCMI SMC transport",
        details=f"{repeated} is referenced by {repeated}.",
    )
    second = add_entry(
        tmp_path,
        timestamp="2026-08-19T11:00:00",
        severity="mid",
        labels=("decision",),
        summary=f"Keep {repeated} active",
    )

    assert "§00" in render_agent_entries(tmp_path, load_entries(tmp_path))

    edit_entries(
        tmp_path,
        ids=(first.id,),
        set_summary="Transport config removed",
        set_details="No repeated config symbol remains here.",
    )
    after_edit = render_agent_entries(tmp_path, load_entries(tmp_path))
    assert repeated in render_entries(load_entries(tmp_path), format_name="markdown")
    assert "§00" in after_edit

    edit_entries(tmp_path, ids=(second.id,), delete=True)
    after_delete = render_agent_entries(tmp_path, load_entries(tmp_path))
    assert "§00" not in after_delete
    assert "No dictionary aliases used" in after_delete


def test_slot_api_sets_queries_and_compacts_current_context(tmp_path: Path, capsys: object) -> None:
    assert (
        main(
            [
                "slot",
                "--task",
                str(tmp_path),
                "--category",
                "goal",
                "--content",
                "Build slot-based task context.",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["query", "--task", str(tmp_path), "--category", "goal", "--format", "markdown"]) == 0
    query_output = capsys.readouterr().out
    assert query_output.startswith("```text\n+---")
    assert "| Goal" in query_output
    assert "Build slot-based task context." in query_output

    assert main(["query", "--task", str(tmp_path), "--cats", "env,validation"]) == 0
    assert capsys.readouterr().out == ""

    assert main(["compact", "--task", str(tmp_path), "--agent-context"]) == 0
    compact_output = capsys.readouterr().out
    assert "| Goal" in compact_output
    assert not (tmp_path / "TASK_CONTEXT.md").exists()


def test_compact_agent_context_excludes_legacy_slot(tmp_path: Path, capsys: object) -> None:
    set_slot(tmp_path, "goal", "Build slot-based task context.")
    set_slot(tmp_path, "operational-memory", "Current memory.")
    set_slot(tmp_path, "legacy", "Old imported context.")

    assert main(["compact", "--task", str(tmp_path), "--agent-context"]) == 0
    compact_output = capsys.readouterr().out

    assert "| Goal" in compact_output
    assert "Old imported context." not in compact_output
    assert "| Legacy" not in compact_output


def test_slot_agent_format_encodes_content_and_renders_dictionary(tmp_path: Path, capsys: object) -> None:
    repeated = "drivers/firmware/scmi/scmi.c"
    assert (
        main(
            [
                "slot",
                "--task",
                str(tmp_path),
                "--category",
                "findings",
                "--content",
                f"{repeated} starts. {repeated} validates. {repeated} remains active.",
                "--format",
                "agent",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out

    assert "## Task Dictionary" in output
    assert repeated in output
    assert "```text\n+---" in output
    assert "§00 starts" in output


def test_missing_database_imports_description_and_markdown_context_to_legacy_slot(tmp_path: Path) -> None:
    (tmp_path / "TASK_DESCRIPTION.md").write_text("# Old description\n\nBrief.\n", encoding="utf-8")
    (tmp_path / "TASK_CONTEXT.md").write_text("# Old context\n\nContext.\n", encoding="utf-8")

    slots = load_slots(tmp_path)

    assert [slot.category for slot in slots] == ["legacy"]
    assert "TASK_DESCRIPTION.md" in slots[0].content
    assert "Brief." in slots[0].content
    assert "TASK_CONTEXT.md" in slots[0].content
    assert "Context." in slots[0].content


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
