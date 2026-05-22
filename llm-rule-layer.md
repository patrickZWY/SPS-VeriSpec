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

- Genericity across Python projects.
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
- `instantiates(Module, CallerQualifiedName, ClassName, LineNumber)`
- `reads_env_var(Module, CallerQualifiedName, EnvVarName, LineNumber)`
- `constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `return_constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `field_flows_to_constructor_arg(Module, QualifiedName, SourceParam, SourceField, ConstructedClass, ArgName, LineNumber)`
- `condition_reads_attribute(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `returns_none(Module, QualifiedName, LineNumber)`
- `returns_literal(Module, QualifiedName, LiteralKind, LiteralValue, LineNumber)`
- `method_override(Module, ClassName, BaseName, MethodName, QualifiedName)`
- `local_depends_on_field(Module, QualifiedName, LocalName, SourceParam, SourceField, LineNumber)`
- `call_result_assigned(Module, QualifiedName, LocalName, CalleeName, LineNumber)`
- `local_dataclass_value(Module, QualifiedName, LocalName, ClassName, LineNumber)`

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
- instantiates(Module, CallerQualifiedName, ClassName, LineNumber)
- reads_env_var(Module, CallerQualifiedName, EnvVarName, LineNumber)
- constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)
- return_constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)
- field_flows_to_constructor_arg(Module, QualifiedName, SourceParam, SourceField, ConstructedClass, ArgName, LineNumber)
- condition_reads_attribute(Module, QualifiedName, OwnerName, AttributeName, LineNumber)
- returns_none(Module, QualifiedName, LineNumber)
- returns_literal(Module, QualifiedName, LiteralKind, LiteralValue, LineNumber)
- method_override(Module, ClassName, BaseName, MethodName, QualifiedName)
- local_depends_on_field(Module, QualifiedName, LocalName, SourceParam, SourceField, LineNumber)
- call_result_assigned(Module, QualifiedName, LocalName, CalleeName, LineNumber)
- local_dataclass_value(Module, QualifiedName, LocalName, ClassName, LineNumber)

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
- summarizes dataclasses without pretending to know runtime semantics

## Review checklist

Use this checklist before accepting an LLM-generated model:

- Does it model all discovered dataclasses by default?
- Is the output valid Souffle syntax with `.decl` and `.output` lines?
- Does it use structured Souffle types when the data is naturally structured?
- Are the rules generic across Python projects?
- Does it avoid claiming behavioral guarantees from schema-only facts?
- Does it clearly separate current schema facts from future desired facts?

## Minimum next-step extractor upgrades

The current extractor already supports schema facts, typed function signatures,
constructor returns, constructor keyword arguments, direct and local-derived
field-to-constructor argument flow, field access, condition field reads, literal
returns, call-result assignment, local dataclass values, method override
candidates, and basic exception facts.

The next useful upgrades after this are:

- `reads_dataclass_field(Module, QualifiedName, ClassName, FieldName, LineNumber)` with resolved class identity instead of parameter-name joining
- `writes_dataclass_field(Module, QualifiedName, ClassName, FieldName, LineNumber)` with resolved class identity
- `calls_resolved(Module, QualifiedName, TargetModule, TargetQualifiedName, LineNumber)`
- `writes_env_var(Module, QualifiedName, EnvVarName, LineNumber)`
- `file_effect(Module, QualifiedName, EffectKind, PathHint, LineNumber)`
- `resolved_extends(Module, ClassName, BaseModule, BaseName)`
- `resolved_param_type_ref(Module, QualifiedName, ParamName, TypeModule, TypeName)`
- `resolved_return_type_ref(Module, QualifiedName, TypeModule, TypeName)`

The default should remain:
model all dataclasses first, then connect code behavior to that schema only when needed.
