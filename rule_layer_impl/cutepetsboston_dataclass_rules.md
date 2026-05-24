# CutePetsBoston Dataclass Rules

This file records the project-specific dataclass model for `CutePetsBoston`.
Unlike `dataclass_modeling_findings.md`, this file is intentionally tied to the
current application domain: adoptable pets, social posts, platform publish
results, and Mastodon preview pipeline values.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-slicing-ai-check
```

## Domain inventory

The current extractor discovers eight dataclasses:

- `abstractions.AdoptablePet`
- `abstractions.Post`
- `abstractions.PostResult`
- `social_posters.mastodon.PreparedCaption`
- `social_posters.mastodon.CaptionThread`
- `utils.pipeline.Phase`
- `utils.pipeline.PipelineResult`
- `utils.pipeline_preview.PreviewSection`

## Core domain types

- `AdoptablePet` is the upstream ingest record from manual or RescueGroups sources. Required fields are `name`, `species`, `breed`, and `location`; optional/defaulted fields describe adoption URL, image URL, age, sex, size, pet ID, and description.
- `Post` is the platform-neutral social media post shape. It carries text plus optional image/link/accessibility metadata and factory-backed `tags`.
- `PostResult` is the publish outcome shape. It always has `success`; platform IDs, URLs, and error text are optional.
- `PreparedCaption` and `CaptionThread` are frozen Mastodon-specific formatting stages. They model the split from a generic `Post` into thread-ready text.
- `Phase` and `PipelineResult` are generic preview/debug tracing support for the Mastodon formatting pipeline.
- `PreviewSection` is a frozen renderer descriptor for preview output.

## Shape rules

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

## Schema-level rules to preserve

- `AdoptablePet` should remain the main source-side domain record.
- `Post` should remain the platform-neutral bridge between pet ingest and platform publishers.
- Platform-specific formatting dataclasses should stay downstream of `Post`, not replace `Post` as the shared poster contract.
- `PostResult` should remain the common publish result contract for all poster implementations.
- Mastodon preview pipeline dataclasses should stay separate from core posting dataclasses because they support debugging and formatting inspection, not general publishing.

## Current schema limitations

- Type references are syntactic, so generic references such as `PipelineResult[CaptionThread]` are only approximated.
- Name-based type matching can over-link classes if two modules define the same dataclass name.
- Schema facts do not prove runtime flow; they only describe declared dataclass structure.
