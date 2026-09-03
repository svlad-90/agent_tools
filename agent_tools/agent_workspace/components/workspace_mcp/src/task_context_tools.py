from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_tools.tools.task_context import DEFAULT_COMPACT_LIMIT
from agent_tools.tools.task_context import SEVERITIES, SLOT_CATEGORIES, STATUSES
from agent_tools.tools.task_context import add_dictionary_terms, add_entry, compact_context, compile_dictionary
from agent_tools.tools.task_context import edit_entries, load_dictionary, load_slots, migrate_legacy_journal
from agent_tools.tools.task_context import render_entries, render_slots, set_slot

from .registry import JsonObject, McpTool, ToolContext, ToolResult
from .registry import bool_arg, int_arg, optional_string_arg, resolve_workspace_path, string_arg, string_list_arg


def task_context_tools() -> list[McpTool]:
    return [
        McpTool(
            name="task_context_query",
            title="Task Context Query",
            description=(
                "Use instead of sqlite/Bash reads when task state is needed. "
                "Validates the task path, reads current TASK_CONTEXT.sqlite3 slots, "
                "omits legacy noise by default, and can render compact agent context."
            ),
            input_schema=_query_input_schema(),
            handler=_task_context_query,
        ),
        McpTool(
            name="task_context_set_slot",
            title="Task Context Set Slot",
            description=(
                "Use instead of manual SQLite writes to update durable task state. "
                "Replaces one current slot in TASK_CONTEXT.sqlite3 with validated "
                "category names and returns the updated slot."
            ),
            input_schema=_set_slot_input_schema(),
            handler=_task_context_set_slot,
        ),
        McpTool(
            name="task_context_add_entry",
            title="Task Context Add Entry",
            description=(
                "Use for append-only findings or validation notes instead of editing "
                "journal files by hand. Adds one structured entry with severity, "
                "status, labels, and artifacts."
            ),
            input_schema=_add_entry_input_schema(),
            handler=_task_context_add_entry,
        ),
        McpTool(
            name="task_context_edit_entries",
            title="Task Context Edit Entries",
            description=(
                "Use for controlled journal cleanup instead of ad-hoc JSON/SQLite edits. "
                "Filters entries, supports dry-run, and applies batch status/label/"
                "artifact/detail changes or deletion."
            ),
            input_schema=_edit_entries_input_schema(),
            handler=_task_context_edit_entries,
        ),
        McpTool(
            name="task_context_dictionary",
            title="Task Context Dictionary",
            description=(
                "Use instead of hand-encoding repeated terms. Reads or appends stable "
                "task dictionary aliases used by compact context rendering."
            ),
            input_schema=_dictionary_input_schema(),
            handler=_task_context_dictionary,
        ),
        McpTool(
            name="task_context_compile_dictionary",
            title="Task Context Compile Dictionary",
            description=(
                "Use to derive dictionary aliases from current task context without "
                "manual text analysis. Updates TASK_CONTEXT.sqlite3 dictionary data."
            ),
            input_schema=_compile_dictionary_input_schema(),
            handler=_task_context_compile_dictionary,
        ),
        McpTool(
            name="task_context_compact",
            title="Task Context Compact",
            description=(
                "Use instead of dumping task files into the model. Renders filtered, "
                "budgeted task context from TASK_CONTEXT.sqlite3 for handoff or "
                "agent prompts."
            ),
            input_schema=_compact_input_schema(),
            handler=_task_context_compact,
        ),
        McpTool(
            name="task_context_migrate_legacy",
            title="Task Context Migrate Legacy",
            description=(
                "Use only for migration from legacy task logs. Imports "
                "TASK_CONTEXT_LOG.jsonl entries into TASK_CONTEXT.sqlite3 with "
                "structured categories."
            ),
            input_schema=_migrate_legacy_input_schema(),
            handler=_task_context_migrate_legacy,
        ),
    ]


def _task_context_query(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    categories = string_list_arg(arguments, "categories")
    include_legacy = bool_arg(arguments, "include_legacy", False)
    format_name = string_arg(arguments, "format", "text")

    slots = load_slots(task_dir, categories)
    if not include_legacy:
        slots = [slot for slot in slots if slot.category != "legacy"]

    if format_name == "json":
        text = json.dumps([slot.to_json() for slot in slots], ensure_ascii=False, indent=2)
        return ToolResult(text=text + "\n", structured_content={"slots": [slot.to_json() for slot in slots]})
    return ToolResult(text=render_slots(slots, format_name=format_name, task_dir=task_dir) + "\n")


def _task_context_set_slot(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    slot = set_slot(
        task_dir,
        string_arg(arguments, "category"),
        string_arg(arguments, "content", ""),
        updated_at=optional_string_arg(arguments, "updated_at"),
    )
    return _render_slots_result([slot], string_arg(arguments, "format", "markdown"), task_dir)


def _task_context_add_entry(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    entry = add_entry(
        task_dir,
        summary=string_arg(arguments, "summary"),
        severity=string_arg(arguments, "severity", "mid"),
        labels=string_list_arg(arguments, "labels"),
        status=string_arg(arguments, "status", "active"),
        details=string_arg(arguments, "details", ""),
        source=string_arg(arguments, "source", "agent"),
        artifacts=string_list_arg(arguments, "artifacts"),
        timestamp=optional_string_arg(arguments, "timestamp"),
    )
    text = json.dumps(entry.to_json(), ensure_ascii=False, sort_keys=True)
    return ToolResult(text=text + "\n", structured_content={"entry": entry.to_json()})


def _task_context_edit_entries(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    entries = edit_entries(
        task_dir,
        ids=_int_list_arg(arguments, "ids"),
        since=optional_string_arg(arguments, "since"),
        until=optional_string_arg(arguments, "until"),
        severity=optional_string_arg(arguments, "severity"),
        labels=string_list_arg(arguments, "labels"),
        statuses=string_list_arg(arguments, "statuses"),
        all_entries=bool_arg(arguments, "all", False),
        set_status=optional_string_arg(arguments, "set_status"),
        set_severity=optional_string_arg(arguments, "set_severity"),
        set_summary=optional_string_arg(arguments, "set_summary"),
        set_details=optional_string_arg(arguments, "set_details"),
        set_source=optional_string_arg(arguments, "set_source"),
        set_labels=_optional_string_list_arg(arguments, "set_labels"),
        add_labels=string_list_arg(arguments, "add_labels"),
        remove_labels=string_list_arg(arguments, "remove_labels"),
        clear_labels=bool_arg(arguments, "clear_labels", False),
        set_artifacts=_optional_string_list_arg(arguments, "set_artifacts"),
        add_artifacts=string_list_arg(arguments, "add_artifacts"),
        remove_artifacts=string_list_arg(arguments, "remove_artifacts"),
        clear_artifacts=bool_arg(arguments, "clear_artifacts", False),
        delete=bool_arg(arguments, "delete", False),
        dry_run=bool_arg(arguments, "dry_run", False),
    )
    action = _edit_action(arguments)
    if string_arg(arguments, "format", "text") == "json":
        payload = {"action": action, "count": len(entries), "entries": [entry.to_json() for entry in entries]}
        return ToolResult(
            text=json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            structured_content=payload,
        )
    rendered = render_entries(entries, format_name=string_arg(arguments, "format", "text"))
    return ToolResult(text=f"{rendered.rstrip()}\ntask-context: {action} {len(entries)} entries\n")


def _task_context_dictionary(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    terms = string_list_arg(arguments, "add")
    if terms:
        added = add_dictionary_terms(task_dir, terms)
        return ToolResult(text=f"task-context: added {added} dictionary aliases\n", structured_content={"added": added})
    dictionary = load_dictionary(task_dir)
    payload = {
        "dictionary": [
            {
                "id": item.id,
                "token": item.token,
                "value": item.value,
                "created_at": item.created_at,
                "status": item.status,
            }
            for item in dictionary
        ]
    }
    if string_arg(arguments, "format", "text") == "json":
        return ToolResult(text=json.dumps(payload["dictionary"], ensure_ascii=False, indent=2) + "\n", structured_content=payload)
    lines = [f"{item['token']}\t{item['status']}\t{item['value']}" for item in payload["dictionary"]]
    return ToolResult(text="\n".join(lines).rstrip() + "\n", structured_content=payload)


def _task_context_compile_dictionary(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    added = compile_dictionary(task_dir)
    return ToolResult(text=f"task-context: compiled dictionary, added {added} aliases\n", structured_content={"added": added})


def _task_context_compact(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    content = compact_context(
        task_dir,
        since=optional_string_arg(arguments, "since"),
        until=optional_string_arg(arguments, "until"),
        severity=string_arg(arguments, "severity", "mid..critical"),
        labels=string_list_arg(arguments, "labels"),
        statuses=string_list_arg(arguments, "statuses") or ("active",),
        limit=int_arg(arguments, "limit", DEFAULT_COMPACT_LIMIT),
        agent_context=bool_arg(arguments, "agent_context", False),
    )
    return ToolResult(text=content.rstrip() + "\n")


def _task_context_migrate_legacy(context: ToolContext, arguments: JsonObject) -> ToolResult:
    task_dir = _resolve_task_dir(context.workspace, string_arg(arguments, "task"))
    count = migrate_legacy_journal(task_dir)
    text = f"task-context: migrated {count} entries\n"
    return ToolResult(text=text, structured_content={"migrated": count})


def _render_slots_result(slots: list[Any], format_name: str, task_dir: Path) -> ToolResult:
    if format_name == "json":
        payload = {"slots": [slot.to_json() for slot in slots]}
        return ToolResult(
            text=json.dumps(payload["slots"], ensure_ascii=False, indent=2) + "\n",
            structured_content=payload,
        )
    return ToolResult(text=render_slots(slots, format_name=format_name, task_dir=task_dir) + "\n")


def _edit_action(arguments: JsonObject) -> str:
    if bool_arg(arguments, "delete", False):
        return "would delete" if bool_arg(arguments, "dry_run", False) else "deleted"
    return "would edit" if bool_arg(arguments, "dry_run", False) else "edited"


def _int_list_arg(arguments: JsonObject, name: str) -> list[int]:
    value = arguments.get(name, [])
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{name} must be a list of integers")
    return value


def _optional_string_list_arg(arguments: JsonObject, name: str) -> list[str] | None:
    if name not in arguments:
        return None
    return string_list_arg(arguments, name)


def _resolve_task_dir(workspace: Path, value: str) -> Path:
    resolved = resolve_workspace_path(workspace, value)
    try:
        resolved.relative_to((workspace / "tasks").resolve())
    except ValueError as error:
        raise ValueError(f"task must be under workspace tasks/: {value}") from error
    return resolved


def _task_property() -> JsonObject:
    return {
        "type": "string",
        "description": "Workspace-relative or absolute task directory under workspace tasks/.",
    }


def _format_property(*values: str, default: str, description: str = "Output format.") -> JsonObject:
    return {"type": "string", "enum": list(values), "default": default, "description": description}


def _string_array_property(default: list[str] | None = None, description: str = "String list.") -> JsonObject:
    return {"type": "array", "items": {"type": "string"}, "default": default or [], "description": description}


def _slot_category_property() -> JsonObject:
    return {"type": "string", "enum": list(SLOT_CATEGORIES), "description": "Task context singleton slot category."}


def _slot_categories_property() -> JsonObject:
    return {
        "type": "array",
        "items": {"type": "string", "enum": list(SLOT_CATEGORIES)},
        "default": [],
        "description": "Optional slot category filter. Empty returns all current non-legacy slots by default.",
    }


def _severity_property(default: str | None = None) -> JsonObject:
    result: JsonObject = {"type": "string", "enum": list(SEVERITIES), "description": "Journal severity filter or value."}
    if default is not None:
        result["default"] = default
    return result


def _status_property(default: str | None = None) -> JsonObject:
    result: JsonObject = {"type": "string", "enum": list(STATUSES), "description": "Journal status filter or value."}
    if default is not None:
        result["default"] = default
    return result


def _query_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "categories": _slot_categories_property(),
            "format": _format_property(
                "text",
                "markdown",
                "agent",
                "json",
                default="text",
                description="Use agent for compact model context or json for structured consumers.",
            ),
            "include_legacy": {"type": "boolean", "description": "Include migrated legacy slot content. Default omits legacy noise.", "default": False},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _set_slot_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "category": _slot_category_property(),
            "content": {"type": "string", "description": "Full replacement content for the singleton slot.", "default": ""},
            "updated_at": {"type": "string", "description": "Optional ISO timestamp override. Omit to use current time."},
            "format": _format_property("text", "markdown", "agent", "json", default="markdown", description="Response format for the updated slot."),
        },
        "required": ["task", "category"],
        "additionalProperties": False,
    }


def _add_entry_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "summary": {"type": "string", "description": "Short factual journal entry summary."},
            "severity": _severity_property("mid"),
            "labels": _string_array_property(description="Optional searchable labels."),
            "status": _status_property("active"),
            "details": {"type": "string", "description": "Additional factual details, commands, paths, or evidence.", "default": ""},
            "source": {"type": "string", "description": "Origin of the entry, usually agent or user.", "default": "agent"},
            "artifacts": _string_array_property(description="Workspace-relative artifact paths associated with the entry."),
            "timestamp": {"type": "string", "description": "Optional ISO timestamp override. Omit to use current time."},
        },
        "required": ["task", "summary"],
        "additionalProperties": False,
    }


def _edit_entries_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "ids": {"type": "array", "items": {"type": "integer"}, "description": "Specific journal entry ids to edit.", "default": []},
            "since": {"type": "string", "description": "Only edit entries at or after this ISO/date timestamp."},
            "until": {"type": "string", "description": "Only edit entries at or before this ISO/date timestamp."},
            "severity": {"type": "string", "description": "Only edit entries matching this severity."},
            "labels": _string_array_property(description="Only edit entries containing these labels."),
            "statuses": {"type": "array", "items": {"type": "string", "enum": list(STATUSES)}, "description": "Only edit entries with these statuses.", "default": []},
            "all": {"type": "boolean", "description": "Edit all entries matching filters. Use carefully.", "default": False},
            "set_status": _status_property(),
            "set_severity": _severity_property(),
            "set_summary": {"type": "string", "description": "Replace summary for matching entries."},
            "set_details": {"type": "string", "description": "Replace details for matching entries."},
            "set_source": {"type": "string", "description": "Replace source for matching entries."},
            "set_labels": _string_array_property(description="Replace labels for matching entries."),
            "add_labels": _string_array_property(description="Add these labels to matching entries."),
            "remove_labels": _string_array_property(description="Remove these labels from matching entries."),
            "clear_labels": {"type": "boolean", "description": "Remove all labels from matching entries.", "default": False},
            "set_artifacts": _string_array_property(description="Replace artifact paths for matching entries."),
            "add_artifacts": _string_array_property(description="Add artifact paths to matching entries."),
            "remove_artifacts": _string_array_property(description="Remove artifact paths from matching entries."),
            "clear_artifacts": {"type": "boolean", "description": "Remove all artifact paths from matching entries.", "default": False},
            "delete": {"type": "boolean", "description": "Delete matching entries instead of editing them.", "default": False},
            "dry_run": {"type": "boolean", "description": "Preview affected entries without writing changes.", "default": False},
            "format": _format_property("text", "markdown", "json", default="text", description="Response format for matched/edited entries."),
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _dictionary_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "format": _format_property("text", "json", default="text", description="Response format for dictionary aliases."),
            "add": _string_array_property(description="Stable terms to add to the task dictionary."),
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _compile_dictionary_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {"task": _task_property()},
        "required": ["task"],
        "additionalProperties": False,
    }


def _compact_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {
            "task": _task_property(),
            "since": {"type": "string", "description": "Only include entries at or after this ISO/date timestamp."},
            "until": {"type": "string", "description": "Only include entries at or before this ISO/date timestamp."},
            "severity": {"type": "string", "description": "Severity filter expression, for example mid..critical.", "default": "mid..critical"},
            "labels": _string_array_property(description="Only include entries containing these labels."),
            "statuses": {"type": "array", "items": {"type": "string", "enum": list(STATUSES)}, "description": "Only include entries with these statuses.", "default": ["active"]},
            "limit": {"type": "integer", "minimum": 1, "description": "Approximate output token budget for compact context.", "default": DEFAULT_COMPACT_LIMIT},
            "agent_context": {"type": "boolean", "description": "Render in the compact format intended for agent prompt injection.", "default": False},
        },
        "required": ["task"],
        "additionalProperties": False,
    }


def _migrate_legacy_input_schema() -> JsonObject:
    return {
        "type": "object",
        "properties": {"task": _task_property()},
        "required": ["task"],
        "additionalProperties": False,
    }
