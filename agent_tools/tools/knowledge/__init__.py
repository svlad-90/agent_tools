"""Topic-scoped workspace knowledge CLI."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Sequence


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_TOPICS_DIR = AGENT_TOOLS_ROOT / "knowledge" / "topics"
PRIVATE_TOPICS_ENV = "AGENT_TOOLS_PRIVATE_KNOWLEDGE_DIR"
KNOWLEDGE_DB_ENV = "AGENT_TOOLS_KNOWLEDGE_DB"
DEFAULT_PRIVATE_TOPICS_DIR = AGENT_TOOLS_ROOT / "knowledge" / "private" / "topics"
DEFAULT_KNOWLEDGE_DB = AGENT_TOOLS_ROOT / "knowledge" / "private" / "knowledge.sqlite3"
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
VALID_STATUSES = ("active", "stale", "superseded")


def _private_topics_dir() -> Path:
    configured = os.environ.get(PRIVATE_TOPICS_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_PRIVATE_TOPICS_DIR


def _knowledge_db_path() -> Path:
    configured = os.environ.get(KNOWLEDGE_DB_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_KNOWLEDGE_DB


def _scope_topics_dir(scope: str) -> Path:
    if scope == "public":
        return PUBLIC_TOPICS_DIR
    if scope == "private":
        return _private_topics_dir()
    raise ValueError(f"unknown knowledge scope: {scope}")


def _validate_topic(topic: str) -> str:
    if not TOPIC_RE.fullmatch(topic):
        raise argparse.ArgumentTypeError("topic must match [a-z0-9][a-z0-9_-]*")
    return topic


def _topic_path(topic: str, *, scope: str) -> Path:
    return _scope_topics_dir(scope) / f"{topic}.md"


def _iter_topic_paths(scope: str) -> list[tuple[str, str, Path]]:
    scopes = ("public", "private") if scope == "all" else (scope,)
    paths: list[tuple[str, str, Path]] = []
    for item_scope in scopes:
        topics_dir = _scope_topics_dir(item_scope)
        if not topics_dir.is_dir():
            continue
        for path in sorted(topics_dir.glob("*.md"), key=lambda candidate: candidate.name.casefold()):
            paths.append((item_scope, path.stem, path))
    return paths


def list_topics(args: argparse.Namespace) -> int:
    for scope, topic, path in _iter_topic_paths(args.scope):
        print(f"{scope}\t{topic}\t{path}")
    return 0


def get_topic(args: argparse.Namespace) -> int:
    found = False
    for scope in _lookup_scopes(args.scope):
        path = _topic_path(args.topic, scope=scope)
        if not path.is_file():
            continue
        if args.with_header:
            print(f"# {scope}:{args.topic}")
            print()
        print(path.read_text(encoding="utf-8").rstrip())
        found = True
        break
    if found:
        return 0
    print(f"knowledge: topic not found: {args.topic}", file=sys.stderr)
    return 1


def set_topic(args: argparse.Namespace) -> int:
    path = _topic_path(args.topic, scope=args.scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    finding = args.finding.strip()
    if not finding:
        print("knowledge: finding must not be empty", file=sys.stderr)
        return 1
    prefix = "" if path.exists() and path.read_text(encoding="utf-8").strip() else f"# {args.topic}\n\n"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(prefix)
        stream.write(f"- {finding}\n")
    print(f"knowledge: wrote {args.scope}:{args.topic} -> {path}")
    return 0


def search_topics(args: argparse.Namespace) -> int:
    query = args.query.casefold()
    matches = 0
    for scope, topic, path in _iter_topic_paths(args.scope):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if query in line.casefold():
                print(f"{scope}:{topic}:{line_no}: {line}")
                matches += 1
    return 0 if matches else 1


def init_db(args: argparse.Namespace) -> int:
    path = _knowledge_db_path_from_args(args)
    _ensure_db(path)
    print(f"knowledge: db ready: {path}")
    return 0


def db_add(args: argparse.Namespace) -> int:
    topic = _validate_topic(args.topic)
    status = _validate_status(args.status)
    scope = args.scope
    text = args.text.strip()
    if not text:
        print("knowledge: text must not be empty", file=sys.stderr)
        return 1
    path = _knowledge_db_path_from_args(args)
    _ensure_db(path)
    created_at = _now()
    with sqlite3.connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO findings(topic, scope, status, text, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (topic, scope, status, text, args.source.strip(), created_at, created_at),
        )
        finding_id = int(cursor.lastrowid)
        for tag in _normalized_tags(args.tag):
            connection.execute(
                "INSERT OR IGNORE INTO tags(finding_id, tag) VALUES (?, ?)",
                (finding_id, tag),
            )
    print(f"knowledge: added #{finding_id} {scope}:{topic}")
    return 0


def db_get(args: argparse.Namespace) -> int:
    path = _knowledge_db_path_from_args(args)
    if not path.is_file():
        print(f"knowledge: db not found: {path}", file=sys.stderr)
        return 1
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            """
            SELECT id, topic, scope, status, text, source, created_at, updated_at
            FROM findings
            WHERE id = ?
            """,
            (args.finding_id,),
        ).fetchone()
        if row is None:
            print(f"knowledge: finding not found: {args.finding_id}", file=sys.stderr)
            return 1
        tags = [
            item[0]
            for item in connection.execute(
                "SELECT tag FROM tags WHERE finding_id = ? ORDER BY tag",
                (args.finding_id,),
            )
        ]
    finding_id, topic, scope, status, text, source, created_at, updated_at = row
    print(f"#{finding_id}\t{scope}:{topic}\t{status}")
    if tags:
        print(f"tags:\t{', '.join(tags)}")
    if source:
        print(f"source:\t{source}")
    print(f"created:\t{created_at}")
    print(f"updated:\t{updated_at}")
    print()
    print(text)
    return 0


def db_search(args: argparse.Namespace) -> int:
    path = _knowledge_db_path_from_args(args)
    if not path.is_file():
        print(f"knowledge: db not found: {path}", file=sys.stderr)
        return 1
    statuses = tuple(VALID_STATUSES) if args.status == "all" else (args.status,)
    scopes = ("public", "private") if args.scope == "all" else (args.scope,)
    query = f"%{args.query.casefold()}%"
    rows: list[tuple[object, ...]]
    with sqlite3.connect(path) as connection:
        placeholders_status = ",".join("?" for _ in statuses)
        placeholders_scope = ",".join("?" for _ in scopes)
        rows = connection.execute(
            f"""
            SELECT id, topic, scope, status, text
            FROM findings
            WHERE status IN ({placeholders_status})
              AND scope IN ({placeholders_scope})
              AND lower(text || ' ' || topic || ' ' || source) LIKE ?
            ORDER BY updated_at DESC, id DESC
            """,
            (*statuses, *scopes, query),
        ).fetchall()
    for finding_id, topic, scope, status, text in rows:
        first_line = str(text).splitlines()[0]
        print(f"#{finding_id}\t{scope}:{topic}\t{status}\t{first_line}")
    return 0 if rows else 1


def db_topics(args: argparse.Namespace) -> int:
    path = _knowledge_db_path_from_args(args)
    if not path.is_file():
        print(f"knowledge: db not found: {path}", file=sys.stderr)
        return 1
    scopes = ("public", "private") if args.scope == "all" else (args.scope,)
    with sqlite3.connect(path) as connection:
        placeholders = ",".join("?" for _ in scopes)
        rows = connection.execute(
            f"""
            SELECT scope, topic, count(*)
            FROM findings
            WHERE scope IN ({placeholders})
            GROUP BY scope, topic
            ORDER BY scope, topic
            """,
            scopes,
        ).fetchall()
    for scope, topic, count in rows:
        print(f"{scope}\t{topic}\t{count}")
    return 0


def _knowledge_db_path_from_args(args: argparse.Namespace) -> Path:
    value = getattr(args, "db", None)
    if value:
        return Path(value).expanduser().resolve()
    return _knowledge_db_path()


def _ensure_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                scope TEXT NOT NULL CHECK(scope IN ('public', 'private')),
                status TEXT NOT NULL CHECK(status IN ('active', 'stale', 'superseded')),
                text TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS findings_topic_idx
                ON findings(topic, scope, status);
            CREATE TABLE IF NOT EXISTS tags (
                finding_id INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
                tag TEXT NOT NULL,
                PRIMARY KEY(finding_id, tag)
            );
            CREATE INDEX IF NOT EXISTS tags_tag_idx ON tags(tag);
            """
        )


def _normalized_tags(values: Sequence[str]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for value in values:
        tag = value.strip().casefold()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def _validate_status(status: str) -> str:
    if status not in VALID_STATUSES:
        raise argparse.ArgumentTypeError(f"status must be one of: {', '.join(VALID_STATUSES)}")
    return status


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lookup_scopes(scope: str) -> tuple[str, ...]:
    if scope == "all":
        return ("private", "public")
    return (scope,)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    list_parser = subparsers.add_parser("list", help="List knowledge topics.")
    list_parser.add_argument("--scope", choices=("all", "public", "private"), default="all")
    list_parser.set_defaults(func=list_topics)

    get_parser = subparsers.add_parser("get", help="Print one topic.")
    get_parser.add_argument("topic", type=_validate_topic)
    get_parser.add_argument("--scope", choices=("all", "public", "private"), default="all")
    get_parser.add_argument("--with-header", action="store_true")
    get_parser.set_defaults(func=get_topic)

    set_parser = subparsers.add_parser("set", help="Append one finding to a topic.")
    set_parser.add_argument("topic", type=_validate_topic)
    set_parser.add_argument("finding")
    set_parser.add_argument("--scope", choices=("public", "private"), default="private")
    set_parser.set_defaults(func=set_topic)

    search_parser = subparsers.add_parser("search", help="Search topic text.")
    search_parser.add_argument("query")
    search_parser.add_argument("--scope", choices=("all", "public", "private"), default="all")
    search_parser.set_defaults(func=search_topics)

    init_db_parser = subparsers.add_parser("db-init", help="Initialize the local SQLite knowledge database.")
    init_db_parser.add_argument("--db", help="Knowledge database path. Default: private knowledge database.")
    init_db_parser.set_defaults(func=init_db)

    add_parser = subparsers.add_parser("db-add", help="Add one finding to the SQLite knowledge database.")
    add_parser.add_argument("topic", type=_validate_topic)
    add_parser.add_argument("text")
    add_parser.add_argument("--scope", choices=("public", "private"), default="private")
    add_parser.add_argument("--status", choices=VALID_STATUSES, default="active")
    add_parser.add_argument("--source", default="")
    add_parser.add_argument("--tag", action="append", default=[])
    add_parser.add_argument("--db", help="Knowledge database path. Default: private knowledge database.")
    add_parser.set_defaults(func=db_add)

    get_db_parser = subparsers.add_parser("db-get", help="Print one SQLite knowledge finding.")
    get_db_parser.add_argument("finding_id", type=int)
    get_db_parser.add_argument("--db", help="Knowledge database path. Default: private knowledge database.")
    get_db_parser.set_defaults(func=db_get)

    db_search_parser = subparsers.add_parser("db-search", help="Search SQLite knowledge findings.")
    db_search_parser.add_argument("query")
    db_search_parser.add_argument("--scope", choices=("all", "public", "private"), default="all")
    db_search_parser.add_argument("--status", choices=("all", *VALID_STATUSES), default="active")
    db_search_parser.add_argument("--db", help="Knowledge database path. Default: private knowledge database.")
    db_search_parser.set_defaults(func=db_search)

    topics_db_parser = subparsers.add_parser("db-topics", help="List SQLite knowledge topics.")
    topics_db_parser.add_argument("--scope", choices=("all", "public", "private"), default="all")
    topics_db_parser.add_argument("--db", help="Knowledge database path. Default: private knowledge database.")
    topics_db_parser.set_defaults(func=db_topics)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
