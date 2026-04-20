import json
import os
import time
from typing import Dict, Any, Optional

from openai import OpenAI

# ========= 配置区 =========
INPUT_FILE = "clean.jsonl"
OUTPUT_FILE = "clean_labeled_by_llm.jsonl"
MODEL = "gpt-4o-mini"   # 小模型先跑
SLEEP_SEC = 0.2         # 控速，别太猛
MAX_RETRY = 3

LABELS = [
    "主旨概括",
    "意图判断",
    "细节判断",
    "标题选择",
    "词句理解",
    "语句填空",
]

SYSTEM_PROMPT = """你是一个公职考试言语理解题型标注助手。
你的任务是根据题干文本，把题目标注为以下六类之一：

1. 主旨概括
2. 意图判断
3. 细节判断
4. 标题选择
5. 词句理解
6. 语句填空

判定标准：
- 语句填空：题干中存在明显空缺，要求填入词语、成语、句子，常见“填入画横线部分最恰当的一项是”“依次填入画横线部分最恰当的一项是”。
- 标题选择：要求给一段文字选择标题，常见“最适合做这段文字标题的是”。
- 主旨概括：要求概括文段中心、主要内容、主要介绍、意在说明什么。
- 意图判断：要求判断“接下来最可能讲什么”“作者意在强调/说明”“这段文字接下来最可能介绍的是”。
- 细节判断：针对文段具体信息做正误或细节判断，常见“下列说法正确/错误的是”“不符合这段文字的是”。
- 词句理解：针对词语、句子、短语在文中的含义理解，常见“文中画线词语/句子理解最恰当的是”“这句话意在说明”。

要求：
- 只能输出一个标签，必须来自六类。
- 若文本中存在明显空缺或“填入横线”，优先判为“语句填空”。
- 若是“这段文字主要介绍了/说明了/强调了”，优先在“主旨概括”和“意图判断”中精确区分：
  - 已经在问文段中心内容 -> 主旨概括
  - 在问作者意图 / 下文内容 / 写作目的 -> 意图判断
- 输出严格 JSON，不要解释，不要额外文本。

输出格式：
{"question_type":"语句填空"}
"""

USER_TEMPLATE = """请根据下面题干判定题型。

题干：
{stem}
"""


def load_done_ids(path: str) -> set:
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                qid = str(obj.get("question_id", "")).strip()
                if qid:
                    done.add(qid)
            except Exception:
                continue
    return done


def extract_text(item: Dict[str, Any]) -> str:
    # 优先用 stem
    stem = item.get("stem")
    if isinstance(stem, str) and stem.strip():
        return stem.strip()

    # 兜底：raw_content / 其他字段
    for key in ["text", "content", "raw_content"]:
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    return ""


def call_llm(client: OpenAI, stem: str) -> str:
    prompt = USER_TEMPLATE.format(stem=stem)

    resp = client.responses.create(
        model=MODEL,
        temperature=0,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    text = resp.output_text.strip()
    data = json.loads(text)
    label = data["question_type"].strip()

    if label not in LABELS:
        raise ValueError(f"非法标签: {label}")

    return label


def safe_label_item(client: OpenAI, item: Dict[str, Any]) -> Optional[str]:
    stem = extract_text(item)
    if not stem:
        return None

    last_err = None
    for i in range(MAX_RETRY):
        try:
            return call_llm(client, stem)
        except Exception as e:
            last_err = e
            time.sleep(1.2 * (i + 1))

    print(f"[失败] question_id={item.get('question_id')} err={last_err}")
    return None


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请先设置环境变量 OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    done_ids = load_done_ids(OUTPUT_FILE)
    print(f"已存在结果: {len(done_ids)} 条")

    total = 0
    skipped = 0
    success = 0
    failed = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
         open(OUTPUT_FILE, "a", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue

            total += 1
            item = json.loads(line)
            qid = str(item.get("question_id", "")).strip()

            if qid and qid in done_ids:
                skipped += 1
                continue

            label = safe_label_item(client, item)

            new_item = dict(item)
            new_item["question_type_6"] = label
            new_item["question_type_6_method"] = "llm"
            new_item["question_type_6_model"] = MODEL

            if label is None:
                new_item["question_type_6"] = "待复核"
                failed += 1
            else:
                success += 1

            fout.write(json.dumps(new_item, ensure_ascii=False) + "\n")
            fout.flush()

            if total % 20 == 0:
                print(
                    f"processed={total} skipped={skipped} "
                    f"success={success} failed={failed}"
                )

            time.sleep(SLEEP_SEC)

    print("完成")
    print(
        json.dumps(
            {
                "total": total,
                "skipped": skipped,
                "success": success,
                "failed": failed,
                "output": OUTPUT_FILE,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()