"""Public API for task context rendering."""

from __future__ import annotations

from ..src.context import ContextEntry
from ..src.context import DICTIONARY_TOKEN_RE
from ..src.context import context_dictionary_data
from ..src.context import context_dictionary_markdown
from ..src.context import context_entry_cards_markdown
from ..src.context import encoded_context_entries_markdown
from ..src.context import load_task_context_dictionary
from ..src.context import load_task_context_slots
from ..src.context import render_task_context_slots
from ..src.context import slot_dictionary_data
from ..src.context import task_context_details_markdown
from ..src.context import task_goal_slot_markdown

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
