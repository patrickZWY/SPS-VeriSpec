# CutePetsBoston case study

This is the original end-to-end target for SPS-VeriSpec: a Python app that posts
a random adoptable pet from the Boston MSPCA to several social media feeds (see
[`CutePetsBoston/README.md`](../../CutePetsBoston/README.md) for the app itself).

This document records the **project-specific** rules and findings produced by
running the generic Souffle layers against this app. Unlike the generic per-layer
references in [`docs/layers/`](../layers/), everything here is intentionally tied
to the application domain — adoptable pets, social posts, platform publish
results, and the Mastodon preview pipeline — and should be updated when the
application flow changes.

All findings below were generated with:

```bash
python3 tools/run_static_analysis.py CutePetsBoston --engine souffle --work-dir /tmp/sps-slicing-ai-check
```

The sections map to the generic analysis layers:

- [Dataclass schema rules](#dataclass-schema-rules) — `dataclass_schema_model.dl`
- [Dataclass effect rules](#dataclass-effect-rules) — `dataclass_effect_model.dl`
- [Deduction rules](#deduction-rules) — `dataclass_deduction_model.dl`
- [Semantic rules](#semantic-rules) — `semantic_model.dl`
- [Test-generation rules](#test-generation-rules) — `dataclass_test_model.dl` + `semantic_model.dl`

---

## Dataclass schema rules

This is the project-specific dataclass model for `CutePetsBoston`. Unlike the
generic [schema layer reference](../layers/schema.md), it is tied to the current
application domain.

### Domain inventory

The current extractor discovers eight dataclasses:

- `abstractions.AdoptablePet`
- `abstractions.Post`
- `abstractions.PostResult`
- `social_posters.mastodon.PreparedCaption`
- `social_posters.mastodon.CaptionThread`
- `utils.pipeline.Phase`
- `utils.pipeline.PipelineResult`
- `utils.pipeline_preview.PreviewSection`

### Core domain types

- `AdoptablePet` is the upstream ingest record from manual or RescueGroups sources. Required fields are `name`, `species`, `breed`, and `location`; optional/defaulted fields describe adoption URL, image URL, age, sex, size, pet ID, and description.
- `Post` is the platform-neutral social media post shape. It carries text plus optional image/link/accessibility metadata and factory-backed `tags`.
- `PostResult` is the publish outcome shape. It always has `success`; platform IDs, URLs, and error text are optional.
- `PreparedCaption` and `CaptionThread` are frozen Mastodon-specific formatting stages. They model the split from a generic `Post` into thread-ready text.
- `Phase` and `PipelineResult` are generic preview/debug tracing support for the Mastodon formatting pipeline.
- `PreviewSection` is a frozen renderer descriptor for preview output.

### Shape rules

Current `dataclass_shape` summaries use this order:

```text
[field_count, required_count, optional_count, defaulted_count, factory_count, frozen]
```

Current shapes:

- `abstractions.AdoptablePet -> [11, 4, 6, 7, 0, 0]`
- `abstractions.Post -> [5, 1, 3, 4, 1, 0]`
- `abstractions.PostResult -> [4, 1, 3, 3, 0, 0]`
- `social_posters.mastodon.PreparedCaption -> [4, 4, 0, 0, 0, 1]`
- `social_posters.mastodon.CaptionThread -> [7, 4, 3, 0, 0, 1]`
- `utils.pipeline.Phase -> [2, 2, 0, 0, 0, 1]`
- `utils.pipeline.PipelineResult -> [3, 0, 1, 2, 2, 0]`
- `utils.pipeline_preview.PreviewSection -> [3, 3, 0, 0, 0, 1]`

### Schema-level rules to preserve

- `AdoptablePet` should remain the main source-side domain record.
- `Post` should remain the platform-neutral bridge between pet ingest and platform publishers.
- Platform-specific formatting dataclasses should stay downstream of `Post`, not replace `Post` as the shared poster contract.
- `PostResult` should remain the common publish result contract for all poster implementations.
- Mastodon preview pipeline dataclasses should stay separate from core posting dataclasses because they support debugging and formatting inspection, not general publishing.

### Schema limitations

- Type references are syntactic, so generic references such as `PipelineResult[CaptionThread]` are only approximated.
- Name-based type matching can over-link classes if two modules define the same dataclass name.
- Schema facts do not prove runtime flow; they only describe declared dataclass structure.

---

## Dataclass effect rules

Project-specific dataclass-to-function and dataclass-to-effect rules. This is
intentionally concrete and should be updated when the application flow changes.

### Main effect paths

- `AdoptablePet` is produced by `SourceManual._build_pet` and `SourceRescueGroups._parse_animal`.
- `AdoptablePet` is fetched by `SourceManual.fetch_pets`, `SourceRescueGroups.fetch_pets`, and the abstract `PetSource.fetch_pets` contract.
- `AdoptablePet` is transformed into `Post` by `SocialPoster.format_post` and `PosterMastodon.format_post`.
- `Post` is consumed by platform `publish` implementations and converted into `PostResult`.
- `Post` is also consumed by Mastodon caption helpers to produce `PreparedCaption` and then `CaptionThread`.
- `PipelineResult` records preview/debug traces for the Mastodon formatting pipeline.

### Important function links

Source-side links:

- `adoption_sources.manual.SourceManual._build_pet -> AdoptablePet`
- `adoption_sources.rescue_groups.SourceRescueGroups._parse_animal -> AdoptablePet`
- `adoption_sources.rescue_groups.SourceRescueGroups.fetch_pets -> AdoptablePet`

Formatting links:

- `abstractions.SocialPoster.format_post: AdoptablePet -> Post`
- `social_posters.mastodon.PosterMastodon.format_post: AdoptablePet -> Post`
- `social_posters.mastodon.PosterMastodon._prepare_caption: Post -> PreparedCaption`
- `social_posters.mastodon.PosterMastodon._build_caption_thread: PreparedCaption -> CaptionThread`
- `social_posters.mastodon.PosterMastodon.build_formatting_pipeline: AdoptablePet -> PipelineResult[CaptionThread]`

Publish links:

- `social_posters.bluesky.PosterBluesky.publish: Post -> PostResult`
- `social_posters.debug.PosterDebug.publish: Post -> PostResult`
- `social_posters.instagram.PosterInstagram.publish: Post -> PostResult`
- `social_posters.mastodon.PosterMastodon.publish: Post -> PostResult`
- `social_posters.mastodon.PosterMastodon._ensure_ready_to_publish: Post -> PostResult | None`

### Field influence rules

Fields currently observed as contributing to `AdoptablePet -> Post`:

- `adoption_url`
- `breed`
- `description`
- `image_url`
- `location`
- `name`
- `species`

Fields currently observed as contributing to `Post -> PostResult`:

- `alt_text`
- `image_url`
- `link`
- `tags`
- `text`

Fields currently observed as contributing to Mastodon caption transformations:

- `Post.text -> PreparedCaption`
- `Post.tags -> PreparedCaption`
- `PreparedCaption.caption_text -> CaptionThread`
- `PreparedCaption.tag_suffix -> CaptionThread`

The generic semantic model now composes these field influences across
intermediate dataclasses and also records observable required fields, explicit
dataclass constructor literals, string-composition targets, and numeric
boundary candidates. The current semantic layer also records external-call
field slices, control-dependence slices, abstract-state candidates, and
protocol-order events that help review effectful paths.

### Effect categories to watch

- Network effects are attached to source fetching and platform publishing through calls such as `requests.post`, `requests.get`, response parsing, and platform SDK calls.
- Exception effects are attached to RescueGroups parsing/fetching and platform publishing paths.
- Dataclass construction effects are attached to source parsing, post formatting, publish result creation, and Mastodon caption/thread creation.

### Effect limitations

- The effect model itself still records parameter-based field reads, while the test-generation and deduction layers add local alias and call-result inference.
- Function-level call effects are over-approximated: every call inside a dataclass-linked function is associated with that dataclass.
- Call-result propagation is conservative and can over-approximate semantic influence through SDK/API return values.
- Branch-local result semantics are still approximate. Literal result fields can be connected to nearby conditions with line-order control-dependence slices, but a precise CFG/path-sensitive model is still future work.
- Protocol events such as validate/authenticate/publish are name-classified and line-ordered; cross-method workflows can still appear as review candidates.

---

## Deduction rules

Project-specific deductions from the generic dataclass schema and effect layers.
These are useful for reviewing the current application architecture and for
deciding where extractor precision should improve next.

### Deduction summary

- Dataclasses discovered: 8
- Direct dataclass transformations: 12
- Reachable dataclass transformation pairs: 9
- Dataclass-linked functions: 66
- Semantic field flows: 54
- Composed semantic field flows: 86
- Observable required fields: 21
- Backward output slices: 69
- External-call field slices: 67
- Control-dependence slices: 16
- Nullable use-before-guard candidates: 12
- Protocol obligation candidates: 3
- Numeric boundary candidates: 18

### Direct transformation rules

Current direct transformation edges:

- `abstractions.AdoptablePet -> abstractions.Post`
- `abstractions.AdoptablePet -> social_posters.mastodon.CaptionThread`
- `abstractions.AdoptablePet -> utils.pipeline.PipelineResult`
- `abstractions.Post -> abstractions.PostResult`
- `abstractions.Post -> social_posters.mastodon.PreparedCaption`
- `social_posters.mastodon.PreparedCaption -> social_posters.mastodon.CaptionThread`

The repeated `Post -> PostResult` edge appears through the abstract poster
contract plus Bluesky, Debug, Instagram, and Mastodon implementations.

### Reachability rules

Current reachable transformation chains:

- `AdoptablePet => Post`
- `AdoptablePet => PostResult`
- `AdoptablePet => PreparedCaption`
- `AdoptablePet => CaptionThread`
- `AdoptablePet => PipelineResult`
- `Post => PostResult`
- `Post => PreparedCaption`
- `Post => CaptionThread`
- `PreparedCaption => CaptionThread`

The intended high-level domain path is:

```text
AdoptablePet -> Post -> PostResult
```

The Mastodon formatting/debug path extends that with:

```text
AdoptablePet -> Post -> PreparedCaption -> CaptionThread
```

### Topology rules

- Entry dataclass: `abstractions.AdoptablePet`
- Bridge dataclasses: `abstractions.Post`, `social_posters.mastodon.PreparedCaption`
- Terminal dataclasses: `abstractions.PostResult`, `social_posters.mastodon.CaptionThread`, `utils.pipeline.PipelineResult`

`utils.pipeline.Phase` and `utils.pipeline_preview.PreviewSection` are currently
classified as both entry-like or terminal-like helper shapes because they do not
participate in the main transformation graph. Treat them as tooling dataclasses,
not business-domain endpoints.

### Blind-spot rules

Current unread required fields:

- `social_posters.mastodon.PreparedCaption.post`
- `social_posters.mastodon.PreparedCaption.tags`
- `social_posters.mastodon.CaptionThread.was_split`
- `social_posters.mastodon.CaptionThread.was_capped`
- `utils.pipeline.Phase.name`
- `utils.pipeline.Phase.value`
- `utils.pipeline_preview.PreviewSection.stage`
- `utils.pipeline_preview.PreviewSection.title`
- `utils.pipeline_preview.PreviewSection.render`

These are review candidates, not guaranteed bugs. In this project, several are
still extractor precision gaps around generic pipeline values and helper
renderer callbacks. `PostResult.success`, `CaptionThread.main_caption`, and
`CaptionThread.replies` are now inferred through local/call-result reads.

### Semantic review candidates

The semantic model now adds project-specific review targets on top of the
deduction graph:

- required pet fields such as `name`, `breed`, `species`, and `location` are observable through `Post.text` or `Post.alt_text`
- `Post.text` and `Post.tags` compose into Mastodon caption/thread fields through `PreparedCaption`
- `PostResult.success` is observed as explicit `True` and `False` constructor literals across publish paths
- string-length and truncation code produces boundary candidates, for example around description cleanup and platform caption limits
- lossy required-field candidates identify transforms where a required field has no detected flow into the returned dataclass
- external-call field slices identify dataclass fields that influence SDK, HTTP, print/debug, or formatting call arguments
- nullable-use candidates identify optional fields read without an obvious earlier guard or validation event in the same function
- protocol candidates identify publish-like calls without an obvious earlier validate/authenticate event in the same function

### Project-specific verification targets

- Verify that every concrete `SocialPoster.publish` returns `PostResult` on all success and failure paths.
- Verify that platform publish paths either require or gracefully handle missing `Post.image_url`.
- Verify that `AdoptablePet` records selected for posting always have `image_url` and `adoption_url`.
- Verify that Mastodon caption splitting preserves the relation `Post.text -> PreparedCaption.caption_text -> CaptionThread.main_caption/replies`.
- Verify boundary behavior for discovered numeric limits such as description truncation and platform caption limits.
- Verify success/failure result literals align with the concrete branch behavior that constructs them.
- Review external-call field slices for fields that cross network/API/logging boundaries.
- Review protocol candidates in `main.run` and Mastodon thread posting to decide whether cross-method authentication summaries are needed.
- Verify that Slack failure notification remains outside the dataclass transformation graph unless a future alert-result dataclass is introduced.

### Recommended extractor improvements for this project

- Resolve generic type arguments for `PipelineResult[CaptionThread]`.
- Add better class identity resolution across imports to avoid name-only joins.
- Add branch-local return facts that connect specific optional-field checks to specific returned constructors.
- Add CFG/control-dependence facts beyond current line-order slices for validation and guarded-effect reasoning.
- Add more precise call-boundary summaries so SDK/API return values do not over-approximate semantic influence.
- Add cross-method protocol summaries so authenticate/validate performed in one method can discharge publish/use obligations in another method.

---

## Semantic rules

Project-specific interpretations of the generic semantic model in
`souffle_static_analysis/semantic_model.dl`.

### Semantic summary

- Semantic field flows: 54
- Composed semantic field flows: 86
- Observable required fields: 21
- Lossy required-field candidates: 7
- Dataclass boolean literals: 11
- String composition targets: 4
- Numeric bounds: 6
- Numeric boundary candidates: 18
- Boundary behaviors: 2
- Helper boundary behaviors: 1
- Backward output slices: 69
- Function backward slices: 46
- External-call field slices: 67
- Control-dependence slices: 16
- Abstract value states: 193
- Abstract numeric states: 1
- Nullable use-before-guard candidates: 12
- Typestate transitions: 8
- Protocol obligation candidates: 3

### Domain-level semantic flows

The semantic model confirms the core `AdoptablePet -> Post` field influence:

- `AdoptablePet.name -> Post.text`
- `AdoptablePet.name -> Post.alt_text`
- `AdoptablePet.breed -> Post.text`
- `AdoptablePet.breed -> Post.tags`
- `AdoptablePet.breed -> Post.alt_text`
- `AdoptablePet.species -> Post.text`
- `AdoptablePet.species -> Post.tags`
- `AdoptablePet.species -> Post.alt_text`
- `AdoptablePet.location -> Post.text`
- `AdoptablePet.location -> Post.tags`
- `AdoptablePet.image_url -> Post.image_url`
- `AdoptablePet.adoption_url -> Post.link`

`Post.alt_text` is marked as string-composed in both the abstract
`SocialPoster.format_post` path and concrete poster formatting paths.

### Composed semantic flows

The generic semantic model composes field influence across intermediate
dataclasses. For the current app, the important composed flows include:

- `AdoptablePet.name/breed/species/location -> Post.text`
- `AdoptablePet.name/breed/species -> Post.alt_text`
- `AdoptablePet.image_url -> Post.image_url -> PostResult.post_id/post_url`
- `AdoptablePet.breed/species/location -> Post.tags -> PreparedCaption.tag_suffix`
- `Post.text -> PreparedCaption.caption_text -> CaptionThread.main_caption/main_text/replies/overflow`
- `Post.tags -> PreparedCaption.tag_suffix -> CaptionThread.main_caption/main_text/replies/overflow`

These are conservative test-generation candidates. In particular, flows through
`PostResult.post_id` and `PostResult.post_url` can be over-approximated when
external SDK/API return values are involved.

### Observable required fields

Required `AdoptablePet` identity fields are observable through string-valued
`Post` fields:

- `AdoptablePet.name -> Post.text`
- `AdoptablePet.name -> Post.alt_text`
- `AdoptablePet.breed -> Post.text`
- `AdoptablePet.breed -> Post.alt_text`
- `AdoptablePet.species -> Post.text`
- `AdoptablePet.species -> Post.alt_text`
- `AdoptablePet.location -> Post.text`

Mastodon caption helpers also expose required `PreparedCaption` fields:

- `PreparedCaption.caption_text -> CaptionThread.main_caption`
- `PreparedCaption.caption_text -> CaptionThread.main_text`
- `PreparedCaption.caption_text -> CaptionThread.overflow`
- `PreparedCaption.tag_suffix -> CaptionThread.main_caption`
- `PreparedCaption.tag_suffix -> CaptionThread.main_text`
- `PreparedCaption.tag_suffix -> CaptionThread.overflow`

### Lossy required-field candidates

These are not guaranteed bugs. They are places where the current analysis sees
a required input field but no detected flow into the returned dataclass:

- `Post.text` does not flow to `PostResult` in `PosterBluesky.publish`
- `Post.text` does not flow to `PostResult` in `PosterDebug.publish`
- `Post.text` does not flow to `PostResult` in `PosterInstagram.publish`
- `Post.text` does not flow to `PostResult` in `PosterMastodon._ensure_ready_to_publish`
- `Post.text` does not flow to `PostResult` in `PosterMastodon.publish`
- `PreparedCaption.post` does not flow to `CaptionThread` in `PosterMastodon._build_caption_thread`
- `PreparedCaption.tags` does not flow to `CaptionThread` in `PosterMastodon._build_caption_thread`

The publish cases are likely intentional: `Post.text` is the content being
published, while `PostResult` records platform outcome metadata. The
`PreparedCaption.post` and `PreparedCaption.tags` cases are worth review:
`tag_suffix` is used downstream, but the original `tags` field itself is not
directly observable in the returned `CaptionThread`.

### Literal result semantics

The model detects explicit boolean constructor literals for result/status
dataclasses:

- `PosterBluesky.publish` constructs `PostResult.success = False`
- `PosterBluesky.publish` constructs `PostResult.success = True`
- `PosterDebug.publish` constructs `PostResult.success = True`
- `PosterInstagram.publish` constructs `PostResult.success = False`
- `PosterInstagram.publish` constructs `PostResult.success = True`
- `PosterMastodon._ensure_ready_to_publish` constructs `PostResult.success = False`
- `PosterMastodon.publish` constructs `PostResult.success = False`
- `PosterMastodon.publish` constructs `PostResult.success = True`
- `PosterMastodon._build_caption_thread` constructs `CaptionThread.was_capped = False`
- `PosterMastodon._build_caption_thread` constructs `CaptionThread.was_split = False`
- `PosterMastodon._build_caption_thread` constructs `CaptionThread.was_split = True`

These facts are useful for success/failure test templates. Line-order
control-dependence slices now provide a conservative bridge from conditions to
nearby returns/exceptions/protocol events, but they still do not replace
branch-local return facts or a full CFG.

### String composition targets

Current string-composed dataclass fields:

- `SocialPoster.format_post -> Post.alt_text` uses an f-string
- `PosterBluesky.format_post -> Post.alt_text` uses an f-string
- `PosterMastodon.format_post -> Post.alt_text` uses an f-string
- `PosterMastodon._build_caption_thread -> CaptionThread.main_caption` uses an f-string

Generated tests should vary the source fields that flow into these outputs and
assert the rendered strings remain useful and stable.

### Numeric boundary candidates

Current numeric bounds:

- `PosterBluesky.format_post`: `pet.description < 120`
- `PosterBluesky._build_text_and_facets`: `available >= 0`
- `PosterInstagram._format_caption`: `caption < 2200`
- `PosterMastodon._validated_main_limit`: `main_limit <= 0`
- `SourceRescueGroups._clean_description`: `len(text) > 500`
- `SourceRescueGroups._clean_description`: `text[:497]`

Generated boundary tests should include:

- `pet.description` lengths or values around `119`, `120`, and `121`
- Bluesky `available` values around `-1`, `0`, and `1`
- Instagram caption lengths around `2199`, `2200`, and `2201`
- Mastodon `main_limit` values around `-1`, `0`, and `1`
- RescueGroups description lengths around `496`, `497`, `498`, `499`, `500`, and `501`

### Boundary behavior semantics

The boundary-behavior layer associates generic numeric bounds with the input and
output surface they affect.

Current dataclass/input behaviors:

- `Post.text -> str.<return>` in `PosterInstagram._format_caption` has `max_length` behavior around `caption < 2200`.
- `Post.tags -> str.<return>` in `PosterInstagram._format_caption` also contributes to the same caption max-length behavior because tag text can be appended to the caption.

Current helper behaviors:

- `SourceRescueGroups._clean_description(description) -> return` has `truncate_or_include` behavior around the local `text[:497]` slice.

This is the level where generic boundaries become platform/helper-specific test
intent. Raw facts still say "`caption` has an upper bound"; behavior facts say
"this input contributes to a returned string max-length constraint."

### Slicing and protocol candidates

The slicing layer exposes where field values influence observable outputs,
external calls, and guards:

- External-call slices show fields such as `Post.image_url`, `Post.text`, `Post.tags`, `Post.link`, and `Post.alt_text` flowing into SDK, formatting, print/debug, and HTTP call arguments.
- Control-dependence slices connect guard atoms such as `post.image_url` to nearby exceptions, returned dataclasses, or publish-like protocol events.
- Backward output slices provide the reverse view of observable outputs, for example which source fields can reach `CaptionThread.main_caption`.

The typestate/protocol layer currently reports a small number of review
candidates:

- `main.run` calls a publish-like method on `poster`; whether this is safe depends on the concrete poster implementation and earlier setup.
- `PosterMastodon._post_thread` performs `status_post` calls on `self._session`; the intended authentication happens through `_ensure_ready_to_publish`, so this is a cross-method protocol obligation.

These are useful review targets, not automatic bugs. They point to places where
the tool should later learn cross-method typestate summaries.

### Abstract-state candidates

The abstract-state layer currently records:

- optional dataclass fields that may be `None`
- truthy/falsy and non-null states observed in branch conditions
- string-length bounds from `len(...)` and slice facts
- success/failure status literals such as `PostResult.success = True/False`
- optional field reads that lack an obvious prior guard or validation event in the same function

The nullable-use candidates should be read as prompts for tests or review. Some
are intentional because the code tolerates `None`; others may reveal missing
guards or cross-method validation that the current analysis cannot summarize.

### Recommended project tests

- Vary `AdoptablePet.name`, `breed`, `species`, and `location`; assert they are observable in `Post.text` or `Post.alt_text` as intended.
- Vary `AdoptablePet.image_url` and `adoption_url`; assert the corresponding optional `Post` fields preserve absence and valid values.
- Run common `Post` fixtures through all `publish` implementations and assert `PostResult.success` matches success/failure scenarios.
- Generate boundary tests for RescueGroups description cleanup and platform caption/length limits.
- Verify Mastodon caption construction preserves `Post.text` and tag suffixes through `PreparedCaption` into `CaptionThread`.

### Semantic precision limits

- Semantic flows are conservative and can include SDK/API-result over-approximations.
- Literal result facts are not yet branch-local; control-dependence slices are line-order candidates, not path-sensitive proofs.
- Numeric facts cover direct integer literals and simple local integer assignments, not full arithmetic.
- String-composition facts identify construction style and contributing fields, not exact rendered string equality.
- Field identity is still partly name-based and should be improved with stronger alias and type-resolution facts.
- Boundary behavior summaries are intentionally narrow. They currently cover upper-bound string caps through dataclass/local dependencies and simple helper truncation, not arbitrary platform API constraints.
- Typestate/protocol findings are name-based event-order candidates and should be validated against the concrete workflow.

---

## Test-generation rules

Project-specific test-generation targets derived from the generic dataclass test
model (`souffle_static_analysis/dataclass_test_model.dl`) and the generic
semantic model (`souffle_static_analysis/semantic_model.dl`).

### Model layers

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

### Project test targets

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

### Contract conformance targets

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

### Practical generated-test ideas

- Generate `AdoptablePet` cases where `adoption_url` is `None`, empty, and a valid URL; assert `Post.link` and post text behavior are intentional.
- Generate `AdoptablePet` cases where `image_url` is `None`, empty, and a valid URL; assert `Post.image_url` follows the input.
- Generate `AdoptablePet` cases that vary `name`, `breed`, and `species`; assert `Post.alt_text` and tag/text construction are intentional.
- Run shared `Post` fixtures through all concrete `publish` implementations and assert each path returns `PostResult`.
- Generate platform-specific missing-image tests because multiple publish methods branch on `Post.image_url`.
- Generate Bluesky link/facet tests because `PosterBluesky._build_text_and_facets` branches on `Post.link`.
- Generate numeric boundary tests from discovered string-length and truncation bounds.
- Assert explicit success/failure result literal paths such as `PostResult.success = True` and `PostResult.success = False`.
- Review lossy required-field candidates before deciding whether they are intentional lossy transformations or missing behavior.

### Generated-test artifact

The first executable generator keeps tests outside `CutePetsBoston/` so this
repository can be shared without committing the full sample application. Given
an analysis run such as:

```bash
python3 tools/run_static_analysis.py CutePetsBoston --engine souffle --work-dir /tmp/sps-analysis-run
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

### Test-generation precision limits

- Field-to-constructor-argument flow now captures aliases and many composed expressions, including f-strings and list elements.
- Semantic flow is conservative and should be validated with concrete tests.
- Call-result propagation is conservative; mappings through SDK/API return values can over-approximate semantic influence.
- Override matching is name-based and base-class-name-based; import-resolved inheritance exists as facts but matching still needs better cross-module precision.
- Branch/control-dependence facts show candidate line-order influence, not a path-sensitive guarantee about which return branch is controlled.

### Future potential work

- Feed validation results back into the relation store so pass/fail/skip counts can be linked directly to the derived relation that produced each test.
- Improve executable/review report comparisons across runs so users can distinguish likely program failures from weak static-analysis oracles.
- Extend Hypothesis templates beyond current transform properties into optional field combinations, richer Mastodon length boundaries, tag normalization, and contract conformance.
- Add executable templates for selected slicing, nullable-use, and protocol-order candidates once their assertion oracles are strong enough.
- Mutation testing is now available for relation-guided transform mappings, common-AST collection iteration, interprocedural pipeline stages, and solver-adjacent boundary changes. Branch-condition mutants and generated-input mutants remain useful next extensions.
- Explore concolic testing with SAT/SMT solvers to solve branch and boundary constraints instead of relying only on sampled examples.
- Extend evaluation statistics beyond current line coverage, relation-yield, coverage deltas, and mutation score into branch coverage, dataclass-field coverage, derived-relation coverage, and oracle-strength reporting.
