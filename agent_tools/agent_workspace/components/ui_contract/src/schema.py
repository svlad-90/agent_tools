from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UiNode:
    node_id: str
    role: str
    children: tuple[str, ...] = ()
    label_key: str | None = None
    widget: str | None = None
    layout: str | None = None
    orientation: str | None = None
    hexpand: bool | None = None
    vexpand: bool | None = None
    min_value: int | None = None
    max_value: int | None = None
    step: int | None = None
    width: int | None = None
    height: int | None = None
    visible: bool | None = True

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.node_id,
            "role": self.role,
            "children": list(self.children),
        }
        for key, value in (
            ("label_key", self.label_key),
            ("widget", self.widget),
            ("layout", self.layout),
            ("orientation", self.orientation),
            ("hexpand", self.hexpand),
            ("vexpand", self.vexpand),
            ("min_value", self.min_value),
            ("max_value", self.max_value),
            ("step", self.step),
            ("width", self.width),
            ("height", self.height),
            ("visible", self.visible),
        ):
            if value is not None:
                data[key] = value
        return data


@dataclass(frozen=True)
class UiTree:
    frontend: str
    view: str
    root_id: str
    nodes: tuple[UiNode, ...]
    schema: str = "agent-workspace-ui-tree-v1"

    def node_map(self) -> dict[str, UiNode]:
        return {node.node_id: node for node in self.nodes}

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "frontend": self.frontend,
            "view": self.view,
            "root_id": self.root_id,
            "nodes": [node.to_json() for node in self.nodes],
        }


@dataclass(frozen=True)
class UiContractIssue:
    node_id: str
    field: str
    expected: object
    actual: object

    def to_json(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "field": self.field,
            "expected": self.expected,
            "actual": self.actual,
        }


STRICT_NODE_FIELDS = (
    "role",
    "children",
    "label_key",
    "widget",
    "layout",
    "orientation",
    "hexpand",
    "vexpand",
    "min_value",
    "max_value",
    "step",
    "visible",
)


def compare_ui_trees(expected: UiTree, actual: UiTree) -> list[UiContractIssue]:
    issues: list[UiContractIssue] = []
    if expected.schema != actual.schema:
        issues.append(UiContractIssue(expected.root_id, "schema", expected.schema, actual.schema))
    if expected.view != actual.view:
        issues.append(UiContractIssue(expected.root_id, "view", expected.view, actual.view))
    if expected.root_id != actual.root_id:
        issues.append(UiContractIssue(expected.root_id, "root_id", expected.root_id, actual.root_id))

    expected_nodes = expected.node_map()
    actual_nodes = actual.node_map()
    for node_id in sorted(expected_nodes.keys() - actual_nodes.keys()):
        issues.append(UiContractIssue(node_id, "node", "present", "missing"))
    for node_id in sorted(actual_nodes.keys() - expected_nodes.keys()):
        issues.append(UiContractIssue(node_id, "node", "absent", "present"))
    for node_id in sorted(expected_nodes.keys() & actual_nodes.keys()):
        expected_node = expected_nodes[node_id]
        actual_node = actual_nodes[node_id]
        for field in STRICT_NODE_FIELDS:
            expected_value = getattr(expected_node, field)
            actual_value = getattr(actual_node, field)
            if expected_value != actual_value:
                issues.append(UiContractIssue(node_id, field, expected_value, actual_value))
    return issues
