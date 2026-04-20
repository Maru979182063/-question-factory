from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
PASSAGE_SERVICE_ROOT = ROOT / "passage_service"
REPORTS_ROOT = ROOT / "reports" / "shadow_pilot"
HIERARCHY_PATH = ROOT / "card_specs" / "normalized" / "runtime_mappings" / "distill_family_hierarchy_mapping.yaml"
INDEX_VERSION = "v2.index.manual_shadow.v1"
MANUAL_TRACE_VERSION = "manual_shadow_backfill.v1"

os.chdir(PASSAGE_SERVICE_ROOT)
if str(PASSAGE_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(PASSAGE_SERVICE_ROOT))

from app.core.enums import ArticleStatus  # noqa: E402
from app.domain.services._common import ServiceBase  # noqa: E402
from app.infra.crawl.extractors.readability_extractor import ReadabilityLikeExtractor  # noqa: E402
from app.infra.crawl.fetchers.http_fetcher import HttpCrawlerFetcher  # noqa: E402
from app.infra.db.orm.candidate_span import CandidateSpanORM  # noqa: E402
from app.infra.db.orm.material_span import MaterialSpanORM  # noqa: E402
from app.infra.db.orm.review import TaggingReviewORM  # noqa: E402
from app.infra.db.repositories.utils import new_id  # noqa: E402
from app.infra.db.session import get_session, init_db  # noqa: E402
from app.infra.ingest.cleaners.basic_cleaner import BasicCleaner  # noqa: E402
from app.infra.plugins.loader import load_plugins  # noqa: E402


WORKLOG_PATHS = {
    "center_understanding": ROOT / "reports" / "shadow_pilot" / "manual_leaf_backfill_worklog_2026-04-20.md",
    "sentence_fill": ROOT / "reports" / "shadow_pilot" / "manual_sentence_fill_backfill_worklog_2026-04-20.md",
    "sentence_order": ROOT / "reports" / "shadow_pilot" / "manual_sentence_order_backfill_worklog_2026-04-20.md",
}

QUESTION_CARD_BY_FAMILY = {
    "center_understanding": "question.center_understanding.standard_v1",
    "sentence_fill": "question.sentence_fill.standard_v1",
    "sentence_order": "question.sentence_order.standard_v1",
}

RUNTIME_BINDING_BY_FAMILY = {
    "center_understanding": {"question_type": "main_idea", "business_subtype": "center_understanding"},
    "sentence_fill": {"question_type": "sentence_fill", "business_subtype": None},
    "sentence_order": {"question_type": "sentence_order", "business_subtype": None},
}

CENTER_BUSINESS_CARD_BY_LEAF = {
    "cu_relation_turning": "turning_relation_focus__main_idea",
    "cu_relation_parallel": "parallel_comprehensive_summary__main_idea",
    "cu_relation_countermeasure": "necessary_condition_countermeasure__main_idea",
    "cu_relation_plain": "theme_word_focus__main_idea",
    "cu_relation_variant": "cause_effect__conclusion_focus__main_idea",
    "cu_subsentence_data": "parallel_comprehensive_summary__main_idea",
    "cu_subsentence_example": "theme_word_focus__main_idea",
    "cu_subsentence_prelude": "theme_word_focus__main_idea",
    "cu_subsentence_multi_angle": "parallel_comprehensive_summary__main_idea",
    "cu_subsentence_other": "theme_word_focus__main_idea",
}

MATERIAL_CARD_BY_LEAF = {
    "cu_relation_turning": "center_material.relation_turning",
    "cu_relation_parallel": "center_material.relation_parallel",
    "cu_relation_countermeasure": "center_material.relation_countermeasure",
    "cu_relation_plain": "center_material.relation_plain",
    "cu_relation_variant": "center_material.relation_variant",
    "cu_subsentence_data": "center_material.subsentence_data",
    "cu_subsentence_example": "center_material.subsentence_example",
    "cu_subsentence_prelude": "center_material.subsentence_prelude",
    "cu_subsentence_multi_angle": "center_material.subsentence_multi_angle",
    "cu_subsentence_other": "center_material.subsentence_other",
    "opening_summary": "fill_material.opening_summary",
    "opening_topic_intro": "fill_material.opening_topic_intro",
    "opening_clause_lead": "fill_material.opening_clause_lead",
    "bridge_transition": "fill_material.bridge_transition",
    "middle_focus_shift": "fill_material.middle_focus_shift",
    "middle_explanation": "fill_material.middle_explanation",
    "ending_clause_summary": "fill_material.ending_clause_summary",
    "ending_summary": "fill_material.ending_summary",
    "ending_countermeasure": "fill_material.ending_countermeasure",
    "first_sentence_gate": "order_material.first_sentence_gate",
    "carry_parallel_expand": "order_material.carry_parallel_expand",
    "dual_anchor_lock": "order_material.dual_anchor_lock",
    "timeline_progression": "order_material.timeline_progression",
    "viewpoint_reason_action": "order_material.viewpoint_reason_action",
    "problem_solution_case_blocks": "order_material.problem_solution_case_blocks",
    "sequence_first_sentence_gate": "order_material.first_sentence_gate",
    "sequence_dual_anchor_lock": "order_material.dual_anchor_lock",
    "tail_sentence_gate": "order_material.tail_sentence_gate",
}


@dataclass
class ManualEntry:
    entry_id: str
    mother_family_id: str
    source_site: str
    title: str
    url: str
    find_path: str
    child_family_id: str
    main_leaf: str
    side_hits: list[str]
    truth_fit: str
    status: str
    worklog_path: str


class _ShadowManualWriter(ServiceBase):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.fetcher = HttpCrawlerFetcher()
        self.extractor = ReadabilityLikeExtractor()
        self.cleaner = BasicCleaner()

    def import_entry(self, entry: ManualEntry) -> dict[str, Any]:
        synthetic_url = self._synthetic_source_url(entry)
        existing = self.article_repo.get_by_source_url(synthetic_url)
        if existing is not None:
            return {"status": "exists", "article_id": existing.id, "source_url": synthetic_url}

        html = self.fetcher.fetch_text(entry.url)
        extracted = self.extractor.extract(html, entry.url, {})
        raw_text = str(extracted.get("raw_text") or "").strip()
        cleaned_text = self.cleaner.clean(raw_text)
        manual_excerpt = self._select_manual_excerpt(
            text=cleaned_text or raw_text,
            family=entry.mother_family_id,
            child_family_id=entry.child_family_id,
        )
        if len(manual_excerpt) < 120:
            raise RuntimeError(f"manual excerpt too short for {entry.entry_id}")

        article_title = str(extracted.get("title") or entry.title or "").strip() or entry.title
        article = self.article_repo.create(
            source=f"shadow_manual_backfill::{entry.mother_family_id}",
            source_url=synthetic_url,
            title=article_title,
            raw_text=manual_excerpt,
            clean_text=manual_excerpt,
            language="zh",
            domain=urlparse(entry.url).netloc,
            status=ArticleStatus.CLEANED.value,
            hash=self._manual_hash(entry=entry, text=manual_excerpt),
        )
        candidate = self.candidate_repo.replace_for_article(
            article.id,
            [
                {
                    "start_paragraph": 0,
                    "end_paragraph": max(0, self._paragraph_count(manual_excerpt) - 1),
                    "start_sentence": 0,
                    "end_sentence": max(0, self._sentence_count(manual_excerpt) - 1),
                    "span_type": "manual_shadow_curated",
                    "text": manual_excerpt,
                    "generated_by": "manual_shadow_backfill",
                    "status": "accepted",
                    "segmentation_version": MANUAL_TRACE_VERSION,
                }
            ],
        )[0]

        quality_score = self._quality_score(entry.truth_fit)
        material = self.material_repo.create(
            article_id=article.id,
            candidate_span_id=candidate.id,
            text=manual_excerpt,
            normalized_text_hash=self._normalized_text_hash(manual_excerpt),
            material_family_id=entry.mother_family_id,
            is_primary=True,
            span_type="manual_shadow_curated",
            length_bucket=self._length_bucket(manual_excerpt),
            paragraph_count=self._paragraph_count(manual_excerpt),
            sentence_count=self._sentence_count(manual_excerpt),
            status="gray",
            release_channel="gray",
            gray_ratio=1.0,
            gray_reason="manual_shadow_backfill",
            segmentation_version=MANUAL_TRACE_VERSION,
            tag_version=MANUAL_TRACE_VERSION,
            fit_version=MANUAL_TRACE_VERSION,
            prompt_version=MANUAL_TRACE_VERSION,
            primary_family=entry.mother_family_id,
            primary_subtype=entry.child_family_id,
            secondary_subtypes=list(entry.side_hits),
            universal_profile={},
            family_scores={entry.mother_family_id: quality_score},
            capability_scores={},
            parallel_families=[],
            structure_features={"manual_shadow_backfill": True},
            family_profiles={entry.mother_family_id: {"main_leaf": entry.main_leaf, "truth_fit": entry.truth_fit}},
            subtype_candidates=[entry.main_leaf],
            secondary_candidates=list(entry.side_hits),
            candidate_labels=[entry.main_leaf, entry.child_family_id],
            primary_label=entry.main_leaf,
            decision_trace={"manual_shadow_backfill": self._manual_trace(entry)},
            primary_route={"mode": "manual_shadow_backfill", "main_leaf": entry.main_leaf},
            reject_reason=None,
            variants=[],
            source=self._material_source(entry=entry, article_title=article_title),
            source_tail=entry.url,
            integrity={"mode": "manual_shadow_backfill", "manual_excerpt": True},
            quality_flags=["manual_shadow_backfill", "shadow_only", "shadow_ready_manual"],
            knowledge_tags=[entry.mother_family_id, entry.child_family_id, entry.main_leaf, *entry.side_hits],
            fit_scores={entry.main_leaf: 1.0},
            feature_profile={"manual_shadow_backfill": True},
            quality_score=quality_score,
            v2_index_version=None,
            v2_business_family_ids=[],
            v2_index_payload={},
            usage_count=0,
            accept_count=0,
            reject_count=0,
            last_used_at=None,
        )
        self.review_repo.init_review(material.id, "review_confirmed")

        cached_item = self._build_cached_item(entry=entry, article=article, material=material, article_title=article_title)
        self.material_repo.update_metrics(
            material.id,
            v2_index_version=INDEX_VERSION,
            v2_business_family_ids=[entry.mother_family_id],
            v2_index_payload={entry.mother_family_id: cached_item},
        )
        return {
            "status": "imported",
            "article_id": article.id,
            "material_id": material.id,
            "source_url": synthetic_url,
            "selected_leaf_id": entry.main_leaf,
            "child_family_id": entry.child_family_id,
        }

    @staticmethod
    def _synthetic_source_url(entry: ManualEntry) -> str:
        return f"{entry.url}#shadow-manual-{entry.mother_family_id}-{entry.entry_id}"

    @staticmethod
    def _manual_hash(*, entry: ManualEntry, text: str) -> str:
        payload = f"{entry.mother_family_id}|{entry.entry_id}|{entry.url}|{text}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalized_text_hash(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _paragraph_count(text: str) -> int:
        paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n|\n", text) if segment.strip()]
        return max(1, len(paragraphs))

    @staticmethod
    def _sentence_count(text: str) -> int:
        sentences = [segment.strip() for segment in re.split(r"(?<=[。！？!?；;])\s*", text) if segment.strip()]
        return max(1, len(sentences))

    @staticmethod
    def _length_bucket(text: str) -> str:
        length = len(text)
        if length < 220:
            return "short"
        if length < 520:
            return "medium"
        return "long"

    @staticmethod
    def _quality_score(truth_fit: str) -> float:
        normalized = str(truth_fit or "").strip()
        if "高" in normalized and "中" not in normalized:
            return 0.92
        if normalized in {"中高", "较高"}:
            return 0.88
        if normalized == "中":
            return 0.82
        if normalized in {"中低", "较低"}:
            return 0.74
        return 0.68

    def _select_manual_excerpt(self, *, text: str, family: str, child_family_id: str) -> str:
        normalized = str(text or "").strip()
        if len(normalized) <= 980:
            return normalized
        paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n|\n", normalized) if segment.strip()]
        if not paragraphs:
            paragraphs = [normalized]
        if family == "sentence_fill":
            if child_family_id == "sentence_fill_head_start":
                return self._clip_from_start(paragraphs, limit=720)
            if child_family_id == "sentence_fill_middle":
                return self._clip_from_middle(paragraphs, limit=760)
            return self._clip_from_end(paragraphs, limit=720)
        if family == "sentence_order":
            if child_family_id == "sentence_order_tail_sentence":
                return self._clip_from_end(paragraphs, limit=920)
            if child_family_id == "sentence_order_first_sentence":
                return self._clip_from_start(paragraphs, limit=920)
            return self._clip_from_start(paragraphs, limit=980)
        return self._clip_from_start(paragraphs, limit=980)

    @staticmethod
    def _clip_from_start(paragraphs: list[str], *, limit: int) -> str:
        merged: list[str] = []
        total = 0
        for paragraph in paragraphs:
            if total and total + len(paragraph) > limit:
                break
            merged.append(paragraph)
            total += len(paragraph)
            if total >= limit:
                break
        return "\n\n".join(merged).strip()

    @staticmethod
    def _clip_from_end(paragraphs: list[str], *, limit: int) -> str:
        merged: list[str] = []
        total = 0
        for paragraph in reversed(paragraphs):
            if total and total + len(paragraph) > limit:
                break
            merged.append(paragraph)
            total += len(paragraph)
            if total >= limit:
                break
        return "\n\n".join(reversed(merged)).strip()

    @staticmethod
    def _clip_from_middle(paragraphs: list[str], *, limit: int) -> str:
        if not paragraphs:
            return ""
        mid = len(paragraphs) // 2
        left = mid
        right = mid + 1
        merged: list[str] = []
        total = 0
        while left >= 0 or right < len(paragraphs):
            if left >= 0:
                paragraph = paragraphs[left]
                if not total or total + len(paragraph) <= limit:
                    merged.insert(0, paragraph)
                    total += len(paragraph)
                left -= 1
                if total >= limit:
                    break
            if right < len(paragraphs):
                paragraph = paragraphs[right]
                if total + len(paragraph) <= limit:
                    merged.append(paragraph)
                    total += len(paragraph)
                right += 1
                if total >= limit:
                    break
        return "\n\n".join(merged).strip()

    @staticmethod
    def _manual_trace(entry: ManualEntry) -> dict[str, Any]:
        return {
            "version": MANUAL_TRACE_VERSION,
            "entry_id": entry.entry_id,
            "worklog_path": entry.worklog_path,
            "source_url": entry.url,
            "find_path": entry.find_path,
            "truth_fit": entry.truth_fit,
            "side_hits": list(entry.side_hits),
            "import_mode": "direct_shadow_cached_material",
        }

    @staticmethod
    def _material_source(*, entry: ManualEntry, article_title: str) -> dict[str, Any]:
        return {
            "source_id": "manual_shadow_backfill",
            "source_name": entry.source_site,
            "source_url": entry.url,
            "article_title": article_title,
            "channel": "shadow_manual",
            "manual_backfill": {
                "entry_id": entry.entry_id,
                "mother_family_id": entry.mother_family_id,
                "child_family_id": entry.child_family_id,
                "selected_leaf_id": entry.main_leaf,
                "truth_fit": entry.truth_fit,
                "side_hits": list(entry.side_hits),
                "find_path": entry.find_path,
                "worklog_path": entry.worklog_path,
            },
        }

    def _build_cached_item(self, *, entry: ManualEntry, article, material, article_title: str) -> dict[str, Any]:
        question_card_id = QUESTION_CARD_BY_FAMILY[entry.mother_family_id]
        runtime_binding = dict(RUNTIME_BINDING_BY_FAMILY[entry.mother_family_id])
        selected_material_card = MATERIAL_CARD_BY_LEAF.get(entry.main_leaf, f"manual_shadow.{entry.main_leaf}")
        selected_business_card = self._selected_business_card(entry)
        quality_score = float(material.quality_score or 0.0)
        text_value = str(material.text or "")
        shadow_mount = self._shadow_mount(entry=entry, selected_material_card=selected_material_card, selected_business_card=selected_business_card)
        task_scoring = self._task_scoring(entry=entry, quality_score=quality_score)
        selected_task_scoring = self._selected_task_scoring(task_scoring=task_scoring, family=entry.mother_family_id)
        neutral_signal_profile = self._neutral_signal_profile(entry=entry, quality_score=quality_score)
        paragraph_end = max(0, int(getattr(material, "paragraph_count", 1) or 1) - 1)
        sentence_end = max(0, int(getattr(material, "sentence_count", 1) or 1) - 1)
        article_profile = {
            "document_genre": self._document_genre(entry),
            "article_purpose_frame": "手工筛选",
            "discourse_shape": entry.main_leaf,
            "core_object": article_title,
            "global_main_claim": article_title,
            "closure_score": round(min(0.95, quality_score), 4),
            "context_dependency": self._context_dependency(entry.mother_family_id),
            "paragraph_count": material.paragraph_count,
            "sentence_count": material.sentence_count,
        }
        local_profile = {
            "candidate_type": self._candidate_type(entry.mother_family_id),
            "discourse_shape": entry.main_leaf,
            "context_dependency": self._context_dependency(entry.mother_family_id),
            "closure_score": round(min(0.92, quality_score - 0.04), 4),
            "core_object": article_title,
            "material_structure_label": entry.main_leaf,
            "family_affinity_topk": [{"family_id": entry.mother_family_id, "score": round(quality_score, 4)}],
        }
        business_feature_profile = self._business_feature_profile(entry=entry)
        prompt_extras = {
            "retrieval_mode": "manual_shadow_backfill",
            "manual_shadow_entry_id": entry.entry_id,
            "manual_shadow_leaf_id": entry.main_leaf,
        }
        return {
            "_business_family_id": entry.mother_family_id,
            "_cached_business_family_id": entry.mother_family_id,
            "_cached_index_version": INDEX_VERSION,
            "material_id": material.id,
            "article_id": article.id,
            "article_title": article_title,
            "candidate_id": material.id,
            "candidate_type": self._candidate_type(entry.mother_family_id),
            "text": text_value,
            "consumable_text": text_value,
            "original_text": text_value,
            "quality_score": quality_score,
            "retrieval_match_profile": {
                "query_terms": [],
                "query_hits": [],
                "match_score": 0.0,
                "length_fit_score": 0.0,
                "target_length": None,
                "actual_length": len(text_value),
            },
            "business_card_recommendations": [selected_business_card] if selected_business_card else [],
            "eligible_material_cards": [{"card_id": selected_material_card, "score": round(quality_score, 4)}],
            "material_card_id": selected_material_card,
            "selected_business_card": selected_business_card,
            "preferred_question_cards": [question_card_id],
            "llm_selection_score": round(max(0.6, quality_score - 0.08), 4),
            "llm_generation_readiness": {
                "status": "manual_shadow_ready",
                "score": round(max(0.6, quality_score - 0.04), 4),
                "source": "manual_shadow_backfill",
            },
            "article_profile": article_profile,
            "local_profile": local_profile,
            "neutral_signal_profile": neutral_signal_profile,
            "business_feature_profile": business_feature_profile,
            "task_scoring": task_scoring,
            "selected_task_scoring": selected_task_scoring,
            "source": self._material_source(entry=entry, article_title=article_title),
            "meta": {
                "manual_shadow_backfill": self._manual_trace(entry),
                "precomputed_from_material": True,
                "candidate_span_id": str(getattr(material, "candidate_span_id", "") or ""),
                "paragraph_range": [0, paragraph_end],
                "sentence_range": [0, sentence_end],
                "source_paragraph_range_original": [0, paragraph_end],
                "source_sentence_range_original": [0, sentence_end],
                "anchor_adaptation": {
                    "adapted": False,
                    "preserved_anchor": True,
                    "source_paragraph_range_original": [0, paragraph_end],
                    "source_sentence_range_original": [0, sentence_end],
                },
            },
            "shadow_mount": shadow_mount,
            "question_ready_context": {
                "question_card_id": question_card_id,
                "runtime_binding": runtime_binding,
                "selected_material_card": selected_material_card,
                "selected_business_card": selected_business_card,
                "generation_archetype": entry.main_leaf,
                "resolved_slots": self._resolved_slots(entry),
                "pattern_candidates": [entry.main_leaf],
                "prompt_extras": prompt_extras,
                "validator_contract": {"manual_shadow_backfill": {"enabled": True, "selected_leaf_id": entry.main_leaf}},
                "selected_leaf_id": entry.main_leaf,
                "child_family_id": entry.child_family_id,
                "shadow_status": shadow_mount["status"],
                "leaf_trace_version": shadow_mount["leaf_trace_version"],
                "fallback_to_business_card": False,
                "shadow_ready": True,
                "shadow_mount": shadow_mount,
            },
            "selected_leaf_id": entry.main_leaf,
            "child_family_id": entry.child_family_id,
            "shadow_status": shadow_mount["status"],
            "leaf_trace_version": shadow_mount["leaf_trace_version"],
            "fallback_to_business_card": False,
            "shadow_ready": True,
        }

    def _selected_business_card(self, entry: ManualEntry) -> str:
        if entry.mother_family_id == "center_understanding":
            return CENTER_BUSINESS_CARD_BY_LEAF.get(entry.main_leaf, "theme_word_focus__main_idea")
        if entry.mother_family_id == "sentence_fill":
            return f"sentence_fill__manual_shadow__{entry.main_leaf}"
        if entry.mother_family_id == "sentence_order":
            return f"sentence_order__manual_shadow__{entry.main_leaf}"
        return ""

    @staticmethod
    def _document_genre(entry: ManualEntry) -> str:
        source = str(entry.source_site or "")
        if "科普" in source:
            return "科普说明"
        if "社科" in source:
            return "社科评论"
        if "人民网" in source or "光明" in source:
            return "评论"
        return "手工筛选材料"

    @staticmethod
    def _context_dependency(family: str) -> float:
        if family == "sentence_order":
            return 0.10
        if family == "sentence_fill":
            return 0.14
        return 0.18

    @staticmethod
    def _candidate_type(family: str) -> str:
        return "sentence_block_group" if family == "sentence_order" else "closed_span"

    def _business_feature_profile(self, *, entry: ManualEntry) -> dict[str, Any]:
        if entry.mother_family_id == "sentence_fill":
            blank_position, function_type = self._fill_blank_and_function(entry.main_leaf)
            return {
                "sentence_fill_profile": {
                    "blank_position": blank_position,
                    "function_type": function_type,
                    "explicit_slot_ready": True,
                    "unit_type": "sentence",
                    "logic_relation": function_type,
                    "backward_link_strength": 0.72,
                    "forward_link_strength": 0.72,
                    "bidirectional_validation": 0.72,
                    "reference_dependency": 0.34,
                }
            }
        if entry.mother_family_id == "sentence_order":
            return {
                "sentence_order_profile": {
                    "unit_count": 6,
                    "opening_rule": "explicit_opening",
                    "closing_rule": "summary",
                    "binding_pair_count": 3,
                    "unique_opener_score": 0.78,
                    "exchange_risk": 0.18,
                    "function_overlap_score": 0.12,
                    "multi_path_risk": 0.16,
                    "context_closure_score": 0.76,
                    "sequence_integrity": 0.8,
                }
            }
        return {
            "feature_type": entry.main_leaf,
            "logic_relations": [entry.main_leaf],
            "topic_consistency_strength": 0.82,
            "semantic_completeness_score": 0.82,
            "readability": 0.82,
            "material_structure_label": entry.main_leaf,
        }

    def _neutral_signal_profile(self, *, entry: ManualEntry, quality_score: float) -> dict[str, Any]:
        if entry.mother_family_id == "center_understanding":
            branch_focus = 0.24
            if entry.main_leaf in {"cu_relation_parallel", "cu_subsentence_multi_angle"}:
                branch_focus = 0.38
            elif entry.main_leaf in {"cu_subsentence_other", "cu_subsentence_example"}:
                branch_focus = 0.30
            return {
                "material_structure_label": entry.main_leaf,
                "single_center_strength": round(max(0.78, min(0.92, quality_score)), 4),
                "branch_focus_strength": branch_focus,
                "topic_consistency_strength": round(max(0.72, quality_score - 0.06), 4),
                "summary_strength": round(max(0.64, quality_score - 0.08), 4),
                "closure_score": round(max(0.68, quality_score - 0.04), 4),
                "titleability": round(max(0.58, quality_score - 0.12), 4),
                "analysis_to_conclusion_strength": round(max(0.58, quality_score - 0.10), 4),
                "example_to_theme_strength": 0.62 if entry.main_leaf in {"cu_subsentence_example", "cu_subsentence_other"} else 0.34,
                "context_dependency": self._context_dependency(entry.mother_family_id),
                "task_scoring": self._task_scoring(entry=entry, quality_score=quality_score),
            }
        if entry.mother_family_id == "sentence_fill":
            blank_position, function_type = self._fill_blank_and_function(entry.main_leaf)
            return {
                "material_structure_label": entry.main_leaf,
                "context_dependency": 0.14,
                "summary_strength": round(max(0.58, quality_score - 0.10), 4),
                "closure_score": round(max(0.60, quality_score - 0.10), 4),
                "blank_position": blank_position,
                "function_type": function_type,
                "task_scoring": self._task_scoring(entry=entry, quality_score=quality_score),
            }
        return {
            "material_structure_label": entry.main_leaf,
            "context_dependency": 0.10,
            "opening_anchor_type": "explicit_opening",
            "closing_anchor_type": "summary",
            "opening_signal_strength": round(max(0.60, quality_score - 0.10), 4),
            "closing_signal_strength": round(max(0.60, quality_score - 0.10), 4),
            "local_binding_strength": round(max(0.58, quality_score - 0.12), 4),
            "sequence_integrity": round(max(0.64, quality_score - 0.08), 4),
            "task_scoring": self._task_scoring(entry=entry, quality_score=quality_score),
        }

    def _task_scoring(self, *, entry: ManualEntry, quality_score: float) -> dict[str, Any]:
        if entry.mother_family_id == "center_understanding":
            return {
                "main_idea": {
                    "task_family": "main_idea",
                    "readiness_score": round(max(0.6, quality_score - 0.04), 4),
                    "final_candidate_score": round(max(0.58, quality_score - 0.06), 4),
                    "recommended": True,
                    "needs_review": False,
                    "risk_penalties": {},
                    "difficulty_vector": {
                        "complexity_score": 0.56,
                        "ambiguity_score": 0.28,
                        "reasoning_depth_score": 0.62,
                        "constraint_intensity_score": 0.6,
                    },
                }
            }
        if entry.mother_family_id == "sentence_fill":
            return {
                "sentence_fill": {
                    "task_family": "sentence_fill",
                    "readiness_score": round(max(0.58, quality_score - 0.06), 4),
                    "final_candidate_score": round(max(0.56, quality_score - 0.08), 4),
                    "recommended": True,
                    "needs_review": False,
                    "risk_penalties": {},
                }
            }
        return {
            "sentence_order": {
                "task_family": "sentence_order",
                "readiness_score": round(max(0.58, quality_score - 0.06), 4),
                "final_candidate_score": round(max(0.56, quality_score - 0.08), 4),
                "recommended": True,
                "needs_review": False,
                "risk_penalties": {},
            }
        }

    @staticmethod
    def _selected_task_scoring(*, task_scoring: dict[str, Any], family: str) -> dict[str, Any]:
        if family == "center_understanding":
            return dict(task_scoring.get("main_idea") or {})
        if family == "sentence_fill":
            return dict(task_scoring.get("sentence_fill") or {})
        if family == "sentence_order":
            return dict(task_scoring.get("sentence_order") or {})
        return {}

    def _shadow_mount(self, *, entry: ManualEntry, selected_material_card: str, selected_business_card: str) -> dict[str, Any]:
        return {
            "version": "shadow_mount.manual_backfill.v1",
            "mount_source": "manual_shadow_backfill",
            "mother_family_id": entry.mother_family_id,
            "runtime_selected_material_card": selected_material_card,
            "runtime_selected_business_card": selected_business_card,
            "child_family_id": entry.child_family_id,
            "status": "manual_curated",
            "child_family_candidates": [entry.child_family_id],
            "expected_material_card_id": selected_material_card,
            "selected_leaf_id": entry.main_leaf,
            "leaf_trace_version": MANUAL_TRACE_VERSION,
            "fallback_to_business_card": False,
            "shadow_ready": True,
            "leaf_trace": {
                "resolver": "manual_shadow_backfill",
                "family": entry.mother_family_id,
                "child_family_id": entry.child_family_id,
                "selected_leaf_id": entry.main_leaf,
                "side_hits": list(entry.side_hits),
                "truth_fit": entry.truth_fit,
                "find_path": entry.find_path,
            },
            "manual_side_hits": list(entry.side_hits),
            "manual_truth_fit": entry.truth_fit,
        }

    def _resolved_slots(self, entry: ManualEntry) -> dict[str, Any]:
        if entry.mother_family_id == "sentence_fill":
            blank_position, function_type = self._fill_blank_and_function(entry.main_leaf)
            return {
                "blank_position": blank_position,
                "function_type": function_type,
                "manual_shadow_leaf_id": entry.main_leaf,
            }
        if entry.mother_family_id == "sentence_order":
            return {
                "candidate_type": "sentence_block_group",
                "manual_shadow_leaf_id": entry.main_leaf,
            }
        return {
            "structure_type": entry.main_leaf,
            "main_axis_source": "manual_shadow_backfill",
            "manual_shadow_leaf_id": entry.main_leaf,
        }

    @staticmethod
    def _fill_blank_and_function(leaf_id: str) -> tuple[str, str]:
        mapping = {
            "opening_summary": ("opening", "summary"),
            "opening_topic_intro": ("opening", "topic_intro"),
            "opening_clause_lead": ("opening", "topic_intro"),
            "bridge_transition": ("middle", "bridge"),
            "middle_focus_shift": ("middle", "lead_next"),
            "middle_explanation": ("middle", "carry_previous"),
            "ending_clause_summary": ("ending", "conclusion"),
            "ending_summary": ("ending", "conclusion"),
            "ending_countermeasure": ("ending", "countermeasure"),
        }
        return mapping.get(leaf_id, ("middle", "bridge"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import hand-curated manual backfill samples into shadow DB as indexed manual materials.")
    parser.add_argument(
        "--families",
        nargs="+",
        default=["center_understanding", "sentence_fill", "sentence_order"],
        choices=["center_understanding", "sentence_fill", "sentence_order"],
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on imported entries; 0 means all.")
    parser.add_argument("--report-path", type=str, default="", help="Optional fixed markdown report path.")
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _infer_center_child_family(leaf_id: str) -> str:
    if leaf_id.startswith("cu_relation_"):
        return "center_understanding_relation_words"
    return "center_understanding_subsentence_features"


def _parse_worklog_entries(*, family: str, worklog_path: Path) -> list[ManualEntry]:
    text = worklog_path.read_text(encoding="utf-8-sig")
    chunks = text.split("### Entry ")
    entries: list[ManualEntry] = []
    for raw_chunk in chunks[1:]:
        chunk = raw_chunk.strip()
        if not chunk:
            continue
        entry_id = chunk.splitlines()[0].strip()

        def extract(key: str) -> str:
            match = re.search(rf"- `{re.escape(key)}`:\s*(.+)", chunk)
            return str(match.group(1)).strip() if match else ""

        status = extract("status")
        if status not in {"keep", "keep_with_windowing"}:
            continue
        title = extract("title")
        url = extract("url")
        main_leaf = extract("main_leaf").strip("`")
        if not title or not url or not main_leaf:
            continue
        child_family_id = extract("child_family").strip("`")
        if not child_family_id and family == "center_understanding":
            child_family_id = _infer_center_child_family(main_leaf)
        side_hits_raw = extract("side_hits")
        side_hits = [token.strip().strip("`") for token in side_hits_raw.split(",") if token.strip() and token.strip() != "[]"]
        entries.append(
            ManualEntry(
                entry_id=entry_id,
                mother_family_id=family,
                source_site=extract("source_site"),
                title=title,
                url=url,
                find_path=extract("find_path"),
                child_family_id=child_family_id,
                main_leaf=main_leaf,
                side_hits=side_hits,
                truth_fit=extract("truth_fit"),
                status=status,
                worklog_path=str(worklog_path),
            )
        )
    return entries


def load_manual_entries(families: list[str]) -> list[ManualEntry]:
    entries: list[ManualEntry] = []
    hierarchy = _load_yaml(HIERARCHY_PATH)
    allowed_child_ids = {
        family: set(((hierarchy.get("mother_families") or {}).get(family) or {}).get("child_family_ids") or [])
        for family in families
    }
    for family in families:
        worklog_path = WORKLOG_PATHS[family]
        family_entries = _parse_worklog_entries(family=family, worklog_path=worklog_path)
        for entry in family_entries:
            if entry.child_family_id and allowed_child_ids.get(family) and entry.child_family_id not in allowed_child_ids[family]:
                raise RuntimeError(f"entry {entry.entry_id} child_family_id not allowed for {family}: {entry.child_family_id}")
        entries.extend(family_entries)
    return entries


def write_report(*, report_path: Path, summary: dict[str, Any], results: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    lines = [
        "# Manual Shadow Backfill Import Report",
        "",
        f"- run_at: `{summary['run_at']}`",
        f"- imported_count: `{summary['imported_count']}`",
        f"- existing_count: `{summary['existing_count']}`",
        f"- failed_count: `{summary['failed_count']}`",
        f"- families: `{summary['families']}`",
        "",
        "## Imported",
    ]
    for item in results[:200]:
        lines.append(
            f"- `{item.get('entry_id')}` {item.get('mother_family_id')} / {item.get('selected_leaf_id')} -> "
            f"`{item.get('material_id')}`"
        )
    if failures:
        lines.extend(["", "## Failures"])
        for item in failures[:200]:
            lines.append(f"- `{item.get('entry_id')}` {item.get('url')}: {item.get('error')}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    init_db()
    load_plugins()
    entries = load_manual_entries(args.families)
    if args.limit > 0:
        entries = entries[: args.limit]

    session = get_session()
    writer = _ShadowManualWriter(session)
    imported: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    existing_count = 0
    imported_count = 0

    for entry in entries:
        try:
            result = writer.import_entry(entry)
            result["entry_id"] = entry.entry_id
            result["mother_family_id"] = entry.mother_family_id
            if result.get("status") == "exists":
                existing_count += 1
            else:
                imported_count += 1
            imported.append(result)
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "entry_id": entry.entry_id,
                    "mother_family_id": entry.mother_family_id,
                    "main_leaf": entry.main_leaf,
                    "url": entry.url,
                    "error": str(exc),
                }
            )
            session.rollback()

    summary = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "families": args.families,
        "imported_count": imported_count,
        "existing_count": existing_count,
        "failed_count": len(failures),
    }
    report_path = (
        Path(args.report_path)
        if args.report_path
        else REPORTS_ROOT / f"manual_shadow_backfill_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    write_report(report_path=report_path, summary=summary, results=imported, failures=failures)
    print(f"report_path={report_path}")
    print(f"imported_count={imported_count}")
    print(f"existing_count={existing_count}")
    print(f"failed_count={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
