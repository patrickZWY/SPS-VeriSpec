# Generated Test Validation Report

- Generated tests: `/Users/zhengwangyuan/repos/SPS-VeriSpec/generated_tests/transformers`
- Target project: `/Users/zhengwangyuan/repos/SPS-VeriSpec/transformers/src`
- Return code: `0`
- Passed: 0
- Failed: 0
- Errors: 0
- Skipped: 106
- XFailed: 0
- XPassed: 0

## Command

```bash
/Users/zhengwangyuan/repos/SPS-VeriSpec/.venv/bin/python -m pytest -q /Users/zhengwangyuan/repos/SPS-VeriSpec/generated_tests/transformers -rs
```

## Pytest Output

```text
ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss [ 67%]
ssssssssssssssssssssssssssssssssss                                       [100%]
=========================== short test summary info ============================
SKIPPED [1] generated_tests/transformers/test_generated_common_ast_properties.py:66: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_conversions.py:75: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_hypothesis.py:131: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_properties.py:81: got empty parameter set for (case)
SKIPPED [7] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.generation.configuration_utils: No module named 'numpy'
SKIPPED [2] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.modeling_attn_mask_utils: No module named 'numpy'
SKIPPED [84] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.modeling_outputs: No module named 'numpy'
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.tokenization_utils_base: No module named 'numpy'
SKIPPED [4] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.trainer_callback: No module named 'numpy'
SKIPPED [2] generated_tests/transformers/test_generated_dataclass_schema.py:879: Cannot import transformers.utils.loading_report: No module named 'numpy'
SKIPPED [1] generated_tests/transformers/test_generated_helper_boundaries.py:51: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_interprocedural_properties.py:76: got empty parameter set for (case)
106 skipped in 0.75s

```
