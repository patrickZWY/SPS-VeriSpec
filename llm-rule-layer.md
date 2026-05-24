# LLM Souffle Modeling Guide

This file defines how to prompt an LLM during the current phase of the project.

The current phase is not whole-program translation. The current phase is
dataclass-first modeling for arbitrary Python projects.

The LLM should use Python facts extracted by `tools/python_to_souffle.py` and
produce reviewable Souffle models. At this stage, the LLM should prefer schema
abstractions over control-flow encodings.

## Default modeling policy

- Model every discoverable dataclass by default.
- Do not ask the user which dataclasses to include.
- Treat the full set of dataclasses as a candidate model inventory.
- Let the user prune or keep generated models later.
- Prefer dataclass schema modeling before whole-program modeling.
- Escalate to function, call, or control-flow modeling only when the dataclass
  layer is clearly insufficient for the goal.

## What the LLM should optimize for

- Generality across Python projects.
- Explicit Souffle syntax.
- Small composable relations.
- Structured Souffle types such as records when the model has real structure.
- Conservative claims. The LLM should distinguish schema facts from behavioral facts.

## What the LLM should not do

- Do not ask the user to pre-select dataclasses.
- Do not jump directly to whole-program translation unless the task explicitly requires it.
- Do not invent base predicates that the extractor does not emit.
- Do not claim runtime guarantees from schema-only facts.
- Do not flatten structured metadata into many unrelated string predicates when
  a Souffle record type would be clearer.

## Current base fact schema

The extractor currently emits these relevant predicates:

- `module(Module)`
- `module_file(Module, RelativePath)`
- `imports(Module, ImportedSymbol)`
- `defines_class(Module, ClassName)`
- `extends(Module, ClassName, BaseName)`
- `dataclass(Module, ClassName, IsFrozen, LineNumber)`
- `dataclass_field(Module, ClassName, FieldName, TypeRepr, IsOptional, HasDefault, DefaultKind, Position, LineNumber)`
- `dataclass_field_default_factory(Module, ClassName, FieldName, FactoryName)`
- `dataclass_field_type_ref(Module, ClassName, FieldName, TypeRef)`
- `method_of_class(Module, ClassName, QualifiedName)`
- `function_param(Module, QualifiedName, ParamName, TypeRepr, Position, LineNumber)`
- `function_param_type_ref(Module, QualifiedName, ParamName, TypeRef)`
- `function_return_type(Module, QualifiedName, TypeRepr, LineNumber)`
- `function_return_type_ref(Module, QualifiedName, TypeRef)`
- `returns_dataclass(Module, QualifiedName, ClassName, LineNumber)`
- `attribute_read(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `attribute_write(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `handles_exception(Module, QualifiedName, ExceptionType, LineNumber)`
- `raises_exception(Module, QualifiedName, ExceptionType, LineNumber)`
- `defines_function(Module, QualifiedName, Arity)`
- `function_name(Module, QualifiedName, Name)`
- `calls(Module, CallerQualifiedName, CalleeName, LineNumber)`
- `call_target(Module, CallerQualifiedName, CalleeName, CalleeModule, CalleeQualifiedName, CallKind, LineNumber)`
- `call_argument(Module, CallerQualifiedName, CalleeName, ArgPosition, ArgName, SourceExpr, LineNumber)`
- `call_protocol_event(Module, QualifiedName, ReceiverExpr, EventKind, CalleeName, LineNumber)`
- `instantiates(Module, CallerQualifiedName, ClassName, LineNumber)`
- `reads_env_var(Module, CallerQualifiedName, EnvVarName, LineNumber)`
- `constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `return_constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `field_flows_to_constructor_arg(Module, QualifiedName, SourceParam, SourceField, ConstructedClass, ArgName, LineNumber)`
- `condition_reads_attribute(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `branch_condition(Module, QualifiedName, ConditionExpr, LineNumber)`
- `condition_atom(Module, QualifiedName, AtomExpr, AtomState, LineNumber)`
- `returns_none(Module, QualifiedName, LineNumber)`
- `returns_literal(Module, QualifiedName, LiteralKind, LiteralValue, LineNumber)`
- `method_override(Module, ClassName, BaseName, MethodName, QualifiedName)`
- `local_depends_on_field(Module, QualifiedName, LocalName, SourceParam, SourceField, LineNumber)`
- `call_result_assigned(Module, QualifiedName, LocalName, CalleeName, LineNumber)`
- `resolved_call_result_assigned(Module, QualifiedName, LocalName, CalleeModule, CalleeQualifiedName, LineNumber)`
- `return_call(Module, QualifiedName, CalleeName, LineNumber)`
- `resolved_return_call(Module, QualifiedName, CalleeModule, CalleeQualifiedName, LineNumber)`
- `return_local(Module, QualifiedName, LocalName, LineNumber)`
- `local_dataclass_value(Module, QualifiedName, LocalName, ClassName, LineNumber)`
- `literal_assigned(Module, QualifiedName, LocalName, LiteralKind, LiteralValue, LineNumber)`
- `constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)`
- `return_constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)`
- `constructor_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)`
- `return_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)`
- `numeric_literal(Module, QualifiedName, Value, LineNumber)`
- `numeric_assignment(Module, QualifiedName, LocalName, Value, LineNumber)`
- `len_call(Module, QualifiedName, Expression, LineNumber)`
- `numeric_compare(Module, QualifiedName, Expression, Op, Value, LineNumber)`
- `string_slice_upper_bound(Module, QualifiedName, Expression, UpperBound, LineNumber)`

The model should assume:

- `Module` is a dotted Python module path.
- `ClassName` is the class name as declared in source.
- `TypeRepr` is syntactic source-level type text, not a resolved static type.
- `TypeRef` is a syntactic type reference extracted from the annotation AST.
- Base facts are loaded into Souffle from per-relation `.facts` files.

## Recommended LLM workflow

1. Build or refine a Souffle dataclass schema model over all discovered dataclasses.
2. Use Souffle record types to package field metadata and summaries.
3. Derive candidate abstractions such as:
   - required versus optional fields
   - default-backed and factory-backed fields
   - dataclass-to-dataclass dependencies
   - mutable versus frozen dataclass summaries
4. Then connect functions or methods to the dataclass layer through typed parameters, typed returns, constructor sites, field reads/writes, and exception effects.
5. Then use Souffle deduction to surface hidden relations such as reachable transformations, bridge dataclasses, field-to-transformation links, and unread required fields.
6. Then derive test-generation targets from class/dataclass roles, method-level transformations, field-to-constructor-argument flows, optional-field branches, mutability, and override contracts.
7. Then derive semantic candidates from composed field flows, observable required fields, literal constructor values, string composition, numeric bounds, interprocedural summaries, slicing, abstract states, and protocol-order events. Keep these conservative and validate them with generated concrete tests or human review.

## Prompt template for dataclass modeling

```text
You are designing a Souffle model over a fixed fact base extracted from a
Python project. The goal is dataclass-first modeling, not whole-program
translation.

Model every discoverable dataclass by default. Do not ask the user which
dataclasses to include. Users can prune the generated model later.

Work only from the provided predicates. Do not invent new base facts.

Base predicates:
- module(Module)
- module_file(Module, RelativePath)
- imports(Module, ImportedSymbol)
- defines_class(Module, ClassName)
- extends(Module, ClassName, BaseName)
- dataclass(Module, ClassName, IsFrozen, LineNumber)
- dataclass_field(Module, ClassName, FieldName, TypeRepr, IsOptional, HasDefault, DefaultKind, Position, LineNumber)
- dataclass_field_default_factory(Module, ClassName, FieldName, FactoryName)
- dataclass_field_type_ref(Module, ClassName, FieldName, TypeRef)
- method_of_class(Module, ClassName, QualifiedName)
- function_param(Module, QualifiedName, ParamName, TypeRepr, Position, LineNumber)
- function_param_type_ref(Module, QualifiedName, ParamName, TypeRef)
- function_return_type(Module, QualifiedName, TypeRepr, LineNumber)
- function_return_type_ref(Module, QualifiedName, TypeRef)
- returns_dataclass(Module, QualifiedName, ClassName, LineNumber)
- attribute_read(Module, QualifiedName, OwnerName, AttributeName, LineNumber)
- attribute_write(Module, QualifiedName, OwnerName, AttributeName, LineNumber)
- handles_exception(Module, QualifiedName, ExceptionType, LineNumber)
- raises_exception(Module, QualifiedName, ExceptionType, LineNumber)
- defines_function(Module, QualifiedName, Arity)
- function_name(Module, QualifiedName, Name)
- calls(Module, CallerQualifiedName, CalleeName, LineNumber)
- call_target(Module, CallerQualifiedName, CalleeName, CalleeModule, CalleeQualifiedName, CallKind, LineNumber)
- call_argument(Module, CallerQualifiedName, CalleeName, ArgPosition, ArgName, SourceExpr, LineNumber)
- call_protocol_event(Module, QualifiedName, ReceiverExpr, EventKind, CalleeName, LineNumber)
- instantiates(Module, CallerQualifiedName, ClassName, LineNumber)
- reads_env_var(Module, CallerQualifiedName, EnvVarName, LineNumber)
- constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)
- return_constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)
- field_flows_to_constructor_arg(Module, QualifiedName, SourceParam, SourceField, ConstructedClass, ArgName, LineNumber)
- condition_reads_attribute(Module, QualifiedName, OwnerName, AttributeName, LineNumber)
- branch_condition(Module, QualifiedName, ConditionExpr, LineNumber)
- condition_atom(Module, QualifiedName, AtomExpr, AtomState, LineNumber)
- returns_none(Module, QualifiedName, LineNumber)
- returns_literal(Module, QualifiedName, LiteralKind, LiteralValue, LineNumber)
- method_override(Module, ClassName, BaseName, MethodName, QualifiedName)
- local_depends_on_field(Module, QualifiedName, LocalName, SourceParam, SourceField, LineNumber)
- call_result_assigned(Module, QualifiedName, LocalName, CalleeName, LineNumber)
- resolved_call_result_assigned(Module, QualifiedName, LocalName, CalleeModule, CalleeQualifiedName, LineNumber)
- return_call(Module, QualifiedName, CalleeName, LineNumber)
- resolved_return_call(Module, QualifiedName, CalleeModule, CalleeQualifiedName, LineNumber)
- return_local(Module, QualifiedName, LocalName, LineNumber)
- local_dataclass_value(Module, QualifiedName, LocalName, ClassName, LineNumber)
- literal_assigned(Module, QualifiedName, LocalName, LiteralKind, LiteralValue, LineNumber)
- constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)
- return_constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)
- constructor_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)
- return_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)
- numeric_literal(Module, QualifiedName, Value, LineNumber)
- numeric_assignment(Module, QualifiedName, LocalName, Value, LineNumber)
- len_call(Module, QualifiedName, Expression, LineNumber)
- numeric_compare(Module, QualifiedName, Expression, Op, Value, LineNumber)
- string_slice_upper_bound(Module, QualifiedName, Expression, UpperBound, LineNumber)

Task:
[INSERT CONCRETE MODELING GOAL]

Output requirements:
1. Emit valid Souffle syntax.
2. Prefer Souffle record types when packaging field or dataclass metadata.
3. Model all discovered dataclasses unless the task explicitly states otherwise.
4. Declare derived relations with .decl.
5. Add .output declarations for relations worth inspection.
6. Explain what each relation captures.
7. State limitations and likely false positives.
8. If the current fact schema is insufficient, propose the minimum extractor
   additions needed after first giving the best model possible with current facts.

Output format:
- Rules in Souffle syntax.
- Then a short explanation section.
- Then a limitations section.
```

## What a good dataclass-focused answer looks like

A good answer typically does some of the following:

- defines a record like `FieldShape` or `DataclassShape`
- emits a complete dataclass inventory relation
- classifies required, optional, defaulted, and factory-backed fields
- derives schema-level dataclass dependencies from field type references
- connects dataclasses to typed functions and methods
- associates dataclasses with field-access, call, env-read, and exception effects
- identifies dataclass-to-dataclass transformations
- identifies field-to-constructor-argument mappings for concrete test targets
- classifies classes by how their methods accept, return, or construct dataclasses
- surfaces optional-field branches and override contracts
- composes field flows across transformations when the intermediate field identity is known
- distinguishes observable required fields from required fields that appear lossy in a transform
- derives boundary-test candidates from numeric comparisons and slice bounds
- surfaces literal status/result fields such as `success=True` or `success=False`
- derives interprocedural summaries and observable/backward output slices
- surfaces external-call field slices and control-dependence slices
- classifies small abstract states such as nullness, emptiness, string-length
  bounds, and status/result literals
- flags typestate/protocol order candidates such as validate/authenticate before
  publish-like calls
- summarizes dataclasses without pretending to know runtime semantics

## Review checklist

Use this checklist before accepting an LLM-generated model:

- Does it model all discovered dataclasses by default?
- Is the output valid Souffle syntax with `.decl` and `.output` lines?
- Does it use structured Souffle types when the data is naturally structured?
- Are the rules generic across Python projects?
- Does it avoid claiming behavioral guarantees from schema-only facts?
- Does it clearly separate current facts, conservative semantic candidates, and future desired facts?

## Minimum next-step extractor upgrades

The current extractor already supports schema facts, typed function signatures,
constructor returns, constructor keyword arguments, direct and local-derived
field-to-constructor argument flow, field access, condition field reads,
branch-condition atoms, call arguments, resolved call targets, protocol event
classification, return-call sites, literal returns, assigned literals,
constructor argument literals, string-composition markers, numeric literals,
numeric assignments, `len(...)` calls, numeric comparisons, slice upper bounds,
call-result assignment, resolved call-result assignment, local dataclass values,
method override candidates, and basic exception facts.

The next useful upgrades after this are:

- `reads_dataclass_field(Module, QualifiedName, ClassName, FieldName, LineNumber)` with resolved class identity instead of parameter-name joining
- `writes_dataclass_field(Module, QualifiedName, ClassName, FieldName, LineNumber)` with resolved class identity
- `branch_return(Module, QualifiedName, ConditionId, ReturnedClass, LineNumber)` to connect guards to returned constructors
- CFG/control-dependence facts for validation and guarded-effect reasoning beyond
  the current line-order slice candidates
- `writes_env_var(Module, QualifiedName, EnvVarName, LineNumber)`
- `file_effect(Module, QualifiedName, EffectKind, PathHint, LineNumber)`
- more precise alias/points-to summaries for local variables and object fields
- higher-precision protocol event classification for framework-specific APIs

The default should remain:
model all dataclasses first, then connect code behavior to that schema only when needed.
