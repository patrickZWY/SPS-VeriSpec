# SPS-VeriSpec

SPS-VeriSpec is an experimental static-analysis and test-generation prototype
for Python projects. It extracts Python AST facts, runs Souffle Datalog rules
over those facts, and turns high-confidence derived relations into executable
pytest tests or quarantined review candidates.

The current system is deliberately conservative. The trusted path is static:
Python fact extraction, Souffle analysis, conservative test generation, and
validation. Optional LLM-assisted lanes exist, but they stay quarantined and do
not silently become trusted evidence.

## Current conclusion

The main result so far is that relation discovery and executable-oracle
generation have to be treated separately.

- The static Python-to-Datalog pipeline is useful for surfacing reviewable
  relations such as field flow, observable output slices, boundary behavior,
  protocol-order candidates, and dataclass conversion obligations.
- The most portable executable oracles today are runtime dataclass schema
  checks, constructor/default behavior, and generic conversion-profile tests.
- The current LLM-assisted rule-generation lane should be treated as
  experimental. Recent CutePetsBoston and bounded Transformers comparisons
  showed no semantic/test relation delta over the static rule set.
- Quarantined LLM oracle and invariant-mining lanes are more useful than the
  LLM rule lane, but they remain review inputs until a human promotes them.

## Quick Start

The preferred entry point is the orchestrated runner:

```bash
python3 tools/evaluate_pipeline.py \
  --target-project /path/to/python-project \
  --project-name myproject \
  --work-dir /tmp/sps-myproject-eval
```

Optional lanes:

- `--with-static-metamorphic`
- `--with-invariants --invariant-spec /path/to/call-specs.json`
- `--with-plateau`
- `--skip-mutation`

This writes:

- `/tmp/sps-myproject-eval/pipeline_report.md`
- `/tmp/sps-myproject-eval/pipeline_report.json`

For the local visual demo workbench:

```bash
python3 -m pip install -r requirements-demo.txt
python3 -m sps_agent.server --host 127.0.0.1 --port 8765
```

The browser workbench serves checked-in replay cases by default and exposes only
allowlisted local runs through `POST /api/run`. See
[docs/agent-workbench.md](docs/agent-workbench.md).

Scheduled local runs can also enable a quarantined local-model semantic-assist
lane with `--with-plateau --with-local-llm-semantic-assist`, for example with a
Qwen model served by Ollama. The model writes proposal JSON for review and
validation; it does not promote tests into the trusted suite by itself.

If you want direct static-analysis output instead of the full orchestrated run:

```bash
python3 tools/run_static_analysis.py /path/to/python-project \
  --engine souffle \
  --work-dir /tmp/sps-analysis-run
```

## Implemented pipeline

The current pipeline includes:

- Python AST fact extraction for dataclasses, functions, calls, field
  reads/writes, exceptions, overrides, literals, boundaries, and several
  common-AST surfaces.
- Souffle rule layers for schema, effect, deduction, test-target, semantic,
  interprocedural, slicing, abstract-state, typestate/protocol, and boundary
  relations.
- Conservative pytest generation for dataclass schema/default checks,
  conversion-profile checks, selected transform relations, helper boundaries,
  common-AST collection behavior, and some interprocedural observable slices.
- Validation, coverage, evaluation, mutation, semantic generator-coverage, and
  static-analysis metamorphic evaluation runners.
- Quarantined structured-output invariant mining and quarantined plateau/LLM
  candidate generation.

## Main tools

- `tools/evaluate_pipeline.py`: orchestrated end-to-end runner.
- `tools/run_static_analysis.py`: fact extraction plus Souffle analysis.
- `tools/generate_pytest_from_properties.py`: conservative trusted test
  generation.
- `tools/validate_generated_tests.py`: generated-suite validation and report.
- `tools/evaluation_stats.py`: relation yield plus coverage summary.
- `tools/generator_coverage.py`: discovered-vs-emitted semantic family
  coverage and strict-vs-weak family counts.
- `tools/mutation_eval.py`: relation-guided mutation evaluation.
- `tools/metamorphic_eval_static_analysis.py`: stability checks for selected
  derived relations under source/fact-preserving transforms.
- `tools/mine_invariants.py`: quarantined structured-output invariant mining.
- `tools/llm_candidate_generation.py`: quarantined plateau/LLM candidate lane.

## Benchmarks

The main case studies are:

- `CutePetsBoston`: original end-to-end target.
- `dacite`: dataclass-generalization target.
- bounded `transformers`: scale and dependency-stress target.
- `type_checker_case_study/`: a separate progressive-composition case study
  where the same validated-composition idea found real bugs in a Hindley-Milner
  type checker.

## Repository map

- `souffle_static_analysis/`: trusted static rule backend.
- `rule_layer/`: experimental LLM rule lane (quarantined).
- `tools/`: analysis, generation, validation, and evaluation tooling.
- `prototype_tests/`: tests for the Python tooling.
- `validation_requirements/`: target-specific disposable validation
  environments.
- `generated_tests/`: generated artifacts from prior runs.
- `type_checker_case_study/`: separate case study and its own README.
- `docs/`: all project documentation (see below).
- `CutePetsBoston/`, `dacite/`, `transformers/`: vendored sample target
  projects.

## Limits

- The current strongest generic lane is dataclass-centered. Projects without
  meaningful dataclass structure will get less value.
- Python is the only supported source language.
- Many relation families are still review-only because strong executable
  oracles are harder than relation discovery.
- Large targets may require dependency-specific disposable validation
  environments before generated tests can be judged fairly.

## Documentation

All project documentation lives under [docs/](docs/). Start with the
[documentation index](docs/index.md), which gives a reading order and a
topic-by-topic map. Key entries:

- [docs/architecture.md](docs/architecture.md): the single-page mental model —
  the `facts -> rules -> tests` pipeline, the trusted-vs-quarantined split, and
  the directory map. The best starting point.
- [docs/motivation.md](docs/motivation.md): the research vision behind the
  project (local-only; gitignored).
- [docs/workflow.md](docs/workflow.md): practical end-to-end workflow and
  examples of derived relations becoming tests.
- [docs/extraction-and-souffle.md](docs/extraction-and-souffle.md): lower-level
  extraction and Souffle workflow.
- [docs/test-generation.md](docs/test-generation.md): design notes for the
  generic dataclass-centered generator.
- [docs/llm-rule-layer.md](docs/llm-rule-layer.md): guidance for the experimental
  LLM-assisted rule lane.
- [docs/evaluation-and-roadmap.md](docs/evaluation-and-roadmap.md): detailed
  evaluation protocol, roadmap, and research backlog.
- [docs/layers/](docs/layers/): per-layer references for the Souffle backend
  (schema, effect, deduction, semantic).
- [docs/case-studies/](docs/case-studies/): the CutePetsBoston and type-checker
  case studies.
- [type_checker_case_study/README.md](type_checker_case_study/README.md):
  progressive validated composition case study (canonical docs in place).
