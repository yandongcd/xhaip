"""Phase 0' 测试: 新 Agent 核心功能验证.

验证: anesthesia / infection-control / emergency-triage / pc-aki / fall-prevention
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT / "packages" / "haip-hospital"))

import pytest

# ── anesthesia ──


def test_anesthesia_asa_assessment():
    from modules.anesthesia import asa_assessment
    result = asa_assessment(patient_id="P001")
    assert result["status"] == "ok"
    assert "summary" in result


def test_anesthesia_anticoagulation():
    from modules.anesthesia import anticoagulation_bridge
    result = anticoagulation_bridge(patient_id="P001")
    assert result["status"] == "ok"


# ── infection-control ──


def test_infection_control_mdro():
    from modules.infection_control import mdro_surveillance
    result = mdro_surveillance(time_range="7d", department="ICU")
    assert result["status"] == "ok"
    assert "MDRO" in result["summary"]


def test_infection_control_outbreak():
    from modules.infection_control import outbreak_detection
    result = outbreak_detection(cases=[1, 2, 3], time_window=7)
    assert result["status"] == "ok"
    assert "橙色预警" in result["summary"] or "暴发" in str(result)


# ── emergency-triage ──


def test_emergency_triage_level_i():
    from modules.emergency_triage import triage_assess
    result = triage_assess(
        patient_id="P001",
        chief_complaint="胸痛大汗呼吸困难",
        vital_signs={"SpO2": 82, "SBP": 70},
    )
    assert result["status"] == "ok"


def test_emergency_red_flags():
    from modules.emergency_triage import red_flag_detect
    result = red_flag_detect(
        patient_id="P001",
        chief_complaint="突发右侧肢体无力口角歪斜言语不清",
        vital_signs={"SpO2": 96, "SBP": 145},
    )
    assert result["red_flags"] is not None


def test_emergency_green_channel():
    from modules.emergency_triage import green_channel_check
    result = green_channel_check(
        patient_id="P001",
        chief_complaint="胸痛大汗2小时",
        red_flags=[{"flag": "胸痛_ACS", "matched": 3}],
    )
    assert "胸痛中心" in str(result["channels"])


# ── pc-aki ──


def test_pc_aki_risk_screen():
    from modules.pc_aki import risk_screen
    result = risk_screen(patient_id="P001")
    assert result["status"] == "ok"


def test_pc_aki_renal_assess():
    from modules.pc_aki import renal_assess
    result = renal_assess(patient_id="P001", pre_creatinine=88, post_creatinine=100)
    assert result["status"] == "ok"
    assert "eGFR" in str(result.get("findings", ""))


# ── fall-prevention ──


def test_fall_morse_assess():
    from modules.fall_prevention import morse_assess
    result = morse_assess(patient_id="P001")
    assert result["status"] == "ok"


def test_fall_prevention_plan():
    from modules.fall_prevention import prevention_plan
    result = prevention_plan(patient_id="P001", morse_score=50, risk_level="高危")
    assert result["status"] == "ok"
    assert "高危" in result.get("risk_level", "")


def test_fall_postop_check():
    from modules.fall_prevention import postop_check
    result = postop_check(patient_id="P001", surgery_date="2026-07-26", anesthesia_type="全麻")
    assert result["status"] == "ok"


# ── hip-fracture-mdt ──


def test_hip_fracture_classify():
    from modules.hip_fracture_mdt import fracture_classify
    result = fracture_classify(patient_id="P001", xray_findings="Garden III 股骨颈骨折")
    assert result["status"] == "ok"
    assert "Garden" in str(result.get("findings", "")) or "分型" in result.get("summary", "")


def test_hip_fracture_timing():
    from modules.hip_fracture_mdt import surgical_timing
    result = surgical_timing(patient_id="P001")
    assert result["status"] == "ok"


def test_hip_fracture_mdt_coordinate():
    from modules.hip_fracture_mdt import mdt_coordinate
    result = mdt_coordinate(patient_id="P001", question="老年髋部骨折围术期评估")
    assert result["status"] == "ok"


def test_hip_fracture_perioperative():
    from modules.hip_fracture_mdt import perioperative_plan
    result = perioperative_plan(patient_id="P001", fracture_type="Garden III", asa_level=2)
    assert result["status"] == "ok"


# ── tpn-prescription ──


def test_tpn_nutrition_screen():
    from modules.tpn_prescription import nutrition_screen
    result = nutrition_screen(patient_id="PH001")
    assert result["status"] == "ok"


def test_tpn_energy_calculate():
    from modules.tpn_prescription import energy_calculate
    result = energy_calculate(weight_kg=45, height_cm=158, age=58, gender="female", stress_level="major_surgery")
    assert result["status"] == "ok"
    assert result["tee_kcal"] > 800


def test_tpn_safety_check():
    from modules.tpn_prescription import safety_check
    result = safety_check(formula={"渗透压": "1300 mOsm/L"})
    assert result["status"] == "ok"
