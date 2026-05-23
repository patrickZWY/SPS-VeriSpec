# Generated Test Report

- Analysis directory: `/private/tmp/sps-boundary-semantics-run`
- Test file: `generated_tests/cutepetsboston/test_generated_dataclass_properties.py`
- Hypothesis test file: `generated_tests/cutepetsboston/test_generated_dataclass_hypothesis.py`
- Helper boundary test file: `generated_tests/cutepetsboston/test_generated_helper_boundaries.py`
- Executable cases emitted: 32
- Helper boundary cases emitted: 3
- Candidate relations left as review items: 16
- Helper boundary relations left as review items: 3

## Run

Set `PYTHONPATH` to the target project checkout and run pytest against this directory:

```bash
PYTHONPATH=/path/to/target-project pytest generated_tests/cutepetsboston
```

Or run through the SPS-VeriSpec validation wrapper to produce a Markdown summary:

```bash
python3 tools/validate_generated_tests.py generated_tests/cutepetsboston --target-project /path/to/target-project
```

To produce relation-yield and coverage-delta evaluation stats:

```bash
python3 tools/evaluation_stats.py --analysis-dir /private/tmp/sps-boundary-semantics-run --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/cutepetsboston --report /tmp/sps-evaluation-stats.md
```

To run mutation evaluation against handwritten, generated, and combined suites:

```bash
python3 tools/mutation_eval.py --analysis-dir /private/tmp/sps-boundary-semantics-run --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/cutepetsboston --max-mutants 12 --report /tmp/sps-mutation-eval.md
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

## Helper Boundary Cases

- `SourceRescueGroups._clean_description-description-len-text--lower_exclusive-500-below`: `adoption_sources.rescue_groups.SourceRescueGroups._clean_description` with `description` length 499; output length <= 500
- `SourceRescueGroups._clean_description-description-len-text--lower_exclusive-500-at`: `adoption_sources.rescue_groups.SourceRescueGroups._clean_description` with `description` length 500; output length <= 500
- `SourceRescueGroups._clean_description-description-len-text--lower_exclusive-500-above`: `adoption_sources.rescue_groups.SourceRescueGroups._clean_description` with `description` length 501; output length <= 500

## Helper Boundary Review Candidates

- `PosterBluesky._build_text_and_facets` boundary skipped: only `len(...)` helper boundaries are generated automatically.
- `PosterInstagram._format_caption` boundary skipped: only `len(...)` helper boundaries are generated automatically.
- `PosterMastodon._validated_main_limit` boundary skipped: only `len(...)` helper boundaries are generated automatically.

## Notes

The default generator only emits public `format*` method tests with string/list observations.
The Hypothesis file is optional at runtime and is skipped by pytest when Hypothesis is not installed.
Helper boundary tests are lower-confidence because they may call private helper methods directly.
Relations involving publishing, private helpers, branch-only facts, lossy flows, or non-string outputs are kept as review candidates until stronger oracles are available.
