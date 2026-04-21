"""Explore leaf-level difficulty effects for sentence_fill.

The report answers two handoff questions:
1. Do the existing structural axes become useful inside each leaf family?
2. Which residuals suggest additional leaf-specific dimensions?

This script is diagnostic only. It does not write prompt assets, card specs, or
validator configuration.
"""

from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CURVE_JSON = ROOT / "reports/difficulty_control/empirical_curve/sentence_fill_empirical_curve_fit.json"
LABEL_JSON = ROOT / "reports/difficulty_control/empirical_labeling/manual_label_fit_report.json"
LABEL_DIR = ROOT / "reports/difficulty_control/empirical_labeling"
OUT_DIR = ROOT / "reports/difficulty_control/leaf_difficulty_exploration"
ASSET_DIR = OUT_DIR / "assets"

AXES = (
    "local_binding_complexity",
    "global_context_dependency",
    "distractor_similarity",
    "blank_function_ambiguity",
)

LABEL_FEATURES = (
    "easy_wrong_option_competition",
    "correct_option_abstraction_gap",
    "surface_trap_salience",
    "plausible_distractor_count_norm",
    "expression_register_difficulty",
    "reasoning_operation_complexity",
    "blank_syntactic_form_complexity",
)


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    return sum(data) / len(data) if data else 0.0


def _std(values: Iterable[float]) -> float:
    data = list(values)
    if len(data) < 2:
        return 0.0
    avg = _mean(data)
    return (sum((value - avg) ** 2 for value in data) / (len(data) - 1)) ** 0.5


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _dot(left: list[float], right: list[float]) -> float:
    return sum(x * y for x, y in zip(left, right))


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    if left_var <= 1e-12 or right_var <= 1e-12:
        return 0.0
    return numerator / math.sqrt(left_var * right_var)


def _rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        avg_rank = (cursor + end + 2) / 2.0
        for _, index in ordered[cursor : end + 1]:
            ranks[index] = avg_rank
        cursor = end + 1
    return ranks


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 2:
        return 0.0
    return _pearson(_rank(left), _rank(right))


def _metrics(target: list[float], predicted: list[float]) -> dict[str, float]:
    if not target:
        return {"mae": 0.0, "rmse": 0.0, "pearson": 0.0, "spearman": 0.0}
    return {
        "mae": round(_mean(abs(y - p) for y, p in zip(target, predicted)), 4),
        "rmse": round(math.sqrt(_mean((y - p) ** 2 for y, p in zip(target, predicted))), 4),
        "pearson": round(_pearson(predicted, target), 4),
        "spearman": round(_spearman(predicted, target), 4),
    }


def _fit_affine(raw: list[float], target: list[float], *, allow_negative_scale: bool) -> tuple[float, float]:
    raw_mean = _mean(raw)
    target_mean = _mean(target)
    variance = sum((value - raw_mean) ** 2 for value in raw)
    if variance <= 1e-12:
        return target_mean, 0.0
    covariance = sum((x - raw_mean) * (y - target_mean) for x, y in zip(raw, target))
    scale = covariance / variance
    if scale < 0 and not allow_negative_scale:
        return target_mean, 0.0
    return target_mean - scale * raw_mean, scale


def _weight_grid(feature_count: int, step: float) -> Iterable[list[float]]:
    units = int(round(1.0 / step))

    def rec(remaining: int, slots: int, prefix: list[int]) -> Iterable[list[float]]:
        if slots == 1:
            yield [(part / units) for part in prefix + [remaining]]
            return
        for value in range(remaining + 1):
            yield from rec(remaining - value, slots - 1, prefix + [value])

    yield from rec(units, feature_count, [])


def _fit_weighted_model(
    x_rows: list[list[float]],
    target: list[float],
    *,
    step: float = 0.1,
    allow_negative_scale: bool = False,
) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for weights in _weight_grid(len(x_rows[0]), step):
        raw = [_dot(row, weights) for row in x_rows]
        intercept, scale = _fit_affine(raw, target, allow_negative_scale=allow_negative_scale)
        predicted = [_clamp(intercept + scale * score) for score in raw]
        current = {
            "weights": weights,
            "intercept": intercept,
            "scale": scale,
            "metrics": _metrics(target, predicted),
        }
        if best is None or (
            current["metrics"]["mae"],
            -current["metrics"]["spearman"],
        ) < (
            best["metrics"]["mae"],
            -best["metrics"]["spearman"],
        ):
            best = current
    return best or {
        "weights": [1.0 / len(x_rows[0])] * len(x_rows[0]),
        "intercept": 0.0,
        "scale": 1.0,
        "metrics": {},
    }


def _cross_validate_leaf(x_rows: list[list[float]], target: list[float], *, k: int = 5) -> dict[str, float]:
    predictions: list[float] = []
    actuals: list[float] = []
    for fold in range(k):
        train_x = [row for index, row in enumerate(x_rows) if index % k != fold]
        train_y = [value for index, value in enumerate(target) if index % k != fold]
        test_x = [row for index, row in enumerate(x_rows) if index % k == fold]
        test_y = [value for index, value in enumerate(target) if index % k == fold]
        if not train_x or not test_x:
            continue
        fit = _fit_weighted_model(train_x, train_y, allow_negative_scale=False)
        raw = [_dot(row, fit["weights"]) for row in test_x]
        fold_pred = [_clamp(fit["intercept"] + fit["scale"] * score) for score in raw]
        predictions.extend(fold_pred)
        actuals.extend(test_y)
    return _metrics(actuals, predictions)


def _load_curve_samples() -> list[dict[str, Any]]:
    payload = json.loads(CURVE_JSON.read_text(encoding="utf-8"))
    return payload["scored_samples"]


def _load_labeled_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(LABEL_DIR.glob("label_output_*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _axis_row(row: dict[str, Any]) -> list[float]:
    scores = row.get("axis_scores") or {}
    return [float(scores.get(axis, 0.0)) for axis in AXES]


def _label_value(row: dict[str, Any], feature: str) -> float:
    labels = row.get("labels") or {}
    if feature == "plausible_distractor_count_norm":
        return _clamp(float(labels.get("plausible_distractor_count") or 0.0) / 3.0)
    return _clamp(float(labels.get(feature) or 0.0))


def _combined_prediction(row: dict[str, Any], label_report: dict[str, Any]) -> float:
    model = label_report["models"]["combined"]
    raw = 0.0
    for feature, weight in model["weights"].items():
        if feature.startswith("axis."):
            raw += float(weight) * float((row.get("axis_scores") or {}).get(feature.split(".", 1)[1], 0.0))
        elif feature.startswith("label."):
            raw += float(weight) * _label_value(row, feature.split(".", 1)[1])
    return _clamp(float(model["intercept"]) + float(model["scale"]) * raw)


def _leaf_structure_summary(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        grouped[row["leaf"]].append(row)

    summaries = []
    for leaf, rows in sorted(grouped.items()):
        target = [float(row["empirical_difficulty"]) for row in rows]
        x_rows = [_axis_row(row) for row in rows]
        current_pred = [float(row["predicted_difficulty"]) for row in rows]
        leaf_mean_pred = [_mean(target)] * len(target)
        axis_correlations = {
            axis: round(_spearman([row[i] for row in x_rows], target), 4)
            for i, axis in enumerate(AXES)
        }
        axis_std = {axis: round(_std(row[i] for row in x_rows), 4) for i, axis in enumerate(AXES)}
        fitted = None
        signed = None
        cv = None
        if len(rows) >= 12:
            fitted = _fit_weighted_model(x_rows, target, allow_negative_scale=False)
            signed = _fit_weighted_model(x_rows, target, allow_negative_scale=True)
        if len(rows) >= 20:
            cv = _cross_validate_leaf(x_rows, target)
        summaries.append(
            {
                "leaf": leaf,
                "n": len(rows),
                "target_mean": round(_mean(target), 4),
                "target_sd": round(_std(target), 4),
                "leaf_mean_baseline": _metrics(target, leaf_mean_pred),
                "current_global_structure": _metrics(target, current_pred),
                "axis_spearman": axis_correlations,
                "axis_std": axis_std,
                "leaf_fit_positive": _serialize_fit(fitted),
                "leaf_fit_signed_diagnostic": _serialize_fit(signed),
                "leaf_fit_cv_positive": cv,
            }
        )
    return summaries


def _serialize_fit(fit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not fit:
        return None
    return {
        "weights": {axis: round(weight, 4) for axis, weight in zip(AXES, fit["weights"])},
        "intercept": round(float(fit["intercept"]), 4),
        "scale": round(float(fit["scale"]), 4),
        "metrics": fit["metrics"],
    }


def _label_residual_summary(labeled_rows: list[dict[str, Any]], label_report: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in labeled_rows:
        predicted = _combined_prediction(row, label_report)
        target = float(row["empirical_difficulty"])
        enriched = {
            "annotation_id": row.get("annotation_id"),
            "qid": row.get("qid"),
            "leaf": row.get("leaf"),
            "target": target,
            "predicted": round(predicted, 4),
            "residual": round(target - predicted, 4),
            "abs_error": round(abs(target - predicted), 4),
            "answer": row.get("answer"),
            "easy_wrong_option": row.get("easy_wrong_option"),
            "stem": row.get("stem"),
            "material_preview": (row.get("material_text") or "")[:180],
            "options": row.get("options") or {},
            "labels": row.get("labels") or {},
        }
        rows.append(enriched)

    residuals = [row["residual"] for row in rows]
    feature_correlations = {
        feature: round(_spearman([_label_value(row, feature) for row in labeled_rows], residuals), 4)
        for feature in LABEL_FEATURES
    }
    leaf_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        leaf_grouped[row["leaf"]].append(row)
    leaf_residuals = []
    for leaf, leaf_rows in sorted(leaf_grouped.items()):
        leaf_residuals.append(
            {
                "leaf": leaf,
                "n": len(leaf_rows),
                "mean_residual": round(_mean(row["residual"] for row in leaf_rows), 4),
                "mae": round(_mean(row["abs_error"] for row in leaf_rows), 4),
                "hard_underestimated_count": sum(1 for row in leaf_rows if row["residual"] > 0.15),
                "easy_overestimated_count": sum(1 for row in leaf_rows if row["residual"] < -0.15),
            }
        )
    return {
        "feature_residual_spearman": feature_correlations,
        "leaf_residuals": leaf_residuals,
        "largest_underestimated": sorted(rows, key=lambda item: item["residual"], reverse=True)[:8],
        "largest_overestimated": sorted(rows, key=lambda item: item["residual"])[:8],
    }


def _bar_svg(title: str, data: list[tuple[str, float]], path: Path, *, width: int = 940, height: int = 500) -> None:
    margin_left = 255
    margin_right = 42
    margin_top = 54
    margin_bottom = 34
    plot_width = width - margin_left - margin_right
    row_h = (height - margin_top - margin_bottom) / max(len(data), 1)
    max_v = max(max(value for _, value in data), 0.001)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="34" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(data):
        y = margin_top + idx * row_h + row_h * 0.18
        bar_h = max(10, row_h * 0.48)
        bar_w = plot_width * max(value, 0.0) / max_v
        parts.extend(
            [
                f'<text x="{margin_left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
                f'font-size="14" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>',
                f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="6" fill="#2F6F73"/>',
                f'<text x="{margin_left + bar_w + 8:.1f}" y="{y + bar_h * 0.72:.1f}" '
                f'font-size="13" font-family="Consolas, monospace" fill="#4D564F">{_fmt(value)}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _diverging_svg(title: str, data: list[tuple[str, float]], path: Path, *, width: int = 940, height: int = 500) -> None:
    margin_left = 255
    margin_right = 54
    margin_top = 54
    margin_bottom = 34
    plot_width = width - margin_left - margin_right
    center = margin_left + plot_width / 2
    row_h = (height - margin_top - margin_bottom) / max(len(data), 1)
    max_abs = max(max(abs(value) for _, value in data), 0.05)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="34" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
        f'<line x1="{center:.1f}" y1="{margin_top - 10}" x2="{center:.1f}" y2="{height - margin_bottom + 8}" stroke="#AFA38F" stroke-width="2"/>',
    ]
    for idx, (label, value) in enumerate(data):
        y = margin_top + idx * row_h + row_h * 0.18
        bar_h = max(10, row_h * 0.48)
        bar_w = (plot_width / 2) * abs(value) / max_abs
        x = center if value >= 0 else center - bar_w
        color = "#B96045" if value >= 0 else "#3F6FA3"
        text_anchor = "start" if value >= 0 else "end"
        text_x = x + bar_w + 8 if value >= 0 else x - 8
        parts.extend(
            [
                f'<text x="{margin_left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
                f'font-size="14" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>',
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="6" fill="{color}"/>',
                f'<text x="{text_x:.1f}" y="{y + bar_h * 0.72:.1f}" text-anchor="{text_anchor}" '
                f'font-size="13" font-family="Consolas, monospace" fill="#4D564F">{value:+.3f}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _render_report(
    leaf_summary: list[dict[str, Any]],
    residual_summary: dict[str, Any],
    label_report: dict[str, Any],
) -> str:
    valid_cv = [row for row in leaf_summary if row.get("leaf_fit_cv_positive")]
    structure_wins = [
        row
        for row in valid_cv
        if row["leaf_fit_cv_positive"]["mae"] + 0.01 < row["leaf_mean_baseline"]["mae"]
        and row["leaf_fit_cv_positive"]["spearman"] > 0.15
    ]
    mean_only = [
        row
        for row in valid_cv
        if abs(row["leaf_fit_cv_positive"]["mae"] - row["leaf_mean_baseline"]["mae"]) <= 0.01
        or row["leaf_fit_cv_positive"]["spearman"] <= 0.15
    ]
    cv_rows = []
    for row in sorted(valid_cv, key=lambda item: item["leaf_fit_cv_positive"]["mae"]):
        best_axis = max(row["axis_spearman"].items(), key=lambda item: abs(item[1]))
        cv_rows.append(
            [
                row["leaf"],
                str(row["n"]),
                _fmt(row["target_mean"]),
                _fmt(row["target_sd"]),
                _fmt(row["leaf_mean_baseline"]["mae"]),
                _fmt(row["current_global_structure"]["mae"]),
                _fmt(row["leaf_fit_cv_positive"]["mae"]),
                _fmt(row["leaf_fit_cv_positive"]["spearman"]),
                f"{best_axis[0]}={best_axis[1]:+.3f}",
            ]
        )

    fit_rows = []
    for row in sorted(leaf_summary, key=lambda item: item["current_global_structure"]["mae"], reverse=True):
        fit = row.get("leaf_fit_positive") or {}
        weight_text = "样本不足"
        if fit:
            positive_weights = [
                f"{name}={weight:.1f}"
                for name, weight in fit["weights"].items()
                if weight > 0
            ]
            weight_text = ", ".join(positive_weights) or "仅均值"
        fit_rows.append(
            [
                row["leaf"],
                str(row["n"]),
                _fmt(row["current_global_structure"]["mae"]),
                _fmt((row.get("leaf_fit_positive") or {}).get("metrics", {}).get("mae", 0.0))
                if row.get("leaf_fit_positive")
                else "-",
                weight_text,
            ]
        )

    residual_rows = []
    for row in sorted(residual_summary["leaf_residuals"], key=lambda item: abs(item["mean_residual"]), reverse=True):
        residual_rows.append(
            [
                row["leaf"],
                str(row["n"]),
                _fmt(row["mae"]),
                f"{row['mean_residual']:+.3f}",
                str(row["hard_underestimated_count"]),
                str(row["easy_overestimated_count"]),
            ]
        )

    feature_residual_rows = [
        [feature, f"{value:+.3f}"]
        for feature, value in sorted(
            residual_summary["feature_residual_spearman"].items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
    ]

    under_rows = []
    for row in residual_summary["largest_underestimated"][:5]:
        under_rows.append(
            [
                row["annotation_id"],
                row["leaf"],
                _fmt(row["target"]),
                _fmt(row["predicted"]),
                f"{row['residual']:+.3f}",
                f"{row['answer']}/{row['easy_wrong_option']}",
            ]
        )

    over_rows = []
    for row in residual_summary["largest_overestimated"][:5]:
        over_rows.append(
            [
                row["annotation_id"],
                row["leaf"],
                _fmt(row["target"]),
                _fmt(row["predicted"]),
                f"{row['residual']:+.3f}",
                f"{row['answer']}/{row['easy_wrong_option']}",
            ]
        )

    return f"""# sentence_fill 叶族难度有效性探索

生成时间：2026-04-21
目的：检查“全局四轴拟合弱”是否掩盖了叶族内部有效性，并寻找下一轮应补的叶族维度。

## 1. 结论先行

全局结构四轴弱，不等于叶族内完全无效。更准确的结论是：

- 有些叶族内，结构轴可以提供一定排序信号，但收益不稳定，且经交叉验证后不宜直接封为主曲线。
- 大多数叶族的核心误差仍来自“叶族均值偏置 + 学生错项机制”，不是单纯调四轴权重能解决。
- 组合模型仍存在叶族残差，说明下一轮不应该只加全局经验轴，还要加少量叶族偏置维度。
- 另一个重要现象：多个叶族里结构轴出现“方向倒挂”或“方差太低”。这说明它们目前更像生成约束标签，而不是稳定的学生难度测量尺。

按较保守标准，当前可视为“结构轴叶族内有苗头”的叶族数：`{len(structure_wins)}`；更像“均值/偏置主导”的叶族数：`{len(mean_only)}`。这不是坏消息，反而说明体系层级应该拆清楚。

## 2. 叶族内：结构四轴是否有效

判断口径：

- `叶族均值基线`：只用该叶族平均难度预测。
- `当前全局结构轴`：当前四轴总分在该叶族上的表现。
- `叶族内四轴 CV`：只在该叶族内部重拟合四轴，并做 5-fold CV；样本少于 20 的叶族不做 CV。

![Leaf structure CV MAE](assets/leaf_structure_cv_mae.svg)

{_table(["叶族", "n", "真实均值", "真实SD", "均值MAE", "全局四轴MAE", "叶内四轴CV_MAE", "叶内四轴CV_Spearman", "最强单轴"], cv_rows)}

训练内拟合权重只作诊断，不作为上线配置：

{_table(["叶族", "n", "全局四轴MAE", "叶内训练MAE", "叶内候选权重"], fit_rows)}

阅读解释：

- `开头-概括后文` 和 `开头-首句中的分句` 在训练内能看到正向结构信号，尤其是 `global_context_dependency` 与 `blank_function_ambiguity`，但 CV 后不稳，说明样本还不足以封权重。
- `中间-启下`、`中间-承上启下`、`结尾-总结前文` 里出现负向诊断信号：越被结构轴判复杂，真实正确率不一定越低，有时反而更容易。这常见于“逻辑关系很显性”的题。
- `话题引入` 的全量真实难度最高之一，但结构轴解释力弱，说明它的难点不在横线位置本身，而在话题框架/引用/格言与全文主旨的贴合。
- `特殊题型-问语句在文中的位置` 样本太少，且任务形态已经偏插入句定位，不宜和普通 sentence_fill 共曲线。

## 3. 叶族间：残差仍然存在

组合模型当前权重：

- `easy_wrong_option_competition`: `{label_report["models"]["combined"]["weights"].get("label.easy_wrong_option_competition")}`
- `correct_option_abstraction_gap`: `{label_report["models"]["combined"]["weights"].get("label.correct_option_abstraction_gap")}`
- `local_binding_complexity`: `{label_report["models"]["combined"]["weights"].get("axis.local_binding_complexity")}`
- `global_context_dependency`: `{label_report["models"]["combined"]["weights"].get("axis.global_context_dependency")}`

即便组合模型明显优于纯结构轴，叶族残差仍然不平。

![Combined residual by leaf](assets/combined_residual_by_leaf.svg)

{_table(["叶族", "n", "MAE", "平均残差 target-pred", "被低估难题数", "被高估易题数"], residual_rows)}

解释残差方向：

- `平均残差 > 0`：模型低估了难度，真实学生更容易错。
- `平均残差 < 0`：模型高估了难度，真实学生没那么容易错。

## 4. 现有标签维度之外，还像缺什么

在组合模型残差上看，已有观察维度与残差的相关如下：

{_table(["观察维度", "与残差 Spearman"], feature_residual_rows)}

这提示下一轮优先探索这些维度：

1. `leaf_baseline_offset`：叶族天然均值不同，尤其是话题引入、尾句分句、特殊位置题，不应完全压进同一条全局曲线。
2. `topic_entry_abstraction`：开头-话题引入题不是简单“引入话题”，难点常在从具体材料跳到更高层话题框架；诗句/格言引入尤其需要单列。
3. `idiom_or_quote_mapping`：含成语、俗语、诗句的题，学生不是只比较语义，还要把抽象表达映射到材料论证关系。
4. `clause_continuation_constraint`：首句/尾句中的分句题有句法续接约束，但句法约束有时降低难度，有时制造陷阱，需要单独拆。
5. `conclusion_force_strength`：结尾总结/对策类题，正确项是否被前文强制推出，比“是否结尾”更影响难度。
6. `option_order_polarity_trap`：有些易题看似选项很像，但只要注意前后顺序、转折方向、褒贬方向就很容易排除；当前“表层相似”容易把它高估。
7. `option_register_gap`：有些错项不只是语义竞争，而是表达风格、政策话语、学术话语与原文语域更贴近，学生会被表层风格带偏。

## 5. 误差样本：哪些题被低估/高估

被低估的难题：

{_table(["id", "叶族", "真实难度", "预测难度", "残差", "答案/易错"], under_rows)}

被高估的易题：

{_table(["id", "叶族", "真实难度", "预测难度", "残差", "答案/易错"], over_rows)}

## 6. 推荐落地方式

不要把叶族都拆成独立模型。建议采用：

```text
family structural axes
  -> family empirical axes
  -> leaf offset / leaf residual hints
  -> item-level truth calibration
```

本轮可以进入 candidate patch 的不是“每个叶族一套规则”，而是：

- 保留四个结构轴作为生成控制主干。
- 新增两个家族经验轴作为真实难度校准主干。
- 给叶族增加只读偏置字段，例如 `leaf_difficulty_offset_hint`、`leaf_residual_risk_tags`。
- 对 `话题引入`、`首/尾句分句`、`特殊位置题` 做下一轮重点标注。
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    curve_samples = _load_curve_samples()
    labeled_rows = _load_labeled_rows()
    label_report = json.loads(LABEL_JSON.read_text(encoding="utf-8"))

    leaf_summary = _leaf_structure_summary(curve_samples)
    residual_summary = _label_residual_summary(labeled_rows, label_report)

    cv_data = [
        (row["leaf"], row["leaf_fit_cv_positive"]["mae"])
        for row in leaf_summary
        if row.get("leaf_fit_cv_positive")
    ]
    _bar_svg(
        "Per-leaf structural-axis CV MAE",
        sorted(cv_data, key=lambda item: item[1], reverse=True),
        ASSET_DIR / "leaf_structure_cv_mae.svg",
    )
    _diverging_svg(
        "Combined-model mean residual by leaf",
        sorted(
            [(row["leaf"], row["mean_residual"]) for row in residual_summary["leaf_residuals"]],
            key=lambda item: item[1],
            reverse=True,
        ),
        ASSET_DIR / "combined_residual_by_leaf.svg",
    )

    report = {
        "leaf_structure_summary": leaf_summary,
        "label_residual_summary": residual_summary,
    }
    (OUT_DIR / "leaf_difficulty_exploration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    csv_rows = []
    for row in leaf_summary:
        csv_rows.append(
            {
                "leaf": row["leaf"],
                "n": row["n"],
                "target_mean": row["target_mean"],
                "target_sd": row["target_sd"],
                "mean_baseline_mae": row["leaf_mean_baseline"]["mae"],
                "current_global_structure_mae": row["current_global_structure"]["mae"],
                "leaf_fit_train_mae": (row.get("leaf_fit_positive") or {}).get("metrics", {}).get("mae"),
                "leaf_fit_cv_mae": (row.get("leaf_fit_cv_positive") or {}).get("mae"),
                "leaf_fit_cv_spearman": (row.get("leaf_fit_cv_positive") or {}).get("spearman"),
                "best_axis": max(row["axis_spearman"].items(), key=lambda item: abs(item[1]))[0],
                "best_axis_spearman": max(row["axis_spearman"].items(), key=lambda item: abs(item[1]))[1],
            }
        )
    _write_csv(OUT_DIR / "leaf_structure_summary.csv", csv_rows)
    (OUT_DIR / "leaf_difficulty_exploration_report.md").write_text(
        _render_report(leaf_summary, residual_summary, label_report),
        encoding="utf-8",
    )
    index = {
        "report": str((OUT_DIR / "leaf_difficulty_exploration_report.md").relative_to(ROOT)),
        "json": str((OUT_DIR / "leaf_difficulty_exploration.json").relative_to(ROOT)),
        "csv": str((OUT_DIR / "leaf_structure_summary.csv").relative_to(ROOT)),
        "assets": sorted(str(path.relative_to(ROOT)) for path in ASSET_DIR.glob("*.svg")),
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
