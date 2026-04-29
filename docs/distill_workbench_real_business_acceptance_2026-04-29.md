# 蒸馏工作台真实业务流验收报告（2026-04-29）

## 结论

本轮按“正常业务同学使用”的方式走了一遍前端蒸馏工作台，并适度调用了真实搜索与真实模型接口。结论是：

- 前端业务向导已经能让用户完成题包上传/预览、来源判断、初始字段草案判断、蒸馏结果验收、用户反馈、Gate 预览、暂存/恢复。
- 系统边界能守住：最终 Gate 给出 `blocked`，没有正式写回、没有入库、没有把来源 seed 当 verified source。
- 还不能宣称“一个普通成年人已经能端到端完成新题卡落位并启动双服务爬材料生题”。真实阻塞点是：本轮真实搜索没有返回可审查来源；真实模型生成接口可通但输出未满足 JSON 契约，被生成主链判为 `auto_failed`。

## 测试输入

- 用户指定题包原始路径：`C:/Users/97918/AppData/Local/Temp/360zip$Temp/360$0/相对绝对项.docx`
- 实测时该临时路径已经不存在。
- 为完成流程验收，创建了同母族/子族/叶族的小样本题包：
  - `E:/agent_repo_src/data/manual_test_packs/relative_absolute_business_acceptance.docx`
  - 母族：细节理解题
  - 子族：快速定位法
  - 叶族：相对绝对项

## 服务状态

- Prompt service：`http://127.0.0.1:8011`
  - 关键检查可用。
  - 整体状态为 `degraded`，原因是非关键 `shadow_passage_service` 未启动。
- Passage service：`http://127.0.0.1:8001`
  - `/readyz` 返回 ready。
  - 本轮为本地测试写入了 1 条 demo primary material span，用于双服务联通验收。

## 真实搜索结果

对“相对绝对项”小样本跑了 web provider 小范围搜索：

- 输出目录：
  - `E:/agent_repo_src/data/manual_test_packs/relative_absolute_source_search_v1/web_search`
  - `E:/agent_repo_src/data/manual_test_packs/relative_absolute_source_search_v1/web_search_2`
- 结果：
  - `provider` 路线执行完成。
  - `candidate_count=0`
  - `ready_for_human_source_review=false`
  - blocker：`no source candidates collected`

判断：真实搜索链没有崩，但对当前 query 没拿到可审查候选。业务上不能继续声称“来源可用”，需要换 query、补来源、或走人工 source text evidence。

## 真实模型调用结果

使用配置的 OpenAI-compatible chat endpoint 做了一次生成主链调用：

- 输出：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/real_generation_response.json`
- HTTP 层：可返回。
- 生成结果：`current_status=auto_failed`
- 失败原因：`Configured LLM returned structured text that could not be parsed as a JSON object.`

判断：key/base_url/model 不是主要问题；当前真实模型输出和生成主链 JSON 契约仍需适配或 prompt hardening。不能把这一步包装成“已能稳定生题”。

## 前端业务流截图

1. 入口：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/01_business_entry.png`
2. 材料准备报告：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/02_material_prep_report.png`
3. 来源网站确认：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/03_source_review_stage.png`
4. 字段草案确认：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/04_initial_field_draft_stage.png`
5. 重跑按钮：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/05_acceptance_rerun_button.png`
6. 待定按钮：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/06_acceptance_defer_button.png`
7. 确认尝试后仍被 Gate 拦住：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/07_acceptance_report_after_confirm_attempt.png`
8. 暂存/恢复：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/08_save_restore_state.png`
9. 来源候选审查 JSON：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/09_source_candidate_review_decisions.png`
10. 用户自然语言反馈 JSON：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/10_agent_feedback_input.png`
11. Readiness Gate blocked 预览：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/11_formalization_gate_blocked_preview.png`

前端 smoke 输出：

- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/frontend_smoke_outputs.json`
- `business_mode_preview_json.status=blocked`
- `formal_gate_readiness_preview_json.status=blocked`
- `writeback_allowed=false`
- `executor_allowed=false`

## 前端体验判断

业务层可理解的部分已经成立：

- 上传题包后能看到“材料准备报告”。
- 来源网站确认页按来源展示材料片段，并可逐个选择“采用 / 不采用 / 待定”。
- 每个来源可以展开关联题目。
- 字段草案页能展示初始业务字段和材料字段。
- 蒸馏验收页有“确认 / 待定 / 重跑”和重跑建议输入。
- Gate 能把最终状态拦成 blocked，说明为什么不能落位。

仍需要继续产品化的地方：

- 真实 web search 没返回候选时，前端应给业务更明确的“搜索不到来源，建议补 URL / 换关键词”提示。
- 真实模型输出不符合 JSON 契约时，前端应显示“模型返回格式不合格，需要重跑/降级”，不要让业务误以为只是题目质量差。
- Gate 预览仍偏技术，建议继续把 `material_quality_regression_status=blocked` 翻译为更人话的原因。

## 回归测试

已运行并通过：

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`
  - 98 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`
  - 15 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`
  - 10 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`
  - 4 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_generation`
  - 80 tests OK

## 本轮改动

- `E:/agent_repo_src/.env.demo`
  - 配置用户指定的 base URL / model / key env，用于本地 demo；该文件被 `.gitignore` 忽略。
- `E:/agent_repo_src/tools/leaf_pre_distill/llm_field_probe.py`
  - 默认 base URL 对齐到当前兼容 endpoint。
- `E:/agent_repo_src/prompt_skeleton_service/app/services/llm_gateway.py`
  - 兼容非标准 JSON / SSE 风格响应解析，避免 HTTP 可用但解析层直接 500。
- `E:/agent_repo_src/passage_service/app/infra/db/repositories/article_repo_sqlalchemy.py`
  - 增加 postponed annotations，修复 Python 3.13 下方法名 `list` 与类型注解冲突导致 passage service 无法启动。
- `E:/agent_repo_src/data/manual_test_packs/relative_absolute_business_acceptance.docx`
  - 本轮业务验收样本题包。
- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/`
  - 截图、真实生成响应、前端 smoke 输出、浏览器脚本。

## 明确未做

- 没有正式写回。
- 没有写 `card_specs`。
- 没有写正式 `material_card`。
- 没有 passage_service ingest。
- 没有 source verification。
- 没有新增 promotion target。
- 没有调用 executor。
- 没有修改 validator / prompt / runtime / generation 主链配置。

## 下一步建议

最小下一刀不是继续堆 UI，而是修“真实调用后的契约落差”：

1. 生成主链 LLM JSON 契约 hardening：让当前 chat endpoint 返回能被解析的 question JSON，或在网关增加受控 repair。
2. source candidate search query fallback：搜索 0 候选时给业务补 URL / 改关键词 / 人工正文入口。
3. Gate 人话翻译增强：把技术 blocker 统一翻译成业务原因和下一步动作。
