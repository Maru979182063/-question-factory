# word_usage_content_word Proto Mapping Execution Report

Date: 2026-04-25

## Outcome

Implemented the minimum experimental/proto generation route for:

```text
question_focus = word_usage
business_subtype = word_usage_content_word
extra_constraints.experimental_proto_route = true
```

This route lets a real distill trial produce a reviewable proto item without
promoting `word_usage` into a formal stable mother family.

## Modified Files

- `prompt_skeleton_service/app/services/question_generation.py`
- `prompt_skeleton_service/tests/test_word_usage_proto_mapping.py`
- `docs/word_usage_content_word_proto_mapping_audit_2026-04-25.md`
- `docs/word_usage_content_word_proto_mapping_execution_report_2026-04-25.md`

## Proto IDs

- `question_card_id`: `proto.word_usage.content_word.v0`
- `business_feature_card_id`: `proto.word_usage.content_word.feature.v0`
- `prompt_profile`: `proto_word_usage_explanation`
- `material_strategy`: `proto_text_context_window`
- `validator_contract`: `proto_minimal_json_shape_only`

## Implementation Notes

The implementation adds a narrow early branch inside
`QuestionGenerationService.generate()` before the normal input decoder gate.

It only activates when all of these are true:

- `question_focus == "word_usage"`
- `business_subtype == "word_usage_content_word"`
- `extra_constraints.experimental_proto_route is True`

If the flag is missing, the request continues into the original decoder and
still fails with:

```text
Selected business_subtype is not mapped yet.
```

If an unknown subtype is supplied, it also fails through the original guard.

## Generated Output Shape

The proto route creates a minimal reviewable item with:

- `question_type = word_usage`
- `business_subtype = word_usage_content_word`
- `generated_question.metadata.experimental = true`
- `generated_question.metadata.proto_family = word_usage`
- `generated_question.metadata.proto_child_family = word_usage_content_word`
- `generated_question.metadata.formalized = false`
- `validation_result.warnings` containing `proto_minimal_json_shape_only`

The route is deterministic and does not call an LLM.

## System API Smoke

Ran a real FastAPI `TestClient` chain through:

```text
POST /api/v1/distill/datasets
POST /api/v1/distill/sessions
POST /api/v1/distill/sessions/{session_id}/trials
```

Result:

```json
{
  "dataset_status": "active",
  "sample_count": 1,
  "session_status": "active",
  "run_status": "completed",
  "fit_band": "high",
  "item_question_type": "word_usage",
  "item_business_subtype": "word_usage_content_word",
  "sample_error": null
}
```

The item metadata included:

```json
{
  "experimental": true,
  "proto_family": "word_usage",
  "proto_child_family": "word_usage_content_word",
  "business_subtype": "word_usage_content_word",
  "question_card_id": "proto.word_usage.content_word.v0",
  "business_feature_card_id": "proto.word_usage.content_word.feature.v0",
  "material_strategy": "proto_text_context_window",
  "validator_contract": "proto_minimal_json_shape_only",
  "prompt_profile": "proto_word_usage_explanation",
  "source": "bootstrap_discovery",
  "formalized": false
}
```

## Test Results

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

Result:

```text
Ran 4 tests in 0.261s
OK
```

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

Result:

```text
Ran 10 tests in 1.396s
OK
```

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

Result:

```text
Ran 12 tests in 0.072s
OK
```

## Explicit Non-Goals Preserved

- Did not formally promote `word_usage` mother family.
- Did not add a normalized `word_usage` question card.
- Did not convert `candidate_axes` into formal fields.
- Did not add a promotion target.
- Did not write back to `card_specs`.
- Did not modify validator main business logic.
- Did not change database schema or add migrations.
- Did not change frontend tabs.
- Did not affect existing `sentence_fill`, `sentence_order`, or
  `center_understanding` decoder targets.

