"""Fit sentence_fill difficulty with subagent-labeled leaf axes.

This script compares:
- existing structural axes
- existing global empirical labels
- newly labeled leaf-specific axes

It is an offline experiment only. It does not mutate prompt assets, card specs,
or validator configuration.
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
GLOBAL_LABEL_DIR = ROOT / "reports/difficulty_control/empirical_labeling"
LEAF_LABEL_DIR = ROOT / "reports/difficulty_control/leaf_axis_labeling"
LEAF_HYPOTHESES_JSON = ROOT / "reports/difficulty_control/leaf_feature_exploration/leaf_feature_hypotheses.json"
OUT_DIR = ROOT / "reports/difficulty_control/leaf_axis_fit"
ASSET_DIR = OUT_DIR / "assets"

STRUCTURE_FEATURES = (
    "axis.local_binding_complexity",
    "axis.global_context_dependency",
    "axis.distractor_similarity",
    "axis.blank_function_ambiguity",
)

GLOBAL_EMPIRICAL_FEATURES = (
    "global.easy_wrong_option_competition",
    "global.correct_option_abstraction_gap",
    "global.surface_trap_salience",
    "global.plausible_distractor_count_norm",
    "global.expression_register_difficulty",
    "global.reasoning_operation_complexity",
    "global.blank_syntactic_form_complexity",
)

LEAF_META_FEATURES = (
    "leaf_meta.mean_score",
    "leaf_meta.weighted_mean_score",
    "leaf_meta.max_score",
    "leaf_meta.high_score_count_norm",
    "leaf_meta.score_spread",
)

ALPHAS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    return sum(data) / len(data) if data else 0.0


def _std(values: Iterable[float]) -> float:
    data = list(values)
    if len(data) < 2:
        return 0.0
    avg = _mean(data)
    return (sum((value - avg) ** 2 for value in data) / (len(data) - 1)) ** 0.5


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        rank = (cursor + end + 2) / 2.0
        for _, index in ordered[cursor : end + 1]:
            ranks[index] = rank
        cursor = end + 1
    return ranks


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


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 2:
        return 0.0
    return _pearson(_rank(left), _rank(right))


def _band(value: float) -> str:
    if value <= 0.30:
        return "easy"
    if value >= 0.55:
        return "hard"
    return "medium"


def _metrics(target: list[float], predicted: list[float]) -> dict[str, float]:
    if not target:
        return {"mae": 0.0, "rmse": 0.0, "pearson": 0.0, "spearman": 0.0, "band_agreement": 0.0}
    return {
        "mae": round(_mean(abs(y - p) for y, p in zip(target, predicted)), 4),
        "rmse": round(math.sqrt(_mean((y - p) ** 2 for y, p in zip(target, predicted))), 4),
        "pearson": round(_pearson(predicted, target), 4),
        "spearman": round(_spearman(predicted, target), 4),
        "band_agreement": round(_mean(1.0 if _band(y) == _band(p) else 0.0 for y, p in zip(target, predicted)), 4),
    }


def load_global_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(GLOBAL_LABEL_DIR.glob("label_output_*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                rows[row["annotation_id"]] = row
    return rows


def load_leaf_labels() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    missing = []
    for name in ("A", "B", "C"):
        path = LEAF_LABEL_DIR / f"leaf_axis_label_output_{name}.jsonl"
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row.get("leaf_axis_scores"):
                    raise ValueError(f"{path}:{line_number} missing leaf_axis_scores")
                rows[row["annotation_id"]] = row
    if missing:
        raise FileNotFoundError("Missing leaf-axis label outputs: " + ", ".join(missing))
    return rows


def merge_rows() -> list[dict[str, Any]]:
    global_rows = load_global_rows()
    leaf_rows = load_leaf_labels()
    missing = sorted(set(global_rows) - set(leaf_rows))
    extra = sorted(set(leaf_rows) - set(global_rows))
    if missing or extra:
        raise ValueError(f"Label mismatch. missing={missing[:5]} extra={extra[:5]}")
    merged = []
    for annotation_id in sorted(global_rows):
        row = dict(global_rows[annotation_id])
        row["leaf_axis_scores"] = leaf_rows[annotation_id]["leaf_axis_scores"]
        row["leaf_axis_confidence"] = leaf_rows[annotation_id].get("leaf_axis_confidence")
        row["leaf_axis_note"] = leaf_rows[annotation_id].get("leaf_axis_note")
        merged.append(row)
    return merged


def leaf_axis_features(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    names = sorted({name for row in rows for name in (row.get("leaf_axis_scores") or {})})
    return tuple(f"leaf.{name}" for name in names)


def leaf_onehot_features(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(f"leaf_id.{leaf}" for leaf in sorted({row["leaf"] for row in rows}))


def load_leaf_importance() -> dict[str, dict[str, float]]:
    hypotheses = json.loads(LEAF_HYPOTHESES_JSON.read_text(encoding="utf-8"))
    output: dict[str, dict[str, float]] = {}
    for leaf, payload in hypotheses.items():
        output[leaf] = {
            name: float(importance)
            for name, importance, _ in payload.get("candidate_dimensions") or []
        }
    return output


LEAF_IMPORTANCE = load_leaf_importance()


def leaf_meta_value(row: dict[str, Any], key: str) -> float:
    scores = {name: float(value) for name, value in (row.get("leaf_axis_scores") or {}).items()}
    if not scores:
        return 0.0
    values = list(scores.values())
    if key == "mean_score":
        return _clamp(_mean(values))
    if key == "weighted_mean_score":
        weights = LEAF_IMPORTANCE.get(row["leaf"], {})
        denominator = sum(weights.get(name, 1.0) for name in scores) or 1.0
        return _clamp(sum(value * weights.get(name, 1.0) for name, value in scores.items()) / denominator)
    if key == "max_score":
        return _clamp(max(values))
    if key == "high_score_count_norm":
        return _clamp(sum(1 for value in values if value >= 0.70) / max(len(values), 1))
    if key == "score_spread":
        return _clamp(max(values) - min(values))
    raise KeyError(key)


def feature_value(row: dict[str, Any], feature: str) -> float:
    if feature.startswith("axis."):
        return float((row.get("axis_scores") or {}).get(feature.split(".", 1)[1], 0.0))
    if feature.startswith("global."):
        labels = row.get("labels") or {}
        key = feature.split(".", 1)[1]
        if key == "plausible_distractor_count_norm":
            return _clamp(float(labels.get("plausible_distractor_count") or 0.0) / 3.0)
        return _clamp(float(labels.get(key) or 0.0))
    if feature.startswith("leaf."):
        return _clamp(float((row.get("leaf_axis_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("leaf_meta."):
        return leaf_meta_value(row, feature.split(".", 1)[1])
    if feature.startswith("leaf_id."):
        return 1.0 if row["leaf"] == feature.split(".", 1)[1] else 0.0
    raise KeyError(feature)


def target_value(row: dict[str, Any]) -> float:
    return _clamp(float(row["empirical_difficulty"]))


def design_matrix(rows: list[dict[str, Any]], features: tuple[str, ...]) -> list[list[float]]:
    return [[feature_value(row, feature) for feature in features] for row in rows]


def standardize_train(x_rows: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    if not x_rows:
        return [], [], []
    cols = len(x_rows[0])
    means = [_mean(row[col] for row in x_rows) for col in range(cols)]
    scales = []
    for col in range(cols):
        scale = _std(row[col] for row in x_rows)
        scales.append(scale if scale > 1e-9 else 1.0)
    return (
        [[(value - means[col]) / scales[col] for col, value in enumerate(row)] for row in x_rows],
        means,
        scales,
    )


def apply_standardize(x_rows: list[list[float]], means: list[float], scales: list[float]) -> list[list[float]]:
    return [[(value - means[col]) / scales[col] for col, value in enumerate(row)] for row in x_rows]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    a = [row[:] + [value] for row, value in zip(matrix, vector)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            a[col][col] += 1e-8
            pivot = col
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        if abs(pivot_value) < 1e-12:
            continue
        for j in range(col, n + 1):
            a[col][j] /= pivot_value
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if abs(factor) < 1e-12:
                continue
            for j in range(col, n + 1):
                a[row][j] -= factor * a[col][j]
    return [a[row][n] for row in range(n)]


def fit_ridge(x_rows: list[list[float]], target: list[float], *, alpha: float) -> dict[str, Any]:
    x_std, means, scales = standardize_train(x_rows)
    # Add intercept. Intercept is not penalized.
    x_aug = [[1.0] + row for row in x_std]
    cols = len(x_aug[0])
    xtx = [[0.0 for _ in range(cols)] for _ in range(cols)]
    xty = [0.0 for _ in range(cols)]
    for row, y in zip(x_aug, target):
        for i in range(cols):
            xty[i] += row[i] * y
            for j in range(cols):
                xtx[i][j] += row[i] * row[j]
    for idx in range(1, cols):
        xtx[idx][idx] += alpha
    coefs = solve_linear_system(xtx, xty)
    return {"coefs": coefs, "means": means, "scales": scales, "alpha": alpha}


def predict(model: dict[str, Any], x_rows: list[list[float]]) -> list[float]:
    x_std = apply_standardize(x_rows, model["means"], model["scales"])
    predictions = []
    for row in x_std:
        score = model["coefs"][0] + sum(coef * value for coef, value in zip(model["coefs"][1:], row))
        predictions.append(_clamp(score))
    return predictions


def select_alpha(rows: list[dict[str, Any]], features: tuple[str, ...], *, k: int = 4) -> float:
    if len(rows) < 8:
        return 1.0
    best_alpha = ALPHAS[0]
    best_mae = float("inf")
    for alpha in ALPHAS:
        actuals: list[float] = []
        predictions: list[float] = []
        for fold in range(k):
            train = [row for index, row in enumerate(rows) if index % k != fold]
            test = [row for index, row in enumerate(rows) if index % k == fold]
            if not train or not test:
                continue
            train_x = design_matrix(train, features)
            train_y = [target_value(row) for row in train]
            model = fit_ridge(train_x, train_y, alpha=alpha)
            predictions.extend(predict(model, design_matrix(test, features)))
            actuals.extend(target_value(row) for row in test)
        mae = _metrics(actuals, predictions)["mae"]
        if mae < best_mae:
            best_mae = mae
            best_alpha = alpha
    return best_alpha


def fit_model(rows: list[dict[str, Any]], features: tuple[str, ...]) -> dict[str, Any]:
    alpha = select_alpha(rows, features)
    x_rows = design_matrix(rows, features)
    target = [target_value(row) for row in rows]
    model = fit_ridge(x_rows, target, alpha=alpha)
    predictions = predict(model, x_rows)
    coefficients = {
        feature: round(coef, 4)
        for feature, coef in zip(features, model["coefs"][1:])
    }
    scored_rows = []
    for row, predicted in zip(rows, predictions):
        scored_rows.append(
            {
                "annotation_id": row.get("annotation_id"),
                "qid": row.get("qid"),
                "leaf": row.get("leaf"),
                "empirical_difficulty": round(target_value(row), 4),
                "predicted_difficulty": round(predicted, 4),
                "absolute_error": round(abs(target_value(row) - predicted), 4),
                "answer": row.get("answer"),
                "easy_wrong_option": row.get("easy_wrong_option"),
                "leaf_axis_note": row.get("leaf_axis_note"),
            }
        )
    return {
        "features": list(features),
        "feature_count": len(features),
        "alpha": alpha,
        "metrics": _metrics(target, predictions),
        "cross_validation": cross_validate(rows, features),
        "leaf_holdout": leaf_holdout_validate(rows, features),
        "coefficients": coefficients,
        "top_coefficients": sorted(
            coefficients.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:15],
        "largest_errors": sorted(scored_rows, key=lambda item: item["absolute_error"], reverse=True)[:10],
        "scored_rows": scored_rows,
    }


def cross_validate(rows: list[dict[str, Any]], features: tuple[str, ...], *, k: int = 5) -> dict[str, Any]:
    actuals: list[float] = []
    predictions: list[float] = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        alpha = select_alpha(train, features)
        model = fit_ridge(design_matrix(train, features), [target_value(row) for row in train], alpha=alpha)
        pred = predict(model, design_matrix(test, features))
        target = [target_value(row) for row in test]
        predictions.extend(pred)
        actuals.extend(target)
        folds.append({"fold": fold + 1, "n": len(test), "alpha": alpha, "metrics": _metrics(target, pred)})
    return {"overall": _metrics(actuals, predictions), "folds": folds}


def leaf_holdout_validate(rows: list[dict[str, Any]], features: tuple[str, ...]) -> dict[str, Any]:
    actuals: list[float] = []
    predictions: list[float] = []
    leaves = sorted({row["leaf"] for row in rows})
    folds = []
    for leaf in leaves:
        train = [row for row in rows if row["leaf"] != leaf]
        test = [row for row in rows if row["leaf"] == leaf]
        if len(test) < 2 or not train:
            continue
        alpha = select_alpha(train, features)
        model = fit_ridge(design_matrix(train, features), [target_value(row) for row in train], alpha=alpha)
        pred = predict(model, design_matrix(test, features))
        target = [target_value(row) for row in test]
        predictions.extend(pred)
        actuals.extend(target)
        folds.append({"leaf": leaf, "n": len(test), "alpha": alpha, "metrics": _metrics(target, pred)})
    return {"overall": _metrics(actuals, predictions), "folds": folds}


def leaf_summary(model: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in model["scored_rows"]:
        grouped[row["leaf"]].append(row)
    summary = []
    for leaf, rows in sorted(grouped.items()):
        summary.append(
            {
                "leaf": leaf,
                "n": len(rows),
                "mae": round(_mean(float(row["absolute_error"]) for row in rows), 4),
                "bias": round(
                    _mean(float(row["predicted_difficulty"]) - float(row["empirical_difficulty"]) for row in rows),
                    4,
                ),
                "target_mean": round(_mean(float(row["empirical_difficulty"]) for row in rows), 4),
                "predicted_mean": round(_mean(float(row["predicted_difficulty"]) for row in rows), 4),
            }
        )
    return summary


def _bar_svg(title: str, data: list[tuple[str, float]], path: Path, *, width: int = 920, height: int = 430) -> None:
    margin_left = 240
    margin_right = 46
    margin_top = 56
    margin_bottom = 36
    plot_width = width - margin_left - margin_right
    row_h = (height - margin_top - margin_bottom) / max(len(data), 1)
    max_value = max(max(value for _, value in data), 0.001)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="36" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(data):
        y = margin_top + idx * row_h + row_h * 0.18
        bar_h = max(10, row_h * 0.5)
        bar_w = plot_width * value / max_value
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


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    model_rows = []
    model_titles = {
        "structure_only": "原结构四轴",
        "global_empirical": "全局经验轴",
        "leaf_meta": "叶族汇总信号",
        "leaf_axis": "叶族维度",
        "global_plus_leaf_meta": "全局经验 + 叶族汇总",
        "global_plus_leaf": "全局经验 + 叶族维度",
        "all_axes_plus_leaf_meta": "结构 + 全局经验 + 叶族汇总",
        "all_axes": "结构 + 全局经验 + 叶族维度",
        "all_axes_with_leaf_id_diagnostic": "含叶族ID诊断项",
    }
    for name, model in report["models"].items():
        cv = model["cross_validation"]["overall"]
        holdout = model["leaf_holdout"]["overall"]
        model_rows.append(
            [
                model_titles.get(name, name),
                str(model["feature_count"]),
                _fmt(model["metrics"]["mae"]),
                _fmt(cv["mae"]),
                _fmt(cv["spearman"]),
                _fmt(cv["band_agreement"]),
                _fmt(holdout["mae"]),
                _fmt(holdout["spearman"]),
            ]
        )

    best = report["models"][report["best_model"]]
    global_cv = report["models"]["global_empirical"]["cross_validation"]["overall"]
    leaf_axis_cv = report["models"]["leaf_axis"]["cross_validation"]["overall"]
    leaf_meta_cv = report["models"]["leaf_meta"]["cross_validation"]["overall"]
    global_leaf_meta_cv = report["models"]["global_plus_leaf_meta"]["cross_validation"]["overall"]
    all_leaf_meta_cv = report["models"]["all_axes_plus_leaf_meta"]["cross_validation"]["overall"]
    coef_rows = [[f"`{name}`", f"{value:+.4f}"] for name, value in best["top_coefficients"][:12]]
    leaf_rows = [
        [
            row["leaf"],
            str(row["n"]),
            _fmt(row["target_mean"]),
            _fmt(row["predicted_mean"]),
            _fmt(row["mae"]),
            f"{row['bias']:+.3f}",
        ]
        for row in sorted(report["best_leaf_summary"], key=lambda item: item["mae"], reverse=True)
    ]

    return f"""# sentence_fill 叶族维度标注拟合实验

生成时间：2026-04-21
样本：`{report["sample_count"]}` 道人工阅读标注样本。
标注方式：subagent 分包阅读标注叶族候选维度，输入中不包含正确率或经验难度。

## 1. 结论

加入叶族维度后，模型是否有效主要看两个指标：

- `5-fold CV`：已知叶族内的泛化能力，适合评估“我们已经有这些叶族，补叶族轴是否能控得更细”。
- `leaf-held-out`：完全留出一个叶族的迁移能力，适合评估“叶族维度能不能跨叶族迁移”。对叶族专属维度来说，这个指标天然更苛刻。

本次最优模型：`{report["best_model"]}`。

实验判定：

- 暂不建议把本轮叶族维度升格为正式难度权重。`global_empirical` 的 5-fold MAE 为 `{_fmt(global_cv["mae"])}`，仍优于 `leaf_axis` 的 `{_fmt(leaf_axis_cv["mae"])}`。
- 叶族维度压缩成汇总信号后有所改善，`leaf_meta` 的 5-fold Spearman 为 `{_fmt(leaf_meta_cv["spearman"])}`，说明方向不是完全无效，但 MAE `{_fmt(leaf_meta_cv["mae"])}` 仍不够。
- `全局经验 + 叶族汇总` 没超过全局经验轴：MAE `{_fmt(global_leaf_meta_cv["mae"])}` vs `{_fmt(global_cv["mae"])}`。
- `结构 + 全局经验 + 叶族汇总` 的 Spearman `{_fmt(all_leaf_meta_cv["spearman"])}` 略高于全局经验轴 `{_fmt(global_cv["spearman"])}`，但 MAE `{_fmt(all_leaf_meta_cv["mae"])}` 仍略差。当前只能作为诊断信号，不宜作为主权重。

{_table(["模型", "特征数", "Train MAE", "5-fold MAE", "5-fold Spearman", "5-fold 档位一致", "Leaf-held-out MAE", "Leaf-held-out Spearman"], model_rows)}

![Model CV MAE](assets/model_cv_mae.svg)

![Model CV Spearman](assets/model_cv_spearman.svg)

## 2. 最优模型的主要系数

注意：这里是 ridge 标准化系数，用于判断方向与相对贡献，不应直接回写配置。

{_table(["特征", "标准化系数"], coef_rows)}

## 3. 叶族内表现

![Best model leaf MAE](assets/best_model_leaf_mae.svg)

{_table(["叶族", "n", "真实均值", "预测均值", "MAE", "Bias"], leaf_rows)}

## 4. 解释

如果 `全局经验 + 叶族维度` 或 `all_axes` 的 5-fold 指标优于 `全局经验轴`，说明叶族维度确实帮助我们在已知叶族内做精细控制。
如果 leaf-held-out 没有同步提升，这不是失败，而是说明：叶族维度更适合作为“叶族特征层”，不是跨叶族通用母族曲线。

工程建议：

- 叶族维度先作为 `candidate leaf axes` 接入 diff/backtest，不自动回写主配置。
- 下一轮扩大标注后，再把稳定维度升格到正式 leaf protocol。
- 不建议用含 `leaf_id` 的诊断模型上线；它只用于判断叶族均值偏置有多强。
"""


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    rows = merge_rows()
    leaf_features = leaf_axis_features(rows)
    leaf_id_features = leaf_onehot_features(rows)

    model_features = {
        "structure_only": STRUCTURE_FEATURES,
        "global_empirical": GLOBAL_EMPIRICAL_FEATURES,
        "leaf_meta": LEAF_META_FEATURES,
        "leaf_axis": leaf_features,
        "global_plus_leaf_meta": GLOBAL_EMPIRICAL_FEATURES + LEAF_META_FEATURES,
        "global_plus_leaf": GLOBAL_EMPIRICAL_FEATURES + leaf_features,
        "all_axes_plus_leaf_meta": STRUCTURE_FEATURES + GLOBAL_EMPIRICAL_FEATURES + LEAF_META_FEATURES,
        "all_axes": STRUCTURE_FEATURES + GLOBAL_EMPIRICAL_FEATURES + leaf_features,
        "all_axes_with_leaf_id_diagnostic": STRUCTURE_FEATURES
        + GLOBAL_EMPIRICAL_FEATURES
        + leaf_features
        + leaf_id_features,
    }
    models = {name: fit_model(rows, features) for name, features in model_features.items()}
    best_model = min(
        (name for name in models if name != "all_axes_with_leaf_id_diagnostic"),
        key=lambda name: (
            models[name]["cross_validation"]["overall"]["mae"],
            -models[name]["cross_validation"]["overall"]["spearman"],
        ),
    )
    report = {
        "sample_count": len(rows),
        "leaf_axis_feature_count": len(leaf_features),
        "leaf_axis_features": list(leaf_features),
        "best_model": best_model,
        "models": models,
        "best_leaf_summary": leaf_summary(models[best_model]),
    }

    (OUT_DIR / "leaf_axis_fit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "leaf_axis_fit_report.md").write_text(render_markdown(report), encoding="utf-8")
    write_csv(OUT_DIR / "best_model_scored_rows.csv", models[best_model]["scored_rows"])

    title_map = {
        "structure_only": "结构四轴",
        "global_empirical": "全局经验",
        "leaf_meta": "叶族汇总",
        "leaf_axis": "叶族维度",
        "global_plus_leaf_meta": "全局+叶族汇总",
        "global_plus_leaf": "全局+叶族",
        "all_axes_plus_leaf_meta": "全量+叶族汇总",
        "all_axes": "全量组合",
    }
    _bar_svg(
        "5-fold CV MAE",
        [(title_map[name], models[name]["cross_validation"]["overall"]["mae"]) for name in title_map],
        ASSET_DIR / "model_cv_mae.svg",
    )
    _bar_svg(
        "5-fold CV Spearman",
        [(title_map[name], max(0.0, models[name]["cross_validation"]["overall"]["spearman"])) for name in title_map],
        ASSET_DIR / "model_cv_spearman.svg",
    )
    _bar_svg(
        "Best model MAE by leaf",
        [(row["leaf"], row["mae"]) for row in sorted(report["best_leaf_summary"], key=lambda item: item["mae"], reverse=True)],
        ASSET_DIR / "best_model_leaf_mae.svg",
        height=500,
    )
    index = {
        "report": str((OUT_DIR / "leaf_axis_fit_report.md").relative_to(ROOT)),
        "json": str((OUT_DIR / "leaf_axis_fit_report.json").relative_to(ROOT)),
        "csv": str((OUT_DIR / "best_model_scored_rows.csv").relative_to(ROOT)),
        "assets": sorted(str(path.relative_to(ROOT)) for path in ASSET_DIR.glob("*.svg")),
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
