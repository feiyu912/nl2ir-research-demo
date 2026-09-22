# Provenance

The artifact was generated from a new public-only specification on 2026-09-22. The generator uses fixed loops and contains no randomness. Entities and cases are reproducible byte-for-byte by running `python3 generate_suite.py`.

Design inputs were limited to abstract mechanism names: Boolean structure, nested same-object binding, ranges, multivalue quantification, canonicalization, normalization, cross-field conflicts, and schema validity. No production prompt, Elasticsearch path, private dataset, historical sample, original label, tenant/company record, or user query was used.

The generator freezes explicit expected entity IDs with its own compact oracle. The direct evaluator and lowered tuple-DSL evaluator are separate implementations in one auditable standard-library file. Tests assert that both independently match the frozen IDs and that each targeted mutation is rejected or changes the frozen result.
