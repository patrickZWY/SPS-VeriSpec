# Current workflow

1. Begin with a Python project such as `CutePetsBoston`.

2. Extract Python AST facts with `tools/python_to_souffle.py`.

The extractor now emits facts for:

- modules, imports, classes, inheritance, functions, and methods
- dataclasses, fields, optionality, defaults, factories, and frozen status
- function parameters, return annotations, constructor calls, and exceptions
- field reads/writes, condition field reads, env reads, and call effects
- constructor keyword arguments and return constructor keyword arguments
- local dependencies from dataclass fields through aliases and composed expressions
- field-to-constructor-argument flows
- call-result assignments and local dataclass values
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
- optional fields read in branch conditions
- override contracts for abstract class implementations
- unread required fields after local and call-result read inference
- semantic and composed semantic field flows
- observable required fields and lossy required-field candidates
- literal dataclass field values such as `PostResult.success = False`
- numeric boundary-test candidates from comparisons and slicing

5. Generate tests from derived relationships.

Useful current targets include:

- optional boundary tests such as `AdoptablePet.adoption_url -> Post.link`
- optional image tests such as `AdoptablePet.image_url -> Post.image_url`
- required field mapping tests such as `AdoptablePet.name/breed/species -> Post.alt_text`
- post text/tag tests from `AdoptablePet.breed/species/location`
- Mastodon formatting tests such as `PreparedCaption.caption_text -> CaptionThread.main_caption/replies`
- contract tests for each `SocialPoster.publish(Post) -> PostResult`
- contract tests for each `PetSource.fetch_pets() -> Iterable[AdoptablePet]`

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

6. Validate generated tests by executing them.

7. Surface contradictions and review candidates to users.

Examples:

- a required field that is still unread
- a platform implementation that violates the `SocialPoster` return contract
- an optional field used in a branch without sufficient test coverage
- a suspicious mutable or frozen dataclass design

8. User decides whether to modify the Python program, the Souffle models, or the generated tests.

9. Re-run extraction and update the knowledge base.

# Remaining potential work

- Resolve imports and type identities instead of relying mostly on names.
- Add more precise call-boundary summaries so arbitrary SDK/API return values do not over-approximate semantic influence.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Add CFG/control-dependence facts so validation guards and returned constructors can be linked more precisely.
- Add lightweight alias/points-to facts so local field reads/writes are less name-based.
- Examine the current Souffle rules for precision, redundancy, performance, and whether their derived relations are actually useful for test generation.
- Generate executable property/fuzz tests directly from the test-target CSV outputs.
- Feed test execution results back into the knowledge base.

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
- Interprocedural dataflow summaries: summarize what each function validates,
  sanitizes, parses, formats, publishes, constructs, observes, or drops so
  callers can compose those facts without inlining whole functions.
- Program slicing: derive backward slices from observable outputs such as
  status fields, error fields, exceptions, external calls, logs, and returned
  dataclasses. This can produce focused tests for what actually influences an
  externally visible result.
- Control-dependence analysis: connect branch conditions to guarded effects,
  returned constructors, raised exceptions, and failure paths. This is the
  missing bridge between `condition_reads_attribute` and branch-specific
  semantic obligations.
- Abstract interpretation domains: add small lattices for nullness, emptiness,
  sign/range, string length, collection size, enum-like state, and maybe
  success/failure status. These can produce boundary and invariant candidates.
- Typestate / protocol analysis: infer order-sensitive obligations such as
  authenticate-before-publish, validate-before-use, parse-before-field-access,
  open-before-read/write, and close-after-use.
- Effect and purity summaries: distinguish pure dataclass transformations from
  functions with network, filesystem, environment, clock, randomness, mutation,
  or exception effects.
- Dead-code and dead-data candidates: surface never-constructed dataclasses,
  unread required fields, unobserved result fields, impossible branches,
  unused constructor arguments, and transformations whose outputs are ignored.
- Contract conformance analysis: compare subclasses or implementations of the
  same abstract method for accepted dataclasses, returned dataclasses,
  success/failure shapes, required-field observability, and effect profiles.

# Souffle features to explore

- Stratified negation: useful for review candidates such as unread required fields, missing overrides, untested boundaries, and terminal dataclasses.
- Aggregates: useful for summaries and prioritization, such as counting transformations per dataclass or effects per method.
- Records: useful for packaging structured metadata such as field shapes, dataclass shapes, effect events, and function links.
- Transitive recursion: useful for reachable dataclass transformations, inheritance chains, call-chain reachability, and multi-step dataflow.
- Components: useful for keeping the growing rule layer modular, for example separating schema, class, transform, and test-target rules.
- Functors: useful for limited normalization or classification, but should be used carefully so Souffle does not become string-processing glue.
- Eqrel / equivalence relations: useful for import aliases, type identity resolution, and alias-like relations between names.
- Subsumption or lattice-style reasoning: potentially useful later for ranking candidate severity or merging abstract states.
- Choice: useful for representative examples and compact test-seed selection, but not for core analysis where completeness matters.
- Profile to find optimal order of atoms in the body of a rule.

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
  approximations, and future lattice-style summaries.
- Program slicing and program-dependence graph work motivates future output-
  and status-field slicing. A representative reference is Horwitz, Reps, and
  Binkley's interprocedural slicing line of work, summarized in
  [Interprocedural Slicing Using Dependence Graphs](https://research.cs.wisc.edu/wpis/papers/toplas90.pdf).
- [QuickCheck](https://hackage.haskell.org/package/QuickCheck) and
  [Hypothesis](https://hypothesis.readthedocs.io/) motivate the eventual step
  from derived relations to executable property-based tests.
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
