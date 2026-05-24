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
- `/tmp/sps-analysis-run/semantic_out/function_summary_input_to_output.csv`
- `/tmp/sps-analysis-run/semantic_out/call_parameter_binding.csv`
- `/tmp/sps-analysis-run/semantic_out/interprocedural_local_field_flow.csv`
- `/tmp/sps-analysis-run/semantic_out/interprocedural_method_transform.csv`
- `/tmp/sps-analysis-run/semantic_out/backward_output_slice.csv`
- `/tmp/sps-analysis-run/semantic_out/function_backward_slice.csv`
- `/tmp/sps-analysis-run/semantic_out/external_call_field_slice.csv`
- `/tmp/sps-analysis-run/semantic_out/control_dependence_slice.csv`
- `/tmp/sps-analysis-run/semantic_out/abstract_value_state.csv`
- `/tmp/sps-analysis-run/semantic_out/abstract_numeric_state.csv`
- `/tmp/sps-analysis-run/semantic_out/nullable_use_before_guard_candidate.csv`
- `/tmp/sps-analysis-run/semantic_out/protocol_obligation_candidate.csv`
- `/tmp/sps-analysis-run/semantic_out/typestate_protocol_violation.csv`
- `/tmp/sps-analysis-run/semantic_out/interprocedural_field_flow.csv`
- `/tmp/sps-analysis-run/semantic_out/multi_hop_interprocedural_field_flow.csv`
- `/tmp/sps-analysis-run/semantic_out/observable_output_slice.csv`
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
- `generated_tests/cutepetsboston/test_generated_common_ast_properties.py`
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
relations, lower-confidence helper-boundary tests when a private helper
boundary can be driven by a simple string input, common-AST collection tests,
and interprocedural observable-slice tests when a public method path can drive
the source dataclass to the output dataclass. It keeps publishing paths,
branch-only facts, lossy-flow candidates, interprocedural slices without strong
executable oracles, and other lower-confidence relations in the generated
report until stronger oracles are available.

For the current CutePetsBoston snapshot, the generated suite contains 73 tests
and validates cleanly against the local target checkout.

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

## Development requirement

Every feature addition or behavior-changing edit should include an evaluation
pass that records what changed. At minimum, re-run the generated-test
validation and the relevant evaluation commands for the changed behavior:

- `tools/validate_generated_tests.py` for generated-test pass/fail/skip changes.
- `tools/coverage_stats.py` or `tools/evaluation_stats.py` for coverage,
  relation-to-test yield, and coverage-delta changes.
- `tools/mutation_eval.py` when the change affects generated tests, boundary
  behavior, relation-guided transforms, or mutation-relevant logic.

Include the before/after result or a short note explaining why a command was not
applicable. This keeps new features tied to measurable analysis and testing
effects instead of only implementation changes.

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

The important research bet is not simply that Datalog can hold many extracted
facts. The useful outcome depends on deriving interesting relations: semantic,
behavioral, or cross-cutting properties that are hard to notice from one local
syntax node. Purely syntactic or structural relations are still useful as raw
material, but they should not be treated as success by themselves. A relation is
valuable when it helps generate a compact, nontrivial test, exposes a hidden
dependency, or explains a behavior-level obligation such as a boundary,
observable output, status result, or contract conformance case.

As the rule layer grows, relation quality should be evaluated alongside
quantity. Large relation sets that are mostly local AST shape, type plumbing, or
long brittle joins are a warning sign: they may be too noisy to compose into
tests developers can understand. Prefer relation layers that compress low-level
facts into higher-level test obligations with clear oracles.

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
- Common AST fact extraction for local aliases, loop/comprehension iteration,
  assertions, context managers, await/yield expressions, pattern matching, and
  subscript access.
- Semantic field-flow, composed-flow, observable-required-field,
  lossy-field-candidate, literal-status, numeric-boundary, and boundary-behavior
  derivations.
- Semantic relations that use common AST facts, including local-alias closure,
  alias-normalized attribute reads, dataclass collection iteration, asserted
  dataclass fields, matched dataclass subjects, async obligation candidates, and
  generator output candidates.
- Interprocedural dataflow summaries that lift local semantic field-flow facts
  into reusable function summaries, compose those summaries across dataclass
  boundaries, and derive observable output slices.
- Program-slicing candidates for backward output slices, function-local
  backward slices, external-call field slices, and control-dependence slices.
- Initial abstract-interpretation candidates for nullness, emptiness, string
  length, and status/result literals.
- Initial typestate/protocol candidates for validate/authenticate-before-publish
  and open-before-close style ordering mistakes.
- Dataclass option extraction for the standard `@dataclass` options:
  `init`, `repr`, `eq`, `order`, `unsafe_hash`, `frozen`, `match_args`,
  `kw_only`, `slots`, and `weakref_slot`.
- One-command analysis runner with Markdown summary output.
- Portable pytest generation from a conservative subset of derived dataclass
  transformation properties.
- Optional Hypothesis property-test generation for supported transformation
  properties.
- Lower-confidence helper-boundary pytest generation for simple string-length
  helper boundaries.
- Common-AST pytest generation for observable dataclass collection iteration
  relations.
- Generated-test validation runner with pass/fail/skip Markdown reports.
- Combined coverage-statistics runner for target tests plus generated tests.
- Evaluation-statistics runner for relation-to-test yield and coverage deltas.
- Boundary-guided mutation-evaluation runner for handwritten, generated, and
  combined mutation scores.
- Common-AST collection-iteration mutation operators for dataclass collection
  fields such as `Post.tags`.
- Souffle boundary-behavior relations that associate generic numeric bounds
  with dataclass inputs, primitive string returns, and helper return behavior.

Still future work:

Priority next steps:

- Validate generality on a second project. Every claim of generality currently
  rests on `CutePetsBoston`. Run the full pipeline against at least one other
  Python project (a Flask service, a CLI tool, or any non-trivial codebase),
  record which rules fire, which generated tests survive, and publish the
  delta. This single experiment tells us more about the rule layer than more
  relations on the existing case study.
- Tighten or measure oracle strength in generated tests. The current
  `_assert_observed` helper in
  `generated_tests/cutepetsboston/test_generated_dataclass_properties.py`
  accepts substring match, lowercase-normalized match, comma-prefix
  capitalization, and list-contains. Either replace loose assertions with
  exact equality where the analysis supports it, or report what fraction of
  generated tests have a strict-equality oracle versus a loose one in the
  evaluation report. Passing rate without oracle strength is not evidence.
- Close the informal-to-formal loop by one step. When a generated test fails,
  surface the Datalog relation that produced it and let a human accept,
  reject, or refine that relation. Persist the decision so accepted relations
  feed the next analysis round and rejected ones are demoted. This is the
  minimum feedback path that turns the current one-way `facts -> rules ->
  tests` pipeline into the iterative loop described in `motivation.md`.

- Continue the AST coverage audit. The extractor now captures several common
  syntax surfaces beyond dataclass flows, but the standard `ast` grammar still
  includes nodes that are not represented as facts. Missing syntax should be
  tracked by whether it can support semantic relations and test obligations,
  not by raw node-count completeness alone.
- Expand executable interprocedural tests beyond simple observable string
  slices, especially optional string outputs, collection outputs, and status
  dataclasses.
- Expand executable property/fuzz tests from more derived CSV relations,
  especially public boundary, branch-condition, and combination-heavy
  properties.
- Turn dataclass options beyond `frozen` into executable obligations: constructor
  shape for `init`/`kw_only`, comparison and ordering behavior for `eq`/`order`,
  hashing risks for `unsafe_hash`, pattern-matching API shape for `match_args`,
  and attribute-layout behavior for `slots`/`weakref_slot`.
- Feed generated-test pass/fail/skip results back into the analysis loop.
- Improve generated reports so dependency-bound skips, assertion failures,
  human-review properties, and evaluation deltas are easier to compare across
  runs.
- Resolve imports and type identities more precisely.
- Add higher-precision call-boundary summaries for callbacks, generic
  containers, and dynamically selected functions.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Refine CFG/control-dependence facts beyond the current line-order slice
  candidates for more precise guarded-return and validation reasoning.
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
- Expand common-AST generated tests beyond the current observable dataclass
  collection iteration template, especially asserted field obligations,
  pattern-match cases, async result handling, and generator output behavior.

Potential static-analysis directions:

- Lightweight points-to/may-alias analysis for local variables, object fields, and constructor results.
- Taint-style source/sink/sanitizer analysis for user input, environment variables, file/network data, and external API responses.
- Interprocedural dataflow summary expansion for validation, sanitization,
  formatting, publish, parse, and error-result behavior. An initial field-flow
  summary and observable-slice layer is implemented.
- Expand program slicing beyond the initial observable-output, external-call,
  and control-dependence slices, especially for logs, exception values, and
  branch-specific outputs.
- Refine control-dependence and guarded-return analysis to connect conditions
  with specific constructors, effects, and failure paths.
- Expand abstract-interpretation-style domains beyond the initial nullness,
  emptiness, string-length, and status candidates, especially sign/range,
  collection size, and enum-like state.
- Expand typestate/protocol analysis beyond the initial event-order candidates,
  especially parse-before-field-access, open-before-read/write, transaction
  begin/commit/rollback, and async resource protocols.
- Effect and purity summaries to distinguish pure transformations from network, filesystem, environment, clock, randomness, or exception effects.
- Dead/unreachable relation candidates such as unused required fields, never-constructed dataclasses, impossible branches, and unobserved result fields.
