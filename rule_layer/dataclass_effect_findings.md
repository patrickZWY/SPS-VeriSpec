# Generic Dataclass Effect Modeling Run

This file describes the generic Souffle workflow that associates dataclasses
with effects in surrounding functions and methods.

The purpose is still abstraction, not whole-program translation. The model
starts from all discovered dataclasses, then links them to effects through
typed function signatures, constructor sites, field access, and exception or
call behavior.

## Souffle program

The generic program is `rule_layer/dataclass_effect_model.dl`.

It uses Souffle record types:

- `FunctionLink`
- `EffectEvent`
- `FieldEvent`

## How to run it

```bash
python3 tools/python_to_souffle.py <python-project-dir> --souffle-facts-dir /tmp/project-facts
mkdir -p /tmp/project-effect-out
souffle -F /tmp/project-facts -D /tmp/project-effect-out \
  rule_layer/dataclass_effect_model.dl
```

Useful output files:

- `/tmp/project-effect-out/dataclass_function.csv`
- `/tmp/project-effect-out/dataclass_field_effect.csv`
- `/tmp/project-effect-out/dataclass_effect.csv`
- `/tmp/project-effect-out/dataclass_transformation.csv`
- `/tmp/project-effect-out/function_call_edge.csv`
- `/tmp/project-effect-out/reachable_function_call.csv`
- `/tmp/project-effect-out/interprocedural_dataclass_function.csv`
- `/tmp/project-effect-out/interprocedural_dataclass_field_effect.csv`
- `/tmp/project-effect-out/interprocedural_dataclass_effect.csv`

## Example output shape

Example dataclass-to-function links:

- `<DataclassA> <- <function_or_method> [param_type, <parameter_name>]`
- `<DataclassB> <- <function_or_method> [return_type, <DataclassB>]`
- `<DataclassC> <- <function_or_method> [constructor_call, <DataclassC>]`

Example field effects:

- `<DataclassA> / <function_or_method>` reads `<field_name>`
- `<DataclassA> / <function_or_method>` writes `<field_name>`
- `<DataclassB> / <function_or_method>` reads `<field_name>`

Example effect events:

- `<DataclassA> / <function_or_method>` includes call effects such as `<callee_name>`
- `<DataclassA> / <function_or_method>` includes a raised exception effect such as `<ExceptionType>`
- `<DataclassB> / <function_or_method>` includes dataclass construction or return effects

Example dataclass transformations:

- `<DataclassA> -> <DataclassB>` in `<function_or_method>`
- `<DataclassB> -> <DataclassC>` in `<function_or_method>`

## What the outputs mean

- `dataclass_function` links a dataclass to a function through typed parameters, typed returns, constructor returns, or constructor calls.
- `dataclass_field_effect` records field reads and writes when the dataclass is visible through a typed function parameter.
- `dataclass_effect` records generic effects in dataclass-related functions: calls, env reads, exception handling, raises, and dataclass construction or return events.
- `dataclass_transformation` approximates value-shape transitions between dataclasses across functions.
- `function_call_edge` and `reachable_function_call` expose the resolved call
  graph available to later stages.
- `interprocedural_dataclass_function`,
  `interprocedural_dataclass_field_effect`, and
  `interprocedural_dataclass_effect` lift dataclass/effect associations across
  reachable calls.

## Current limitations

- Class identity is improved by `resolved_*` facts, but there are still dynamic
  import and generic-type limitations.
- This effect layer records parameter-based field effects; local alias and call-result inference is handled in the deduction and test-target layers.
- `dataclass_effect` currently treats all calls inside a dataclass-related function as associated effects. That is useful for exploration but can over-approximate.
- Function-level association is still syntactic; it does not imply an exact runtime dataflow proof.
- Interprocedural effect reachability is callgraph-based and can over-approximate
  when callbacks, dynamic dispatch, or SDK calls are involved.
