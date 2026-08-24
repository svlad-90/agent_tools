from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


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
    return [report_harness_adapter_ready(task_dir)]


def report_harness_adapter_ready(task_dir: Path) -> ActualizeResult:
    return ActualizeResult(
        "PASS",
        "actualize-harness-adapter-ready",
        "task uses hook-driven harness adapter; no task-local front door bell is required",
        str(task_dir),
    )


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
