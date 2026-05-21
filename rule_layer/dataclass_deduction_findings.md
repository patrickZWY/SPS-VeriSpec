# Generic Dataclass Deduction Run

This file describes the deduction layer that runs after dataclass schema and
dataclass effect modeling.

The goal is to surface hidden relationships rather than only emit raw facts.
This is the point where Souffle starts being used for actual deduction:
transitive relationships, topology, latent field influence, and schema/effect
blind spots.

## Souffle program

The generic program is `rule_layer/dataclass_deduction_model.dl`.

## How to run it

```bash
python3 tools/python_to_souffle.py CutePetsBoston --souffle-facts-dir /tmp/cutepets-facts
mkdir -p /tmp/cutepets-deduction-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-deduction-out \
  rule_layer/dataclass_deduction_model.dl
```

Or run the whole pipeline:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/cutepets-run
```

## What this layer deduces

- direct dataclass transformations
- reachable multi-step dataclass transformations
- entry dataclasses with no incoming transformation edges
- bridge dataclasses with both incoming and outgoing transformation edges
- terminal dataclasses with no outgoing transformation edges
- fields that participate in dataclass transformations
- required fields that never appear in any tracked field-read relation
- dataclasses that participate in call or exception effects

## Example output on CutePetsBoston

Key direct transformations:

- `AdoptablePet -> Post`
- `Post -> PostResult`
- `Post -> PreparedCaption`
- `PreparedCaption -> CaptionThread`
- `AdoptablePet -> PipelineResult`

Key reachable transformations:

- `AdoptablePet => PostResult`
- `AdoptablePet => PreparedCaption`
- `AdoptablePet => CaptionThread`
- `Post => CaptionThread`

Topology deductions:

- bridge dataclasses: `Post`, `PreparedCaption`
- entry dataclass: `AdoptablePet`
- terminal dataclasses: `PostResult`, `CaptionThread`, `PipelineResult`

Field-to-transformation deductions:

- `AdoptablePet.name -> Post`
- `AdoptablePet.breed -> Post`
- `AdoptablePet.description -> Post`
- `Post.text -> PreparedCaption`
- `Post.tags -> PreparedCaption`
- `PreparedCaption.caption_text -> CaptionThread`

Blind-spot deductions:

- unread required fields currently include `PostResult.success`, `PreparedCaption.post`, and several preview/pipeline helper fields

## Why this matters

This is the first layer that starts turning extracted and abstracted facts into
something more like a latent relational model:

- what data types feed other data types
- which dataclasses act as bridges
- which fields appear to matter for transformations
- which required fields are currently invisible to the tracked effect model

## Current limitations

- Transformations are still syntactic and type-name-based.
- Reachability is structural, not proof of runtime execution paths.
- Unread required fields may reflect real blind spots or simply limitations of the current field-access extraction.
