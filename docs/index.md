# SPS-VeriSpec documentation

Start at the repo [README.md](../README.md) for the one-paragraph overview and
quick start. This index is the map of everything else.

## Read in this order

1. **[motivation.md](motivation.md)** — *why* the project exists: the
   informal-to-formal loop between tests and theorems. (Local-only; gitignored.)
2. **[architecture.md](architecture.md)** — *how* it fits together: the
   `facts -> rules -> tests` pipeline, the trusted-vs-quarantined split, and the
   directory map. The best single starting point for understanding the repo.
3. **[workflow.md](workflow.md)** — the practical end-to-end walkthrough: every
   stage with concrete commands, outputs, and recorded evidence.

## Reference by topic

| If you want to… | Read |
| --- | --- |
| Run the pipeline end to end with commands | [workflow.md](workflow.md) |
| Understand fact extraction + per-model Souffle commands | [extraction-and-souffle.md](extraction-and-souffle.md) |
| Understand how relations become tests (generator design) | [test-generation.md](test-generation.md) |
| Use the stage-by-stage evaluation protocol + see the roadmap/backlog | [evaluation-and-roadmap.md](evaluation-and-roadmap.md) |
| Work on the experimental LLM rule lane (prompts, fact schema) | [llm-rule-layer.md](llm-rule-layer.md) |

## Souffle rule-layer references

The trusted backend (`souffle_static_analysis/*.dl`) runs in layers. Each has a
reference describing how to run it, its outputs, and what they mean:

- [layers/schema.md](layers/schema.md) — dataclass inventory and shapes
- [layers/effect.md](layers/effect.md) — dataclass↔effect associations
- [layers/deduction.md](layers/deduction.md) — reachable transforms and topology
- [layers/semantic.md](layers/semantic.md) — value flows, slices, boundaries, abstract states, protocols

## Case studies

- [case-studies/cutepetsboston.md](case-studies/cutepetsboston.md) — the original
  target, with the concrete project-specific rules/findings for every layer.
- [case-studies/type-checker.md](case-studies/type-checker.md) — the separate,
  self-contained progressive-composition experiment (docs live in
  [`type_checker_case_study/`](../type_checker_case_study/)).
