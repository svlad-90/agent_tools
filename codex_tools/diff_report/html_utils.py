from __future__ import annotations

import html
import re


def anchor(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)


def comment_anchor(file_path: str, line: int) -> str:
    return f"comment-{anchor(file_path)}-{line}"


def line_anchor(file_path: str, line: int) -> str:
    return f"line-{anchor(file_path)}-{line}"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_text(value: object) -> str:
    text = str(value)
    url_re = re.compile(r"https?://[^\s<>'\"`]+")
    parts: list[str] = []
    last = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal last
        parts.append(esc(text[last:match.start()]))
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
    parts.append(esc(text[last:]))
    return "".join(parts)
