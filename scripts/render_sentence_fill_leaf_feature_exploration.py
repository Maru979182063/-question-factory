"""Render a leaf-first feature exploration report for sentence_fill.

This is a reading-led report generator. The numerical inputs are used as
scaffolding, while the leaf feature hypotheses are intentionally explicit and
reviewable instead of being hidden inside service code.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = ROOT / "reports/difficulty_control/empirical_labeling"
LEAF_EXPLORATION_JSON = ROOT / "reports/difficulty_control/leaf_difficulty_exploration/leaf_difficulty_exploration.json"
OUT_DIR = ROOT / "reports/difficulty_control/leaf_feature_exploration"
ASSET_DIR = OUT_DIR / "assets"


LEAF_FEATURES: dict[str, dict[str, Any]] = {
    "横线在中间-启下": {
        "role": "前文给出背景或对比，横线必须把读者推向后文论述方向。",
        "core_mechanism": "后文指向锚点是否明确，以及横线是否需要把局部事实提升为下一步论点。",
        "reuse_axes": {
            "local_binding_complexity": "保留，但应改写为前句触发点识别。",
            "global_context_dependency": "弱化；启下题更看后文落点，不只是全文依赖。",
            "distractor_similarity": "保留，但要从表面相似改为方向相似。",
            "blank_function_ambiguity": "保留，用于判断横线是转折、推进还是类比延展。",
        },
        "candidate_dimensions": [
            ("forward_anchor_specificity", 3, "后文有没有显性落点；落点越隐蔽越难。"),
            ("transition_abstraction_leap", 3, "是否要从前文事实跳到后文概括命题。"),
            ("analogy_chain_fit", 2, "比喻/类比链是否明确，例如吸铁石、火、旗帜。"),
            ("option_direction_competition", 2, "错项是否也能指向后文，但方向偏一层。"),
        ],
        "reading_note": "易题往往有强类比链或后文直接承接；难题通常是前文事实和后文结论之间隔着一层抽象桥。",
    },
    "横线在中间-承上": {
        "role": "横线主要回收前文局部语义，后文只是延续或补充。",
        "core_mechanism": "是否能精准复现前文的语义重心，而不是选择一个貌似相关的泛化表达。",
        "reuse_axes": {
            "local_binding_complexity": "核心轴，应细化为前文重心锁定。",
            "global_context_dependency": "通常不是主轴，除非后文反向限定。",
            "distractor_similarity": "保留，尤其是近义表达和语域相似错项。",
            "blank_function_ambiguity": "弱化；功能通常明确为承上。",
        },
        "candidate_dimensions": [
            ("previous_focus_lock", 3, "前文中心词/中心关系是否容易锁定。"),
            ("micro_collocation_fit", 3, "文学性、成语、搭配是否精细，例如云在头顶流着。"),
            ("local_register_fit", 2, "选项语体是否贴合文段。"),
            ("causal_tail_precision", 2, "承上句是否还要精确落到因果后果。"),
        ],
        "reading_note": "这一叶族经常不是宏观难，而是微观贴合难；文学描写、习语搭配会让表面结构轴低估难度。",
    },
    "横线在中间-承上启下": {
        "role": "横线同时回收前文并开启后文，是典型枢纽句。",
        "core_mechanism": "前后约束是否同向，还是需要把两个语义面折叠成一个中介命题。",
        "reuse_axes": {
            "local_binding_complexity": "保留，但必须拆成前向绑定和后向绑定。",
            "global_context_dependency": "保留，是本叶族核心结构轴之一。",
            "distractor_similarity": "保留，但要看错项是否只满足一侧语境。",
            "blank_function_ambiguity": "保留，尤其区分解释、转折、价值判断、引语承接。",
        },
        "candidate_dimensions": [
            ("bidirectional_constraint_balance", 3, "选项是否同时满足前后文，还是只满足一边。"),
            ("hinge_concept_abstraction", 3, "枢纽概念是否需要高层概括。"),
            ("quote_or_maxim_mapping", 3, "格言/成语是否要映射到文段价值关系。"),
            ("one_side_distractor_strength", 2, "强错项常常只贴前文或只贴后文。"),
        ],
        "reading_note": "这类题的难度不在横线位置本身，而在双向约束。只满足一侧的错项是主要陷阱。",
    },
    "横线在开头-概括后文": {
        "role": "横线作为总领句，压缩后文全部论述。",
        "core_mechanism": "概括范围、抽象层级和后文例证密度是否匹配。",
        "reuse_axes": {
            "local_binding_complexity": "弱化；开头题局部绑定通常不是关键。",
            "global_context_dependency": "核心轴，但应细化为全文覆盖率。",
            "distractor_similarity": "保留，尤其是只概括局部例子的错项。",
            "blank_function_ambiguity": "保留，用于区分总领、引入、价值判断。",
        },
        "candidate_dimensions": [
            ("summary_scope_coverage", 3, "正确项是否覆盖全文而非局部材料。"),
            ("theme_abstraction_gap", 3, "正确项是否需要从例证上升为抽象主题。"),
            ("example_enumeration_clarity", 2, "后文例子是否同质；同质越强越容易。"),
            ("philosophical_concept_tension", 2, "相对/绝对、真理/谬误等概念对立会显著增难。"),
        ],
        "reading_note": "易题常是多个同质例子直接指向总领；难题往往有哲理化、相对化、概念边界。",
    },
    "横线在开头-横线为首句中的分句": {
        "role": "横线不是完整首句，而是首句内部的成分或分句。",
        "core_mechanism": "既要接句法，又要接开篇论述方向；句法约束有时降低难度，有时制造陷阱。",
        "reuse_axes": {
            "local_binding_complexity": "保留，但应解释为句内搭桥。",
            "global_context_dependency": "保留，训练内已有一定信号。",
            "distractor_similarity": "保留，尤其政策/抽象名词竞争。",
            "blank_function_ambiguity": "保留，但要拆成句法功能和语义功能。",
        },
        "candidate_dimensions": [
            ("opening_clause_syntax_lock", 3, "句法位置是否强约束选项。"),
            ("opening_clause_semantic_role", 3, "该分句是定义、对比、判断还是话题设定。"),
            ("policy_abstraction_competition", 2, "政策类抽象名词容易相互竞争。"),
            ("idiom_to_argument_fit", 2, "成语/格言作为分句时要映射后文论证。"),
        ],
        "reading_note": "这类题不能简单归入开头概括；它有很强的句内结构层，应该单独建叶族轴。",
    },
    "横线在开头-话题引入": {
        "role": "横线用引语、格言、现象或判断把读者带入话题。",
        "core_mechanism": "引入语和后文主旨之间的映射关系，尤其是诗句/格言的抽象含义。",
        "reuse_axes": {
            "local_binding_complexity": "弱化；局部绑定无法解释诗句映射。",
            "global_context_dependency": "保留，但要重写为话题框架匹配。",
            "distractor_similarity": "保留，错项常有相似积极语义但价值方向不同。",
            "blank_function_ambiguity": "保留，用于区分话题引入和总领判断。",
        },
        "candidate_dimensions": [
            ("topic_entry_abstraction", 3, "引入语到全文主题之间的抽象跨度。"),
            ("quote_idiom_mapping", 3, "诗句、格言、成语的语义映射难度。"),
            ("quote_familiarity_risk", 2, "熟悉但方向相近的名句会制造误选。"),
            ("value_direction_precision", 2, "改革、求索、更新、坚韧等价值方向是否精确。"),
        ],
        "reading_note": "这是全量里结构轴最容易低估的叶族之一；它的难点在文化表达和话题框架，不在横线位置。",
    },
    "横线在结尾-总结前文（原为 结论）": {
        "role": "横线收束全文，给出结论、判断或概括。",
        "core_mechanism": "前文是否强制推出某个结论，以及选项是否过宽、过窄或偷换概念。",
        "reuse_axes": {
            "local_binding_complexity": "弱化；结尾题更依赖多句累积。",
            "global_context_dependency": "核心轴，但需细化为结论强制力。",
            "distractor_similarity": "保留，尤其结论范围相近错项。",
            "blank_function_ambiguity": "保留，用于区分结论、评价、延伸。",
        },
        "candidate_dimensions": [
            ("conclusion_force_strength", 3, "前文是否只能推出一个结论。"),
            ("scope_exactness", 3, "正确项范围是否恰好覆盖前文。"),
            ("constraint_list_integration", 2, "是否要整合多条限制/瓶颈/原因。"),
            ("over_extension_trap", 2, "错项是否把结论扩大为领域判断或未来判断。"),
        ],
        "reading_note": "易题有强因果收束；难题常在多个限制条件中抽取恰当结论，错项看起来更宏大但越界。",
    },
    "横线在结尾-提出对策（原为 对策）": {
        "role": "横线根据前文问题或风险提出行动方案。",
        "core_mechanism": "方案是否精准回应前文问题的层级、对象和范围。",
        "reuse_axes": {
            "local_binding_complexity": "保留为问题触发点识别。",
            "global_context_dependency": "保留，但不是总结全文，而是整合问题链。",
            "distractor_similarity": "保留，错项常是泛化对策或只解局部问题。",
            "blank_function_ambiguity": "保留，用于识别是否必须给对策。",
        },
        "candidate_dimensions": [
            ("problem_solution_specificity", 3, "对策是否直接回应核心问题。"),
            ("actor_scope_alignment", 2, "行动主体和责任边界是否匹配。"),
            ("countermeasure_granularity", 3, "对策过泛或过细都会错。"),
            ("multi_problem_coverage", 2, "是否覆盖前文多个问题层。"),
        ],
        "reading_note": "这一叶族的核心不是结尾，而是问题-方案匹配；错项常有正确价值但解决错对象。",
    },
    "横线在结尾-横线为尾句中的分句": {
        "role": "横线是尾句的一部分，既要完成句内结构，又要完成全文收束。",
        "core_mechanism": "尾句分句的语义转向、情感立场和句法收束是否精确。",
        "reuse_axes": {
            "local_binding_complexity": "保留，句内前半句约束很强。",
            "global_context_dependency": "保留，尾句必须回收全文。",
            "distractor_similarity": "保留，但要看立场/情感方向，而非只看词面。",
            "blank_function_ambiguity": "保留，但拆成句内功能和全文功能。",
        },
        "candidate_dimensions": [
            ("tail_clause_semantic_turn", 3, "尾句前半句到横线的语义转向是否隐蔽。"),
            ("stance_emotion_calibration", 3, "惋惜、肯定、批判、升华等情感立场是否精确。"),
            ("sentence_completion_constraint", 2, "句法和语气是否强约束选项。"),
            ("final_scope_compression", 2, "是否要把全文压缩成尾句中的一个分句。"),
        ],
        "reading_note": "这类题会被全局经验轴低估，因为难点常是尾句局部立场，而不是传统的易错项竞争强度。",
    },
    "特殊题型-问语句在文中的位置": {
        "role": "严格说已经不是常规语句填空，而是插入句定位或多空排序。",
        "core_mechanism": "候选句和多个位置之间的双边衔接、指代、逻辑顺序匹配。",
        "reuse_axes": {
            "local_binding_complexity": "需要重写为插入点左右邻接约束。",
            "global_context_dependency": "保留，但任务形态不同。",
            "distractor_similarity": "不再是选项语义相似，而是位置相似。",
            "blank_function_ambiguity": "应替换为插入功能类型。",
        },
        "candidate_dimensions": [
            ("insertion_bilateral_anchor", 3, "插入句前后两侧是否同时匹配。"),
            ("position_sequence_logic", 3, "位置顺序和论证推进是否清晰。"),
            ("reference_resolution_load", 2, "代词、指称、承接词是否增加定位负担。"),
            ("multi_blank_ordering_load", 3, "多空排序题应单独拆，不宜混入常规曲线。"),
        ],
        "reading_note": "建议从 sentence_fill 常规曲线中拆出，至少先作为特殊叶族单列。",
    },
}


def _mean(values: Iterable[float]) -> float:
    data = list(values)
    return sum(data) / len(data) if data else 0.0


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _load_labeled_rows() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(LABEL_DIR.glob("label_output_*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _difficulty_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["leaf"]].append(row)

    summary = []
    for leaf, leaf_rows in sorted(grouped.items()):
        easy = min(leaf_rows, key=lambda row: float(row["empirical_difficulty"]))
        hard = max(leaf_rows, key=lambda row: float(row["empirical_difficulty"]))
        summary.append(
            {
                "leaf": leaf,
                "n": len(leaf_rows),
                "mean_difficulty": _mean(float(row["empirical_difficulty"]) for row in leaf_rows),
                "mean_easy_wrong": _mean(
                    float((row.get("labels") or {}).get("easy_wrong_option_competition", 0.0))
                    for row in leaf_rows
                ),
                "mean_abstraction": _mean(
                    float((row.get("labels") or {}).get("correct_option_abstraction_gap", 0.0))
                    for row in leaf_rows
                ),
                "easy_example": _example_payload(easy),
                "hard_example": _example_payload(hard),
            }
        )
    return summary


def _example_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("annotation_id"),
        "qid": row.get("qid"),
        "difficulty": round(float(row["empirical_difficulty"]), 4),
        "answer": row.get("answer"),
        "easy_wrong_option": row.get("easy_wrong_option"),
        "material_preview": (row.get("material_text") or "").replace("\n", " ")[:150],
        "option_answer_text": (row.get("options") or {}).get(row.get("answer"), ""),
        "option_easy_wrong_text": (row.get("options") or {}).get(row.get("easy_wrong_option"), ""),
    }


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _bar_svg(title: str, data: list[tuple[str, float]], path: Path, *, width: int = 960, height: int = 500) -> None:
    margin_left = 260
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
        parts.append(
            f'<text x="{margin_left - 12}" y="{y + bar_h * 0.72:.1f}" text-anchor="end" '
            f'font-size="14" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(label)}</text>'
        )
        parts.append(f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="6" fill="#2F6F73"/>')
        parts.append(
            f'<text x="{margin_left + bar_w + 8:.1f}" y="{y + bar_h * 0.72:.1f}" '
            f'font-size="13" font-family="Consolas, monospace" fill="#4D564F">{_fmt(value)}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _heatmap_svg(path: Path) -> None:
    leaves = list(LEAF_FEATURES.keys())
    dimensions = [
        "local_or_clause_lock",
        "global_scope",
        "option_competition",
        "abstraction_gap",
        "quote_idiom_mapping",
        "stance_or_value_direction",
        "solution_or_conclusion_force",
    ]
    scores = {
        "横线在中间-启下": [2, 2, 2, 3, 1, 1, 0],
        "横线在中间-承上": [3, 1, 2, 1, 2, 1, 0],
        "横线在中间-承上启下": [2, 3, 3, 3, 3, 2, 1],
        "横线在开头-概括后文": [1, 3, 2, 3, 1, 2, 2],
        "横线在开头-横线为首句中的分句": [3, 2, 2, 2, 2, 2, 0],
        "横线在开头-话题引入": [1, 3, 3, 3, 3, 3, 0],
        "横线在结尾-总结前文（原为 结论）": [1, 3, 2, 2, 1, 2, 3],
        "横线在结尾-提出对策（原为 对策）": [2, 2, 2, 2, 0, 1, 3],
        "横线在结尾-横线为尾句中的分句": [3, 2, 2, 2, 1, 3, 2],
        "特殊题型-问语句在文中的位置": [3, 3, 1, 1, 2, 1, 0],
    }
    width, height = 1120, 620
    left, top = 260, 96
    cell_w, cell_h = 116, 42
    colors = ["#EFE5D4", "#C9D8BF", "#7FB09C", "#2F6F73"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FBF7EF"/>',
        '<text x="24" y="38" font-size="22" font-family="Georgia, SimSun, serif" fill="#1E2B25">Leaf feature intensity map</text>',
        '<text x="24" y="62" font-size="13" font-family="Microsoft YaHei, SimSun, sans-serif" fill="#667067">0=弱 / 1=观察 / 2=重要 / 3=核心</text>',
    ]
    for j, dim in enumerate(dimensions):
        x = left + j * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x:.1f}" y="{top - 18}" text-anchor="middle" font-size="12" '
            f'font-family="Consolas, Microsoft YaHei, sans-serif" fill="#39423D">{html.escape(dim)}</text>'
        )
    for i, leaf in enumerate(leaves):
        y = top + i * cell_h
        parts.append(
            f'<text x="{left - 12}" y="{y + 27}" text-anchor="end" font-size="14" '
            f'font-family="Microsoft YaHei, SimSun, sans-serif" fill="#39423D">{html.escape(leaf)}</text>'
        )
        for j, score in enumerate(scores[leaf]):
            x = left + j * cell_w
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 6}" height="{cell_h - 6}" rx="7" '
                f'fill="{colors[score]}"/>'
            )
            parts.append(
                f'<text x="{x + cell_w / 2 - 3:.1f}" y="{y + 24}" text-anchor="middle" font-size="13" '
                f'font-family="Consolas, monospace" fill="#1E2B25">{score}</text>'
            )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _render_markdown(summary: list[dict[str, Any]], leaf_stats: dict[str, Any]) -> str:
    stat_by_leaf = {row["leaf"]: row for row in leaf_stats.get("leaf_structure_summary", [])}
    overview_rows = []
    for row in sorted(summary, key=lambda item: item["mean_difficulty"], reverse=True):
        stat = stat_by_leaf.get(row["leaf"], {})
        overview_rows.append(
            [
                row["leaf"],
                str(row["n"]),
                _fmt(row["mean_difficulty"]),
                _fmt(row["mean_easy_wrong"]),
                _fmt(row["mean_abstraction"]),
                _fmt((stat.get("current_global_structure") or {}).get("mae", 0.0)),
                _fmt((stat.get("leaf_mean_baseline") or {}).get("mae", 0.0)),
            ]
        )

    sections = []
    for row in summary:
        leaf = row["leaf"]
        spec = LEAF_FEATURES[leaf]
        dim_rows = [
            [f"`{name}`", str(score), note]
            for name, score, note in spec["candidate_dimensions"]
        ]
        reuse_rows = [[f"`{axis}`", note] for axis, note in spec["reuse_axes"].items()]
        easy = row["easy_example"]
        hard = row["hard_example"]
        sections.append(
            f"""### {leaf}

定位：{spec["role"]}

核心机制：{spec["core_mechanism"]}

阅读观察：{spec["reading_note"]}

{_table(["候选叶族维度", "强度", "说明"], dim_rows)}

{_table(["原四轴", "叶族内复用/改写"], reuse_rows)}

样本对照：

- 易题 `{easy["id"]}` / 难度 `{_fmt(easy["difficulty"])}`：答案 `{easy["answer"]}`，易错 `{easy["easy_wrong_option"]}`。正确项：{easy["option_answer_text"]}；易错项：{easy["option_easy_wrong_text"]}。
- 难题 `{hard["id"]}` / 难度 `{_fmt(hard["difficulty"])}`：答案 `{hard["answer"]}`，易错 `{hard["easy_wrong_option"]}`。正确项：{hard["option_answer_text"]}；易错项：{hard["option_easy_wrong_text"]}。
"""
        )

    return f"""# sentence_fill 叶族特征层探索报告

生成时间：2026-04-21
视角：叶族优先，母族只保留为协议外壳和跨叶族公共字段。

## 1. 总结

你的判断基本成立：在语句填空里，真正有区分度的不是 `sentence_fill` 这个母族，而是最下级叶族。母族仍有工程意义，例如统一 schema、报告字段、prompt/validator 接口，但它不应该承担主要难度解释。

更合理的设计是：

```text
leaf_family = feature layer
sentence_fill = protocol envelope
empirical truth = calibration layer
```

也就是说，`sentence_fill` 只管统一“怎么描述难度”，叶族才管“这类题到底难在哪里”。

## 2. 叶族概览

![Leaf empirical difficulty](assets/leaf_empirical_difficulty.svg)

![Leaf feature intensity map](assets/leaf_feature_intensity_map.svg)

{_table(["叶族", "标注n", "平均真实难度", "易错项竞争", "正确项抽象", "当前结构MAE", "叶族均值MAE"], overview_rows)}

解读：

- `开头-话题引入`、`中间-承上启下`、`尾句分句` 更像高风险叶族。
- `开头-概括后文` 当前组合模型表现最好，但仍需要自己的“概括范围/抽象层级”维度。
- `特殊题型-问语句在文中的位置` 不建议继续混在普通填空里，应先单列。

## 3. 原四轴该如何处理

原四轴不是废掉，而是需要从“母族通用定义”下沉为“叶族内改写定义”：

- `local_binding_complexity` 在承上题里是前文重心锁定，在首/尾句分句里是句内续接约束，在插入句题里是左右邻接约束。
- `global_context_dependency` 在概括后文里是全文覆盖率，在话题引入里是话题框架映射，在结尾总结里是结论强制力。
- `distractor_similarity` 不能只看表层相似，要按叶族改写为方向竞争、范围竞争、立场竞争、方案竞争。
- `blank_function_ambiguity` 只能作为粗轴；叶族内要拆成启下、承上、双向枢纽、总领、引入、对策、尾句分句等具体功能。

## 4. 逐叶族探索

{chr(10).join(sections)}

## 5. 建议的新架构

建议难度协议改成两级定义：

```yaml
difficulty_target:
  family: sentence_fill
  leaf_family: 横线在开头-话题引入
  family_axes:
    local_binding_complexity: ...
    global_context_dependency: ...
    distractor_similarity: ...
    blank_function_ambiguity: ...
  leaf_axes:
    topic_entry_abstraction: ...
    quote_idiom_mapping: ...
    value_direction_precision: ...
  empirical_axes:
    easy_wrong_option_competition: ...
    correct_option_abstraction_gap: ...
```

其中：

- `family_axes` 负责跨系统兼容。
- `leaf_axes` 负责真实特征表达。
- `empirical_axes` 负责和学生正确率拟合。

## 6. 下一轮最小落地建议

先不要给 10 个叶族都做完整模型。建议挑 3 个高价值叶族做最小闭环：

1. `横线在开头-话题引入`：补 `topic_entry_abstraction / quote_idiom_mapping / value_direction_precision`。
2. `横线在结尾-横线为尾句中的分句`：补 `tail_clause_semantic_turn / stance_emotion_calibration`。
3. `横线在中间-承上启下`：补 `bidirectional_constraint_balance / one_side_distractor_strength`。

这三类最能证明叶族特征层的必要性，也最容易解释为什么全局母族曲线不够。
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    rows = _load_labeled_rows()
    summary = _difficulty_summary(rows)
    leaf_stats = json.loads(LEAF_EXPLORATION_JSON.read_text(encoding="utf-8"))

    _bar_svg(
        "Leaf empirical difficulty from labeled samples",
        [(row["leaf"], row["mean_difficulty"]) for row in sorted(summary, key=lambda item: item["mean_difficulty"], reverse=True)],
        ASSET_DIR / "leaf_empirical_difficulty.svg",
    )
    _heatmap_svg(ASSET_DIR / "leaf_feature_intensity_map.svg")

    report = _render_markdown(summary, leaf_stats)
    (OUT_DIR / "sentence_fill_leaf_feature_exploration_report.md").write_text(report, encoding="utf-8")
    (OUT_DIR / "leaf_feature_hypotheses.json").write_text(
        json.dumps(LEAF_FEATURES, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    index = {
        "report": str((OUT_DIR / "sentence_fill_leaf_feature_exploration_report.md").relative_to(ROOT)),
        "hypotheses": str((OUT_DIR / "leaf_feature_hypotheses.json").relative_to(ROOT)),
        "assets": sorted(str(path.relative_to(ROOT)) for path in ASSET_DIR.glob("*.svg")),
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(index, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
