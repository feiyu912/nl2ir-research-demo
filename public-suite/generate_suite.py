#!/usr/bin/env python3
"""Generate the frozen, fully synthetic NL2IR public conformance suite."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

CITIES = ["Northport", "Eastvale", "Southbay", "Westhaven"]
DEGREES = ["bachelor", "master", "doctorate", "associate"]
SKILLS = ["python", "sql", "java", "kubernetes", "tableau", "rust"]
LANGUAGES = ["english", "german", "japanese", "french"]
CERTS = ["cloud-a", "data-b", "security-c", "project-d"]


def entities() -> list[dict]:
    rows = []
    for i in range(32):
        role_a = ["engineer", "analyst", "manager", "designer"][i % 4]
        role_b = ["analyst", "engineer", "designer", "manager"][(i // 4) % 4]
        rows.append({
            "entity_id": f"SYN-{i + 1:03d}",
            "synthetic": True,
            "city": CITIES[i % 4],
            "age": 22 + i,
            "degree": DEGREES[(i // 2) % 4],
            "skills": sorted({SKILLS[i % 6], SKILLS[(i + 2) % 6]}),
            "languages": sorted({LANGUAGES[i % 4], LANGUAGES[(i + 1) % 4]}),
            "certificates": sorted({CERTS[i % 4]}),
            "active": i % 3 != 0,
            "graduation_year": 2014 + (i % 13),
            "gap_months": (i * 3) % 18,
            "work_years": i % 12,
            "company_history": [
                {"company": f"Org-{chr(65 + i % 5)}", "role": role_a, "months": 6 + (i * 5) % 55},
                {"company": f"Org-{chr(65 + (i + 2) % 5)}", "role": role_b, "months": 4 + (i * 7) % 49},
            ],
        })
    return rows


def leaf(field: str, op: str, value):
    return {"field": field, "op": op, "value": value}


def AND(*children):
    return {"and": list(children)}


def OR(*children):
    return {"or": list(children)}


def NOT(child):
    return {"not": child}


def describe(node) -> str:
    if "and" in node:
        return "(" + " and ".join(describe(x) for x in node["and"]) + ")"
    if "or" in node:
        return "(" + " or ".join(describe(x) for x in node["or"]) + ")"
    if "not" in node:
        return "not " + describe(node["not"])
    return f"{node['field']} {node['op']} {node['value']}"


def anchor_for(i: int, mode: int):
    """A meaningful synthetic context that uniquely identifies entity i."""
    age = 22 + i
    year = 2014 + i % 13
    work = i % 12
    city = CITIES[i % 4]
    if mode == 0:
        return leaf("age", "eq", age), f"age exactly {age}"
    if mode == 1:
        return AND(leaf("graduation_year", "eq", year), leaf("work_years", "eq", work)), f"graduated in {year} with {work} work years"
    if mode == 2:
        return AND(leaf("city", "eq", city), leaf("graduation_year", "eq", year)), f"in {city} and graduated in {year}"
    return AND(leaf("age", "gte", age), leaf("age", "lte", age)), f"age exactly {age} expressed as a closed range"


def oracle_compare(actual, op: str, expected) -> bool:
    """Reference semantics used only while freezing expected entity IDs."""
    return {
        "eq": actual == expected,
        "gte": actual >= expected,
        "lte": actual <= expected,
        "gt": actual > expected,
        "lt": actual < expected,
    }.get(op, False)


def oracle_matches(node: dict, entity: dict) -> bool:
    """Small generator-side oracle, independent of runner.py's two evaluators."""
    if "and" in node:
        return all(oracle_matches(child, entity) for child in node["and"])
    if "or" in node:
        return any(oracle_matches(child, entity) for child in node["or"])
    if "not" in node:
        return not oracle_matches(node["not"], entity)
    field, op, wanted = node["field"], node["op"], node["value"]
    if field == "company_history":
        return any(
            ("company" not in wanted or job["company"] == wanted["company"])
            and ("role" not in wanted or job["role"] == wanted["role"])
            and ("months_gte" not in wanted or job["months"] >= wanted["months_gte"])
            for job in entity["company_history"]
        )
    if field in {"company", "role", "role_months"}:
        source = {"company": "company", "role": "role", "role_months": "months"}[field]
        return any(oracle_compare(job[source], op, wanted) for job in entity["company_history"])
    actual = entity[field]
    if op == "all":
        return set(wanted).issubset(actual)
    if op == "any":
        return bool(set(wanted).intersection(actual))
    if op == "contains":
        return wanted in actual
    return oracle_compare(actual, op, wanted)


def make_cases() -> list[dict]:
    specs: list[tuple[str, int]] = [
        ("boolean_negation", 25), ("nested_same_object", 25),
        ("numeric_date_ranges", 20), ("multivalue_all_any", 20),
        ("equality_canonicalization", 15), ("normalization_aliases", 20),
        ("cross_field_conflicts", 15), ("invalid_schema_only", 10),
    ]
    rows = entities()
    cases = []
    n = 0
    for cat_index, (category, count) in enumerate(specs):
        for j in range(count):
            n += 1
            i = (j + cat_index * 3) % 32
            entity = rows[i]
            anchor, anchor_text = anchor_for(i, j % 4)

            if category == "boolean_negation":
                a = leaf("city", "eq", entity["city"])
                b_true = leaf("active", "eq", entity["active"])
                b_false = leaf("active", "eq", not entity["active"])
                c_true = leaf("skills", "contains", entity["skills"][0])
                c_false = leaf("skills", "contains", next(v for v in SKILLS if v not in entity["skills"]))
                shapes = [AND(a, b_true), OR(a, b_false), NOT(OR(NOT(a), b_false)),
                          OR(AND(a, b_true), c_false), AND(a, OR(b_false, c_true))]
                core = shapes[j % len(shapes)]
                bad = NOT(core)
                rule = "Preserve AND, OR, and NOT structure, branch threshold, and polarity exactly."
                request = f"Profiles {anchor_text} satisfying {describe(core)}."
            elif category == "nested_same_object":
                first, second = entity["company_history"]
                if j % 3 == 0:
                    # Positive witness: both facts really occur in one object.
                    value = {"company": first["company"], "role": first["role"]}
                    loose = leaf(
                        "company_history", "same_object",
                        {"company": first["company"], "role": "nonmatching-role"},
                    )
                elif first["role"] != second["role"]:
                    # Negative witness: flattened leaves can match different objects.
                    value = {"company": first["company"], "role": second["role"]}
                    loose = AND(leaf("company", "eq", first["company"]), leaf("role", "eq", second["role"]))
                elif first["months"] != second["months"]:
                    low, high = sorted((first, second), key=lambda x: x["months"])
                    value = {"company": low["company"], "months_gte": low["months"] + 1}
                    loose = AND(leaf("company", "eq", low["company"]), leaf("role_months", "gte", low["months"] + 1))
                else:
                    value = {"company": first["company"], "role": "nonmatching-role"}
                    loose = AND(leaf("company", "eq", first["company"]), leaf("role", "eq", second["role"]))
                core = leaf("company_history", "same_object", value)
                bad = loose
                rule = "Company, role, and tenure constraints must bind to one history object."
                parts = []
                if "company" in value: parts.append(f"company {value['company']}")
                if "role" in value: parts.append(f"role {value['role']}")
                if "months_gte" in value: parts.append(f"at least {value['months_gte']} months")
                request = f"Profiles {anchor_text}; require {' and '.join(parts)} in the same job."
            elif category == "numeric_date_ranges":
                field = ["age", "work_years", "gap_months", "graduation_year"][j % 4]
                actual = entity[field]
                form = j % 5
                if form == 0: core, bad = leaf(field, "gte", actual), leaf(field, "gt", actual)
                elif form == 1: core, bad = leaf(field, "lte", actual), leaf(field, "lt", actual)
                elif form == 2: core, bad = leaf(field, "eq", actual), leaf(field, "gt", actual)
                elif form == 3: core, bad = AND(leaf(field, "gte", actual), leaf(field, "lte", actual)), leaf(field, "gt", actual)
                else: core, bad = leaf(field, "gt", actual - 1), leaf(field, "gte", actual + 1)
                rule = "Preserve inclusive, strict, equality, closed-range, numeric, and calendar boundaries."
                request = f"Profiles {anchor_text}; additionally require {describe(core)}."
            elif category == "multivalue_all_any":
                field = ["skills", "languages", "certificates"][j % 3]
                present = entity[field][0]
                universe = SKILLS if field == "skills" else LANGUAGES if field == "languages" else CERTS
                absent = next(v for v in universe if v not in entity[field])
                if j % 4 == 0:
                    # Positive ALL witness; the mutation adds one missing value.
                    values = sorted(entity[field])
                    core = leaf(field, "all", values)
                    bad = leaf(field, "all", sorted(set(values + [absent])))
                elif j % 2 == 0:
                    # Positive ANY witness versus an unsatisfied ALL mutation.
                    values = sorted([present, absent])
                    core, bad = leaf(field, "any", values), leaf(field, "all", values)
                else:
                    # Negative ALL witness versus a satisfiable ANY mutation.
                    values = sorted([present, absent])
                    core, bad = leaf(field, "all", values), leaf(field, "any", values)
                rule = "ALL requires every listed value; ANY requires at least one across a multivalue field."
                requested_op = "ALL" if j % 4 == 0 or j % 2 else "ANY"
                request = f"Profiles {anchor_text}; apply {requested_op} over {field}: {', '.join(values)}."
            elif category == "equality_canonicalization":
                mode = j % 3
                if mode == 0:
                    value = entity["city"]
                    core, bad = leaf("city", "eq", value), leaf("city", "eq", value.lower())
                    request = f"Profiles {anchor_text} whose city equals canonical value {value}."
                elif mode == 1:
                    value = entity["degree"]
                    core, bad = leaf("degree", "eq", value), leaf("degree", "term", value)
                    request = f"Profiles {anchor_text} whose degree equals {value}."
                else:
                    vals = sorted(entity["languages"])
                    core, bad = leaf("languages", "any", vals), leaf("languages", "any", list(reversed(vals)))
                    request = f"Profiles {anchor_text} using canonical language list {', '.join(vals)}."
                rule = "Equality uses eq with canonical spelling; arrays are unique and deterministically ordered."
            elif category == "normalization_aliases":
                mode = j % 4
                if mode == 0:
                    canon = entity["skills"][0]
                    alias = {"python":"Py", "sql":"Structured Query Language", "java":"JVM Java", "kubernetes":"K8s", "tableau":"Tableau BI", "rust":"Rustlang"}[canon]
                    core, bad = leaf("skills", "contains", canon), leaf("skills", "contains", alias.lower())
                    request, rule = f"Profiles {anchor_text} familiar with alias {alias}.", f"Normalize {alias!r} to {canon!r}."
                elif mode == 1:
                    core, bad = leaf("active", "eq", entity["active"]), leaf("active", "eq", "currently-working" if entity["active"] else "not-working")
                    status = "currently active" if entity["active"] else "not active"
                    request, rule = f"Profiles {anchor_text} who are {status}.", "Normalize status phrases to Boolean values."
                elif mode == 2:
                    years = entity["work_years"]
                    core, bad = leaf("work_years", "eq", years), leaf("work_years", "eq", years * 12)
                    request, rule = f"Profiles {anchor_text} with exactly {years} years of work.", "Normalize duration to the target field unit."
                else:
                    year = entity["graduation_year"]
                    core, bad = leaf("graduation_year", "eq", year), leaf("graduation_year", "eq", year % 100)
                    request, rule = f"Profiles {anchor_text} from class of '{str(year)[2:]}.", "Normalize abbreviated years to four digits."
            elif category == "cross_field_conflicts":
                year, degree = entity["graduation_year"], entity["degree"]
                core = AND(leaf("graduation_year", "eq", year), leaf("degree", "eq", degree))
                if j % 2 == 0:
                    bad = AND(leaf("work_years", "eq", year), leaf("degree", "eq", degree))
                else:
                    bad = AND(core, NOT(leaf("graduation_year", "eq", year)))
                rule = "Route each value to its declared field and reject contradictory leaves."
                request = f"Profiles {anchor_text}, graduating in {year} with degree {degree}."
            else:
                fields = [("city", entity["city"]), ("degree", entity["degree"]),
                          ("active", entity["active"]), ("age", entity["age"]),
                          ("graduation_year", entity["graduation_year"])]
                field, value = fields[j % len(fields)]
                core = leaf(field, "eq", value)
                bad = ({"field": field, "operator": "eq", "value": value} if j % 2 == 0
                       else leaf(field, "term", value))
                rule = "A leaf has exactly field, op, value; schema-valid trees must also satisfy the executable contract."
                request = f"Profiles {anchor_text}; require public field {field} to equal {value!r}."

            reference = {"where": AND(anchor, core), "optional": [], "unsupported": []}
            mutation = {"where": AND(anchor, bad), "optional": [], "unsupported": []}
            expected_ids = sorted(
                row["entity_id"] for row in rows if oracle_matches(reference["where"], row)
            )
            cases.append({"case_id": f"PUB-{n:03d}", "synthetic": True,
                          "category": category, "request": request, "contract_rule": rule,
                          "reference_ir": reference, "targeted_mutation": mutation,
                          "expected_entity_ids": expected_ids,
                          "mutation_expected": "rejected_or_denotation_changed"})
    assert len(cases) == 150
    return cases


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    dump(ROOT / "data" / "entities.json", entities())
    dump(ROOT / "data" / "cases.json", make_cases())
    print("generated 32 entities and 150 cases")
