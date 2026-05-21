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

The generic program is `rule_layer/dataclass_schema_model.dl`.

It uses Souffle record types:

- `FieldShape`
- `DataclassShape`

This keeps field metadata structured instead of scattering it across many
loosely related predicates.

## How to run it

```bash
python3 tools/python_to_souffle.py CutePetsBoston --souffle-facts-dir /tmp/cutepets-facts
mkdir -p /tmp/cutepets-dataclass-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-dataclass-out \
  rule_layer/dataclass_schema_model.dl
```

Useful output files:

- `/tmp/cutepets-dataclass-out/modeled_dataclass.csv`
- `/tmp/cutepets-dataclass-out/dataclass_field_shape.csv`
- `/tmp/cutepets-dataclass-out/dataclass_shape.csv`
- `/tmp/cutepets-dataclass-out/dataclass_dependency.csv`

## Example output on CutePetsBoston

Current discovered dataclasses:

- `abstractions.AdoptablePet`
- `abstractions.Post`
- `abstractions.PostResult`
- `social_posters.mastodon.PreparedCaption`
- `social_posters.mastodon.CaptionThread`
- `utils.pipeline.Phase`
- `utils.pipeline.PipelineResult`
- `utils.pipeline_preview.PreviewSection`

Example `dataclass_shape` rows:

- `abstractions.AdoptablePet -> [11, 4, 6, 7, 0, 0]`
- `abstractions.Post -> [5, 1, 3, 4, 1, 0]`
- `utils.pipeline.PipelineResult -> [3, 0, 1, 2, 2, 0]`

Interpreting that record:

- `field_count`
- `required_count`
- `optional_count`
- `defaulted_count`
- `factory_count`
- `frozen`

Example dependencies:

- `social_posters.mastodon.PreparedCaption.post -> Post`
- `utils.pipeline.PipelineResult.trace -> Phase`

Example factory-backed fields:

- `abstractions.Post.tags -> list`
- `utils.pipeline.PipelineResult.trace -> list`
- `utils.pipeline.PipelineResult.errors -> list`

## What the outputs mean

- `modeled_dataclass` is the complete discovered dataclass inventory.
- `dataclass_field_shape` packages field-level metadata into a Souffle record.
- `required_field`, `optional_field`, `defaulted_field`, and `factory_backed_field` support later invariant generation.
- `dataclass_dependency` approximates schema-level links between dataclasses through field type references.
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
- Methods that construct, transform, or validate dataclasses are not yet connected to the schema layer.
