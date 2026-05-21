# Generic Dataclass Effect Modeling Run

This file describes the generic Souffle workflow that associates dataclasses
with effects in surrounding functions and methods.

The purpose is still abstraction, not whole-program translation. The model
starts from all discovered dataclasses, then links them to effects through
typed function signatures, constructor sites, field access, and exception or
call behavior.

## Souffle program

The generic program is `rule_layer/dataclass_effect_model.dl`.

It uses Souffle record types:

- `FunctionLink`
- `EffectEvent`
- `FieldEvent`

## How to run it

```bash
python3 tools/python_to_souffle.py CutePetsBoston --souffle-facts-dir /tmp/cutepets-facts
mkdir -p /tmp/cutepets-effect-out
souffle -F /tmp/cutepets-facts -D /tmp/cutepets-effect-out \
  rule_layer/dataclass_effect_model.dl
```

Useful output files:

- `/tmp/cutepets-effect-out/dataclass_function.csv`
- `/tmp/cutepets-effect-out/dataclass_field_effect.csv`
- `/tmp/cutepets-effect-out/dataclass_effect.csv`
- `/tmp/cutepets-effect-out/dataclass_transformation.csv`

## Example output on CutePetsBoston

Example dataclass-to-function links:

- `AdoptablePet <- SocialPoster.format_post [param_type, pet]`
- `Post <- SocialPoster.format_post [return_type, Post]`
- `PostResult <- SocialPoster.publish [return_type, PostResult]`
- `PreparedCaption <- PosterMastodon._prepare_caption [return_type, PreparedCaption]`
- `CaptionThread <- PosterMastodon._build_caption_thread [return_type, CaptionThread]`

Example field effects:

- `AdoptablePet / SocialPoster.format_post` reads `name`, `breed`, `species`, `location`, `description`, `adoption_url`, `image_url`
- `Post / PosterBluesky.publish` reads `image_url` and `alt_text`
- `Post / PosterInstagram._format_caption` reads `text` and `tags`
- `Post / PosterMastodon._prepare_caption` reads `text` and `tags`

Example effect events:

- `AdoptablePet / SourceRescueGroups.fetch_pets` includes call effects such as `requests.post`, `response.json`, and `self._parse_animal`
- `AdoptablePet / SourceRescueGroups.fetch_pets` includes a raised exception effect for `ValueError`
- `AdoptablePet / SourceRescueGroups._parse_animal` includes an exception-handler effect for `Exception`
- `PostResult / PosterMastodon.publish` includes dataclass construction and return effects

Example dataclass transformations:

- `AdoptablePet -> Post` in `SocialPoster.format_post`
- `Post -> PostResult` in `SocialPoster.publish`
- `Post -> PreparedCaption` in `PosterMastodon._prepare_caption`
- `PreparedCaption -> CaptionThread` in `PosterMastodon._build_caption_thread`

## What the outputs mean

- `dataclass_function` links a dataclass to a function through typed parameters, typed returns, constructor returns, or constructor calls.
- `dataclass_field_effect` records field reads and writes when the dataclass is visible through a typed function parameter.
- `dataclass_effect` records generic effects in dataclass-related functions: calls, env reads, exception handling, raises, and dataclass construction or return events.
- `dataclass_transformation` approximates value-shape transitions between dataclasses across functions.

## Current limitations

- Class identity is mostly name-based, not fully import-resolved.
- Field effects currently rely on typed parameter names, so dataclass field use through aliases or untyped locals can be missed.
- `dataclass_effect` currently treats all calls inside a dataclass-related function as associated effects. That is useful for exploration but can over-approximate.
- Function-level association is still syntactic; it does not imply an exact runtime dataflow proof.
