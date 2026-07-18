"""脊柱骨科 + 关节与骨病外科 — A2A 集成测试.

覆盖:
  - spine-surgery: asia_classification, cobb_severity, stenosis_assessment,
    odi_score, surgical_pathway, red_flags
  - joint-surgery: harris_hip_score, kss_score, pji_diagnosis,
    tha_tka_planning, eras_pathway, revision_assessment
"""

from __future__ import annotations

import importlib
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from haip.agent import _registry, DomainPlugin, ToolDef, register
from haip.a2a import call, clear_history

SPINE_TOOLS = [
    ToolDef(name="asia_classification", description="",
            handler="spine_surgery.asia_classification"),
    ToolDef(name="cobb_severity", description="",
            handler="spine_surgery.cobb_severity"),
    ToolDef(name="stenosis_assessment", description="",
            handler="spine_surgery.stenosis_assessment"),
    ToolDef(name="odi_score", description="",
            handler="spine_surgery.odi_score"),
    ToolDef(name="surgical_pathway", description="",
            handler="spine_surgery.surgical_pathway"),
    ToolDef(name="red_flags", description="",
            handler="spine_surgery.red_flags"),
]

JOINT_TOOLS = [
    ToolDef(name="harris_hip_score", description="",
            handler="joint_surgery.harris_hip_score"),
    ToolDef(name="kss_score", description="",
            handler="joint_surgery.kss_score"),
    ToolDef(name="pji_diagnosis", description="",
            handler="joint_surgery.pji_diagnosis"),
    ToolDef(name="tha_tka_planning", description="",
            handler="joint_surgery.tha_tka_planning"),
    ToolDef(name="eras_pathway", description="",
            handler="joint_surgery.eras_pathway"),
    ToolDef(name="revision_assessment", description="",
            handler="joint_surgery.revision_assessment"),
]


def setup_function():
    _registry.clear()
    clear_history()


# ═══════════════════════════════════════════════════════════
# spine-surgery A2A 测试
# ═══════════════════════════════════════════════════════════

class TestSpineA2A:
    """spine-surgery 6 工具 A2A 集成测试."""

    def test_asia_classification_grade_a(self):
        """ASIA A级 — 完全损伤, 无骶段保留."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "asia_classification", {
            "motor_level": "C6", "sensory_level": "C6",
            "motor_scores": {"c5": 3, "c6": 1, "c7": 0, "c8": 0, "t1": 0,
                             "l2": 0, "l3": 0, "l4": 0, "l5": 0, "s1": 0},
            "sacral_sparing": False, "anal_contraction": False,
        })
        assert r["status"] == "ok"
        assert r["asia_grade"] == "A"
        assert r["completeness"] == "完全性"

    def test_asia_classification_grade_d(self):
        """ASIA D级 — 不完全损伤, 保留骶段, 肌力大部分≥3级."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "asia_classification", {
            "motor_level": "L3", "sensory_level": "L2",
            "motor_scores": {"c5": 5, "c6": 5, "c7": 5, "c8": 5, "t1": 5,
                             "l2": 5, "l3": 4, "l4": 4, "l5": 4, "s1": 4},
            "sacral_sparing": True, "anal_contraction": True,
        })
        assert r["status"] == "ok"
        assert r["asia_grade"] == "D"
        assert r["completeness"] == "不完全性"

    def test_cobb_severity_moderate_bracing(self):
        """Cobb 角度 35° + Risser 2 → 中度侧弯, 支具治疗."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "cobb_severity", {
            "cobb_angle": 35, "risser_grade": 2, "age": 14,
            "curve_type": "thoracic", "progression_risk": "medium",
        })
        assert r["status"] == "ok"
        assert r["grade"] == "moderate"
        assert "支具" in r["treatment"]

    def test_cobb_severity_severe_surgery(self):
        """Cobb 50° → 重度侧弯, 手术指征."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "cobb_severity", {
            "cobb_angle": 50, "risser_grade": 4, "age": 16,
            "curve_type": "thoracic", "progression_risk": "high",
        })
        assert r["status"] == "ok"
        assert r["grade"] == "severe"
        assert len(r["surgery_indications"]) >= 1

    def test_stenosis_assessment_severe(self):
        """神经源性跛行 + 步行<50m + Schizas C → 重度."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "stenosis_assessment", {
            "symptoms": ["神经源性跛行", "根性痛"],
            "walking_distance_m": 30, "schizas_grade": "C",
            "segment_level": "L4-L5", "central_stenosis": True,
            "foraminal_stenosis": False, "age": 68,
        })
        assert r["status"] == "ok"
        assert r["severity"] == "重度"

    def test_stenosis_assessment_mild(self):
        """步行>500m, 无Schizas分级 → 轻度/保守治疗."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "stenosis_assessment", {
            "symptoms": [], "walking_distance_m": 600,
            "schizas_grade": "", "segment_level": "L3-L4",
            "central_stenosis": False, "foraminal_stenosis": False, "age": 45,
        })
        assert r["status"] == "ok"
        assert r["severity"] in ("极轻度/无症状", "轻度")

    def test_odi_score_moderate(self):
        """ODI 各项均有分值 → 中度功能障碍."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        scores = {}
        for item_id in ["pain_intensity", "personal_care", "lifting", "walking",
                          "sitting", "standing", "sleeping", "sex_life",
                          "social_life", "traveling"]:
            scores[item_id] = 3
        r = call("spine-surgery", "odi_score", {"scores": scores})
        assert r["status"] == "ok"
        assert r["odi_pct"] == 60.0
        assert r["grade"] == "重度功能障碍"

    def test_odi_score_empty_returns_error(self):
        """空 scores → 异常输入."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "odi_score", {"scores": {}})
        assert r["status"] == "error"

    def test_surgical_pathway_peld(self):
        """腰椎间盘突出 L5-S1 → PELD."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "surgical_pathway", {
            "diagnosis": "腰椎间盘突出", "segment": "L5-S1",
            "t_score": -0.5, "age": 35, "multi_level": False,
            "instability": False, "prior_surgery": False,
        })
        assert r["status"] == "ok"
        assert r["primary_procedure"] == "peld"

    def test_surgical_pathway_open_multilevel(self):
        """多节段椎管狭窄 → 开放手术."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "surgical_pathway", {
            "diagnosis": "椎管狭窄", "segment": "L3-S1",
            "t_score": -2.0, "age": 72, "multi_level": True,
            "instability": True, "prior_surgery": False,
        })
        assert r["status"] == "ok"
        assert r["primary_procedure"] == "open"

    def test_red_flags_cauda_equina(self):
        """马尾综合征 → 急诊升级."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "red_flags", {
            "patient_id": "P_SPINE_001",
            "symptoms": ["急性尿潴留", "鞍区麻木", "进行性下肢无力"],
            "history": [], "age": 45,
            "lab_crp": 5, "lab_esr": 15,
        })
        assert r["status"] == "ok"
        assert r["emergency_upgrade"] is True
        assert any("马尾" in f["category"] for f in r["flags"])

    def test_red_flags_no_hits(self):
        """无红旗征命中."""
        register(DomainPlugin(name="spine-surgery", type="business", tools=SPINE_TOOLS))
        r = call("spine-surgery", "red_flags", {
            "patient_id": "P_SPINE_002",
            "symptoms": ["腰背痛 (活动后加重)"], "history": [],
            "age": 35, "lab_crp": 3, "lab_esr": 10,
        })
        assert r["status"] == "ok"
        assert r["emergency_upgrade"] is False


# ═══════════════════════════════════════════════════════════
# joint-surgery A2A 测试
# ═══════════════════════════════════════════════════════════

class TestJointA2A:
    """joint-surgery 6 工具 A2A 集成测试."""

    def test_harris_hip_score_excellent(self):
        """无痛+功能完全 → 优 (≥90)."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "harris_hip_score", {
            "pain_level": "none", "gait": "无跛行", "support": "无",
            "walking_distance": "不受限", "stairs": "正常上下楼",
            "sitting": "舒适坐1h+", "shoes_socks": "容易",
            "public_transport": "可乘公交",
        })
        assert r["status"] == "ok"
        assert r["total_score"] >= 90
        assert "优" in r["grade"]

    def test_harris_hip_score_poor(self):
        """重度疼痛+双拐 → 差."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "harris_hip_score", {
            "pain_level": "severe", "gait": "重度跛行", "support": "双拐",
            "walking_distance": "0.3-0.8km", "stairs": "困难",
            "sitting": "舒适坐30min", "shoes_socks": "困难",
            "public_transport": "不能乘公交",
        })
        assert r["status"] == "ok"
        assert r["total_score"] < 70

    def test_kss_score_good(self):
        """中度疼痛 + 好ROM → 良."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "kss_score", {
            "pain": 35, "rom_degrees": 110,
            "mediolateral_stability_mm": 3, "anteroposterior_stability_mm": 3,
            "flexion_contracture_deg": 0, "extensor_lag_deg": 0,
            "alignment_degrees": 3, "walk_blocks": 7,
            "stairs_up_down": 30, "walking_aid": "none",
        })
        assert r["status"] == "ok"
        assert r["clinical_score"] >= 70
        assert "良" in r["clinical_grade"]

    def test_kss_score_with_deductions(self):
        """屈曲挛缩20°+伸膝迟滞15° → 扣减."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "kss_score", {
            "pain": 30, "rom_degrees": 90,
            "mediolateral_stability_mm": 3, "anteroposterior_stability_mm": 3,
            "flexion_contracture_deg": 20, "extensor_lag_deg": 15,
            "alignment_degrees": 3, "walk_blocks": 3,
            "stairs_up_down": 10, "walking_aid": "single_cane",
        })
        assert r["status"] == "ok"
        assert r["clinical_score"] < 80

    def test_pji_diagnosis_major_sinus(self):
        """窦道 → 直接判定感染 (主要标准)."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "pji_diagnosis", {
            "sinus_tract": True, "positive_cultures": 0,
            "same_organism": False, "crp": 5, "esr": 20,
            "synovial_wbc": 2000, "pmn_pct": 60,
            "alpha_defensin_positive": False,
            "frozen_section_positive": False,
            "intraop_purulence": False, "d_dimer": 500,
        })
        assert r["status"] == "ok"
        assert r["diagnosis"] == "感染 (Confirmed Infection)"
        assert r["major_criteria_hit"] is True

    def test_pji_diagnosis_minor_infected(self):
        """次要标准累计 ≥6 分 → 感染."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "pji_diagnosis", {
            "sinus_tract": False, "positive_cultures": 0,
            "same_organism": False, "crp": 15, "esr": 35,
            "synovial_wbc": 5000, "pmn_pct": 85,
            "alpha_defensin_positive": True,
            "frozen_section_positive": False,
            "intraop_purulence": False, "d_dimer": 900,
        })
        assert r["status"] == "ok"
        assert r["minor_score"] >= 6
        assert "感染" in r["diagnosis"]

    def test_pji_diagnosis_not_infected(self):
        """全阴性 → 排除感染."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "pji_diagnosis", {
            "sinus_tract": False, "positive_cultures": 0,
            "same_organism": False, "crp": 5, "esr": 15,
            "synovial_wbc": 1500, "pmn_pct": 50,
            "alpha_defensin_positive": False,
            "frozen_section_positive": False,
            "intraop_purulence": False, "d_dimer": 400,
        })
        assert r["status"] == "ok"
        assert r["minor_score"] < 2
        assert "未感染" in r["diagnosis"]

    def test_tha_tka_planning_hip(self):
        """髋关节置换术前规划 — 骨关节炎."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "tha_tka_planning", {
            "joint": "hip", "diagnosis": "晚期骨关节炎",
            "age": 68, "bmi": 26, "infection_risk": "low",
            "bone_quality": "osteopenia", "deformity_degree": "轻度",
            "prior_surgery": False,
        })
        assert r["status"] == "ok"
        assert "THA" in r["procedure"]
        assert r["cleared_for_surgery"] is True

    def test_tha_tka_planning_invalid_joint(self):
        """无效关节类型 → error."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "tha_tka_planning", {
            "joint": "shoulder", "diagnosis": "骨关节炎",
            "age": 60, "bmi": 25, "infection_risk": "low",
            "bone_quality": "normal", "deformity_degree": "轻度",
            "prior_surgery": False,
        })
        assert r["status"] == "error"

    def test_eras_pathway_tha(self):
        """THA ERAS 路径 — 完整 phases."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "eras_pathway", {
            "procedure": "THA", "patient_id": "P_JT_001",
            "age": 65, "comorbidities": ["糖尿病"], "current_phase": "preop",
        })
        assert r["status"] == "ok"
        assert "preop_day1" in r["phases"]
        assert "discharge" in r["phases"]
        assert len(r["high_risk_modifications"]) >= 1

    def test_revision_assessment_septic(self):
        """CRP/ESR 升高 + 松动 → 感染性松动, 二期翻修."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "revision_assessment", {
            "joint": "hip", "issue_type": "loosening",
            "lab_crp": 15, "lab_esr": 45,
            "symptoms": ["静息痛", "夜间痛"],
            "xray_findings": ["假体周围透亮线"],
            "prior_revision_count": 0,
        })
        assert r["status"] == "ok"
        assert r["infection_likely"] is True
        assert any("二期" in plan for plan in r["revision_plan"])

    def test_revision_assessment_aseptic_wear(self):
        """聚乙烯磨损 → 更换内衬."""
        register(DomainPlugin(name="joint-surgery", type="business", tools=JOINT_TOOLS))
        r = call("joint-surgery", "revision_assessment", {
            "joint": "knee", "issue_type": "wear",
            "lab_crp": 3, "lab_esr": 10,
            "symptoms": ["活动时疼痛"],
            "xray_findings": ["关节间隙不对称变窄"],
            "prior_revision_count": 0,
        })
        assert r["status"] == "ok"
        assert r["infection_likely"] is False
        assert any("内衬" in plan for plan in r["revision_plan"])
