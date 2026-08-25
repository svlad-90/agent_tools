from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import TextIO
from uuid import uuid4

from agent_tools.agent_workspace.components.markdown.api import rough_token_count

DEFAULT_LIMITED_BASH_OUTPUT_TOKENS = 2_000
LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS"
PREVIEW_LINE_COUNT = 10
PREVIEW_LINE_CHARS = 300


@dataclass(frozen=True)
class LimitedBashResult:
    exit_code: int
    output_tokens: int
    exceeded: bool
    log_base: Path | None


class OutputPreview:
    def __init__(self, *, line_count: int = PREVIEW_LINE_COUNT, line_chars: int = PREVIEW_LINE_CHARS) -> None:
        self.line_count = line_count
        self.line_chars = line_chars
        self.head: list[str] = []
        self.tail: list[str] = []
        self._pending = ""

    def feed(self, text: str) -> None:
        if not text:
            return
        parts = (self._pending + text).splitlines(keepends=True)
        self._pending = ""
        for part in parts:
            if part.endswith(("\n", "\r")):
                self._add_line(part.rstrip("\r\n"))
            else:
                self._pending = part

    def lines(self) -> list[str]:
        head = list(self.head)
        tail = list(self.tail)
        if self._pending:
            pending = self._format_line(self._pending)
            if not tail or tail[-1] != pending:
                if len(head) < self.line_count:
                    head.append(pending)
                tail = [*tail, pending][-self.line_count :]
        if not head and not tail:
            return []
        if tail and head[-len(tail) :] != tail:
            return [*head, "....", *tail]
        return head

    def _add_line(self, line: str) -> None:
        formatted = self._format_line(line)
        if len(self.head) < self.line_count:
            self.head.append(formatted)
        self.tail.append(formatted)
        if len(self.tail) > self.line_count:
            self.tail.pop(0)

    def _format_line(self, line: str) -> str:
        if len(line) <= self.line_chars:
            return line
        omitted = len(line) - self.line_chars
        return f"{line[: self.line_chars]}... [truncated {omitted} chars]"


def limited_bash_command(command: str, *, limit: int, cwd: Path | None = None) -> list[str]:
    encoded = base64.b64encode(command.encode("utf-8")).decode("ascii")
    result = [
        "python3",
        "-m",
        "agent_tools.agent_workspace.components.harness_adapter.limited_bash",
        "--limit",
        str(limit),
        "--command-b64",
        encoded,
    ]
    if cwd is not None:
        result.extend(["--cwd", str(cwd)])
    return result


def limited_bash_shell_command(command: str, *, limit: int, cwd: Path | None = None) -> str:
    return _shell_join(limited_bash_command(command, limit=limit, cwd=cwd))


def run_limited_bash(command: str, *, limit: int, cwd: Path | None = None) -> LimitedBashResult:
    if limit < 1:
        raise ValueError("limit must be positive")
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    stdout_preview = OutputPreview()
    stderr_preview = OutputPreview()
    counts = {"stdout_chars": 0, "stderr_chars": 0, "stdout_tokens": 0, "stderr_tokens": 0}
    with tempfile.TemporaryDirectory(prefix="agent-workspace-limited-bash-") as temp_dir:
        temp_base = Path(temp_dir) / "output"
        stdout_log = temp_base.with_suffix(".stdout.log")
        stderr_log = temp_base.with_suffix(".stderr.log")
        meta_log = temp_base.with_suffix(".meta.txt")
        process = subprocess.Popen(
            ["/bin/bash", "-lc", command],
            cwd=str(cwd) if cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        assert process.stderr is not None
        with stdout_log.open("w", encoding="utf-8") as stdout_file, stderr_log.open("w", encoding="utf-8") as stderr_file:
            stdout_thread = threading.Thread(
                target=_copy_stream,
                args=(process.stdout, stdout_file, stdout_chunks, stdout_preview, counts, "stdout", limit),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_copy_stream,
                args=(process.stderr, stderr_file, stderr_chunks, stderr_preview, counts, "stderr", limit),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            exit_code = process.wait()
            stdout_thread.join()
            stderr_thread.join()

        total_tokens = counts["stdout_tokens"] + counts["stderr_tokens"]
        total_chars = counts["stdout_chars"] + counts["stderr_chars"]
        exceeded = total_tokens > limit
        if exceeded:
            meta_log.write_text(
                "\n".join(
                    (
                        f"timestamp={datetime.now().astimezone().isoformat(timespec='seconds')}",
                        f"cwd={cwd or Path.cwd()}",
                        f"exit_code={exit_code}",
                        f"limit_tokens={limit}",
                        f"output_tokens={total_tokens}",
                        f"output_chars={total_chars}",
                        f"command={command}",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            log_base = _publish_logs(stdout_log, stderr_log, meta_log)
            print(
                _limit_message(
                    limit=limit,
                    output_tokens=total_tokens,
                    log_base=log_base,
                    original_exit_code=exit_code,
                    stdout_preview=stdout_preview.lines(),
                    stderr_preview=stderr_preview.lines(),
                )
            )
            return LimitedBashResult(exit_code=2, output_tokens=total_tokens, exceeded=True, log_base=log_base)

        sys.stdout.write("".join(stdout_chunks))
        sys.stderr.write("".join(stderr_chunks))
        return LimitedBashResult(exit_code=exit_code, output_tokens=total_tokens, exceeded=False, log_base=None)


def limit_from_env(env: dict[str, str] | None = None) -> int:
    env = env or os.environ
    raw = env.get(LIMIT_ENV_VAR, "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LIMITED_BASH_OUTPUT_TOKENS
    return max(100, min(200_000, value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=limit_from_env())
    parser.add_argument("--cwd")
    parser.add_argument("--command-b64", required=True)
    args = parser.parse_args(argv)
    try:
        command = base64.b64decode(args.command_b64.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"limited_bash: invalid command payload: {exc}", file=sys.stderr)
        return 2
    cwd = Path(args.cwd).resolve() if args.cwd else None
    try:
        return run_limited_bash(command, limit=args.limit, cwd=cwd).exit_code
    except (OSError, ValueError) as exc:
        print(f"limited_bash: {exc}", file=sys.stderr)
        return 2


def _copy_stream(
    stream: TextIO,
    log_file: TextIO,
    chunks: list[str],
    preview: OutputPreview,
    counts: dict[str, int],
    key: str,
    limit: int,
) -> None:
    while True:
        chunk = stream.read(8192)
        if not chunk:
            return
        log_file.write(chunk)
        preview.feed(chunk)
        counts[f"{key}_chars"] += len(chunk)
        counts[f"{key}_tokens"] += rough_token_count(chunk)
        if counts["stdout_tokens"] + counts["stderr_tokens"] <= limit:
            chunks.append(chunk)


def _limit_message(
    *,
    limit: int,
    output_tokens: int,
    log_base: Path,
    original_exit_code: int,
    stdout_preview: list[str],
    stderr_preview: list[str],
) -> str:
    preview = _preview_text(stdout_preview=stdout_preview, stderr_preview=stderr_preview)
    message = (
        "limited_bash: command output was not returned to the agent because it "
        f"exceeded the configured limit ({output_tokens} > {limit} estimated tokens).\n"
        f"Configured Bash output limit: {limit} estimated tokens.\n"
        f"{preview}"
        "Run a narrower command and explicitly cap output, for example with "
        "`head`, `tail`, `sed -n`, `rg --max-count`, `find ... | head`, or a "
        "tool-specific quiet/summary flag.\n"
        f"Full output was saved next to {log_base}.stdout.log and {log_base}.stderr.log.\n"
        f"Original command exit code: {original_exit_code}."
    )
    return message


def _preview_text(*, stdout_preview: list[str], stderr_preview: list[str]) -> str:
    parts = []
    if stdout_preview:
        parts.append("stdout preview:\n" + "\n".join(stdout_preview))
    if stderr_preview:
        parts.append("stderr preview:\n" + "\n".join(stderr_preview))
    if not parts:
        return ""
    return "\n".join(parts) + "\n"


def _publish_logs(stdout_log: Path, stderr_log: Path, meta_log: Path) -> Path:
    log_base = _new_log_base()
    shutil.move(str(stdout_log), log_base.with_suffix(".stdout.log"))
    shutil.move(str(stderr_log), log_base.with_suffix(".stderr.log"))
    shutil.move(str(meta_log), log_base.with_suffix(".meta.txt"))
    return log_base


def _new_log_base() -> Path:
    task_dir = os.environ.get("AGENT_TOOLS_TASK_DIR") or os.environ.get("PAF_TASK_DIR")
    if task_dir:
        log_dir = Path(task_dir) / "report" / "logs" / "limited-bash"
    else:
        log_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "agent-workspace-limited-bash"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    return log_dir / f"limited_bash_{stamp}_{os.getpid()}_{uuid4().hex[:8]}"


def _shell_join(args: list[str]) -> str:
    import shlex

    return " ".join(shlex.quote(arg) for arg in args)
