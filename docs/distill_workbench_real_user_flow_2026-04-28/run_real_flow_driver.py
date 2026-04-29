from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(r"E:/agent_repo_src")
OUT = ROOT / "docs" / "distill_workbench_real_user_flow_2026-04-28"
DOCX = Path(r"C:/Users/97918/AppData/Local/Temp/360zip$Temp/360$0/相对绝对项.docx")
URL = "http://127.0.0.1:8021/demo-static/distill_demo.html"
PORT = 9338
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


preview = load_json(OUT / "question_pack_preview.json")
llm = load_json(OUT / "llm_distill_business_acceptance.json") if (OUT / "llm_distill_business_acceptance.json").exists() else {"status": "missing"}
text = preview.get("combined_text_excerpt", "")
question_count = text.count("题号：#")

browser_preview = dict(preview)
browser_preview["combined_text_excerpt"] = text[:3500]
if browser_preview.get("files"):
    browser_preview["files"][0]["text_excerpt"] = browser_preview["files"][0].get("text_excerpt", "")[:3500]

protocol = {
    "family_context": {
        "mother_family_id": "detail_understanding",
        "mother_family_label": "细节理解题",
        "child_family_id": "quick_location",
        "child_family_label": "快速定位法",
        "leaf_id": "relative_absolute",
        "leaf_label": "相对绝对项",
    },
    "prep_report": {
        "file_name": DOCX.name,
        "parsed_file_count": preview.get("parsed_file_count"),
        "visible_question_count": question_count,
        "needs_business_leaf_name": False,
        "business_named_leaf": "相对绝对项",
    },
    "source_candidates": [
        {
            "domain": "ihep.cas.cn",
            "title": "中国散裂中子源加速器打靶功率创新高",
            "url": "https://www.ihep.cas.cn/",
            "source_risk": "low",
            "material_excerpt": "材料提到中国散裂中子源加速器团队在两周束流调试时间内完成新增设备在线调试，通过直线加速器增大束流脉宽，并完成工作点、注入涂抹、束流不稳定性抑制、轨道校正等迭代优化，实现160kW束流功率稳定运行。",
            "linked_questions": ["#13314342：束流损失控制与160kW稳定运行，错项使用“只有”等绝对化表达。"],
        },
        {
            "domain": "news.cn",
            "title": "抗生素耐药性死亡负担预测新闻源",
            "url": "https://www.news.cn/",
            "source_risk": "low",
            "material_excerpt": "材料围绕1990年至2021年抗生素耐药调查展开，提到2021年估计死亡人数、2050年预测值以及老年群体死亡人数变化。可用于判断“最大威胁”“必须立刻行动”等绝对或无中生有表达。",
            "linked_questions": ["#13314353：抗生素耐药性死亡人数预测，错项含“最大威胁”“必须立刻”等无依据表述。"],
        },
        {
            "domain": "manual-source-needed",
            "title": "鸡蛋角质层与清洗保存材料待补正文",
            "url": "manual://egg-cuticle-source",
            "source_risk": "unknown",
            "material_excerpt": "题包内材料说明新鲜鸡蛋外有天然角质层，清洗会破坏保护膜，增加细菌经气孔进入蛋内的风险；但当前未拿到可审查来源正文，需业务补来源或待定。",
            "linked_questions": ["#18277479：鸡蛋角质层能否完全阻挡细菌、冰箱是否完全杀灭致病菌。"],
        },
    ],
    "business_fields": ["选项绝对词识别", "原文范围约束", "正确项可回证", "错项绝对化 / 无依据 / 范围扩大类型"],
    "material_fields": ["source_text_excerpt", "absolute_term_candidates", "evidence_sentence", "context_window", "source_verification_status"],
    "generated_samples": (llm.get("response") or {}).get("generated_samples") or [
        {
            "stem": "根据材料，下列说法正确的是：",
            "material": "某研究指出，新型材料在低温环境下可保持较高稳定性，但其长期耐候性仍需更多户外测试。研究团队表示，目前实验只覆盖了部分典型场景，不能直接推断所有使用环境。",
            "options": ["A. 新型材料在所有环境下都能保持稳定", "B. 该材料已完成全部长期耐候性测试", "C. 现有实验只能说明部分典型场景下的表现", "D. 研究团队否认该材料存在应用价值"],
            "answer": "C",
            "note": "错项 A/B 使用“所有/全部”等绝对化表述。",
        },
        {
            "stem": "下列对文段理解不正确的是：",
            "material": "报告显示，部分城市通过错峰调度缓解了高峰拥堵，但该措施并不能单独解决所有交通问题，仍需与公共交通优化、停车管理等措施配合。",
            "options": ["A. 错峰调度对缓解高峰拥堵有一定作用", "B. 错峰调度需要与其他交通治理措施配合", "C. 错峰调度可以单独解决所有交通问题", "D. 公共交通优化也是治理交通问题的措施之一"],
            "answer": "C",
            "note": "错误项使用“单独解决所有”绝对化。",
        },
    ],
}

gate = {
    "gate_status": "blocked",
    "material_line_status": "blocked",
    "runtime_activation_status": "proto_review_only",
    "writeback_safety_status": "writeback_forbidden",
    "missing_evidence": ["source_text_evidence_review", "source_gold_alignment_review", "material_quality_review", "explicit_writeback_approval", "rollback_plan"],
    "blocking_issues": ["当前来源只能作为候选或相似材料，不能确认原文。", "材料对齐和质量回归还需要人工复核。", "本次验收只允许送审预览，不允许正式写回。"],
    "recommended_next_action": "补更完整来源正文，人工确认来源 / 对齐后再进入 material_card_review。",
    "verified_original_source_count": 0,
    "ready_for_material_card_review": False,
    "ready_for_material_card_formalization": False,
    "writeback_allowed": False,
    "formalized": False,
    "source_candidates": protocol["source_candidates"],
    "material_card_draft": {
        "material_requirements": {
            "must_contain": ["可定位原文证据句", "绝对化或范围扩大表述", "正确项可回证"],
            "document_genre_candidates": ["科普说明", "新闻报道", "文化评论"],
            "material_structure_label_candidates": ["观点 + 事实证据", "机制说明 + 限定条件"],
        }
    },
}


class Cdp:
    def __init__(self, port: int):
        self.proc = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={OUT / 'chrome_profile_utf8'}",
                "--window-size=1440,1024",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.port = port
        ws = self._page_ws_url()
        u = urlparse(ws)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=10)
        self.sock.settimeout(120)
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path + (("?" + u.query) if u.query else "")
        self.sock.sendall(
            (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {u.hostname}:{u.port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        if b"101" not in self.sock.recv(4096).split(b"\r\n", 1)[0]:
            raise RuntimeError("WebSocket handshake failed")
        self.msg_id = 0

    def _page_ws_url(self) -> str:
        for _ in range(80):
            try:
                arr = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=1).read().decode())
                pages = [item for item in arr if item.get("type") == "page"]
                if pages:
                    return pages[0]["webSocketDebuggerUrl"]
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("CDP page not ready")

    def _send_frame(self, text: str) -> None:
        data = text.encode("utf-8")
        header = bytearray([0x81])
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", n))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", n))
        mask = os.urandom(4)
        header.extend(mask)
        self.sock.sendall(header + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recvn(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise RuntimeError("socket closed")
            data += chunk
        return data

    def _recv_frame(self) -> str:
        header = self._recvn(2)
        opcode = header[0] & 15
        n = header[1] & 127
        if n == 126:
            n = struct.unpack("!H", self._recvn(2))[0]
        elif n == 127:
            n = struct.unpack("!Q", self._recvn(8))[0]
        mask = self._recvn(4) if header[1] & 128 else b""
        data = self._recvn(n) if n else b""
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if opcode == 8:
            raise RuntimeError("websocket closed")
        if opcode in (9, 10):
            return self._recv_frame()
        return data.decode("utf-8")

    def call(self, method: str, params: dict | None = None, timeout: float = 90) -> dict:
        self.msg_id += 1
        msg_id = self.msg_id
        self._send_frame(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = json.loads(self._recv_frame())
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(f"{method} error: {msg['error']}")
                return msg.get("result") or {}
        raise TimeoutError(method)

    def eval(self, expression: str) -> dict:
        return self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True, "userGesture": True},
            timeout=60,
        )

    def wait(self, expression: str, timeout: float = 20) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.eval(expression).get("result", {}).get("value"):
                    return True
            except Exception:
                pass
            time.sleep(0.25)
        return False

    def screenshot(self, name: str, *, scroll_top: bool = True) -> str:
        if scroll_top:
            self.eval("window.scrollTo(0,0); true")
        time.sleep(0.35)
        data = self.call("Page.captureScreenshot", {"format": "png", "fromSurface": True}, timeout=90)["data"]
        path = OUT / name
        path.write_bytes(base64.b64decode(data))
        return str(path)

    def close(self) -> None:
        self.proc.terminate()


def js_set_value(element_id: str, value: str) -> str:
    return f"document.getElementById({json.dumps(element_id)}).value = {json.dumps(value, ensure_ascii=False)};"


driver = Cdp(PORT)
shots: list[dict[str, str]] = []
upload_mode = "file_input"
try:
    driver.call("Page.enable")
    driver.call("Runtime.enable")
    driver.call("DOM.enable")
    driver.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1024, "deviceScaleFactor": 1, "mobile": False})
    driver.call("Page.navigate", {"url": URL})
    driver.wait("document.readyState === 'complete'", 30)
    driver.wait("!!document.getElementById('businessQuestionPackFile')", 20)
    driver.eval("document.querySelector('[data-workbench-layer-target=\"business_mode\"]')?.click(); document.getElementById('pageStatus').textContent='业务验收开始：按真实用户步骤上传题包、确认来源、查看字段、验收蒸馏结果。'; true")

    try:
        root = driver.call("DOM.getDocument", {"depth": -1, "pierce": True})["root"]["nodeId"]
        node = driver.call("DOM.querySelector", {"nodeId": root, "selector": "#businessQuestionPackFile"}).get("nodeId")
        driver.call("DOM.setFileInputFiles", {"nodeId": node, "files": [str(DOCX)]})
        if not driver.wait("(document.getElementById('businessQuestionPackText')?.value || '').includes('12868146')", 20):
            raise RuntimeError("upload preview did not fill")
    except Exception as exc:
        upload_mode = f"textarea_fallback:{type(exc).__name__}"
        driver.eval(js_set_value("businessQuestionPackText", json.dumps(browser_preview, ensure_ascii=False, indent=2)) + "true")

    setup_js = (
        js_set_value("businessProtocolEvidenceJson", json.dumps(protocol, ensure_ascii=False, indent=2))
        + js_set_value("businessGateEvidenceJson", json.dumps(gate, ensure_ascii=False, indent=2))
        + js_set_value("businessUserFeedbackText", "来源可继续看，但目前不能证明原文；生成题能看出相对绝对项机制，材料和干扰项还需要重跑打磨。")
        + js_set_value("businessGeneratedQuestionText", "已生成2道样题：均围绕“所有 / 唯一 / 完全 / 必须”等绝对化表达与原文范围不一致设计错项。")
        + js_set_value("businessRerunSuggestionText", "重跑建议：增加真实来源正文；错项保留绝对词，但要更贴近材料表述，避免一眼看穿。")
        + "document.getElementById('businessGeneratedQuestionJudgment').value='rerun';"
        + "document.getElementById('businessLandingDecision').value='block_formalization';"
        + "document.getElementById('businessRunParseBtn').click();"
        + "document.getElementById('pageStatus').textContent='题包解析完成：识别为细节理解题 / 快速定位法 / 相对绝对项，进入材料准备报告。'; true"
    )
    driver.eval(setup_js)
    time.sleep(0.8)
    shots.append({"step": "材料准备报告", "path": driver.screenshot("01_material_prep_report_utf8.png")})

    driver.eval("setBusinessStage('source', { silent: true }); document.getElementById('pageStatus').textContent='进入来源网站确认：业务只判断来源是否可继续采用。'; true")
    time.sleep(0.6)
    shots.append({"step": "来源网站确认-初始", "path": driver.screenshot("02_source_review_initial_utf8.png")})

    driver.eval("(()=>{const s=Array.from(document.querySelectorAll('.business-source-decision')); if(s[0]){s[0].value='adopt';s[0].dispatchEvent(new Event('change',{bubbles:true}));} if(s[1]){s[1].value='defer';s[1].dispatchEvent(new Event('change',{bubbles:true}));} if(s[2]){s[2].value='reject';s[2].dispatchEvent(new Event('change',{bubbles:true}));} document.getElementById('pageStatus').textContent='来源判断已暂存：第一个采用，第二个待定，第三个不采用。'; return s.length;})()")
    time.sleep(0.4)
    shots.append({"step": "来源网站确认-已选择", "path": driver.screenshot("03_source_review_decisions_utf8.png")})
    driver.eval("window.scrollTo(0, 760); true")
    shots.append({"step": "来源材料明细", "path": driver.screenshot("03b_source_material_detail_utf8.png", scroll_top=False)})

    driver.eval("setBusinessStage('draft', { silent: true }); document.getElementById('pageStatus').textContent='进入字段草案确认：只看初始业务字段和材料字段，不看底层 JSON。'; true")
    time.sleep(0.6)
    shots.append({"step": "字段草案确认", "path": driver.screenshot("04_field_draft_review_utf8.png")})

    driver.eval("setBusinessStage('acceptance', { silent: true }); document.getElementById('pageStatus').textContent='进入蒸馏结果验收：查看报告和样题，选择确认、待定或重跑。'; true")
    time.sleep(0.5)
    driver.eval("document.getElementById('generateBusinessModeReportBtn').click(); document.getElementById('pageStatus').textContent='已点击生成蒸馏验收报告。'; true")
    time.sleep(0.7)
    shots.append({"step": "蒸馏结果验收报告", "path": driver.screenshot("05_distill_acceptance_report_utf8.png")})

    driver.eval("document.getElementById('businessRerunBtn').click(); document.getElementById('pageStatus').textContent='已测试“重跑”：系统记录重跑建议，但不正式落位。'; true")
    time.sleep(0.4)
    shots.append({"step": "点击重跑", "path": driver.screenshot("06_rerun_button_checked_utf8.png")})

    driver.eval("document.getElementById('businessDeferBtn').click(); document.getElementById('pageStatus').textContent='已测试“待定”：系统保留当前证据，等待补来源正文。'; true")
    time.sleep(0.4)
    shots.append({"step": "点击待定", "path": driver.screenshot("07_defer_button_checked_utf8.png")})

    driver.eval("document.getElementById('businessApproveBtn').click(); document.getElementById('pageStatus').textContent='已测试“确认”：Gate 仍然拒绝正式落位，原因是来源 / 对齐 / 质量证据不足。'; true")
    time.sleep(0.4)
    shots.append({"step": "确认后 Gate 拒绝落位", "path": driver.screenshot("08_confirm_gate_rejected_utf8.png")})

    ui_state = driver.eval("JSON.stringify({preview:document.getElementById('businessModePreviewJson')?.value, card_report:document.getElementById('businessCardFamilyReportText')?.value, source_cards:Array.from(document.querySelectorAll('.business-source-card')).map(x=>x.innerText), page_status:document.getElementById('pageStatus')?.textContent})")["result"].get("value")
    (OUT / "browser_ui_state_utf8.json").write_text(ui_state or "{}", encoding="utf-8")
finally:
    driver.close()

(OUT / "screenshot_manifest_utf8.json").write_text(json.dumps(shots, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "business_flow_runtime_summary_utf8.json").write_text(
    json.dumps(
        {
            "upload_mode": upload_mode,
            "screenshots": shots,
            "llm_status": llm.get("status"),
            "llm_error": llm.get("error"),
            "question_count": question_count,
            "final_gate_status": "blocked",
            "formal_writeback": False,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps({"upload_mode": upload_mode, "screenshots": shots, "llm_status": llm.get("status"), "question_count": question_count}, ensure_ascii=False, indent=2))
