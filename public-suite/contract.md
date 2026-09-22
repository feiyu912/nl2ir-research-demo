# Minimal Public NL2IR Contract

This contract is purpose-built for the synthetic suite. It is not the production prompt or schema.

An IR root contains exactly `where`, `optional`, and `unsupported`. `where` is a Boolean tree. `and` and `or` contain at least two children; `not` contains one child. A leaf contains exactly `field`, `op`, and `value`.

Operator support is field-typed. `age`, `graduation_year`, `gap_months`, and `work_years` take integer values with `eq`, `gte`, `lte`, `gt`, or `lt`. `active` takes a Boolean value with `eq`. `city` and `degree` take a string with `eq`. `skills`, `languages`, and `certificates` take either a string with `contains` or a nonempty, unique, lexicographically ordered string array with `all`/`any`. `all` means every listed value is present; `any` means at least one is present.

`company_history` uses `same_object`: company, role, and tenure tests must be satisfied by one history object. Lowering them into independent document-level predicates is contract-invalid because it permits cross-object matches.

Inclusive and strict numeric or calendar boundaries remain distinct. The frozen reference IRs show the canonical value expected after normalization; the runner does not claim to implement a natural-language normalizer. Each value is routed to its declared field. A conjunction containing both `X` and `NOT(X)` is rejected. Unsupported hard conditions cause rejection; they are never silently dropped. Optional preferences do not alter hard-filter denotation.

The suite tests eight operational dimensions listed in the README. It does not claim to cover every possible natural-language interpretation or backend behavior.
