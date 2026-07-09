"""创伤骨科模块测试."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from orthopedics import (  # noqa: E402
    evaluate_timing, predict_complications, nursing_plan, followup_plan,
    assess, plan,
)

ELDERLY_HIP = {"patient_id": "P001", "labs": {
    "troponin": 0.05, "hb": 85, "egfr": 35, "wbc": 13,
    "crp": 120, "glucose": 14.5, "inr": 1.8, "albumin": 28},
    "ecg_findings": "ST DEPRESSION in V4-V6",
    "conditions": ["高血压", "糖尿病", "冠心病"],
    "meds": ["warfarin"]}

HEALTHY = {"patient_id": "P002", "labs": {
    "troponin": 0.005, "hb": 145, "egfr": 95, "wbc": 6,
    "crp": 3, "glucose": 5.2, "inr": 1.0, "albumin": 42},
    "ecg_findings": "正常窦性心律",
    "conditions": [], "meds": []}


class TestTimingEngine:
    def test_high_risk_cardiac(self):
        r = evaluate_timing(**ELDERLY_HIP)
        assert r["urgency"] == "elective"
        assert "cardiac_troponin" in r["high_triggers"]
        assert "感染" in r["sla"] or "MDT" in r["sla"] or r["sla"] == "MDT 确定"

    def test_high_risk_ecg(self):
        r = evaluate_timing(patient_id="P003", labs={},
                           ecg_findings="VT 持续性室性心动过速", conditions=[], meds=[])
        assert r["urgency"] == "elective"
        assert any("ecg" in t for t in r["high_triggers"])

    def test_medium_risk_combined(self):
        labs = {"inr": 2.0, "hb": 95, "wbc": 15}
        r = evaluate_timing(patient_id="P004", labs=labs,
                           conditions=["冠心病"], meds=["warfarin"],
                           ecg_findings="正常")
        assert r["urgency"] == "urgent"
        assert len(r["medium_triggers"]) >= 2

    def test_no_delay_emergency(self):
        r = evaluate_timing(**HEALTHY)
        assert r["urgency"] == "emergency"
        assert r["total_factors"] == 0

    def test_anticoag_severe(self):
        r = evaluate_timing(patient_id="P005", labs={"inr": 2.5, "hb": 140},
                           meds=["warfarin"], conditions=[], ecg_findings="正常")
        assert "anticoag_severe" in r["medium_triggers"]


class TestComplicationPredictor:
    def test_elderly_high_risk(self):
        r = predict_complications(patient_id="P001", age=82, labs={"wbc": 14, "crp": 110, "albumin": 25},
                                  conditions=["糖尿病", "冠心病", "卧床"])
        assert r["overall_risk"] in ("high", "moderate")
        assert len(r["prevention"]) >= 2

    def test_young_low_risk(self):
        r = predict_complications(patient_id="P002", age=45, labs={}, conditions=[])
        assert r["overall_risk"] == "low"
        assert len(r["prevention"]) == 0 or all("low" in str(v) for v in r["risks"].values())


class TestNursingPlan:
    def test_four_stages_present(self):
        r = nursing_plan(patient_id="P001")
        assert "stage_1_preop" in r["plan"]
        assert "stage_2_day0" in r["plan"]
        assert "stage_3_early" in r["plan"]
        assert "stage_4_recovery" in r["plan"]

    def test_highlights_for_comorbid(self):
        r = nursing_plan(patient_id="P001", age=85, conditions=["糖尿病", "COPD", "高血压"])
        assert len(r["highlights"]) >= 3


class TestFollowupPlan:
    def test_four_timepoints(self):
        r = followup_plan(patient_id="P001")
        assert len(r["schedule"]) == 4
        assert r["schedule"][0]["month"] == 1
        assert r["schedule"][3]["month"] == 12

    def test_red_flags_count(self):
        r = followup_plan(patient_id="P001")
        assert len(r["red_flags"]) == 6

    def test_osteoporosis_mgmt(self):
        r = followup_plan(patient_id="P001")
        assert "calcium" in r["osteoporosis_management"]


class TestFractureClassifier:
    def test_femoral_neck(self):
        r = assess(xray_findings={"location": "femoral_neck", "type": "Garden IV"})
        assert "Garden" in r["classification"]
        assert r["severity"] == "high"

    def test_intertroch(self):
        r = assess(xray_findings={"location": "intertrochanteric", "type": "Evans ID"})
        assert "Evans" in r["classification"]


class TestSurgeryPlanner:
    def test_elderly_tha(self):
        r = plan(fracture_type="femoral neck", age=78)
        assert "THA" in r["procedure"]

    def test_intertroch_pfna(self):
        r = plan(fracture_type="intertrochanteric", age=75)
        assert "PFNA" in r["procedure"]
