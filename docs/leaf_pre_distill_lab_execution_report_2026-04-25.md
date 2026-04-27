# 叶族预蒸馏实验台执行报告

日期：2026-04-25

## 本轮完成内容

已按 MVP 路线落地一个离线版 `leaf_pre_distill` 工具链。它不改正式题卡、不改 service、不自动 promotion，只负责从新叶族题包生成可复现候选产物。

新增工具模块：

| 文件 | 作用 |
|---|---|
| `tools/leaf_pre_distill/docx_reader.py` | 读取 docx，抽取题目块、题干、答案、解析、考点、正确率 |
| `tools/leaf_pre_distill/behavior_marker.py` | 把样本转成可观测解题动作 |
| `tools/leaf_pre_distill/field_candidate_builder.py` | 聚合字段候选、支持率、schema gap、slot projection draft |
| `tools/leaf_pre_distill/report_renderer.py` | 生成 Markdown 预蒸馏报告 |
| `tools/leaf_pre_distill/run.py` | CLI 入口 |
| `tests/test_leaf_pre_distill.py` | 防止字段污染的最小回归测试 |

CLI 形态：

```powershell
python -m tools.leaf_pre_distill.run `
  --mother-family-id sentence_order `
  --child-family-id sentence_order_sequence `
  --leaf-label "日常逻辑-时间脉络" `
  --source-file "C:\...\日常逻辑-时间脉络.docx" `
  --output-dir "data\leaf_pre_distill\smoke_sentence_order_timeline_20260425"
```

## Artifact 产物

每次运行会生成：

```text
manifest.json
samples.jsonl
behavior_traces.jsonl
field_candidates.json
slot_projection_draft.yaml
report.md
```

这些产物对应我们计划里的：

- `leaf_pack_manifest`
- `parsed_leaf_samples`
- `behavior_trace`
- `leaf_field_candidate_report`
- `slot_projection_draft`
- `schema_gap_report`

## 冒烟测试

使用用户提供的 4 个语句排序题包分别跑 clean leaf：

| 叶族 | 样本数 | 高置信主字段 | 支持率 | Schema Gap |
|---|---:|---|---:|---:|
| 首句特征-背景引入 | 50 | `opening_anchor_type=background_intro` | 100% | 0 |
| 关联词-其他 | 49 | `local_binding_strength=high` | 100% | 0 |
| 日常逻辑-时间脉络 | 50 | `ordering_logic=timeline_progression` | 100% | 1 |
| 结论 | 39 | `closing_anchor_type=conclusion` | 100% | 0 |

时间脉络的 schema gap 与前面人工实验一致：

```yaml
field: timeline_progression_as_middle_structure
reason: timeline progression is better represented as ordering_logic or material overlay than as middle_structure_type
suggested_resolution: keep middle_structure_type=local_binding and encode ordering_logic=timeline_progression
```

这说明工具链能复现核心判断：时间脉络不是硬塞 `middle_structure_type`，而应进入 `ordering_logic` 或 material overlay。

## 质量修正

第一版冒烟时发现一个污染点：

```text
“确定首句”这种通用动作会误触发 background_intro。
```

已修正为：`background_intro` 只由“背景引入 / 背景铺垫 / 引出话题 / 宏观话题 / 社会热词 / 人们常说”等特异证据触发。新增单测保证通用首句判断不会生成 `opening_anchor_type=background_intro`。

## 测试结果

已执行：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：

```text
Ran 2 tests in 0.001s
OK
```

同时执行：

```powershell
python -m tools.leaf_pre_distill.run --help
```

CLI 正常输出参数说明。

注意：本机未安装 `pytest`，所以本轮使用标准库 `unittest`。

## 生成的冒烟产物目录

| 叶族 | 产物目录 |
|---|---|
| 四包混跑基线 | `data/leaf_pre_distill/smoke_sentence_order_20260425/` |
| 首句特征-背景引入 | `data/leaf_pre_distill/smoke_sentence_order_opening_20260425/` |
| 关联词-其他 | `data/leaf_pre_distill/smoke_sentence_order_connector_20260425/` |
| 日常逻辑-时间脉络 | `data/leaf_pre_distill/smoke_sentence_order_timeline_20260425/` |
| 结论 | `data/leaf_pre_distill/smoke_sentence_order_tail_20260425/` |

## 当前边界

本轮完成的是离线内核，不是完整产品化接入。

尚未做：

- API 入口；
- 前端 tab；
- 数据库表；
- promotion target 扩展；
- 自动 attach 到 distill session；
- 自动写回 card_specs；
- LLM 裁判或聚类。

这是刻意保守的：先让“新叶族预处理 -> 候选字段 -> 报告/草案”跑稳，再接入现有蒸馏工作台。

## 下一步建议

建议下一轮做两件事：

1. 写 `docs/leaf_pre_distill_artifact_contract.md`，把 artifact 契约正式化。
2. 扩展 distill patch / promotion target，让 `leaf_pre_distill_report` 和 `schema_gap_report` 可以被现有 review / promotion bundle 承载。

这两步完成后，叶族预蒸馏就能正式挂到现有蒸馏台，而不是只作为离线脚本存在。
