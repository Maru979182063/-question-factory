# center_understanding / degree_word 字段消费映射

状态：candidate consumption map
日期：2026-04-21

## 映射总表

| 真题现象 | 标注字段 | 控制轴 | Prompt 消费点 | Validator 复查点 | Diff Report 呈现 |
| --- | --- | --- | --- | --- | --- |
| 易错项抓住局部细节 | `center_axes.local_detail_distractor_strength` | primary | 要求最强错项局部真实但非中心 | 检查错项是否只是局部、例子、原因或结果 | `axis_diff.local_detail_distractor_strength` |
| 决胜证据隐藏在尾句/转折/程度词 | `center_pairwise_axes.decisive_evidence_visibility_load` | hard guardrail | hard 档要求证据不在首句直接暴露 | 检查解析是否指出决胜证据位置 | `review_delta.evidence_visibility` |
| 易错项接近主旨 | `center_pairwise_axes.easy_wrong_main_claim_proximity` | hard guardrail | hard 档允许错项接近但必须范围/程度错位 | 检查错项与主旨的差异是否明确 | `axis_diff.main_claim_proximity` |
| 排除易错项需要多步判断 | `center_pairwise_axes.exclusion_reasoning_load` | diagnostic | 不单独控制，可用于提高解析质量 | 检查解析是否说明多步排除路径 | `review_delta.exclusion_reasoning` |
| 正确项抽象换说 | `center_axes.correct_option_abstraction_gap` | secondary diagnostic | 可控制正确项不要照抄原文 | 检查正确项是否覆盖中心且不过度抽象 | `axis_diff.correct_option_abstraction_gap` |
| 文段行文转折复杂 | `center_axes.discourse_turn_complexity` | passage diagnostic | 可控制文段结构复杂度 | 检查主旨是否依赖转折/总结/对策 | `structural_changes.discourse_turn` |

## Prompt 最小消费格式

```yaml
leaf_control_box:
  family: center_understanding
  leaf_family: degree_word
  target_band: hard
  local_detail_distractor_strength: 3
  decisive_evidence_visibility_load: 4
  easy_wrong_main_claim_proximity: 4
```

## Validator 最小输出格式

```json
{
  "actual_leaf_control_band": "hard-control",
  "local_detail_distractor_strength": 3,
  "decisive_evidence_visibility_load": 4,
  "easy_wrong_main_claim_proximity": 4,
  "exclusion_reasoning_load": 4,
  "degree_scope_gap": "wrong option is locally valid but too narrow",
  "validator_status": "pass_candidate"
}
```

## Diff Report 字段

```json
{
  "target_difficulty": "hard",
  "actual_difficulty": "medium",
  "gold_difficulty": 0.58,
  "fit_result": "under_shot",
  "axis_diff": {
    "local_detail_distractor_strength": {
      "target": 3,
      "actual": 2
    }
  },
  "structural_changes": [
    "strongest distractor became obviously secondary"
  ],
  "validator_status": "needs_review",
  "review_delta": "hard guardrail missing",
  "promotion_recommendation": "keep_candidate_only"
}
```

## 关键边界

- `local_detail_distractor_strength` 是当前主旋钮。
- pairwise 字段是 hard guardrail，不是独立主轴。
- passage 字段用于诊断，不进入当前 projection。
- 任何自动回写主配置都必须禁止。
