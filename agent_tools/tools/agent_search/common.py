from __future__ import annotations

import os

import regex

from .models import AgentSearchError


TEXT_BYTES_LIMIT = 2_000_000


def compile_query(query: str, *, fixed: bool, case_sensitive: bool, ignore_case: bool) -> regex.Pattern[str]:
    if case_sensitive and ignore_case:
        raise AgentSearchError("--case-sensitive and --ignore-case are mutually exclusive")
    pattern = regex.escape(query) if fixed else query
    flags = regex.MULTILINE
    if ignore_case or (not case_sensitive and query.lower() == query):
        flags |= regex.IGNORECASE
    try:
        return regex.compile(pattern, flags)
    except regex.error as error:
        raise AgentSearchError(f"invalid regex: {error}") from error


def normalized_threads(threads: int | None) -> int:
    if threads is None:
        cpu_count = os.cpu_count() or 1
        return max(1, cpu_count // 2)
    return max(1, threads)


def normalize_extension(extension: str) -> str:
    lowered = extension.lower()
    if not lowered.startswith("."):
        return f".{lowered}"
    return lowered


def trim(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."
