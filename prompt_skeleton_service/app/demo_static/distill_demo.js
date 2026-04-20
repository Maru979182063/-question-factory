const state = {
  datasets: [],
  sessions: [],
  selectedDatasetId: "",
  selectedSessionId: "",
  selectedRunId: "",
  currentRun: null,
};

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
    root.innerHTML = `<div class="distill-empty">还没有样本集。先在左边建一套数据，session 才有稳定边界。</div>`;
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
              <strong>question_type</strong>
              <div>${escapeHtml(item.question_type || "-")}</div>
            </div>
            <div class="distill-meta-box">
              <strong>latest_run_at</strong>
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
    root.innerHTML = `<div class="distill-empty">先选中一条会话里的 run，或者刚跑完一轮试验后会自动切过来。</div>`;
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
        <strong>最新沉淀 Bundle</strong>
        <div style="margin-bottom:8px;">
          <span class="distill-badge distill-badge-good">${escapeHtml(latestPromotion.status || "ready")}</span>
        </div>
        <div>沉淀人：${escapeHtml(latestPromotion.promoter || "-")}</div>
        <div>目标：${escapeHtml((latestPromotion.targets || []).join(", ") || "-")}</div>
        <div>patch 数：${escapeHtml((latestPromotion.patch_ids || []).length)}</div>
        <div style="margin-top:8px;">artifact：${escapeHtml(latestPromotion.artifact_path || "-")}</div>
      </div>
    `
    : `<div class="distill-detail-box"><strong>最新沉淀 Bundle</strong><div>这条 run 还没有生成 promotion bundle。</div></div>`;

  root.innerHTML = `
    <div class="distill-detail-box">
      <strong>当前 Run</strong>
      <div class="distill-badge-row" style="margin-bottom:10px;">
        <span class="distill-badge distill-badge-info">第 ${escapeHtml(run.run_no)} 轮</span>
        <span class="distill-badge distill-badge-info">${escapeHtml(run.status || "-")}</span>
        <span class="${fitBadgeClass(fitSummary.fit_band)}">${escapeHtml(fitSummary.fit_band || "unknown")}</span>
      </div>
      <div>run_id：${escapeHtml(run.run_id)}</div>
      <div>session_id：${escapeHtml(run.session_id)}</div>
      <div>split：${escapeHtml(run.split || "-")}</div>
      <div>标签：${escapeHtml(run.label || "-")}</div>
      <div>patch 数：${escapeHtml(run.patch_count ?? 0)}</div>
      <div>promotion 数：${escapeHtml(run.promotion_count ?? 0)}</div>
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
        <strong>最新 Patch</strong>
        ${
          patchPreview
            ? `
            <div>目标：${escapeHtml(patchPreview.target || "-")}</div>
            <div>标题：${escapeHtml(patchPreview.title || "-")}</div>
            <div>scope_key：${escapeHtml(patchPreview.scope_key || "-")}</div>
            <div style="margin-top:8px;">摘要：${escapeHtml(patchPreview.summary || "-")}</div>
          `
            : `<div>这条 run 还没有 patch 记录。</div>`
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
      <strong>Patch 列表预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(run.patches || []))}</pre>
    </div>

    <div class="distill-detail-box">
      <strong>Promotion 列表预览</strong>
      <pre class="distill-detail-pre">${escapeHtml(prettyJson(run.promotions || []))}</pre>
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
        passage: "The passage argues that governance needs both efficiency and fairness.",
        stem: "下列选项中，最能概括这段材料主旨的是：",
        options: {
          A: "Governance should balance efficiency and fairness.",
          B: "Technology replaces governance.",
          C: "More investment solves everything.",
          D: "Only markets matter.",
        },
        answer: "A",
        analysis: "The passage highlights balance rather than a single extreme.",
      },
      generation_request: {
        question_focus: "center_understanding",
        business_subtype: "center_understanding",
        difficulty_level: "medium",
        count: 1,
        topic: "governance",
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
    topic: "governance",
  });

  $("trialLabel").value = "baseline dev 检查";
  $("trialHypothesis").value = "当前 baseline request 在 dev 上应该先跑到可接受的拟合度。";
  $("reviewSummary").value = "如果 test 也稳定，可以考虑沉淀。";
  $("patchTitle").value = "收紧题卡控制槽位";
  $("patchSummary").value = "把本轮观察到的拟合改动显式记录成 patch。";
  $("patchPayload").value = prettyJson({
    prompt_patch: {
      instruction: "prefer closer option wording",
    },
  });
  $("promoteSummary").value = "把审核通过且 patch 齐全的 run 打包成正式沉淀候选。";
}

async function handleCreateDataset(event) {
  event.preventDefault();
  const button = $("createDatasetBtn");
  withButtonLoading(button, true);
  setPageStatus("正在创建样本集...", "info");
  try {
    const payload = {
      title: $("datasetTitle").value.trim(),
      description: $("datasetDescription").value.trim() || null,
      question_card_id: $("datasetCardId").value.trim() || null,
      question_type: $("datasetQuestionType").value.trim() || null,
      business_subtype: $("datasetBusinessSubtype").value.trim() || null,
      split_mode: $("datasetSplitMode").value,
      samples: parseJsonField($("datasetSamples").value, "samples JSON", []),
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
    const baselineRequest = parseJsonField($("sessionBaselineRequest").value, "baseline_request JSON", null);
    const truthSourceQuestion = parseJsonField($("sessionTruthSourceQuestion").value, "truth_source_question JSON", null);
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
    setPageStatus("先选择一条蒸馏会话再跑 trial。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在运行 trial，这一步会真正调用 question_generation...", "info");
  try {
    const request = parseJsonField($("trialRequest").value, "trial request JSON", null);
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
    setPageStatus("先选择一条 run 再提交审核。", "error");
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
    setPageStatus("先选择一条 run 再记录 patch。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在记录 patch...", "info");
  try {
    const patchPayload = parseJsonField($("patchPayload").value, "patch JSON", {});
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
    setPageStatus(`Patch 已记录：${payload.title}`, "info");
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
    setPageStatus("先选择一条 run 再生成 promotion bundle。", "error");
    return;
  }
  withButtonLoading(button, true);
  setPageStatus("正在生成 promote bundle...", "info");
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
    setPageStatus(`Promote bundle 已生成：${run.latest_promotion?.artifact_path || "ready"}`, "info");
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

  $("refreshAllBtn").addEventListener("click", async () => {
    setPageStatus("正在刷新样本集、会话和 run...", "info");
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
      setPageStatus("当前 run 已刷新。", "info");
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
  setPageStatus("正在加载蒸馏训练工作台...", "info");
  try {
    await refreshAll();
    setPageStatus("蒸馏训练工作台已就绪。先看左边示例，按你的数据替换 JSON 就可以直接跑。", "info");
  } catch (error) {
    setPageStatus(`初始化失败：${error.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);
