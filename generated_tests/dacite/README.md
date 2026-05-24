# Generated Test Report

- Analysis directory: `/private/tmp/sps-dacite-souffle`
- Import prefix: `dacite`
- Test file: `generated_tests/dacite/test_generated_dataclass_properties.py`
- Hypothesis test file: `generated_tests/dacite/test_generated_dataclass_hypothesis.py`
- Dataclass schema test file: `generated_tests/dacite/test_generated_dataclass_schema.py`
- Dataclass conversion test file: `generated_tests/dacite/test_generated_dataclass_conversions.py`
- Helper boundary test file: `generated_tests/dacite/test_generated_helper_boundaries.py`
- Common-AST test file: `generated_tests/dacite/test_generated_common_ast_properties.py`
- Interprocedural test file: `generated_tests/dacite/test_generated_interprocedural_properties.py`
- Legacy transform/property cases emitted: 0
- Dataclass schema cases emitted: 1
- Dataclass constructor cases emitted: 1
- Dataclass conversion cases emitted: 1
- Helper boundary cases emitted: 0
- Common-AST cases emitted: 0
- Interprocedural cases emitted: 0
- Candidate relations left as review items: 0
- Helper boundary relations left as review items: 1
- Common-AST relations left as review items: 2
- Interprocedural relations left as review items: 0

## Run

Use a disposable validation venv for target-project dependencies:

```bash
python3 -m venv /tmp/sps-dacite-validation-venv
/tmp/sps-dacite-validation-venv/bin/python -m pip install pytest
/tmp/sps-dacite-validation-venv/bin/python -m pip install -r /path/to/target-validation-requirements.txt
/tmp/sps-dacite-validation-venv/bin/python tools/validate_generated_tests.py generated_tests/dacite --target-project /path/to/target-project
rm -rf /tmp/sps-dacite-validation-venv
```

For dependency-light targets, the requirements install can be omitted. The validation venv should be removed after recording results and recreated when validation is needed again.

If the target dependencies are already available in the current shell, the equivalent direct pytest command is:

```bash
PYTHONPATH=/path/to/target-project pytest generated_tests/dacite
```

To produce relation-yield, common-AST/interprocedural yield, and coverage-delta evaluation stats:

```bash
/tmp/sps-dacite-validation-venv/bin/python tools/evaluation_stats.py --analysis-dir /private/tmp/sps-dacite-souffle --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/dacite --report /tmp/sps-evaluation-stats.md
```

To run relation-guided transform, collection-iteration, interprocedural-pipeline, and boundary mutation evaluation against handwritten, generated, and combined suites:

```bash
/tmp/sps-dacite-validation-venv/bin/python tools/mutation_eval.py --analysis-dir /private/tmp/sps-dacite-souffle --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/dacite --max-mutants 12 --report /tmp/sps-mutation-eval.md
```

## Legacy Transform/Property Cases

- No legacy transform/property cases were emitted by the conservative generator.

## Dataclass Schema Cases

- `schema-config-Config`: runtime schema for `dacite.config.Config`

## Dataclass Constructor Cases

- `constructor-config-Config`: constructor/default behavior for `dacite.config.Config`

## Dataclass Conversion Cases

- `conversion-dict_to_dataclass-core-from_dict`: `dacite.core.from_dict` as `dict_to_dataclass`

## Review Candidates

- No candidates were skipped.

## Helper Boundary Cases

- No helper boundary cases were emitted.

## Helper Boundary Review Candidates

- `_build_value_for_union` boundary skipped: method owner class was not resolved.

## Common-AST Cases

- No common-AST cases were emitted.

## Common-AST Review Candidates

- `_build_value` collection iteration skipped: method owner class was not resolved.
- `__dereference` alias attribute read relation kept for review: no conservative executable oracle yet.

## Interprocedural Cases

- No interprocedural cases were emitted.

## Interprocedural Review Candidates

- No interprocedural candidates were skipped.

## Notes

The dataclass-transform generator only emits public `format*` method tests with string/list observations.
The dataclass schema generator emits runtime `dataclasses` reflection and constructor/default tests for every discovered dataclass up to `--max-cases`.
The dataclass conversion generator emits profile tests for public `from_dict`, `structure`, `to_dict`, `asdict`, and `unstructure` callables.
The Hypothesis file is optional at runtime and is skipped by pytest when Hypothesis is not installed.
Helper boundary tests are lower-confidence because they may call private helper methods directly.
Common-AST tests are conservative and currently focus on observable collection iteration over dataclass fields.
Interprocedural tests are conservative and currently require a public method that drives the source dataclass to the output dataclass.
Relations involving publishing, private helpers, branch/control facts, lossy flows, nullable-use findings, protocol-order findings, or unsupported interprocedural outputs are kept as review candidates until stronger oracles are available.
