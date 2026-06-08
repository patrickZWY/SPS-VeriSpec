# Type-checker case study

This case study is **self-contained** and lives in its own directory with its
own documentation. It is a separate progressive, test-validated composition
experiment: rather than analyzing Python dataclasses, it grows expressions for a
Hindley-Milner type checker from elementary forms and uses a cheap test (the type
checker itself) plus a Datalog policy to find composition bugs. Composing simpler
expressions exposed real type-checker bugs that the hand-written tests missed,
found reference-free via metamorphic relations.

Canonical documentation (kept in place because the code, tests, and reports all
live alongside it):

- [`type_checker_case_study/README.md`](../../type_checker_case_study/README.md) — overview, layout, how to run, and what the current run shows.
- [`type_checker_case_study/metamorphic-oracle-plan.md`](../../type_checker_case_study/metamorphic-oracle-plan.md) — the full metamorphic-oracle plan.
- [`type_checker_case_study/METAMORPHIC_FINDINGS.md`](../../type_checker_case_study/METAMORPHIC_FINDINGS.md) — the bugs the metamorphic phase found.
- [`type_checker_case_study/metamorphic-related-work.md`](../../type_checker_case_study/metamorphic-related-work.md) — related-work scan behind the added relations.
