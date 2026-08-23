from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


FRONT_DOOR_BELL_FILE = "front_door_bell.py"


@dataclass(frozen=True)
class ActualizeResult:
    status: str
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {
            "status": self.status,
            "code": self.code,
            "message": self.message,
        }
        if self.path is not None:
            result["path"] = self.path
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Actualize an existing workspace task for current tools.")
    parser.add_argument("--task", required=True, help="Task directory to actualize.")
    parser.add_argument("--workspace", default=".", help="Workspace root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    workspace = Path(args.workspace).resolve()
    task_dir = _resolve_task_dir(workspace, args.task)
    results = actualize_task(task_dir, workspace=workspace)
    if args.json:
        print(json.dumps([result.as_dict() for result in results], indent=2, sort_keys=True))
    else:
        print(render_text(results))
    return 1 if any(result.status == "FAIL" for result in results) else 0


def actualize_task(task_dir: Path, *, workspace: Path) -> list[ActualizeResult]:
    task_dir = task_dir.resolve()
    workspace = workspace.resolve()
    try:
        task_dir.relative_to(workspace)
    except ValueError:
        return [
            ActualizeResult(
                "FAIL",
                "actualize-outside-workspace",
                "refusing to actualize task outside workspace",
                str(task_dir),
            )
        ]
    if not task_dir.exists() or not task_dir.is_dir():
        return [
            ActualizeResult(
                "FAIL",
                "actualize-task-dir-missing",
                "task directory does not exist",
                str(task_dir),
            )
        ]
    return [ensure_front_door_bell(task_dir)]


def ensure_front_door_bell(task_dir: Path) -> ActualizeResult:
    front_door_path = task_dir / FRONT_DOOR_BELL_FILE
    if front_door_path.is_file():
        return ActualizeResult(
            "PASS",
            "actualize-front-door-bell-existing",
            f"{FRONT_DOOR_BELL_FILE} already exists",
            str(front_door_path),
        )
    if front_door_path.exists():
        return ActualizeResult(
            "FAIL",
            "actualize-front-door-bell-blocked",
            f"{FRONT_DOOR_BELL_FILE} exists but is not a file",
            str(front_door_path),
        )

    front_door_path.write_text(front_door_bell_script(), encoding="utf-8")
    if os.name != "nt":
        front_door_path.chmod(front_door_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return ActualizeResult(
        "PASS",
        "actualize-front-door-bell-created",
        f"created {FRONT_DOOR_BELL_FILE}",
        str(front_door_path),
    )


def front_door_bell_script() -> str:
    return """#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


TASK_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = TASK_DIR.parent.parent if TASK_DIR.parent.name == "tasks" else Path.cwd()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from agent_tools.tools.front_desk_bell import main


if __name__ == "__main__":
    raise SystemExit(main(["--task", str(TASK_DIR), "--workspace", str(WORKSPACE_ROOT), *sys.argv[1:]]))
"""


def render_text(results: list[ActualizeResult]) -> str:
    lines = []
    for result in results:
        path = f" ({result.path})" if result.path else ""
        lines.append(f"[{result.status}] {result.code}: {result.message}{path}")
    return "\n".join(lines)


def _resolve_task_dir(workspace: Path, task: str) -> Path:
    path = Path(task)
    if path.is_absolute():
        return path.resolve()
    return (workspace / path).resolve()
