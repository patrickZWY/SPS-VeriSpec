# Generic Dataclass Deduction Run

This file describes the deduction layer that runs after dataclass schema and
dataclass effect modeling.

The goal is to surface hidden relationships rather than only emit raw facts.
This is the point where Souffle starts being used for actual deduction:
transitive relationships, topology, latent field influence, and schema/effect
blind spots.

For field-level semantic composition, literal constructor values, and numeric
boundary candidates, see the later generic semantic layer in
`rule_layer/semantic_model.dl`.

## Souffle program

The generic program is `rule_layer/dataclass_deduction_model.dl`.

## How to run it

```bash
python3 tools/python_to_souffle.py <python-project-dir> --souffle-facts-dir /tmp/project-facts
mkdir -p /tmp/project-deduction-out
souffle -F /tmp/project-facts -D /tmp/project-deduction-out \
  rule_layer/dataclass_deduction_model.dl
```

Or run the whole pipeline:

```bash
python3 tools/run_souffle_models.py <python-project-dir> --work-dir /tmp/project-run
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
- reachable function-call edges and interprocedural dataclass/function links
- interprocedural field-use and dataclass-transform candidates reached through
  resolved calls

## Example output shape

Key direct transformations:

- `<DataclassA> -> <DataclassB>`
- `<DataclassB> -> <DataclassC>`
- `<DataclassC> -> <DataclassD>`

Key reachable transformations:

- `<DataclassA> => <DataclassC>`
- `<DataclassA> => <DataclassD>`
- `<DataclassB> => <DataclassD>`

Topology deductions:

- bridge dataclasses: dataclasses with both incoming and outgoing transformation edges
- entry dataclasses: dataclasses with outgoing but no incoming transformation edges
- terminal dataclasses: dataclasses with incoming but no outgoing transformation edges

Field-to-transformation deductions:

- `<DataclassA>.<field_name> -> <DataclassB>`
- `<DataclassB>.<field_name> -> <DataclassC>`
- `<DataclassC>.<field_name> -> <DataclassD>`

Blind-spot deductions:

- unread required fields are emitted as `<Dataclass>.<field_name>` candidates for review

Interprocedural deductions:

- `<caller> reaches <callee> for <DataclassA> -> <DataclassB>`
- `<caller> reaches <callee> that reads <Dataclass>.<field_name>`

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
- Semantic flow and boundary-test derivations are handled in `rule_layer/semantic_model.dl`, not this deduction-only layer.
- Interprocedural deductions depend on resolved call targets and are
  conservative around dynamic dispatch, callbacks, and framework calls.
