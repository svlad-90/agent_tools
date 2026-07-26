from __future__ import annotations

import html
import re
from collections.abc import Sequence

from .models import VocabularyTerm


def anchor(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)


def comment_anchor(file_path: str, line: int) -> str:
    return f"comment-{anchor(file_path)}-{line}"


def line_anchor(file_path: str, line: int) -> str:
    return f"line-{anchor(file_path)}-{line}"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_text(value: object, vocabulary: Sequence[VocabularyTerm] = ()) -> str:
    text = str(value)
    url_re = re.compile(r"https?://[^\s<>'\"`]+")
    parts: list[str] = []
    last = 0
    term_re, term_lookup = vocabulary_matcher(vocabulary)

    def repl(match: re.Match[str]) -> str:
        nonlocal last
        parts.append(format_plain_text(text[last:match.start()], term_re, term_lookup))
        raw_url = match.group(0)
        url = raw_url.rstrip(".,);")
        suffix = raw_url[len(url):]
        safe_url = esc(url)
        parts.append(
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>'
        )
        parts.append(esc(suffix))
        last = match.end()
        return ""

    url_re.sub(repl, text)
    parts.append(format_plain_text(text[last:], term_re, term_lookup))
    return "".join(parts)


def vocabulary_matcher(
    vocabulary: Sequence[VocabularyTerm],
) -> tuple[re.Pattern[str] | None, dict[str, VocabularyTerm]]:
    lookup: dict[str, VocabularyTerm] = {}
    tokens: list[str] = []
    for entry in vocabulary:
        for token in (entry.term, *entry.aliases):
            normalized = token.strip()
            if not normalized:
                continue
            key = normalized.casefold()
            if key in lookup:
                continue
            lookup[key] = entry
            tokens.append(normalized)
    if not tokens:
        return None, {}
    escaped = sorted((re.escape(token) for token in tokens), key=len, reverse=True)
    pattern = r"(?<![A-Za-z0-9_])(" + "|".join(escaped) + r")(?![A-Za-z0-9_])"
    return re.compile(pattern, re.IGNORECASE), lookup


def format_plain_text(
    text: str,
    term_re: re.Pattern[str] | None,
    term_lookup: dict[str, VocabularyTerm],
) -> str:
    if term_re is None:
        return esc(text)
    parts: list[str] = []
    last = 0
    for match in term_re.finditer(text):
        parts.append(esc(text[last:match.start()]))
        matched_text = match.group(0)
        entry = term_lookup.get(matched_text.casefold())
        if entry is None:
            parts.append(esc(matched_text))
        else:
            parts.append(
                '<span class="vocabulary-ref-wrap">'
                f'<button type="button" class="vocabulary-ref" data-term="{esc(entry.term)}">'
                f'{esc(matched_text)}</button>'
                '<span class="vocabulary-popover" role="tooltip">'
                f'<strong>{esc(entry.term)}</strong>'
                f'<span>{esc(entry.definition)}</span>'
                "</span></span>"
            )
        last = match.end()
    parts.append(esc(text[last:]))
    return "".join(parts)
