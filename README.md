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

Those relations are not tests yet, but they are structured enough to become
test templates.

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
- Semantic field-flow, composed-flow, observable-required-field, lossy-field-candidate, literal-status, and numeric-boundary derivations.
- One-command analysis runner with Markdown summary output.

Still future work:

- Generate executable property/fuzz tests from the derived CSV relations.
- Resolve imports and type identities more precisely.
- Add more precise call-boundary summaries.
- Add branch-local return facts that connect a condition to a specific returned constructor.
- Add CFG/control-dependence facts for more precise guarded-return and validation reasoning.
- Feed test execution results back into the analysis loop.

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
