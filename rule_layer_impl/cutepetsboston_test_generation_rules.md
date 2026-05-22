# CutePetsBoston Test Generation Rules

This file records project-specific test-generation targets derived from the
generic dataclass test model.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/cutepets-updated-run2
```

## New model layer

The generic model is `rule_layer/dataclass_test_model.dl`.

It derives test-oriented relations from:

- dataclass field metadata
- class/method ownership
- inheritance and method override candidates
- constructor keyword arguments
- direct and local-derived field-to-constructor-argument flows
- local dependencies through aliases and composed expressions
- optional fields read in branch conditions

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

## Current precision limits

- Field-to-constructor-argument flow now captures aliases and many composed expressions, including f-strings and list elements.
- Call-result propagation is conservative; mappings through SDK/API return values can over-approximate semantic influence.
- Override matching is name-based and base-class-name-based; import-resolved inheritance is still future work.
- Branch facts show that a field appears in a condition, not which return branch it controls.
