from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_tools.tools.task_context import ContextEntry
from agent_tools.tools.task_context import DICTIONARY_TOKEN_RE
from agent_tools.tools.task_context import load_dictionary as load_task_context_dictionary
from agent_tools.tools.task_context import load_slots as load_task_context_slots
from agent_tools.tools.task_context import render_slots as render_task_context_slots

from .artifacts import artifact_relative_label
from .artifacts import artifact_updated_label
from .artifacts import task_artifact_entries
from .commands import task_action_command
from .commands import task_check_command
from .core import TaskAction
from .core import TaskSummary
from .core import discover_tasks
from .core import load_task_actions_config
from .core import read_task_file
from .core import run_task_check


DEFAULT_CONTEXT_SEVERITY = ("mid", "high", "critical")
DEFAULT_CONTEXT_STATUS = ("active",)


@dataclass(frozen=True)
class TaskContextFilters:
    since: str | None = None
    until: str | None = None
    severity: tuple[str, ...] | None = DEFAULT_CONTEXT_SEVERITY
    statuses: tuple[str, ...] | None = DEFAULT_CONTEXT_STATUS
    labels: tuple[str, ...] = ()
    newest_first: bool = True


class AgentWorkspaceService:
    """Headless Agent Workspace operations shared by UI frontends."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def tasks(self) -> list[dict[str, Any]]:
        return [task_summary_data(task) for task in discover_tasks(self.workspace)]

    def task(self, task_name: str) -> TaskSummary:
        for task in discover_tasks(self.workspace):
            if task.name == task_name:
                return task
        raise KeyError(f"unknown task: {task_name}")

    def task_snapshot(
        self,
        task_name: str,
        *,
        context_filters: TaskContextFilters | None = None,
        encoded_context: bool = False,
    ) -> dict[str, Any]:
        task = self.task(task_name)
        context_filters = context_filters or TaskContextFilters()
        return {
            "task": task_summary_data(task),
            "description": _task_goal_slot_markdown(task),
            "context": self.task_context(task_name, filters=context_filters, encoded=encoded_context),
            "actions": self.task_actions(task_name),
            "artifacts": self.task_artifacts(task_name),
            "task_check": run_task_check(task, self.workspace),
        }

    def task_context(
        self,
        task_name: str,
        *,
        filters: TaskContextFilters | None = None,
        encoded: bool = False,
    ) -> dict[str, Any]:
        task = self.task(task_name)
        filters = filters or TaskContextFilters()
        slots = load_task_context_slots(task.path)
        visible_slots = [slot for slot in slots if slot.category != "goal"]
        markdown = render_task_context_slots(
            visible_slots,
            format_name="agent" if encoded else "markdown",
            task_dir=task.path,
        )
        return {
            "entries": [slot.to_json() for slot in visible_slots],
            "markdown": markdown,
            "dictionary": slot_dictionary_data(task, markdown) if encoded else [],
            "available_labels": [],
        }

    def task_actions(self, task_name: str) -> dict[str, Any]:
        task = self.task(task_name)
        config = load_task_actions_config(task)
        return {
            "actions": [task_action_data(action) for action in config.actions],
            "errors": list(config.errors),
        }

    def task_artifacts(self, task_name: str) -> list[dict[str, Any]]:
        task = self.task(task_name)
        return [
            {
                "group": entry.group,
                "path": str(entry.path),
                "label": artifact_relative_label(task, entry.path),
                "updated": entry.updated,
                "updated_label": artifact_updated_label(entry.updated),
            }
            for entry in task_artifact_entries(task)
        ]

    def task_check_command(self, task_name: str) -> str:
        return task_check_command(self.workspace, self.task(task_name))

    def task_action_command(self, task_name: str, action_id: str) -> str:
        task = self.task(task_name)
        config = load_task_actions_config(task)
        for action in config.actions:
            if action.action_id == action_id:
                return task_action_command(action)
        raise KeyError(f"unknown task action: {action_id}")


def task_summary_data(task: TaskSummary) -> dict[str, Any]:
    return {
        "name": task.name,
        "path": str(task.path),
        "has_description": task.has_description,
        "has_context": task.has_context,
        "description_tokens": task.description_tokens,
        "context_tokens": task.context_tokens,
        "context_over_budget": task.context_over_budget,
    }


def _task_goal_slot_markdown(task: TaskSummary) -> str:
    slots = load_task_context_slots(task.path, ("goal",))
    if slots:
        return render_task_context_slots(slots, format_name="markdown", task_dir=task.path)
    return "# Goal\n\n- Empty.\n"


def context_entry_data(entry: ContextEntry, *, encoded: bool = False) -> dict[str, Any]:
    summary = entry.encoded_summary if encoded else entry.summary
    details = entry.encoded_details if encoded else entry.details
    return {
        "id": entry.id,
        "timestamp": entry.timestamp,
        "severity": entry.severity,
        "status": entry.status,
        "labels": list(entry.labels),
        "summary": summary or "",
        "details": details or "",
        "source": entry.source,
        "artifacts": list(entry.artifacts),
    }


def task_action_data(action: TaskAction) -> dict[str, Any]:
    return {
        "id": action.action_id,
        "label": action.label,
        "command": list(action.command) if isinstance(action.command, tuple) else action.command,
        "cwd": str(action.cwd),
        "env": dict(action.env),
        "parameters": [
            {
                "name": parameter.name,
                "label": parameter.label,
                "type": parameter.parameter_type,
                "set": parameter.set_name,
                "default": parameter.default,
                "global": parameter.global_name,
            }
            for parameter in action.parameters
        ],
        "bindings": dict(action.bindings or {}),
        "base_action_id": action.base_action_id,
        "is_shortcut": action.is_shortcut,
    }


def context_cards_markdown(task: TaskSummary, entries: list[ContextEntry], *, encoded: bool = False) -> str:
    if not entries:
        return ""
    parts: list[str] = []
    if encoded:
        dictionary = context_dictionary_markdown(task, entries)
        if dictionary:
            parts.append(dictionary)
    cards = [_context_entry_card(entry, encoded=encoded) for entry in entries]
    parts.append("```text\n" + "\n\n".join(cards) + "\n```")
    return "\n\n".join(parts)


def context_dictionary_data(task: TaskSummary, entries: list[ContextEntry]) -> list[dict[str, str]]:
    used_tokens = _used_dictionary_tokens(entries)
    if not used_tokens:
        return []
    return [
        {"token": item.token, "value": item.value}
        for item in load_task_context_dictionary(task.path)
        if item.token in used_tokens
    ]


def slot_dictionary_data(task: TaskSummary, markdown: str) -> list[dict[str, str]]:
    used_tokens = {match.group(0) for match in DICTIONARY_TOKEN_RE.finditer(markdown)}
    if not used_tokens:
        return []
    return [
        {"token": item.token, "value": item.value}
        for item in load_task_context_dictionary(task.path)
        if item.token in used_tokens
    ]


def context_dictionary_markdown(task: TaskSummary, entries: list[ContextEntry]) -> str:
    items = context_dictionary_data(task, entries)
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
    summary = entry.encoded_summary if encoded else entry.summary
    details = entry.encoded_details if encoded else entry.details
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
