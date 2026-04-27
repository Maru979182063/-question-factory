# System Debug Adapter Registry Contract

日期：2026-04-27

## 1. 目标

`artifact adapter registry` 是 system debug control plane 的连接语义层。

它解决的问题是：

- 总控台不只知道“有哪些文件”；
- 还知道“哪个 output artifact 可以作为哪条链的 input”；
- 还知道“必需字段是什么、缺失时怎么降级、是否只能人工传递”。

它不是：

- 自动总执行器；
- LLM 调度器；
- 生题执行器；
- distill run 执行器；
- crawler；
- writeback executor；
- promotion executor。

## 2. 强边界

本层保持只读：

- 不自动执行任何链；
- 不自动调用 LLM；
- 不自动执行生题；
- 不自动执行 distill run；
- 不自动执行 source search / crawl / body fetch；
- 不自动写 material_card / card_specs / runtime / prompt / validator；
- 不自动 promotion；
- 不把人工串联说成自动 orchestrator。

## 3. Adapter Entry

每条 adapter entry 至少包含：

```json
{
  "adapter_name": "",
  "source_chain": "",
  "source_artifact_role": "",
  "source_artifact_patterns": [],
  "target_chain": "",
  "target_input_role": "",
  "required_fields": [],
  "optional_fields": [],
  "missing_field_strategy": "block | warn | degrade | manual_fill",
  "manual_path_allowed": true,
  "contract_status": "explicit | inferred | manual_only",
  "notes": ""
}
```

字段解释：

- `adapter_name`：连接名称，必须唯一。
- `source_chain`：产出 artifact 的链。
- `source_artifact_role`：源 artifact 的语义角色。
- `source_artifact_patterns`：用于 artifact index 匹配的文件名或路径后缀。
- `target_chain`：消费 artifact 的链。
- `target_input_role`：目标链中的输入角色。
- `required_fields`：连接成立所需字段。
- `optional_fields`：可用但不阻断的字段。
- `missing_field_strategy`：缺字段处理策略。
- `manual_path_allowed`：是否允许仍通过人工路径传递。
- `contract_status`：契约成熟度。
- `notes`：边界说明。

## 4. Contract Status

### explicit

已有明确代码、CLI 参数、schema 或文档契约。

含义：

- 连接关系已经比较稳定；
- 总控台可以检查 artifact 是否满足最低字段；
- 但仍不自动执行目标链。

### inferred

根据当前代码/服务关系可以推断，但还没有稳定落文或统一 artifact contract。

含义：

- 可以用于报告和人工调试；
- 不能当作自动编排依据；
- 应优先补正式 adapter 文档或统一 artifact schema。

### manual_only

目前只能人工拼接。

含义：

- 总控台只能提示人工桥接；
- 不应标记为自动 ready；
- 不应被 master execution plane 使用。

## 5. Missing Field Strategy

### block

缺 required field 时阻断连接。

适用：

- gold schema；
- distill run；
- promotion bundle；
- 结构不完整会导致误判的输入。

### warn

缺字段时允许继续展示，但报告 warning。

适用：

- 边界说明；
- 统计字段；
- 非核心辅助字段。

### degrade

缺字段时降级为人工审查或弱证据。

适用：

- 生成结果到难度评估；
- 难度 evidence 到 distill review。

### manual_fill

缺字段时必须人工补齐。

适用：

- manual-only 链；
- 尚未正式实现的清洗、切片、选段；
- draft 到 runtime 的人工桥接。

## 6. 当前登记的 adapter

最小版本登记：

1. `gold_reconstruction_to_truth_gold_regression`
2. `source_review_seed_registry_to_material_protocol_split_pipeline`
3. `source_review_crawl_manifest_to_material_protocol_split_pipeline`
4. `source_review_to_material_cleaning_slicing_chain`
5. `material_protocol_split_to_question_generation_runtime`
6. `question_protocol_patch_to_question_generation_runtime`
7. `question_generation_to_difficulty_control`
8. `truth_gold_regression_to_difficulty_control`
9. `question_generation_to_distillation_workbench`
10. `difficulty_control_to_distillation_workbench`

其中：

- `explicit`：已有较明确契约；
- `inferred`：能推断但尚未稳定落文；
- `manual_only`：只能人工拼接。

## 7. 输出 artifact

新增：

- `system_debug_adapter_registry.json`

该 artifact 包含：

- adapters；
- validation_errors；
- contract_status_counts；
- resolutions；
- read_only / auto_execute / writeback_allowed 边界。

## 8. Report 增强

`system_debug_report.json/md` 新增：

- `adapter_coverage`
- `adapter_status_matrix`
- `explicit_adapters`
- `inferred_adapters`
- `manual_only_adapters`
- `manual_only_connection_list`
- `missing_required_fields`

每条 chain 新增：

- `inbound_adapters`
- `outbound_adapters`
- `ready_to_connect`
- `blocked_by_missing_fields`
- `manual_bridge_required`

## 9. 当前限制

- adapter 匹配仍基于文件名和路径后缀；
- JSONL 只检查首条记录的 required fields；
- 不读取数据库 run；
- 不判断业务语义正确性；
- 不执行目标链；
- 不判断 draft 是否已经正式写回。

