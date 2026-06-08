# rule_layer/ — experimental LLM rule lane

This directory holds the Souffle/Datalog source for the **experimental,
LLM-assisted rule lane** (the `llm` engine in `tools/run_souffle_models.py` and
`tools/run_static_analysis.py`). It is the counterpart to
[`souffle_static_analysis/`](../souffle_static_analysis/), which holds the
**trusted static** backend.

`.dl` files here are loaded by path, so they must stay in this directory.

Status: the latest evidence does **not** support this lane. In the 2026-05-24
CutePetsBoston and bounded Transformers comparison it produced no additional
semantic/test relation rows versus the static rules — the only difference was
provenance taint in combined reports. Treat it as experimental and keep it
quarantined.

For how to prompt the LLM during this phase, the base-fact schema, the prompt
template, and the review checklist, see
[`docs/llm-rule-layer.md`](../docs/llm-rule-layer.md).

The generic per-layer references (schema, effect, deduction, semantic) describe
the trusted backend and now live under [`docs/layers/`](../docs/layers/).
