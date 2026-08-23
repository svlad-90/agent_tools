from __future__ import annotations

from agent_tools.tools.agent_workspace.components.test_support.src.helpers import *


def test_task_context_component_cards_markdown_renders_console_cards() -> None:
    content = context_entry_cards_markdown(
        [
            ContextEntry(
                timestamp="2026-08-19T10:30:00+03:00",
                severity="critical",
                labels=("blocker", "validation"),
                status="active",
                summary="Release validation is blocked on approval",
                details="Critical blocker is intentionally active for filter testing.",
                source="agent",
                artifacts=("report/validation/latest.json",),
                id=36,
            )
        ]
    )

    assert content.startswith("```text\n+")
    assert "#36 [CRITICAL] [ACTIVE]  2026-08-19 10:30:00+03:00" in content
    assert "summary  Release validation is blocked on approval" in content
    assert "labels   #blocker #validation" in content
    assert "artifacts report/validation/latest.json" in content
    assert content.endswith("\n```")


def test_task_context_component_encoded_cards_keep_dictionary_above_cards(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    add_entry(
        task,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary="drivers/firmware/scmi/scmi.c has active context",
        details=(
            "drivers/firmware/scmi/scmi.c records active context. "
            "drivers/firmware/scmi/scmi.c appears in the handoff. "
            "drivers/firmware/scmi/scmi.c remains the target file."
        ),
    )
    summary = discover_tasks_with_context(task, tmp_path)

    content = encoded_context_entries_markdown(summary.path, load_task_context_entries(task))

    assert content.startswith("## Dictionary\n\n```text\n§00 = drivers/firmware/scmi/scmi.c")
    assert "```\n\n```text\n+" in content
    assert "summary  §00 has active context" in content
    assert "details  §00 records active context." in content


def test_task_context_details_can_render_encoded_dictionary_view(tmp_path: Path) -> None:
    task = tmp_path / "tasks" / "sample-task"
    task.mkdir(parents=True)
    add_entry(
        task,
        timestamp="2026-08-19T10:00:00",
        severity="high",
        labels=("bug",),
        summary="drivers/firmware/scmi/scmi.c has active context",
        details=(
            "drivers/firmware/scmi/scmi.c records active context. "
            "drivers/firmware/scmi/scmi.c appears in the handoff. "
            "drivers/firmware/scmi/scmi.c remains the target file."
        ),
    )
    summary = discover_tasks_with_context(task, tmp_path)
    entries = load_task_context_entries(task)

    decoded = task_context_details_markdown(summary.path, entries, encoded=False)
    encoded = task_context_details_markdown(summary.path, entries, encoded=True)

    assert "## Task Dictionary" not in decoded
    assert "drivers/firmware/scmi/scmi.c has active context" in decoded
    assert "## Task Dictionary" not in encoded
    assert "## Encoded Context" not in encoded
    assert "drivers/firmware/scmi/scmi.c" in encoded
    assert encoded.startswith("## Dictionary")
    assert "§00" in encoded
    assert "## Dictionary" in encoded
    assert "§00 = drivers/firmware/scmi/scmi.c" in encoded

