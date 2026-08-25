from __future__ import annotations

from datetime import datetime
import faulthandler
import io
import os
from pathlib import Path
import sys
import threading
import traceback
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows runners.
    fcntl = None


AGENT_WORKSPACE_CRASH_LOG_FILE = "agent-workspace-crash.log"
AGENT_WORKSPACE_LOCK_FILE = ".agent-workspace.lock"

_CRASH_LOG_HANDLE: Any | None = None
_PREVIOUS_EXCEPTHOOK: Any | None = None
_PREVIOUS_THREADING_EXCEPTHOOK: Any | None = None


def agent_workspace_crash_log_path(workspace: Path) -> Path:
    return workspace.resolve() / AGENT_WORKSPACE_CRASH_LOG_FILE


def agent_workspace_lock_path(workspace: Path) -> Path:
    return workspace.resolve() / AGENT_WORKSPACE_LOCK_FILE


def acquire_agent_workspace_lock(workspace: Path) -> io.TextIOWrapper | None:
    if fcntl is None:
        return None
    lock_path = agent_workspace_lock_path(workspace)
    try:
        handle = lock_path.open("w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        return handle
    except BlockingIOError:
        return None
    except OSError:
        return None


def log_agent_workspace_exception(
    workspace: Path,
    frontend: str,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: Any,
) -> None:
    log_path = agent_workspace_crash_log_path(workspace)
    try:
        with log_path.open("a", encoding="utf-8") as stream:
            timestamp = datetime.now().isoformat(timespec="seconds")
            stream.write(f"\n[{timestamp}] Agent Workspace {frontend} exception pid={os.getpid()}\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=stream)
            stream.flush()
    except OSError:
        return


def install_agent_workspace_exception_logger(workspace: Path, frontend: str) -> Path:
    global _CRASH_LOG_HANDLE
    global _PREVIOUS_EXCEPTHOOK
    global _PREVIOUS_THREADING_EXCEPTHOOK

    workspace = workspace.resolve()
    log_path = agent_workspace_crash_log_path(workspace)
    try:
        _CRASH_LOG_HANDLE = log_path.open("a", encoding="utf-8")
        timestamp = datetime.now().isoformat(timespec="seconds")
        _CRASH_LOG_HANDLE.write(f"\n[{timestamp}] Agent Workspace {frontend} started pid={os.getpid()}\n")
        _CRASH_LOG_HANDLE.flush()
        faulthandler.enable(file=_CRASH_LOG_HANDLE, all_threads=True)
    except OSError:
        _CRASH_LOG_HANDLE = None

    if _PREVIOUS_EXCEPTHOOK is None:
        _PREVIOUS_EXCEPTHOOK = sys.excepthook
    if _PREVIOUS_THREADING_EXCEPTHOOK is None and hasattr(threading, "excepthook"):
        _PREVIOUS_THREADING_EXCEPTHOOK = threading.excepthook

    def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        log_agent_workspace_exception(workspace, frontend, exc_type, exc_value, exc_traceback)
        if _PREVIOUS_EXCEPTHOOK is not None:
            _PREVIOUS_EXCEPTHOOK(exc_type, exc_value, exc_traceback)

    def threading_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is not None and args.exc_value is not None:
            log_agent_workspace_exception(workspace, frontend, args.exc_type, args.exc_value, args.exc_traceback)
        if _PREVIOUS_THREADING_EXCEPTHOOK is not None:
            _PREVIOUS_THREADING_EXCEPTHOOK(args)

    sys.excepthook = excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = threading_excepthook
    return log_path


def abort_agent_workspace_with_stack_dump(workspace: Path, frontend: str) -> None:
    log_path = agent_workspace_crash_log_path(workspace)
    try:
        with log_path.open("a", encoding="utf-8") as stream:
            timestamp = datetime.now().isoformat(timespec="seconds")
            stream.write(f"\n[{timestamp}] Agent Workspace {frontend} forced stack dump pid={os.getpid()}\n")
            faulthandler.dump_traceback(file=stream, all_threads=True)
            stream.flush()
    except OSError:
        pass
    os.abort()
