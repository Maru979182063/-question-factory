from __future__ import annotations

from collections import Counter
from typing import Any


UNKNOWN_FAMILY_IDS = {"", "unknown", "proto", "new", "word_usage"}


def build_bootstrap_discovery(
    *,
    manifest: dict[str, Any],
    samples: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    candidate_report: dict[str, Any],
    llm_safe_digest: dict[str, Any] | None = None,
    proto_family_label: str | None = None,
    known_family_matched: bool | None = None,
) -> dict[str, Any]:
    signals = collect_bootstrap_signals(
        samples=samples,
        traces=traces,
        candidate_report=candidate_report,
        llm_safe_digest=llm_safe_digest,
    )
    matched = _known_family_matched(
        manifest=manifest,
        signals=signals,
        explicit=known_family_matched,
    )
    proto_family = infer_proto_family(
        manifest=manifest,
        signals=signals,
        proto_family_label=proto_family_label,
        known_family_matched=matched,
    )
    candidate_axes = build_candidate_axes(signals)
    taxonomy = build_distractor_taxonomy(signals)
    anchors = build_evidence_anchors(signals)
    schema_gaps = build_schema_gap_hypotheses(signals=signals, known_family_matched=matched)

    return {
        "discovery_version": "v1",
        "enabled": True,
        "known_family_matched": matched,
        "source": "bootstrap_leaf_discovery",
        "status": "hypothesis_only",
        "promotion_allowed": False,
        "proto_mother_family": proto_family,
        "candidate_axes": candidate_axes,
        "distractor_taxonomy": taxonomy,
        "evidence_anchors": anchors,
        "schema_gap_hypotheses": schema_gaps,
        "difficulty_signals": signals.get("difficulty_signals") or [],
        "next_human_questions": _next_human_questions(proto_family, candidate_axes),
        "limits": [
            "candidate_axes are not fields.",
            "hypothesis is not confirmed.",
            "discovery is not promotion.",
            "proto_mother_family is not a formal mother_family.",
            "This artifact does not confirm formal fields.",
            "This artifact must be followed by axis confirmation before field_candidates can be created.",
        ],
    }


def collect_bootstrap_signals(
    *,
    samples: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    candidate_report: dict[str, Any],
    llm_safe_digest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exam_keywords = _collect_keyword_examples(samples, "exam_points", EXAM_KEYWORDS)
    ask_patterns = _collect_keyword_examples(samples, "stem", ASK_PATTERNS)
    analysis_actions = _collect_keyword_examples(samples, "analysis", ANALYSIS_ACTIONS)
    distractor_markers = _collect_keyword_examples(samples, "analysis", DISTRACTOR_MARKERS)
    behavior_actions = Counter()
    for trace in traces:
        for action in trace.get("observed_actions") or []:
            behavior_actions[str(action.get("action") or "")] += 1

    difficulty_signals = []
    for sample in samples[:20]:
        if sample.get("correct_rate") or sample.get("wrong_option"):
            difficulty_signals.append(
                {
                    "sample_id": str(sample.get("sample_id") or ""),
                    "correct_rate": str(sample.get("correct_rate") or ""),
                    "wrong_option": str(sample.get("wrong_option") or ""),
                }
            )

    return {
        "sample_count": len(samples),
        "field_candidate_count": len(candidate_report.get("field_candidates") or []),
        "behavior_action_count": sum(behavior_actions.values()),
        "exam_keywords": exam_keywords,
        "ask_patterns": ask_patterns,
        "analysis_actions": analysis_actions,
        "distractor_markers": distractor_markers,
        "behavior_actions": [
            {"action": action, "count": count}
            for action, count in behavior_actions.most_common(12)
            if action
        ],
        "difficulty_signals": difficulty_signals,
        "llm_digest_present": bool(llm_safe_digest),
    }


def infer_proto_family(
    *,
    manifest: dict[str, Any],
    signals: dict[str, Any],
    proto_family_label: str | None = None,
    known_family_matched: bool = False,
) -> dict[str, str]:
    mother_family_id = str(manifest.get("mother_family_id") or "")
    leaf_label = str(manifest.get("leaf_label") or "")
    label = proto_family_label or mother_family_id or "proto_unknown"
    if _has_any(signals, ("实词", "词语", "含义", "意思", "指代", "语境", "上下文")) or label == "word_usage":
        description = "词句理解/实词解释类"
        confidence = "medium"
        if not proto_family_label:
            label = mother_family_id or "word_usage"
    elif known_family_matched:
        description = f"Known family matched by existing markers: {mother_family_id}"
        confidence = "medium"
    else:
        description = f"Proto family hypothesis inferred from leaf pack: {leaf_label or label}"
        confidence = "low"
    return {
        "label": label,
        "description": description,
        "confidence": confidence,
        "status": "hypothesis",
    }


def build_candidate_axes(signals: dict[str, Any]) -> list[dict[str, Any]]:
    axes: list[dict[str, Any]] = []
    if _has_any(signals, ("词语", "实词", "含义", "意思", "概念", "术语", "指的是")):
        axes.append(
            _axis(
                axis="explanation_target_type",
                description="题目要求识别被解释对象是词语、短语、概念、术语或语境中的特定指称。",
                values=["word_or_phrase", "concept_term", "contextual_referent"],
                evidence_examples=_examples(signals, "exam_keywords", "ask_patterns"),
                support_estimate=_support_estimate(signals, ("词语", "实词", "含义", "意思", "概念", "指的是")),
                risk="may merge word meaning, concept understanding, and referent resolution into one broad axis",
            )
        )
    if _has_any(signals, ("指代", "指的是", "这个", "就近", "前文", "后文", "对应")):
        axes.append(
            _axis(
                axis="referent_resolution_mode",
                description="题目要求解释词语或短语在上下文中的指代对象或对应内容。",
                values=["near_context_reference", "forward_reference", "backward_reference"],
                evidence_examples=_examples(signals, "ask_patterns", "analysis_actions"),
                support_estimate=_support_estimate(signals, ("指代", "指的是", "这个", "就近", "前文", "后文")),
                risk="may need to split near-reference questions from broader semantic definition questions",
            )
        )
    if _has_any(signals, ("语境", "上下文", "文中", "不是字面", "结合", "联系")):
        axes.append(
            _axis(
                axis="contextual_meaning_mode",
                description="题目要求结合上下文或具体语境解释词语含义，而不是只取字面义。",
                values=["contextual_definition", "semantic_paraphrase", "literal_meaning_rejection"],
                evidence_examples=_examples(signals, "ask_patterns", "analysis_actions"),
                support_estimate=_support_estimate(signals, ("语境", "上下文", "文中", "不是字面", "结合", "联系")),
                risk="may confuse actual solving action with common analysis wording",
            )
        )
    if _has_any(signals, ("范围扩大", "范围缩小", "偷换概念", "无中生有", "概念", "边界")):
        axes.append(
            _axis(
                axis="concept_boundary_mode",
                description="题目要求校正概念边界，排除范围扩大、范围缩小、偷换概念或无中生有的解释。",
                values=["scope_control", "concept_boundary", "unsupported_extension_filter"],
                evidence_examples=_examples(signals, "analysis_actions", "distractor_markers"),
                support_estimate=_support_estimate(signals, ("范围扩大", "范围缩小", "偷换概念", "无中生有", "概念")),
                risk="may overlap with generic option-elimination behavior",
            )
        )
    if _has_any(signals, ("排除", "对应", "无中生有", "并非", "不是", "错误")):
        axes.append(
            _axis(
                axis="option_elimination_mode",
                description="解析中通过选项排除确认语境义或指代对象。",
                values=["unsupported_option_filter", "referent_mismatch_filter", "scope_shift_filter"],
                evidence_examples=_examples(signals, "analysis_actions", "distractor_markers"),
                support_estimate=_support_estimate(signals, ("排除", "对应", "无中生有", "并非", "不是")),
                risk="may be too generic unless tied to word-meaning evidence",
            )
        )
    return axes


def build_distractor_taxonomy(signals: dict[str, Any]) -> list[dict[str, Any]]:
    taxonomy: list[dict[str, Any]] = []
    if _has_any(signals, ("字面", "不是字面")):
        taxonomy.append(_taxonomy("literal_meaning_trap", "把词语字面义当作语境义。", _examples(signals, "analysis_actions")))
    if _has_any(signals, ("范围扩大", "范围缩小")):
        taxonomy.append(_taxonomy("scope_shift", "把语境中的含义范围扩大或缩小。", _examples(signals, "distractor_markers")))
    if _has_any(signals, ("偷换概念", "无中生有", "概念")):
        taxonomy.append(_taxonomy("concept_swap", "用相近概念、无中生有内容或偷换概念干扰。", _examples(signals, "distractor_markers")))
    if _has_any(signals, ("指代", "对应", "前文", "后文", "这个")):
        taxonomy.append(_taxonomy("referent_mismatch", "错配词语在上下文中的指代对象或对应位置。", _examples(signals, "analysis_actions")))
    if _has_any(signals, ("语境", "上下文", "文中", "脱离")):
        taxonomy.append(_taxonomy("context_detached", "脱离上下文语境解释词义。", _examples(signals, "analysis_actions")))
    return taxonomy


def build_evidence_anchors(signals: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for anchor_type, key in (
        ("exam_point_keyword", "exam_keywords"),
        ("question_ask_pattern", "ask_patterns"),
        ("analysis_action_marker", "analysis_actions"),
        ("distractor_marker", "distractor_markers"),
    ):
        examples = _unique_examples(signals.get(key) or [], limit=6)
        if examples:
            anchors.append({"anchor_type": anchor_type, "examples": examples, "status": "hypothesis"})
    return anchors


def build_schema_gap_hypotheses(*, signals: dict[str, Any], known_family_matched: bool) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if not known_family_matched:
        gaps.append(
            {
                "gap": "no_existing_family_marker_space",
                "reason": "known deterministic marker rules did not yield behavior traces or field candidates",
                "status": "hypothesis",
            }
        )
    if signals.get("field_candidate_count") == 0 and build_candidate_axes(signals):
        gaps.append(
            {
                "gap": "candidate_axes_without_confirmed_candidates",
                "reason": "bootstrap discovery found hypothesis axes, but no confirmed candidate fields exist yet",
                "status": "hypothesis",
            }
        )
    return gaps


def _known_family_matched(
    *,
    manifest: dict[str, Any],
    signals: dict[str, Any],
    explicit: bool | None,
) -> bool:
    if explicit is not None:
        return explicit
    mother_family_id = str(manifest.get("mother_family_id") or "").strip()
    if mother_family_id in UNKNOWN_FAMILY_IDS:
        return False
    if int(signals.get("field_candidate_count") or 0) == 0:
        return False
    if int(signals.get("behavior_action_count") or 0) == 0:
        return False
    return True


def _collect_keyword_examples(samples: list[dict[str, Any]], key: str, keywords: tuple[str, ...]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sample in samples:
        text = str(sample.get(key) or "")
        if not text:
            continue
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            results.append(
                {
                    "sample_id": str(sample.get("sample_id") or ""),
                    "keywords": matched[:6],
                    "excerpt": _excerpt(text, matched[0]),
                }
            )
        if len(results) >= 20:
            break
    return results


def _axis(
    *,
    axis: str,
    description: str,
    values: list[str],
    evidence_examples: list[str],
    support_estimate: str,
    risk: str,
) -> dict[str, Any]:
    return {
        "axis": axis,
        "description": description,
        "values": values,
        "evidence_examples": evidence_examples[:6],
        "support_estimate": support_estimate,
        "risk": risk,
        "status": "hypothesis",
    }


def _taxonomy(mode: str, description: str, examples: list[str]) -> dict[str, Any]:
    return {
        "mode": mode,
        "description": description,
        "evidence_examples": examples[:6],
        "status": "hypothesis",
    }


def _next_human_questions(proto_family: dict[str, str], axes: list[dict[str, Any]]) -> list[str]:
    questions = [
        "这些题是在考词语语境义，还是考概念理解？",
        "是否需要把指代解释、术语定义、语境限定拆成不同叶族？",
        "哪些候选轴应该被保留为 seed markers，哪些只是通用解析话术？",
    ]
    if proto_family.get("label"):
        questions.append(f"`{proto_family['label']}` 应该保留、改名、合并、拆分，还是撤销？")
    if axes:
        questions.append("下一轮 axis confirmation 应先验证 support_rate、干扰项解释力和消融问题。")
    return questions


def _has_any(signals: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    haystack = str(signals)
    return any(keyword in haystack for keyword in keywords)


def _examples(signals: dict[str, Any], *keys: str) -> list[str]:
    rows = []
    for key in keys:
        rows.extend(signals.get(key) or [])
    return _unique_examples(rows, limit=6)


def _unique_examples(rows: list[dict[str, Any]], *, limit: int) -> list[str]:
    examples: list[str] = []
    for row in rows:
        excerpt = str(row.get("excerpt") or "").strip()
        if excerpt and excerpt not in examples:
            examples.append(excerpt)
        if len(examples) >= limit:
            break
    return examples


def _support_estimate(signals: dict[str, Any], keywords: tuple[str, ...]) -> str:
    count = 0
    for key in ("exam_keywords", "ask_patterns", "analysis_actions", "distractor_markers"):
        for row in signals.get(key) or []:
            if any(keyword in row.get("keywords", []) for keyword in keywords):
                count += 1
    sample_count = max(1, int(signals.get("sample_count") or 0))
    rate = count / sample_count
    if rate >= 0.6:
        return "high"
    if rate >= 0.2:
        return "medium"
    return "low"


def _excerpt(text: str, marker: str, *, radius: int = 36) -> str:
    cleaned = " ".join(str(text or "").split())
    index = cleaned.find(marker)
    if index < 0:
        return _clip(cleaned, 96)
    start = max(0, index - radius)
    end = min(len(cleaned), index + len(marker) + radius)
    prefix = "..." if start else ""
    suffix = "..." if end < len(cleaned) else ""
    return prefix + cleaned[start:end] + suffix


def _clip(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


EXAM_KEYWORDS = (
    "实词",
    "词语理解",
    "词句理解",
    "含义",
    "意思",
    "指代",
    "概念",
    "解释",
    "语境义",
)

ASK_PATTERNS = (
    "词语在文中的意思",
    "在文中的意思",
    "加点词",
    "指的是",
    "含义",
    "理解正确",
    "理解不正确",
    "解释最贴切",
    "意思是",
)

ANALYSIS_ACTIONS = (
    "联系上下文",
    "结合上下文",
    "结合语境",
    "语境",
    "文中",
    "指代前文",
    "指代后文",
    "就近",
    "前文",
    "后文",
    "不是字面",
    "字面意思",
    "概念解释",
    "对应",
    "排除",
)

DISTRACTOR_MARKERS = (
    "偷换概念",
    "范围扩大",
    "范围缩小",
    "无中生有",
    "并非",
    "不是",
    "字面",
    "对应错误",
    "脱离语境",
)
