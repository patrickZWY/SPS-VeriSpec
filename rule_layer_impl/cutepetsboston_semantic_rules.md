# CutePetsBoston Semantic Rules

This file records project-specific interpretations of the generic semantic
model in `rule_layer/semantic_model.dl`.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-docs-check
```

## Current semantic summary

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

## Domain-level semantic flows

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

## Composed semantic flows

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

## Observable required fields

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

## Lossy required-field candidates

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

## Literal result semantics

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

These facts are useful for success/failure test templates. They do not yet say
which branch condition controls each literal; branch-local return facts are the
next needed precision improvement.

## String composition targets

Current string-composed dataclass fields:

- `SocialPoster.format_post -> Post.alt_text` uses an f-string
- `PosterBluesky.format_post -> Post.alt_text` uses an f-string
- `PosterMastodon.format_post -> Post.alt_text` uses an f-string
- `PosterMastodon._build_caption_thread -> CaptionThread.main_caption` uses an f-string

Generated tests should vary the source fields that flow into these outputs and
assert the rendered strings remain useful and stable.

## Numeric boundary candidates

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

## Boundary behavior semantics

The boundary-behavior layer associates generic numeric bounds with the input and
output surface they affect.

Current dataclass/input behaviors:

- `Post.text -> str.<return>` in `PosterInstagram._format_caption` has
  `max_length` behavior around `caption < 2200`.
- `Post.tags -> str.<return>` in `PosterInstagram._format_caption` also
  contributes to the same caption max-length behavior because tag text can be
  appended to the caption.

Current helper behaviors:

- `SourceRescueGroups._clean_description(description) -> return` has
  `truncate_or_include` behavior around the local `text[:497]` slice.

This is the level where generic boundaries become platform/helper-specific test
intent. Raw facts still say "`caption` has an upper bound"; behavior facts say
"this input contributes to a returned string max-length constraint."

## Recommended project tests

- Vary `AdoptablePet.name`, `breed`, `species`, and `location`; assert they are
  observable in `Post.text` or `Post.alt_text` as intended.
- Vary `AdoptablePet.image_url` and `adoption_url`; assert the corresponding
  optional `Post` fields preserve absence and valid values.
- Run common `Post` fixtures through all `publish` implementations and assert
  `PostResult.success` matches success/failure scenarios.
- Generate boundary tests for RescueGroups description cleanup and platform
  caption/length limits.
- Verify Mastodon caption construction preserves `Post.text` and tag suffixes
  through `PreparedCaption` into `CaptionThread`.

## Current precision limits

- Semantic flows are conservative and can include SDK/API-result
  over-approximations.
- Literal result facts are not yet branch-local.
- Numeric facts cover direct integer literals and simple local integer
  assignments, not full arithmetic.
- String-composition facts identify construction style and contributing fields,
  not exact rendered string equality.
- Field identity is still partly name-based and should be improved with
  stronger alias and type-resolution facts.
- Boundary behavior summaries are intentionally narrow. They currently cover
  upper-bound string caps through dataclass/local dependencies and simple helper
  truncation, not arbitrary platform API constraints.
