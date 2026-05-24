# CutePetsBoston Dataclass Effect Rules

This file records project-specific dataclass-to-function and dataclass-to-effect
rules for `CutePetsBoston`. It is intentionally concrete and should be updated
when the application flow changes.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-slicing-ai-check
```

## Main effect paths

- `AdoptablePet` is produced by `SourceManual._build_pet` and `SourceRescueGroups._parse_animal`.
- `AdoptablePet` is fetched by `SourceManual.fetch_pets`, `SourceRescueGroups.fetch_pets`, and the abstract `PetSource.fetch_pets` contract.
- `AdoptablePet` is transformed into `Post` by `SocialPoster.format_post` and `PosterMastodon.format_post`.
- `Post` is consumed by platform `publish` implementations and converted into `PostResult`.
- `Post` is also consumed by Mastodon caption helpers to produce `PreparedCaption` and then `CaptionThread`.
- `PipelineResult` records preview/debug traces for the Mastodon formatting pipeline.

## Important function links

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

## Field influence rules

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

## Effect categories to watch

- Network effects are attached to source fetching and platform publishing through calls such as `requests.post`, `requests.get`, response parsing, and platform SDK calls.
- Exception effects are attached to RescueGroups parsing/fetching and platform publishing paths.
- Dataclass construction effects are attached to source parsing, post formatting, publish result creation, and Mastodon caption/thread creation.

## Current effect limitations

- The effect model itself still records parameter-based field reads, while the test-generation and deduction layers add local alias and call-result inference.
- Function-level call effects are over-approximated: every call inside a dataclass-linked function is associated with that dataclass.
- Call-result propagation is conservative and can over-approximate semantic influence through SDK/API return values.
- Branch-local result semantics are still approximate. Literal result fields can
  be connected to nearby conditions with line-order control-dependence slices,
  but a precise CFG/path-sensitive model is still future work.
- Protocol events such as validate/authenticate/publish are name-classified and
  line-ordered; cross-method workflows can still appear as review candidates.
