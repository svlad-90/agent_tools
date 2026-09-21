from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .models import DiffReportError
from .report_json import relationship_graph_from_payload


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        create table graph_meta (
            key text primary key,
            value text not null
        );

        create table graph_nodes (
            node_id text primary key,
            node_type text not null,
            label text not null,
            status text not null,
            node_json text not null,
            position integer not null unique
        );

        create table graph_edges (
            edge_id text primary key,
            source text not null,
            target text not null,
            relation text not null,
            edge_json text not null,
            position integer not null unique
        );

        create table report_documents (
            name text primary key,
            payload_json text not null
        );
        create index idx_graph_nodes_type on graph_nodes(node_type);
        create index idx_graph_nodes_status on graph_nodes(status);
        create index idx_graph_edges_source on graph_edges(source);
        create index idx_graph_edges_target on graph_edges(target);
        create index idx_graph_edges_relation on graph_edges(relation);
        """
    )


def write_graph(connection: sqlite3.Connection, graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
        raise ValueError("Relationship graph must contain nodes and an edge list")
    graph_meta = [
        ("title", str(graph.get("title") or "Relationship Graph")),
        ("status_order_json", json.dumps(graph.get("status_order", []), ensure_ascii=False)),
        ("traversal_json", json.dumps(graph.get("traversal", {}), ensure_ascii=False)),
        ("filter_defaults_json", json.dumps(graph.get("filter_defaults", {}), ensure_ascii=False)),
        ("model_json", json.dumps(graph.get("model"), ensure_ascii=False)),
        ("node_count", str(len(nodes))),
        ("edge_count", str(len(edges))),
    ]
    graph_node_rows: list[tuple[str, str, str, str, str, int]] = []
    graph_edge_rows: list[tuple[str, str, str, str, str, int]] = []
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Invalid graph node at position {index}")
        node_id = str(node.get("id") or "")
        if not node_id or node_id in node_ids:
            raise ValueError(f"Missing or duplicate graph node ID at position {index}")
        node_ids.add(node_id)
        graph_node_rows.append(
            (
                node_id,
                str(node.get("type") or "entity"),
                str(node.get("label") or node_id),
                str(node.get("status") or "unknown"),
                json.dumps(node, ensure_ascii=False, separators=(",", ":")),
                index,
            )
        )
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"Invalid graph edge at position {index}")
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in node_ids or target not in node_ids:
            raise ValueError(f"Graph edge at position {index} references a missing node")
        relation = str(edge.get("relation") or "related_to")
        edge_id = hashlib.sha1(f"{source}\0{target}\0{relation}\0{index}".encode("utf-8")).hexdigest()
        graph_edge_rows.append(
            (
                f"edge:{edge_id[:20]}",
                source,
                target,
                relation,
                json.dumps(edge, ensure_ascii=False, separators=(",", ":")),
                index,
            )
        )
    try:
        relationship_graph_from_payload(graph)
    except DiffReportError as error:
        raise ValueError(str(error)) from error
    connection.executemany("insert into graph_meta values (?, ?)", graph_meta)
    connection.executemany("insert into graph_nodes values (?, ?, ?, ?, ?, ?)", graph_node_rows)
    connection.executemany("insert into graph_edges values (?, ?, ?, ?, ?, ?)", graph_edge_rows)
    return {
        **{key: value for key, value in graph.items() if key not in {"nodes", "edges"}},
        "data_source": "sqlite", "node_count": len(nodes), "edge_count": len(edges),
        "nodes": [], "edges": [],
    }


def read_relationship_graph(connection: sqlite3.Connection) -> dict[str, Any]:
    meta = dict(connection.execute("select key, value from graph_meta"))
    nodes = [
        json.loads(row[0])
        for row in connection.execute("select node_json from graph_nodes order by position")
    ]
    edges = [
        json.loads(row[0])
        for row in connection.execute("select edge_json from graph_edges order by position")
    ]
    if not nodes:
        raise ValueError("The report database contains no relationship graph; run the full pipeline")
    return {
        "title": meta.get("title", "Relationship Graph"),
        **({"model": json.loads(meta["model_json"])} if meta.get("model_json", "null") != "null" else {}),
        "nodes": nodes,
        "edges": edges,
        "traversal": json.loads(meta.get("traversal_json", "{}")),
        "filter_defaults": json.loads(meta.get("filter_defaults_json", "{}")),
        "status_order": json.loads(meta.get("status_order_json", "[]")),
        "count": len(nodes),
    }


def write_report(connection: sqlite3.Connection, payload: dict[str, Any], name: str = "dashboard") -> None:
    """Store a document and its graph atomically without committing caller work."""
    connection.execute("savepoint report_document")
    try:
        document = dict(payload)
        document["relationship_graph"] = write_graph(connection, payload["relationship_graph"])
        connection.execute("insert into report_documents values (?, ?)",
                           (name, json.dumps(document, ensure_ascii=False, separators=(",", ":"))))
    except Exception:
        connection.execute("rollback to report_document")
        raise
    finally:
        connection.execute("release report_document")


def read_report(connection: sqlite3.Connection, name: str = "dashboard") -> dict[str, Any]:
    row = connection.execute("select payload_json from report_documents where name = ?", (name,)).fetchone()
    if row is None:
        raise ValueError(f"The report database contains no document: {name}")
    payload = json.loads(row[0])
    payload["relationship_graph"].update(read_relationship_graph(connection))
    return payload


def read_dashboard(connection: sqlite3.Connection) -> dict[str, Any]:
    return read_report(connection)


def query_report(connection: sqlite3.Connection, name: str, params: dict[str, str]) -> dict[str, Any]:
    """HTTP counterpart of the embedded provider's built-in queries."""
    if name == "relationship-graph":
        return {"query": name, **read_relationship_graph(connection)}
    if name != "search":
        raise ValueError(f"Unsupported report query: {name}")
    if not params.get("q"):
        raise ValueError("search requires q")
    try:
        limit = max(1, min(int(params.get("limit", "200")), 5000))
    except ValueError:
        limit = 200
    pattern = f"%{params['q']}%"
    cursor = connection.execute(
        "select node_id as entity_id, node_type as entity_type, label as title, status "
        "from graph_nodes where node_id like ? or label like ? order by position limit ?",
        (pattern, pattern, limit),
    )
    columns = [item[0] for item in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor]
    return {"query": name, "rows": rows, "count": len(rows)}
