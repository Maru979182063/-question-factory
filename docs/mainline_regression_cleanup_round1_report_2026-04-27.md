# 主链回归清账第一刀执行报告

日期：2026-04-27

## 执行结论

本轮完成两个目标：

1. MaterialBridgeV2 测试签名清账已完成，`test_material_bridge_v2` 单测恢复通过。
2. few-shot fixture 只做审计与计划，未实现、未创建假 CSV、未改生产 loader。

本轮没有触碰 validator / sentence_order / slot_resolver 契约漂移，也没有修改新题包正式化工厂逻辑。

## 修改文件列表

- `prompt_skeleton_service/tests/test_material_bridge_v2.py`
- `docs/fewshot_fixture_isolation_audit_plan_2026-04-27.md`
- `docs/mainline_regression_cleanup_round1_report_2026-04-27.md`

## MaterialBridgeV2 测试修复内容

问题：

旧测试直接调用：

```python
MaterialBridgeV2Service._search_candidates(...)
```

但当前实现要求 keyword-only 参数：

- `shadow_child_family_ids`
- `shadow_selected_leaf_ids`

修复：

只在 `prompt_skeleton_service/tests/test_material_bridge_v2.py` 的 3 个直接调用点补显式空列表：

```python
shadow_child_family_ids=[]
shadow_selected_leaf_ids=[]
```

未修改：

- `MaterialBridgeV2Service` 实现
- shadow filtering 行为
- material bridge 业务逻辑

## test_material_bridge_v2 结果

命令：

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_material_bridge_v2
```

结果：

`Ran 13 tests ... OK`

## few-shot fixture 审计结论

已新增审计计划：

`docs/fewshot_fixture_isolation_audit_plan_2026-04-27.md`

结论：

- 当前 Round 1 few-shot 缺文件失败来自本地资产缺失。
- 配置引用位置在 `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`。
- loader 缺文件抛 `DomainError` 是生产保护，不建议改成静默降级。
- 不建议在 `reports/` 下创建随便的空 CSV。
- 推荐下一刀使用：
  - `prompt_skeleton_service/tests/fixtures/round1_fewshot/*.csv`
  - 测试专用 prompt asset config
  - patch `_CONFIG_PATH`
  - 清理 loader cache

## 推荐下一步

下一刀建议：

`few-shot fixture isolation implementation v1`

建议只覆盖：

- `prompt_skeleton_service/tests/test_prompt_builder.py`
- `prompt_skeleton_service/tests/test_question_generation.py`
- `prompt_skeleton_service/tests/test_review_workbench.py`

先把 CSV 缺失噪声清掉，再重新观察剩余 failures。不要把 validator/schema/difficulty 契约漂移混进下一刀。

## 验收测试

### MaterialBridgeV2

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_material_bridge_v2
```

结果：`Ran 13 tests ... OK`

### 新工厂 scoped tests

```powershell
python -m unittest discover -s tests -p test_leaf_pre_distill.py
```

结果：`Ran 82 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

结果：`Ran 11 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

结果：`Ran 10 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping
```

结果：`Ran 4 tests ... OK`

## 明确未做

- 没有改生产 `MaterialBridgeV2` 逻辑。
- 没有改 shadow filtering 行为。
- 没有改 `question_generation_prompt_assets.py` 的缺文件保护。
- 没有创建空 CSV 糊测试。
- 没有改 prompt builder 业务逻辑。
- 没有改 generation 主链。
- 没有改 review workbench 状态机。
- 没有改 validator。
- 没有碰 sentence_order / slot_resolver 契约漂移。
- 没有改新题包正式化工厂相关逻辑。

