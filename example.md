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
- method override candidates

3. Run the generic Souffle rule layer.

The current reusable models are:

- `rule_layer/dataclass_schema_model.dl`
- `rule_layer/dataclass_effect_model.dl`
- `rule_layer/dataclass_deduction_model.dl`
- `rule_layer/dataclass_test_model.dl`

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
- Preserve key literal data such as numbers, bounds, limits, and thresholds during fact extraction so generated tests can target boundary values.
- Examine the current Souffle rules for precision, redundancy, performance, and whether their derived relations are actually useful for test generation.
- Generate executable property/fuzz tests directly from the test-target CSV outputs.
- Feed test execution results back into the knowledge base.

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
