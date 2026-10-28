from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Any
from uuid import uuid4

from agent_tools.tools.task_context import compile_dictionary
from agent_tools.tools.task_context import DATABASE_FILENAME as TASK_CONTEXT_DATABASE_FILE

from ...artifacts.api import artifact_relative_label
from ...artifacts.api import artifact_text_preview
from ...artifacts.api import artifact_updated_label
from ...artifacts.api import task_artifact_entries
from ...commands.api import task_action_command
from ...commands.api import task_check_command
from ...harness_adapter.api import load_harness_debug_events
from ...task_actions.api import TaskAction
from ...task_actions.api import load_task_actions_config
from ...task_catalog.api import TaskSummary
from ...task_catalog.api import discover_tasks
from ...task_catalog.api import run_task_check
from ...task_catalog.api import task_init_command
from ...task_catalog.api import task_path_for_name
from ...task_context.api import load_task_context_slots
from ...task_context.api import render_task_context_slots
from ...task_context.api import set_task_context_slot
from ...task_context.api import slot_dictionary_data
from ...task_context.api import task_goal_slot_markdown
from ...web_terminal.api import WebTerminalManager
from ...web_terminal.api import WebTerminalSession
from ...web_terminal.api import shell_command
from ...web_terminal.api import shell_environment


DEFAULT_CONTEXT_SEVERITY = ("mid", "high", "critical")
DEFAULT_CONTEXT_STATUS = ("active",)
TASK_CREATION_TIMEOUT_SECONDS = 30


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
        self._task_creation_lock = threading.Lock()
        self._terminals = WebTerminalManager()
        self._terminal_lifecycle_lock = threading.Lock()
        self._terminal_lifecycle_state = "running"

    def tasks(self) -> list[dict[str, Any]]:
        return [task_summary_data(task) for task in discover_tasks(self.workspace)]

    def create_task(self, task_name: str, *, privacy: str = "public") -> dict[str, Any]:
        task_name = task_name.strip()
        if privacy not in {"public", "private"}:
            raise ValueError(f"invalid task privacy: {privacy}")
        task_path = task_path_for_name(self.workspace, task_name)
        if task_path is None:
            raise ValueError(f"invalid task name: {task_name}")
        with self._task_creation_lock:
            tasks_root = task_path.parent
            tasks_root.mkdir(parents=True, exist_ok=True)
            if task_path.exists():
                raise ValueError(f"task already exists: {task_name}")
            staging_path = tasks_root / f".agent-workspace-create-{uuid4().hex}"
            staging_path.mkdir()
            try:
                result = subprocess.run(
                    task_init_command(self.workspace, staging_path, privacy=privacy),
                    cwd=self.workspace,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=TASK_CREATION_TIMEOUT_SECONDS,
                )
                if result.returncode != 0:
                    message = (result.stderr or result.stdout or "task init failed").strip()
                    raise RuntimeError(message)
                if not (staging_path / TASK_CONTEXT_DATABASE_FILE).is_file():
                    raise RuntimeError("task init did not create the context database")
                try:
                    task_path.mkdir()
                except FileExistsError:
                    raise ValueError(f"task already exists: {task_name}") from None
                try:
                    children = sorted(
                        staging_path.iterdir(),
                        key=lambda child: (child.name == TASK_CONTEXT_DATABASE_FILE, child.name),
                    )
                    for child in children:
                        child.rename(task_path / child.name)
                except Exception as error:
                    raise RuntimeError(
                        f"task layout publication failed; partial task remains at {task_path}"
                    ) from error
                try:
                    if staging_path.exists():
                        shutil.rmtree(staging_path)
                except OSError:
                    pass
            except Exception:
                if staging_path.exists():
                    shutil.rmtree(staging_path)
                raise
        task = TaskSummary(task_path.name, task_path, True, True, 0, 0, False)
        return {"task": task_summary_data(task)}

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
            "ai_debug": self.ai_debug_events(task_name),
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
        return self._task_context(task, filters=filters, encoded=encoded)

    def _task_context(
        self,
        task: TaskSummary,
        *,
        filters: TaskContextFilters | None = None,
        encoded: bool = False,
    ) -> dict[str, Any]:
        filters = filters or TaskContextFilters()
        if encoded:
            compile_dictionary(task.path)
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

    def save_task_context_slot(
        self,
        task_name: str,
        category: str,
        content: str,
    ) -> dict[str, Any]:
        task = self.task(task_name)
        slot = set_task_context_slot(task.path, category, content)
        return {
            "slot": slot.to_json(),
            "context": self._task_context(task),
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

    def artifact_content(self, task_name: str, label: str) -> dict[str, object]:
        return artifact_text_preview(self.task(task_name), label)

    def ai_debug_events(self, task_name: str, *, session_id: str | None = None) -> list[dict[str, Any]]:
        task = self.task(task_name)
        return [
            event.to_json()
            for event in load_harness_debug_events(task.path, session_id=session_id)
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

    def terminal_sessions(self, task_name: str) -> list[dict[str, Any]]:
        self.task(task_name)
        return [session.to_json() for session in self._terminals.sessions(task_name)]

    def all_terminal_sessions(self) -> list[dict[str, Any]]:
        return [session.to_json() for session in self._terminals.sessions()]

    def start_shell_terminal(self, task_name: str) -> dict[str, Any]:
        task = self.task(task_name)
        with self._terminal_lifecycle_lock:
            if self._terminal_lifecycle_state != "running":
                raise RuntimeError("terminal service is shut down")
            session = self._terminals.start(
                task_name=task.name,
                task_path=task.path,
                command=shell_command(),
                cwd=task.path,
                env=shell_environment(dict(os.environ), task.name),
                kind="shell",
            )
            sessions = [item.to_json() for item in self._terminals.sessions(task.name)]
        return {"session": session.to_json(), "sessions": sessions}

    def send_terminal_input(self, task_name: str, session_id: str, data: str) -> dict[str, Any]:
        self._task_terminal_session(task_name, session_id)
        self._terminals.send(session_id, data)
        return {"id": session_id, "accepted": True}

    def resize_terminal(
        self,
        task_name: str,
        session_id: str,
        *,
        rows: int,
        columns: int,
    ) -> dict[str, Any]:
        self._task_terminal_session(task_name, session_id)
        return self._terminals.resize(session_id, rows=rows, columns=columns)

    def terminal_output(self, task_name: str, session_id: str, *, offset: int = 0) -> dict[str, Any]:
        self._task_terminal_session(task_name, session_id)
        return self._terminals.output(session_id, offset=offset)

    def close_terminal(self, task_name: str, session_id: str) -> dict[str, Any]:
        with self._terminal_lifecycle_lock:
            session = self._task_terminal_session(task_name, session_id)
            closed = self._terminals.close(session_id)
        session_data = session.to_json()
        session_data["exited"] = True
        return {"closed": closed, "session": session_data}

    def shutdown(self) -> None:
        failures: list[Exception] = []
        with self._terminal_lifecycle_lock:
            if self._terminal_lifecycle_state == "shut-down":
                return
            self._terminal_lifecycle_state = "shutting-down"
            for session in self._terminals.sessions():
                try:
                    self._terminals.close(session.session_id)
                except KeyError:
                    continue
                except Exception as error:
                    failures.append(error)
            self._terminal_lifecycle_state = "shutdown-failed" if failures else "shut-down"
        if failures:
            raise RuntimeError("failed to close all terminal sessions") from failures[0]

    def _task_terminal_session(self, task_name: str, session_id: str) -> WebTerminalSession:
        task = self.task(task_name)
        session = self._terminals.session(session_id)
        if session.task_name != task.name:
            raise KeyError(f"unknown terminal session for task {task.name}: {session_id}")
        return session


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
