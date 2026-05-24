# Current workflow

1. Begin with a Python project such as `CutePetsBoston`.

2. Extract Python AST facts with `tools/python_to_souffle.py`.

The extractor now emits facts for:

- modules, imports, classes, inheritance, functions, and methods
- import aliases plus resolved dataclass field, parameter, and return type refs
- dataclasses, fields, optionality, defaults, factories, and dataclass options
  such as `frozen`, `order`, `eq`, `kw_only`, `slots`, and `unsafe_hash`
- function parameters, return annotations, constructor calls, and exceptions
- field reads/writes, condition field reads, env reads, and call effects
- constructor keyword arguments and return constructor keyword arguments
- local dependencies from dataclass fields through aliases and composed expressions
- field-to-constructor-argument flows
- call-result assignments and local dataclass values
- local aliases, loop/comprehension iteration, assertions, context managers,
  await/yield expressions, pattern matches, and subscript access
- literal constructor values, string composition, numeric comparisons, `len(...)`, and slice bounds
- method override candidates

3. Run the generic Souffle rule layer.

The current reusable models are:

- `rule_layer/dataclass_schema_model.dl`
- `rule_layer/dataclass_effect_model.dl`
- `rule_layer/dataclass_deduction_model.dl`
- `rule_layer/dataclass_test_model.dl`
- `rule_layer/semantic_model.dl`

The one-command workflow is:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-analysis-run
```

4. Review derived relationships.

The analyzer now derives:

- discovered dataclass inventory and shape summaries
- direct and reachable dataclass transformations
- class/dataclass roles such as accepts, returns, and constructs
- method-level dataclass transformations
- field-to-transformation relations
- field-to-constructor-argument mappings
- optional and required field test targets
- dataclass option relations such as comparable, ordered, keyword-only,
  slotted, unsafe-hash, mutable, and frozen dataclasses
- optional fields read in branch conditions
- override contracts for abstract class implementations
- unread required fields after local and call-result read inference
- semantic and composed semantic field flows
- function-level dataflow summaries, interprocedural field flows, multi-hop
  interprocedural flows, and observable output slices
- backward output slices, external-call field slices, and control-dependence
  slices
- small abstract-state candidates for nullness, emptiness, string length, and
  success/failure status
- typestate/protocol candidates such as validate/authenticate-before-publish
- alias-normalized attribute reads, dataclass collection iteration, asserted
  dataclass fields, matched dataclass subjects, async obligation candidates, and
  generator output candidates
- observable required fields and lossy required-field candidates
- literal dataclass field values such as `PostResult.success = False`
- numeric boundary-test candidates from comparisons and slicing
- boundary-level behavior summaries that connect generic bounds to platform or
  helper output behavior

5. Generate tests from derived relationships.

Useful generated or review targets include:

- optional boundary tests such as `AdoptablePet.adoption_url -> Post.link`
- optional image tests such as `AdoptablePet.image_url -> Post.image_url`
- required field mapping tests such as `AdoptablePet.name/breed/species -> Post.alt_text`
- post text/tag tests from `AdoptablePet.breed/species/location`
- Mastodon formatting tests such as `PreparedCaption.caption_text -> CaptionThread.main_caption/replies`
- review candidates for `SocialPoster.publish(Post) -> PostResult`
  implementations
- review candidates for `PetSource.fetch_pets() -> Iterable[AdoptablePet]`
  implementations

The current executable generator writes tests into this repository, not into
the analyzed target project. This matters for sample targets such as
`CutePetsBoston`, where users may provide their own local checkout instead of
committing the whole app into this repo.

```bash
python3 tools/generate_pytest_from_properties.py \
  --analysis-dir /tmp/sps-analysis-run \
  --output-dir generated_tests \
  --project-name cutepetsboston
```

Generated output:

```text
generated_tests/cutepetsboston/test_generated_dataclass_properties.py
generated_tests/cutepetsboston/test_generated_dataclass_hypothesis.py
generated_tests/cutepetsboston/test_generated_helper_boundaries.py
generated_tests/cutepetsboston/test_generated_common_ast_properties.py
generated_tests/cutepetsboston/README.md
```

The generated pytest file imports target modules dynamically, so run it with
the target checkout on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/CutePetsBoston pytest generated_tests/cutepetsboston
```

The default generator is intentionally conservative. It emits executable example
tests for public `format*` dataclass transformations with simple string/list
observability or exact optional-field passthrough. It also emits optional
Hypothesis tests for those same supported relations. It emits lower-confidence
helper-boundary tests when a private helper boundary can be driven by a simple
string input. It also emits common-AST tests when a method iterates over a
dataclass collection field and the iterated item is observable in the returned
value. It reports the rest as review candidates, including publish methods,
helper boundaries that need custom input construction, branch-only facts, lossy
required-field candidates, common-AST relations without a strong oracle, and
relations whose assertion oracle is not yet strong enough.

Concrete current output examples:

```text
method_field_to_constructor_arg:
abstractions	SocialPoster	SocialPoster.format_post	AdoptablePet	name	Post	alt_text
```

This says `SocialPoster.format_post` maps `AdoptablePet.name` into
`Post.alt_text`. A generated test can vary `pet.name` and assert the resulting
`Post.alt_text` changes correctly.

```text
transform_optional_field_test_target:
abstractions	SocialPoster	SocialPoster.format_post	AdoptablePet	image_url	Post	image_url
```

This says optional `AdoptablePet.image_url` flows into optional
`Post.image_url`. A generated test can cover `None`, empty string, malformed
URL, and valid URL cases.

```text
transform_required_field_test_target:
abstractions	SocialPoster	SocialPoster.format_post	AdoptablePet	breed	Post	tags
```

This says required `AdoptablePet.breed` influences `Post.tags`. A generated test
can check breed normalization, including spaces, case, and punctuation.

```text
optional_field_read_in_condition:
social_posters.mastodon	PosterMastodon	PosterMastodon._ensure_ready_to_publish	abstractions	Post	image_url
```

This says `PosterMastodon._ensure_ready_to_publish` branches on optional
`Post.image_url`. A generated test can assert that a missing image URL returns a
failure `PostResult` instead of attempting to publish.

```text
inferred_local_dataclass_read:
main	run	abstractions	PostResult	result	success	81
```

This says `main.run` reads `PostResult.success` through local variable
`result`. A generated integration-style test can verify failed publish results
are observed and reported by orchestration code.

```text
override_dataclass_contract:
social_posters.instagram	PosterInstagram	SocialPoster	publish	PosterInstagram.publish	Post	accepts
```

This says `PosterInstagram.publish` overrides the `SocialPoster.publish`
contract and accepts `Post`. A generated conformance test can run the same
`Post` fixtures through every concrete poster implementation.

```text
observable_required_field:
abstractions	SocialPoster.format_post	abstractions	AdoptablePet	name	abstractions	Post	text
```

This says a required input field is visible in a string-valued output field. A
generated property test can vary `AdoptablePet.name` and assert that the
formatted `Post.text` changes or contains the expected value.

```text
boundary_test_candidate:
adoption_sources.rescue_groups	SourceRescueGroups._clean_description	len(text)	at	500
```

This says the analyzer found a numeric boundary around `len(text)`. A generated
test can cover `499`, `500`, and `501` length cases and verify truncation or
validation behavior.

```text
boundary_behavior:
social_posters.instagram	PosterInstagram	PosterInstagram._format_caption	caption	upper_exclusive	2200	abstractions	Post	text	<primitive>	str	<return>	max_length
```

This says a generic `caption < 2200` bound has been lifted to a behavior-level
summary: `Post.text` contributes to a primitive string return with max-length
semantics.

```text
helper_boundary_behavior:
adoption_sources.rescue_groups	SourceRescueGroups	SourceRescueGroups._clean_description	text	upper_exclusive	497	description	return	truncate_or_include
```

This says a private helper boundary can be associated with its public input
parameter and return behavior, instead of staying as an untyped numeric fact.

```text
multi_hop_interprocedural_field_flow:
abstractions	AdoptablePet	name	social_posters.mastodon	CaptionThread	main_caption
```

This says a source field can flow through more than one dataclass transformation
before reaching an observable output field. These multi-hop summaries are the
intended basis for less trivial generated tests that operate one layer above a
single local mapping.

6. Validate generated tests by executing them.

The first validation loop should be mechanical:

- run generated tests against the user's target checkout
- record pass/fail/skip counts
- preserve dependency-related skips separately from assertion failures
- connect failures back to the derived relation that produced the test
- decide whether the failure means a program bug, a weak oracle, or an
  over-approximate static property

This project includes a validation runner that executes the generated pytest
suite against a target checkout and writes a pass/fail/skip report:

```bash
python3 tools/validate_generated_tests.py \
  generated_tests/cutepetsboston \
  --target-project /path/to/CutePetsBoston
```

The generated README records the direct pytest command and separates emitted
executable cases from candidate relations left for review.

7. Measure combined source coverage.

The coverage-statistics runner uses the Python standard-library `trace` module,
so it does not require `coverage.py`. It can run the target project's handwritten
tests and the generated tests together, then report line coverage for target
source files:

```bash
python3 tools/coverage_stats.py \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --report /tmp/sps-coverage-stats.md
```

For the local CutePetsBoston checkout used during development, the combined run
covered `461/911` target source lines (`50.6%`) with `137` pytest cases passing.

8. Measure evaluation yield and coverage deltas.

The evaluation-statistics runner combines inline SVG charts, relation-to-test
yield, and three coverage runs: handwritten tests only, generated tests only,
and both together.

```bash
python3 tools/evaluation_stats.py \
  --analysis-dir /tmp/sps-analysis-run \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --report /tmp/sps-evaluation-stats.md
```

For the local CutePetsBoston checkout used during development:

- Unique transform relations tested: `24/40` (`60.0%`).
- Helper boundary cases emitted: `3/5` (`60.0%`).
- Handwritten target tests covered `427/911` lines (`46.9%`).
- Generated tests covered `260/911` lines (`28.5%`).
- Combined tests covered `461/911` lines (`50.6%`), adding `34` covered lines
  and `3.7` percentage points over handwritten tests.

9. Run mutation evaluation.

The mutation runner creates a temporary copy of the target checkout, applies
small relation-guided transform mutants and solver-adjacent boundary mutants,
then compares handwritten, generated, and combined mutation scores.

```bash
python3 tools/mutation_eval.py \
  --analysis-dir /tmp/sps-analysis-run \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --max-mutants 12 \
  --report /tmp/sps-mutation-eval.md
```

For the local CutePetsBoston checkout used during development:

- Handwritten target tests killed `12/12` mutants (`100.0%`).
- Generated tests killed `5/12` mutants (`41.7%`).
- Combined tests killed `12/12` mutants (`100.0%`).
- Generated tests killed the core transform mutants in `abstractions.py`, but
  most platform-specific boundary mutants survived generated-only testing.

After adding common-AST collection-iteration generated tests and mutation
operators, an expanded local run with `--max-mutants 16` included four
`Post.tags` iteration mutants in Bluesky and Instagram formatting code. The
generated suite killed all four collection-iteration mutants, increasing the
generated-only mutation score for that run to `11/16` (`68.8%`).

10. Surface contradictions and review candidates to users.

Examples:

- a required field that is still unread
- a platform implementation that violates the `SocialPoster` return contract
- an optional field used in a branch without sufficient test coverage
- a suspicious dataclass design, such as mutable, frozen-with-mutable-field,
  ordered, keyword-only, slotted, or unsafe-hash behavior

11. User decides whether to modify the Python program, the Souffle models, or the generated tests.

12. Re-run extraction and update the knowledge base.

When adding a new feature or changing existing behavior, treat evaluation as a
required part of the workflow. Re-run the relevant generated-test validation,
coverage/evaluation statistics, and mutation evaluation commands above, then
record what changed or why a specific evaluation was not applicable. The goal is
to make each feature change visible as an analysis, test-yield, coverage, or
mutation-score delta rather than only as a code diff.

# Remaining potential work

Priority next steps:

- Validate generality on a second project. Every claim of generality currently
  rests on `CutePetsBoston`. Run the full pipeline against at least one other
  Python project (a Flask service, a CLI tool, or any non-trivial codebase),
  record which rules fire, which generated tests survive, and publish the
  delta. This single experiment tells us more about the rule layer than more
  relations on the existing case study.
- Tighten or measure oracle strength in generated tests. The current
  `_assert_observed` helper in
  `generated_tests/cutepetsboston/test_generated_dataclass_properties.py`
  accepts substring match, lowercase-normalized match, comma-prefix
  capitalization, and list-contains. Either replace loose assertions with
  exact equality where the analysis supports it, or report what fraction of
  generated tests have a strict-equality oracle versus a loose one in the
  evaluation report. Passing rate without oracle strength is not evidence.
- Close the informal-to-formal loop by one step. When a generated test fails,
  surface the Datalog relation that produced it and let a human accept,
  reject, or refine that relation. Persist the decision so accepted relations
  feed the next analysis round and rejected ones are demoted. This is the
  minimum feedback path that turns the current one-way `facts -> rules ->
  tests` pipeline into the iterative loop described in `motivation.md`.

- Investigate: are we actually utilizing Datalog's ability to deduce facts
  by repeatedly applying rules? Do the rules we have so far and the facts
  we produce work well to produce new facts or most of them are incompatible.
- Continue the AST coverage audit against Python's standard `ast` grammar.
  Current extraction covers more common surfaces, including local aliases,
  loops/comprehensions, assertions, context managers, async/yield expressions,
  pattern matching, and subscript access. Remaining missing nodes should be
  classified by the semantic relation they could enable, so the project does
  not chase syntax coverage that cannot improve tests.
- Improve relation quality, not just relation quantity. The project should
  avoid treating mostly syntactic or structural facts as the final result; those
  facts are only useful when they compose into semantic, behavioral, or
  cross-cutting relations that can generate compact nontrivial tests.
- Use the full dataclass option surface when deriving relations. `frozen` is
  only one option; `init`, `repr`, `eq`, `order`, `unsafe_hash`, `match_args`,
  `kw_only`, `slots`, and `weakref_slot` can also imply constructor,
  comparison, hashing, pattern-matching, attribute-layout, and API-stability
  test obligations.
- Strengthen property-to-property composition. The current relations between
  properties are relatively weak, so the rule layer cannot yet discover many
  deeper properties from the first layer of Souffle-derived facts.
- Expand executable tests from interprocedural dataflow summaries and
  observable output slices beyond the current simple public string-output cases.
  Optional string outputs, collection outputs, and status dataclasses still need
  stronger oracles.
- Improve import and type-identity resolution beyond the current `resolved_*`
  type-reference facts.
- Add more precise call-boundary summaries so arbitrary SDK/API return values do not over-approximate semantic influence.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Refine CFG/control-dependence facts beyond the current line-order slice
  candidates so validation guards and returned constructors can be linked more
  precisely.
- Extend alias/points-to analysis beyond the current local dependency and
  import-alias facts so object identity is less name-based.
- Expand executable property/fuzz tests beyond the currently supported
  transform relations and simple helper boundaries, especially public boundary
  values, branch conditions, and dataclass combinations.
- Use the new boundary-behavior relations directly in generated tests, so
  platform-specific boundary tests come from `boundary_behavior.csv` instead of
  only raw numeric-bound rows.
- Use common-AST semantic relations directly in generated tests, especially
  asserted fields, pattern-match cases, async result handling, and generator
  output behavior. Dataclass collection iteration has an initial executable
  template when the iterated value is observable in the return value.
- Feed generated-test pass/fail/skip results back into the knowledge base.
- Expand mutation testing beyond the current relation-guided transform and
  solver-adjacent boundary mutants, including generated-input mutation and
  branch-condition mutation.
- Expand abstract-interpretation domains beyond the initial nullness,
  emptiness, string-length, and success/failure candidates, especially
  collection size, sign/range, and enum-like state.
- Expand typestate/protocol analysis beyond the initial event-order candidates,
  especially parse-before-field-access, open-before-read/write, transaction
  begin/commit/rollback, and async resource protocols.
- Add concolic testing experiments that combine concrete execution with
  SAT/SMT solving for branch conditions and numeric/string boundaries.
- Expand evaluation statistics beyond the current relation-yield, line coverage
  deltas, and mutation score: branch coverage, dataclass-field coverage,
  relation coverage, and high-confidence property coverage.

# Potential static-analysis layers

These are generic analyses that should fit the current Souffle workflow. They
should be conservative: use them to propose hidden semantic properties, then
validate those properties with concrete generated tests.

- Points-to / may-alias analysis: infer when locals, attributes, constructor
  results, and call results may refer to the same abstract object. This would
  improve field read/write resolution and reduce name-based joins.
- Taint and information-flow analysis: track data from sources such as env
  vars, user input, files, network responses, and external APIs into sinks such
  as logs, publish calls, database writes, subprocesses, or returned dataclasses.
- Initial implementation: interprocedural dataflow summaries now lift local
  field-flow facts into function summaries, compose those summaries across
  dataclass boundaries, derive observable output slices, and emit executable
  tests for the high-confidence public string-output subset.
- Program slicing: backward output slices, function-local backward slices,
  external-call field slices, and control-dependence slices are implemented as
  review/test-target candidates. Further work should add precise branch-local
  return and exception-value slices.
- Control-dependence analysis: line-order control slices now connect condition
  atoms to nearby returned constructors, raised exceptions, and protocol
  events. Full CFG/path-sensitive control dependence remains future work.
- Abstract interpretation domains: initial nullness, emptiness, string-length,
  and success/failure status candidates are implemented. More precise lattices
  for sign/range, collection size, and enum-like state remain future work.
- Typestate / protocol analysis: initial event-order candidates are implemented
  for validate/authenticate-before-publish and open-before-close. Framework-
  specific protocols and path-sensitive state machines remain future work.
- Effect and purity summaries: distinguish pure dataclass transformations from
  functions with network, filesystem, environment, clock, randomness, mutation,
  or exception effects.
- Dead-code and dead-data candidates: surface never-constructed dataclasses,
  unread required fields, unobserved result fields, impossible branches,
  unused constructor arguments, and transformations whose outputs are ignored.
- Contract conformance analysis: compare subclasses or implementations of the
  same abstract method for accepted dataclasses, returned dataclasses,
  success/failure shapes, required-field observability, and effect profiles.

# Souffle features used or still worth exploring

Already used:

- Records: package field shapes, dataclass shapes, effect events, and function links.
- Aggregates: count fields by required, optional, defaulted, and factory-backed status.
- Stratified negation: surface review candidates such as entry/terminal dataclasses
  and unread required fields.
- Transitive recursion: derive reachable dataclass transformations.
- Arithmetic functors: generate nearby boundary-test candidates from numeric
  comparisons.

Still worth exploring:

- Components: keep the growing rule layer modular, for example separating schema,
  class, transform, and test-target rules.
- Eqrel / equivalence relations: improve import aliases, type identity
  resolution, and alias-like relations between names.
- Subsumption or lattice-style reasoning: rank candidate severity or merge
  abstract states.
- Choice: select representative examples and compact test seeds, but not for
  core analysis where completeness matters.
- Profiling: find better atom order and rule structure as the models grow.

# Related works and references

This project is experimental, but the implementation and direction are informed
by prior tools and analysis traditions:

- [Souffle](https://souffle-lang.github.io/) and its CAV 2016 tool paper,
  [Souffle: On Synthesis of Program Analyzers](https://souffle-lang.github.io/cav-paper),
  are the direct inspiration for expressing static analyses as Datalog rules.
- The Souffle documentation on [input/output execution](https://www.souffle-lang.com/execute)
  is the basis for the `.facts` and `.csv` workflow used by
  `tools/python_to_souffle.py` and `tools/run_souffle_models.py`.
- The official Souffle [examples](https://souffle-lang.github.io/examples)
  are referenced in `motivation.md` as examples of static analysis with
  Datalog, including pointer/alias-style analyses.
- [Doop](https://github.com/plast-lab/doop), a declarative pointer and taint
  analysis framework that targets Souffle, is a useful reference point for
  larger-scale Datalog-based program analysis.
- Reps, Horwitz, and Sagiv's IFDS work on interprocedural finite distributive
  subset problems motivates treating program-analysis questions as graph
  reachability over finite facts. See these notes on
  [interprocedural analysis](https://pages.cs.wisc.edu/~fischer/cs701.f14/6.INTERPROCEDURAL-ANALYSIS.html).
- Cousot and Cousot's
  [abstract interpretation](https://cs.nyu.edu/~pcousot/COUSOTpapers/POPL77.shtml)
  motivates conservative semantic facts such as numeric bounds, string-length
  approximations, the current small abstract-state layer, and future
  lattice-style summaries.
- Program slicing and program-dependence graph work motivates the current
  output, external-call, and control-dependence slices. A representative
  reference is Horwitz, Reps, and
  Binkley's interprocedural slicing line of work, summarized in
  [Interprocedural Slicing Using Dependence Graphs](https://research.cs.wisc.edu/wpis/papers/toplas90.pdf).
- [QuickCheck](https://hackage.haskell.org/package/QuickCheck) and
  [Hypothesis](https://hypothesis.readthedocs.io/) motivate expanding from the
  current transform-focused property tests to richer property-based tests.
- [Alperen Keles](https://alperenkeles.com/) is a useful property-based testing
  reference to review as this project turns derived semantic relations into
  stronger generated tests.
- The Teleport article
  [Using Datalog to Test for Access](https://goteleport.com/blog/testing-access-datalog/)
  is cited in `motivation.md` as an example of using Datalog to answer concrete
  configuration/access questions.
- Michelin's
  [An Introduction to Datalog](https://blogit.michelin.io/an-introduction-to-datalog/)
  is cited in `motivation.md` as a practical data-modeling reference for
  Datalog-style relational thinking.
- Norbert Wojtowicz's talk
  [Domain Modeling With Datalog](https://www.rubyevents.org/talks/domain-modeling-with-datalog)
  is cited in `motivation.md` and is useful background for entity/attribute/value
  modeling, evolving relationships, and Datalog as a domain-modeling tool. The
  direct video link is [YouTube: Domain modeling with Datalog](https://youtu.be/oo-7mN9WXTw).
- [Rosette](https://docs.racket-lang.org/rosette-guide/index.html) is cited in
  `motivation.md` as a nearby solver-aided programming reference point.
- The Cloudflare/Racket/Rosette reference in `motivation.md` corresponds to
  [How Cloudflare Uses Racket and Rosette to Verify DNS Changes](https://racket.discourse.group/t/how-cloudflare-uses-racket-and-rosette-to-verify-dns-changes/3983),
  with the direct video at
  [YouTube: How Cloudflare Uses Racket and Rosette to Verify DNS Changes](https://youtu.be/7Twlh-Opq5E).
- [TLA+](https://lamport.org/tla/tla.html), [Lean](https://lean-lang.org/),
  [Rocq/Coq](https://rocq-prover.org/), and [Dafny](https://dafny.org/) are
  referenced in `motivation.md` as examples of stronger formal-specification
  or proof-oriented tooling. This project is intentionally lighter-weight: it
  tries to infer conservative testable properties from ordinary Python code.
- Dijkstra's observation that testing shows bug presence rather than absence is
  quoted in `motivation.md`; one source traces it to
  [Notes on Structured Programming, EWD249](https://libquotes.com/edsger-w-dijkstra/quote/lbn6u3f).
