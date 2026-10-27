from __future__ import annotations

import codecs
import ctypes
from dataclasses import dataclass, field
from pathlib import Path
import errno
import os
import signal
import struct
import subprocess
import sys
import threading
import time
from typing import Any
from uuid import uuid4

try:
    import fcntl
    import termios
    import pty
except ImportError:  # pragma: no cover - exercised on Windows hosts.
    fcntl = None  # type: ignore[assignment]
    termios = None  # type: ignore[assignment]
    pty = None  # type: ignore[assignment]


_MAX_BUFFER_CHARS = 200_000
@dataclass(frozen=True)
class WebTerminalSession:
    session_id: str
    task_name: str
    task_path: Path
    kind: str
    command: tuple[str, ...]
    cwd: Path
    exited: bool
    run_id: str | None
    terminal_mode: str
    encoding: str

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.session_id,
            "task": self.task_name,
            "kind": self.kind,
            "command": list(self.command),
            "cwd": str(self.cwd),
            "exited": self.exited,
            "run_id": self.run_id,
            "terminal_mode": self.terminal_mode,
            "encoding": self.encoding,
        }


@dataclass
class _ManagedTerminalSession:
    session_id: str
    task_name: str
    task_path: Path
    kind: str
    command: tuple[str, ...]
    cwd: Path
    process: subprocess.Popen[Any]
    output: str = ""
    output_start: int = 0
    output_end: int = 0
    closed: bool = False
    run_id: str | None = None
    pty_master_fd: int | None = None
    terminal_mode: str = "pipe"
    encoding: str = "utf-8"
    reader_done: threading.Event = field(default_factory=threading.Event, repr=False)
    io_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    termination_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    termination_started: bool = False

    def snapshot(self) -> WebTerminalSession:
        return WebTerminalSession(
            session_id=self.session_id,
            task_name=self.task_name,
            task_path=self.task_path,
            kind=self.kind,
            command=self.command,
            cwd=self.cwd,
            exited=self.process.returncode is not None,
            run_id=self.run_id,
            terminal_mode=self.terminal_mode,
            encoding=self.encoding,
        )


class WebTerminalManager:
    def __init__(self) -> None:
        self._sessions: dict[str, _ManagedTerminalSession] = {}
        self._lock = threading.Lock()

    def start(
        self,
        *,
        task_name: str,
        task_path: Path,
        command: list[str],
        cwd: Path,
        env: dict[str, str],
        kind: str,
        run_id: str | None = None,
    ) -> WebTerminalSession:
        process, pty_master_fd = _start_process(command, cwd=cwd, env=env)
        session = _ManagedTerminalSession(
            session_id=uuid4().hex,
            task_name=task_name,
            task_path=task_path,
            kind=kind,
            command=tuple(command),
            cwd=cwd,
            process=process,
            run_id=run_id,
            pty_master_fd=pty_master_fd,
            terminal_mode="pty" if pty_master_fd is not None else "pipe",
            encoding="utf-8" if pty_master_fd is not None else _pipe_encoding(),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        reader = threading.Thread(target=self._read_output, args=(session,), daemon=True)
        try:
            reader.start()
        except Exception:
            with self._lock:
                self._sessions.pop(session.session_id, None)
            _terminate_process(session.process)
            _close_process_streams(session.process)
            if session.pty_master_fd is not None:
                os.close(session.pty_master_fd)
                session.pty_master_fd = None
            raise
        return session.snapshot()

    def sessions(self, task_name: str | None = None) -> list[WebTerminalSession]:
        with self._lock:
            sessions = list(self._sessions.values())
        if task_name is not None:
            sessions = [session for session in sessions if session.task_name == task_name]
        return [session.snapshot() for session in sessions]

    def session(self, session_id: str) -> WebTerminalSession:
        return self._session(session_id).snapshot()

    def _session(self, session_id: str) -> _ManagedTerminalSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown terminal session: {session_id}")
        return session

    def send(self, session_id: str, data: str) -> None:
        session = self._session(session_id)
        payload = data.encode(session.encoding, errors="replace")
        with session.io_lock:
            with self._lock:
                if session.closed or session.process.returncode is not None:
                    raise ValueError("terminal session is closed")
                master_fd = session.pty_master_fd
                stdin = session.process.stdin
            try:
                if master_fd is not None:
                    _write_all(master_fd, payload)
                    return
                if stdin is None:
                    raise ValueError("terminal session is closed")
                stdin.write(payload)
                stdin.flush()
            except (BrokenPipeError, OSError, ValueError) as error:
                raise ValueError("terminal session is closed") from error

    def resize(self, session_id: str, *, rows: int, columns: int) -> dict[str, Any]:
        session = self._session(session_id)
        rows = max(1, min(int(rows), 200))
        columns = max(1, min(int(columns), 500))
        with session.io_lock:
            with self._lock:
                if session.closed or session.process.returncode is not None:
                    raise ValueError("terminal session is closed")
                master_fd = session.pty_master_fd
            resized = master_fd is not None and _set_terminal_window_size(
                master_fd,
                rows=rows,
                columns=columns,
            )
        return {"id": session.session_id, "rows": rows, "columns": columns, "resized": resized}

    def output(self, session_id: str, *, offset: int = 0) -> dict[str, Any]:
        session = self._session(session_id)
        with self._lock:
            output = session.output
            output_start = session.output_start
            output_end = session.output_end
        requested_offset = max(0, int(offset))
        effective_offset = max(output_start, min(requested_offset, output_end))
        return {
            "id": session.session_id,
            "task": session.task_name,
            "offset": output_end,
            "start_offset": output_start,
            "truncated": requested_offset < output_start,
            "text": output[effective_offset - output_start :],
            "exited": session.process.returncode is not None,
        }

    def close(self, session_id: str) -> bool:
        session = self._session(session_id)
        with self._lock:
            session.closed = True
        with session.termination_lock:
            if not session.reader_done.is_set() and not session.termination_started:
                session.termination_started = True
                try:
                    _terminate_process(session.process)
                except Exception:
                    session.termination_started = False
                    raise
        if not session.reader_done.wait(timeout=3):
            raise RuntimeError("terminal output reader did not stop")
        with self._lock:
            self._sessions.pop(session_id, None)
        return True

    def running_agent_kinds(self, task_name: str) -> tuple[str, ...]:
        kinds: list[str] = []
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            if (
                session.task_name == task_name
                and session.kind in {"codex", "claude"}
                and session.process.returncode is None
            ):
                kinds.append(session.kind)
        return tuple(kinds)

    def local_agent_run_ids(self) -> frozenset[str]:
        return frozenset(
            session.run_id
            for session in self._managed_sessions()
            if session.run_id is not None and session.process.returncode is None
        )

    def _managed_sessions(self) -> list[_ManagedTerminalSession]:
        with self._lock:
            return list(self._sessions.values())

    def _read_output(self, session: _ManagedTerminalSession) -> None:
        if session.pty_master_fd is not None:
            self._read_pty_output(session)
            return
        stream = session.process.stdout
        if stream is None:
            session.reader_done.set()
            return
        decoder = codecs.getincrementaldecoder(session.encoding)(errors="replace")
        try:
            read_chunk = getattr(stream, "read1", stream.read)
            while True:
                chunk = read_chunk(4096)
                if not chunk:
                    break
                self._append_output(session, decoder.decode(chunk))
        finally:
            self._append_output(session, decoder.decode(b"", final=True))
            with session.termination_lock:
                session.process.wait()
                self._close_session_streams(session)
                session.reader_done.set()

    def _read_pty_output(self, session: _ManagedTerminalSession) -> None:
        assert session.pty_master_fd is not None
        decoder = codecs.getincrementaldecoder(session.encoding)(errors="replace")
        try:
            while True:
                master_fd = session.pty_master_fd
                if master_fd is None:
                    break
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError as error:
                    if error.errno in {errno.EIO, errno.EBADF}:
                        break
                    raise
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if not text:
                    continue
                self._append_output(session, text)
        finally:
            self._append_output(session, decoder.decode(b"", final=True))
            with session.termination_lock:
                session.process.wait()
                self._close_session_streams(session)
                session.reader_done.set()

    def _append_output(self, session: _ManagedTerminalSession, text: str) -> None:
        if not text:
            return
        with self._lock:
            combined = session.output + text
            dropped = max(0, len(combined) - _MAX_BUFFER_CHARS)
            session.output = combined[dropped:]
            session.output_start += dropped
            session.output_end += len(text)

    def _close_session_streams(self, session: _ManagedTerminalSession) -> None:
        with session.io_lock:
            with self._lock:
                master_fd = session.pty_master_fd
                session.pty_master_fd = None
            if master_fd is not None:
                try:
                    os.close(master_fd)
                except OSError:
                    pass
            _close_process_streams(session.process)


def _start_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> tuple[subprocess.Popen[Any], int | None]:
    if os.name != "nt" and pty is not None:
        master_fd, slave_fd = pty.openpty()
        try:
            _set_terminal_window_size(slave_fd, rows=40, columns=240)
            launcher = Path(__file__).with_name("pty_exec.py")
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(launcher),
                    *command,
                ],
                cwd=str(cwd),
                env=env,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
        except Exception:
            os.close(master_fd)
            raise
        finally:
            os.close(slave_fd)
        return process, master_fd
    if os.name == "nt":
        launcher = Path(__file__).with_name("windows_exec.py")
        command = [sys.executable, str(launcher), *command]
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        start_new_session=True,
    )
    return process, None


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        if process.poll() is None:
            process.terminate()
    else:
        if not _signal_process_group(process.pid, signal.SIGTERM) and process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        leader_exited = process.poll() is not None
        group_exited = os.name == "nt" or not _process_group_exists(process.pid)
        if leader_exited and group_exited:
            process.wait()
            return
        time.sleep(0.02)
    if os.name == "nt":
        if process.poll() is None:
            process.kill()
    else:
        if not _signal_process_group(process.pid, signal.SIGKILL) and process.poll() is None:
            process.kill()
    process.wait(timeout=2)


def _signal_process_group(process_id: int, signal_number: int) -> bool:
    try:
        os.killpg(process_id, signal_number)
    except ProcessLookupError:
        return False
    return True


def _process_group_exists(process_id: int) -> bool:
    return _signal_process_group(process_id, 0)


def _close_process_streams(process: subprocess.Popen[Any]) -> None:
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _pipe_encoding() -> str:
    if os.name != "nt":
        return "utf-8"
    code_page = ctypes.windll.kernel32.GetOEMCP()
    return f"cp{code_page}" if code_page else "utf-8"


def _write_all(fd: int, payload: bytes) -> None:
    written = 0
    while written < len(payload):
        try:
            count = os.write(fd, payload[written:])
        except InterruptedError:
            continue
        if count <= 0:
            raise OSError(errno.EPIPE, "terminal write returned no data")
        written += count


def _set_terminal_window_size(fd: int, *, rows: int, columns: int) -> bool:
    if fcntl is None or termios is None:
        return False
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    except OSError:
        return False
    return True
