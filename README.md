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
-> future generated tests / design review
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

## What this project is trying to achieve

The goal is to make testing more automatic and iterative. Instead of relying
only on manually written tests, the project tries to infer useful program
relationships first, then use those relationships to propose or generate tests.

For example, the analyzer can currently surface relations such as:

- `AdoptablePet.name -> Post.alt_text`
- `AdoptablePet.image_url -> Post.image_url`
- `Post.image_url` is checked by Mastodon publish readiness logic
- concrete poster classes implement `SocialPoster.publish(Post) -> PostResult`

Those relations are not tests yet, but they are structured enough to become
test templates.

## Repository map

- `CutePetsBoston/`: optional local checkout of the sample Python application used as the current analysis target.
- `tools/`: Python tooling for AST fact extraction and one-command Souffle model execution.
- `rule_layer/`: generic reusable Souffle Datalog models and base fact declarations.
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
- Generic dataclass schema, effect, deduction, and test-target Souffle models.
- Local dependency tracking through aliases and composed expressions.
- Conservative call-result read inference.
- One-command analysis runner with Markdown summary output.

Still future work:

- Generate executable property/fuzz tests from the derived CSV relations.
- Resolve imports and type identities more precisely.
- Add more precise call-boundary summaries.
- Preserve key literal data such as numbers, bounds, limits, and thresholds during fact extraction for future boundary-test generation.
- Feed test execution results back into the analysis loop.
