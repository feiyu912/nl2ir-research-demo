#!/usr/bin/env python3
"""Pure-stdlib runner for the synthetic public conformance suite."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = {"city", "age", "degree", "skills", "languages", "certificates", "active",
          "graduation_year", "gap_months", "work_years", "company_history"}
NUMERIC_FIELDS = {"age", "graduation_year", "gap_months", "work_years"}
TEXT_FIELDS = {"city", "degree"}
MULTIVALUE_FIELDS = {"skills", "languages", "certificates"}
SCALAR_OPS = {"eq", "gte", "lte", "gt", "lt", "contains"}
MULTI_OPS = {"all", "any"}


class ContractError(ValueError):
    pass


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_ir(ir: dict) -> None:
    if not isinstance(ir, dict) or set(ir) != {"where", "optional", "unsupported"}:
        raise ContractError("IR root must contain exactly where, optional, unsupported")
    if not isinstance(ir["optional"], list) or not isinstance(ir["unsupported"], list):
        raise ContractError("optional and unsupported must be arrays")
    if ir["unsupported"]:
        raise ContractError("unsupported hard conditions fail closed")
    validate_node(ir["where"])
    reject_contradictory_conjunctions(ir["where"])
    for item in ir["optional"]:
        validate_node(item)


def validate_node(node) -> None:
    if not isinstance(node, dict):
        raise ContractError("node must be an object")
    bool_keys = set(node) & {"and", "or", "not"}
    if bool_keys:
        if len(bool_keys) != 1 or len(node) != 1:
            raise ContractError("boolean node has one operator only")
        key = next(iter(bool_keys))
        if key == "not":
            validate_node(node[key]); return
        children = node[key]
        if not isinstance(children, list) or len(children) < 2:
            raise ContractError(f"{key} requires at least two children")
        for child in children:
            validate_node(child)
        return
    if set(node) != {"field", "op", "value"}:
        raise ContractError("leaf must contain exactly field, op, value")
    field, op, value = node["field"], node["op"], node["value"]
    if field not in FIELDS:
        raise ContractError(f"unknown field: {field}")
    if field == "company_history":
        if op != "same_object" or not isinstance(value, dict) or not value:
            raise ContractError("company_history requires a same_object constraint")
        if not set(value) <= {"company", "role", "months_gte"}:
            raise ContractError("unknown same_object key")
        if "company" in value and not isinstance(value["company"], str):
            raise ContractError("same_object company must be a string")
        if "role" in value and not isinstance(value["role"], str):
            raise ContractError("same_object role must be a string")
        if "months_gte" in value and (not isinstance(value["months_gte"], int) or isinstance(value["months_gte"], bool)):
            raise ContractError("same_object months_gte must be an integer")
        return
    if op in MULTI_OPS:
        if field not in MULTIVALUE_FIELDS:
            raise ContractError("all/any require a multivalue field")
        if (not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value)
                or value != sorted(set(value))):
            raise ContractError("multivalue arrays must be nonempty, unique, canonical order")
    elif op not in SCALAR_OPS:
        raise ContractError(f"unknown operator: {op}")
    elif field in NUMERIC_FIELDS:
        if op not in {"eq", "gte", "lte", "gt", "lt"}:
            raise ContractError(f"numeric field does not support {op}")
        if not isinstance(value, int) or isinstance(value, bool):
            raise ContractError("numeric field value must be an integer")
    elif field == "active":
        if op != "eq" or not isinstance(value, bool):
            raise ContractError("active supports Boolean eq only")
    elif field in TEXT_FIELDS:
        if op != "eq" or not isinstance(value, str):
            raise ContractError(f"{field} supports string eq only")
    elif field in MULTIVALUE_FIELDS:
        if op != "contains" or not isinstance(value, str):
            raise ContractError(f"{field} scalar leaves support string contains only")


def reject_contradictory_conjunctions(node: dict) -> None:
    """Reject X AND NOT(X), including when AND nodes are nested."""
    if "and" in node:
        positive, negative = set(), set()

        def collect(child: dict) -> None:
            if "and" in child:
                for grandchild in child["and"]:
                    collect(grandchild)
            elif "not" in child:
                negative.add(json.dumps(child["not"], sort_keys=True))
            else:
                positive.add(json.dumps(child, sort_keys=True))

        for child in node["and"]:
            collect(child)
        if positive & negative:
            raise ContractError("contradictory conjunction")
        for child in node["and"]:
            reject_contradictory_conjunctions(child)
    elif "or" in node:
        for child in node["or"]:
            reject_contradictory_conjunctions(child)
    elif "not" in node:
        reject_contradictory_conjunctions(node["not"])


# Implementation A: evaluate the IR tree directly.
def direct_node(node: dict, entity: dict) -> bool:
    if "and" in node:
        return all(direct_node(x, entity) for x in node["and"])
    if "or" in node:
        return any(direct_node(x, entity) for x in node["or"])
    if "not" in node:
        return not direct_node(node["not"], entity)
    field, op, value = node["field"], node["op"], node["value"]
    if field == "company_history":
        return any(
            ("company" not in value or row["company"] == value["company"])
            and ("role" not in value or row["role"] == value["role"])
            and ("months_gte" not in value or row["months"] >= value["months_gte"])
            for row in entity["company_history"]
        )
    if field in {"company", "role", "role_months"}:
        key = {"company": "company", "role": "role", "role_months": "months"}[field]
        vals = [r[key] for r in entity["company_history"]]
        return any(compare(v, op, value) for v in vals)
    actual = entity[field]
    if op == "all": return all(v in actual for v in value)
    if op == "any": return any(v in actual for v in value)
    if op == "contains": return value in actual
    return compare(actual, op, value)


def compare(actual, op: str, expected) -> bool:
    if op == "eq": return actual == expected
    if op == "gte": return actual >= expected
    if op == "lte": return actual <= expected
    if op == "gt": return actual > expected
    if op == "lt": return actual < expected
    return False


def direct_ids(ir: dict, entities: list[dict]) -> list[str]:
    return sorted(e["entity_id"] for e in entities if direct_node(ir["where"], e))


# Implementation B: lower to a deliberately different tuple DSL, then interpret it.
def lower(node: dict):
    if "and" in node: return ("BOOL_ALL", tuple(lower(x) for x in node["and"]))
    if "or" in node: return ("BOOL_ANY", tuple(lower(x) for x in node["or"]))
    if "not" in node: return ("BOOL_NONE", lower(node["not"]))
    if node["field"] == "company_history":
        tests = []
        for key, value in node["value"].items():
            tests.append((key, "gte" if key == "months_gte" else "eq", value))
        return ("NESTED_ONE", tuple(tests))
    return ("ATOM", node["field"], node["op"], node["value"])


def dsl_eval(code, record: dict) -> bool:
    tag = code[0]
    if tag == "BOOL_ALL":
        result = True
        for child in code[1]: result = result and dsl_eval(child, record)
        return result
    if tag == "BOOL_ANY":
        result = False
        for child in code[1]: result = result or dsl_eval(child, record)
        return result
    if tag == "BOOL_NONE": return not dsl_eval(code[1], record)
    if tag == "NESTED_ONE":
        for job in record["company_history"]:
            ok = True
            for key, operation, wanted in code[1]:
                actual = job["months"] if key == "months_gte" else job[key]
                ok = ok and ((actual >= wanted) if operation == "gte" else (actual == wanted))
            if ok: return True
        return False
    _, field, operation, wanted = code
    if field in {"company", "role", "role_months"}:
        source = {"company": "company", "role": "role", "role_months": "months"}[field]
        actuals = [j[source] for j in record["company_history"]]
        return any(atom_eval(x, operation, wanted) for x in actuals)
    return atom_eval(record[field], operation, wanted)


def atom_eval(actual, operation: str, wanted) -> bool:
    if operation == "all": return set(wanted).issubset(set(actual))
    if operation == "any": return bool(set(wanted).intersection(actual))
    if operation == "contains": return wanted in actual
    if operation == "eq": return actual == wanted
    if operation == "gte": return actual >= wanted
    if operation == "lte": return actual <= wanted
    if operation == "gt": return actual > wanted
    if operation == "lt": return actual < wanted
    raise ContractError(f"unhandled DSL operation: {operation}")


def lowered_ids(ir: dict, entities: list[dict]) -> list[str]:
    code = lower(ir["where"])
    return sorted(r["entity_id"] for r in entities if dsl_eval(code, r))


def run_suite() -> dict:
    entities = load_json(ROOT / "data" / "entities.json")
    cases = load_json(ROOT / "data" / "cases.json")
    rows = []
    for case in cases:
        ref = case["reference_ir"]
        validate_ir(ref)
        expected = case["expected_entity_ids"]
        direct = direct_ids(ref, entities)
        lowered = lowered_ids(ref, entities)
        direct_matches_oracle = direct == expected
        lowered_matches_oracle = lowered == expected
        positive = direct_matches_oracle and lowered_matches_oracle
        mutation_valid, mutation_ids = True, []
        try:
            validate_ir(case["targeted_mutation"])
            mutation_ids = direct_ids(case["targeted_mutation"], entities)
            mutation_lowered = lowered_ids(case["targeted_mutation"], entities)
            if mutation_ids != mutation_lowered:
                mutation_valid = False
        except ContractError:
            mutation_valid = False
        mutation_caught = (not mutation_valid) or mutation_ids != expected
        rows.append({"case_id": case["case_id"], "category": case["category"],
                     "expected_entity_ids": expected, "direct_entity_ids": direct,
                     "lowered_entity_ids": lowered,
                     "direct_matches_oracle": direct_matches_oracle,
                     "lowered_matches_oracle": lowered_matches_oracle,
                     "positive_control_passed": positive,
                     "mutation_caught": mutation_caught})
    return {"case_count": len(rows),
            "positive_controls_passed": sum(r["positive_control_passed"] for r in rows),
            "mutations_caught": sum(r["mutation_caught"] for r in rows), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_suite()
    if args.json: print(json.dumps(result, indent=2))
    else: print(f"positive {result['positive_controls_passed']}/{result['case_count']}; mutations caught {result['mutations_caught']}/{result['case_count']}")
    raise SystemExit(0 if result["positive_controls_passed"] == result["case_count"] and result["mutations_caught"] == result["case_count"] else 1)
