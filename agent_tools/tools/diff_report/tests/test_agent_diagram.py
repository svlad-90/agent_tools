from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_tools.tools.diff_report.agent_diagram import compile_agent_diagram
from agent_tools.tools.diff_report.agent_diagram import parse_agent_diagram_source
from agent_tools.tools.diff_report.comments import load_comments
from agent_tools.tools.diff_report.models import DiffReportError


class AgentDiagramTests(unittest.TestCase):
    def test_component_graph_compiles_to_plantuml(self) -> None:
        source = compile_agent_diagram(
            {
                "type": "component_graph",
                "title": "Report diagram pipeline",
                "groups": [{"id": "report", "label": "Diff report"}],
                "nodes": [
                    {"id": "comments", "label": "comments JSON", "group": "report"},
                    {"id": "renderer", "label": "HTML renderer", "kind": "service"},
                    {"id": "browser", "label": "Reviewer", "kind": "actor"},
                ],
                "edges": [
                    {"from": "comments", "to": "renderer", "label": "declares", "focus": True},
                    {"from": "renderer", "to": "browser", "label": "renders"},
                ],
                "focus": ["renderer"],
                "notes": [{"of": "renderer", "text": "Generated from agent_diagram JSON"}],
            },
            diagram_key="pipeline",
        )

        self.assertIn("@startuml", source)
        self.assertIn('title "Report diagram pipeline"', source)
        self.assertIn('package "Diff report" as report', source)
        self.assertIn('component "comments JSON" as comments', source)
        self.assertIn('component "HTML renderer" as renderer #FFE8A3', source)
        self.assertIn('actor "Reviewer" as browser', source)
        self.assertIn("top to bottom direction", source)
        self.assertIn("comments -[#D97706]down-> renderer : declares", source)
        self.assertIn("note right of renderer", source)

    def test_component_graph_can_use_horizontal_layout(self) -> None:
        source = compile_agent_diagram(
            {
                "type": "component_graph",
                "direction": "right",
                "nodes": [{"id": "input"}, {"id": "output"}],
                "edges": [{"from": "input", "to": "output"}],
            },
            diagram_key="horizontal",
        )

        self.assertIn("left to right direction", source)
        self.assertIn("input -right-> output", source)

    def test_component_graph_parses_generated_plantuml_subset(self) -> None:
        source = compile_agent_diagram(
            {
                "type": "component_graph",
                "title": "Editable",
                "groups": [{"id": "grp", "label": "Group"}],
                "nodes": [
                    {"id": "input", "label": "Input", "group": "grp"},
                    {"id": "output", "label": "Output"},
                ],
                "edges": [{"from": "input", "to": "output", "label": "renders", "focus": True}],
                "focus": ["output"],
                "notes": [{"of": "output", "position": "right", "text": "Check this"}],
            },
            diagram_key="round-trip",
        )

        parsed = parse_agent_diagram_source(source, diagram_key="round-trip")

        self.assertEqual("component_graph", parsed["type"])
        self.assertEqual("Editable", parsed["title"])
        self.assertEqual([{"id": "grp", "label": "Group"}], parsed["groups"])
        self.assertIn({"id": "input", "label": "Input", "group": "grp"}, parsed["nodes"])
        self.assertIn({"id": "output", "label": "Output"}, parsed["nodes"])
        self.assertEqual([{"from": "input", "to": "output", "label": "renders", "direction": "down"}], parsed["edges"])
        self.assertIn("output", parsed["focus"])
        self.assertIn({"from": "input", "to": "output", "label": "renders"}, parsed["focus"])
        self.assertEqual([{"of": "output", "position": "right", "text": "Check this"}], parsed["notes"])

    def test_sequence_flow_keeps_combined_fragments(self) -> None:
        source = compile_agent_diagram(
            {
                "type": "sequence_flow",
                "participants": [
                    {"id": "ui", "label": "GTK UI", "kind": "boundary"},
                    {"id": "svc", "label": "Workspace service", "kind": "control"},
                    {"id": "ctx", "label": "Task context", "kind": "database"},
                ],
                "steps": [
                    {"from": "ui", "to": "svc", "message": "create_task()", "activate": True},
                    {
                        "alt": [
                            {
                                "condition": "valid request",
                                "steps": [{"from": "svc", "to": "ctx", "message": "init slots"}],
                            },
                            {
                                "condition": "validation failed",
                                "steps": [{"from": "svc", "to": "ui", "message": "show error"}],
                            },
                        ]
                    },
                    {
                        "loop": {
                            "condition": "until task is ready",
                            "steps": [{"from": "svc", "to": "ctx", "message": "poll state"}],
                        }
                    },
                    {
                        "par": [
                            {
                                "condition": "persist",
                                "steps": [{"from": "svc", "to": "ctx", "message": "write state"}],
                            },
                            {
                                "condition": "notify",
                                "steps": [{"from": "svc", "to": "ui", "message": "refresh"}],
                            },
                        ]
                    },
                ],
                "focus": ["svc", {"from": "svc", "to": "ctx", "message": "write state"}],
            },
            diagram_key="task-create",
        )

        self.assertIn('boundary "GTK UI" as ui', source)
        self.assertIn('control "Workspace service" as svc #FFE8A3', source)
        self.assertIn("ui -> svc: create_task()", source)
        self.assertIn("alt valid request", source)
        self.assertIn("else validation failed", source)
        self.assertIn("loop until task is ready", source)
        self.assertIn("par persist", source)
        self.assertIn("svc -[#D97706]> ctx: write state", source)
        self.assertIn("else notify", source)

    def test_class_model_compiles_common_relationships(self) -> None:
        source = compile_agent_diagram(
            {
                "type": "class_model",
                "packages": [{"id": "model", "label": "Report model"}],
                "classes": [
                    {
                        "id": "Diagram",
                        "package": "model",
                        "fields": ["diagram_id: str", "svg: str"],
                        "methods": ["render(): str"],
                    },
                    {"id": "PlantUmlDiagram", "label": "PlantUML diagram"},
                    {"id": "Renderable", "kind": "interface"},
                ],
                "relationships": [
                    {"from": "PlantUmlDiagram", "to": "Diagram", "kind": "extends"},
                    {"from": "PlantUmlDiagram", "to": "Renderable", "kind": "implements", "focus": True},
                ],
                "focus": [{"target": "Diagram"}],
            },
            diagram_key="classes",
        )

        self.assertIn('package "Report model" as model', source)
        self.assertIn('class "Diagram" as Diagram #FFE8A3', source)
        self.assertIn("  diagram_id: str", source)
        self.assertIn('interface "Renderable" as Renderable', source)
        self.assertIn("PlantUmlDiagram --|> Diagram", source)
        self.assertIn("PlantUmlDiagram .[#D97706].|> Renderable", source)

    def test_unknown_reference_fails_before_render(self) -> None:
        with self.assertRaisesRegex(DiffReportError, "unknown node"):
            compile_agent_diagram(
                {
                    "type": "component_graph",
                    "nodes": [{"id": "a"}],
                    "edges": [{"from": "a", "to": "missing"}],
                },
                diagram_key="broken",
            )

    def test_comments_payload_writes_agent_diagram_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            comments_path = root / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "flow"}],
                        "diagrams": {
                            "flow": {
                                "title": "Generated flow",
                                "source": "flow.puml",
                                "svg": "flow.svg",
                                "agent_diagram": {
                                    "type": "component_graph",
                                    "nodes": [{"id": "input", "label": "Input"}],
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.agent_diagram._render_plantuml_svg",
                return_value="<svg><text>Input</text></svg>",
            ):
                comments = load_comments(comments_path)

            self.assertEqual("plantuml", comments.diagrams["flow"].renderer)
            self.assertIn("Input", comments.diagrams["flow"].svg)
            self.assertIn('component "Input" as input', (root / "flow.puml").read_text(encoding="utf-8"))
            self.assertEqual("<svg><text>Input</text></svg>", (root / "flow.svg").read_text(encoding="utf-8"))
            self.assertIsNone(comments.diagrams["flow"].source_task)

    def test_plain_plantuml_artifacts_are_render_only_from_task_report_puml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_diff = root / "tasks" / "demo" / "report" / "diff"
            report_puml = root / "tasks" / "demo" / "report" / "puml"
            report_diff.mkdir(parents=True)
            report_puml.mkdir(parents=True)
            (report_puml / "flow.puml").write_text("@startuml\n[A]\n@enduml\n", encoding="utf-8")
            (report_puml / "flow.svg").write_text("<svg><text>A</text></svg>", encoding="utf-8")
            comments_path = report_diff / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "flow"}],
                        "diagrams": {
                            "flow": {
                                "title": "Plain PlantUML",
                                "renderer": "plantuml",
                                "source": "../puml/flow.puml",
                                "svg": "../puml/flow.svg",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            comments = load_comments(comments_path)

            diagram = comments.diagrams["flow"]
            self.assertIsNone(diagram.source_task)
            self.assertIsNone(diagram.source_path)
            self.assertIsNone(diagram.svg_task)
            self.assertIsNone(diagram.svg_path)

    def test_task_local_agent_diagram_exposes_json_edit_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_diff = root / "tasks" / "demo" / "report" / "diff"
            report_puml = root / "tasks" / "demo" / "report" / "puml"
            report_diff.mkdir(parents=True)
            report_puml.mkdir(parents=True)
            comments_path = report_diff / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "flow"}],
                        "diagrams": {
                            "flow": {
                                "title": "Generated flow",
                                "source": "../puml/flow.puml",
                                "svg": "../puml/flow.svg",
                                "agent_diagram": {
                                    "type": "component_graph",
                                    "nodes": [{"id": "input", "label": "Input"}],
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.agent_diagram._render_plantuml_svg",
                return_value="<svg><text>Input</text></svg>",
            ):
                comments = load_comments(comments_path)

            diagram = comments.diagrams["flow"]
            self.assertEqual("tasks/demo", diagram.comments_task)
            self.assertEqual("report/diff/comments.json", diagram.comments_path)
            self.assertEqual("flow", diagram.comments_diagram)

    def test_agent_diagram_code_links_are_derived_from_structured_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            comments_path = root / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "summary_blocks": [{"type": "diagram", "diagram": "flow"}],
                        "diagrams": {
                            "flow": {
                                "title": "Generated flow",
                                "agent_diagram": {
                                    "type": "component_graph",
                                    "nodes": [
                                        {
                                            "id": "renderer",
                                            "label": "Renderer",
                                            "code": {
                                                "file": "agent_tools/tools/diff_report/agent_diagram.py",
                                                "line": 33,
                                                "title": "Open renderer",
                                            },
                                        }
                                    ],
                                    "edges": [
                                        {
                                            "from": "renderer",
                                            "to": "renderer",
                                            "label": "renders",
                                            "code": {
                                                "file": "agent_tools/tools/diff_report/comments.py",
                                                "line": 344,
                                            },
                                        }
                                    ],
                                },
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.agent_diagram._render_plantuml_svg",
                return_value="<svg><text>Renderer</text><text>renders</text></svg>",
            ):
                comments = load_comments(comments_path)

            self.assertEqual(
                (
                    {
                        "target": "Renderer",
                        "file": "agent_tools/tools/diff_report/agent_diagram.py",
                        "line": 33,
                        "title": "Open renderer",
                    },
                    {
                        "target": "renders",
                        "file": "agent_tools/tools/diff_report/comments.py",
                        "line": 344,
                        "title": "renders",
                    },
                ),
                comments.diagrams["flow"].code_links,
            )

    def test_agent_diagram_variant_renders_comment_specific_focus_and_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            comments_path = root / "comments.json"
            comments_path.write_text(
                json.dumps(
                    {
                        "story": [
                            {
                                "title": "Open focused variant",
                                "body": "Per-comment diagram variant.",
                                "diagram": "flow-comment-1",
                            }
                        ],
                        "diagrams": {
                            "flow": {
                                "title": "Generated flow",
                                "agent_diagram": {
                                    "type": "component_graph",
                                    "nodes": [
                                        {"id": "input", "label": "Input"},
                                        {"id": "output", "label": "Output"},
                                    ],
                                    "edges": [{"from": "input", "to": "output", "label": "renders"}],
                                },
                            },
                            "flow-comment-1": {
                                "variant_of": "flow",
                                "title": "Generated flow - comment 1",
                                "source": "flow-comment-1.puml",
                                "svg": "flow-comment-1.svg",
                                "focus": ["output", {"from": "input", "to": "output", "label": "renders"}],
                                "notes": [
                                    {
                                        "of": "output",
                                        "position": "right",
                                        "text": "Comment-specific annotation",
                                    }
                                ],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "agent_tools.tools.diff_report.agent_diagram._render_plantuml_svg",
                return_value="<svg><text>Output</text><text>Comment-specific annotation</text></svg>",
            ):
                comments = load_comments(comments_path)

            variant_source = (root / "flow-comment-1.puml").read_text(encoding="utf-8")
            self.assertIn('component "Output" as output #FFE8A3', variant_source)
            self.assertIn("input -[#D97706]down-> output : renders", variant_source)
            self.assertIn("note right of output", variant_source)
            self.assertIn("Comment-specific annotation", variant_source)
            self.assertEqual("flow-comment-1", comments.story[0].diagram)


if __name__ == "__main__":
    unittest.main()
