# Axis Confirmation / Formal Patch Draft Audit

Date: 2026-04-25

## Verdict

The current distillation table has reached the "new leaf lab" stage:

```text
source pack
-> leaf_pre_distill artifacts
-> optional LLM probe
-> bootstrap_discovery hypotheses
-> distill dataset/session/trial
-> review/patch/promotion evidence bundle
```

It has not yet reached the "semi-automatic card factory" stage.

The missing layer is not another model call. The missing layer is an explicit
human confirmation state between:

```text
candidate_axes.status = hypothesis
```

and:

```text
formal patch draft for question_card / business_feature_card / material_card /
signal_layer / runtime_mapping / prompt_assets / validator_contract /
material_mapping
```

Without that layer, the system can show promising axes, but it cannot safely say
which axes should become proto fields, seed markers, prompt constraints, material
mapping rows, or validator candidates.

## Current Chain

### Offline leaf_pre_distill

The offline chain can already generate:

- `manifest.json`
- `samples.jsonl`
- `behavior_traces.jsonl`
- `field_candidates.json`
- `slot_projection_draft.yaml`
- `report.md`
- `llm_safe_digest.json`
- `llm_field_probe.json`
- `bootstrap_discovery.json`

For known families, `field_candidates.json` can contain direct candidate fields.
For unknown or weakly matched families, `bootstrap_discovery.json` can produce
candidate axes and proto-family hypotheses.

### Evidence Contract

`docs/leaf_pre_distill_artifact_contract.md` already separates evidence artifacts
from formal config:

- `leaf_pre_distill_report` is evidence.
- `schema_gap_report` is evidence.
- `slot_projection_draft` is an attachment, not a promotion target.
- `llm_field_probe` is an attachment, not a promotion target or judge.
- `bootstrap_discovery` is an attachment, not a promotion target.

This boundary is sound and should be preserved.

### Workbench Promotion Layer

The workbench already supports canonical targets:

- `question_card`
- `business_feature_card`
- `material_card`
- `signal_layer`
- `runtime_mapping`
- `prompt_assets`
- `validator_contract`
- `material_mapping`
- `leaf_pre_distill_report`
- `schema_gap_report`

It also requires explicit patches for every promoted target. This means the
existing workbench is already capable of carrying a future formal patch draft
through review and promotion, as long as the draft is expressed as a patch payload
for one of the canonical targets.

## Current Gap

`bootstrap_discovery.json` deliberately says:

```text
candidate_axes are not fields
hypothesis is not confirmed
discovery is not promotion
proto_mother_family is not a formal mother_family
```

That is correct, but there is currently no next artifact that records:

- which candidate axes the user kept;
- which candidate axes the user dropped;
- whether an axis was renamed, merged, split, or downgraded to a note;
- whether an axis should become a proto field, seed marker, prompt guard, material
  mapping hint, or validator candidate;
- what evidence justified the decision;
- what follow-up tests or ablation questions are still required.

Because that artifact is missing, the system has to jump from:

```text
candidate_axes: hypothesis
```

directly to manual editing or ad hoc patch payloads.

That jump is too large for a repeatable product workflow.

## Recommended State Model

The next state model should be:

```text
hypothesis
-> proto_confirmed
-> formal_patch_draft
-> promoted_evidence_bundle
-> manually_written_formal_config
```

Meaning:

- `hypothesis`: machine-generated or heuristic discovery; not approved.
- `proto_confirmed`: human accepted the axis as worth using in this proto family;
  still not a formal field.
- `formal_patch_draft`: system converted confirmed decisions into structured
  patch drafts for existing canonical targets; still not written back.
- `promoted_evidence_bundle`: review/patch/promotion bundle records that a human
  approved the draft as evidence.
- `manually_written_formal_config`: a later, separate action updates formal card
  specs or runtime config.

## User Confirmation Actions

The confirmation layer should support at least these actions:

- `keep`: keep this axis for proto confirmation.
- `drop`: reject this axis.
- `rename`: keep but rename the axis.
- `merge`: combine several axes into one.
- `split`: split one broad axis into several narrower axes.
- `downgrade_to_note`: keep as human context only.
- `promote_to_proto_field`: turn an axis into a proto field draft.
- `map_to_seed_marker`: use as deterministic marker seed.
- `map_to_prompt_guard`: use as prompt guard or generation instruction draft.
- `map_to_material_mapping`: use as material/card routing hint.
- `map_to_validator_candidate`: use as validator contract candidate.
- `map_to_distractor_taxonomy`: use as distractor mode taxonomy.

These actions should be explicit user decisions, not inferred silently.

## Proposed New Artifacts

### `axis_confirmation.json`

Purpose:

- Stores human decisions over `candidate_axes`, `distractor_taxonomy`, and
  `proto_mother_family` hypotheses.

Promotion evidence:

- Yes, only as an attachment to `leaf_pre_distill_report`.

Direct formal config:

- No.

Independent promotion target:

- No.

Key boundary:

- `proto_confirmed` means "approved for proto drafting", not "formal schema".

### `formal_patch_draft.json`

Purpose:

- Converts `proto_confirmed` decisions into draft patch payloads grouped by
  existing canonical targets.

Promotion evidence:

- Yes, either as an attachment to `leaf_pre_distill_report` or as the payload
  source for explicit canonical target patches.

Direct formal config:

- No.

Independent promotion target:

- No.

Key boundary:

- It is a draft payload, not an automatic writeback.

## Formal Patch Draft Target Mapping

The draft should only emit target groups that already exist:

- `question_card`
- `business_feature_card`
- `material_card`
- `signal_layer`
- `runtime_mapping`
- `prompt_assets`
- `validator_contract`
- `material_mapping`

It should not invent new promotion targets.

For `word_usage_content_word`, expected draft groups may include:

- `business_feature_card`: proto feature fields such as contextual meaning mode.
- `signal_layer`: solving-action markers and evidence anchors.
- `runtime_mapping`: proto route identifiers and family/subfamily mapping draft.
- `prompt_assets`: prompt guards for contextual meaning explanation.
- `validator_contract`: minimal structure checks and future business checks.
- `material_mapping`: context-window material strategy hints.

The first implementation should not generate a full formal `question_card` unless
the user explicitly confirms that the proto family is ready to become a formal
card family.

## Current Storage Fit

No database migration is required for the next step.

The workbench patch table stores:

```text
target TEXT
payload_json JSON
```

So `axis_confirmation.json` and `formal_patch_draft.json` can remain offline
artifacts and be referenced from a `leaf_pre_distill_report` patch payload, while
selected draft groups can also be copied into canonical target patches.

## Risks

### Over-promotion Risk

The biggest risk is treating `proto_confirmed` as formal. It must remain a
middle state.

### Axis/Field Confusion

Candidate axes are dimensions of variation. Fields are schema slots. A confirmed
axis may become a field, prompt guard, material mapping rule, validator candidate,
or only a note.

### Broad Axis Risk

Unknown families often produce broad axes like "contextual meaning mode". Human
confirmation must allow split and merge decisions before formal patch drafting.

### Prompt-Only Drift

Some confirmed axes may be better represented as prompt guards, not schema fields.
The draft generator must not force everything into `question_card`.

### Existing Route Safety

The next step must not affect existing `sentence_fill`, `sentence_order`, or
`center_understanding` generation. It should be offline/artifact-first.

## Recommendation

Use a two-artifact bridge:

```text
bootstrap_discovery.json
-> axis_confirmation.json
-> formal_patch_draft.json
```

Then let the existing workbench carry those artifacts through review, patch, and
promotion.

This turns the current system from a discovery lab into a controlled proto-card
drafting workflow without silently changing formal cards.

