from __future__ import annotations

import unittest

from agent_tools.tools.diff_report.graph_model import compile_graph, validate_model
from agent_tools.tools.diff_report.models import DiffReportError


def model() -> dict:
    return {
        "version": 1,
        "entity_types": {
            "scope": {"rank": 0, "representation": "node", "root": True},
            "item": {"rank": 1, "representation": "node"},
        },
        "relation_types": {
            "contains": {
                "source": ["scope"], "target": ["item"], "kind": "ownership",
                "cardinality": "one_to_many", "traversal": "forward",
            },
        },
        "derivations": [],
        "contexts": [],
    }


class GraphModelTests(unittest.TestCase):
    def test_compiles_declared_types_and_relations(self) -> None:
        graph = {"nodes": [{"id": "s", "type": "scope"}, {"id": "i", "type": "item"}],
                 "edges": [{"source": "s", "target": "i", "relation": "contains"}]}

        compiled = compile_graph(graph, model())

        self.assertEqual({"scope": 0, "item": 1}, compiled["traversal"]["type_ranks"])
        self.assertEqual("contains", compiled["edges"][0]["relation"])

    def test_rejects_unknown_entity_type(self) -> None:
        invalid = model()
        invalid["relation_types"]["contains"]["target"] = ["missing"]

        with self.assertRaisesRegex(DiffReportError, "unknown endpoint"):
            validate_model(invalid)
