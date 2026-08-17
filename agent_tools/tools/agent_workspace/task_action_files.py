from __future__ import annotations

from pathlib import Path
import shlex

from .core import TaskAction


def task_action_code_path(action: TaskAction) -> Path | None:
    command = action.command
    if isinstance(command, str):
        try:
            tokens = shlex.split(command)
        except ValueError:
            return None
    else:
        tokens = list(command)
    if not tokens:
        return None
    script_index = 1 if tokens[0] in {"bash", "sh", "python", "python3"} and len(tokens) > 1 else 0
    candidate = Path(tokens[script_index])
    if not candidate.is_absolute():
        candidate = action.cwd / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(action.cwd.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None
