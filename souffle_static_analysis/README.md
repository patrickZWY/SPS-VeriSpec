# Souffle Static Analysis Backend

This directory contains the Souffle/Datalog implementation of the current
SPS-VeriSpec static-analysis layers.

The Python frontend still extracts AST facts into `.facts` files. The analyses
in this directory consume those facts and derive schema, effect, deduction,
test-target, semantic, interprocedural, slicing, abstract-state, typestate, and
boundary relations.

Run only this backend with:

```bash
python3 tools/run_static_analysis.py /path/to/python-project \
  --engine souffle \
  --work-dir /tmp/sps-souffle-run
```

Run only the Python extractor/fact-inventory backend with:

```bash
python3 tools/run_static_analysis.py /path/to/python-project \
  --engine python \
  --work-dir /tmp/sps-python-run
```

The `python` engine intentionally does not run these Datalog rules. It emits
raw extracted fact counts only, which makes it useful as a baseline for checking
what the Souffle backend derives beyond the Python frontend.

## Per-layer references

The rules run in layers (schema → effect → deduction → test-target → semantic).
Each layer has a reference describing how to run it, its outputs, and what they
mean, under [`docs/layers/`](../docs/layers/):

- [schema](../docs/layers/schema.md) (`dataclass_schema_model.dl`)
- [effect](../docs/layers/effect.md) (`dataclass_effect_model.dl`)
- [deduction](../docs/layers/deduction.md) (`dataclass_deduction_model.dl`)
- [semantic](../docs/layers/semantic.md) (`semantic_model.dl`)

The experimental LLM rule lane is the parallel [`rule_layer/`](../rule_layer/).
See [`docs/architecture.md`](../docs/architecture.md) for how these fit together.
