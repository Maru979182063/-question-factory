# 项目架构与服务流程图

本文档是 `docs/system_architecture.md` 的视觉版补充，用来快速理解当前真实系统，而不是描述未来理想架构。

阅读口径：

- `prompt_skeleton_service` 是出题、评审、交付侧主服务。
- `passage_service` 是文章、材料、题卡上下文侧主服务。
- `card_specs/` 与 `configs/` 是规则控制面，但当前仍有部分规则散落在 service、validator 和前端补丁里。
- `/demo` 是一个单页工作台，不是多页面后台。

## 1. 系统总览

```mermaid
flowchart LR
    classDef ui fill:#E8F3FF,stroke:#4B83C4,color:#1F3552
    classDef service fill:#F4F0FF,stroke:#7B61C8,color:#2E245B
    classDef config fill:#FFF4D6,stroke:#C5922C,color:#4A3510
    classDef data fill:#EAF8EF,stroke:#3D9A5D,color:#173B23
    classDef external fill:#FDECEC,stroke:#C75C5C,color:#4B2020
    classDef ops fill:#F3F4F6,stroke:#737986,color:#252A31

    User["用户 / 教研运营"]:::external

    subgraph Frontend["前端工作台"]
        Demo["/demo<br/>builder / loading / result"]:::ui
        Static["demo_static<br/>index.html + app_v2.js + zh_patch"]:::ui
    end

    subgraph PromptService["prompt_skeleton_service"]
        PromptAPI["FastAPI routers<br/>questions / review / prompt / distill"]:::service
        Orchestrator["编排层<br/>decode / slot resolve / prompt build"]:::service
        Generation["题目生成服务<br/>LLM generate / repair / validate"]:::service
        Review["评审与交付<br/>review action / delivery export"]:::service
        Queue["异步生成队列<br/>generate-async"]:::service
        QDB[(本地 SQLite<br/>batches / items / versions / actions)]:::data
    end

    subgraph PassageService["passage_service"]
        PassageAPI["FastAPI routes<br/>articles / materials / materials_v2"]:::service
        Ingest["文章导入 / 抓取"]:::service
        Segment["切片与候选材料生成"]:::service
        Tagging["通用标签 / 题族标签 / 治理"]:::service
        V2Index["V2 材料索引与检索"]:::service
        PDB[(passage_service.db<br/>articles / spans / materials / reviews)]:::data
    end

    subgraph RulePlane["规则与配置控制面"]
        TypeConfigs["configs/types/*.yaml<br/>题型 slot / pattern"]:::config
        RuntimeConfigs["question_runtime*.yaml<br/>provider / routing / materials"]:::config
        PromptTemplates["prompt_templates.yaml<br/>prompt assets"]:::config
        CardSpecs["card_specs/<br/>question / material / business cards"]:::config
    end

    subgraph External["外部依赖"]
        WebSources["外部文章源"]:::external
        LLM["LLM Provider<br/>生成 / 修复 / judge / 材料轻修"]:::external
    end

    subgraph Ops["运维与观察"]
        Scripts["scripts/<br/>试跑 / 回填 / 报表 / demo 启动"]:::ops
        Reports["reports / logs<br/>运行报告与日志"]:::ops
    end

    User --> Demo
    Demo --> Static
    Demo --> PromptAPI
    PromptAPI --> Orchestrator
    PromptAPI --> Queue
    Orchestrator --> Generation
    Generation --> Review
    Generation --> QDB
    Review --> QDB

    Generation -->|取材 POST /materials/v2/search| PassageAPI
    PassageAPI --> V2Index
    V2Index --> PDB

    WebSources --> Ingest
    Ingest --> Segment
    Segment --> Tagging
    Tagging --> V2Index
    Ingest --> PDB
    Segment --> PDB
    Tagging --> PDB

    TypeConfigs --> Orchestrator
    RuntimeConfigs --> Orchestrator
    RuntimeConfigs --> Generation
    PromptTemplates --> Generation
    CardSpecs --> V2Index
    CardSpecs --> Generation
    LLM --> Generation
    LLM --> Tagging
    Scripts --> PromptAPI
    Scripts --> PassageAPI
    PromptAPI --> Reports
    PassageAPI --> Reports
```

## 2. 分层职责图

```mermaid
flowchart TB
    classDef layer fill:#F8FAFC,stroke:#64748B,color:#111827
    classDef rule fill:#FFF7ED,stroke:#EA580C,color:#431407
    classDef service fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef data fill:#ECFDF5,stroke:#059669,color:#064E3B

    UI["前端工作台层<br/>采集输入、展示结果、触发 review action"]:::layer
    API["接口路由层<br/>questions / review / materials / diagnostics"]:::layer
    Orchestration["编排层<br/>请求解码、slot resolve、pattern 选择、prompt build"]:::service
    Domain["领域服务层<br/>材料加工、取材、生成、校验、评审、导出"]:::service
    Rule["规则控制面<br/>题型配置、运行时配置、题卡、材料卡、业务卡"]:::rule
    Infra["基础设施层<br/>SQLite、SQLAlchemy、HTTP fetcher、LLM gateway、插件"]:::data

    UI --> API
    API --> Orchestration
    Orchestration --> Domain
    Rule --> Orchestration
    Rule --> Domain
    Domain --> Infra
    Infra --> Domain

    UI -.->|当前仍存在少量 UI 映射与补丁逻辑| Rule
    Domain -.->|当前仍存在部分内置规则| Rule
```

## 3. 出题生成主流程

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户 / demo
    participant Q as questions router
    participant O as PromptOrchestratorService
    participant G as QuestionGenerationService
    participant MB as MaterialBridgeV2Service
    participant P as passage_service /materials/v2/search
    participant V2 as MaterialPipelineV2Service
    participant L as LLM Provider
    participant VAL as QuestionValidator + Evaluation
    participant DB as QuestionRepository SQLite

    U->>Q: POST /api/v1/questions/generate
    Q->>O: 初始化编排服务
    Q->>G: generate(request)
    G->>G: prepare_request / decode target
    G->>G: resolve question card binding
    G->>G: source question analysis
    G->>MB: select_materials(...)
    MB->>P: POST /materials/v2/search
    P->>V2: search(payload)
    V2-->>P: question_ready_context candidates
    P-->>MB: 材料候选 + warnings
    MB-->>G: MaterialSelectionResult[]
    G->>L: 生成结构化题目
    L-->>G: raw model output
    G->>VAL: 结构校验 / 难度校验 / LLM judge
    VAL-->>G: validation_result / evaluation_result
    alt 校验通过
        G->>DB: save_version + save_item
        G->>DB: save_batch
        G-->>Q: QuestionGenerationBatchResponse
        Q-->>U: batch + items + warnings
    else 校验失败但可修复
        G->>L: targeted repair
        L-->>G: repaired output
        G->>VAL: 复验
    else 多次失败
        G-->>Q: 422 with rejected_attempts
        Q-->>U: 失败原因与记录路径
    end
```

## 4. 材料服务入库与 V2 检索流程

```mermaid
flowchart TB
    classDef input fill:#FDECEC,stroke:#C75C5C,color:#4B2020
    classDef step fill:#E8F3FF,stroke:#3B82F6,color:#102A43
    classDef gate fill:#FFF4D6,stroke:#C5922C,color:#4A3510
    classDef data fill:#EAF8EF,stroke:#3D9A5D,color:#173B23
    classDef output fill:#F4F0FF,stroke:#7B61C8,color:#2E245B

    Source["外部文章源 / 手工入库"]:::input
    Crawl["CrawlService<br/>发现 URL、抓取正文"]:::step
    Ingest["IngestService<br/>清洗、去重、写入 article"]:::step
    Segment["SegmentService<br/>段落句子切分、候选 span"]:::step
    V2Build["MaterialPipelineV2<br/>LLM 候选 + 规则候选 + planner gate"]:::step
    Fallback["V1 fallback<br/>paragraph / sentence / story fragment"]:::gate
    Tag["TagService<br/>完整性门、通用标签、题族路由"]:::step
    Governance["MaterialGovernance<br/>标签治理、合并、灰度/稳定"]:::gate
    Pool["PoolService<br/>写入 material pool"]:::data
    ReviewInit["ReviewService<br/>auto_tagged / review_pending"]:::data
    Sync["SyncService<br/>同步可检索材料"]:::data
    Precompute["MaterialV2IndexService<br/>预计算 v2_index_payload"]:::data
    Search["/materials/v2/search<br/>按题卡、业务卡、结构约束检索"]:::output
    QRC["question_ready_context<br/>resolved_slots / prompt_extras / validator_contract"]:::output

    Source --> Crawl --> Ingest --> Segment --> V2Build
    V2Build -->|有合格候选| Tag
    V2Build -->|无合格候选| Fallback --> Tag
    Tag --> Governance --> Pool
    Pool --> ReviewInit --> Sync --> Precompute
    Precompute --> Search --> QRC
```

## 5. 评审与改题动作流程

```mermaid
flowchart TD
    classDef ui fill:#E8F3FF,stroke:#4B83C4,color:#1F3552
    classDef service fill:#F4F0FF,stroke:#7B61C8,color:#2E245B
    classDef guard fill:#FFF4D6,stroke:#C5922C,color:#4A3510
    classDef data fill:#EAF8EF,stroke:#3D9A5D,color:#173B23
    classDef terminal fill:#F3F4F6,stroke:#737986,color:#252A31

    Result["resultScreen<br/>结果卡 + 控制面板"]:::ui
    Controls["GET /questions/{item_id}/controls"]:::service
    Replacements["GET /questions/{item_id}/replacement-materials"]:::service
    Action["POST /questions/{item_id}/review-actions"]:::service
    Confirm["POST /questions/{item_id}/confirm"]:::service

    Policy["QuestionReviewService<br/>动作策略与边界审计"]:::guard
    Decision{"动作类型"}:::guard
    StateOnly["approve / confirm / discard<br/>只改状态"]:::service
    Repair["minor_edit / question_modify / text_modify / distractor_patch<br/>重走生成或定向修复"]:::service
    Manual["manual_edit<br/>受限字段手工保存"]:::service
    Audit["审计 changed_fields / truth_touched / material_boundary"]:::guard
    Version["save_version"]:::data
    Item["save_item"]:::data
    ActionLog["save_review_action"]:::data
    Export["delivery/export<br/>导出通过题目"]:::terminal

    Result --> Controls
    Result --> Replacements
    Result --> Action
    Result --> Confirm
    Action --> Policy
    Confirm --> Policy
    Policy --> Decision
    Decision --> StateOnly
    Decision --> Repair
    Decision --> Manual
    StateOnly --> Audit
    Repair --> Audit
    Manual --> Audit
    Audit --> Version
    Audit --> Item
    Audit --> ActionLog
    Item --> Export
```

## 6. 前端工作台页面流转

```mermaid
stateDiagram-v2
    [*] --> Builder

    state "Builder 输入页" as Builder
    state "Loading 状态页" as Loading
    state "Result 综合工作页" as Result

    Builder: 选择题族 / 二级类型
    Builder: 设置难度、文本方向、材料结构、数量
    Builder: 可录入参考母题并自动拆题回填

    Loading: 展示生成过程状态
    Loading: 允许返回上一页

    Result: 展示题目、答案、解析和材料信息
    Result: 加载控制项和备选材料
    Result: 执行换材、重做、手工编辑、通过、作废、导出

    Builder --> Loading: POST /api/v1/questions/generate
    Builder --> Builder: POST /api/v1/questions/source-question/parse
    Loading --> Result: 生成完成
    Loading --> Builder: 返回
    Result --> Result: GET controls / replacement-materials
    Result --> Result: POST review-actions / confirm
    Result --> Builder: 返回首页
    Result --> [*]: 导出或结束批次
```

## 7. 规则控制面如何影响运行时

```mermaid
flowchart LR
    classDef config fill:#FFF4D6,stroke:#C5922C,color:#4A3510
    classDef runtime fill:#EEF2FF,stroke:#6366F1,color:#312E81
    classDef output fill:#EAF8EF,stroke:#3D9A5D,color:#173B23
    classDef risk fill:#FDECEC,stroke:#C75C5C,color:#4B2020

    Types["configs/types/*.yaml<br/>slot schema / pattern / match_rules"]:::config
    Runtime["question_runtime*.yaml<br/>LLM 路由、材料服务、运行策略"]:::config
    Templates["prompt_templates.yaml<br/>prompt skeleton"]:::config
    Assets["question_generation_prompt_assets.yaml<br/>生成提示资产"]:::config
    Cards["card_specs/normalized<br/>question cards / material cards / signal layers"]:::config
    Business["card_specs/business_feature_slots<br/>业务特征卡"]:::config

    Decode["input_decoder / slot_resolver<br/>标准请求"]:::runtime
    Binding["question_card_binding<br/>题卡绑定"]:::runtime
    Bridge["material_bridge_v2<br/>检索参数与结构约束"]:::runtime
    V2["MaterialPipelineV2<br/>材料卡与业务卡匹配"]:::runtime
    Prompt["prompt_builder + generation_service<br/>最终生成上下文"]:::runtime
    Validator["question_validator / evaluation_service<br/>结构、难度、judge"]:::runtime
    Result["可评审题目对象<br/>item + version + review surface"]:::output

    Types --> Decode
    Runtime --> Bridge
    Runtime --> Prompt
    Templates --> Prompt
    Assets --> Prompt
    Cards --> Binding
    Cards --> V2
    Business --> V2
    Decode --> Binding --> Bridge --> V2 --> Prompt --> Validator --> Result

    UIMap["前端与 router 中仍有部分 UI 映射"]:::risk
    ServiceRules["service / validator 中仍有部分内置规则"]:::risk
    UIMap -.->|待逐步回收| Types
    ServiceRules -.->|待逐步回收| Cards
```

## 8. 文档维护建议

当下面任一事实发生变化时，应同步更新本文：

- `/demo` 的正式入口脚本或页面 screen 发生变化。
- `prompt_skeleton_service` 与 `passage_service` 的接口边界发生变化。
- `/materials/v2/search` 返回的 `question_ready_context` 字段发生变化。
- 题卡、材料卡、业务卡成为唯一规则来源，或新增新的规则控制面。
- review action 新增动作类型，或动作边界从 `QuestionReviewService` 中迁移。
