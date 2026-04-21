from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

STRUCTURE_FEATURES = (
    "axis.local_binding_complexity",
    "axis.global_context_dependency",
    "axis.distractor_similarity",
    "axis.blank_function_ambiguity",
)

LABEL_FEATURES = (
    "label.easy_wrong_option_competition",
    "label.correct_option_abstraction_gap",
    "label.surface_trap_salience",
    "label.plausible_distractor_count_norm",
    "label.expression_register_difficulty",
    "label.reasoning_operation_complexity",
    "label.blank_syntactic_form_complexity",
)


def load_labeled_rows(input_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("label_output_*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            labels = payload.get("labels") or {}
            required = [
                "easy_wrong_option_competition",
                "correct_option_abstraction_gap",
                "surface_trap_salience",
                "plausible_distractor_count",
                "expression_register_difficulty",
                "reasoning_operation_complexity",
                "blank_syntactic_form_complexity",
            ]
            missing = [key for key in required if key not in labels]
            if missing:
                raise ValueError(f"{path}:{line_number} missing labels: {missing}")
            rows.append(payload)
    return rows


def feature_value(row: dict[str, Any], feature: str) -> float:
    if feature.startswith("axis."):
        return clamp(float((row.get("axis_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    labels = row.get("labels") or {}
    key = feature.split(".", 1)[1]
    if key == "plausible_distractor_count_norm":
        return clamp(float(labels.get("plausible_distractor_count") or 0.0) / 3.0)
    return clamp(float(labels.get(key) or 0.0))


def target_value(row: dict[str, Any]) -> float:
    return clamp(float(row["empirical_difficulty"]))


def fit_model(rows: list[dict[str, Any]], features: tuple[str, ...], *, step: float = 0.1) -> dict[str, Any]:
    x_rows = [[feature_value(row, feature) for feature in features] for row in rows]
    y = [target_value(row) for row in rows]
    best = grid_search_weights(x_rows, y, feature_count=len(features), step=step)
    raw_scores = [dot(row, best["weights"]) for row in x_rows]
    predictions = [clamp(best["intercept"] + best["scale"] * score) for score in raw_scores]
    scored_rows = []
    for row, raw_score, predicted in zip(rows, raw_scores, predictions):
        scored_rows.append(
            {
                "annotation_id": row.get("annotation_id"),
                "qid": row.get("qid"),
                "leaf": row.get("leaf"),
                "correct_rate": row.get("correct_rate"),
                "empirical_difficulty": row.get("empirical_difficulty"),
                "predicted_difficulty": round(predicted, 4),
                "absolute_error": round(abs(predicted - target_value(row)), 4),
                "raw_score": round(raw_score, 4),
                "answer": row.get("answer"),
                "easy_wrong_option": row.get("easy_wrong_option"),
                "label_note": (row.get("labels") or {}).get("label_note"),
            }
        )
    return {
        "features": features,
        "weights": {feature: round(weight, 4) for feature, weight in zip(features, best["weights"])},
        "intercept": round(best["intercept"], 4),
        "scale": round(best["scale"], 4),
        "metrics": metrics(y, predictions),
        "cross_validation": cross_validate(x_rows, y, features, step=step),
        "largest_errors": sorted(scored_rows, key=lambda item: item["absolute_error"], reverse=True)[:10],
        "scored_rows": scored_rows,
    }


def grid_search_weights(x_rows: list[list[float]], y: list[float], *, feature_count: int, step: float) -> dict[str, Any]:
    units = int(round(1.0 / step))
    best: dict[str, Any] | None = None

    def rec(remaining: int, slots: int, prefix: list[int]) -> None:
        nonlocal best
        if slots == 1:
            parts = prefix + [remaining]
            weights = [part / units for part in parts]
            raw = [dot(row, weights) for row in x_rows]
            intercept, scale = fit_affine(raw, y)
            if scale < 0:
                return
            pred = [clamp(intercept + scale * score) for score in raw]
            current = {
                "weights": weights,
                "intercept": intercept,
                "scale": scale,
                "mae": mean(abs(left - right) for left, right in zip(y, pred)),
                "spearman": spearman(pred, y),
            }
            if best is None or (current["mae"], -current["spearman"]) < (best["mae"], -best["spearman"]):
                best = current
            return
        for value in range(remaining + 1):
            rec(remaining - value, slots - 1, prefix + [value])

    rec(units, feature_count, [])
    return best or {
        "weights": [1.0 / feature_count] * feature_count,
        "intercept": 0.0,
        "scale": 1.0,
    }


def cross_validate(x_rows: list[list[float]], y: list[float], features: tuple[str, ...], *, step: float, k: int = 5) -> dict[str, Any]:
    predictions: list[tuple[float, float]] = []
    folds = []
    for fold in range(k):
        train_x = [row for idx, row in enumerate(x_rows) if idx % k != fold]
        train_y = [value for idx, value in enumerate(y) if idx % k != fold]
        test_x = [row for idx, row in enumerate(x_rows) if idx % k == fold]
        test_y = [value for idx, value in enumerate(y) if idx % k == fold]
        if not test_x:
            continue
        fit = grid_search_weights(train_x, train_y, feature_count=len(features), step=step)
        raw = [dot(row, fit["weights"]) for row in test_x]
        pred = [clamp(fit["intercept"] + fit["scale"] * score) for score in raw]
        predictions.extend(zip(test_y, pred))
        folds.append({"fold": fold + 1, "n": len(test_y), "metrics": metrics(test_y, pred)})
    all_y = [item[0] for item in predictions]
    all_pred = [item[1] for item in predictions]
    return {"overall": metrics(all_y, all_pred), "folds": folds}


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


def metrics(y: list[float], pred: list[float]) -> dict[str, float]:
    if not y:
        return {}
    return {
        "mae": round(mean(abs(left - right) for left, right in zip(y, pred)), 4),
        "rmse": round(math.sqrt(mean((left - right) ** 2 for left, right in zip(y, pred))), 4),
        "pearson": round(pearson(pred, y), 4),
        "spearman": round(spearman(pred, y), 4),
        "band_agreement": round(mean(1.0 if band(left) == band(right) else 0.0 for left, right in zip(y, pred)), 4),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# sentence_fill 人工经验维度拟合实验",
        "",
        f"- 标注样本数：{report['sample_count']}",
        "- 目标：验证新增经验维度是否比当前四轴更能解释学生正确率。",
        "- 注意：这是离线实验，不自动回写题卡、prompt assets 或 validator。",
        "",
        "## 1. 模型对比",
        "",
        "| model | features | MAE | RMSE | Pearson | Spearman | band_agreement | CV_MAE | CV_Spearman |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, model in report["models"].items():
        metrics_payload = model["metrics"]
        cv_payload = model["cross_validation"]["overall"]
        lines.append(
            f"| {name} | {len(model['features'])} | {metrics_payload['mae']} | {metrics_payload['rmse']} | {metrics_payload['pearson']} | {metrics_payload['spearman']} | {metrics_payload['band_agreement']} | {cv_payload['mae']} | {cv_payload['spearman']} |"
        )

    lines.extend(["", "## 2. 最佳模型权重", ""])
    best_name = report["best_model"]
    best = report["models"][best_name]
    lines.extend([f"- best_model: `{best_name}`", "", "| feature | weight |", "| --- | ---: |"])
    for feature, weight in best["weights"].items():
        if weight > 0:
            lines.append(f"| `{feature}` | {weight} |")
    lines.extend(
        [
            "",
            f"- linear calibration: `difficulty = {best['intercept']} + {best['scale']} * weighted_score`",
            "",
            "## 3. 误差最大的样本",
            "",
            "| qid | leaf | empirical | predicted | abs_error | answer/easy_wrong | note |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in best["largest_errors"]:
        lines.append(
            f"| `{row['qid']}` | {row['leaf']} | {row['empirical_difficulty']} | {row['predicted_difficulty']} | {row['absolute_error']} | {row['answer']}/{row['easy_wrong_option']} | {row.get('label_note') or ''} |"
        )
    lines.extend(
        [
            "",
            "## 4. 初步结论",
            "",
            "- 如果 label_only 或 combined 明显优于 structure_only，说明缺失的不是四轴权重，而是经验难度维度。",
            "- 如果交叉验证收益也成立，才建议把这些维度升级为正式 candidate patch。",
            "- 如果只在训练内收益明显，说明标注样本仍偏小，需要扩标后再定权重。",
        ]
    )
    return "\n".join(lines)


def band(value: float) -> str:
    if value <= 0.30:
        return "easy"
    if value >= 0.55:
        return "hard"
    return "medium"


def dot(left: list[float], right: list[float]) -> float:
    return sum(x * y for x, y in zip(left, right))


def mean(values) -> float:
    data = [float(value) for value in values]
    return sum(data) / len(data) if data else 0.0


def pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator > 1e-12 else 0.0


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


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit empirical difficulty using manual sentence_fill labels.")
    parser.add_argument(
        "--input-dir",
        default=str(ROOT / "reports" / "difficulty_control" / "empirical_labeling"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports" / "difficulty_control" / "empirical_labeling"),
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    rows = load_labeled_rows(input_dir)
    if not rows:
        raise SystemExit(f"no labeled rows found in {input_dir}")

    models = {
        "structure_only": fit_model(rows, STRUCTURE_FEATURES, step=0.1),
        "label_only": fit_model(rows, LABEL_FEATURES, step=0.1),
        # Coarse grid is enough for this hand-label experiment; fine tuning can come after labels are expanded.
        "combined": fit_model(rows, STRUCTURE_FEATURES + LABEL_FEATURES, step=0.2),
    }
    best_model = min(models, key=lambda name: (models[name]["cross_validation"]["overall"]["mae"], -models[name]["cross_validation"]["overall"]["spearman"]))
    report = {
        "sample_count": len(rows),
        "best_model": best_model,
        "models": models,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "manual_label_fit_report.json"
    md_path = output_dir / "manual_label_fit_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"labeled rows: {len(rows)}")
    print(f"json report written to: {json_path}")
    print(f"markdown report written to: {md_path}")


if __name__ == "__main__":
    main()
