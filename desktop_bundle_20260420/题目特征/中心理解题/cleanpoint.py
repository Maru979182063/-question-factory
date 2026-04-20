# -*- coding: utf-8 -*-
"""
docx -> 3 jsonl 抽取脚本
用途：
1. 读取题库 docx
2. 按题目切分
3. 每题分别调用模型 3 次：
   - 文选选取逻辑
   - 题目制作逻辑
   - 题目控制逻辑
4. 输出 3 个 jsonl 文件

环境变量：
- OPENAI_API_KEY

运行示例：
python extract_verbal_logic.py --input sample.docx --output_dir outputs --model gpt-4.1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from openai import OpenAI


# =========================
# 基础工具
# =========================

def read_docx_text(path: str) -> str:
    doc = Document(path)
    lines: List[str] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def safe_json_loads(text: str) -> Dict[str, Any]:
    text = text.strip()

    # 去掉 ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试截取最外层 {}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        return json.loads(candidate)

    raise ValueError(f"无法解析 JSON：{text[:300]}")


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_whitespace(s: Optional[str]) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


# =========================
# 文档切题
# =========================

QUESTION_START_RE = re.compile(r"(?m)^\d+\.\s*题号：#?\d+")


def split_question_blocks(full_text: str) -> List[str]:
    matches = list(QUESTION_START_RE.finditer(full_text))
    if not matches:
        return []

    blocks: List[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        block = full_text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def extract_between(block: str, start_label: str, end_labels: List[str]) -> str:
    pattern = re.escape(start_label) + r"\n?"
    m = re.search(pattern, block)
    if not m:
        return ""

    start = m.end()
    end = len(block)

    for label in end_labels:
        m2 = re.search(re.escape(label), block[start:])
        if m2:
            end = min(end, start + m2.start())

    return block[start:end].strip()


def extract_single_line_field(block: str, field_name: str) -> str:
    # 匹配类似：【答案】 D / 【正确率】67.15%
    patterns = [
        rf"{re.escape(field_name)}\s*[:：]?\s*(.+)",
        rf"\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, block)
        if m:
            return m.group(1).strip()
    return ""


def parse_question_block(block: str) -> Dict[str, Any]:
    qid_match = re.search(r"题号：#?(\d+)", block)
    question_id = qid_match.group(1) if qid_match else ""

    source_exam = extract_single_line_field(block, "所属试卷")
    answer = extract_single_line_field(block, "答案")
    source_text = extract_single_line_field(block, "文段出处")
    accuracy = extract_single_line_field(block, "正确率")
    easy_wrong = extract_single_line_field(block, "易错项")
    point_tree = extract_single_line_field(block, "考点")

    material = extract_between(
        block,
        "【材料】",
        ["【题干】", "【答案】", "【解析】", "【文段出处】", "【正确率】", "【易错项】", "【考点】"],
    )

    question_stem = extract_between(
        block,
        "【题干】",
        ["A.", "A．", "【答案】", "【解析】", "【文段出处】", "【正确率】", "【易错项】", "【考点】"],
    )

    analysis = extract_between(
        block,
        "【解析】",
        ["【文段出处】", "【解析视频】", "【正确率】", "【易错项】", "【考点】"],
    )

    # 选项
    options = {}
    option_pattern = re.compile(
        r"(?m)^(A|B|C|D)[\.．、]\s*(.+?)(?=^(?:A|B|C|D)[\.．、]\s*|^【答案】|^【解析】|$)",
        re.S,
    )
    for m in option_pattern.finditer(block):
        options[m.group(1)] = normalize_whitespace(m.group(2))

    return {
        "question_id": question_id,
        "source_exam": source_exam,
        "material": material,
        "question_stem": question_stem,
        "options": options,
        "answer": answer,
        "analysis": analysis,
        "source_text": source_text,
        "accuracy": accuracy,
        "easy_wrong_option": easy_wrong,
        "point_tree": point_tree,
        "raw_block": block,
    }


# =========================
# OpenAI 调用
# =========================

def build_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("未检测到 OPENAI_API_KEY 环境变量。")
    return OpenAI(api_key=api_key)


def call_model_json(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_payload: Dict[str, Any],
    max_retries: int = 3,
    sleep_sec: float = 2.0,
) -> Dict[str, Any]:
    last_err: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
            )
            text = response.output_text
            return safe_json_loads(text)
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(sleep_sec * attempt)

    raise RuntimeError(f"模型调用失败：{last_err}")


# =========================
# Prompt 模板
# =========================

PASSAGE_LOGIC_PROMPT = """
你是中文公考/事业单位言语题研究助手。
你的任务：只根据用户提供的单道题信息，抽取“文选选取逻辑”。

要求：
1. 只输出一个 JSON 对象，不要输出解释。
2. 不要虚构题外信息。
3. 所有字段必须存在；拿不准时用空字符串、空数组或“未知”。
4. 你的目标不是解释这道题，而是反推出：
   “什么样的文段适合被拿来出这类中心理解题”。

输出字段：
{
  "question_id": "",
  "question_type": "",
  "point_tree": "",
  "article_length_level": "短/中/长/未知",
  "paragraph_count_level": "单段/双段/多段/未知",
  "structure_type": "总分/分总/总分总/递进/并列/转折/提出问题-分析问题-解决问题/混合/未知",
  "main_position": "开头/中间/结尾/隐含/未知",
  "logic_relations": [],
  "info_density": "低/中/高/未知",
  "clarity": "清晰/中等/偏绕/未知",
  "topic_style": [],
  "suitable_for": [],
  "difficulty_base": "简单/中等/较难/未知",
  "passage_selection_rules": [
    "规则1",
    "规则2"
  ]
}
""".strip()


CONSTRUCTION_LOGIC_PROMPT = """
你是中文公考/事业单位言语题研究助手。
你的任务：只根据用户提供的单道题信息，抽取“题目制作逻辑”。

要求：
1. 只输出一个 JSON 对象，不要输出解释。
2. 聚焦于：正确项怎么来、错误项怎么错、题目加工方式是什么。
3. 所有字段必须存在；拿不准时用空字符串、空数组或“未知”。

输出字段：
{
  "question_id": "",
  "question_type": "",
  "point_tree": "",
  "correct_answer": "",
  "correct_source": "结论句/转折后/对策句/全文整合/抽象概括/未知",
  "processing_type": "直取/整合/抽象/未知",
  "answer_abstraction_level": "低/中/高/未知",
  "trap_types": [],
  "distractor_pattern": [],
  "common_mistake_reason": "",
  "construction_rules": [
    "规则1",
    "规则2"
  ]
}
""".strip()


CONTROL_LOGIC_PROMPT = """
你是中文公考/事业单位言语题研究助手。
你的任务：只根据用户提供的单道题信息，抽取“题目控制逻辑”。

要求：
1. 只输出一个 JSON 对象，不要输出解释。
2. 聚焦于：这道题的难度从哪里来、怎么控制。
3. 可以结合正确率，但不能机械地只看正确率。
4. 所有字段必须存在；拿不准时用空字符串、空数组或“未知”。

输出字段：
{
  "question_id": "",
  "question_type": "",
  "point_tree": "",
  "accuracy": "",
  "difficulty_level": "简单/中等/较难/未知",
  "difficulty_source": "文段/选项/混合/未知",
  "passage_difficulty": {
    "main_position": "开头/中间/结尾/隐含/未知",
    "structure_complexity": "低/中/高/未知",
    "information_dispersion": "低/中/高/未知",
    "clarity": "清晰/中等/偏绕/未知"
  },
  "correct_option_difficulty": {
    "abstraction_level": "低/中/高/未知",
    "integration_required": "是/否/未知"
  },
  "distractor_difficulty": {
    "similarity_level": "低/中/高/未知",
    "local_correctness": "低/中/高/未知"
  },
  "control_rules": [
    "规则1",
    "规则2"
  ]
}
""".strip()


# =========================
# 题目负载构造
# =========================

def build_question_payload(q: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "question_id": q["question_id"],
        "source_exam": q["source_exam"],
        "material": q["material"],
        "question_stem": q["question_stem"],
        "options": q["options"],
        "answer": q["answer"],
        "analysis": q["analysis"],
        "source_text": q["source_text"],
        "accuracy": q["accuracy"],
        "easy_wrong_option": q["easy_wrong_option"],
        "point_tree": q["point_tree"],
    }


# =========================
# 主流程
# =========================

def process_file(input_path: str, output_dir: str, model: str) -> None:
    client = build_client()

    full_text = read_docx_text(input_path)
    blocks = split_question_blocks(full_text)
    if not blocks:
        raise ValueError("未在文档中识别到题目块，请检查 docx 内容格式。")

    questions = [parse_question_block(b) for b in blocks]

    passage_rows: List[Dict[str, Any]] = []
    construction_rows: List[Dict[str, Any]] = []
    control_rows: List[Dict[str, Any]] = []
    error_rows: List[Dict[str, Any]] = []

    for idx, q in enumerate(questions, start=1):
        print(f"[{idx}/{len(questions)}] 处理题号 {q['question_id']} ...")
        payload = build_question_payload(q)

        try:
            passage_json = call_model_json(
                client=client,
                model=model,
                system_prompt=PASSAGE_LOGIC_PROMPT,
                user_payload=payload,
            )
            passage_rows.append(passage_json)
        except Exception as e:
            error_rows.append({
                "question_id": q["question_id"],
                "stage": "文选选取逻辑",
                "error": str(e),
            })

        try:
            construction_json = call_model_json(
                client=client,
                model=model,
                system_prompt=CONSTRUCTION_LOGIC_PROMPT,
                user_payload=payload,
            )
            construction_rows.append(construction_json)
        except Exception as e:
            error_rows.append({
                "question_id": q["question_id"],
                "stage": "题目制作逻辑",
                "error": str(e),
            })

        try:
            control_json = call_model_json(
                client=client,
                model=model,
                system_prompt=CONTROL_LOGIC_PROMPT,
                user_payload=payload,
            )
            control_rows.append(control_json)
        except Exception as e:
            error_rows.append({
                "question_id": q["question_id"],
                "stage": "题目控制逻辑",
                "error": str(e),
            })

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(out_dir / "questions_parsed.jsonl", questions)
    write_jsonl(out_dir / "文选选取逻辑.jsonl", passage_rows)
    write_jsonl(out_dir / "题目制作逻辑.jsonl", construction_rows)
    write_jsonl(out_dir / "题目控制逻辑.jsonl", control_rows)
    write_jsonl(out_dir / "error_log.jsonl", error_rows)

    print("处理完成。")
    print(f"questions_parsed.jsonl: {len(questions)} 条")
    print(f"文选选取逻辑.jsonl: {len(passage_rows)} 条")
    print(f"题目制作逻辑.jsonl: {len(construction_rows)} 条")
    print(f"题目控制逻辑.jsonl: {len(control_rows)} 条")
    print(f"error_log.jsonl: {len(error_rows)} 条")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="输入 docx 文件路径")
    parser.add_argument("--output_dir", required=True, help="输出目录")
    parser.add_argument("--model", default="gpt-4.1", help="模型名，默认 gpt-4.1")
    args = parser.parse_args()

    process_file(
        input_path=args.input,
        output_dir=args.output_dir,
        model=args.model,
    )


if __name__ == "__main__":
    main()