# 蒸馏工作台修稳第一刀报告（2026-04-29）

## 本轮目标

针对真实业务流验收暴露出的两个阻塞点做小范围修稳：

1. 真实模型接口可通，但返回格式不稳定，生成主链容易因为 JSON 解析失败而没有可审查题。
2. 真实来源搜索 0 候选时，业务页缺少继续推进的人工补 URL / 人工补正文入口。

本轮不做正式写回，不改 validator 大治理，不改 prompt/runtime 主配置，不新增 promotion target。

## 修改文件

- `E:/agent_repo_src/prompt_skeleton_service/app/services/text_readability.py`
- `E:/agent_repo_src/prompt_skeleton_service/app/services/llm_gateway.py`
- `E:/agent_repo_src/prompt_skeleton_service/app/services/question_generation.py`
- `E:/agent_repo_src/prompt_skeleton_service/app/demo_static/distill_demo.html`
- `E:/agent_repo_src/prompt_skeleton_service/app/demo_static/distill_demo.js`
- `E:/agent_repo_src/prompt_skeleton_service/tests/test_generation_readability.py`
- `E:/agent_repo_src/prompt_skeleton_service/tests/test_demo_shell.py`
- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/run_frontend_smoke.py`

## 修稳内容

### 1. LLM JSON 解析增强

`extract_json_object` 现在额外支持：

- JSON 被模型作为字符串包了一层，例如：`"{\"stem\":\"...\"}"`。
- 模型返回单元素数组，例如：`[{"stem":"..."}]`。

`LLMGatewayService._extract_text_output` 现在额外支持：

- provider 直接把文本放在 `text/content/result/response`。
- provider 把 JSON 放在 tool call 的 `function.arguments`。
- content list 中使用 `content` 而不是 `text`。

这些都是只读解析增强，不改变 schema、不放宽正式写回。

### 2. forced_user_material 可审查 fallback

当请求处于 `forced_user_material` 模式，并且 LLM provider / JSON 契约失败时，系统现在会构造一条带明确标记的可审查 fallback 题：

- `forced_user_material_fallback=true`
- `fallback_requires_human_review=true`
- `fallback_reason=...`

这条题仍然会经过 validator。若 validator 不通过，状态仍可能是 `auto_failed`，但前端/工作台至少能看到题目、选项、解析，用于人工判断和反馈，而不是空失败。

边界：

- 只在用户自带材料模式启用。
- 不让正式主链静默通过。
- 不绕过 validator。
- 不自动 formalize。

### 3. 搜索 0 候选时的业务兜底入口

业务向导“来源网站确认”页新增：

- 人工补充来源网址：`businessManualSourceUrl`
- 人工补充材料片段：`businessManualSourceText`

当搜索没有候选网址时，页面会提示业务可以人工补 URL 或材料片段，作为后续 `source_text_evidence` 的待审证据。

边界文案保留：

- 不确认原文。
- 不抓正文。
- 不入库。

## 真实调用复测

重启 prompt service 后，使用真实配置 endpoint 再次调用生成 API：

- 输出：`E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/real_generation_response_after_fix.json`
- HTTP 状态：200
- item 状态：`auto_failed`
- 但已生成可审查题目：
  - stem：`根据材料，下列说法最符合文意的是：`
  - metadata 中包含 `forced_user_material_fallback=true`
  - metadata 中包含 `fallback_requires_human_review=true`

解释：这次不再是“没有题可看”的空失败；系统能给出可人工审核的 fallback 题。但 validator 仍将其判为 `auto_failed`，原因包括 `main_axis_mismatch`。这属于后续题型/validator 契约问题，不在本轮硬放行。

## 前端复测

已重跑：

- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/run_frontend_smoke.py`

截图已更新，尤其是：

- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/03_source_review_stage.png`
- `E:/agent_repo_src/docs/distill_workbench_real_business_acceptance_2026-04-29/11_formalization_gate_blocked_preview.png`

## 测试结果

通过：

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`
  - 98 tests OK
- `python -m unittest prompt_skeleton_service.tests.test_generation_readability`
  - 12 tests OK
- `python -m unittest prompt_skeleton_service.tests.test_question_generation`
  - 80 tests OK
- `python -m unittest prompt_skeleton_service.tests.test_demo_shell`
  - 15 tests OK
- `python -m unittest prompt_skeleton_service.tests.test_distill_workbench prompt_skeleton_service.tests.test_word_usage_proto_mapping prompt_skeleton_service.tests.test_question_generation prompt_skeleton_service.tests.test_generation_readability`
  - 106 tests OK

备注：`test_generation_readability` 和 `test_demo_shell` 合并在同一个 Python 进程中运行时，前者测试桩会污染 `fastapi` 模块导入；分开运行均通过。这是既有测试隔离问题，不是本轮业务失败。

## 当前状态判断

比上一轮稳了：

- 模型返回格式不稳时，工作台不会只得到空失败。
- 业务来源搜索 0 候选时，有人工补 URL / 补材料片段入口。
- Gate 仍能正确 blocked，不会越权写回。

仍未完全解决：

- fallback 题只是“可审查”，不是高质量可落位题。
- `center_understanding` validator 仍可能拦截 fallback 题，这个拦截是合理的，不能为了绿灯直接放宽。
- 真实搜索 provider 对新题包 query 仍可能 0 候选，需要下一刀做 query fallback / 人工 URL evidence 产品化。

## 未做事项

- 没有正式写回。
- 没有写 `card_specs`。
- 没有正式写 `material_card`。
- 没有 passage_service ingest。
- 没有 source verification。
- 没有新增 promotion target。
- 没有调用 executor。
- 没有放宽 validator。
