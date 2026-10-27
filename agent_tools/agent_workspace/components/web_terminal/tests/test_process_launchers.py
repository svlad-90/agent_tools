from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import time

import pytest

from agent_tools.agent_workspace.components.web_terminal.src import windows_exec


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX pty")
def test_pty_launcher_gives_command_a_controlling_terminal() -> None:
    import pty

    launcher = Path(windows_exec.__file__).with_name("pty_exec.py")
    master_fd, slave_fd = pty.openpty()
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                str(launcher),
                sys.executable,
                "-c",
                "import os; print(os.tcgetpgrp(0) == os.getpgrp())",
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
    finally:
        os.close(slave_fd)

    try:
        output = os.read(master_fd, 4096).decode("utf-8", errors="replace")
        assert process.wait(timeout=5) == 0
    finally:
        os.close(master_fd)

    assert "True" in output


def test_windows_launcher_configures_job_before_starting_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Result:
        returncode = 7

    monkeypatch.setattr(windows_exec.os, "name", "nt")
    monkeypatch.setattr(
        windows_exec,
        "_configure_process_job",
        lambda: events.append("configure-job"),
    )
    monkeypatch.setattr(
        windows_exec.subprocess,
        "run",
        lambda command, check: events.append(f"run:{command[0]}") or Result(),
    )

    assert windows_exec.main(["child.exe"]) == 7
    assert events == ["configure-job", "run:child.exe"]


@pytest.mark.skipif(os.name != "nt", reason="requires Windows Job Objects")
def test_windows_launcher_terminates_descendant_when_launcher_exits(
    tmp_path: Path,
) -> None:
    import ctypes
    from ctypes import wintypes

    launcher = Path(windows_exec.__file__)
    child_pid_file = tmp_path / "child.pid"
    child_code = (
        "from pathlib import Path; import os, time; "
        f"Path({str(child_pid_file)!r}).write_text(str(os.getpid())); "
        "time.sleep(30)"
    )
    process = subprocess.Popen(
        [sys.executable, str(launcher), sys.executable, "-c", child_code],
        cwd=tmp_path,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not child_pid_file.exists():
            time.sleep(0.02)
        assert child_pid_file.exists()
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        child_handle = kernel32.OpenProcess(0x00100000, False, child_pid)
        assert child_handle
        try:
            process.terminate()
            process.wait(timeout=5)
            assert kernel32.WaitForSingleObject(child_handle, 5000) == 0
        finally:
            kernel32.CloseHandle(child_handle)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
