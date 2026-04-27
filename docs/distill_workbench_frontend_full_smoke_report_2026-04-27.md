# 蒸馏工作台前端全量 smoke 与节点 mock 报告

日期：2026-04-27

## 1. 本轮目标

本轮做两件事：

1. 对当前蒸馏工作台前端做一轮全量 smoke；
2. 产出每个关键节点的前端页面 mock，方便后续产品化审查。

本轮不做：

- 不调用 LLM；
- 不执行真实生题；
- 不执行真实 distill trial；
- 不联网搜索；
- 不抓正文；
- 不写 material_card；
- 不写 card_specs；
- 不改 runtime / prompt / validator / generation 主链；
- 不新增 promotion target。

## 2. Browser 说明

尝试使用 Codex in-app Browser runtime 初始化浏览器，但本机 Node/browser runtime 返回系统拒绝访问。

因此本轮改用：

- FastAPI `TestClient` 检查真实路由与静态资源；
- 本地 uvicorn 检查服务可启动；
- DOM / JS 字符串 smoke 检查关键前端节点与函数；
- 独立静态 HTML/PNG 生成节点页面 mock。

这意味着：

- 路由、静态资源、关键 DOM、JS 函数、边界字段已经通过真实服务检查；
- 但没有通过 in-app browser 做真实点击截图。

## 3. 实际检查结果

前端 smoke 结果文件：

`docs/distill_workbench_frontend_full_smoke_result_2026-04-27.json`

结果：

- total: 55
- passed: 55
- failed: 0

覆盖项：

- `/demo` 可访问；
- `/demo/distill` 未授权时跳转到 `/demo`；
- access verify 后可进入 `/demo/distill`；
- `/demo-static/distill_demo.js` 可访问；
- `/demo-static/styles.css` 可访问；
- 样本集、会话、试跑、审核、补丁、候选轴确认、写回预览、来源候选人审、promotion、行为包等关键 DOM 节点存在；
- 创建 dataset/session/trial、review、patch、promote、axis confirmation、formal patch draft、writeback preview、source review decision 等关键 JS 函数存在；
- source review 六类 decision 存在；
- canonical target 选项存在；
- 前端 JS 未硬编码 `verified=true`、`verified_original_source=true`、`crawl_allowed=true`、`writeback_allowed=true` 等越权字段。

## 4. 节点 mock 产物

静态总览页面：

`docs/distill_workbench_node_mocks.html`

PNG 节点 mock：

1. `docs/distill_workbench_node_mocks/01_dataset.png`
2. `docs/distill_workbench_node_mocks/02_session.png`
3. `docs/distill_workbench_node_mocks/03_trial.png`
4. `docs/distill_workbench_node_mocks/04_review.png`
5. `docs/distill_workbench_node_mocks/05_patch.png`
6. `docs/distill_workbench_node_mocks/06_axis.png`
7. `docs/distill_workbench_node_mocks/07_writeback.png`
8. `docs/distill_workbench_node_mocks/08_source_review.png`
9. `docs/distill_workbench_node_mocks/09_promotion.png`
10. `docs/distill_workbench_node_mocks/10_behavior.png`
11. `docs/distill_workbench_node_mocks/11_difficulty.png`
12. `docs/distill_workbench_node_mocks/12_system_control.png`

这些 mock 只表达页面结构和产品状态，不接 API，不执行业务逻辑。

## 5. 节点覆盖

### 1. 样本集创建

输入真题样本、split、题型、子类、generation request。

输出：

- dataset_id

边界：

- 不调用模型；
- 不蒸馏；
- 不写题卡。

### 2. 蒸馏会话

围绕 dataset 或 baseline request 创建 session。

输出：

- session_id

边界：

- 只建立实验上下文。

### 3. 试跑

执行 trial，保留 request snapshot、fit summary、sample error。

重点：

- experimental proto route 开关必须显式开启；
- 后端仍负责拦截未知 subtype。

### 4. 人工审核

用户判断 run 是否允许 promotion。

边界：

- 未审核不能 promote；
- allow_promote 必须带 promotion targets。

### 5. 补丁登记

登记 evidence path 或 draft payload。

边界：

- patch 只是 workbench 记录；
- 不写正式配置。

### 6. 候选轴确认

从 bootstrap hypothesis 进入 proto_confirmed。

边界：

- proto_confirmed 不是 formal；
- formal_patch_draft 仍是 draft。

### 7. 写回计划预览

formal_patch_draft 生成 writeback plan 和 diff preview。

边界：

- 不写文件；
- 真正写回必须 explicit approval。

### 8. 来源候选人审

用户审查 source candidate，生成 review decisions。

边界：

- similar material 不是 original source；
- original_source_candidate 也不是 verified original source；
- 不抓正文、不入库、不生成 material_card。

### 9. 证据 promotion

把审核通过且 patch 完整的 run 打成 promotion bundle。

边界：

- bundle 是 evidence；
- 不自动写回。

### 10. 行为包

从生成结果构造 behavior packet 和 distillation diff。

边界：

- 用于复盘；
- 不自动 patch 主链。

### 11. 难度回归

展示 difficulty projection / assessment / diff / calibration 的前端占位。

边界：

- calibration patch candidate 必须经过 review；
- 不直接改 prompt 或 validator。

### 12. 系统级调试总控台

只读聚合多条子链状态和 artifact。

边界：

- 不执行链路；
- 不调用 LLM；
- 不写回。

## 6. 已运行命令

```powershell
python -m unittest prompt_skeleton_service.tests.test_demo_shell
```

结果：

- 10 tests passed

```powershell
python -m unittest prompt_skeleton_service.tests.test_distill_workbench
```

结果：

- 10 tests passed

```powershell
python -m unittest tests.test_system_debug_control_plane
```

结果：

- 4 tests passed

自定义前端 smoke：

- 55 checks passed

## 7. 当前结论

当前蒸馏工作台前端的主要节点、静态资源、access gate、关键 JS 组装函数和边界字段都能通过 smoke。

前端页面 mock 已覆盖从样本集到系统级调试总控台的 12 个节点。

下一步如果要继续产品化，建议先补：

1. 把这 12 个节点 mock 合并成真实前端导航；
2. 给系统级总控台增加只读 artifact 上传/粘贴入口；
3. 用真实浏览器环境补一轮点击级截图测试。

