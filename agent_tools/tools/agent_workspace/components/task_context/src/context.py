from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_tools.tools.task_context import ContextEntry
from agent_tools.tools.task_context import DICTIONARY_TOKEN_RE
from agent_tools.tools.task_context import load_dictionary as load_task_context_dictionary
from agent_tools.tools.task_context import load_slots as load_task_context_slots
from agent_tools.tools.task_context import render_entries as render_task_context_entries
from agent_tools.tools.task_context import render_slots as render_task_context_slots


def task_goal_slot_markdown(task_dir: Path) -> str:
    slots = load_task_context_slots(task_dir, ("goal",))
    if slots:
        return render_task_context_slots(slots, format_name="markdown", task_dir=task_dir)
    return "# Goal\n\n- Empty.\n"


def task_context_details_markdown(task_dir: Path, entries: Any, *, encoded: bool = False) -> str:
    entries = list(entries)
    if encoded:
        return encoded_context_entries_markdown(task_dir, entries)
    return render_task_context_entries(entries, format_name="markdown")


def encoded_context_entries_markdown(task_dir: Path, entries: list[ContextEntry]) -> str:
    parts: list[str] = []
    dictionary = context_dictionary_markdown(task_dir, entries)
    if dictionary:
        parts.append(dictionary)
    cards = context_entry_cards_markdown(entries, encoded=True)
    if cards:
        parts.append(cards)
    return "\n\n".join(parts)


def context_entry_cards_markdown(entries: Any, *, encoded: bool = False) -> str:
    cards = [_context_entry_card(entry, encoded=encoded) for entry in entries]
    if not cards:
        return ""
    return "```text\n" + "\n\n".join(cards) + "\n```"


def context_dictionary_data(task_dir: Path, entries: list[ContextEntry]) -> list[dict[str, str]]:
    used_tokens = _used_dictionary_tokens(entries)
    if not used_tokens:
        return []
    return [
        {"token": item.token, "value": item.value}
        for item in load_task_context_dictionary(task_dir)
        if item.token in used_tokens
    ]


def slot_dictionary_data(task_dir: Path, markdown: str) -> list[dict[str, str]]:
    used_tokens = {match.group(0) for match in DICTIONARY_TOKEN_RE.finditer(markdown)}
    if not used_tokens:
        return []
    return [
        {"token": item.token, "value": item.value}
        for item in load_task_context_dictionary(task_dir)
        if item.token in used_tokens
    ]


def context_dictionary_markdown(task_dir: Path, entries: list[ContextEntry]) -> str:
    items = context_dictionary_data(task_dir, entries)
    if not items:
        return ""
    lines = [f"{item['token']} = {item['value']}" for item in items]
    return "## Dictionary\n\n```text\n" + "\n".join(lines) + "\n```"


def _used_dictionary_tokens(entries: list[ContextEntry]) -> set[str]:
    used_tokens: set[str] = set()
    for entry in entries:
        for value in (entry.encoded_summary, entry.encoded_details):
            used_tokens.update(match.group(0) for match in DICTIONARY_TOKEN_RE.finditer(value or ""))
    return used_tokens


def _context_entry_card(entry: ContextEntry, *, width: int = 96, encoded: bool = False) -> str:
    summary = entry.encoded_summary if encoded and entry.encoded_summary else entry.summary
    details = entry.encoded_details if encoded and entry.encoded_details else entry.details
    labels = " ".join(f"#{label}" for label in entry.labels) if entry.labels else "-"
    rows = [
        _context_entry_head(entry),
        " " + "-" * (width - 4) + " ",
        f"summary  {summary}",
    ]
    if details:
        rows.append(f"details  {details}")
    if entry.artifacts:
        rows.append("artifacts " + ", ".join(entry.artifacts))
    rows.extend([f"labels   {labels}", f"source   {entry.source}"])
    boxed_rows = [_boxed_line(row, width) for row in rows]
    border = "+" + "-" * (width - 2) + "+"
    return "\n".join([border, *boxed_rows, border])


def _context_entry_head(entry: ContextEntry) -> str:
    timestamp = entry.timestamp.replace("T", " ", 1)
    entry_id = f"#{entry.id} " if entry.id is not None else ""
    return f"{entry_id}[{entry.severity.upper()}] [{entry.status.upper()}]  {timestamp}"


def _boxed_line(text: str, width: int) -> str:
    content_width = width - 4
    lines: list[str] = []
    remaining = text
    while len(remaining) > content_width:
        split_at = remaining.rfind(" ", 0, content_width + 1)
        if split_at <= 0:
            split_at = content_width
        lines.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    lines.append(remaining)
    return "\n".join(f"| {line:<{content_width}} |" for line in lines)


__all__ = [
    "ContextEntry",
    "DICTIONARY_TOKEN_RE",
    "context_dictionary_data",
    "context_dictionary_markdown",
    "context_entry_cards_markdown",
    "encoded_context_entries_markdown",
    "load_task_context_dictionary",
    "load_task_context_slots",
    "render_task_context_slots",
    "slot_dictionary_data",
    "task_context_details_markdown",
    "task_goal_slot_markdown",
]
