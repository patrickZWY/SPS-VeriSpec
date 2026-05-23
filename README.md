# SPS-VeriSpec

SPS-VeriSpec is an experimental static-analysis and test-generation prototype
for Python projects. It extracts Python AST facts, runs Souffle Datalog rules
over those facts, and surfaces relationships that can become executable tests
or design-review candidates.

The current experiment uses `CutePetsBoston` as the target project. Because
that sample app may not be checked into every clone of this repository, clone or
copy a local version of CutePetsBoston into this repo as `CutePetsBoston/`, or
pass the path to any Python project you want to analyze.

## High-level workflow

```text
Python source
-> AST fact extraction
-> Souffle rule layers
-> derived CSV relations and Markdown summaries
-> generated-test candidates / design review
```

If you want to reproduce the current experiment, first put the sample project at
`./CutePetsBoston`:

```bash
# from this repository root
git clone <your-cute-pets-boston-repo-url> CutePetsBoston
```

Then run the full current analysis with:

```bash
python3 tools/run_souffle_models.py CutePetsBoston --work-dir /tmp/sps-analysis-run
```

To analyze a different Python project, replace `CutePetsBoston` with that
project path:

```bash
python3 tools/run_souffle_models.py /path/to/python-project --work-dir /tmp/sps-analysis-run
```

Then inspect:

```bash
sed -n '1,280p' /tmp/sps-analysis-run/summary.md
```

Useful relation outputs include:

- `/tmp/sps-analysis-run/test_out/method_field_to_constructor_arg.csv`
- `/tmp/sps-analysis-run/test_out/transform_optional_field_test_target.csv`
- `/tmp/sps-analysis-run/test_out/transform_required_field_test_target.csv`
- `/tmp/sps-analysis-run/test_out/override_dataclass_contract.csv`
- `/tmp/sps-analysis-run/deduction_out/unread_required_field.csv`
- `/tmp/sps-analysis-run/semantic_out/semantic_field_flow.csv`
- `/tmp/sps-analysis-run/semantic_out/composed_semantic_field_flow.csv`
- `/tmp/sps-analysis-run/semantic_out/observable_required_field.csv`
- `/tmp/sps-analysis-run/semantic_out/lossy_required_field_candidate.csv`
- `/tmp/sps-analysis-run/semantic_out/boundary_test_candidate.csv`
- `/tmp/sps-analysis-run/semantic_out/boundary_behavior.csv`
- `/tmp/sps-analysis-run/semantic_out/helper_boundary_behavior.csv`

To generate portable pytest tests from the conservative executable subset of
the derived properties, keep the tests outside the analyzed project:

```bash
python3 tools/generate_pytest_from_properties.py \
  --analysis-dir /tmp/sps-analysis-run \
  --output-dir generated_tests \
  --project-name cutepetsboston
```

This writes:

- `generated_tests/cutepetsboston/test_generated_dataclass_properties.py`
- `generated_tests/cutepetsboston/test_generated_dataclass_hypothesis.py`
- `generated_tests/cutepetsboston/test_generated_helper_boundaries.py`
- `generated_tests/cutepetsboston/README.md`

The generated tests are intentionally not written into `CutePetsBoston/`.
Users can clone or copy their own target checkout, install its dependencies,
and run the generated tests with the target project on `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/CutePetsBoston pytest generated_tests/cutepetsboston
```

The current generator emits public `format*` dataclass-transformation tests
where the derived relation has a simple string/list oracle. It also emits an
optional Hypothesis-backed property test file for the same conservative
relations. It also emits lower-confidence helper-boundary tests when a private
helper boundary can be driven by a simple string input. It keeps publishing
paths, branch-only facts, lossy-flow candidates, and other lower-confidence
relations in the generated report until stronger oracles are available.

To run generated tests and write a validation summary:

```bash
python3 tools/validate_generated_tests.py \
  generated_tests/cutepetsboston \
  --target-project /path/to/CutePetsBoston
```

To measure how much target source coverage the target tests and generated tests
cover together:

```bash
python3 tools/coverage_stats.py \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --report /tmp/sps-coverage-stats.md
```

To produce a broader evaluation report with inline SVG charts, relation-to-test
yield, and coverage deltas for handwritten, generated, and combined suites:

```bash
python3 tools/evaluation_stats.py \
  --analysis-dir /tmp/sps-analysis-run \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --report /tmp/sps-evaluation-stats.md
```

To run a small mutation evaluation over relation-guided transform mutants and
solver-adjacent boundary mutants:

```bash
python3 tools/mutation_eval.py \
  --analysis-dir /tmp/sps-analysis-run \
  --target-project /path/to/CutePetsBoston \
  --target-tests /path/to/CutePetsBoston/tests \
  --generated-tests generated_tests/cutepetsboston \
  --max-mutants 12 \
  --report /tmp/sps-mutation-eval.md
```

## What this project is trying to achieve

The goal is to make testing more automated and iterative. Instead of relying
only on manually written tests, the project tries to infer useful program
relationships first, then use those relationships to propose or generate tests
that can surface potential bugs or design inconsistencies.

For example, the analyzer can currently surface relations such as:

- `AdoptablePet.name -> Post.alt_text`
- `AdoptablePet.image_url -> Post.image_url`
- `Post.image_url` is checked by Mastodon publish readiness logic
- concrete poster classes implement `SocialPoster.publish(Post) -> PostResult`
- `AdoptablePet.name` is observable through string-valued output fields
- `PostResult.success` is constructed from explicit boolean literals
- numeric/string bounds such as `len(text) > 500` and `text[:497]` produce boundary-test candidates
- boundary-level semantics connect generic bounds to platform behavior such as
  Instagram caption max length and RescueGroups description truncation

Those relations are not tests yet, but they are structured enough to become
test templates.

## Project metadata

- Research prototype, not a finished verification system.
- Coding agent: OpenAI Codex through `codex-cli 0.133.0`.
- Codex model: Codex based on GPT-5.
- Tested OS: macOS on Darwin `24.6.0`, `x86_64`.
- Python: `3.12.0`.
- Souffle: `2.5`.
- pytest: `9.0.3` inside the local `.venv`.
- Main case study: `CutePetsBoston`.
- Portability status: not systematically tested across Linux, Windows, multiple
  Python versions, or multiple Souffle versions.

## Repository map

- `CutePetsBoston/`: optional local checkout of the sample Python application used as the current analysis target.
- `tools/`: Python tooling for AST fact extraction and one-command Souffle model execution.
- `rule_layer/`: generic reusable Souffle Datalog models and base fact declarations.
  It includes schema, effect, deduction, test-target, and semantic models.
- `rule_layer_impl/`: project-specific interpretation notes for the CutePetsBoston analysis results.
- `prototype_tests/`: unit tests for the Python AST extractor and fact writer.
- `example.md`: current end-to-end workflow and examples of derived relations that can become tests.
- `motivation.md`: project motivation and research questions around iterative test generation.
- `souffle-prototype.md`: practical guide for extracting facts and running the Souffle models.
- `llm-rule-layer.md`: guidance for using an LLM to create or review generic Souffle rule layers.
- `dataclass-test-generation-layer.md`: design notes for turning dataclass analysis results into test targets.

## Current status

Implemented:

- Python AST fact extraction.
- Generic dataclass schema, effect, deduction, test-target, and semantic Souffle models.
- Local dependency tracking through aliases and composed expressions.
- Conservative call-result read inference.
- Literal, string-composition, numeric-comparison, `len(...)`, and slice-bound fact extraction.
- Semantic field-flow, composed-flow, observable-required-field,
  lossy-field-candidate, literal-status, numeric-boundary, and boundary-behavior
  derivations.
- One-command analysis runner with Markdown summary output.
- Portable pytest generation from a conservative subset of derived dataclass
  transformation properties.
- Optional Hypothesis property-test generation for supported transformation
  properties.
- Lower-confidence helper-boundary pytest generation for simple string-length
  helper boundaries.
- Generated-test validation runner with pass/fail/skip Markdown reports.
- Combined coverage-statistics runner for target tests plus generated tests.
- Evaluation-statistics runner for relation-to-test yield and coverage deltas.
- Boundary-guided mutation-evaluation runner for handwritten, generated, and
  combined mutation scores.
- Souffle boundary-behavior relations that associate generic numeric bounds
  with dataclass inputs, primitive string returns, and helper return behavior.

Still future work:

- Expand executable property/fuzz tests from more derived CSV relations,
  especially public boundary, branch-condition, and combination-heavy
  properties.
- Feed generated-test pass/fail/skip results back into the analysis loop.
- Improve generated reports so dependency-bound skips, assertion failures,
  human-review properties, and evaluation deltas are easier to compare across
  runs.
- Resolve imports and type identities more precisely.
- Add more precise call-boundary summaries.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Add CFG/control-dependence facts for more precise guarded-return and validation reasoning.
- Expand mutation testing beyond the current relation-guided transform and
  solver-adjacent boundary mutants.
- Explore concolic testing and solver-aided test generation so path conditions
  and boundary constraints can be solved rather than sampled.
- Compute deeper coverage and relation-coverage statistics, such as branch
  coverage, dataclass-field coverage, derived-property coverage, and the
  percentage of high-confidence relations backed by executable tests. Basic
  line coverage, relation-to-test yield, coverage deltas, and mutation score
  are implemented.
- Use `boundary_behavior.csv` and `helper_boundary_behavior.csv` directly in
  executable test generation instead of relying only on raw numeric-bound facts.

Potential static-analysis directions:

- Lightweight points-to/may-alias analysis for local variables, object fields, and constructor results.
- Taint-style source/sink/sanitizer analysis for user input, environment variables, file/network data, and external API responses.
- Interprocedural dataflow summaries for validation, sanitization, formatting, publish, parse, and error-result behavior.
- Program slicing over observable outputs such as return dataclasses, status fields, exceptions, logs, and external calls.
- Control-dependence and guarded-return analysis to connect conditions with specific constructors, effects, and failure paths.
- Abstract-interpretation-style domains for nullness, emptiness, sign/range, string length, collection size, and enum-like state.
- Typestate/protocol analysis for order-sensitive APIs such as authenticate-before-publish, validate-before-use, open-before-read/write, and parse-before-field-access.
- Effect and purity summaries to distinguish pure transformations from network, filesystem, environment, clock, randomness, or exception effects.
- Dead/unreachable relation candidates such as unused required fields, never-constructed dataclasses, impossible branches, and unobserved result fields.
