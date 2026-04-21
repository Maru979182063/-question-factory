from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "reports" / "difficulty_control" / "highfit_probe"
OUT_MD = PROBE_DIR / "degree_word_correlation_analysis.md"
OUT_JSON = PROBE_DIR / "degree_word_correlation_analysis.json"


FEATURES = [
    ("passage", "main_claim_visibility", lambda row: row["center_axes"]["main_claim_visibility"]),
    ("passage", "discourse_turn_complexity", lambda row: row["center_axes"]["discourse_turn_complexity"]),
    ("passage", "scope_degree_decision_load", lambda row: row["center_axes"]["scope_degree_decision_load"]),
    ("correct_option", "correct_option_abstraction_gap", lambda row: row["center_axes"]["correct_option_abstraction_gap"]),
    ("option_set", "option_competition_density", lambda row: row["center_axes"]["option_competition_density"]),
    ("option_set", "theme_term_overlap_trap", lambda row: row["center_axes"]["theme_term_overlap_trap"]),
    ("distractor", "local_detail_distractor_strength", lambda row: row["center_axes"]["local_detail_distractor_strength"]),
    ("pairwise", "easy_wrong_partial_validity", lambda row: row["center_pairwise_axes"]["easy_wrong_partial_validity"]),
    ("pairwise", "easy_wrong_main_claim_proximity", lambda row: row["center_pairwise_axes"]["easy_wrong_main_claim_proximity"]),
    ("pairwise", "scope_degree_gap_subtlety", lambda row: row["center_pairwise_axes"]["scope_degree_gap_subtlety"]),
    (
        "pairwise",
        "correct_option_completeness_advantage_hidden",
        lambda row: row["center_pairwise_axes"]["correct_option_completeness_advantage_hidden"],
    ),
    ("pairwise", "decisive_evidence_visibility_load", lambda row: row["center_pairwise_axes"]["decisive_evidence_visibility_load"]),
    ("pairwise", "surface_wording_similarity", lambda row: row["center_pairwise_axes"]["surface_wording_similarity"]),
    ("pairwise", "exclusion_reasoning_load", lambda row: row["center_pairwise_axes"]["exclusion_reasoning_load"]),
    ("text_aux", "passage_char_len", lambda row: len(row.get("passage") or "")),
    ("text_aux", "passage_clause_count", lambda row: _clause_count(row.get("passage") or "")),
    ("text_aux", "option_mean_char_len", lambda row: _option_mean_len(row.get("options") or {})),
    ("text_aux", "correct_easy_wrong_len_gap", lambda row: _correct_wrong_len_gap(row)),
]


def main() -> None:
    rows = _load_degree_word_rows()
    feature_rows = _feature_rows(rows)
    y = [row["actual_difficulty"] for row in feature_rows]

    correlation_rows = []
    for group, name, _ in FEATURES:
        xs = [float(row[name]) for row in feature_rows]
        corr = _correlation_result(xs, y, seed=17)
        corr.update({"group": group, "feature": name, "mean": _mean(xs), "std": _std(xs)})
        correlation_rows.append(corr)
    correlation_rows = _apply_bh_q_values(correlation_rows)

    repeated_cv = []
    for group, name, _ in FEATURES:
        repeated_cv.append(
            {
                "group": group,
                "feature": name,
                **_repeated_univariate_cv(feature_rows, name, seed=23, reps=200),
            }
        )

    groups = {
        "passage_only": ["main_claim_visibility", "discourse_turn_complexity", "scope_degree_decision_load"],
        "option_set_only": ["option_competition_density", "theme_term_overlap_trap"],
        "distractor_primary": ["local_detail_distractor_strength"],
        "pairwise_only": [
            "easy_wrong_partial_validity",
            "easy_wrong_main_claim_proximity",
            "scope_degree_gap_subtlety",
            "decisive_evidence_visibility_load",
            "exclusion_reasoning_load",
        ],
        "candidate_control_index": [
            "local_detail_distractor_strength",
            "decisive_evidence_visibility_load",
            "easy_wrong_main_claim_proximity",
        ],
        "all_reading_axes": [
            "main_claim_visibility",
            "discourse_turn_complexity",
            "scope_degree_decision_load",
            "correct_option_abstraction_gap",
            "option_competition_density",
            "theme_term_overlap_trap",
            "local_detail_distractor_strength",
            "easy_wrong_partial_validity",
            "easy_wrong_main_claim_proximity",
            "scope_degree_gap_subtlety",
            "decisive_evidence_visibility_load",
            "exclusion_reasoning_load",
        ],
    }
    group_cv = [
        {"model": name, **_repeated_multivariate_cv(feature_rows, names, seed=31, reps=200)}
        for name, names in groups.items()
    ]

    report = {
        "sample": {
            "family": "center_understanding",
            "leaf": "程度词",
            "n": len(feature_rows),
            "actual_difficulty_mean": _mean(y),
            "actual_difficulty_std": _std(y),
            "actual_difficulty_min": min(y),
            "actual_difficulty_max": max(y),
        },
        "correlations": sorted(correlation_rows, key=lambda item: abs(item["spearman"]), reverse=True),
        "repeated_univariate_cv": sorted(repeated_cv, key=lambda item: item["mae_gain_mean"], reverse=True),
        "repeated_group_cv": sorted(group_cv, key=lambda item: item["mae_gain_mean"], reverse=True),
        "control_index_bins": _control_index_bins(feature_rows),
        "interpretation": _interpretation(),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(_render_markdown(report), encoding="utf-8")
    print(json.dumps({"report": str(OUT_MD), "sample": report["sample"], "top": report["correlations"][:5]}, ensure_ascii=False, indent=2))


def _load_degree_word_rows() -> list[dict[str, Any]]:
    truth = {row["sample_id"]: row for row in _read_jsonl(PROBE_DIR / "highfit_probe_hidden_truth.jsonl")}
    public_inputs = {}
    for name in ("center_highfit_label_input_A.jsonl", "center_highfit_label_input_B.jsonl", "center_highfit_label_input_C.jsonl"):
        public_inputs.update({row["sample_id"]: row for row in _read_jsonl(PROBE_DIR / name)})
    center_labels = []
    for name in ("center_highfit_label_output_A.jsonl", "center_highfit_label_output_B.jsonl", "center_highfit_label_output_C.jsonl"):
        center_labels.extend(_read_jsonl(PROBE_DIR / name))
    pairwise = {}
    for name in ("center_pairwise_label_output_A.jsonl", "center_pairwise_label_output_B.jsonl", "center_pairwise_label_output_C.jsonl"):
        pairwise.update({row["sample_id"]: row for row in _read_jsonl(PROBE_DIR / name)})

    rows = []
    for label in center_labels:
        sample_id = label["sample_id"]
        t = truth[sample_id]
        if t["family"] != "center_understanding" or t["leaf"] != "程度词":
            continue
        row = dict(public_inputs.get(sample_id) or {})
        row.update(t)
        row.update(label)
        row.update(pairwise.get(sample_id) or {})
        row["actual_difficulty"] = float(t["empirical_difficulty"])
        rows.append(row)
    return rows


def _feature_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        item = {
            "sample_id": row["sample_id"],
            "qid": row["qid"],
            "actual_difficulty": row["actual_difficulty"],
            "passage": row.get("passage") or "",
            "options": row.get("options") or {},
        }
        for _, name, fn in FEATURES:
            item[name] = float(fn(row))
        item["candidate_control_index"] = (
            0.58 * item["local_detail_distractor_strength"]
            + 0.22 * item["decisive_evidence_visibility_load"]
            + 0.20 * item["easy_wrong_main_claim_proximity"]
        )
        output.append(item)
    return output


def _correlation_result(xs: list[float], ys: list[float], *, seed: int) -> dict[str, float]:
    spearman = _spearman(xs, ys)
    pearson = _pearson(xs, ys)
    rng = random.Random(seed)
    permutations = []
    shuffled = ys[:]
    for _ in range(4000):
        rng.shuffle(shuffled)
        permutations.append(abs(_spearman(xs, shuffled)))
    p_value = (sum(value >= abs(spearman) for value in permutations) + 1) / (len(permutations) + 1)
    boot = []
    n = len(xs)
    for _ in range(2000):
        indices = [rng.randrange(n) for _ in range(n)]
        boot_x = [xs[idx] for idx in indices]
        boot_y = [ys[idx] for idx in indices]
        boot.append(_spearman(boot_x, boot_y))
    boot.sort()
    return {
        "spearman": spearman,
        "pearson": pearson,
        "perm_p": p_value,
        "spearman_ci_low": boot[int(0.025 * len(boot))],
        "spearman_ci_high": boot[int(0.975 * len(boot))],
    }


def _apply_bh_q_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(enumerate(rows), key=lambda item: item[1]["perm_p"])
    m = len(rows)
    q_values = [1.0] * m
    previous = 1.0
    for rank, (idx, row) in reversed(list(enumerate(ordered, start=1))):
        q = min(previous, row["perm_p"] * m / rank)
        q_values[idx] = q
        previous = q
    for idx, row in enumerate(rows):
        row["bh_q"] = q_values[idx]
    return rows


def _repeated_univariate_cv(rows: list[dict[str, Any]], feature: str, *, seed: int, reps: int) -> dict[str, float]:
    return _repeated_cv(rows, [feature], seed=seed, reps=reps)


def _repeated_multivariate_cv(rows: list[dict[str, Any]], features: list[str], *, seed: int, reps: int) -> dict[str, float]:
    return _repeated_cv(rows, features, seed=seed, reps=reps)


def _repeated_cv(rows: list[dict[str, Any]], features: list[str], *, seed: int, reps: int) -> dict[str, float]:
    rng = random.Random(seed)
    mae_values = []
    base_mae_values = []
    spearman_values = []
    groups = sorted({row["qid"] for row in rows})
    for _ in range(reps):
        shuffled_groups = groups[:]
        rng.shuffle(shuffled_groups)
        folds = [set(shuffled_groups[idx::5]) for idx in range(5)]
        predictions = [0.0] * len(rows)
        baseline_predictions = [0.0] * len(rows)
        for fold in folds:
            train = [row for row in rows if row["qid"] not in fold]
            test_indices = [idx for idx, row in enumerate(rows) if row["qid"] in fold]
            model = _fit_ridge(train, features, alpha=2.0)
            baseline = _mean(row["actual_difficulty"] for row in train)
            for idx in test_indices:
                predictions[idx] = model(rows[idx])
                baseline_predictions[idx] = baseline
        y = [row["actual_difficulty"] for row in rows]
        mae_values.append(_mae(y, predictions))
        base_mae_values.append(_mae(y, baseline_predictions))
        spearman_values.append(_spearman(y, predictions))
    gains = [base - model for base, model in zip(base_mae_values, mae_values, strict=True)]
    return {
        "features": len(features),
        "baseline_mae_mean": _mean(base_mae_values),
        "cv_mae_mean": _mean(mae_values),
        "mae_gain_mean": _mean(gains),
        "mae_gain_ci_low": _percentile(gains, 0.025),
        "mae_gain_ci_high": _percentile(gains, 0.975),
        "cv_spearman_mean": _mean(spearman_values),
        "cv_spearman_median": _percentile(spearman_values, 0.5),
    }


def _fit_ridge(rows: list[dict[str, Any]], features: list[str], *, alpha: float) -> Callable[[dict[str, Any]], float]:
    x = [[float(row[name]) for name in features] for row in rows]
    y = [row["actual_difficulty"] for row in rows]
    means = [_mean(row[col] for row in x) for col in range(len(features))]
    stds = []
    for col, mean in enumerate(means):
        std = math.sqrt(_mean((row[col] - mean) ** 2 for row in x))
        stds.append(std or 1.0)
    design = [[1.0] + [(value - means[idx]) / stds[idx] for idx, value in enumerate(row)] for row in x]
    weights = _solve(_normal_matrix(design, alpha), _normal_vector(design, y))

    def predict(row: dict[str, Any]) -> float:
        values = [float(row[name]) for name in features]
        scaled = [1.0] + [(value - means[idx]) / stds[idx] for idx, value in enumerate(values)]
        return max(0.0, min(1.0, sum(a * b for a, b in zip(scaled, weights, strict=True))))

    return predict


def _control_index_bins(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [
        ("easy_control", lambda value: value < 2.45),
        ("medium_control", lambda value: 2.45 <= value < 3.45),
        ("hard_control", lambda value: value >= 3.45),
    ]
    out = []
    for name, fn in bins:
        vals = [row["actual_difficulty"] for row in rows if fn(row["candidate_control_index"])]
        out.append(
            {
                "band": name,
                "n": len(vals),
                "mean_actual_difficulty": _mean(vals) if vals else 0.0,
                "std": _std(vals),
                "min": min(vals) if vals else 0.0,
                "max": max(vals) if vals else 0.0,
            }
        )
    return out


def _interpretation() -> list[str]:
    return [
        "不是只有选项项有效；文段/主旨侧的 discourse_turn_complexity 和 correct_option_abstraction_gap 有方向性，但在当前样本中弱于局部细节错项强度。",
        "local_detail_distractor_strength 是当前最清楚的叶族主旋钮：它同时具备可读标注、可 prompt 控制、可 validator 复查、可投影分箱。",
        "pairwise 轴中的 decisive_evidence_visibility_load、exclusion_reasoning_load、easy_wrong_main_claim_proximity 适合做 hard guardrail，而不适合作为单独主轴。",
        "当前统计支持仍是 candidate 级别；多重比较校正后不能宣称强显著，只能宣称有方向一致的可控潜质。",
    ]


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# center_understanding / 程度词：叶族控制相关性分析",
        "",
        "本报告补足叶族难度控制的统计过程：不只看选项，也纳入文段主旨可见性、行文转折、正确项抽象差距、范围程度判断、选项集竞争、正确项-易错项 pairwise 竞争与少量文本辅助项。",
        "",
        "## 样本",
        "",
        f"- family: `{report['sample']['family']}`",
        f"- leaf: `{report['sample']['leaf']}`",
        f"- n: `{report['sample']['n']}`",
        f"- actual difficulty mean: `{report['sample']['actual_difficulty_mean']:.4f}`",
        f"- actual difficulty std: `{report['sample']['actual_difficulty_std']:.4f}`",
        f"- range: `{report['sample']['actual_difficulty_min']:.4f}` - `{report['sample']['actual_difficulty_max']:.4f}`",
        "",
        "## 相关性",
        "",
        _correlation_table(report["correlations"]),
        "",
        "说明：`perm_p` 为 Spearman 置换检验 p 值，`bh_q` 为 Benjamini-Hochberg 多重比较校正后的 q 值。",
        "",
        "## 单轴重复 5-fold CV",
        "",
        _cv_table(report["repeated_univariate_cv"]),
        "",
        "## 组级消融重复 5-fold CV",
        "",
        _group_cv_table(report["repeated_group_cv"]),
        "",
        "## control_index 分箱",
        "",
        _bin_table(report["control_index_bins"]),
        "",
        "## 结论",
        "",
    ]
    lines.extend(f"- {item}" for item in report["interpretation"])
    lines.append("")
    return "\n".join(lines)


def _correlation_table(rows: list[dict[str, Any]]) -> str:
    out = [
        "| group | feature | Spearman | 95% CI | Pearson | perm_p | bh_q |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            f"| `{row['group']}` | `{row['feature']}` | {row['spearman']:.4f} | "
            f"[{row['spearman_ci_low']:.4f}, {row['spearman_ci_high']:.4f}] | "
            f"{row['pearson']:.4f} | {row['perm_p']:.4f} | {row['bh_q']:.4f} |"
        )
    return "\n".join(out)


def _cv_table(rows: list[dict[str, Any]]) -> str:
    out = [
        "| group | feature | baseline MAE | CV MAE | MAE gain | gain 95% CI | CV Spearman mean |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            f"| `{row['group']}` | `{row['feature']}` | {row['baseline_mae_mean']:.4f} | "
            f"{row['cv_mae_mean']:.4f} | {row['mae_gain_mean']:.4f} | "
            f"[{row['mae_gain_ci_low']:.4f}, {row['mae_gain_ci_high']:.4f}] | {row['cv_spearman_mean']:.4f} |"
        )
    return "\n".join(out)


def _group_cv_table(rows: list[dict[str, Any]]) -> str:
    out = [
        "| model | features | baseline MAE | CV MAE | MAE gain | gain 95% CI | CV Spearman mean |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            f"| `{row['model']}` | {row['features']} | {row['baseline_mae_mean']:.4f} | {row['cv_mae_mean']:.4f} | "
            f"{row['mae_gain_mean']:.4f} | [{row['mae_gain_ci_low']:.4f}, {row['mae_gain_ci_high']:.4f}] | "
            f"{row['cv_spearman_mean']:.4f} |"
        )
    return "\n".join(out)


def _bin_table(rows: list[dict[str, Any]]) -> str:
    out = ["| band | n | mean difficulty | std | min | max |", "|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        out.append(f"| `{row['band']}` | {row['n']} | {row['mean_actual_difficulty']:.4f} | {row['std']:.4f} | {row['min']:.4f} | {row['max']:.4f} |")
    return "\n".join(out)


def _clause_count(text: str) -> int:
    return len([part for part in re.split(r"[，。；：！？、\n]+", text) if part.strip()])


def _option_mean_len(options: dict[str, str]) -> float:
    vals = [len(str(value)) for value in options.values() if str(value)]
    return _mean(vals)


def _correct_wrong_len_gap(row: dict[str, Any]) -> float:
    options = row.get("options") or {}
    correct = str(options.get(row.get("answer") or "") or "")
    wrong = str(options.get(row.get("easy_wrong") or "") or "")
    return abs(len(correct) - len(wrong))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _normal_matrix(design: list[list[float]], alpha: float) -> list[list[float]]:
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
    cols = len(design[0])
    vector = [0.0 for _ in range(cols)]
    for row, y in zip(design, target, strict=True):
        for idx in range(cols):
            vector[idx] += row[idx] * y
    return vector


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    aug = [matrix[idx][:] + [vector[idx]] for idx in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col] or 1e-12
        for j in range(col, n + 1):
            aug[col][j] /= divisor
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
    return [aug[idx][n] for idx in range(n)]


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    return _mean(abs(a - b) for a, b in zip(y_true, y_pred, strict=True))


def _spearman(xs: list[float], ys: list[float]) -> float:
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return 0.0
    return _pearson(_ranks(xs), _ranks(ys))


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    dx = sum((value - mx) ** 2 for value in xs)
    dy = sum((value - my) ** 2 for value in ys)
    if dx == 0 or dy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / math.sqrt(dx * dy)


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


def _mean(values: Any) -> float:
    vals = [float(value) for value in values]
    return sum(vals) / len(vals) if vals else 0.0


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    m = _mean(values)
    return math.sqrt(_mean((value - m) ** 2 for value in values))


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return ordered[idx]


if __name__ == "__main__":
    main()
