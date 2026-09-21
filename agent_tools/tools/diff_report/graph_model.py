"""Compile a declared entity model into the renderer's graph wire format."""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from .models import DiffReportError


def _object(value: Any, where: str, keys: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) - keys:
        raise DiffReportError(f"{where}: expected object with keys {sorted(keys)}")
    return value


def _names(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
        raise DiffReportError(f"{where}: expected non-empty string list")
    if len(value) != len(set(value)):
        raise DiffReportError(f"{where}: duplicate names")
    return value


def _named_objects(value: Any, where: str) -> dict:
    if not isinstance(value, dict) or not value:
        raise DiffReportError(f"{where}: expected non-empty name mapping")
    if not all(isinstance(key, str) and key.strip() for key in value):
        raise DiffReportError(f"{where}: invalid name")
    return value


def _path_types(path: Any, relations: dict, where: str) -> tuple[set[str], set[str]]:
    if not isinstance(path, list) or not path:
        raise DiffReportError(f"{where}: expected non-empty path")
    start: set[str] = set()
    previous: set[str] = set()
    for index, raw in enumerate(path):
        step = _object(raw, where, {"relation", "direction"})
        relation = relations.get(str(step.get("relation", "")))
        direction = step.get("direction", "forward")
        if relation is None or relation["kind"] == "context" or direction not in ("forward", "reverse"):
            raise DiffReportError(f"{where}: invalid path step")
        source, target = set(relation["source"]), set(relation["target"])
        if direction == "reverse":
            source, target = target, source
        if index and not previous.intersection(source):
            raise DiffReportError(f"{where}: disconnected path types")
        if not index:
            start = source
        previous = target
    return start, previous


def validate_model(raw: Any) -> dict:
    """Validate configuration without inferring semantics from names or ranks."""
    model = deepcopy(_object(raw, "graph model", {"version", "entity_types", "relation_types", "derivations", "contexts"}))
    if type(model.get("version")) is not int or model["version"] != 1:
        raise DiffReportError("graph model: version must be 1")
    types = _named_objects(model.get("entity_types"), "entity_types")
    for name, raw_type in types.items():
        spec = _object(raw_type, name, {"rank", "representation", "root", "label", "nested_label", "shape", "scope", "scope_field", "terminal"})
        if type(spec.get("rank")) is not int or spec["rank"] < 0:
            raise DiffReportError(f"{name}: rank must be a non-negative integer")
        if spec.get("representation") not in ("node", "leaf_table"):
            raise DiffReportError(f"{name}: representation must be node or leaf_table")
        if type(spec.get("root", False)) is not bool or (spec.get("root") and spec["representation"] != "node"):
            raise DiffReportError(f"{name}: invalid root declaration")
        for field in ("label", "nested_label", "scope_field"):
            if field in spec and (not isinstance(spec[field], str) or not spec[field].strip()):
                raise DiffReportError(f"{name}: {field} must be non-empty text")
        if spec.get("shape", "round-rectangle") not in ("ellipse", "round-rectangle", "rectangle", "diamond", "hexagon", "barrel", "tag", "round-tag"):
            raise DiffReportError(f"{name}: unsupported shape")
        if spec.get("scope", "global") not in ("global", "isolated"):
            raise DiffReportError(f"{name}: scope must be global or isolated")
        if type(spec.get("terminal", False)) is not bool:
            raise DiffReportError(f"{name}: terminal must be boolean")
    relations = _named_objects(model.get("relation_types"), "relation_types")
    for name, raw_relation in relations.items():
        spec = _object(raw_relation, name, {"source", "target", "kind", "cardinality", "traversal", "group", "grouping", "filter_mode", "hierarchy"})
        if "hierarchy" in spec and (type(spec["hierarchy"]) is not bool or spec.get("kind") != "ownership"):
            raise DiffReportError(f"{name}: hierarchy must be boolean on an ownership relation")
        if "filter_mode" in spec and (spec.get("kind") != "context" or
                                      spec["filter_mode"] not in ("shared_children", "none")):
            raise DiffReportError(f"{name}: filter_mode requires a context relation and shared_children or none")
        if "grouping" in spec and (type(spec["grouping"]) is not bool or spec.get("kind") != "context"):
            raise DiffReportError(f"{name}: grouping must be boolean on a context relation")
        for endpoint in ("source", "target"):
            if set(_names(spec.get(endpoint), f"{name}.{endpoint}")) - types.keys():
                raise DiffReportError(f"{name}: unknown endpoint type")
        if spec.get("kind") not in ("ownership", "association", "context"):
            raise DiffReportError(f"{name}: invalid relation kind")
        if spec.get("cardinality") not in ("one_to_one", "one_to_many", "many_to_one", "many_to_many"):
            raise DiffReportError(f"{name}: invalid cardinality")
        if spec.get("traversal") not in ("both", "forward", "reverse", "none", "fallback"):
            raise DiffReportError(f"{name}: invalid traversal")
        if spec["kind"] == "ownership" and spec["cardinality"] not in ("one_to_one", "one_to_many"):
            raise DiffReportError(f"{name}: ownership requires at most one owner")
        if spec["kind"] == "context":
            if spec["traversal"] != "none" or not isinstance(spec.get("group"), str) or not spec["group"].strip():
                raise DiffReportError(f"{name}: context requires group and traversal none")
        elif "group" in spec:
            raise DiffReportError(f"{name}: group is only valid for context relations")
    rule_ids: set[str] = set()
    derived_relations: set[str] = set()
    for category in ("derivations", "contexts"):
        rules = model.setdefault(category, [])
        if not isinstance(rules, list):
            raise DiffReportError(f"{category}: expected list")
        for raw_rule in rules:
            keys = {"id", "relation", "path"} if category == "derivations" else {"id", "relation", "membership_path", "child_relation"}
            rule = _object(raw_rule, category, keys)
            name = rule.get("id")
            if not isinstance(name, str) or not name.strip() or name in rule_ids:
                raise DiffReportError(f"{category}: missing or duplicate rule id")
            rule_ids.add(name)
            relation = relations.get(str(rule.get("relation", "")))
            if relation is None:
                raise DiffReportError(f"{name}: unknown output relation")
            path = rule.get("path" if category == "derivations" else "membership_path")
            source, target = _path_types(path, relations, name)
            if not set(relation["source"]).issubset(source):
                raise DiffReportError(f"{name}: path source does not cover relation source")
            if category == "derivations":
                if relation["kind"] != "association" or not target.issubset(relation["target"]):
                    raise DiffReportError(f"{name}: derived relation must be an association with matching endpoints")
                # A summary association must not widen its underlying child membership.
                if relation["traversal"] not in ("none", "fallback"):
                    raise DiffReportError(f"{name}: derived association requires traversal none or fallback")
                derived_relations.add(rule["relation"])
            else:
                child = relations.get(str(rule.get("child_relation", "")))
                if relation["kind"] != "context" or child is None or child["kind"] == "context":
                    raise DiffReportError(f"{name}: invalid context or child relation")
                if not set(relation["target"]).issubset(child["source"]) or not target.intersection(child["target"]):
                    raise DiffReportError(f"{name}: context membership and child endpoints do not match")
    # Derivations use explicit evidence only. No rule ordering or recursive closure.
    for rule in model["derivations"]:
        if any(step["relation"] in derived_relations for step in rule["path"]):
            raise DiffReportError(f"{rule['id']}: derivations cannot depend on derived relations")
    return model


def _validate_entities(nodes: list[dict], edges: list[dict], model: dict) -> dict[str, dict]:
    types, relations = model["entity_types"], model["relation_types"]
    by_id: dict[str, dict] = {}
    root_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise DiffReportError("graph model: invalid node")
        node_id, kind = node.get("id"), node.get("type")
        if not isinstance(node_id, str) or not node_id or node_id in by_id:
            raise DiffReportError("graph model: missing or duplicate node id")
        if kind not in types or types[kind]["representation"] != "node":
            raise DiffReportError(f"{node_id}: unknown type or leaf_table entity used as graph node")
        by_id[node_id] = node
        if types[kind].get("root"):
            root_ids.add(node_id)
    if len(root_ids) > 1:
        raise DiffReportError("graph model: more than one root node")
    aliases: set[str] = set()
    for node in nodes:
        values = node.get("aliases", [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
            raise DiffReportError("graph model: aliases must be non-empty string identities")
        for value in values:
            if value in by_id or value in aliases:
                raise DiffReportError("graph model: ambiguous node alias " + value)
            aliases.add(value)
    owners: dict[str, str] = {}
    outgoing: dict[str, set[str]] = defaultdict(set)
    cardinalities: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    edge_keys: set[tuple[str, str, str]] = set()
    children: dict[str, set[str]] = defaultdict(set)
    contexts: list[dict] = []
    context_groups: dict[str, str] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            raise DiffReportError("graph model: invalid edge")
        source, target, name = edge.get("source"), edge.get("target"), edge.get("relation")
        if source not in by_id or target not in by_id or name not in relations:
            raise DiffReportError("graph model: missing endpoint or unknown relation")
        spec = relations[name]
        if "equivalent" in edge:
            if type(edge["equivalent"]) is not bool or not spec.get("hierarchy"):
                raise DiffReportError("equivalent requires a hierarchy relationship and boolean value")
            if edge["equivalent"] and not str(edge.get("equivalence_basis", "")).strip():
                raise DiffReportError("equivalent hierarchy requires an equivalence_basis")
        key = (source, target, name)
        if key in edge_keys:
            raise DiffReportError(f"{name}: duplicate relationship {source} -> {target}")
        edge_keys.add(key)
        if by_id[source]["type"] not in spec["source"] or by_id[target]["type"] not in spec["target"]:
            raise DiffReportError(f"{name}: wrong endpoint types for {source} -> {target}")
        if (spec["kind"] == "context") != ("context_children" in edge):
            raise DiffReportError(f"{name}: context_children must match relation kind")
        if spec["kind"] == "context":
            contexts.append(edge)
            group = edge.get("context_group", spec["group"])
            if group != spec["group"] or context_groups.setdefault(source, group) != group:
                raise DiffReportError(f"{source}: inconsistent context group")
        else:
            children[source].add(target)
        if "traverse" in edge and edge["traverse"] != spec["traversal"]:
            raise DiffReportError(f"{name}: edge traversal conflicts with model")
        cardinalities[(name, "source", source)].add(target)
        cardinalities[(name, "target", target)].add(source)
        if spec["kind"] == "ownership":
            if target in root_ids or owners.setdefault(target, source) != source:
                raise DiffReportError(f"{target}: root has an owner or entity has multiple owners")
            outgoing[source].add(target)
    for (name, side, node_id), peers in cardinalities.items():
        cardinality = relations[name]["cardinality"]
        limited = cardinality == "one_to_one" or cardinality == ("many_to_one" if side == "source" else "one_to_many")
        if limited and len(peers) > 1:
            raise DiffReportError(f"{name}: cardinality violation at {node_id}")
    degrees = {node_id: int(node_id in owners) for node_id in by_id}
    queue = deque(node_id for node_id, degree in degrees.items() if degree == 0)
    visited = 0
    while queue:
        source = queue.popleft()
        visited += 1
        for target in outgoing[source]:
            degrees[target] -= 1
            if degrees[target] == 0:
                queue.append(target)
    if visited != len(by_id):
        raise DiffReportError("graph model: ownership cycle")
    for edge in contexts:
        members = edge["context_children"]
        if not isinstance(members, list) or not all(isinstance(member, str) for member in members):
            raise DiffReportError("context_children must be a string list")
        if set(members) - children[edge["target"]]:
            raise DiffReportError("context_children must reference direct children")
    return by_id


class _PathIndex:
    """Finite typed joins; retain one witness per endpoint instead of all paths."""

    def __init__(self, edges: list[dict]) -> None:
        self.edges = edges
        self.adjacency: dict[tuple[str, str, str], list[tuple[str, int]]] = defaultdict(list)
        for index, edge in enumerate(edges):
            if "context_children" in edge:
                continue
            self.adjacency[(edge["relation"], "forward", edge["source"])].append((edge["target"], index))
            self.adjacency[(edge["relation"], "reverse", edge["target"])].append((edge["source"], index))

    def walk(self, start: str, path: list[dict]) -> dict[str, list[int]]:
        reached = {start: []}
        for step in path:
            following: dict[str, list[int]] = {}
            for source, witness in reached.items():
                for target, index in self.adjacency[(step["relation"], step.get("direction", "forward"), source)]:
                    following.setdefault(target, witness + [index])
            reached = following
        return reached


def _collapse_equivalent_hierarchy(graph: dict, model: dict) -> None:
    """Contract explicitly reviewed equivalents before deriving any context links."""
    nodes, edges = graph["nodes"], graph["edges"]
    relations = model["relation_types"]
    while True:
        candidates = [edge for edge in edges if edge.get("equivalent")]
        if not candidates:
            return
        # Process inner pairs first so an explicitly marked chain remains valid.
        sources = {edge["source"] for edge in candidates}
        pair = next(edge for edge in candidates if edge["target"] not in sources)
        parent_id, child_id = pair["source"], pair["target"]
        by_id = {node["id"]: node for node in nodes}
        parent, child = by_id[parent_id], by_id[child_id]
        siblings = {edge["target"] for edge in edges if edge["source"] == parent_id
                    and relations[edge["relation"]].get("hierarchy")}
        if parent["type"] != child["type"] or siblings != {child_id}:
            raise DiffReportError("equivalent hierarchy requires a sole child of the same entity type")
        if parent.get("status", "unknown") not in {"unknown", child.get("status", "unknown")}:
            raise DiffReportError("equivalent hierarchy has conflicting node statuses")
        child_members = {edge["target"] for edge in edges if edge["source"] == child_id
                         and relations[edge["relation"]]["kind"] != "context"}
        contexts = {(edge["source"], edge["relation"]): edge["context_children"]
                    for edge in edges if edge["target"] == child_id and "context_children" in edge}
        rewritten: dict[tuple[str, str, str], dict] = {}
        for original in edges:
            if original is pair:
                continue
            edge = deepcopy(original)
            if "context_children" in edge and child_id in edge["context_children"]:
                replacement = (contexts.get((edge["source"], edge["relation"]), child_members)
                               if edge["target"] == parent_id else {parent_id})
                edge["context_children"] = sorted((set(edge["context_children"]) - {child_id}) | set(replacement))
            for endpoint in ("source", "target"):
                if edge[endpoint] == child_id:
                    edge[endpoint] = parent_id
            if edge["source"] == edge["target"]:
                raise DiffReportError("equivalent hierarchy would discard a non-hierarchy self relationship")
            key = (edge["source"], edge["target"], edge["relation"])
            if key in rewritten and rewritten[key] != edge:
                raise DiffReportError("equivalent hierarchy has conflicting relationship facts")
            rewritten[key] = edge
        parent.setdefault("collapsed_nodes", []).append({
            "node": deepcopy(child), "equivalence_basis": pair["equivalence_basis"],
        })
        parent["aliases"] = sorted(set(parent.get("aliases", [])) | {child_id} | set(child.get("aliases", [])))
        if parent.get("status", "unknown") == "unknown":
            parent["status"] = child.get("status", "unknown")
        nodes.remove(child)
        edges[:] = rewritten.values()
        _validate_entities(nodes, edges, model)


def compile_graph(graph: dict, raw_model: dict) -> dict:
    """Compile source facts once; ranks never imply ownership or new associations.

    Generated edge provenance contains source-edge positions in this output.
    Leaf tables remain application-owned query data, not graph nodes.
    """
    model = validate_model(raw_model)
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise DiffReportError("graph model: graph requires node and edge lists")
    result = deepcopy(graph)
    nodes, edges = result["nodes"], result["edges"]
    if "model" in graph or any(isinstance(edge, dict) and "model_provenance" in edge for edge in edges):
        raise DiffReportError("graph model: expected source facts, not an already compiled graph")
    by_id = _validate_entities(nodes, edges, model)
    _collapse_equivalent_hierarchy(result, model)
    by_id = _validate_entities(nodes, edges, model)
    relations = model["relation_types"]
    index = _PathIndex(edges)
    explicit_keys = {(edge["source"], edge["target"], edge["relation"]) for edge in edges}
    generated: dict[tuple[str, str, str], dict] = {}
    for rule in model["derivations"]:
        spec = relations[rule["relation"]]
        for source, node in by_id.items():
            if node["type"] not in spec["source"]:
                continue
            for target, witness in index.walk(source, rule["path"]).items():
                key = (source, target, rule["relation"])
                edge = generated.setdefault(key, {"source": source, "target": target, "relation": rule["relation"], "model_provenance": []})
                edge["model_provenance"].append({"rule": rule["id"], "source_edges": witness})
    # Context membership joins share a child, not every descendant of its owner.
    for rule in model["contexts"]:
        spec = relations[rule["relation"]]
        child_owners: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for position, edge in enumerate(edges):
            if edge["relation"] == rule["child_relation"] and by_id[edge["source"]]["type"] in spec["target"]:
                child_owners[edge["target"]].append((edge["source"], position))
        for source, node in by_id.items():
            if node["type"] not in spec["source"]:
                continue
            for child, witness in index.walk(source, rule["membership_path"]).items():
                for focus, child_edge in child_owners.get(child, []):
                    if source == focus:
                        continue
                    key = (source, focus, rule["relation"])
                    edge = generated.setdefault(key, {"source": source, "target": focus, "relation": rule["relation"],
                                                     "context_children": [], "context_group": spec["group"], "model_provenance": []})
                    if child not in edge["context_children"]:
                        edge["context_children"].append(child)
                    edge["model_provenance"].append({"rule": rule["id"], "child": child, "source_edges": witness + [child_edge]})
    # A hierarchy includes each nested group's membership, but keeps the
    # immediate group as the context child so filters constrain every hop.
    hierarchy_parents = {edge["target"]: (edge["source"], position)
                         for position, edge in enumerate(edges)
                         if relations[edge["relation"]].get("hierarchy")}
    explicit_by_key = {(edge["source"], edge["target"], edge["relation"]): edge for edge in edges}
    for context in [edge for key, edge in generated.items() if key not in explicit_keys] + edges[:]:
        spec = relations[context["relation"]]
        if not spec.get("grouping") or not context.get("context_children"):
            continue
        child = context["target"]
        path: list[int] = []
        while child in hierarchy_parents:
            parent, position = hierarchy_parents[child]
            path.append(position)
            if by_id[parent]["type"] not in spec["target"]:
                break
            key = (context["source"], parent, context["relation"])
            if parent == context["source"]:
                break
            override = explicit_by_key.get(key)
            if override is not None and child not in override["context_children"]:
                break
            inherited = generated.setdefault(key, {
                "source": context["source"], "target": parent, "relation": context["relation"],
                "context_children": [], "context_group": spec["group"], "model_provenance": [],
            })
            if child not in inherited["context_children"]:
                inherited["context_children"].append(child)
            inherited["model_provenance"].append({
                "rule": "hierarchy-membership", "child": child,
                "source_edges": sorted({index for witness in context.get("model_provenance", [])
                                        for index in witness.get("source_edges", [])} | set(path)),
            })
            child = parent
    for key in sorted(generated):
        if key in explicit_keys:
            continue
        edge = generated[key]
        if "context_children" in edge:
            edge["context_children"].sort()
        edges.append(edge)
    _validate_entities(nodes, edges, model)
    for edge in edges:
        spec = relations[edge["relation"]]
        if spec["kind"] == "context":
            if edge.get("context_group", spec["group"]) != spec["group"]:
                raise DiffReportError("context group conflicts with model")
            edge["context_group"] = spec["group"]
        if spec["kind"] != "context" and spec["traversal"] in ("none", "fallback", "reverse"):
            edge["context_traverse"] = False
    result["model"] = model
    result["traversal"] = model_traversal(model)
    return result


def validate_graph_model(nodes: list[dict], edges: list[dict], raw_model: dict) -> dict:
    """Validate loaded facts as well as declarations at the renderer boundary."""
    model = validate_model(raw_model)
    _validate_entities(nodes, edges, model)
    return model


def model_traversal(model: dict) -> dict:
    return {
        "type_ranks": {name: spec["rank"] for name, spec in model["entity_types"].items() if spec["representation"] == "node"},
        "relation_traversal": {name: spec["traversal"] for name, spec in model["relation_types"].items()},
        "edge_direction": "focused_context",
        "terminal_types": [name for name, spec in model["entity_types"].items() if spec.get("terminal")],
    }
