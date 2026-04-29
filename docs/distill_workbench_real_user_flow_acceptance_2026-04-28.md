# 蒸馏工作台真实业务流验收报告（相对绝对项）

## 结论

本轮按业务同学路径跑通了前端工作台的“新题包正式化业务向导”：

题包上传 / 解析 -> 来源网站确认 -> 字段草案确认 -> 蒸馏结果验收 -> 重跑 / 待定 / 确认按钮 -> Gate 拒绝正式落位。

最终结论是：前端流程可走完，且最后没有越权落位；但本轮外部模型 API 返回 429，说明“真实模型返回”这一项未成功，需要更换可用额度 / endpoint 后再做一次模型侧复测。

## 输入

- 题包文件：`C:/Users/97918/AppData/Local/Temp/360zip$Temp/360$0/相对绝对项.docx`
- 用户指定母族：细节理解题
- 用户指定子族：快速定位法
- 用户指定叶族：相对绝对项
- 前端页面：`http://127.0.0.1:8021/demo-static/distill_demo.html`
- 验收输出目录：`docs/distill_workbench_real_user_flow_2026-04-28/`

## 实际执行

1. 启动本地 FastAPI 工作台服务，`distill_demo.html` 返回 200。
2. 通过前端文件输入控件上传 `.docx`，后端 `question-pack/preview` 返回 parsed。
3. 工作台识别到 13 道题，内容包含题号、题干、答案、解析、出处、正确率、易错项。
4. 执行真实搜索查询，围绕题包出处关键词寻找来源候选。
5. 对外部模型 API 做一次受控调用，key 只读环境变量；调用失败，返回 HTTP 429。
6. 将真实题包解析、搜索候选、业务字段草案、材料字段草案、Gate blocked 证据塞入前端工作台。
7. 逐步测试业务按钮和下拉：
   - 解析题包并生成报告
   - 来源阶段切换
   - 来源下拉：采用 / 待定 / 不采用
   - 字段草案阶段切换
   - 蒸馏结果验收阶段切换
   - 生成蒸馏验收报告
   - 重跑
   - 待定
   - 确认
8. 最后点击确认后，Gate 仍然保持 blocked，不允许正式写回。

## 来源候选

本轮为了模拟真实用户判断，把来源展示成材料片段，而不是题目问句：

- `ihep.cas.cn`：中国散裂中子源加速器材料，关联 #13314342，业务选择“采用”。
- `news.cn`：抗生素耐药性死亡负担预测材料，关联 #13314353，业务选择“待定”。
- `manual-source-needed`：鸡蛋角质层材料，当前无可审查来源正文，业务选择“不采用”。

这些选择只表示“后续是否继续审查”，不确认原文、不抓正文、不入库。

## 模型调用

- 使用环境变量中的 API key。
- 不在命令、日志、报告中写 key。
- 调用目标：基于题包预览生成业务字段、材料字段、样题和 Gate 判断。
- 结果：失败，HTTP 429 Too Many Requests。
- 处理方式：本轮前端验收继续使用可解释 fallback 样题，不把模型侧视为通过。

## 截图

- 材料准备报告：`docs/distill_workbench_real_user_flow_2026-04-28/01_material_prep_report_utf8.png`
- 来源网站确认：`docs/distill_workbench_real_user_flow_2026-04-28/02_source_review_initial_utf8.png`
- 来源选择已暂存：`docs/distill_workbench_real_user_flow_2026-04-28/03_source_review_decisions_utf8.png`
- 来源材料明细：`docs/distill_workbench_real_user_flow_2026-04-28/03b_source_material_detail_utf8.png`
- 字段草案确认：`docs/distill_workbench_real_user_flow_2026-04-28/04_field_draft_review_utf8.png`
- 蒸馏结果验收报告：`docs/distill_workbench_real_user_flow_2026-04-28/05_distill_acceptance_report_utf8.png`
- 点击重跑：`docs/distill_workbench_real_user_flow_2026-04-28/06_rerun_button_checked_utf8.png`
- 点击待定：`docs/distill_workbench_real_user_flow_2026-04-28/07_defer_button_checked_utf8.png`
- 点击确认后 Gate 拒绝落位：`docs/distill_workbench_real_user_flow_2026-04-28/08_confirm_gate_rejected_utf8.png`

## 发现的问题

1. 前端业务流可以走通，但“真实模型返回”没有拿到，原因是 provider 返回 429。
2. 业务按钮足够简化，但当前业务流仍依赖技术 JSON 注入 evidence；后续如果要完全给业务同学用，需要把 evidence 生成接到后端按钮，不应让业务粘 JSON。
3. 来源页面目前能展示材料片段和关联题目，业务能单独选择采用 / 不采用 / 待定，这一版符合用户刚才要求。
4. 工作台没有执行 source verification，也没有打开网页正文；这符合边界，但意味着 Gate 拒绝落位是合理结果。

## 回归测试

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`：98 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell`：15 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench`：10 tests OK
- `$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`：4 tests OK

## 边界声明

本轮没有：

- 正式写回；
- card_specs 写回；
- material_card 写回；
- runtime / prompt / validator / generation 主链修改；
- source verification；
- passage_service ingest；
- material promotion；
- 新增 promotion target。

## 下一步建议

先换一个可用模型 endpoint 或恢复 API 额度，再重跑同一份前端验收脚本。只要模型侧能返回，下一轮就能验证“业务上传题包 -> 模型产出初版字段 / 样题 -> 业务点击重跑 / 确认 -> Gate 拒绝或送审”的完整真实路径。
