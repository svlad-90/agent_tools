from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
from typing import Any

from .models import DiffReportError


@dataclass(frozen=True)
class DrawioNode:
    node_id: str
    label: str
    rank: int
    lane: int | None = None
    width: int = 160
    height: int = 64


@dataclass(frozen=True)
class DrawioEdge:
    source: str
    target: str
    label: str = ""
    render: bool = True
    show_label: bool = True


@dataclass(frozen=True)
class DrawioLayoutNode:
    node: DrawioNode
    x: int
    y: int


@dataclass(frozen=True)
class DrawioLayout:
    nodes: tuple[DrawioLayoutNode, ...]
    edges: tuple[DrawioEdge, ...]
    width: int
    height: int
    edge_points: tuple[tuple[tuple[float, float], ...], ...] = ()


def drawio_graph_svg(raw: Any, *, diagram_key: str) -> str:
    _, svg = drawio_graph_artifacts(raw, diagram_key=diagram_key)
    return svg


def drawio_graph_artifacts(raw: Any, *, diagram_key: str) -> tuple[str, str]:
    layout = layout_drawio_graph(raw, diagram_key=diagram_key)
    xml = drawio_layout_xml(layout)
    source_xml = _layout_drawio_xml(xml, raw) or xml
    exported_svg = _export_drawio_svg(source_xml)
    if exported_svg is not None:
        return source_xml, exported_svg
    return source_xml, drawio_layout_svg(layout)


def drawio_graph_xml(raw: Any, *, diagram_key: str) -> str:
    return drawio_layout_xml(layout_drawio_graph(raw, diagram_key=diagram_key))


def _layout_drawio_xml(xml: str, raw: Any) -> str | None:
    executable = _drawio_export_executable()
    if executable is None:
        return None
    with tempfile.TemporaryDirectory(prefix="diff-report-drawio-layout-") as temp_dir:
        source = Path(temp_dir) / "diagram.drawio"
        output = Path(temp_dir) / "diagram.layout.drawio"
        source.write_text(xml, encoding="utf-8")
        command = [
            executable,
            *_drawio_electron_flags(),
            "--layout",
            _drawio_layout_spec(raw),
            "--export",
            "--format",
            "xml",
            "--output",
            str(output),
            str(source),
        ]
        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        if not output.is_file():
            return None
        laid_out_xml = output.read_text(encoding="utf-8")
        if "<mxfile" not in laid_out_xml or "<mxGraphModel" not in laid_out_xml:
            return None
        return laid_out_xml


def _export_drawio_svg(xml: str) -> str | None:
    executable = _drawio_export_executable()
    if executable is None:
        return None
    with tempfile.TemporaryDirectory(prefix="diff-report-drawio-") as temp_dir:
        source = Path(temp_dir) / "diagram.drawio"
        output = Path(temp_dir) / "diagram.svg"
        source.write_text(xml, encoding="utf-8")
        command = [
            executable,
            *_drawio_electron_flags(),
            "--export",
            "--format",
            "svg",
            "--theme",
            "light",
            "--output",
            str(output),
            str(source),
        ]
        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        if not output.is_file():
            return None
        svg = output.read_text(encoding="utf-8")
        if "<svg" not in svg:
            return None
        return svg


def _drawio_electron_flags() -> tuple[str, ...]:
    return ("--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage")


def _drawio_layout_spec(raw: Any) -> str:
    if isinstance(raw, dict) and "drawio_layout" in raw:
        value = raw["drawio_layout"]
        if isinstance(value, str):
            return value
        return json.dumps(value, separators=(",", ":"))
    return json.dumps(
        [
            {
                "layout": "elkLayered",
                "config": {
                    "elk.direction": "DOWN",
                    "elk.spacing.nodeNode": "80",
                    "elk.layered.spacing.nodeNodeBetweenLayers": "100",
                    "elk.edgeLabels.inline": "false",
                },
            }
        ],
        separators=(",", ":"),
    )


def _drawio_export_executable() -> str | None:
    for executable in ("drawio", "diagrams.net", "diagramsnet"):
        path = shutil.which(executable)
        if path is not None:
            return path
    return None


def check_drawio_cli() -> tuple[bool, str]:
    executable = _drawio_export_executable()
    if executable is None:
        return (
            False,
            "drawio CLI not found; drawio_graph will use the built-in fallback SVG renderer.",
        )
    try:
        result = subprocess.run(
            [executable, *_drawio_electron_flags(), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        return (
            False,
            f"drawio CLI found at {executable}, but it did not start cleanly: {error}",
        )
    version = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "version unknown"
    return (
        True,
        f"drawio CLI ok: {executable} ({version}); drawio_graph will use diagrams.net layout/export.",
    )


def _layout_engine(raw: Any) -> str:
    if isinstance(raw, dict):
        return str(raw.get("layout_engine", raw.get("layout", "layered"))).strip().lower()
    return "layered"


def _graphviz_layout(raw: Any, *, diagram_key: str) -> DrawioLayout | None:
    nodes, edges = _parse_graph(raw, diagram_key=diagram_key)
    dot = _graphviz_dot(nodes, edges)
    try:
        result = subprocess.run(
            ["dot", "-Tplain"],
            input=dot,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return _layout_from_graphviz_plain(result.stdout, nodes=nodes, edges=edges)


def _graphviz_dot(nodes: tuple[DrawioNode, ...], edges: tuple[DrawioEdge, ...]) -> str:
    parts = [
        "digraph drawio_graph {",
        "  graph [rankdir=TB, splines=ortho, nodesep=0.45, ranksep=0.75, bgcolor=\"transparent\"];",
        "  node [shape=box, style=\"rounded,filled\", fillcolor=\"#f6f8fa\", color=\"#8c959f\", fontname=\"Arial\", fontsize=13, margin=\"0.12,0.08\"];",
        "  edge [color=\"#57606a\", fontname=\"Arial\", fontsize=12, arrowsize=0.8];",
    ]
    by_rank: dict[int, list[DrawioNode]] = {}
    for node in nodes:
        width_inches = node.width / 72
        height_inches = node.height / 72
        parts.append(
            f'  "{_dot_escape(node.node_id)}" [label="{_dot_escape(node.label)}", '
            f'width={width_inches:.2f}, height={height_inches:.2f}, fixedsize=true];'
        )
        by_rank.setdefault(node.rank, []).append(node)
    for rank, rank_nodes in sorted(by_rank.items()):
        ordered = sorted(rank_nodes, key=lambda node: (node.lane if node.lane is not None else 10_000, node.node_id))
        parts.append("  { rank=same; " + " ".join(f'"{_dot_escape(node.node_id)}";' for node in ordered) + " }")
        for left, right in zip(ordered, ordered[1:]):
            parts.append(f'  "{_dot_escape(left.node_id)}" -> "{_dot_escape(right.node_id)}" [style=invis, weight=8];')
    for edge in edges:
        if not edge.render:
            continue
        label = f' [label="{_dot_escape(edge.label)}"]' if edge.label and edge.show_label else ""
        parts.append(f'  "{_dot_escape(edge.source)}" -> "{_dot_escape(edge.target)}"{label};')
    parts.append("}")
    return "\n".join(parts)


def _dot_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def layout_drawio_graph(raw: Any, *, diagram_key: str) -> DrawioLayout:
    if _layout_engine(raw) == "graphviz":
        graphviz_layout = _graphviz_layout(raw, diagram_key=diagram_key)
        if graphviz_layout is not None:
            return graphviz_layout
    nodes, edges = _parse_graph(raw, diagram_key=diagram_key)
    by_rank: dict[int, list[DrawioNode]] = {}
    for node in nodes:
        by_rank.setdefault(node.rank, []).append(node)
    if not by_rank:
        raise DiffReportError(f"drawio_graph nodes must not be empty: {diagram_key}")

    rank_gap = _positive_int(raw.get("rank_gap", 96), field="rank_gap", diagram_key=diagram_key)
    lane_gap = _positive_int(raw.get("lane_gap", 48), field="lane_gap", diagram_key=diagram_key)
    margin_x = _positive_int(raw.get("margin_x", 32), field="margin_x", diagram_key=diagram_key)
    margin_y = _positive_int(raw.get("margin_y", 32), field="margin_y", diagram_key=diagram_key)

    layout_nodes: list[DrawioLayoutNode] = []
    max_width = 0
    max_bottom = 0
    for rank_index, rank in enumerate(sorted(by_rank)):
        row = sorted(by_rank[rank], key=lambda node: (node.lane if node.lane is not None else 10_000, node.node_id))
        x = margin_x
        row_height = max(node.height for node in row)
        y = margin_y + rank_index * (row_height + rank_gap)
        for node in row:
            layout_nodes.append(DrawioLayoutNode(node=node, x=x, y=y))
            max_width = max(max_width, x + node.width)
            max_bottom = max(max_bottom, y + node.height)
            x += node.width + lane_gap

    return DrawioLayout(
        nodes=tuple(layout_nodes),
        edges=tuple(edge for edge in edges if edge.render),
        width=max_width + margin_x,
        height=max_bottom + margin_y,
    )


def drawio_layout_svg(layout: DrawioLayout) -> str:
    nodes_by_id = {item.node.node_id: item for item in layout.nodes}
    edge_labels: list[tuple[float, float, str]] = []
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width}" height="{layout.height}" '
        f'viewBox="0 0 {layout.width} {layout.height}">',
        "<defs>",
        '<marker id="drawio-graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#57606a"/>',
        "</marker>",
        "</defs>",
        '<g fill="none" stroke="#57606a" stroke-width="1.5" marker-end="url(#drawio-graph-arrow)">',
    ]
    for edge_index, edge in enumerate(layout.edges):
        source = nodes_by_id[edge.source]
        target = nodes_by_id[edge.target]
        points = layout.edge_points[edge_index] if edge_index < len(layout.edge_points) else ()
        if not points:
            points = _edge_points(source, target)
        parts.append(f'<path d="{_svg_path(points)}"/>')
        if edge.label:
            label_x, label_y = _edge_label_position(points)
            edge_labels.append((label_x, label_y, edge.label))
    parts.append("</g>")
    parts.append('<g font-family="Arial, sans-serif" font-size="12" fill="#57606a">')
    for label_x, label_y, label in edge_labels:
        label_width = max(42, len(label) * 7 + 12)
        parts.append(
            f'<rect x="{label_x - label_width / 2:.1f}" y="{label_y - 13:.1f}" '
            f'width="{label_width}" height="18" rx="4" ry="4" fill="#ffffff" opacity="0.92"/>'
        )
        parts.append(f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle">{escape(label)}</text>')
    parts.append("</g>")
    parts.append('<g font-family="Arial, sans-serif" font-size="13" fill="#24292f">')
    for item in layout.nodes:
        parts.append(
            f'<rect x="{item.x}" y="{item.y}" width="{item.node.width}" height="{item.node.height}" '
            'rx="8" ry="8" fill="#f6f8fa" stroke="#8c959f" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{item.x + item.node.width / 2:.1f}" y="{item.y + item.node.height / 2 + 5:.1f}" '
            f'text-anchor="middle">{escape(item.node.label)}</text>'
        )
    parts.append("</g></svg>")
    return "".join(parts)


def _edge_points(source: DrawioLayoutNode, target: DrawioLayoutNode) -> tuple[tuple[float, float], ...]:
    source_center_x = source.x + source.node.width / 2
    source_center_y = source.y + source.node.height / 2
    target_center_x = target.x + target.node.width / 2
    target_center_y = target.y + target.node.height / 2
    if target.y >= source.y + source.node.height:
        start = (source_center_x, float(source.y + source.node.height))
        end = (target_center_x, float(target.y))
        mid_y = (start[1] + end[1]) / 2
        return _simplify_points((start, (start[0], mid_y), (end[0], mid_y), end))
    if source.y >= target.y + target.node.height:
        start = (source_center_x, float(source.y))
        end = (target_center_x, float(target.y + target.node.height))
        mid_y = (start[1] + end[1]) / 2
        return _simplify_points((start, (start[0], mid_y), (end[0], mid_y), end))
    if target.x >= source.x + source.node.width:
        start = (float(source.x + source.node.width), source_center_y)
        end = (float(target.x), target_center_y)
        mid_x = (start[0] + end[0]) / 2
        return _simplify_points((start, (mid_x, start[1]), (mid_x, end[1]), end))
    if source.x >= target.x + target.node.width:
        start = (float(source.x), source_center_y)
        end = (float(target.x + target.node.width), target_center_y)
        mid_x = (start[0] + end[0]) / 2
        return _simplify_points((start, (mid_x, start[1]), (mid_x, end[1]), end))
    return ((source_center_x, source_center_y), (target_center_x, target_center_y))


def _simplify_points(points: tuple[tuple[float, float], ...]) -> tuple[tuple[float, float], ...]:
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    simplified: list[tuple[float, float]] = []
    for point in deduped:
        if len(simplified) >= 2 and _is_between_collinear(simplified[-2], simplified[-1], point):
            simplified[-1] = point
        else:
            simplified.append(point)
    return tuple(simplified)


def _is_between_collinear(
    previous: tuple[float, float],
    current: tuple[float, float],
    following: tuple[float, float],
) -> bool:
    return (
        (previous[0] == current[0] == following[0] and min(previous[1], following[1]) <= current[1] <= max(previous[1], following[1]))
        or (previous[1] == current[1] == following[1] and min(previous[0], following[0]) <= current[0] <= max(previous[0], following[0]))
    )


def _svg_path(points: tuple[tuple[float, float], ...]) -> str:
    first, *rest = points
    commands = [f"M {first[0]:.1f} {first[1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in rest)
    return " ".join(commands)


def _edge_label_position(points: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    segments = list(zip(points, points[1:]))
    if not segments:
        return points[0]
    start, end = max(
        segments,
        key=lambda segment: abs(segment[0][0] - segment[1][0]) + abs(segment[0][1] - segment[1][1]),
    )
    label_x = (start[0] + end[0]) / 2
    label_y = (start[1] + end[1]) / 2 - 6
    return label_x, label_y


def drawio_layout_xml(layout: DrawioLayout) -> str:
    nodes_by_id = {item.node.node_id: item for item in layout.nodes}
    parts = [
        '<mxfile><diagram name="Page-1"><mxGraphModel><root>',
        '<mxCell id="0"/>',
        '<mxCell id="1" parent="0"/>',
    ]
    for item in layout.nodes:
        node_id = _xml_id(item.node.node_id)
        parts.append(
            f'<mxCell id="{node_id}" value="{escape(item.node.label)}" '
            'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f6f8fa;strokeColor=#8c959f;" vertex="1" parent="1">'
            f'<mxGeometry x="{item.x}" y="{item.y}" width="{item.node.width}" height="{item.node.height}" as="geometry"/>'
            "</mxCell>"
        )
    for index, edge in enumerate(layout.edges, start=1):
        points = layout.edge_points[index - 1] if index - 1 < len(layout.edge_points) else ()
        if not points:
            points = _edge_points(nodes_by_id[edge.source], nodes_by_id[edge.target])
        geometry = '<mxGeometry relative="1" as="geometry"/>'
        parts.append(
            f'<mxCell id="edge-{index}" value="{escape(_edge_xml_label(edge))}" '
            f'style="{_drawio_edge_style(nodes_by_id[edge.source], nodes_by_id[edge.target], points)}" '
            f'edge="1" parent="1" source="{_xml_id(edge.source)}" target="{_xml_id(edge.target)}">'
            f"{geometry}"
            "</mxCell>"
        )
    parts.append("</root></mxGraphModel></diagram></mxfile>")
    return "".join(parts)


def _parse_graph(raw: Any, *, diagram_key: str) -> tuple[tuple[DrawioNode, ...], tuple[DrawioEdge, ...]]:
    if not isinstance(raw, dict):
        raise DiffReportError(f"drawio_graph must be an object: {diagram_key}")
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise DiffReportError(f"drawio_graph.nodes must be a non-empty list: {diagram_key}")
    nodes: list[DrawioNode] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            raise DiffReportError(f"drawio_graph.nodes[{index}] must be an object: {diagram_key}")
        node_id = _non_empty_text(item.get("id"), field=f"nodes[{index}].id", diagram_key=diagram_key)
        if node_id in seen:
            raise DiffReportError(f"drawio_graph duplicate node id: {diagram_key}: {node_id}")
        seen.add(node_id)
        nodes.append(
            DrawioNode(
                node_id=node_id,
                label=str(item.get("label", node_id)),
                rank=_non_negative_int(item.get("rank", 0), field=f"nodes[{index}].rank", diagram_key=diagram_key),
                lane=_optional_non_negative_int(item.get("lane"), field=f"nodes[{index}].lane", diagram_key=diagram_key),
                width=_positive_int(item.get("width", 160), field=f"nodes[{index}].width", diagram_key=diagram_key),
                height=_positive_int(item.get("height", 64), field=f"nodes[{index}].height", diagram_key=diagram_key),
            )
        )
    raw_edges = raw.get("edges", [])
    if not isinstance(raw_edges, list):
        raise DiffReportError(f"drawio_graph.edges must be a list: {diagram_key}")
    edges: list[DrawioEdge] = []
    for index, item in enumerate(raw_edges):
        if not isinstance(item, dict):
            raise DiffReportError(f"drawio_graph.edges[{index}] must be an object: {diagram_key}")
        source = _non_empty_text(item.get("from"), field=f"edges[{index}].from", diagram_key=diagram_key)
        target = _non_empty_text(item.get("to"), field=f"edges[{index}].to", diagram_key=diagram_key)
        if source not in seen or target not in seen:
            raise DiffReportError(f"drawio_graph edge references unknown node: {diagram_key}: {source}->{target}")
        edges.append(
            DrawioEdge(
                source=source,
                target=target,
                label=str(item.get("label", "")),
                render=_edge_render_enabled(item),
                show_label=_edge_label_enabled(item),
            )
        )
    return tuple(nodes), tuple(edges)


def _edge_render_enabled(item: dict[str, Any]) -> bool:
    if "render" in item:
        return _bool_value(item["render"], default=True)
    if "hidden" in item:
        return not _bool_value(item["hidden"], default=False)
    return True


def _edge_label_enabled(item: dict[str, Any]) -> bool:
    if "show_label" in item:
        return _bool_value(item["show_label"], default=True)
    if "label_render" in item:
        return _bool_value(item["label_render"], default=True)
    if "label_hidden" in item:
        return not _bool_value(item["label_hidden"], default=False)
    return True


def _edge_xml_label(edge: DrawioEdge) -> str:
    if edge.show_label:
        return edge.label
    return ""


def _bool_value(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _layout_from_graphviz_plain(
    plain: str,
    *,
    nodes: tuple[DrawioNode, ...],
    edges: tuple[DrawioEdge, ...],
) -> DrawioLayout | None:
    graph_width = 0.0
    graph_height = 0.0
    by_id = {node.node_id: node for node in nodes}
    layout_nodes: list[DrawioLayoutNode] = []
    edge_points: list[tuple[tuple[float, float], ...]] = []
    for line in plain.splitlines():
        if not line.strip():
            continue
        tokens = shlex.split(line)
        if not tokens:
            continue
        if tokens[0] == "graph" and len(tokens) >= 4:
            graph_width = float(tokens[2]) * 72
            graph_height = float(tokens[3]) * 72
            continue
        if tokens[0] == "node" and len(tokens) >= 7:
            node = by_id.get(tokens[1])
            if node is None:
                continue
            center_x = float(tokens[2]) * 72
            center_y = float(tokens[3]) * 72
            width = float(tokens[4]) * 72
            height = float(tokens[5]) * 72
            x = int(round(center_x - width / 2))
            y = int(round(graph_height - center_y - height / 2))
            layout_nodes.append(
                DrawioLayoutNode(
                    node=DrawioNode(
                        node_id=node.node_id,
                        label=node.label,
                        rank=node.rank,
                        lane=node.lane,
                        width=int(round(width)),
                        height=int(round(height)),
                    ),
                    x=x,
                    y=y,
                )
            )
            continue
        if tokens[0] == "edge" and len(tokens) >= 6 and "invis" not in tokens:
            point_count = int(tokens[3])
            raw_points = tokens[4:4 + point_count * 2]
            points: list[tuple[float, float]] = []
            for index in range(0, len(raw_points), 2):
                points.append((float(raw_points[index]) * 72, graph_height - float(raw_points[index + 1]) * 72))
            edge_points.append(_simplify_points(tuple(points)))
    if not layout_nodes or not graph_width or not graph_height:
        return None
    ordered_nodes = tuple(sorted(layout_nodes, key=lambda item: (item.node.rank, item.node.lane or 0, item.node.node_id)))
    return DrawioLayout(
        nodes=ordered_nodes,
        edges=tuple(edge for edge in edges if edge.render),
        width=int(round(graph_width)),
        height=int(round(graph_height)),
        edge_points=(),
    )


def _drawio_edge_style(
    source: DrawioLayoutNode,
    target: DrawioLayoutNode,
    points: tuple[tuple[float, float], ...],
) -> str:
    exit_x, exit_y = _terminal_fraction(source, points[0])
    entry_x, entry_y = _terminal_fraction(target, points[-1])
    return (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
        "jettySize=auto;html=1;endArrow=block;endFill=1;"
        f"exitX={exit_x:.3f};exitY={exit_y:.3f};exitDx=0;exitDy=0;"
        f"entryX={entry_x:.3f};entryY={entry_y:.3f};entryDx=0;entryDy=0;"
    )


def _terminal_fraction(node: DrawioLayoutNode, point: tuple[float, float]) -> tuple[float, float]:
    left = float(node.x)
    right = float(node.x + node.node.width)
    top = float(node.y)
    bottom = float(node.y + node.node.height)
    x, y = point
    distances = (
        (abs(x - left), 0.0, _clamp_fraction((y - top) / node.node.height)),
        (abs(x - right), 1.0, _clamp_fraction((y - top) / node.node.height)),
        (abs(y - top), _clamp_fraction((x - left) / node.node.width), 0.0),
        (abs(y - bottom), _clamp_fraction((x - left) / node.node.width), 1.0),
    )
    _, fraction_x, fraction_y = min(distances, key=lambda item: item[0])
    return fraction_x, fraction_y


def _clamp_fraction(value: float) -> float:
    clamped = min(1.0, max(0.0, value))
    for anchor in (0.0, 0.5, 1.0):
        if abs(clamped - anchor) < 0.02:
            return anchor
    return clamped


def _non_empty_text(value: Any, *, field: str, diagram_key: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DiffReportError(f"drawio_graph.{field} must be non-empty: {diagram_key}")
    return text


def _positive_int(value: Any, *, field: str, diagram_key: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise DiffReportError(f"drawio_graph.{field} must be positive: {diagram_key}")
    return parsed


def _non_negative_int(value: Any, *, field: str, diagram_key: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise DiffReportError(f"drawio_graph.{field} must be non-negative: {diagram_key}")
    return parsed


def _optional_non_negative_int(value: Any, *, field: str, diagram_key: str) -> int | None:
    if value is None:
        return None
    return _non_negative_int(value, field=field, diagram_key=diagram_key)


def _xml_id(value: str) -> str:
    return "node-" + "".join(character if character.isalnum() or character in "-_" else "-" for character in value)
