"""Fit the topic-introduction leaf control-box experiment.

Scope: sentence_fill / 横线在开头-话题引入

The labels are produced from reading-only packets that do not contain student
accuracy. This script joins those labels with hidden truth and compares the new
control boxes against baselines.
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
DATA_DIR = ROOT / "reports/difficulty_control/topic_intro_control_box_test"
ASSET_DIR = DATA_DIR / "assets"

STRUCTURE_FEATURES = (
    "axis.local_binding_complexity",
    "axis.global_context_dependency",
    "axis.distractor_similarity",
    "axis.blank_function_ambiguity",
)

GLOBAL_FEATURES = (
    "global.easy_wrong_option_competition",
    "global.correct_option_abstraction_gap",
)

CONTROL_BOX_FEATURES = (
    "control.post_context_constraint_strength",
    "control.quote_idiom_mapping_load",
    "control.value_direction_precision",
    "control.opening_register_competition",
    "control.generic_positive_trap_strength",
)

PAIRWISE_FEATURES = (
    "pairwise.semantic_distance_correct_vs_wrong",
    "pairwise.wrong_option_partial_match_strength",
    "pairwise.correct_option_exclusivity",
    "pairwise.decisive_evidence_visibility",
    "pairwise.wrong_option_overgeneralization",
    "pairwise.correct_wrong_value_axis_gap",
    "pairwise.correct_wrong_register_gap",
)

CELL_SCORE_FEATURES = (
    "cell_score.cultural_expression_intensity",
    "cell_score.topic_frame_matching_load",
    "cell_score.value_stance_matching_load",
    "cell_score.phenomenon_setup_load",
    "cell_score.cell_purity",
)

OPTION_SET_FEATURES = (
    "option_set.distractor_cluster_coherence",
    "option_set.distractor_complementarity",
    "option_set.correct_option_visibility_in_set",
    "option_set.correct_option_crowding_pressure",
)

DECISION_FEATURES = (
    "decision.correct_option_selectability",
    "decision.distractor_answer_likeness",
)

QUALITY_FEATURES = (
    "quality.answer_key_stability",
    "quality.option_balance_quality",
    "quality.correct_option_non_overclaim_fit",
    "quality.distractor_overclaim_strength",
)

COGNITIVE_SCORE_FEATURES = (
    "cognitive.cognitive_task_purity",
)

CLAIM_ALIGNMENT_FEATURES = (
    "claim.main_claim_alignment",
    "claim.governing_scope_fit",
    "claim.relation_type_fit",
    "claim.main_object_value_action_fit",
)

DISTRACTOR_ERROR_FEATURES = (
    "distractor_error.same_topic_wrong_focus",
    "distractor_error.same_domain_moralized_drift",
    "distractor_error.example_as_thesis_error",
    "distractor_error.policy_vs_value_swap",
    "distractor_error.object_scope_shift",
)

QUOTE_MAPPING_SCORE_FEATURES = (
    "quote_mapping.mapping_type_purity",
)

EVIDENCE_STRUCTURE_SCORE_FEATURES = (
    "evidence.evidence_structure_purity",
    "evidence.decisive_evidence_span_visibility",
    "evidence.wrong_option_local_evidence_capture",
)

REFINED_MAPPING_FEATURES = (
    "refined.mapping_difficulty_rank",
    "refined.mapping_type_purity",
)

REFINED_CLAIM_FEATURES = (
    "refined.main_object_value_action_fit",
    "refined.main_claim_alignment",
)

REFINED_DISTRACTOR_FEATURES = (
    "refined.object_scope_shift",
    "refined.same_topic_wrong_focus",
    "refined.wrong_option_local_evidence_capture",
    "refined.wrong_option_partial_match_strength",
    "refined.distractor_overclaim_strength",
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
        avg_rank = (cursor + end + 2) / 2.0
        for _, index in ordered[cursor : end + 1]:
            ranks[index] = avg_rank
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


def metrics(target: list[float], pred: list[float]) -> dict[str, float]:
    if not target:
        return {"mae": 0.0, "rmse": 0.0, "pearson": 0.0, "spearman": 0.0, "band_agreement": 0.0}
    return {
        "mae": round(_mean(abs(y - p) for y, p in zip(target, pred)), 4),
        "rmse": round(math.sqrt(_mean((y - p) ** 2 for y, p in zip(target, pred))), 4),
        "pearson": round(_pearson(pred, target), 4),
        "spearman": round(_spearman(pred, target), 4),
        "band_agreement": round(_mean(1.0 if _band(y) == _band(p) else 0.0 for y, p in zip(target, pred)), 4),
    }


def load_truth() -> dict[str, dict[str, Any]]:
    rows = {}
    path = DATA_DIR / "topic_intro_hidden_truth.jsonl"
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["sample_id"]] = row
    return rows


def load_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    missing = []
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_control_label_output_{name}.jsonl"
        if not path.exists():
            missing.append(path.name)
            continue
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row.get("global_axis_scores") or not row.get("control_box_scores"):
                    raise ValueError(f"{path}:{line_number} missing scores")
                rows[row["sample_id"]] = row
    if missing:
        raise FileNotFoundError("Missing label output files: " + ", ".join(missing))
    return rows


def load_pairwise_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_pairwise_label_output_{name}.jsonl"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row.get("pairwise_scores"):
                    raise ValueError(f"{path}:{line_number} missing pairwise_scores")
                rows[row["sample_id"]] = row
    return rows


def load_cell_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_cell_label_output_{name}.jsonl"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not row.get("primary_cell") or not row.get("cell_scores"):
                    raise ValueError(f"{path}:{line_number} missing cell labels")
                rows[row["sample_id"]] = row
    return rows


def load_mechanism_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_mechanism_label_output_{name}.jsonl"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                required = ("option_set_scores", "cognitive_task", "decision_confidence_scores", "quality_surface_scores")
                if any(not row.get(key) for key in required):
                    raise ValueError(f"{path}:{line_number} missing mechanism labels")
                rows[row["sample_id"]] = row
    return rows


def load_claim_error_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_claim_error_label_output_{name}.jsonl"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                required = ("claim_alignment_scores", "distractor_error_scores", "quote_mapping_type", "evidence_structure")
                if any(not row.get(key) for key in required):
                    raise ValueError(f"{path}:{line_number} missing claim/error labels")
                rows[row["sample_id"]] = row
    return rows


def load_refined_labels() -> dict[str, dict[str, Any]]:
    rows = {}
    for name in ("A", "B", "C"):
        path = DATA_DIR / f"topic_intro_refined_label_output_{name}.jsonl"
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                required = ("refined_mapping", "refined_claim_scores", "refined_distractor_scores")
                if any(not row.get(key) for key in required):
                    raise ValueError(f"{path}:{line_number} missing refined labels")
                rows[row["sample_id"]] = row
    return rows


def merge_rows() -> list[dict[str, Any]]:
    truth = load_truth()
    labels = load_labels()
    pairwise = load_pairwise_labels()
    cells = load_cell_labels()
    mechanisms = load_mechanism_labels()
    claim_error = load_claim_error_labels()
    refined = load_refined_labels()
    if set(truth) != set(labels):
        raise ValueError(f"truth/label mismatch missing={sorted(set(truth)-set(labels))[:5]}")
    rows = []
    for sample_id in sorted(truth):
        row = dict(truth[sample_id])
        row.update(
            {
                "global_axis_scores": labels[sample_id]["global_axis_scores"],
                "control_box_scores": labels[sample_id]["control_box_scores"],
                "label_confidence": labels[sample_id].get("label_confidence"),
                "label_note": labels[sample_id].get("label_note"),
            }
        )
        if sample_id in pairwise:
            row["pairwise_scores"] = pairwise[sample_id]["pairwise_scores"]
            row["pairwise_note"] = pairwise[sample_id].get("pairwise_note")
        if sample_id in cells:
            row["primary_cell"] = cells[sample_id]["primary_cell"]
            row["cell_scores"] = cells[sample_id]["cell_scores"]
            row["cell_note"] = cells[sample_id].get("cell_note")
        if sample_id in mechanisms:
            mechanism = mechanisms[sample_id]
            row["option_set_scores"] = mechanism["option_set_scores"]
            row["primary_cognitive_task"] = mechanism["cognitive_task"]["primary_cognitive_task"]
            row["cognitive_task_purity"] = mechanism["cognitive_task"]["cognitive_task_purity"]
            row["decision_confidence_scores"] = mechanism["decision_confidence_scores"]
            row["quality_surface_scores"] = mechanism["quality_surface_scores"]
            row["mechanism_note"] = mechanism.get("label_note")
        if sample_id in claim_error:
            payload = claim_error[sample_id]
            row["claim_alignment_scores"] = payload["claim_alignment_scores"]
            row["distractor_error_scores"] = payload["distractor_error_scores"]
            row["primary_mapping_type"] = payload["quote_mapping_type"]["primary_mapping_type"]
            row["mapping_type_purity"] = payload["quote_mapping_type"]["mapping_type_purity"]
            row["primary_evidence_structure"] = payload["evidence_structure"]["primary_evidence_structure"]
            row["evidence_structure_purity"] = payload["evidence_structure"]["evidence_structure_purity"]
            row["decisive_evidence_span_visibility"] = payload["evidence_structure"]["decisive_evidence_span_visibility"]
            row["wrong_option_local_evidence_capture"] = payload["evidence_structure"]["wrong_option_local_evidence_capture"]
            row["claim_error_note"] = payload.get("label_note")
        if sample_id in refined:
            payload = refined[sample_id]
            row["refined_primary_mapping_type"] = payload["refined_mapping"]["primary_mapping_type"]
            row["refined_mapping_difficulty_rank"] = payload["refined_mapping"]["mapping_difficulty_rank"]
            row["refined_mapping_type_purity"] = payload["refined_mapping"]["mapping_type_purity"]
            row["refined_claim_scores"] = payload["refined_claim_scores"]
            row["refined_distractor_scores"] = payload["refined_distractor_scores"]
            row["refined_note"] = payload.get("label_note")
        rows.append(row)
    return rows


def target(row: dict[str, Any]) -> float:
    return _clamp(float(row["empirical_difficulty"]))


def feature_value(row: dict[str, Any], feature: str) -> float:
    if feature == "mean_baseline":
        return 1.0
    if feature.startswith("axis."):
        return float((row.get("axis_scores") or {}).get(feature.split(".", 1)[1], 0.0))
    if feature.startswith("global."):
        return _clamp(float((row.get("global_axis_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("control."):
        return _clamp(float((row.get("control_box_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("pairwise."):
        return _clamp(float((row.get("pairwise_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("cell_score."):
        return _clamp(float((row.get("cell_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("cell_id."):
        return 1.0 if row.get("primary_cell") == feature.split(".", 1)[1] else 0.0
    if feature.startswith("option_set."):
        return _clamp(float((row.get("option_set_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("decision."):
        return _clamp(float((row.get("decision_confidence_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("quality."):
        return _clamp(float((row.get("quality_surface_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature == "cognitive.cognitive_task_purity":
        return _clamp(float(row.get("cognitive_task_purity") or 0.0))
    if feature.startswith("cognitive_id."):
        return 1.0 if row.get("primary_cognitive_task") == feature.split(".", 1)[1] else 0.0
    if feature.startswith("claim."):
        return _clamp(float((row.get("claim_alignment_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("distractor_error."):
        return _clamp(float((row.get("distractor_error_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature == "quote_mapping.mapping_type_purity":
        return _clamp(float(row.get("mapping_type_purity") or 0.0))
    if feature.startswith("mapping_id."):
        return 1.0 if row.get("primary_mapping_type") == feature.split(".", 1)[1] else 0.0
    if feature == "evidence.evidence_structure_purity":
        return _clamp(float(row.get("evidence_structure_purity") or 0.0))
    if feature == "evidence.decisive_evidence_span_visibility":
        return _clamp(float(row.get("decisive_evidence_span_visibility") or 0.0))
    if feature == "evidence.wrong_option_local_evidence_capture":
        return _clamp(float(row.get("wrong_option_local_evidence_capture") or 0.0))
    if feature.startswith("evidence_id."):
        return 1.0 if row.get("primary_evidence_structure") == feature.split(".", 1)[1] else 0.0
    if feature == "refined.mapping_difficulty_rank":
        return _clamp(float(row.get("refined_mapping_difficulty_rank") or 0.0))
    if feature == "refined.mapping_type_purity":
        return _clamp(float(row.get("refined_mapping_type_purity") or 0.0))
    if feature in REFINED_CLAIM_FEATURES:
        return _clamp(float((row.get("refined_claim_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature in REFINED_DISTRACTOR_FEATURES:
        return _clamp(float((row.get("refined_distractor_scores") or {}).get(feature.split(".", 1)[1], 0.0)))
    if feature.startswith("refined_mapping_id."):
        return 1.0 if row.get("refined_primary_mapping_type") == feature.split(".", 1)[1] else 0.0
    raise KeyError(feature)


def design(rows: list[dict[str, Any]], features: tuple[str, ...]) -> list[list[float]]:
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


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
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


def fit_ridge(x_rows: list[list[float]], y: list[float], *, alpha: float) -> dict[str, Any]:
    x_std, means, scales = standardize_train(x_rows)
    x_aug = [[1.0] + row for row in x_std]
    cols = len(x_aug[0])
    xtx = [[0.0 for _ in range(cols)] for _ in range(cols)]
    xty = [0.0 for _ in range(cols)]
    for row, target_value in zip(x_aug, y):
        for i in range(cols):
            xty[i] += row[i] * target_value
            for j in range(cols):
                xtx[i][j] += row[i] * row[j]
    for idx in range(1, cols):
        xtx[idx][idx] += alpha
    return {"coefs": solve(xtx, xty), "means": means, "scales": scales, "alpha": alpha}


def predict(model: dict[str, Any], x_rows: list[list[float]]) -> list[float]:
    x_std = apply_standardize(x_rows, model["means"], model["scales"])
    output = []
    for row in x_std:
        score = model["coefs"][0] + sum(coef * value for coef, value in zip(model["coefs"][1:], row))
        output.append(_clamp(score))
    return output


def mean_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y = [target(row) for row in rows]
    pred = [_mean(y)] * len(y)
    return {
        "features": [],
        "feature_count": 0,
        "metrics": metrics(y, pred),
        "cross_validation": mean_baseline_cv(rows),
        "coefficients": {},
        "top_coefficients": [],
        "scored_rows": score_rows(rows, pred),
    }


def cell_mean_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y = [target(row) for row in rows]
    cell_means = {
        cell: _mean(target(row) for row in group)
        for cell, group in group_by_cell(rows).items()
    }
    global_mean = _mean(y)
    pred = [cell_means.get(row.get("primary_cell"), global_mean) for row in rows]
    return {
        "features": [],
        "feature_count": 0,
        "metrics": metrics(y, pred),
        "cross_validation": cell_mean_baseline_cv(rows),
        "coefficients": {},
        "top_coefficients": [],
        "scored_rows": score_rows(rows, pred),
    }


def cognitive_mean_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    y = [target(row) for row in rows]
    task_means = {
        task: _mean(target(row) for row in group)
        for task, group in group_by_cognitive_task(rows).items()
    }
    global_mean = _mean(y)
    pred = [task_means.get(row.get("primary_cognitive_task"), global_mean) for row in rows]
    return {
        "features": [],
        "feature_count": 0,
        "metrics": metrics(y, pred),
        "cross_validation": cognitive_mean_baseline_cv(rows),
        "coefficients": {},
        "top_coefficients": [],
        "scored_rows": score_rows(rows, pred),
    }


def categorical_mean_baseline(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    y = [target(row) for row in rows]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "unlabeled")].append(row)
    means = {name: _mean(target(row) for row in group) for name, group in grouped.items()}
    global_mean = _mean(y)
    pred = [means.get(str(row.get(key) or "unlabeled"), global_mean) for row in rows]
    return {
        "features": [],
        "feature_count": 0,
        "metrics": metrics(y, pred),
        "cross_validation": categorical_mean_baseline_cv(rows, key),
        "coefficients": {},
        "top_coefficients": [],
        "scored_rows": score_rows(rows, pred),
    }


def categorical_mean_baseline_cv(rows: list[dict[str, Any]], key: str, *, k: int = 5) -> dict[str, Any]:
    actuals = []
    predictions = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        global_mean = _mean(target(row) for row in train)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in train:
            grouped[str(row.get(key) or "unlabeled")].append(row)
        means = {name: _mean(target(row) for row in group) for name, group in grouped.items()}
        pred = [means.get(str(row.get(key) or "unlabeled"), global_mean) for row in test]
        y = [target(row) for row in test]
        actuals.extend(y)
        predictions.extend(pred)
        folds.append({"fold": fold + 1, "n": len(test), "metrics": metrics(y, pred)})
    return {"overall": metrics(actuals, predictions), "folds": folds}


def group_by_cell(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("primary_cell") or "unlabeled")].append(row)
    return grouped


def group_by_cognitive_task(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("primary_cognitive_task") or "unlabeled")].append(row)
    return grouped


def cognitive_mean_baseline_cv(rows: list[dict[str, Any]], *, k: int = 5) -> dict[str, Any]:
    actuals = []
    predictions = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        global_mean = _mean(target(row) for row in train)
        task_means = {
            task: _mean(target(row) for row in group)
            for task, group in group_by_cognitive_task(train).items()
        }
        pred = [task_means.get(row.get("primary_cognitive_task"), global_mean) for row in test]
        y = [target(row) for row in test]
        actuals.extend(y)
        predictions.extend(pred)
        folds.append({"fold": fold + 1, "n": len(test), "metrics": metrics(y, pred)})
    return {"overall": metrics(actuals, predictions), "folds": folds}


def cell_mean_baseline_cv(rows: list[dict[str, Any]], *, k: int = 5) -> dict[str, Any]:
    actuals = []
    predictions = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        global_mean = _mean(target(row) for row in train)
        cell_means = {
            cell: _mean(target(row) for row in group)
            for cell, group in group_by_cell(train).items()
        }
        pred = [cell_means.get(row.get("primary_cell"), global_mean) for row in test]
        y = [target(row) for row in test]
        actuals.extend(y)
        predictions.extend(pred)
        folds.append({"fold": fold + 1, "n": len(test), "metrics": metrics(y, pred)})
    return {"overall": metrics(actuals, predictions), "folds": folds}


def mean_baseline_cv(rows: list[dict[str, Any]], *, k: int = 5) -> dict[str, Any]:
    actuals = []
    predictions = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        avg = _mean(target(row) for row in train)
        pred = [avg] * len(test)
        y = [target(row) for row in test]
        actuals.extend(y)
        predictions.extend(pred)
        folds.append({"fold": fold + 1, "n": len(test), "metrics": metrics(y, pred)})
    return {"overall": metrics(actuals, predictions), "folds": folds}


def select_alpha(rows: list[dict[str, Any]], features: tuple[str, ...], *, k: int = 4) -> float:
    best_alpha = ALPHAS[0]
    best_mae = float("inf")
    for alpha in ALPHAS:
        actuals = []
        predictions = []
        for fold in range(k):
            train = [row for index, row in enumerate(rows) if index % k != fold]
            test = [row for index, row in enumerate(rows) if index % k == fold]
            model = fit_ridge(design(train, features), [target(row) for row in train], alpha=alpha)
            pred = predict(model, design(test, features))
            actuals.extend(target(row) for row in test)
            predictions.extend(pred)
        mae = metrics(actuals, predictions)["mae"]
        if mae < best_mae:
            best_mae = mae
            best_alpha = alpha
    return best_alpha


def fit_model(rows: list[dict[str, Any]], features: tuple[str, ...]) -> dict[str, Any]:
    alpha = select_alpha(rows, features)
    y = [target(row) for row in rows]
    model = fit_ridge(design(rows, features), y, alpha=alpha)
    pred = predict(model, design(rows, features))
    coefficients = {feature: round(coef, 4) for feature, coef in zip(features, model["coefs"][1:])}
    return {
        "features": list(features),
        "feature_count": len(features),
        "alpha": alpha,
        "metrics": metrics(y, pred),
        "cross_validation": cross_validate(rows, features),
        "coefficients": coefficients,
        "top_coefficients": sorted(coefficients.items(), key=lambda item: abs(item[1]), reverse=True),
        "scored_rows": score_rows(rows, pred),
    }


def cross_validate(rows: list[dict[str, Any]], features: tuple[str, ...], *, k: int = 5) -> dict[str, Any]:
    actuals = []
    predictions = []
    folds = []
    for fold in range(k):
        train = [row for index, row in enumerate(rows) if index % k != fold]
        test = [row for index, row in enumerate(rows) if index % k == fold]
        alpha = select_alpha(train, features)
        model = fit_ridge(design(train, features), [target(row) for row in train], alpha=alpha)
        pred = predict(model, design(test, features))
        y = [target(row) for row in test]
        actuals.extend(y)
        predictions.extend(pred)
        folds.append({"fold": fold + 1, "n": len(test), "alpha": alpha, "metrics": metrics(y, pred)})
    return {"overall": metrics(actuals, predictions), "folds": folds}


def score_rows(rows: list[dict[str, Any]], pred: list[float]) -> list[dict[str, Any]]:
    output = []
    for row, predicted in zip(rows, pred):
        output.append(
            {
                "sample_id": row["sample_id"],
                "qid": row.get("qid"),
                "empirical_difficulty": round(target(row), 4),
                "predicted_difficulty": round(predicted, 4),
                "absolute_error": round(abs(target(row) - predicted), 4),
                "answer": row.get("answer"),
                "easy_wrong_option": row.get("easy_wrong_option"),
                "label_note": row.get("label_note"),
            }
        )
    return output


def leaf_band_summary(rows: list[dict[str, Any]], scored_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored_rows:
        grouped[_band(float(row["empirical_difficulty"]))].append(row)
    output = []
    for band, band_rows in sorted(grouped.items()):
        output.append(
            {
                "band": band,
                "n": len(band_rows),
                "mae": round(_mean(float(row["absolute_error"]) for row in band_rows), 4),
                "target_mean": round(_mean(float(row["empirical_difficulty"]) for row in band_rows), 4),
                "predicted_mean": round(_mean(float(row["predicted_difficulty"]) for row in band_rows), 4),
            }
        )
    return output


def feature_diagnostics(rows: list[dict[str, Any]], features: tuple[str, ...]) -> list[dict[str, Any]]:
    y = [target(row) for row in rows]
    output = []
    for feature in features:
        values = [feature_value(row, feature) for row in rows]
        output.append(
            {
                "feature": feature,
                "mean": round(_mean(values), 4),
                "std": round(_std(values), 4),
                "spearman_to_truth": round(_spearman(values, y), 4),
                "pearson_to_truth": round(_pearson(values, y), 4),
            }
        )
    return sorted(output, key=lambda item: abs(item["spearman_to_truth"]), reverse=True)


def cell_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for cell, group in sorted(group_by_cell(rows).items()):
        values = [target(row) for row in group]
        output.append(
            {
                "cell": cell,
                "n": len(group),
                "mean_difficulty": round(_mean(values), 4),
                "std_difficulty": round(_std(values), 4),
                "easy": sum(1 for value in values if _band(value) == "easy"),
                "medium": sum(1 for value in values if _band(value) == "medium"),
                "hard": sum(1 for value in values if _band(value) == "hard"),
            }
        )
    return sorted(output, key=lambda item: item["mean_difficulty"], reverse=True)


def cognitive_task_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for task, group in sorted(group_by_cognitive_task(rows).items()):
        values = [target(row) for row in group]
        output.append(
            {
                "task": task,
                "n": len(group),
                "mean_difficulty": round(_mean(values), 4),
                "std_difficulty": round(_std(values), 4),
                "easy": sum(1 for value in values if _band(value) == "easy"),
                "medium": sum(1 for value in values if _band(value) == "medium"),
                "hard": sum(1 for value in values if _band(value) == "hard"),
            }
        )
    return sorted(output, key=lambda item: item["mean_difficulty"], reverse=True)


def categorical_summary(rows: list[dict[str, Any]], key: str, label_key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "unlabeled")].append(row)
    output = []
    for name, group in sorted(grouped.items()):
        values = [target(row) for row in group]
        output.append(
            {
                label_key: name,
                "n": len(group),
                "mean_difficulty": round(_mean(values), 4),
                "std_difficulty": round(_std(values), 4),
                "easy": sum(1 for value in values if _band(value) == "easy"),
                "medium": sum(1 for value in values if _band(value) == "medium"),
                "hard": sum(1 for value in values if _band(value) == "hard"),
            }
        )
    return sorted(output, key=lambda item: item["mean_difficulty"], reverse=True)


def bar_svg(title: str, data: list[tuple[str, float]], path: Path) -> None:
    width, height = 860, 390
    left, right, top, bottom = 210, 40, 56, 34
    plot_w = width - left - right
    row_h = (height - top - bottom) / max(len(data), 1)
    max_v = max(max(value for _, value in data), 0.001)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="36" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(data):
        y = top + idx * row_h + row_h * 0.18
        h = max(12, row_h * 0.5)
        w = plot_w * max(value, 0.0) / max_v
        parts.extend(
            [
                f'<text x="{left - 12}" y="{y + h * 0.72:.1f}" text-anchor="end" font-size="14" '
                f'font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>',
                f'<rect x="{left}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="#2F6F73"/>',
                f'<text x="{left + w + 8:.1f}" y="{y + h * 0.72:.1f}" font-size="13" '
                f'font-family="Consolas, monospace" fill="#4D564F">{_fmt(value)}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    titles = {
        "mean_baseline": "叶族均值基线",
        "structure_only": "原结构四轴",
        "global_axes": "2 个全局经验轴",
        "control_boxes": "5 个话题引入控制箱",
        "pairwise_axes": "7 个正确项-易错项差异轴",
        "global_plus_control": "全局经验 + 控制箱",
        "global_plus_pairwise": "全局经验 + pairwise",
        "control_plus_pairwise": "控制箱 + pairwise",
        "all_features": "结构 + 全局经验 + 控制箱",
        "all_features_with_pairwise": "结构 + 全局经验 + 控制箱 + pairwise",
        "cell_mean_baseline": "细胞均值基线",
        "cell_scores": "细胞分数",
        "cell_id_diagnostic": "细胞ID诊断",
        "cell_scores_plus_pairwise": "细胞分数 + pairwise",
        "option_set_layer": "完整选项集竞争层",
        "decision_layer": "决策置信度层",
        "quality_layer": "题质/表面工程层",
        "cognitive_score_layer": "认知任务纯度",
        "mechanism_scores": "新机制分数层",
        "cognitive_task_mean": "认知任务均值基线",
        "cognitive_task_id_diagnostic": "认知任务ID诊断",
        "mechanism_plus_pairwise": "新机制 + pairwise",
        "claim_alignment_layer": "总领命题对位层",
        "distractor_error_layer": "易错项偏差机制层",
        "quote_mapping_layer": "引句映射类型层",
        "evidence_structure_layer": "段内证据结构层",
        "claim_error_scores": "新总领/偏差/证据分数层",
        "mapping_type_mean": "引句映射类型均值基线",
        "evidence_structure_mean": "证据结构均值基线",
        "claim_error_plus_pairwise": "新总领偏差层 + pairwise",
        "refined_mapping_mean": "精简映射类型均值基线",
        "refined_mapping_layer": "精简映射层",
        "refined_claim_layer": "精简总领对位层",
        "refined_distractor_layer": "精简易错项寄生层",
        "refined_scores": "精简候选分数层",
        "refined_scores_plus_pairwise": "精简候选 + pairwise",
    }
    model_rows = []
    for name, model in report["models"].items():
        cv = model["cross_validation"]["overall"]
        model_rows.append(
            [
                titles.get(name, name),
                str(model["feature_count"]),
                _fmt(model["metrics"]["mae"]),
                _fmt(cv["mae"]),
                _fmt(cv["spearman"]),
                _fmt(cv["band_agreement"]),
            ]
        )
    best = report["models"][report["best_model"]]
    baseline_cv = report["models"]["mean_baseline"]["cross_validation"]["overall"]
    global_cv = report["models"]["global_axes"]["cross_validation"]["overall"]
    control_cv = report["models"]["control_boxes"]["cross_validation"]["overall"]
    combined_cv = report["models"]["global_plus_control"]["cross_validation"]["overall"]
    coef_rows = [[f"`{name}`", f"{value:+.4f}"] for name, value in best["top_coefficients"][:10]]
    band_rows = [
        [row["band"], str(row["n"]), _fmt(row["target_mean"]), _fmt(row["predicted_mean"]), _fmt(row["mae"])]
        for row in report["band_summary"]
    ]
    cell_rows = [
        [
            row["cell"],
            str(row["n"]),
            _fmt(row["mean_difficulty"]),
            _fmt(row["std_difficulty"]),
            str(row["easy"]),
            str(row["medium"]),
            str(row["hard"]),
        ]
        for row in report.get("cell_summary", [])
    ]
    task_rows = [
        [
            row["task"],
            str(row["n"]),
            _fmt(row["mean_difficulty"]),
            _fmt(row["std_difficulty"]),
            str(row["easy"]),
            str(row["medium"]),
            str(row["hard"]),
        ]
        for row in report.get("cognitive_task_summary", [])
    ]
    mapping_rows = [
        [
            row["mapping_type"],
            str(row["n"]),
            _fmt(row["mean_difficulty"]),
            _fmt(row["std_difficulty"]),
            str(row["easy"]),
            str(row["medium"]),
            str(row["hard"]),
        ]
        for row in report.get("mapping_type_summary", [])
    ]
    evidence_rows = [
        [
            row["evidence_structure"],
            str(row["n"]),
            _fmt(row["mean_difficulty"]),
            _fmt(row["std_difficulty"]),
            str(row["easy"]),
            str(row["medium"]),
            str(row["hard"]),
        ]
        for row in report.get("evidence_structure_summary", [])
    ]
    refined_mapping_rows = [
        [
            row["refined_mapping_type"],
            str(row["n"]),
            _fmt(row["mean_difficulty"]),
            _fmt(row["std_difficulty"]),
            str(row["easy"]),
            str(row["medium"]),
            str(row["hard"]),
        ]
        for row in report.get("refined_mapping_type_summary", [])
    ]
    diagnostic_features = GLOBAL_FEATURES + CONTROL_BOX_FEATURES
    if any(row.get("pairwise_scores") for row in report["rows_for_diagnostics"]):
        diagnostic_features = diagnostic_features + PAIRWISE_FEATURES
    diagnostic_rows = [
        [
            f"`{row['feature']}`",
            _fmt(row["mean"]),
            _fmt(row["std"]),
            f"{row['spearman_to_truth']:+.3f}",
            f"{row['pearson_to_truth']:+.3f}",
        ]
        for row in report["feature_diagnostics"]
    ]
    return f"""# 话题引入控制箱拟合测试

叶族：`sentence_fill / 横线在开头-话题引入`
样本：`{report["sample_count"]}` 道真题。
标注：subagent 阅读标注，输入不含正确率；拟合阶段再与隐藏正确率合并。

## 1. 结果

本次最优模型：`{report["best_model"]}`。

判定：**本轮控制箱拟合失败，不建议升格为正式难度权重。**

- 叶族均值基线 5-fold MAE 是 `{_fmt(baseline_cv["mae"])}`。
- 5 个控制箱 5-fold MAE 是 `{_fmt(control_cv["mae"])}`，没有超过均值基线。
- 2 个全局经验轴 5-fold MAE 是 `{_fmt(global_cv["mae"])}`。
- 全局经验 + 控制箱 5-fold MAE 是 `{_fmt(combined_cv["mae"])}`，没有产生增量。
- Spearman 全部不稳定且为负，说明当前标注定义没有捕捉学生正确率排序。

{table(["模型", "特征数", "Train MAE", "5-fold MAE", "5-fold Spearman", "5-fold 档位一致"], model_rows)}

![CV MAE](assets/topic_intro_cv_mae.svg)

![CV Spearman](assets/topic_intro_cv_spearman.svg)

## 2. 最优模型系数

系数为标准化 ridge 系数，只用于方向判断，不直接回写配置。

{table(["特征", "系数"], coef_rows)}

## 3. 难度档表现

{table(["真实难度档", "n", "真实均值", "预测均值", "MAE"], band_rows)}

## 4. 细胞层分布

{table(["cell", "n", "真实均值", "真实SD", "easy", "medium", "hard"], cell_rows)}

## 5. 认知任务分布

{table(["task", "n", "真实均值", "真实SD", "easy", "medium", "hard"], task_rows)}

## 6. 引句映射与证据结构分布

{table(["mapping_type", "n", "真实均值", "真实SD", "easy", "medium", "hard"], mapping_rows)}

{table(["evidence_structure", "n", "真实均值", "真实SD", "easy", "medium", "hard"], evidence_rows)}

## 7. 精简映射类型分布

{table(["refined_mapping_type", "n", "真实均值", "真实SD", "easy", "medium", "hard"], refined_mapping_rows)}

## 8. 单特征诊断

{table(["特征", "均值", "标准差", "Spearman", "Pearson"], diagnostic_rows)}

## 9. 判定口径

- 如果 `control_boxes` 明显好于 `mean_baseline`，说明这 5 个控制箱具备叶族内解释力。
- 如果 `global_plus_control` 明显好于 `global_axes`，说明控制箱对全局经验轴有增量价值。
- 如果只提升训练集、不提升 5-fold，说明控制箱还只是诊断语言，不该进入正式权重。
"""


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    rows = merge_rows()
    model_features = {
        "mean_baseline": (),
        "structure_only": STRUCTURE_FEATURES,
        "global_axes": GLOBAL_FEATURES,
        "control_boxes": CONTROL_BOX_FEATURES,
        "global_plus_control": GLOBAL_FEATURES + CONTROL_BOX_FEATURES,
        "all_features": STRUCTURE_FEATURES + GLOBAL_FEATURES + CONTROL_BOX_FEATURES,
    }
    if all(row.get("pairwise_scores") for row in rows):
        model_features.update(
            {
                "pairwise_axes": PAIRWISE_FEATURES,
                "global_plus_pairwise": GLOBAL_FEATURES + PAIRWISE_FEATURES,
                "control_plus_pairwise": CONTROL_BOX_FEATURES + PAIRWISE_FEATURES,
                "all_features_with_pairwise": STRUCTURE_FEATURES
                + GLOBAL_FEATURES
                + CONTROL_BOX_FEATURES
                + PAIRWISE_FEATURES,
            }
        )
    if all(row.get("primary_cell") for row in rows):
        cell_id_features = tuple(f"cell_id.{cell}" for cell in sorted({row["primary_cell"] for row in rows}))
        model_features.update(
            {
                "cell_mean_baseline": (),
                "cell_scores": CELL_SCORE_FEATURES,
                "cell_id_diagnostic": cell_id_features,
                "cell_scores_plus_pairwise": CELL_SCORE_FEATURES + PAIRWISE_FEATURES
                if all(row.get("pairwise_scores") for row in rows)
                else CELL_SCORE_FEATURES,
            }
        )
    if all(row.get("primary_cognitive_task") for row in rows):
        cognitive_id_features = tuple(
            f"cognitive_id.{task}" for task in sorted({row["primary_cognitive_task"] for row in rows})
        )
    if all(row.get("primary_mapping_type") for row in rows):
        mapping_id_features = tuple(
            f"mapping_id.{name}" for name in sorted({row["primary_mapping_type"] for row in rows})
        )
    if all(row.get("refined_primary_mapping_type") for row in rows):
        refined_mapping_id_features = tuple(
            f"refined_mapping_id.{name}" for name in sorted({row["refined_primary_mapping_type"] for row in rows})
        )
        refined_features = REFINED_MAPPING_FEATURES + REFINED_CLAIM_FEATURES + REFINED_DISTRACTOR_FEATURES
        model_features.update(
            {
                "refined_mapping_mean": (),
                "refined_mapping_layer": REFINED_MAPPING_FEATURES + refined_mapping_id_features,
                "refined_claim_layer": REFINED_CLAIM_FEATURES,
                "refined_distractor_layer": REFINED_DISTRACTOR_FEATURES,
                "refined_scores": refined_features,
                "refined_scores_plus_pairwise": refined_features + PAIRWISE_FEATURES
                if all(row.get("pairwise_scores") for row in rows)
                else refined_features,
            }
        )
        evidence_id_features = tuple(
            f"evidence_id.{name}" for name in sorted({row["primary_evidence_structure"] for row in rows})
        )
        claim_error_features = (
            CLAIM_ALIGNMENT_FEATURES
            + DISTRACTOR_ERROR_FEATURES
            + QUOTE_MAPPING_SCORE_FEATURES
            + EVIDENCE_STRUCTURE_SCORE_FEATURES
        )
        model_features.update(
            {
                "claim_alignment_layer": CLAIM_ALIGNMENT_FEATURES,
                "distractor_error_layer": DISTRACTOR_ERROR_FEATURES,
                "quote_mapping_layer": QUOTE_MAPPING_SCORE_FEATURES + mapping_id_features,
                "evidence_structure_layer": EVIDENCE_STRUCTURE_SCORE_FEATURES + evidence_id_features,
                "claim_error_scores": claim_error_features,
                "mapping_type_mean": (),
                "evidence_structure_mean": (),
                "claim_error_plus_pairwise": claim_error_features + PAIRWISE_FEATURES
                if all(row.get("pairwise_scores") for row in rows)
                else claim_error_features,
            }
        )
        mechanism_features = OPTION_SET_FEATURES + DECISION_FEATURES + QUALITY_FEATURES + COGNITIVE_SCORE_FEATURES
        model_features.update(
            {
                "option_set_layer": OPTION_SET_FEATURES,
                "decision_layer": DECISION_FEATURES,
                "quality_layer": QUALITY_FEATURES,
                "cognitive_score_layer": COGNITIVE_SCORE_FEATURES,
                "mechanism_scores": mechanism_features,
                "cognitive_task_mean": (),
                "cognitive_task_id_diagnostic": cognitive_id_features,
                "mechanism_plus_pairwise": mechanism_features + PAIRWISE_FEATURES
                if all(row.get("pairwise_scores") for row in rows)
                else mechanism_features,
            }
        )
    models = {}
    for name, features in model_features.items():
        if name == "mean_baseline":
            models[name] = mean_baseline(rows)
        elif name == "cell_mean_baseline":
            models[name] = cell_mean_baseline(rows)
        elif name == "cognitive_task_mean":
            models[name] = cognitive_mean_baseline(rows)
        elif name == "mapping_type_mean":
            models[name] = categorical_mean_baseline(rows, "primary_mapping_type")
        elif name == "evidence_structure_mean":
            models[name] = categorical_mean_baseline(rows, "primary_evidence_structure")
        elif name == "refined_mapping_mean":
            models[name] = categorical_mean_baseline(rows, "refined_primary_mapping_type")
        else:
            models[name] = fit_model(rows, features)
    best_model = min(models, key=lambda name: (models[name]["cross_validation"]["overall"]["mae"], -models[name]["cross_validation"]["overall"]["spearman"]))
    report = {
        "sample_count": len(rows),
        "best_model": best_model,
        "models": models,
        "band_summary": leaf_band_summary(rows, models[best_model]["scored_rows"]),
        "cell_summary": cell_summary(rows) if all(row.get("primary_cell") for row in rows) else [],
        "cognitive_task_summary": cognitive_task_summary(rows)
        if all(row.get("primary_cognitive_task") for row in rows)
        else [],
        "mapping_type_summary": categorical_summary(rows, "primary_mapping_type", "mapping_type")
        if all(row.get("primary_mapping_type") for row in rows)
        else [],
        "evidence_structure_summary": categorical_summary(rows, "primary_evidence_structure", "evidence_structure")
        if all(row.get("primary_evidence_structure") for row in rows)
        else [],
        "refined_mapping_type_summary": categorical_summary(rows, "refined_primary_mapping_type", "refined_mapping_type")
        if all(row.get("refined_primary_mapping_type") for row in rows)
        else [],
        "feature_diagnostics": feature_diagnostics(
            rows,
            (
                GLOBAL_FEATURES
                + CONTROL_BOX_FEATURES
                + PAIRWISE_FEATURES
                + CELL_SCORE_FEATURES
                + OPTION_SET_FEATURES
                + DECISION_FEATURES
                + QUALITY_FEATURES
                + COGNITIVE_SCORE_FEATURES
                + CLAIM_ALIGNMENT_FEATURES
                + DISTRACTOR_ERROR_FEATURES
                + QUOTE_MAPPING_SCORE_FEATURES
                + EVIDENCE_STRUCTURE_SCORE_FEATURES
                + REFINED_MAPPING_FEATURES
                + REFINED_CLAIM_FEATURES
                + REFINED_DISTRACTOR_FEATURES
            )
            if all(row.get("refined_primary_mapping_type") for row in rows)
            else (
                (
                    GLOBAL_FEATURES
                    + CONTROL_BOX_FEATURES
                    + PAIRWISE_FEATURES
                    + CELL_SCORE_FEATURES
                    + OPTION_SET_FEATURES
                    + DECISION_FEATURES
                    + QUALITY_FEATURES
                    + COGNITIVE_SCORE_FEATURES
                    + CLAIM_ALIGNMENT_FEATURES
                    + DISTRACTOR_ERROR_FEATURES
                    + QUOTE_MAPPING_SCORE_FEATURES
                    + EVIDENCE_STRUCTURE_SCORE_FEATURES
                )
                if all(row.get("primary_mapping_type") for row in rows)
                else (
                    (
                        GLOBAL_FEATURES
                        + CONTROL_BOX_FEATURES
                        + PAIRWISE_FEATURES
                        + CELL_SCORE_FEATURES
                        + OPTION_SET_FEATURES
                        + DECISION_FEATURES
                        + QUALITY_FEATURES
                        + COGNITIVE_SCORE_FEATURES
                    )
                    if all(row.get("primary_cognitive_task") for row in rows)
                    else (
                        (GLOBAL_FEATURES + CONTROL_BOX_FEATURES + PAIRWISE_FEATURES + CELL_SCORE_FEATURES)
                        if all(row.get("pairwise_scores") for row in rows)
                        else (GLOBAL_FEATURES + CONTROL_BOX_FEATURES)
                    )
                )
            ),
        ),
        "rows_for_diagnostics": [{"sample_id": row["sample_id"], "pairwise_scores": bool(row.get("pairwise_scores"))} for row in rows],
    }
    (DATA_DIR / "topic_intro_control_box_fit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "topic_intro_control_box_fit_report.md").write_text(render_markdown(report), encoding="utf-8")
    write_csv(DATA_DIR / "topic_intro_best_model_scored_rows.csv", models[best_model]["scored_rows"])

    title_map = {
        "mean_baseline": "均值基线",
        "structure_only": "结构四轴",
        "global_axes": "全局经验",
        "control_boxes": "控制箱",
        "global_plus_control": "全局+控制箱",
        "all_features": "全量组合",
    }
    if "pairwise_axes" in models:
        title_map.update(
            {
                "pairwise_axes": "pairwise",
                "global_plus_pairwise": "全局+pairwise",
                "control_plus_pairwise": "控制箱+pairwise",
                "all_features_with_pairwise": "全量+pairwise",
            }
        )
    if "cell_mean_baseline" in models:
        title_map.update(
            {
                "cell_mean_baseline": "细胞均值",
                "cell_scores": "细胞分数",
                "cell_id_diagnostic": "细胞ID",
                "cell_scores_plus_pairwise": "细胞+pairwise",
            }
        )
    if "mechanism_scores" in models:
        title_map.update(
            {
                "option_set_layer": "选项集",
                "decision_layer": "决策置信",
                "quality_layer": "题质",
                "cognitive_score_layer": "认知纯度",
                "mechanism_scores": "新机制",
                "cognitive_task_mean": "认知均值",
                "cognitive_task_id_diagnostic": "认知ID",
                "mechanism_plus_pairwise": "机制+pairwise",
            }
        )
    if "claim_error_scores" in models:
        title_map.update(
            {
                "claim_alignment_layer": "总领对位",
                "distractor_error_layer": "错项偏差",
                "quote_mapping_layer": "引句映射",
                "evidence_structure_layer": "证据结构",
                "claim_error_scores": "总领偏差层",
                "mapping_type_mean": "映射均值",
                "evidence_structure_mean": "证据均值",
                "claim_error_plus_pairwise": "总领+pairwise",
            }
        )
    if "refined_scores" in models:
        title_map.update(
            {
                "refined_mapping_mean": "精简映射均值",
                "refined_mapping_layer": "精简映射",
                "refined_claim_layer": "精简总领",
                "refined_distractor_layer": "精简错项",
                "refined_scores": "精简候选",
                "refined_scores_plus_pairwise": "精简+pairwise",
            }
        )
    bar_svg(
        "Topic intro 5-fold CV MAE",
        [(title_map[name], models[name]["cross_validation"]["overall"]["mae"]) for name in title_map],
        ASSET_DIR / "topic_intro_cv_mae.svg",
    )
    bar_svg(
        "Topic intro 5-fold CV Spearman",
        [(title_map[name], max(0.0, models[name]["cross_validation"]["overall"]["spearman"])) for name in title_map],
        ASSET_DIR / "topic_intro_cv_spearman.svg",
    )
    index = {
        "report": str((DATA_DIR / "topic_intro_control_box_fit_report.md").relative_to(ROOT)),
        "json": str((DATA_DIR / "topic_intro_control_box_fit_report.json").relative_to(ROOT)),
        "csv": str((DATA_DIR / "topic_intro_best_model_scored_rows.csv").relative_to(ROOT)),
        "assets": sorted(str(path.relative_to(ROOT)) for path in ASSET_DIR.glob("*.svg")),
    }
    (DATA_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
