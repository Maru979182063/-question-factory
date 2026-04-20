from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.enrich_shadow_mount_tags import LEAF_TRACE_VERSION, SHADOW_VERSION, ShadowMountMapper


def test_shadow_mount_resolves_subsentence_data_leaf_without_alias_only() -> None:
    mapper = ShadowMountMapper()
    item = {
        "text": (
            "长期以来，铜箔在强度、导电性与热稳定性之间存在难以兼得的困境。"
            "实验检测显示，该材料拉伸强度高达900兆帕，导电率保持在90%IACS，"
            "室温放置半年后性能无衰减，成功破解了行业瓶颈。"
        ),
        "question_ready_context": {
            "selected_material_card": "center_material.subsentence_data",
            "selected_business_card": "parallel_comprehensive_summary__main_idea",
            "pattern_candidates": ["whole_passage_integration"],
            "resolved_slots": {},
        },
    }

    shadow = mapper.build_shadow_mount(family="center_understanding", item=item)

    assert shadow["version"] == SHADOW_VERSION
    assert shadow["child_family_id"] == "center_understanding_subsentence_features"
    assert shadow["selected_leaf_id"] == "cu_subsentence_data"
    assert shadow["leaf_trace_version"] == LEAF_TRACE_VERSION
    assert shadow["fallback_to_business_card"] is False
    assert shadow["shadow_ready"] is True
    assert "selected_material_card_exact_match" in (shadow["leaf_trace"]["selected_reason"] or [])
    assert "evidence_chain_language" in str(shadow["leaf_trace"]["candidates"])


def test_shadow_mount_can_shadow_override_parallel_surface_into_subsentence_data() -> None:
    mapper = ShadowMountMapper()
    item = {
        "text": (
            "长期以来，铜箔在强度、导电性与热稳定性之间存在难以兼得的困境。"
            "实验检测显示，该材料拉伸强度高达900兆帕，导电率保持在90%IACS，"
            "室温放置半年后性能无衰减，成功破解了行业瓶颈。"
        ),
        "question_ready_context": {
            "selected_material_card": "center_material.relation_parallel",
            "selected_business_card": "parallel_comprehensive_summary__main_idea",
            "pattern_candidates": ["whole_passage_integration"],
            "resolved_slots": {},
        },
    }

    shadow = mapper.build_shadow_mount(family="center_understanding", item=item)

    assert shadow["child_family_id"] == "center_understanding_subsentence_features"
    assert shadow["selected_leaf_id"] == "cu_subsentence_data"
    assert shadow["shadow_ready"] is True
    assert shadow["semantic_override"]["reason"] == "support_layer_evidence_profile_overrides_parallel_surface"


def test_shadow_mount_keeps_relation_turning_leaf_path_available() -> None:
    mapper = ShadowMountMapper()
    item = {
        "text": "起初人们忽视这一现象，但转折之后，文章把重心落到后段主旨判断上。",
        "question_ready_context": {
            "selected_material_card": "center_material.relation_turning",
            "selected_business_card": "turning_relation_focus__main_idea",
            "pattern_candidates": ["whole_passage_integration"],
            "resolved_slots": {},
        },
    }

    shadow = mapper.build_shadow_mount(family="center_understanding", item=item)

    assert shadow["child_family_id"] == "center_understanding_relation_words"
    assert shadow["selected_leaf_id"] == "cu_relation_turning"
    assert shadow["shadow_ready"] is True
