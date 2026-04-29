const state = {
  datasets: [],
  sessions: [],
  selectedDatasetId: "",
  selectedSessionId: "",
  selectedRunId: "",
  currentRun: null,
  behaviorPacket: null,
  behaviorRequest: null,
  bootstrapDiscovery: null,
  axisConfirmation: null,
  formalPatchDraft: null,
  formalWritebackPlan: null,
  formalWritebackDiff: "",
  formalizationGatePreview: null,
  businessSummary: null,
  businessSummaryMarkdown: "",
  businessView: null,
  businessViewMarkdown: "",
  businessViewPage: "scope",
  businessViewAsyncTimer: null,
  leafIssueRows: [],
  leafDistillTasks: [],
  historyDistillStep: "issues",
  selectedLeafTaskId: "",
  businessModePreview: null,
  sourceCandidates: [],
  sourceCandidateReviews: {},
};

const WORKBENCH_DRAFT_STORAGE_KEY = "distill_demo_workbench_draft_v1";
const WORKBENCH_DEFAULT_LAYER = "business_mode";
const WORKBENCH_VISIBLE_LAYERS = new Set(["business_mode", "status_history"]);

const WORKBENCH_PANEL_LAYER_SELECTORS = {
  business_mode: ["businessModeForm"],
  status_history: ["businessSummaryForm", "businessReadableView", "leafIssueSelectionTable", "leafDistillTaskQueue", "leafDistillAcceptancePanel"],
};

const SOURCE_REVIEW_DECISIONS = [
  "keep_as_original_source_candidate",
  "keep_as_similar_material_seed",
  "keep_as_domain_seed",
  "reject_question_bank",
  "reject_irrelevant",
  "defer",
];

const SOURCE_KEEP_DECISIONS = new Set([
  "keep_as_original_source_candidate",
  "keep_as_similar_material_seed",
  "keep_as_domain_seed",
]);

const SOURCE_RISKY_KEEP_BLOCKERS = new Set(["question_bank_like", "exam_training_like"]);

const SOURCE_RISK_FILTERS = [
  { value: "all", label: "全部风险" },
  { value: "low", label: "低风险" },
  { value: "unknown", label: "未知风险" },
  { value: "risky", label: "题库页 / 培训站风险" },
];

const SOURCE_USE_BY_DECISION = {
  keep_as_original_source_candidate: "original_source_candidate",
  keep_as_similar_material_seed: "similar_material",
  keep_as_domain_seed: "domain_seed",
  reject_question_bank: "reject",
  reject_irrelevant: "reject",
  defer: "defer",
};

const SOURCE_DECISION_LABELS = {
  keep_as_original_source_candidate: "保留为原文候选",
  keep_as_similar_material_seed: "保留为相似材料种子",
  keep_as_domain_seed: "保留为域名种子",
  reject_question_bank: "拒绝：题库或培训站",
  reject_irrelevant: "拒绝：无关来源",
  defer: "暂缓判断",
};

const SOURCE_USE_LABELS = {
  original_source_candidate: "原文候选",
  similar_material: "相似材料",
  domain_seed: "域名种子",
  reject: "拒绝",
  defer: "暂缓",
};

const SOURCE_PRIORITY_LABELS = {
  high: "高",
  medium: "中",
  low: "低",
};

const SOURCE_RISK_LABELS = {
  low: "低风险",
  medium: "中风险",
  unknown: "未知风险",
  question_bank_like: "疑似题库页",
  exam_training_like: "疑似培训站",
  blocked: "已阻断",
};

const MOCK_SOURCE_CANDIDATE_ROWS = [
  {
    sample_id: "word_usage_mock_001",
    query: "二氧化碳浓度 植物生长 光合作用 研究",
    query_type: "keyword_combo",
    title: "二氧化碳浓度升高对植物生长影响的研究进展",
    url: "https://www.example.edu.cn/research/co2-plant-growth",
    domain: "example.edu.cn",
    snippet: "文章讨论二氧化碳浓度变化对植物光合作用、生长速率和生态适应的影响，可作为相似材料种子。",
    source_risk: "low",
    candidate_status: "candidate",
    candidate_score: 0.74,
    verification_status: "unverified",
    verified: false,
  },
  {
    sample_id: "word_usage_mock_002",
    query: "城市更新 公共空间 社区治理 评论",
    query_type: "keyword_combo",
    title: "让城市更新更有温度",
    url: "https://www.example-news.cn/comment/city-renewal-public-space",
    domain: "example-news.cn",
    snippet: "评论文章围绕城市更新、公共空间和社区治理展开，可用于同主题材料补库，但尚未确认原文。",
    source_risk: "unknown",
    candidate_status: "weak_candidate",
    candidate_score: 0.46,
    verification_status: "unverified",
    verified: false,
  },
  {
    sample_id: "word_usage_mock_003",
    query: "语境义 实词理解 公务员考试",
    query_type: "keyword_combo",
    title: "2024国考行测言语理解实词题答案解析",
    url: "https://www.exam-training.example/tiku/word-usage-answer",
    domain: "exam-training.example",
    snippet: "页面包含公务员考试、行测、答案解析、正确答案等训练站话术，默认不应作为 source seed。",
    source_risk: "exam_training_like",
    candidate_status: "question_bank_like",
    candidate_score: 0.12,
    verification_status: "unverified",
    verified: false,
  },
];

const AXIS_CONFIRM_ACTIONS = [
  "keep",
  "drop",
  "rename",
  "split",
  "merge",
  "promote_to_proto_field",
  "map_to_seed_marker",
  "map_to_prompt_guard",
  "map_to_material_mapping",
  "map_to_validator_candidate",
  "map_to_distractor_taxonomy",
  "downgrade_to_note",
];

const AXIS_DRAFT_TARGETS = [
  "business_feature_card",
  "prompt_assets",
  "signal_layer",
  "validator_contract",
  "material_mapping",
  "runtime_mapping",
];

const AXIS_ACTION_LABELS = {
  keep: "保留",
  drop: "丢弃",
  rename: "改名",
  split: "拆分",
  merge: "合并",
  promote_to_proto_field: "提升为原型字段",
  map_to_seed_marker: "映射为种子标记",
  map_to_prompt_guard: "映射为提示保护",
  map_to_material_mapping: "映射为材料映射",
  map_to_validator_candidate: "映射为校验候选",
  map_to_distractor_taxonomy: "映射为干扰项分类",
  downgrade_to_note: "降级为备注",
};

const AXIS_TARGET_LABELS = {
  business_feature_card: "业务特征卡",
  prompt_assets: "提示资产",
  signal_layer: "信号层",
  validator_contract: "校验契约",
  material_mapping: "材料映射",
  runtime_mapping: "运行映射",
};

const AXIS_SOURCE_TYPE_LABELS = {
  candidate_axis: "候选轴",
  distractor_taxonomy: "干扰项分类",
};

const AXIS_CONFIRMING_ACTIONS = new Set([
  "keep",
  "rename",
  "split",
  "merge",
  "promote_to_proto_field",
  "map_to_seed_marker",
  "map_to_prompt_guard",
  "map_to_material_mapping",
  "map_to_validator_candidate",
  "map_to_distractor_taxonomy",
]);

const WRITEBACK_TARGET_FILES = {
  business_feature_card: "card_specs/business_feature_slots/examples/{proto_family}_{proto_child_family}.proto.yaml",
  signal_layer: "card_specs/normalized/signal_layers/{proto_family}_signal_layer.proto.yaml",
  material_mapping: "card_specs/normalized/runtime_mappings/distill_material_card_id_mapping.yaml",
  runtime_mapping: "card_specs/normalized/runtime_mappings/distill_family_hierarchy_mapping.yaml",
  prompt_assets: "prompt_skeleton_service/configs/prompt_templates.yaml",
  validator_contract: "card_specs/validator_contracts/proto/{proto_family}_{proto_child_family}.validator.yaml",
};

const SHARED_WRITEBACK_TARGETS = new Set(["material_mapping", "runtime_mapping", "prompt_assets"]);

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function parseJsonField(value, fieldName, fallback = undefined) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return fallback;
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${fieldName} 不是合法 JSON: ${error.message}`);
  }
}

function assignWorkbenchPanelLayers() {
  const layerById = {};
  Object.entries(WORKBENCH_PANEL_LAYER_SELECTORS).forEach(([layer, ids]) => {
    ids.forEach((id) => {
      layerById[id] = layer;
    });
  });
  document.querySelectorAll(".distill-panel").forEach((panel) => {
    if (panel.dataset.workbenchLayer) return;
    const matchedId = Object.keys(layerById).find((id) => panel.querySelector(`#${id}`));
    panel.dataset.workbenchLayer = matchedId ? layerById[matchedId] : "internal_tools";
  });
}

function setWorkbenchLayer(layer) {
  const targetLayer = WORKBENCH_VISIBLE_LAYERS.has(layer) ? layer : WORKBENCH_DEFAULT_LAYER;
  state.activeWorkbenchLayer = targetLayer;
  document.body.dataset.workbenchLayer = targetLayer;
  document.querySelectorAll(".distill-panel").forEach((panel) => {
    panel.classList.toggle("is-layer-hidden", panel.dataset.workbenchLayer !== targetLayer);
  });
  document.querySelectorAll(".workbench-layer-btn").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.workbenchLayerTarget === targetLayer);
  });
  updateWorkbenchDraftStatus();
}

function collectWorkbenchDraft() {
  const fields = {};
  document.querySelectorAll("input[id], textarea[id], select[id]").forEach((node) => {
    if (node.type === "file") return;
    fields[node.id] = node.type === "checkbox" ? Boolean(node.checked) : node.value;
  });
  return {
    draft_version: "v1",
    saved_at: new Date().toISOString(),
    active_layer: state.activeWorkbenchLayer || WORKBENCH_DEFAULT_LAYER,
    selected_ids: {
      dataset_id: state.selectedDatasetId || "",
      session_id: state.selectedSessionId || "",
      run_id: state.selectedRunId || "",
    },
    fields,
  };
}

function saveWorkbenchDraft() {
  const draft = collectWorkbenchDraft();
  localStorage.setItem(WORKBENCH_DRAFT_STORAGE_KEY, JSON.stringify(draft));
  updateWorkbenchDraftStatus(draft);
  setPageStatus("已暂存当前工作台状态。暂存只保存在本机浏览器，不会写正式配置。", "info");
}

function loadStoredWorkbenchDraft() {
  try {
    const raw = localStorage.getItem(WORKBENCH_DRAFT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function restoreWorkbenchDraft(options = {}) {
  const draft = loadStoredWorkbenchDraft();
  if (!draft?.fields) {
    if (!options.silent) setPageStatus("没有可恢复的暂存状态。", "error");
    return;
  }
  Object.entries(draft.fields).forEach(([id, value]) => {
    const node = $(id);
    if (!node) return;
    if (node.type === "checkbox") {
      node.checked = Boolean(value);
    } else {
      node.value = value ?? "";
    }
  });
  setWorkbenchLayer(draft.active_layer || WORKBENCH_DEFAULT_LAYER);
  updateWorkbenchDraftStatus(draft);
  if (!options.silent) setPageStatus("已恢复暂存状态。请按需刷新列表或继续当前工位。", "info");
}

function clearWorkbenchDraft() {
  localStorage.removeItem(WORKBENCH_DRAFT_STORAGE_KEY);
  updateWorkbenchDraftStatus(null);
  setPageStatus("已清空本机暂存。", "info");
}

function updateWorkbenchDraftStatus(draft = loadStoredWorkbenchDraft()) {
  const node = $("workbenchDraftStatus");
  if (!node) return;
  if (!draft?.saved_at) {
    node.textContent = "未暂存";
    return;
  }
  const activeLayer = state.activeWorkbenchLayer || draft.active_layer || WORKBENCH_DEFAULT_LAYER;
  const layerLabel = activeLayer === "status_history" ? "历史记录调整蒸馏" : "新题卡蒸馏";
  node.textContent = `已暂存：${formatTime(draft.saved_at)} / 当前视角：${layerLabel}`;
}

function exitWorkbench() {
  saveWorkbenchDraft();
  window.location.href = "/demo";
}

function withExperimentalProtoRoute(request, enabled) {
  if (!enabled || !request || typeof request !== "object" || Array.isArray(request)) {
    return request;
  }
  return {
    ...request,
    extra_constraints: {
      ...(request.extra_constraints && typeof request.extra_constraints === "object" && !Array.isArray(request.extra_constraints)
        ? request.extra_constraints
        : {}),
      experimental_proto_route: true,
    },
  };
}

function withExperimentalProtoRouteSamples(samples, enabled) {
  if (!enabled || !Array.isArray(samples)) {
    return samples;
  }
  return samples.map((sample) => {
    if (!sample || typeof sample !== "object" || Array.isArray(sample)) {
      return sample;
    }
    return {
      ...sample,
      generation_request: withExperimentalProtoRoute(sample.generation_request, true),
    };
  });
}

function axisSourceRows(discovery) {
  if (!discovery || typeof discovery !== "object") {
    return [];
  }
  const axes = Array.isArray(discovery.candidate_axes)
    ? discovery.candidate_axes.map((item) => ({
        source_type: "candidate_axis",
        source_id: item.axis,
        label: item.axis,
        description: item.description,
        status: item.status,
        support_estimate: item.support_estimate,
        risk: item.risk,
        evidence_examples: item.evidence_examples || [],
      }))
    : [];
  const taxonomy = Array.isArray(discovery.distractor_taxonomy)
    ? discovery.distractor_taxonomy.map((item) => ({
        source_type: "distractor_taxonomy",
        source_id: item.mode,
        label: item.mode,
        description: item.description,
        status: item.status,
        support_estimate: "",
        risk: "",
        evidence_examples: item.evidence_examples || [],
      }))
    : [];
  return axes.concat(taxonomy).filter((item) => item.source_id);
}

function defaultAxisAction(row) {
  if (row.source_type === "distractor_taxonomy") {
    return "map_to_distractor_taxonomy";
  }
  if (row.source_id === "option_elimination_mode") {
    return "downgrade_to_note";
  }
  return "promote_to_proto_field";
}

function defaultAxisTarget(action, sourceType) {
  if (action === "map_to_prompt_guard") return "prompt_assets";
  if (action === "map_to_material_mapping") return "material_mapping";
  if (action === "map_to_validator_candidate") return "validator_contract";
  if (action === "map_to_seed_marker" || action === "map_to_distractor_taxonomy" || sourceType === "distractor_taxonomy") {
    return "signal_layer";
  }
  if (action === "drop" || action === "downgrade_to_note") return "business_feature_card";
  return "business_feature_card";
}

function renderAxisDecisionRows(discovery) {
  const root = $("axisDecisionList");
  const rows = axisSourceRows(discovery);
  if (!rows.length) {
    root.innerHTML = `<div class="distill-empty">还没有载入候选轴。请粘贴启动发现文件后点击“载入候选轴”。</div>`;
    return;
  }
  root.innerHTML = rows
    .map((row, index) => {
      const action = defaultAxisAction(row);
      const target = defaultAxisTarget(action, row.source_type);
      return `
        <div class="axis-decision-row" data-axis-index="${index}">
          <div>
            <div class="axis-decision-title">${escapeHtml(row.label)}</div>
            <div class="distill-help">${escapeHtml(AXIS_SOURCE_TYPE_LABELS[row.source_type] || row.source_type)} / 支持度 ${escapeHtml(row.support_estimate || "-")} / 状态 ${escapeHtml(row.status || "-")}</div>
            <div class="distill-help">${escapeHtml(row.risk || row.description || "")}</div>
          </div>
          <label class="distill-field">
            <span>处理动作</span>
            <select class="axis-action">
              ${AXIS_CONFIRM_ACTIONS.map((item) => `<option value="${escapeHtml(item)}"${item === action ? " selected" : ""}>${escapeHtml(AXIS_ACTION_LABELS[item] || item)}</option>`).join("")}
            </select>
          </label>
          <label class="distill-field">
            <span>目标层</span>
            <select class="axis-target">
              ${AXIS_DRAFT_TARGETS.map((item) => `<option value="${escapeHtml(item)}"${item === target ? " selected" : ""}>${escapeHtml(AXIS_TARGET_LABELS[item] || item)}</option>`).join("")}
            </select>
          </label>
          <label class="distill-field">
            <span>确认名称</span>
            <input class="axis-name" type="text" value="${escapeHtml(row.source_id)}" />
          </label>
          <textarea class="axis-rationale" placeholder="人工确认理由">${escapeHtml(row.description || row.risk || "")}</textarea>
        </div>
      `;
    })
    .join("");

  root.querySelectorAll(".axis-action").forEach((node) => {
    node.addEventListener("change", () => {
      const row = node.closest(".axis-decision-row");
      const source = rows[Number(row?.getAttribute("data-axis-index") || 0)] || {};
      const target = row?.querySelector(".axis-target");
      if (target) {
        target.value = defaultAxisTarget(node.value, source.source_type);
      }
    });
  });
}

function parseSourceCandidateJsonl(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`来源候选结果第 ${index + 1} 行不是合法 JSON：${error.message}`);
      }
    });
}

function sourceRiskValue(candidate) {
  return String(candidate?.source_risk || candidate?.candidate_status || "unknown");
}

function sourceRiskLabel(value) {
  return SOURCE_RISK_LABELS[value] || value || "未知风险";
}

function isRiskySourceCandidate(candidate) {
  const risk = sourceRiskValue(candidate);
  return SOURCE_RISKY_KEEP_BLOCKERS.has(risk) || risk === "blocked" || candidate?.candidate_status === "blocked";
}

function sourceUseForDecision(decision) {
  return SOURCE_USE_BY_DECISION[decision] || "defer";
}

function defaultSourceDecision(candidate) {
  return isRiskySourceCandidate(candidate) ? "reject_question_bank" : "defer";
}

function sourceReviewStateFor(index, candidate) {
  const key = String(index);
  const existing = state.sourceCandidateReviews[key] || {};
  const decision = existing.decision || defaultSourceDecision(candidate);
  return {
    decision,
    source_use: existing.source_use || sourceUseForDecision(decision),
    crawl_priority: existing.crawl_priority || "medium",
    rationale: existing.rationale || "",
    review_notes: existing.review_notes || "",
    human_opened_url: Boolean(existing.human_opened_url),
    allow_risky_seed: Boolean(existing.allow_risky_seed),
  };
}

function saveSourceReviewEdits() {
  document.querySelectorAll(".source-review-card").forEach((card) => {
    const index = String(card.getAttribute("data-source-index") || "");
    if (!index) return;
    state.sourceCandidateReviews[index] = {
      decision: card.querySelector(".source-review-decision")?.value || "defer",
      source_use: card.querySelector(".source-review-source-use")?.value || "defer",
      crawl_priority: card.querySelector(".source-review-crawl-priority")?.value || "medium",
      rationale: card.querySelector(".source-review-rationale")?.value.trim() || "",
      review_notes: card.querySelector(".source-review-notes")?.value.trim() || "",
      human_opened_url: Boolean(card.querySelector(".source-review-opened")?.checked),
      allow_risky_seed: Boolean(card.querySelector(".source-review-risky-allow")?.checked),
    };
  });
}

function sourceCandidateMatchesFilter(candidate, filter) {
  const risk = sourceRiskValue(candidate);
  if (!filter || filter === "all") return true;
  if (filter === "risky") return isRiskySourceCandidate(candidate);
  if (filter === "unknown") return risk === "unknown" || !risk;
  return risk === filter;
}

function renderSourceCandidateReviewList() {
  const root = $("sourceCandidateReviewList");
  if (!root) return;
  const filter = $("sourceRiskFilter")?.value || "all";
  const visible = state.sourceCandidates
    .map((candidate, index) => ({ candidate, index }))
    .filter(({ candidate }) => sourceCandidateMatchesFilter(candidate, filter));
  if (!state.sourceCandidates.length) {
    root.innerHTML = `<div class="distill-empty">请粘贴来源候选结果，再点击“载入候选来源”。</div>`;
    return;
  }
  if (!visible.length) {
    root.innerHTML = `<div class="distill-empty">当前风险筛选下没有候选来源。</div>`;
    return;
  }
  root.innerHTML = visible
    .map(({ candidate, index }) => {
      const draft = sourceReviewStateFor(index, candidate);
      const risk = sourceRiskValue(candidate);
      const risky = isRiskySourceCandidate(candidate);
      const title = candidate.title || candidate.url || "未命名候选来源";
      const candidateScore = candidate.candidate_score ?? "-";
      return `
        <div class="source-review-card${risky ? " is-risky" : ""}" data-source-index="${index}">
          <div>
            <div class="source-review-title">${escapeHtml(title)}</div>
            <a class="source-review-url" href="${escapeHtml(candidate.url || "#")}" target="_blank" rel="noreferrer">${escapeHtml(candidate.url || "缺少链接")}</a>
            <div class="source-review-grid">
              <div><strong>样本编号</strong><br />${escapeHtml(candidate.sample_id || "-")}</div>
              <div><strong>域名</strong><br />${escapeHtml(candidate.domain || "-")}</div>
              <div><strong>搜索语句</strong><br />${escapeHtml(candidate.query || "-")}</div>
              <div><strong>候选分数</strong><br />${escapeHtml(candidateScore)}</div>
              <div><strong>候选状态</strong><br />${escapeHtml(candidate.candidate_status || "-")}</div>
              <div><strong>验证状态</strong><br />${escapeHtml(candidate.verification_status || "未验证")} / 已验证=${escapeHtml(candidate.verified === true ? "是" : "否")}</div>
            </div>
            <div class="source-risk-pill${risky ? " is-risky" : ""}">${escapeHtml(sourceRiskLabel(risk))}</div>
            <p class="distill-help">${escapeHtml(candidate.snippet || "")}</p>
            ${risky ? `<div class="source-review-warning">该候选疑似题库页或培训站。若仍要保留，必须勾选“允许风险种子”并填写明确理由。</div>` : ""}
          </div>
          <div>
            <div class="source-review-grid">
              <label class="distill-field">
                <span>审查决策</span>
                <select class="source-review-decision">
                  ${SOURCE_REVIEW_DECISIONS.map((item) => `<option value="${escapeHtml(item)}"${item === draft.decision ? " selected" : ""}>${escapeHtml(SOURCE_DECISION_LABELS[item] || item)}</option>`).join("")}
                </select>
              </label>
              <label class="distill-field">
                <span>来源用途</span>
                <select class="source-review-source-use">
                  ${["original_source_candidate", "similar_material", "domain_seed", "reject", "defer"].map((item) => `<option value="${escapeHtml(item)}"${item === draft.source_use ? " selected" : ""}>${escapeHtml(SOURCE_USE_LABELS[item] || item)}</option>`).join("")}
                </select>
              </label>
              <label class="distill-field">
                <span>后续抓取优先级</span>
                <select class="source-review-crawl-priority">
                  ${["high", "medium", "low"].map((item) => `<option value="${escapeHtml(item)}"${item === draft.crawl_priority ? " selected" : ""}>${escapeHtml(SOURCE_PRIORITY_LABELS[item] || item)}</option>`).join("")}
                </select>
              </label>
              <label class="distill-check">
                <input class="source-review-opened" type="checkbox"${draft.human_opened_url ? " checked" : ""} />
                <span>人工已打开链接</span>
              </label>
            </div>
            <label class="distill-field">
              <span>审查理由</span>
              <textarea class="source-review-rationale" placeholder="保留类决策必须填写理由">${escapeHtml(draft.rationale)}</textarea>
            </label>
            <label class="distill-field">
              <span>审查备注</span>
              <textarea class="source-review-notes" placeholder="可选备注">${escapeHtml(draft.review_notes)}</textarea>
            </label>
            ${risky ? `
              <label class="distill-check">
                <input class="source-review-risky-allow" type="checkbox"${draft.allow_risky_seed ? " checked" : ""} />
                <span>允许风险种子</span>
              </label>
            ` : `<input class="source-review-risky-allow" type="checkbox" hidden />`}
          </div>
        </div>
      `;
    })
    .join("");

  root.querySelectorAll(".source-review-decision").forEach((node) => {
    node.addEventListener("change", () => {
      const card = node.closest(".source-review-card");
      const sourceUse = card?.querySelector(".source-review-source-use");
      if (sourceUse) {
        sourceUse.value = sourceUseForDecision(node.value);
      }
    });
  });
}

function buildSourceReviewDecisionPayload(candidates, reviewsByIndex, metadata = {}) {
  const errors = [];
  const decisions = [];
  candidates.forEach((candidate, index) => {
    const review = reviewsByIndex[String(index)] || {};
    const decision = review.decision || defaultSourceDecision(candidate);
    const keepDecision = SOURCE_KEEP_DECISIONS.has(decision);
    const risky = isRiskySourceCandidate(candidate);
    const sampleId = String(candidate.sample_id || "").trim();
    const url = String(candidate.url || "").trim();
    const rationale = String(review.rationale || "").trim();
    if (!sampleId || !url) {
      errors.push(`第 ${index + 1} 条候选必须包含样本编号和链接。`);
    }
    if (keepDecision && !rationale) {
      errors.push(`${sampleId || `第 ${index + 1} 条候选`} 是保留类决策，必须填写审查理由。`);
    }
    if (keepDecision && risky && !review.allow_risky_seed) {
      errors.push(`${sampleId || `第 ${index + 1} 条候选`} 存在题库或培训站风险，必须勾选允许风险种子。`);
    }
    const item = {
      sample_id: sampleId,
      url,
      decision,
      source_use: review.source_use || sourceUseForDecision(decision),
      rationale,
      review_notes: String(review.review_notes || "").trim(),
      human_opened_url: Boolean(review.human_opened_url),
    };
    if (keepDecision) {
      item.crawl_priority = review.crawl_priority || "medium";
    }
    if (keepDecision && risky && review.allow_risky_seed) {
      item.allow_risky_seed = true;
    }
    decisions.push(item);
  });
  if (errors.length) {
    throw new Error(errors.join("\n"));
  }
  return {
    review_version: "v1",
    reviewer: metadata.reviewer || "人工",
    reviewed_at: metadata.reviewed_at || new Date().toISOString(),
    source_candidate_results_path: metadata.source_candidate_results_path || "",
    decisions,
  };
}

function handleLoadSourceCandidates() {
  try {
    state.sourceCandidates = parseSourceCandidateJsonl($("sourceCandidateResultsJsonl").value);
    state.sourceCandidateReviews = {};
    renderSourceCandidateReviewList();
    $("sourceReviewDecisionsJson").value = "";
    setPageStatus(`已载入 ${state.sourceCandidates.length} 条候选来源。审查结果只会成为未验证的种子资产。`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleFillMockSourceCandidates() {
  $("sourceCandidateResultsPath").value = "mock/source_candidate_results.jsonl";
  $("sourceCandidateResultsJsonl").value = MOCK_SOURCE_CANDIDATE_ROWS.map((row) => JSON.stringify(row)).join("\n");
  handleLoadSourceCandidates();
}

function handleBatchSourceDecision(decision) {
  saveSourceReviewEdits();
  const filter = $("sourceRiskFilter")?.value || "all";
  state.sourceCandidates.forEach((candidate, index) => {
    if (!sourceCandidateMatchesFilter(candidate, filter)) return;
    state.sourceCandidateReviews[String(index)] = {
      ...(state.sourceCandidateReviews[String(index)] || {}),
      decision,
      source_use: sourceUseForDecision(decision),
    };
  });
  renderSourceCandidateReviewList();
}

function handleGenerateSourceReviewDecisions() {
  try {
    saveSourceReviewEdits();
    const payload = buildSourceReviewDecisionPayload(state.sourceCandidates, state.sourceCandidateReviews, {
      reviewer: $("sourceCandidateReviewer").value.trim() || "人工",
      source_candidate_results_path: $("sourceCandidateResultsPath").value.trim(),
    });
    $("sourceReviewDecisionsJson").value = prettyJson(payload);
    setPageStatus(`已生成 ${payload.decisions.length} 条来源审查决策。本步骤不会确认原文、抓正文或写材料库。`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

async function handleCopySourceReviewDecisions() {
  const text = $("sourceReviewDecisionsJson").value;
  if (!text.trim()) {
    setPageStatus("请先生成来源审查决策文件，再复制。", "error");
    return;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      $("sourceReviewDecisionsJson").select();
      document.execCommand("copy");
    }
    setPageStatus("已复制来源审查决策文件内容。", "info");
  } catch (error) {
    setPageStatus(`复制失败：${error.message}`, "error");
  }
}

function handleDownloadSourceReviewDecisions() {
  const text = $("sourceReviewDecisionsJson").value;
  if (!text.trim()) {
    setPageStatus("请先生成来源审查决策文件，再下载。", "error");
    return;
  }
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "source_candidate_review_decisions.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setPageStatus("已下载来源审查决策文件。它只是审查输入，不是抓取批准。", "info");
}

function buildAgentReviewFeedbackInputPayload() {
  const rawFeedback = $("agentFeedbackRaw").value.trim();
  if (!rawFeedback) {
    throw new Error("请先填写用户原始反馈。");
  }
  const targetArtifacts = $("agentFeedbackTargetArtifacts").value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return {
    feedback_version: "v1",
    reviewer: $("agentFeedbackReviewer").value.trim() || "human",
    reviewed_at: new Date().toISOString(),
    target_scope: $("agentFeedbackTargetScope").value || "batch",
    target_artifacts: targetArtifacts,
    raw_feedback: rawFeedback,
    context: {
      family_context: {},
      sample_ids: [],
      artifact_paths: targetArtifacts,
    },
  };
}

function handleGenerateAgentReviewFeedbackInput() {
  try {
    const payload = buildAgentReviewFeedbackInputPayload();
    $("agentReviewFeedbackInputJson").value = prettyJson(payload);
    setPageStatus("已生成用户反馈输入 JSON。该文件只是 evidence，不会直接写回。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

async function handleCopyAgentReviewFeedbackInput() {
  const text = $("agentReviewFeedbackInputJson").value;
  if (!text.trim()) {
    setPageStatus("请先生成反馈输入 JSON，再复制。", "error");
    return;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      $("agentReviewFeedbackInputJson").select();
      document.execCommand("copy");
    }
    setPageStatus("已复制反馈输入 JSON。", "info");
  } catch (error) {
    setPageStatus(`复制失败：${error.message}`, "error");
  }
}

function handleDownloadAgentReviewFeedbackInput() {
  const text = $("agentReviewFeedbackInputJson").value;
  if (!text.trim()) {
    setPageStatus("请先生成反馈输入 JSON，再下载。", "error");
    return;
  }
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "agent_review_feedback_input.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const FORMALIZATION_GATE_STATUS = [
  "blocked",
  "review_needed",
  "material_card_review_ready",
  "proto_ready",
  "writeback_plan_ready",
];

const FORMALIZATION_GATE_UNSAFE_FIELDS = new Set([
  "formalized",
  "writeback_allowed",
  "executor_allowed",
  "verified",
  "verified_original_source",
  "material_card_write",
  "card_specs_write",
  "passage_service_ingest",
  "promotion_target_added",
]);

function emptyPreviewArtifact(status = "blocked") {
  return {
    preview_version: "v1",
    status,
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    requires_human_review: true,
    requires_regression: true,
    blocking_issues: [],
    missing_evidence: [],
    recommended_next_action: "",
  };
}

function parseOptionalJsonElement(id, label) {
  const node = $(id);
  if (!node) return null;
  return parseJsonField(node.value, label, null);
}

function scanUnsafeGateFields(value, path = "$", findings = []) {
  if (!value || typeof value !== "object") return findings;
  if (Array.isArray(value)) {
    value.forEach((item, index) => scanUnsafeGateFields(item, `${path}[${index}]`, findings));
    return findings;
  }
  Object.entries(value).forEach(([key, child]) => {
    if (FORMALIZATION_GATE_UNSAFE_FIELDS.has(key) && child === true) {
      findings.push(`${path}.${key}=true`);
    }
    scanUnsafeGateFields(child, `${path}.${key}`, findings);
  });
  return findings;
}

function gateTargetsFromDraft(formalPatchDraft) {
  const targetPatches = Array.isArray(formalPatchDraft?.target_patches) ? formalPatchDraft.target_patches : [];
  return targetPatches.map((item) => item.target).filter(Boolean);
}

function summarizeMaterialEvidence(materialEvidence, materialCardDraft) {
  const evidence = materialEvidence && typeof materialEvidence === "object" ? materialEvidence : {};
  const qualityStatus =
    evidence.material_quality_regression_status ||
    evidence.material_quality_status ||
    evidence.status ||
    "missing";
  const verifiedCount = Number(evidence.verified_original_source_count || 0);
  return {
    source_text_evidence_status: evidence.source_text_evidence_status || evidence.source_text_status || "unknown",
    source_gold_alignment_status: evidence.source_gold_alignment_status || evidence.alignment_status || "unknown",
    material_quality_regression_status: qualityStatus,
    verified_original_source_count: Number.isFinite(verifiedCount) ? verifiedCount : 0,
    requires_source_review: evidence.requires_source_review !== false,
    requires_alignment_review: evidence.requires_alignment_review !== false,
    requires_material_quality_review: evidence.requires_material_quality_review !== false,
    ready_for_material_card_review: Boolean(evidence.ready_for_material_card_review),
    ready_for_material_card_formalization: false,
    material_card_draft_status: materialCardDraft?.status || "unknown",
    blocking_issues: Array.isArray(evidence.blocking_issues) ? evidence.blocking_issues : [],
  };
}

function feedbackHasHighSeverityUnresolved(agentFeedback) {
  const items = Array.isArray(agentFeedback?.normalized_feedback) ? agentFeedback.normalized_feedback : [];
  return items.some((item) => {
    const severity = String(item.severity || "").toLowerCase();
    const status = String(item.status || item.resolution_status || "").toLowerCase();
    return severity === "high" && !["resolved", "accepted"].includes(status);
  });
}

function buildFormalizationGatePreview() {
  const inputs = {
    formal_patch_draft: parseOptionalJsonElement("formalGateFormalPatchDraftJson", "formal_patch_draft.json"),
    material_card_draft: parseOptionalJsonElement("formalGateMaterialCardDraftJson", "material_card_draft.json"),
    material_evidence_summary: parseOptionalJsonElement("formalGateMaterialEvidenceSummaryJson", "material_evidence_summary"),
    agent_review_feedback: parseOptionalJsonElement("formalGateAgentFeedbackJson", "agent_review_feedback_normalized.json"),
    source_review: parseOptionalJsonElement("formalGateSourceReviewJson", "source_candidate_review.json"),
    truth_gold_regression: parseOptionalJsonElement("formalGateTruthGoldRegressionJson", "truth_gold_regression_results.json"),
    runtime_activation_plan: parseOptionalJsonElement("formalGateRuntimeActivationPlanJson", "runtime_activation_plan.json"),
    formalization_packet: parseOptionalJsonElement("formalGateFormalizationPacketJson", "new_leaf_formalization_packet.json"),
    readiness_checklist: parseOptionalJsonElement("formalGateReadinessChecklistJson", "formalization_readiness_checklist.json"),
  };
  const blockingIssues = [];
  const missingEvidence = [];
  const warnings = [];

  Object.entries(inputs).forEach(([name, payload]) => {
    scanUnsafeGateFields(payload).forEach((finding) => {
      warnings.push(`${name}: ${finding}`);
    });
  });
  if (warnings.length) {
    blockingIssues.push("输入 artifact 中出现越权字段，Gate 预览已阻断。");
  }

  if (!inputs.formal_patch_draft) missingEvidence.push("formal_patch_draft");
  if (!inputs.agent_review_feedback) missingEvidence.push("agent_review_feedback_normalized");
  if (!inputs.runtime_activation_plan) missingEvidence.push("runtime_activation_plan");

  const targets = gateTargetsFromDraft(inputs.formal_patch_draft);
  const includesMaterialCard = targets.includes("material_card") || Boolean(inputs.material_card_draft);
  if (includesMaterialCard && !inputs.material_evidence_summary) {
    missingEvidence.push("material_evidence_summary");
  }

  const materialSummary = summarizeMaterialEvidence(inputs.material_evidence_summary, inputs.material_card_draft);
  if (materialSummary.material_quality_regression_status === "blocked") {
    blockingIssues.push("material_quality_regression_status=blocked");
  }
  if (materialSummary.requires_alignment_review) {
    blockingIssues.push("source_gold_alignment 仍需人工复核。");
  }
  if (materialSummary.verified_original_source_count > 0 && !inputs.source_review?.source_verification_approval) {
    blockingIssues.push("出现 verified_original_source_count>0，但没有 source verification approval。");
  }
  if (inputs.material_card_draft?.formalized === true || inputs.material_card_draft?.writeback_allowed === true) {
    blockingIssues.push("material_card_draft 试图 formalize 或 writeback。");
  }
  if (feedbackHasHighSeverityUnresolved(inputs.agent_review_feedback)) {
    blockingIssues.push("存在 high severity unresolved feedback。");
  }

  const canRunProto = Boolean(
    inputs.runtime_activation_plan?.proto_vs_formal?.can_run_proto_trial ||
      inputs.runtime_activation_plan?.can_run_proto_trial
  );
  const canRunFormal = Boolean(
    inputs.runtime_activation_plan?.proto_vs_formal?.can_run_formal_generation ||
      inputs.runtime_activation_plan?.can_run_formal_generation
  );
  const currentReadinessStatus = inputs.readiness_checklist?.status || "";
  let status = "blocked";
  if (!blockingIssues.length && !missingEvidence.length) {
    if (currentReadinessStatus === "writeback_plan_ready") {
      status = "writeback_plan_ready";
    } else if (materialSummary.ready_for_material_card_review) {
      status = "material_card_review_ready";
    } else if (canRunProto && !canRunFormal) {
      status = "proto_ready";
    } else {
      status = "review_needed";
    }
  }
  if (!FORMALIZATION_GATE_STATUS.includes(status)) status = "blocked";

  const recommendedNextAction =
    status === "blocked"
      ? "补齐缺失 evidence 或处理 blocking issues，再重新生成 Gate 预览。"
      : status === "material_card_review_ready"
        ? "进入 material_card 人工 review；这仍然不是 formalization。"
        : status === "proto_ready"
          ? "可继续 proto trial 和回归；正式生成仍需 writeback plan 与 approval。"
          : status === "writeback_plan_ready"
            ? "可准备正式 writeback plan/diff，但仍不能调用 executor。"
            : "进入人工复核，确认 evidence、runtime 和 regression。";

  const packetPreview = {
    ...emptyPreviewArtifact(status),
    packet_type: "new_leaf_formalization_packet_preview",
    evidence_refs: {
      formal_patch_draft: Boolean(inputs.formal_patch_draft),
      material_card_draft: Boolean(inputs.material_card_draft),
      material_evidence_summary: Boolean(inputs.material_evidence_summary),
      agent_review_feedback: Boolean(inputs.agent_review_feedback),
      source_review: Boolean(inputs.source_review),
      truth_gold_regression: Boolean(inputs.truth_gold_regression),
    },
    formal_targets: targets,
    material_evidence_summary: materialSummary,
    blocking_issues: blockingIssues,
    missing_evidence: missingEvidence,
    recommended_next_action: recommendedNextAction,
  };

  const runtimePreview = {
    ...emptyPreviewArtifact(status),
    asset_type: "runtime_activation_plan_preview",
    runtime_activation_status: inputs.runtime_activation_plan?.status || "missing",
    proto_vs_formal: {
      can_run_proto_trial: canRunProto,
      can_run_formal_generation: canRunFormal,
      blocked_reasons: inputs.runtime_activation_plan?.proto_vs_formal?.blocked_reasons || [],
    },
    runtime_targets: inputs.runtime_activation_plan?.runtime_targets || {},
    blocking_issues: blockingIssues,
    missing_evidence: missingEvidence,
    recommended_next_action: recommendedNextAction,
  };

  const readinessPreview = {
    ...emptyPreviewArtifact(status),
    asset_type: "formalization_readiness_checklist_preview",
    gate_status: status,
    material_line_status: materialSummary.material_quality_regression_status,
    runtime_activation_status: runtimePreview.runtime_activation_status,
    writeback_safety_status: "executor_blocked_in_frontend_preview",
    user_feedback_status: inputs.agent_review_feedback ? inputs.agent_review_feedback.status || "available" : "missing",
    blocking_issues: blockingIssues,
    missing_evidence: missingEvidence,
    recommended_next_action: recommendedNextAction,
    warnings,
  };
  return { status, packetPreview, runtimePreview, readinessPreview, warnings };
}

function renderFormalizationGateSummary(result) {
  const root = $("formalGateSummary");
  if (!root) return;
  const readiness = result.readinessPreview || {};
  const issueItems = (readiness.blocking_issues || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const missingItems = (readiness.missing_evidence || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const warningItems = (readiness.warnings || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  root.innerHTML = `
    <div class="distill-detail-box">
      <strong>Gate status</strong>
      <div class="distill-badge-row" style="margin-top:8px;">
        <span class="${result.status === "blocked" ? "distill-badge distill-badge-warn" : "distill-badge distill-badge-info"}">${escapeHtml(result.status)}</span>
      </div>
      <div style="margin-top:8px;">Recommended next action: ${escapeHtml(readiness.recommended_next_action || "-")}</div>
      <div style="margin-top:8px;">material_card_review_ready is not material_card_formalization_ready.</div>
    </div>
    <div class="distill-detail-box"><strong>Blocking issues</strong><ul>${issueItems || "<li>none</li>"}</ul></div>
    <div class="distill-detail-box"><strong>Missing evidence</strong><ul>${missingItems || "<li>none</li>"}</ul></div>
    <div class="distill-detail-box"><strong>Unsafe field warnings</strong><ul>${warningItems || "<li>none</li>"}</ul></div>
  `;
}

function handleGenerateFormalizationGatePreview() {
  try {
    const result = buildFormalizationGatePreview();
    state.formalizationGatePreview = result;
    $("formalGatePacketPreviewJson").value = prettyJson(result.packetPreview);
    $("formalGateRuntimePreviewJson").value = prettyJson(result.runtimePreview);
    $("formalGateReadinessPreviewJson").value = prettyJson(result.readinessPreview);
    renderFormalizationGateSummary(result);
    setPageStatus("已生成 Formalization Gate Preview。该预览不会写回、不会调用 executor。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

async function copyFormalGateOutput(id, label) {
  const text = $(id).value;
  if (!text.trim()) {
    setPageStatus(`请先生成 ${label}。`, "error");
    return;
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      $(id).select();
      document.execCommand("copy");
    }
    setPageStatus(`已复制 ${label}。`, "info");
  } catch (error) {
    setPageStatus(`复制失败：${error.message}`, "error");
  }
}

function handleDownloadFormalGatePreview() {
  const text = $("formalGateReadinessPreviewJson").value || $("formalGatePacketPreviewJson").value;
  if (!text.trim()) {
    setPageStatus("请先生成 Gate Preview JSON，再下载。", "error");
    return;
  }
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "formalization_gate_preview.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function handleClearFormalGateInputs() {
  [
    "formalGateFormalPatchDraftJson",
    "formalGateMaterialCardDraftJson",
    "formalGateMaterialEvidenceSummaryJson",
    "formalGateAgentFeedbackJson",
    "formalGateSourceReviewJson",
    "formalGateTruthGoldRegressionJson",
    "formalGateRuntimeActivationPlanJson",
    "formalGateFormalizationPacketJson",
    "formalGateReadinessChecklistJson",
    "formalGatePacketPreviewJson",
    "formalGateRuntimePreviewJson",
    "formalGateReadinessPreviewJson",
  ].forEach((id) => {
    const node = $(id);
    if (node) node.value = "";
  });
  state.formalizationGatePreview = null;
  renderFormalizationGateSummary({ status: "blocked", readinessPreview: emptyPreviewArtifact("blocked") });
  setPageStatus("已清空 Formalization Gate Preview 输入。", "info");
}

function handleFillBlockedFormalGateExample() {
  $("formalGateFormalPatchDraftJson").value = prettyJson({
    draft_version: "v1",
    status: "draft_only",
    formalized: false,
    writeback_allowed: false,
    target_patches: [{ target: "material_card" }, { target: "prompt_assets" }],
  });
  $("formalGateMaterialEvidenceSummaryJson").value = prettyJson({
    source_text_evidence_status: "available",
    source_gold_alignment_status: "needs_human_review",
    material_quality_regression_status: "blocked",
    verified_original_source_count: 0,
    requires_alignment_review: true,
    requires_material_quality_review: true,
    ready_for_material_card_review: false,
    ready_for_material_card_formalization: false,
    blocking_issues: ["alignment weak", "material quality blocked"],
  });
  $("formalGateAgentFeedbackJson").value = prettyJson({
    feedback_version: "v1",
    status: "normalized",
    formalized: false,
    writeback_allowed: false,
    normalized_feedback: [{ dimension: "material_too_short", severity: "high", target_line: "material_line" }],
  });
  $("formalGateRuntimeActivationPlanJson").value = prettyJson({
    activation_plan_version: "v1",
    status: "draft_only",
    formalized: false,
    writeback_allowed: false,
    proto_vs_formal: {
      can_run_proto_trial: true,
      can_run_formal_generation: false,
      blocked_reasons: ["material evidence blocked"],
    },
  });
  handleGenerateFormalizationGatePreview();
}

function parseBusinessJsonOrText(raw, label) {
  const text = String(raw || "").trim();
  if (!text) return { kind: "missing", payload: null, summary: `${label}: missing` };
  try {
    return { kind: "json", payload: JSON.parse(text), summary: `${label}: JSON` };
  } catch {
    const lines = text.split(/\r?\n/).filter((line) => line.trim());
    if (lines.length > 1 && lines.every((line) => line.trim().startsWith("{"))) {
      const rows = [];
      let ok = true;
      lines.forEach((line) => {
        try {
          rows.push(JSON.parse(line));
        } catch {
          ok = false;
        }
      });
      if (ok) return { kind: "jsonl", payload: rows, summary: `${label}: JSONL / ${rows.length} rows` };
    }
    if (text.includes(",") && lines.length > 1) {
      return { kind: "csv", payload: { row_count: Math.max(lines.length - 1, 0), header: lines[0] }, summary: `${label}: CSV / ${Math.max(lines.length - 1, 0)} rows` };
    }
    return { kind: "text", payload: { text_preview: text.slice(0, 1200) }, summary: `${label}: text` };
  }
}

function businessFamilyContext(questionPack, protocolEvidence, gateEvidence) {
  const pack = questionPack?.payload || {};
  const protocol = protocolEvidence?.payload || {};
  const gate = gateEvidence?.payload || {};
  const familyContext =
    protocol.family_context ||
    gate.family_context ||
    protocol.material_card_draft?.family_binding ||
    gate.material_card_draft?.family_binding ||
    {};
  const firstSample = Array.isArray(pack.samples) ? pack.samples[0] : Array.isArray(pack) ? pack[0] : {};
  return {
    mother_family_id: familyContext.mother_family_id || pack.mother_family_id || firstSample?.mother_family_id || "unknown",
    child_family_id: familyContext.child_family_id || pack.child_family_id || firstSample?.child_family_id || "unknown",
    leaf_label: familyContext.leaf_label || pack.leaf_label || firstSample?.leaf_label || "unknown",
    question_focus: familyContext.question_focus || pack.question_focus || firstSample?.question_focus || "unknown",
    question_card_reference: familyContext.question_card_reference || pack.question_card_id || firstSample?.question_card_id || "",
  };
}

function businessCandidateFeatures(protocolEvidence, gateEvidence) {
  const protocol = protocolEvidence?.payload || {};
  const gate = gateEvidence?.payload || {};
  const features = [];
  const axes = protocol.candidate_axes || protocol.bootstrap_discovery?.candidate_axes || [];
  if (Array.isArray(axes)) {
    axes.slice(0, 6).forEach((axis) => {
      features.push(axis.label || axis.name || axis.axis_name || axis.source_id || axis.id);
    });
  }
  const patches = protocol.target_patches || protocol.formal_patch_draft?.target_patches || [];
  if (Array.isArray(patches)) {
    patches.forEach((patch) => {
      const decisions = patch.patch?.proto_confirmed_decisions || [];
      decisions.slice(0, 4).forEach((item) => features.push(item.confirmed_name || item.name || item.source_id));
    });
  }
  const requirements =
    protocol.material_requirements ||
    gate.material_card_draft?.material_requirements ||
    gate.material_requirements ||
    {};
  ["must_contain", "must_avoid", "document_genre_candidates", "material_structure_label_candidates"].forEach((key) => {
    const values = requirements[key];
    if (Array.isArray(values)) values.slice(0, 4).forEach((item) => features.push(item));
  });
  return Array.from(new Set(features.filter(Boolean))).slice(0, 10);
}

function businessFeedbackDimensions(rawFeedback) {
  const raw = String(rawFeedback || "");
  const dimensions = [];
  const push = (dimension, label) => dimensions.push({ dimension, label });
  if (/简单|容易|太浅|难度低/.test(raw)) push("difficulty_too_low", "\u96BE\u5EA6\u504F\u4F4E");
  if (/太难|难度高|看不懂/.test(raw)) push("difficulty_too_high", "\u96BE\u5EA6\u504F\u9AD8");
  if (/材料.*短|字数.*少|上下文.*少/.test(raw)) push("material_too_short", "\u6750\u6599\u504F\u77ED");
  if (/材料.*不像|原文|自然/.test(raw)) push("source_like_material_weak", "\u6750\u6599\u4E0D\u591F\u50CF\u81EA\u7136\u539F\u6587");
  if (/干扰|迷惑|选项.*直|太直给/.test(raw)) push("distractor_weakness", "\u5E72\u6270\u9879\u5F31");
  if (/解析|说服力|理由/.test(raw)) push("explanation_weak", "\u89E3\u6790\u8BF4\u670D\u529B\u5F31");
  if (/不像真题|风格/.test(raw)) push("exam_style_mismatch", "\u4E0D\u50CF\u771F\u9898");
  if (/题库|答案解析|教培/.test(raw)) push("question_bank_style_contamination", "\u7591\u4F3C\u9898\u5E93\u5316\u6C61\u67D3");
  return dimensions;
}

function businessGateEvidenceSummary(gateEvidence) {
  const gate = gateEvidence?.payload || {};
  const material = gate.material_evidence_summary || gate.material_protocol_summary || gate;
  const status = gate.status || material.material_quality_regression_status || material.source_gold_alignment_status || "blocked";
  const blockingIssues = []
    .concat(gate.blocking_issues || [])
    .concat(material.blocking_issues || [])
    .filter(Boolean);
  const missingEvidence = []
    .concat(gate.missing_evidence || [])
    .concat(material.missing_evidence || [])
    .filter(Boolean);
  return {
    status,
    source_text_evidence_status: material.source_text_evidence_status || "unknown",
    source_gold_alignment_status: material.source_gold_alignment_status || "unknown",
    material_quality_regression_status: material.material_quality_regression_status || material.status || "unknown",
    verified_original_source_count: Number(material.verified_original_source_count || 0),
    ready_for_material_card_review: Boolean(material.ready_for_material_card_review || gate.ready_for_material_card_review),
    ready_for_material_card_formalization: false,
    blocking_issues: blockingIssues,
    missing_evidence: missingEvidence,
  };
}

function businessHumanGateTranslation(gateSummary, feedbackDimensions) {
  const reasons = [];
  const nextSteps = [];
  const status = gateSummary.status || "blocked";
  if (status === "blocked" || gateSummary.material_quality_regression_status === "blocked") {
    reasons.push("\u6750\u6599\u8BC1\u636E\u8FD8\u4E0D\u8DB3\u4EE5\u652F\u6491\u6B63\u5F0F\u843D\u4F4D\u3002");
  }
  if (gateSummary.source_gold_alignment_status && !["aligned", "partial"].includes(gateSummary.source_gold_alignment_status)) {
    reasons.push("\u6765\u6E90\u6B63\u6587\u548C\u771F\u9898 gold \u6750\u6599\u7684\u5BF9\u9F50\u8FD8\u9700\u8981\u4EBA\u5DE5\u590D\u6838\u3002");
  }
  if (gateSummary.verified_original_source_count > 0) {
    reasons.push("\u8F93\u5165\u91CC\u51FA\u73B0\u4E86\u5DF2\u9A8C\u8BC1\u539F\u6587\u8BA1\u6570\uFF0C\u4F46\u524D\u7AEF\u4E0D\u80FD\u786E\u8BA4\u539F\u6587\u3002");
  }
  if (feedbackDimensions.some((item) => item.dimension === "material_too_short")) {
    reasons.push("\u7528\u6237\u53CD\u9988\u6307\u51FA\u6750\u6599\u504F\u77ED\uFF0C\u9700\u8981\u66F4\u5B8C\u6574\u7684\u4E0A\u4E0B\u6587\u3002");
  }
  if (feedbackDimensions.some((item) => item.dimension === "distractor_weakness")) {
    reasons.push("\u7528\u6237\u53CD\u9988\u6307\u51FA\u5E72\u6270\u9879\u5F31\uFF0C\u540E\u7EED\u9700\u8981\u7528\u6750\u6599\u673A\u5236\u652F\u6491\u9009\u9879\u8BBE\u8BA1\u3002");
  }
  if (!reasons.length) reasons.push("\u4E3B\u8981 evidence \u5DF2\u7ECF\u8F83\u5B8C\u6574\uFF0C\u4F46\u4ECD\u9700\u8981\u4EBA\u5DE5\u590D\u6838\u3002");
  if (gateSummary.source_text_evidence_status !== "available") {
    nextSteps.push("\u8865\u5145\u66F4\u5B8C\u6574\u7684\u6765\u6E90\u6B63\u6587\uFF0C\u4E0D\u8981\u7528\u9898\u5E93\u9875\u4EE3\u66FF\u539F\u6587\u3002");
  }
  nextSteps.push("\u4EBA\u5DE5\u786E\u8BA4 source/gold \u5BF9\u9F50\u5173\u7CFB\uFF0C\u533A\u5206\u539F\u6587\u5019\u9009\u548C\u76F8\u4F3C\u6750\u6599\u3002");
  nextSteps.push("\u91CD\u65B0\u8DD1\u6750\u6599\u8D28\u91CF\u56DE\u5F52\u548C readiness gate\u3002");
  const headline =
    status === "material_card_review_ready"
      ? "\u53EF\u4EE5\u8FDB\u5165\u6750\u6599\u5361\u4EBA\u5DE5\u5BA1\u9605\uFF0C\u4F46\u8FD8\u4E0D\u80FD\u6B63\u5F0F\u5199\u56DE\u3002"
      : status === "proto_ready"
        ? "\u53EF\u4EE5\u7EE7\u7EED\u539F\u578B\u8BD5\u8DD1\uFF0C\u4F46\u8FD8\u4E0D\u80FD\u6B63\u5F0F\u843D\u4F4D\u3002"
        : "\u5F53\u524D\u4E0D\u80FD\u6B63\u5F0F\u843D\u4F4D\u3002";
  return { headline, reasons, nextSteps };
}

function buildBusinessCardFamilyMarkdown(preview) {
  const family = preview.family_context || {};
  const features = preview.core_features?.length ? preview.core_features : ["\u5C1A\u9700\u8981\u66F4\u591A\u6837\u672C\u548C\u4EBA\u5DE5\u786E\u8BA4\u3002"];
  const feedback = preview.feedback_dimensions || [];
  const lines = [
    "# \u5361\u65CF\u8349\u6848\u62A5\u544A",
    "",
    `- \u7CFB\u7EDF\u8BC6\u522B\u7684\u6BCD\u65CF\uFF1A${family.mother_family_id || "unknown"}`,
    `- \u7CFB\u7EDF\u8BC6\u522B\u7684\u5B50\u65CF\uFF1A${family.child_family_id || "unknown"}`,
    `- \u53F6\u65CF / \u4E1A\u52A1\u6807\u7B7E\uFF1A${family.leaf_label || "unknown"}`,
    "",
    "## \u6838\u5FC3\u7279\u5F81",
    ...features.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## \u5F53\u524D\u72B6\u6001",
    `- \u9898\u578B proto / \u8865\u4E01 evidence\uFF1A${preview.protocol_available ? "\u5DF2\u6709" : "\u4E0D\u8DB3"}`,
    `- \u7528\u6237\u53CD\u9988\uFF1A${feedback.length ? feedback.map((item) => item.label).join(" / ") : "\u6682\u65E0\u7ED3\u6784\u5316\u53CD\u9988"}`,
    `- \u6750\u6599\u7EBF\u72B6\u6001\uFF1A${preview.gate_summary.material_quality_regression_status || "unknown"}`,
    `- \u662F\u5426\u53EF\u6B63\u5F0F\u5199\u56DE\uFF1A\u5426`,
    "",
    "## \u4E1A\u52A1\u7ED3\u8BBA",
    preview.human_gate.headline,
    "",
    "## \u4E0B\u4E00\u6B65",
    ...preview.human_gate.nextSteps.map((item, index) => `${index + 1}. ${item}`),
    "",
    "> \u8FD9\u662F\u4E1A\u52A1\u53EF\u8BFB\u8349\u6848\uFF0C\u4E0D\u662F\u6B63\u5F0F material_card / question_card \u5199\u56DE\u3002",
  ];
  return lines.join("\n");
}

function buildBusinessModePreview() {
  const questionPack = parseBusinessJsonOrText($("businessQuestionPackText").value, "question_pack");
  const protocolEvidence = parseBusinessJsonOrText($("businessProtocolEvidenceJson").value, "protocol_evidence");
  const gateEvidence = parseBusinessJsonOrText($("businessGateEvidenceJson").value, "gate_evidence");
  const familyContext = businessFamilyContext(questionPack, protocolEvidence, gateEvidence);
  const features = businessCandidateFeatures(protocolEvidence, gateEvidence);
  const feedbackDimensions = businessFeedbackDimensions($("businessUserFeedbackText").value);
  const gateSummary = businessGateEvidenceSummary(gateEvidence);
  const humanGate = businessHumanGateTranslation(gateSummary, feedbackDimensions);
  const preview = {
    preview_version: "v1",
    mode: "business",
    status: gateSummary.status || "blocked",
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    family_context: familyContext,
    input_support: {
      upload_preview_formats: ["pdf", "csv", "doc", "docx", "json", "jsonl", "md", "markdown", "txt", "xlsx"],
      best_effort_formats: ["pdf", "doc"],
      structured_formats: ["json", "jsonl", "csv", "xlsx"],
    },
    package_summary: questionPack.summary,
    protocol_available: protocolEvidence.kind !== "missing",
    gate_summary: gateSummary,
    core_features: features,
    feedback_dimensions: feedbackDimensions,
    human_gate: humanGate,
    limits: [
      "business mode is a readable preview, not formal writeback",
      "technical JSON remains available under details",
      "material_card_review_ready is not material_card formalization",
    ],
  };
  preview.card_family_report_markdown = buildBusinessCardFamilyMarkdown(preview);
  return preview;
}

/* Deprecated duplicate business-mode renderer kept inert after the staged workflow rewrite.
function renderBusinessModePreview(preview) {
  const reasons = preview.human_gate.reasons.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const nextSteps = preview.human_gate.nextSteps.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const features = (preview.core_features || []).map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const feedback = (preview.feedback_dimensions || []).map((item) => `<span class="distill-badge distill-badge-info">${escapeHtml(item.label)}</span>`).join("");
  $("businessHumanSummary").innerHTML = `
    <h3>\u4EBA\u8BDD\u7ED3\u8BBA</h3>
    <div class="business-status-pill">${escapeHtml(preview.human_gate.headline)}</div>
    <h3 style="margin-top:14px;">\u539F\u56E0</h3>
    <ol>${reasons}</ol>
    <h3>\u4E0B\u4E00\u6B65</h3>
    <ol>${nextSteps}</ol>
  `;
  $("businessCardFamilySummary").innerHTML = `
    <h3>\u5361\u65CF\u8349\u6848\u62A5\u544A</h3>
    <div>\u7CFB\u7EDF\u8BC6\u522B\uFF1A${escapeHtml(preview.family_context.mother_family_id)} / ${escapeHtml(preview.family_context.child_family_id)} / ${escapeHtml(preview.family_context.leaf_label)}</div>
    <h3 style="margin-top:14px;">\u6838\u5FC3\u7279\u5F81</h3>
    <ol>${features || `<li>\u5C1A\u9700\u66F4\u591A evidence\u3002</li>`}</ol>
    <h3>\u7528\u6237\u53CD\u9988</h3>
    <div class="distill-badge-row">${feedback || `<span class="distill-help">\u6682\u65E0\u7ED3\u6784\u5316\u53CD\u9988</span>`}</div>
  `;
  $("businessCardFamilyReportText").value = preview.card_family_report_markdown;
  $("businessModePreviewJson").value = prettyJson(preview);
}

function handleGenerateBusinessModeReport() {
  try {
    const preview = buildBusinessModePreview();
    state.businessModePreview = preview;
    renderBusinessModePreview(preview);
    setPageStatus("\u5DF2\u751F\u6210\u4E1A\u52A1\u6A21\u5F0F\u62A5\u544A\u3002\u6280\u672F JSON \u5DF2\u6536\u8FDB\u8BE6\u60C5\u533A\u3002", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleFillBusinessModeExample() {
  $("businessQuestionPackText").value = prettyJson({
    mother_family_id: "word_usage",
    child_family_id: "word_usage_content_word",
    leaf_label: "\u5B9E\u8BCD\u8BED\u5883\u4E49",
    samples: [{ sample_id: "sample-1" }, { sample_id: "sample-2" }],
  });
  $("businessProtocolEvidenceJson").value = prettyJson({
    family_context: {
      mother_family_id: "word_usage",
      child_family_id: "word_usage_content_word",
      leaf_label: "\u5B9E\u8BCD\u8BED\u5883\u4E49",
    },
    candidate_axes: [
      { name: "\u4F9D\u8D56\u4E0A\u4E0B\u6587\u8BED\u5883" },
      { name: "\u9519\u9879\u6765\u81EA\u5C40\u90E8\u8BCD\u4E49\u8BEF\u8BFB" },
      { name: "\u6750\u6599\u9700\u8981\u8DB3\u591F\u524D\u540E\u6587" },
    ],
  });
  $("businessGateEvidenceJson").value = prettyJson({
    status: "blocked",
    material_evidence_summary: {
      source_text_evidence_status: "available",
      source_gold_alignment_status: "needs_human_review",
      material_quality_regression_status: "blocked",
      verified_original_source_count: 0,
      ready_for_material_card_review: false,
      blocking_issues: ["source/gold alignment weak", "material quality regression blocked"],
    },
  });
  $("businessUserFeedbackText").value = "\u592A\u7B80\u5355\uFF0C\u6750\u6599\u4E5F\u592A\u77ED\uFF0C\u5E72\u6270\u9879\u4E0D\u591F\u8FF7\u60D1\uFF0C\u4E0D\u50CF\u771F\u9898\u3002";
  handleGenerateBusinessModeReport();
}

async function handleCopyBusinessModeReport() {
  const text = $("businessCardFamilyReportText").value;
  if (!text.trim()) {
    setPageStatus("\u8BF7\u5148\u751F\u6210\u4E1A\u52A1\u62A5\u544A\u3002", "error");
    return;
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    $("businessCardFamilyReportText").select();
    document.execCommand("copy");
  }
  setPageStatus("\u5DF2\u590D\u5236\u5361\u65CF\u8349\u6848\u62A5\u544A\u3002", "info");
}

async function handleBusinessQuestionPackFile(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file, file.name));
  setPageStatus("\u6B63\u5728\u89E3\u6790\u9898\u5305\u9884\u89C8\uFF1A" + files.map((file) => file.name).join(", "), "info");
  try {
    const response = await fetch("/api/v1/distill/question-pack/preview", {
      method: "POST",
      body: formData,
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error?.message || "question pack preview failed");
    }
    $("businessQuestionPackText").value = prettyJson(payload);
    const manualCount = Number(payload.manual_required_file_count || 0);
    const parsedCount = Number(payload.parsed_file_count || 0);
    setPageStatus(`\u9898\u5305\u9884\u89C8\u5B8C\u6210\uFF1A\u5DF2\u89E3\u6790 ${parsedCount} \u4E2A\u6587\u4EF6\uFF0C${manualCount} \u4E2A\u9700\u8981\u4EBA\u5DE5\u590D\u6838\u3002`, "info");
  } catch (error) {
    const textFiles = files.filter((file) => /\.(json|jsonl|csv|txt|md|markdown)$/i.test(file.name));
    if (!textFiles.length) {
      $("businessQuestionPackText").value = prettyJson({
        preview_version: "v1",
        status: "manual_required",
        files: files.map((file) => ({ file_name: file.name, size_bytes: file.size, status: "upload_preview_failed" })),
        error: error.message,
      });
      setPageStatus("\u9898\u5305\u9884\u89C8\u63A5\u53E3\u4E0D\u53EF\u7528\uFF0C\u4E14\u6240\u9009\u6587\u4EF6\u4E0D\u662F\u6D4F\u89C8\u5668\u53EF\u76F4\u8BFB\u6587\u672C\u683C\u5F0F\u3002", "error");
      return;
    }
    const texts = await Promise.all(textFiles.map((file) => file.text()));
    $("businessQuestionPackText").value = texts.join("\n\n");
    setPageStatus("\u540E\u7AEF\u9884\u89C8\u63A5\u53E3\u4E0D\u53EF\u7528\uFF0C\u5DF2\u964D\u7EA7\u8BFB\u53D6\u6587\u672C\u578B\u9898\u5305\u3002", "info");
  }
}

function businessFeedbackDimensions(rawFeedback) {
  const raw = String(rawFeedback || "");
  const dimensions = [];
  const push = (dimension, label) => dimensions.push({ dimension, label });
  const has = (pattern) => pattern.test(raw);
  if (has(/太简单|容易|偏简单|难度低|难度偏低|浅/)) push("difficulty_too_low", "难度偏低");
  if (has(/太难|难度高|难度偏高|看不懂/)) push("difficulty_too_high", "难度偏高");
  if (has(/材料.*短|字数.*少|上下文.*少|语境.*不够|材料短/)) push("material_too_short", "材料偏短");
  if (has(/材料.*不像|不像原文|自然原文|来源.*不自然/)) push("source_like_material_weak", "材料不够像自然原文");
  if (has(/干扰|迷惑|选项.*直给|太直给|错项.*弱/)) push("distractor_weakness", "干扰项弱");
  if (has(/解析|说服力|理由不够/)) push("explanation_weak", "解析说服力弱");
  if (has(/不像真题|风格不对|题感不对/)) push("exam_style_mismatch", "不像真题");
  if (has(/题库|答案解析|教培|刷题/)) push("question_bank_style_contamination", "疑似题库化污染");
  return Array.from(new Map(dimensions.map((item) => [item.dimension, item])).values());
}

function businessSelectLabel(id) {
  const node = $(id);
  if (!node) return "";
  return node.selectedOptions?.[0]?.textContent || node.value || "";
}

function businessUserJudgments() {
  return {
    source_usefulness: $("businessSourceUsefulness")?.value || "unknown",
    source_usefulness_label: businessSelectLabel("businessSourceUsefulness"),
    source_review_note: $("businessSourceReviewText")?.value?.trim() || "",
    generated_question_judgment: $("businessGeneratedQuestionJudgment")?.value || "unknown",
    generated_question_judgment_label: businessSelectLabel("businessGeneratedQuestionJudgment"),
    generated_question_note: $("businessGeneratedQuestionText")?.value?.trim() || "",
    landing_decision: $("businessLandingDecision")?.value || "unknown",
    landing_decision_label: businessSelectLabel("businessLandingDecision"),
  };
}

function businessHumanGateTranslation(gateSummary, feedbackDimensions, userJudgments = {}) {
  const reasons = [];
  const nextSteps = [];
  const status = gateSummary.status || "blocked";
  if (status === "blocked" || gateSummary.material_quality_regression_status === "blocked") {
    reasons.push("材料证据还不足以支撑正式落位。");
  }
  if (gateSummary.source_gold_alignment_status && !["aligned", "partial"].includes(gateSummary.source_gold_alignment_status)) {
    reasons.push("来源正文和真题材料的对齐还需要人工复核。");
  }
  if (gateSummary.verified_original_source_count > 0) {
    reasons.push("输入里出现已验证原文计数，但前端不能确认原文。");
  }
  if (feedbackDimensions.some((item) => item.dimension === "material_too_short")) {
    reasons.push("用户反馈指出材料偏短，需要更完整的上下文。");
  }
  if (feedbackDimensions.some((item) => item.dimension === "distractor_weakness")) {
    reasons.push("用户反馈指出干扰项弱，后续需要用材料机制支撑选项设计。");
  }
  if (userJudgments.source_usefulness === "question_bank") {
    reasons.push("用户判断当前来源像题库或解析页，不能作为材料来源继续推进。");
  } else if (userJudgments.source_usefulness === "irrelevant") {
    reasons.push("用户判断当前来源无关，需要淘汰或重新找来源。");
  } else if (userJudgments.source_usefulness === "similar_only") {
    reasons.push("用户判断当前来源只能算相似材料，不能当作已确认原文。");
  }
  if (userJudgments.generated_question_judgment === "not_usable") {
    reasons.push("用户判断生成题不能用，说明题卡或材料机制还没有稳定。");
  } else if (userJudgments.generated_question_judgment === "needs_edit") {
    reasons.push("用户判断生成题需要修改，还不能直接进入正式落位。");
  }
  if (userJudgments.landing_decision === "hold_material") {
    reasons.push("用户选择先补材料来源或正文。");
  } else if (userJudgments.landing_decision === "hold_quality") {
    reasons.push("用户选择先改生成质量。");
  } else if (userJudgments.landing_decision === "reject_now") {
    reasons.push("用户选择暂不落位。");
  }
  if (!reasons.length) reasons.push("主要证据已经较完整，但仍需要人工复核。");
  if (gateSummary.source_text_evidence_status !== "available") {
    nextSteps.push("补充更完整的来源正文，不要用题库页代替原文。");
  }
  if (["question_bank", "irrelevant"].includes(userJudgments.source_usefulness)) {
    nextSteps.push("重新选择候选来源，优先使用可靠文章页或机构 / 媒体原文。");
  }
  if (["not_usable", "needs_edit"].includes(userJudgments.generated_question_judgment)) {
    nextSteps.push("把生成题问题记录为反馈证据，再重新试生成小样本。");
  }
  nextSteps.push("人工确认来源与真题材料的对齐关系，区分原文候选和相似材料。");
  nextSteps.push("重新跑材料质量回归和 readiness gate。");
  const headline =
    userJudgments.landing_decision === "reject_now"
      ? "用户已选择暂不落位。"
      : userJudgments.generated_question_judgment === "not_usable"
        ? "当前生成题不能用，不能正式落位。"
        : userJudgments.source_usefulness === "question_bank" || userJudgments.source_usefulness === "irrelevant"
          ? "当前来源不能支撑落位。"
          : status === "material_card_review_ready"
            ? "可以进入材料卡人工审阅，但还不能正式写回。"
            : status === "proto_ready"
              ? "可以继续原型试跑，但还不能正式落位。"
              : "当前不能正式落位。";
  return { headline, reasons, nextSteps };
}

function buildBusinessCardFamilyMarkdown(preview) {
  const family = preview.family_context || {};
  const features = preview.core_features?.length ? preview.core_features : ["尚需要更多样本和人工确认。"];
  const feedback = preview.feedback_dimensions || [];
  const judgments = preview.user_judgments || {};
  const lines = [
    "# 卡族草案报告",
    "",
    `- 系统识别的母族：${family.mother_family_id || "unknown"}`,
    `- 系统识别的子族：${family.child_family_id || "unknown"}`,
    `- 叶族 / 业务标签：${family.leaf_label || "unknown"}`,
    "",
    "## 核心特征",
    ...features.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## 业务判断",
    `- 来源有没有用：${judgments.source_usefulness_label || "未判断"}`,
    `- 生成题能不能用：${judgments.generated_question_judgment_label || "未判断"}`,
    `- 是否允许送审：${judgments.landing_decision_label || "未判断"}`,
    "",
    "## 当前状态",
    `- 题型 proto / 补丁证据：${preview.protocol_available ? "已存在" : "不足"}`,
    `- 用户反馈：${feedback.length ? feedback.map((item) => item.label).join(" / ") : "暂无结构化反馈"}`,
    `- 材料线状态：${preview.gate_summary.material_quality_regression_status || "unknown"}`,
    "- 是否可正式写回：否",
    "",
    "## 业务结论",
    preview.human_gate.headline,
    "",
    "## 下一步",
    ...preview.human_gate.nextSteps.map((item, index) => `${index + 1}. ${item}`),
    "",
    "> 这是业务可读草案，不是正式 material_card / question_card 写回。",
  ];
  return lines.join("\n");
}

function buildBusinessModePreview() {
  const questionPack = parseBusinessJsonOrText($("businessQuestionPackText").value, "question_pack");
  const protocolEvidence = parseBusinessJsonOrText($("businessProtocolEvidenceJson").value, "protocol_evidence");
  const gateEvidence = parseBusinessJsonOrText($("businessGateEvidenceJson").value, "gate_evidence");
  const familyContext = businessFamilyContext(questionPack, protocolEvidence, gateEvidence);
  const features = businessCandidateFeatures(protocolEvidence, gateEvidence);
  const feedbackDimensions = businessFeedbackDimensions($("businessUserFeedbackText").value);
  const gateSummary = businessGateEvidenceSummary(gateEvidence);
  const userJudgments = businessUserJudgments();
  const humanGate = businessHumanGateTranslation(gateSummary, feedbackDimensions, userJudgments);
  const preview = {
    preview_version: "v1",
    mode: "business",
    status: gateSummary.status || "blocked",
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    family_context: familyContext,
    input_support: {
      upload_preview_formats: ["pdf", "csv", "doc", "docx", "json", "jsonl", "md", "markdown", "txt", "xlsx"],
      best_effort_formats: ["pdf", "doc"],
      structured_formats: ["json", "jsonl", "csv", "xlsx"],
    },
    package_summary: questionPack.summary,
    protocol_available: protocolEvidence.kind !== "missing",
    gate_summary: gateSummary,
    core_features: features,
    user_judgments: userJudgments,
    feedback_dimensions: feedbackDimensions,
    human_gate: humanGate,
    limits: [
      "业务模式只收集用户判断，不正式写回",
      "技术 JSON 保留在详情区",
      "material_card_review_ready 不等于 material_card formalization",
    ],
  };
  preview.card_family_report_markdown = buildBusinessCardFamilyMarkdown(preview);
  return preview;
}

function renderBusinessModePreview(preview) {
  const reasons = preview.human_gate.reasons.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const nextSteps = preview.human_gate.nextSteps.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const features = (preview.core_features || []).map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const feedback = (preview.feedback_dimensions || []).map((item) => `<span class="distill-badge distill-badge-info">${escapeHtml(item.label)}</span>`).join("");
  const judgments = preview.user_judgments || {};
  $("businessHumanSummary").innerHTML = `
    <h3>人话结论</h3>
    <div class="business-status-pill">${escapeHtml(preview.human_gate.headline)}</div>
    <h3 style="margin-top:14px;">业务判断</h3>
    <ul>
      <li>来源：${escapeHtml(judgments.source_usefulness_label || "未判断")}</li>
      <li>生成题：${escapeHtml(judgments.generated_question_judgment_label || "未判断")}</li>
      <li>落位：${escapeHtml(judgments.landing_decision_label || "未判断")}</li>
    </ul>
    <h3 style="margin-top:14px;">原因</h3>
    <ol>${reasons}</ol>
    <h3>下一步</h3>
    <ol>${nextSteps}</ol>
  `;
  $("businessCardFamilySummary").innerHTML = `
    <h3>卡族草案报告</h3>
    <div>系统识别：${escapeHtml(preview.family_context.mother_family_id)} / ${escapeHtml(preview.family_context.child_family_id)} / ${escapeHtml(preview.family_context.leaf_label)}</div>
    <h3 style="margin-top:14px;">核心特征</h3>
    <ol>${features || `<li>尚需更多 evidence。</li>`}</ol>
    <h3>用户反馈</h3>
    <div class="distill-badge-row">${feedback || `<span class="distill-help">暂无结构化反馈</span>`}</div>
  `;
  $("businessCardFamilyReportText").value = preview.card_family_report_markdown;
  $("businessModePreviewJson").value = prettyJson(preview);
}

function handleFillBusinessModeExample() {
  $("businessQuestionPackText").value = "系统识别：词语理解 / 实词语境义。样本数：8。用户无需填写 JSON。";
  $("businessProtocolEvidenceJson").value = prettyJson({
    family_context: {
      mother_family_id: "word_usage",
      child_family_id: "word_usage_content_word",
      leaf_label: "实词语境义",
    },
    candidate_axes: [
      { name: "依赖上下文语境" },
      { name: "错项来自局部词义误读" },
      { name: "材料需要足够前后文" },
    ],
  });
  $("businessGateEvidenceJson").value = prettyJson({
    status: "blocked",
    material_evidence_summary: {
      source_text_evidence_status: "available",
      source_gold_alignment_status: "needs_human_review",
      material_quality_regression_status: "blocked",
      verified_original_source_count: 0,
      ready_for_material_card_review: false,
      blocking_issues: ["source/gold alignment weak", "material quality regression blocked"],
    },
  });
  $("businessSourceUsefulness").value = "similar_only";
  $("businessSourceReviewText").value = "这个网址主题相关，可以继续看，但还不能当已确认原文。";
  $("businessGeneratedQuestionJudgment").value = "needs_edit";
  $("businessGeneratedQuestionText").value = "生成题有题感，但材料偏短，错项还不够迷惑。";
  $("businessLandingDecision").value = "hold_material";
  $("businessUserFeedbackText").value = "太简单，材料也太短，干扰项不够迷惑，不像真题。";
  handleGenerateBusinessModeReport();
}
*/

const BUSINESS_STAGE_IDS = ["prep", "source", "draft", "acceptance"];

function setBusinessLoading(active, message) {
  const root = $("businessAsyncLoading");
  const text = $("businessAsyncLoadingText");
  if (!root) return;
  root.classList.toggle("is-active", Boolean(active));
  if (text && message) text.textContent = message;
}

function setBusinessStage(stage, options = {}) {
  const target = BUSINESS_STAGE_IDS.includes(stage) ? stage : "prep";
  document.querySelectorAll("[data-business-stage]").forEach((panel) => {
    panel.hidden = panel.getAttribute("data-business-stage") !== target;
  });
  document.querySelectorAll("[data-business-stage-target]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.businessStageTarget === target);
  });
  if (!options.silent) setPageStatus(`已切换到业务流程：${businessStageTitle(target)}。`, "info");
}

function businessStageTitle(stage) {
  return {
    prep: "材料准备报告",
    source: "来源网站确认",
    draft: "字段草案确认",
    acceptance: "蒸馏结果验收",
  }[stage] || "材料准备报告";
}

function transitionBusinessStage(stage, message) {
  setBusinessLoading(true, message || "系统正在处理，请稍候...");
  window.setTimeout(() => {
    setBusinessLoading(false);
    setBusinessStage(stage);
  }, 450);
}

function businessFeedbackDimensions(rawFeedback) {
  const raw = String(rawFeedback || "");
  const dimensions = [];
  const push = (dimension, label) => dimensions.push({ dimension, label });
  const has = (pattern) => pattern.test(raw);
  if (has(/太简单|容易|偏简单|难度低|难度偏低|浅/)) push("difficulty_too_low", "难度偏低");
  if (has(/太难|难度高|难度偏高|看不懂/)) push("difficulty_too_high", "难度偏高");
  if (has(/材料.*短|字数.*少|上下文.*少|语境.*不够|材料短/)) push("material_too_short", "材料偏短");
  if (has(/材料.*不像|不像原文|自然原文|来源.*不自然/)) push("source_like_material_weak", "材料不够像自然原文");
  if (has(/干扰|迷惑|选项.*直给|太直给|错项.*弱/)) push("distractor_weakness", "干扰项弱");
  if (has(/解析|说服力|理由不够/)) push("explanation_weak", "解析说服力弱");
  if (has(/不像真题|风格不对|题感不对/)) push("exam_style_mismatch", "不像真题");
  if (has(/题库|答案解析|教培|刷题/)) push("question_bank_style_contamination", "疑似题库化污染");
  return Array.from(new Map(dimensions.map((item) => [item.dimension, item])).values());
}

function businessSelectLabel(id) {
  const node = $(id);
  if (!node) return "";
  return node.selectedOptions?.[0]?.textContent || node.value || "";
}

function businessSourceDecisions() {
  return Array.from(document.querySelectorAll(".business-source-card")).map((card) => {
    const select = card.querySelector(".business-source-decision");
    return {
      source_key: card.getAttribute("data-source-key") || "",
      source_title: card.querySelector(".business-source-title")?.textContent?.trim() || "",
      decision: select?.value || "defer",
      decision_label: select?.selectedOptions?.[0]?.textContent || "待定",
      material_excerpt: card.querySelector(".business-material-excerpt")?.textContent?.trim() || "",
      linked_questions: Array.from(card.querySelectorAll(".business-linked-question")).map((item) => item.textContent.trim()).filter(Boolean),
    };
  });
}

function businessUserJudgments() {
  return {
    source_usefulness: $("businessSourceUsefulness")?.value || "unknown",
    source_usefulness_label: businessSelectLabel("businessSourceUsefulness"),
    source_review_note: $("businessSourceReviewText")?.value?.trim() || "",
    manual_source_url: $("businessManualSourceUrl")?.value?.trim() || "",
    manual_source_text_excerpt: $("businessManualSourceText")?.value?.trim() || "",
    source_decisions: businessSourceDecisions(),
    draft_readiness: $("businessDraftReadiness")?.value || "unknown",
    draft_readiness_label: businessSelectLabel("businessDraftReadiness"),
    generated_question_judgment: $("businessGeneratedQuestionJudgment")?.value || "unknown",
    generated_question_judgment_label: businessSelectLabel("businessGeneratedQuestionJudgment"),
    generated_question_note: $("businessGeneratedQuestionText")?.value?.trim() || "",
    rerun_suggestion: $("businessRerunSuggestionText")?.value?.trim() || "",
    landing_decision: $("businessLandingDecision")?.value || "unknown",
    landing_decision_label: businessSelectLabel("businessLandingDecision"),
  };
}

function businessHumanGateTranslation(gateSummary, feedbackDimensions, userJudgments = {}) {
  const reasons = [];
  const nextSteps = [];
  const status = gateSummary.status || "blocked";
  if (status === "blocked" || gateSummary.material_quality_regression_status === "blocked") reasons.push("材料证据还不足以支撑正式落位。");
  if (gateSummary.source_gold_alignment_status && !["aligned", "partial"].includes(gateSummary.source_gold_alignment_status)) reasons.push("来源正文和真题材料的对齐还需要人工复核。");
  if (gateSummary.verified_original_source_count > 0) reasons.push("输入里出现已验证原文计数，但前端不能确认原文。");
  if (feedbackDimensions.some((item) => item.dimension === "material_too_short")) reasons.push("用户反馈指出材料偏短，需要更完整的上下文。");
  if (feedbackDimensions.some((item) => item.dimension === "distractor_weakness")) reasons.push("用户反馈指出干扰项弱，后续需要用材料机制支撑选项设计。");
  if (userJudgments.source_usefulness === "question_bank") reasons.push("用户判断当前来源像题库或解析页，不能作为材料来源继续推进。");
  if (userJudgments.source_usefulness === "irrelevant") reasons.push("用户判断当前来源无关，需要淘汰或重新找来源。");
  if (userJudgments.source_usefulness === "similar_only") reasons.push("用户判断当前来源只能算相似材料，不能当作已确认原文。");
  if (userJudgments.draft_readiness === "needs_rename") reasons.push("业务字段还需要命名或改名。");
  if (userJudgments.draft_readiness === "needs_split") reasons.push("当前题包可能需要拆成多个题型后再蒸馏。");
  if (userJudgments.draft_readiness === "needs_more_material") reasons.push("材料字段还不够，暂不适合进入稳定蒸馏。");
  if (userJudgments.generated_question_judgment === "not_usable") reasons.push("用户判断生成题不能用，说明题卡或材料机制还没有稳定。");
  if (userJudgments.generated_question_judgment === "needs_edit") reasons.push("用户判断生成题需要修改，还不能直接进入正式落位。");
  if (userJudgments.landing_decision === "hold_material") reasons.push("用户选择先补材料来源或正文。");
  if (userJudgments.landing_decision === "hold_quality") reasons.push("用户选择先改生成质量。");
  if (userJudgments.landing_decision === "reject_now") reasons.push("用户选择暂不落位。");
  if (!reasons.length) reasons.push("主要证据已经较完整，但仍需要人工复核。");
  if (gateSummary.source_text_evidence_status !== "available") nextSteps.push("补充更完整的来源正文，不要用题库页代替原文。");
  if (["question_bank", "irrelevant"].includes(userJudgments.source_usefulness)) nextSteps.push("重新选择候选来源，优先使用可靠文章页或机构 / 媒体原文。");
  if (["not_usable", "needs_edit"].includes(userJudgments.generated_question_judgment)) nextSteps.push("把生成题问题记录为反馈证据，再重新试生成小样本。");
  if (userJudgments.rerun_suggestion) nextSteps.push(`重跑建议：${userJudgments.rerun_suggestion}`);
  nextSteps.push("人工确认来源与真题材料的对齐关系，区分原文候选和相似材料。");
  nextSteps.push("重新跑材料质量回归和 readiness gate。");
  const headline =
    userJudgments.landing_decision === "approve_review" && userJudgments.generated_question_judgment === "usable"
      ? "可以进入正式化送审，但仍不能自动写回。"
      : userJudgments.landing_decision === "reject_now"
        ? "用户已选择暂不落位。"
        : userJudgments.generated_question_judgment === "not_usable"
          ? "当前生成题不能用，不能正式落位。"
          : userJudgments.source_usefulness === "question_bank" || userJudgments.source_usefulness === "irrelevant"
            ? "当前来源不能支撑落位。"
            : status === "material_card_review_ready"
              ? "可以进入材料卡人工审阅，但还不能正式写回。"
              : status === "proto_ready"
                ? "可以继续原型试跑，但还不能正式落位。"
                : "当前不能正式落位。";
  return { headline, reasons, nextSteps };
}

function updateBusinessPrepReport(preview) {
  const family = preview.family_context || {};
  const pack = preview.question_pack_payload || {};
  const files = Array.isArray(pack.files) ? pack.files : [];
  const sampleCount = Number(pack.sample_count || 0) || (Array.isArray(pack.samples) ? pack.samples.length : 0) || Number(pack.file_count || 0);
  const manualRequired = Number(pack.manual_required_file_count || 0) || files.filter((item) => item.requires_human_review || ["manual_required", "degraded"].includes(item.status)).length;
  $("businessPrepReport").innerHTML = `
    <h3>题包准备报告</h3>
    <ul>
      <li>题目 / 文件数量：${escapeHtml(String(sampleCount || "待系统解析"))}</li>
      <li>母族：${escapeHtml(family.mother_family_id || "需要识别")}</li>
      <li>叶族：${escapeHtml(family.leaf_label || "需要业务手工命名")}</li>
      <li>需要人工复核文件：${escapeHtml(String(manualRequired))}</li>
      <li>是否需要业务命名：${family.leaf_label === "需要业务命名" ? "是" : "否"}</li>
    </ul>
  `;
}

function updateBusinessSourceSiteList(preview) {
  const gate = preview.gate_payload || {};
  const candidates = gate.source_candidates || gate.candidates || gate.reviewed_candidates || [];
  const cards = Array.isArray(candidates) && candidates.length
    ? candidates.slice(0, 8).map((item, index) => {
      const title = item.domain || item.url || item.title || `候选来源 ${index + 1}`;
      const risk = item.source_risk || item.risk || "unknown";
      const materialExcerpt =
        item.material_excerpt ||
        item.text_excerpt ||
        item.source_text_excerpt ||
        item.restored_human_material ||
        item.context_window ||
        item.snippet ||
        "暂无可读材料片段；需要补 source_text_evidence。";
      const questions = []
        .concat(item.linked_questions || [])
        .concat(item.questions || [])
        .concat(item.sample_questions || [])
        .concat(item.sample_id ? [{ sample_id: item.sample_id, stem: item.stem || item.query || "" }] : [])
        .filter(Boolean);
      const questionRows = questions.length
        ? questions.slice(0, 5).map((question) => {
          const sampleId = typeof question === "string" ? question : question.sample_id || question.id || "未命名题目";
          const stem = typeof question === "string" ? "" : question.stem || question.question || question.title || "";
          return `<li class="business-linked-question"><strong>${escapeHtml(sampleId)}</strong>${stem ? `：${escapeHtml(stem)}` : ""}</li>`;
        }).join("")
        : `<li class="business-linked-question">暂未绑定具体题目，需回到来源候选结果补 sample_id。</li>`;
      const defaultDecision = risk === "question_bank_like" || risk === "exam_training_like" ? "reject" : "defer";
      return `
        <div class="source-review-card business-source-card" data-source-key="${escapeHtml(title)}">
          <div>
            <h3 class="source-review-title business-source-title">${escapeHtml(title)}</h3>
            <span class="source-risk-pill ${defaultDecision === "reject" ? "is-risky" : ""}">${escapeHtml(risk)}</span>
            <div class="distill-detail-box" style="margin-top:12px;">
              <strong>材料片段 / 主题摘要</strong>
              <div class="business-material-excerpt">${escapeHtml(materialExcerpt)}</div>
            </div>
            <details style="margin-top:12px;">
              <summary>查看关联题目</summary>
              <ul class="distill-note-list" style="margin-top:8px;">${questionRows}</ul>
            </details>
          </div>
          <label class="distill-field">
            <span>来源操作</span>
            <select class="business-source-decision">
              <option value="adopt" ${defaultDecision === "adopt" ? "selected" : ""}>采用</option>
              <option value="reject" ${defaultDecision === "reject" ? "selected" : ""}>不采用</option>
              <option value="defer" ${defaultDecision === "defer" ? "selected" : ""}>待定</option>
            </select>
            <div class="distill-help">采用只表示后续继续审查；不确认原文、不抓正文、不入库。</div>
          </label>
        </div>`;
    }).join("")
    : `
      <div class="distill-help">
        暂无候选网址。请先尝试重新搜索；如果仍然没有结果，可以在下方人工补充来源网址或材料片段，作为后续 source_text_evidence 的待审证据。
      </div>`;
  $("businessSourceSiteList").innerHTML = `${cards}<div class="distill-help" style="margin-top:10px;">业务只判断这些来源是否有用，不确认原文。</div>`;
}

function updateBusinessDraftFields(preview) {
  const features = preview.core_features?.length ? preview.core_features : ["需要上下文语境", "需要错项机制", "需要材料证据"];
  const material = preview.gate_payload?.material_card_draft?.material_requirements || {};
  const materialFields = []
    .concat(material.must_contain || [])
    .concat(material.document_genre_candidates || [])
    .concat(material.material_structure_label_candidates || []);
  $("businessInitialBusinessFields").innerHTML = features.slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("businessInitialMaterialFields").innerHTML = (materialFields.length ? materialFields : ["来源正文", "上下文窗口", "可切片材料段"]).slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function buildBusinessModePreview() {
  const questionPack = parseBusinessJsonOrText($("businessQuestionPackText").value, "question_pack");
  const protocolEvidence = parseBusinessJsonOrText($("businessProtocolEvidenceJson").value, "protocol_evidence");
  const gateEvidence = parseBusinessJsonOrText($("businessGateEvidenceJson").value, "gate_evidence");
  const familyContext = businessFamilyContext(questionPack, protocolEvidence, gateEvidence);
  const features = businessCandidateFeatures(protocolEvidence, gateEvidence);
  const feedbackDimensions = businessFeedbackDimensions($("businessUserFeedbackText").value);
  const gateSummary = businessGateEvidenceSummary(gateEvidence);
  const userJudgments = businessUserJudgments();
  const humanGate = businessHumanGateTranslation(gateSummary, feedbackDimensions, userJudgments);
  const preview = {
    preview_version: "v2",
    mode: "business_stage_workflow",
    status: gateSummary.status || "blocked",
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    family_context: familyContext,
    input_support: {
      upload_preview_formats: ["pdf", "csv", "doc", "docx", "json", "jsonl", "md", "markdown", "txt", "xlsx"],
      best_effort_formats: ["pdf", "doc"],
      structured_formats: ["json", "jsonl", "csv", "xlsx"],
    },
    question_pack_payload: questionPack.payload,
    gate_payload: gateEvidence.payload,
    package_summary: questionPack.summary,
    protocol_available: protocolEvidence.kind !== "missing",
    gate_summary: gateSummary,
    core_features: features,
    user_judgments: userJudgments,
    feedback_dimensions: feedbackDimensions,
    human_gate: humanGate,
    limits: ["业务模式只收集用户判断，不正式写回", "技术 JSON 保留在详情区", "确认送审不等于 executor approval"],
  };
  preview.card_family_report_markdown = buildBusinessCardFamilyMarkdown(preview);
  return preview;
}

function buildBusinessCardFamilyMarkdown(preview) {
  const family = preview.family_context || {};
  const features = preview.core_features?.length ? preview.core_features : ["尚需要更多样本和人工确认。"];
  const feedback = preview.feedback_dimensions || [];
  const judgments = preview.user_judgments || {};
  const lines = [
    "# 卡族草案报告",
    "",
    `- 系统识别的母族：${family.mother_family_id || "unknown"}`,
    `- 系统识别的子族：${family.child_family_id || "unknown"}`,
    `- 叶族 / 业务标签：${family.leaf_label || "unknown"}`,
    "",
    "## 业务判断",
    `- 来源有没有用：${judgments.source_usefulness_label || "未判断"}`,
    `- 字段草案是否可蒸馏：${judgments.draft_readiness_label || "未判断"}`,
    `- 生成题能不能用：${judgments.generated_question_judgment_label || "未判断"}`,
    `- 是否允许送审：${judgments.landing_decision_label || "未判断"}`,
    "",
    "## 核心特征",
    ...features.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## 当前状态",
    `- 题型 proto / 补丁证据：${preview.protocol_available ? "已存在" : "不足"}`,
    `- 用户反馈：${feedback.length ? feedback.map((item) => item.label).join(" / ") : "暂无结构化反馈"}`,
    `- 材料线状态：${preview.gate_summary.material_quality_regression_status || "unknown"}`,
    "- 是否可正式写回：否",
    "",
    "## 业务结论",
    preview.human_gate.headline,
    "",
    "## 下一步",
    ...preview.human_gate.nextSteps.map((item, index) => `${index + 1}. ${item}`),
    "",
    "> 这是业务可读草案，不是正式 material_card / question_card 写回。",
  ];
  return lines.join("\n");
}

function renderBusinessModePreview(preview) {
  const reasons = preview.human_gate.reasons.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const nextSteps = preview.human_gate.nextSteps.map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const features = (preview.core_features || []).map((item, index) => `<li>${index + 1}. ${escapeHtml(item)}</li>`).join("");
  const feedback = (preview.feedback_dimensions || []).map((item) => `<span class="distill-badge distill-badge-info">${escapeHtml(item.label)}</span>`).join("");
  const judgments = preview.user_judgments || {};
  updateBusinessPrepReport(preview);
  updateBusinessSourceSiteList(preview);
  updateBusinessDraftFields(preview);
  $("businessHumanSummary").innerHTML = `
    <h3>蒸馏结果报告</h3>
    <div class="business-status-pill">${escapeHtml(preview.human_gate.headline)}</div>
    <h3 style="margin-top:14px;">业务判断</h3>
    <ul>
      <li>来源：${escapeHtml(judgments.source_usefulness_label || "未判断")}</li>
      <li>字段草案：${escapeHtml(judgments.draft_readiness_label || "未判断")}</li>
      <li>生成题：${escapeHtml(judgments.generated_question_judgment_label || "未判断")}</li>
      <li>送审：${escapeHtml(judgments.landing_decision_label || "未判断")}</li>
    </ul>
    <h3 style="margin-top:14px;">原因</h3>
    <ol>${reasons}</ol>
    <h3>下一步</h3>
    <ol>${nextSteps}</ol>
  `;
  $("businessCardFamilySummary").innerHTML = `
    <h3>示例样题与卡族草案</h3>
    <div>系统识别：${escapeHtml(preview.family_context.mother_family_id)} / ${escapeHtml(preview.family_context.child_family_id)} / ${escapeHtml(preview.family_context.leaf_label)}</div>
    <h3 style="margin-top:14px;">核心特征</h3>
    <ol>${features || `<li>尚需更多 evidence。</li>`}</ol>
    <h3>用户反馈</h3>
    <div class="distill-badge-row">${feedback || `<span class="distill-help">暂无结构化反馈</span>`}</div>
    <h3 style="margin-top:14px;">示例样题</h3>
    <ol><li>示例题 1：等待 proto trial 输出。</li><li>示例题 2：等待 proto trial 输出。</li></ol>
  `;
  $("businessCardFamilyReportText").value = preview.card_family_report_markdown;
  $("businessModePreviewJson").value = prettyJson(preview);
}

function handleGenerateBusinessModeReport() {
  try {
    setBusinessLoading(true, "正在生成蒸馏验收报告...");
    window.setTimeout(() => {
      const preview = buildBusinessModePreview();
      state.businessModePreview = preview;
      renderBusinessModePreview(preview);
      setBusinessLoading(false);
      setPageStatus("已生成业务蒸馏验收报告。技术 JSON 已收进详情区。", "info");
    }, 450);
  } catch (error) {
    setBusinessLoading(false);
    setPageStatus(error.message, "error");
  }
}

async function handleCopyBusinessModeReport() {
  const target = $("businessCardFamilyReportText");
  const text = target?.value || "";
  if (!text.trim()) {
    setPageStatus("请先生成业务报告。", "error");
    return;
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    target.select();
    document.execCommand("copy");
  }
  setPageStatus("已复制业务报告。", "info");
}

function handleBusinessFinalDecision(decision) {
  if (decision === "approve") {
    $("businessLandingDecision").value = "approve_review";
    if ($("businessGeneratedQuestionJudgment").value === "unknown") $("businessGeneratedQuestionJudgment").value = "usable";
  } else if (decision === "defer") {
    $("businessLandingDecision").value = "hold_material";
  } else if (decision === "rerun") {
    $("businessLandingDecision").value = "hold_quality";
  }
  handleGenerateBusinessModeReport();
}

function handleFillBusinessModeExample() {
  $("businessQuestionPackText").value = "题包准备报告：共 8 题；系统识别为词语理解 / 实词语境义；叶族名建议为“实词语境义”；PDF 解析正常，仍需业务确认命名。";
  $("businessProtocolEvidenceJson").value = prettyJson({
    family_context: { mother_family_id: "word_usage", child_family_id: "word_usage_content_word", leaf_label: "实词语境义" },
    candidate_axes: [{ name: "依赖上下文语境" }, { name: "错项来自局部词义误读" }, { name: "材料需要足够前后文" }],
  });
  $("businessGateEvidenceJson").value = prettyJson({
    status: "blocked",
    source_candidates: [
      {
        domain: "people.com.cn",
        source_risk: "low",
        material_excerpt: "在现代社会治理中，公共服务需要在长期实践中不断沉淀经验，把零散做法转化为可复制的制度安排。",
        linked_questions: [
          { sample_id: "sample-1", stem: "结合文段，判断“沉淀”在文中的含义。" },
          { sample_id: "sample-3", stem: "下列对加点词理解正确的是哪一项？" },
        ],
      },
      {
        domain: "nju.edu.cn",
        source_risk: "low",
        material_excerpt: "面对外部环境变化，个体和组织都需要持续调适自身结构，使原有经验与新的任务要求重新匹配。",
        linked_questions: [{ sample_id: "sample-2", stem: "文中“调适”一词最接近的含义是？" }],
      },
      {
        domain: "某公考题库站",
        source_risk: "question_bank_like",
        material_excerpt: "页面主要展示题干、选项、正确答案和答案解析，缺少可作为自然原文的连续材料。",
        linked_questions: [{ sample_id: "sample-4", stem: "该题疑似来自解析页转载。" }],
      },
    ],
    material_evidence_summary: {
      source_text_evidence_status: "available",
      source_gold_alignment_status: "needs_human_review",
      material_quality_regression_status: "blocked",
      verified_original_source_count: 0,
      ready_for_material_card_review: false,
      blocking_issues: ["source/gold alignment weak", "material quality regression blocked"],
    },
    material_card_draft: { material_requirements: { must_contain: ["上下文窗口", "语境解释线索"], document_genre_candidates: ["评论", "科普", "新闻"] } },
  });
  $("businessSourceUsefulness").value = "similar_only";
  $("businessSourceReviewText").value = "这几个网址主题相关，可以继续看，但还不能当已确认原文。";
  $("businessDraftReadiness").value = "needs_more_material";
  $("businessGeneratedQuestionJudgment").value = "needs_edit";
  $("businessGeneratedQuestionText").value = "生成题有题感，但材料偏短，错项还不够迷惑。";
  $("businessRerunSuggestionText").value = "材料加长一点，干扰项更贴近原词表层义。";
  $("businessLandingDecision").value = "hold_material";
  $("businessUserFeedbackText").value = "太简单，材料也太短，干扰项不够迷惑，不像真题。";
  renderBusinessModePreview(buildBusinessModePreview());
  setBusinessStage("prep", { silent: true });
  setPageStatus("已填入四步业务流程示例。", "info");
}

async function handleBusinessQuestionPackFile(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file, file.name));
  setBusinessLoading(true, "正在解析题包并生成材料准备报告...");
  try {
    const response = await fetch("/api/v1/distill/question-pack/preview", { method: "POST", body: formData, headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.detail || payload?.error?.message || "question pack preview failed");
    $("businessQuestionPackText").value = prettyJson(payload);
    const preview = buildBusinessModePreview();
    state.businessModePreview = preview;
    renderBusinessModePreview(preview);
    setBusinessLoading(false);
    setPageStatus(`题包准备报告完成：已解析 ${Number(payload.parsed_file_count || 0)} 个文件，${Number(payload.manual_required_file_count || 0)} 个需要人工复核。`, "info");
  } catch (error) {
    setBusinessLoading(false);
    const textFiles = files.filter((file) => /\.(json|jsonl|csv|txt|md|markdown)$/i.test(file.name));
    if (!textFiles.length) {
      $("businessQuestionPackText").value = prettyJson({ preview_version: "v1", status: "manual_required", files: files.map((file) => ({ file_name: file.name, size_bytes: file.size, status: "upload_preview_failed" })), error: error.message });
      renderBusinessModePreview(buildBusinessModePreview());
      setPageStatus("题包预览接口不可用，且所选文件不是浏览器可直读文本格式。", "error");
      return;
    }
    const texts = await Promise.all(textFiles.map((file) => file.text()));
    $("businessQuestionPackText").value = texts.join("\n\n");
    renderBusinessModePreview(buildBusinessModePreview());
    setPageStatus("后端预览接口不可用，已降级读取文本型题包。", "info");
  }
}

function collectAxisDecisionPayload() {
  const discovery = state.bootstrapDiscovery || parseJsonField($("bootstrapDiscoveryJson").value, "启动发现 JSON", {});
  const manifest = parseJsonField($("axisManifestJson").value, "清单 JSON", {});
  const sourceRows = axisSourceRows(discovery);
  const decisions = Array.from(document.querySelectorAll(".axis-decision-row")).map((row) => {
    const source = sourceRows[Number(row.getAttribute("data-axis-index") || 0)] || {};
    return {
      source_type: source.source_type,
      source_id: source.source_id,
      action: row.querySelector(".axis-action")?.value || "keep",
      target_name: row.querySelector(".axis-name")?.value.trim() || source.source_id,
      target_layer: row.querySelector(".axis-target")?.value || defaultAxisTarget("keep", source.source_type),
      rationale: row.querySelector(".axis-rationale")?.value.trim() || "",
    };
  });
  return {
    decision_version: "v1",
    reviewer: $("axisPatchAuthor").value.trim() || "distill_demo_user",
    proto_family_label: manifest.mother_family_id || discovery?.proto_mother_family?.label || "",
    decisions,
  };
}

function buildAxisConfirmationArtifact(manifest, discovery, decisionPayload) {
  const knownSources = new Set(axisSourceRows(discovery).map((row) => `${row.source_type}:${row.source_id}`));
  const confirmed = [];
  const rejected = [];
  const warnings = [];
  (decisionPayload.decisions || []).forEach((decision) => {
    const key = `${decision.source_type}:${decision.source_id}`;
    if (!knownSources.has(key)) {
      warnings.push(`已忽略未知来源：${key}`);
      rejected.push({ ...decision, status: "rejected", reason: "unknown_source" });
      return;
    }
    if (!AXIS_CONFIRM_ACTIONS.includes(decision.action)) {
      warnings.push(`已忽略不支持的动作：${decision.action}`);
      rejected.push({ ...decision, status: "rejected", reason: "unsupported_action" });
      return;
    }
    if (!AXIS_CONFIRMING_ACTIONS.has(decision.action)) {
      rejected.push({
        source_type: decision.source_type,
        source_id: decision.source_id,
        decision: decision.action,
        status: decision.action === "downgrade_to_note" ? "deferred" : "rejected",
        rationale: decision.rationale || "",
      });
      return;
    }
    confirmed.push({
      source_type: decision.source_type,
      source_id: decision.source_id,
      decision: decision.action,
      confirmed_name: decision.target_name || decision.source_id,
      target_layer: decision.target_layer || defaultAxisTarget(decision.action, decision.source_type),
      status: "proto_confirmed",
      formal: false,
      rationale: decision.rationale || "",
    });
  });
  return {
    confirmation_version: "v1",
    enabled: true,
    source: "distill_demo_axis_confirmation",
    status: confirmed.length ? "proto_confirmed" : "no_confirmed_axes",
    formalized: false,
    promotion_allowed: false,
    reviewer: decisionPayload.reviewer || null,
    proto_mother_family: {
      label: decisionPayload.proto_family_label || discovery?.proto_mother_family?.label || manifest.mother_family_id || "",
      source_label: discovery?.proto_mother_family?.label || null,
      status: confirmed.length ? "proto_confirmed" : "hypothesis",
      formal: false,
    },
    source_artifacts: {
      bootstrap_discovery: "bootstrap_discovery.json",
      manifest_job_id: manifest.job_id || null,
    },
    axis_decisions: confirmed,
    rejected_or_deferred: rejected,
    warnings,
    limits: [
      "原型确认不是正式化。",
      "已确认候选轴默认不等于正式字段。",
      "已确认候选轴不会自动写入正式题卡。",
      "正式补丁草案仍需要单独生成，并经过人工审核。",
    ],
  };
}

function patchScopeKey(target, manifest, family) {
  const child = manifest.child_family_id || "proto_leaf";
  if (target === "business_feature_card") return `proto.${family}.${child}.feature.v0`;
  if (target === "prompt_assets") return `proto_${family}_${child}_prompt`;
  if (target === "validator_contract") return `proto.${family}.${child}.validator.v0`;
  if (target === "runtime_mapping") return `proto.${family}.${child}.runtime.v0`;
  if (target === "material_mapping") return `proto.${family}.${child}.material_mapping.v0`;
  if (target === "signal_layer") return `proto.${family}.${child}.signal.v0`;
  return `proto.${family}.${child}.${target}.v0`;
}

function buildFormalPatchDraftArtifact(manifest, confirmation) {
  const decisions = (confirmation.axis_decisions || []).filter((item) => item.status === "proto_confirmed");
  const family = confirmation.proto_mother_family?.label || manifest.mother_family_id || "proto";
  const groups = {};
  decisions.forEach((decision) => {
    const target = decision.target_layer || "business_feature_card";
    if (!AXIS_DRAFT_TARGETS.includes(target)) return;
    groups[target] = groups[target] || [];
    groups[target].push(decision);
  });
  const targetPatches = Object.keys(groups)
    .sort()
    .map((target) => ({
      target,
      scope_key: patchScopeKey(target, manifest, family),
      draft_status: "draft_only",
      writeback_allowed: false,
      formalized: false,
      patch: {
        experimental: true,
        formalized: false,
        source: "axis_confirmation",
        proto_family: family,
        proto_child_family: manifest.child_family_id || null,
        leaf_label: manifest.leaf_label || null,
        proto_confirmed_decisions: groups[target].map((decision) => ({
          source_type: decision.source_type,
          source_id: decision.source_id,
          confirmed_name: decision.confirmed_name,
          decision: decision.decision,
          status: "proto_confirmed",
          formal: false,
          rationale: decision.rationale || "",
        })),
      },
    }));
  return {
    draft_version: "v1",
    enabled: true,
    source: "axis_confirmation",
    status: targetPatches.length ? "draft_only" : "blocked",
    writeback_allowed: false,
    formalized: false,
    promotion_allowed: false,
    proto_family: family,
    proto_child_family: manifest.child_family_id || null,
    leaf_label: manifest.leaf_label || null,
    target_patches: targetPatches,
    warnings: targetPatches.length ? [] : ["没有可用于生成草案的原型确认候选轴决策。"],
    limits: [
      "这个文件是补丁草案，不是正式配置变更。",
      "写回开关保持关闭。",
      "正式化状态保持关闭。",
      "每个目标补丁仍然必须经过人工审核、补丁记录和沉淀流程。",
      "没有发生正式题卡写回。",
    ],
  };
}

function formatTargetFile(template, family, child) {
  return String(template || "card_specs/proto/{proto_family}_{proto_child_family}.yaml")
    .replaceAll("{proto_family}", family)
    .replaceAll("{proto_child_family}", child);
}

function buildFormalWritebackPlanArtifact(draft, reviewer) {
  const family = draft.proto_family || "proto";
  const child = draft.proto_child_family || "proto_leaf";
  const targetPatches = Array.isArray(draft.target_patches) ? draft.target_patches : [];
  const writebackItems = targetPatches.map((targetPatch) => {
    const decisions = targetPatch.patch?.proto_confirmed_decisions || [];
    const targetFile = formatTargetFile(WRITEBACK_TARGET_FILES[targetPatch.target], family, child);
    return {
      target: targetPatch.target,
      scope_key: targetPatch.scope_key || null,
      target_file: targetFile,
      operation: "append_or_create_preview",
      writeback_allowed: false,
      requires_explicit_approval: true,
      proposed_additions: decisions.map((decision) => ({
        name: decision.confirmed_name || decision.source_id || "",
        source_id: decision.source_id || "",
        decision: decision.decision || "",
        summary: decision.rationale || "Proto-confirmed axis addition.",
        status: "preview_only",
      })),
      prompt_guards:
        targetPatch.target === "prompt_assets"
          ? decisions.map((decision) => `Respect proto-confirmed axis \`${decision.confirmed_name || decision.source_id}\` when generating and explaining the item.`)
          : [],
      validator_candidates:
        targetPatch.target === "validator_contract"
          ? decisions.map((decision) => `check_proto_${decision.confirmed_name || decision.source_id}_evidence`)
          : [],
      shared_config_touch: SHARED_WRITEBACK_TARGETS.has(targetPatch.target),
      rollback: `从 ${targetFile} 中移除作用域键为 ${targetPatch.scope_key || "<unknown>"} 的新增内容。`,
    };
  });
  const shared = writebackItems.some((item) => item.shared_config_touch);
  return {
    plan_version: "v1",
    source: "formal_patch_draft",
    status: "preview_only",
    writeback_allowed: false,
    requires_explicit_approval: true,
    reviewer: reviewer || null,
    proto_family: family,
    proto_child_family: child,
    leaf_label: draft.leaf_label || null,
    writeback_items: writebackItems,
    legacy_family_impact: {
      sentence_fill: shared ? "requires_regression" : "no_direct_file_touch_planned",
      sentence_order: shared ? "requires_regression" : "no_direct_file_touch_planned",
      center_understanding: shared ? "requires_regression" : "no_direct_file_touch_planned",
      shared_config_touch: shared,
      note: "共享配置目标即使只是预览，也必须在真正写回前做回归。",
    },
    regression_requirements: [
      "写回前运行语句填空回归。",
      "写回前运行语句排序回归。",
      "写回前运行中心理解回归。",
      "写回前运行词语理解原型路由回归。",
    ],
    rollback_note:
      "这个计划不会改动文件。若之后批准写回，回滚时应还原写回项列出的精确文件，或应用差异预览中的反向补丁。",
    limits: [
      "这是写回预览，不是写回执行。",
      "写回开关保持关闭。",
      "任何正式文件变更前都必须显式批准。",
      "这个计划不会修改正式题卡、提示资产、校验器、运行映射或生题文件。",
    ],
  };
}

function renderFormalWritebackDiff(plan) {
  const lines = [];
  lines.push("# 正式写回差异预览", "", "> 仅用于预览。没有任何文件被改动。", "");
  lines.push(`- 状态：\`${plan.status}\``);
  lines.push(`- 是否允许写回：\`${plan.writeback_allowed}\``);
  lines.push(`- 是否需要显式批准：\`${plan.requires_explicit_approval}\``);
  lines.push(`- 原型母族：\`${plan.proto_family}\``);
  lines.push(`- 原型子族：\`${plan.proto_child_family}\``, "", "## 文件", "");
  (plan.writeback_items || []).forEach((item) => {
    lines.push(`- \`${item.target}\` -> \`${item.target_file}\` (${item.operation})`);
  });
  if (!plan.writeback_items?.length) {
    lines.push("- 没有拟写回的目标文件。");
  }
  lines.push("", "## 拟新增内容", "");
  (plan.writeback_items || []).forEach((item) => {
    lines.push(`### ${AXIS_TARGET_LABELS[item.target] || item.target}`, "", `文件：\`${item.target_file}\``, "");
    (item.proposed_additions || []).forEach((addition) => {
      lines.push(`- \`${addition.name}\`: ${addition.summary}`);
    });
    if (item.prompt_guards?.length) {
      lines.push("", "提示保护：");
      item.prompt_guards.forEach((guard) => lines.push(`- ${guard}`));
    }
    if (item.validator_candidates?.length) {
      lines.push("", "校验候选：");
      item.validator_candidates.forEach((candidate) => lines.push(`- \`${candidate}\``));
    }
    lines.push("");
  });
  const impact = plan.legacy_family_impact || {};
  lines.push("## 旧题型影响", "");
  lines.push(`- sentence_fill: \`${impact.sentence_fill}\``);
  lines.push(`- sentence_order: \`${impact.sentence_order}\``);
  lines.push(`- center_understanding: \`${impact.center_understanding}\``);
  lines.push(`- 是否触碰共享配置：\`${impact.shared_config_touch}\``, "", "## 回滚", "", plan.rollback_note || "没有回滚说明。", "", "## 回归要求", "");
  (plan.regression_requirements || []).forEach((item) => lines.push(`- ${item}`));
  lines.push("");
  return lines.join("\n");
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message =
      typeof payload === "string"
        ? payload
        : payload?.error?.message || payload?.detail || JSON.stringify(payload, null, 2);
    throw new Error(String(message));
  }
  return payload;
}

function setPageStatus(message, type = "info") {
  const node = $("pageStatus");
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    node.className = "distill-status distill-status-info";
    return;
  }
  node.hidden = false;
  node.textContent = message;
  node.className = `distill-status ${type === "error" ? "distill-status-error" : "distill-status-info"}`;
}

function withButtonLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
}

function formatTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("zh-CN", { hour12: false });
  } catch {
    return value;
  }
}

function fitBadgeClass(fitBand) {
  if (fitBand === "high") return "distill-badge distill-badge-good";
  if (fitBand === "medium") return "distill-badge distill-badge-warn";
  return "distill-badge distill-badge-info";
}

function renderDatasets() {
  const root = $("datasetsList");
  if (!state.datasets.length) {
    root.innerHTML = `<div class="distill-empty">还没有样本集。先在左边建一套数据，会话才有稳定边界。</div>`;
    return;
  }
  root.innerHTML = state.datasets
    .map((item) => {
      const activeClass = item.dataset_id === state.selectedDatasetId ? " is-active" : "";
      return `
        <article class="distill-card${activeClass}" data-dataset-id="${escapeHtml(item.dataset_id)}">
          <h3>${escapeHtml(item.title || item.dataset_id)}</h3>
          <div class="distill-badge-row" style="margin-bottom:10px;">
            <span class="distill-badge distill-badge-info">${escapeHtml(item.split_mode || "manual")}</span>
            <span class="distill-badge distill-badge-info">${escapeHtml(item.question_type || "-")}</span>
          </div>
          <div class="distill-meta">
            <div class="distill-meta-box">
              <strong>样本数量</strong>
              <div>${escapeHtml(item.sample_count ?? 0)}</div>
            </div>
            <div class="distill-meta-box">
              <strong>切分统计</strong>
              <div>${escapeHtml(JSON.stringify(item.split_counts || {}))}</div>
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  root.querySelectorAll("[data-dataset-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedDatasetId = node.getAttribute("data-dataset-id") || "";
      renderDatasets();
    });
  });
}

function renderSessions() {
  const root = $("sessionsList");
  if (!state.sessions.length) {
    root.innerHTML = `<div class="distill-empty">还没有蒸馏会话。样本集定好之后，在左边创建一条训练任务。</div>`;
    return;
  }
  root.innerHTML = state.sessions
    .map((item) => {
      const activeClass = item.session_id === state.selectedSessionId ? " is-active" : "";
      return `
        <article class="distill-card${activeClass}" data-session-id="${escapeHtml(item.session_id)}">
          <h3>${escapeHtml(item.title || item.session_id)}</h3>
          <div class="distill-badge-row" style="margin-bottom:10px;">
            <span class="distill-badge distill-badge-info">${escapeHtml(item.mode || "-")}</span>
            <span class="distill-badge distill-badge-info">${escapeHtml(item.status || "-")}</span>
          </div>
          <div class="distill-meta">
            <div class="distill-meta-box">
              <strong>绑定数据集</strong>
              <div>${escapeHtml(item.dataset_id || "-")}</div>
            </div>
            <div class="distill-meta-box">
              <strong>试验次数</strong>
              <div>${escapeHtml(item.run_count ?? 0)}</div>
            </div>
            <div class="distill-meta-box">
              <strong>题型标识</strong>
              <div>${escapeHtml(item.question_type || "-")}</div>
            </div>
            <div class="distill-meta-box">
              <strong>最近运行时间</strong>
              <div>${escapeHtml(formatTime(item.latest_run_at))}</div>
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  root.querySelectorAll("[data-session-id]").forEach((node) => {
    node.addEventListener("click", async () => {
      state.selectedSessionId = node.getAttribute("data-session-id") || "";
      renderSessions();
      await selectSession(state.selectedSessionId);
    });
  });
}

function renderRunDetail(run) {
  const root = $("runDetail");
  if (!run) {
    root.innerHTML = `<div class="distill-empty">先选中一条会话里的运行，或者刚跑完一轮试验后会自动切过来。</div>`;
    return;
  }

  const latestReview = run.latest_review;
  const latestPromotion = run.latest_promotion;
  const fitSummary = run.fit_summary || {};
  const firstSample = Array.isArray(run.sample_results) && run.sample_results.length ? run.sample_results[0] : null;
  const patchPreview = Array.isArray(run.patches) && run.patches.length ? run.patches[0] : null;
  const noteHtml = Array.isArray(fitSummary.notes) && fitSummary.notes.length
    ? `<ul class="distill-note-list">${fitSummary.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul>`
    : `<div class="distill-help">当前没有额外拟合备注。</div>`;
  const reviewHtml = latestReview
    ? `
      <div class="distill-detail-box">
        <strong>最新审核</strong>
        <div style="margin-bottom:8px;">
          <span class="distill-badge ${latestReview.verdict === "approved" ? "distill-badge-good" : latestReview.verdict === "rejected" ? "distill-badge-warn" : "distill-badge-info"}">
            ${escapeHtml(latestReview.verdict)}
          </span>
        </div>
        <div>审核人：${escapeHtml(latestReview.reviewer || "-")}</div>
        <div>允许沉淀：${escapeHtml(String(Boolean(latestReview.allow_promote)))}</div>
        <div>沉淀目标：${escapeHtml((latestReview.promotion_targets || []).join(", ") || "-")}</div>
        <div style="margin-top:8px;">摘要：${escapeHtml(latestReview.summary || "-")}</div>
        <div style="margin-top:8px;">原因：${escapeHtml(latestReview.reason || "-")}</div>
      </div>
    `
    : `<div class="distill-detail-box"><strong>最新审核</strong><div>这条 run 还没有人工结论。</div></div>`;
  const promotionHtml = latestPromotion
    ? `
      <div class="distill-detail-box">
        <strong>最新沉淀包</strong>
        <div style="margin-bottom:8px;">
          <span class="distill-badge distill-badge-good">${escapeHtml(latestPromotion.status || "就绪")}</span>
        </div>
        <div>沉淀人：${escapeHtml(latestPromotion.promoter || "-")}</div>
        <div>目标：${escapeHtml((latestPromotion.targets || []).join(", ") || "-")}</div>
        <div>补丁数：${escapeHtml((latestPromotion.patch_ids || []).length)}</div>
        <div style="margin-top:8px;">产物路径：${escapeHtml(latestPromotion.artifact_path || "-")}</div>
      </div>
    `
    : `<div class="distill-detail-box"><strong>最新沉淀包</strong><div>这条运行还没有生成沉淀包。</div></div>`;

  root.innerHTML = `
    <div class="distill-detail-box">
      <strong>当前运行</strong>
      <div class="distill-badge-row" style="margin-bottom:10px;">
        <span class="distill-badge distill-badge-info">第 ${escapeHtml(run.run_no)} 轮</span>
        <span class="distill-badge distill-badge-info">${escapeHtml(run.status || "-")}</span>
        <span class="${fitBadgeClass(fitSummary.fit_band)}">${escapeHtml(fitSummary.fit_band || "未知")}</span>
      </div>
      <div>运行编号：${escapeHtml(run.run_id)}</div>
      <div>会话编号：${escapeHtml(run.session_id)}</div>
      <div>切分集：${escapeHtml(run.split || "-")}</div>
      <div>标签：${escapeHtml(run.label || "-")}</div>
      <div>补丁数：${escapeHtml(run.patch_count ?? 0)}</div>
      <div>沉淀次数：${escapeHtml(run.promotion_count ?? 0)}</div>
      <div style="margin-top:8px;">假设：${escapeHtml(run.hypothesis || "-")}</div>
    </div>

    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>拟合摘要</strong>
        <div>题型一致：${escapeHtml(String(fitSummary.question_type_match))}</div>
        <div>业务子类一致：${escapeHtml(String(fitSummary.business_subtype_match))}</div>
        <div>答案一致：${escapeHtml(String(fitSummary.answer_match))}</div>
        <div>题干相似度：${escapeHtml(fitSummary.stem_similarity ?? "-")}</div>
        <div>解析相似度：${escapeHtml(fitSummary.analysis_similarity ?? "-")}</div>
        <div>选项重合度：${escapeHtml(fitSummary.option_overlap ?? "-")}</div>
        <div>材料相似度：${escapeHtml(fitSummary.material_similarity ?? "-")}</div>
      </div>
      ${reviewHtml}
    </div>

    <div class="distill-run-grid">
      ${promotionHtml}
      <div class="distill-detail-box">
        <strong>最新补丁</strong>
        ${
          patchPreview
            ? `
            <div>目标：${escapeHtml(patchPreview.target || "-")}</div>
            <div>标题：${escapeHtml(patchPreview.title || "-")}</div>
            <div>作用域键：${escapeHtml(patchPreview.scope_key || "-")}</div>
            <div style="margin-top:8px;">摘要：${escapeHtml(patchPreview.summary || "-")}</div>
          `
            : `<div>这条运行还没有补丁记录。</div>`
        }
      </div>
    </div>

    <div class="distill-detail-box">
      <strong>拟合备注</strong>
      ${noteHtml}
    </div>

    <div class="distill-detail-box">
      <strong>请求快照</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(run.request_snapshot || {}))}</pre>
    </div>

    <div class="distill-detail-box">
      <strong>样本结果预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(firstSample || {}))}</pre>
    </div>

    <div class="distill-detail-box">
      <strong>补丁列表预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(run.patches || []))}</pre>
    </div>

    <div class="distill-detail-box">
      <strong>沉淀记录预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(run.promotions || []))}</pre>
    </div>
  `;
}

function renderBehaviorPacket(packet) {
  const root = $("behaviorPacketDetail");
  if (!packet) {
    root.innerHTML = `<div class="distill-empty">先在左边输入 item_id、question_type 或 question_card_id，再生成行为蒸馏包。</div>`;
    return;
  }

  const summary = packet.aggregate_summary || {};
  const report = packet.report || {};
  const selectedAdjustment = packet.selected_agent_adjustment || null;
  const patchHints = Array.isArray(packet.candidate_patch_hints) ? packet.candidate_patch_hints : [];
  const topChangedFields = Array.isArray(summary.top_changed_fields) ? summary.top_changed_fields : [];
  const topActionTypes = Array.isArray(summary.top_action_types) ? summary.top_action_types : [];
  const topThresholds = Array.isArray(summary.top_failed_thresholds) ? summary.top_failed_thresholds : [];
  const itemPreview = Array.isArray(packet.item_traces) && packet.item_traces.length ? packet.item_traces[0] : null;
  const hypotheses = Array.isArray(summary.recommended_hypotheses) ? summary.recommended_hypotheses : [];
  const findings = Array.isArray(report.findings) ? report.findings : [];
  const nextSteps = Array.isArray(report.recommended_next_steps) ? report.recommended_next_steps : [];

  root.innerHTML = `
    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>聚合摘要</strong>
        <div>题目数：${escapeHtml(summary.item_count ?? 0)}</div>
        <div>版本数：${escapeHtml(summary.total_versions ?? 0)}</div>
        <div>审核动作数：${escapeHtml(summary.total_review_actions ?? 0)}</div>
        <div>使用事件数：${escapeHtml(summary.total_usage_events ?? 0)}</div>
        <div>下载数：${escapeHtml(summary.total_downloads ?? 0)}</div>
      </div>
      <div class="distill-detail-box">
        <strong>通过/丢弃结构</strong>
        <div>直接通过率：${escapeHtml(summary.accepted_direct_rate ?? "-")}</div>
        <div>修改后保留率：${escapeHtml(summary.accepted_after_edit_rate ?? "-")}</div>
        <div>丢弃率：${escapeHtml(summary.discard_rate ?? "-")}</div>
        <div>下载率：${escapeHtml(summary.download_rate ?? "-")}</div>
        <div>触达真题率：${escapeHtml(summary.truth_touched_rate ?? "-")}</div>
        <div>材料边界穿越率：${escapeHtml(summary.material_boundary_cross_rate ?? "-")}</div>
      </div>
    </div>

    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>高频改动字段</strong>
        <pre class="distill-detail-pre">${escapeHtml(prettyJson(topChangedFields))}</pre>
      </div>
      <div class="distill-detail-box">
        <strong>高频动作类型</strong>
        <pre class="distill-detail-pre">${escapeHtml(prettyJson(topActionTypes))}</pre>
      </div>
    </div>

    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>高频失败阈值</strong>
        <pre class="distill-detail-pre">${escapeHtml(prettyJson(topThresholds))}</pre>
      </div>
      <div class="distill-detail-box">
        <strong>建议假设</strong>
        ${
          hypotheses.length
            ? `<ul class="distill-note-list">${hypotheses.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
            : `<div class="distill-help">当前没有额外建议。</div>`
        }
      </div>
    </div>

    <div class="distill-detail-box">
      <strong>行为蒸馏执行摘要</strong>
      <div style="margin-bottom:8px;">${escapeHtml(report.executive_summary || "-")}</div>
      ${
        findings.length
          ? `<ul class="distill-note-list">${findings.map((item) => `<li>[${escapeHtml(item.severity)}] ${escapeHtml(item.title)}：${escapeHtml(item.summary)}</li>`).join("")}</ul>`
          : `<div class="distill-help">当前没有额外 findings。</div>`
      }
    </div>

    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>候选补丁提示</strong>
        <pre class="distill-detail-pre">${escapeHtml(prettyJson(patchHints))}</pre>
      </div>
      <div class="distill-detail-box">
        <strong>选中的智能体调整</strong>
        <pre class="distill-detail-pre">${escapeHtml(prettyJson(selectedAdjustment || {}))}</pre>
      </div>
    </div>

    <div class="distill-detail-box">
      <strong>推荐下一步</strong>
      ${
        nextSteps.length
          ? `<ul class="distill-note-list">${nextSteps.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
          : `<div class="distill-help">当前没有额外下一步建议。</div>`
      }
    </div>

    <div class="distill-detail-box">
      <strong>题目轨迹预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(itemPreview || {}))}</pre>
    </div>

    <div class="distill-detail-box">
      <strong>完整行为蒸馏包</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(packet))}</pre>
    </div>
  `;
}

function normalizeBusinessCountItems(raw, keyName) {
  if (!raw) return [];
  if (!Array.isArray(raw) && typeof raw === "object") {
    return Object.entries(raw).map(([key, count]) => ({ [keyName]: key, count: Number(count || 0) }));
  }
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item !== "object" || item === null) return { [keyName]: String(item), count: 1 };
      const key = item[keyName] || item.key || item.field || item.name || item.threshold || item.pattern;
      return key ? { [keyName]: key, count: Number(item.count || item.value || 1) } : null;
    })
    .filter(Boolean);
}

function inferBusinessTargetLayer(key, severity = "medium") {
  const text = String(key || "").toLowerCase();
  if (text.includes("answer") || text.includes("gold") || String(key).includes("答案")) return ["validator_contract", "high"];
  if (text.includes("material") || text.includes("passage") || text.includes("source") || String(key).includes("材料")) {
    return ["material_mapping", severity === "high" ? "high" : "medium"];
  }
  if (text.includes("distractor") || text.includes("option") || String(key).includes("干扰")) return ["validator_contract", "medium"];
  if (text.includes("stem") || text.includes("question") || String(key).includes("不像真题")) return ["question_card", "medium"];
  if (text.includes("review") || String(key).includes("审核")) return ["review_process", "low"];
  return ["unknown", severity === "high" ? "medium" : "low"];
}

function businessFieldSentence(field) {
  const text = String(field || "").toLowerCase();
  if (text.includes("distractor") || text.includes("option") || String(field).includes("干扰")) {
    return "用户经常修改干扰项解释，说明错项迷惑性可能不足。";
  }
  if (text.includes("material") || text.includes("passage") || String(field).includes("材料")) {
    return "多次修改材料片段，说明材料筛选或切片规则需要继续验证。";
  }
  if (text.includes("analysis") || String(field).includes("解析")) return "解析被反复修改，说明解释链路可能不够稳定。";
  return "该字段重复被修改，需要人工确认它是否代表结构性规律。";
}

function buildBusinessSignal(kind, key, count, description, evidence, severity = "medium", regressionAvailable = false) {
  const [targetLayer, riskLevel] = inferBusinessTargetLayer(key, severity);
  const supportCount = Number(count || 0);
  let recommendedStatus = "observe_more";
  let reason = "信号多次出现，但缺少 truth_gold/material regression 支撑，不能直接写回。";
  if (supportCount <= 1) {
    recommendedStatus = "single_case_only";
    reason = "这个反馈或修改目前只是单例，可能是人工偏好，不建议进入题卡配置。";
  } else if (targetLayer === "unknown") {
    recommendedStatus = "observe_more";
    reason = "出现过多次，但还不能明确映射到安全的正式层级，建议继续观察。";
  } else if (riskLevel === "high") {
    recommendedStatus = "observe_more";
    reason = "信号可能影响旧题型或答案稳定性，需要人审和回归后再判断。";
  } else if (regressionAvailable) {
    recommendedStatus = "suitable_for_formalization_packet";
    reason = "信号多次出现，且已有回归类证据，可作为 formalization packet 的候选 evidence。";
  }
  return {
    signal_id: `${kind}_${String(key || "unknown").replace(/[^\w\u4e00-\u9fa5]+/g, "_")}`.slice(0, 80),
    business_description: description,
    technical_hint: `${kind}:${key}`,
    target_layer: targetLayer,
    evidence,
    support_count: supportCount,
    support_level: supportCount >= 3 ? "high" : supportCount === 2 ? "medium" : "low",
    risk_level: riskLevel,
    recommended_status: recommendedStatus,
    reason,
    requires_regression: true,
    requires_human_confirmation: true,
  };
}

function buildBehaviorBusinessSummary(packet, feedback) {
  const aggregate = packet?.aggregate_summary || {};
  const feedbackItems = Array.isArray(feedback?.normalized_feedback) ? feedback.normalized_feedback : [];
  const editFields = normalizeBusinessCountItems(aggregate.top_changed_fields || aggregate.changed_field_distribution, "field").map((item) => ({
    field: item.field,
    count: Number(item.count || 0),
    business_description: businessFieldSentence(item.field),
  }));
  const failures = normalizeBusinessCountItems(aggregate.top_failed_thresholds || aggregate.failure_patterns, "pattern").map((item) => ({
    pattern: item.pattern,
    count: Number(item.count || 0),
    business_description: String(item.pattern || "").includes("distractor") ? "干扰项相关失败反复出现，可能指向错项机制不足。" : "该失败模式重复出现，建议结合 validator/regression 证据判断。",
  }));
  const userFeedback = feedbackItems.map((item) => ({
    feedback: item.summary || item.raw_feedback || item.dimension || "",
    dimension: item.dimension || "unknown",
    severity: item.severity || "medium",
    count: Number(item.count || 1),
  }));
  const regressionAvailable = Boolean(packet?.truth_gold_regression_results || packet?.material_quality_regression_results);
  const signals = []
    .concat(editFields.map((item) => buildBusinessSignal("edit", item.field, item.count, item.business_description, [item], "medium", regressionAvailable)))
    .concat(failures.map((item) => buildBusinessSignal("failure", item.pattern, item.count, item.business_description, [item], "medium", regressionAvailable)))
    .concat(userFeedback.map((item) => buildBusinessSignal("feedback", item.dimension || item.feedback, item.count, item.feedback || "用户反馈集中出现，需要继续观察。", [item], item.severity, regressionAvailable)));
  const reviewCount = Number(aggregate.total_review_actions || packet?.review_count || 0);
  const sampleCount = Number(aggregate.item_count || packet?.sample_count || 0);
  const patchCount = Number(aggregate.total_patch_actions || packet?.patch_count || 0);
  const missing = [];
  if (!packet || !Object.keys(packet).length) missing.push("behavior_packet");
  if (!feedback || !Object.keys(feedback).length) missing.push("agent_review_feedback");
  missing.push("truth_gold_regression_results", "material_quality_regression_results");
  const blocking = !packet || reviewCount <= 0 ? ["behavior_packet_missing_or_review_records_missing"] : [];
  const overview = {
    direct_pass_rate: aggregate.accepted_direct_rate ?? aggregate.direct_pass_rate ?? null,
    modified_then_kept_rate: aggregate.accepted_after_edit_rate ?? (reviewCount ? Number((patchCount / reviewCount).toFixed(4)) : null),
    rejected_rate: aggregate.discard_rate ?? aggregate.rejected_rate ?? null,
    dominant_review_pattern: patchCount > 0 ? "modified_then_kept" : "unknown",
    overall_quality_signal: blocking.length ? "blocked" : signals.length ? "needs_attention" : "unknown",
  };
  const summary = {
    summary_version: "v1",
    status: blocking.length ? "blocked" : missing.length ? "partial" : "completed",
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    requires_human_review: true,
    source: {
      behavior_packet_path: "",
      run_id: packet?.run_id || "",
      sample_count: sampleCount,
      review_count: reviewCount,
      patch_count: patchCount,
      promotion_count: Number(aggregate.total_promotion_actions || packet?.promotion_count || 0),
    },
    business_overview: overview,
    high_frequency_edit_fields: editFields,
    high_frequency_failure_patterns: failures,
    high_frequency_user_feedback: userFeedback,
    candidate_improvement_signals: signals,
    not_recommended_for_promotion: signals
      .filter((item) => ["single_case_only", "do_not_promote", "blocked"].includes(item.recommended_status))
      .map((item) => ({ signal_id: item.signal_id, reason: item.reason, recommended_status: item.recommended_status })),
    missing_evidence: missing,
    blocking_issues: blocking,
    recommended_next_action: blocking.length ? "blocked" : sampleCount < 3 || reviewCount < 3 ? "collect_more_samples" : signals.some((item) => item.recommended_status === "suitable_for_formalization_packet") ? "formalization_packet" : "observe_more",
  };
  return summary;
}

function businessStatusLabel(status) {
  const labels = {
    suitable_for_formalization_packet: "建议进入送审包",
    observe_more: "继续观察",
    needs_more_samples: "继续观察",
    single_case_only: "仅个例，不沉淀",
    do_not_promote: "不沉淀",
    blocked: "证据冲突，blocked",
  };
  return labels[status] || "继续观察";
}

function businessAssetLabel(layer) {
  const labels = {
    question_card: "题卡",
    material_card: "材料卡",
    prompt_assets: "prompt",
    validator_contract: "validator",
    runtime_mapping: "runtime",
    material_mapping: "材料映射",
    review_process: "审核流程",
    unknown: "仅观察",
  };
  return labels[layer] || "仅观察";
}

function businessProblemName(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("distractor") || text.includes("option") || String(value).includes("干扰")) return "干扰项不够迷惑";
  if (text.includes("material") || text.includes("passage") || text.includes("source") || String(value).includes("材料")) return "材料上下文不足";
  if (String(value).includes("不像真题") || String(value).includes("真题")) return "题目不像真题";
  if (text.includes("answer") || String(value).includes("答案")) return "答案稳定性风险";
  if (text.includes("analysis") || String(value).includes("解析")) return "解析说服力不足";
  return String(value || "未命名问题");
}

function normalizeBeforeAfterComparisons(rawPairs) {
  const pairs = Array.isArray(rawPairs) ? rawPairs : [];
  return pairs
    .map((item) => {
      const before = item.before || item.before_question || item.original_question;
      const after = item.after || item.after_question || item.modified_question;
      if (!before || !after) return null;
      return {
        material_parameter: item.material_parameter || item.material_params || "同一材料参数",
        before_question: before,
        after_question: after,
        changed_fields: item.changed_fields || item.field || [],
        change_reason: item.change_reason || item.reason || "",
        validator_result_change: item.validator_result_change || item.validator_delta || "unknown",
        human_review_change: item.human_review_change || item.review_delta || "unknown",
      };
    })
    .filter(Boolean);
}

function collectBehaviorActionClusters(packet, summary) {
  const traces = Array.isArray(packet?.item_traces) ? packet.item_traces : [];
  const clusters = new Map();
  traces.forEach((trace, index) => {
    const itemId = trace.item_id || trace.question_id || trace.sample_id || trace.qid || `item_${index + 1}`;
    const leafId = trace.leaf_id || trace.question_type || trace.question_card_id || packet?.question_type || summary?.source?.run_id || "unknown";
    const fields = []
      .concat(trace.changed_fields || [])
      .concat((trace.patch_actions || []).flatMap((action) => action.changed_fields || action.fields || action.field || []))
      .concat((trace.review_actions || []).flatMap((action) => action.changed_fields || action.fields || action.field || []))
      .filter(Boolean)
      .map((field) => String(field));
    const actionTypes = []
      .concat((trace.review_actions || []).map((action) => action.action_type || action.verdict || action.action))
      .concat((trace.patch_actions || []).map((action) => action.action_type || action.target || "patch"))
      .filter(Boolean)
      .map((item) => String(item));
    const uniqueFields = Array.from(new Set(fields.length ? fields : (summary.high_frequency_edit_fields || []).map((item) => item.field).filter(Boolean)));
    uniqueFields.forEach((field) => {
      const key = `${leafId}::${field}`;
      const cluster = clusters.get(key) || {
        cluster_id: key.replace(/[^\w\u4e00-\u9fa5]+/g, "_").slice(0, 90),
        leaf_id: leafId,
        modified_field: field,
        affected_items: [],
        action_types: [],
        repeated_action: "",
        count: 0,
      };
      if (!cluster.affected_items.includes(itemId)) cluster.affected_items.push(itemId);
      actionTypes.forEach((type) => {
        if (!cluster.action_types.includes(type)) cluster.action_types.push(type);
      });
      cluster.count += 1;
      cluster.repeated_action = `${cluster.affected_items.length} 道题集中修改 ${businessProblemName(field)}`;
      clusters.set(key, cluster);
    });
  });
  if (!clusters.size) {
    (summary.high_frequency_edit_fields || []).forEach((item) => {
      const leafId = summary.source?.run_id || "unknown";
      const field = item.field || "unknown";
      clusters.set(`${leafId}::${field}`, {
        cluster_id: `${leafId}_${field}`.replace(/[^\w\u4e00-\u9fa5]+/g, "_").slice(0, 90),
        leaf_id: leafId,
        modified_field: field,
        affected_items: [],
        action_types: ["patch_or_review_edit"],
        repeated_action: `${item.count || 0} 次集中修改 ${businessProblemName(field)}`,
        count: Number(item.count || 0),
      });
    });
  }
  return Array.from(clusters.values()).sort((a, b) => Number(b.count || 0) - Number(a.count || 0));
}

function buildActionProblemItems(problems, actionClusters) {
  return (problems || []).map((problem, index) => {
    const cluster =
      actionClusters.find((item) => businessProblemName(item.modified_field) === problem.problem_name) ||
      actionClusters[index] ||
      {};
    return {
      problem_id: `problem_${index + 1}`,
      title: problem.problem_name,
      affected_leaf: cluster.leaf_id || "unknown",
      affected_items: cluster.affected_items || [],
      repeated_action: cluster.repeated_action || `${problem.support || "若干"} 的相似修改`,
      modified_fields: cluster.modified_field ? [cluster.modified_field] : [],
      inferred_from_actions: `${problem.evidence_source || "行为证据"}：${cluster.repeated_action || problem.support || "重复修改"}`,
      business_judgment: problem.business_explanation,
      status_label: problem.current_suggestion,
      technical_detail: problem.technical_detail || {},
    };
  });
}

function buildBehaviorBusinessView(summary, beforeAfterPairs = [], packet = {}) {
  const source = summary.source || {};
  const overview = summary.business_overview || {};
  const comparisons = normalizeBeforeAfterComparisons(beforeAfterPairs);
  const missing = Array.from(new Set([].concat(summary.missing_evidence || [])));
  if (!comparisons.length) {
    ["missing_before_after_question_pair", "missing_same_material_parameter_trace", "missing_validator_before_after_result"].forEach((item) => {
      if (!missing.includes(item)) missing.push(item);
    });
  }
  const problems = []
    .concat((summary.high_frequency_edit_fields || []).map((item) => ({
      problem_name: businessProblemName(item.field),
      business_explanation: item.business_description || businessFieldSentence(item.field),
      evidence_source: "审核修改字段",
      support: Number(item.count || 0) >= 3 ? `高频，出现 ${item.count} 次` : `出现 ${item.count || 0} 次`,
      current_suggestion: Number(item.count || 0) === 1 ? "仅个例，不沉淀" : "继续观察",
      technical_detail: { field: item.field, count: item.count || 0 },
    })))
    .concat((summary.high_frequency_failure_patterns || []).map((item) => ({
      problem_name: businessProblemName(item.pattern),
      business_explanation: item.business_description || "该失败模式重复出现，需要结合回归证据判断。",
      evidence_source: "失败模式统计",
      support: Number(item.count || 0) >= 3 ? `高频，出现 ${item.count} 次` : `出现 ${item.count || 0} 次`,
      current_suggestion: Number(item.count || 0) === 1 ? "仅个例，不沉淀" : "继续观察",
      technical_detail: { pattern: item.pattern, count: item.count || 0 },
    })))
    .concat((summary.high_frequency_user_feedback || []).map((item) => ({
      problem_name: businessProblemName(item.feedback || item.dimension),
      business_explanation: item.feedback || "用户反馈集中出现，需要判断是否为结构性问题。",
      evidence_source: "用户反馈",
      support: Number(item.count || 0) >= 3 ? `高频，出现 ${item.count} 次` : `出现 ${item.count || 0} 次`,
      current_suggestion: Number(item.count || 0) === 1 ? "仅个例，不沉淀" : "继续观察",
      technical_detail: { dimension: item.dimension, severity: item.severity, count: item.count || 0 },
    })));
  const actionClusters = collectBehaviorActionClusters(packet, summary);
  const actionProblemItems = buildActionProblemItems(problems, actionClusters);
  const recommendations = (summary.candidate_improvement_signals || []).map((item) => ({
    recommendation: item.business_description,
    asset_label: businessAssetLabel(item.target_layer),
    reason: item.reason,
    risk: item.risk_level === "high" ? "高，暂缓" : item.risk_level === "medium" ? "中" : "低",
    status_label: businessStatusLabel(item.recommended_status),
    missing_evidence: Array.from(new Set(["人工确认", "回归证据"].concat((summary.missing_evidence || []).filter((name) => String(name).includes("regression"))))),
    technical_detail: {
      signal_id: item.signal_id,
      target_layer: item.target_layer,
      recommended_status: item.recommended_status,
    },
  }));
  const canEnterPacket = recommendations.some((item) => item.status_label === "建议进入送审包") && summary.status !== "blocked";
  const canEnterReview = recommendations.length > 0 && summary.status !== "blocked";
  const blockedReasons = Array.from(new Set([].concat(summary.blocking_issues || []).concat(missing.map((item) => `缺少证据:${item}`))));
  return {
    view_version: "v1",
    status: summary.status || "partial",
    formalized: false,
    writeback_allowed: false,
    executor_allowed: false,
    family_context: {
      stage: summary.recommended_next_action === "formalization_packet" ? "review / packet" : summary.recommended_next_action === "blocked" ? "blocked review" : "proto trial / review",
      leaf_id: source.run_id || "unknown",
      question_type: "unknown",
      business_subtype: "unknown",
      sample_count: source.sample_count || 0,
      review_count: source.review_count || 0,
      patch_count: source.patch_count || 0,
      promotion_count: source.promotion_count || 0,
      overall_status: { stable: "稳定", needs_attention: "需关注", blocked: "blocked", unknown: "继续观察" }[overview.overall_quality_signal] || "继续观察",
    },
    business_problem_summary: problems,
    action_clusters: actionClusters,
    action_problem_items: actionProblemItems,
    distilled_recommendations: recommendations,
    before_after_comparisons: comparisons,
    landing_status: {
      can_formalize: false,
      can_enter_formalization_packet: canEnterPacket,
      can_enter_review: canEnterReview,
      landing_label: canEnterPacket ? "仅可进入送审包" : canEnterReview ? "仅可继续观察" : "不能落位",
      blocked_reasons: blockedReasons,
      next_action: {
        human_review: "先人工确认候选沉淀点",
        observe_more: "继续观察更多样本",
        formalization_packet: "可进入送审包，但不能直接落位",
        collect_more_samples: "补充更多样本和回归证据",
        blocked: "先处理阻塞证据",
      }[summary.recommended_next_action] || "继续观察更多样本",
    },
    technical_refs: [
      "behavior_distillation_business_view.json",
      "behavior_distillation_business_summary.json",
      "behavior_distillation_formalization_evidence.json",
      "new_leaf_formalization_packet 摘要",
      "readiness gate 摘要",
    ],
    missing_evidence: missing,
  };
}

function renderBusinessViewMarkdown(view) {
  const context = view.family_context || {};
  const landing = view.landing_status || {};
  const lines = [
    "# 业务视图：本阶段叶族问题与沉淀建议",
    "",
    "> 业务蒸馏结果是 evidence，不是正式配置；blocked 不等于失败，只表示当前证据或流程还没满足落位条件。",
    "",
    "## 当前阶段与叶族",
    "",
    `- 当前阶段：${context.stage}`,
    `- 当前题型或叶族：${context.leaf_id}`,
    `- 样本数：${context.sample_count}`,
    `- 审核数：${context.review_count}`,
    `- 修改数：${context.patch_count}`,
    `- 沉淀包数：${context.promotion_count}`,
    `- 当前整体状态：${context.overall_status}`,
    "",
    "## 高频问题抽象",
    "",
    ...(view.business_problem_summary.length
      ? view.business_problem_summary.map((item) => `- ${item.problem_name}：${item.business_explanation} 证据：${item.evidence_source}；建议：${item.current_suggestion}`)
      : ["- 当前没有足够重复出现的问题，建议继续观察。"]),
    "",
    "## 蒸馏后结果",
    "",
    ...(view.distilled_recommendations.length
      ? view.distilled_recommendations.map((item) => `- ${item.recommendation} 建议进入：${item.asset_label}；状态：${item.status_label}；风险：${item.risk}。`)
      : ["- 暂无可送审的沉淀建议。"]),
    "",
    "## 前后题目对比",
    "",
    ...(view.before_after_comparisons.length
      ? view.before_after_comparisons.map((item) => `- 同一材料参数 ${JSON.stringify(item.material_parameter)}：修改字段 ${JSON.stringify(item.changed_fields)}，原因：${item.change_reason || "未填写"}`)
      : ["- 当前行为蒸馏包缺少可展示的 before/after 题目对比。需要接入 review version chain 或 patch diff 后展示。"]),
    "",
    "## 当前是否可以落位",
    "",
    `- 当前能否落位：${landing.landing_label}`,
    `- 不能落位的原因：${landing.blocked_reasons?.join("；") || "无"}`,
    `- 下一步建议：${landing.next_action}`,
  ];
  return `${lines.join("\n")}\n`;
}

function renderBusinessReadableView(view) {
  const context = view.family_context || {};
  const problems = view.business_problem_summary || [];
  const recommendations = view.distilled_recommendations || [];
  const comparisons = view.before_after_comparisons || [];
  const landing = view.landing_status || {};
  $("businessReadableView").innerHTML = `
    <div class="distill-detail-box">
      <strong>业务视图：本阶段叶族问题与沉淀建议</strong>
      <div>当前处于 ${escapeHtml(context.stage)} 阶段。本轮样本主要集中在 ${escapeHtml(context.leaf_id)}，系统已收集审核与修改行为，当前整体状态为 ${escapeHtml(context.overall_status)}。</div>
    </div>
    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>当前阶段与叶族</strong>
        <div>当前阶段：${escapeHtml(context.stage)}</div>
        <div>当前题型或叶族：${escapeHtml(context.leaf_id)}</div>
        <div>样本数：${escapeHtml(context.sample_count)}</div>
        <div>审核数：${escapeHtml(context.review_count)}</div>
        <div>修改数：${escapeHtml(context.patch_count)}</div>
        <div>沉淀包数：${escapeHtml(context.promotion_count)}</div>
      </div>
      <div class="distill-detail-box">
        <strong>高频问题</strong>
        ${
          problems.length
            ? `<ul class="distill-note-list">${problems.map((item) => `<li><strong>${escapeHtml(item.problem_name)}</strong>：${escapeHtml(item.business_explanation)}<br />证据：${escapeHtml(item.evidence_source)}；${escapeHtml(item.support)}；建议：${escapeHtml(item.current_suggestion)}</li>`).join("")}</ul>`
            : `<div>当前没有足够重复出现的问题，建议继续观察。</div>`
        }
      </div>
    </div>
    <div class="distill-run-grid">
      <div class="distill-detail-box">
        <strong>蒸馏后结果</strong>
        ${
          recommendations.length
            ? `<ul class="distill-note-list">${recommendations.map((item) => `<li>${escapeHtml(item.recommendation || "")}<br />建议进入：${escapeHtml(item.asset_label)}；状态：${escapeHtml(item.status_label)}；风险：${escapeHtml(item.risk)}；还缺：${escapeHtml((item.missing_evidence || []).join("、") || "暂无明确缺口")}</li>`).join("")}</ul>`
            : `<div>暂无可送审的沉淀建议。</div>`
        }
      </div>
      <div class="distill-detail-box">
        <strong>前后题目对比</strong>
        ${
          comparisons.length
            ? `<ul class="distill-note-list">${comparisons.map((item) => `<li>同一材料参数：${escapeHtml(JSON.stringify(item.material_parameter))}<br />原题版本：${escapeHtml(String(item.before_question))}<br />修改后版本：${escapeHtml(String(item.after_question))}<br />修改字段：${escapeHtml(JSON.stringify(item.changed_fields))}<br />修改原因：${escapeHtml(item.change_reason || "-")}<br />validator 结果变化：${escapeHtml(item.validator_result_change || "unknown")}<br />人审结论变化：${escapeHtml(item.human_review_change || "unknown")}</li>`).join("")}</ul>`
            : `<div>当前行为蒸馏包缺少可展示的 before/after 题目对比。需要接入 review version chain 或 patch diff 后展示。</div>`
        }
      </div>
    </div>
    <div class="distill-detail-box">
      <strong>当前是否可以落位</strong>
      <div>当前能否落位：${escapeHtml(landing.landing_label || "不能落位")}</div>
      <div>不能落位的原因：${escapeHtml((landing.blocked_reasons || []).join("；") || "无")}</div>
      <div>下一步建议：${escapeHtml(landing.next_action || "继续观察更多样本")}</div>
      <div class="distill-help">落位 = 正式写回 / 正式启用配置；送审包 = evidence，可以生成；blocked 不等于失败。</div>
    </div>
  `;
}

function renderDiffText(text, side) {
  const raw = String(text || "");
  if (!raw) return "";
  return escapeHtml(raw);
}

function renderBeforeAfterDiff(beforeText, afterText, side) {
  const before = String(beforeText || "");
  const after = String(afterText || "");
  let start = 0;
  while (start < before.length && start < after.length && before[start] === after[start]) start += 1;
  let beforeEnd = before.length - 1;
  let afterEnd = after.length - 1;
  while (beforeEnd >= start && afterEnd >= start && before[beforeEnd] === after[afterEnd]) {
    beforeEnd -= 1;
    afterEnd -= 1;
  }
  const source = side === "before" ? before : after;
  const end = side === "before" ? beforeEnd : afterEnd;
  const color = side === "before" ? "#fee2e2" : "#dcfce7";
  if (start > end) return escapeHtml(source);
  return `${escapeHtml(source.slice(0, start))}<mark style="background:${color};padding:1px 2px;border-radius:3px;">${escapeHtml(source.slice(start, end + 1))}</mark>${escapeHtml(source.slice(end + 1))}`;
}

function setBusinessViewPage(page) {
  state.businessViewPage = page;
  if (state.businessView) renderBusinessReadableView(state.businessView);
}

function businessViewStageLabel(value) {
  return {
    proto_trial_review: "proto trial / review",
    patch_review: "patch review",
    promotion_review: "promotion review",
    readiness: "readiness",
  }[value] || "proto trial / review";
}

function parseBusinessViewLeafSelection() {
  const mode = $("businessViewScopeMode")?.value || "single";
  const raw = $("businessViewLeafId")?.value || "";
  const leafIds = raw
    .split(/[,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  return { mode, leaf_ids: mode === "all" ? [] : leafIds };
}

function applyBusinessViewLeafScope(view, selection) {
  const clusters = view.action_clusters || [];
  const allLeafIds = Array.from(new Set(clusters.map((item) => item.leaf_id).filter(Boolean)));
  const selectedLeafIds =
    selection.mode === "all"
      ? allLeafIds
      : selection.leaf_ids.length
        ? selection.leaf_ids
        : allLeafIds.slice(0, 1);
  const selectedSet = new Set(selectedLeafIds);
  const filteredClusters = selection.mode === "all" || !selectedSet.size ? clusters : clusters.filter((item) => selectedSet.has(item.leaf_id));
  const filteredProblems =
    selection.mode === "all" || !selectedSet.size
      ? view.action_problem_items || []
      : (view.action_problem_items || []).filter((item) => selectedSet.has(item.affected_leaf));
  const leafOverview = selectedLeafIds.map((leafId) => {
    const leafClusters = clusters.filter((item) => item.leaf_id === leafId);
    const itemIds = Array.from(new Set(leafClusters.flatMap((item) => item.affected_items || [])));
    return {
      leaf_id: leafId,
      cluster_count: leafClusters.length,
      affected_item_count: itemIds.length,
      top_modified_fields: leafClusters.slice(0, 4).map((item) => item.modified_field),
    };
  });
  view.family_context.scope_mode = selection.mode;
  view.family_context.leaf_ids = selectedLeafIds;
  view.family_context.leaf_id =
    selection.mode === "all"
      ? `全部叶族（${selectedLeafIds.length || allLeafIds.length}）`
      : selectedLeafIds.length > 1
        ? `多叶族（${selectedLeafIds.length}）`
        : selectedLeafIds[0] || view.family_context.leaf_id;
  view.leaf_overview = leafOverview;
  view.filtered_action_clusters = filteredClusters;
  view.filtered_action_problem_items = filteredProblems;
  return view;
}

function setBusinessViewAsyncState({ visible, title, text, progress, help }) {
  const panel = $("businessViewAsyncState");
  if (!panel) return;
  panel.style.display = visible ? "block" : "none";
  $("businessViewAsyncTitle").textContent = title || "正在处理";
  $("businessViewAsyncText").textContent = text || "";
  $("businessViewAsyncBar").style.width = `${Math.max(0, Math.min(100, Number(progress || 0)))}%`;
  $("businessViewAsyncHelp").textContent =
    help || "长任务会轮询状态；完成后再生成业务视图。";
}

function clearBusinessViewAsyncTimer() {
  if (state.businessViewAsyncTimer) {
    window.clearInterval(state.businessViewAsyncTimer);
    state.businessViewAsyncTimer = null;
  }
}

function runBusinessViewLoadingSequence(steps, done) {
  clearBusinessViewAsyncTimer();
  let index = 0;
  const apply = () => {
    const step = steps[Math.min(index, steps.length - 1)];
    setBusinessViewAsyncState({ visible: true, ...step });
    index += 1;
    if (index >= steps.length) {
      clearBusinessViewAsyncTimer();
      window.setTimeout(() => {
        done?.();
      }, 280);
    }
  };
  apply();
  state.businessViewAsyncTimer = window.setInterval(apply, 520);
}

function handleLoadBusinessViewExisting() {
  runBusinessViewLoadingSequence(
    [
      { title: "读取已完成结果", text: "正在读取 behavior packet / business summary...", progress: 20 },
      { title: "解析动作簇", text: "正在统计哪个叶族、哪些题、哪些字段被集中修改...", progress: 45 },
      { title: "生成业务页", text: "正在生成人话问题条目、前后对比和落位判断...", progress: 75 },
      { title: "完成", text: "业务视图已渲染，可以逐页查看。", progress: 100 },
    ],
    () => {
      handleGenerateBusinessSummary({ preventDefault() {} });
      window.setTimeout(() => setBusinessViewAsyncState({ visible: false }), 900);
    },
  );
}

function handleStartBusinessViewLongTask() {
  clearBusinessViewAsyncTimer();
  let progress = 8;
  setBusinessViewAsyncState({
    visible: true,
    title: "模型调试蒸馏长任务",
    text: "任务已创建，等待后端队列执行。",
    progress,
    help: "状态：排队中",
  });
  state.businessViewAsyncTimer = window.setInterval(() => {
    progress = Math.min(92, progress + 7);
    setBusinessViewAsyncState({
      visible: true,
      title: "模型调试蒸馏长任务",
      text: progress < 35 ? "排队中：等待后端任务接收..." : progress < 70 ? "运行中：等待模型调试蒸馏和 diff 产物..." : "回归中：等待 validator / truth-gold 证据回填...",
      progress,
      help: progress < 35 ? "状态：排队中" : progress < 70 ? "状态：模型运行中" : "状态：回归中",
    });
  }, 850);
  setPageStatus("蒸馏任务已进入状态跟踪。", "info");
}

function businessViewPageButton(page, label) {
  const active = state.businessViewPage === page;
  return `<button type="button" class="${active ? "distill-primary" : "distill-secondary"} business-view-page-btn" data-business-view-page="${escapeHtml(page)}">${escapeHtml(label)}</button>`;
}

function renderBusinessViewScopePage(view) {
  const context = view.family_context || {};
  const leafOverview = view.leaf_overview || [];
  return `
    <div class="distill-detail-box">
      <strong>当前阶段与叶族</strong>
      <div>当前阶段：${escapeHtml(context.stage)}</div>
      <div>当前范围：${escapeHtml(context.leaf_id)}</div>
      <div>样本数：${escapeHtml(context.sample_count)}</div>
      <div>审核数：${escapeHtml(context.review_count)}</div>
      <div>修改数：${escapeHtml(context.patch_count)}</div>
      <div>沉淀包数：${escapeHtml(context.promotion_count)}</div>
      <div>当前整体状态：${escapeHtml(context.overall_status)}</div>
      <div class="distill-help">来源：已完成的行为蒸馏结果。</div>
    </div>
    <div class="distill-detail-box">
      <strong>叶族概览</strong>
      ${
        leafOverview.length
          ? `<ul class="distill-note-list">${leafOverview.map((item) => `<li>${escapeHtml(item.leaf_id)}：${escapeHtml(item.cluster_count)} 类动作簇，影响 ${escapeHtml(item.affected_item_count || "未知")} 道题；主要字段：${escapeHtml((item.top_modified_fields || []).join("、") || "-")}</li>`).join("")}</ul>`
          : `<div>当前行为包没有叶族分组信息；请补充 item_traces 中的 leaf_id / question_type。</div>`
      }
    </div>
  `;
}

function renderBusinessViewActionsPage(view) {
  const items = view.filtered_action_problem_items || view.action_problem_items || [];
  const clusters = view.filtered_action_clusters || view.action_clusters || [];
  return `
    <div class="distill-detail-box">
      <strong>动作判断：哪些叶族哪些题被统一修改过</strong>
      ${
        clusters.length
          ? `<ul class="distill-note-list">${clusters.map((item) => `<li>${escapeHtml(item.leaf_id)}：${escapeHtml(item.repeated_action)}；题目：${escapeHtml((item.affected_items || []).join("、") || "行为包未给出题号")}；动作：${escapeHtml((item.action_types || []).join("、") || "patch/review")}</li>`).join("")}</ul>`
          : `<div>当前行为包没有足够的 item trace，无法定位到具体题号。</div>`
      }
    </div>
    <div class="distill-run-grid">
      ${
        items.length
          ? items.map((item) => `
              <div class="distill-detail-box">
                <strong>${escapeHtml(item.title)}</strong>
                <div>影响叶族：${escapeHtml(item.affected_leaf)}</div>
                <div>影响题目：${escapeHtml((item.affected_items || []).join("、") || "缺少题号 trace")}</div>
                <div>动作依据：${escapeHtml(item.inferred_from_actions)}</div>
                <div>业务判断：${escapeHtml(item.business_judgment || "")}</div>
                <div>当前建议：${escapeHtml(item.status_label || "继续观察")}</div>
              </div>
            `).join("")
          : `<div class="distill-detail-box">还没有可展示的小条目。需要更多 review action / patch trace。</div>`
      }
    </div>
  `;
}

function renderBusinessViewResultPage(view) {
  const recommendations = view.distilled_recommendations || [];
  return `
    <div class="distill-detail-box">
      <strong>蒸馏后结果</strong>
      ${
        recommendations.length
          ? `<ul class="distill-note-list">${recommendations.map((item) => `<li>${escapeHtml(item.recommendation || "")}<br />建议进入：${escapeHtml(item.asset_label)}；状态：${escapeHtml(item.status_label)}；风险：${escapeHtml(item.risk)}；还缺：${escapeHtml((item.missing_evidence || []).join("、") || "暂无明确缺口")}<br />为什么：${escapeHtml(item.reason || "")}</li>`).join("")}</ul>`
          : `<div>暂无可送审的沉淀建议。</div>`
      }
      <div class="distill-help">这些只是沉淀建议，不会自动改题卡、prompt 或 validator。</div>
    </div>
  `;
}

function renderBusinessViewComparePage(view) {
  const comparisons = view.before_after_comparisons || [];
  if (!comparisons.length) {
    return `
      <div class="distill-detail-box">
        <strong>前后题目对比</strong>
        <div>当前行为蒸馏包缺少可展示的 before/after 题目对比。需要接入 review version chain 或 patch diff 后展示。</div>
        <div class="distill-help">不会伪造旧题或蒸馏后结果；缺失证据已记录到 missing_evidence。</div>
      </div>
    `;
  }
  return comparisons.map((item) => `
    <div class="distill-detail-box">
      <strong>同一材料参数</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(item.material_parameter))}</pre>
      <div class="distill-run-grid">
        <div class="distill-detail-box">
          <strong>旧历史题目 / 改之前</strong>
          <div>${renderBeforeAfterDiff(item.before_question, item.after_question, "before")}</div>
        </div>
        <div class="distill-detail-box">
          <strong>蒸馏后结果 / 改之后</strong>
          <div>${renderBeforeAfterDiff(item.before_question, item.after_question, "after")}</div>
        </div>
      </div>
      <div>修改字段：${escapeHtml(JSON.stringify(item.changed_fields))}</div>
      <div>修改原因：${escapeHtml(item.change_reason || "-")}</div>
      <div>validator 结果变化：${escapeHtml(item.validator_result_change || "unknown")}</div>
      <div>人审结论变化：${escapeHtml(item.human_review_change || "unknown")}</div>
    </div>
  `).join("");
}

function renderBusinessViewLandingPage(view) {
  const landing = view.landing_status || {};
  return `
    <div class="distill-detail-box">
      <strong>当前是否可以落位</strong>
      <div>当前能否落位：${escapeHtml(landing.landing_label || "不能落位")}</div>
      <div>不能落位的原因：${escapeHtml((landing.blocked_reasons || []).join("；") || "无")}</div>
      <div>下一步建议：${escapeHtml(landing.next_action || "继续观察更多样本")}</div>
      <div class="distill-help">落位 = 正式写回 / 正式启用配置；送审包 = evidence，可以生成；blocked 不等于失败。</div>
    </div>
  `;
}

function renderBusinessReadableView(view) {
  const context = view.family_context || {};
  const selectedCount = (state.leafIssueRows || []).filter((row) => row.selected).length;
  const selectedLeafCount = new Set((state.leafIssueRows || []).filter((row) => row.selected).map((row) => row.leaf_id)).size;
  const taskCount = (state.leafDistillTasks || []).length;
  $("businessReadableView").innerHTML = `
    <div class="distill-detail-box">
      <strong>多叶族蒸馏任务工作台</strong>
      <div>${escapeHtml(historyDistillStepTitle())}</div>
      <div class="distill-help">范围：${escapeHtml(context.leaf_id || "等待选择")}；阶段：${escapeHtml(context.stage || "proto trial / review")}。</div>
    </div>
    <div class="distill-inline-actions">
      ${historyDistillStepButton("issues", "1 叶族问题选择")}
      ${historyDistillStepButton("tasks", "2 多任务队列")}
      ${historyDistillStepButton("acceptance", "3 多任务验收发布")}
    </div>
    <div class="distill-detail-box">
      <strong>当前选择</strong>
      <div>已选：${escapeHtml(selectedLeafCount)} 个叶族 / ${escapeHtml(selectedCount)} 个问题。${taskCount ? `已拆成 ${escapeHtml(taskCount)} 个隔离任务。` : "提交后会按叶族拆成隔离任务。"}</div>
    </div>
  `;
  $("businessReadableView").querySelectorAll(".history-distill-step-btn").forEach((button) => {
    button.addEventListener("click", () => setHistoryDistillStep(button.dataset.historyDistillStep || "issues"));
  });
  updateHistoryDistillPanels();
}

function historyDistillStepTitle() {
  if (state.historyDistillStep === "tasks") return "2 多任务队列。提交后一个叶族一个任务，状态和结果彼此隔离。";
  if (state.historyDistillStep === "acceptance") return "3 多任务验收与独立发布。左侧选择叶族任务，右侧验收、暂存、返工或发布。";
  return "1 叶族问题选择。很多叶族按组排列，点击叶族展开问题条目，勾选本次要处理的问题。";
}

function historyDistillStepButton(step, label) {
  const active = state.historyDistillStep === step;
  return `<button type="button" class="${active ? "distill-primary" : "distill-secondary"} history-distill-step-btn" data-history-distill-step="${escapeHtml(step)}">${escapeHtml(label)}</button>`;
}

function setHistoryDistillStep(step) {
  state.historyDistillStep = ["issues", "tasks", "acceptance"].includes(step) ? step : "issues";
  if (state.businessView) renderBusinessReadableView(state.businessView);
  updateHistoryDistillPanels();
}

function updateHistoryDistillPanels() {
  const issuePanel = $("leafIssueSelectionTable");
  const taskPanel = $("leafDistillTaskQueue");
  const acceptancePanel = $("leafDistillAcceptancePanel");
  if (issuePanel) issuePanel.style.display = state.historyDistillStep === "issues" ? "block" : "none";
  if (taskPanel) taskPanel.style.display = state.historyDistillStep === "tasks" ? "block" : "none";
  if (acceptancePanel) acceptancePanel.style.display = state.historyDistillStep === "acceptance" ? "block" : "none";
}

function buildLeafIssueRowsFromBusinessView(view) {
  const rawRows = (view.action_problem_items || [])
    .filter((item) => item.affected_leaf && item.affected_leaf !== "unknown")
    .map((item, index) => ({
    issue_id: item.problem_id || `issue_${index + 1}`,
    leaf_id: item.affected_leaf || "unknown",
    problem_name: item.title || "未命名问题",
    frequency: Number((item.technical_detail || {}).count || 0) || Number(String(item.repeated_action || "").match(/\d+/)?.[0] || 0),
    affected_items: item.affected_items || [],
    action_basis: item.inferred_from_actions || item.repeated_action || "",
    recommendation: item.status_label || "继续观察",
    selected: true,
  }));
  const merged = new Map();
  rawRows.forEach((row) => {
    const key = `${row.leaf_id}::${String(row.problem_name || "").trim()}`;
    const existing = merged.get(key);
    if (!existing) {
      merged.set(key, {
        ...row,
        issue_id: `issue_${merged.size + 1}`,
        affected_items: Array.from(new Set(row.affected_items || [])),
        action_basis_parts: row.action_basis ? [row.action_basis] : [],
      });
      return;
    }
    existing.frequency = Math.max(Number(existing.frequency || 0), Number(row.frequency || 0));
    existing.affected_items = Array.from(new Set([...(existing.affected_items || []), ...(row.affected_items || [])]));
    if (row.action_basis && !existing.action_basis_parts.includes(row.action_basis)) {
      existing.action_basis_parts.push(row.action_basis);
    }
    if (row.recommendation && existing.recommendation === "继续观察") existing.recommendation = row.recommendation;
  });
  const rows = Array.from(merged.values()).map((row) => ({
    ...row,
    action_basis: (row.action_basis_parts || []).slice(0, 2).join("；") || row.action_basis || "",
  }));
  if (rows.length) return rows;
  const fallbackLeafId = (view.family_context || {}).leaf_id || "";
  if (!fallbackLeafId || fallbackLeafId === "unknown" || fallbackLeafId.startsWith("多叶族") || fallbackLeafId.startsWith("全部叶族")) return [];
  return (view.business_problem_summary || []).map((item, index) => ({
    issue_id: `issue_${index + 1}`,
    leaf_id: fallbackLeafId,
    problem_name: item.problem_name,
    frequency: Number((item.technical_detail || {}).count || 0),
    affected_items: [],
    action_basis: `${item.evidence_source || "行为证据"}：${item.support || ""}`,
    recommendation: item.current_suggestion || "继续观察",
    selected: true,
  }));
}

function renderLeafIssueSelectionTable() {
  const root = $("leafIssueSelectionTable");
  if (!root) return;
  const rows = state.leafIssueRows || [];
  if (!rows.length) {
    root.innerHTML = `<div class="distill-empty">先生成业务视图，再从业务视图生成问题条目。</div>`;
    return;
  }
  const grouped = rows.reduce((acc, row) => {
    (acc[row.leaf_id] ||= []).push(row);
    return acc;
  }, {});
  const selected = rows.filter((row) => row.selected);
  const selectedLeafCount = new Set(selected.map((row) => row.leaf_id)).size;
  root.innerHTML = `
    <div class="distill-detail-box">
      <strong>叶族问题列表</strong>
      <div class="distill-help">很多叶族按组排列；勾选本次要处理的问题，提交后按叶族拆成独立任务。</div>
    </div>
    ${Object.entries(grouped)
    .map(([leafId, items]) => `
      <div class="distill-detail-box">
        <div style="display:grid;grid-template-columns:minmax(180px,1fr) 120px 120px;gap:12px;align-items:center;border-bottom:1px solid #d7e0ec;padding-bottom:10px;margin-bottom:8px;">
          <strong>▾ ${escapeHtml(leafId)}</strong>
          <span class="distill-signal-medium">${escapeHtml(items.length)} 个问题</span>
          <span>影响 ${escapeHtml(new Set(items.flatMap((row) => row.affected_items || [])).size || "未知")} 题</span>
        </div>
        ${items.map((row) => `
          <label class="distill-check" style="display:flex;align-items:flex-start;gap:10px;margin-top:10px;">
            <input class="leaf-issue-checkbox" type="checkbox" data-issue-id="${escapeHtml(row.issue_id)}" ${row.selected ? "checked" : ""} />
            <span>
              <strong>${escapeHtml(row.problem_name)}</strong>
              <br />出现频次：${escapeHtml(row.frequency || 0)}；影响题目：${escapeHtml((row.affected_items || []).join("、") || "未提供题号")}
              <br />动作依据：${escapeHtml(row.action_basis || "-")}
              <br />建议：${escapeHtml(row.recommendation || "继续观察")}
            </span>
          </label>
        `).join("")}
      </div>
    `)
    .join("")}
    <div class="distill-detail-box">
      <button id="historySubmitSelectedIssuesBtn" type="button" class="distill-primary">提交所选问题</button>
      <span class="distill-help" style="margin-left:16px;">已选：${escapeHtml(selectedLeafCount)} 个叶族 / ${escapeHtml(selected.length)} 个问题。提交后拆成 ${escapeHtml(selectedLeafCount || 0)} 个隔离任务。</span>
    </div>
  `;
  root.querySelectorAll(".leaf-issue-checkbox").forEach((node) => {
    node.addEventListener("change", () => {
      const row = state.leafIssueRows.find((item) => item.issue_id === (node.getAttribute("data-issue-id") || ""));
      if (row) row.selected = node.checked;
      renderLeafIssueSelectionTable();
      if (state.businessView) renderBusinessReadableView(state.businessView);
    });
  });
  $("historySubmitSelectedIssuesBtn")?.addEventListener("click", submitLeafIssueTasks);
}

function handleBuildLeafIssueSelection() {
  if (!state.businessView) {
    setPageStatus("请先生成业务视图。", "error");
    return;
  }
  state.leafIssueRows = buildLeafIssueRowsFromBusinessView(state.businessView);
  state.historyDistillStep = "issues";
  renderLeafIssueSelectionTable();
  renderLeafDistillTaskQueue();
  renderLeafDistillAcceptancePanel();
  renderBusinessReadableView(state.businessView);
  setPageStatus("已生成问题条目。请选择这次要处理的问题。", "info");
}

function submitLeafIssueTasks() {
  const selected = (state.leafIssueRows || []).filter((row) => row.selected);
  if (!selected.length) {
    setPageStatus("请至少选择一个问题条目。", "error");
    return;
  }
  const grouped = selected.reduce((acc, row) => {
    (acc[row.leaf_id] ||= []).push(row);
    return acc;
  }, {});
  state.leafDistillTasks = Object.entries(grouped).map(([leafId, issues], index) => ({
    task_id: `leaf_distill_${index + 1}_${leafId}`.replace(/[^\w\u4e00-\u9fa5]+/g, "_"),
    leaf_id: leafId,
    status: "待验收",
    issues,
    progress: 100,
    agent_suggestion: "建议检查本叶族前后题目差异；效果不好就提交意见继续蒸馏，效果稳定可确认发布。",
    decision: "pending",
    frozen_version: "",
    rollback_available: false,
  }));
  state.historyDistillStep = "tasks";
  state.selectedLeafTaskId = state.leafDistillTasks[0]?.task_id || "";
  renderLeafDistillTaskQueue();
  renderLeafDistillAcceptancePanel();
  if (state.businessView) renderBusinessReadableView(state.businessView);
  setPageStatus(`已按 ${state.leafDistillTasks.length} 个叶族拆分任务；任务彼此隔离。`, "info");
}

function renderLeafDistillTaskQueue() {
  const root = $("leafDistillTaskQueue");
  if (!root) return;
  const tasks = state.leafDistillTasks || [];
  if (!tasks.length) {
    root.innerHTML = `<div class="distill-empty">提交问题条目后，这里会按叶族生成隔离任务。</div>`;
    return;
  }
  const statusCounts = tasks.reduce((acc, task) => {
    acc[task.status] = (acc[task.status] || 0) + 1;
    return acc;
  }, {});
  root.innerHTML = `
    <div class="distill-detail-box">
      <strong>任务汇总</strong>
      <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-weight:800;">
        <span>总任务 ${escapeHtml(tasks.length)}</span>
        <span>排队 ${escapeHtml(statusCounts["排队中"] || 0)}</span>
        <span>蒸馏中 ${escapeHtml(statusCounts["蒸馏中"] || 0)}</span>
        <span>回归中 ${escapeHtml(statusCounts["回归中"] || 0)}</span>
        <span>待验收 ${escapeHtml(statusCounts["待验收"] || 0)}</span>
        <span>已暂存 ${escapeHtml(statusCounts["已暂存"] || 0)}</span>
        <span>已发布 ${escapeHtml(statusCounts["已发布"] || 0)}</span>
      </div>
    </div>
      <div class="distill-run-grid">
        ${tasks.map((task) => `
          <div class="distill-detail-box">
            <strong>${escapeHtml(task.leaf_id)}</strong>
            <h3 style="margin:10px 0;color:${task.status === "待验收" ? "#146c43" : "#2563eb"};">状态：${escapeHtml(task.status)}</h3>
            <div>问题：${escapeHtml(task.issues.map((item) => item.problem_name).join("、"))}</div>
            <div style="height:10px;background:#e5e7eb;margin:16px 0;border-radius:999px;overflow:hidden;">
              <div style="height:100%;width:${escapeHtml(task.progress || 0)}%;background:${task.status === "待验收" ? "#146c43" : "#2563eb"};"></div>
            </div>
            <button type="button" class="distill-secondary leaf-task-open" data-task-id="${escapeHtml(task.task_id)}">查看详情</button>
          </div>
        `).join("")}
      </div>
  `;
  root.querySelectorAll(".leaf-task-open").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedLeafTaskId = node.getAttribute("data-task-id") || "";
      state.historyDistillStep = "acceptance";
      renderLeafDistillAcceptancePanel();
      if (state.businessView) renderBusinessReadableView(state.businessView);
    });
  });
}

function renderLeafDistillAcceptancePanel() {
  const root = $("leafDistillAcceptancePanel");
  if (!root) return;
  const tasks = state.leafDistillTasks || [];
  if (!tasks.length) {
    root.innerHTML = `<div class="distill-empty">任务完成后，每个叶族会独立验收、暂存、返工或发布。</div>`;
    return;
  }
  const comparisons = (state.businessView || {}).before_after_comparisons || [];
  const selected = tasks.find((task) => task.task_id === state.selectedLeafTaskId) || tasks[0];
  state.selectedLeafTaskId = selected.task_id;
  const comparison =
    comparisons.find((item) => String(item.material_parameter?.leaf_id || item.leaf_id || "").includes(selected.leaf_id)) ||
    comparisons[0] ||
    null;
  root.innerHTML = `
    <div class="distill-run-grid" style="grid-template-columns:280px minmax(0,1fr);">
      <div class="distill-detail-box">
        <strong>任务列表</strong>
        ${tasks.map((task) => `
          <button type="button" class="${task.task_id === selected.task_id ? "distill-primary" : "distill-secondary"} leaf-task-select" data-task-id="${escapeHtml(task.task_id)}" style="width:100%;margin-top:10px;text-align:left;">
            ${escapeHtml(task.leaf_id)}　${escapeHtml(task.status)}
          </button>
        `).join("")}
        <div class="distill-inline-actions" style="margin-top:22px;">
          <button type="button" class="distill-secondary">批量发布</button>
          <span class="distill-help">需二次确认</span>
        </div>
      </div>
      <div>
        <div class="distill-detail-box">
          <strong>验收：${escapeHtml(selected.leaf_id)}</strong>
          <div>问题：${escapeHtml(selected.issues.map((item) => item.problem_name).join("、"))}</div>
          <div>频次：${escapeHtml(selected.issues.reduce((sum, item) => sum + Number(item.frequency || 0), 0))}　影响题目：${escapeHtml(Array.from(new Set(selected.issues.flatMap((item) => item.affected_items || []))).join("、") || "未提供题号")}</div>
          <div style="margin-top:10px;">调试 agent 建议：${escapeHtml(selected.agent_suggestion)}</div>
        </div>
        ${
          comparison
            ? `<div class="distill-run-grid" style="margin-top:16px;">
                <div class="distill-detail-box"><strong>改之前</strong><div style="color:#b91c1c;">${renderBeforeAfterDiff(comparison.before_question, comparison.after_question, "before")}</div><div class="distill-help">validator：${escapeHtml(comparison.validator_result_change?.split("->")[0] || "unknown")}</div></div>
                <div class="distill-detail-box"><strong>改之后</strong><div style="color:#166534;">${renderBeforeAfterDiff(comparison.before_question, comparison.after_question, "after")}</div><div class="distill-help">validator：${escapeHtml(comparison.validator_result_change?.split("->")[1] || "unknown")}</div></div>
              </div>`
            : `<div class="distill-detail-box" style="margin-top:16px;">缺少 before/after 对比。可先暂存，补齐 diff 后再验收。</div>`
        }
        <div class="distill-detail-box" style="margin-top:16px;">
          <strong>当前任务操作</strong>
          <div class="distill-inline-actions" style="margin-top:12px;">
            <button type="button" class="distill-secondary leaf-task-feedback" data-task-id="${escapeHtml(selected.task_id)}">提交意见继续蒸馏</button>
            <button type="button" class="distill-secondary leaf-task-hold" data-task-id="${escapeHtml(selected.task_id)}">暂存下次继续</button>
            <button type="button" class="distill-primary leaf-task-publish" data-task-id="${escapeHtml(selected.task_id)}">确认发布</button>
            <span class="distill-help">确认发布会冻结当前版本；发布后可回退，不影响其他叶族任务。</span>
          </div>
          ${selected.rollback_available ? `<div class="distill-help">已冻结版本：${escapeHtml(selected.frozen_version)}；可回退。</div>` : ""}
        </div>
      </div>
    </div>
  `;
  root.querySelectorAll(".leaf-task-select").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedLeafTaskId = node.getAttribute("data-task-id") || "";
      renderLeafDistillAcceptancePanel();
    });
  });
  root.querySelectorAll(".leaf-task-feedback").forEach((node) => node.addEventListener("click", () => updateLeafTaskDecision(node.getAttribute("data-task-id"), "继续蒸馏")));
  root.querySelectorAll(".leaf-task-hold").forEach((node) => node.addEventListener("click", () => updateLeafTaskDecision(node.getAttribute("data-task-id"), "暂存")));
  root.querySelectorAll(".leaf-task-publish").forEach((node) => node.addEventListener("click", () => confirmLeafTaskPublish(node.getAttribute("data-task-id"))));
}

function updateLeafTaskDecision(taskId, decision) {
  const task = state.leafDistillTasks.find((item) => item.task_id === taskId);
  if (!task) return;
  task.decision = decision;
  task.status = decision === "暂存" ? "已暂存" : "需继续蒸馏";
  state.historyDistillStep = "acceptance";
  renderLeafDistillTaskQueue();
  renderLeafDistillAcceptancePanel();
  if (state.businessView) renderBusinessReadableView(state.businessView);
  setPageStatus(`${task.leaf_id} 已标记为：${decision}。`, "info");
}

function confirmLeafTaskPublish(taskId) {
  const task = state.leafDistillTasks.find((item) => item.task_id === taskId);
  if (!task) return;
  if (!window.confirm(`确认发布 ${task.leaf_id}？系统会冻结当前版本，发布后仍可回退。`)) return;
  task.decision = "发布";
  task.status = "已发布";
  task.frozen_version = `${task.leaf_id}@${new Date().toISOString()}`;
  task.rollback_available = true;
  state.historyDistillStep = "acceptance";
  renderLeafDistillTaskQueue();
  renderLeafDistillAcceptancePanel();
  if (state.businessView) renderBusinessReadableView(state.businessView);
  setPageStatus(`${task.leaf_id} 已冻结当前版本并发布。`, "info");
}

function renderBusinessSummaryMarkdown(summary) {
  const firstEdit = summary.high_frequency_edit_fields?.[0];
  const firstFeedback = summary.high_frequency_user_feedback?.[0];
  const lines = [
    "# Behavior Distillation Business Summary",
    "",
    "> 业务蒸馏结果是 evidence，不是正式配置；高频修改不等于自动改题卡，这里不会调用 executor。",
    "",
    "## 审核总体情况",
    "",
    `- 审核动作: ${summary.source.review_count}`,
    `- 补丁动作: ${summary.source.patch_count}`,
    `- 总体质量信号: ${summary.business_overview.overall_quality_signal}`,
    "",
    "## 人话摘要",
    "",
    firstEdit && firstFeedback
      ? `系统观察到：用户多次修改 ${firstEdit.field}，并反复指出“${firstFeedback.feedback}”。这个信号可能指向结构性问题，建议作为 formalization packet 的候选 evidence，但不能直接写回。`
      : "当前修改样本不足，不能沉淀为正式规则，只建议继续观察。",
    "",
    "## 候选沉淀建议",
    "",
    ...(summary.candidate_improvement_signals.length
      ? summary.candidate_improvement_signals.map((item) => `- ${item.business_description} target_layer=${item.target_layer}, status=${item.recommended_status}。${item.reason}`)
      : ["- 暂无候选沉淀建议。"]),
    "",
    "## 下一步建议",
    "",
    `- ${summary.recommended_next_action}`,
    "- 正式落位仍需 formalization packet、readiness gate、人审、回归和受控写回。",
  ];
  return `${lines.join("\n")}\n`;
}

function renderBusinessSummary(summary, markdown) {
  $("businessSummaryJson").value = prettyJson(summary);
  $("businessSummaryMarkdown").value = markdown;
  const edits = summary.high_frequency_edit_fields || [];
  const signals = summary.candidate_improvement_signals || [];
  $("businessSummaryHumanPreview").innerHTML = `
    <div class="distill-detail-box">
      <strong>业务可读总结已生成</strong>
      <div>本次共识别 ${escapeHtml(edits.length)} 类高频修改和 ${escapeHtml(signals.length)} 条候选沉淀建议。完整 JSON 已放入下方“技术详情”折叠区。</div>
      <div class="distill-help">业务蒸馏结果是 evidence，不是正式配置；这里不会调用 executor。</div>
    </div>
  `;
}

async function handleGenerateBusinessSummary(event) {
  event.preventDefault();
  try {
    const packet = parseJsonField($("businessSummaryBehaviorPacketJson").value, "behavior packet JSON", state.behaviorPacket || {});
    const feedback = parseJsonField($("businessSummaryFeedbackJson").value, "agent_review_feedback_normalized JSON", {});
    const beforeAfter = parseJsonField($("businessSummaryBeforeAfterJson").value, "前后题目对比 JSON", []);
    const summary = buildBehaviorBusinessSummary(packet, feedback);
    const view = buildBehaviorBusinessView(summary, beforeAfter, packet);
    view.family_context.stage = businessViewStageLabel($("businessViewStage").value);
    applyBusinessViewLeafScope(view, parseBusinessViewLeafSelection());
    state.businessSummary = summary;
    state.businessSummaryMarkdown = renderBusinessSummaryMarkdown(summary);
    state.businessView = view;
    state.businessViewMarkdown = renderBusinessViewMarkdown(view);
    state.historyDistillStep = "issues";
    state.leafIssueRows = buildLeafIssueRowsFromBusinessView(view);
    $("businessViewJson").value = prettyJson(view);
    $("businessViewMarkdown").value = state.businessViewMarkdown;
    renderBusinessReadableView(view);
    renderLeafIssueSelectionTable();
    renderLeafDistillTaskQueue();
    renderLeafDistillAcceptancePanel();
    renderBusinessSummary(summary, state.businessSummaryMarkdown);
    setPageStatus("已生成业务蒸馏总览。它只是 evidence，不会写回或调用 executor。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

async function copyBusinessSummaryOutput(id, label) {
  const text = $(id).value;
  if (!text.trim()) {
    setPageStatus(`请先生成 ${label}。`, "error");
    return;
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    $(id).select();
    document.execCommand("copy");
  }
  setPageStatus(`${label} 已复制。`, "info");
}

function downloadBusinessSummaryOutput(id, filename, type) {
  const text = $(id).value;
  if (!text.trim()) {
    setPageStatus(`请先生成 ${filename}。`, "error");
    return;
  }
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setPageStatus(`${filename} 已下载。`, "info");
}

function refreshSelectOptions() {
  const datasetOptions = ['<option value="">未选择</option>']
    .concat(state.datasets.map((item) => `<option value="${escapeHtml(item.dataset_id)}">${escapeHtml(item.title || item.dataset_id)}</option>`))
    .join("");
  $("sessionDatasetId").innerHTML = datasetOptions;
  $("sessionDatasetId").value = state.selectedDatasetId || "";

  const sessionOptions = ['<option value="">未选择</option>']
    .concat(state.sessions.map((item) => `<option value="${escapeHtml(item.session_id)}">${escapeHtml(item.title || item.session_id)}</option>`))
    .join("");
  $("trialSessionId").innerHTML = sessionOptions;
  $("trialSessionId").value = state.selectedSessionId || "";

  const reviewOptions = ['<option value="">未选择</option>']
    .concat(
      state.sessions.flatMap((session) =>
        (session.runs || []).map(
          (run) =>
            `<option value="${escapeHtml(run.run_id)}">${escapeHtml(session.title || session.session_id)} / 第 ${escapeHtml(run.run_no)} 轮</option>`,
        ),
      ),
    )
    .join("");
  $("reviewRunId").innerHTML = reviewOptions;
  $("reviewRunId").value = state.selectedRunId || "";
  $("patchRunId").innerHTML = reviewOptions;
  $("patchRunId").value = state.selectedRunId || "";
  $("axisPatchRunId").innerHTML = reviewOptions;
  $("axisPatchRunId").value = state.selectedRunId || "";
  $("promoteRunId").innerHTML = reviewOptions;
  $("promoteRunId").value = state.selectedRunId || "";
}

async function loadDatasets() {
  const payload = await apiFetch("/api/v1/distill/datasets?limit=100");
  state.datasets = payload.items || [];
  if (!state.selectedDatasetId && state.datasets.length) {
    state.selectedDatasetId = state.datasets[0].dataset_id;
  }
  renderDatasets();
  refreshSelectOptions();
}

async function loadSessions() {
  const payload = await apiFetch("/api/v1/distill/sessions?limit=100");
  const items = payload.items || [];
  state.sessions = await Promise.all(
    items.map(async (item) => {
      try {
        return await apiFetch(`/api/v1/distill/sessions/${encodeURIComponent(item.session_id)}`);
      } catch {
        return item;
      }
    }),
  );
  if (!state.selectedSessionId && state.sessions.length) {
    state.selectedSessionId = state.sessions[0].session_id;
  }
  renderSessions();
  refreshSelectOptions();

  if (state.selectedSessionId) {
    const selected = state.sessions.find((item) => item.session_id === state.selectedSessionId);
    const firstRun = selected?.runs?.[0];
    if (firstRun && !state.selectedRunId) {
      state.selectedRunId = firstRun.run_id;
    }
  }
}

async function selectSession(sessionId) {
  if (!sessionId) return;
  const detail = await apiFetch(`/api/v1/distill/sessions/${encodeURIComponent(sessionId)}`);
  state.sessions = state.sessions.map((item) => (item.session_id === sessionId ? detail : item));
  renderSessions();
  refreshSelectOptions();
  if (Array.isArray(detail.runs) && detail.runs.length) {
    state.selectedRunId = detail.runs[0].run_id;
    $("reviewRunId").value = state.selectedRunId;
    await loadRun(state.selectedRunId);
  } else {
    state.selectedRunId = "";
    state.currentRun = null;
    renderRunDetail(null);
    refreshSelectOptions();
  }
}

async function loadRun(runId) {
  if (!runId) {
    state.currentRun = null;
    renderRunDetail(null);
    return;
  }
  state.currentRun = await apiFetch(`/api/v1/distill/runs/${encodeURIComponent(runId)}`);
  state.selectedRunId = runId;
  renderRunDetail(state.currentRun);
  refreshSelectOptions();
}

async function refreshAll() {
  await loadDatasets();
  await loadSessions();
  if (state.selectedRunId) {
    await loadRun(state.selectedRunId);
  } else {
    renderRunDetail(null);
  }
}

function fillTemplates() {
  $("datasetTitle").value = "主旨题起始样本集";
  $("datasetQuestionType").value = "main_idea";
  $("datasetBusinessSubtype").value = "center_understanding";
  $("datasetDescription").value = "一套用于主旨题题卡微调的起始样本。";
  $("datasetSamples").value = prettyJson([
    {
      sample_key: "sample-dev-01",
      split: "dev",
      truth_source_question: {
        passage: "这段材料认为，治理既需要效率，也需要公平。",
        stem: "下列选项中，最能概括这段材料主旨的是：",
        options: {
          A: "治理应当兼顾效率与公平。",
          B: "技术可以替代治理。",
          C: "增加投入能够解决一切问题。",
          D: "市场机制最重要。",
        },
        answer: "A",
        analysis: "材料强调效率与公平的平衡，而不是单一极端。",
      },
      generation_request: {
        question_focus: "center_understanding",
        business_subtype: "center_understanding",
        difficulty_level: "medium",
        count: 1,
        topic: "治理",
      },
    },
  ]);

  $("sessionTitle").value = "主旨题题卡微调";
  $("sessionQuestionType").value = "main_idea";
  $("sessionBusinessSubtype").value = "center_understanding";
  $("sessionGoal").value = "先让 dev 上的主旨题拟合稳定，再观察 test 是否还能保持。";
  $("sessionBaselineRequest").value = prettyJson({
    question_focus: "center_understanding",
    business_subtype: "center_understanding",
    difficulty_level: "medium",
    count: 1,
    topic: "治理",
  });

  $("trialLabel").value = "基线开发集检查";
  $("trialHypothesis").value = "当前基线请求在开发集上应该先跑到可接受的拟合度。";
  $("reviewSummary").value = "如果测试集也稳定，可以考虑沉淀。";
  $("patchTitle").value = "收紧题卡控制槽位";
  $("patchSummary").value = "把本轮观察到的拟合改动显式记录成补丁。";
  $("patchPayload").value = prettyJson({
    prompt_patch: {
      instruction: "优先贴近选项措辞",
    },
  });
  $("axisManifestJson").value = prettyJson({
    job_id: "leaf_pre_distill_demo",
    mother_family_id: "word_usage",
    child_family_id: "word_usage_content_word",
    leaf_label: "实词",
  });
  $("bootstrapDiscoveryJson").value = prettyJson({
    discovery_version: "v1",
    enabled: true,
    status: "hypothesis_only",
    promotion_allowed: false,
    proto_mother_family: { label: "word_usage", status: "hypothesis" },
    candidate_axes: [
      {
        axis: "explanation_target_type",
        description: "识别被解释对象是词语、短语、概念，还是语境中的指代对象。",
        support_estimate: "high",
        status: "hypothesis",
        risk: "可能把多种解释对象合并得过宽。",
      },
      {
        axis: "referent_resolution_mode",
        description: "通过局部上下文解释词语或短语。",
        support_estimate: "medium",
        status: "hypothesis",
        risk: "可能与语境含义模式重叠。",
      },
    ],
    distractor_taxonomy: [
      {
        mode: "context_detached",
        description: "脱离材料语境解释目标词语。",
        status: "hypothesis",
      },
    ],
  });
  renderAxisDecisionRows(parseJsonField($("bootstrapDiscoveryJson").value, "启动发现 JSON", {}));
  $("promoteSummary").value = "把审核通过且补丁齐全的运行打包成正式沉淀候选。";
  $("behaviorQuestionType").value = "sentence_fill";
  $("behaviorQuestionCardId").value = "sentence_fill_middle_bridge";
  $("behaviorLimit").value = "20";
}

async function handleCreateDataset(event) {
  event.preventDefault();
  const button = $("createDatasetBtn");
  withButtonLoading(button, true);
  setPageStatus("正在创建样本集...", "info");
  try {
    const samples = parseJsonField($("datasetSamples").value, "样本 JSON", []);
    const payload = {
      title: $("datasetTitle").value.trim(),
      description: $("datasetDescription").value.trim() || null,
      question_card_id: $("datasetCardId").value.trim() || null,
      question_type: $("datasetQuestionType").value.trim() || null,
      business_subtype: $("datasetBusinessSubtype").value.trim() || null,
      split_mode: $("datasetSplitMode").value,
      samples: withExperimentalProtoRouteSamples(samples, $("datasetExperimentalProtoRoute").checked),
    };
    const dataset = await apiFetch("/api/v1/distill/datasets", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedDatasetId = dataset.dataset_id;
    await loadDatasets();
    $("sessionDatasetId").value = dataset.dataset_id;
    setPageStatus(`样本集已创建：${dataset.title}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handleCreateSession(event) {
  event.preventDefault();
  const button = $("createSessionBtn");
  withButtonLoading(button, true);
  setPageStatus("正在创建蒸馏会话...", "info");
  try {
    const baselineRequest = parseJsonField($("sessionBaselineRequest").value, "基线请求 JSON", null);
    const truthSourceQuestion = parseJsonField($("sessionTruthSourceQuestion").value, "真题样本 JSON", null);
    const payload = {
      title: $("sessionTitle").value.trim(),
      mode: $("sessionMode").value,
      goal: $("sessionGoal").value.trim() || null,
      dataset_id: $("sessionDatasetId").value || null,
      question_type: $("sessionQuestionType").value.trim() || null,
      business_subtype: $("sessionBusinessSubtype").value.trim() || null,
      baseline_request: baselineRequest,
      truth_source_question: truthSourceQuestion,
    };
    const session = await apiFetch("/api/v1/distill/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedSessionId = session.session_id;
    await loadSessions();
    $("trialSessionId").value = session.session_id;
    setPageStatus(`蒸馏会话已创建：${session.title}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handleRunTrial(event) {
  event.preventDefault();
  const button = $("runTrialBtn");
  const sessionId = $("trialSessionId").value;
  if (!sessionId) {
    setPageStatus("请先选择一条蒸馏会话，再运行试验。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在运行试验，这一步会真正调用生题服务...", "info");
  try {
    const request = withExperimentalProtoRoute(
      parseJsonField($("trialRequest").value, "试验请求 JSON", null),
      $("trialExperimentalProtoRoute").checked
    );
    const payload = {
      request,
      label: $("trialLabel").value.trim() || null,
      hypothesis: $("trialHypothesis").value.trim() || null,
      split: $("trialSplit").value,
      sample_id: $("trialSampleId").value.trim() || null,
      sample_limit: Number($("trialSampleLimit").value || 1),
    };
    const run = await apiFetch(`/api/v1/distill/sessions/${encodeURIComponent(sessionId)}/trials`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedSessionId = sessionId;
    state.selectedRunId = run.run_id;
    await loadSessions();
    await loadRun(run.run_id);
    setPageStatus(`试验已完成：第 ${run.run_no} 轮 / ${run.status}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handleSubmitReview(event) {
  event.preventDefault();
  const button = $("submitReviewBtn");
  const runId = $("reviewRunId").value;
  if (!runId) {
    setPageStatus("请先选择一条运行，再提交审核。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在提交人工审核...", "info");
  try {
    const allowPromote = $("reviewAllowPromote").checked;
    const promotionTargets = Array.from(document.querySelectorAll(".review-target:checked")).map((node) => node.value);
    const payload = {
      verdict: $("reviewVerdict").value,
      summary: $("reviewSummary").value.trim() || null,
      reason: $("reviewReason").value.trim() || null,
      reviewer: $("reviewReviewer").value.trim() || null,
      allow_promote: allowPromote,
      promotion_targets: promotionTargets,
    };
    const run = await apiFetch(`/api/v1/distill/runs/${encodeURIComponent(runId)}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedRunId = run.run_id;
    await loadSessions();
    await loadRun(run.run_id);
    setPageStatus(`审核已提交：${run.latest_review?.verdict || payload.verdict}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handleSubmitPatch(event) {
  event.preventDefault();
  const button = $("submitPatchBtn");
  const runId = $("patchRunId").value;
  if (!runId) {
    setPageStatus("请先选择一条运行，再记录补丁。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在记录补丁...", "info");
  try {
    const patchPayload = parseJsonField($("patchPayload").value, "补丁 JSON", {});
    const payload = {
      target: $("patchTarget").value,
      title: $("patchTitle").value.trim(),
      summary: $("patchSummary").value.trim() || null,
      scope_key: $("patchScopeKey").value.trim() || null,
      patch: patchPayload,
      author: $("patchAuthor").value.trim() || null,
    };
    const run = await apiFetch(`/api/v1/distill/runs/${encodeURIComponent(runId)}/patches`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedRunId = run.run_id;
    await loadSessions();
    await loadRun(run.run_id);
    setPageStatus(`补丁已记录：${payload.title}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

function handleLoadBootstrapDiscovery() {
  try {
    state.bootstrapDiscovery = parseJsonField($("bootstrapDiscoveryJson").value, "启动发现 JSON", {});
    renderAxisDecisionRows(state.bootstrapDiscovery);
    const count = axisSourceRows(state.bootstrapDiscovery).length;
    setPageStatus(`已载入 ${count} 条候选轴 / 干扰项分类，等待人工确认。`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleGenerateAxisConfirmation() {
  try {
    const manifest = parseJsonField($("axisManifestJson").value, "清单 JSON", {});
    const discovery = state.bootstrapDiscovery || parseJsonField($("bootstrapDiscoveryJson").value, "启动发现 JSON", {});
    const decisionPayload = collectAxisDecisionPayload();
    state.axisConfirmation = buildAxisConfirmationArtifact(manifest, discovery, decisionPayload);
    $("axisConfirmationJson").value = prettyJson(state.axisConfirmation);
    setPageStatus("已生成候选轴确认文件；它只是原型确认证据，不是正式配置。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleGenerateFormalPatchDraft() {
  try {
    const manifest = parseJsonField($("axisManifestJson").value, "清单 JSON", {});
    const confirmation = parseJsonField($("axisConfirmationJson").value, "候选轴确认 JSON", state.axisConfirmation || {});
    state.formalPatchDraft = buildFormalPatchDraftArtifact(manifest, confirmation);
    $("formalPatchDraftJson").value = prettyJson(state.formalPatchDraft);
    setPageStatus("已生成正式补丁草案预览；它只是一份草案，仍然禁止写回。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleGenerateWritebackPreview() {
  try {
    const draft = parseJsonField($("formalPatchDraftJson").value, "正式补丁草案 JSON", state.formalPatchDraft || {});
    if (draft.writeback_allowed !== false || draft.formalized !== false) {
      throw new Error("生成写回预览前，正式补丁草案必须保持禁止写回且未正式化。");
    }
    state.formalWritebackPlan = buildFormalWritebackPlanArtifact(draft, $("axisPatchAuthor").value.trim() || null);
    state.formalWritebackDiff = renderFormalWritebackDiff(state.formalWritebackPlan);
    $("formalWritebackPlanJson").value = prettyJson(state.formalWritebackPlan);
    $("formalWritebackDiffMd").value = state.formalWritebackDiff;
    setPageStatus("已生成写回计划和差异预览；没有改动任何文件。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

function handleCopyWritebackPlanToLeafPatch() {
  try {
    const manifest = parseJsonField($("axisManifestJson").value, "清单 JSON", {});
    const plan = parseJsonField($("formalWritebackPlanJson").value, "正式写回计划 JSON", state.formalWritebackPlan || {});
    if (plan.writeback_allowed !== false || plan.requires_explicit_approval !== true) {
      throw new Error("写回计划必须保持仅预览状态，并要求显式批准。");
    }
    const artifactBase = manifest.output_dir || manifest.artifact_dir || `data/leaf_pre_distill/${manifest.job_id || "<job_id>"}`;
    $("patchTarget").value = "leaf_pre_distill_report";
    $("patchTitle").value = "挂载正式写回预览证据";
    $("patchSummary").value =
      "把正式补丁草案、写回计划和差异预览路径作为叶族预蒸馏报告证据挂载；不会执行正式写回。";
    $("patchScopeKey").value = manifest.job_id || plan.proto_child_family || "";
    $("patchPayload").value = prettyJson({
      artifact_type: "leaf_pre_distill_report",
      artifact_path: `${artifactBase}/report.md`,
      formal_patch_draft_path: `${artifactBase}/formal_patch_draft.json`,
      formal_writeback_plan_path: `${artifactBase}/formal_writeback_plan.json`,
      formal_writeback_diff_path: `${artifactBase}/formal_writeback_diff.md`,
      writeback_allowed: false,
      requires_explicit_approval: true,
      proto_family: plan.proto_family || null,
      proto_child_family: plan.proto_child_family || null,
      preview_status: plan.status || "preview_only",
    });
    setPageStatus("叶族报告补丁已填入写回预览附件路径。确认后可以提交补丁。", "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  }
}

async function handleCreateCanonicalPatches() {
  const button = $("createCanonicalPatchesBtn");
  const runId = $("axisPatchRunId").value || state.selectedRunId;
  if (!runId) {
    setPageStatus("创建规范目标补丁前，请先选择目标运行。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在根据已编辑的正式补丁草案预览创建规范目标补丁...", "info");
  try {
    const draft = parseJsonField($("formalPatchDraftJson").value, "正式补丁草案 JSON", {});
    if (draft.writeback_allowed !== false || draft.formalized !== false) {
      throw new Error("正式补丁草案必须保持禁止写回且未正式化。");
    }
    const patches = Array.isArray(draft.target_patches) ? draft.target_patches : [];
    const allowed = patches.filter((patch) => AXIS_DRAFT_TARGETS.includes(patch.target));
    if (!allowed.length) {
      throw new Error("正式补丁草案里没有可创建的规范目标补丁。");
    }
    for (const patch of allowed) {
      await apiFetch(`/api/v1/distill/runs/${encodeURIComponent(runId)}/patches`, {
        method: "POST",
        body: JSON.stringify({
          target: patch.target,
          title: `来自候选轴确认的 ${patch.target} 草案`,
          summary: "由正式补丁草案预览生成的规范目标补丁，仅草案用途，不会写正式文件。",
          scope_key: patch.scope_key || null,
          patch: patch.patch || {},
          author: $("axisPatchAuthor").value.trim() || null,
        }),
      });
    }
    await loadSessions();
    await loadRun(runId);
    setPageStatus(`已创建 ${allowed.length} 个规范目标补丁；没有写回正式题卡。`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handlePromoteRun(event) {
  event.preventDefault();
  const button = $("submitPromoteBtn");
  const runId = $("promoteRunId").value;
  if (!runId) {
    setPageStatus("请先选择一条运行，再生成沉淀包。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在生成沉淀包...", "info");
  try {
    const targets = Array.from(document.querySelectorAll(".promote-target:checked")).map((node) => node.value);
    const payload = {
      targets,
      summary: $("promoteSummary").value.trim() || null,
      promoter: $("promotePromoter").value.trim() || null,
    };
    const run = await apiFetch(`/api/v1/distill/runs/${encodeURIComponent(runId)}/promote`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedRunId = run.run_id;
    await loadSessions();
    await loadRun(run.run_id);
    setPageStatus(`沉淀包已生成：${run.latest_promotion?.artifact_path || "就绪"}`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

async function handleBuildBehaviorPacket(event) {
  event.preventDefault();
  const button = $("buildBehaviorPacketBtn");
  withButtonLoading(button, true);
  setPageStatus("正在提取历史版本动作，生成行为蒸馏包...", "info");
  try {
    const payload = {
      item_id: $("behaviorItemId").value.trim() || null,
      question_type: $("behaviorQuestionType").value.trim() || null,
      question_card_id: $("behaviorQuestionCardId").value.trim() || null,
      limit: Number($("behaviorLimit").value || 20),
      include_item_traces: $("behaviorIncludeTraces").checked,
    };
    state.behaviorRequest = payload;
    state.behaviorPacket = await apiFetch("/api/v1/distill/behavior/packets", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("businessSummaryBehaviorPacketJson").value = prettyJson(state.behaviorPacket);
    renderBehaviorPacket(state.behaviorPacket);
    setPageStatus(`行为蒸馏包已生成：覆盖 ${state.behaviorPacket.aggregate_summary?.item_count ?? 0} 道题。`, "info");
  } catch (error) {
    setPageStatus(error.message, "error");
  } finally {
    withButtonLoading(button, false);
  }
}

function bindEvents() {
  $("datasetForm").addEventListener("submit", handleCreateDataset);
  $("sessionForm").addEventListener("submit", handleCreateSession);
  $("trialForm").addEventListener("submit", handleRunTrial);
  $("reviewForm").addEventListener("submit", handleSubmitReview);
  $("patchForm").addEventListener("submit", handleSubmitPatch);
  $("promoteForm").addEventListener("submit", handlePromoteRun);
  $("behaviorForm").addEventListener("submit", handleBuildBehaviorPacket);
  $("businessSummaryForm").addEventListener("submit", handleGenerateBusinessSummary);
  $("loadBusinessViewExistingBtn").addEventListener("click", handleLoadBusinessViewExisting);
  $("startBusinessViewLongTaskBtn").addEventListener("click", handleStartBusinessViewLongTask);
  $("buildLeafIssueSelectionBtn").addEventListener("click", handleBuildLeafIssueSelection);
  $("submitLeafIssueTasksBtn").addEventListener("click", submitLeafIssueTasks);
  $("copyBusinessSummaryJsonBtn").addEventListener("click", () => copyBusinessSummaryOutput("businessSummaryJson", "behavior_distillation_business_summary.json"));
  $("downloadBusinessSummaryJsonBtn").addEventListener("click", () => downloadBusinessSummaryOutput("businessSummaryJson", "behavior_distillation_business_summary.json", "application/json"));
  $("copyBusinessSummaryMarkdownBtn").addEventListener("click", () => copyBusinessSummaryOutput("businessSummaryMarkdown", "behavior_distillation_business_report.md"));
  $("downloadBusinessSummaryMarkdownBtn").addEventListener("click", () => downloadBusinessSummaryOutput("businessSummaryMarkdown", "behavior_distillation_business_report.md", "text/markdown"));
  $("axisConfirmForm").addEventListener("submit", (event) => event.preventDefault());
  $("writebackPreviewForm").addEventListener("submit", (event) => event.preventDefault());
  $("sourceCandidateReviewForm").addEventListener("submit", (event) => event.preventDefault());
  $("loadBootstrapDiscoveryBtn").addEventListener("click", handleLoadBootstrapDiscovery);
  $("generateAxisConfirmationBtn").addEventListener("click", handleGenerateAxisConfirmation);
  $("generateFormalPatchDraftBtn").addEventListener("click", handleGenerateFormalPatchDraft);
  $("generateWritebackPreviewBtn").addEventListener("click", handleGenerateWritebackPreview);
  $("copyWritebackPlanToLeafPatchBtn").addEventListener("click", handleCopyWritebackPlanToLeafPatch);
  $("createCanonicalPatchesBtn").addEventListener("click", handleCreateCanonicalPatches);
  $("loadSourceCandidatesBtn").addEventListener("click", handleLoadSourceCandidates);
  $("fillMockSourceCandidatesBtn").addEventListener("click", handleFillMockSourceCandidates);
  $("batchRejectQuestionBankBtn").addEventListener("click", () => handleBatchSourceDecision("reject_question_bank"));
  $("batchDeferSourcesBtn").addEventListener("click", () => handleBatchSourceDecision("defer"));
  $("sourceRiskFilter").addEventListener("change", () => {
    saveSourceReviewEdits();
    renderSourceCandidateReviewList();
  });
  $("generateSourceReviewDecisionsBtn").addEventListener("click", handleGenerateSourceReviewDecisions);
  $("copySourceReviewDecisionsBtn").addEventListener("click", handleCopySourceReviewDecisions);
  $("downloadSourceReviewDecisionsBtn").addEventListener("click", handleDownloadSourceReviewDecisions);
  $("agentReviewFeedbackForm").addEventListener("submit", (event) => event.preventDefault());
  $("generateAgentFeedbackInputBtn").addEventListener("click", handleGenerateAgentReviewFeedbackInput);
  $("copyAgentFeedbackInputBtn").addEventListener("click", handleCopyAgentReviewFeedbackInput);
  $("downloadAgentFeedbackInputBtn").addEventListener("click", handleDownloadAgentReviewFeedbackInput);
  $("formalizationGatePreviewForm").addEventListener("submit", (event) => event.preventDefault());
  $("generateFormalGatePreviewBtn").addEventListener("click", handleGenerateFormalizationGatePreview);
  $("fillBlockedFormalGateExampleBtn").addEventListener("click", handleFillBlockedFormalGateExample);
  $("copyFormalGatePacketPreviewBtn").addEventListener("click", () =>
    copyFormalGateOutput("formalGatePacketPreviewJson", "Packet Preview JSON")
  );
  $("copyFormalGateReadinessPreviewBtn").addEventListener("click", () =>
    copyFormalGateOutput("formalGateReadinessPreviewJson", "Readiness Checklist Preview JSON")
  );
  $("downloadFormalGatePreviewBtn").addEventListener("click", handleDownloadFormalGatePreview);
  $("clearFormalGatePreviewBtn").addEventListener("click", handleClearFormalGateInputs);
  $("businessModeForm").addEventListener("submit", (event) => event.preventDefault());
  $("businessQuestionPackFile").addEventListener("change", handleBusinessQuestionPackFile);
  $("businessRunParseBtn").addEventListener("click", () => {
    setBusinessLoading(true, "正在解析题包并生成材料准备报告...");
    window.setTimeout(() => {
      renderBusinessModePreview(buildBusinessModePreview());
      setBusinessLoading(false);
      setPageStatus("已生成题包准备报告。", "info");
    }, 450);
  });
  $("generateBusinessModeReportBtn").addEventListener("click", handleGenerateBusinessModeReport);
  $("fillBusinessModeExampleBtn").addEventListener("click", handleFillBusinessModeExample);
  $("copyBusinessModeReportBtn").addEventListener("click", handleCopyBusinessModeReport);
  $("businessApproveBtn").addEventListener("click", () => handleBusinessFinalDecision("approve"));
  $("businessDeferBtn").addEventListener("click", () => handleBusinessFinalDecision("defer"));
  $("businessRerunBtn").addEventListener("click", () => handleBusinessFinalDecision("rerun"));
  document.querySelectorAll(".business-stage-btn").forEach((button) => {
    button.addEventListener("click", () => setBusinessStage(button.dataset.businessStageTarget || "prep"));
  });
  document.querySelectorAll(".business-next-stage").forEach((button) => {
    button.addEventListener("click", () => transitionBusinessStage(button.dataset.businessNextStage || "prep", `正在进入${businessStageTitle(button.dataset.businessNextStage || "prep")}...`));
  });
  document.querySelectorAll(".workbench-layer-btn").forEach((button) => {
    button.addEventListener("click", () => setWorkbenchLayer(button.dataset.workbenchLayerTarget || WORKBENCH_DEFAULT_LAYER));
  });
  $("saveWorkbenchDraftBtn").addEventListener("click", saveWorkbenchDraft);
  $("restoreWorkbenchDraftBtn").addEventListener("click", restoreWorkbenchDraft);
  $("clearWorkbenchDraftBtn").addEventListener("click", clearWorkbenchDraft);
  $("exitWorkbenchBtn").addEventListener("click", exitWorkbench);

  $("refreshAllBtn").addEventListener("click", async () => {
    setPageStatus("正在刷新样本集、会话和运行...", "info");
    try {
      await refreshAll();
      setPageStatus("已刷新。", "info");
    } catch (error) {
      setPageStatus(error.message, "error");
    }
  });
  $("fillTemplatesBtn").addEventListener("click", fillTemplates);
  $("refreshDatasetsBtn").addEventListener("click", async () => {
    try {
      await loadDatasets();
      setPageStatus("样本集列表已刷新。", "info");
    } catch (error) {
      setPageStatus(error.message, "error");
    }
  });
  $("refreshSessionsBtn").addEventListener("click", async () => {
    try {
      await loadSessions();
      setPageStatus("蒸馏会话列表已刷新。", "info");
    } catch (error) {
      setPageStatus(error.message, "error");
    }
  });
  $("refreshRunBtn").addEventListener("click", async () => {
    try {
      await loadRun($("reviewRunId").value || state.selectedRunId);
      setPageStatus("当前运行已刷新。", "info");
    } catch (error) {
      setPageStatus(error.message, "error");
    }
  });
  $("refreshBehaviorBtn").addEventListener("click", async () => {
    if (!state.behaviorRequest) {
      renderBehaviorPacket(null);
      setPageStatus("还没有行为蒸馏请求，先在左边生成一次。", "info");
      return;
    }
    try {
      state.behaviorPacket = await apiFetch("/api/v1/distill/behavior/packets", {
        method: "POST",
        body: JSON.stringify(state.behaviorRequest),
      });
      $("businessSummaryBehaviorPacketJson").value = prettyJson(state.behaviorPacket);
      renderBehaviorPacket(state.behaviorPacket);
      setPageStatus("行为蒸馏包已刷新。", "info");
    } catch (error) {
      setPageStatus(error.message, "error");
    }
  });

  $("trialSessionId").addEventListener("change", async (event) => {
    const sessionId = event.target.value || "";
    state.selectedSessionId = sessionId;
    if (sessionId) {
      await selectSession(sessionId);
    }
  });

  $("reviewRunId").addEventListener("change", async (event) => {
    const runId = event.target.value || "";
    if (runId) {
      await loadRun(runId);
    }
  });
  $("patchRunId").addEventListener("change", async (event) => {
    const runId = event.target.value || "";
    if (runId) {
      await loadRun(runId);
    }
  });
  $("axisPatchRunId").addEventListener("change", async (event) => {
    const runId = event.target.value || "";
    if (runId) {
      await loadRun(runId);
    }
  });
  $("promoteRunId").addEventListener("change", async (event) => {
    const runId = event.target.value || "";
    if (runId) {
      await loadRun(runId);
    }
  });
}

async function init() {
  assignWorkbenchPanelLayers();
  bindEvents();
  fillTemplates();
  renderBehaviorPacket(null);
  renderSourceCandidateReviewList();
  renderFormalizationGateSummary({ status: "blocked", readinessPreview: emptyPreviewArtifact("blocked") });
  if (loadStoredWorkbenchDraft()) {
    restoreWorkbenchDraft({ silent: true });
  } else {
    setWorkbenchLayer(WORKBENCH_DEFAULT_LAYER);
  }
  setPageStatus("正在加载蒸馏训练工作台...", "info");
  try {
    await refreshAll();
    setPageStatus("蒸馏训练工作台已就绪。先看左边示例，按你的数据替换 JSON 就可以直接跑。", "info");
  } catch (error) {
    setPageStatus(`初始化失败：${error.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);
