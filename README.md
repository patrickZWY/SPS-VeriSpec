# SPS-VeriSpec

SPS-VeriSpec is an experimental static-analysis and test-generation prototype
for Python projects. It extracts Python AST facts, runs Souffle Datalog rules
over those facts, and surfaces relationships that can become executable tests
or design-review candidates.

The original experiment used `CutePetsBoston` as the target project. The current
dataclass-generalization experiments also use `dacite` as a small
dataclass-centered target and a bounded `transformers` slice as a large-library
stress target. Because these target checkouts may not be present in every clone
of this repository, clone or copy the target project locally, or pass the path
to any Python project you want to analyze.

## High-level workflow

The trusted executable pipeline today remains static. It runs the Python
extractor and the Souffle rules under `souffle_static_analysis/`, then turns the
derived CSV relations into pytest files. Optional LLM-assisted rule and oracle
lanes are quarantined review inputs: they may propose rules or tests, but they
do not silently become trusted evidence.

Evidence from the 2026-05-24 CutePetsBoston and bounded Transformers
evaluation argues against treating the current LLM-assisted rule lane as a win.
For both targets, static, LLM-only, and combined rule modes produced identical
semantic/test relation outputs: CutePetsBoston stayed at `62` relations and
`1477` rows, and the bounded Transformers slice stayed at `62` relations and
`2326` rows. The combined provenance report marked findings as `mixed`
(`2885` CutePetsBoston rows and `4966` Transformers rows), but no extra
semantic/test rows appeared. The useful LLM contribution in that run was only
the quarantined oracle lane: it produced two passing CutePetsBoston promotion
candidates and one passing Transformers promotion candidate.

```text
Python source
-> AST fact extraction (tools/python_to_souffle.py)
-> Souffle rules under souffle_static_analysis/
   (dataclass schema/effect/deduction, test-target, semantic,
    interprocedural dataflow, slicing, abstract states,
    typestate/protocol, common-AST relations)
-> optional LLM-assisted rule mode with provenance taint
-> derived CSV relations and Markdown summaries
-> conservative generated pytest tests plus quarantined review candidates
-> validation, coverage/evaluation reports, and mutation evaluation
```

The semantic/static-analysis layer is deliberately lightweight. It does not try
to prove whole-program correctness. It derives reviewable relations such as
field influence, observable output slices, boundary behavior, nullness/emptiness
states, and protocol-order candidates, then the generator turns only the
high-confidence subset into executable tests.

## Current conclusion

The Python-to-Datalog analysis pipeline is useful, but executable oracle
generation must be treated as a separate layer. The first generator was
overfit to CutePetsBoston-shaped transforms: public `format*` methods, simple
string/list observations, and dataclass-to-dataclass field flow. That pattern
does not cover many dataclass-heavy libraries.

The current LLM-assisted rule-generation path should not be presented as
improving the rule layer. In the CutePetsBoston plus bounded Transformers
comparison, it generated no additional semantic/test relation rows over static
rules. Keep it available only as an experimental provenance-tainted mode unless
a future run shows new high-quality relations that survive validation. The LLM
oracle-synthesis path is more useful because its output is explicitly
quarantined: passing synthesized tests are promotion candidates, while failing
tests are review records rather than trusted-suite failures.

The portable oracle families are now:

- runtime dataclass schema checks through `dataclasses.fields` and
  `__dataclass_params__`
- constructor/default/default-factory behavior checks
- generic conversion-profile checks for APIs such as `from_dict`, `structure`,
  `to_dict`, `asdict`, and `unstructure`
- conservative project-specific transform tests only when there is a strong
  executable oracle

`dacite` is the better near-term generalization benchmark because the full
package is small, dependency-light, and centered on dataclass conversion.
`transformers` remains useful, but mainly as a scale and dependency stress
target: full-tree extraction still needs streaming/progress-aware work, and
many modules require the target runtime dependency chain before generated tests
can be judged executable.

## Agent analysis protocol

When an agent is asked to analyze a target project, it should run the whole
pipeline and report artifacts back to the user. Do not stop after producing raw
facts or a single summary file.

Use this protocol for each target project:

1. Identify the target checkout and project name.
   - Example target path: `CutePetsBoston` or `/path/to/project`.
   - Example project name: `cutepetsboston` or another lowercase identifier.
2. Run the Python fact-inventory baseline:

   ```bash
   .venv/bin/python tools/run_static_analysis.py <target-project> \
     --engine python \
     --work-dir /tmp/sps-<project-name>-python
   ```

3. Run the Souffle static-analysis backend:

   ```bash
   .venv/bin/python tools/run_static_analysis.py <target-project> \
     --engine souffle \
     --work-dir /tmp/sps-<project-name>-souffle
   ```

   To evaluate optional LLM-assisted rule generation, run comparable static,
   LLM-only, and combined modes and compare `semantic_out/` plus `test_out/`
   rows before claiming improvement. The 2026-05-24 CutePetsBoston and bounded
   Transformers run found no semantic/test row delta for LLM-assisted rules, so
   the default recommendation remains the static trusted rule set.

4. Inspect and summarize both analysis reports:
   - `/tmp/sps-<project-name>-python/summary.md`
   - `/tmp/sps-<project-name>-souffle/summary.md`
   - Call out whether the Souffle backend derived meaningful schema,
     transformation, semantic, interprocedural, slicing, abstract-state,
     typestate, boundary, or common-AST relations.
5. Attempt generated tests from the Souffle output:

   ```bash
   .venv/bin/python tools/generate_pytest_from_properties.py \
     --analysis-dir /tmp/sps-<project-name>-souffle \
     --output-dir generated_tests \
     --project-name <project-name>
   ```

   If analysis was intentionally run on an inner package directory, pass
   `--import-prefix <top_level_package>` so generated imports match the target
   project root used during validation.

   Quarantined LLM oracle proposals can be generated from review candidates
   into `test_generated_llm_oracle_candidates.py` and `oracle_candidates.json`.
   These tests must stay outside the trusted suite until reviewed. In the
   2026-05-24 run, CutePetsBoston produced two passing promotion candidates and
   the bounded Transformers slice produced one passing promotion candidate.
6. Prepare a disposable validation environment for target dependencies.

   The main `.venv` is for SPS-VeriSpec development dependencies only. Do not
   leave large target/runtime dependencies such as PyTorch installed there after
   an experiment. Create a temporary validation venv, install only the
   dependencies needed to import the target project and run pytest, then remove
   that venv after validation/evaluation.

   ```bash
   python3 -m venv /tmp/sps-<project-name>-validation-venv
   /tmp/sps-<project-name>-validation-venv/bin/python -m pip install pytest
   /tmp/sps-<project-name>-validation-venv/bin/python -m pip install \
     -r <target-validation-requirements.txt>
   ```

   For the bounded Transformers experiment, use:

   ```bash
   /tmp/sps-transformers-validation-venv/bin/python -m pip install \
     -r validation_requirements/transformers.txt
   ```

   If a target is dependency-light, this step can be just `pytest` or the
   target's own requirements file. Missing dependencies are not equivalent to
   bad generated tests; they should be reported as dependency/import skips.

7. Validate generated tests when any executable tests are emitted:

   ```bash
   /tmp/sps-<project-name>-validation-venv/bin/python \
     tools/validate_generated_tests.py \
     generated_tests/<project-name> \
     --target-project <target-project>
   ```

   For example, installing Transformers runtime dependencies changed the bounded
   Transformers generated suite from mostly skipped to `99 passed, 8 skipped`
   for static generation and `99 passed, 7 skipped, 1 xpassed` for the combined
   LLM-oracle run.

8. Run coverage and visualization evaluation when the target has a test suite
   and generated tests are importable:

   ```bash
   /tmp/sps-<project-name>-validation-venv/bin/python \
     tools/coverage_stats.py \
     --target-project <target-project> \
     --target-tests <target-project>/tests \
     --generated-tests generated_tests/<project-name> \
     --report /tmp/sps-<project-name>-coverage.md

   /tmp/sps-<project-name>-validation-venv/bin/python \
     tools/evaluation_stats.py \
     --analysis-dir /tmp/sps-<project-name>-souffle \
     --target-project <target-project> \
     --target-tests <target-project>/tests \
     --generated-tests generated_tests/<project-name> \
     --report /tmp/sps-<project-name>-evaluation.md
   ```

9. Run mutation evaluation when generated tests and target tests both run:

   ```bash
   /tmp/sps-<project-name>-validation-venv/bin/python \
     tools/mutation_eval.py \
     --analysis-dir /tmp/sps-<project-name>-souffle \
     --target-project <target-project> \
     --target-tests <target-project>/tests \
     --generated-tests generated_tests/<project-name> \
     --max-mutants 16 \
     --report /tmp/sps-<project-name>-mutation.md
   ```

10. Clean the disposable validation environment after validation/evaluation is
    complete:

   ```bash
   rm -rf /tmp/sps-<project-name>-validation-venv
   ```

   Recreate it from the same requirements file the next time validation is
   needed. This keeps heavyweight target dependencies out of the main project
   environment and prevents stale dependency state from affecting future runs.

11. Final user report must include:
   - Commands that passed or failed.
   - Paths to Markdown reports and generated test files.
   - Generated-test pass/fail/skip counts.
   - Relation-to-test yield and coverage delta when available.
   - Mutation score and which mutants handwritten tests missed when available.
   - A short assessment of whether the analysis generalized to the new project
     and what blocked any missing stages.

If you want to reproduce the current experiment, first put the sample project at
`./CutePetsBoston`:

```bash
# from this repository root
git clone <your-cute-pets-boston-repo-url> CutePetsBoston
```

Then run the full current analysis with:

```bash
python3 tools/run_static_analysis.py CutePetsBoston \
  --engine souffle \
  --work-dir /tmp/sps-analysis-run
```

To analyze a different Python project, replace `CutePetsBoston` with that
project path:

```bash
python3 tools/run_static_analysis.py /path/to/python-project \
  --engine souffle \
  --work-dir /tmp/sps-analysis-run
```

The advanced static-analysis relations are implemented in Souffle under
`souffle_static_analysis/`. Python is still used as the frontend that extracts
AST facts and as the orchestration/reporting/test-generation layer. To run only
the Python extractor/fact-inventory baseline, without any Souffle-derived
relations:

```bash
python3 tools/run_static_analysis.py /path/to/python-project \
  --engine python \
  --work-dir /tmp/sps-python-facts-run
```

For backwards compatibility, `tools/run_souffle_models.py` still runs the
Souffle backend directly.

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
- `/tmp/sps-analysis-run/semantic_out/alias_attribute_read.csv`
- `/tmp/sps-analysis-run/semantic_out/dataclass_collection_iteration.csv`
- `/tmp/sps-analysis-run/semantic_out/asserted_dataclass_field.csv`
- `/tmp/sps-analysis-run/semantic_out/matched_dataclass_subject.csv`
- `/tmp/sps-analysis-run/semantic_out/async_obligation_candidate.csv`
- `/tmp/sps-analysis-run/semantic_out/generator_output_candidate.csv`

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
- `generated_tests/cutepetsboston/test_generated_dataclass_schema.py`
- `generated_tests/cutepetsboston/test_generated_dataclass_conversions.py`
- `generated_tests/cutepetsboston/test_generated_helper_boundaries.py`
- `generated_tests/cutepetsboston/test_generated_common_ast_properties.py`
- `generated_tests/cutepetsboston/test_generated_interprocedural_properties.py`
- `generated_tests/cutepetsboston/README.md`

The generated tests are intentionally not written into `CutePetsBoston/`.
Users can clone or copy their own target checkout and run the generated tests
from a disposable validation venv. Prefer installing target dependencies into
that temporary venv instead of the main `.venv`:

```bash
python3 -m venv /tmp/sps-cutepetsboston-validation-venv
/tmp/sps-cutepetsboston-validation-venv/bin/python -m pip install pytest
/tmp/sps-cutepetsboston-validation-venv/bin/python tools/validate_generated_tests.py \
  generated_tests/cutepetsboston \
  --target-project /path/to/CutePetsBoston
rm -rf /tmp/sps-cutepetsboston-validation-venv
```

The current generator always emits runtime dataclass schema and
constructor/default tests for discovered dataclasses. It also emits public
`format*` dataclass-transformation tests where the derived relation has a simple
string/list oracle, an optional Hypothesis-backed property test file for those
same conservative transform relations, conversion-profile tests for
`from_dict`/`structure` and `to_dict`/`asdict`/`unstructure` APIs,
lower-confidence helper-boundary tests when a private helper boundary can be
driven by a simple string input, common-AST collection tests, and
interprocedural observable-slice tests when a public method path can drive the
source dataclass to the output dataclass. It keeps publishing paths, branch-only
facts, lossy-flow candidates, interprocedural slices without strong executable
oracles, and other lower-confidence relations in the generated report until
stronger oracles are available.

The LLM oracle generator is separate from this conservative path. It writes
quarantined candidates and a manifest with provenance, oracle strength, and
validation classification. In the 2026-05-24 evaluation, these candidates
helped only as review artifacts: CutePetsBoston got two passing promotion
candidates, and the bounded Transformers slice got one passing promotion
candidate. They did not change trusted relation yield.

For the current CutePetsBoston snapshot, the static generated suite validated
with `89 passed, 2 skipped`. The combined LLM-oracle run validated with
`89 passed, 1 skipped, 2 xpassed`, and the oracle-only validation showed
`2 passed`. The dacite
generalization experiment also produces executable non-formatter tests: runtime
schema/default checks plus a `from_dict` conversion-profile oracle. A bounded
Transformers dataclass-heavy slice validates with `99 passed, 8 skipped` for
static generation and `99 passed, 7 skipped, 1 xpassed` for the combined
LLM-oracle run after installing runtime dependencies; the oracle-only validation
showed `1 passed`.

To run generated tests and write a validation summary:

```bash
/tmp/sps-<project-name>-validation-venv/bin/python \
  tools/validate_generated_tests.py \
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

The evaluation report measures how many derived relations became tests,
separates handwritten-only, generated-only, and combined source-line coverage,
and reports the coverage delta added by generated tests. It currently includes
relation-yield views for dataclass transforms, helper boundaries, common-AST
relations, and interprocedural observable-slice cases.

In the 2026-05-24 comparison, CutePetsBoston static and combined runs had the
same conservative relation yield: `24/40` transform relations, `3/5` helper
boundaries, `2/6` common-AST cases, and `4/69` interprocedural cases. The
combined source coverage was identical in both modes at `507/911` lines
(`55.7%`); the target's handwritten suite still had one pre-existing failing
Hypothesis case unrelated to generated tests. On the stable bounded
Transformers pass, static coverage was `8431/621075` lines (`1.357%`) and the
combined LLM-oracle pass was `8439/621075` lines (`1.359%`), an 8-line gain
from the quarantined oracle candidate.

To run a small mutation evaluation over relation-guided transform mutants,
common-AST collection-iteration mutants, interprocedural pipeline mutants, and
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

The mutation runner copies the target checkout, applies one mutant at a time,
and compares handwritten, generated, and combined mutation scores. Current
operators replace relation-guided field references in transform code, drop
observed collection-iteration contributions, replace pipeline stages that
participate in multi-hop interprocedural flows, tighten or weaken comparison
operators, perturb boundary constants near derived numeric bounds, and remove
simple truncation markers.

The 2026-05-24 CutePetsBoston LLM comparison used a small six-mutant diagnostic
sample because the target's handwritten suite had a pre-existing failure. Both
static and combined runs killed `6/6` mutants with handwritten, generated, and
combined suites; no mutant was killed only by the LLM-assisted candidate tests.

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

When a validation pass needs target-specific dependencies, install them in a
disposable `/tmp/sps-<project-name>-validation-venv` and delete that venv after
recording the result. Do not keep large target dependencies in the main
SPS-VeriSpec `.venv`; recreate the disposable environment when validation is
needed again.

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
- Main case studies: `CutePetsBoston` for the original end-to-end transform
  workflow, `dacite` for dataclass-generalization, and a bounded `transformers`
  slice for scale/dependency stress.
- Portability status: not systematically tested across Linux, Windows, multiple
  Python versions, or multiple Souffle versions.

## Repository map

- `CutePetsBoston/`: optional local checkout of the sample Python application
  used as the original analysis target.
- `dacite/`: optional local checkout used for the smaller dataclass conversion
  generalization experiment.
- `transformers/`: optional local checkout used for the large-library
  dataclass/dependency stress experiment.
- `tools/`: Python tooling for AST fact extraction, backend orchestration,
  generated tests, validation, coverage/evaluation, and mutation evaluation.
- `validation_requirements/`: target-specific dependency files for disposable
  validation venvs. These are not installed into the main `.venv`.
- `souffle_static_analysis/`: runnable Souffle/Datalog static-analysis backend.
  It includes schema, effect, deduction, test-target, semantic,
  interprocedural, slicing, abstract-state, typestate, and boundary rules.
- `rule_layer/`: optional LLM-assisted rule source used only in
  provenance-tainted experimental modes. The trusted static backend remains
  `souffle_static_analysis/`.
- `rule_layer_impl/`: project-specific interpretation notes for the CutePetsBoston analysis results.
- `prototype_tests/`: unit tests for the Python AST extractor and fact writer.
- `example.md`: current end-to-end workflow and examples of derived relations that can become tests.
- `souffle-prototype.md`: practical guide for extracting facts and running the Souffle models.
- `llm-rule-layer.md`: guidance for using an LLM to create or review generic Souffle rule layers.
- `dataclass-test-generation-layer.md`: design notes for turning dataclass analysis results into test targets.

## Current status

Implemented:

- Python AST fact extraction for modules, imports, classes, functions,
  dataclasses, fields, type references, calls, constructor arguments, field
  reads/writes, exceptions, environment reads, and method overrides.
- Generic Souffle dataclass schema modeling, including required/optional fields,
  default/factory-backed fields, dataclass dependencies, and dataclass shape
  summaries.
- Dataclass effect modeling for typed parameters/returns, constructor sites,
  field effects, call effects, environment reads, exceptions, and
  dataclass-to-dataclass transformations.
- Deduction rules for reachable transformations, entry/bridge/terminal
  dataclasses, field-to-transformation relations, unread required fields, and
  effectful dataclasses.
- Test-target modeling for mutable/frozen dataclasses, optional/required field
  targets, method-level transforms, field-to-constructor mappings, optional
  branch reads, and override contracts.
- Local dependency tracking through aliases and composed expressions, plus
  conservative call-result read inference.
- Dataclass option extraction for the standard `@dataclass` options:
  `init`, `repr`, `eq`, `order`, `unsafe_hash`, `frozen`, `match_args`,
  `kw_only`, `slots`, and `weakref_slot`.
- One-command analysis runner with Markdown summary output, plus separated
  backend selection for Souffle-derived analysis versus Python fact inventory.
- Optional rule modes for static, LLM-assisted, and combined Souffle runs, with
  provenance taint reported as `static`, `llm`, or `mixed`.
- Semantic field-flow, composed-flow, observable-required-field,
  lossy-field-candidate, literal-status, string-composition, numeric-boundary,
  and boundary-test derivations.
- Literal, string-composition, numeric-comparison, `len(...)`, and slice-bound
  fact extraction used by the semantic layer.
- Portable pytest generation from the conservative executable subset of
  dataclass transformation and optional-field properties.
- Portable runtime dataclass schema and constructor/default pytest generation
  for discovered dataclasses.
- Generic dataclass conversion-profile pytest generation for public
  `from_dict`, `structure`, `to_dict`, `asdict`, and `unstructure` APIs.
- Import-prefix aware generated tests for analyses run on an inner package
  directory but validated from the real project root.
- Runtime skips for static dataclass facts that resolve to non-dataclass
  optional dependency implementations in the installed target environment.
- Optional Hypothesis property-test generation for supported transformation
  properties.
- Generated-test validation runner with pass/fail/skip Markdown reports.
- Combined coverage-statistics runner for target tests plus generated tests.
- Evaluation-statistics runner for relation-to-test yield, inline SVG charts,
  handwritten/generated/combined coverage, and coverage deltas.
- Boundary-guided mutation-evaluation runner comparing handwritten, generated,
  and combined mutation scores for relation-guided transform,
  collection-iteration, interprocedural pipeline, and solver-adjacent boundary
  mutants.
- Souffle boundary-behavior relations that associate generic numeric bounds
  with dataclass inputs, primitive string returns, and helper return behavior.
- Lower-confidence helper-boundary pytest generation for simple string-length
  helper boundaries.
- Common AST fact extraction for local aliases, loop/comprehension iteration,
  assertions, context managers, await/yield expressions, pattern matching, and
  subscript access.
- Semantic relations that use common AST facts, including local-alias closure,
  alias-normalized attribute reads, dataclass collection iteration, asserted
  dataclass fields, matched dataclass subjects, async obligation candidates, and
  generator output candidates.
- Common-AST pytest generation for observable dataclass collection iteration
  relations.
- Common-AST collection-iteration mutation operators for dataclass collection
  fields such as `Post.tags`.
- Interprocedural dataflow summaries that lift local semantic field-flow facts
  into reusable function summaries, compose those summaries across dataclass
  boundaries, and derive observable output slices.
- Interprocedural generated tests for public method paths with simple
  observable string-output oracles.
- Interprocedural pipeline mutation operators for multi-hop semantic flows.
- Program-slicing candidates for backward output slices, function-local
  backward slices, external-call field slices, and control-dependence slices.
- Initial abstract-interpretation candidates for nullness, emptiness, string
  length, and status/result literals.
- Initial typestate/protocol candidates for validate/authenticate-before-publish
  and open-before-close style ordering mistakes.
- Quarantined LLM oracle candidate generation with `oracle_candidates.json`
  manifests, prompt/input hashes, source provenance, oracle strength,
  validation results, and promotion/conflict classifications.
- Validation handling for quarantined LLM oracle tests so failures are recorded
  as review records rather than trusted generated-suite failures.

Still future work:

- Promote reviewed quarantined oracle candidates into trusted generated tests
  only after human acceptance, and record why rejected candidates were weak
  or ungrounded.

- Do not invest further in the current LLM-assisted rule-generation path unless
  it starts producing additional validated semantic/test relations. The
  2026-05-24 CutePetsBoston and bounded Transformers comparison found no
  semantic/test row delta versus static rules. Preserve provenance-tainted mode
  for experiments, but prioritize the quarantined oracle lane and static rule
  quality.

- Keep quarantined LLM oracle synthesis, but treat it as review support rather
  than evidence. Passing LLM-created tests are promotion candidates; they should
  not enter the trusted generated suite without human review.

- Broaden the benchmark set beyond CutePetsBoston, dacite, and the bounded
  Transformers slice. The next targets should be small-to-medium
  dataclass-heavy projects with low dependency friction, so regressions in
  generic schema/default/conversion oracles are easy to diagnose.
- Make full-tree extraction and fact resolution streaming or progress-aware so
  very large libraries such as Transformers can be analyzed without ad hoc
  slices.
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
  tests` pipeline into an iterative analysis loop.

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
- Extend dataclass option obligations beyond the current runtime schema checks:
  constructor shape for `init`/`kw_only`, comparison and ordering behavior for
  `eq`/`order`, hashing risks for `unsafe_hash`, pattern-matching API shape for
  `match_args`, and attribute-layout behavior for `slots`/`weakref_slot`.
- Feed generated-test pass/fail/skip results back into the analysis loop.
- Improve generated reports so dependency-bound skips, assertion failures,
  human-review properties, and evaluation deltas are easier to compare across
  runs.
- Add a target-environment setup report that records installed dependencies and
  classifies validation skips as empty-case, missing-dependency, runtime-shape,
  or fixture-construction skips.
- Resolve imports and type identities more precisely.
- Add higher-precision call-boundary summaries for callbacks, generic
  containers, and dynamically selected functions.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Refine CFG/control-dependence facts beyond the current line-order slice
  candidates for more precise guarded-return and validation reasoning.
- Expand mutation testing beyond the current relation-guided transform,
  common-AST collection-iteration, interprocedural pipeline, and
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

- Lightweight points-to/may-alias analysis for local variables, object fields,
  and constructor results. Local alias and local field-dependency facts are
  implemented, but object-level and heap-level aliasing remain future work.
- Taint-style source/sink/sanitizer analysis for user input, environment
  variables, file/network data, and external API responses. Environment-read
  and external-call slice facts exist, but end-to-end source/sink/sanitizer
  classification remains future work.
- Interprocedural dataflow summary expansion for validation, sanitization,
  formatting, publish, parse, and error-result behavior. Initial field-flow
  summaries, multi-hop dataclass composition, observable slices, and a small
  executable public-path subset are implemented.
- Program slicing beyond the initial observable-output, function-backward,
  external-call, and line-order control-dependence slices, especially for logs,
  exception values, and branch-specific outputs.
- Control-dependence and guarded-return analysis beyond the current line-order
  candidates, so conditions can be linked more precisely with specific
  constructors, effects, and failure paths.
- Abstract-interpretation-style domains beyond the initial nullness, emptiness,
  string-length, numeric-bound, and status candidates, especially sign/range,
  collection size, and enum-like state.
- Typestate/protocol analysis beyond the initial event-order candidates,
  especially parse-before-field-access, open-before-read/write, transaction
  begin/commit/rollback, and async resource protocols.
- Effect and purity summaries to distinguish pure transformations from network,
  filesystem, environment, clock, randomness, or exception effects.
- Dead/unreachable relation candidates such as unused required fields,
  never-constructed dataclasses, impossible branches, and unobserved result
  fields. Unread required-field candidates are implemented; broader dead-data
  and unreachable-branch analysis remains future work.

## Important Limitation:

- Our analysis heavily relies on dataclasses so projects without dataclasses
  will not produce meaningful tests. In the future, our analysis will be
  extended to more common Python structures.

- This project is Python only so project with interoperation with other
  PLs will be impacted.
