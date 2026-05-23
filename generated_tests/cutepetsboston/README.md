# Generated Test Report

- Analysis directory: `/private/tmp/sps-testgen-run`
- Test file: `generated_tests/cutepetsboston/test_generated_dataclass_properties.py`
- Executable cases emitted: 32
- Candidate relations left as review items: 16

## Run

Set `PYTHONPATH` to the target project checkout and run pytest against this directory:

```bash
PYTHONPATH=/path/to/target-project pytest generated_tests/cutepetsboston
```

## Emitted Cases

- `SocialPoster.format_post-AdoptablePet-breed-Post-text-value`: `AdoptablePet.breed` -> `text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-breed-Post-tags-value`: `AdoptablePet.breed` -> `tags` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-breed-Post-alt_text-value`: `AdoptablePet.breed` -> `alt_text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-location-Post-text-value`: `AdoptablePet.location` -> `text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-location-Post-tags-value`: `AdoptablePet.location` -> `tags` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-name-Post-text-value`: `AdoptablePet.name` -> `text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-name-Post-alt_text-value`: `AdoptablePet.name` -> `alt_text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-species-Post-text-value`: `AdoptablePet.species` -> `text` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-species-Post-tags-value`: `AdoptablePet.species` -> `tags` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-species-Post-alt_text-value`: `AdoptablePet.species` -> `alt_text` via `abstractions.SocialPoster.format_post`
- `PosterMastodon.format_post-AdoptablePet-breed-Post-text-value`: `AdoptablePet.breed` -> `text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-breed-Post-tags-value`: `AdoptablePet.breed` -> `tags` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-breed-Post-alt_text-value`: `AdoptablePet.breed` -> `alt_text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-location-Post-text-value`: `AdoptablePet.location` -> `text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-location-Post-tags-value`: `AdoptablePet.location` -> `tags` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-name-Post-text-value`: `AdoptablePet.name` -> `text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-name-Post-alt_text-value`: `AdoptablePet.name` -> `alt_text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-species-Post-text-value`: `AdoptablePet.species` -> `text` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-species-Post-tags-value`: `AdoptablePet.species` -> `tags` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-species-Post-alt_text-value`: `AdoptablePet.species` -> `alt_text` via `social_posters.mastodon.PosterMastodon.format_post`
- `SocialPoster.format_post-AdoptablePet-adoption_url-Post-link-none`: `AdoptablePet.adoption_url` -> `link` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-adoption_url-Post-link-empty`: `AdoptablePet.adoption_url` -> `link` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-adoption_url-Post-link-value`: `AdoptablePet.adoption_url` -> `link` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-image_url-Post-image_url-none`: `AdoptablePet.image_url` -> `image_url` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-image_url-Post-image_url-empty`: `AdoptablePet.image_url` -> `image_url` via `abstractions.SocialPoster.format_post`
- `SocialPoster.format_post-AdoptablePet-image_url-Post-image_url-value`: `AdoptablePet.image_url` -> `image_url` via `abstractions.SocialPoster.format_post`
- `PosterMastodon.format_post-AdoptablePet-adoption_url-Post-link-none`: `AdoptablePet.adoption_url` -> `link` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-adoption_url-Post-link-empty`: `AdoptablePet.adoption_url` -> `link` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-adoption_url-Post-link-value`: `AdoptablePet.adoption_url` -> `link` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-image_url-Post-image_url-none`: `AdoptablePet.image_url` -> `image_url` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-image_url-Post-image_url-empty`: `AdoptablePet.image_url` -> `image_url` via `social_posters.mastodon.PosterMastodon.format_post`
- `PosterMastodon.format_post-AdoptablePet-image_url-Post-image_url-value`: `AdoptablePet.image_url` -> `image_url` via `social_posters.mastodon.PosterMastodon.format_post`

## Review Candidates

- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._build_caption_thread` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon._prepare_caption` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon.publish` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon.publish` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon.publish` skipped: default generator only emits public `format*` transforms.
- `PosterMastodon.publish` skipped: default generator only emits public `format*` transforms.

## Notes

The default generator only emits public `format*` method tests with string/list observations.
Relations involving publishing, private helpers, branch-only facts, lossy flows, or non-string outputs are kept as review candidates until stronger oracles are available.
