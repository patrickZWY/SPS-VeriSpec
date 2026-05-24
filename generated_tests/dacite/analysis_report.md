# Dacite Dataclass Generalization Experiment

## Target

- Target checkout: `dacite/dacite`
- Rationale: small dataclass-centered library with a public `from_dict` API, nested dataclass conversion behavior, and few runtime dependencies.
- Analysis work dir: `/private/tmp/sps-dacite-souffle`

## Analysis Results

- Dataclasses discovered: 1 (`dacite.config.Config`)
- Callgraph-reachable function pairs: 160
- Dataclass-linked functions: 5
- Interprocedural dataclass effects: 312
- Numeric boundary candidates: 3
- Common-AST dataclass collection iterations: 1

## Generated Tests

- Runtime dataclass schema cases: 1
- Constructor/default cases: 1
- Conversion-profile cases: 1 (`dacite.core.from_dict`)
- Legacy CutePetsBoston-style transform cases: 0

The generated conversion test defines local dataclasses and drives `from_dict`
through a nested dictionary fixture. This exercises a dataclass-heavy target
without relying on `format*` method names or CutePetsBoston field names.

## Validation

- Command: `.venv/bin/python tools/validate_generated_tests.py generated_tests/dacite --target-project dacite`
- Result: 3 passed, 5 skipped, 0 failed, 0 errors

## Interpretation

This is a better second target than Transformers for near-term generalization:
the full package analysis completes quickly, imports are lightweight, and the
generated suite now contains executable non-CutePetsBoston oracles. Transformers
should remain a scale/framework stress test, not the primary generalization
proof target.
