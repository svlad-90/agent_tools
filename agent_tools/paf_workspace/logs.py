from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Mapping
from pathlib import Path
import os
import shutil
import sys
import time


TASK_PAF_LOG_DIR = Path("report") / "logs" / "paf"
TASK_DIR_ENV_VARS = ("PAF_TASK_DIR", "AGENT_TOOLS_TASK_DIR")
ACTIVE_LOG_DIR = ".active"
PAF_RUN_PREFIX = "paf_"


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


def prepare_paf_log_run(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    run_dir = log_dir / _new_run_name()
    run_dir.mkdir()
    _mark_run_active(log_dir, run_dir)
    _cleanup_paf_log_runs(log_dir, keep_latest_completed=False)
    return run_dir


def finish_paf_log_run(run_dir: Path) -> None:
    log_dir = run_dir.parent
    try:
        (log_dir / ACTIVE_LOG_DIR / run_dir.name).unlink(missing_ok=True)
        _append_run_meta(run_dir, f"finished_at={time.time():.6f}\n")
    except OSError:
        pass
    _cleanup_paf_log_runs(log_dir, keep_latest_completed=True)


def clear_log_dir(log_dir: Path) -> None:
    if not log_dir.is_dir():
        return
    for path in log_dir.iterdir():
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError:
            pass


def _cleanup_paf_log_runs(log_dir: Path, *, keep_latest_completed: bool) -> None:
    if not log_dir.is_dir():
        return
    active = _active_runs(log_dir)
    keep_completed = _overlapping_completed_runs(log_dir, active) if keep_latest_completed else set()
    for path in log_dir.iterdir():
        if path.name == ACTIVE_LOG_DIR:
            _cleanup_empty_active_dir(path)
            continue
        if path.name in active or path.name in keep_completed:
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError:
            pass


def _new_run_name() -> str:
    import uuid
    from datetime import datetime

    stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return f"{PAF_RUN_PREFIX}{stamp}_{os.getpid()}_{uuid.uuid4().hex[:8]}"


def _mark_run_active(log_dir: Path, run_dir: Path) -> None:
    active_dir = log_dir / ACTIVE_LOG_DIR
    active_dir.mkdir(parents=True, exist_ok=True)
    try:
        started_at = time.time()
        (active_dir / run_dir.name).write_text(
            f"pid={os.getpid()}\nstarted_at={started_at:.6f}\n",
            encoding="utf-8",
        )
        (run_dir / "run.meta").write_text(f"started_at={started_at:.6f}\n", encoding="utf-8")
    except OSError:
        pass


def _active_runs(log_dir: Path) -> set[str]:
    active_dir = log_dir / ACTIVE_LOG_DIR
    if not active_dir.is_dir():
        return set()
    return {path.name for path in active_dir.iterdir() if path.is_file()}


def _overlapping_completed_runs(log_dir: Path, active: set[str]) -> set[str]:
    runs = []
    for path in log_dir.iterdir():
        if not path.is_dir() or not path.name.startswith(PAF_RUN_PREFIX) or path.name in active:
            continue
        interval = _run_interval(path)
        if interval is None:
            continue
        runs.append((path.name, interval))
    if not runs:
        return set()
    latest_name, latest_interval = max(runs, key=lambda item: item[1][1])
    keep = {latest_name}
    keep.update(name for name, interval in runs if _intervals_overlap(interval, latest_interval))
    return keep


def _run_interval(run_dir: Path) -> tuple[float, float] | None:
    metadata = _read_key_value_file(run_dir / "run.meta")
    try:
        started = float(metadata["started_at"])
        finished = float(metadata["finished_at"])
    except (KeyError, ValueError):
        return None
    return started, finished


def _intervals_overlap(left: tuple[float, float], right: tuple[float, float]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _append_run_meta(run_dir: Path, text: str) -> None:
    try:
        with (run_dir / "run.meta").open("a", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        pass


def _read_key_value_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def _cleanup_empty_active_dir(active_dir: Path) -> None:
    if not active_dir.is_dir():
        return
    try:
        if not any(active_dir.iterdir()):
            active_dir.rmdir()
    except OSError:
        pass


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
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Remove existing files inside the resolved task-local PAF log directory.",
    )
    parser.add_argument(
        "--prepare-run",
        action="store_true",
        help="Create and print a per-run PAF log directory after cleaning old inactive runs.",
    )
    parser.add_argument(
        "--finish-run",
        type=Path,
        help="Mark a per-run PAF log directory complete and clean old inactive runs.",
    )
    args = parser.parse_args(argv)

    try:
        log_dir = resolve_paf_log_dir(
            workspace_root=args.workspace_root,
            cwd=args.cwd,
            config_path=args.config,
        )
        if args.clear_existing:
            clear_log_dir(log_dir)
        if args.prepare_run:
            print(prepare_paf_log_run(log_dir))
        elif args.finish_run is not None:
            run_dir = args.finish_run.expanduser().resolve()
            if run_dir.parent != log_dir.resolve():
                raise PafLogDirError(f"--finish-run must be inside resolved PAF log directory: {log_dir}")
            finish_paf_log_run(run_dir)
            print(run_dir)
        else:
            print(log_dir)
    except PafLogDirError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
