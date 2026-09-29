from __future__ import annotations

import json
import urllib.error
import urllib.request
from unittest import mock

from agent_tools.agent_workspace.components.test_support.src.helpers import *
from agent_tools.agent_workspace.components.diff_report_feedback.api import start_diff_report_feedback_server


def test_diff_report_feedback_server_handshake_and_drawio_write(tmp_path: Path) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        handshake = _json_get(f"{handle.base_url}/api/v1/handshake")

        assert handshake["ok"] is True
        assert handshake["workspace"] == str(tmp_path.resolve())
        assert handshake["capabilities"] == [
            "drawio",
            "agent_diagram",
            "agent_diagram_plantuml",
            "agent_diagram_preview",
        ]
        assert handshake["artifact_roots"] == ["tasks/*/report/drawio"]

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


def test_diff_report_feedback_server_edits_agent_diagram_json(tmp_path: Path) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        comments = tmp_path / "tasks" / "sample" / "report" / "diff" / "comments.json"
        comments.parent.mkdir(parents=True)
        comments.write_text(
            json.dumps(
                {
                    "diagrams": {
                        "flow": {
                            "title": "Generated flow",
                            "source": "../puml/flow.puml",
                            "svg": "../puml/flow.svg",
                            "agent_diagram": {
                                "type": "component_graph",
                                "nodes": [{"id": "a", "label": "A"}],
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        url = (
            f"{handle.base_url}/api/v1/agent-diagram/source"
            "?task=tasks/sample"
            "&comments=report/diff/comments.json"
            "&diagram=flow"
        )
        source = _json_get(url)

        assert source["ok"] is True
        assert source["diagram"] == "flow"
        assert source["value"]["agent_diagram"]["nodes"] == [{"id": "a", "label": "A"}]

        updated = source["value"]
        updated["agent_diagram"]["nodes"] = [{"id": "b", "label": "B"}]
        with mock.patch(
            "agent_tools.agent_workspace.components.diff_report_feedback.src.server.agent_diagram_artifacts",
            return_value=('@startuml\ncomponent "B" as b\n@enduml\n', "<svg><text>B</text></svg>"),
        ):
            request = urllib.request.Request(
                url,
                data=json.dumps({"value": updated}).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            rendered = json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))

        assert rendered["ok"] is True
        assert rendered["diagram"] == "flow"
        assert "B" in rendered["source"]
        assert rendered["svg"] == "<svg><text>B</text></svg>"
        assert '"label": "B"' in comments.read_text(encoding="utf-8")
        assert "B" in (tmp_path / "tasks" / "sample" / "report" / "puml" / "flow.puml").read_text(encoding="utf-8")
        assert (tmp_path / "tasks" / "sample" / "report" / "puml" / "flow.svg").read_text(
            encoding="utf-8"
        ) == "<svg><text>B</text></svg>"
    finally:
        handle.stop()


def test_diff_report_feedback_server_edits_agent_diagram_plantuml_as_json(tmp_path: Path) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        comments = tmp_path / "tasks" / "sample" / "report" / "diff" / "comments.json"
        comments.parent.mkdir(parents=True)
        comments.write_text(
            json.dumps(
                {
                    "diagrams": {
                        "flow": {
                            "title": "Generated flow",
                            "source": "../puml/flow.puml",
                            "svg": "../puml/flow.svg",
                            "agent_diagram": {
                                "type": "component_graph",
                                "nodes": [{"id": "a", "label": "A"}],
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        url = (
            f"{handle.base_url}/api/v1/agent-diagram/source"
            "?task=tasks/sample"
            "&comments=report/diff/comments.json"
            "&diagram=flow"
        )
        source = _json_get(url)

        assert source["source_format"] == "plantuml"
        assert 'component "A" as a' in source["source"]

        next_source = source["source"].replace('component "A" as a', 'component "B" as b')
        with mock.patch(
            "agent_tools.agent_workspace.components.diff_report_feedback.src.server.agent_diagram_artifacts",
            return_value=('@startuml\ncomponent "B" as b\n@enduml\n', "<svg><text>B</text></svg>"),
        ):
            request = urllib.request.Request(
                url,
                data=json.dumps({"source_format": "plantuml", "source": next_source}).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            rendered = json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))

        assert rendered["ok"] is True
        payload = json.loads(comments.read_text(encoding="utf-8"))
        assert payload["diagrams"]["flow"]["agent_diagram"]["nodes"] == [{"id": "b", "label": "B"}]
        assert "B" in (tmp_path / "tasks" / "sample" / "report" / "puml" / "flow.puml").read_text(encoding="utf-8")
    finally:
        handle.stop()


def test_diff_report_feedback_server_previews_agent_diagram_plantuml_without_writing(
    tmp_path: Path,
) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        comments = tmp_path / "tasks" / "sample" / "report" / "diff" / "comments.json"
        comments.parent.mkdir(parents=True)
        comments.write_text(
            json.dumps(
                {
                    "diagrams": {
                        "flow": {
                            "title": "Generated flow",
                            "source": "../puml/flow.puml",
                            "svg": "../puml/flow.svg",
                            "agent_diagram": {
                                "type": "component_graph",
                                "nodes": [{"id": "a", "label": "A"}],
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        url = (
            f"{handle.base_url}/api/v1/agent-diagram/preview"
            "?task=tasks/sample"
            "&comments=report/diff/comments.json"
            "&diagram=flow"
        )
        source = '@startuml\ncomponent "Preview" as preview\n@enduml\n'
        with mock.patch(
            "agent_tools.agent_workspace.components.diff_report_feedback.src.server.agent_diagram_artifacts",
            return_value=("@startuml\ncomponent \"Preview\" as preview\n@enduml\n", "<svg><text>Preview</text></svg>"),
        ):
            request = urllib.request.Request(
                url,
                data=json.dumps({"source_format": "plantuml", "source": source}).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            rendered = json.loads(urllib.request.urlopen(request, timeout=5).read().decode("utf-8"))

        assert rendered["ok"] is True
        assert rendered["svg"] == "<svg><text>Preview</text></svg>"
        payload = json.loads(comments.read_text(encoding="utf-8"))
        assert payload["diagrams"]["flow"]["agent_diagram"]["nodes"] == [{"id": "a", "label": "A"}]
        assert not (tmp_path / "tasks" / "sample" / "report" / "puml" / "flow.puml").exists()
    finally:
        handle.stop()


def test_diff_report_feedback_server_returns_diagnostic_svg_for_plantuml_preview_error(
    tmp_path: Path,
) -> None:
    handle = start_diff_report_feedback_server(tmp_path, port=0)
    try:
        comments = tmp_path / "tasks" / "sample" / "report" / "diff" / "comments.json"
        comments.parent.mkdir(parents=True)
        comments.write_text(
            json.dumps(
                {
                    "diagrams": {
                        "flow": {
                            "title": "Generated flow",
                            "agent_diagram": {
                                "type": "component_graph",
                                "nodes": [{"id": "a", "label": "A"}],
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        url = (
            f"{handle.base_url}/api/v1/agent-diagram/preview"
            "?task=tasks/sample"
            "&comments=report/diff/comments.json"
            "&diagram=flow"
        )
        source = '@startuml\nrectangle "Raw PlantUML" as raw\ncomponent "A" as a\n@enduml\n'
        with mock.patch(
            "agent_tools.agent_workspace.components.diff_report_feedback.src.server.render_plantuml_source_svg",
            return_value="<svg><text>PlantUML diagnostic</text></svg>",
        ):
            request = urllib.request.Request(
                url,
                data=json.dumps({"source_format": "plantuml", "source": source}).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            try:
                urllib.request.urlopen(request, timeout=5)
            except urllib.error.HTTPError as error:
                rendered = json.loads(error.read().decode("utf-8"))
                assert error.code == 400
            else:
                raise AssertionError("invalid PlantUML subset preview unexpectedly succeeded")

        assert "unsupported component_graph PlantUML line" in rendered["error"]
        assert rendered["svg"] == "<svg><text>PlantUML diagnostic</text></svg>"
        assert rendered["source"] == source
    finally:
        handle.stop()


def _json_get(url: str) -> dict[str, object]:
    return json.loads(urllib.request.urlopen(url, timeout=5).read().decode("utf-8"))
