# Architecture overview

This is the single-page mental model of how SPS-VeriSpec fits together. It
synthesizes the detail that the other docs cover stage by stage; follow the
links for specifics.

## The core idea

SPS-VeriSpec turns ordinary Python into reviewable static relations, then turns
the high-confidence ones into executable pytest tests. The pipeline is one-way
today (`facts -> rules -> tests`), and deliberately **conservative**: a clear
line separates a **trusted** static path from **quarantined** experimental lanes
that stay review-only until a human promotes them. The research motivation behind
this — the informal-to-formal loop between tests and theorems — is in
[motivation.md](motivation.md).

## The trusted pipeline

```
Python project
     │
     ▼
1. Fact extraction          tools/python_to_souffle.py
     │  emits one .facts file per relation (dataclasses, functions, calls,
     │  field reads/writes, literals, boundaries, AST surfaces, ...)
     ▼
2. Souffle rule layers      souffle_static_analysis/*.dl   (the "static" engine)
     │  schema → effect → deduction → test-target → semantic
     │  derives reviewable relations (CSV outputs)
     ▼
3. Test generation          tools/generate_pytest_from_properties.py
     │  conservative, executable subset → generated_tests/<project>/
     │  everything else is reported as review candidates
     ▼
4. Validation               tools/validate_generated_tests.py
     │  runs the generated suite against a target checkout (pass/fail/skip)
     ▼
5. Evaluation               coverage_stats / evaluation_stats /
        generator_coverage / mutation_eval / metamorphic_eval_static_analysis
```

The orchestrated entry point that runs the whole thing is
`tools/evaluate_pipeline.py`. The lower-level extraction + Souffle runner is
`tools/run_static_analysis.py` (with `--engine python` for the extractor-only
baseline or `--engine souffle` for the full backend).

- Stage-by-stage commands and evidence: [workflow.md](workflow.md)
- Extraction + per-model Souffle commands: [extraction-and-souffle.md](extraction-and-souffle.md)
- The full evaluation protocol + roadmap: [evaluation-and-roadmap.md](evaluation-and-roadmap.md)

## The Souffle rule layers

Each layer consumes the `.facts` from extraction (and the outputs of earlier
layers) and adds a level of abstraction. Per-layer references live in
[`layers/`](layers/):

| Layer | Source `.dl` | Reference | Derives |
| --- | --- | --- | --- |
| Schema | `dataclass_schema_model.dl` | [layers/schema.md](layers/schema.md) | dataclass inventory, field shapes, dependencies |
| Effect | `dataclass_effect_model.dl` | [layers/effect.md](layers/effect.md) | dataclass↔function links, field effects, transformations |
| Deduction | `dataclass_deduction_model.dl` | [layers/deduction.md](layers/deduction.md) | reachable transforms, topology, unread-field blind spots |
| Test-target | `dataclass_test_model.dl` | (see [test-generation.md](test-generation.md)) | mutability/optional/override test targets, field→ctor flows |
| Semantic | `semantic_model.dl` | [layers/semantic.md](layers/semantic.md) | field flows, slices, boundaries, abstract states, protocols |

How the generator turns these relations into tests (and which stay review-only)
is described in [test-generation.md](test-generation.md).

## Trusted vs. quarantined

| | Trusted (static) | Quarantined (experimental) |
| --- | --- | --- |
| Rule backend | `souffle_static_analysis/` | `rule_layer/` (LLM rule lane — see its [README](../rule_layer/README.md)) |
| Test lanes | `generate_pytest_from_properties.py` | `oracle_synthesis.py`, `mine_invariants.py`, `llm_candidate_generation.py` |
| Status | the supported path | review inputs only, until a human promotes them |

The latest evidence shows the LLM **rule** lane adds no relation delta over the
static rules; the quarantined LLM **oracle** and invariant-mining lanes are more
useful but still review-only. See [llm-rule-layer.md](llm-rule-layer.md).

## Directory map

| Path | Role |
| --- | --- |
| `tools/` | analysis, generation, validation, and evaluation tooling |
| `souffle_static_analysis/` | trusted static rule backend (`.dl`) |
| `rule_layer/` | experimental LLM rule lane (`.dl`) |
| `prototype_tests/` | tests for the Python tooling |
| `generated_tests/` | generated artifacts from prior runs |
| `validation_requirements/` | target-specific disposable validation environments |
| `docs/` | all project documentation (this directory) |
| `type_checker_case_study/` | separate, self-contained case study (see [case-studies/type-checker.md](case-studies/type-checker.md)) |
| `CutePetsBoston/`, `dacite/`, `transformers/` | vendored sample target projects |

## Benchmarks

- **CutePetsBoston** — the original end-to-end target ([case study](case-studies/cutepetsboston.md)).
- **dacite** — small, dataclass-centered generalization target; the clean near-term proof target.
- **bounded transformers** — scale and dependency-stress target.
- **type-checker** — the separate progressive-composition case study ([case study](case-studies/type-checker.md)).
