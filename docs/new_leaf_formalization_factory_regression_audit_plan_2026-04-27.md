# 新题包正式化工厂回归审计与修复计划

日期：2026-04-27

## 审计结论

新题包正式化工厂 4+1 刀自身相关测试已通过：

- `tests/test_leaf_pre_distill.py`
- `prompt_skeleton_service.tests.test_demo_shell`
- `prompt_skeleton_service.tests.test_distill_workbench`
- `prompt_skeleton_service.tests.test_word_usage_proto_mapping`

更大范围的 `prompt_skeleton_service/tests` 全量 discover 未通过，失败主要来自既有主链回归债务，而不是本轮正式化工厂新增工具直接引入。

本轮不建议直接修主链。应先拆成三类清账：

1. 测试签名漂移
2. 本地资产缺失
3. 题型契约 / validator / difficulty 规则漂移

## 实际测试结果

已通过：

```powershell
python -m unittest discover -s tests
```

结果：`Ran 91 tests ... OK`

未全绿：

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest discover -s prompt_skeleton_service\tests
```

结果：`Ran 312 tests`，`failures=32, errors=35`

## 失败类别

### 1. MaterialBridgeV2 测试签名漂移

现象：

`MaterialBridgeV2Service._search_candidates()` 当前实现要求：

- `shadow_child_family_ids`
- `shadow_selected_leaf_ids`

但部分旧单测直接调用 `_search_candidates(...)` 时没有传这两个 keyword-only 参数。

代表失败：

- `test_search_candidates_filters_review_pending_remote_items`
- `test_search_candidates_keeps_preferred_business_cards_as_soft_hint`
- `test_search_candidates_retries_remote_search_after_timeout`

定位：

- 实现：`prompt_skeleton_service/app/services/material_bridge_v2.py`
- 测试：`prompt_skeleton_service/tests/test_material_bridge_v2.py`

判断：

这是测试接口与实现签名漂移。外部公开调用路径已经通过上层函数传入默认空列表，失败集中在直接测私有函数的旧单测。

修复计划：

- 优先修改测试调用，显式传：
  - `shadow_child_family_ids=[]`
  - `shadow_selected_leaf_ids=[]`
- 不建议为了旧测试给 `_search_candidates` 改回宽松签名，除非确认有外部调用依赖。

影响：

- 低风险。
- 只改测试不会影响生产逻辑。
- 如果改实现默认值，可能掩盖 shadow filtering 缺参问题，让 future adapter 边界变松。

### 2. Round 1 few-shot CSV 资产缺失

现象：

多条 prompt builder / question generation / review workbench 测试失败于：

`Round 1 few-shot pack file does not exist.`

缺失文件：

- `E:\agent_repo_src\reports\round1_fewshot_sentence_fill_candidates_2026-04-12.csv`
- 同配置还引用：
  - `round1_fewshot_center_understanding_candidates_2026-04-12.csv`
  - `round1_fewshot_sentence_order_candidates_2026-04-12.csv`

定位：

- 配置：`prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`
- loader：`prompt_skeleton_service/app/services/question_generation_prompt_assets.py`

判断：

这是运行测试所需本地资产缺失，不是正式化工厂引入的代码回归。

可选修复方案：

方案 A：补齐测试 fixture CSV

- 优点：最贴近当前配置预期。
- 缺点：需要确认 CSV schema 和样例内容；随便造空文件可能让 few-shot 相关断言失真。
- 影响：中等。会影响 prompt builder 选择 few-shot 的测试结果。

方案 B：测试中注入临时 prompt asset 配置

- 优点：不污染真实 `reports/` 资产；测试可控。
- 缺点：需要调整多处测试 setup。
- 影响：低到中。更像测试隔离修复。

方案 C：loader 对缺失 CSV 降级为空

- 优点：能快速减少报错。
- 缺点：风险高。当前 DomainError 可能是刻意保护，防止生成链在缺 few-shot 资产时静默劣化。
- 影响：高。不建议作为第一刀。

推荐：

先走方案 B 或 A。不要直接让生产 loader 静默 fallback。

### 3. Validator / sentence_order / slot_resolver 契约漂移

现象：

大量失败集中在：

- `test_question_validator`
- `test_sentence_order_schema`
- `test_slot_resolver`

代表失败：

- `test_center_understanding_*`
- `test_sentence_fill_*`
- `test_sentence_order_*`
- `test_difficulty_projection_does_not_add_target_bias`

判断：

这类不是单纯缺文件。它们反映当前 validator、normalized question card、runtime slots、difficulty projection 与测试预期之间已经发生漂移。

这组不能一口气机械改测试，否则会把真实行为变化抹掉。

修复计划：

1. 先跑单文件：
   - `test_question_validator`
   - `test_sentence_order_schema`
   - `test_slot_resolver`
2. 每个文件按“测试期望是否仍是当前产品契约”分类：
   - 测试过期：改测试
   - 实现漂移：修实现
   - 配置漂移：修卡 / runtime 配置
3. 每修一类，跑旧三大题型回归，确认没有污染。

影响：

- 高风险。
- 可能影响生题质量、旧题型 validator 判定、难度控制、材料桥输出、正式 trial。
- 不应和新叶族正式化工厂同一刀混修。

### 4. Review workbench 失败

现象：

多条 `test_review_workbench` error/failure。

推断：

部分来自 generation endpoint 失败，即 few-shot CSV 缺失导致 review workbench 无法生成初始题目和版本。

但其中也可能混有 review action / material patch / status transition 的独立漂移。

修复计划：

1. 先解决 few-shot 资产缺失。
2. 重新单跑 `test_review_workbench`。
3. 剩余失败再判断是否为 review 状态机问题。

影响：

- 中到高。
- review workbench 是用户人工验收链路，不能为了绿测试放宽校验。

## 与本轮新题包正式化工厂的关系

本轮新工厂新增的是离线 evidence / draft / gate 链：

- 用户反馈归一化
- 新叶族正式化送审包
- runtime activation plan
- readiness gate
- 前端反馈输入 JSON

这些模块不调用：

- `question_generation`
- `question_validator`
- `MaterialBridgeV2._search_candidates`
- prompt builder few-shot loader
- review workbench generation endpoint

因此当前全量失败不能直接归因于本轮 4+1 刀。

## 推荐修复顺序

### 第一刀：测试签名清账

范围：

- `prompt_skeleton_service/tests/test_material_bridge_v2.py`

动作：

- 给直接调用 `_search_candidates` 的旧测试补：
  - `shadow_child_family_ids=[]`
  - `shadow_selected_leaf_ids=[]`

预期：

- 消除 3 个 MaterialBridgeV2 TypeError。

风险：

- 低。

### 第二刀：few-shot 测试资产隔离

范围：

- `prompt_skeleton_service/tests/test_prompt_builder.py`
- `prompt_skeleton_service/tests/test_question_generation.py`
- `prompt_skeleton_service/tests/test_review_workbench.py`

动作：

- 建立测试专用 few-shot fixture 或测试专用 prompt asset config。
- 不修改生产 loader 的缺文件保护。

预期：

- 消除 prompt builder / generation / review workbench 中由缺 CSV 引发的大量 error。

风险：

- 中。
- 如果 fixture 内容不符合测试预期，可能暴露新的 few-shot 选择断言失败。

### 第三刀：旧题型契约专项审计

范围：

- `test_question_validator`
- `test_sentence_order_schema`
- `test_slot_resolver`

动作：

- 逐条判断是测试过期、实现漂移，还是配置漂移。
- 每类单独改。

预期：

- 收敛 validator / schema / difficulty 投影失败。

风险：

- 高。
- 可能影响旧三大题型正式行为，不应和前两刀混在一起。

## 不建议的做法

- 不建议直接把 few-shot loader 改成缺文件静默通过。
- 不建议一次性更新所有 validator 测试期望。
- 不建议为了全量绿而放宽 validator 主逻辑。
- 不建议把 MaterialBridgeV2 新参数改成任意缺省后不测 shadow 行为。

## 对新题型正式化目标的影响

短期：

- 不阻塞正式化工厂的 evidence / packet / plan / gate 能力。
- 会阻塞“全仓库绿灯”或“旧主链可放心发布”的判断。

中期：

- runtime activation plan 最后要落到真实 generation / validator / material bridge。
- 如果这些旧主链回归不清账，新题包即使送审包完整，也无法安全进入正式写回。

长期：

- 新题型正式化工厂必须依赖旧题型主链稳定性。
- readiness gate 后续应接入这些回归结果，旧题型不绿时不得进入 executor-ready。

## 最小下一步建议

只补一刀的话，先做：

`MaterialBridgeV2 测试签名清账 + few-shot fixture 审计`

理由：

- 它们是明确、低到中风险、可快速把 error 数降下来的问题。
- 先消掉环境/测试接口类噪声，才能看清 validator/schema 真正剩余失败。

