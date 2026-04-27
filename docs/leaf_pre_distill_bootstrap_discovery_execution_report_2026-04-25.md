# Leaf Pre-Distill Bootstrap Discovery Execution Report

Date: 2026-04-25

## Scope

This slice adds the first deterministic `bootstrap_leaf_discovery` layer for unknown or weakly matched leaf packs.

The layer generates:

- `bootstrap_discovery.json`

This artifact is evidence-only and can only be attached to `leaf_pre_distill_report`.

## Behavior

Default behavior remains closed:

- no `--enable-bootstrap-discovery`: no `bootstrap_discovery.json`
- no automatic write-back to formal configuration
- no new promotion target

When enabled, the tool builds hypothesis-level discovery from parsed samples, behavior traces, field candidates, and optional LLM-safe digest metadata.

The first heuristic version looks at:

- `exam_points`
- question ask patterns in `stem`
- solving-action wording in `analysis`
- distractor markers in `analysis`
- weak difficulty signals from `correct_rate` and `wrong_option`

## Boundaries

- `candidate_axes` are not fields.
- `hypothesis` is not confirmed.
- `discovery` is not promotion.
- `proto_mother_family` is not a formal mother family.
- `promotion_allowed` is always false.
- No `confirmed_fields`, `slot_projection_updates`, or `validator_contract_candidates` are emitted.

## Validation

Commands run:

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
python -m py_compile tools/leaf_pre_distill/bootstrap_discovery.py tools/leaf_pre_distill/run.py tools/leaf_pre_distill/report_renderer.py
```

Result:

- `test_leaf_pre_distill.py`: 12 tests OK
- `test_distill_workbench.py`: 10 tests OK
- `py_compile`: OK

Real-pack smoke:

- input: `实词.docx`
- output: `data/leaf_pre_distill/real_word_usage_bootstrap_20260425`
- `field_candidate_count`: 0
- `bootstrap_discovery.json`: generated
- candidate axes included `explanation_target_type`, `referent_resolution_mode`, `contextual_meaning_mode`, `concept_boundary_mode`, and `option_elimination_mode`.

## Next Use

For packs such as `word_usage / 实词`, this layer can produce candidate axes even when deterministic `field_candidates` is empty. The next layer should confirm, merge, split, downgrade, or reject those axes before any seed marker or proto schema is manually written.
