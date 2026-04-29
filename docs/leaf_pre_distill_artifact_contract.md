# Leaf Pre-Distill Artifact Contract

This document defines the artifact contract for offline leaf pre-distillation outputs. These artifacts are allowed to enter the distill workbench as evidence for review, patch, and promotion bundles.

## Boundary

- `leaf_pre_distill_report` is evidence, not a formal config change.
- `schema_gap_report` explains a schema gap. It does not mean the schema has already changed.
- `slot_projection_draft` is a landing draft. In the first integration version, it is not an independent promotion target. It is stored as an attachment path inside a `leaf_pre_distill_report` patch payload.

Example patch payload:

```json
{
  "artifact_type": "leaf_pre_distill_report",
  "artifact_path": "data/leaf_pre_distill/example/report.md",
  "field_candidates_path": "data/leaf_pre_distill/example/field_candidates.json",
  "slot_projection_draft_path": "data/leaf_pre_distill/example/slot_projection_draft.yaml",
  "llm_field_probe_path": "data/leaf_pre_distill/example/llm_field_probe.json",
  "bootstrap_discovery_path": "data/leaf_pre_distill/example/bootstrap_discovery.json",
  "axis_confirmation_path": "data/leaf_pre_distill/example/axis_confirmation.json",
  "formal_patch_draft_path": "data/leaf_pre_distill/example/formal_patch_draft.json",
  "formal_writeback_plan_path": "data/leaf_pre_distill/example/formal_writeback_plan.json",
  "formal_writeback_diff_path": "data/leaf_pre_distill/example/formal_writeback_diff.md",
  "model_safe_gold_reconstruction_input_path": "data/leaf_pre_distill/example/model_safe_gold_reconstruction_input.jsonl",
  "gold_reconstruction_results_path": "data/leaf_pre_distill/example/gold_reconstruction_results.jsonl",
  "gold_reconstruction_report_path": "data/leaf_pre_distill/example/gold_reconstruction_report.md",
  "truth_gold_split_manifest_path": "data/leaf_pre_distill/example/truth_gold_split_manifest.json",
  "truth_gold_regression_results_path": "data/leaf_pre_distill/example/truth_gold_regression_results.json",
  "truth_gold_regression_report_path": "data/leaf_pre_distill/example/truth_gold_regression_report.md",
  "source_discovery_queries_path": "data/leaf_pre_distill/example/source_discovery_queries.jsonl",
  "material_source_profile_path": "data/leaf_pre_distill/example/material_source_profile.json",
  "initial_material_seed_pack_path": "data/leaf_pre_distill/example/initial_material_seed_pack.jsonl",
  "source_discovery_preparation_report_path": "data/leaf_pre_distill/example/source_discovery_preparation_report.md",
  "search_request_manifest_path": "data/leaf_pre_distill/example/search_request_manifest.json",
  "source_candidate_results_path": "data/leaf_pre_distill/example/source_candidate_results.jsonl",
  "source_candidate_summary_path": "data/leaf_pre_distill/example/source_candidate_summary.json",
  "source_candidate_alignment_report_path": "data/leaf_pre_distill/example/source_candidate_alignment_report.md",
  "source_candidate_review_decisions_path": "data/leaf_pre_distill/example/source_candidate_review_decisions.json",
  "source_candidate_review_path": "data/leaf_pre_distill/example/source_candidate_review.json",
  "source_seed_registry_path": "data/leaf_pre_distill/example/source_seed_registry.jsonl",
  "crawl_seed_manifest_path": "data/leaf_pre_distill/example/crawl_seed_manifest.json",
  "source_candidate_human_review_report_path": "data/leaf_pre_distill/example/source_candidate_human_review_report.md",
  "source_text_evidence_approval_path": "data/leaf_pre_distill/example/source_text_evidence_approval.json",
  "source_text_evidence_manifest_path": "data/leaf_pre_distill/example/source_text_evidence_manifest.json",
  "source_text_evidence_results_path": "data/leaf_pre_distill/example/source_text_evidence_results.jsonl",
  "source_text_evidence_report_path": "data/leaf_pre_distill/example/source_text_evidence_report.md",
  "source_gold_alignment_results_path": "data/leaf_pre_distill/example/source_gold_alignment_results.jsonl",
  "source_gold_alignment_summary_path": "data/leaf_pre_distill/example/source_gold_alignment_summary.json",
  "source_gold_alignment_report_path": "data/leaf_pre_distill/example/source_gold_alignment_report.md",
  "source_gold_alignment_review_path": "data/leaf_pre_distill/example/source_gold_alignment_review.json",
  "material_quality_regression_results_path": "data/leaf_pre_distill/example/material_quality_regression_results.json",
  "material_quality_regression_report_path": "data/leaf_pre_distill/example/material_quality_regression_report.md",
  "material_quality_review_path": "data/leaf_pre_distill/example/material_quality_review.json",
  "system_alignment_findings_path": "data/leaf_pre_distill/example/system_alignment_findings.json",
  "material_protocol_draft_input_digest_path": "data/leaf_pre_distill/example/material_protocol_draft_input_digest.json",
  "material_card_draft_path": "data/leaf_pre_distill/example/material_card_draft.json",
  "material_line_prompt_assets_draft_path": "data/leaf_pre_distill/example/material_line_prompt_assets_draft.json",
  "material_quality_regression_draft_path": "data/leaf_pre_distill/example/material_quality_regression_draft.json",
  "material_review_prompts_path": "data/leaf_pre_distill/example/material_review_prompts.md",
  "material_bridge_mapping_draft_path": "data/leaf_pre_distill/example/material_bridge_mapping_draft.json",
  "material_protocol_assets_draft_report_path": "data/leaf_pre_distill/example/material_protocol_assets_draft_report.md",
  "agent_review_feedback_input_path": "data/leaf_pre_distill/example/agent_review_feedback_input.json",
  "agent_review_feedback_normalized_path": "data/leaf_pre_distill/example/agent_review_feedback_normalized.json",
  "agent_review_feedback_report_path": "data/leaf_pre_distill/example/agent_review_feedback_report.md",
  "new_leaf_formalization_packet_path": "data/leaf_pre_distill/example/new_leaf_formalization_packet.json",
  "new_leaf_formalization_packet_report_path": "data/leaf_pre_distill/example/new_leaf_formalization_packet_report.md",
  "runtime_activation_plan_path": "data/leaf_pre_distill/example/runtime_activation_plan.json",
  "runtime_activation_plan_report_path": "data/leaf_pre_distill/example/runtime_activation_plan_report.md",
  "formalization_readiness_checklist_path": "data/leaf_pre_distill/example/formalization_readiness_checklist.json",
  "formalization_readiness_report_path": "data/leaf_pre_distill/example/formalization_readiness_report.md"
}
```

## `manifest.json`

Purpose: identifies the pre-distillation job boundary.

Key fields:

- `job_id`
- `created_at`
- `mother_family_id`
- `child_family_id`
- `leaf_label`
- `source_files`
- `clean_leaf_boundary`
- `operator`
- `artifact_version`

Promotion evidence: yes, as metadata attached to `leaf_pre_distill_report`.

Direct formal config: no.

Human review focus:

- Is the leaf boundary clean?
- Are the mother and child family IDs plausible?
- Are source files traceable and appropriate for the claimed leaf?

## `samples.jsonl`

Purpose: stores parsed source questions, one JSON object per line.

Key fields:

- `sample_id`
- `source_file`
- `source_file_name`
- `mother_family_id`
- `leaf_label`
- `qid`
- `stem`
- `answer`
- `analysis`
- `exam_points`
- `correct_rate`
- `raw_text`
- `parse_warnings`

Promotion evidence: yes, as evidence backing support-rate calculations.

Direct formal config: no.

Human review focus:

- Are samples parsed correctly?
- Are answer, analysis, and exam point fields present?
- Are parse warnings acceptable?
- Is sample count large enough for the claimed confidence?

## `behavior_traces.jsonl`

Purpose: stores observable solving-action traces extracted from each sample.

Key fields:

- `sample_id`
- `qid`
- `mother_family_id`
- `leaf_label`
- `observed_actions`
- `uniqueness_source`
- `distractor_modes`
- `confidence`

Promotion evidence: yes, as evidence for candidate fields and validator candidates.

Direct formal config: no.

Human review focus:

- Are observed actions specific to the leaf, not generic solving language?
- Are uniqueness sources supported by analysis text?
- Are distractor modes aligned with real wrong-option mechanisms?

## `field_candidates.json`

Purpose: aggregates traces into candidate protocol fields.

Key fields:

- `mother_family_id`
- `leaf_label`
- `sample_count`
- `field_candidates`
- `schema_gaps`
- `summary`

Important `field_candidates` fields:

- `field_path`
- `proposed_value`
- `target_layer`
- `support_count`
- `support_rate`
- `confidence`
- `evidence_examples`
- `uniqueness_source`
- `distractor_modes`
- `ablation_question`

Promotion evidence: yes, usually attached to `leaf_pre_distill_report`.

Direct formal config: no.

Human review focus:

- Are high-confidence fields supported by enough samples?
- Are medium/low fields kept out of formal landing?
- Does each field have a meaningful ablation question?
- Are schema gaps real, or are they caused by weak marker rules?

## `slot_projection_draft.yaml`

Purpose: drafts where candidate fields may land in the card system.

Key fields:

- `mother_family_id`
- `leaf_label`
- `canonical_slot_updates`
- `overlay_updates`
- `schema_gaps`
- `validator_contract_candidates`
- `promotion_targets`

Promotion evidence: yes, but only as an attachment path inside `leaf_pre_distill_report` patch payload.

Direct formal config: no.

Independent promotion target: no, not in the first integration version.

Human review focus:

- Are canonical slot updates actually present in the existing card schema?
- Are overlay updates better expressed as business feature card or material card changes?
- Are schema gaps separated from formal updates?
- Are validator contract candidates testable?

## `report.md`

Purpose: human-readable summary of the pre-distillation job.

Key sections:

- basic job information
- field candidate table
- recommended landing draft
- schema gaps
- ablation questions
- conclusion

Promotion evidence: yes. This is the primary artifact for `leaf_pre_distill_report`.

Direct formal config: no.

Human review focus:

- Is the main conclusion supported by artifacts?
- Are schema gaps clearly separated from formal patches?
- Does the report avoid claiming automatic card changes?
- Does it identify which candidates should stay draft-only?

## `system_alignment_findings.json`

Purpose: records the repository-confirmed material-service and material-bridge landing points used before drafting material-line protocol assets.

Key fields:

- `alignment_version`
- `checked_files`
- `confirmed_existing_fields`
- `confirmed_existing_entrypoints`
- `confirmed_material_card_shape`
- `confirmed_bridge_request_fields`
- `confirmed_runtime_material_config`
- `missing_or_unknown`
- `recommended_minimal_compatible_mapping`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the draft use real repository fields rather than invented formal fields?
- Are passage-service routes and material bridge fields correctly detected?
- Are unsupported assumptions marked as missing or proposed?

## `material_protocol_draft_input_digest.json`

Purpose: compact model-safe digest for drafting material-line protocol assets from the current artifact pack.

Key fields:

- `digest_version`
- `family_context`
- `evidence_paths`
- `missing_evidence`
- `gold_reconstruction_summary`
- `truth_gold_regression_summary`
- `source_discovery_summary`
- `source_candidate_summary`
- `source_review_summary`
- `seed_registry_summary`
- `system_alignment_findings_summary`
- `drafting_instructions`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does family context come from artifacts rather than a hard-coded sample family?
- Are missing evidence items clearly recorded?
- Does the digest avoid API keys and unbounded raw source bodies?

## `material_card_draft.json`

Purpose: draft-only material-card asset generated from current evidence and repository alignment.

Key fields:

- `draft_version`
- `asset_type`
- `status`
- `formalized`
- `writeback_allowed`
- `requires_human_review`
- `requires_regression`
- `material_card_id_draft`
- `family_binding`
- `evidence_refs`
- `source_policy`
- `material_requirements`
- `cleaning_and_slicing_hypothesis`
- `quality_gate_draft`
- `system_compatibility`
- `evidence_gaps`
- `next_required_evidence`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is the draft based on current family evidence?
- Did it avoid treating source seeds as verified sources?
- Are source body, alignment, and regression gaps explicit?
- Are proposed fields separated from repository-confirmed material-card fields?

## `material_line_prompt_assets_draft.json`

Purpose: draft-only prompt asset bundle for material-line review, alignment, transformation, quality review, and material-card drafting.

Key fields:

- `draft_version`
- `asset_type`
- `status`
- `formalized`
- `writeback_allowed`
- `requires_human_review`
- `requires_regression`
- `family_context`
- `global_forbidden_actions`
- `prompts`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are prompts generic across families?
- Do prompts require evidence citation and uncertainty reporting?
- Do forbidden actions prevent source confirmation, material promotion, and formal writeback?

## `material_quality_regression_draft.json`

Purpose: draft-only material quality regression dimensions for future material-line validation.

Key fields:

- `draft_version`
- `asset_type`
- `status`
- `formalized`
- `writeback_allowed`
- `requires_human_review`
- `requires_regression`
- `family_context`
- `dimensions`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does each dimension include method, confidence, limitation, and required future evidence?
- Does the draft avoid claiming that scores replace human approval?
- Are holdout and overfit risks represented?

## `material_review_prompts.md`

Purpose: human-readable review prompts for source review, source evidence review, material quality review, and material-card draft review.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are decisions and forbidden outputs clear?
- Do prompts distinguish original source candidates from similar material?
- Do prompts prohibit verified flags, crawl approval, and formal writeback?

## `material_bridge_mapping_draft.json`

Purpose: draft-only mapping from current family context to repository-confirmed material bridge/search fields.

Key fields:

- `mapping_draft_version`
- `asset_type`
- `status`
- `formalized`
- `writeback_allowed`
- `requires_human_review`
- `requires_regression`
- `target_runtime`
- `draft_mapping`
- `mapping_rationale`
- `confirmed_repository_fields_used`
- `proposed_fields_not_confirmed`
- `missing_evidence`
- `requires_bridge_smoke`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does it reference `system_alignment_findings`?
- Does it only treat repository-confirmed request fields as existing fields?
- Does it avoid modifying `question_runtime.yaml` or calling `/materials/v2/search`?

## `material_protocol_assets_draft_report.md`

Purpose: readable summary of material protocol draft generation, system alignment, evidence gaps, and next required evidence.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Was draft generation dry-run, mock, or llm?
- Are blocked errors shown instead of fake successful drafts?
- Are all boundaries clear: no network, no source verification, no material-card writeback, no card-specs/runtime/prompt/validator mutation?

## `llm_safe_digest.json`

Purpose: stores a short, model-safe digest for the optional LLM field probe. It intentionally excludes raw docx text, full stems, full analyses, and `raw_text`.

Key fields:

- `digest_version`
- `mother_family_id`
- `child_family_id`
- `leaf_label`
- `sample_count`
- `field_candidates`
- `schema_gaps`
- `slot_projection_summary`
- `behavior_action_stats`
- `safety_notes`
- `truncation`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the digest lose key evidence needed to judge the probe?
- Are evidence examples short and traceable to existing candidates?
- Does the digest avoid raw docx text, full question stems, and full raw samples?
- Are truncation settings visible enough to judge whether the probe is under-informed?

## `llm_field_probe.json`

Purpose: stores optional low-cost LLM review of existing field candidates. It can summarize a leaf signature, confirm existing candidate fields, comment on schema gaps, and flag risks.

Key fields:

- `probe_version`
- `enabled`
- `model`
- `input_digest_hash`
- `usable`
- `leaf_signature`
- `confirmed_fields`
- `field_risks`
- `schema_gap_comments`
- `warnings`
- `rejected_suggestions`
- `should_promote`
- `raw_output`
- `error`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the model treat the task or output schema as material?
- Are `confirmed_fields` only confirmations of existing field candidates or slot projection fields?
- Are field risks useful for human review?
- Are schema gap comments explanatory rather than claiming the schema changed?
- Did hallucinated fields appear in `rejected_suggestions` instead of `confirmed_fields`?
- Is `should_promote` false?

## `bootstrap_discovery.json`

Purpose: stores hypothesis-level discovery results for unknown or weakly matched leaf packs. It helps reviewers inspect possible proto mother family, candidate axes, distractor taxonomy, and next human questions when deterministic field candidates are empty or weak.

Key fields:

- `discovery_version`
- `enabled`
- `known_family_matched`
- `source`
- `status`
- `promotion_allowed`
- `proto_mother_family`
- `candidate_axes`
- `distractor_taxonomy`
- `evidence_anchors`
- `schema_gap_hypotheses`
- `difficulty_signals`
- `next_human_questions`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are candidate axes grounded in parsed samples?
- Did the discovery confuse question wording with actual solving action?
- Are candidate axes too broad and should be split?
- Are distractor taxonomy hypotheses useful?
- Should proto family be kept, renamed, merged, split, or rejected?
- What seed markers or proto schema should be manually written for the next confirmation pass?

Hard boundaries:

- `candidate_axes` are not fields.
- `hypothesis` is not confirmed.
- `discovery` is not promotion.
- `proto_mother_family` is not a formal mother family.
- `promotion_allowed` must be false.

## `axis_confirmation.json`

Purpose: stores explicit human decisions over bootstrap candidate axes, distractor taxonomy entries, evidence anchors, and proto mother-family hypotheses.

Key fields:

- `confirmation_version`
- `enabled`
- `source`
- `status`
- `formalized`
- `promotion_allowed`
- `reviewer`
- `proto_mother_family`
- `axis_decisions`
- `rejected_or_deferred`
- `warnings`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did a human explicitly keep, drop, rename, merge, split, or map each axis?
- Are kept decisions still marked `proto_confirmed`, not formal?
- Are broad axes split before becoming proto fields?
- Are dropped or deferred axes preserved for audit?
- Are unknown source axes rejected instead of silently accepted?

Hard boundaries:

- `proto_confirmed` is not formal.
- `axis_decisions` are not automatic fields.
- `promotion_allowed` must be false.
- `formalized` must be false.
- No `card_specs` writeback has occurred.

## `formal_patch_draft.json`

Purpose: stores draft-only patch payloads generated from `axis_confirmation.json`, grouped by existing canonical targets.

Key fields:

- `draft_version`
- `enabled`
- `source`
- `status`
- `writeback_allowed`
- `formalized`
- `promotion_allowed`
- `proto_family`
- `proto_child_family`
- `target_patches`
- `warnings`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`, or as a source artifact for separately created canonical target patches.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are draft target groups limited to existing canonical targets?
- Are proto patches still marked `experimental` and `formalized=false`?
- Does the draft preserve the human rationale from `axis_confirmation.json`?
- Is any axis being forced into `question_card` when it belongs in prompt, signal, material, or validator layers?
- Is `writeback_allowed` false?

Hard boundaries:

- Draft patches are not writeback.
- `writeback_allowed` must be false.
- `formalized` must be false.
- No new promotion target is introduced.
- No validator, prompt, runtime mapping, or card spec file has been changed by this artifact.

## `formal_writeback_plan.json`

Purpose: stores a preview-only plan that explains how a `formal_patch_draft` would map to formal files if a later explicit writeback is approved.

Key fields:

- `plan_version`
- `status`
- `writeback_allowed`
- `requires_explicit_approval`
- `proto_family`
- `proto_child_family`
- `writeback_items`
- `legacy_family_impact`
- `regression_requirements`
- `rollback_note`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are the proposed target files correct?
- Are proposed additions scoped to proto material?
- Does the plan identify shared config touch points?
- Are old-family regression requirements explicit?
- Is the rollback note precise enough for a later writeback?

Hard boundaries:

- This is a preview plan, not approval to write files.
- `writeback_allowed` must be false.
- `requires_explicit_approval` must be true.
- No file is modified by generating this artifact.

## `formal_writeback_diff.md`

Purpose: stores a human-readable diff preview derived from `formal_writeback_plan.json`.

Key sections:

- target files
- proposed additions
- prompt guards
- validator candidates
- legacy family impact
- rollback
- regression requirements

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the diff preview show every file that would change?
- Are additions understandable before any writeback?
- Are prompt guards and validator candidates clearly separated?
- Does the preview avoid implying that files have already changed?

## `model_safe_gold_reconstruction_input.jsonl`

Purpose: stores model-readable, length-controlled true-question packages for model-based gold schema reconstruction.

Key fields:

- `sample_id`
- `source_file`
- `source_file_name`
- `mother_family_id`
- `child_family_id`
- `leaf_label`
- `raw_question_block`
- `stem`
- `options`
- `answer`
- `analysis`
- `exam_points`
- `correct_rate`
- `easy_wrong_option`
- `input_hash`
- `truncation`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is the input limited to true-question material and metadata?
- Is long raw text truncated and recorded?
- Does each row have `input_hash`?
- Does it avoid mixing prompt/task/output-schema text into material fields?

## `gold_reconstruction_results.jsonl`

Purpose: stores one unified-schema model reconstruction per sample.

This is gold reconstruction, not protocol distillation.

Key fields:

- `sample_id`
- `reconstruction_summary`
- `gold_material`
- `gold_question`
- `answer_mechanism`
- `distractor_mechanism`
- `gold_quality_flags`
- `mechanical_checks`
- `source`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the model understand the original true question?
- Did it rewrite the item into a new question?
- Did it invent missing source material?
- Did it correctly mark low confidence, missing information, and `needs_human_review`?
- Did it recognize when source article context is required?
- Does downstream `truth_gold_regression` use reconstructed gold rather than raw samples?

Hard boundaries:

- This artifact must not use `confirmed_fields`.
- This artifact must not emit validator rules, prompt guards, or card specs.
- This is not formal card, prompt, validator, or protocol field discovery.

## `gold_reconstruction_report.md`

Purpose: human-readable report for model-based gold reconstruction quality and mechanical check status.

Key sections:

- sample count
- question family guess distribution
- confidence distribution
- needs-human-review count
- source-article-required count
- warning statistics
- low-confidence samples
- needs-human-review samples
- examples
- mechanical check summary

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are low-confidence and review-needed samples visible?
- Are mechanical failures structural only rather than semantic judgments?
- Are warnings useful for deciding whether truth-gold regression can trust the reconstructed gold?

## `truth_gold_split_manifest.json`

Purpose: stores deterministic train/dev/eval/insurance holdout splits for a truth-gold regression loop.

Key fields:

- `split_version`
- `source_artifact_dir`
- `mother_family_id`
- `child_family_id`
- `leaf_label`
- `sample_count`
- `splits`
- `split_counts`
- `split_seed`
- `anti_overfit_notes`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does `insurance_holdout` exist and stay non-empty?
- Is the holdout excluded from axis discovery and prompt tuning?
- Are split counts appropriate for the source pack size?
- Is the split seed recorded for repeatability?

## `truth_gold_regression_results.json`

Purpose: stores deterministic original-vs-generated regression scores for a true-question gold reference loop.

Key fields:

- `regression_version`
- `mode`
- `gold_sample_count`
- `generated_item_count`
- `split_scores`
- `dimensions`
- `sample_results`
- `summary`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is generated comparison available for eval and insurance holdout?
- Is the result only surface-similar, or does it preserve the solving mechanism?
- Are overfit risks high because generated text copies the source too closely?
- Which failed dimension should feed the next distillation turn: material card, question card, prompt guard, validator candidate, or material processing?

Hard boundary:

- This artifact is a quality-regression report, not formal writeback approval.
- High fit does not mean true-question quality is good.

## `truth_gold_regression_report.md`

Purpose: human-readable truth-gold regression report summarizing split coverage, comparison status, dimension scores, failed samples, overfit risk, and next user-review focus.

Key sections:

- dataset split
- generated comparison status
- split scores
- dimension scores
- original-vs-generated examples
- failed or review-needed samples
- user review focus

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the report make holdout and overfit risk visible?
- Does it distinguish mechanism fit from lexical fit?
- Does it avoid claiming formal readiness?
- Are next feedback destinations clear enough for the next distillation loop?

## `source_discovery_queries.jsonl`

Purpose: stores de-question-bank-ified source discovery query candidates derived from reconstructed gold material.

Key fields:

- `sample_id`
- `query_version`
- `gold_source`
- `restored_human_material`
- `search_queries`
- `anti_question_bank_terms`
- `question_bank_contamination_risk`
- `likely_source_type`
- `requires_source_article`
- `needs_human_review`
- `warnings`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are search queries de-question-bank-ified?
- Does `restored_human_material` look like natural source text rather than a stem, option, or answer explanation?
- Are likely query results at risk of being question-bank pages?
- Do samples that lack reliable material get `needs_human_review=true`?

Hard boundary:

- This artifact does not execute web search.
- It must not treat raw samples as verified source material.

## `material_source_profile.json`

Purpose: summarizes material-source readiness, contamination risk, query quality, and whether the material line is ready for later source discovery.

Key fields:

- `profile_version`
- `source_artifact_dir`
- `sample_count`
- `gold_source`
- `using_raw_sample_material`
- `source_type_distribution`
- `question_bank_contamination_summary`
- `requires_source_article_count`
- `needs_human_review_count`
- `query_quality_summary`
- `material_line_conclusion`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is reconstructed gold available, or did the run fall back to raw sample material?
- Is the query set ready for source discovery, or blocked by contamination and missing material?
- Does the profile clearly avoid claiming that an original source has been found?

## `initial_material_seed_pack.jsonl`

Purpose: stores seed-only material requirements and source-discovery query bundles for later passage/source tooling.

Key fields:

- `seed_id`
- `sample_id`
- `seed_version`
- `source`
- `material_seed_type`
- `restored_human_material`
- `material_requirements`
- `search_queries`
- `negative_source_patterns`
- `status`
- `formalized`
- `needs_human_review`
- `warnings`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is each seed clearly `seed_only` and `formalized=false`?
- Are material requirements useful for later source discovery or passage services?
- Does the seed avoid becoming a production material library by accident?

## `source_discovery_preparation_report.md`

Purpose: human-readable material-line report for restored material clues, query examples, contamination risks, source readiness, and initial seed examples.

Key sections:

- sample count
- whether reconstructed gold was used
- query quality distribution
- question-bank contamination risk
- requires-source-article count
- needs-human-review samples
- restored human material examples
- search query examples
- initial material seed examples
- readiness and boundaries

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are query examples safe enough to send into later source discovery?
- Does the report show that no web search or material-card writeback happened?
- Is more human source text or URL evidence still needed?

## `search_request_manifest.json`

Purpose: records selected low-risk samples and search queries for bounded source candidate search.

Key fields:

- `search_version`
- `source_queries_path`
- `provider`
- `provider_status`
- `run_search`
- `selected_sample_ids`
- `query_count`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Were only low-risk source discovery rows selected?
- Was real search executed or was this a manual/mock request manifest?
- Are max sample, query, and result limits bounded?
- Is the provider status clear enough to reproduce the search?

## `source_candidate_results.jsonl`

Purpose: stores unverified candidate source search results and lightweight alignment signals.

Key fields:

- `sample_id`
- `query`
- `query_type`
- `candidate_rank`
- `title`
- `url`
- `domain`
- `snippet`
- `source_risk`
- `candidate_score`
- `candidate_status`
- `verification_status`
- `verified`
- `alignment_signals`
- `warnings`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the candidate look like an original article or only a question-bank/answer-analysis page?
- Are exam-training domains marked as risky?
- Does `verified` remain false until human review?
- Do alignment signals justify opening the URL in a later source review?

Hard boundaries:

- Candidate sources are not verified original sources.
- `verified` must be false.
- `verification_status` must be `unverified`.
- No passage-service or material-library write occurs.

## `source_candidate_summary.json`

Purpose: summarizes candidate source status, source risk counts, blocked samples, and whether the result is ready for human source review.

Key fields:

- `summary_version`
- `sample_count`
- `query_count`
- `candidate_count`
- `candidate_status_counts`
- `source_risk_counts`
- `samples_with_candidate`
- `samples_blocked`
- `ready_for_human_source_review`
- `ready_for_material_card_draft`
- `main_blockers`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are there enough non-question-bank candidates to review manually?
- Which samples are blocked?
- Are risky results counted instead of hidden?
- Is `ready_for_material_card_draft` still false?

## `source_candidate_alignment_report.md`

Purpose: human-readable source candidate search report.

Key sections:

- provider and run mode
- selected samples
- query list
- candidate status distribution
- source risk distribution
- top candidates by sample
- blocked samples
- human review checklist
- boundaries

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which candidate URLs should be opened by a human?
- Are question-bank-like and exam-training-like candidates rejected or downgraded?
- Is the report clear that no source has been confirmed?
- Is the next step source review/alignment rather than material-card writeback?

## `source_candidate_review_decisions.json`

Purpose: stores human-authored or UI-generated review decisions over `source_candidate_results.jsonl`.

Key fields:

- `review_version`
- `reviewer`
- `reviewed_at`
- `source_candidate_results_path`
- `decisions`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does each decision explain why the candidate is accepted, rejected, or deferred?
- Does it distinguish similar material from original-source candidates?
- Does any risky candidate require explicit `allow_risky_seed=true`?

## `source_candidate_review.json`

Purpose: normalized review output generated from source candidates and human decisions.

Key fields:

- `review_version`
- `status`
- `reviewer`
- `decision_counts`
- `accepted_count`
- `rejected_count`
- `deferred_count`
- `seed_count`
- `risky_accepted_seed_count`
- `verified_original_source_count`
- `reviewed_candidates`
- `warnings`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did user decisions match real candidates?
- Were question-bank and exam-training candidates rejected or explicitly warned?
- Are all reviewed candidates still `verified=false`?
- Is `verified_original_source_count` still zero?

Hard boundaries:

- Human review in this artifact does not confirm original sources.
- `verified_original_source_count` must be zero in v1.
- No source body is fetched.

## `source_seed_registry.jsonl`

Purpose: stores accepted candidate sources as seed-only assets for future crawl approval, source alignment, or material enrichment.

Key fields:

- `seed_id`
- `sample_id`
- `source_use`
- `seed_type`
- `url`
- `domain`
- `title`
- `snippet`
- `source_risk`
- `candidate_status`
- `crawl_priority`
- `verification_status`
- `verified_original_source`
- `verified`
- `formalized`
- `status`
- `review_rationale`
- `warnings`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is this seed original-source candidate, similar material, or domain seed?
- Is similar material clearly not treated as original source?
- Are risky accepted seeds visible?
- Are all seeds `status=seed_only`, `formalized=false`, and `verified=false`?

Hard boundaries:

- Source seed is not material library.
- Source seed is not material_card.
- Source seed is not verified source.

## `crawl_seed_manifest.json`

Purpose: summarizes seed registry for a future crawl-approval step.

Key fields:

- `crawl_seed_version`
- `source_seed_registry_path`
- `seed_count`
- `domain_counts`
- `priority_counts`
- `crawl_allowed`
- `requires_explicit_crawl_approval`
- `recommended_limits`
- `blocked_domains_or_patterns`
- `ready_for_crawl_review`
- `ready_for_material_card_draft`
- `limits`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is crawl still disabled?
- Are blocked domains and risky patterns visible?
- Does the manifest require explicit crawl approval?
- Is `ready_for_material_card_draft` false?

Hard boundaries:

- `crawl_allowed` must be false.
- `recommended_limits.fetch_body` must be false.
- This manifest is not crawl approval.

## `source_candidate_human_review_report.md`

Purpose: human-readable review report covering accepted, rejected, deferred, risky accepted seeds, and crawl seed preview.

Key sections:

- input candidate summary
- decision counts
- accepted similar material seeds
- accepted original-source candidates
- accepted domain seeds
- rejected question-bank / exam-training pages
- rejected irrelevant items
- deferred items
- risky accepted seeds
- crawl seed preview
- human review checklist
- boundaries

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did accepted seeds reflect user intent?
- Did rejected candidates avoid becoming seeds?
- Are crawl and material-card boundaries clear?

## `source_text_evidence_approval.json`

Purpose: records explicit human approval to prepare source text evidence from selected seed-only source candidates.

Key fields:

- `approval_version`
- `reviewer`
- `approved_seed_ids`
- `limits`
- `approval_scope`
- `does_not_confirm_original_source`
- `does_not_allow_material_library_write`
- `does_not_allow_material_card_write`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the user explicitly approve only the intended seed IDs?
- Are risky seeds excluded unless explicitly allowed?
- Is this approval limited to preparing evidence, not confirming the source?

## `source_text_evidence_manifest.json`

Purpose: summarizes source text evidence preparation over approved source seeds.

Key fields:

- `evidence_version`
- `status`
- `mode`
- `approved_seed_count`
- `result_count`
- `available_count`
- `blocked_count`
- `manual_required_count`
- `verified_original_source_count`
- `ready_for_source_gold_alignment`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which seeds produced available text evidence?
- Which seeds require manual source text review?
- Is `verified_original_source_count` still zero?

## `source_text_evidence_results.jsonl`

Purpose: stores reviewable source text excerpts or failure/manual-required rows for approved source seeds.

Key fields:

- `seed_id`
- `sample_id`
- `url`
- `source_use`
- `text_status`
- `text_excerpt`
- `text_hash`
- `boilerplate_risk`
- `question_bank_contamination_risk`
- `verified`
- `verified_original_source`
- `requires_human_review`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the excerpt look like source material rather than a question-bank page?
- Is unavailable text recorded honestly instead of fabricated?
- Are all rows still `verified=false` and `verified_original_source=false`?

## `source_text_evidence_report.md`

Purpose: readable report for source text evidence status, blocked/manual rows, and boundaries.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is source text evidence sufficient to attempt source/gold alignment?
- Which rows need manual text collection?
- Does the report avoid source verification claims?

## `source_gold_alignment_results.jsonl`

Purpose: stores source/gold alignment evidence comparing source text evidence with reconstructed gold material.

Key fields:

- `sample_id`
- `seed_id`
- `alignment_status`
- `relationship`
- `confidence`
- `matched_spans`
- `transformation_hypothesis`
- `verified_original_source`
- `requires_human_review`
- `warnings`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is the relationship original-source candidate, similar material, topic-related, or pollution?
- Are matched spans plausible?
- Does the artifact avoid treating alignment as source verification?

## `source_gold_alignment_summary.json`

Purpose: summarizes alignment status counts, relationship counts, and readiness for material quality regression.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are blocked or weak alignments visible?
- Is `verified_original_source_count` still zero?
- Is the next step human alignment review or quality regression?

## `source_gold_alignment_report.md`

Purpose: readable report for source/gold alignment evidence.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is similar material clearly not treated as original source?
- Are source/gold transformation hypotheses still hypotheses?
- What should the human reviewer confirm next?

## `source_gold_alignment_review.json`

Purpose: placeholder schema for human review of source/gold alignment decisions.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the user accept, reject, or defer each alignment relationship?
- Is any original-source claim explicitly left unverified until a later source verification step?

## `material_quality_regression_results.json`

Purpose: readiness evidence evaluating source provenance, contamination, alignment, sufficiency, slicing potential, family fit, bridge compatibility, and human-review requirements.

Key fields:

- `regression_version`
- `status`
- `ready_for_material_card_formalization`
- `dimensions`
- `blocking_issues`
- `recommended_next_action`
- `verified_original_source_count`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which material quality dimensions block formalization?
- Does the report avoid equating low contamination with verified source?
- Does any score incorrectly imply automatic approval?

## `material_quality_regression_report.md`

Purpose: readable material quality regression report.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are blocked dimensions understandable?
- Is material_card formalization still disabled until review/regression/writeback planning?

## `material_quality_review.json`

Purpose: placeholder schema for human review of material quality regression.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the user accept the quality diagnosis?
- Which evidence gaps should be addressed before material_card draft or writeback planning?

## `agent_review_feedback_input.json`

Purpose: records raw human natural-language feedback and the target scope before semantic normalization.

Key fields:

- `feedback_version`
- `reviewer`
- `target_scope`
- `target_artifacts`
- `raw_feedback`
- `context`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Is the feedback scoped to the right batch/sample/artifact?
- Are target artifacts traceable?
- Is the feedback preserved verbatim before normalization?

## `agent_review_feedback_normalized.json`

Purpose: stores structured dimensions inferred from human feedback, such as difficulty, material, distractor, prompt, validator, or runtime concerns.

Key fields:

- `status`
- `raw_feedback`
- `normalized_feedback`
- `routing`
- `writeback_allowed`
- `formalized`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Did the normalization preserve user intent?
- Are severity and target_line reasonable?
- Are high-severity items handled before readiness approval?

## `agent_review_feedback_report.md`

Purpose: readable report for normalized human feedback.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which feedback dimensions are blocking?
- Which line should handle each feedback item?
- Does the report avoid proposing direct writeback?

## `new_leaf_formalization_packet.json`

Purpose: combines discovery, confirmed axes, patch drafts, material drafts, source seeds, regression, and feedback into a draft review packet for a new leaf.

Key fields:

- `packet_type`
- `status`
- `family_context`
- `evidence_refs`
- `formal_target_candidates`
- `missing_evidence`
- `blocking_issues`
- `recommended_next_action`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are target candidates evidence-backed?
- Are material seeds still unverified?
- Are user feedback and regression gaps represented?
- Is the packet still draft-only?

## `new_leaf_formalization_packet_report.md`

Purpose: readable summary of the new-leaf formalization review packet.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- What is blocked?
- Which target candidates need writeback plans?
- Is runtime activation still required?

## `runtime_activation_plan.json`

Purpose: explains how a draft formalization packet would need to connect to runtime bindings, prompt assets, validators, material bridge mapping, and business subtype mapping.

Key fields:

- `status`
- `family_context`
- `runtime_targets`
- `proto_vs_formal`
- `activation_blockers`
- `required_regressions_before_activation`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which runtime bindings are missing?
- Can a proto trial run?
- Why formal generation remains blocked?
- Which changes need writeback plan and regression?

## `runtime_activation_plan_report.md`

Purpose: readable report of runtime activation requirements and blockers.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Does the plan stay read-only?
- Are runtime blockers explicit?
- Are required regressions listed?

## `formalization_readiness_checklist.json`

Purpose: records readiness gate checks before a new leaf can move toward writeback planning or guarded execution.

Key fields:

- `status`
- `family_context`
- `checks`
- `categories`
- `blocking_issues`
- `recommended_next_action`
- `writeback_allowed`
- `formalized`

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Are high-severity feedback items unresolved?
- Is runtime activation blocked?
- Are truth-gold regression and insurance holdout available?
- Is writeback safety incomplete?

## `formalization_readiness_report.md`

Purpose: readable summary of readiness gate pass/fail/warning checks.

Promotion evidence: yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config: no.

Independent promotion target: no.

Human review focus:

- Which checks block formalization?
- Is material_card still prevented from formalization when source evidence is unverified?
- Is explicit approval still required?

## Promotion Target Mapping

Allowed evidence targets:

- `leaf_pre_distill_report`
- `schema_gap_report`

Allowed formal landing targets, when separately approved by review:

- `question_card`
- `business_feature_card`
- `material_card`
- `signal_layer`
- `runtime_mapping`
- `prompt_assets`
- `validator_contract`
- `material_mapping`

Not an independent target in v1:

- `slot_projection_draft`
- `llm_safe_digest`
- `llm_field_probe`
- `bootstrap_discovery`
- `axis_confirmation`
- `formal_patch_draft`
- `formal_writeback_plan`
- `formal_writeback_diff`
- `model_safe_gold_reconstruction_input`
- `gold_reconstruction_results`
- `gold_reconstruction_report`
- `truth_gold_split_manifest`
- `truth_gold_regression_results`
- `truth_gold_regression_report`
- `source_discovery_queries`
- `material_source_profile`
- `initial_material_seed_pack`
- `source_discovery_preparation_report`
- `search_request_manifest`
- `source_candidate_results`
- `source_candidate_summary`
- `source_candidate_alignment_report`
- `source_candidate_review_decisions`
- `source_candidate_review`
- `source_seed_registry`
- `crawl_seed_manifest`
- `source_candidate_human_review_report`
- `source_text_evidence_approval`
- `source_text_evidence_manifest`
- `source_text_evidence_results`
- `source_text_evidence_report`
- `source_gold_alignment_results`
- `source_gold_alignment_summary`
- `source_gold_alignment_report`
- `source_gold_alignment_review`
- `material_quality_regression_results`
- `material_quality_regression_report`
- `material_quality_review`
- `agent_review_feedback_input`
- `agent_review_feedback_normalized`
- `agent_review_feedback_report`
- `new_leaf_formalization_packet`
- `new_leaf_formalization_packet_report`
- `runtime_activation_plan`
- `runtime_activation_plan_report`
- `formalization_readiness_checklist`
- `formalization_readiness_report`

`slot_projection_draft` must be referenced through `slot_projection_draft_path` inside a `leaf_pre_distill_report` patch payload.
`llm_safe_digest` and `llm_field_probe` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload.
`bootstrap_discovery` must be referenced through `bootstrap_discovery_path` inside a `leaf_pre_distill_report` patch payload.
`axis_confirmation` must be referenced through `axis_confirmation_path` inside a `leaf_pre_distill_report` patch payload.
`formal_patch_draft` must be referenced through `formal_patch_draft_path` inside a `leaf_pre_distill_report` patch payload unless a human separately creates explicit canonical target patches.
`formal_writeback_plan` and `formal_writeback_diff` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are preview evidence, not writeback approval.
`model_safe_gold_reconstruction_input`, `gold_reconstruction_results`, and `gold_reconstruction_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are gold reconstruction evidence, not protocol field discovery or formal writeback approval.
`truth_gold_split_manifest`, `truth_gold_regression_results`, and `truth_gold_regression_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are quality regression evidence, not formal writeback approval.
`source_discovery_queries`, `material_source_profile`, `initial_material_seed_pack`, and `source_discovery_preparation_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are material-line preparation evidence, not formal material cards, source search results, or material-library writes.
`search_request_manifest`, `source_candidate_results`, `source_candidate_summary`, and `source_candidate_alignment_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are unverified candidate-source evidence, not source confirmation, material-card drafts, or passage-service writes.
`source_candidate_review_decisions`, `source_candidate_review`, `source_seed_registry`, `crawl_seed_manifest`, and `source_candidate_human_review_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are human-review and seed-only evidence, not source confirmation, crawler approval, material-library writes, or material-card drafts.
`source_text_evidence_approval`, `source_text_evidence_manifest`, `source_text_evidence_results`, and `source_text_evidence_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are source-text evidence preparation artifacts, not source verification, body-ingest approval, material-library writes, or material-card drafts.
`source_gold_alignment_results`, `source_gold_alignment_summary`, `source_gold_alignment_report`, and `source_gold_alignment_review` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are alignment evidence, not verified original-source proof.
`material_quality_regression_results`, `material_quality_regression_report`, and `material_quality_review` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are material readiness evidence, not direct formal config and not material-card approval.
`agent_review_feedback_input`, `agent_review_feedback_normalized`, and `agent_review_feedback_report` must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are user feedback evidence, not direct configuration changes.
`new_leaf_formalization_packet`, `runtime_activation_plan`, and `formalization_readiness_checklist` plus their reports must be referenced through attachment paths inside a `leaf_pre_distill_report` patch payload. They are review, planning, and gate evidence, not writeback approval or executor artifacts.
## Behavior Distillation Business Summary v1

新增 artifacts:

- `behavior_distillation_business_summary.json`
- `behavior_distillation_business_report.md`
- `behavior_distillation_formalization_evidence.json`

边界:

- Promotion evidence only as attachment to `leaf_pre_distill_report`.
- Direct formal config: no.
- Independent promotion target: no.
- `formalized=false`.
- `writeback_allowed=false`.
- `executor_allowed=false`.

输入支持范围:

- behavior packet artifact JSON 或 `/api/v1/distill/behavior/packets` 等价输出。
- run details: `review_count`, `patch_count`, `promotion_count`, latest review/patch/promotion records。
- `agent_review_feedback_input.json` / `agent_review_feedback_normalized.json`。
- validator result、`truth_gold_regression_results.json`、`material_quality_regression_results.json`，存在时作为辅助 evidence。
- 缺失输入写入 `missing_evidence`，不直接失败。

输出结构要点:

- `business_overview`: 直接通过、修改后保留、驳回等审核画像。
- `high_frequency_edit_fields`: 高频修改字段。
- `high_frequency_failure_patterns`: 高频失败原因。
- `high_frequency_user_feedback`: 高频用户反馈。
- `candidate_improvement_signals`: 候选沉淀建议，包含 `target_layer`、证据、支持强度、风险、推荐状态、人审和回归要求。
- `not_recommended_for_promotion`: 单例、过拟合、高风险或冲突项。
- `recommended_next_action`: `human_review` / `observe_more` / `formalization_packet` / `collect_more_samples` / `blocked`。

接入:

- `new_leaf_formalization_packet.json` 可读取 `behavior_distillation_business_summary.json` 并生成 `behavior_distillation_summary`，只作为 evidence refs 或 evidence-only target candidate。
- `formalization_readiness_checklist.json` 可读取该 summary。缺失时是 warning，不阻塞主流程；高风险未人审 signal 至少进入 `review_needed`；冲突 signal 可进入 blocked/review_needed。
- 行为蒸馏 evidence 不能让 gate 进入 executor-ready，也不能替代 approval、writeback plan、regression 或人工确认。
