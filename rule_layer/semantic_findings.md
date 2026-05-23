# Generic Semantic Modeling Run

This file describes the generic semantic layer implemented in
`rule_layer/semantic_model.dl`.

The goal is to move beyond dataclass shape without becoming project-specific.
The layer derives conservative semantic candidates from value flow, literal
constructor arguments, string construction, numeric bounds, and boundary-level
behavior summaries. These candidates are intended to drive concrete tests and
review, not to prove full runtime correctness.

## Souffle program

The generic program is `rule_layer/semantic_model.dl`.

## How to run it

```bash
python3 tools/python_to_souffle.py <python-project-dir> --souffle-facts-dir /tmp/project-facts
mkdir -p /tmp/project-semantic-out
souffle -F /tmp/project-facts -D /tmp/project-semantic-out \
  rule_layer/semantic_model.dl
```

Or run the whole pipeline:

```bash
python3 tools/run_souffle_models.py <python-project-dir> --work-dir /tmp/project-run
```

## What this layer deduces

- field-level semantic flows between dataclass fields
- composed field-level flows across multiple transformations
- required fields that are observable through string-valued target fields
- required fields that appear lossy in a returned dataclass
- boolean and string literals assigned to dataclass constructor fields
- string-valued fields built through f-strings, joins, format calls, or simple concatenation
- numeric bounds from comparisons and string slicing
- `below`, `at`, and `above` boundary-test candidates
- boundary behavior that associates generic bounds with dataclass inputs,
  primitive string returns, or helper returns
- conflicting inclusive numeric-bound candidates

## Useful outputs

- `/tmp/project-semantic-out/semantic_field_flow.csv`
- `/tmp/project-semantic-out/composed_semantic_field_flow.csv`
- `/tmp/project-semantic-out/observable_required_field.csv`
- `/tmp/project-semantic-out/lossy_required_field_candidate.csv`
- `/tmp/project-semantic-out/dataclass_bool_literal.csv`
- `/tmp/project-semantic-out/dataclass_string_literal.csv`
- `/tmp/project-semantic-out/string_composition_target.csv`
- `/tmp/project-semantic-out/numeric_bound.csv`
- `/tmp/project-semantic-out/boundary_test_candidate.csv`
- `/tmp/project-semantic-out/boundary_behavior.csv`
- `/tmp/project-semantic-out/helper_boundary_behavior.csv`
- `/tmp/project-semantic-out/numeric_bound_conflict_candidate.csv`

## Example output shape

Semantic field flow:

```text
<function_module> <qualified_name> <source_module> <source_class> <source_field> <target_module> <target_class> <target_field> <flow_kind>
```

Composed semantic field flow:

```text
<source_module> <source_class> <source_field> <target_module> <target_class> <target_field>
```

Boundary-test candidate:

```text
<function_module> <qualified_name> <expression> <case_kind> <test_value>
```

For a comparison like `len(text) > 500`, the current model can emit boundary
candidates around `499`, `500`, and `501`.

Boundary behavior:

```text
<function_module> <class_name> <qualified_name> <expression> <bound_kind> <bound_value> <input_module> <input_class> <input_field> <output_module> <output_class> <output_field> <behavior_kind>
```

Helper boundary behavior:

```text
<function_module> <class_name> <qualified_name> <expression> <bound_kind> <bound_value> <input_param> <output_kind> <behavior_kind>
```

These relations encode the platform/helper level above raw numeric boundaries:
for example, a local caption slice can become `Post.text -> str.<return>` with
`max_length`, while a private cleanup helper can become `description -> return`
with `truncate_or_include`.

## Why this matters

The earlier layers can say that one dataclass transforms into another. The
semantic layer can say which required input fields are observable, which fields
appear dropped, which status fields are set with explicit literals, and which
numeric boundaries deserve tests. The boundary-behavior relations add one more
level: they associate a generic bound with the input and output surface that a
test should exercise.

That gives a better bridge from analysis to executable tests:

- vary required fields that should be observable in output text
- generate boundary values for length and truncation checks
- select stronger platform-specific boundary tests from behavior summaries
- test success/failure result constructors from observed boolean literals
- review lossy required-field candidates before deciding whether they are bugs

## Current limitations

- The analysis is syntactic and conservative.
- Field identity is still partly name-based.
- Branch-local semantics are not modeled yet, so a literal constructor value is
  not necessarily tied to a specific condition.
- Numeric reasoning currently tracks direct integer literals and simple local
  integer assignments, not arbitrary arithmetic.
- String semantics detect construction style and field influence, not exact
  rendered string content.
- Call-boundary influence is intentionally conservative and can over-approximate.
- Boundary behavior is a summary layer over syntactic facts; it is intentionally
  narrow and currently handles direct/local dataclass string caps and simple
  helper-return truncation.
