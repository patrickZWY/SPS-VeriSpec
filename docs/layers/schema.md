# Generic Dataclass Modeling Run

This file describes the generic dataclass-first Souffle workflow.

The point of this layer is not to translate the entire Python program. The
point is to build a candidate semantic model from every discoverable dataclass,
then let developers keep or prune the resulting abstractions later.

## Default policy

- Model every dataclass found in the project.
- Do not ask the user to pre-select dataclasses.
- Treat the full dataclass set as a candidate model inventory.
- Push pruning decisions to a later review step.
- Prefer schema and dependency modeling before control-flow or whole-program modeling.

## Souffle program

The generic program is `souffle_static_analysis/dataclass_schema_model.dl`.

It uses Souffle record types:

- `FieldShape`
- `DataclassShape`

This keeps field metadata structured instead of scattering it across many
loosely related predicates.

## How to run it

```bash
python3 tools/python_to_souffle.py <python-project-dir> --souffle-facts-dir /tmp/project-facts
mkdir -p /tmp/project-dataclass-out
souffle -F /tmp/project-facts -D /tmp/project-dataclass-out \
  souffle_static_analysis/dataclass_schema_model.dl
```

Useful output files:

- `/tmp/project-dataclass-out/modeled_dataclass.csv`
- `/tmp/project-dataclass-out/modeled_dataclass_option.csv`
- `/tmp/project-dataclass-out/dataclass_field_shape.csv`
- `/tmp/project-dataclass-out/dataclass_shape.csv`
- `/tmp/project-dataclass-out/dataclass_dependency.csv`
- `/tmp/project-dataclass-out/reachable_dataclass_dependency.csv`

## Example output shape

Current discovered dataclasses are emitted as module/class pairs:

- `<module_a>.<DataclassA>`
- `<module_a>.<DataclassB>`
- `<module_b>.<DataclassC>`

Example `dataclass_shape` rows:

- `<module_a>.<DataclassA> -> [field_count, required_count, optional_count, defaulted_count, factory_count, frozen]`
- `<module_a>.<DataclassB> -> [field_count, required_count, optional_count, defaulted_count, factory_count, frozen]`

Interpreting that record:

- `field_count`
- `required_count`
- `optional_count`
- `defaulted_count`
- `factory_count`
- `frozen`

Example dependencies:

- `<module_a>.<DataclassA>.<field_name> -> <DataclassB>`
- `<module_b>.<DataclassC>.<field_name> -> <DataclassA>`

Example factory-backed fields:

- `<module_a>.<DataclassA>.<field_name> -> list`
- `<module_b>.<DataclassC>.<field_name> -> dict`

## What the outputs mean

- `modeled_dataclass` is the complete discovered dataclass inventory.
- `modeled_dataclass_option` records the standard `@dataclass` option surface,
  including whether each option was explicit or inherited from the dataclass
  default: `init`, `repr`, `eq`, `order`, `unsafe_hash`, `frozen`,
  `match_args`, `kw_only`, `slots`, and `weakref_slot`.
- `dataclass_field_shape` packages field-level metadata into a Souffle record.
- `required_field`, `optional_field`, `defaulted_field`, and `factory_backed_field` support later invariant generation.
- `dataclass_dependency` approximates schema-level links between dataclasses through field type references.
- `reachable_dataclass_dependency` composes schema dependencies transitively.
- `dataclass_shape` gives a compact summary per dataclass: field count, required count, optional count, defaulted count, factory-backed field count, and frozen status.

## Why this is the right abstraction level

- It generalizes across Python projects much better than project-specific behavior rules.
- It captures domain structure instead of incidental implementation details.
- It gives the LLM a concrete inventory to summarize, merge, or prune later.
- It uses Souffle for structured relational modeling, not for a premature whole-program encoding.

## Current limitations

- Type references are syntactic and not fully resolved across imports.
- Dataclass dependencies are name-based, so collisions between unrelated classes with the same name are possible.
- This layer models declared schema, not runtime invariants or control flow.
- Method construction, transformation, validation candidates, semantic field flow, literal values, and numeric boundaries are modeled by later effect, deduction, test-target, and semantic layers rather than this schema-only layer.
