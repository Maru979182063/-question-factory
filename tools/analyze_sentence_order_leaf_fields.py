import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


BASE = Path(r"C:\Users\97918\AppData\Local\Temp\360zip$Temp")
DIRS = ["360$12", "360$13", "360$14", "360$15"]
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def docx_paras(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    paras = []
    for p in root.findall(".//w:p", NS):
        text = "".join(t.text for t in p.findall(".//w:t", NS) if t.text)
        text = text.replace("\xa0", " ").strip()
        if text:
            paras.append(text)
    return paras


def is_start(para: str) -> bool:
    return len(para) > 3 and para[0].isdigit() and "#" in para[:30]


def split_blocks(paras: list[str]) -> list[list[str]]:
    starts = [idx for idx, para in enumerate(paras) if is_start(para)]
    return [
        paras[start : starts[idx + 1] if idx + 1 < len(starts) else len(paras)]
        for idx, start in enumerate(starts)
    ]


def section(block: list[str], label: str) -> str:
    start = None
    inline_head = ""
    for idx, para in enumerate(block):
        if para == label:
            start = idx
            break
        if para.startswith(label):
            start = idx
            inline_head = para[len(label) :].strip()
            break
    if start is None:
        return ""
    end = len(block)
    for idx in range(start + 1, len(block)):
        if block[idx].startswith("【") and block[idx].endswith("】"):
            end = idx
            break
        if block[idx].startswith("【") and "】" in block[idx]:
            end = idx
            break
    parts = [inline_head] if inline_head else []
    parts.extend(block[start + 1 : end])
    return "\n".join(part for part in parts if part).strip()


def leaf_from_name(name: str) -> str:
    if "背景引入" in name:
        return "first_sentence_background_intro"
    if "关联词" in name:
        return "deterministic_binding_connector_other"
    if "时间脉络" in name:
        return "timeline_progression"
    if "结论" in name:
        return "tail_conclusion"
    return "unknown"


MARKERS = {
    "background": ["背景引入", "背景铺垫", "引出话题", "宏观话题", "社会热词", "人们常说"],
    "opening": ["确定首句", "适合做首句", "不适合做首句", "首句"],
    "tail": ["确定尾句", "尾句", "适合做尾句", "做尾句", "总结", "结论"],
    "connector": ["关联词", "不仅", "更要", "递进", "转折", "然而", "但", "换言之", "因此", "显然"],
    "reference": ["指代", "这", "该", "其", "承接", "衔接"],
    "time": ["时间顺序", "时间脉络", "先后", "之后", "此前", "以来", "古代", "近代", "现代", "首先", "其次"],
    "logic": ["行文逻辑", "观点", "解释", "说明", "问题", "对策", "原因", "结果", "按照逻辑顺序"],
    "binding": ["捆绑", "紧密相连", "构成", "相连", "排除"],
    "block_swap": ["对比", "位置", "顺序", "应在", "应该在"],
}


def evidence(text: str) -> dict[str, int]:
    return {key: sum(text.count(marker) for marker in markers) for key, markers in MARKERS.items()}


def main() -> None:
    files = []
    for folder in DIRS:
        files.extend(sorted((BASE / folder).glob("*.docx")))

    records = []
    for file in files:
        leaf = leaf_from_name(file.name)
        for block in split_blocks(docx_paras(file)):
            text = "\n".join(block)
            qid = re.search(r"#[0-9]+", text)
            analysis = section(block, "【解析】")
            points = section(block, "【考点】")
            records.append(
                {
                    "file": file.name,
                    "leaf": leaf,
                    "qid": qid.group(0) if qid else "",
                    "analysis": analysis,
                    "points": points,
                    "ev": evidence(f"{analysis}\n{points}\n{text[:900]}"),
                }
            )

    by_leaf = defaultdict(list)
    for record in records:
        by_leaf[record["leaf"]].append(record)

    summary = {"total": len(records), "leaves": {}}
    for leaf, leaf_records in by_leaf.items():
        agg = Counter()
        for record in leaf_records:
            agg.update(record["ev"])
        support_rates = {
            key: round(sum(1 for record in leaf_records if record["ev"][key] > 0) / len(leaf_records), 3)
            for key in MARKERS
        }
        summary["leaves"][leaf] = {
            "file": leaf_records[0]["file"],
            "n": len(leaf_records),
            "agg": dict(agg),
            "support_rates": support_rates,
            "samples": [
                {
                    "qid": record["qid"],
                    "points": record["points"][:260],
                }
                for record in leaf_records[:6]
            ],
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
