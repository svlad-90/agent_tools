from __future__ import annotations

from pathlib import Path
import shlex
import sys

from .core import PAF_HIDE_TASK_ENV_VAR
from .core import TASK_ACTION_LOGS_DIR
from .core import TaskAction
from .core import TaskSummary
from .core import agent_executable
from .core import task_action_log_basename


def task_check_shell_command(workspace: Path, task: TaskSummary) -> str:
    return " ".join(
        [
            "cd",
            shlex.quote(str(workspace)),
            "&&",
            shlex.join(
                [
                    sys_executable(),
                    "-m",
                    "agent_tools.tools.agent_workspace.actions",
                    "task-check",
                    "--workspace",
                    str(workspace),
                    "--task",
                    str(task.path),
                ]
            ),
        ]
    )


def task_action_shell_command(action: TaskAction) -> str:
    command = action.command if isinstance(action.command, str) else shlex.join(action.command)
    env_values = dict(action.env)
    env_values[PAF_HIDE_TASK_ENV_VAR] = "1"
    env = " ".join(
        f"{key}={shlex.quote(value)}"
        for key, value in sorted(env_values.items())
    )
    prefix = f"{env} " if env else ""
    log_name = task_action_log_basename(action.action_id)
    inner = "\n".join(
        [
            "set -o pipefail",
            "__agent_task_dir=$PWD",
            'while [ "$__agent_task_dir" != "/" ] && [ ! -f "$__agent_task_dir/TASK_DESCRIPTION.md" ]; do',
            '    __agent_task_dir=$(dirname "$__agent_task_dir")',
            "done",
            'if [ ! -f "$__agent_task_dir/TASK_DESCRIPTION.md" ]; then',
            "    __agent_task_dir=$PWD",
            "fi",
            f"__agent_log_dir=\"$__agent_task_dir/{TASK_ACTION_LOGS_DIR.as_posix()}\"",
            'mkdir -p "$__agent_log_dir"',
            f"__agent_log=\"$__agent_log_dir/{log_name}-$(date +%Y%m%d-%H%M%S).log\"",
            'echo "Logging task action to $__agent_log"',
            f"({prefix}{command}) 2>&1 | tee -a \"$__agent_log\"",
            "exit ${PIPESTATUS[0]}",
        ]
    )
    return f"cd {shlex.quote(str(action.cwd))} && bash -lc {shlex.quote(inner)}"


def sys_executable() -> str:
    return sys.executable or "python3"


def codex_executable() -> str:
    return agent_executable("codex") or "codex"


def claude_executable() -> str:
    return agent_executable("claude") or "claude"
