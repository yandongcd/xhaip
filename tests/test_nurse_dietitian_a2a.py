"""nurse-general + dietitian A2A contract tests.

Tests each agent's core tools via the A2A dispatcher (import → call → assert).
Tests = nurse-general 6 tools × ≥3 cases + dietitian 6 tools × ≥3 cases + edge cases.
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))

import pytest
from haip.a2a import call, clear_history
from haip.agent import DomainPlugin, ToolDef, _registry, register

_SAVED_REGISTRY: dict = {}


def setup_function():
    global _SAVED_REGISTRY
    _SAVED_REGISTRY = dict(_registry)
    _registry.clear()
    clear_history()


def teardown_function():
    """恢复注册表, 避免清空污染同 worker 后续测试 (如 test_ui_contracts)."""
    _registry.clear()
    _registry.update(_SAVED_REGISTRY)


# ═══════════════════════════════════════════════════════════
# nurse-general A2A tests
# ═══════════════════════════════════════════════════════════

def _register_nurse():
    register(DomainPlugin(name="nurse-general", type="business", tools=[
        ToolDef(name="braden_score", description="", handler="nurse_general.braden_score"),
        ToolDef(name="morse_fall_score", description="", handler="nurse_general.morse_fall_score"),
        ToolDef(name="caprini_dvt", description="", handler="nurse_general.caprini_dvt"),
        ToolDef(name="vte_nursing_bundle", description="", handler="nurse_general.vte_nursing_bundle"),
        ToolDef(name="handover_summary", description="", handler="nurse_general.handover_summary"),
        ToolDef(name="vital_signs_alert", description="", handler="nurse_general.vital_signs_alert"),
    ]))


def _register_dietitian():
    register(DomainPlugin(name="dietitian", type="business", tools=[
        ToolDef(name="nrs2002_screen", description="", handler="dietitian.nrs2002_screen"),
        ToolDef(name="glim_diagnosis", description="", handler="dietitian.glim_diagnosis"),
        ToolDef(name="route_decision", description="", handler="dietitian.route_decision"),
        ToolDef(name="energy_protein_target", description="", handler="dietitian.energy_protein_target"),
        ToolDef(name="refeeding_risk", description="", handler="dietitian.refeeding_risk"),
        ToolDef(name="nutrition_report", description="", handler="dietitian.nutrition_report"),
    ]))


# ── Braden Score ──────────────────────────────────────────────────────────

class TestBradenScore:
    def test_braden_normal(self):
        _register_nurse()
        r = call("nurse-general", "braden_score", {
            "sensory": "未受损", "moisture": "极少潮湿",
            "activity": "经常行走", "mobility": "未受限",
            "nutrition": "极佳", "friction": "无明显问题",
        })
        assert r["status"] == "ok"
        assert r["total_score"] >= 20
        assert r["risk_level"] == "无风险"

    def test_braden_severe(self):
        _register_nurse()
        r = call("nurse-general", "braden_score", {
            "sensory": "完全受限", "moisture": "持续潮湿",
            "activity": "卧床", "mobility": "完全无法移动",
            "nutrition": "严重不足", "friction": "存在问题",
        })
        assert r["status"] == "ok"
        assert r["total_score"] <= 9
        assert r["risk_level"] == "极高危"

    def test_braden_moderate(self):
        _register_nurse()
        r = call("nurse-general", "braden_score", {
            "sensory": "轻度受限", "moisture": "偶尔潮湿",
            "activity": "轮椅", "mobility": "轻度受限",
            "nutrition": "可能不足", "friction": "潜在问题",
        })
        assert r["status"] == "ok"
        assert r["total_score"] == 15
        assert r["risk_level"] == "低危"

    def test_braden_empty_input(self):
        _register_nurse()
        r = call("nurse-general", "braden_score", {})
        assert r["status"] == "ok"
        assert r["total_score"] == 0


# ── Morse Fall Score ──────────────────────────────────────────────────────

class TestMorseFallScore:
    def test_morse_low_risk(self):
        _register_nurse()
        r = call("nurse-general", "morse_fall_score", {
            "fall_history": "无", "secondary_diagnosis": "无",
            "ambulatory_aid": "无/正常", "iv_heparin_lock": "无",
            "gait": "正常/不适用", "mental_status": "正常/知晓活动能力",
        })
        assert r["status"] == "ok"
        assert r["risk_level"] == "低危"

    def test_morse_high_risk(self):
        _register_nurse()
        r = call("nurse-general", "morse_fall_score", {
            "fall_history": "是/近3月有跌倒", "secondary_diagnosis": "≥2个",
            "ambulatory_aid": "扶墙/家具行走", "iv_heparin_lock": "有静脉输液/肝素锁",
            "gait": "异常步态/虚弱", "mental_status": "认知障碍/高估活动能力",
        })
        assert r["status"] == "ok"
        assert r["risk_level"] == "高危"
        assert r["total_score"] > 45

    def test_morse_empty(self):
        _register_nurse()
        r = call("nurse-general", "morse_fall_score", {})
        assert r["status"] == "ok"
        assert r["total_score"] == 0


# ── Caprini DVT ───────────────────────────────────────────────────────────

class TestCapriniDVT:
    def test_caprini_low_young(self):
        _register_nurse()
        r = call("nurse-general", "caprini_dvt", {
            "age": 30, "bmi": 22.0, "surgery_type": "",
            "surgery_duration_min": 0, "conditions": [], "medications": [],
        })
        assert r["status"] == "ok"
        assert r["total_score"] <= 1

    def test_caprini_elderly_hip(self):
        _register_nurse()
        r = call("nurse-general", "caprini_dvt", {
            "age": 78, "bmi": 28.0,
            "surgery_type": "THA", "surgery_duration_min": 90,
            "conditions": ["髋部骨折", "高血压", "糖尿病"],
            "medications": [],
        })
        assert r["status"] == "ok"
        assert r["risk_level"] in ("高危", "极高危")
        assert r["total_score"] >= 5

    def test_caprini_empty(self):
        _register_nurse()
        r = call("nurse-general", "caprini_dvt", {})
        assert r["status"] == "ok"
        assert r["total_score"] == 0
        assert r["risk_level"] == "低危"


# ── VTE Nursing Bundle ────────────────────────────────────────────────────

class TestVTENursingBundle:
    def test_vte_standard(self):
        _register_nurse()
        r = call("nurse-general", "vte_nursing_bundle", {
            "procedure": "THA", "age": 72,
            "conditions": ["高血压", "糖尿病"],
        })
        assert r["status"] == "ok"
        assert len(r["stages"]) == 4
        assert len(r["highlights"]) >= 2

    def test_vte_elderly(self):
        _register_nurse()
        r = call("nurse-general", "vte_nursing_bundle", {
            "procedure": "PFNA", "age": 88,
            "conditions": ["骨质疏松", "认知障碍"],
        })
        assert r["status"] == "ok"
        assert "高龄" in " ".join(r["highlights"])

    def test_vte_empty(self):
        _register_nurse()
        r = call("nurse-general", "vte_nursing_bundle", {})
        assert r["status"] == "ok"
        assert len(r["stages"]) == 4
        assert r["total_checklist_items"] == 27


# ── Handover Summary ──────────────────────────────────────────────────────

class TestHandoverSummary:
    def test_handover_full(self):
        _register_nurse()
        r = call("nurse-general", "handover_summary", {
            "patient_id": "P001", "patient_name": "张三",
            "age": 78, "diagnosis": "左股骨颈骨折 (Garden IV)",
            "current_status": "术后D2, 生命体征平稳, VAS 2分, 伤口干洁",
            "key_events": "D0 THA术后, D1拔尿管, D2下床站立",
            "recommendations": ["继续抗凝 LMWH qd", "防跌倒宣教", "明日查Hb"],
        })
        assert r["status"] == "ok"
        assert "【S — 现状】" in r["sbar_text"]
        assert "【B — 背景】" in r["sbar_text"]
        assert "【A — 评估】" in r["sbar_text"]
        assert "【R — 建议】" in r["sbar_text"]

    def test_handover_minimal(self):
        _register_nurse()
        r = call("nurse-general", "handover_summary", {
            "patient_id": "P002", "patient_name": "李四",
            "age": 45, "diagnosis": "阑尾炎术后",
            "current_status": "术后D1, 已排气, 半流食",
        })
        assert r["status"] == "ok"
        assert "P002" in r["sbar_text"]

    def test_handover_empty(self):
        _register_nurse()
        r = call("nurse-general", "handover_summary", {})
        assert r["status"] == "ok"
        assert "【S — 现状】" in r["sbar_text"]


# ── Vital Signs Alert ─────────────────────────────────────────────────────

class TestVitalSignsAlert:
    def test_vitals_normal(self):
        _register_nurse()
        r = call("nurse-general", "vital_signs_alert", {
            "temperature": 36.5, "pulse": 72,
            "respiration": 16, "systolic_bp": 125,
            "spo2": 98.0, "avpu": "alert",
        })
        assert r["status"] == "ok"
        assert r["ews_total"] == 0
        assert r["escalation_level"] == "routine"

    def test_vitals_critical(self):
        _register_nurse()
        r = call("nurse-general", "vital_signs_alert", {
            "temperature": 35.0, "pulse": 38,
            "respiration": 8, "systolic_bp": 80,
            "spo2": 80.0, "avpu": "u",
        })
        assert r["status"] == "ok"
        assert r["ews_total"] >= 7
        assert r["escalation_level"] == "emergency"

    def test_vitals_moderate(self):
        _register_nurse()
        r = call("nurse-general", "vital_signs_alert", {
            "temperature": 38.2, "pulse": 95,
            "respiration": 22, "systolic_bp": 105,
            "spo2": 91.0, "avpu": "alert",
        })
        assert r["status"] == "ok"
        assert 4 <= r["ews_total"] <= 6

    def test_vitals_empty(self):
        _register_nurse()
        r = call("nurse-general", "vital_signs_alert", {})
        assert r["status"] == "ok"
        assert "ews_total" in r


# ═══════════════════════════════════════════════════════════
# dietitian A2A tests
# ═══════════════════════════════════════════════════════════

# ── NRS2002 ───────────────────────────────────────────────────────────────

class TestNRS2002:
    def test_nrs2002_high_risk(self):
        _register_dietitian()
        r = call("dietitian", "nrs2002_screen", {
            "weight_kg": 42.0, "height_cm": 165.0,
            "age": 75, "disease_severity": 2,
            "food_intake_pct": 30, "weight_loss_3mo_pct": 8.0,
        })
        assert r["status"] == "ok"
        assert r["nrs2002_total"] >= 5
        assert r["risk_level"] == "高"

    def test_nrs2002_low_risk(self):
        _register_dietitian()
        r = call("dietitian", "nrs2002_screen", {
            "weight_kg": 65.0, "height_cm": 170.0,
            "age": 40, "disease_severity": 0,
            "food_intake_pct": 100, "weight_loss_3mo_pct": 0.0,
        })
        assert r["status"] == "ok"
        assert r["risk_level"] == "低"
        assert not r["at_risk"]

    def test_nrs2002_elderly_bonus(self):
        _register_dietitian()
        r = call("dietitian", "nrs2002_screen", {
            "weight_kg": 65.0, "height_cm": 170.0,
            "age": 72, "disease_severity": 1,
            "food_intake_pct": 80, "weight_loss_3mo_pct": 0.0,
        })
        assert r["status"] == "ok"
        assert r["nrs2002_components"]["age_bonus"]["score"] == 1

    def test_nrs2002_empty(self):
        _register_dietitian()
        r = call("dietitian", "nrs2002_screen", {})
        assert r["status"] == "ok"


# ── GLIM ──────────────────────────────────────────────────────────────────

class TestGLIM:
    def test_glim_severe(self):
        _register_dietitian()
        r = call("dietitian", "glim_diagnosis", {
            "weight_loss_6mo_pct": 12.0, "bmi": 15.0,
            "food_intake_week_pct": 30, "disease_burden": "胰腺炎, sepsis",
            "crp": 120.0,
        })
        assert r["status"] == "ok"
        assert r["malnutrition_confirmed"] is True
        assert "重度" in r["diagnosis"]

    def test_glim_negative(self):
        _register_dietitian()
        r = call("dietitian", "glim_diagnosis", {
            "weight_loss_6mo_pct": 0.0, "bmi": 23.0,
            "food_intake_week_pct": 100, "disease_burden": "",
            "crp": 3.0,
        })
        assert r["status"] == "ok"
        assert r["malnutrition_confirmed"] is False

    def test_glim_empty(self):
        _register_dietitian()
        r = call("dietitian", "glim_diagnosis", {})
        assert r["status"] == "ok"
        assert "diagnosis" in r


# ── Route Decision ────────────────────────────────────────────────────────

class TestRouteDecision:
    def test_route_en(self):
        _register_dietitian()
        r = call("dietitian", "route_decision", {
            "gi_function": "正常", "oral_intake_pct": 90,
            "fasting_days": 0, "bowel_obstruction": False,
            "hemodynamic_unstable": False,
        })
        assert r["status"] == "ok"
        assert r["recommended_route"] == "EN"

    def test_route_pn_obstruction(self):
        _register_dietitian()
        r = call("dietitian", "route_decision", {
            "gi_function": "正常", "oral_intake_pct": 0,
            "fasting_days": 0, "bowel_obstruction": True,
            "hemodynamic_unstable": False,
        })
        assert r["status"] == "ok"
        assert r["recommended_route"] == "PN"

    def test_route_hemodynamic_unstable(self):
        _register_dietitian()
        r = call("dietitian", "route_decision", {
            "gi_function": "正常", "oral_intake_pct": 0,
            "fasting_days": 0, "bowel_obstruction": False,
            "hemodynamic_unstable": True,
        })
        assert r["status"] == "ok"
        assert "暂缓" in r["recommended_route"]

    def test_route_spn_partial(self):
        _register_dietitian()
        r = call("dietitian", "route_decision", {
            "gi_function": "部分", "oral_intake_pct": 40,
            "fasting_days": 2, "bowel_obstruction": False,
            "hemodynamic_unstable": False,
        })
        assert r["status"] == "ok"
        assert r["recommended_route"] in ("SPN", "PN")


# ── Energy / Protein ──────────────────────────────────────────────────────

class TestEnergyProtein:
    def test_energy_normal(self):
        _register_dietitian()
        r = call("dietitian", "energy_protein_target", {
            "weight_kg": 70.0, "height_cm": 175.0,
            "age": 45, "gender": "M",
            "activity_factor": 1.2, "stress_factor": 1.0,
            "condition": "",
        })
        assert r["status"] == "ok"
        assert r["bee_kcal"] > 1000
        assert r["tee_kcal"] > 1000

    def test_energy_trauma(self):
        _register_dietitian()
        r = call("dietitian", "energy_protein_target", {
            "weight_kg": 65.0, "height_cm": 160.0,
            "age": 30, "gender": "F",
            "activity_factor": 1.0, "stress_factor": 1.3,
            "condition": "创伤",
        })
        assert r["status"] == "ok"
        assert "创伤" in r["protein_target"]["category"]

    def test_energy_empty(self):
        _register_dietitian()
        r = call("dietitian", "energy_protein_target", {})
        assert r["status"] == "ok"
        assert r["bee_kcal"] > 0


# ── Refeeding ─────────────────────────────────────────────────────────────

class TestRefeeding:
    def test_refeeding_high(self):
        _register_dietitian()
        r = call("dietitian", "refeeding_risk", {
            "bmi": 14.5, "weight_loss_3mo_pct": 18.0,
            "fasting_days": 12,
            "potassium": 3.0, "phosphorus": 0.4, "magnesium": 0.5,
        })
        assert r["status"] == "ok"
        assert r["risk_level"] == "高危"
        assert r["major_count"] >= 1

    def test_refeeding_low(self):
        _register_dietitian()
        r = call("dietitian", "refeeding_risk", {
            "bmi": 24.0, "weight_loss_3mo_pct": 2.0,
            "fasting_days": 1,
            "potassium": 4.5, "phosphorus": 1.4, "magnesium": 1.0,
        })
        assert r["status"] == "ok"
        assert r["risk_level"] == "低危"

    def test_refeeding_empty(self):
        _register_dietitian()
        r = call("dietitian", "refeeding_risk", {})
        assert r["status"] == "ok"
        assert r["risk_level"] == "低危"


# ── Nutrition Report ──────────────────────────────────────────────────────

class TestNutritionReport:
    def test_report_full(self):
        _register_dietitian()
        r = call("dietitian", "nutrition_report", {
            "patient_id": "P001",
            "nrs2002": {"nrs2002_total": 5, "risk_level": "高"},
            "glim": {"diagnosis": "中度营养不良 (Stage 1)"},
            "route": {"recommended_route": "EN"},
            "energy_protein": {
                "energy_target": "1500 - 1800 kcal/d",
                "protein_target": {"g_per_day": "78 - 97.5"},
            },
            "refeeding": {"risk_level": "高危"},
        })
        assert r["status"] == "ok"
        assert "P001" in r["report_text"]
        assert r["critical_count"] >= 2

    def test_report_minimal(self):
        _register_dietitian()
        r = call("dietitian", "nutrition_report", {"patient_id": "P002"})
        assert r["status"] == "ok"
        assert "P002" in r["report_text"]

    def test_report_empty(self):
        _register_dietitian()
        r = call("dietitian", "nutrition_report", {})
        assert r["status"] == "ok"


# ── Edge Cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_nurse_bad_input_types(self):
        """Non-string / None inputs to Braden should degrade gracefully."""
        _register_nurse()
        r = call("nurse-general", "braden_score", {
            "sensory": "", "moisture": "",
        })
        assert r["status"] == "ok"
        assert "total_score" in r

    def test_dietitian_negative_weight(self):
        """Negative weight should not crash."""
        _register_dietitian()
        r = call("dietitian", "nrs2002_screen", {
            "weight_kg": -10.0, "height_cm": 170.0,
        })
        assert r["status"] == "ok"

    def test_vitals_extreme_values(self):
        """Extreme vital signs should not crash."""
        _register_nurse()
        r = call("nurse-general", "vital_signs_alert", {
            "temperature": 42.0, "pulse": 200,
            "respiration": 40, "systolic_bp": 250,
            "spo2": 50.0, "avpu": "p",
        })
        assert r["status"] == "ok"
        assert r["ews_total"] >= 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
