from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from agent_tools.tools.diff_report.cli import main
from agent_tools.tools.diff_report.core import generate_report


def _browser() -> str | None:
    configured = os.environ.get("DIFF_REPORT_BROWSER")
    if configured:
        return configured
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


@unittest.skipUnless(_browser(), "Chrome-compatible browser is not available")
class BrowserSmokeTests(unittest.TestCase):
    def test_report_json_self_test_runs_in_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_json = root / "report.json"
            output = root / "report.html"
            report_json.write_text(json.dumps(_generic_report_payload()), encoding="utf-8")

            status = main(
                [
                    "--report-json",
                    str(report_json),
                    "--output",
                    str(output),
                    "--report-test-mode",
                ]
            )

            self.assertEqual(0, status)
            result = _evaluate_in_browser(
                output,
                "window.__reportSelfTest.runAll()",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("pass"), result)
        self.assertGreaterEqual(int(result.get("total", 0)), 1)

    def test_story_bar_pinning_does_not_jump_during_manual_scroll(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            diff_path = root / "change.patch"
            comments_path = root / "comments.json"
            output = root / "report.html"
            diff_path.write_text(_long_diff(), encoding="utf-8")
            comments_path.write_text(json.dumps(_story_comments()), encoding="utf-8")
            generate_report(
                output_path=output,
                title="Synthetic scroll report",
                diff_file=diff_path,
                comments_file=comments_path,
            )

            result = _evaluate_in_browser(
                output,
                r"""(async () => {
                  window.scrollTo(0, 1400);
                  window.dispatchEvent(new WheelEvent("wheel", {deltaY: 1400, bubbles: true}));
                  await new Promise(resolve => setTimeout(resolve, 180));
                  const afterWait = window.scrollY;
                  const sentinel = document.querySelector(".story-sentinel");
                  const sentinelHeight = sentinel ? sentinel.getBoundingClientRect().height : 0;
                  const pinned = document.body.classList.contains("has-pinned-story");
                  window.scrollTo(0, 900);
                  await new Promise(resolve => setTimeout(resolve, 80));
                  return {
                    afterWait,
                    afterManual: window.scrollY,
                    pinned,
                    sentinelHeight
                  };
                })()""",
                await_promise=True,
            )

        self.assertIsInstance(result, dict)
        self.assertGreaterEqual(result.get("afterWait", 0), 1000, result)
        self.assertGreaterEqual(result.get("afterManual", 0), 850, result)
        self.assertTrue(result.get("pinned"), result)
        self.assertGreater(result.get("sentinelHeight", 0), 0, result)


def _generic_report_payload() -> dict[str, object]:
    rows = [{"id": f"row-{index:03d}", "status": "not_failed"} for index in range(1, 80)]
    return {
        "title": "Synthetic dashboard",
        "summary_blocks": [{"type": "text", "body": "Synthetic browser smoke report."}],
        "metric_tables": [
            {
                "title": "Metrics",
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "passed", "label": "Passed"},
                ],
                "rows": [
                    {
                        "cells": {
                            "name": {
                                "text": "Components",
                                "graph_view": {
                                    "focus": "product:test",
                                    "types": ["product", "component"],
                                    "target_type": "component",
                                },
                            },
                            "passed": {
                                "text": "3",
                                "status": "not_failed",
                                "graph_view": {
                                    "focus": "product:test",
                                    "types": ["product", "component"],
                                    "target_type": "component",
                                    "filters": {"component": {"status": ["not_failed"]}},
                                },
                            },
                        }
                    }
                ],
            }
        ],
        "tables": [{"title": "Synthetic rows", "columns": ["id", "status"], "rows": rows}],
        "relationship_graph": {
            "title": "Synthetic graph",
            "nodes": [
                {"id": "product:test", "type": "product", "label": "Test product", "status": "not_failed"},
                {"id": "component:1", "type": "component", "label": "Component 1", "status": "not_failed"},
                {"id": "component:2", "type": "component", "label": "Component 2", "status": "not_failed"},
                {"id": "component:3", "type": "component", "label": "Component 3", "status": "not_failed"},
            ],
            "edges": [
                {"source": "product:test", "target": "component:1", "relation": "contains"},
                {"source": "product:test", "target": "component:2", "relation": "contains"},
                {"source": "product:test", "target": "component:3", "relation": "contains"},
            ],
        },
    }


def _story_comments() -> dict[str, object]:
    return {
        "summary": "Synthetic story scroll report.",
        "inline": [
            {
                "file": "src/demo.c",
                "line": 120,
                "title": "Late line",
                "body": "This comment forces a long page.",
            }
        ],
        "story": [
            {"title": "Top", "body": "Start at the file.", "file": "src/demo.c"},
            {
                "title": "Late comment",
                "body": "Jump near the end.",
                "comment": {"file": "src/demo.c", "line": 120},
            },
        ],
    }


def _long_diff() -> str:
    added_lines = "\n".join(f"+int demo_{index:03d}(void) {{ return {index}; }}" for index in range(1, 181))
    return (
        "diff --git a/src/demo.c b/src/demo.c\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        "+++ b/src/demo.c\n"
        "@@ -0,0 +1,180 @@\n"
        f"{added_lines}\n"
    )


def _evaluate_in_browser(html: Path, expression: str, *, await_promise: bool = False) -> object:
    browser = _browser()
    if not browser:
        raise unittest.SkipTest("Chrome-compatible browser is not available")
    profile_dir = Path(tempfile.mkdtemp(prefix="diff-report-browser-test-"))
    process = subprocess.Popen(
        [
            browser,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-crash-reporter",
            "--disable-crashpad",
            f"--user-data-dir={profile_dir}",
            "--remote-debugging-port=0",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        port = _wait_for_debug_port(profile_dir)
        targets = _browser_json(port, "/json/list")
        target = next(item for item in targets if isinstance(item, dict) and item.get("type") == "page")
        with _CdpConnection(target["webSocketDebuggerUrl"]) as cdp:
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False},
            )
            cdp.call("Page.navigate", {"url": html.resolve().as_uri()})
            _wait_for_page_ready(cdp)
            result = cdp.call(
                "Runtime.evaluate",
                {"expression": expression, "awaitPromise": await_promise, "returnByValue": True},
            )
            value = result.get("result", {}).get("result", {})
            if value.get("subtype") == "error":
                raise AssertionError(value.get("description") or value)
            return value.get("value")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        shutil.rmtree(profile_dir, ignore_errors=True)


def _wait_for_page_ready(cdp: "_CdpConnection") -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = cdp.call("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
        if response.get("result", {}).get("result", {}).get("value") == "complete":
            return
        time.sleep(0.05)
    raise RuntimeError("page did not finish loading")


def _wait_for_debug_port(profile_dir: Path) -> int:
    port_file = profile_dir / "DevToolsActivePort"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if port_file.is_file():
            return int(port_file.read_text(encoding="utf-8").splitlines()[0])
        time.sleep(0.05)
    raise RuntimeError("Chrome DevTools port file was not created")


def _browser_json(port: int, path: str) -> object:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class _CdpConnection:
    def __init__(self, websocket_url: str) -> None:
        prefix = "ws://"
        if not websocket_url.startswith(prefix):
            raise ValueError(f"unsupported DevTools websocket URL: {websocket_url}")
        host_port, self.path = websocket_url[len(prefix) :].split("/", 1)
        self.path = "/" + self.path
        self.host, port = host_port.split(":", 1)
        self.port = int(port)
        self.sock: socket.socket | None = None
        self.next_id = 1

    def __enter__(self) -> "_CdpConnection":
        raw = socket.create_connection((self.host, self.port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        raw.sendall(request.encode("ascii"))
        response = raw.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raw.close()
            raise RuntimeError("DevTools websocket handshake failed")
        self.sock = raw
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def call(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        message_id = self.next_id
        self.next_id += 1
        self._send_json({"id": message_id, "method": method, "params": params or {}})
        while True:
            message = self._recv_json()
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message

    def _send_json(self, payload: dict[str, object]) -> None:
        self._send_frame(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    def _recv_json(self) -> dict[str, object]:
        while True:
            opcode, payload = self._recv_frame()
            if opcode == 1:
                return json.loads(payload.decode("utf-8"))
            if opcode == 9:
                self._send_frame(payload, opcode=10)

    def _send_frame(self, payload: bytes, opcode: int = 1) -> None:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126])
            header.extend(struct.pack("!H", length))
        else:
            header.extend([0x80 | 127])
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_frame(self) -> tuple[int, bytes]:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        first, second = self._read_exact(2)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        if self.sock is None:
            raise RuntimeError("websocket is not connected")
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise RuntimeError("websocket closed")
            chunks.extend(chunk)
        return bytes(chunks)
