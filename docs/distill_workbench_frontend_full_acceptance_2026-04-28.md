# 蒸馏工作台前端全链路验收报告

日期：2026-04-28  
入口：http://127.0.0.1:8017/demo-static/distill_demo.html  
测试方式：Playwright 驱动真实浏览器页面，所有关键步骤均从前端表单点击触发后端 `/api/v1/distill/*` 接口。

## 结论

本轮前端工作台可以完成“新叶族 / 新题包 proto 送审链路”的完整制作：

1. 创建样本集。
2. 创建新题卡蒸馏会话。
3. 运行 `word_usage_content_word` experimental proto trial。
4. 人工审核并允许沉淀。
5. 在 Axis Decision UI 中生成 `axis_confirmation` 和 `formal_patch_draft`。
6. 一键创建 6 类规范目标补丁：
   - `business_feature_card`
   - `prompt_assets`
   - `signal_layer`
   - `validator_contract`
   - `material_mapping`
   - `runtime_mapping`
7. 生成 promotion bundle。
8. 来源候选审查 UI 能生成 `source_candidate_review_decisions.json`。
9. 用户自然语言反馈 UI 能生成 `agent_review_feedback_input.json`。

这说明用户可以通过前端完成新题包“送审包 / 草案沉淀包”制作。它仍然不是正式写回：没有写 `card_specs`，没有写正式 `material_card`，没有改 runtime/prompt/validator/generation 主链。

## 真实前端运行结果

### Unicode 中文输入复验

为排除 PowerShell 管道对中文测试数据的污染，我使用 Unicode 转义重新跑了一次核心链路。结果：

- run_id：`37e8745b-5d16-47de-8ff2-a25abf7ec4e4`
- run status：`completed`
- review_count：`1`
- patch_count：`6`
- promotion_count：`1`
- review summary：`中文原型试跑通过，仅允许草案沉淀。`
- promotion summary：`中文新题包前端验收沉淀包：草案不写回。`
- fit band：`high`
- generated/truth match：
  - question_type_match：`true`
  - business_subtype_match：`true`
  - answer_match：`true`

### 首轮完整 UI 截图

截图目录：`docs/distill_workbench_frontend_acceptance_2026-04-28/`

- `01_initial_workbench.png`
- `02_dataset_created.png`
- `03_session_created.png`
- `04_trial_completed.png`
- `05_review_submitted.png`
- `06_axis_decisions_loaded.png`
- `07_formal_patch_draft_preview.png`
- `08_canonical_patches_created.png`
- `09_promotion_bundle_created.png`
- `10_source_review_decisions_generated.png`
- `11_agent_feedback_input_generated.png`
- `12_unicode_full_flow_completed.png`

### API 覆盖

前端实际触发并返回 200 的接口包括：

- `GET /api/v1/distill/datasets`
- `POST /api/v1/distill/datasets`
- `GET /api/v1/distill/sessions`
- `POST /api/v1/distill/sessions`
- `POST /api/v1/distill/sessions/{session_id}/trials`
- `GET /api/v1/distill/runs/{run_id}`
- `POST /api/v1/distill/runs/{run_id}/review`
- `POST /api/v1/distill/runs/{run_id}/patches`
- `POST /api/v1/distill/runs/{run_id}/promote`

## API / LLM 说明

本轮“前端工作台完整制作”主要调用的是本地后端 distill API。`word_usage_content_word` 当前走的是后端 experimental proto route，不需要外部 LLM 才能完成 trial。

环境中存在 `OPENAI_API_KEY`，但本轮前端工作台链路没有需要调用外部 LLM 的页面动作；因此没有把 key 写入命令、日志或报告。后续如果要把 gold reconstruction / material protocol draft 的 LLM 模式也集成到前端，需要新增受控 UI 入口和独立验收。

## 边界确认

本轮没有做：

- 正式写回；
- `card_specs` 写回；
- `material_card` formalization；
- `runtime_mapping` 写回；
- `prompt_assets` 正式写回；
- `validator_contract` 正式写回；
- generation / validator / prompt / runtime 主链修改；
- passage_service ingest；
- material promotion；
- 新增正式 promotion target；
- source verification；
- material library write。

## 发现的问题

1. 浏览器控制台出现 1 个 404 资源请求，未影响主流程。初步判断像静态附属资源或 favicon 类缺失，需要后续单独确认。
2. 用户如果把“完整制作”理解为正式写入 `card_specs` 并启用生产 runtime，本轮还不能保证。当前前端能完成的是送审包、补丁草案和沉淀包；正式落位仍需要 readiness gate、explicit approval、writeback plan/diff、guarded executor。
3. 材料侧 full seed acceptance 目前仍是 blocked/review_needed：source/gold alignment 与 material quality regression 证据还不足，不能进入 material_card formalization。

## 回归测试

已通过：

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
# Ran 88 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
# Ran 11 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
# Ran 10 tests - OK

$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
# Ran 4 tests - OK
```

## 最终判断

可以交给用户前端操作的能力：新题包 proto 试跑、人工审核、axis decision、formal patch draft 预览、规范目标补丁生成、promotion bundle、source review decision、agent feedback input。

不能宣称已经完成的能力：正式题卡写回、正式 material_card 落位、source verification、材料入库、生产 runtime 激活。

下一步最小补刀：把 `new_leaf_formalization_packet / runtime_activation_plan / readiness_gate` 的运行入口做成前端可操作区块。这样用户完成 promotion bundle 后，可以继续在同一个工作台里看到“为什么能/不能写回”的 gate 结论，而不是切回命令行。
