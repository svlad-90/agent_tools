"""Shared SQLite helpers for task-local agent_tools databases."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3


TASK_CONTEXT_DATABASE_FILENAME = "TASK_CONTEXT.sqlite3"
TASK_DATABASE_BUSY_TIMEOUT_MS = 30_000
TASK_DATABASE_CONNECT_TIMEOUT_SECONDS = TASK_DATABASE_BUSY_TIMEOUT_MS / 1000


def task_database_path(task_dir: Path) -> Path:
    return task_dir / TASK_CONTEXT_DATABASE_FILENAME


@contextmanager
def connect_task_database(task_dir: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(
        task_database_path(task_dir),
        timeout=TASK_DATABASE_CONNECT_TIMEOUT_SECONDS,
    )
    configure_task_database_connection(connection)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def configure_task_database_connection(connection: sqlite3.Connection) -> None:
    connection.execute(f"PRAGMA busy_timeout = {TASK_DATABASE_BUSY_TIMEOUT_MS}")


def configure_task_database_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
