# 蒸馏台业务向导分层修正报告

## 修正判断

上一版业务模式仍然像一个被业务化包装过的工程表单。真实业务流程应该是异步分层的：先看题包解析报告，再看来源网站，再看字段草案，最后看蒸馏报告和示例样题。

## 新业务流程

1. 材料准备报告
   - 上传题包；
   - 系统解析题量、文件格式、是否需要人工复核；
   - 系统判断是否已有母族 / 叶族；
   - 如果没有明确叶族名，提示业务手工命名。

2. 来源网站确认
   - 展示系统找到的候选来源网站；
   - 业务只判断网站是否有用；
   - 不确认原文，不抓正文，不入库。

3. 字段草案确认
   - 展示初始业务字段；
   - 展示初始材料字段；
   - 业务判断是否可以进入蒸馏，或是否需要改名 / 拆分 / 补材料。

4. 蒸馏结果验收
   - 展示蒸馏报告；
   - 展示 2-3 个示例样题；
   - 业务选择：确认、待定、重跑；
   - 业务填写重跑建议。

## 前端改动

- 业务模式增加四个 stage panel：
  - `businessStagePrep`
  - `businessStageSource`
  - `businessStageDraft`
  - `businessStageAcceptance`
- 增加异步 loading：`businessAsyncLoading`。
- 增加最终操作按钮：确认 / 待定 / 重跑。
- 技术 JSON 仍折叠在“查看技术详情”中。

## Mock 图

- `docs/mock_business_flow_prep_2026-04-28.png`
- `docs/mock_business_flow_source_2026-04-28.png`
- `docs/mock_business_flow_draft_2026-04-28.png`
- `docs/mock_business_flow_acceptance_2026-04-28.png`

## 边界

- 不做正式写回。
- 不确认原文。
- 不写 material_card。
- 不写 card_specs。
- 不调用 executor。
- 不改 generation / validator / prompt / runtime 主链。

## 来源确认页补充

按业务反馈，来源确认页新增：

- 每个来源卡片展示该来源命中的题目；
- 每个来源独立下拉操作：采用 / 不采用 / 待定；
- 操作只表示后续是否继续审查，不确认原文、不抓正文、不入库；
- 新 mock 图：`docs/mock_business_flow_source_with_questions_2026-04-28.png`。

## 来源卡材料展示修正

按业务反馈，来源卡主展示内容从“命中的题目问句”改为“材料片段 / 主题摘要”。

- 材料片段优先读取 `material_excerpt` / `text_excerpt` / `source_text_excerpt` / `restored_human_material` / `context_window` / `snippet`。
- 关联题目折叠到“查看关联题目”中，只作为追踪辅助。
- 每个来源仍保留独立下拉：采用 / 不采用 / 待定。
- 新 mock 图：`docs/mock_business_flow_source_material_excerpt_2026-04-28.png`。
