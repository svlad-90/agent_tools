from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...artifacts.api import artifact_relative_label
from ...artifacts.api import artifact_updated_label
from ...artifacts.api import task_artifact_entries
from ...commands.api import task_action_command
from ...commands.api import task_check_command
from ...task_actions.api import TaskAction
from ...task_actions.api import load_task_actions_config
from ...task_catalog.api import TaskSummary
from ...task_catalog.api import discover_tasks
from ...task_catalog.api import run_task_check
from ...task_context.api import load_task_context_slots
from ...task_context.api import render_task_context_slots
from ...task_context.api import slot_dictionary_data
from ...task_context.api import task_goal_slot_markdown


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
            "description": task_goal_slot_markdown(task.path),
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
            "dictionary": slot_dictionary_data(task.path, markdown) if encoded else [],
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
