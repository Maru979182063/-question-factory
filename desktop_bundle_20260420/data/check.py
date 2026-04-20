import os
import json
import time
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI


# =========================
# 配置区
# =========================

INPUT_FILES = [
    "clean_llm_语句填空.jsonl",
    "clean_llm_主旨概括.jsonl",
    "clean_llm_意图判断.jsonl",
    "clean_llm_标题选择.jsonl",
    "clean_llm_细节判断.jsonl",
    "clean_llm_词句理解.jsonl",
]

START_IDX = 0
MAX_ITEMS = 200

OUTPUT_DIR = "outputs_6types_v2"

BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MAX_RETRIES = 3
RETRY_SLEEP = 2
SAVE_RAW_RESPONSE = True
SLEEP_BETWEEN_REQUESTS = 0.3
SKIP_IF_OUTPUT_EXISTS = False


PASSAGE_FUNCTION_ENUM = [
    "背景引入",
    "观点提出",
    "解释说明",
    "对比辨析",
    "因果论证",
    "举例论证",
    "总结归纳",
    "其他",
]

QUESTION_TYPE_ENUM = [
    "主旨概括",
    "意图判断",
    "细节判断",
    "标题选择",
    "词句理解",
    "语句填空",
]

STYLE_DOMAIN_ENUM = [
    "政治治理",
    "法律司法",
    "经济发展",
    "科技科普",
    "文化社科",
    "民生社会",
    "生态环境",
    "其他",
]

SIM_LEVEL_ENUM = ["低", "中", "高"]

GENERIC_TERM_BLACKLIST = {
    "资源", "政策", "农村", "农民", "产业", "问题", "发展", "规律", "市场规律",
    "科学", "历史真实", "结果", "体系", "结构体系", "研究成果", "工作",
    "信息", "数据", "文化", "故事", "精神", "文章", "视野", "能力"
}

IDIOM_BLACKLIST = {
    "样板村", "平均用力", "简单分解", "尊重农村发展实际", "市场规律",
    "科学事实", "科学数据", "重复操作", "应急情境", "互联网谣言",
    "体积巨大", "厚薄不一", "站在老年人的角度", "资源", "政策",
    "发展模式", "单一发展方式", "临场发挥", "生产与传播", "开阔的视野",
    "认知盲区", "思维局限", "良法是善治的前提"
}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# =========================
# 工具函数
# =========================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def calc_text_length(stem: str) -> int:
    if not stem:
        return 0
    return len("".join(str(stem).split()))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def clamp_score(value: Any, default: float = 0.0) -> float:
    x = safe_float(value, default)
    x = max(0.0, min(1.0, x))
    return round(x, 2)


def clean_string_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        result = []
        for x in value:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                result.append(s)
        return result

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for sep in ["，", "、", ";", "；", "|", "/"]:
            text = text.replace(sep, ",")
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    return []


def dedup_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def looks_like_too_long_phrase(text: str) -> bool:
    return len(text) > 10


def looks_like_sentence_fragment(text: str) -> bool:
    bad_chars = ["，", "。", "；", "：", "？", "！", "“", "”", "(", ")", "（", "）"]
    return any(c in text for c in bad_chars)


def clean_idiom_terms(items: List[str]) -> List[str]:
    cleaned = []
    for x in items:
        x = x.strip()
        if not x:
            continue
        if x in IDIOM_BLACKLIST:
            continue
        if looks_like_sentence_fragment(x):
            continue
        if looks_like_too_long_phrase(x):
            continue

        pure = re.sub(r"[^\u4e00-\u9fa5]", "", x)
        if len(pure) < 4 or len(pure) > 8:
            continue

        cleaned.append(x)

    return dedup_keep_order(cleaned)[:4]


def clean_term_terms(items: List[str]) -> List[str]:
    cleaned = []
    for x in items:
        x = x.strip()
        if not x:
            continue
        if x in GENERIC_TERM_BLACKLIST:
            continue
        if looks_like_sentence_fragment(x):
            continue
        if len(x) > 12:
            continue

        cleaned.append(x)

    return dedup_keep_order(cleaned)[:6]


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = name.replace(".jsonl", "")
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    return name


def map_level_to_score(level: str, dim: str) -> float:
    """
    把低/中/高映射成更有区分度的分数区间。
    这里故意拉开间距，避免全堆在 0.6~0.8。
    """
    mapping = {
        "semantic_similarity": {
            "低": 0.25,
            "中": 0.55,
            "高": 0.85,
        },
        "pos_style_similarity": {
            "低": 0.30,
            "中": 0.60,
            "高": 0.85,
        },
        "collocation_similarity": {
            "低": 0.20,
            "中": 0.55,
            "高": 0.88,
        },
        "distractor_strength": {
            "低": 0.22,
            "中": 0.58,
            "高": 0.86,
        },
    }
    return round(mapping.get(dim, {}).get(level, 0.5), 2)


# =========================
# Prompt
# =========================

def build_prompt(stem: str, options: Dict[str, str]) -> str:
    return f"""你是一个严谨的公考言语题标注助手。

请基于题干和选项，对题目进行标注。
必须严格遵守以下要求：

【总体要求】
1. 只输出 JSON，不要输出解释、前后缀、markdown。
2. 只看 stem 统计 idiom、term、style_domain，不统计 options。
3. 若无法完全确定，也必须给出最合理判断，但不要偷懒输出固定值。
4. 不要为了凑数量而多报词。
5. 相似度不要机械打 0.65/0.70/0.75；必须先判断“低/中/高”，再给分。

【题目类别 question_type】
必须严格从以下六类中选择一个：
{QUESTION_TYPE_ENUM}

【idiom_terms / idiom_count】
idiom_terms 只统计：
1. 标准成语
2. 固定俗语
3. 典故性固定表达
4. 常见固定熟语

不包括：
1. 普通四字词（如：平均用力、资源配置）
2. 一般抽象短语（如：市场规律、发展模式）
3. 临时搭配
4. 长句片段
5. 普通名词短语

规则：
- 只统计 stem，不统计 options
- 如果不确定，不计入
- 每题最多输出 4 个
- idiom_count = idiom_terms 的数量

【term_terms / term_count】
term_terms 只统计：
1. 在科学、技术、法律、经济、政策、军事、医学、传播、互联网等领域中
   具有较强专属性的名词或名词短语

包括示例：
- 基因
- 量子理论
- 广义相对论
- 区块链技术
- 数据协调机制
- 科学立法
- 航天医学

不包括：
1. 普通泛词（如：资源、政策、产业、农村、农民、问题、发展）
2. 一般抽象词
3. 日常表达
4. 普通书面词

规则：
- 只统计 stem，不统计 options
- 如果不确定，不计入
- 每题最多输出 6 个
- term_count = term_terms 的数量

【passage_function】
必须严格从以下类别中选择一个：
{PASSAGE_FUNCTION_ENUM}

判定提示：
- 如果文段主要在定义、介绍、说明某对象/机制，多为“解释说明”
- 如果文段主要先给结论或主张，再展开，多为“观点提出”
- 如果文段主要在比较两种情况/两种路径，多为“对比辨析”
- 如果不明显，再选“其他”

【文字风格 / 文本领域 style_domain】
请判断 stem 的主要文本领域，只能从以下类别中选择一个：
{STYLE_DOMAIN_ENUM}

判定原则：
- 只看 stem，不看 options
- 选择文段主要讨论对象，而不是表面词汇
- 涉及政府治理、政策执行、制度建设、基层工作，优先判为“政治治理”
- 涉及立法、司法、法院、裁判、法律适用，优先判为“法律司法”
- 涉及产业、市场、金融、经济运行、乡村振兴，优先判为“经济发展”
- 涉及科技原理、医学技术、自然科学、工程技术，优先判为“科技科普”
- 涉及文化、历史、艺术、阅读、传播、社会思想，优先判为“文化社科”
- 涉及养老、教育、公服、数字鸿沟、普通社会生活问题，优先判为“民生社会”
- 涉及生态保护、环保、绿水青山、环境治理，优先判为“生态环境”
- 实在不明显，再选“其他”

【option_similarity_detail / option_similarity_score】
请不要直接拍脑袋给 0.xx。
必须先对下面四个维度分别做“低/中/高”判断，再给出对应分数。

四个维度：
1. semantic_similarity：四个选项在语义上的接近程度
2. pos_style_similarity：四个选项在词性、文体风格上的接近程度
3. collocation_similarity：四个选项代入空格后，与上下文搭配的接近程度
4. distractor_strength：错误项对正确项的干扰强度

分档标准：
- 低：差异很大，容易排除
- 中：有部分干扰，但仍能排除一部分
- 高：高度接近，很难区分

请同时输出：
1. 四个维度的 level（低/中/高）
2. 四个维度的 score（0~1，保留两位小数）
3. 一个综合 option_similarity_score（0~1，保留两位小数）

硬性要求：
- 如果四个选项明显差异大，至少两个维度应为“低”
- 如果四个选项高度接近，至少两个维度应为“高”
- 四个维度不要全部相同，除非题目确实极端一致
- option_similarity_score 应与四个维度整体一致，不能随意偏离
- 不要默认输出 0.70 左右

请输出如下 JSON 结构：
{{
  "question_type": "",
  "idiom_terms": [],
  "idiom_count": 0,
  "term_terms": [],
  "term_count": 0,
  "passage_function": "",
  "style_domain": "",
  "option_similarity_detail": {{
    "semantic_similarity_level": "",
    "semantic_similarity_score": 0.0,
    "pos_style_similarity_level": "",
    "pos_style_similarity_score": 0.0,
    "collocation_similarity_level": "",
    "collocation_similarity_score": 0.0,
    "distractor_strength_level": "",
    "distractor_strength_score": 0.0
  }},
  "option_similarity_score": 0.0
}}

题干 stem：
{stem}

选项 options：
{json.dumps(options, ensure_ascii=False)}
"""


# =========================
# 标注后处理
# =========================

def normalize_label(data: Dict[str, Any]) -> Dict[str, Any]:
    question_type = data.get("question_type", "细节判断")
    if question_type not in QUESTION_TYPE_ENUM:
        question_type = "细节判断"

    raw_idiom_terms = clean_string_list(data.get("idiom_terms", []))
    raw_idiom_terms = dedup_keep_order(raw_idiom_terms)
    idiom_terms = clean_idiom_terms(raw_idiom_terms)

    raw_term_terms = clean_string_list(data.get("term_terms", []))
    raw_term_terms = dedup_keep_order(raw_term_terms)
    term_terms = clean_term_terms(raw_term_terms)

    passage_function = data.get("passage_function", "其他")
    if passage_function not in PASSAGE_FUNCTION_ENUM:
        passage_function = "其他"

    style_domain = data.get("style_domain", "其他")
    if style_domain not in STYLE_DOMAIN_ENUM:
        style_domain = "其他"

    detail = data.get("option_similarity_detail", {})
    if not isinstance(detail, dict):
        detail = {}

    sem_level = detail.get("semantic_similarity_level", "中")
    pos_level = detail.get("pos_style_similarity_level", "中")
    col_level = detail.get("collocation_similarity_level", "中")
    dis_level = detail.get("distractor_strength_level", "中")

    if sem_level not in SIM_LEVEL_ENUM:
        sem_level = "中"
    if pos_level not in SIM_LEVEL_ENUM:
        pos_level = "中"
    if col_level not in SIM_LEVEL_ENUM:
        col_level = "中"
    if dis_level not in SIM_LEVEL_ENUM:
        dis_level = "中"

    # 优先使用 level 映射，只有模型明确给 score 时才参考，但仍会校正
    semantic_similarity = map_level_to_score(sem_level, "semantic_similarity")
    pos_style_similarity = map_level_to_score(pos_level, "pos_style_similarity")
    collocation_similarity = map_level_to_score(col_level, "collocation_similarity")
    distractor_strength = map_level_to_score(dis_level, "distractor_strength")

    # 若模型给了 score，则做温和融合，避免完全被忽略
    raw_sem = detail.get("semantic_similarity_score")
    raw_pos = detail.get("pos_style_similarity_score")
    raw_col = detail.get("collocation_similarity_score")
    raw_dis = detail.get("distractor_strength_score")

    def blend(mapped: float, raw: Any) -> float:
        if raw is None:
            return mapped
        r = clamp_score(raw, mapped)
        return round((mapped * 0.7 + r * 0.3), 2)

    semantic_similarity = blend(semantic_similarity, raw_sem)
    pos_style_similarity = blend(pos_style_similarity, raw_pos)
    collocation_similarity = blend(collocation_similarity, raw_col)
    distractor_strength = blend(distractor_strength, raw_dis)

    # 如果四项完全一样，做轻微拉开
    scores = [
        semantic_similarity,
        pos_style_similarity,
        collocation_similarity,
        distractor_strength,
    ]
    if len(set(scores)) == 1:
        base = scores[0]
        semantic_similarity = clamp_score(base - 0.08, base)
        pos_style_similarity = clamp_score(base + 0.06, base)
        collocation_similarity = clamp_score(base, base)
        distractor_strength = clamp_score(base + 0.03, base)

    option_similarity_detail = {
        "semantic_similarity_level": sem_level,
        "semantic_similarity_score": semantic_similarity,
        "pos_style_similarity_level": pos_level,
        "pos_style_similarity_score": pos_style_similarity,
        "collocation_similarity_level": col_level,
        "collocation_similarity_score": collocation_similarity,
        "distractor_strength_level": dis_level,
        "distractor_strength_score": distractor_strength,
    }

    avg_score = round(
        (
            semantic_similarity
            + pos_style_similarity
            + collocation_similarity
            + distractor_strength
        ) / 4,
        2,
    )

    raw_total = data.get("option_similarity_score", avg_score)
    total_score = clamp_score(raw_total, avg_score)

    # 总分偏离平均太大就拉回
    if abs(total_score - avg_score) >= 0.12:
        total_score = avg_score

    return {
        "question_type": question_type,
        "idiom_terms": idiom_terms,
        "idiom_count": len(idiom_terms),
        "term_terms": term_terms,
        "term_count": len(term_terms),
        "passage_function": passage_function,
        "style_domain": style_domain,
        "option_similarity_detail": option_similarity_detail,
        "option_similarity_score": total_score,
    }


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        return json.loads(candidate)

    raise ValueError("模型返回中未找到合法 JSON")


# =========================
# 模型调用
# =========================

def call_model(stem: str, options: Dict[str, str]) -> Dict[str, Any]:
    prompt = build_prompt(stem, options)
    last_err: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                messages=[
                    {"role": "system", "content": "你是一个只输出 JSON 的标注助手。"},
                    {"role": "user", "content": prompt},
                ],
            )

            content = resp.choices[0].message.content or ""
            parsed = extract_json(content)
            normalized = normalize_label(parsed)

            return {
                "parsed": parsed,
                "normalized": normalized,
                "raw_content": content,
            }

        except Exception as e:
            last_err = e
            print(f"[WARN] 模型调用失败，第 {attempt}/{MAX_RETRIES} 次重试：{e}")
            time.sleep(RETRY_SLEEP)

    raise RuntimeError(f"模型多次调用失败：{last_err}")


# =========================
# 文件处理
# =========================

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def process_one_file(input_file: str) -> None:
    bucket_name = sanitize_filename(input_file)

    output_jsonl = os.path.join(OUTPUT_DIR, f"{bucket_name}_labeled.jsonl")
    output_check_json = os.path.join(OUTPUT_DIR, f"{bucket_name}_check.json")
    output_raw_json = os.path.join(OUTPUT_DIR, f"{bucket_name}_raw.json")

    if SKIP_IF_OUTPUT_EXISTS and os.path.exists(output_jsonl):
        print(f"[SKIP] 已存在输出，跳过：{input_file}")
        return

    print("=" * 80)
    print(f"[INFO] 开始处理文件：{input_file}")
    print(f"[INFO] 输出 JSONL：{output_jsonl}")
    print(f"[INFO] 输出 CHECK：{output_check_json}")
    if SAVE_RAW_RESPONSE:
        print(f"[INFO] 输出 RAW：{output_raw_json}")

    all_items = load_jsonl(input_file)
    target_items = all_items[START_IDX:START_IDX + MAX_ITEMS]

    print(f"[INFO] 文件总条数：{len(all_items)}")
    print(f"[INFO] 本次处理区间：[{START_IDX}, {START_IDX + len(target_items)})")
    print(f"[INFO] 实际处理条数：{len(target_items)}")

    labeled_items: List[Dict[str, Any]] = []
    check_items: List[Dict[str, Any]] = []
    raw_items: List[Dict[str, Any]] = []

    for i, item in enumerate(target_items, start=1):
        stem = item.get("stem", "")
        options = item.get("options", {})

        print(f"[INFO] 正在处理 {bucket_name} 第 {i}/{len(target_items)} 题")

        result = call_model(stem, options)
        label = result["normalized"]
        label["text_length"] = calc_text_length(stem)

        new_item = dict(item)
        new_item["label"] = label
        labeled_items.append(new_item)

        check_items.append({
            "question_id": item.get("question_id"),
            "stem": stem,
            "options": options,
            "label": label,
        })

        if SAVE_RAW_RESPONSE:
            raw_items.append({
                "question_id": item.get("question_id"),
                "stem": stem,
                "raw_content": result["raw_content"],
                "parsed": result["parsed"],
                "normalized": label,
            })

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    with open(output_jsonl, "w", encoding="utf-8") as f:
        for item in labeled_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(output_check_json, "w", encoding="utf-8") as f:
        json.dump(check_items, f, ensure_ascii=False, indent=2)

    if SAVE_RAW_RESPONSE:
        with open(output_raw_json, "w", encoding="utf-8") as f:
            json.dump(raw_items, f, ensure_ascii=False, indent=2)

    print(f"[DONE] 已完成：{input_file}")
    print(f"[DONE] 输出：{output_jsonl}")
    print(f"[DONE] 输出：{output_check_json}")
    if SAVE_RAW_RESPONSE:
        print(f"[DONE] 输出：{output_raw_json}")


def main() -> None:
    if API_KEY == "YOUR_API_KEY" or not API_KEY:
        raise ValueError("请先设置 OPENAI_API_KEY 环境变量")

    ensure_dir(OUTPUT_DIR)

    for input_file in INPUT_FILES:
        process_one_file(input_file)

    print("=" * 80)
    print("[ALL DONE] 6 个文件已全部处理完成")


if __name__ == "__main__":
    main()