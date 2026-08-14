"""Topic-scoped workspace knowledge CLI."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Sequence


AGENT_TOOLS_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_TOPICS_DIR = AGENT_TOOLS_ROOT / "knowledge" / "topics"
PRIVATE_TOPICS_ENV = "AGENT_TOOLS_PRIVATE_KNOWLEDGE_DIR"
DEFAULT_PRIVATE_TOPICS_DIR = AGENT_TOOLS_ROOT / "knowledge" / "private" / "topics"
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _private_topics_dir() -> Path:
    configured = os.environ.get(PRIVATE_TOPICS_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_PRIVATE_TOPICS_DIR


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

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
