from __future__ import annotations

from pathlib import Path

from agent_tools.lib.database import TASK_CONTEXT_DATABASE_FILENAME
from agent_tools.lib.database import TASK_DATABASE_BUSY_TIMEOUT_MS
from agent_tools.lib.database import connect_task_database
from agent_tools.lib.database import configure_task_database_schema
from agent_tools.lib.database import task_database_path


def test_task_database_path_uses_task_context_sqlite_name(tmp_path: Path) -> None:
    assert task_database_path(tmp_path) == tmp_path / TASK_CONTEXT_DATABASE_FILENAME


def test_connect_task_database_sets_busy_timeout(tmp_path: Path) -> None:
    with connect_task_database(tmp_path) as connection:
        timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]

    assert timeout == TASK_DATABASE_BUSY_TIMEOUT_MS


def test_configure_task_database_schema_uses_wal(tmp_path: Path) -> None:
    with connect_task_database(tmp_path) as connection:
        configure_task_database_schema(connection)
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]

    assert journal_mode.lower() == "wal"
    assert synchronous == 1
