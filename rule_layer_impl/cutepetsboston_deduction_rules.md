# CutePetsBoston Dataclass Deduction Rules

This file records project-specific deductions from the generic dataclass schema
and effect layers. These are useful for reviewing the current application
architecture and for deciding where extractor precision should improve next.

Generated with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/cutepets-project-rules
```

## Current deduction summary

- Dataclasses discovered: 8
- Direct dataclass transformations: 12
- Reachable dataclass transformation pairs: 9
- Dataclass-linked functions: 66

## Direct transformation rules

Current direct transformation edges:

- `abstractions.AdoptablePet -> abstractions.Post`
- `abstractions.AdoptablePet -> social_posters.mastodon.CaptionThread`
- `abstractions.AdoptablePet -> utils.pipeline.PipelineResult`
- `abstractions.Post -> abstractions.PostResult`
- `abstractions.Post -> social_posters.mastodon.PreparedCaption`
- `social_posters.mastodon.PreparedCaption -> social_posters.mastodon.CaptionThread`

The repeated `Post -> PostResult` edge appears through the abstract poster
contract plus Bluesky, Debug, Instagram, and Mastodon implementations.

## Reachability rules

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

## Topology rules

- Entry dataclass: `abstractions.AdoptablePet`
- Bridge dataclasses: `abstractions.Post`, `social_posters.mastodon.PreparedCaption`
- Terminal dataclasses: `abstractions.PostResult`, `social_posters.mastodon.CaptionThread`, `utils.pipeline.PipelineResult`

`utils.pipeline.Phase` and `utils.pipeline_preview.PreviewSection` are currently
classified as both entry-like or terminal-like helper shapes because they do not
participate in the main transformation graph. Treat them as tooling dataclasses,
not business-domain endpoints.

## Blind-spot rules

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

## Project-specific verification targets

- Verify that every concrete `SocialPoster.publish` returns `PostResult` on all success and failure paths.
- Verify that platform publish paths either require or gracefully handle missing `Post.image_url`.
- Verify that `AdoptablePet` records selected for posting always have `image_url` and `adoption_url`.
- Verify that Mastodon caption splitting preserves the relation `Post.text -> PreparedCaption.caption_text -> CaptionThread.main_caption/replies`.
- Verify that Slack failure notification remains outside the dataclass transformation graph unless a future alert-result dataclass is introduced.

## Recommended extractor improvements for this project

- Resolve generic type arguments for `PipelineResult[CaptionThread]`.
- Add better class identity resolution across imports to avoid name-only joins.
- Add branch-local return facts that connect specific optional-field checks to specific returned constructors.
- Add more precise call-boundary summaries so SDK/API return values do not over-approximate semantic influence.
