# Few-shot Fixture Isolation 审计与计划

日期：2026-04-27

## 结论

当前多条 prompt builder / question generation / review workbench 测试失败，是因为 Round 1 few-shot CSV 资产在本地缺失，而不是新题包正式化工厂引入的逻辑回归。

本轮只做审计，不实现 fixture。下一刀建议优先做“测试专用 prompt asset config + tests/fixtures 最小 CSV”，避免污染真实 `reports/` 和生产配置。

## 1. 哪些测试依赖 few-shot CSV

直接依赖或触发 Round 1 few-shot 加载的测试包括：

- `prompt_skeleton_service/tests/test_prompt_builder.py`
  - `test_round1_sentence_fill_fewshot_is_selected_from_candidate_pack`
  - `test_round1_sentence_fill_missing_opening_coverage_does_not_force_irrelevant_asset`
  - `test_round1_center_understanding_adds_boundary_guard_lines`

- `prompt_skeleton_service/tests/test_question_generation.py`
  - 使用 `use_fewshot=True` 的 generation 流程会触发 prompt builder 和 few-shot loader。
  - `_build_round1_fewshot_sections` 的局部测试不依赖 CSV，但端到端生成测试会依赖。

- `prompt_skeleton_service/tests/test_review_workbench.py`
  - 多个 smoke test 先通过 generation endpoint 创建题目与版本，因此会间接触发 few-shot loader。

## 2. 当前配置在哪里引用这些文件

配置文件：

`prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`

引用位置：

```yaml
question_generation:
  round1_fewshot_assets:
    enabled: true
    packs:
      sentence_fill:
        csv_path: "../../reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv"
      center_understanding:
        csv_path: "../../reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv"
      sentence_order:
        csv_path: "../../reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv"
```

当前本地缺失：

- `reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv`
- `reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`
- `reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv`

## 3. loader 缺文件报错是否是生产保护

是。loader 位于：

`prompt_skeleton_service/app/services/question_generation_prompt_assets.py`

当 pack 配置启用但 `csv_path` 不存在时，它显式抛出 `DomainError`：

```python
raise DomainError(
    "Round 1 few-shot pack file does not exist.",
    status_code=500,
    details={"config_path": str(_CONFIG_PATH), "family": family, "csv_path": str(csv_path)},
)
```

这个行为像生产保护：配置声明启用 few-shot pack，但资产不存在时不应静默降级，否则生成链会在缺关键 few-shot 约束时继续运行，质量问题会被掩盖。

## 4. 为什么不建议改生产 loader 静默降级

不建议把缺文件改成返回空列表，原因：

- 会让生产配置错误被静默吞掉。
- 会导致 prompt builder 在缺少 Round 1 few-shot 资产时仍继续生成。
- 会让测试“绿”但真实生题质量下降，尤其是 sentence_fill / center_understanding / sentence_order 的结构型 few-shot。
- 会削弱 readiness gate 后续对 prompt asset 完整性的判断。

如果需要降级，也应该只在测试配置中显式关闭或替换路径，而不是改生产 loader 语义。

## 5. 方案 A：补 `tests/fixtures` 下最小 CSV fixture

做法：

- 在 `prompt_skeleton_service/tests/fixtures/round1_fewshot/` 下放测试 CSV：
  - `round1_fewshot_sentence_fill_candidates.csv`
  - `round1_fewshot_center_understanding_candidates.csv`
  - `round1_fewshot_sentence_order_candidates.csv`
- 测试中构造临时 `question_generation_prompt_assets.yaml`，把 `csv_path` 指向 fixtures。

根据 loader `_row_to_fewshot_example`，CSV 至少需要以下通用字段：

- `sample_id`
- `question_card_id`
- `coverage_tag`
- `fewshot_use_reason`

family 特定字段：

sentence_fill:

- `blank_position`
- `function_type`
- `logic_relation`

center_understanding:

- `main_axis_source`
- `argument_structure`

sentence_order:

- `candidate_type`
- `opening_anchor_type`
- `closing_anchor_type`

优点：

- fixture 小而可控。
- 不污染真实 `reports/`。
- 能保留生产 loader 的缺文件保护。

缺点：

- 需要为 prompt builder / generation / review workbench 测试接入临时配置路径。
- 如果测试里有细粒度 few-shot 内容断言，fixture 需要精心匹配。

## 6. 方案 B：测试中注入测试专用 prompt asset config

做法：

- 每个相关 TestCase 在 `setUp` 中创建临时 `question_generation_prompt_assets.yaml`。
- patch `app.services.question_generation_prompt_assets._CONFIG_PATH` 指向临时配置。
- 清理缓存：
  - `load_question_generation_prompt_assets.cache_clear()`
  - `load_round1_fewshot_assets.cache_clear()`
- 配置里的 CSV 路径指向临时 fixture。

优点：

- 测试环境隔离最干净。
- 不需要修改生产配置。
- 可以按测试需要启用/关闭 packs。

缺点：

- 改动测试 setup 较多。
- review workbench 走 FastAPI app 时，要确保 patch 在 app/service 实例初始化前生效。

## 7. 推荐方案

推荐组合方案：

**方案 A + 方案 B**

即：

1. 在 `prompt_skeleton_service/tests/fixtures/round1_fewshot/` 新增最小 CSV fixture。
2. 在相关测试 setup 中注入测试专用 prompt asset config，指向 fixture。
3. 不修改生产 `question_generation_prompt_assets.yaml`。
4. 不修改生产 loader 缺文件保护。

理由：

- fixture 提供稳定样本。
- 测试专用 config 避免污染真实 `reports/`。
- loader 的生产保护保持不变。

## 8. 对各测试链影响

### prompt_builder

影响：

- 可恢复 Round 1 few-shot example 选择测试。
- 可明确测试 sentence_fill 缺 opening coverage 时不强塞 middle asset。

风险：

- fixture 内容若不匹配断言，会出现 few-shot slot 断言失败。

### question_generation

影响：

- 端到端 generation 不再因为 CSV 缺失直接 500。
- 后续失败会暴露真实 generation / validator / prompt 问题。

风险：

- 生成结果可能因 fixture 内容影响 prompt，需保持结构-only、短小、稳定。

### review_workbench

影响：

- 可先消掉 generation endpoint 因 CSV 缺失造成的大量 error。
- 剩余 review 状态机问题会更清晰。

风险：

- 如果 review workbench 初始化 service 早于 patch，需要调整测试初始化顺序。

## 9. 下一刀实现应改哪些测试 setup

建议下一刀改：

- `prompt_skeleton_service/tests/test_prompt_builder.py`
- `prompt_skeleton_service/tests/test_question_generation.py`
- `prompt_skeleton_service/tests/test_review_workbench.py`

新增辅助工具：

- `prompt_skeleton_service/tests/fixtures/round1_fewshot/*.csv`
- 可选：`prompt_skeleton_service/tests/helpers/fewshot_assets.py`

helper 可提供：

- 创建临时 prompt asset config
- 写入最小 CSV fixture
- patch `_CONFIG_PATH`
- 清理 loader lru cache

## 10. 如何避免污染真实 reports/ 和生产配置

原则：

- 不在 `reports/` 下创建测试 CSV。
- 不修改 `prompt_skeleton_service/configs/question_generation_prompt_assets.yaml`。
- 不修改 `question_generation_prompt_assets.py` 的缺文件保护。
- 测试配置放在 `TemporaryDirectory` 或 `tests/fixtures`。
- 每个测试结束后清理 patch 和 cache。

## 下一步建议

下一刀可以执行：

`few-shot fixture isolation implementation v1`

验收方式：

1. 单跑 `test_prompt_builder`，确认 Round 1 few-shot 相关测试恢复。
2. 单跑 `test_question_generation`，确认不再出现 CSV missing 的 DomainError。
3. 单跑 `test_review_workbench`，确认 generation 入口不再因 few-shot 资产缺失失败。
4. 再看剩余失败，避免把 validator/schema 契约漂移混进本刀。

