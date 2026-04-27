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
  sourceCandidates: [],
  sourceCandidateReviews: {},
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
  bindEvents();
  fillTemplates();
  renderBehaviorPacket(null);
  renderSourceCandidateReviewList();
  setPageStatus("正在加载蒸馏训练工作台...", "info");
  try {
    await refreshAll();
    setPageStatus("蒸馏训练工作台已就绪。先看左边示例，按你的数据替换 JSON 就可以直接跑。", "info");
  } catch (error) {
    setPageStatus(`初始化失败：${error.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);
