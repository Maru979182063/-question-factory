# behavior_distillation_business_summary_v1 执行报告

## 1. 修改文件列表

- `tools/leaf_pre_distill/behavior_distillation_business_summary.py`
- `tools/leaf_pre_distill/run.py`
- `tools/leaf_pre_distill/report_renderer.py`
- `tools/leaf_pre_distill/new_leaf_formalization_packet.py`
- `tools/leaf_pre_distill/formalization_readiness_gate.py`
- `docs/leaf_pre_distill_artifact_contract.md`
- `tests/test_leaf_pre_distill.py`
- `prompt_skeleton_service/app/demo_static/distill_demo.html`
- `prompt_skeleton_service/app/demo_static/distill_demo.js`
- `prompt_skeleton_service/tests/test_demo_shell.py`

## 2. 新增 artifacts

- `behavior_distillation_business_summary.json`
- `behavior_distillation_business_report.md`
- `behavior_distillation_formalization_evidence.json`

三者均为 `leaf_pre_distill_report` 的 promotion evidence attachment，不是 direct formal config，也不是 independent promotion target。

## 3. 输入支持范围

支持 behavior packet、run detail、agent review feedback、validator result、truth-gold regression、material quality regression。缺失输入写入 `missing_evidence`，不直接失败。

## 4. 输出 summary 结构

summary 固定包含 `summary_version=v1`、`formalized=false`、`writeback_allowed=false`、`executor_allowed=false`、`business_overview`、高频修改字段、高频失败模式、高频用户反馈、候选沉淀建议、不推荐沉淀项、缺失证据、阻塞问题和下一步建议。

## 5. 人话摘要规则

报告把字段统计翻译成业务表达，例如干扰项反复修改会解释为错项迷惑性可能不足，材料片段反复修改会解释为材料筛选或切片规则需要验证，单例反馈会明确标记为不建议沉淀。

## 6. Candidate Improvement Signal 规则

多次出现且有明确 target layer、风险可控、具备 regression 证据时，可标为 `suitable_for_formalization_packet`。出现不足标为 `single_case_only`，证据不足标为 `observe_more`，高风险或冲突需要人审和回归，blocked 只表示证据冲突或核心行为数据缺失。

## 7. 接入 new_leaf_formalization_packet

`new_leaf_formalization_packet` 会读取 `behavior_distillation_business_summary.json`，生成 `behavior_distillation_summary`，并把适合沉淀的信号作为 `evidence_only` 的 formal target candidate 或 evidence refs。不会新增正式 promotion target，不覆盖用户 axis confirmation。

## 8. 接入 readiness gate

readiness gate 会读取 behavior summary。缺失时只 warning；高风险未人审 signal 至少让 gate 进入 `review_needed`；行为信号与 validator/regression 冲突时可 blocked。行为蒸馏不能让 gate 进入 executor-ready。

## 9. 前端 UI 增强

distill demo 新增“业务蒸馏总览”区块，支持粘贴 behavior packet JSON 和可选 feedback JSON，生成业务摘要、JSON artifact 和 Markdown report，并支持复制/下载。页面明确展示 evidence-only 边界和不会调用 executor。

## 10. 测试结果

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`: 95 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`: 15 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`: 10 tests OK.
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`: 4 tests OK.

补充检查：

- `python -m py_compile tools/leaf_pre_distill/behavior_distillation_business_summary.py tools/leaf_pre_distill/new_leaf_formalization_packet.py tools/leaf_pre_distill/formalization_readiness_gate.py tools/leaf_pre_distill/run.py`: OK.
- `node --check prompt_skeleton_service/app/demo_static/distill_demo.js`: 未执行成功，本机 `node.exe` 返回 Access is denied；已由 demo shell 静态测试覆盖关键入口和边界字符串。

## 11. 明确没有做

- 没有正式写回。
- 没有 executor 调用。
- 没有 card_specs 写回。
- 没有 material_card 写回。
- 没有 prompt_assets 写回。
- 没有 runtime_mapping 写回。
- 没有 validator_contract 写回。
- 没有 generation / validator / prompt / runtime 主链修改。
- 没有新增 promotion target。
