# Generated Test Report

- Analysis directory: `/private/tmp/sps-transformers-slice-analysis`
- Import prefix: `transformers`
- Test file: `generated_tests/transformers/test_generated_dataclass_properties.py`
- Hypothesis test file: `generated_tests/transformers/test_generated_dataclass_hypothesis.py`
- Dataclass schema test file: `generated_tests/transformers/test_generated_dataclass_schema.py`
- Dataclass conversion test file: `generated_tests/transformers/test_generated_dataclass_conversions.py`
- Helper boundary test file: `generated_tests/transformers/test_generated_helper_boundaries.py`
- Common-AST test file: `generated_tests/transformers/test_generated_common_ast_properties.py`
- Interprocedural test file: `generated_tests/transformers/test_generated_interprocedural_properties.py`
- Legacy transform/property cases emitted: 0
- Dataclass schema cases emitted: 52
- Dataclass constructor cases emitted: 48
- Dataclass conversion cases emitted: 0
- Helper boundary cases emitted: 0
- Common-AST cases emitted: 0
- Interprocedural cases emitted: 0
- Candidate relations left as review items: 0
- Helper boundary relations left as review items: 4
- Common-AST relations left as review items: 17
- Interprocedural relations left as review items: 0

## Run

Use a disposable validation venv for target-project dependencies:

```bash
python3 -m venv /tmp/sps-transformers-validation-venv
/tmp/sps-transformers-validation-venv/bin/python -m pip install pytest
/tmp/sps-transformers-validation-venv/bin/python -m pip install -r /path/to/target-validation-requirements.txt
/tmp/sps-transformers-validation-venv/bin/python tools/validate_generated_tests.py generated_tests/transformers --target-project /path/to/target-project
rm -rf /tmp/sps-transformers-validation-venv
```

For dependency-light targets, the requirements install can be omitted. The validation venv should be removed after recording results and recreated when validation is needed again.

If the target dependencies are already available in the current shell, the equivalent direct pytest command is:

```bash
PYTHONPATH=/path/to/target-project pytest generated_tests/transformers
```

To produce relation-yield, common-AST/interprocedural yield, and coverage-delta evaluation stats:

```bash
/tmp/sps-transformers-validation-venv/bin/python tools/evaluation_stats.py --analysis-dir /private/tmp/sps-transformers-slice-analysis --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/transformers --report /tmp/sps-evaluation-stats.md
```

To run relation-guided transform, collection-iteration, interprocedural-pipeline, and boundary mutation evaluation against handwritten, generated, and combined suites:

```bash
/tmp/sps-transformers-validation-venv/bin/python tools/mutation_eval.py --analysis-dir /private/tmp/sps-transformers-slice-analysis --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests generated_tests/transformers --max-mutants 12 --report /tmp/sps-mutation-eval.md
```

## Legacy Transform/Property Cases

- No legacy transform/property cases were emitted by the conservative generator.

## Dataclass Schema Cases

- `schema-generation.configuration_utils-BaseWatermarkingConfig`: runtime schema for `transformers.generation.configuration_utils.BaseWatermarkingConfig`
- `schema-generation.configuration_utils-CompileConfig`: runtime schema for `transformers.generation.configuration_utils.CompileConfig`
- `schema-generation.configuration_utils-ContinuousBatchingConfig`: runtime schema for `transformers.generation.configuration_utils.ContinuousBatchingConfig`
- `schema-generation.configuration_utils-SynthIDTextWatermarkingConfig`: runtime schema for `transformers.generation.configuration_utils.SynthIDTextWatermarkingConfig`
- `schema-generation.configuration_utils-WatermarkingConfig`: runtime schema for `transformers.generation.configuration_utils.WatermarkingConfig`
- `schema-modeling_attn_mask_utils-AttentionMaskConverter`: runtime schema for `transformers.modeling_attn_mask_utils.AttentionMaskConverter`
- `schema-modeling_outputs-BackboneOutput`: runtime schema for `transformers.modeling_outputs.BackboneOutput`
- `schema-modeling_outputs-BaseModelOutput`: runtime schema for `transformers.modeling_outputs.BaseModelOutput`
- `schema-modeling_outputs-BaseModelOutputWithCrossAttentions`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithCrossAttentions`
- `schema-modeling_outputs-BaseModelOutputWithNoAttention`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithNoAttention`
- `schema-modeling_outputs-BaseModelOutputWithPast`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPast`
- `schema-modeling_outputs-BaseModelOutputWithPastAndCrossAttentions`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPastAndCrossAttentions`
- `schema-modeling_outputs-BaseModelOutputWithPooling`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPooling`
- `schema-modeling_outputs-BaseModelOutputWithPoolingAndCrossAttentions`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndCrossAttentions`
- `schema-modeling_outputs-BaseModelOutputWithPoolingAndNoAttention`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndNoAttention`
- `schema-modeling_outputs-BaseModelOutputWithPoolingAndProjection`: runtime schema for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndProjection`
- `schema-modeling_outputs-CausalLMOutput`: runtime schema for `transformers.modeling_outputs.CausalLMOutput`
- `schema-modeling_outputs-CausalLMOutputWithCrossAttentions`: runtime schema for `transformers.modeling_outputs.CausalLMOutputWithCrossAttentions`
- `schema-modeling_outputs-CausalLMOutputWithPast`: runtime schema for `transformers.modeling_outputs.CausalLMOutputWithPast`
- `schema-modeling_outputs-DepthEstimatorOutput`: runtime schema for `transformers.modeling_outputs.DepthEstimatorOutput`
- `schema-modeling_outputs-ImageClassifierOutput`: runtime schema for `transformers.modeling_outputs.ImageClassifierOutput`
- `schema-modeling_outputs-ImageClassifierOutputWithNoAttention`: runtime schema for `transformers.modeling_outputs.ImageClassifierOutputWithNoAttention`
- `schema-modeling_outputs-ImageSuperResolutionOutput`: runtime schema for `transformers.modeling_outputs.ImageSuperResolutionOutput`
- `schema-modeling_outputs-MaskedImageModelingOutput`: runtime schema for `transformers.modeling_outputs.MaskedImageModelingOutput`
- `schema-modeling_outputs-MaskedLMOutput`: runtime schema for `transformers.modeling_outputs.MaskedLMOutput`
- `schema-modeling_outputs-MoEModelOutput`: runtime schema for `transformers.modeling_outputs.MoEModelOutput`
- `schema-modeling_outputs-MoEModelOutputWithPastAndCrossAttentions`: runtime schema for `transformers.modeling_outputs.MoEModelOutputWithPastAndCrossAttentions`
- `schema-modeling_outputs-MoeCausalLMOutputWithPast`: runtime schema for `transformers.modeling_outputs.MoeCausalLMOutputWithPast`
- `schema-modeling_outputs-MoeModelOutputWithPast`: runtime schema for `transformers.modeling_outputs.MoeModelOutputWithPast`
- `schema-modeling_outputs-MultipleChoiceModelOutput`: runtime schema for `transformers.modeling_outputs.MultipleChoiceModelOutput`
- `schema-modeling_outputs-NextSentencePredictorOutput`: runtime schema for `transformers.modeling_outputs.NextSentencePredictorOutput`
- `schema-modeling_outputs-QuestionAnsweringModelOutput`: runtime schema for `transformers.modeling_outputs.QuestionAnsweringModelOutput`
- `schema-modeling_outputs-SampleTSPredictionOutput`: runtime schema for `transformers.modeling_outputs.SampleTSPredictionOutput`
- `schema-modeling_outputs-SemanticSegmenterOutput`: runtime schema for `transformers.modeling_outputs.SemanticSegmenterOutput`
- `schema-modeling_outputs-Seq2SeqLMOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqLMOutput`
- `schema-modeling_outputs-Seq2SeqMoEModelOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqMoEModelOutput`
- `schema-modeling_outputs-Seq2SeqMoEOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqMoEOutput`
- `schema-modeling_outputs-Seq2SeqModelOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqModelOutput`
- `schema-modeling_outputs-Seq2SeqQuestionAnsweringModelOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqQuestionAnsweringModelOutput`
- `schema-modeling_outputs-Seq2SeqSequenceClassifierOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqSequenceClassifierOutput`
- `schema-modeling_outputs-Seq2SeqSpectrogramOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqSpectrogramOutput`
- `schema-modeling_outputs-Seq2SeqTSModelOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqTSModelOutput`
- `schema-modeling_outputs-Seq2SeqTSPredictionOutput`: runtime schema for `transformers.modeling_outputs.Seq2SeqTSPredictionOutput`
- `schema-modeling_outputs-SequenceClassifierOutput`: runtime schema for `transformers.modeling_outputs.SequenceClassifierOutput`
- `schema-modeling_outputs-SequenceClassifierOutputWithPast`: runtime schema for `transformers.modeling_outputs.SequenceClassifierOutputWithPast`
- `schema-modeling_outputs-TokenClassifierOutput`: runtime schema for `transformers.modeling_outputs.TokenClassifierOutput`
- `schema-modeling_outputs-Wav2Vec2BaseModelOutput`: runtime schema for `transformers.modeling_outputs.Wav2Vec2BaseModelOutput`
- `schema-modeling_outputs-XVectorOutput`: runtime schema for `transformers.modeling_outputs.XVectorOutput`
- `schema-tokenization_utils_base-AddedToken`: runtime schema for `transformers.tokenization_utils_base.AddedToken`
- `schema-trainer_callback-TrainerControl`: runtime schema for `transformers.trainer_callback.TrainerControl`
- `schema-trainer_callback-TrainerState`: runtime schema for `transformers.trainer_callback.TrainerState`
- `schema-utils.loading_report-LoadStateDictInfo`: runtime schema for `transformers.utils.loading_report.LoadStateDictInfo`

## Dataclass Constructor Cases

- `constructor-generation.configuration_utils-CompileConfig`: constructor/default behavior for `transformers.generation.configuration_utils.CompileConfig`
- `constructor-generation.configuration_utils-ContinuousBatchingConfig`: constructor/default behavior for `transformers.generation.configuration_utils.ContinuousBatchingConfig`
- `constructor-modeling_attn_mask_utils-AttentionMaskConverter`: constructor/default behavior for `transformers.modeling_attn_mask_utils.AttentionMaskConverter`
- `constructor-modeling_outputs-BackboneOutput`: constructor/default behavior for `transformers.modeling_outputs.BackboneOutput`
- `constructor-modeling_outputs-BaseModelOutput`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutput`
- `constructor-modeling_outputs-BaseModelOutputWithCrossAttentions`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithCrossAttentions`
- `constructor-modeling_outputs-BaseModelOutputWithNoAttention`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithNoAttention`
- `constructor-modeling_outputs-BaseModelOutputWithPast`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPast`
- `constructor-modeling_outputs-BaseModelOutputWithPastAndCrossAttentions`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPastAndCrossAttentions`
- `constructor-modeling_outputs-BaseModelOutputWithPooling`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPooling`
- `constructor-modeling_outputs-BaseModelOutputWithPoolingAndCrossAttentions`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndCrossAttentions`
- `constructor-modeling_outputs-BaseModelOutputWithPoolingAndNoAttention`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndNoAttention`
- `constructor-modeling_outputs-BaseModelOutputWithPoolingAndProjection`: constructor/default behavior for `transformers.modeling_outputs.BaseModelOutputWithPoolingAndProjection`
- `constructor-modeling_outputs-CausalLMOutput`: constructor/default behavior for `transformers.modeling_outputs.CausalLMOutput`
- `constructor-modeling_outputs-CausalLMOutputWithCrossAttentions`: constructor/default behavior for `transformers.modeling_outputs.CausalLMOutputWithCrossAttentions`
- `constructor-modeling_outputs-CausalLMOutputWithPast`: constructor/default behavior for `transformers.modeling_outputs.CausalLMOutputWithPast`
- `constructor-modeling_outputs-DepthEstimatorOutput`: constructor/default behavior for `transformers.modeling_outputs.DepthEstimatorOutput`
- `constructor-modeling_outputs-ImageClassifierOutput`: constructor/default behavior for `transformers.modeling_outputs.ImageClassifierOutput`
- `constructor-modeling_outputs-ImageClassifierOutputWithNoAttention`: constructor/default behavior for `transformers.modeling_outputs.ImageClassifierOutputWithNoAttention`
- `constructor-modeling_outputs-ImageSuperResolutionOutput`: constructor/default behavior for `transformers.modeling_outputs.ImageSuperResolutionOutput`
- `constructor-modeling_outputs-MaskedImageModelingOutput`: constructor/default behavior for `transformers.modeling_outputs.MaskedImageModelingOutput`
- `constructor-modeling_outputs-MaskedLMOutput`: constructor/default behavior for `transformers.modeling_outputs.MaskedLMOutput`
- `constructor-modeling_outputs-MoEModelOutput`: constructor/default behavior for `transformers.modeling_outputs.MoEModelOutput`
- `constructor-modeling_outputs-MoEModelOutputWithPastAndCrossAttentions`: constructor/default behavior for `transformers.modeling_outputs.MoEModelOutputWithPastAndCrossAttentions`
- `constructor-modeling_outputs-MoeCausalLMOutputWithPast`: constructor/default behavior for `transformers.modeling_outputs.MoeCausalLMOutputWithPast`
- `constructor-modeling_outputs-MoeModelOutputWithPast`: constructor/default behavior for `transformers.modeling_outputs.MoeModelOutputWithPast`
- `constructor-modeling_outputs-MultipleChoiceModelOutput`: constructor/default behavior for `transformers.modeling_outputs.MultipleChoiceModelOutput`
- `constructor-modeling_outputs-NextSentencePredictorOutput`: constructor/default behavior for `transformers.modeling_outputs.NextSentencePredictorOutput`
- `constructor-modeling_outputs-QuestionAnsweringModelOutput`: constructor/default behavior for `transformers.modeling_outputs.QuestionAnsweringModelOutput`
- `constructor-modeling_outputs-SampleTSPredictionOutput`: constructor/default behavior for `transformers.modeling_outputs.SampleTSPredictionOutput`
- `constructor-modeling_outputs-SemanticSegmenterOutput`: constructor/default behavior for `transformers.modeling_outputs.SemanticSegmenterOutput`
- `constructor-modeling_outputs-Seq2SeqLMOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqLMOutput`
- `constructor-modeling_outputs-Seq2SeqMoEModelOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqMoEModelOutput`
- `constructor-modeling_outputs-Seq2SeqMoEOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqMoEOutput`
- `constructor-modeling_outputs-Seq2SeqModelOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqModelOutput`
- `constructor-modeling_outputs-Seq2SeqQuestionAnsweringModelOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqQuestionAnsweringModelOutput`
- `constructor-modeling_outputs-Seq2SeqSequenceClassifierOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqSequenceClassifierOutput`
- `constructor-modeling_outputs-Seq2SeqSpectrogramOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqSpectrogramOutput`
- `constructor-modeling_outputs-Seq2SeqTSModelOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqTSModelOutput`
- `constructor-modeling_outputs-Seq2SeqTSPredictionOutput`: constructor/default behavior for `transformers.modeling_outputs.Seq2SeqTSPredictionOutput`
- `constructor-modeling_outputs-SequenceClassifierOutput`: constructor/default behavior for `transformers.modeling_outputs.SequenceClassifierOutput`
- `constructor-modeling_outputs-SequenceClassifierOutputWithPast`: constructor/default behavior for `transformers.modeling_outputs.SequenceClassifierOutputWithPast`
- `constructor-modeling_outputs-TokenClassifierOutput`: constructor/default behavior for `transformers.modeling_outputs.TokenClassifierOutput`
- `constructor-modeling_outputs-Wav2Vec2BaseModelOutput`: constructor/default behavior for `transformers.modeling_outputs.Wav2Vec2BaseModelOutput`
- `constructor-modeling_outputs-XVectorOutput`: constructor/default behavior for `transformers.modeling_outputs.XVectorOutput`
- `constructor-trainer_callback-TrainerControl`: constructor/default behavior for `transformers.trainer_callback.TrainerControl`
- `constructor-trainer_callback-TrainerState`: constructor/default behavior for `transformers.trainer_callback.TrainerState`
- `constructor-utils.loading_report-LoadStateDictInfo`: constructor/default behavior for `transformers.utils.loading_report.LoadStateDictInfo`

## Dataclass Conversion Cases

- No dataclass conversion cases were emitted.

## Review Candidates

- No candidates were skipped.

## Helper Boundary Cases

- No helper boundary cases were emitted.

## Helper Boundary Review Candidates

- `PreTrainedTokenizerBase._get_padding_truncation_strategies` boundary skipped: only `len(...)` helper boundaries are generated automatically.
- `ContinuousBatchingConfig.__post_init__` boundary skipped: only `len(...)` helper boundaries are generated automatically.
- `AttentionMaskConverter.__init__` boundary skipped: only `len(...)` helper boundaries are generated automatically.
- `AttentionMaskConverter._make_causal_mask` boundary skipped: only `len(...)` helper boundaries are generated automatically.

## Common-AST Cases

- No common-AST cases were emitted.

## Common-AST Review Candidates

- `BaseWatermarkingConfig.__iter__` generator output relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase._from_pretrained` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase.get_chat_template` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase.get_chat_template` alias attribute read relation kept for review: no conservative executable oracle yet.
- `PreTrainedTokenizerBase.register_for_auto_class` alias attribute read relation kept for review: no conservative executable oracle yet.
- `EarlyStoppingCallback.on_evaluate` alias attribute read relation kept for review: no conservative executable oracle yet.
- `GenerationConfig.from_model_config` alias attribute read relation kept for review: no conservative executable oracle yet.
- `GenerationConfig.from_model_config` alias attribute read relation kept for review: no conservative executable oracle yet.
- `AttentionMaskConverter.to_4d` alias attribute read relation kept for review: no conservative executable oracle yet.
- `_prepare_4d_causal_attention_mask_for_sdpa` alias attribute read relation kept for review: no conservative executable oracle yet.
- `_prepare_4d_causal_attention_mask_for_sdpa` alias attribute read relation kept for review: no conservative executable oracle yet.

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
