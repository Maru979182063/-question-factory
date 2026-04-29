# 蒸馏台业务模式入口修正报告

## 修正原因

上一版业务模式仍然把技术 evidence 入口包装给业务用户看，默认暴露了 `axis_confirmation`、`formal_patch_draft`、Gate evidence 等 JSON 输入。这不符合真实业务使用方式。

业务用户更适合做三类判断：

1. 当前候选网址是否有用。
2. 生成出来的题是否能用。
3. 当前是否允许进入正式化送审。

题包 JSON、runtime mapping、validator contract、readiness gate 等内容仍保留为技术详情，不作为业务默认入口。

## 本轮修改

- 将业务模式说明改为“三个判断口”。
- 将技术 JSON 输入移入“查看技术详情”折叠区。
- 新增业务默认输入：
  - 候选来源判断；
  - 生成题判断；
  - 是否允许进入正式化送审；
  - 简短业务反馈。
- 业务报告现在会输出：
  - 来源有没有用；
  - 生成题能不能用；
  - 是否允许送审；
  - 当前为什么不能落位；
  - 下一步该补来源、补质量还是继续 review。

## 边界

- 业务选择“可以进入送审”不会触发正式写回。
- 业务选择“网址有用”不会确认原文。
- 业务选择“生成题能用”不会跳过回归。
- 技术 JSON 仍只作为详情和审计，不要求业务填写。

## 测试

- `python -m unittest discover -s tests -p test_leaf_pre_distill.py`：通过，88 tests。
- `PYTHONPATH=E:\\agent_repo_src\\prompt_skeleton_service python -m unittest prompt_skeleton_service.tests.test_demo_shell`：通过，14 tests。
- `PYTHONPATH=E:\\agent_repo_src\\prompt_skeleton_service python -m unittest prompt_skeleton_service.tests.test_distill_workbench`：通过，10 tests。
- `PYTHONPATH=E:\\agent_repo_src\\prompt_skeleton_service python -m unittest prompt_skeleton_service.tests.test_word_usage_proto_mapping`：通过，4 tests。
