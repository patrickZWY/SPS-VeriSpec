# Detailed protocol and roadmap

This file holds the material that is too detailed for the top-level README:
the full evaluation protocol, the current research backlog, and longer-term
static-analysis directions.

## Detailed evaluation protocol

Use this when you need a stage-by-stage run instead of the single
`tools/evaluate_pipeline.py` entry point.

1. Identify the target checkout and project name.
2. Prefer `tools/evaluate_pipeline.py` for a consolidated run.
3. Run `tools/run_static_analysis.py --engine python` when you want the
   extractor-only baseline.
4. Run `tools/run_static_analysis.py --engine souffle` when you need the raw
   analysis directory or want to compare static versus experimental rule modes.
5. Inspect the generated summary reports and selected derived relations.
6. Run `tools/generate_pytest_from_properties.py` to emit conservative trusted
   tests.
7. Create a disposable validation environment for target dependencies.
8. Run `tools/validate_generated_tests.py`.
9. Optionally run `tools/mine_invariants.py` with replayable call specs.
10. Optionally run `tools/metamorphic_eval_static_analysis.py`.
11. Run `tools/coverage_stats.py` and `tools/evaluation_stats.py` when the
    target has runnable tests.
12. Run `tools/generator_coverage.py` to measure discovered-vs-emitted
    semantic families and strict-vs-weak family counts.
13. Run `tools/mutation_eval.py` when handwritten and generated tests both run.
14. Remove the disposable validation environment.
15. Record command outcomes, artifact paths, pass/fail/skip counts, yield,
    coverage, mutation score, and blockers.

The more practical walkthroughs live in:

- [../example.md](../example.md)
- [../souffle-prototype.md](../souffle-prototype.md)

## Current detailed backlog

Priority next work:

- Persist pipeline metrics across runs so deltas are diffable across commits
  and targets instead of staying as isolated per-run artifacts.
- Add wall-clock and peak-memory profiling for extraction, Souffle solving,
  validation, invariant mining, and mutation evaluation.
- Promote quarantined oracle candidates into trusted generated tests only after
  human review, and record why rejected candidates were weak or ungrounded.
- Tighten per-assertion oracle-strength accounting beyond the current
  family-level strict/weak reporting.
- Close the feedback loop from failing generated tests back to the originating
  relation so accepted/rejected decisions affect later runs.

Still open:

- Broaden the benchmark set beyond CutePetsBoston, dacite, bounded
  Transformers, and the type-checker case study.
- Make full-tree extraction and fact resolution more progress-aware for very
  large targets.
- Expand executable interprocedural tests beyond simple observable string
  slices.
- Expand executable property/fuzz tests from more boundary, branch-condition,
  and combination-heavy relations.
- Extend dataclass option obligations beyond current runtime schema checks.
- Improve report quality around dependency-bound skips, assertion failures, and
  review-only properties.
- Improve import and type-identity resolution.
- Add higher-precision callback/container/dynamic call-boundary summaries.
- Refine guarded-return and control-dependence reasoning.
- Expand mutation operators beyond the current relation-guided transform,
  collection-iteration, interprocedural pipeline, and solver-adjacent boundary
  set.
- Explore solver-aided or concolic generation for path and boundary conditions.
- Expand deeper coverage metrics such as branch coverage, dataclass-field
  coverage, derived-relation coverage, and high-confidence executable coverage.
- Use `boundary_behavior.csv` and `helper_boundary_behavior.csv` more directly
  in executable generation.
- Expand common-AST generated tests beyond collection-iteration cases.

## Potential static-analysis directions

- Lightweight points-to or may-alias analysis for locals, object fields, and
  constructor results.
- Taint-style source/sink/sanitizer analysis for environment, file, network,
  and API flows.
- Stronger interprocedural summaries for validation, sanitization, formatting,
  parsing, publish, and error-result behavior.
- Program slicing beyond the current observable-output, function-backward,
  external-call, and line-order control-dependence candidates.
- More precise control-dependence and guarded-return analysis.
- Richer abstract domains for sign/range, collection size, and enum-like state.
- Richer typestate or protocol modeling beyond the current event-order
  candidates.
- Effect and purity summaries.
- Dead-data and unreachable-branch candidates beyond unread required fields.
