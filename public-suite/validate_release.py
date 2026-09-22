#!/usr/bin/env python3
"""Release gate: structure, privacy markers, deterministic controls."""
from __future__ import annotations

import json
import hashlib
import re
from collections import Counter
from pathlib import Path

from runner import ROOT, run_suite, validate_ir

EXPECTED = {
    "boolean_negation": 25, "nested_same_object": 25, "numeric_date_ranges": 20,
    "multivalue_all_any": 20, "equality_canonicalization": 15,
    "normalization_aliases": 20, "cross_field_conflicts": 15, "invalid_schema_only": 10,
}
# SHA-256 only: the public validator must not publish the private markers it checks.
PRIVATE_MARKER_HASHES = {
    7: {"3c6b6365e90d178208865f3701d2f8e94b2bbd5713026cf6b9b2b37f75e298c9"},
    9: {
        "ebf279a0867ed4d0a52f2c33916e089e687a4fd3ad45bb9837bb72015d508c4a",
        "a101916003002fc3a6dff0bc993eb4c6ac6716861d17d3efba960eed2eb324d5",
    },
    10: {"c3b5ad4e8deb948ca47bb812b4222970b84979920cd128f9c32305fba65be078"},
    11: {"04ed75b72ace97cd89150c58b5da0761267a8553fc45d32741f9f07153b9b046"},
    12: {"482fd8574ed4c7010b91c271cc1c4dd12ed58608aba397daacdccda82b1f4ec6"},
    14: {"fb14e7fb6bdb41d7baf8448a986628778d6b9d914583e9aaeb22056c19c4ae40"},
    15: {"49d24c8f69612a4b5597d68a1b5cab998473d501dd74adee1f6c43c16865fc09"},
    16: {"a3e9dc699345bbee085537c9404da402890aa998c5c2e9917191f915c3eb16fb"},
}
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?\d[ -]?){10,14}(?!\d)")


def main() -> None:
    entities = json.loads((ROOT / "data/entities.json").read_text())
    cases = json.loads((ROOT / "data/cases.json").read_text())
    assert len(entities) == 32 and len({e["entity_id"] for e in entities}) == 32
    assert len(cases) == 150 and len({c["case_id"] for c in cases}) == 150
    assert Counter(c["category"] for c in cases) == Counter(EXPECTED)
    assert len({c["request"] for c in cases}) == 150
    hard_reference = {json.dumps(c["reference_ir"]["where"], sort_keys=True) for c in cases}
    hard_mutation = {json.dumps(c["targeted_mutation"]["where"], sort_keys=True) for c in cases}
    assert len(hard_reference) == 150
    assert len(hard_mutation) == 150
    pairs = {(json.dumps(c["reference_ir"], sort_keys=True), json.dumps(c["targeted_mutation"], sort_keys=True)) for c in cases}
    assert len(pairs) == 150
    assert all(e.get("synthetic") is True for e in entities)
    assert all(c.get("synthetic") is True for c in cases)
    for case in cases:
        validate_ir(case["reference_ir"])
        assert isinstance(case.get("expected_entity_ids"), list)
        assert case["expected_entity_ids"] == sorted(set(case["expected_entity_ids"]))
        assert set(case["expected_entity_ids"]) <= {e["entity_id"] for e in entities}

    scan_files = [p for p in ROOT.rglob("*") if p.is_file() and ".pyc" not in p.name and "__pycache__" not in p.parts]
    for path in scan_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        for length, forbidden_hashes in PRIVATE_MARKER_HASHES.items():
            observed = {
                hashlib.sha256(lowered[i:i + length].encode()).hexdigest()
                for i in range(max(0, len(lowered) - length + 1))
            }
            assert observed.isdisjoint(forbidden_hashes), f"private marker hash matched in {path}"
        # Machine-generated hexadecimal digests (this validator's hash denylist and
        # the SHA256SUMS manifest) can contain digit runs that resemble phone
        # numbers, so both files are excluded from the text-pattern scan. Their own
        # content is checked structurally and by hash above.
        if path.name not in {"validate_release.py", "SHA256SUMS"}:
            assert not EMAIL.search(text), f"email-like string in {path}"
            assert not PHONE.search(text), f"phone-like string in {path}"

    result = run_suite()
    assert result["positive_controls_passed"] == 150
    assert result["mutations_caught"] == 150
    assert all(18 <= e["age"] <= 100 for e in entities)
    print("release validation passed: 32 synthetic entities, 150 cases, 150 unique requests, "
          "150 unique hard reference trees, 150 unique hard mutation trees, "
          "150 positive controls, 150 mutations caught")


if __name__ == "__main__":
    main()
