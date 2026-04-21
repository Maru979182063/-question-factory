from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "reports" / "difficulty_control" / "highfit_probe"
ASSET_DIR = PROBE_DIR / "assets"

CENTER_AXES = [
    "main_claim_visibility",
    "theme_term_overlap_trap",
    "correct_option_abstraction_gap",
    "local_detail_distractor_strength",
    "scope_degree_decision_load",
    "discourse_turn_complexity",
    "option_competition_density",
]
CENTER_PAIRWISE_AXES = [
    "easy_wrong_partial_validity",
    "easy_wrong_main_claim_proximity",
    "scope_degree_gap_subtlety",
    "correct_option_completeness_advantage_hidden",
    "decisive_evidence_visibility_load",
    "surface_wording_similarity",
    "exclusion_reasoning_load",
]
ORDER_AXES = [
    "first_sentence_ambiguity",
    "adjacency_bundle_ambiguity",
    "referential_dependency_load",
    "logical_sequence_depth",
    "option_sequence_competition",
    "global_coherence_reconstruction_load",
]


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    truth = {row["sample_id"]: row for row in _read_jsonl(PROBE_DIR / "highfit_probe_hidden_truth.jsonl")}
    labels = _load_labels()
    pairwise_labels = {row["sample_id"]: row for row in _load_pairwise_labels()}
    rows = [_merge_row(truth[row["sample_id"]], row) for row in labels if row["sample_id"] in truth]
    for row in rows:
        pairwise = pairwise_labels.get(row["sample_id"])
        if pairwise:
            row.update(pairwise)

    center_rows = [row for row in rows if row["family"] == "center_understanding"]
    order_rows = [row for row in rows if row["family"] == "sentence_order"]

    report: dict[str, Any] = {
        "sample_counts": {
            "all": len(rows),
            "center_understanding": len(center_rows),
            "sentence_order": len(order_rows),
        },
        "center": _evaluate_center(center_rows),
        "sentence_order": _evaluate_order(order_rows),
    }
    report["recommendation"] = _build_recommendation(report)

    (PROBE_DIR / "highfit_probe_fit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown(report)
    _write_best_scored_rows(report, rows)
    print(json.dumps(_console_summary(report), ensure_ascii=False, indent=2))


def _load_labels() -> list[dict[str, Any]]:
    paths = [
        PROBE_DIR / "center_highfit_label_output_A.jsonl",
        PROBE_DIR / "center_highfit_label_output_B.jsonl",
        PROBE_DIR / "center_highfit_label_output_C.jsonl",
        PROBE_DIR / "order_highfit_label_output_A.jsonl",
    ]
    labels: list[dict[str, Any]] = []
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing label outputs: " + ", ".join(missing))
    for path in paths:
        labels.extend(_read_jsonl(path))
    return labels


def _load_pairwise_labels() -> list[dict[str, Any]]:
    paths = [
        PROBE_DIR / "center_pairwise_label_output_A.jsonl",
        PROBE_DIR / "center_pairwise_label_output_B.jsonl",
        PROBE_DIR / "center_pairwise_label_output_C.jsonl",
    ]
    if any(not path.exists() for path in paths):
        return []
    labels: list[dict[str, Any]] = []
    for path in paths:
        labels.extend(_read_jsonl(path))
    return labels


def _merge_row(truth: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    merged = dict(truth)
    merged.update(label)
    merged["y"] = float(truth["empirical_difficulty"])
    return merged


def _evaluate_center(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = [
        _mean_model("mean_baseline"),
        _category_mean_model("leaf_mean", lambda row: row["leaf"]),
        _category_mean_model("error_type_mean", lambda row: _nested(row, "center_type", "dominant_error_type") or "unknown"),
        _category_mean_model(
            "local_detail_axis_mean",
            lambda row: str((row.get("center_axes") or {}).get("local_detail_distractor_strength", "unknown")),
        ),
        _ridge_model("local_detail_single_axis", ["local_detail_distractor_strength"], family="center"),
        _ridge_model(
            "center_selected_axes_ridge",
            ["local_detail_distractor_strength", "discourse_turn_complexity", "correct_option_abstraction_gap"],
            family="center",
        ),
        _category_mean_model("pairwise_type_mean", lambda row: _nested(row, "pairwise_type", "dominant_pairwise_trap") or "unknown"),
        _ridge_model("pairwise_axes_ridge", CENTER_PAIRWISE_AXES, family="center_pairwise"),
        _ridge_model(
            "pairwise_selected_axes_ridge",
            [
                "easy_wrong_partial_validity",
                "easy_wrong_main_claim_proximity",
                "scope_degree_gap_subtlety",
                "decisive_evidence_visibility_load",
                "exclusion_reasoning_load",
            ],
            family="center_pairwise",
        ),
        _ridge_model("center_axes_ridge", CENTER_AXES, family="center"),
        _ridge_model("center_axes_plus_leaf", CENTER_AXES, family="center", category_keys=[lambda row: f"leaf::{row['leaf']}"]),
        _ridge_model(
            "center_axes_plus_error_type",
            CENTER_AXES,
            family="center",
            category_keys=[lambda row: f"err::{_nested(row, 'center_type', 'dominant_error_type') or 'unknown'}"],
        ),
    ]
    result = _evaluate_models(rows, models)
    result["axis_diagnostics"] = _axis_diagnostics(rows, CENTER_AXES, family="center")
    result["pairwise_axis_diagnostics"] = _axis_diagnostics(rows, CENTER_PAIRWISE_AXES, family="center_pairwise")
    result["leaf_summary"] = _group_summary(rows, lambda row: row["leaf"])
    result["error_type_summary"] = _group_summary(rows, lambda row: _nested(row, "center_type", "dominant_error_type") or "unknown")
    result["leaf_fit"] = {
        leaf: _evaluate_center_leaf([row for row in rows if row["leaf"] == leaf])
        for leaf in sorted({row["leaf"] for row in rows})
    }
    return result


def _evaluate_center_leaf(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = [
        _mean_model("mean_baseline"),
        _category_mean_model("error_type_mean", lambda row: _nested(row, "center_type", "dominant_error_type") or "unknown"),
        _ridge_model("local_detail_single_axis", ["local_detail_distractor_strength"], family="center"),
        _ridge_model(
            "selected_leaf_axes_ridge",
            ["local_detail_distractor_strength", "discourse_turn_complexity", "correct_option_abstraction_gap"],
            family="center",
        ),
        _ridge_model("pairwise_axes_ridge", CENTER_PAIRWISE_AXES, family="center_pairwise"),
        _category_mean_model("pairwise_type_mean", lambda row: _nested(row, "pairwise_type", "dominant_pairwise_trap") or "unknown"),
    ]
    result = _evaluate_models(rows, models)
    result["axis_diagnostics"] = _axis_diagnostics(rows, CENTER_AXES, family="center")
    return result


def _evaluate_order(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = [
        _mean_model("mean_baseline"),
        _category_mean_model("sentence_count_mean", lambda row: str(row.get("sentence_count") or "unknown")),
        _category_mean_model("order_type_mean", lambda row: _nested(row, "order_type", "dominant_order_mechanism") or "unknown"),
        _category_mean_model(
            "first_sentence_axis_mean",
            lambda row: str((row.get("order_axes") or {}).get("first_sentence_ambiguity", "unknown")),
        ),
        _ridge_model("order_axes_ridge", ORDER_AXES, family="order"),
        _ridge_model(
            "order_axes_plus_sentence_count",
            ORDER_AXES,
            family="order",
            category_keys=[lambda row: f"n::{row.get('sentence_count') or 'unknown'}"],
        ),
        _ridge_model(
            "order_axes_plus_type",
            ORDER_AXES,
            family="order",
            category_keys=[lambda row: f"type::{_nested(row, 'order_type', 'dominant_order_mechanism') or 'unknown'}"],
        ),
    ]
    result = _evaluate_models(rows, models)
    result["axis_diagnostics"] = _axis_diagnostics(rows, ORDER_AXES, family="order")
    result["sentence_count_summary"] = _group_summary(rows, lambda row: str(row.get("sentence_count") or "unknown"))
    result["order_type_summary"] = _group_summary(rows, lambda row: _nested(row, "order_type", "dominant_order_mechanism") or "unknown")
    result["sentence_count_fit"] = {
        str(count): _evaluate_order_leaf([row for row in rows if str(row.get("sentence_count") or "unknown") == str(count)])
        for count in sorted({str(row.get("sentence_count") or "unknown") for row in rows})
        if len([row for row in rows if str(row.get("sentence_count") or "unknown") == str(count)]) >= 10
    }
    return result


def _evaluate_order_leaf(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = [
        _mean_model("mean_baseline"),
        _category_mean_model("order_type_mean", lambda row: _nested(row, "order_type", "dominant_order_mechanism") or "unknown"),
        _ridge_model("order_axes_ridge", ORDER_AXES, family="order"),
    ]
    result = _evaluate_models(rows, models)
    result["axis_diagnostics"] = _axis_diagnostics(rows, ORDER_AXES, family="order")
    return result


def _evaluate_models(rows: list[dict[str, Any]], models: list[dict[str, Any]]) -> dict[str, Any]:
    folds = _group_folds(rows, k=5)
    out: dict[str, Any] = {"models": []}
    for model in models:
        cv_pred = [math.nan] * len(rows)
        for test_idx in folds:
            train_idx = [idx for idx in range(len(rows)) if idx not in test_idx]
            train = [rows[idx] for idx in train_idx]
            test = [rows[idx] for idx in test_idx]
            predictor = model["fit"](train)
            for idx, pred in zip(test_idx, predictor(test), strict=True):
                cv_pred[idx] = pred
        train_predictor = model["fit"](rows)
        train_pred = train_predictor(rows)
        y = [row["y"] for row in rows]
        out["models"].append(
            {
                "name": model["name"],
                "train_mae": _mae(y, train_pred),
                "train_spearman": _spearman(y, train_pred),
                "cv_mae": _mae(y, cv_pred),
                "cv_spearman": _spearman(y, cv_pred),
                "cv_band_accuracy": _band_accuracy(y, cv_pred),
            }
        )
    out["best_by_mae"] = min(out["models"], key=lambda item: item["cv_mae"]) if rows else None
    out["best_by_spearman"] = max(out["models"], key=lambda item: item["cv_spearman"]) if rows else None
    return out


def _mean_model(name: str) -> dict[str, Any]:
    def fit(train: list[dict[str, Any]]) -> Callable[[list[dict[str, Any]]], list[float]]:
        mean = _safe_mean(row["y"] for row in train)
        return lambda test: [mean for _ in test]

    return {"name": name, "fit": fit}


def _category_mean_model(name: str, key_fn: Callable[[dict[str, Any]], str]) -> dict[str, Any]:
    def fit(train: list[dict[str, Any]]) -> Callable[[list[dict[str, Any]]], list[float]]:
        global_mean = _safe_mean(row["y"] for row in train)
        sums: dict[str, list[float]] = {}
        for row in train:
            sums.setdefault(key_fn(row), []).append(row["y"])
        means = {key: _safe_mean(values) for key, values in sums.items()}
        return lambda test: [means.get(key_fn(row), global_mean) for row in test]

    return {"name": name, "fit": fit}


def _ridge_model(
    name: str,
    axes: list[str],
    *,
    family: str,
    category_keys: list[Callable[[dict[str, Any]], str]] | None = None,
    alpha: float = 2.0,
) -> dict[str, Any]:
    category_keys = category_keys or []

    def fit(train: list[dict[str, Any]]) -> Callable[[list[dict[str, Any]]], list[float]]:
        category_vocab = sorted({key_fn(row) for key_fn in category_keys for row in train})
        x_train = _feature_matrix(train, axes=axes, family=family, category_keys=category_keys, category_vocab=category_vocab)
        y_train = [float(row["y"]) for row in train]
        means = _column_means(x_train)
        stds = _column_stds(x_train, means)
        x_scaled = _scale_matrix(x_train, means, stds)
        x_design = [[1.0] + row for row in x_scaled]
        normal_x = _normal_matrix(x_design, alpha=alpha)
        normal_y = _normal_vector(x_design, y_train)
        weights = _solve_linear_system(normal_x, normal_y)

        def predict(test: list[dict[str, Any]]) -> list[float]:
            x_test = _feature_matrix(test, axes=axes, family=family, category_keys=category_keys, category_vocab=category_vocab)
            x_test_scaled = _scale_matrix(x_test, means, stds)
            x_test_design = [[1.0] + row for row in x_test_scaled]
            raw = [_dot(row, weights) for row in x_test_design]
            return [float(min(1.0, max(0.0, value))) for value in raw]

        return predict

    return {"name": name, "fit": fit}


def _feature_matrix(
    rows: list[dict[str, Any]],
    *,
    axes: list[str],
    family: str,
    category_keys: list[Callable[[dict[str, Any]], str]],
    category_vocab: list[str],
) -> list[list[float]]:
    if family == "center":
        axis_key = "center_axes"
    elif family == "center_pairwise":
        axis_key = "center_pairwise_axes"
    else:
        axis_key = "order_axes"
    matrix: list[list[float]] = []
    for row in rows:
        axis_values = row.get(axis_key) or {}
        values = [float(axis_values.get(axis, 3) or 3) for axis in axes]
        cats = {key_fn(row) for key_fn in category_keys}
        values.extend(1.0 if cat in cats else 0.0 for cat in category_vocab)
        matrix.append(values)
    return matrix


def _axis_diagnostics(rows: list[dict[str, Any]], axes: list[str], *, family: str) -> list[dict[str, Any]]:
    if family == "center":
        axis_key = "center_axes"
    elif family == "center_pairwise":
        axis_key = "center_pairwise_axes"
    else:
        axis_key = "order_axes"
    y = [row["y"] for row in rows]
    diagnostics = []
    for axis in axes:
        values = [float((row.get(axis_key) or {}).get(axis, 3) or 3) for row in rows]
        diagnostics.append(
            {
                "axis": axis,
                "mean": _safe_mean(values),
                "std": _std(values),
                "spearman": _spearman(values, y),
                "pearson": _pearson(values, y),
            }
        )
    return sorted(diagnostics, key=lambda item: abs(item["spearman"]), reverse=True)


def _group_folds(rows: list[dict[str, Any]], *, k: int) -> list[list[int]]:
    groups: dict[str, list[int]] = {}
    for idx, row in enumerate(rows):
        groups.setdefault(str(row.get("qid") or row["sample_id"]), []).append(idx)
    folds = [[] for _ in range(k)]
    for offset, group_key in enumerate(sorted(groups)):
        folds[offset % k].extend(groups[group_key])
    return [fold for fold in folds if fold]


def _group_summary(rows: list[dict[str, Any]], key_fn: Callable[[dict[str, Any]], str]) -> list[dict[str, Any]]:
    buckets: dict[str, list[float]] = {}
    for row in rows:
        buckets.setdefault(key_fn(row), []).append(row["y"])
    return [
        {"group": key, "n": len(values), "mean_difficulty": _safe_mean(values), "std": _std(values)}
        for key, values in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def _build_recommendation(report: dict[str, Any]) -> dict[str, Any]:
    center_best = report["center"].get("best_by_mae")
    order_best = report["sentence_order"].get("best_by_mae")
    center_base = _model_by_name(report["center"], "mean_baseline")
    order_base = _model_by_name(report["sentence_order"], "mean_baseline")
    candidates = []
    if center_best and center_base:
        candidates.append(
            {
                "family": "center_understanding",
                "scope": "overall",
                "best_model": center_best["name"],
                "mae_gain": center_base["cv_mae"] - center_best["cv_mae"],
                "cv_spearman": center_best["cv_spearman"],
            }
        )
    for leaf, section in (report["center"].get("leaf_fit") or {}).items():
        best = section.get("best_by_mae")
        base = _model_by_name(section, "mean_baseline")
        if best and base:
            candidates.append(
                {
                    "family": "center_understanding",
                    "scope": f"leaf::{leaf}",
                    "best_model": best["name"],
                    "mae_gain": base["cv_mae"] - best["cv_mae"],
                    "cv_spearman": best["cv_spearman"],
                }
            )
    if order_best and order_base:
        candidates.append(
            {
                "family": "sentence_order",
                "scope": "overall",
                "best_model": order_best["name"],
                "mae_gain": order_base["cv_mae"] - order_best["cv_mae"],
                "cv_spearman": order_best["cv_spearman"],
            }
        )
    for count, section in (report["sentence_order"].get("sentence_count_fit") or {}).items():
        best = section.get("best_by_mae")
        base = _model_by_name(section, "mean_baseline")
        if best and base:
            candidates.append(
                {
                    "family": "sentence_order",
                    "scope": f"sentence_count::{count}",
                    "best_model": best["name"],
                    "mae_gain": base["cv_mae"] - best["cv_mae"],
                    "cv_spearman": best["cv_spearman"],
                }
            )
    winner = max(candidates, key=lambda item: (item["mae_gain"], item["cv_spearman"])) if candidates else None
    return {
        "winner": winner,
        "promotion_threshold": "candidate if MAE gain >= 0.025 and CV Spearman >= 0.25; strong if MAE gain >= 0.04 and CV Spearman >= 0.35",
        "candidates": candidates,
    }


def _write_markdown(report: dict[str, Any]) -> None:
    center_models = report["center"]["models"]
    order_models = report["sentence_order"]["models"]
    _write_bar_svg(ASSET_DIR / "highfit_center_cv_mae.svg", center_models, value_key="cv_mae", title="Center Understanding CV MAE", lower_is_better=True)
    _write_bar_svg(ASSET_DIR / "highfit_center_cv_spearman.svg", center_models, value_key="cv_spearman", title="Center Understanding CV Spearman")
    _write_bar_svg(ASSET_DIR / "highfit_order_cv_mae.svg", order_models, value_key="cv_mae", title="Sentence Order CV MAE", lower_is_better=True)
    _write_bar_svg(ASSET_DIR / "highfit_order_cv_spearman.svg", order_models, value_key="cv_spearman", title="Sentence Order CV Spearman")

    lines = [
        "# 高拟合难度控制探针报告",
        "",
        "本报告对 `中心理解题` 与 `语句排序题` 做同一套隐藏真值实验：标注阶段不暴露正确率，拟合阶段用学生正确率换算出的 `empirical_difficulty = 1 - correct_rate` 做验证。",
        "",
        "## 样本概况",
        "",
        f"- 中心理解：{report['sample_counts']['center_understanding']} 道",
        f"- 语句排序：{report['sample_counts']['sentence_order']} 道",
        "",
        "## 一、中心理解题拟合结果",
        "",
        "![Center CV MAE](assets/highfit_center_cv_mae.svg)",
        "",
        "![Center CV Spearman](assets/highfit_center_cv_spearman.svg)",
        "",
        _models_table(center_models),
        "",
        "### 中心理解轴诊断",
        "",
        _axis_table(report["center"]["axis_diagnostics"]),
        "",
        "### 中心理解 Pairwise 轴诊断",
        "",
        _axis_table(report["center"]["pairwise_axis_diagnostics"]),
        "",
        "### 中心理解叶族/错误类型均值",
        "",
        _summary_table(report["center"]["leaf_summary"], "leaf"),
        "",
        _summary_table(report["center"]["error_type_summary"], "error_type"),
        "",
        "### 中心理解叶族内拟合",
        "",
        _leaf_fit_section(report["center"]["leaf_fit"]),
        "",
        "## 二、语句排序题拟合结果",
        "",
        "![Order CV MAE](assets/highfit_order_cv_mae.svg)",
        "",
        "![Order CV Spearman](assets/highfit_order_cv_spearman.svg)",
        "",
        _models_table(order_models),
        "",
        "### 语句排序轴诊断",
        "",
        _axis_table(report["sentence_order"]["axis_diagnostics"]),
        "",
        "### 语句排序结构均值",
        "",
        _summary_table(report["sentence_order"]["sentence_count_summary"], "sentence_count"),
        "",
        _summary_table(report["sentence_order"]["order_type_summary"], "order_type"),
        "",
        "### 语句排序句数内拟合",
        "",
        _leaf_fit_section(report["sentence_order"]["sentence_count_fit"]),
        "",
        "## 三、结论",
        "",
        _recommendation_text(report["recommendation"]),
        "",
    ]
    (PROBE_DIR / "highfit_probe_fit_report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_best_scored_rows(report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    family = (report["recommendation"].get("winner") or {}).get("family")
    if not family:
        return
    subset = [row for row in rows if row["family"] == family]
    section = report["center"] if family == "center_understanding" else report["sentence_order"]
    best_name = section["best_by_mae"]["name"]
    models = _center_model_defs() if family == "center_understanding" else _order_model_defs()
    model = next(model for model in models if model["name"] == best_name)
    pred = model["fit"](subset)(subset)
    with (PROBE_DIR / "highfit_best_model_scored_rows.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["sample_id", "family", "leaf", "qid", "actual_difficulty", "predicted_difficulty", "abs_error"],
        )
        writer.writeheader()
        for row, value in sorted(zip(subset, pred, strict=True), key=lambda pair: abs(pair[0]["y"] - pair[1]), reverse=True):
            writer.writerow(
                {
                    "sample_id": row["sample_id"],
                    "family": row["family"],
                    "leaf": row["leaf"],
                    "qid": row["qid"],
                    "actual_difficulty": f"{row['y']:.4f}",
                    "predicted_difficulty": f"{value:.4f}",
                    "abs_error": f"{abs(row['y'] - value):.4f}",
                }
            )


def _center_model_defs() -> list[dict[str, Any]]:
    return [
        _mean_model("mean_baseline"),
        _category_mean_model("leaf_mean", lambda row: row["leaf"]),
        _category_mean_model("error_type_mean", lambda row: _nested(row, "center_type", "dominant_error_type") or "unknown"),
        _category_mean_model(
            "local_detail_axis_mean",
            lambda row: str((row.get("center_axes") or {}).get("local_detail_distractor_strength", "unknown")),
        ),
        _ridge_model("local_detail_single_axis", ["local_detail_distractor_strength"], family="center"),
        _ridge_model(
            "center_selected_axes_ridge",
            ["local_detail_distractor_strength", "discourse_turn_complexity", "correct_option_abstraction_gap"],
            family="center",
        ),
        _category_mean_model("pairwise_type_mean", lambda row: _nested(row, "pairwise_type", "dominant_pairwise_trap") or "unknown"),
        _ridge_model("pairwise_axes_ridge", CENTER_PAIRWISE_AXES, family="center_pairwise"),
        _ridge_model(
            "pairwise_selected_axes_ridge",
            [
                "easy_wrong_partial_validity",
                "easy_wrong_main_claim_proximity",
                "scope_degree_gap_subtlety",
                "decisive_evidence_visibility_load",
                "exclusion_reasoning_load",
            ],
            family="center_pairwise",
        ),
        _ridge_model("center_axes_ridge", CENTER_AXES, family="center"),
        _ridge_model("center_axes_plus_leaf", CENTER_AXES, family="center", category_keys=[lambda row: f"leaf::{row['leaf']}"]),
        _ridge_model(
            "center_axes_plus_error_type",
            CENTER_AXES,
            family="center",
            category_keys=[lambda row: f"err::{_nested(row, 'center_type', 'dominant_error_type') or 'unknown'}"],
        ),
    ]


def _order_model_defs() -> list[dict[str, Any]]:
    return [
        _mean_model("mean_baseline"),
        _category_mean_model("sentence_count_mean", lambda row: str(row.get("sentence_count") or "unknown")),
        _category_mean_model("order_type_mean", lambda row: _nested(row, "order_type", "dominant_order_mechanism") or "unknown"),
        _category_mean_model(
            "first_sentence_axis_mean",
            lambda row: str((row.get("order_axes") or {}).get("first_sentence_ambiguity", "unknown")),
        ),
        _ridge_model("order_axes_ridge", ORDER_AXES, family="order"),
        _ridge_model("order_axes_plus_sentence_count", ORDER_AXES, family="order", category_keys=[lambda row: f"n::{row.get('sentence_count') or 'unknown'}"]),
        _ridge_model(
            "order_axes_plus_type",
            ORDER_AXES,
            family="order",
            category_keys=[lambda row: f"type::{_nested(row, 'order_type', 'dominant_order_mechanism') or 'unknown'}"],
        ),
    ]


def _models_table(models: list[dict[str, Any]]) -> str:
    rows = ["| model | train MAE | CV MAE | CV Spearman | CV band acc |", "|---|---:|---:|---:|---:|"]
    for model in sorted(models, key=lambda item: item["cv_mae"]):
        rows.append(
            f"| `{model['name']}` | {model['train_mae']:.4f} | {model['cv_mae']:.4f} | {model['cv_spearman']:.4f} | {model['cv_band_accuracy']:.4f} |"
        )
    return "\n".join(rows)


def _axis_table(items: list[dict[str, Any]]) -> str:
    rows = ["| axis | mean | std | Spearman | Pearson |", "|---|---:|---:|---:|---:|"]
    for item in items:
        rows.append(f"| `{item['axis']}` | {item['mean']:.3f} | {item['std']:.3f} | {item['spearman']:.4f} | {item['pearson']:.4f} |")
    return "\n".join(rows)


def _summary_table(items: list[dict[str, Any]], title: str) -> str:
    rows = [f"| {title} | n | mean difficulty | std |", "|---|---:|---:|---:|"]
    for item in items:
        rows.append(f"| `{item['group']}` | {item['n']} | {item['mean_difficulty']:.4f} | {item['std']:.4f} |")
    return "\n".join(rows)


def _leaf_fit_section(items: dict[str, Any]) -> str:
    if not items:
        return "无可用叶族内拟合。"
    lines: list[str] = []
    for leaf, result in items.items():
        best = result.get("best_by_mae") or {}
        base = _model_by_name(result, "mean_baseline") or {}
        gain = (base.get("cv_mae") or 0.0) - (best.get("cv_mae") or 0.0)
        lines.extend(
            [
                f"#### `{leaf}`",
                "",
                f"- best: `{best.get('name', '')}`",
                f"- CV MAE: `{best.get('cv_mae', 0.0):.4f}`",
                f"- MAE gain vs mean: `{gain:.4f}`",
                f"- CV Spearman: `{best.get('cv_spearman', 0.0):.4f}`",
                "",
                _models_table(result.get("models") or []),
                "",
                _axis_table((result.get("axis_diagnostics") or [])[:4]),
                "",
            ]
        )
    return "\n".join(lines)


def _recommendation_text(recommendation: dict[str, Any]) -> str:
    winner = recommendation.get("winner")
    if not winner:
        return "未形成可推荐模型。"
    status = "强候选" if winner["mae_gain"] >= 0.04 and winner["cv_spearman"] >= 0.35 else "候选" if winner["mae_gain"] >= 0.025 and winner["cv_spearman"] >= 0.25 else "观察项"
    return (
        f"当前最优方向是 `{winner['family']}` / `{winner.get('scope', 'overall')}` 的 `{winner['best_model']}`，"
        f"相对均值基线 MAE 增益为 `{winner['mae_gain']:.4f}`，CV Spearman 为 `{winner['cv_spearman']:.4f}`。"
        f"按本轮阈值判定为：**{status}**。"
    )


def _write_bar_svg(path: Path, models: list[dict[str, Any]], *, value_key: str, title: str, lower_is_better: bool = False) -> None:
    models = sorted(models, key=lambda item: item[value_key], reverse=not lower_is_better)
    width = 880
    row_h = 34
    height = 70 + row_h * len(models)
    values = [float(model[value_key]) for model in models]
    min_value = min(0.0, min(values, default=0.0))
    max_value = max(values, default=1.0)
    span = max(max_value - min_value, 0.001)
    lines = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='#fbfaf7'/>",
        f"<text x='24' y='32' font-family='Georgia, serif' font-size='22' fill='#2b2118'>{title}</text>",
    ]
    zero_x = 250 + (0 - min_value) / span * 560
    lines.append(f"<line x1='{zero_x:.1f}' y1='52' x2='{zero_x:.1f}' y2='{height - 18}' stroke='#b8aa99' stroke-width='1'/>")
    for idx, model in enumerate(models):
        y = 62 + idx * row_h
        value = float(model[value_key])
        x0 = min(zero_x, 250 + (value - min_value) / span * 560)
        bar_w = abs(250 + (value - min_value) / span * 560 - zero_x)
        color = "#2f6f73" if (lower_is_better and idx == 0) or (not lower_is_better and idx == 0) else "#d49b5c"
        lines.append(f"<text x='24' y='{y + 18}' font-family='Consolas, monospace' font-size='13' fill='#3d332a'>{model['name']}</text>")
        lines.append(f"<rect x='{x0:.1f}' y='{y}' width='{bar_w:.1f}' height='21' rx='5' fill='{color}' opacity='0.92'/>")
        lines.append(f"<text x='820' y='{y + 16}' text-anchor='end' font-family='Consolas, monospace' font-size='13' fill='#3d332a'>{value:.4f}</text>")
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _column_means(matrix: list[list[float]]) -> list[float]:
    if not matrix:
        return []
    return [_safe_mean(row[col] for row in matrix) for col in range(len(matrix[0]))]


def _column_stds(matrix: list[list[float]], means: list[float]) -> list[float]:
    if not matrix:
        return []
    stds: list[float] = []
    for col, mean in enumerate(means):
        value = math.sqrt(sum((row[col] - mean) ** 2 for row in matrix) / len(matrix))
        stds.append(value if value else 1.0)
    return stds


def _scale_matrix(matrix: list[list[float]], means: list[float], stds: list[float]) -> list[list[float]]:
    return [[(value - means[idx]) / stds[idx] for idx, value in enumerate(row)] for row in matrix]


def _normal_matrix(design: list[list[float]], *, alpha: float) -> list[list[float]]:
    if not design:
        return []
    cols = len(design[0])
    matrix = [[0.0 for _ in range(cols)] for _ in range(cols)]
    for row in design:
        for i in range(cols):
            for j in range(cols):
                matrix[i][j] += row[i] * row[j]
    for idx in range(1, cols):
        matrix[idx][idx] += alpha
    return matrix


def _normal_vector(design: list[list[float]], target: list[float]) -> list[float]:
    if not design:
        return []
    cols = len(design[0])
    vector = [0.0 for _ in range(cols)]
    for row, y in zip(design, target, strict=True):
        for idx in range(cols):
            vector[idx] += row[idx] * y
    return vector


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a small dense linear system with partial-pivot Gauss-Jordan."""
    n = len(vector)
    aug = [matrix[idx][:] + [vector[idx]] for idx in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-12:
            aug[col][col] += 1e-8
            pivot = col
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        if abs(divisor) < 1e-12:
            divisor = 1e-12
        for j in range(col, n + 1):
            aug[col][j] /= divisor
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor == 0:
                continue
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
    return [aug[idx][n] for idx in range(n)]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _nested(row: dict[str, Any], first: str, second: str) -> Any:
    value = row.get(first)
    if not isinstance(value, dict):
        return None
    return value.get(second)


def _model_by_name(section: dict[str, Any], name: str) -> dict[str, Any] | None:
    for model in section.get("models") or []:
        if model["name"] == name:
            return model
    return None


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    pairs = [(a, b) for a, b in zip(y_true, y_pred, strict=True) if not math.isnan(b)]
    return _safe_mean(abs(a - b) for a, b in pairs)


def _band_accuracy(y_true: list[float], y_pred: list[float]) -> float:
    pairs = [(a, b) for a, b in zip(y_true, y_pred, strict=True) if not math.isnan(b)]
    if not pairs:
        return 0.0
    return sum(_band(a) == _band(b) for a, b in pairs) / len(pairs)


def _band(value: float) -> str:
    if value < 0.34:
        return "easy"
    if value < 0.67:
        return "medium"
    return "hard"


def _spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return 0.0
    return _pearson(_ranks(xs), _ranks(ys))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean_x = _safe_mean(xs)
    mean_y = _safe_mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        rank = (cursor + 1 + end) / 2
        for idx in range(cursor, end):
            ranks[indexed[idx][0]] = rank
        cursor = end
    return ranks


def _safe_mean(values: Any) -> float:
    vals = [float(value) for value in values]
    return sum(vals) / len(vals) if vals else 0.0


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = _safe_mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_counts": report["sample_counts"],
        "center_best": report["center"]["best_by_mae"],
        "order_best": report["sentence_order"]["best_by_mae"],
        "recommendation": report["recommendation"],
        "report": str(PROBE_DIR / "highfit_probe_fit_report.md"),
    }


if __name__ == "__main__":
    main()
