# Agent Material Generation Platform

这是当前主项目的根 README，用来让你或换机器后的协作者快速恢复开发环境、启动材料生成链路，并知道哪些内容应该提交、哪些必须留在本机。

## 项目定位

本仓库服务于公考/事业单位言语理解题目的材料池、题型骨架、真题蒸馏、难度实验和本地演示工作台。当前主线不是“学习机”实验，而是围绕最新影子材料库和题目生成闭环继续推进。

核心服务有两个：

- `passage_service`: 材料摄取、切分、标签、影子材料池、材料搜索和材料治理。
- `prompt_skeleton_service`: 题型配置、prompt 组装、题目生成、真题蒸馏、难度控制和演示页面。

## 目录速览

```text
.
├── passage_service/                 # 材料服务，独立虚拟环境 passage_service/.venv
├── prompt_skeleton_service/          # 生题/演示服务，使用仓库根 .venv
├── desktop_bundle_20260420/          # 已提交的真题/材料包，换机器可直接拉取
├── configs/difficulty_experiments/   # 难度实验配置
├── docs/                             # 架构、交接、实验和启动文档
├── scripts/                          # 一键启动、实验、审计和报告脚本
└── test/                             # 材料卡/真题点位测试资产
```

当前保留的影子库配置是：

```text
passage_service/app/config/shadow_material_pilot_round2.yaml
```

旧版 `shadow_material_pilot*.yaml`、根目录 `tmp_*`、`load_test_*.json` 和临时抽取目录已经清掉，并写入 `.gitignore`，后续不要再把这类运行产物提交上来。

## 环境依赖

基础要求：

- Python 3.11+
- PowerShell 5+ 或 PowerShell 7+
- Git
- 可选：ngrok，用于外网临时访问本地 demo

Python 依赖以两个服务的 `pyproject.toml` 为准：

- `prompt_skeleton_service/pyproject.toml`: FastAPI、Uvicorn、Pydantic v2、PyYAML、httpx。
- `passage_service/pyproject.toml`: FastAPI、Uvicorn、SQLAlchemy、Pydantic v2、pydantic-settings、PyYAML、httpx、BeautifulSoup4、APScheduler。

一键初始化会创建两个虚拟环境并以 editable 模式安装服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1
```

如果要重建虚拟环境：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1 -ForceRecreate
```

## 环境变量

本机真实环境文件不要提交。仓库会忽略 `.env.demo`、`.env.dev`、`.env.mvp`、`passage_service/.env` 等文件，只保留示例文件。

推荐从示例创建本机配置：

```powershell
Copy-Item .\.env.demo.example .\.env.demo
Copy-Item .\passage_service\.env.example .\passage_service\.env
```

最少需要配置：

```powershell
$env:GENERATION_LLM_API_KEY="your_key"
$env:MATERIAL_LLM_API_KEY="your_key"
```

常用可选项：

```powershell
$env:GENERATION_LLM_BASE_URL="https://api.openai.com/v1"
$env:MATERIAL_LLM_BASE_URL="https://api.openai.com/v1"
$env:PASSAGE_OPENAI_API_KEY="your_key"
$env:PASSAGE_OPENAI_BASE_URL="https://api.openai.com/v1"
```

如果要开启 demo API token：

```powershell
$env:PROMPT_SERVICE_SECURITY_ENABLED="true"
$env:PROMPT_SERVICE_API_TOKEN="replace_with_local_token"
```

## 本地启动

开发环境一键拉起材料服务和生题服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload
```

开发端口：

- Prompt/demo UI: `http://127.0.0.1:8111/demo`
- 真题蒸馏 UI: `http://127.0.0.1:8111/demo/distill`
- 用户材料 UI: `http://127.0.0.1:8111/demo/user-material`
- Prompt diagnostics: `http://127.0.0.1:8111/api/v1/diagnostics/dependencies`
- Passage docs: `http://127.0.0.1:8101/docs`
- Passage diagnostics: `http://127.0.0.1:8101/api/v1/diagnostics/runtime`

如果要同时起 ngrok：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload -StartNgrok
```

如果遇到 ngrok `ERR_NGROK_6030`，通常是同一个固定域名已有其他隧道占用。先关掉旧 ngrok 进程，或换一个临时域名重新拉起。

## 常用工作流

材料影子库：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_shadow_material_pilot.py
```

真题蒸馏调试：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_distillation_debug_packet.py
```

难度实验工作台：

```powershell
.\.venv\Scripts\python.exe .\scripts\difficulty_experiment_workbench.py --help
```

前端 smoke：

```powershell
.\.venv\Scripts\python.exe .\scripts\smoke_test_demo_frontend.py
```

## 测试

Prompt 服务测试：

```powershell
.\.venv\Scripts\python.exe -m pytest .\prompt_skeleton_service\tests
```

Passage 服务测试：

```powershell
.\passage_service\.venv\Scripts\python.exe -m pytest .\passage_service\tests
```

快速语法检查示例：

```powershell
.\.venv\Scripts\python.exe -m py_compile .\scripts\run_shadow_material_pilot.py
```

## 提交卫生

可以提交：

- 源码、配置模板、prompt 资产、架构/交接文档。
- `desktop_bundle_20260420/` 里已经确认要保留的真题/材料包。
- `configs/difficulty_experiments/`、`docs/`、`scripts/` 里服务主线需要的实验和报告资产。

不要提交：

- `.env*` 真实环境文件、API key、ngrok token。
- `logs/`、`reports/`、`tmp/`、`tmp_*`、`load_test_*.json`。
- 本机数据库、虚拟环境、缓存、导出文件、学习机临时目录。

换机器继续开发的标准路径：

```powershell
git clone https://github.com/Maru979182063/-.git agent
cd agent
git checkout codex/dev-local
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-demo.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start-demo.ps1 -Profile dev -Reload
```
