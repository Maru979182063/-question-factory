from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
LABELS = {
    "source_exam": "【所属试卷】",
    "stem": "【题干】",
    "answer": "【答案】",
    "analysis": "【解析】",
    "exam_points": "【考点】",
    "correct_rate": "【正确率】",
    "wrong_option": "【易错项】",
}


def read_docx_paragraphs(path: str | Path) -> list[str]:
    docx_path = Path(path)
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for para in root.findall(".//w:p", NS):
        text = "".join(node.text for node in para.findall(".//w:t", NS) if node.text)
        text = text.replace("\xa0", " ").strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def split_question_blocks(paragraphs: list[str]) -> list[list[str]]:
    starts = [index for index, para in enumerate(paragraphs) if _is_question_start(para)]
    return [
        paragraphs[start : starts[index + 1] if index + 1 < len(starts) else len(paragraphs)]
        for index, start in enumerate(starts)
    ]


def parse_docx_pack(path: str | Path, *, mother_family_id: str, leaf_label: str) -> list[dict[str, Any]]:
    docx_path = Path(path)
    samples: list[dict[str, Any]] = []
    for index, block in enumerate(split_question_blocks(read_docx_paragraphs(docx_path)), start=1):
        raw_text = "\n".join(block)
        qid_match = re.search(r"#[0-9]+", raw_text)
        sample_id = f"{docx_path.stem}_{qid_match.group(0)[1:] if qid_match else index}"
        sample = {
            "sample_id": sample_id,
            "source_file": str(docx_path),
            "source_file_name": docx_path.name,
            "mother_family_id": mother_family_id,
            "leaf_label": leaf_label,
            "qid": qid_match.group(0) if qid_match else None,
            "source_exam": _section(block, LABELS["source_exam"]),
            "stem": _section(block, LABELS["stem"]),
            "answer": _first_line(_section(block, LABELS["answer"])),
            "analysis": _section(block, LABELS["analysis"]),
            "exam_points": _section(block, LABELS["exam_points"]),
            "correct_rate": _first_line(_section(block, LABELS["correct_rate"])),
            "wrong_option": _first_line(_section(block, LABELS["wrong_option"])),
            "raw_text": raw_text,
            "parse_warnings": [],
        }
        if not sample["stem"]:
            sample["parse_warnings"].append("missing_stem")
        if not sample["analysis"]:
            sample["parse_warnings"].append("missing_analysis")
        samples.append(sample)
    return samples


def _is_question_start(para: str) -> bool:
    return bool(re.match(r"^\d+\.\s*题号[:：]?#?[0-9]+", para))


def _section(block: list[str], label: str) -> str:
    start = None
    inline_head = ""
    for index, para in enumerate(block):
        if para == label:
            start = index
            break
        if para.startswith(label):
            start = index
            inline_head = para[len(label) :].strip()
            break
    if start is None:
        return ""

    end = len(block)
    for index in range(start + 1, len(block)):
        if block[index].startswith("【") and "】" in block[index]:
            end = index
            break
    parts = [inline_head] if inline_head else []
    parts.extend(block[start + 1 : end])
    return "\n".join(part for part in parts if part).strip()


def _first_line(text: str) -> str | None:
    for line in str(text or "").splitlines():
        line = line.strip()
        if line:
            return line
    return None
