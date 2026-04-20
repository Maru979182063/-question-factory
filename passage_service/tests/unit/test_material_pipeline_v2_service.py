from types import SimpleNamespace

from app.domain.services.material_pipeline_v2_service import MaterialPipelineV2Service


class _FakeRegistry:
    def get_question_card(self, card_id: str) -> dict:
        if "center_understanding" in card_id:
            family_id = "center_understanding"
            subtype_id = "center_understanding"
            runtime_binding = {
                "question_type": "main_idea",
                "business_subtype": "center_understanding",
            }
        else:
            family_id = "title_selection"
            subtype_id = "title_selection"
            runtime_binding = {
                "question_type": "main_idea",
                "business_subtype": "title_selection",
            }
        return {
            "card_id": card_id,
            "business_family_id": family_id,
            "business_subtype_id": subtype_id,
            "runtime_binding": runtime_binding,
        }

    def get_default_question_card(self, business_family_id: str) -> dict:
        return self.get_question_card(f"question.{business_family_id}.standard_v1")

    def get_business_cards(self, business_family_id: str, *, runtime_question_type: str | None = None, runtime_business_subtype: str | None = None) -> list[dict]:
        return []


class _FakePipeline:
    INDEX_VERSION = "test-index"

    def __init__(self) -> None:
        self.registry = _FakeRegistry()
        self.rebuild_calls: list[str] = []

    def _selected_task_scoring_for_item(self, *, item: dict, business_family_id: str) -> dict:
        return dict(item.get("selected_task_scoring") or {})

    def refresh_cached_item(self, *, cached_item: dict, query_terms: list[str], target_length, length_tolerance: int, enable_anchor_adaptation: bool, preserve_anchor: bool) -> dict:
        return dict(cached_item)

    def build_cached_item_from_material(self, *, material, article, business_family_id: str, question_card_id: str | None = None, **kwargs) -> dict:
        self.rebuild_calls.append(str(question_card_id))
        return {
            "candidate_id": material.id,
            "article_id": material.article_id,
            "article_title": "rebuilt",
            "text": "rebuilt candidate",
            "original_text": "rebuilt candidate",
            "question_ready_context": {
                "question_card_id": question_card_id,
                "selected_material_card": "title_material.plain_main_recovery",
            },
            "eligible_material_cards": [{"card_id": "title_material.plain_main_recovery", "score": 0.91}],
            "eligible_business_cards": [],
            "business_card_recommendations": [],
            "selected_task_scoring": {
                "task_family": "main_idea",
                "final_candidate_score": 0.62,
                "readiness_score": 0.68,
                "risk_penalties": {"example_dominance_penalty": 0.12},
                "difficulty_vector": {
                    "reasoning_depth_score": 0.61,
                    "ambiguity_score": 0.32,
                },
                "difficulty_band_hint": "medium",
            },
            "quality_score": 0.82,
            "source": {"source_name": "src"},
            "meta": {},
        }

    def _cached_prefilter_sort_key(
        self,
        *,
        cached_item: dict,
        business_family_id: str,
        card_score: float,
        structure_score: float,
        hit_count: int,
        quality_score: float,
    ) -> tuple[int, float, int, float]:
        return (int(card_score), float(structure_score), int(hit_count), float(quality_score))

    def _passes_runtime_material_gate(self, *, item: dict, business_family_id: str, question_card: dict, min_card_score: float, min_business_card_score: float, require_business_card: bool, **kwargs) -> tuple[bool, str]:
        cards = item.get("eligible_material_cards") or []
        top_card_score = float(cards[0].get("score") or 0.0) if cards else 0.0
        if top_card_score < min_card_score:
            return False, "material_card_score_below_threshold"
        return bool(item.get("selected_task_scoring")), ""

    def _select_diverse_items(self, items: list[dict], limit: int) -> list[dict]:
        return items[:limit]


def test_search_cached_rebuilds_question_card_mismatched_cached_item() -> None:
    service = MaterialPipelineV2Service.__new__(MaterialPipelineV2Service)
    service.pipeline = _FakePipeline()
    service.material_repo = SimpleNamespace(
        list_v2_cached=lambda **kwargs: [
            SimpleNamespace(
                id="mat-1",
                article_id="article-1",
                v2_index_payload={
                    "title_selection": {
                        "candidate_id": "mat-1",
                        "article_id": "article-1",
                        "article_title": "stale",
                        "text": "stale candidate",
                        "original_text": "stale candidate",
                        "question_ready_context": {
                            "question_card_id": "question.center_understanding.standard_v1",
                            "selected_material_card": "title_material.problem_essence_judgement",
                        },
                        "eligible_material_cards": [{"card_id": "title_material.problem_essence_judgement", "score": 0.94}],
                        "eligible_business_cards": [],
                        "business_card_recommendations": [],
                        "selected_task_scoring": {},
                        "quality_score": 0.88,
                        "source": {"source_name": "src"},
                        "meta": {},
                    }
                },
                usage_count=0,
                last_used_at=None,
            )
        ]
    )
    service.article_repo = SimpleNamespace(get=lambda article_id: SimpleNamespace(id=article_id))
    service._load_review_status_map = lambda material_ids: {}
    service._apply_review_gate = lambda **kwargs: (kwargs["materials"], {"mode": kwargs["mode"]})
    service._cached_structure_match_score = lambda **kwargs: 1.0
    service._minimum_structure_score = lambda *args, **kwargs: 0.0
    service._refresh_cached_item_for_search = lambda **kwargs: service.pipeline.build_cached_item_from_material(
        material=kwargs["material"],
        article=SimpleNamespace(id=kwargs["material"].article_id),
        business_family_id=kwargs["business_family_id"],
        question_card_id=str(kwargs["question_card"].get("card_id") or "") or None,
    )

    result = service._search_cached(
        {
            "business_family_id": "title_selection",
            "question_card_id": "question.title_selection.standard_v1",
            "candidate_limit": 3,
            "min_card_score": 0.55,
            "min_business_card_score": 0.45,
        }
    )

    assert result is not None
    assert [item["candidate_id"] for item in result["items"]] == ["mat-1"]
    assert result["items"][0]["question_ready_context"]["question_card_id"] == "question.title_selection.standard_v1"
    assert service.pipeline.rebuild_calls == ["question.title_selection.standard_v1"]


def test_search_cached_can_filter_by_shadow_leaf_and_return_shadow_observation() -> None:
    service = MaterialPipelineV2Service.__new__(MaterialPipelineV2Service)
    service.pipeline = _FakePipeline()
    service.material_repo = SimpleNamespace(
        list_v2_cached=lambda **kwargs: [
            SimpleNamespace(
                id="mat-data",
                article_id="article-data",
                v2_index_payload={
                    "center_understanding": {
                        "candidate_id": "mat-data",
                        "article_id": "article-data",
                        "article_title": "data",
                        "text": "实验检测显示，该材料强度高达900兆帕。",
                        "original_text": "实验检测显示，该材料强度高达900兆帕。",
                        "question_ready_context": {
                            "question_card_id": "question.center_understanding.standard_v1",
                            "selected_material_card": "center_material.subsentence_data",
                            "selected_business_card": "parallel_comprehensive_summary__main_idea",
                        },
                        "selected_task_scoring": {"final_candidate_score": 0.72},
                        "eligible_material_cards": [{"card_id": "center_material.subsentence_data", "score": 0.91}],
                        "quality_score": 0.89,
                        "shadow_mount": {
                            "status": "mapped_unique",
                            "child_family_id": "center_understanding_subsentence_features",
                            "selected_leaf_id": "cu_subsentence_data",
                            "shadow_ready": True,
                            "fallback_to_business_card": False,
                            "leaf_trace_version": "leaf_trace.v1",
                        },
                        "source": {"source_name": "src"},
                        "meta": {},
                    }
                },
                usage_count=0,
                last_used_at=None,
            ),
            SimpleNamespace(
                id="mat-turning",
                article_id="article-turning",
                v2_index_payload={
                    "center_understanding": {
                        "candidate_id": "mat-turning",
                        "article_id": "article-turning",
                        "article_title": "turning",
                        "text": "但转折之后，文章把重心落到后段判断。",
                        "original_text": "但转折之后，文章把重心落到后段判断。",
                        "question_ready_context": {
                            "question_card_id": "question.center_understanding.standard_v1",
                            "selected_material_card": "center_material.relation_turning",
                            "selected_business_card": "turning_relation_focus__main_idea",
                        },
                        "selected_task_scoring": {"final_candidate_score": 0.71},
                        "eligible_material_cards": [{"card_id": "center_material.relation_turning", "score": 0.88}],
                        "quality_score": 0.86,
                        "shadow_mount": {
                            "status": "mapped_unique",
                            "child_family_id": "center_understanding_relation_words",
                            "selected_leaf_id": "cu_relation_turning",
                            "shadow_ready": True,
                            "fallback_to_business_card": False,
                            "leaf_trace_version": "leaf_trace.v1",
                        },
                        "source": {"source_name": "src"},
                        "meta": {},
                    }
                },
                usage_count=0,
                last_used_at=None,
            ),
        ]
    )
    service.article_repo = SimpleNamespace(get=lambda article_id: SimpleNamespace(id=article_id))
    service._load_review_status_map = lambda material_ids: {}
    service._apply_review_gate = lambda **kwargs: (kwargs["materials"], {"mode": kwargs["mode"]})
    service._cached_structure_match_score = lambda **kwargs: 1.0
    service._minimum_structure_score = lambda *args, **kwargs: 0.0

    result = service._search_cached(
        {
            "business_family_id": "center_understanding",
            "question_card_id": "question.center_understanding.standard_v1",
            "candidate_limit": 5,
            "status": "gray",
            "release_channel": "gray",
            "shadow_selected_leaf_ids": ["cu_subsentence_data"],
            "include_shadow_observation": True,
            "min_card_score": 0.3,
            "min_business_card_score": 0.25,
        }
    )

    assert result is not None
    assert [item["candidate_id"] for item in result["items"]] == ["mat-data"]
    assert result["items"][0]["shadow_observation"]["selected_leaf_id"] == "cu_subsentence_data"
    assert result["items"][0]["shadow_observation"]["child_family_id"] == "center_understanding_subsentence_features"


def test_observability_reports_shadow_leaf_stats() -> None:
    materials = [
        SimpleNamespace(
            id="mat-data",
            status="gray",
            release_channel="gray",
            usage_count=0,
            quality_score=0.89,
            v2_business_family_ids=["center_understanding"],
            v2_index_version="v2.index.test",
            v2_index_payload={
                "center_understanding": {
                    "text": "实验检测显示，该材料强度高达900兆帕。",
                    "question_ready_context": {
                        "selected_material_card": "center_material.subsentence_data",
                        "selected_business_card": "parallel_comprehensive_summary__main_idea",
                    },
                    "shadow_mount": {
                        "status": "mapped_unique",
                        "child_family_id": "center_understanding_subsentence_features",
                        "selected_leaf_id": "cu_subsentence_data",
                        "shadow_ready": True,
                        "fallback_to_business_card": False,
                        "leaf_trace_version": "leaf_trace.v1",
                    },
                }
            },
        ),
        SimpleNamespace(
            id="mat-turning",
            status="gray",
            release_channel="gray",
            usage_count=1,
            quality_score=0.84,
            v2_business_family_ids=["center_understanding", "title_selection"],
            v2_index_version="v2.index.test",
            v2_index_payload={
                "center_understanding": {
                    "text": "但转折之后，文章把重心落到后段判断。",
                    "question_ready_context": {
                        "selected_material_card": "center_material.relation_turning",
                        "selected_business_card": "turning_relation_focus__main_idea",
                    },
                    "shadow_mount": {
                        "status": "mapped_unique",
                        "child_family_id": "center_understanding_relation_words",
                        "selected_leaf_id": "cu_relation_turning",
                        "shadow_ready": True,
                        "fallback_to_business_card": False,
                        "leaf_trace_version": "leaf_trace.v1",
                    },
                }
            },
        ),
    ]
    service = MaterialPipelineV2Service.__new__(MaterialPipelineV2Service)
    service.session = SimpleNamespace(scalars=lambda stmt: materials)
    service._load_review_status_map = lambda material_ids: {}
    service._apply_review_gate = lambda **kwargs: (kwargs["materials"], {"mode": kwargs["mode"]})

    result = service.observability(
        {
            "business_family_id": "center_understanding",
            "status": "gray",
            "release_channel": "gray",
            "shadow_sample_limit": 2,
        }
    )

    shadow = result["shadow_observability"]
    assert shadow["families_with_selected_leaf_id"]["center_understanding"] == 2
    assert shadow["leaf_counts"]["cu_subsentence_data"] == 1
    assert shadow["leaf_counts"]["cu_relation_turning"] == 1
    assert shadow["mapped_unique_ratio"] == 1.0
    assert shadow["fallback_to_business_card_ratio"] == 0.0
    assert shadow["shadow_ready_ratio"] == 1.0


def test_shadow_search_uses_cached_only_without_article_fallback() -> None:
    service = MaterialPipelineV2Service.__new__(MaterialPipelineV2Service)
    service.pipeline = _FakePipeline()
    cached_result = {
        "items": [{"candidate_id": "mat-shadow", "shadow_observation": {"selected_leaf_id": "cu_relation_turning"}}],
        "warnings": [],
        "article_count": 1,
        "article_ids": ["article-1"],
        "cache_hit": True,
        "index_version": "test-index",
    }
    service._search_cached = lambda payload: dict(cached_result)
    service._apply_external_fallback_if_needed = lambda **kwargs: {"should_not_run": True}

    result = service.shadow_search(
        {
            "business_family_id": "center_understanding",
            "status": "gray",
            "release_channel": "gray",
        }
    )

    assert result["result_mode"] == "shadow_cache_hit"
    assert result["items"][0]["candidate_id"] == "mat-shadow"
    assert "shadow_cache_filters:gray:gray" in result["warnings"]


def test_shadow_search_returns_empty_cache_miss_instead_of_article_pipeline() -> None:
    service = MaterialPipelineV2Service.__new__(MaterialPipelineV2Service)
    service.pipeline = _FakePipeline()
    service._search_cached = lambda payload: None

    result = service.shadow_search(
        {
            "business_family_id": "center_understanding",
            "question_card_id": "question.center_understanding.standard_v1",
            "status": "gray",
            "release_channel": "gray",
        }
    )

    assert result["items"] == []
    assert result["result_mode"] == "shadow_cache_miss"
    assert "shadow_cache_miss:no_indexed_shadow_materials_matched" in result["warnings"]
