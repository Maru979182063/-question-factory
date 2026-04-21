from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SERVICE_ROOT = ROOT / "prompt_skeleton_service"
if str(PROMPT_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(PROMPT_SERVICE_ROOT))

from app.schemas.item import GeneratedQuestion  # noqa: E402
from app.services.difficulty_assessment_service import DifficultyAssessmentService  # noqa: E402


AXES = (
    "local_binding_complexity",
    "global_context_dependency",
    "distractor_similarity",
    "blank_function_ambiguity",
)


FAMILY_SLOT_HINTS = {
    "横线在开头-概括后文": {
        "blank_position": "opening",
        "function_type": "summary",
        "logic_relation": "summary",
        "context_dependency": "high",
    },
    "横线在开头-话题引入": {
        "blank_position": "opening",
        "function_type": "topic_intro",
        "logic_relation": "transition",
        "context_dependency": "medium",
    },
    "横线在开头-横线为首句中的分句": {
        "blank_position": "opening",
        "function_type": "topic_intro",
        "logic_relation": "transition",
        "context_dependency": "medium",
    },
    "横线在中间-启下": {
        "blank_position": "middle",
        "function_type": "lead_next",
        "logic_relation": "transition",
        "context_dependency": "high",
    },
    "横线在中间-承上": {
        "blank_position": "middle",
        "function_type": "carry_previous",
        "logic_relation": "continuation",
        "context_dependency": "medium",
    },
    "横线在中间-承上启下": {
        "blank_position": "middle",
        "function_type": "bridge",
        "logic_relation": "transition",
        "context_dependency": "high",
        "bidirectional_validation": "high",
    },
    "横线在结尾-总结前文（原为 结论）": {
        "blank_position": "ending",
        "function_type": "conclusion",
        "logic_relation": "summary",
        "context_dependency": "medium",
    },
    "横线在结尾-提出对策（原为 对策）": {
        "blank_position": "ending",
        "function_type": "countermeasure",
        "logic_relation": "action",
        "context_dependency": "medium",
    },
    "横线在结尾-横线为尾句中的分句": {
        "blank_position": "ending",
        "function_type": "conclusion",
        "logic_relation": "summary",
        "context_dependency": "medium",
    },
    "特殊题型-问语句在文中的位置": {
        "blank_position": "inserted",
        "function_type": "reference_summary",
        "logic_relation": "reference_match",
        "context_dependency": "high",
        "reference_dependency": "high",
    },
}


def extract_docx_paragraphs(path: Path) -> list[str]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        parts: list[str] = []
        for node in paragraph.iter():
            tag = node.tag.split("}", 1)[-1]
            if tag == "t" and node.text:
                parts.append(node.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag == "br":
                parts.append("\n")
        text = "".join(parts).replace("\xa0", " ").strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def parse_question_blocks(paragraphs: list[str], *, source_file: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_field: str | None = None
    question_start = re.compile(r"^\d+[\.．]\s*题号[:：]")

    for raw_text in paragraphs:
        text = raw_text.strip()
        if question_start.match(text):
            if current:
                blocks.append(_finalize_block(current))
            current = {"source_file": source_file, "fields": {}, "question_header": text}
            current_field = None
            current["qid"] = _extract_after_marker(text, "题号") or ""
            continue
        if current is None:
            continue

        marker = re.match(r"^【([^】]+)】\s*(.*)$", text)
        if marker:
            current_field = marker.group(1).strip()
            rest = marker.group(2).strip()
            current["fields"].setdefault(current_field, [])
            if rest:
                current["fields"][current_field].append(rest)
            continue

        if current_field:
            current["fields"].setdefault(current_field, []).append(text)

    if current:
        blocks.append(_finalize_block(current))
    return blocks


def _finalize_block(block: dict[str, Any]) -> dict[str, Any]:
    fields = block.get("fields") or {}
    normalized: dict[str, Any] = {
        "source_file": block.get("source_file", ""),
        "qid": str(block.get("qid") or "").lstrip("#"),
        "exam": "\n".join(fields.get("所属试卷") or []).strip(),
        "answer": "\n".join(fields.get("答案") or []).strip().upper()[:1],
        "analysis": "\n".join(fields.get("解析") or []).strip(),
        "correct_rate_raw": "\n".join(fields.get("正确率") or []).strip(),
        "easy_wrong_option": "\n".join(fields.get("易错项") or []).strip().upper()[:1],
        "exam_point": "\n".join(fields.get("考点") or []).strip(),
    }
    question_lines = [line for line in fields.get("题干") or [] if line.strip()]
    parsed_question = parse_question_text(question_lines)
    normalized.update(parsed_question)
    return normalized


def parse_question_text(lines: list[str]) -> dict[str, Any]:
    joined = "\n".join(lines)
    option_line_index = next((idx for idx, line in enumerate(lines) if _looks_like_option_line(line)), -1)
    option_text = ""
    material_lines = list(lines)
    if option_line_index >= 0:
        option_text = lines[option_line_index]
        material_lines = lines[:option_line_index]

    options = parse_options(option_text)
    stem = ""
    if material_lines and ("填入" in material_lines[-1] or "以下句子" in material_lines[-1]):
        stem = material_lines[-1]
        material_lines = material_lines[:-1]
    material_text = "\n".join(material_lines).strip()
    return {
        "stem": stem,
        "material_text": normalize_blank_marker(material_text),
        "options": options,
    }


def parse_options(option_text: str) -> dict[str, str]:
    option_text = option_text.replace("\t", " ").strip()
    matches = list(re.finditer(r"([ABCD])[\.．、]", option_text))
    options: dict[str, str] = {}
    for index, match in enumerate(matches):
        key = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(option_text)
        options[key] = option_text[start:end].strip()
    return options


def normalize_blank_marker(text: str) -> str:
    normalized = text.strip()
    normalized = re.sub(r"[＿_]{2,}", "____", normalized)
    normalized = re.sub(r"[ 　]{4,}", "____", normalized)
    normalized = normalized.replace("（    ）", "____")
    normalized = normalized.replace("(    )", "____")
    if "____" not in normalized and normalized.startswith("。"):
        normalized = "____" + normalized
    return normalized


def _looks_like_option_line(text: str) -> bool:
    return all(token in text for token in ("A.", "B.", "C.", "D.")) or all(
        token in text for token in ("A．", "B．", "C．", "D．")
    )


def _extract_after_marker(text: str, marker: str) -> str | None:
    match = re.search(rf"{marker}[:：]\s*([^\s]+)", text)
    return match.group(1) if match else None


def parse_correct_rate(raw_value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", raw_value or "")
    if not match:
        return None
    value = float(match.group(1))
    if value > 1:
        value /= 100.0
    return max(0.0, min(1.0, value))


def empirical_band_from_rate(correct_rate: float) -> str:
    if correct_rate >= 0.70:
        return "easy"
    if correct_rate <= 0.45:
        return "hard"
    return "medium"


def band_from_difficulty_score(score: float) -> str:
    if score <= 0.30:
        return "easy"
    if score >= 0.55:
        return "hard"
    return "medium"


def load_samples(input_dir: Path) -> list[dict[str, Any]]:
    assessment_service = DifficultyAssessmentService()
    samples: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.docx")):
        source_stem = path.stem
        slot_hints = FAMILY_SLOT_HINTS.get(source_stem, {})
        paragraphs = extract_docx_paragraphs(path)
        for block in parse_question_blocks(paragraphs, source_file=path.name):
            correct_rate = parse_correct_rate(str(block.get("correct_rate_raw") or ""))
            options = block.get("options") or {}
            answer = str(block.get("answer") or "").strip().upper()
            if correct_rate is None or answer not in options or len(options) < 4:
                continue
            generated_question = GeneratedQuestion(
                question_type="sentence_fill",
                stem=block.get("stem") or "填入横线处最恰当的一项是：",
                options=options,
                answer=answer,
                analysis=block.get("analysis") or "",
            )
            assessment = assessment_service.assess(
                question_type="sentence_fill",
                target_difficulty=empirical_band_from_rate(correct_rate),
                generated_question=generated_question,
                material_text=block.get("material_text") or "",
                resolved_slots=slot_hints,
                validator_status="truth_accuracy_reference",
            )
            row = {
                **block,
                "leaf": source_stem,
                "correct_rate": correct_rate,
                "empirical_difficulty": round(1.0 - correct_rate, 4),
                "empirical_band": empirical_band_from_rate(correct_rate),
                "slot_hints": slot_hints,
                "axis_scores": assessment.axis_scores,
                "current_equal_axis_score": round(sum(assessment.axis_scores.get(axis, 0.0) for axis in AXES) / len(AXES), 4),
            }
            samples.append(row)
    return samples


def fit_curve(samples: list[dict[str, Any]]) -> dict[str, Any]:
    x_rows = [[float(sample["axis_scores"].get(axis, 0.0)) for axis in AXES] for sample in samples]
    y = [float(sample["empirical_difficulty"]) for sample in samples]
    equal_weights = [1 / len(AXES)] * len(AXES)
    equal_raw = [sum(value * weight for value, weight in zip(row, equal_weights)) for row in x_rows]
    equal_a, equal_b = fit_affine(equal_raw, y)
    equal_pred = [clip01(equal_a + equal_b * score) for score in equal_raw]

    best = grid_search_weights(x_rows, y, step=0.05)
    fitted_raw = [sum(value * weight for value, weight in zip(row, best["weights"])) for row in x_rows]
    fitted_pred = [clip01(best["intercept"] + best["scale"] * score) for score in fitted_raw]

    cv = cross_validate(x_rows, y, k=5, step=0.1)
    scored_samples = []
    for sample, raw_score, pred in zip(samples, fitted_raw, fitted_pred):
        scored_samples.append(
            {
                "sample_id": f"{sample.get('source_file')}::{sample.get('qid')}",
                "leaf": sample.get("leaf"),
                "qid": sample.get("qid"),
                "correct_rate": sample.get("correct_rate"),
                "empirical_difficulty": sample.get("empirical_difficulty"),
                "empirical_band": sample.get("empirical_band"),
                "predicted_difficulty": round(pred, 4),
                "predicted_band": band_from_difficulty_score(pred),
                "absolute_error": round(abs(pred - sample["empirical_difficulty"]), 4),
                "raw_weighted_axis_score": round(raw_score, 4),
                "axis_scores": sample.get("axis_scores"),
                "answer": sample.get("answer"),
                "easy_wrong_option": sample.get("easy_wrong_option"),
                "stem": sample.get("stem"),
                "material_preview": str(sample.get("material_text") or "")[:180],
            }
        )

    return {
        "axes": AXES,
        "sample_count": len(samples),
        "axis_correlations": {
            axis: round(pearson([row[index] for row in x_rows], y), 4)
            for index, axis in enumerate(AXES)
        },
        "equal_weight_baseline": {
            "weights": dict(zip(AXES, equal_weights)),
            "intercept": round(equal_a, 4),
            "scale": round(equal_b, 4),
            "metrics": metrics(y, equal_pred),
        },
        "fitted_candidate": {
            "weights": {axis: round(weight, 4) for axis, weight in zip(AXES, best["weights"])},
            "intercept": round(best["intercept"], 4),
            "scale": round(best["scale"], 4),
            "metrics": metrics(y, fitted_pred),
        },
        "cross_validation": cv,
        "leaf_summary": leaf_summary(scored_samples),
        "curve_bins": curve_bins(scored_samples),
        "largest_errors": sorted(scored_samples, key=lambda item: item["absolute_error"], reverse=True)[:12],
        "calibration_judgment": calibration_judgment(
            baseline_metrics=metrics(y, equal_pred),
            fitted_metrics=metrics(y, fitted_pred),
            axis_correlations={
                axis: pearson([row[index] for row in x_rows], y)
                for index, axis in enumerate(AXES)
            },
        ),
        "scored_samples": scored_samples,
    }


def grid_search_weights(x_rows: list[list[float]], y: list[float], *, step: float) -> dict[str, Any]:
    units = int(round(1.0 / step))
    best: dict[str, Any] | None = None
    for a in range(units + 1):
        for b in range(units - a + 1):
            for c in range(units - a - b + 1):
                d = units - a - b - c
                weights = [a / units, b / units, c / units, d / units]
                if not any(weights):
                    continue
                raw = [sum(value * weight for value, weight in zip(row, weights)) for row in x_rows]
                intercept, scale = fit_affine(raw, y)
                if scale < 0:
                    continue
                pred = [clip01(intercept + scale * score) for score in raw]
                current = {
                    "weights": weights,
                    "intercept": intercept,
                    "scale": scale,
                    "mae": mean(abs(left - right) for left, right in zip(y, pred)),
                    "pearson": pearson(raw, y),
                }
                if best is None or (current["mae"], -current["pearson"]) < (best["mae"], -best["pearson"]):
                    best = current
    return best or {"weights": [0.25, 0.25, 0.25, 0.25], "intercept": 0.0, "scale": 1.0}


def cross_validate(x_rows: list[list[float]], y: list[float], *, k: int, step: float) -> dict[str, Any]:
    folds: list[dict[str, Any]] = []
    predictions: list[tuple[float, float]] = []
    for fold in range(k):
        train_x = [row for index, row in enumerate(x_rows) if index % k != fold]
        train_y = [value for index, value in enumerate(y) if index % k != fold]
        test_x = [row for index, row in enumerate(x_rows) if index % k == fold]
        test_y = [value for index, value in enumerate(y) if index % k == fold]
        if not train_x or not test_x:
            continue
        fit = grid_search_weights(train_x, train_y, step=step)
        raw = [sum(value * weight for value, weight in zip(row, fit["weights"])) for row in test_x]
        pred = [clip01(fit["intercept"] + fit["scale"] * score) for score in raw]
        predictions.extend(zip(test_y, pred))
        folds.append(
            {
                "fold": fold + 1,
                "n_test": len(test_y),
                "weights": {axis: round(weight, 3) for axis, weight in zip(AXES, fit["weights"])},
                "metrics": metrics(test_y, pred),
            }
        )
    all_y = [item[0] for item in predictions]
    all_pred = [item[1] for item in predictions]
    return {"folds": folds, "overall": metrics(all_y, all_pred) if all_y else {}}


def fit_affine(raw_scores: list[float], y: list[float]) -> tuple[float, float]:
    x_mean = mean(raw_scores)
    y_mean = mean(y)
    variance = sum((value - x_mean) ** 2 for value in raw_scores)
    if variance <= 1e-12:
        return y_mean, 0.0
    covariance = sum((x - x_mean) * (target - y_mean) for x, target in zip(raw_scores, y))
    scale = covariance / variance
    intercept = y_mean - scale * x_mean
    return intercept, scale


def metrics(y: list[float], pred: list[float]) -> dict[str, Any]:
    if not y:
        return {}
    empirical_bands = [band_from_difficulty_score(value) for value in y]
    predicted_bands = [band_from_difficulty_score(value) for value in pred]
    return {
        "mae": round(mean(abs(left - right) for left, right in zip(y, pred)), 4),
        "rmse": round(math.sqrt(mean((left - right) ** 2 for left, right in zip(y, pred))), 4),
        "pearson": round(pearson(pred, y), 4),
        "spearman": round(spearman(pred, y), 4),
        "band_agreement": round(mean(1.0 if left == right else 0.0 for left, right in zip(empirical_bands, predicted_bands)), 4),
    }


def leaf_summary(scored_samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for sample in scored_samples:
        grouped.setdefault(str(sample.get("leaf") or "unknown"), []).append(sample)
    summary = []
    for leaf, rows in sorted(grouped.items()):
        summary.append(
            {
                "leaf": leaf,
                "n": len(rows),
                "avg_correct_rate": round(mean(row["correct_rate"] for row in rows), 4),
                "avg_empirical_difficulty": round(mean(row["empirical_difficulty"] for row in rows), 4),
                "avg_predicted_difficulty": round(mean(row["predicted_difficulty"] for row in rows), 4),
                "mae": round(mean(row["absolute_error"] for row in rows), 4),
            }
        )
    return summary


def curve_bins(scored_samples: list[dict[str, Any]], *, bin_count: int = 5) -> list[dict[str, Any]]:
    rows = sorted(scored_samples, key=lambda item: item["predicted_difficulty"])
    if not rows:
        return []
    bins = []
    for index in range(bin_count):
        start = index * len(rows) // bin_count
        end = (index + 1) * len(rows) // bin_count
        chunk = rows[start:end]
        if not chunk:
            continue
        bins.append(
            {
                "bin": index + 1,
                "n": len(chunk),
                "predicted_range": [
                    round(min(row["predicted_difficulty"] for row in chunk), 4),
                    round(max(row["predicted_difficulty"] for row in chunk), 4),
                ],
                "avg_predicted_difficulty": round(mean(row["predicted_difficulty"] for row in chunk), 4),
                "avg_empirical_difficulty": round(mean(row["empirical_difficulty"] for row in chunk), 4),
                "avg_correct_rate": round(mean(row["correct_rate"] for row in chunk), 4),
            }
        )
    return bins


def calibration_judgment(
    *,
    baseline_metrics: dict[str, Any],
    fitted_metrics: dict[str, Any],
    axis_correlations: dict[str, float],
) -> dict[str, Any]:
    max_axis_corr = max((abs(value) for value in axis_correlations.values()), default=0.0)
    fitted_pearson = abs(float(fitted_metrics.get("pearson") or 0.0))
    baseline_pearson = abs(float(baseline_metrics.get("pearson") or 0.0))
    if max(fitted_pearson, baseline_pearson, max_axis_corr) < 0.15:
        level = "not_aligned"
        summary = "当前四轴难度分数与学生正确率难度曲线尚未形成稳定一致关系。"
    elif max(fitted_pearson, baseline_pearson) < 0.35:
        level = "weak_alignment"
        summary = "当前四轴与学生正确率存在弱关系，只能作为结构难度信号，不能单独充当经验难度。"
    else:
        level = "usable_alignment"
        summary = "当前四轴与学生正确率已有可用的一致性，可进入小样本人工复核。"
    return {
        "level": level,
        "summary": summary,
        "recommended_action": "保留四轴作为结构控制层，新增学生正确率校准层；先输出 candidate patch，不自动回写主配置。",
        "missing_empirical_signals": [
            "easy_wrong_option_competition",
            "correct_option_abstraction_gap",
            "surface_familiarity_and_register",
            "trap_salience",
            "background_or_idiom_dependency",
        ],
    }


def render_markdown(report: dict[str, Any], *, input_dir: Path) -> str:
    fitted = report["fitted_candidate"]
    baseline = report["equal_weight_baseline"]
    cv = report["cross_validation"].get("overall") or {}
    judgment = report["calibration_judgment"]
    lines = [
        "# sentence_fill 学生正确率难度曲线拟合报告",
        "",
        f"- 数据来源：`{input_dir}`",
        f"- 样本数：{report['sample_count']}",
        "- 外部真值：`empirical_difficulty = 1 - correct_rate`",
        "- 说明：本报告只产出离线校准候选，不自动回写题卡、prompt assets 或 validator。",
        "",
        "## 1. 结论",
        "",
        f"- 校准判断：`{judgment['level']}`。{judgment['summary']}",
        f"- 当前四轴等权基线：Pearson={baseline['metrics']['pearson']}，Spearman={baseline['metrics']['spearman']}，MAE={baseline['metrics']['mae']}，分档一致率={baseline['metrics']['band_agreement']}。",
        f"- 拟合候选权重：Pearson={fitted['metrics']['pearson']}，Spearman={fitted['metrics']['spearman']}，MAE={fitted['metrics']['mae']}，分档一致率={fitted['metrics']['band_agreement']}。",
        f"- 5 折交叉验证：Pearson={cv.get('pearson')}，Spearman={cv.get('spearman')}，MAE={cv.get('mae')}，分档一致率={cv.get('band_agreement')}。",
        f"- 建议动作：{judgment['recommended_action']}",
        "",
        "## 2. 单轴相关性",
        "",
        "| axis | Pearson with empirical difficulty |",
        "| --- | ---: |",
    ]
    for axis, corr in report["axis_correlations"].items():
        lines.append(f"| `{axis}` | {corr} |")
    lines.extend(
        [
            "",
            "## 3. 候选权重",
        "",
        "| axis | weight |",
        "| --- | ---: |",
        ]
    )
    for axis, weight in fitted["weights"].items():
        lines.append(f"| `{axis}` | {weight} |")
    lines.extend(
        [
            "",
            f"- 线性校准：`difficulty = {fitted['intercept']} + {fitted['scale']} * weighted_axis_score`",
            "- 解释：如果拟合仍接近等权或相关性很低，说明“只调四轴权重”不足以解释学生真实失分。",
            "",
            "## 4. 难度曲线分箱",
            "",
            "| bin | n | predicted_range | avg_predicted_difficulty | avg_empirical_difficulty | avg_correct_rate |",
            "| ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in report["curve_bins"]:
        lines.append(
            f"| {row['bin']} | {row['n']} | {row['predicted_range']} | {row['avg_predicted_difficulty']} | {row['avg_empirical_difficulty']} | {row['avg_correct_rate']} |"
        )
    lines.extend(
        [
            "",
            "## 5. 最下级考点表现",
            "",
            "| leaf | n | avg_correct_rate | avg_empirical_difficulty | avg_predicted_difficulty | mae |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["leaf_summary"]:
        lines.append(
            f"| {row['leaf']} | {row['n']} | {row['avg_correct_rate']} | {row['avg_empirical_difficulty']} | {row['avg_predicted_difficulty']} | {row['mae']} |"
        )
    lines.extend(
        [
            "",
            "## 6. 误差最大的样本",
            "",
            "| sample | leaf | correct_rate | empirical | predicted | abs_error | answer/easy_wrong |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["largest_errors"]:
        lines.append(
            f"| `{row['qid']}` | {row['leaf']} | {row['correct_rate']} | {row['empirical_difficulty']} | {row['predicted_difficulty']} | {row['absolute_error']} | {row['answer']}/{row['easy_wrong_option']} |"
        )
    lines.extend(
        [
            "",
            "## 7. 可解释性判断",
            "",
            "- 当前四轴更像“结构可控性轴”，不是完整的“学生失分概率轴”。",
            "- 学生正确率低的题，常常不是因为局部绑定或干扰项字面相似，而是因为易错项抓住了更强的表面主题、选项抽象层级更诱人、表达风格更像常识判断。",
            "- 因此下一步应新增经验校准信号，而不是直接把当前四轴阈值整体拉高。",
            "",
            "建议新增的经验校准信号：",
        ]
    )
    for signal in judgment["missing_empirical_signals"]:
        lines.append(f"- `{signal}`")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "leaf",
        "qid",
        "correct_rate",
        "empirical_difficulty",
        "empirical_band",
        "predicted_difficulty",
        "predicted_band",
        "absolute_error",
        "raw_weighted_axis_score",
        "answer",
        "easy_wrong_option",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def mean(values) -> float:
    data = [float(value) for value in values]
    if not data:
        return 0.0
    return sum(data) / len(data)


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_var * right_var)
    if denominator <= 1e-12:
        return 0.0
    return numerator / denominator


def spearman(left: list[float], right: list[float]) -> float:
    return pearson(rank(left), rank(right))


def rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        avg_rank = (index + end - 1) / 2 + 1
        for original_index, _ in indexed[index:end]:
            ranks[original_index] = avg_rank
        index = end
    return ranks


def clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Fit sentence_fill difficulty curve against student accuracy labels.")
    parser.add_argument(
        "--input-dir",
        default=str(Path.home() / "Desktop" / "语句填空题"),
        help="Directory containing lowest-level sentence_fill docx packs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "difficulty_control" / "empirical_curve"),
        help="Output directory.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    samples = load_samples(input_dir)
    if not samples:
        raise SystemExit(f"no usable samples parsed from: {input_dir}")
    report = fit_curve(samples)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "sentence_fill_empirical_curve_fit.json"
    md_path = output_dir / "sentence_fill_empirical_curve_fit.md"
    csv_path = output_dir / "sentence_fill_empirical_curve_scored_samples.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, input_dir=input_dir), encoding="utf-8")
    write_csv(csv_path, report["scored_samples"])

    print(f"samples parsed: {report['sample_count']}")
    print(f"json report written to: {json_path}")
    print(f"markdown report written to: {md_path}")
    print(f"scored samples written to: {csv_path}")


if __name__ == "__main__":
    main()
