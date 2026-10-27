from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import errno
import os
import subprocess
import sys
import threading
import time

import pytest

from agent_tools.agent_workspace.components.web_terminal.api import WebTerminalManager
from agent_tools.agent_workspace.components.web_terminal.api import shell_environment
from agent_tools.agent_workspace.components.web_terminal.src import terminal as terminal_module
from agent_tools.agent_workspace.components.web_terminal.src.terminal import _MAX_BUFFER_CHARS
from agent_tools.agent_workspace.components.web_terminal.src.terminal import _write_all
from agent_tools.agent_workspace.components.web_terminal.src.terminal import (
    _ManagedTerminalSession,
)


def test_web_terminal_manager_runs_process_and_reads_output(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "print('terminal-ready')"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    deadline = time.time() + 5
    output = {"text": ""}
    while time.time() < deadline:
        output = manager.output(session.session_id)
        if "terminal-ready" in output["text"]:
            break
        time.sleep(0.05)

    assert "terminal-ready" in output["text"]
    assert output["task"] == "sample-task"
    assert manager.sessions("sample-task")[0].session_id == session.session_id
    assert not hasattr(session, "process")
    with pytest.raises(FrozenInstanceError):
        session.task_name = "changed"  # type: ignore[misc]
    expected_mode = "pipe" if os.name == "nt" else "pty"
    assert session.to_json()["terminal_mode"] == expected_mode


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_web_terminal_preserves_raw_pty_stream(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('alpha\\r\\nbeta\\x1b[31mred\\x1b[0m')",
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    deadline = time.time() + 5
    output = {"text": ""}
    while time.time() < deadline:
        output = manager.output(session.session_id)
        if output["exited"] and "beta" in output["text"] and "red" in output["text"]:
            break
        time.sleep(0.05)

    assert "alpha\r" in output["text"]
    assert "\nbeta" in output["text"]
    assert "\x1b[31m" in output["text"]


def test_web_terminal_manager_closes_process_streams_after_exit(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "print('done')"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)

    assert managed.reader_done.wait(timeout=5)

    assert managed.process.returncode is not None
    assert managed.pty_master_fd is None
    assert manager.session(session.session_id).exited is True
    assert session.to_json()["terminal_mode"] == ("pipe" if os.name == "nt" else "pty")


def test_web_terminal_close_closes_pty_master(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)
    master_fd = managed.pty_master_fd

    manager.close(session.session_id)

    assert managed.process.returncode is not None
    assert managed.reader_done.is_set()
    assert managed.pty_master_fd is None
    with pytest.raises(KeyError, match="unknown terminal session"):
        manager.session(session.session_id)
    if master_fd is not None:
        try:
            os.fstat(master_fd)
        except OSError as error:
            assert error.errno == errno.EBADF
        else:  # pragma: no cover - defensive assertion for POSIX fd leaks.
            raise AssertionError("pty master fd remained open")


def test_close_does_not_signal_process_group_after_reader_reaped_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "pass"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)
    assert managed.reader_done.wait(timeout=5)

    def unexpected_killpg(process_id: int, signal_number: int) -> None:
        raise AssertionError(f"unexpected killpg({process_id}, {signal_number})")

    monkeypatch.setattr(terminal_module.os, "killpg", unexpected_killpg)

    assert manager.close(session.session_id) is True


def test_concurrent_close_terminates_process_only_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    real_terminate = terminal_module._terminate_process
    termination_entered = threading.Event()
    allow_termination = threading.Event()
    termination_calls = 0
    errors: list[Exception] = []

    def controlled_terminate(process: subprocess.Popen[object]) -> None:
        nonlocal termination_calls
        termination_calls += 1
        termination_entered.set()
        assert allow_termination.wait(timeout=5)
        real_terminate(process)

    def close_session() -> None:
        try:
            manager.close(session.session_id)
        except Exception as error:  # pragma: no cover - asserted below.
            errors.append(error)

    monkeypatch.setattr(terminal_module, "_terminate_process", controlled_terminate)
    first = threading.Thread(target=close_session)
    second = threading.Thread(target=close_session)
    first.start()
    assert termination_entered.wait(timeout=5)
    second.start()
    allow_termination.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert errors == []
    assert termination_calls == 1
    assert not first.is_alive()
    assert not second.is_alive()


def test_close_can_retry_after_termination_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)
    real_terminate = terminal_module._terminate_process
    termination_calls = 0

    def fail_once(process: subprocess.Popen[object]) -> None:
        nonlocal termination_calls
        termination_calls += 1
        if termination_calls == 1:
            raise PermissionError("simulated termination failure")
        real_terminate(process)

    monkeypatch.setattr(terminal_module, "_terminate_process", fail_once)

    with pytest.raises(PermissionError, match="simulated termination failure"):
        manager.close(session.session_id)
    assert managed.process.returncode is None

    assert manager.close(session.session_id) is True
    assert termination_calls == 2
    assert managed.process.returncode is not None


def test_web_terminal_resize_returns_clamped_dimensions(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    try:
        result = manager.resize(session.session_id, rows=500, columns=1000)
    finally:
        manager.close(session.session_id)

    assert result == {
        "id": session.session_id,
        "rows": 200,
        "columns": 500,
        "resized": os.name != "nt",
    }


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_web_terminal_launcher_cannot_be_shadowed_by_task_package(tmp_path: Path) -> None:
    shadow = tmp_path / "agent_tools"
    shadow.mkdir()
    marker = tmp_path / "shadow-imported"
    (shadow / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
        encoding="utf-8",
    )
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "print('safe-launch')"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    deadline = time.time() + 5
    output = {"text": ""}
    while time.time() < deadline:
        output = manager.output(session.session_id)
        if output["exited"] and "safe-launch" in output["text"]:
            break
        time.sleep(0.05)

    assert "safe-launch" in output["text"]
    assert not marker.exists()


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_blocked_send_does_not_hold_manager_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)
    write_started = threading.Event()
    allow_write = threading.Event()

    def blocked_write(fd: int, payload: bytes) -> None:
        assert fd == managed.pty_master_fd
        assert payload == b"input"
        write_started.set()
        assert allow_write.wait(timeout=5)

    monkeypatch.setattr(terminal_module, "_write_all", blocked_write)
    sender = threading.Thread(target=manager.send, args=(session.session_id, "input"))
    sender.start()
    try:
        assert write_started.wait(timeout=5)
        assert manager.output(session.session_id)["id"] == session.session_id
    finally:
        allow_write.set()
        sender.join(timeout=5)
        manager.close(session.session_id)

    assert not sender.is_alive()


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_close_interrupts_blocked_send(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)
    write_started = threading.Event()
    send_finished = threading.Event()

    def write_until_process_exits(fd: int, payload: bytes) -> None:
        write_started.set()
        deadline = time.time() + 5
        while time.time() < deadline and managed.process.returncode is None:
            time.sleep(0.01)
        raise BrokenPipeError

    def send_input() -> None:
        try:
            manager.send(session.session_id, "input")
        except ValueError:
            pass
        finally:
            send_finished.set()

    monkeypatch.setattr(terminal_module, "_write_all", write_until_process_exits)
    sender = threading.Thread(target=send_input)
    sender.start()
    assert write_started.wait(timeout=5)

    manager.close(session.session_id)
    sender.join(timeout=5)

    assert send_finished.is_set()
    assert not sender.is_alive()
    assert managed.process.returncode is not None


def test_start_cleans_up_process_when_reader_thread_cannot_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started_processes: list[subprocess.Popen[object]] = []
    real_start_process = terminal_module._start_process

    def capturing_start_process(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> tuple[subprocess.Popen[object], int | None]:
        process, master_fd = real_start_process(command, cwd=cwd, env=env)
        started_processes.append(process)
        return process, master_fd

    def fail_thread_start(thread: threading.Thread) -> None:
        raise RuntimeError("thread unavailable")

    monkeypatch.setattr(terminal_module, "_start_process", capturing_start_process)
    monkeypatch.setattr(threading.Thread, "start", fail_thread_start)

    with pytest.raises(RuntimeError, match="thread unavailable"):
        WebTerminalManager().start(
            task_name="sample-task",
            task_path=tmp_path,
            command=[sys.executable, "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            env=os.environ.copy(),
            kind="shell",
        )

    assert len(started_processes) == 1
    assert started_processes[0].poll() is not None


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX process groups")
def test_close_terminates_descendant_process_group(tmp_path: Path) -> None:
    child_ready = tmp_path / "child-ready"
    child_stopped = tmp_path / "child-stopped"
    child_code = (
        "import pathlib, signal, sys, time; "
        f"marker = pathlib.Path({str(child_stopped)!r}); "
        "signal.signal(signal.SIGTERM, lambda *_: (marker.touch(), sys.exit(0))); "
        f"pathlib.Path({str(child_ready)!r}).touch(); "
        "time.sleep(30)"
    )
    parent_code = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "time.sleep(30)"
    )
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[sys.executable, "-c", parent_code],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)

    deadline = time.time() + 5
    while time.time() < deadline and not child_ready.exists():
        time.sleep(0.02)
    assert child_ready.exists()
    manager.close(session.session_id)

    assert child_stopped.exists()
    assert managed.reader_done.is_set()


@pytest.mark.skipif(os.name == "nt" or not Path("/bin/bash").exists(), reason="requires POSIX bash")
def test_web_terminal_bash_has_controlling_terminal(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=["/bin/bash", "-i"],
        cwd=tmp_path,
        env=shell_environment(os.environ.copy(), "sample-task"),
        kind="shell",
    )

    try:
        manager.send(session.session_id, "echo web-shell-ok\nexit\n")
        deadline = time.time() + 5
        output = {"text": ""}
        while time.time() < deadline:
            output = manager.output(session.session_id)
            if "web-shell-ok" in output["text"] and output["exited"]:
                break
            time.sleep(0.05)
    finally:
        if not manager.session(session.session_id).exited:
            manager.close(session.session_id)

    assert "web-shell-ok" in output["text"]
    assert "cannot set terminal process group" not in output["text"]
    assert "no job control in this shell" not in output["text"]


def test_output_offsets_continue_after_buffer_truncation(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = _ManagedTerminalSession(
        session_id="session",
        task_name="task",
        task_path=tmp_path,
        kind="shell",
        command=("bash", "-i"),
        cwd=tmp_path,
        process=subprocess.Popen([sys.executable, "-c", ""]),
    )
    try:
        manager._sessions[session.session_id] = session
        manager._append_output(session, "x" * _MAX_BUFFER_CHARS)
        first = manager.output(session.session_id)
        manager._append_output(session, "new")
        second = manager.output(session.session_id, offset=first["offset"])

        assert second["text"] == "new"
        assert second["offset"] == _MAX_BUFFER_CHARS + 3
        assert second["start_offset"] == 3
        assert second["truncated"] is False
        assert manager.output(session.session_id, offset=0)["truncated"] is True
    finally:
        session.process.wait(timeout=5)


def test_write_all_retries_partial_and_interrupted_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written = bytearray()
    calls = 0

    def fake_write(fd: int, payload: bytes) -> int:
        nonlocal calls
        assert fd == 17
        calls += 1
        if calls == 1:
            raise InterruptedError
        count = min(2, len(payload))
        written.extend(payload[:count])
        return count

    monkeypatch.setattr(terminal_module.os, "write", fake_write)

    _write_all(17, b"abcdef")

    assert written == b"abcdef"


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_web_terminal_preserves_utf8_split_across_reads(tmp_path: Path) -> None:
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[
            sys.executable,
            "-c",
            (
                "import os, time; "
                "os.write(1, b'\\xe2'); time.sleep(0.1); "
                "os.write(1, b'\\x82\\xac')"
            ),
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    deadline = time.time() + 5
    output = {"text": ""}
    while time.time() < deadline:
        output = manager.output(session.session_id)
        if output["exited"] and "€" in output["text"]:
            break
        time.sleep(0.05)

    assert "€" in output["text"]
    assert "�" not in output["text"]


def test_pipe_fallback_streams_output_without_waiting_for_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(terminal_module, "pty", None)
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[
            sys.executable,
            "-c",
            "import sys, time; sys.stdout.write('prompt> '); sys.stdout.flush(); time.sleep(1)",
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )

    try:
        deadline = time.time() + 0.8
        output = {"text": ""}
        while time.time() < deadline:
            output = manager.output(session.session_id)
            if "prompt> " in output["text"]:
                break
            time.sleep(0.05)

        assert "prompt> " in output["text"]
        assert manager.session(session.session_id).exited is False
        assert manager.resize(session.session_id, rows=30, columns=90)["resized"] is False
    finally:
        manager.close(session.session_id)


def test_pipe_fallback_uses_selected_windows_code_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(terminal_module, "pty", None)
    monkeypatch.setattr(terminal_module, "_pipe_encoding", lambda: "cp1251")
    manager = WebTerminalManager()
    session = manager.start(
        task_name="sample-task",
        task_path=tmp_path,
        command=[
            sys.executable,
            "-c",
            "import os; os.write(1, 'Привет'.encode('cp1251'))",
        ],
        cwd=tmp_path,
        env=os.environ.copy(),
        kind="shell",
    )
    managed = manager._session(session.session_id)

    deadline = time.time() + 5
    output = {"text": ""}
    while time.time() < deadline:
        output = manager.output(session.session_id)
        if managed.reader_done.is_set():
            break
        time.sleep(0.05)

    assert output["text"] == "Привет"
    assert session.encoding == "cp1251"
