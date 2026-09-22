from __future__ import annotations

import inspect
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runner  # noqa: E402
import validate_release  # noqa: E402


class PublicSuiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = json.loads((ROOT / "data/entities.json").read_text())
        cls.cases = json.loads((ROOT / "data/cases.json").read_text())

    def test_frozen_counts(self):
        self.assertEqual(len(self.entities), 32)
        self.assertEqual(len(self.cases), 150)
        self.assertEqual(Counter(x["category"] for x in self.cases), Counter(validate_release.EXPECTED))

    def test_synthetic_markers_and_ids(self):
        self.assertTrue(all(x["synthetic"] is True for x in self.entities + self.cases))
        self.assertEqual(len({x["entity_id"] for x in self.entities}), 32)
        self.assertEqual(len({x["case_id"] for x in self.cases}), 150)

    def test_diversity_invariants(self):
        self.assertEqual(len({x["request"] for x in self.cases}), 150)
        self.assertEqual(len({json.dumps(x["reference_ir"]["where"], sort_keys=True) for x in self.cases}), 150)
        self.assertEqual(len({json.dumps(x["targeted_mutation"]["where"], sort_keys=True) for x in self.cases}), 150)
        pairs = {(json.dumps(x["reference_ir"], sort_keys=True),
                  json.dumps(x["targeted_mutation"], sort_keys=True)) for x in self.cases}
        self.assertEqual(len(pairs), 150)
        self.assertTrue(all(18 <= x["age"] <= 100 for x in self.entities))

    def test_reference_contract(self):
        for case in self.cases:
            runner.validate_ir(case["reference_ir"])
            self.assertEqual(case["expected_entity_ids"], sorted(set(case["expected_entity_ids"])))

    def test_oracle_has_positive_and_negative_witnesses(self):
        by_category = {}
        for case in self.cases:
            by_category.setdefault(case["category"], []).append(case)
        self.assertGreaterEqual(
            sum(bool(x["expected_entity_ids"]) for x in by_category["nested_same_object"]), 8
        )
        self.assertGreaterEqual(
            sum(bool(x["expected_entity_ids"]) for x in by_category["multivalue_all_any"]), 10
        )
        for category, cases in by_category.items():
            if category not in {"nested_same_object", "multivalue_all_any"}:
                self.assertTrue(all(x["expected_entity_ids"] for x in cases), category)

    def test_all_controls(self):
        result = runner.run_suite()
        self.assertEqual(result["positive_controls_passed"], 150)
        self.assertEqual(result["mutations_caught"], 150)
        self.assertTrue(all(row["direct_matches_oracle"] for row in result["rows"]))
        self.assertTrue(all(row["lowered_matches_oracle"] for row in result["rows"]))

    def test_evaluator_paths_are_separate(self):
        lowered_source = inspect.getsource(runner.lower) + inspect.getsource(runner.dsl_eval)
        self.assertNotIn("direct_node", lowered_source)
        self.assertNotIn("direct_ids", lowered_source)

    def test_field_type_and_operator_matrix(self):
        bad_nodes = [
            {"field": "age", "op": "contains", "value": "2"},
            {"field": "active", "op": "gte", "value": False},
            {"field": "company_history", "op": "same_object", "value": {"months_gte": "twelve"}},
            {"field": "company", "op": "eq", "value": "Org-A"},
        ]
        for node in bad_nodes:
            with self.assertRaises(runner.ContractError):
                runner.validate_ir({"where": node, "optional": [], "unsupported": []})
        composite = {"or": [
            {"field": "city", "op": "eq", "value": "Northport"},
            {"field": "active", "op": "eq", "value": True},
        ]}
        with self.assertRaises(runner.ContractError):
            runner.validate_ir({"where": {"and": [composite, {"not": composite}]},
                                "optional": [], "unsupported": []})

    def test_common_mode_or_as_and_fault_is_detected_by_frozen_oracle(self):
        def corrupt(node, entity):
            if "and" in node:
                return all(corrupt(x, entity) for x in node["and"])
            if "or" in node:  # deliberate injected fault
                return all(corrupt(x, entity) for x in node["or"])
            if "not" in node:
                return not corrupt(node["not"], entity)
            return runner.direct_node(node, entity)

        failures = 0
        for case in self.cases:
            got = sorted(e["entity_id"] for e in self.entities if corrupt(case["reference_ir"]["where"], e))
            failures += got != case["expected_entity_ids"]
        self.assertGreater(failures, 0)

    def test_requests_are_self_contained(self):
        for case in self.cases:
            request = case["request"].lower()
            self.assertNotIn("boundary form", request)
            self.assertNotIn("stated status", request)


if __name__ == "__main__":
    unittest.main()
