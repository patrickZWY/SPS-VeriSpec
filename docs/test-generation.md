# Dataclass Test Generation Layer

This file describes the test-target and semantic modeling layers after the
dataclass schema/effect/dataflow rules.

The current rules can answer questions like:

- Which dataclasses exist?
- Which fields are required, optional, defaulted, or factory-backed?
- Which functions connect `DataclassA -> DataclassB`?
- Which fields are read in a transformation?

That is useful, but it is not enough for generating tests that expose bad
dataclass design or behavior bugs. Test generation needs stronger semantic
candidates: mutability risks, constructor boundary conditions, class/dataclass
roles, method-level transformation behavior, and field-level influence.
The current implementation now also derives conservative semantic candidates
from composed field flow, literal constructor values, string composition, and
numeric bounds.
It also derives an interprocedural dataflow layer: resolved call targets,
call-parameter bindings, per-function input-to-output field summaries,
callsite-aware local field flow, recursive composition across dataclass
boundaries, and observable output slices that can drive one-layer-higher
generated tests.
On top of that, the semantic layer now emits conservative slicing,
abstract-state, and protocol-order candidates: backward output slices,
external-call field slices, control-dependence slices, nullness/emptiness/string
length/status states, nullable-use-before-guard candidates, and
validate/authenticate-before-publish style typestate obligations.

The extractor is still incomplete relative to Python's full `ast` grammar, but
it now captures several common surfaces outside direct dataclass transformations:
local aliases, loop/comprehension iteration, assertions, context managers,
await/yield expressions, pattern matching, and subscript access. Future
extractor work should keep prioritizing AST nodes that unlock semantic
obligations or better oracles, rather than adding every syntax node as an
isolated structural fact.

## Current conclusion

The Datalog analysis layer is not the main blocker. It already derives useful
dataclass schema, field, role, call, and semantic relations. The failure in the
second experiment was that the first executable generator was too narrow: it
mostly emitted CutePetsBoston-shaped formatter tests for public `format*`
methods with simple string/list observations.

The generator now needs two tiers:

- generic dataclass oracles that should work for most dataclass-heavy Python
  projects
- project-pattern oracles that are emitted only when the static relation has a
  strong runtime fixture and assertion template

The generic tier currently includes runtime schema checks, constructor/default
checks, default-factory checks, and conversion-profile checks for common
dataclass loader/converter APIs. This tier is what made the dacite experiment
produce executable non-CutePetsBoston tests and what made a bounded
Transformers dataclass slice executable once runtime dependencies were
installed.

## Goal

Produce derived facts that can become test targets.

Examples:

- A mutable dataclass is passed through many platform publishers.
- A required field is never read after construction.
- An optional field is read before a guard.
- A frozen dataclass contains a mutable field such as `list`.
- A dataclass option implies behavior that should be tested: `kw_only=True`
  changes constructor call shape, `order=True` creates ordering methods,
  `eq=False` removes value equality, `unsafe_hash=True` creates hashing risks,
  `match_args=False` affects pattern matching, and `slots=True` changes
  attribute layout.
- A class method transforms one dataclass into another while reading only a
  subset of required fields.
- A subclass overrides a method that transforms the same input dataclass into a
  different output dataclass.
- A required input field is observable in a string-valued output field.
- A required input field appears lossy in a transformation.
- A status/result dataclass is constructed with explicit boolean literals.
- A comparison or slice bound implies boundary cases such as `bound - 1`,
  `bound`, and `bound + 1`.
- A loop or comprehension iterates over a dataclass collection field.
- An assertion or pattern-match guard reads a dataclass field.
- An async function awaits an external result that may need status/error tests.
- A generator yields values derived from a dataclass field.

## Current facts already useful for this

The extractor already emits enough facts for a first version:

- `defines_class(Module, ClassName)`
- `extends(Module, ClassName, BaseName)`
- `dataclass(Module, ClassName, IsFrozen, LineNumber)`
- `dataclass_option(Module, ClassName, OptionName, OptionValue, IsExplicit)`
- `dataclass_field(Module, ClassName, FieldName, TypeRepr, IsOptional, HasDefault, DefaultKind, Position, LineNumber)`
- `dataclass_field_default_factory(Module, ClassName, FieldName, FactoryName)`
- `dataclass_field_type_ref(Module, ClassName, FieldName, TypeRef)`
- `method_of_class(Module, ClassName, QualifiedName)`
- `function_param_type_ref(Module, QualifiedName, ParamName, TypeRef)`
- `function_return_type_ref(Module, QualifiedName, TypeRef)`
- `returns_dataclass(Module, QualifiedName, ClassName, LineNumber)`
- `attribute_read(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `attribute_write(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `local_alias(Module, QualifiedName, LocalName, TargetName, LineNumber)`
- `loop_iterates(Module, QualifiedName, TargetName, IterExpr, LineNumber)`
- `comprehension_iterates(Module, QualifiedName, TargetName, IterExpr, LineNumber)`
- `assertion(Module, QualifiedName, TestExpr, LineNumber)`
- `with_resource(Module, QualifiedName, ContextExpr, OptionalName, LineNumber)`
- `await_expr(Module, QualifiedName, AwaitedExpr, LineNumber)`
- `yield_value(Module, QualifiedName, ValueExpr, LineNumber)`
- `match_subject(Module, QualifiedName, SubjectExpr, LineNumber)`
- `match_case(Module, QualifiedName, PatternKind, GuardExpr, LineNumber)`
- `subscript_access(Module, QualifiedName, OwnerExpr, IndexKind, LineNumber)`
- `calls(Module, QualifiedName, CalleeName, LineNumber)`
- `instantiates(Module, QualifiedName, ClassName, LineNumber)`
- `function_name(Module, QualifiedName, Name)`
- `literal_assigned(Module, QualifiedName, LocalName, LiteralKind, LiteralValue, LineNumber)`
- `constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)`
- `return_constructor_arg_literal(Module, QualifiedName, ConstructedClass, ArgName, LiteralKind, LiteralValue, LineNumber)`
- `constructor_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)`
- `return_arg_string_composition(Module, QualifiedName, ConstructedClass, ArgName, CompositionKind, LineNumber)`
- `numeric_assignment(Module, QualifiedName, LocalName, Value, LineNumber)`
- `len_call(Module, QualifiedName, Expression, LineNumber)`
- `numeric_compare(Module, QualifiedName, Expression, Op, Value, LineNumber)`
- `string_slice_upper_bound(Module, QualifiedName, Expression, UpperBound, LineNumber)`

## Derived dataclass design facts

These are schema-level facts that can become test heuristics.

```souffle
.decl mutable_dataclass(module_name:symbol, class_name:symbol)
.decl frozen_dataclass(module_name:symbol, class_name:symbol)
.decl optional_dataclass_field(module_name:symbol, class_name:symbol, field_name:symbol)
.decl required_dataclass_field(module_name:symbol, class_name:symbol, field_name:symbol)
.decl mutable_default_factory_field(module_name:symbol, class_name:symbol, field_name:symbol, factory_name:symbol)
.decl frozen_contains_mutable_field(module_name:symbol, class_name:symbol, field_name:symbol, factory_name:symbol)

mutable_dataclass(M, C) :- dataclass(M, C, 0, _).
frozen_dataclass(M, C) :- dataclass(M, C, 1, _).

optional_dataclass_field(M, C, F) :-
  dataclass_field(M, C, F, _, 1, _, _, _, _).

required_dataclass_field(M, C, F) :-
  dataclass_field(M, C, F, _, 0, 0, _, _, _).

mutable_default_factory_field(M, C, F, Factory) :-
  dataclass_field_default_factory(M, C, F, Factory),
  (Factory = "list"; Factory = "dict"; Factory = "set").

frozen_contains_mutable_field(M, C, F, Factory) :-
  frozen_dataclass(M, C),
  mutable_default_factory_field(M, C, F, Factory).
```

Test targets:

- For `mutable_dataclass`, generate mutation/aliasing tests around methods that pass the value through.
- For `frozen_contains_mutable_field`, test whether nested mutable state can still be mutated despite `frozen=True`.
- For optional fields, generate `None` boundary tests for every method that reads the field.

## Portable generated-test layout

Generated tests should live outside the analyzed target project. The analyzer
may run against a local checkout that is not committed to this repository, so
generated output belongs under a repo-owned directory:

```text
generated_tests/<project-name>/test_generated_dataclass_properties.py
generated_tests/<project-name>/test_generated_dataclass_hypothesis.py
generated_tests/<project-name>/test_generated_dataclass_schema.py
generated_tests/<project-name>/test_generated_dataclass_conversions.py
generated_tests/<project-name>/test_generated_helper_boundaries.py
generated_tests/<project-name>/test_generated_common_ast_properties.py
generated_tests/<project-name>/test_generated_interprocedural_properties.py
generated_tests/<project-name>/README.md
```

Users run those tests by putting their own target checkout on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/target-project pytest generated_tests/<project-name>
```

The first implemented generator is:

```bash
python3 tools/generate_pytest_from_properties.py \
  --analysis-dir /tmp/sps-analysis-run \
  --output-dir generated_tests \
  --project-name cutepetsboston
```

If analysis is run on an inner package directory but validation uses the parent
source root on `PYTHONPATH`, pass `--import-prefix <top_level_package>` so the
generated imports remain executable.

It reads the `facts/`, `test_out/`, and `semantic_out/` directories produced by
`tools/run_static_analysis.py --engine souffle`. It currently emits a
conservative executable subset:

- runtime dataclass schema and constructor/default behavior tests for
  discovered dataclasses
- runtime skips for static dataclass facts that resolve to a non-dataclass
  implementation under the installed optional dependency set
- conversion-profile tests for dataclass loader/converter APIs named
  `from_dict`, `structure`, `to_dict`, `asdict`, or `unstructure`
- public `format*` methods that transform one dataclass into another
- required field mappings with string/list observability assertions
- optional field passthrough mappings with exact `None`, empty-string, and
  non-empty value checks
- helper boundary tests for simple string-length helper methods
- common-AST collection-iteration tests when the iterated value is observable
- interprocedural observable-slice tests for public method paths with simple
  string-output oracles

It deliberately reports lower-confidence candidates instead of executing them:

- publish methods and other effectful paths
- private helper methods where the user-facing contract is unclear
- branch/control-dependence facts where the condition is known but the
  branch-specific oracle is not yet strong enough
- slicing, nullable-use, abstract-state, and protocol candidates that need
  review or a stronger harness before becoming executable tests
- lossy required-field candidates
- non-string/list target fields without a reliable assertion template

This split is important: the generated test file should be useful immediately,
while the generated README keeps the rest of the property inventory visible for
review and future oracle work.

Validation must run in a target environment with dependencies installed. Missing
dependencies can make good generated tests appear non-executable. For example,
the bounded Transformers dataclass slice skipped most model-output tests until
`torch` was installed; after dependency installation it validated with
`99 passed, 7 skipped`. Install those target dependencies in a disposable
validation venv, not in the main SPS-VeriSpec `.venv`, and delete the disposable
venv after validation/evaluation is recorded.

## Class/dataclass role facts

Classes should be related to dataclasses by role, not only by raw type edges.

```souffle
.decl class_method_uses_dataclass(
  class_module:symbol,
  class_name:symbol,
  qualified_name:symbol,
  dataclass_module:symbol,
  dataclass_name:symbol,
  role:symbol
)

class_method_uses_dataclass(CM, Class, Q, DM, D, "accepts") :-
  method_of_class(CM, Class, Q),
  function_param_type_ref(CM, Q, _, D),
  dataclass(DM, D, _, _).

class_method_uses_dataclass(CM, Class, Q, DM, D, "returns") :-
  method_of_class(CM, Class, Q),
  function_return_type_ref(CM, Q, D),
  dataclass(DM, D, _, _).

class_method_uses_dataclass(CM, Class, Q, DM, D, "constructs") :-
  method_of_class(CM, Class, Q),
  instantiates(CM, Q, D, _),
  dataclass(DM, D, _, _).
```

This lets us classify project classes:

- source classes produce domain dataclasses
- formatter classes transform domain dataclasses
- poster classes consume `Post` and return `PostResult`
- preview/debug classes consume intermediate dataclasses

Test targets:

- For every class role `accepts + returns`, generate round-trip or transformation tests.
- For every class role `accepts + constructs`, generate constructor-boundary tests.
- For every subclass that implements the same abstract method, generate conformance tests against the base method contract.

## Inheritance and override facts

Inheritance is important because bugs often appear when subclasses violate a
base dataclass contract.

```souffle
.decl class_inherits(module_name:symbol, class_name:symbol, base_name:symbol)
.decl inherited_dataclass_method(
  module_name:symbol,
  class_name:symbol,
  base_name:symbol,
  qualified_name:symbol,
  dataclass_name:symbol,
  role:symbol
)

class_inherits(M, C, Base) :-
  extends(M, C, Base).

inherited_dataclass_method(M, C, Base, Q, D, Role) :-
  class_inherits(M, C, Base),
  class_method_uses_dataclass(_, Base, Q, _, D, Role).
```

The current fact schema does not fully resolve base classes across imports, so
this is name-based. It is still useful for abstract base classes such as
`PetSource` and `SocialPoster`.

Test targets:

- Every `SocialPoster.publish(post: Post) -> PostResult` implementation should be tested with the same `Post` boundary cases.
- Every `PetSource.fetch_pets() -> Iterable[AdoptablePet]` implementation should be tested for required `AdoptablePet` fields.

For the first executable generator, these contract targets remain report-only
unless the method can be exercised without network, filesystem, environment, or
SDK effects. The next step is to generate mocks or harnesses for effectful
contracts, then run those tests as part of a validation stage.

## Method-level transformation facts

A useful test-generation unit is not just `A -> B`. It is:

```text
class method + input dataclass + output dataclass + fields read + fields written/constructed + calls/effects
```

Suggested relation:

```souffle
.decl method_dataclass_transform(
  class_module:symbol,
  class_name:symbol,
  qualified_name:symbol,
  source_module:symbol,
  source_class:symbol,
  target_module:symbol,
  target_class:symbol
)

method_dataclass_transform(CM, Class, Q, SM, Source, TM, Target) :-
  method_of_class(CM, Class, Q),
  function_param_type_ref(CM, Q, _, Source),
  function_return_type_ref(CM, Q, Target),
  dataclass(SM, Source, _, _),
  dataclass(TM, Target, _, _),
  Source != Target.
```

Then add field influence:

```souffle
.decl method_transform_reads_field(
  class_module:symbol,
  class_name:symbol,
  qualified_name:symbol,
  source_class:symbol,
  field_name:symbol,
  target_class:symbol
)

method_transform_reads_field(CM, Class, Q, Source, Field, Target) :-
  method_dataclass_transform(CM, Class, Q, _, Source, _, Target),
  function_param_type_ref(CM, Q, Param, Source),
  attribute_read(CM, Q, Param, Field, _).
```

Test targets:

- For every field read in a transform, generate value-variation tests and assert the output changes or remains stable as expected.
- For required source fields not read in a transform, flag dead/overmodeled fields or missing test coverage.
- For optional source fields read in a transform, generate `None`, empty string/list, and valid-value cases.

## Interaction facts between dataclasses

Dataclasses can interact through more than type-to-type transformation.

Suggested interaction kinds:

- `contains`: a dataclass field refers to another dataclass type.
- `transforms_to`: a function/method accepts one dataclass and returns another.
- `wraps`: a dataclass stores another dataclass as a field.
- `summarizes`: a dataclass output reads a subset of input fields.
- `branches_on`: a method reads an optional/boolean field in a condition.
- `validates`: a method returns an error/result dataclass based on input field checks.
- `publishes`: a method consumes a dataclass and performs network effects.

The first four are implemented in generic form. Initial `validates` and
`publishes` candidates are also available through line-order
control-dependence slices and protocol-event facts, but branch-local return and
CFG/path-sensitive control-dependence are still needed to reduce false
positives.

## Semantic facts now implemented

The generic semantic model is `souffle_static_analysis/semantic_model.dl`.

It emits:

- `semantic_field_flow`: field-level influence from source dataclass fields to target dataclass fields.
- `composed_semantic_field_flow`: transitive field-level influence across multiple transformations.
- `observable_required_field`: required source fields that reach string-valued output fields.
- `lossy_required_field_candidate`: required source fields with no detected flow to a returned dataclass.
- `dataclass_bool_literal` and `dataclass_string_literal`: literal values assigned to dataclass fields through constructors.
- `string_composition_target`: dataclass fields constructed with f-strings, joins, format calls, or simple concatenation.
- `numeric_bound`: numeric comparison and slice bounds.
- `boundary_test_candidate`: `below`, `at`, and `above` test values for each bound.
- `boundary_behavior`: dataclass-input to output-surface behavior for bounds,
  such as primitive string return max-length behavior.
- `helper_boundary_behavior`: helper input-parameter to return behavior for
  simple private helper truncation/length boundaries.
- `numeric_bound_conflict_candidate`: inconsistent inclusive lower/upper-bound candidates.
- `call_parameter_binding`: resolved caller argument to callee parameter bindings.
- `interprocedural_local_field_flow`: field influence through assigned call results.
- `interprocedural_method_transform`: method-level source/target dataclass transforms inferred from summaries.
- `backward_output_slice` and `function_backward_slice`: reverse views from outputs to source fields.
- `external_call_field_slice`: source dataclass fields that influence call arguments.
- `control_dependence_slice`: condition atoms that guard returned dataclasses, exceptions, or protocol events by line order.
- `abstract_value_state` and `abstract_numeric_state`: small abstract-state candidates for nullness, emptiness, string length, and status literals.
- `nullable_use_before_guard_candidate`: optional field reads without an obvious prior guard or validation event.
- `typestate_transition`, `protocol_obligation_candidate`, and `typestate_protocol_violation`: event-order candidates for workflows such as validate/authenticate-before-publish and open-before-close.

These relations are intentionally conservative. They are meant to generate
candidate properties and tests, not to prove runtime behavior.

## Extractor support now implemented

The extractor now emits these test-generation facts:

- `constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `return_constructor_kwarg(Module, QualifiedName, ConstructedClass, ArgName, SourceExpr, LineNumber)`
- `field_flows_to_constructor_arg(Module, QualifiedName, SourceParam, SourceField, ConstructedClass, ArgName, LineNumber)`
- `condition_reads_attribute(Module, QualifiedName, OwnerName, AttributeName, LineNumber)`
- `returns_none(Module, QualifiedName, LineNumber)`
- `returns_literal(Module, QualifiedName, LiteralKind, LiteralValue, LineNumber)`
- `function_name(Module, QualifiedName, Name)`
- `method_override(Module, ClassName, BaseName, MethodName, QualifiedName)`
- `local_depends_on_field(Module, QualifiedName, LocalName, SourceParam, SourceField, LineNumber)`
- `call_result_assigned(Module, QualifiedName, LocalName, CalleeName, LineNumber)`
- `call_target(Module, QualifiedName, CalleeName, CalleeModule, CalleeQualifiedName, CallKind, LineNumber)`
- `call_argument(Module, QualifiedName, CalleeName, ArgPosition, ArgName, SourceExpr, LineNumber)`
- `call_protocol_event(Module, QualifiedName, ReceiverExpr, EventKind, CalleeName, LineNumber)`
- `branch_condition(Module, QualifiedName, ConditionExpr, LineNumber)`
- `condition_atom(Module, QualifiedName, AtomExpr, AtomState, LineNumber)`
- `return_call(Module, QualifiedName, CalleeName, LineNumber)`
- `resolved_return_call(Module, QualifiedName, CalleeModule, CalleeQualifiedName, LineNumber)`
- `return_local(Module, QualifiedName, LocalName, LineNumber)`
- `resolved_call_result_assigned(Module, QualifiedName, LocalName, CalleeModule, CalleeQualifiedName, LineNumber)`
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

These are sufficient for a first generic test-target model in
`souffle_static_analysis/dataclass_test_model.dl` and the first semantic model in
`souffle_static_analysis/semantic_model.dl`.

## Remaining extractor upgrades

Useful next upgrades:

- higher-precision call-boundary flow summaries for callbacks, generic containers, and dynamically selected functions
- branch-local return facts that connect a condition to a specific returned constructor
- CFG/control-dependence facts beyond current line-order slices for validation
  and guarded-effect reasoning
- lightweight alias/points-to summaries for local variables and object fields

The most important implemented fact is `field_flows_to_constructor_arg`. It
now includes direct field references and intraprocedural local dependencies, so
it can turn a vague transform edge like:

```text
AdoptablePet -> Post
```

into a testable mapping:

```text
AdoptablePet.image_url -> Post.image_url
AdoptablePet.adoption_url -> Post.link
AdoptablePet.name/breed/species -> Post.alt_text
```

That is the level where generated tests become useful.

## What this enables for CutePetsBoston

The current project would get test targets such as:

- Vary `AdoptablePet.image_url` and assert `Post.image_url` follows it.
- Set `AdoptablePet.adoption_url = None` and assert post text/link behavior is intentional.
- Vary `AdoptablePet.breed` and assert `Post.alt_text` and tag generation behave correctly.
- Run the same `Post` cases through every `SocialPoster.publish` implementation and assert each returns `PostResult`.
- Generate Mastodon-specific tests for `Post.text` and `Post.tags` flowing into `PreparedCaption` and then `CaptionThread`.
- Use inferred local/call-result reads to avoid flagging `PostResult.success` as unread when orchestration code checks publish results.
- Generate boundary tests from numeric bounds such as string length checks and slice truncation.
- Assert result/status literals such as successful and failed `PostResult.success` paths.
- Review lossy required-field candidates where a required input field does not reach the returned dataclass.

## What this enables beyond CutePetsBoston

The generic tier is meant to prevent the generator from depending on
CutePetsBoston naming conventions:

- For `dacite`, the generator emits runtime schema/default tests for
  `dacite.config.Config` and a conversion-profile oracle for `dacite.core.from_dict`.
- For the bounded Transformers slice, the generator emits dataclass
  schema/default tests for model-output, callback, configuration, loading-report,
  tokenizer, and attention-mask dataclasses.
- For optional dependency cases, the generated tests skip runtime shapes that no
  longer match the static fallback. `AddedToken` is the motivating example:
  Transformers defines a fallback dataclass when `tokenizers` is absent, but
  resolves to `tokenizers.AddedToken` when `tokenizers` is installed.

This means Transformers should be treated as a scale/dependency stress target,
not the primary proof target. Small libraries like dacite are better for
regression testing generic dataclass oracle generation because their full
analysis completes quickly and dependency failures are easier to interpret.

## Validation and presentation

After generating tests, the framework can validate them by running pytest
against the user's target checkout and collecting a structured result with
`tools/validate_generated_tests.py`:

- passed generated tests
- assertion failures tied back to their source relation
- dependency/import skips
- unsupported review candidates
- generated-test runtime

The user-facing report should present executable tests separately from review
candidates. A failed generated test is not automatically a program bug: it may
also mean the static property was over-approximate or the assertion oracle was
too strong. The report should preserve that distinction.

## Future testing directions

- Extend Hypothesis/property-based generation beyond the current transform
  properties into dataclass schemas, optional field combinations, numeric
  bounds, string bounds, and contract families.
- Mutation testing is implemented for relation-guided field mappings,
  collection iteration, interprocedural pipeline stages, and solver-adjacent
  boundary changes. Future operators should cover dataclass defaults, branch
  predicates, generated inputs, and richer public boundary behavior.
- Concolic testing with SAT/SMT solvers: execute concrete paths, collect path
  constraints from branch and boundary facts, then solve for inputs that reach
  uncovered or suspicious paths.
- Extend evaluation statistics beyond current source-line coverage,
  relation-to-test yield, coverage deltas, and mutation score: branch coverage,
  dataclass-field coverage, derived-relation coverage, contract-family
  coverage, and oracle-strength reporting.

## Bottom line

The next step should not be more undifferentiated dataflow, and it should not be
more project-shaped formatter tests. It should be turning the new semantic
candidates into stronger generic oracles and reports while preserving enough
structure to generate tests:

```text
class role
+ method transform
+ field optionality/default/frozen metadata
+ field-to-constructor-argument flow
+ inheritance/override contracts
+ semantic field flow
+ literal and numeric bounds
+ interprocedural slices
+ abstract states
+ protocol obligations
= useful test targets
```
