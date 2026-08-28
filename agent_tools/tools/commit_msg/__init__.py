from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path


DEFAULT_WIDTH = 72


@dataclass(frozen=True)
class GitIdentity:
    name: str
    email: str

    @property
    def signoff(self) -> str:
        return f"Signed-off-by: {self.name} <{self.email}>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Format a git commit message and add a Signed-off-by trailer.",
    )
    parser.add_argument(
        "message_file",
        nargs="?",
        help="Draft commit message file. Reads stdin when omitted or '-'.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path used to read git user.name and user.email.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Body wrap width. Default: 72.",
    )
    parser.add_argument(
        "--output",
        help="Write formatted message to this file instead of stdout.",
    )
    parser.add_argument("--title", help="Commit subject/title.")
    parser.add_argument(
        "--body",
        action="append",
        default=[],
        help="Commit body paragraph. May be passed more than once.",
    )
    parser.add_argument(
        "--body-file",
        action="append",
        default=[],
        help="Read commit body text from a file. May be passed more than once.",
    )
    parser.add_argument(
        "--signoff",
        nargs="?",
        const="",
        action="append",
        default=[],
        metavar="NAME <EMAIL>",
        help="Add Signed-off-by. Without a value, use repo git identity.",
    )
    parser.add_argument(
        "--assisted-by",
        action="append",
        default=[],
        metavar="AGENT:MODEL [TOOLS]",
        help="Add an Assisted-by trailer. May be passed more than once.",
    )
    parser.add_argument(
        "--reviewed-by",
        action="append",
        default=[],
        metavar="NAME <EMAIL>",
        help="Add a Reviewed-by trailer. May be passed more than once.",
    )
    parser.add_argument(
        "--tested-by",
        action="append",
        default=[],
        metavar="NAME <EMAIL>",
        help="Add a Tested-by trailer. May be passed more than once.",
    )
    parser.add_argument(
        "--acked-by",
        action="append",
        default=[],
        metavar="NAME <EMAIL>",
        help="Add an Acked-by trailer. May be passed more than once.",
    )
    parser.add_argument(
        "--trailer",
        action="append",
        default=[],
        metavar="KEY: VALUE",
        help="Add an arbitrary trailer line. May be passed more than once.",
    )
    parser.add_argument(
        "--no-signoff",
        action="store_true",
        help="Do not add a Signed-off-by trailer.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the formatted message has lines longer than --width.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    repo = Path(args.repo)
    if _has_compose_args(args):
        message = compose_commit_message(
            title=args.title,
            body=args.body,
            body_files=[Path(path) for path in args.body_file],
            signoffs=args.signoff,
            assisted_by=args.assisted_by,
            reviewed_by=args.reviewed_by,
            tested_by=args.tested_by,
            acked_by=args.acked_by,
            trailers=args.trailer,
            repo=repo,
        )
    else:
        message = _read_message(args.message_file)

    identity = None
    if not args.no_signoff and not args.signoff:
        identity = read_git_identity(repo)
    formatted = format_commit_message(message, width=args.width, identity=identity)

    if args.check:
        long_lines = find_long_lines(formatted, width=args.width)
        if long_lines:
            for line_no, length, line in long_lines:
                print(f"{line_no}:{length}:{line}", file=sys.stderr)
            return 1

    if args.output:
        Path(args.output).write_text(formatted, encoding="utf-8")
    else:
        sys.stdout.write(formatted)
    return 0


def format_commit_message(
    message: str,
    *,
    width: int = DEFAULT_WIDTH,
    identity: GitIdentity | None = None,
) -> str:
    lines = _normalize_lines(message)
    content_lines, trailer_lines = _split_trailers(lines)
    content_lines = _strip_blank_edges(content_lines)

    if not content_lines:
        raise ValueError("commit message is empty")

    subject = " ".join(part.strip() for part in content_lines[0].splitlines()).strip()
    body_lines = _strip_blank_edges(content_lines[1:])
    formatted_body = _format_body(body_lines, width=width)

    trailers = _assisted_by_last(trailer_lines)
    if identity is not None:
        trailers = [line for line in trailers if not line.startswith("Signed-off-by:")]
        trailers.append(identity.signoff)
        trailers = _assisted_by_last(trailers)

    result = [subject]
    if formatted_body:
        result.extend(["", *formatted_body])
    if trailers:
        result.extend(["", *trailers])

    return "\n".join(result).rstrip() + "\n"


def compose_commit_message(
    *,
    title: str | None,
    body: list[str],
    body_files: list[Path],
    signoffs: list[str],
    assisted_by: list[str],
    reviewed_by: list[str],
    tested_by: list[str],
    acked_by: list[str],
    trailers: list[str],
    repo: Path,
) -> str:
    if not title:
        raise ValueError("--title is required when composing a commit message")

    lines = [title.strip()]
    body_lines = _compose_body_lines(body, body_files)
    if body_lines:
        lines.extend(["", *body_lines])

    trailer_lines: list[str] = []
    for signoff in signoffs:
        value = signoff.strip() if signoff else read_git_identity(repo).signoff
        trailer_lines.append(_normalize_trailer("Signed-off-by", value))
    for value in reviewed_by:
        trailer_lines.append(_normalize_trailer("Reviewed-by", value))
    for value in tested_by:
        trailer_lines.append(_normalize_trailer("Tested-by", value))
    for value in acked_by:
        trailer_lines.append(_normalize_trailer("Acked-by", value))
    for value in assisted_by:
        trailer_lines.append(_normalize_trailer("Assisted-by", value))
    for trailer in trailers:
        if not _is_trailer_line(trailer):
            raise ValueError(f"invalid trailer: {trailer}")
        trailer_lines.append(trailer.strip())

    if trailer_lines:
        lines.extend(["", *_assisted_by_last(trailer_lines)])

    return "\n".join(lines).rstrip() + "\n"


def read_git_identity(repo: Path) -> GitIdentity:
    name = _git_config(repo, "user.name")
    email = _git_config(repo, "user.email")
    if not name or not email:
        raise ValueError("git user.name and user.email must be configured")
    return GitIdentity(name=name, email=email)


def find_long_lines(message: str, *, width: int = DEFAULT_WIDTH) -> list[tuple[int, int, str]]:
    return [
        (line_no, len(line), line)
        for line_no, line in enumerate(message.splitlines(), start=1)
        if len(line) > width and not _is_trailer_line(line)
    ]


def _has_compose_args(args: argparse.Namespace) -> bool:
    return any(
        (
            args.title,
            args.body,
            args.body_file,
            args.signoff,
            args.assisted_by,
            args.reviewed_by,
            args.tested_by,
            args.acked_by,
            args.trailer,
        )
    )


def _compose_body_lines(body: list[str], body_files: list[Path]) -> list[str]:
    lines: list[str] = []
    for paragraph in body:
        if lines:
            lines.append("")
        lines.extend(_strip_blank_edges(_normalize_lines(paragraph)))
    for body_file in body_files:
        if lines:
            lines.append("")
        lines.extend(_strip_blank_edges(_normalize_lines(body_file.read_text(encoding="utf-8"))))
    return _strip_blank_edges(lines)


def _normalize_trailer(key: str, value: str) -> str:
    value = value.strip()
    if value.startswith(f"{key}: "):
        return value
    if _is_trailer_line(value):
        return value
    return f"{key}: {value}"


def _assisted_by_last(trailer_lines: list[str]) -> list[str]:
    regular = [line for line in trailer_lines if not line.startswith("Assisted-by:")]
    assisted = [line for line in trailer_lines if line.startswith("Assisted-by:")]
    return [*regular, *assisted]


def _read_message(message_file: str | None) -> str:
    if message_file is None or message_file == "-":
        return sys.stdin.read()
    return Path(message_file).read_text(encoding="utf-8")


def _git_config(repo: Path, key: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "config", key],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _normalize_lines(message: str) -> list[str]:
    text = message.replace("\r\n", "\n").replace("\r", "\n")
    return [line.rstrip() for line in text.split("\n")]


def _split_trailers(lines: list[str]) -> tuple[list[str], list[str]]:
    stripped = _strip_blank_edges(lines)
    if not stripped:
        return [], []

    index = len(stripped)
    trailer_start = index
    has_trailer = False
    while index > 0:
        line = stripped[index - 1]
        if _is_trailer_line(line):
            has_trailer = True
            trailer_start = index - 1
            index -= 1
            continue
        if (
            has_trailer
            and line == ""
            and index > 2
            and _is_trailer_line(stripped[index - 2])
        ):
            index -= 1
            continue
        break

    if not has_trailer:
        return stripped, []
    if index > 0 and stripped[index - 1] != "":
        return stripped, []
    trailer_lines = [line for line in stripped[trailer_start:] if _is_trailer_line(line)]
    return _strip_blank_edges(stripped[:index]), trailer_lines


def _is_trailer_line(line: str) -> bool:
    if ": " not in line:
        return False
    key, _value = line.split(": ", 1)
    return bool(key) and all(char.isalnum() or char == "-" for char in key)


def _strip_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    return lines[start:end]


def _format_body(lines: list[str], *, width: int) -> list[str]:
    result: list[str] = []
    paragraph: list[str] = []
    in_fence = False

    def flush_paragraph() -> None:
        if not paragraph:
            return
        result.extend(_wrap_paragraph(paragraph, width=width))
        paragraph.clear()

    for line in lines:
        if line.startswith("```"):
            flush_paragraph()
            result.append(line)
            in_fence = not in_fence
            continue
        if in_fence:
            result.append(line)
            continue
        if line == "":
            flush_paragraph()
            if result and result[-1] != "":
                result.append("")
            continue
        paragraph.append(line)

    flush_paragraph()
    return _strip_blank_edges(result)


def _wrap_paragraph(lines: list[str], *, width: int) -> list[str]:
    first = lines[0]
    bullet_prefix = _bullet_prefix(first)
    if bullet_prefix is not None:
        text = " ".join(_remove_bullet_prefix(line, bullet_prefix) for line in lines)
        return textwrap.wrap(
            text,
            width=width,
            initial_indent=bullet_prefix,
            subsequent_indent=" " * len(bullet_prefix),
            break_long_words=False,
            break_on_hyphens=False,
        )

    text = " ".join(line.strip() for line in lines)
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _bullet_prefix(line: str) -> str | None:
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    for marker in ("- ", "* "):
        if stripped.startswith(marker):
            return indent + marker
    if ". " in stripped:
        maybe_number, _rest = stripped.split(". ", 1)
        if maybe_number.isdigit():
            return indent + maybe_number + ". "
    return None


def _remove_bullet_prefix(line: str, prefix: str) -> str:
    if line.startswith(prefix):
        return line[len(prefix) :].strip()
    return line.strip()
