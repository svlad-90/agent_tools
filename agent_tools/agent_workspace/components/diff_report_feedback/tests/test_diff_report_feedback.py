from __future__ import annotations

import json
import urllib.error
import urllib.request

from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.diff_report_feedback.api import start_diff_report_feedback_server


def test_diff_report_feedback_server_handshake_and_drawio_write(tmp_path: Path) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        handshake = _json_get(f"{handle.base_url}/api/v1/handshake")

        assert handshake["ok"] is True
        assert handshake["workspace"] == str(tmp_path.resolve())
        assert handshake["capabilities"] == ["drawio"]

        url = (
            f"{handle.base_url}/api/v1/artifact"
            "?task=tasks/sample"
            "&path=report/drawio/flow.drawio"
        )
        request = urllib.request.Request(url, data=b"<mxfile />", method="PUT")
        written = json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))

        assert written == {
            "bytes": 10,
            "ok": True,
            "path": "tasks/sample/report/drawio/flow.drawio",
        }
        assert (tmp_path / "tasks" / "sample" / "report" / "drawio" / "flow.drawio").read_text(
            encoding="utf-8"
        ) == "<mxfile />"
        assert urllib.request.urlopen(url, timeout=5).read() == b"<mxfile />"
    finally:
        handle.stop()


def test_diff_report_feedback_server_rejects_paths_outside_drawio(tmp_path: Path) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        bad_url = (
            f"{handle.base_url}/api/v1/artifact"
            "?task=tasks/sample"
            "&path=report/diff/report.json"
        )
        request = urllib.request.Request(bad_url, data=b"{}", method="PUT")

        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("unsafe path was accepted")
    finally:
        handle.stop()


def _json_get(url: str) -> dict[str, object]:
    return json.loads(urllib.request.urlopen(url, timeout=5).read().decode("utf-8"))
