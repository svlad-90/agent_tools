from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from .models import DiffReportError


_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_QUOTED_ALIAS_RE = re.compile(
    r'^(?P<kind>[A-Za-z_][A-Za-z0-9_]*)\s+"(?P<label>(?:\\.|[^"])*)"\s+as\s+(?P<id>[A-Za-z_][A-Za-z0-9_]*)(?:\s+(?P<color>#[A-Fa-f0-9]{6}))?$'
)
_PACKAGE_RE = re.compile(
    r'^package\s+"(?P<label>(?:\\.|[^"])*)"\s+as\s+(?P<id>[A-Za-z_][A-Za-z0-9_]*)\s+\{$'
)
_COMPONENT_EDGE_RE = re.compile(
    r"^(?P<from>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?P<arrow>[.-](?:\[#(?P<color>[A-Fa-f0-9]{6})\])?(?P<direction>down|left|right|up)?[.-]?>)\s+"
    r"(?P<to>[A-Za-z_][A-Za-z0-9_]*)(?:\s*:\s*(?P<label>.*))?$"
)
_CLASS_RELATION_RE = re.compile(
    r"^(?P<from>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?P<arrow>(?:\.|o|\*)?(?:-\[#[A-Fa-f0-9]{6}\]-|-|\.)+(?:\|?>)?)\s+"
    r"(?P<to>[A-Za-z_][A-Za-z0-9_]*)(?:\s*:\s*(?P<label>.*))?$"
)
_FOCUS_FILL = "#FFE8A3"
_FOCUS_LINE = "#D97706"


@dataclass(frozen=True)
class FocusSpec:
    nodes: frozenset[str] = frozenset()
    edges: frozenset[tuple[str, str, str]] = frozenset()

    def node(self, node_id: str) -> bool:
        return node_id in self.nodes

    def edge(self, source: str, target: str, label: str) -> bool:
        normalized_label = label.strip()
        return (
            (source, target, normalized_label) in self.edges
            or (source, target, "") in self.edges
        )


def agent_diagram_artifacts(raw: Any, *, diagram_key: str) -> tuple[str, str]:
    source = compile_agent_diagram(raw, diagram_key=diagram_key)
    return source, _render_plantuml_svg(source, diagram_key=diagram_key)


def agent_diagram_code_links(raw: Any, *, diagram_key: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, dict):
        raise DiffReportError(f"agent_diagram must be an object: {diagram_key}")
    diagram_type = str(raw.get("type", raw.get("profile", ""))).strip()
    if diagram_type == "component_graph":
        return _component_code_links(raw, diagram_key=diagram_key)
    if diagram_type == "sequence_flow":
        return _sequence_code_links(raw, diagram_key=diagram_key)
    if diagram_type == "class_model":
        return _class_code_links(raw, diagram_key=diagram_key)
    raise DiffReportError(
        f"agent_diagram.type must be component_graph, sequence_flow, or class_model: {diagram_key}"
    )


def merge_agent_diagram_variant(base: Any, variant: Any, *, diagram_key: str) -> dict[str, Any]:
    if not isinstance(base, dict):
        raise DiffReportError(f"base agent_diagram must be an object: {diagram_key}")
    if not isinstance(variant, dict):
        raise DiffReportError(f"agent_diagram variant must be an object: {diagram_key}")
    merged = dict(base)
    if "title" in variant:
        merged["title"] = variant["title"]
    if "focus" in variant:
        merged["focus"] = variant["focus"]
    elif "focus_ids" in variant:
        merged["focus_ids"] = variant["focus_ids"]
    for key in ("notes", "annotations"):
        if key in variant:
            base_notes = _dict_list(base.get(key, ()), f"agent_diagram.{key}: {diagram_key}")
            variant_notes = _dict_list(variant.get(key, ()), f"agent_diagram.{key}: {diagram_key}")
            merged[key] = [*base_notes, *variant_notes]
    return merged


def compile_agent_diagram(raw: Any, *, diagram_key: str) -> str:
    if not isinstance(raw, dict):
        raise DiffReportError(f"agent_diagram must be an object: {diagram_key}")
    diagram_type = str(raw.get("type", raw.get("profile", ""))).strip()
    if diagram_type == "component_graph":
        body = _component_graph(raw, diagram_key=diagram_key)
    elif diagram_type == "sequence_flow":
        body = _sequence_flow(raw, diagram_key=diagram_key)
    elif diagram_type == "class_model":
        body = _class_model(raw, diagram_key=diagram_key)
    else:
        raise DiffReportError(
            f"agent_diagram.type must be component_graph, sequence_flow, or class_model: {diagram_key}"
        )
    return "\n".join(["@startuml", *_style_lines(raw), *body, "@enduml", ""])


def parse_agent_diagram_source(source: str, *, diagram_key: str) -> dict[str, Any]:
    """Parse the PlantUML subset emitted by compile_agent_diagram back to JSON."""
    lines = _plantuml_body_lines(source, diagram_key=diagram_key)
    title = ""
    body: list[str] = []
    for line in lines:
        if line.startswith("skinparam "):
            continue
        if line.startswith("title "):
            title = _unescape_text(line.removeprefix("title ").strip().strip('"'))
            continue
        body.append(line)
    if any(line == "autonumber" for line in body):
        raise DiffReportError(f"PlantUML round-trip for sequence_flow is not implemented yet: {diagram_key}")
    if any(line == "hide empty members" for line in body):
        result = _parse_class_model(body, diagram_key=diagram_key)
    else:
        result = _parse_component_graph(body, diagram_key=diagram_key)
    if title:
        result["title"] = title
    compile_agent_diagram(result, diagram_key=diagram_key)
    return result


def _plantuml_body_lines(source: str, *, diagram_key: str) -> list[str]:
    raw_lines = [line.rstrip() for line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [line.strip() for line in raw_lines if line.strip()]
    if not lines or lines[0] != "@startuml" or lines[-1] != "@enduml":
        raise DiffReportError(f"PlantUML source must start with @startuml and end with @enduml: {diagram_key}")
    return lines[1:-1]


def _style_lines(raw: dict[str, Any]) -> list[str]:
    lines = [
        "skinparam backgroundColor white",
        "skinparam shadowing false",
        "skinparam roundcorner 8",
        "skinparam defaultFontName Arial",
        "skinparam ArrowColor #334155",
        "skinparam ArrowFontColor #111827",
        "skinparam componentBackgroundColor #EEF4FF",
        "skinparam componentBorderColor #64748B",
        "skinparam databaseBackgroundColor #ECFDF5",
        "skinparam classBackgroundColor #F8FAFC",
        "skinparam classBorderColor #64748B",
    ]
    title = str(raw.get("title", "")).strip()
    if title:
        lines.append(f"title {_quoted(title)}")
    return lines


def _parse_component_graph(lines: list[str], *, diagram_key: str) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "component_graph", "nodes": [], "edges": []}
    groups: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    focus: list[Any] = []
    current_group: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line == "top to bottom direction":
            result["direction"] = "down"
            index += 1
            continue
        if line == "left to right direction":
            result["direction"] = "right"
            index += 1
            continue
        package_match = _PACKAGE_RE.match(line)
        if package_match:
            current_group = package_match.group("id")
            groups.append({"id": current_group, "label": _unescape_text(package_match.group("label"))})
            index += 1
            continue
        if line == "}":
            current_group = None
            index += 1
            continue
        note = _parse_note_block(lines, index, diagram_key=diagram_key)
        if note is not None:
            notes.append(note[0])
            index = note[1]
            continue
        node_match = _QUOTED_ALIAS_RE.match(line)
        if node_match and node_match.group("kind") in {"component", "actor", "database", "folder"}:
            node = {
                "id": node_match.group("id"),
                "label": _unescape_text(node_match.group("label")),
            }
            kind = node_match.group("kind")
            if kind != "component":
                node["kind"] = "storage" if kind == "database" else kind
            if current_group:
                node["group"] = current_group
            if _is_focus_color(node_match.group("color")):
                focus.append(node["id"])
            result["nodes"].append(node)
            index += 1
            continue
        edge_match = _COMPONENT_EDGE_RE.match(line)
        if edge_match:
            label = _unescape_text((edge_match.group("label") or "").strip())
            edge = {
                "from": edge_match.group("from"),
                "to": edge_match.group("to"),
            }
            if label:
                edge["label"] = label
            direction = edge_match.group("direction")
            if direction:
                edge["direction"] = direction
            arrow = edge_match.group("arrow")
            if arrow.startswith("."):
                edge["dashed"] = True
            if _is_focus_line("#" + edge_match.group("color") if edge_match.group("color") else None):
                focus.append({"from": edge["from"], "to": edge["to"], "label": label})
            result["edges"].append(edge)
            index += 1
            continue
        raise DiffReportError(f"unsupported component_graph PlantUML line in {diagram_key}: {line}")
    if groups:
        result["groups"] = groups
    if notes:
        result["notes"] = notes
    if focus:
        result["focus"] = focus
    return result


def _parse_class_model(lines: list[str], *, diagram_key: str) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "class_model", "classes": [], "relationships": []}
    packages: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    focus: list[Any] = []
    current_package: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line == "hide empty members":
            index += 1
            continue
        package_match = _PACKAGE_RE.match(line)
        if package_match:
            current_package = package_match.group("id")
            packages.append({"id": current_package, "label": _unescape_text(package_match.group("label"))})
            index += 1
            continue
        if line == "}":
            current_package = None
            index += 1
            continue
        note = _parse_note_block(lines, index, diagram_key=diagram_key)
        if note is not None:
            notes.append(note[0])
            index = note[1]
            continue
        class_match = _QUOTED_ALIAS_RE.match(line.removesuffix(" {"))
        if class_match and line.endswith("{") and class_match.group("kind") in {"class", "interface", "enum"}:
            item: dict[str, Any] = {
                "id": class_match.group("id"),
                "label": _unescape_text(class_match.group("label")),
                "kind": class_match.group("kind"),
            }
            if current_package:
                item["package"] = current_package
            if _is_focus_color(class_match.group("color")):
                focus.append(item["id"])
            members: list[str] = []
            index += 1
            while index < len(lines) and lines[index] != "}":
                members.append(_unescape_text(lines[index].strip()))
                index += 1
            if index >= len(lines):
                raise DiffReportError(f"unterminated class block in PlantUML source: {diagram_key}")
            if members:
                item["fields"] = members
            result["classes"].append(item)
            index += 1
            continue
        relation_match = _CLASS_RELATION_RE.match(line)
        if relation_match:
            label = _unescape_text((relation_match.group("label") or "").strip())
            arrow = relation_match.group("arrow")
            relation = {
                "from": relation_match.group("from"),
                "to": relation_match.group("to"),
                "kind": _class_arrow_kind(arrow, diagram_key=diagram_key),
            }
            if label:
                relation["label"] = label
            if _FOCUS_LINE.lower() in arrow.lower():
                focus.append({"from": relation["from"], "to": relation["to"], "label": label})
            result["relationships"].append(relation)
            index += 1
            continue
        raise DiffReportError(f"unsupported class_model PlantUML line in {diagram_key}: {line}")
    if packages:
        result["packages"] = packages
    if notes:
        result["notes"] = notes
    if focus:
        result["focus"] = focus
    return result


def _parse_note_block(
    lines: list[str],
    index: int,
    *,
    diagram_key: str,
) -> tuple[dict[str, Any], int] | None:
    header = lines[index]
    match = re.match(r"^note\s+(?P<position>left|right|top|bottom)\s+of\s+(?P<of>[A-Za-z_][A-Za-z0-9_]*)$", header)
    if not match:
        return None
    text: list[str] = []
    index += 1
    while index < len(lines) and lines[index] != "end note":
      text.append(_unescape_text(lines[index]))
      index += 1
    if index >= len(lines):
        raise DiffReportError(f"unterminated note block in PlantUML source: {diagram_key}")
    return (
        {
            "of": match.group("of"),
            "position": match.group("position"),
            "text": "\n".join(text),
        },
        index + 1,
    )


def _class_arrow_kind(arrow: str, *, diagram_key: str) -> str:
    normalized = re.sub(r"\[#[A-Fa-f0-9]{6}\]", "", arrow)
    mapping = {
        "--": "association",
        "..>": "dependency",
        "--|>": "extends",
        "..|>": "implements",
        "*--": "composition",
        "o--": "aggregation",
    }
    try:
        return mapping[normalized]
    except KeyError as error:
        raise DiffReportError(f"unsupported class relationship arrow in PlantUML source: {arrow}: {diagram_key}") from error


def _is_focus_color(color: str | None) -> bool:
    return bool(color and color.lower() == _FOCUS_FILL.lower())


def _is_focus_line(color: str | None) -> bool:
    return bool(color and color.lower() == _FOCUS_LINE.lower())


def _component_graph(raw: dict[str, Any], *, diagram_key: str) -> list[str]:
    nodes = _dict_list(raw.get("nodes", ()), f"agent_diagram.nodes: {diagram_key}")
    edges = _dict_list(raw.get("edges", ()), f"agent_diagram.edges: {diagram_key}")
    groups = _dict_list(raw.get("groups", ()), f"agent_diagram.groups: {diagram_key}")
    notes = _dict_list(raw.get("notes", ()), f"agent_diagram.notes: {diagram_key}")
    focus = _focus_spec(raw, diagram_key=diagram_key)
    node_ids = {_required_id(node, "id", diagram_key) for node in nodes}
    group_ids = {_required_id(group, "id", diagram_key) for group in groups}
    if len(node_ids) != len(nodes):
        raise DiffReportError(f"agent_diagram node ids must be unique: {diagram_key}")
    if len(group_ids) != len(groups):
        raise DiffReportError(f"agent_diagram group ids must be unique: {diagram_key}")
    if node_ids & group_ids:
        raise DiffReportError(f"agent_diagram node and group ids must not overlap: {diagram_key}")

    children_by_group: dict[str, list[dict[str, Any]]] = {group_id: [] for group_id in group_ids}
    root_nodes: list[dict[str, Any]] = []
    for node in nodes:
        group = str(node.get("group", "")).strip()
        if group:
            if group not in group_ids:
                raise DiffReportError(f"unknown agent_diagram group referenced by node: {group}")
            children_by_group[group].append(node)
        else:
            root_nodes.append(node)

    graph_direction = _component_graph_direction(raw, diagram_key=diagram_key)
    lines: list[str] = [_component_direction_line(graph_direction)]
    for group in groups:
        group_id = _required_id(group, "id", diagram_key)
        label = str(group.get("label", group_id))
        lines.append(f'package "{_escape_text(label)}" as {group_id} {{')
        for node in children_by_group[group_id]:
            lines.append(f"  {_component_node_line(node, focus=focus, diagram_key=diagram_key)}")
        lines.append("}")
    for node in root_nodes:
        lines.append(_component_node_line(node, focus=focus, diagram_key=diagram_key))
    for edge in edges:
        lines.append(
            _component_edge_line(
                edge,
                node_ids | group_ids,
                focus=focus,
                default_direction=graph_direction,
                diagram_key=diagram_key,
            )
        )
    for note in notes:
        lines.extend(_note_lines(note, node_ids | group_ids, diagram_key=diagram_key))
    return lines


def _component_node_line(node: dict[str, Any], *, focus: "FocusSpec", diagram_key: str) -> str:
    node_id = _required_id(node, "id", diagram_key)
    label = str(node.get("label", node_id))
    kind = str(node.get("kind", node.get("type", "component"))).strip().lower()
    keyword = {
        "actor": "actor",
        "database": "database",
        "folder": "folder",
        "storage": "database",
    }.get(kind, "component")
    color = f" {_FOCUS_FILL}" if focus.node(node_id) or bool(node.get("focus")) else ""
    return f'{keyword} "{_escape_text(label)}" as {node_id}{color}'


def _component_edge_line(
    edge: dict[str, Any],
    known_ids: set[str],
    *,
    focus: "FocusSpec",
    default_direction: str,
    diagram_key: str,
) -> str:
    source = _required_id(edge, "from", diagram_key)
    target = _required_id(edge, "to", diagram_key)
    if source not in known_ids or target not in known_ids:
        raise DiffReportError(f"agent_diagram edge references unknown node: {diagram_key}")
    label = str(edge.get("label", "")).strip()
    arrow = _edge_arrow(
        str(edge.get("direction", default_direction)),
        dashed=bool(edge.get("dashed", False)),
        focus=focus.edge(source, target, label) or bool(edge.get("focus")),
    )
    suffix = f" : {_escape_text(label)}" if label else ""
    return f"{source} {arrow} {target}{suffix}"


def _sequence_flow(raw: dict[str, Any], *, diagram_key: str) -> list[str]:
    participants = _dict_list(
        raw.get("participants", ()), f"agent_diagram.participants: {diagram_key}"
    )
    steps = _dict_list(raw.get("steps", ()), f"agent_diagram.steps: {diagram_key}")
    focus = _focus_spec(raw, diagram_key=diagram_key)
    ids = {_required_id(participant, "id", diagram_key) for participant in participants}
    if len(ids) != len(participants):
        raise DiffReportError(f"agent_diagram participant ids must be unique: {diagram_key}")
    lines: list[str] = ["autonumber"]
    for participant in participants:
        participant_id = _required_id(participant, "id", diagram_key)
        label = str(participant.get("label", participant_id))
        kind = str(participant.get("kind", participant.get("type", "participant"))).strip().lower()
        keyword = {
            "actor": "actor",
            "boundary": "boundary",
            "control": "control",
            "database": "database",
            "entity": "entity",
        }.get(kind, "participant")
        color = f" {_FOCUS_FILL}" if focus.node(participant_id) or bool(participant.get("focus")) else ""
        lines.append(f'{keyword} "{_escape_text(label)}" as {participant_id}{color}')
    lines.extend(_sequence_steps(steps, ids, focus=focus, diagram_key=diagram_key, indent=""))
    for note in _dict_list(raw.get("notes", raw.get("annotations", ())), f"agent_diagram.notes: {diagram_key}"):
        lines.extend(_sequence_note_lines(note, ids, diagram_key=diagram_key, indent=""))
    return lines


def _sequence_steps(
    steps: list[dict[str, Any]],
    known_ids: set[str],
    *,
    focus: "FocusSpec",
    diagram_key: str,
    indent: str,
) -> list[str]:
    lines: list[str] = []
    for step in steps:
        if "from" in step and "to" in step:
            source = _required_id(step, "from", diagram_key)
            target = _required_id(step, "to", diagram_key)
            if source not in known_ids or target not in known_ids:
                raise DiffReportError(f"agent_diagram message references unknown participant: {diagram_key}")
            message = str(step.get("message", step.get("label", "")))
            arrow = _message_arrow(
                str(step.get("kind", step.get("type", "sync"))),
                focus=focus.edge(source, target, message) or bool(step.get("focus")),
            )
            lines.append(f"{indent}{source} {arrow} {target}: {_escape_text(message)}")
            if step.get("activate"):
                lines.append(f"{indent}activate {target}")
            if step.get("deactivate"):
                lines.append(f"{indent}deactivate {source}")
            continue
        if "note" in step:
            lines.extend(_sequence_note_lines(step, known_ids, diagram_key=diagram_key, indent=indent))
            continue
        for key in ("alt", "opt", "loop", "par", "group"):
            if key in step:
                lines.extend(_sequence_block(key, step[key], known_ids, focus=focus, diagram_key=diagram_key, indent=indent))
                break
        else:
            raise DiffReportError(f"unknown agent_diagram sequence step: {diagram_key}")
    return lines


def _sequence_block(
    kind: str,
    raw: Any,
    known_ids: set[str],
    *,
    focus: "FocusSpec",
    diagram_key: str,
    indent: str,
) -> list[str]:
    if kind in {"alt", "par"} and isinstance(raw, list):
        branches = _dict_list(raw, f"agent_diagram.alt: {diagram_key}")
        if not branches:
            raise DiffReportError(f"agent_diagram.{kind} must have at least one branch: {diagram_key}")
        lines: list[str] = []
        for index, branch in enumerate(branches):
            condition = str(branch.get("condition", branch.get("label", "")))
            prefix = kind if index == 0 else "else"
            lines.append(f"{indent}{prefix} {_escape_text(condition)}")
            lines.extend(
                _sequence_steps(
                    _dict_list(branch.get("steps", ()), f"agent_diagram.{kind}.steps: {diagram_key}"),
                    known_ids,
                    focus=focus,
                    diagram_key=diagram_key,
                    indent=indent + "  ",
                )
            )
        lines.append(f"{indent}end")
        return lines
    if not isinstance(raw, dict):
        raise DiffReportError(f"agent_diagram.{kind} must be an object: {diagram_key}")
    label = str(raw.get("condition", raw.get("label", raw.get("title", ""))))
    lines = [f"{indent}{kind} {_escape_text(label)}"]
    lines.extend(
        _sequence_steps(
            _dict_list(raw.get("steps", ()), f"agent_diagram.{kind}.steps: {diagram_key}"),
            known_ids,
            focus=focus,
            diagram_key=diagram_key,
            indent=indent + "  ",
        )
    )
    lines.append(f"{indent}end")
    return lines


def _sequence_note_lines(
    raw: dict[str, Any],
    known_ids: set[str],
    *,
    diagram_key: str,
    indent: str,
) -> list[str]:
    target = _required_id(raw, "of", diagram_key)
    if target not in known_ids:
        raise DiffReportError(f"agent_diagram note references unknown participant: {diagram_key}")
    position = str(raw.get("position", "right")).strip().lower()
    if position not in {"left", "right", "over"}:
        raise DiffReportError(f"agent_diagram note position must be left, right, or over: {diagram_key}")
    text = str(raw.get("text", raw.get("note", "")))
    if not text.strip():
        raise DiffReportError(f"agent_diagram note text must be non-empty: {diagram_key}")
    header = f"note {position} of {target}" if position != "over" else f"note over {target}"
    return [f"{indent}{header}", *[f"{indent}{_escape_text(line)}" for line in text.splitlines()], f"{indent}end note"]


def _class_model(raw: dict[str, Any], *, diagram_key: str) -> list[str]:
    classes = _dict_list(raw.get("classes", raw.get("types", ())), f"agent_diagram.classes: {diagram_key}")
    relationships = _dict_list(
        raw.get("relationships", raw.get("edges", ())), f"agent_diagram.relationships: {diagram_key}"
    )
    packages = _dict_list(raw.get("packages", ()), f"agent_diagram.packages: {diagram_key}")
    focus = _focus_spec(raw, diagram_key=diagram_key)
    type_ids = {_required_id(item, "id", diagram_key) for item in classes}
    package_ids = {_required_id(item, "id", diagram_key) for item in packages}
    if len(type_ids) != len(classes):
        raise DiffReportError(f"agent_diagram class ids must be unique: {diagram_key}")
    if len(package_ids) != len(packages):
        raise DiffReportError(f"agent_diagram package ids must be unique: {diagram_key}")
    children_by_package: dict[str, list[dict[str, Any]]] = {package_id: [] for package_id in package_ids}
    root_classes: list[dict[str, Any]] = []
    for item in classes:
        package = str(item.get("package", "")).strip()
        if package:
            if package not in package_ids:
                raise DiffReportError(f"unknown agent_diagram package referenced by class: {package}")
            children_by_package[package].append(item)
        else:
            root_classes.append(item)
    lines: list[str] = ["hide empty members"]
    for package in packages:
        package_id = _required_id(package, "id", diagram_key)
        label = str(package.get("label", package_id))
        lines.append(f'package "{_escape_text(label)}" as {package_id} {{')
        for item in children_by_package[package_id]:
            lines.extend(f"  {line}" if line else line for line in _class_lines(item, focus=focus, diagram_key=diagram_key))
        lines.append("}")
    for item in root_classes:
        lines.extend(_class_lines(item, focus=focus, diagram_key=diagram_key))
    for relation in relationships:
        lines.append(_class_relationship_line(relation, type_ids, focus=focus, diagram_key=diagram_key))
    for note in _dict_list(raw.get("notes", raw.get("annotations", ())), f"agent_diagram.notes: {diagram_key}"):
        lines.extend(_note_lines(note, type_ids | package_ids, diagram_key=diagram_key))
    return lines


def _class_lines(item: dict[str, Any], *, focus: "FocusSpec", diagram_key: str) -> list[str]:
    type_id = _required_id(item, "id", diagram_key)
    label = str(item.get("label", type_id))
    kind = str(item.get("kind", item.get("type", "class"))).strip().lower()
    keyword = {"interface": "interface", "enum": "enum"}.get(kind, "class")
    color = f" {_FOCUS_FILL}" if focus.node(type_id) or bool(item.get("focus")) else ""
    lines = [f'{keyword} "{_escape_text(label)}" as {type_id}{color} {{']
    for field in _string_list(item.get("fields", ())):
        lines.append(f"  {_escape_text(field)}")
    for method in _string_list(item.get("methods", ())):
        lines.append(f"  {_escape_text(method)}")
    lines.append("}")
    return lines


def _class_relationship_line(
    relation: dict[str, Any],
    known_ids: set[str],
    *,
    focus: "FocusSpec",
    diagram_key: str,
) -> str:
    source = _required_id(relation, "from", diagram_key)
    target = _required_id(relation, "to", diagram_key)
    if source not in known_ids or target not in known_ids:
        raise DiffReportError(f"agent_diagram relationship references unknown type: {diagram_key}")
    relation_type = str(relation.get("kind", relation.get("type", "association"))).strip().lower()
    arrow = {
        "aggregation": "o--",
        "association": "--",
        "composition": "*--",
        "dependency": "..>",
        "extends": "--|>",
        "implements": "..|>",
        "inheritance": "--|>",
    }.get(relation_type)
    if arrow is None:
        raise DiffReportError(f"unknown agent_diagram class relationship kind: {relation_type}")
    label = str(relation.get("label", "")).strip()
    suffix = f" : {_escape_text(label)}" if label else ""
    if focus.edge(source, target, label) or bool(relation.get("focus")):
        arrow = _focused_class_arrow(arrow)
    return f"{source} {arrow} {target}{suffix}"


def _note_lines(note: dict[str, Any], known_ids: set[str], *, diagram_key: str) -> list[str]:
    target = _required_id(note, "of", diagram_key)
    if target not in known_ids:
        raise DiffReportError(f"agent_diagram note references unknown node: {diagram_key}")
    text = str(note.get("text", note.get("note", "")))
    if not text.strip():
        raise DiffReportError(f"agent_diagram note text must be non-empty: {diagram_key}")
    position = str(note.get("position", "right")).strip().lower()
    if position not in {"left", "right", "top", "bottom"}:
        raise DiffReportError(f"agent_diagram note position must be left, right, top, or bottom: {diagram_key}")
    return [f"note {position} of {target}", *[_escape_text(line) for line in text.splitlines()], "end note"]


def _component_graph_direction(raw: dict[str, Any], *, diagram_key: str) -> str:
    direction = str(raw.get("direction", raw.get("layout", "down"))).strip().lower()
    aliases = {
        "bottom": "down",
        "horizontal": "right",
        "left-to-right": "right",
        "lr": "right",
        "rightward": "right",
        "tb": "down",
        "top-to-bottom": "down",
        "vertical": "down",
    }
    direction = aliases.get(direction, direction)
    if direction not in {"down", "left", "right", "up"}:
        raise DiffReportError(f"agent_diagram.direction must be down, right, left, or up: {diagram_key}")
    return direction


def _component_direction_line(direction: str) -> str:
    if direction in {"left", "right"}:
        return "left to right direction"
    return "top to bottom direction"


def _render_plantuml_svg(source: str, *, diagram_key: str) -> str:
    return render_plantuml_source_svg(source, diagram_key=diagram_key, allow_error_svg=False)


def render_plantuml_source_svg(source: str, *, diagram_key: str, allow_error_svg: bool = False) -> str:
    executable = shutil.which("plantuml")
    if executable is None:
        raise DiffReportError(
            f"agent_diagram requires the local plantuml executable when no pre-rendered svg is supplied: {diagram_key}"
        )
    try:
        result = subprocess.run(
            [executable, "-tsvg", "-pipe"],
            input=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise DiffReportError(f"PlantUML render timed out for agent_diagram: {diagram_key}") from error
    if result.returncode != 0:
        if allow_error_svg and "<svg" in result.stdout:
            return result.stdout
        message = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
        raise DiffReportError(f"PlantUML render failed for agent_diagram {diagram_key}: {message}")
    if "<svg" not in result.stdout:
        raise DiffReportError(f"PlantUML did not produce SVG for agent_diagram: {diagram_key}")
    return result.stdout


def _dict_list(raw: Any, field: str) -> list[dict[str, Any]]:
    if raw in (None, ()):
        return []
    if not isinstance(raw, list):
        raise DiffReportError(f"{field} must be a list")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise DiffReportError(f"{field}[{index}] must be an object")
        result.append(item)
    return result


def _string_list(raw: Any) -> list[str]:
    if raw in (None, ()):
        return []
    if not isinstance(raw, list):
        raise DiffReportError("agent_diagram class members must be lists")
    return [str(item) for item in raw]


def _required_id(raw: dict[str, Any], field: str, diagram_key: str) -> str:
    value = str(raw.get(field, "")).strip()
    if not _ID_RE.match(value):
        raise DiffReportError(f"agent_diagram.{field} must be a PlantUML-safe identifier: {diagram_key}")
    return value


def _edge_arrow(direction: str, *, dashed: bool, focus: bool = False) -> str:
    color = f"[{_FOCUS_LINE}]" if focus else ""
    if dashed:
        return f".{color}.>"
    normalized = direction.strip().lower()
    if normalized in {"down", "left", "right", "up"}:
        return f"-{color}{normalized}->"
    return f"-{color}->"


def _message_arrow(kind: str, *, focus: bool = False) -> str:
    arrow = {
        "async": "->>",
        "return": "-->",
        "sync": "->",
    }.get(kind.strip().lower(), "->")
    if not focus:
        return arrow
    if arrow.startswith("--"):
        return f"-[{_FOCUS_LINE}]->"
    return f"-[{_FOCUS_LINE}]>"


def _focused_class_arrow(arrow: str) -> str:
    if arrow == "..>":
        return f".[{_FOCUS_LINE}].>"
    if arrow == "..|>":
        return f".[{_FOCUS_LINE}].|>"
    if arrow == "--|>":
        return f"-[{_FOCUS_LINE}]-|>"
    if arrow == "*--":
        return f"*-[{_FOCUS_LINE}]-"
    if arrow == "o--":
        return f"o-[{_FOCUS_LINE}]-"
    return f"-[{_FOCUS_LINE}]-"


def _focus_spec(raw: dict[str, Any], *, diagram_key: str) -> FocusSpec:
    nodes: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    raw_focus = raw.get("focus", raw.get("focus_ids", ()))
    if raw_focus in (None, "", ()):
        return FocusSpec()
    if isinstance(raw_focus, (str, int)):
        raw_items: list[Any] = [raw_focus]
    elif isinstance(raw_focus, list):
        raw_items = raw_focus
    else:
        raise DiffReportError(f"agent_diagram.focus must be a string, object list, or string list: {diagram_key}")
    for index, item in enumerate(raw_items):
        if isinstance(item, (str, int)):
            value = str(item).strip()
            if not _ID_RE.match(value):
                raise DiffReportError(f"agent_diagram.focus[{index}] must be a PlantUML-safe identifier: {diagram_key}")
            nodes.add(value)
            continue
        if not isinstance(item, dict):
            raise DiffReportError(f"agent_diagram.focus[{index}] must be a string or object: {diagram_key}")
        if "target" in item:
            value = str(item["target"]).strip()
            if not _ID_RE.match(value):
                raise DiffReportError(f"agent_diagram.focus[{index}].target must be a PlantUML-safe identifier: {diagram_key}")
            nodes.add(value)
            continue
        source = _required_id(item, "from", diagram_key)
        target = _required_id(item, "to", diagram_key)
        label = str(item.get("label", item.get("message", ""))).strip()
        edges.add((source, target, label))
    return FocusSpec(frozenset(nodes), frozenset(edges))


def _component_code_links(raw: dict[str, Any], *, diagram_key: str) -> tuple[dict[str, Any], ...]:
    links: list[dict[str, Any]] = []
    for node in _dict_list(raw.get("nodes", ()), f"agent_diagram.nodes: {diagram_key}"):
        target = str(node.get("label", node.get("id", ""))).strip()
        links.extend(_code_links_for_target(node, target=target, diagram_key=diagram_key))
    for edge in _dict_list(raw.get("edges", ()), f"agent_diagram.edges: {diagram_key}"):
        target = str(edge.get("label", "")).strip()
        links.extend(_code_links_for_target(edge, target=target, diagram_key=diagram_key))
    return tuple(links)


def _sequence_code_links(raw: dict[str, Any], *, diagram_key: str) -> tuple[dict[str, Any], ...]:
    links: list[dict[str, Any]] = []
    for participant in _dict_list(raw.get("participants", ()), f"agent_diagram.participants: {diagram_key}"):
        target = str(participant.get("label", participant.get("id", ""))).strip()
        links.extend(_code_links_for_target(participant, target=target, diagram_key=diagram_key))
    links.extend(
        _sequence_step_code_links(
            _dict_list(raw.get("steps", ()), f"agent_diagram.steps: {diagram_key}"),
            diagram_key=diagram_key,
        )
    )
    return tuple(links)


def _sequence_step_code_links(steps: list[dict[str, Any]], *, diagram_key: str) -> tuple[dict[str, Any], ...]:
    links: list[dict[str, Any]] = []
    for step in steps:
        if "from" in step and "to" in step:
            target = str(step.get("message", step.get("label", ""))).strip()
            links.extend(_code_links_for_target(step, target=target, diagram_key=diagram_key))
            continue
        for key in ("alt", "par"):
            if key in step and isinstance(step[key], list):
                for branch in _dict_list(step[key], f"agent_diagram.{key}: {diagram_key}"):
                    links.extend(
                        _sequence_step_code_links(
                            _dict_list(branch.get("steps", ()), f"agent_diagram.{key}.steps: {diagram_key}"),
                            diagram_key=diagram_key,
                        )
                    )
                break
        else:
            for key in ("opt", "loop", "group"):
                if key in step and isinstance(step[key], dict):
                    links.extend(
                        _sequence_step_code_links(
                            _dict_list(step[key].get("steps", ()), f"agent_diagram.{key}.steps: {diagram_key}"),
                            diagram_key=diagram_key,
                        )
                    )
                    break
    return tuple(links)


def _class_code_links(raw: dict[str, Any], *, diagram_key: str) -> tuple[dict[str, Any], ...]:
    links: list[dict[str, Any]] = []
    for item in _dict_list(raw.get("classes", raw.get("types", ())), f"agent_diagram.classes: {diagram_key}"):
        target = str(item.get("label", item.get("id", ""))).strip()
        links.extend(_code_links_for_target(item, target=target, diagram_key=diagram_key))
    for relation in _dict_list(
        raw.get("relationships", raw.get("edges", ())), f"agent_diagram.relationships: {diagram_key}"
    ):
        target = str(relation.get("label", "")).strip()
        links.extend(_code_links_for_target(relation, target=target, diagram_key=diagram_key))
    return tuple(links)


def _code_links_for_target(raw: dict[str, Any], *, target: str, diagram_key: str) -> tuple[dict[str, Any], ...]:
    raw_code = raw.get("code", raw.get("code_links", ()))
    if raw_code in (None, "", (), []):
        return ()
    if not target:
        raise DiffReportError(f"agent_diagram code link target text is empty: {diagram_key}")
    raw_links: list[Any]
    if isinstance(raw_code, list):
        raw_links = raw_code
    else:
        raw_links = [raw_code]
    links: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_links):
        if isinstance(entry, str):
            entry = {"file": entry, "line": 1}
        if not isinstance(entry, dict):
            raise DiffReportError(f"agent_diagram code link {index} must be an object: {diagram_key}")
        links.append(_code_link(entry, target=target, diagram_key=diagram_key))
    return tuple(links)


def _code_link(raw: dict[str, Any], *, target: str, diagram_key: str) -> dict[str, Any]:
    file_path = str(raw.get("file", raw.get("path", ""))).strip()
    line = raw.get("line")
    if not file_path:
        raise DiffReportError(f"agent_diagram code link is missing file: {diagram_key}")
    if not isinstance(line, int):
        raise DiffReportError(f"agent_diagram code link line must be an integer: {diagram_key}")
    link: dict[str, Any] = {
        "target": target,
        "file": file_path,
        "line": line,
        "title": str(raw.get("title", target)),
    }
    if "range" in raw:
        link["range"] = raw["range"]
    if "target_info" in raw:
        link["target_info"] = raw["target_info"]
    return link


def _quoted(text: str) -> str:
    return f'"{_escape_text(text)}"'


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _unescape_text(text: str) -> str:
    result: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        result.append(char)
    if escaped:
        result.append("\\")
    return "".join(result)
