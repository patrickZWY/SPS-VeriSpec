# Transformers Dataclass Experiment Investigation

## What Went Wrong

- The full `transformers/src/transformers` tree was too large for the current in-memory extractor/resolver workflow. A later full-tree retry was stopped after several minutes in fact resolution without producing facts. A bounded dataclass-heavy slice completes quickly and is the practical target for this validation run.
- The slice was analyzed from inside the package directory, so facts used module names like `modeling_outputs` and `generation.utils`. Validation used `transformers/src` on `PYTHONPATH`, where the importable names are `transformers.modeling_outputs` and `transformers.generation.utils`. Empty generated case lists masked this import-prefix mismatch.
- The old executable generator was mostly a CutePetsBoston-shaped oracle generator. It required public `format*` methods with field flow from one dataclass into another dataclass output. Transformers has many dataclass schemas and dataclass-consuming methods, but the slice produced:
  - `method_dataclass_transform.csv`: 0 rows
  - `transform_required_field_test_target.csv`: 0 rows
  - `transform_optional_field_test_target.csv`: 0 rows
- The relations that did exist were mostly outside the old executable surface. In the final bounded slice, the analyzer found 52 dataclasses, 77 class/dataclass role links, 99 numeric boundary candidates, 16 alias reads, and 1 generator-output candidate, but no `format*`-style transform oracles.
- Local validation is dependency-bound. Installing the lightweight runtime dependencies moved generated tests from pure skips to executable schema/default checks. Installing `torch` made the model-output dataclasses importable. The package index only exposed `torch==2.2.2`, even though this Transformers checkout declares `torch>=2.4`; validation was therefore based on the best available local wheel, not the declared ideal version.

## Fixes Applied

- Added `--import-prefix` to `tools/generate_pytest_from_properties.py` so inner-package slice analysis can still generate tests importable from the real project root.
- Added `generated_tests/<project>/test_generated_dataclass_schema.py`.
- Added generic runtime dataclass schema oracles using `dataclasses.is_dataclass`, `dataclasses.fields`, and `__dataclass_params__`.
- Added generic constructor/default oracles for discovered dataclasses, including default/factory field checks when a generated fixture can instantiate the class.
- Added generic conversion-profile test generation for top-level `from_dict`, `structure`, `to_dict`, `asdict`, and `unstructure` APIs, plus converter-class `structure`/`unstructure` methods.
- Regenerated the Transformers artifacts with `--import-prefix transformers`.
- Added runtime skips for static dataclass false positives that resolve to non-dataclass optional dependency implementations at runtime. This specifically handles `transformers.tokenization_utils_base.AddedToken`, which is a fallback dataclass only when `tokenizers` is absent; after installing `tokenizers`, it resolves to `tokenizers.AddedToken`.
- Installed the runtime dependency chain for validation: `numpy`, `filelock`, `huggingface-hub`, `safetensors`, `tokenizers`, `tqdm`, and `torch`. `numpy` was pinned back to `1.26.4` because `torch==2.2.2` emitted a NumPy 2.x ABI warning with `numpy==2.4.6`. Future runs should install these into a disposable `/tmp/sps-transformers-validation-venv` from `validation_requirements/transformers.txt`, validate, and then remove that venv.

## Current Transformers Yield

- Transform/property cases: 0
- Runtime dataclass schema cases: 52
- Constructor/default cases: 48
- Conversion-profile cases: 0
- Helper boundary cases: 0
- Common-AST cases: 0
- Interprocedural cases: 0

Local validation result after installing dependencies: 99 passed, 7 skipped, 0 failed, 0 errors. The remaining skips are empty non-applicable generated files plus the expected `AddedToken` runtime skip under the installed `tokenizers` dependency.

## Remaining Work

- Make full-tree extraction streaming or progress-aware so large libraries do not require ad hoc slices.
- Add executable fixture/oracle families for config classes, tokenizer outputs, generation outputs, data collators, callbacks, and `__iter__/to_dict` style dataclass APIs.
- Promote selected alias-read, generator-output, control-dependence, and numeric-bound candidates into executable tests when their fixtures can be constructed conservatively.
- Extend dependency reporting so validation summaries classify empty-case skips, missing-dependency skips, runtime-shape skips, and fixture-construction skips separately.
