# Round 1 Few-shot 资产安装报告

日期：2026-04-27

## 结论

已从用户提供的压缩包中只抽取 3 个当前配置需要的 Round 1 few-shot CSV 到 `reports/`。

未展开压缩包其他内容。

## 来源

压缩包：

`F:/WeChat Files/wxid_318qq4k2hhsh21/FileStorage/File/2026-04/agent_private_sensitive_reports_20260422_012019.zip`

抽取条目：

- `reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv`
- `reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`
- `reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv`

## 落位文件

- `reports/round1_fewshot_sentence_fill_candidates_2026-04-12.csv`
- `reports/round1_fewshot_center_understanding_candidates_2026-04-12.csv`
- `reports/round1_fewshot_sentence_order_candidates_2026-04-12.csv`

## 文件检查

| 文件 | 行数 | 状态 |
|---|---:|---|
| `round1_fewshot_sentence_fill_candidates_2026-04-12.csv` | 12 | schema 匹配 |
| `round1_fewshot_center_understanding_candidates_2026-04-12.csv` | 12 | schema 匹配 |
| `round1_fewshot_sentence_order_candidates_2026-04-12.csv` | 10 | schema 匹配 |

## 额外测试清账

同时修复了 `prompt_skeleton_service/tests/test_question_generation.py` 中一个硬编码本机路径：

原路径：

`C:/Users/Maru/Documents/agent/prompt_skeleton_service/app/services/question_generation.py`

改为：

`Path(__file__).resolve().parents[1] / "app" / "services" / "question_generation.py"`

这是测试路径修复，不涉及业务逻辑。

## 验收

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_prompt_builder
```

结果：`Ran 6 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_question_generation
```

结果：`Ran 80 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest prompt_skeleton_service.tests.test_review_workbench
```

结果：`Ran 41 tests ... OK`

```powershell
$env:PYTHONPATH='E:\agent_repo_src\prompt_skeleton_service'; python -m unittest discover -s prompt_skeleton_service\tests
```

剩余失败已收敛为：

- `test_question_validator`
- `test_sentence_order_schema`
- `test_slot_resolver`

不再有 few-shot CSV missing error。

## 边界

- 没有修改 few-shot loader。
- 没有修改生产 prompt asset 配置。
- 没有改 generation 主链。
- 没有改 review workbench 状态机。
- 没有碰 validator / sentence_order / slot_resolver 契约漂移。

