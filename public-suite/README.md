# NL2IR Synthetic Public Contract-Conformance Suite

This release contains exactly 150 deterministic cases and 32 anonymous synthetic entities. It supports external reproduction of contract and lowering mechanisms without publishing a private prompt, private records, tenant identifiers, backend field paths, or evaluation examples. It is a **mechanism-reproduction artifact**, not evidence of cross-domain generalization and not a model leaderboard.

## Frozen dimensions

| Dimension | Cases | Operational definition |
|---|---:|---|
| `boolean_negation` | 25 | Preserves AND/OR/NOT, polarity, compound negation, and at-least-one branch behavior. |
| `nested_same_object` | 25 | Binds company, role, and tenure constraints to one nested object and blocks cross-object matches. |
| `numeric_date_ranges` | 20 | Distinguishes inclusive, strict, equality, numeric, and calendar boundaries. |
| `multivalue_all_any` | 20 | Distinguishes ALL from ANY over a multivalue domain without forcing values into one nested object. |
| `equality_canonicalization` | 15 | Enforces canonical equality values, uniqueness, and deterministic ordering. |
| `normalization_aliases` | 20 | Contrasts canonicalized reference IR with the execution consequence of an unnormalized mutation. |
| `cross_field_conflicts` | 15 | Detects misrouting, contradictory leaves, and values bound to the wrong field. |
| `invalid_schema_only` | 10 | Separates JSON/schema validity from the stricter executable contract. |

## Run

Requires Python 3.10+ and only the standard library.

```bash
python3 generate_suite.py
python3 runner.py
python3 validate_release.py
python3 -m unittest discover -s tests -v
python3 generate_manifest.py
```

`generate_suite.py` freezes explicit `expected_entity_ids` with a generator-side oracle. `runner.py` then checks those IDs through two separately implemented paths: a direct recursive IR-tree evaluator and a tuple-DSL lowerer/interpreter. Every case must satisfy `direct IDs == lowered IDs == frozen expected IDs`. Each case also has one targeted mutation; a mutation passes the negative control only when it is rejected or changes the frozen denotation.

Expected frozen result: `150/150` positive controls and `150/150` mutations caught. The diversity gate separately requires `150` unique requests, `150` unique hard reference trees, `150` unique hard mutation trees, and `150` unique `(reference IR, targeted mutation)` pairs. Variation comes from meaningful public fields, operators, tree forms, boundary values, entity combinations, and mutation mechanisms; no serial-number padding or unrelated optional condition is used.

## Files

- `contract.md`, `schema.json`: minimal public contract and structural schema.
- `data/entities.json`: 32 synthetic records.
- `data/cases.json`: reference IR, frozen expected entity IDs, and targeted mutation for every case.
- `runner.py`: direct and lowered execution paths.
- `validate_release.py`: counts, synthetic markers, privacy strings, and controls.
- `tests/`: deterministic integrity tests.
- `SHA256SUMS`: release manifest, excluding itself.

## License

Released under **CC BY 4.0**. See `LICENSING.md` for the full grant and attribution terms.

## Distribution note

Do not ship `__pycache__/`, `*.pyc`, or `.pytest_cache/`. They are excluded from
`SHA256SUMS` and from version control, but a plain directory copy or zip would carry them.
Run `find . -name __pycache__ -prune -exec rm -rf {} +` before packaging, then run the
`Run` sequence above to regenerate `SHA256SUMS`.
