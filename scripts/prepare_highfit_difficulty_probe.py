from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "difficulty_control" / "highfit_probe"
DESKTOP = Path.home() / "Desktop"

CENTER_SOURCES = [
    ("center_understanding", "主题词", DESKTOP / "中心理解题" / "主题词.docx"),
    ("center_understanding", "程度词", DESKTOP / "中心理解题" / "程度词.docx"),
]
ORDER_SOURCES = [
    ("sentence_order", "特殊题型-4句、7句", DESKTOP / "语句排序题" / "特殊题型-4句、7句.docx"),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for family, leaf, path in CENTER_SOURCES + ORDER_SOURCES:
        rows.extend(_parse_docx(path=path, family=family, leaf=leaf))

    truth_rows = [
        {
            "sample_id": row["sample_id"],
            "family": row["family"],
            "leaf": row["leaf"],
            "qid": row["qid"],
            "correct_rate": row["correct_rate"],
            "empirical_difficulty": row["empirical_difficulty"],
            "answer": row["answer"],
            "easy_wrong": row["easy_wrong"],
            "sentence_count": row.get("sentence_count"),
        }
        for row in rows
        if row.get("correct_rate") is not None
    ]
    _write_jsonl(OUT_DIR / "highfit_probe_hidden_truth.jsonl", truth_rows)

    center_rows = [row for row in rows if row["family"] == "center_understanding"]
    order_rows = [row for row in rows if row["family"] == "sentence_order"]
    for suffix, subset in _split_rows(center_rows, 3).items():
        _write_jsonl(OUT_DIR / f"center_highfit_label_input_{suffix}.jsonl", [_public_row(row) for row in subset])
        _write_jsonl(OUT_DIR / f"center_pairwise_label_input_{suffix}.jsonl", [_public_row(row) for row in subset])
    _write_jsonl(OUT_DIR / "order_highfit_label_input_A.jsonl", [_public_row(row) for row in order_rows])

    (OUT_DIR / "highfit_label_schema.md").write_text(_schema_text(), encoding="utf-8")
    (OUT_DIR / "center_pairwise_label_schema.md").write_text(_center_pairwise_schema_text(), encoding="utf-8")
    summary = {
        "total_rows": len(rows),
        "truth_rows": len(truth_rows),
        "by_family_leaf": _counts_by(rows, ("family", "leaf")),
        "output_dir": str(OUT_DIR),
    }
    (OUT_DIR / "index.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _parse_docx(*, path: Path, family: str, leaf: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    lines = [p.text.strip() for p in Document(str(path)).paragraphs if p.text.strip()]
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^\d+\.\s*题号：#\d+", line):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)

    rows: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks, start=1):
        row = _parse_block(block=block, family=family, leaf=leaf, ordinal=idx)
        if row:
            rows.append(row)
    return rows


def _parse_block(*, block: list[str], family: str, leaf: str, ordinal: int) -> dict[str, Any] | None:
    header = block[0]
    qid_match = re.search(r"#(\d+)", header)
    if not qid_match:
        return None
    qid = qid_match.group(1)
    tagged = _tagged_sections(block)
    stem_lines = tagged.get("题干") or []
    answer = _first_non_empty(tagged.get("答案") or [])
    analysis_lines = tagged.get("解析") or []
    correct_rate = _extract_percent(block, "正确率")
    easy_wrong = _extract_tag_value(block, "易错项")
    options = _parse_options(stem_lines)
    stem_without_options = [line for line in stem_lines if not _looks_like_options_line(line)]

    if family == "sentence_order":
        numbered_sentences = [line for line in stem_without_options if re.match(r"^[①②③④⑤⑥⑦⑧⑨]", line)]
        prompt_lines = [line for line in stem_without_options if line not in numbered_sentences]
        passage = "\n".join(numbered_sentences).strip()
        stem = "\n".join(prompt_lines).strip()
        sentence_count = len(numbered_sentences)
    else:
        passage_lines = stem_without_options[:-1] if len(stem_without_options) > 1 else stem_without_options
        stem = stem_without_options[-1] if len(stem_without_options) > 1 else ""
        passage = "\n".join(passage_lines).strip()
        sentence_count = None

    sample_id = f"{family}::{leaf}::{qid}"
    return {
        "sample_id": sample_id,
        "family": family,
        "leaf": leaf,
        "qid": qid,
        "ordinal": ordinal,
        "source_header": header,
        "source_exam": _extract_tag_value(block, "所属试卷"),
        "passage": passage,
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": "\n".join(analysis_lines).strip(),
        "correct_rate": correct_rate,
        "empirical_difficulty": None if correct_rate is None else round(1.0 - correct_rate, 6),
        "easy_wrong": easy_wrong,
        "exam_point": _extract_tag_value(block, "考点"),
        "sentence_count": sentence_count,
    }


def _tagged_sections(block: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in block[1:]:
        tag_match = re.match(r"^【([^】]+)】\s*(.*)$", raw)
        if tag_match:
            current = tag_match.group(1).strip()
            rest = tag_match.group(2).strip()
            sections.setdefault(current, [])
            if rest:
                sections[current].append(rest)
            continue
        if current:
            sections.setdefault(current, []).append(raw)
    return sections


def _parse_options(lines: list[str]) -> dict[str, str]:
    option_text = "\n".join(line for line in lines if _looks_like_options_line(line))
    if not option_text:
        return {}
    compact = re.sub(r"\s+", "", option_text)
    options: dict[str, str] = {}
    for key in ("A", "B", "C", "D"):
        match = re.search(rf"{key}[\.\u3001\uff0e:：]?(.*?)(?=[A-D][\.\u3001\uff0e:：]?|$)", compact)
        if match:
            options[key] = match.group(1).strip()
    return options


def _looks_like_options_line(line: str) -> bool:
    compact = re.sub(r"\s+", "", line)
    return bool(re.search(r"A[\.\u3001\uff0e:：]?.+B[\.\u3001\uff0e:：]?.+", compact))


def _extract_percent(block: list[str], tag: str) -> float | None:
    pattern = re.compile(rf"【{re.escape(tag)}】\s*([0-9]+(?:\.[0-9]+)?)%")
    for line in block:
        match = pattern.search(line)
        if match:
            return round(float(match.group(1)) / 100.0, 6)
    return None


def _extract_tag_value(block: list[str], tag: str) -> str:
    pattern = re.compile(rf"^【{re.escape(tag)}】\s*(.*)$")
    for idx, line in enumerate(block):
        match = pattern.match(line)
        if match:
            value = match.group(1).strip()
            if value:
                return value
            if idx + 1 < len(block):
                return block[idx + 1].strip()
    return ""


def _first_non_empty(lines: list[str]) -> str:
    for line in lines:
        if line.strip():
            return line.strip()
    return ""


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    public = {
        key: row[key]
        for key in (
            "sample_id",
            "family",
            "leaf",
            "qid",
            "source_exam",
            "passage",
            "stem",
            "options",
            "answer",
            "easy_wrong",
            "analysis",
            "exam_point",
            "sentence_count",
        )
        if key in row
    }
    return public


def _split_rows(rows: list[dict[str, Any]], parts: int) -> dict[str, list[dict[str, Any]]]:
    names = ["A", "B", "C", "D", "E"]
    buckets = {names[idx]: [] for idx in range(parts)}
    for idx, row in enumerate(rows):
        buckets[names[idx % parts]].append(row)
    return buckets


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _counts_by(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        label = " / ".join(str(row.get(key, "")) for key in keys)
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _schema_text() -> str:
    return """# High-Fit Difficulty Probe Label Schema

本轮标注不看正确率，只读题、选项、答案、易错项和解析，目标是测试“难度控制轴”是否能拟合学生真实正确率。

## center_understanding 输出字段

每行输出一个 JSON，必须保留 `sample_id`，并新增：

```json
{
  "sample_id": "...",
  "center_axes": {
    "main_claim_visibility": 1,
    "theme_term_overlap_trap": 1,
    "correct_option_abstraction_gap": 1,
    "local_detail_distractor_strength": 1,
    "scope_degree_decision_load": 1,
    "discourse_turn_complexity": 1,
    "option_competition_density": 1
  },
  "center_type": {
    "dominant_error_type": "local_detail",
    "reason": "一句话说明"
  }
}
```

打分均为 1-5，分数越高表示越增加作答难度：

- `main_claim_visibility`: 中心句/主旨是否隐藏，越需要跨句综合越高。
- `theme_term_overlap_trap`: 错项是否复用主题词、政策词、关键词来制造表层正确感。
- `correct_option_abstraction_gap`: 正确项是否需要把原文抽象、换说、概括后才能识别。
- `local_detail_distractor_strength`: 易错项是否抓住局部细节、例子、原因、结果中的一段。
- `scope_degree_decision_load`: 是否需要判断“更重要/主要/关键/最/范围大小/主次轻重”。
- `discourse_turn_complexity`: 文段是否有背景-转折-对策-例证-总结等多重结构转折。
- `option_competition_density`: 四个选项是否同时有一定合理性，且差异很细。

`dominant_error_type` 取值：`topic_missing`, `local_detail`, `overgeneralization`, `degree_scope`, `unsupported`, `similar_summary`, `mixed`, `other`。

## sentence_order 输出字段

每行输出一个 JSON，必须保留 `sample_id`，并新增：

```json
{
  "sample_id": "...",
  "order_axes": {
    "first_sentence_ambiguity": 1,
    "adjacency_bundle_ambiguity": 1,
    "referential_dependency_load": 1,
    "logical_sequence_depth": 1,
    "option_sequence_competition": 1,
    "global_coherence_reconstruction_load": 1
  },
  "order_type": {
    "dominant_order_mechanism": "time_sequence",
    "reason": "一句话说明"
  }
}
```

打分均为 1-5，分数越高表示越增加作答难度：

- `first_sentence_ambiguity`: 首句候选是否难区分。
- `adjacency_bundle_ambiguity`: 相邻捆绑关系是否弱、多个捆绑都似乎成立。
- `referential_dependency_load`: 代词、指代、承接对象、关联词回指的负荷。
- `logical_sequence_depth`: 时间、因果、总分、观点解释等链条层级深度。
- `option_sequence_competition`: 选项排列之间是否只差少数关键位置、竞争很贴近。
- `global_coherence_reconstruction_load`: 是否需要先重建全文结构，而不是靠局部线索即可作答。

`dominant_order_mechanism` 取值：`time_sequence`, `topic_progression`, `view_explanation`, `contrast_turn`, `referential_binding`, `mixed`, `other`。
"""


def _center_pairwise_schema_text() -> str:
    return """# Center Understanding Pairwise Label Schema

本轮只标 `中心理解题` 的正确项与易错项竞争关系。不要查看 hidden_truth 或正确率文件。

每行输出一个 JSON，必须保留输入 `sample_id`，并新增：

```json
{
  "sample_id": "...",
  "center_pairwise_axes": {
    "easy_wrong_partial_validity": 1,
    "easy_wrong_main_claim_proximity": 1,
    "scope_degree_gap_subtlety": 1,
    "correct_option_completeness_advantage_hidden": 1,
    "decisive_evidence_visibility_load": 1,
    "surface_wording_similarity": 1,
    "exclusion_reasoning_load": 1
  },
  "pairwise_type": {
    "dominant_pairwise_trap": "local_detail_vs_main_claim",
    "reason": "一句话说明"
  }
}
```

所有轴均为 1-5，分数越高表示越增加作答难度：

- `easy_wrong_partial_validity`: 易错项是否确实抓住原文局部正确内容，而不是明显无关。
- `easy_wrong_main_claim_proximity`: 易错项离文段真正主旨/意图是否很近。
- `scope_degree_gap_subtlety`: 正确项和易错项的范围、程度、主次差异是否细微。
- `correct_option_completeness_advantage_hidden`: 正确项虽然更完整，但优势是否不醒目、不容易一眼看出。
- `decisive_evidence_visibility_load`: 决胜证据是否隐藏在句群关系、转折、程度词、尾句总结中。
- `surface_wording_similarity`: 正确项和易错项在关键词、话术、政策词、表达风格上的表层相似度。
- `exclusion_reasoning_load`: 排除易错项是否需要多步推理，而非一句话即可排除。

`dominant_pairwise_trap` 取值：

- `local_detail_vs_main_claim`
- `scope_degree_shift`
- `similar_summary`
- `topic_word_overlap`
- `unsupported_extension`
- `overgeneralization`
- `under_specific`
- `mixed`
- `other`
"""


if __name__ == "__main__":
    main()
