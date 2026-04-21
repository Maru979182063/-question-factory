from __future__ import annotations

import json
import math
import random
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analyze_degree_word_control_correlations import (  # noqa: E402
    FEATURES,
    _feature_rows,
    _load_degree_word_rows,
    _mean,
    _spearman,
    _std,
)


REPORT_ROOT = ROOT / "reports" / "difficulty_control"
OUT_DIR = REPORT_ROOT / "degree_word_leaf_experiment_report"
ASSET_DIR = OUT_DIR / "assets"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    degree = json.loads((REPORT_ROOT / "highfit_probe" / "degree_word_correlation_analysis.json").read_text(encoding="utf-8"))
    highfit = json.loads((REPORT_ROOT / "highfit_probe" / "highfit_probe_fit_report.json").read_text(encoding="utf-8"))
    manual = json.loads((REPORT_ROOT / "empirical_labeling" / "manual_label_fit_report.json").read_text(encoding="utf-8"))
    topic = json.loads((REPORT_ROOT / "topic_intro_control_box_test" / "topic_intro_control_box_fit_report.json").read_text(encoding="utf-8"))
    feature_rows = _feature_rows(_load_degree_word_rows())

    _write_exploration_funnel_svg(ASSET_DIR / "exploration_funnel.svg", manual, topic, highfit, degree)
    _write_correlation_bar_svg(ASSET_DIR / "degree_word_feature_correlations.svg", degree)
    _write_correlation_heatmap_svg(ASSET_DIR / "degree_word_correlation_heatmap.svg", feature_rows)
    _write_cv_ablation_svg(ASSET_DIR / "degree_word_cv_ablation.svg", degree)
    _write_control_bins_svg(ASSET_DIR / "degree_word_control_bins.svg", degree)
    _write_sample_margin_svg(ASSET_DIR / "degree_word_sample_margin.svg", feature_rows)
    _write_hard_band_svg(ASSET_DIR / "degree_word_hard_band_gap.svg", degree)

    report = _render_markdown(degree, highfit, manual, topic)
    (OUT_DIR / "degree_word_leaf_experiment_report.md").write_text(report, encoding="utf-8")
    (OUT_DIR / "index.json").write_text(
        json.dumps(
            {
                "report": str(OUT_DIR / "degree_word_leaf_experiment_report.md"),
                "assets": [path.name for path in sorted(ASSET_DIR.glob("*.svg"))],
                "source_reports": [
                    "reports/difficulty_control/highfit_probe/degree_word_correlation_analysis.json",
                    "reports/difficulty_control/highfit_probe/highfit_probe_fit_report.json",
                    "reports/difficulty_control/empirical_labeling/manual_label_fit_report.json",
                    "reports/difficulty_control/topic_intro_control_box_test/topic_intro_control_box_fit_report.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"report": str(OUT_DIR / "degree_word_leaf_experiment_report.md")}, ensure_ascii=False, indent=2))


def _render_markdown(degree: dict[str, Any], highfit: dict[str, Any], manual: dict[str, Any], topic: dict[str, Any]) -> str:
    top_corr = degree["correlations"][0]
    top_cv = degree["repeated_univariate_cv"][0]
    winner = highfit["recommendation"]["winner"]
    manual_combined = manual["models"]["combined"]["cross_validation"]["overall"]
    topic_best = topic["models"][topic["best_model"]]["cross_validation"]["overall"]

    lines = [
        "# 难度控制探索收尾报告：center_understanding / 程度词",
        "",
        "## 摘要",
        "",
        "本轮目标不是证明所有题型都已经具备强难度控制，而是回答一个更窄但更关键的问题：难度控制能否真正落到叶族，并找到可量化、可生成、可校验的控制旋钮。",
        "",
        "实验结论是：在 `center_understanding / 程度词` 叶族上，我们获得了一条 candidate 级控制成果。当前最可靠变量是 `local_detail_distractor_strength`，即“易错项是否抓住原文局部细节，但不能覆盖全文中心”。它不是完美终局权重，但已经具备 demo 交付价值和后续扩样潜力。",
        "",
        "关键证据：",
        "",
        f"- 单轴 Spearman：`{top_corr['spearman']:.4f}`，Pearson：`{top_corr['pearson']:.4f}`。",
        f"- 置换检验 p：`{top_corr['perm_p']:.4f}`；BH 多重比较 q：`{top_corr['bh_q']:.4f}`。",
        f"- Bootstrap 95% CI：`[{top_corr['spearman_ci_low']:.4f}, {top_corr['spearman_ci_high']:.4f}]`。",
        f"- 200 次重复 5-fold CV MAE 增益：`{top_cv['mae_gain_mean']:.4f}`，95% CI：`[{top_cv['mae_gain_ci_low']:.4f}, {top_cv['mae_gain_ci_high']:.4f}]`。",
        f"- 叶族级候选模型：`{winner['best_model']}`，scope：`{winner['scope']}`，CV Spearman：`{winner['cv_spearman']:.4f}`。",
        "",
        "![Exploration Funnel](assets/exploration_funnel.svg)",
        "",
        "## 1. 实验背景与路线",
        "",
        "我们先后测试了四类路线：",
        "",
        f"- `sentence_fill` 全局结构轴：结构-only CV Spearman `{manual['models']['structure_only']['cross_validation']['overall']['spearman']:.4f}`，说明只靠结构总轴不足。",
        f"- `sentence_fill` 人工阅读轴：combined CV Spearman `{manual_combined['spearman']:.4f}`，证明“阅读型变量”确实有信号，但尚未严格落到单叶族。",
        f"- `sentence_fill / 话题引入`：最佳模型 `{topic['best_model']}`，CV Spearman `{topic_best['spearman']:.4f}`，有方向但不够稳定。",
        f"- `center_understanding / 程度词`：找到 leaf-level candidate 主轴，能进入 prompt、validator 和 projection。",
        "",
        "这个路线说明：难度控制不是全局平均问题，而是叶族机制问题。母族级变量容易被不同认知任务混合后抵消。",
        "",
        "## 2. 数据与样本",
        "",
        f"- 数据来源：桌面真题包 `中心理解题/主题词.docx`、`中心理解题/程度词.docx`、`语句排序题/特殊题型-4句、7句.docx`。",
        f"- 主实验样本：`center_understanding / 程度词`，n = `{degree['sample']['n']}`。",
        f"- 真实标签：由学生正确率换算 `actual_difficulty = 1 - correct_rate`。",
        f"- 难度分布：均值 `{degree['sample']['actual_difficulty_mean']:.4f}`，标准差 `{degree['sample']['actual_difficulty_std']:.4f}`，范围 `{degree['sample']['actual_difficulty_min']:.4f}` - `{degree['sample']['actual_difficulty_max']:.4f}`。",
        "",
        "## 3. 变量体系",
        "",
        "本轮没有只看选项，而是把变量分成六组：",
        "",
        _variable_table(),
        "",
        "变量设计的原则是：能被人读懂，能被 prompt 控制，能被 validator 复查，能映射到 easy / medium / hard。",
        "",
        "## 4. 方法",
        "",
        "统计方法包括：",
        "",
        "- Spearman：衡量变量与真实难度的单调关系。",
        "- Pearson：观察线性趋势。",
        "- 置换检验：随机打乱真实难度 4000 次，估计相关性偶然出现的概率。",
        "- Bootstrap：重复采样 2000 次，估计 Spearman 置信区间。",
        "- BH 多重比较校正：避免在多变量尝试里过度宣称显著。",
        "- 重复 5-fold CV：200 次随机分折，比较模型 MAE 是否稳定打过叶族均值基线。",
        "- 组级消融：分别测试 passage-only、pairwise-only、distractor-primary、all-reading-axes。",
        "",
        "## 5. 相关性结果",
        "",
        "![Feature Correlations](assets/degree_word_feature_correlations.svg)",
        "",
        _correlation_table(degree["correlations"][:10]),
        "",
        "相关性热力图用于查看变量之间是否互相替代或共同指向同一机制。",
        "",
        "![Correlation Heatmap](assets/degree_word_correlation_heatmap.svg)",
        "",
        "主结论：`local_detail_distractor_strength` 是当前唯一同时具备中等相关、置换检验通过、Bootstrap CI 大部分为正的变量。文段项和 pairwise 项不是没有方向，但在当前样本中不稳定。",
        "",
        "## 6. 拟合与消融",
        "",
        "![CV Ablation](assets/degree_word_cv_ablation.svg)",
        "",
        _group_cv_table(degree["repeated_group_cv"]),
        "",
        "消融结论：",
        "",
        "- `distractor_primary` 单轴最稳，平均 MAE 增益 `0.0132`。",
        "- `candidate_control_index` 加入 guardrail 后分箱更容易解释，但 CV MAE 增益下降到 `0.0051`。",
        "- `passage_only`、`pairwise_only` 和 `all_reading_axes` 都未能稳定打过均值基线，说明当前不能堆变量。",
        "",
        "## 7. 控制映射",
        "",
        "当前推荐 projection：",
        "",
        "```text",
        "control_index =",
        "  0.58 * local_detail_distractor_strength",
        "  + 0.22 * decisive_evidence_visibility_load",
        "  + 0.20 * easy_wrong_main_claim_proximity",
        "```",
        "",
        "![Control Bins](assets/degree_word_control_bins.svg)",
        "",
        _bin_table(degree["control_index_bins"]),
        "",
        "解释：hard-control 当前样本只有 5 道，但平均真实难度已经抬到 `0.5847`。这说明 hard 档有形状，但还需要补样本来稳住曲线。",
        "",
        "## 8. 样本边际与扩样方向",
        "",
        "![Sample Margin](assets/degree_word_sample_margin.svg)",
        "",
        "![Hard Band Gap](assets/degree_word_hard_band_gap.svg)",
        "",
        "样本边际判断：",
        "",
        "- 当前 n=50 能支持 candidate 判断，但不足以支撑正式权重。",
        "- hard-control 只有 5 道，是最大短板；要优先补 hard-control 到 30 道。",
        "- 若扩到 n=120，并保持当前效应量，Spearman 置信区间会明显收窄。",
        "- 下一轮不建议继续扩很多弱轴，而应固定 4 个轴：`local_detail_distractor_strength`、`decisive_evidence_visibility_load`、`easy_wrong_main_claim_proximity`、`exclusion_reasoning_load`。",
        "",
        "## 9. 交付结论",
        "",
        "我们可以在 demo 里这样说：",
        "",
        "> 难度控制已不再停留在母族或全局描述，而是在 `center_understanding / 程度词` 叶族上形成了 candidate 级控制箱。当前主旋钮是“局部细节错项强度”，它与学生真实正确率呈稳定正相关，并在重复交叉验证中带来正向 MAE 增益。该控制箱已具备 prompt 控制、validator 复查和 diff report 映射能力，但仍需扩样本后才能升级为正式权重。",
        "",
        "## 10. 后续工作",
        "",
        "1. 扩样：`center_understanding / 程度词` 从 50 道扩到 120 道。",
        "2. 补 hard：hard-control 从 5 道补到至少 30 道。",
        "3. 固轴：下一轮只标 4 个变量，避免 all-reading-axes 过拟合。",
        "4. 生成验证：用 YAML 控制箱生成 easy/medium/hard 三档题，再由 validator 回放 actual_leaf_control_band。",
        "5. 平移：等程度词稳定后，再测 `center_understanding / 主题词`，但主轴应换成 `decisive_evidence_visibility_load` 和 `exclusion_reasoning_load`，不要机械复用程度词主轴。",
        "",
    ]
    return "\n".join(lines)


def _variable_table() -> str:
    rows = [
        "| 变量组 | 变量 | 控制含义 |",
        "|---|---|---|",
        "| passage | `main_claim_visibility` | 中心是否隐藏，是否需要跨句综合 |",
        "| passage | `discourse_turn_complexity` | 文段是否有背景、转折、对策、总结等结构 |",
        "| passage | `scope_degree_decision_load` | 是否需要判断主次、程度、范围 |",
        "| correct_option | `correct_option_abstraction_gap` | 正确项是否需要抽象换说 |",
        "| option_set | `option_competition_density` | 四个选项是否都具有表面合理性 |",
        "| option_set | `theme_term_overlap_trap` | 错项是否复用主题词制造正确感 |",
        "| distractor | `local_detail_distractor_strength` | 易错项是否抓住局部真实信息 |",
        "| pairwise | `decisive_evidence_visibility_load` | 决胜证据是否隐藏 |",
        "| pairwise | `easy_wrong_main_claim_proximity` | 易错项离主旨是否很近 |",
        "| pairwise | `exclusion_reasoning_load` | 排除易错项需要几步推理 |",
    ]
    return "\n".join(rows)


def _correlation_table(rows: list[dict[str, Any]]) -> str:
    out = ["| group | feature | Spearman | Pearson | perm_p | BH q |", "|---|---|---:|---:|---:|---:|"]
    for row in rows:
        out.append(
            f"| `{row['group']}` | `{row['feature']}` | {row['spearman']:.4f} | {row['pearson']:.4f} | {row['perm_p']:.4f} | {row['bh_q']:.4f} |"
        )
    return "\n".join(out)


def _group_cv_table(rows: list[dict[str, Any]]) -> str:
    out = ["| model | features | CV MAE | MAE gain | gain 95% CI | CV Spearman |", "|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        out.append(
            f"| `{row['model']}` | {row['features']} | {row['cv_mae_mean']:.4f} | {row['mae_gain_mean']:.4f} | "
            f"[{row['mae_gain_ci_low']:.4f}, {row['mae_gain_ci_high']:.4f}] | {row['cv_spearman_mean']:.4f} |"
        )
    return "\n".join(out)


def _bin_table(rows: list[dict[str, Any]]) -> str:
    out = ["| band | n | mean difficulty | std | min | max |", "|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        out.append(
            f"| `{row['band']}` | {row['n']} | {row['mean_actual_difficulty']:.4f} | {row['std']:.4f} | {row['min']:.4f} | {row['max']:.4f} |"
        )
    return "\n".join(out)


def _write_exploration_funnel_svg(path: Path, manual: dict[str, Any], topic: dict[str, Any], highfit: dict[str, Any], degree: dict[str, Any]) -> None:
    cards = [
        ("全局结构轴", manual["models"]["structure_only"]["cross_validation"]["overall"]["spearman"], "未通过"),
        ("阅读型人工轴", manual["models"]["combined"]["cross_validation"]["overall"]["spearman"], "强信号但非叶族"),
        ("话题引入叶族", topic["models"][topic["best_model"]]["cross_validation"]["overall"]["spearman"], "弱候选"),
        ("排序题结构轴", highfit["sentence_order"]["best_by_mae"]["cv_spearman"], "未通过"),
        ("程度词叶族", degree["correlations"][0]["spearman"], "candidate"),
    ]
    width, height = 980, 290
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "难度控制探索路线图", 24, "#2b2118", weight="700")]
    x = 32
    for idx, (title, score, status) in enumerate(cards):
        y = 78
        w = 170
        color = "#2f6f73" if status == "candidate" else "#d49b5c" if "强信号" in status else "#b76e57"
        lines.append(_rect(x, y, w, 130, "#fffaf0", stroke="#d8c7aa", rx=16))
        lines.append(_text(x + 16, y + 30, title, 16, "#2b2118", weight="700"))
        lines.append(_text(x + 16, y + 62, f"Spearman {score:.3f}", 14, "#4d4036"))
        lines.append(_rect(x + 16, y + 82, max(4, min(132, abs(score) * 160)), 16, color, rx=8))
        lines.append(_text(x + 16, y + 120, status, 13, color, weight="700"))
        if idx < len(cards) - 1:
            lines.append(f"<path d='M{x + w + 8} {y + 65} L{x + w + 34} {y + 65}' stroke='#907b66' stroke-width='2' marker-end='url(#arrow)'/>")
        x += 188
    lines.insert(1, "<defs><marker id='arrow' markerWidth='10' markerHeight='10' refX='8' refY='3' orient='auto'><path d='M0,0 L0,6 L8,3 z' fill='#907b66'/></marker></defs>")
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_correlation_bar_svg(path: Path, degree: dict[str, Any]) -> None:
    rows = degree["correlations"][:12]
    width, height = 980, 90 + len(rows) * 34
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "变量与真实难度的 Spearman 相关", 24, "#2b2118", weight="700")]
    zero_x = 510
    lines.append(f"<line x1='{zero_x}' y1='62' x2='{zero_x}' y2='{height-24}' stroke='#b7a58f' stroke-width='1'/>")
    for i, row in enumerate(rows):
        y = 72 + i * 34
        val = row["spearman"]
        bar_w = abs(val) * 420
        x = zero_x if val >= 0 else zero_x - bar_w
        color = "#2f6f73" if row["feature"] == "local_detail_distractor_strength" else "#d49b5c" if val >= 0 else "#b76e57"
        lines.append(_text(28, y + 16, row["feature"], 13, "#3d332a"))
        lines.append(_rect(x, y, bar_w, 20, color, rx=6))
        lines.append(_text(940, y + 15, f"{val:.3f}", 13, "#3d332a", anchor="end"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_correlation_heatmap_svg(path: Path, feature_rows: list[dict[str, Any]]) -> None:
    names = [
        "actual_difficulty",
        "local_detail_distractor_strength",
        "decisive_evidence_visibility_load",
        "easy_wrong_main_claim_proximity",
        "exclusion_reasoning_load",
        "correct_option_abstraction_gap",
        "discourse_turn_complexity",
        "main_claim_visibility",
        "option_competition_density",
        "theme_term_overlap_trap",
    ]
    values = {name: [row[name] if name != "actual_difficulty" else row["actual_difficulty"] for row in feature_rows] for name in names}
    cell = 54
    left = 260
    top = 130
    width = left + cell * len(names) + 30
    height = top + cell * len(names) + 40
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "相关性热力图（Spearman）", 24, "#2b2118", weight="700")]
    for i, name in enumerate(names):
        lines.append(f"<text x='{left + i * cell + 27}' y='{top - 10}' transform='rotate(-45 {left + i * cell + 27},{top - 10})' font-family='Consolas, monospace' font-size='11' fill='#3d332a'>{_short(name)}</text>")
        lines.append(_text(24, top + i * cell + 33, _short(name), 11, "#3d332a"))
    for r, row_name in enumerate(names):
        for c, col_name in enumerate(names):
            corr = _spearman(values[row_name], values[col_name])
            color = _diverging_color(corr)
            x = left + c * cell
            y = top + r * cell
            lines.append(_rect(x, y, cell - 2, cell - 2, color))
            if r == c or row_name == "actual_difficulty" or col_name == "actual_difficulty":
                lines.append(_text(x + cell / 2, y + 31, f"{corr:.2f}", 10, "#2b2118", anchor="middle"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_cv_ablation_svg(path: Path, degree: dict[str, Any]) -> None:
    rows = degree["repeated_group_cv"]
    width, height = 980, 110 + len(rows) * 42
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "组级消融：重复 5-fold CV MAE 增益", 24, "#2b2118", weight="700")]
    zero_x = 520
    scale = 760
    lines.append(f"<line x1='{zero_x}' y1='70' x2='{zero_x}' y2='{height-32}' stroke='#8e7a65' stroke-width='1'/>")
    for i, row in enumerate(rows):
        y = 82 + i * 42
        gain = row["mae_gain_mean"]
        bar_w = abs(gain) * scale
        x = zero_x if gain >= 0 else zero_x - bar_w
        color = "#2f6f73" if gain >= 0 else "#b76e57"
        lines.append(_text(28, y + 16, row["model"], 14, "#3d332a"))
        lines.append(_rect(x, y, bar_w, 24, color, rx=7))
        lines.append(_text(940, y + 17, f"{gain:+.4f}", 13, "#3d332a", anchor="end"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_control_bins_svg(path: Path, degree: dict[str, Any]) -> None:
    rows = degree["control_index_bins"]
    width, height = 780, 360
    chart_x, chart_y, chart_w, chart_h = 90, 70, 600, 220
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "control_index 分箱与真实平均难度", 24, "#2b2118", weight="700")]
    max_v = max(row["mean_actual_difficulty"] + row["std"] for row in rows)
    for i in range(5):
        y = chart_y + chart_h - chart_h * i / 4
        lines.append(f"<line x1='{chart_x}' y1='{y:.1f}' x2='{chart_x+chart_w}' y2='{y:.1f}' stroke='#eadfce'/>")
        lines.append(_text(chart_x - 12, y + 4, f"{max_v*i/4:.2f}", 11, "#6d5a49", anchor="end"))
    bar_w = 110
    gap = 80
    for i, row in enumerate(rows):
        x = chart_x + 80 + i * (bar_w + gap)
        h = chart_h * row["mean_actual_difficulty"] / max_v
        y = chart_y + chart_h - h
        color = ["#91b7a8", "#d49b5c", "#b76e57"][i]
        lines.append(_rect(x, y, bar_w, h, color, rx=10))
        err = chart_h * row["std"] / max_v
        cx = x + bar_w / 2
        lines.append(f"<line x1='{cx}' y1='{max(chart_y, y-err):.1f}' x2='{cx}' y2='{min(chart_y+chart_h, y+err):.1f}' stroke='#2b2118' stroke-width='2'/>")
        lines.append(_text(cx, chart_y + chart_h + 24, row["band"].replace("_", "-"), 13, "#3d332a", anchor="middle"))
        lines.append(_text(cx, y - 10, f"n={row['n']}, mean={row['mean_actual_difficulty']:.2f}", 12, "#3d332a", anchor="middle"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_sample_margin_svg(path: Path, feature_rows: list[dict[str, Any]]) -> None:
    current_r = _spearman([row["local_detail_distractor_strength"] for row in feature_rows], [row["actual_difficulty"] for row in feature_rows])
    points = []
    for n in [50, 80, 120, 160, 200]:
        width = _fisher_ci_width(current_r, n)
        points.append((n, width))
    width, height = 780, 360
    chart_x, chart_y, chart_w, chart_h = 90, 70, 600, 220
    max_width = max(value for _, value in points)
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "样本边际：相关性置信区间预计收窄", 24, "#2b2118", weight="700")]
    for i in range(5):
        y = chart_y + chart_h - chart_h * i / 4
        lines.append(f"<line x1='{chart_x}' y1='{y:.1f}' x2='{chart_x+chart_w}' y2='{y:.1f}' stroke='#eadfce'/>")
    coords = []
    for n, value in points:
        x = chart_x + (n - 50) / (200 - 50) * chart_w
        y = chart_y + chart_h - value / max_width * chart_h
        coords.append((x, y, n, value))
    path_d = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y, _, _) in enumerate(coords))
    lines.append(f"<path d='{path_d}' fill='none' stroke='#2f6f73' stroke-width='4'/>")
    for x, y, n, value in coords:
        lines.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='6' fill='#2f6f73'/>")
        lines.append(_text(x, chart_y + chart_h + 24, str(n), 12, "#3d332a", anchor="middle"))
        lines.append(_text(x, y - 12, f"{value:.2f}", 12, "#3d332a", anchor="middle"))
    lines.append(_text(chart_x + chart_w / 2, height - 22, "sample size", 13, "#3d332a", anchor="middle"))
    lines.append(_text(28, chart_y + 10, "95% CI width", 12, "#3d332a"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_hard_band_svg(path: Path, degree: dict[str, Any]) -> None:
    current = next(row for row in degree["control_index_bins"] if row["band"] == "hard_control")["n"]
    target = 30
    width, height = 650, 220
    lines = [_svg_open(width, height), _rect(0, 0, width, height, "#fbfaf7"), _text(28, 36, "hard-control 样本缺口", 24, "#2b2118", weight="700")]
    x, y, w, h = 70, 95, 500, 36
    lines.append(_rect(x, y, w, h, "#eadfce", rx=18))
    lines.append(_rect(x, y, w * current / target, h, "#b76e57", rx=18))
    lines.append(_text(x, y - 16, f"current: {current}", 14, "#3d332a"))
    lines.append(_text(x + w, y - 16, f"target: {target}", 14, "#3d332a", anchor="end"))
    lines.append(_text(x + w / 2, y + 24, f"{current}/{target}", 16, "#2b2118", anchor="middle", weight="700"))
    lines.append(_text(70, 170, "优先补 hard-control，而不是继续增加弱变量。", 14, "#4d4036"))
    lines.append(_svg_close())
    path.write_text("\n".join(lines), encoding="utf-8")


def _fisher_ci_width(r: float, n: int) -> float:
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(max(1, n - 3))
    lo = math.tanh(z - 1.96 * se)
    hi = math.tanh(z + 1.96 * se)
    return hi - lo


def _short(name: str) -> str:
    mapping = {
        "actual_difficulty": "actual",
        "local_detail_distractor_strength": "local_detail",
        "decisive_evidence_visibility_load": "evidence",
        "easy_wrong_main_claim_proximity": "proximity",
        "exclusion_reasoning_load": "exclusion",
        "correct_option_abstraction_gap": "abstraction",
        "discourse_turn_complexity": "discourse",
        "main_claim_visibility": "claim_visible",
        "option_competition_density": "competition",
        "theme_term_overlap_trap": "theme_overlap",
    }
    return mapping.get(name, name)


def _diverging_color(value: float) -> str:
    value = max(-1.0, min(1.0, value))
    if value >= 0:
        t = value
        r = int(244 * (1 - t) + 47 * t)
        g = int(238 * (1 - t) + 111 * t)
        b = int(226 * (1 - t) + 115 * t)
    else:
        t = -value
        r = int(244 * (1 - t) + 183 * t)
        g = int(238 * (1 - t) + 110 * t)
        b = int(226 * (1 - t) + 87 * t)
    return f"rgb({r},{g},{b})"


def _svg_open(width: int, height: int) -> str:
    return f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"


def _svg_close() -> str:
    return "</svg>"


def _rect(x: float, y: float, w: float, h: float, fill: str, *, stroke: str | None = None, rx: float = 0) -> str:
    stroke_attr = f" stroke='{stroke}'" if stroke else ""
    return f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{rx:.1f}' fill='{fill}'{stroke_attr}/>"


def _text(x: float, y: float, text: str, size: int, fill: str, *, anchor: str = "start", weight: str = "400") -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"<text x='{x:.1f}' y='{y:.1f}' text-anchor='{anchor}' font-family='Georgia, Microsoft YaHei, serif' font-size='{size}' font-weight='{weight}' fill='{fill}'>{escaped}</text>"


if __name__ == "__main__":
    main()
