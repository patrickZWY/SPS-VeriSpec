# Python to Souffle Prototype

This repo now includes a Python AST extractor at `tools/python_to_souffle.py`
that supports a Souffle-first workflow.

The important shift is scope:

- the extractor can still emit broad program facts
- but the recommended first modeling layer is every discoverable dataclass
- the goal is a candidate semantic model inventory, not immediate whole-program translation

## Current scope

The extractor emits Souffle-compatible base facts for:

- modules and file paths
- imports
- class definitions and inheritance
- dataclasses
- dataclass fields
- dataclass field default factories
- dataclass field type references
- function and method definitions
- function names split from qualified names
- function calls
- class instantiations
- environment variable reads
- constructor keyword arguments
- direct and local-derived field-to-constructor-argument flows
- local variable dependencies on dataclass fields
- call-result assignments
- local dataclass value assignments
- condition attribute reads
- literal and `None` returns
- syntactic method override candidates

By default it skips `tests/` and `manual_testing/` so the initial model stays
focused on application code.

## Recommended first workflow

1. Extract facts for the target Python project.
2. Model all discovered dataclasses.
3. Let the LLM and the user review that candidate model inventory.
4. Keep or prune abstractions later.
5. Only then connect behavior or control flow if needed.

This is a better first step than attempting a full Souffle translation of an
entire Python program.

## Generate facts

```bash
python3 tools/python_to_souffle.py <python-project> \
  --souffle-facts-dir /tmp/project-facts
```

This writes one `.facts` file per relation.

You can still inspect a human-readable debug view:

```bash
python3 tools/python_to_souffle.py <python-project> --format debug | sed -n '1,20p'
```

## Generic dataclass modeling

The generic dataclass-first Souffle program is:

```bash
mkdir -p /tmp/project-out
souffle -F /tmp/project-facts -D /tmp/project-out \
  rule_layer/dataclass_schema_model.dl
```

This program uses Souffle record types to keep field metadata structured rather
than flattening everything into stringly relations.

Useful outputs:

- `modeled_dataclass.csv`
- `dataclass_field_shape.csv`
- `required_field.csv`
- `optional_field.csv`
- `defaulted_field.csv`
- `factory_backed_field.csv`
- `dataclass_dependency.csv`
- `dataclass_shape.csv`

## Generic dataclass-to-effects modeling

After the schema layer, the next generic program is:

```bash
mkdir -p /tmp/project-effect-out
souffle -F /tmp/project-facts -D /tmp/project-effect-out \
  rule_layer/dataclass_effect_model.dl
```

This program associates dataclasses with surrounding effects through:

- typed parameters
- typed returns
- dataclass constructor sites
- field reads and writes
- calls
- environment reads
- exception handling and raises
- dataclass-to-dataclass transformations

Useful outputs:

- `dataclass_function.csv`
- `dataclass_field_effect.csv`
- `dataclass_effect.csv`
- `dataclass_transformation.csv`

## Generic deduction over surfaced relations

Once schema and effect relations exist, the next generic layer is deduction:

```bash
mkdir -p /tmp/project-deduction-out
souffle -F /tmp/project-facts -D /tmp/project-deduction-out \
  rule_layer/dataclass_deduction_model.dl
```

This layer surfaces higher-level relationships such as:

- direct and reachable dataclass transformations
- entry, bridge, and terminal dataclasses
- field-to-transformation relationships
- unread required fields
- effectful dataclasses

Useful outputs:

- `dataclass_transform.csv`
- `reachable_dataclass_transform.csv`
- `bridge_dataclass.csv`
- `entry_dataclass.csv`
- `terminal_dataclass.csv`
- `field_to_dataclass_transform.csv`
- `unread_required_field.csv`
- `effectful_dataclass.csv`

## Generic dataclass test-target modeling

After schema, effect, and deduction, the next generic layer is test-target
modeling:

```bash
mkdir -p /tmp/project-test-out
souffle -F /tmp/project-facts -D /tmp/project-test-out \
  rule_layer/dataclass_test_model.dl
```

This layer derives relations intended to drive tests and design review:

- mutable versus frozen dataclasses
- optional and required field test targets
- frozen dataclasses that still contain mutable factory-backed fields
- class methods that accept, return, or construct dataclasses
- method-level dataclass transformations
- field-to-constructor-argument mappings
- local dependency mappings through aliases and composed expressions
- optional fields read in branch conditions
- dataclass contracts inherited or overridden by subclasses

Useful outputs:

- `class_method_uses_dataclass.csv`
- `method_dataclass_transform.csv`
- `method_field_to_constructor_arg.csv`
- `transform_optional_field_test_target.csv`
- `transform_required_field_test_target.csv`
- `optional_field_read_in_condition.csv`
- `frozen_contains_mutable_field.csv`
- `override_dataclass_contract.csv`

## One-command runner

There is also a generic runner:

```bash
python3 tools/run_souffle_models.py <python-project> --work-dir /tmp/project-run
```

This executes extraction plus the schema, effect, deduction, and test-target
models, then writes a Markdown summary to:

```text
/tmp/project-run/summary.md
```

## Example on CutePetsBoston

```bash
python3 tools/python_to_souffle.py CutePetsBoston \
  --souffle-facts-dir /tmp/cutepets-facts
mkdir -p /tmp/cutepets-dataclass-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-dataclass-out \
  rule_layer/dataclass_schema_model.dl

mkdir -p /tmp/cutepets-effect-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-effect-out \
  rule_layer/dataclass_effect_model.dl

mkdir -p /tmp/cutepets-deduction-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-deduction-out \
  rule_layer/dataclass_deduction_model.dl

mkdir -p /tmp/cutepets-test-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-test-out \
  rule_layer/dataclass_test_model.dl

python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/cutepets-run
```

## Verification

The extractor has a stdlib-only test module:

```bash
python3 -m unittest prototype_tests.test_python_to_souffle -v
```

You can also validate the current generic models directly with Souffle:

```bash
python3 tools/python_to_souffle.py CutePetsBoston --souffle-facts-dir /tmp/cutepets-facts

mkdir -p /tmp/cutepets-dataclass-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-dataclass-out \
  rule_layer/dataclass_schema_model.dl

mkdir -p /tmp/cutepets-effect-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-effect-out \
  rule_layer/dataclass_effect_model.dl

mkdir -p /tmp/cutepets-deduction-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-deduction-out \
  rule_layer/dataclass_deduction_model.dl

mkdir -p /tmp/cutepets-test-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-test-out \
  rule_layer/dataclass_test_model.dl

python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/cutepets-run
```
