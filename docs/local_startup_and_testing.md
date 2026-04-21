# 本地启动与测试（local_startup_and_testing）

这份文档用于新机器启动、交接演示和回归测试。项目当前主要由两个本地服务组成：生题服务（prompt_skeleton_service）和材料服务（passage_service）。

## 目录结构速览

```text
agent/
  prompt_skeleton_service/    生题服务、Demo 工作台、评审、蒸馏、难度实验
  passage_service/            材料服务、文章处理、材料池、材料卡收路
  card_specs/                 题卡、材料卡、信号层和运行映射资产
  configs/                    运行配置
  scripts/                    启动、冒烟、压测和实验脚本
  docs/                       架构、交接、协议和实验文档
```

## 首次安装

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1
```

脚本会做这些事：

- 创建根目录 `.venv`。
- 创建 `passage_service\.venv`。
- 以 editable 模式安装两个服务。
- 在需要时复制材料服务的环境变量模板。

安装后至少需要检查这些密钥或环境变量：

```powershell
$env:GENERATION_LLM_API_KEY="你的生成模型 key"
$env:MATERIAL_LLM_API_KEY="你的材料处理模型 key"
```

如果材料服务使用 OpenAI 兼容接口，也需要按当前环境配置：

```powershell
$env:PASSAGE_OPENAI_API_KEY="你的材料服务 key"
```

## 一键启动

开发 profile：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload
```

MVP profile：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile mvp
```

默认 profile：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1
```

启动脚本会先启动材料服务，再启动生题服务，并检查 `/readyz`。

## Profile 与端口

| Profile | 生题服务端口 | 材料服务端口 | 生题环境文件 | 材料环境文件 |
| --- | ---: | ---: | --- | --- |
| default | 8000 | 8001 | `.env.demo` | `passage_service\.env` |
| mvp | 8011 | 8001 | `.env.demo` + `.env.mvp` | `passage_service\.env.mvp` |
| dev | 8111 | 8101 | `.env.demo` + `.env.dev` | `passage_service\.env.dev` |
| uat | 8011 | 8001 | 同 mvp | 同 mvp |

常用访问入口：

- 生题服务健康检查：`http://127.0.0.1:<prompt_port>/readyz`
- 材料服务健康检查：`http://127.0.0.1:<passage_port>/readyz`
- Demo 工作台：`http://127.0.0.1:<prompt_port>/demo`
- 蒸馏工作台：`http://127.0.0.1:<prompt_port>/demo/distill`

## 常见环境变量

| 变量 | 作用 |
| --- | --- |
| `GENERATION_LLM_API_KEY` | 生题服务调用生成模型所需 key |
| `MATERIAL_LLM_API_KEY` | 材料处理或材料分析所需 key |
| `PASSAGE_OPENAI_API_KEY` | 材料服务 OpenAI 兼容调用 key |
| `PASSAGE_DATABASE_URL` | 材料服务数据库地址 |
| `PASSAGE_ALLOW_NON_PRIMARY_DATABASE` | 是否允许非主数据库，用于本地/测试环境 |
| `PROMPT_SERVICE_API_TOKEN` | 生题服务 API token |
| `PROMPT_SERVICE_SECURITY_ENABLED` | 是否开启生题服务安全校验 |

## 本地测试

### 生题服务单元测试

```powershell
.\.venv\Scripts\python -m pytest .\prompt_skeleton_service\tests
```

如果只验证生成链路相关测试：

```powershell
.\.venv\Scripts\python -m pytest .\prompt_skeleton_service\tests\test_question_generation.py .\prompt_skeleton_service\tests\test_question_response_schema.py
```

如果只验证蒸馏链路：

```powershell
.\.venv\Scripts\python -m pytest .\prompt_skeleton_service\tests\test_distill_workbench.py .\prompt_skeleton_service\tests\test_distillation_runtime_service.py
```

如果只验证难度相关能力：

```powershell
.\.venv\Scripts\python -m pytest .\prompt_skeleton_service\tests\test_difficulty_assessment_service.py .\prompt_skeleton_service\tests\test_difficulty_calibration_service.py .\prompt_skeleton_service\tests\test_difficulty_projection_service.py
```

### 前端冒烟

```powershell
.\.venv\Scripts\python .\scripts\smoke_test_demo_frontend.py
```

### 材料运行冒烟

```powershell
.\.venv\Scripts\python .\scripts\passage_runtime_smoke.py
```

### 生成压测

```powershell
.\.venv\Scripts\python .\scripts\load_test_generate.py
```

### 难度实验工具

```powershell
.\.venv\Scripts\python .\scripts\difficulty_experiment_workbench.py
```

## 排障顺序

1. 先看两个服务的 `/readyz` 是否通过。
2. 再看启动脚本打印的端口和环境文件是否符合当前 profile。
3. 如果生成失败，优先检查 `GENERATION_LLM_API_KEY` 和模型调用配置。
4. 如果材料为空，优先检查材料服务端口、`PASSAGE_DATABASE_URL` 和材料库是否有可用材料。
5. 如果异步任务卡住，检查 `async_generation_tasks` 的状态、租约和错误字段。
6. 如果蒸馏或难度实验结果异常，先确认样本集和题卡叶族是否匹配。

## 交接备注

当前测试主要集中在生题服务侧，材料服务已有运行时和冒烟脚本，但测试目录本身较轻。交接时建议先跑生题服务核心测试，再用启动脚本和 Demo 工作台验证双服务联通。
