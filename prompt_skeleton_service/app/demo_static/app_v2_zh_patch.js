(function () {
  function ensureCompatStyle() {
    if (document.getElementById("demoV2CompatStyle")) return;
    const style = document.createElement("style");
    style.id = "demoV2CompatStyle";
    style.textContent = `
      .inline-feedback strong {
        font-weight: 700;
      }

      .distill-entry-anchor {
        position: fixed;
        top: 22px;
        right: 24px;
        z-index: 26;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 12px 18px;
        border: none;
        border-radius: 999px;
        background: linear-gradient(135deg, #176f9f 0%, #114f72 100%);
        color: #fff;
        font-weight: 700;
        box-shadow: 0 14px 28px rgba(17, 79, 114, 0.24);
        cursor: pointer;
      }

      .distill-entry-anchor small {
        opacity: 0.82;
        font-size: 11px;
      }

      .distill-access-overlay[hidden] {
        display: none !important;
      }

      .distill-access-overlay {
        position: fixed;
        inset: 0;
        z-index: 35;
      }

      .distill-access-backdrop {
        position: absolute;
        inset: 0;
        background: rgba(15, 23, 42, 0.38);
        backdrop-filter: blur(4px);
      }

      .distill-access-dialog {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: min(520px, calc(100vw - 32px));
        padding: 28px 28px 24px;
        border-radius: 28px;
        border: 1px solid rgba(214, 224, 238, 0.95);
        background:
          radial-gradient(circle at top right, rgba(255, 218, 143, 0.24), transparent 28%),
          linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(247, 251, 255, 0.99) 100%);
        box-shadow: 0 28px 70px rgba(15, 23, 42, 0.2);
      }

      .distill-access-dialog h2 {
        margin: 0 0 10px;
        font-size: 30px;
        line-height: 1.1;
      }

      .distill-access-dialog p,
      .distill-access-help,
      .distill-access-status {
        color: #66758e;
        line-height: 1.8;
      }

      .distill-access-field {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 18px;
      }

      .distill-access-field span {
        font-size: 14px;
        font-weight: 700;
        color: #30415e;
      }

      .distill-access-actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 18px;
      }

      .distill-access-primary,
      .distill-access-secondary {
        border-radius: 14px;
        padding: 12px 18px;
        font-weight: 700;
        cursor: pointer;
      }

      .distill-access-primary {
        border: none;
        background: linear-gradient(135deg, #1f94ca 0%, #136f9f 100%);
        color: #fff;
      }

      .distill-access-secondary {
        border: 1px solid #d5dfec;
        background: #fff;
        color: #23314a;
      }

      .distill-access-primary:disabled,
      .distill-access-secondary:disabled {
        opacity: 0.6;
        cursor: wait;
      }

      .distill-access-status {
        margin-top: 14px;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid #d6e4f3;
        background: #f4f9ff;
      }

      .distill-access-status.is-error {
        border-color: #edc1c1;
        background: #fff5f5;
        color: #8f3d3d;
      }

      @media (max-width: 720px) {
        .distill-entry-anchor {
          top: 12px;
          right: 12px;
          left: 12px;
          justify-content: center;
        }

        .distill-access-dialog {
          width: calc(100vw - 24px);
          padding: 22px 20px 20px;
        }

        .distill-access-actions {
          flex-direction: column-reverse;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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

  function ensureDistillAccessEntry() {
    if (document.getElementById("distillEntryAnchor")) return;

    const button = document.createElement("button");
    button.id = "distillEntryAnchor";
    button.type = "button";
    button.className = "distill-entry-anchor";
    button.innerHTML = `
      <span>进入蒸馏训练台</span>
      <small>需输入密钥</small>
    `;
    document.body.appendChild(button);

    const overlay = document.createElement("div");
    overlay.id = "distillAccessOverlay";
    overlay.className = "distill-access-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="distill-access-backdrop" data-close="1"></div>
      <div class="distill-access-dialog" role="dialog" aria-modal="true" aria-labelledby="distillAccessTitle">
        <h2 id="distillAccessTitle">蒸馏训练入口</h2>
        <p>
          这里是你训练题卡、材料链和提示词的工作台入口。只有输入 YAML 里配置的访问密钥，
          才能进入训练界面继续跑 dataset、session、trial 和人工审核。
        </p>

        <label class="distill-access-field">
          <span>访问密钥</span>
          <input id="distillAccessKeyInput" type="password" placeholder="请输入训练入口密钥" />
        </label>

        <div class="distill-access-help">
          提示：密钥配置在运行时 YAML 中，不在前端暴露。验证通过后会直接进入中文训练界面。
        </div>

        <div id="distillAccessStatus" class="distill-access-status" hidden></div>

        <div class="distill-access-actions">
          <button id="distillAccessCancelBtn" type="button" class="distill-access-secondary">取消</button>
          <button id="distillAccessConfirmBtn" type="button" class="distill-access-primary">确认进入</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const statusNode = overlay.querySelector("#distillAccessStatus");
    const input = overlay.querySelector("#distillAccessKeyInput");
    const confirmBtn = overlay.querySelector("#distillAccessConfirmBtn");
    const cancelBtn = overlay.querySelector("#distillAccessCancelBtn");

    function setStatus(message, isError = false) {
      if (!message) {
        statusNode.hidden = true;
        statusNode.textContent = "";
        statusNode.className = "distill-access-status";
        return;
      }
      statusNode.hidden = false;
      statusNode.textContent = message;
      statusNode.className = `distill-access-status${isError ? " is-error" : ""}`;
    }

    function openOverlay() {
      overlay.hidden = false;
      setStatus("");
      window.setTimeout(() => input.focus(), 20);
    }

    function closeOverlay() {
      overlay.hidden = true;
      input.value = "";
      setStatus("");
    }

    async function verifyAndEnter() {
      const key = String(input.value || "").trim();
      if (!key) {
        setStatus("请先输入访问密钥。", true);
        return;
      }

      confirmBtn.disabled = true;
      cancelBtn.disabled = true;
      setStatus("正在验证密钥，验证通过后会进入训练界面……", false);
      try {
        const payload = await apiFetch("/api/v1/distill/access/verify", {
          method: "POST",
          body: JSON.stringify({ key }),
        });
        window.location.href = payload?.next || "/demo/distill";
      } catch (error) {
        setStatus(error.message || "密钥验证失败，请重试。", true);
      } finally {
        confirmBtn.disabled = false;
        cancelBtn.disabled = false;
      }
    }

    button.addEventListener("click", openOverlay);
    cancelBtn.addEventListener("click", closeOverlay);
    overlay.querySelectorAll("[data-close='1']").forEach((node) => node.addEventListener("click", closeOverlay));
    confirmBtn.addEventListener("click", verifyAndEnter);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        verifyAndEnter();
      }
      if (event.key === "Escape") {
        closeOverlay();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureCompatStyle();
    ensureDistillAccessEntry();
    document.documentElement.dataset.demoV2ZhPatch = "20260420a";
  });
})();
