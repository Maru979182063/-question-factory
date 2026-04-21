"""Render the sentence-fill empirical difficulty experiment report.

This script is intentionally report-only: it reads experiment artifacts and
does not mutate prompt assets, validator configs, or card specs.
"""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
CURVE_JSON = ROOT / "reports/difficulty_control/empirical_curve/sentence_fill_empirical_curve_fit.json"
CURVE_CSV = ROOT / "reports/difficulty_control/empirical_curve/sentence_fill_empirical_curve_scored_samples.csv"
LABEL_JSON = ROOT / "reports/difficulty_control/empirical_labeling/manual_label_fit_report.json"
LABEL_DIR = ROOT / "reports/difficulty_control/empirical_labeling"
OUT_DIR = ROOT / "reports/difficulty_control/empirical_experiment_report"
ASSET_DIR = OUT_DIR / "assets"


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _std(values: Iterable[float]) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    return (sum((value - avg) ** 2 for value in values) / (len(values) - 1)) ** 0.5


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_curve_rows() -> list[dict]:
    with CURVE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_label_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(LABEL_DIR.glob("label_output_*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _group_prediction_rows(rows: Iterable[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["leaf"]].append(row)

    output: list[dict] = []
    for leaf, leaf_rows in sorted(grouped.items()):
        empirical = [float(row["empirical_difficulty"]) for row in leaf_rows]
        predicted = [float(row["predicted_difficulty"]) for row in leaf_rows]
        errors = [abs(pred - emp) for emp, pred in zip(empirical, predicted)]
        biases = [pred - emp for emp, pred in zip(empirical, predicted)]
        output.append(
            {
                "leaf": leaf,
                "n": len(leaf_rows),
                "empirical_mean": _mean(empirical),
                "empirical_sd": _std(empirical),
                "predicted_mean": _mean(predicted),
                "mae": _mean(errors),
                "bias": _mean(biases),
            }
        )
    return output


def _group_label_rows(rows: Iterable[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["leaf"]].append(row)

    output: list[dict] = []
    for leaf, leaf_rows in sorted(grouped.items()):
        output.append(
            {
                "leaf": leaf,
                "n": len(leaf_rows),
                "empirical_mean": _mean(float(row["empirical_difficulty"]) for row in leaf_rows),
                "easy_wrong_option_competition": _mean(
                    float(row["labels"]["easy_wrong_option_competition"]) for row in leaf_rows
                ),
                "correct_option_abstraction_gap": _mean(
                    float(row["labels"]["correct_option_abstraction_gap"]) for row in leaf_rows
                ),
                "surface_trap_salience": _mean(float(row["labels"]["surface_trap_salience"]) for row in leaf_rows),
                "plausible_distractor_count": _mean(
                    float(row["labels"]["plausible_distractor_count"]) for row in leaf_rows
                ),
            }
        )
    return output


def _bar_chart_svg(
    title: str,
    data: list[tuple[str, float]],
    path: Path,
    *,
    width: int = 920,
    height: int = 430,
    color: str = "#2F6F73",
    max_value: float | None = None,
    value_suffix: str = "",
) -> None:
    margin_left = 245
    margin_right = 42
    margin_top = 54
    margin_bottom = 34
    plot_width = width - margin_left - margin_right
    row_h = (height - margin_top - margin_bottom) / max(len(data), 1)
    max_v = max_value if max_value is not None else max((value for _, value in data), default=1.0)
    max_v = max(max_v, 0.001)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="34" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top - 10}" x2="{margin_left}" y2="{height - margin_bottom + 8}" stroke="#D8CBB7"/>',
    ]
    for idx, (label, value) in enumerate(data):
        y = margin_top + idx * row_h + row_h * 0.18
        bar_h = max(10, row_h * 0.48)
        bar_w = plot_width * max(value, 0) / max_v
        parts.extend(
            [
                f'<text x="{margin_left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
                f'font-size="14" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>',
                f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                f'rx="6" fill="{color}"/>',
                f'<text x="{margin_left + bar_w + 8:.1f}" y="{y + bar_h * 0.72:.1f}" '
                f'font-size="13" font-family="Consolas, monospace" fill="#4D564F">{_fmt(value)}{value_suffix}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _diverging_bar_chart_svg(
    title: str,
    data: list[tuple[str, float]],
    path: Path,
    *,
    width: int = 920,
    height: int = 430,
) -> None:
    margin_left = 245
    margin_right = 50
    margin_top = 54
    margin_bottom = 34
    plot_width = width - margin_left - margin_right
    center = margin_left + plot_width / 2
    row_h = (height - margin_top - margin_bottom) / max(len(data), 1)
    max_abs = max((abs(value) for _, value in data), default=0.1)
    max_abs = max(max_abs, 0.05)

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
        parts.extend(
            [
                f'<text x="{margin_left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
                f'font-size="14" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>',
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="6" fill="{color}"/>',
                f'<text x="{x + bar_w + 8 if value >= 0 else x - 8:.1f}" y="{y + bar_h * 0.72:.1f}" '
                f'text-anchor="start" font-size="13" font-family="Consolas, monospace" fill="#4D564F">{value:+.3f}</text>',
            ]
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _line_chart_svg(title: str, series: dict[str, list[tuple[str, float]]], path: Path) -> None:
    width, height = 920, 420
    margin_left, margin_right, margin_top, margin_bottom = 72, 38, 58, 58
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    labels = [label for label, _ in next(iter(series.values()))]
    max_y = max(value for points in series.values() for _, value in points)
    min_y = min(value for points in series.values() for _, value in points)
    pad = max((max_y - min_y) * 0.12, 0.03)
    max_y += pad
    min_y = max(0.0, min_y - pad)

    def x_at(index: int) -> float:
        return margin_left + plot_w * index / max(len(labels) - 1, 1)

    def y_at(value: float) -> float:
        return margin_top + plot_h * (max_y - value) / max(max_y - min_y, 0.001)

    colors = ["#2F6F73", "#B96045", "#6A5D8F"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        f'<text x="24" y="34" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">{html.escape(title)}</text>',
    ]
    for i in range(5):
        y = margin_top + plot_h * i / 4
        value = max_y - (max_y - min_y) * i / 4
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#E2D7C5"/>')
        parts.append(
            f'<text x="{margin_left - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="12" '
            f'font-family="Consolas, monospace" fill="#667067">{_fmt(value)}</text>'
        )
    for idx, label in enumerate(labels):
        x = x_at(idx)
        parts.append(
            f'<text x="{x:.1f}" y="{height - 24}" text-anchor="middle" font-size="12" '
            f'font-family="Microsoft YaHei, SimSun, sans-serif" fill="#667067">{html.escape(label)}</text>'
        )
    for s_idx, (name, points) in enumerate(series.items()):
        color = colors[s_idx % len(colors)]
        coords = " ".join(f"{x_at(i):.1f},{y_at(value):.1f}" for i, (_, value) in enumerate(points))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round"/>')
        for i, (_, value) in enumerate(points):
            parts.append(f'<circle cx="{x_at(i):.1f}" cy="{y_at(value):.1f}" r="5" fill="{color}"/>')
        legend_x = margin_left + s_idx * 210
        parts.append(f'<rect x="{legend_x}" y="{height - 48}" width="16" height="8" rx="4" fill="{color}"/>')
        parts.append(
            f'<text x="{legend_x + 24}" y="{height - 40}" font-size="13" '
            f'font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(name)}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _model_metric_data(label_report: dict, metric: str) -> list[tuple[str, float]]:
    order = ["structure_only", "label_only", "combined"]
    labels = {
        "structure_only": "结构四轴",
        "label_only": "经验标签",
        "combined": "组合模型",
    }
    return [
        (labels[name], float(label_report["models"][name]["cross_validation"]["overall"][metric]))
        for name in order
    ]


def _curve_bin_series(rows: list[dict]) -> dict[str, list[tuple[str, float]]]:
    sorted_rows = sorted(rows, key=lambda row: float(row["empirical_difficulty"]))
    buckets: list[list[dict]] = [[] for _ in range(5)]
    for index, row in enumerate(sorted_rows):
        buckets[min(4, index * 5 // len(sorted_rows))].append(row)

    empirical: list[tuple[str, float]] = []
    predicted: list[tuple[str, float]] = []
    for index, bucket in enumerate(buckets, start=1):
        label = f"Q{index}"
        empirical.append((label, _mean(float(row["empirical_difficulty"]) for row in bucket)))
        predicted.append((label, _mean(float(row["predicted_difficulty"]) for row in bucket)))
    return {"真实难度": empirical, "结构轴预测": predicted}


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    curve_report = _read_json(CURVE_JSON)
    label_report = _read_json(LABEL_JSON)
    curve_rows = _read_curve_rows()
    label_rows = _read_label_rows()

    structure_leaf_all = _group_prediction_rows(curve_rows)
    combined_leaf = _group_prediction_rows(label_report["models"]["combined"]["scored_rows"])
    label_feature_leaf = _group_label_rows(label_rows)

    _bar_chart_svg(
        "5-fold CV MAE: lower is better",
        _model_metric_data(label_report, "mae"),
        ASSET_DIR / "model_cv_mae.svg",
        color="#2F6F73",
        max_value=0.30,
    )
    _bar_chart_svg(
        "5-fold CV Spearman: higher is better",
        _model_metric_data(label_report, "spearman"),
        ASSET_DIR / "model_cv_spearman.svg",
        color="#B96045",
        max_value=0.80,
    )
    combined_weights = [
        (name.replace("label.", "").replace("axis.", ""), float(value))
        for name, value in label_report["models"]["combined"]["weights"].items()
        if float(value) > 0
    ]
    _bar_chart_svg(
        "Combined model fitted weights",
        combined_weights,
        ASSET_DIR / "combined_weights.svg",
        color="#6A5D8F",
        max_value=1.0,
    )
    _line_chart_svg(
        "373-sample structural curve check",
        _curve_bin_series(curve_rows),
        ASSET_DIR / "structure_curve_bins.svg",
    )
    _bar_chart_svg(
        "Combined model MAE by leaf",
        [(row["leaf"], row["mae"]) for row in sorted(combined_leaf, key=lambda item: item["mae"], reverse=True)],
        ASSET_DIR / "combined_leaf_mae.svg",
        color="#2F6F73",
        max_value=0.24,
        height=500,
    )
    _diverging_bar_chart_svg(
        "Combined model bias by leaf",
        [(row["leaf"], row["bias"]) for row in sorted(combined_leaf, key=lambda item: item["bias"], reverse=True)],
        ASSET_DIR / "combined_leaf_bias.svg",
        height=500,
    )

    structure_metrics = curve_report["equal_weight_baseline"]["metrics"]
    label_models = label_report["models"]
    model_rows = []
    for key, title in [("structure_only", "结构四轴"), ("label_only", "经验标签"), ("combined", "组合模型")]:
        cv = label_models[key]["cross_validation"]["overall"]
        train = label_models[key]["metrics"]
        model_rows.append(
            [
                title,
                _fmt(train["mae"]),
                _fmt(cv["mae"]),
                _fmt(cv["rmse"]),
                _fmt(cv["spearman"]),
                _fmt(cv["band_agreement"]),
            ]
        )

    all_leaf_rows = [
        [
            row["leaf"],
            str(row["n"]),
            _fmt(row["empirical_mean"]),
            _fmt(row["predicted_mean"]),
            _fmt(row["mae"]),
            f"{row['bias']:+.3f}",
        ]
        for row in sorted(structure_leaf_all, key=lambda item: item["mae"], reverse=True)
    ]
    combined_leaf_rows = [
        [
            row["leaf"],
            str(row["n"]),
            _fmt(row["empirical_mean"]),
            _fmt(row["predicted_mean"]),
            _fmt(row["mae"]),
            f"{row['bias']:+.3f}",
        ]
        for row in sorted(combined_leaf, key=lambda item: item["mae"], reverse=True)
    ]
    label_feature_rows = [
        [
            row["leaf"],
            str(row["n"]),
            _fmt(row["empirical_mean"]),
            _fmt(row["easy_wrong_option_competition"]),
            _fmt(row["correct_option_abstraction_gap"]),
            _fmt(row["surface_trap_salience"]),
            _fmt(row["plausible_distractor_count"]),
        ]
        for row in sorted(label_feature_leaf, key=lambda item: item["empirical_mean"], reverse=True)
    ]

    report = f"""# sentence_fill 难度控制经验拟合实验报告

生成时间：2026-04-21
实验目标：验证当前难度控制轴是否能解释真题学生正确率，并找到可落地到题卡系统的最小经验校准维度。

## 1. 管理摘要

本轮实验结论不是“已有四轴已经拟合成功”，而是更有价值的一点：**当前四个结构轴适合做出题控制，但不足以解释学生真实错题难度；真正拉开正确率曲线的，是选项竞争和正确项抽象跨度。**

- 全量解析样本：`373` 道，来自桌面 `语句填空题` 下 `10` 个叶族题包。
- 人工/模型阅读标注样本：`57` 道，按叶族与正确率分层抽样，标注时不使用正确率。
- 真值定义：`empirical_difficulty = 1 - correct_rate`。
- 原结构四轴在全量样本上的相关性很弱：Pearson `{_fmt(structure_metrics["pearson"])}`，Spearman `{_fmt(structure_metrics["spearman"])}`。
- 经验标签模型在 57 样本 5-fold CV 上显著改善：Spearman `{_fmt(label_models["label_only"]["cross_validation"]["overall"]["spearman"])}`，MAE `{_fmt(label_models["label_only"]["cross_validation"]["overall"]["mae"])}`。
- 组合模型最优权重由经验维度主导：`easy_wrong_option_competition = 0.5`，`correct_option_abstraction_gap = 0.3`，并保留 `local_binding_complexity = 0.1`、`global_context_dependency = 0.1` 作为弱辅助。

## 2. 维度层级结论：不是单个叶族维度

这两个主导维度不是“横线在开头-概括后文”这类叶族专属维度，而是 **sentence_fill 家族级经验校准维度**。

建议的层级是：

1. `family = sentence_fill`：放置跨叶族通用的经验难度信号，例如易错项竞争强度、正确项抽象跨度。
2. `leaf_family`：放置叶族先验与偏置，例如“话题引入”天然更依赖话题铺垫，“尾句分句”更容易出现句法续接陷阱。
3. `card_instance`：放置单题实际测量，例如真实正确率、易错项、人工/模型阅读标签。

也就是说，叶族不应该复制一套完全独立的难度轴；叶族更像是对家族经验轴的 `prior / offset / residual correction`。这能避免系统变成 10 套互不兼容的小规则，也方便后续平移到 `sentence_order` 和 `main_idea`。

## 3. 实验设计

数据源：桌面 `C:\\Users\\Maru\\Desktop\\语句填空题` 下按最下级考点整理的真题 docx。
解析字段：题干、文段、选项、答案、解析、正确率、易错项、考点/叶族。
对照目标：学生正确率换算出的经验难度。

模型对比：

- `结构四轴`：当前协议中的 `local_binding_complexity / global_context_dependency / distractor_similarity / blank_function_ambiguity`。
- `经验标签`：阅读样本后标注的学生错题机制维度。
- `组合模型`：结构四轴 + 经验标签一起拟合，观察权重是否保留结构轴。

![5-fold CV MAE](assets/model_cv_mae.svg)

![5-fold CV Spearman](assets/model_cv_spearman.svg)

{_markdown_table(["模型", "Train MAE", "CV MAE", "CV RMSE", "CV Spearman", "CV 难度档一致率"], model_rows)}

## 4. 原结构四轴为什么不够

原四轴是必要的，但它们更像“题目生成结构控制器”，不是完整的“学生错误概率解释器”。在 373 道全量题上，按真实难度分桶后，结构轴预测曲线没有稳定贴住真实曲线。

![373-sample structural curve check](assets/structure_curve_bins.svg)

结构四轴和真实难度的单轴相关：

- `local_binding_complexity`: `{_fmt(curve_report["axis_correlations"]["local_binding_complexity"], 4)}`
- `global_context_dependency`: `{_fmt(curve_report["axis_correlations"]["global_context_dependency"], 4)}`
- `distractor_similarity`: `{_fmt(curve_report["axis_correlations"]["distractor_similarity"], 4)}`
- `blank_function_ambiguity`: `{_fmt(curve_report["axis_correlations"]["blank_function_ambiguity"], 4)}`

解释：结构轴能告诉生成器“横线处需要看前文还是后文、空格功能是否模糊、干扰项表面是否相似”，但学生真正错在何处，往往取决于两个更细的阅读心理机制：

- `easy_wrong_option_competition`：易错项是否真的能和正确项争夺同一个语义位置。
- `correct_option_abstraction_gap`：正确项是否需要从文段中抽象、概括、转述，而不是直接复述。

## 5. 最优经验维度与权重

![Combined model fitted weights](assets/combined_weights.svg)

组合模型给出的候选权重：

- `easy_wrong_option_competition`: `0.5`
- `correct_option_abstraction_gap`: `0.3`
- `local_binding_complexity`: `0.1`
- `global_context_dependency`: `0.1`
- `distractor_similarity / blank_function_ambiguity`: `0`

这个结果不表示结构轴没用，而是说明：**如果目标是拟合学生正确率，结构轴只提供弱辅助；真正主导校准曲线的是经验维度。**

## 6. 叶族波动：有，而且不能忽略

全局拟合并不意味着各叶族都稳定。组合模型总体更好，但叶族残差仍然明显。

![Combined model MAE by leaf](assets/combined_leaf_mae.svg)

![Combined model bias by leaf](assets/combined_leaf_bias.svg)

组合模型在 57 个标注样本上的叶族表现：

{_markdown_table(["叶族", "n", "真实难度均值", "预测难度均值", "MAE", "Bias"], combined_leaf_rows)}

全量 373 样本上，当前结构轴的叶族表现：

{_markdown_table(["叶族", "n", "真实难度均值", "预测难度均值", "MAE", "Bias"], all_leaf_rows)}

需要重点关注的叶族：

- `横线在开头-话题引入`：全量结构轴明显低估真实难度，说明“话题入口”和“概念落点”比当前位置规则更重要。
- `横线在结尾-横线为尾句中的分句`：组合模型仍然低估，可能缺少“句法续接 + 语义收束”的联合陷阱维度。
- `横线在开头-横线为首句中的分句`：组合模型偏高估，说明分句型开头题里有一部分只是句法搭桥，不一定造成学生困难。
- `特殊题型-问语句在文中的位置`：样本只有 3 道，暂时不应和常规填空题共用同一条校准曲线，需要单列观察。

## 7. 经验标签在叶族上的分布

下表显示：两个主导维度是跨叶族存在的，但不同叶族的均值和误差不同。因此它们应放在 `sentence_fill` 家族层，再由叶族提供偏置。

{_markdown_table(["叶族", "n", "真实难度均值", "易错项竞争", "正确项抽象跨度", "表层陷阱显著性", "可竞争干扰项数"], label_feature_rows)}

## 8. 对当前系统的落地建议

建议把难度体系拆成三层，而不是把所有规则继续塞进 service 深处：

1. `DifficultyProjection`：保留现有结构四轴，用于 prompt 和 validator 的可控生成。
2. `EmpiricalDifficultySignals`：新增家族级经验信号，用于解释学生正确率与校准目标难度。
3. `DifficultyCalibrationPatch`：只生成候选 patch，输出给题卡、prompt assets、validator 审阅，不自动回写主配置。

候选新增字段：

```yaml
empirical_difficulty_signals:
  easy_wrong_option_competition: 0.0-1.0
  correct_option_abstraction_gap: 0.0-1.0
  surface_trap_salience: 0.0-1.0
  plausible_distractor_count: 0-3
  leaf_bias_hint: optional
```

当前可先进入最小闭环的只有两个：

- `easy_wrong_option_competition`
- `correct_option_abstraction_gap`

其余维度建议作为观察项，等样本扩大后再决定是否升格。

## 9. 下一步实验

1. 扩大标注：从 57 道扩到至少 120 道，覆盖每个叶族不少于 10 道。
2. 做 leaf-held-out 验证：每次留出一个叶族，检验家族级维度能否迁移。
3. 单列特殊题型：`问语句在文中的位置` 不应暂时混入常规填空曲线。
4. 增加叶族偏置项：例如 `topic_intro_offset`、`tail_clause_syntax_offset`，但只作为校准层候选 patch。
5. 与生成系统接轨：prompt 仍消费结构轴，validator 同时消费结构轴和经验信号，diff report 输出叶族残差。

## 10. 结论

这次实验不能证明“当前难度协议已经完美”，但证明了正确方向：**题卡系统需要结构控制层 + 经验校准层。**

结构四轴负责把题做成目标形态；经验维度负责解释为什么学生会错。全局曲线中，易错项竞争和正确项抽象跨度已经能形成可解释的拟合；叶族层面仍有残差，下一轮应把叶族作为偏置层，而不是把每个叶族拆成独立难度体系。
"""

    (OUT_DIR / "sentence_fill_empirical_experiment_report.md").write_text(report, encoding="utf-8")

    index = {
        "report": str((OUT_DIR / "sentence_fill_empirical_experiment_report.md").relative_to(ROOT)),
        "assets": sorted(str(path.relative_to(ROOT)) for path in ASSET_DIR.glob("*.svg")),
        "inputs": [str(CURVE_JSON.relative_to(ROOT)), str(CURVE_CSV.relative_to(ROOT)), str(LABEL_JSON.relative_to(ROOT))],
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
