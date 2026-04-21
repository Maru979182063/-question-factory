# 项目交接索引（project_handoff_index）

这份索引用来把已有架构图、流程图和新补充的文字文档串起来。阅读目标是：先知道项目在做什么，再知道怎么跑，最后知道数据和资产沉淀在哪里。

## 5 分钟速览

1. 项目总览：`docs/project_portfolio_overview.md`
2. 总架构图：`docs/figma/layered_overall_architecture.md`
3. 核心功能清单：`docs/core_feature_catalog.md`
4. 本地启动与测试：`docs/local_startup_and_testing.md`
5. 数据与表结构图：`docs/data_schema_overview.md`

## 30 分钟交接阅读顺序

### 1. 先理解总闭环

- `docs/project_portfolio_overview.md`
- `docs/figma/layered_overall_architecture.md`

需要掌握的关键词：

- 材料服务
- 生题服务
- 母族、子族、叶族
- 评审与版本
- 蒸馏回流
- 难度实验

### 2. 再理解对外功能

- `docs/core_feature_catalog.md`
- `docs/figma/external_feature_flow_catalog.md`
- `docs/figma/four_service_flowcharts.md`

重点看这些功能：

- 题目生成
- 异步生成
- 评审与修改
- 交付导出
- 材料库维护
- 材料 V2 与材料卡收路
- 蒸馏工作台
- 难度实验
- 配置诊断与观测

### 3. 然后理解题卡体系

- `docs/figma/card_family_consumption_architecture.md`
- `docs/card_driven_protocol.md`
- `docs/three_family_card_protocol_audit.md`

这里不要把“题卡文件名”误认为业务主线。业务主线是：

```text
母族 -> 子族 -> 叶族
```

题卡、材料卡、信号层、功能槽位和运行映射是承载这条主线的资产。

### 4. 接着理解工程运行

- `docs/local_startup_and_testing.md`
- `docs/frontend_structure.md`
- `docs/environment_profiles.md`

优先跑通：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload
```

### 5. 最后看数据和证据链

- `docs/data_schema_overview.md`
- `docs/distill_workbench_service.md`
- `docs/difficulty_experiment_workbench_tooling.md`

优先理解这些表：

- `question_items`
- `question_item_versions`
- `async_generation_tasks`
- `material_spans`
- `feedback_records`
- `distill_runs`
- `distill_run_patches`
- `distill_promotions`

## 求职展示讲法

可以按这个顺序讲：

1. **问题**：阅读理解题目生产不是简单生成文本，而是要保证题型、材料、答案、解析、难度和可复查。
2. **建模**：我用“母族 -> 子族 -> 叶族”组织题型，把材料卡、题卡、信号层作为资产承载。
3. **架构**：系统拆成生题服务和材料服务，生题服务负责生成、评审、蒸馏和实验，材料服务负责材料生产和材料卡收路。
4. **闭环**：题目生成后进入评审和版本链，失败样例进入蒸馏台，难度问题进入实验工具，最后回流到题卡、提示词、材料适配和运行规则。
5. **工程亮点**：本地可启动、可测试，有异步任务、运行事件、配置诊断、数据表证据链和多套工作台。

## 已有图与文档地图

| 类型 | 文档 |
| --- | --- |
| 总架构 | `docs/figma/layered_overall_architecture.md` |
| 四个服务流程 | `docs/figma/four_service_flowcharts.md` |
| 题卡消费路径 | `docs/figma/card_family_consumption_architecture.md` |
| 对外功能流程 | `docs/figma/external_feature_flow_catalog.md` |
| 项目总览 | `docs/project_portfolio_overview.md` |
| 核心功能 | `docs/core_feature_catalog.md` |
| 本地启动测试 | `docs/local_startup_and_testing.md` |
| 数据表结构 | `docs/data_schema_overview.md` |

## 后续可以继续补的内容

- 面试版 1 页项目介绍。
- README 首页改造。
- API 清单与关键路由说明。
- 一组可截图的 Demo 演示路径。
- 常见问题和排障案例。
