# Generated Test Validation Report

- Generated tests: `/Users/zhengwangyuan/repos/SPS-VeriSpec/generated_tests/transformers`
- Target project: `/Users/zhengwangyuan/repos/SPS-VeriSpec/transformers/src`
- Return code: `0`
- Passed: 99
- Failed: 0
- Errors: 0
- Skipped: 7
- XFailed: 0
- XPassed: 0

## Command

```bash
/Users/zhengwangyuan/repos/SPS-VeriSpec/.venv/bin/python -m pytest -q /Users/zhengwangyuan/repos/SPS-VeriSpec/generated_tests/transformers -rs
```

## Pytest Output

```text
ssss................................................s................... [ 67%]
................................ss                                       [100%]
=============================== warnings summary ===============================
generated_tests/transformers/test_generated_dataclass_schema.py::test_generated_dataclass_constructor_defaults[constructor-modeling_attn_mask_utils-AttentionMaskConverter]
  /Users/zhengwangyuan/repos/SPS-VeriSpec/transformers/src/transformers/modeling_attn_mask_utils.py:71: FutureWarning: The attention mask API under `transformers.modeling_attn_mask_utils` (`AttentionMaskConverter`) is deprecated and will be removed in Transformers v5.10. Please use the new API in `transformers.masking_utils`.
    warnings.warn(DEPRECATION_MESSAGE, FutureWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] generated_tests/transformers/test_generated_common_ast_properties.py:66: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_conversions.py:75: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_hypothesis.py:131: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_properties.py:81: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_dataclass_schema.py:965: tokenizers.AddedToken is not a runtime dataclass in this dependency configuration
SKIPPED [1] generated_tests/transformers/test_generated_helper_boundaries.py:51: got empty parameter set for (case)
SKIPPED [1] generated_tests/transformers/test_generated_interprocedural_properties.py:76: got empty parameter set for (case)
99 passed, 7 skipped, 1 warning in 3.77s

```
