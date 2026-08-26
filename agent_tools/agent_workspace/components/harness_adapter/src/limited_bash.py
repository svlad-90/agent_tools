from __future__ import annotations

import argparse
import base64
import codecs
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import BinaryIO, TextIO
from uuid import uuid4

from agent_tools.agent_workspace.components.markdown.api import rough_token_count

DEFAULT_LIMITED_BASH_OUTPUT_TOKENS = 2_000
LIMIT_ENV_VAR = "AGENT_TOOLS_LIMITED_BASH_OUTPUT_TOKENS"


@dataclass(frozen=True)
class LimitedBashResult:
    exit_code: int
    output_tokens: int
    exceeded: bool
    log_base: Path | None


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
    counts = {"stdout_chars": 0, "stderr_chars": 0, "stdout_tokens": 0, "stderr_tokens": 0}
    stream_state: dict[str, object] = {"notice_written": False, "streamed_tokens": 0}
    stream_lock = threading.Lock()
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
            args=(process.stdout, stdout_file, sys.stdout, counts, "stdout", limit, log_base, stream_state, stream_lock),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_copy_stream,
            args=(process.stderr, stderr_file, sys.stderr, counts, "stderr", limit, log_base, stream_state, stream_lock),
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
        print(f"\nlimited_bash: original command exit code: {exit_code}.")
        return LimitedBashResult(exit_code=2, output_tokens=total_tokens, exceeded=True, log_base=log_base)

    _remove_logs(stdout_log, stderr_log, meta_log)
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
    stream: BinaryIO,
    log_file: BinaryIO,
    output: TextIO,
    counts: dict[str, int],
    key: str,
    limit: int,
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
                    counts[f"{key}_chars"] += len(text)
                    counts[f"{key}_tokens"] += rough_token_count(text)
                    _write_limited_stream_part(text, output, limit, log_base, stream_state)
            return
        log_file.write(chunk)
        log_file.flush()
        text = decoder.decode(chunk)
        if not text:
            continue
        parts = text.splitlines(keepends=True) or [text]
        with stream_lock:
            for part in parts:
                counts[f"{key}_chars"] += len(part)
                counts[f"{key}_tokens"] += rough_token_count(part)
                _write_limited_stream_part(part, output, limit, log_base, stream_state)


def _read_binary_chunk(stream: BinaryIO) -> bytes:
    read1 = getattr(stream, "read1", None)
    if callable(read1):
        return read1(8192)
    return stream.read(8192)


def _write_limited_stream_part(
    part: str,
    output: TextIO,
    limit: int,
    log_base: Path,
    stream_state: dict[str, object],
) -> None:
    if bool(stream_state["notice_written"]):
        return
    streamed_tokens = int(stream_state["streamed_tokens"])
    part_tokens = rough_token_count(part)
    if streamed_tokens + part_tokens <= limit:
        output.write(part)
        output.flush()
        stream_state["streamed_tokens"] = streamed_tokens + part_tokens
        return
    remaining_tokens = max(0, limit - streamed_tokens)
    if remaining_tokens > 0:
        prefix = part[: max(1, remaining_tokens * 4)]
        output.write(prefix)
    output.write(_stream_limit_message(limit=limit, log_base=log_base))
    output.flush()
    stream_state["streamed_tokens"] = limit
    stream_state["notice_written"] = True


def _stream_limit_message(
    *,
    limit: int,
    log_base: Path,
) -> str:
    return (
        "\nlimited_bash: configured Bash output limit reached; further command output is being written to files.\n"
        f"Configured Bash output limit: {limit} estimated tokens.\n"
        f"Live stdout log: {log_base}.stdout.log\n"
        f"Live stderr log: {log_base}.stderr.log\n"
        "Run a narrower command and explicitly cap output, for example with "
        "`head`, `tail`, `sed -n`, `rg --max-count`, `find ... | head`, or a "
        "tool-specific quiet/summary flag.\n"
    )


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
    return log_dir / f"limited_bash_{stamp}_{os.getpid()}_{uuid4().hex[:8]}"


def _shell_join(args: list[str]) -> str:
    import shlex

    return " ".join(shlex.quote(arg) for arg in args)
