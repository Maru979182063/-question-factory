import json
import math
import os
from collections import defaultdict

# ========= 配置 =========

FILES = {
    "语句填空": "clean_llm_语句填空_labeled.jsonl",
    "主旨概括": "clean_llm_主旨概括_labeled.jsonl",
    "意图判断": "clean_llm_意图判断_labeled.jsonl",
    "标题选择": "clean_llm_标题选择_labeled.jsonl",
    "细节判断": "clean_llm_细节判断_labeled.jsonl",
    "词句理解": "clean_llm_词句理解_labeled.jsonl",
}

EXPORT_CSV = True
CSV_FILE = "correlation_summary.csv"
STYLE_CSV_FILE = "style_analysis.csv"


# ========= 工具 =========

def corr(x, y):
    n = len(x)
    if n == 0:
        return None

    mx = sum(x) / n
    my = sum(y) / n

    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))

    if dx == 0 or dy == 0:
        return 0

    return round(num / (dx * dy), 4)


def load_and_compute(file_path):
    xs = {
        "text_length": [],
        "idiom_count": [],
        "term_count": [],
        "option_similarity_score": [],
    }
    ys = []

    # 👇 新增：风格分组
    style_stats = defaultdict(list)

    if not os.path.exists(file_path):
        print(f"[WARN] 文件不存在: {file_path}")
        return None, None

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)

            label = obj.get("label", {})
            acc = obj.get("accuracy_pct")

            if acc is None:
                continue

            y = float(acc) / 100.0

            xs["text_length"].append(label.get("text_length", 0))
            xs["idiom_count"].append(label.get("idiom_count", 0))
            xs["term_count"].append(label.get("term_count", 0))
            xs["option_similarity_score"].append(
                label.get("option_similarity_score", 0)
            )

            ys.append(y)

            # 👇 新增：style_domain
            style = label.get("style_domain", "未知")
            style_stats[style].append(y)

    result = {
        "n": len(ys),
        "text_length": corr(xs["text_length"], ys),
        "idiom_count": corr(xs["idiom_count"], ys),
        "term_count": corr(xs["term_count"], ys),
        "option_similarity_score": corr(xs["option_similarity_score"], ys),
    }

    # 👇 计算每个 style 的平均正确率
    style_result = {}
    for k, v in style_stats.items():
        if len(v) == 0:
            continue
        style_result[k] = {
            "n": len(v),
            "avg_accuracy": round(sum(v) / len(v), 4),
        }

    return result, style_result


# ========= 主逻辑 =========

summary = {}
style_summary = {}

for name, path in FILES.items():
    res, style_res = load_and_compute(path)
    if res:
        summary[name] = res
        style_summary[name] = style_res


# ========= 打印相关性 =========

print("\n===== 相关性总表 =====\n")
print(f"{'题型':<10} | {'样本数':<6} | {'text_len':<8} | {'idiom':<8} | {'term':<8} | {'similarity':<10}")
print("-" * 70)

for k, v in summary.items():
    print(f"{k:<10} | {v['n']:<6} | {v['text_length']:<8} | {v['idiom_count']:<8} | {v['term_count']:<8} | {v['option_similarity_score']:<10}")


# ========= 打印风格分析 =========

print("\n===== 风格分析（style_domain） =====\n")

for qtype, styles in style_summary.items():
    print(f"\n--- {qtype} ---")
    print(f"{'风格':<10} | {'样本数':<6} | {'平均正确率':<10}")
    print("-" * 40)

    # 按平均正确率排序（方便看难度）
    sorted_styles = sorted(styles.items(), key=lambda x: x[1]["avg_accuracy"])

    for style, data in sorted_styles:
        print(f"{style:<10} | {data['n']:<6} | {data['avg_accuracy']:<10}")


# ========= 导出 CSV =========

if EXPORT_CSV:
    # 原相关性
    with open(CSV_FILE, "w", encoding="utf-8") as f:
        f.write("question_type,n,text_length,idiom_count,term_count,option_similarity_score\n")
        for k, v in summary.items():
            f.write(f"{k},{v['n']},{v['text_length']},{v['idiom_count']},{v['term_count']},{v['option_similarity_score']}\n")

    # 风格分析
    with open(STYLE_CSV_FILE, "w", encoding="utf-8") as f:
        f.write("question_type,style_domain,n,avg_accuracy\n")
        for qtype, styles in style_summary.items():
            for style, data in styles.items():
                f.write(f"{qtype},{style},{data['n']},{data['avg_accuracy']}\n")

    print(f"\n✅ 已导出 CSV: {CSV_FILE}")
    print(f"✅ 已导出风格分析: {STYLE_CSV_FILE}")