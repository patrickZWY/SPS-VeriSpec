# Transformers Pipeline Report

## Target

- Requested target: `transformers/src/transformers`
- Full target size observed earlier: 2,717 Python files, about 1,107,961 lines.
- Full-tree result: not completed interactively. The extractor/resolver stayed
  in the in-memory phase for several minutes and produced no facts, so the run
  was stopped.
- Scaling conclusion: Transformers is currently a large-library stress target,
  not the primary generalization benchmark. Full-tree support needs
  streaming/progress-aware extraction and fact resolution.

## Bounded Slice Used

Because the full tree did not finish interactively, the final validation used a
smaller dataclass-heavy slice copied under `/tmp/sps-transformers-slice`.
Generated tests still import and validate against the real checkout through
`--target-project transformers/src`.

Files included:

- `modeling_outputs.py`
- `modeling_attn_mask_utils.py`
- `tokenization_utils_base.py`
- `trainer_callback.py`
- `generation/configuration_utils.py`
- `utils/loading_report.py`

## Analysis Results

Souffle backend:

- Summary: `/tmp/sps-transformers-slice-analysis/summary.md`
- Dataclasses discovered: 52
- Dataclass option facts: 520
- Reachable dataclass dependencies: 1
- Callgraph-reachable function pairs: 159
- Dataclass-linked functions: 82
- Interprocedural dataclass effects: 4
- Class/dataclass role links: 77
- External-call field slices: 1
- Control-dependence slices: 6
- Abstract value states: 987
- Abstract numeric states: 9
- Numeric boundary candidates: 99
- Typestate protocol violations: 3
- Alias attribute reads: 16
- Generator output candidates: 1

The old CutePetsBoston-style executable surface still does not fire for this
slice:

- Direct dataclass transformations: 0
- Method dataclass transformations: 0
- Field-to-constructor-arg flows: 0
- Observable output slices: 0

## Generated Tests

Generated files:

- `generated_tests/transformers/test_generated_dataclass_properties.py`
- `generated_tests/transformers/test_generated_dataclass_hypothesis.py`
- `generated_tests/transformers/test_generated_dataclass_schema.py`
- `generated_tests/transformers/test_generated_dataclass_conversions.py`
- `generated_tests/transformers/test_generated_helper_boundaries.py`
- `generated_tests/transformers/test_generated_common_ast_properties.py`
- `generated_tests/transformers/test_generated_interprocedural_properties.py`

Generator result:

- CutePetsBoston-style transform cases emitted: 0
- Runtime dataclass schema cases emitted: 52
- Constructor/default cases emitted: 48
- Dataclass conversion cases emitted: 0
- Helper boundary cases emitted: 0
- Common-AST cases emitted: 0
- Interprocedural cases emitted: 0
- Helper boundary review candidates: 4
- Common-AST review candidates: 17

Interpretation: the generic dataclass oracle layer now produces executable
Transformers tests without relying on `format*` method names or CutePetsBoston
field names. The older transform generator still emits nothing for this target,
which confirms that it was too narrow.

## Dependency Validation

Transformers validation is dependency-bound. Before installing runtime
dependencies, most generated tests were import skips. Installing the lightweight
runtime chain and PyTorch changed the bounded suite to executable tests.

Installed for this validation run:

- `filelock`
- `huggingface-hub`
- `numpy==1.26.4`
- `safetensors`
- `tokenizers`
- `torch==2.2.2`
- `tqdm`

The package index available in this environment exposed `torch==2.2.2` as the
newest PyTorch wheel, while this Transformers checkout declares `torch>=2.4`.
That means the validation uses the best available local wheel, not the ideal
declared dependency set. `numpy` was downgraded from `2.4.6` to `1.26.4`
because `torch==2.2.2` emitted a NumPy 2.x ABI warning.

Going forward, these dependencies should be installed into a disposable
validation venv rather than the main SPS-VeriSpec `.venv`:

```bash
python3 -m venv /tmp/sps-transformers-validation-venv
/tmp/sps-transformers-validation-venv/bin/python -m pip install \
  -r validation_requirements/transformers.txt
/tmp/sps-transformers-validation-venv/bin/python \
  tools/validate_generated_tests.py generated_tests/transformers \
  --target-project transformers/src --pytest-arg=-rs
rm -rf /tmp/sps-transformers-validation-venv
```

## Validation Result

Generated-test validation:

- Report: `generated_tests/transformers/validation_report.md`
- Recorded command before dependency cleanup: `.venv/bin/python tools/validate_generated_tests.py generated_tests/transformers --target-project transformers/src --pytest-arg=-rs`
- Result: `99 passed, 7 skipped, 0 failed, 0 errors`

Remaining skips:

- empty generated files for relation families that did not produce executable
  cases on this slice
- `tokenizers.AddedToken` runtime-shape skip, because Transformers' fallback
  `AddedToken` dataclass is replaced by the installed `tokenizers` implementation

## Conclusion

On Transformers, SPS-VeriSpec now succeeds at generating executable generic
dataclass schema/default tests for a representative dataclass-heavy slice once
runtime dependencies are installed. It still does not complete the full
`src/transformers` tree interactively, and it still needs more oracle families
for config classes, tokenizer outputs, generation outputs, callbacks, and
`__iter__/to_dict` style APIs.

The practical project conclusion is that Datalog analysis is useful, but
executable oracle generation must be semantic and dataclass-generic. Transformers
should remain a scale/dependency stress test; smaller projects such as dacite
are better primary regression targets for proving generality.
