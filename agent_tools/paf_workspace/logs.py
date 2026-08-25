from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Mapping
from pathlib import Path
import os
import sys


TASK_PAF_LOG_DIR = Path("report") / "logs" / "paf"
TASK_DIR_ENV_VARS = ("PAF_TASK_DIR", "AGENT_TOOLS_TASK_DIR")


class PafLogDirError(ValueError):
    pass


def resolve_paf_log_dir(
    *,
    workspace_root: Path,
    cwd: Path,
    config_path: Path,
    env: Mapping[str, str] = os.environ,
) -> Path:
    workspace_root = workspace_root.resolve()
    for name in TASK_DIR_ENV_VARS:
        value = env.get(name)
        if value:
            return _validated_task_dir(Path(value), workspace_root, source=name) / TASK_PAF_LOG_DIR

    for candidate in (cwd, _resolve_path(cwd, config_path)):
        task_dir = _task_dir_from_path(candidate, workspace_root)
        if task_dir is not None and _looks_like_task_dir(task_dir):
            return task_dir / TASK_PAF_LOG_DIR

    raise PafLogDirError(
        "cannot resolve task-local PAF log directory; run from a task directory "
        "or set PAF_TASK_DIR/AGENT_TOOLS_TASK_DIR to a directory under tasks/"
    )


def _validated_task_dir(path: Path, workspace_root: Path, *, source: str) -> Path:
    task_dir = _task_dir_from_path(path, workspace_root)
    if task_dir is None or task_dir.resolve() != path.expanduser().resolve():
        raise PafLogDirError(f"{source} must point to a top-level task directory under {workspace_root / 'tasks'}")
    if not _looks_like_task_dir(task_dir):
        raise PafLogDirError(f"{source} does not point to an existing task directory: {task_dir}")
    return task_dir


def _resolve_path(cwd: Path, path: Path) -> Path:
    path = path.expanduser()
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _task_dir_from_path(path: Path, workspace_root: Path) -> Path | None:
    path = path.expanduser().resolve()
    try:
        rel = path.relative_to(workspace_root)
    except ValueError:
        return None
    if len(rel.parts) < 2 or rel.parts[0] != "tasks":
        return None
    return workspace_root / "tasks" / rel.parts[1]


def _looks_like_task_dir(path: Path) -> bool:
    return path.is_dir() and (path / "TASK_CONTEXT.sqlite3").is_file()


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="Resolve the mandatory task-local PAF log directory.")
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        print(
            resolve_paf_log_dir(
                workspace_root=args.workspace_root,
                cwd=args.cwd,
                config_path=args.config,
            )
        )
    except PafLogDirError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
