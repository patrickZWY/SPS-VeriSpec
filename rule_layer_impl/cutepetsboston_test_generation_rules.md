# CutePetsBoston Test Generation Rules

This file records project-specific test-generation targets derived from the
generic dataclass test model and the generic semantic model.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-slicing-ai-check
```

## Model layers

The generic model is `rule_layer/dataclass_test_model.dl`.
The semantic model is `rule_layer/semantic_model.dl`.

They derive test-oriented relations from:

- dataclass field metadata
- class/method ownership
- inheritance and method override candidates
- constructor keyword arguments
- direct and local-derived field-to-constructor-argument flows
- local dependencies through aliases and composed expressions
- optional fields read in branch conditions
- literal constructor values
- string composition targets
- numeric comparisons, `len(...)`, and slice bounds
- composed semantic field flows and observable required fields
- interprocedural summaries and observable output slices
- external-call field slices and control-dependence slices
- nullable-use and protocol-order review candidates

## Current project test targets

Optional field boundary mappings:

- `AdoptablePet.adoption_url -> Post.link` in `SocialPoster.format_post`
- `AdoptablePet.image_url -> Post.image_url` in `SocialPoster.format_post`
- `AdoptablePet.adoption_url -> Post.link` in `PosterMastodon.format_post`
- `AdoptablePet.image_url -> Post.image_url` in `PosterMastodon.format_post`
- `Post.image_url -> PostResult.post_id/post_url` in `PosterMastodon.publish`
- `Post.alt_text -> PostResult.post_id/post_url` in `PosterMastodon.publish`

Required field mappings:

- `AdoptablePet.name -> Post.text` and `Post.alt_text`
- `AdoptablePet.breed -> Post.text`, `Post.tags`, and `Post.alt_text`
- `AdoptablePet.species -> Post.text`, `Post.tags`, and `Post.alt_text`
- `AdoptablePet.location -> Post.text` and `Post.tags`
- `PreparedCaption.caption_text -> CaptionThread.main_caption/main_text/overflow/replies`
- `PreparedCaption.tag_suffix -> CaptionThread.main_caption/main_limit/main_text/overflow/replies`

Optional branch targets:

- `AdoptablePet.adoption_url` in `SocialPoster.format_post`
- `AdoptablePet.adoption_url` in `PosterMastodon.format_post`
- `Post.image_url` in `PosterBluesky.publish`
- `Post.image_url` in `PosterInstagram.publish`
- `Post.image_url` in `PosterMastodon._ensure_ready_to_publish`
- `Post.link` in `PosterBluesky._build_text_and_facets`

## Contract conformance targets

`PetSource` implementations:

- `SourceManual.fetch_pets` returns `AdoptablePet`
- `SourceRescueGroups.fetch_pets` returns `AdoptablePet`

`SocialPoster` implementations:

- `PosterBluesky.publish` accepts `Post` and returns `PostResult`
- `PosterDebug.publish` accepts `Post` and returns `PostResult`
- `PosterInstagram.publish` accepts `Post` and returns `PostResult`
- `PosterMastodon.publish` accepts `Post` and returns `PostResult`

Formatting overrides:

- `PosterBluesky.format_post` accepts `AdoptablePet`, returns `Post`, and constructs `Post`
- `PosterMastodon.format_post` accepts `AdoptablePet`, returns `Post`, and constructs `Post`

## Practical generated-test ideas

- Generate `AdoptablePet` cases where `adoption_url` is `None`, empty, and a valid URL; assert `Post.link` and post text behavior are intentional.
- Generate `AdoptablePet` cases where `image_url` is `None`, empty, and a valid URL; assert `Post.image_url` follows the input.
- Generate `AdoptablePet` cases that vary `name`, `breed`, and `species`; assert `Post.alt_text` and tag/text construction are intentional.
- Run shared `Post` fixtures through all concrete `publish` implementations and assert each path returns `PostResult`.
- Generate platform-specific missing-image tests because multiple publish methods branch on `Post.image_url`.
- Generate Bluesky link/facet tests because `PosterBluesky._build_text_and_facets` branches on `Post.link`.
- Generate numeric boundary tests from discovered string-length and truncation bounds.
- Assert explicit success/failure result literal paths such as `PostResult.success = True` and `PostResult.success = False`.
- Review lossy required-field candidates before deciding whether they are intentional lossy transformations or missing behavior.

## Current generated-test artifact

The first executable generator keeps tests outside `CutePetsBoston/` so this
repository can be shared without committing the full sample application. Given
an analysis run such as:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-analysis-run
```

generate portable pytest tests with:

```bash
python3 tools/generate_pytest_from_properties.py \
  --analysis-dir /tmp/sps-analysis-run \
  --output-dir generated_tests \
  --project-name cutepetsboston
```

Current output:

```text
generated_tests/cutepetsboston/test_generated_dataclass_properties.py
generated_tests/cutepetsboston/test_generated_dataclass_hypothesis.py
generated_tests/cutepetsboston/test_generated_helper_boundaries.py
generated_tests/cutepetsboston/test_generated_common_ast_properties.py
generated_tests/cutepetsboston/test_generated_interprocedural_properties.py
generated_tests/cutepetsboston/README.md
```

Run them against any local CutePetsBoston checkout with:

```bash
PYTHONPATH=/path/to/CutePetsBoston pytest generated_tests/cutepetsboston
```

The current generated files emit the conservative executable subset: public
`format_post` examples and Hypothesis properties for `SocialPoster` and
`PosterMastodon`, including required field observability into `Post.text`,
`Post.tags`, and `Post.alt_text`, plus optional passthrough checks for
`adoption_url -> link` and `image_url -> image_url`. The helper-boundary file
adds lower-confidence private-helper tests when a string-length boundary can be
driven directly. The common-AST file covers observable dataclass collection
iteration relations, and the interprocedural file covers public observable
string-output slices such as `AdoptablePet` fields reaching
`CaptionThread.main_caption` through `PosterMastodon.build_formatting_pipeline`.

Publishing paths, private Mastodon caption helpers that need dataclass/custom
input construction, optional/collection interprocedural slices, nullable-use
candidates, and protocol-order candidates are still reported as review
candidates because their generated tests need either mocks, stronger
control-dependence facts, or a more precise assertion oracle.

## Current precision limits

- Field-to-constructor-argument flow now captures aliases and many composed expressions, including f-strings and list elements.
- Semantic flow is conservative and should be validated with concrete tests.
- Call-result propagation is conservative; mappings through SDK/API return values can over-approximate semantic influence.
- Override matching is name-based and base-class-name-based; import-resolved inheritance exists as facts but matching still needs better cross-module precision.
- Branch/control-dependence facts show candidate line-order influence, not a
  path-sensitive guarantee about which return branch is controlled.

## Future potential work

- Feed validation results back into the relation store so pass/fail/skip counts
  can be linked directly to the derived relation that produced each test.
- Improve executable/review report comparisons across runs so users can
  distinguish likely program failures from weak static-analysis oracles.
- Extend Hypothesis templates beyond current transform properties into optional
  field combinations, richer Mastodon length boundaries, tag normalization, and
  contract conformance.
- Add executable templates for selected slicing, nullable-use, and
  protocol-order candidates once their assertion oracles are strong enough.
- Explore mutation testing inspired by *The Fuzzing Book* by mutating
  dataclass mappings, branch conditions, and generated inputs, then measuring
  whether generated tests detect the change.
- Explore concolic testing with SAT/SMT solvers to solve branch and boundary
  constraints instead of relying only on sampled examples.
- Extend evaluation statistics beyond current line coverage and coverage deltas
  into branch coverage, dataclass-field coverage, derived-relation coverage, and
  mutation score.
