from __future__ import annotations

import argparse
import base64
import codecs
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import threading
import time
from typing import BinaryIO, TextIO
from uuid import uuid4

from agent_tools.agent_workspace.components.markdown.api import rough_token_count

DEFAULT_LIMITED_BASH_OUTPUT_TOKENS = 2_000
LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS"
DEFAULT_LIMITED_BASH_HEAD_TOKENS = 2_000
HEAD_LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_HEAD_TOKENS"
DEFAULT_LIMITED_BASH_TAIL_TOKENS = 2_000
TAIL_LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_TAIL_TOKENS"
DEFAULT_LIMITED_BASH_HEARTBEAT_TOKENS = 1_000
HEARTBEAT_LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_HEARTBEAT_TOKENS"
DEFAULT_IDLE_NOTICE_SECONDS = 30.0
IDLE_NOTICE_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_IDLE_NOTICE_SECONDS"
TAIL_LINE_LIMIT = 20
HEARTBEAT_NOTICE_TOKEN_LIMIT = 300
MIN_HEARTBEAT_DETAIL_TOKENS = 80
ACTIVE_LOG_DIR = ".active"


@dataclass(frozen=True)
class LimitedBashResult:
    exit_code: int
    output_tokens: int
    exceeded: bool
    log_base: Path | None
    idle_notice_emitted: bool = False


@dataclass(frozen=True)
class OutputBudgets:
    limit_tokens: int
    service_tokens: int
    stdout_head_tokens: int
    stderr_head_tokens: int
    stdout_tail_tokens: int
    stderr_tail_tokens: int
    heartbeat_tokens: int

    @property
    def head_tokens(self) -> int:
        return self.stdout_head_tokens + self.stderr_head_tokens

    @property
    def tail_tokens(self) -> int:
        return self.stdout_tail_tokens + self.stderr_tail_tokens


@dataclass
class StreamCapture:
    head_tokens: int
    tail_tokens: int
    output: TextIO
    printed_head_tokens: int = 0
    chars: int = 0
    tokens: int = 0
    lines: int = 0
    interval_tokens: int = 0
    interval_lines: int = 0
    tail_parts: deque[str] | None = None
    tail_part_tokens: deque[int] | None = None
    tail_total_tokens: int = 0
    deferred_parts: list[str] | None = None

    def __post_init__(self) -> None:
        if self.tail_parts is None:
            self.tail_parts = deque()
        if self.tail_part_tokens is None:
            self.tail_part_tokens = deque()
        if self.deferred_parts is None:
            self.deferred_parts = []


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
    if cwd is None:
        return _shell_join(limited_bash_command(command, limit=limit))
    cwd_text = str(cwd)
    return f"cd {shlex.quote(cwd_text)} && {_shell_join(limited_bash_command(command, limit=limit, cwd=cwd))}"


def run_limited_bash(
    command: str,
    *,
    limit: int,
    cwd: Path | None = None,
    head_limit: int | None = None,
    tail_limit: int | None = None,
    heartbeat_limit: int | None = None,
    idle_notice_seconds: float | None = None,
) -> LimitedBashResult:
    if limit < 1:
        raise ValueError("limit must be positive")
    if head_limit is not None and head_limit < 1:
        raise ValueError("head_limit must be positive")
    if tail_limit is not None and tail_limit < 1:
        raise ValueError("tail_limit must be positive")
    if heartbeat_limit is not None and heartbeat_limit < 0:
        raise ValueError("heartbeat_limit must be non-negative")
    if idle_notice_seconds is None:
        idle_notice_seconds = idle_notice_seconds_from_env()
    budgets = _allocate_output_budgets(
        limit,
        head_limit=head_limit,
        tail_limit=tail_limit,
        heartbeat_limit=heartbeat_limit,
    )
    captures = {
        "stdout": StreamCapture(
            head_tokens=budgets.stdout_head_tokens,
            tail_tokens=budgets.stdout_tail_tokens,
            output=sys.stdout,
        ),
        "stderr": StreamCapture(
            head_tokens=budgets.stderr_head_tokens,
            tail_tokens=budgets.stderr_tail_tokens,
            output=sys.stderr,
        ),
    }
    stream_state: dict[str, object] = {
        "notice_written": False,
        "last_activity": time.monotonic(),
        "idle_notice_written": False,
        "heartbeat_tokens": 0,
    }
    stream_lock = threading.Lock()
    done = threading.Event()
    log_base = _new_log_base()
    stdout_log = log_base.with_suffix(".stdout.log")
    stderr_log = log_base.with_suffix(".stderr.log")
    meta_log = log_base.with_suffix(".meta.txt")
    process = subprocess.Popen(
        ["/bin/bash", "-lc", command],
        cwd=str(cwd) if cwd is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    with stdout_log.open("wb") as stdout_file, stderr_log.open("wb") as stderr_file:
        stdout_thread = threading.Thread(
            target=_copy_stream,
            args=(
                process.stdout,
                stdout_file,
                captures,
                "stdout",
                budgets,
                log_base,
                stream_state,
                stream_lock,
            ),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_copy_stream,
            args=(
                process.stderr,
                stderr_file,
                captures,
                "stderr",
                budgets,
                log_base,
                stream_state,
                stream_lock,
            ),
            daemon=True,
        )
        idle_thread = threading.Thread(
            target=_write_idle_notices,
            args=(
                done,
                sys.stderr,
                idle_notice_seconds,
                log_base,
                budgets,
                captures,
                stream_state,
                stream_lock,
            ),
            daemon=True,
        )
        idle_thread.start()
        stdout_thread.start()
        stderr_thread.start()
        try:
            exit_code = process.wait()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise
        finally:
            done.set()
            stdout_thread.join()
            stderr_thread.join()
            idle_thread.join(timeout=1)

    total_tokens = captures["stdout"].tokens + captures["stderr"].tokens
    total_chars = captures["stdout"].chars + captures["stderr"].chars
    exceeded = total_tokens > budgets.limit_tokens
    idle_notice_emitted = bool(stream_state["idle_notice_written"])
    if exceeded:
        meta_log.write_text(
            "\n".join(
                (
                    f"timestamp={datetime.now().astimezone().isoformat(timespec='seconds')}",
                    f"cwd={cwd or Path.cwd()}",
                    f"exit_code={exit_code}",
                    f"limit_tokens={budgets.limit_tokens}",
                    f"head_limit_tokens={budgets.head_tokens}",
                    f"tail_limit_tokens={budgets.tail_tokens}",
                    f"heartbeat_limit_tokens={budgets.heartbeat_tokens}",
                    f"output_tokens={total_tokens}",
                    f"output_chars={total_chars}",
                    f"stdout_tokens={captures['stdout'].tokens}",
                    f"stderr_tokens={captures['stderr'].tokens}",
                    f"stdout_chars={captures['stdout'].chars}",
                    f"stderr_chars={captures['stderr'].chars}",
                    f"stdout_lines={captures['stdout'].lines}",
                    f"stderr_lines={captures['stderr'].lines}",
                    f"command={command}",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        _finalize_log_base(log_base, keep_completed=True)
        _write_final_overflow_summary(
            sys.stderr,
            limit=budgets.limit_tokens,
            output_tokens=total_tokens,
            exit_code=exit_code,
            log_base=log_base,
            budgets=budgets,
            captures=captures,
        )
        return LimitedBashResult(
            exit_code=2,
            output_tokens=total_tokens,
            exceeded=True,
            log_base=log_base,
            idle_notice_emitted=idle_notice_emitted,
        )

    if idle_notice_emitted:
        _flush_deferred_output(captures)
        meta_log.write_text(
            "\n".join(
                (
                    f"timestamp={datetime.now().astimezone().isoformat(timespec='seconds')}",
                    f"cwd={cwd or Path.cwd()}",
                    f"exit_code={exit_code}",
                    f"limit_tokens={budgets.limit_tokens}",
                    f"head_limit_tokens={budgets.head_tokens}",
                    f"tail_limit_tokens={budgets.tail_tokens}",
                    f"heartbeat_limit_tokens={budgets.heartbeat_tokens}",
                    f"output_tokens={total_tokens}",
                    f"output_chars={total_chars}",
                    f"stdout_tokens={captures['stdout'].tokens}",
                    f"stderr_tokens={captures['stderr'].tokens}",
                    "idle_notice_emitted=true",
                    f"command={command}",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        _finalize_log_base(log_base, keep_completed=True)
        return LimitedBashResult(
            exit_code=exit_code,
            output_tokens=total_tokens,
            exceeded=False,
            log_base=log_base,
            idle_notice_emitted=True,
        )
    _flush_deferred_output(captures)
    _remove_logs(stdout_log, stderr_log, meta_log)
    _finalize_log_base(log_base, keep_completed=False)
    return LimitedBashResult(exit_code=exit_code, output_tokens=total_tokens, exceeded=False, log_base=None)


def limit_from_env(env: dict[str, str] | None = None) -> int:
    return _int_env(LIMIT_ENV_VAR, DEFAULT_LIMITED_BASH_OUTPUT_TOKENS, 100, 200_000, env=env)


def head_limit_from_env(env: dict[str, str] | None = None) -> int:
    fallback = limit_from_env(env)
    return _int_env(HEAD_LIMIT_ENV_VAR, fallback, 100, 200_000, env=env)


def tail_limit_from_env(env: dict[str, str] | None = None) -> int:
    fallback = limit_from_env(env)
    return _int_env(TAIL_LIMIT_ENV_VAR, fallback, 100, 200_000, env=env)


def heartbeat_limit_from_env(env: dict[str, str] | None = None) -> int:
    return _int_env(
        HEARTBEAT_LIMIT_ENV_VAR,
        DEFAULT_LIMITED_BASH_HEARTBEAT_TOKENS,
        0,
        200_000,
        env=env,
    )


def idle_notice_seconds_from_env(env: dict[str, str] | None = None) -> float:
    env = env or os.environ
    raw = env.get(IDLE_NOTICE_ENV_VAR, "")
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_IDLE_NOTICE_SECONDS
    if value <= 0:
        return 0.0
    return max(1.0, min(300.0, value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=limit_from_env())
    parser.add_argument("--head-limit", type=int)
    parser.add_argument("--tail-limit", type=int)
    parser.add_argument("--heartbeat-limit", type=int)
    parser.add_argument("--idle-notice-seconds", type=float, default=idle_notice_seconds_from_env())
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
        return run_limited_bash(
            command,
            limit=args.limit,
            cwd=cwd,
            head_limit=args.head_limit if args.head_limit is not None else _optional_int_env(HEAD_LIMIT_ENV_VAR),
            tail_limit=args.tail_limit if args.tail_limit is not None else _optional_int_env(TAIL_LIMIT_ENV_VAR),
            heartbeat_limit=(
                args.heartbeat_limit if args.heartbeat_limit is not None else heartbeat_limit_from_env()
            ),
            idle_notice_seconds=args.idle_notice_seconds,
        ).exit_code
    except (OSError, ValueError) as exc:
        print(f"limited_bash: {exc}", file=sys.stderr)
        return 2


def _copy_stream(
    stream: BinaryIO,
    log_file: BinaryIO,
    captures: dict[str, StreamCapture],
    key: str,
    budgets: OutputBudgets,
    log_base: Path,
    stream_state: dict[str, object],
    stream_lock: threading.Lock,
) -> None:
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    while True:
        chunk = _read_binary_chunk(stream)
        if not chunk:
            text = decoder.decode(b"", final=True)
            if text:
                with stream_lock:
                    _record_stream_part(
                        text,
                        captures,
                        captures[key],
                        budgets,
                        log_base,
                        stream_state,
                    )
            return
        log_file.write(chunk)
        log_file.flush()
        text = decoder.decode(chunk)
        if not text:
            continue
        parts = text.splitlines(keepends=True) or [text]
        with stream_lock:
            for part in parts:
                _record_stream_part(
                    part,
                    captures,
                    captures[key],
                    budgets,
                    log_base,
                    stream_state,
                )


def _read_binary_chunk(stream: BinaryIO) -> bytes:
    read1 = getattr(stream, "read1", None)
    if callable(read1):
        return read1(8192)
    return stream.read(8192)


def _record_stream_part(
    part: str,
    captures: dict[str, StreamCapture],
    capture: StreamCapture,
    budgets: OutputBudgets,
    log_base: Path,
    stream_state: dict[str, object],
) -> None:
    stream_state["last_activity"] = time.monotonic()
    part_tokens = rough_token_count(part)
    capture.chars += len(part)
    capture.tokens += part_tokens
    capture.lines += part.count("\n")
    if part and not part.endswith("\n"):
        capture.lines += 1
    capture.interval_tokens += part_tokens
    capture.interval_lines += part.count("\n")
    if part and not part.endswith("\n"):
        capture.interval_lines += 1
    _append_tail_part(capture, part, part_tokens)

    if capture.printed_head_tokens >= capture.head_tokens:
        if not bool(stream_state["notice_written"]) and _combined_tokens(captures) <= budgets.limit_tokens:
            _defer_stream_part(capture, part)
            return
        if not bool(stream_state["notice_written"]):
            sys.stderr.write(_head_limit_message(limit=budgets, log_base=log_base))
            sys.stderr.flush()
            stream_state["notice_written"] = True
        return

    remaining_tokens = max(0, capture.head_tokens - capture.printed_head_tokens)
    if part_tokens <= remaining_tokens:
        capture.output.write(part)
        capture.output.flush()
        capture.printed_head_tokens += part_tokens
        if _combined_tokens(captures) > budgets.limit_tokens:
            _write_head_notice_once(budgets, log_base, stream_state)
        return

    if remaining_tokens > 0:
        prefix_length = max(1, remaining_tokens * 4)
        prefix = part[:prefix_length]
        capture.output.write(prefix)
        capture.output.flush()
        capture.printed_head_tokens = capture.head_tokens
        remainder = part[prefix_length:]
        if remainder and _combined_tokens(captures) <= budgets.limit_tokens:
            _defer_stream_part(capture, remainder)
            return
    _write_head_notice_once(budgets, log_base, stream_state)


def _append_tail_part(capture: StreamCapture, part: str, part_tokens: int) -> None:
    assert capture.tail_parts is not None
    assert capture.tail_part_tokens is not None
    capture.tail_parts.append(part)
    capture.tail_part_tokens.append(part_tokens)
    capture.tail_total_tokens += part_tokens
    while (
        (capture.tail_total_tokens > capture.tail_tokens or len(capture.tail_parts) > TAIL_LINE_LIMIT)
        and capture.tail_parts
        and capture.tail_part_tokens
        and len(capture.tail_parts) > TAIL_LINE_LIMIT
    ):
        capture.tail_parts.popleft()
        capture.tail_total_tokens -= capture.tail_part_tokens.popleft()


def _write_head_notice_once(
    budgets: OutputBudgets,
    log_base: Path,
    stream_state: dict[str, object],
) -> None:
    if bool(stream_state["notice_written"]):
        return
    sys.stderr.write(_head_limit_message(limit=budgets, log_base=log_base))
    sys.stderr.flush()
    stream_state["notice_written"] = True


def _defer_stream_part(capture: StreamCapture, part: str) -> None:
    assert capture.deferred_parts is not None
    capture.deferred_parts.append(part)


def _flush_deferred_output(captures: dict[str, StreamCapture]) -> None:
    for capture in captures.values():
        assert capture.deferred_parts is not None
        if not capture.deferred_parts:
            continue
        capture.output.write("".join(capture.deferred_parts))
        capture.output.flush()
        capture.deferred_parts.clear()


def _combined_tokens(captures: dict[str, StreamCapture]) -> int:
    return sum(capture.tokens for capture in captures.values())


def _write_idle_notices(
    done: threading.Event,
    output: TextIO,
    idle_notice_seconds: float,
    log_base: Path,
    budgets: OutputBudgets,
    captures: dict[str, StreamCapture],
    stream_state: dict[str, object],
    stream_lock: threading.Lock,
) -> None:
    if idle_notice_seconds <= 0:
        return
    while not done.wait(idle_notice_seconds):
        with stream_lock:
            idle_for = time.monotonic() - float(stream_state["last_activity"])
            interval_stdout = captures["stdout"].interval_tokens
            interval_stderr = captures["stderr"].interval_tokens
            should_write_progress = bool(stream_state["notice_written"]) and (
                interval_stdout > 0 or interval_stderr > 0
            )
            should_write_idle = idle_for >= idle_notice_seconds
            if not should_write_progress and not should_write_idle:
                continue
            budget_remaining = budgets.heartbeat_tokens - int(stream_state["heartbeat_tokens"])
            if budget_remaining < MIN_HEARTBEAT_DETAIL_TOKENS:
                notice = _heartbeat_exhausted_notice(idle_for=idle_for, log_base=log_base, captures=captures)
            else:
                notice = _progress_notice(
                    idle_for=idle_for,
                    log_base=log_base,
                    captures=captures,
                    include_recent=should_write_progress,
                )
                notice = _cap_text_to_tokens(notice, min(budget_remaining, HEARTBEAT_NOTICE_TOKEN_LIMIT))
                stream_state["heartbeat_tokens"] = int(stream_state["heartbeat_tokens"]) + rough_token_count(notice)
            output.write(notice)
            output.flush()
            stream_state["last_activity"] = time.monotonic()
            stream_state["idle_notice_written"] = True
            for capture in captures.values():
                capture.interval_tokens = 0
                capture.interval_lines = 0


def _head_limit_message(
    *,
    limit: OutputBudgets,
    log_base: Path,
) -> str:
    return (
        "\n--- limited_bash: output head budget reached ---\n"
        "Collecting tail buffers for the final summary.\n"
        f"Head shown: stdout ~{limit.stdout_head_tokens} tokens, "
        f"stderr ~{limit.stderr_head_tokens} tokens.\n"
        f"Reserved for completion: tail ~{limit.tail_tokens} tokens, "
        f"service ~{limit.service_tokens} tokens.\n"
        f"Live stdout log: {log_base}.stdout.log\n"
        f"Live stderr log: {log_base}.stderr.log\n"
        "--- end limited_bash ---\n"
    )


def _write_final_overflow_summary(
    output: TextIO,
    *,
    limit: int,
    output_tokens: int,
    exit_code: int,
    log_base: Path,
    budgets: OutputBudgets,
    captures: dict[str, StreamCapture],
) -> None:
    output.write(
        "\n--- limited_bash: final overflow summary ---\n"
        f"Configured limit: {limit} estimated tokens. "
        f"Observed: ~{output_tokens} tokens.\n"
        f"Original command exit code: {exit_code}.\n"
        "Full logs:\n"
        f"- stdout: {log_base}.stdout.log\n"
        f"- stderr: {log_base}.stderr.log\n"
        f"- metadata: {log_base}.meta.txt\n\n"
        "Output shown:\n"
        f"- stdout head: ~{budgets.stdout_head_tokens} tokens\n"
        f"- stderr head: ~{budgets.stderr_head_tokens} tokens\n"
        f"- stdout tail: ~{budgets.stdout_tail_tokens} tokens\n"
        f"- stderr tail: ~{budgets.stderr_tail_tokens} tokens\n"
        f"- service/heartbeat: ~{budgets.service_tokens + budgets.heartbeat_tokens} tokens\n"
    )
    _write_tail_section(output, "STDOUT", captures["stdout"])
    _write_tail_section(output, "STDERR", captures["stderr"])
    output.write(
        "\n[limited_bash] rerun with a narrower command if more context is needed. "
        "Examples: `tail -n 120 <log>`, `rg -n \"error:|FAILED|Traceback\" <log>`.\n"
        "--- end limited_bash ---\n"
    )
    output.flush()


def _write_tail_section(output: TextIO, title: str, capture: StreamCapture) -> None:
    tail_text = _tail_text(capture)
    omitted_tokens = max(0, capture.tokens - capture.printed_head_tokens - rough_token_count(tail_text))
    output.write(
        f"\n{title} omitted: ~{omitted_tokens} tokens. "
        f"Full stream is in {title.lower()} log.\n"
    )
    if tail_text:
        output.write(f"\n{title} LAST {TAIL_LINE_LIMIT} LINES:\n")
        output.write(tail_text)
        if not tail_text.endswith("\n"):
            output.write("\n")


def _tail_text(capture: StreamCapture) -> str:
    assert capture.tail_parts is not None
    text = "".join(capture.tail_parts)
    lines = text.splitlines(keepends=True)
    if len(lines) > TAIL_LINE_LIMIT:
        text = "".join(lines[-TAIL_LINE_LIMIT:])
    return _cap_text_to_tokens(text, capture.tail_tokens, keep="tail")


def _progress_notice(
    *,
    idle_for: float,
    log_base: Path,
    captures: dict[str, StreamCapture],
    include_recent: bool,
) -> str:
    if include_recent:
        notice = (
            "\n[limited_bash] command still running; "
            f"interval: stdout +{captures['stdout'].interval_lines} lines/"
            f"~{captures['stdout'].interval_tokens} tokens, "
            f"stderr +{captures['stderr'].interval_lines} lines/"
            f"~{captures['stderr'].interval_tokens} tokens; "
            f"total: stdout ~{captures['stdout'].tokens}, "
            f"stderr ~{captures['stderr'].tokens} tokens.\n"
            f"[limited_bash] live logs: stdout={log_base}.stdout.log "
            f"stderr={log_base}.stderr.log\n"
        )
        stderr_recent = _recent_lines(captures["stderr"], max_lines=3)
        stdout_recent = _recent_lines(captures["stdout"], max_lines=3)
        if stderr_recent:
            notice += "\n--- limited_bash: stderr recent ---\n" + stderr_recent
            if not stderr_recent.endswith("\n"):
                notice += "\n"
            notice += "--- end limited_bash ---\n"
        if stdout_recent:
            notice += "\n--- limited_bash: stdout recent ---\n" + stdout_recent
            if not stdout_recent.endswith("\n"):
                notice += "\n"
            notice += "--- end limited_bash ---\n"
        return notice

    return (
        "\n[limited_bash] command is still running with no output "
        f"for {int(idle_for)}s.\n"
        f"[limited_bash] live logs: stdout={log_base}.stdout.log "
        f"stderr={log_base}.stderr.log\n"
    )


def _heartbeat_exhausted_notice(
    *,
    idle_for: float,
    log_base: Path,
    captures: dict[str, StreamCapture],
) -> str:
    return (
        "\n[limited_bash] command still running; detailed heartbeat budget exhausted. "
        f"interval: stdout +{captures['stdout'].interval_lines} lines/"
        f"~{captures['stdout'].interval_tokens} tokens, "
        f"stderr +{captures['stderr'].interval_lines} lines/"
        f"~{captures['stderr'].interval_tokens} tokens; "
        f"total: stdout ~{captures['stdout'].tokens}, "
        f"stderr ~{captures['stderr'].tokens} tokens; "
        f"idle ~{int(idle_for)}s.\n"
        f"[limited_bash] live logs: stdout={log_base}.stdout.log "
        f"stderr={log_base}.stderr.log\n"
    )


def _recent_lines(capture: StreamCapture, *, max_lines: int) -> str:
    text = _tail_text(capture)
    return "".join(text.splitlines(keepends=True)[-max_lines:])


def _cap_text_to_tokens(text: str, token_limit: int, *, keep: str = "head") -> str:
    if token_limit <= 0 or rough_token_count(text) <= token_limit:
        return text
    if keep == "tail":
        char_limit = min(2_000, max(200, token_limit * 4))
        return text[-char_limit:]
    char_limit = max(1, token_limit * 4)
    return text[:char_limit]


def _allocate_output_budgets(
    limit: int,
    *,
    head_limit: int | None = None,
    tail_limit: int | None = None,
    heartbeat_limit: int | None = None,
) -> OutputBudgets:
    if head_limit is None and tail_limit is None:
        service = max(1, int(limit * 0.15))
        tail = max(1, int(limit * 0.25))
        head = max(1, limit - service - tail)
        heartbeat = min(600, max(80, int(limit * 0.3))) if heartbeat_limit is None else heartbeat_limit
    else:
        head = head_limit if head_limit is not None else DEFAULT_LIMITED_BASH_HEAD_TOKENS
        tail = tail_limit if tail_limit is not None else DEFAULT_LIMITED_BASH_TAIL_TOKENS
        limit = head + tail
        service = min(500, max(100, int(limit * 0.1)))
        heartbeat = DEFAULT_LIMITED_BASH_HEARTBEAT_TOKENS if heartbeat_limit is None else heartbeat_limit
    stderr_head = max(1, int(head * 0.4))
    stdout_head = max(1, head - stderr_head)
    stderr_tail = max(1, int(tail * 0.5))
    stdout_tail = max(1, tail - stderr_tail)
    return OutputBudgets(
        limit_tokens=limit,
        service_tokens=service,
        stdout_head_tokens=stdout_head,
        stderr_head_tokens=stderr_head,
        stdout_tail_tokens=stdout_tail,
        stderr_tail_tokens=stderr_tail,
        heartbeat_tokens=heartbeat,
    )


def _int_env(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
    *,
    env: dict[str, str] | None = None,
) -> int:
    env = env or os.environ
    raw = env.get(name, "")
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _optional_int_env(env_var: str, env: dict[str, str] | None = None) -> int | None:
    env = env or os.environ
    if env_var not in env:
        return None
    return _int_env(env_var, 0, 100, 200_000, env=env)


def _remove_logs(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _new_log_base() -> Path:
    task_dir = os.environ.get("AGENT_TOOLS_TASK_DIR") or os.environ.get("PAF_TASK_DIR")
    if task_dir:
        log_dir = Path(task_dir) / "report" / "logs" / "limited-bash"
    else:
        log_dir = Path(os.environ.get("TMPDIR", "/tmp")) / "agent-workspace-limited-bash"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    run_dir = log_dir / f"limited_bash_{stamp}_{os.getpid()}_{uuid4().hex[:8]}"
    run_dir.mkdir()
    log_base = run_dir / "limited_bash"
    _mark_log_base_active(log_base)
    _cleanup_limited_bash_logs(log_dir, keep_latest_completed=False)
    return log_base


def _mark_log_base_active(log_base: Path) -> None:
    log_dir = log_base.parent.parent
    active_dir = log_dir / ACTIVE_LOG_DIR
    active_dir.mkdir(parents=True, exist_ok=True)
    try:
        started_at = time.time()
        (active_dir / log_base.parent.name).write_text(
            f"pid={os.getpid()}\nstarted_at={started_at:.6f}\n",
            encoding="utf-8",
        )
        (log_base.parent / "run.meta").write_text(
            f"started_at={started_at:.6f}\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _finalize_log_base(log_base: Path, *, keep_completed: bool) -> None:
    run_dir = log_base.parent
    log_dir = run_dir.parent
    try:
        (log_dir / ACTIVE_LOG_DIR / run_dir.name).unlink(missing_ok=True)
        if keep_completed:
            _append_run_meta(run_dir, f"finished_at={time.time():.6f}\n")
        else:
            shutil.rmtree(run_dir)
    except OSError:
        pass
    _cleanup_limited_bash_logs(log_dir, keep_latest_completed=True)


def _cleanup_limited_bash_logs(log_dir: Path, *, keep_latest_completed: bool = True) -> None:
    if not log_dir.is_dir():
        return
    active = _active_log_bases(log_dir)
    keep_completed = _overlapping_completed_log_runs(log_dir, active) if keep_latest_completed else set()
    for path in log_dir.iterdir():
        if path.name == ACTIVE_LOG_DIR:
            _cleanup_empty_active_log_dir(path)
            continue
        if path.name in active or path.name in keep_completed:
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError:
            pass


def _active_log_bases(log_dir: Path) -> set[str]:
    active_dir = log_dir / ACTIVE_LOG_DIR
    if not active_dir.is_dir():
        return set()
    return {path.name for path in active_dir.iterdir() if path.is_file()}


def _overlapping_completed_log_runs(log_dir: Path, active: set[str]) -> set[str]:
    completed = []
    for path in log_dir.iterdir():
        if not path.is_dir() or path.name == ACTIVE_LOG_DIR or path.name in active:
            continue
        interval = _run_interval(path)
        if interval is None:
            continue
        completed.append((path.name, interval))
    if not completed:
        return set()
    latest_name, latest_interval = max(completed, key=lambda item: item[1][1])
    keep = {latest_name}
    keep.update(name for name, interval in completed if _intervals_overlap(interval, latest_interval))
    return keep


def _run_interval(run_dir: Path) -> tuple[float, float] | None:
    metadata = _read_key_value_file(run_dir / "run.meta")
    try:
        started = float(metadata["started_at"])
        finished = float(metadata["finished_at"])
    except (KeyError, ValueError):
        return None
    return started, finished


def _intervals_overlap(left: tuple[float, float], right: tuple[float, float]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _append_run_meta(run_dir: Path, text: str) -> None:
    try:
        with (run_dir / "run.meta").open("a", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        pass


def _read_key_value_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def _cleanup_empty_active_log_dir(active_dir: Path) -> None:
    if not active_dir.is_dir():
        return
    try:
        if not any(active_dir.iterdir()):
            active_dir.rmdir()
    except OSError:
        pass


def _shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)
