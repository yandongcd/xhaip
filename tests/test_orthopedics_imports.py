"""Orthopedics module import & smoke tests — guards against broken ported imports.

Regression test for the haip-0710 → xhaip migration: every module must import
cleanly and expose its core entry points (broken `agents.domains.haip.*`
imports previously made the whole orthopedics package unimportable).
"""

from __future__ import annotations

import pytest

ORTHO_MODULES = [
    "orthopedics.checklist",
    "orthopedics.clinical",
    "orthopedics.completeness",
    "orthopedics.complication_predictor",
    "orthopedics.extended",
    "orthopedics.fracture_classifier",
    "orthopedics.his_adapter",
    "orthopedics.idata_adapter",
    "orthopedics.mdt",
    "orthopedics.osteoporosis_mgmt",
    "orthopedics.rehab_tracker",
    "orthopedics.surgery_planner",
    "orthopedics.timing_engine",
]

SHARED_MODULES = [
    "shared.assets_loader",
    "shared.ecg_analyzer",
    "shared.guidelines",
    "shared.knowledge",
    "shared.llm_adapter",
    "shared.triage_engine",
    "shared.timing_engine",
]


@pytest.mark.parametrize("module_name", ORTHO_MODULES + SHARED_MODULES)
def test_module_imports(module_name: str) -> None:
    """Every ported module must import without agents.* leftovers."""
    import importlib
    mod = importlib.import_module(module_name)
    assert mod is not None


@pytest.mark.parametrize("module_name", ORTHO_MODULES)
def test_no_legacy_imports(module_name: str) -> None:
    """No module may reference the legacy haip import graph (comments excluded)."""
    import importlib
    import re
    mod = importlib.import_module(module_name)
    src = getattr(mod, "__file__", "")
    with open(src, encoding="utf-8") as f:
        code = f.read()
    legacy_imports = re.findall(r"^\s*(?:from|import)\s+agents[.\s]", code, re.MULTILINE)
    assert not legacy_imports


def test_checklist_generate() -> None:
    from orthopedics.checklist import generate_checklist
    result = generate_checklist("85岁女性髋部骨折，既往高血压、糖尿病、冠心病支架术后，胸闷胸痛2天")
    assert result["triggered_count"] >= 1
    assert "all_items" in result
    assert result["recommendation"]


def test_completeness_check() -> None:
    from orthopedics.completeness import check_test_completeness
    patient = {
        "lab_tests": [{"name": "血常规", "value": 1}, {"name": "肝肾功能", "value": 1}],
        "examinations": [{"name": "心电图", "value": "正常"}],
    }
    result = check_test_completeness(patient)
    assert "completeness_pct" in result
    assert result["total_required"] > 0


def test_timing_engine_v2() -> None:
    from orthopedics.timing_engine import evaluate_timing
    patient = {
        "patient_id": "P-TEST-001",
        "age": 85,
        "diagnosis": "左股骨颈骨折",
        "past_history": "冠心病 支架术后",
        "lab_tests": [{"name": "肌钙蛋白I", "value": 0.5}],
    }
    decision = evaluate_timing(patient)
    assert decision["urgency"] in ("elective", "urgent", "emergency")
    assert "delay_factors" in decision
    assert decision["engine_version"]


def test_fracture_classifier_rule_path() -> None:
    from orthopedics.fracture_classifier import classify_hip_fracture
    result = classify_hip_fracture("左股骨颈骨折", "X线示股骨颈完全移位")
    assert result["fracture_type"] == "股骨颈骨折"
    assert result["phase"] == "preop"
    assert result["classification_system"]


def test_fracture_classifier_postop_redirect() -> None:
    from orthopedics.fracture_classifier import classify_hip_fracture
    result = classify_hip_fracture("股骨颈骨折", "术后X线示内固定位置良好", phase="postop")
    assert result["redirect_to_stage_9"] is True


def test_surgery_planner_template_decision_matrix() -> None:
    from orthopedics.surgery_planner import recommend_surgery
    plan = recommend_surgery(
        {"age": 60, "functional_status": "活跃"},
        {"type": "股骨颈骨折", "classification_type": "Garden II"},
        use_llm=False,
    )
    assert plan["recommended_surgery"]


def test_surgery_planner_llm_fallback_no_key() -> None:
    """With no API key configured, LLM path degrades to the template."""
    from orthopedics.surgery_planner import recommend_surgery
    plan = recommend_surgery(
        {"age": 80, "diagnosis": "股骨转子间骨折"},
        {"type": "股骨转子间骨折"},
        use_llm=True,
    )
    assert plan["recommended_surgery"]


def test_guidelines_available() -> None:
    from shared.guidelines import available_guidelines
    guidelines = available_guidelines()
    assert len(guidelines) > 0
    assert all("name" in g and "path" in g for g in guidelines)


def test_knowledge_check_range_safe() -> None:
    from shared.knowledge import check_range
    assert check_range("葡萄糖", 7.5)["abnormal"] is True
    assert check_range("葡萄糖", 5.0)["abnormal"] is False
    assert check_range("未知指标", 123)["abnormal"] is False
    assert check_range("葡萄糖", None)["abnormal"] is False


def test_assets_loader_loads_rules() -> None:
    from shared.assets_loader import (
        load_completeness_rules,
        load_surgery_type_rules,
        load_timing_rules,
    )
    assert load_completeness_rules().get("required_tests")
    assert load_surgery_type_rules().get("decision_matrix")
    assert load_timing_rules().get("delay_factors")
