"""创伤骨科模块测试 (含 v1.1 新增: MDT + Pain + Education + Mock 适配器)."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from orthopedics import (
    assess,
    evaluate_timing,
    followup_plan,
    nursing_plan,
    plan,
    predict_complications,
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


# ── v1.1 新增测试 ──


class TestMDTConsultation:
    def test_full_mdt(self):
        from orthopedics.mdt import mdt_aggregate, mdt_summary
        r = mdt_aggregate(
            patient_id="P001",
            chief_complaint="跌倒后右髋疼痛 3h",
            cardio_eval={"risk_level": "中危 — 高血压控制良好", "recommendations": ["术前心超"]},
            anesthesia_eval={"asa_grade": "ASA II", "recommended_plan": "椎管内麻醉"},
            orthopedic_eval={"diagnosis": "股骨颈骨折 Garden III", "recommended_surgery": "THA",
                              "rationale": "72岁 Garden III 移位 > NICE §1.5 推荐 THA"},
        )
        assert r["patient_id"] == "P001"
        assert r["diagnosis"]["primary"] == "股骨颈骨折 Garden III"
        assert r["risk_assessment"]["cardiac"] == "中危 — 高血压控制良好"
        assert r["risk_assessment"]["anesthesia"] == "ASA II"
        assert r["treatment_plan"]["recommended"] == "THA"
        assert r["disclaimer"]

        s = mdt_summary(r)
        assert s["mdt_id"]
        assert s["risk_overall"]
        assert "summary_markdown" in s

    def test_degraded_mdt(self):
        from orthopedics.mdt import mdt_aggregate
        r = mdt_aggregate(
            patient_id="P002",
            chief_complaint="跌倒后左髋疼痛",
            anesthesia_eval=None,
        )
        assert r["_degraded"]
        assert "anesthesia" in r["_degraded_agents"]
        assert "待补充" in r["risk_assessment"]["anesthesia"]

    def test_mdt_with_pain(self):
        from orthopedics.mdt import mdt_aggregate
        r = mdt_aggregate(
            patient_id="P003",
            chief_complaint="跌倒后左髋疼痛 5h VAS 8",
            orthopedic_eval={"diagnosis": "转子间骨折 Evans ID", "recommended_surgery": "PFNA"},
            pain_eval={"vas_score": 8, "analgesia_plan": "FICB + 舒芬太尼 PCA"},
        )
        assert r["controversies"]
        has_pain = any(c.get("source") == "疼痛管理" for c in r["controversies"] if isinstance(c, dict))
        assert has_pain


class TestPainManagement:
    def test_assess_pain_valid(self):
        from pain_management import assess_pain
        r = assess_pain(patient_id="P001", vas_score=7.0, nurse_id="N001", assessment_time="2026-07-11T08:00")
        assert r["severity"] == "重度"
        assert r["vas_score"] == 7.0

    def test_assess_pain_missing(self):
        from pain_management import assess_pain
        r = assess_pain(patient_id="P001")
        assert r.get("requires_input")

    def test_assess_pain_oob(self):
        from pain_management import assess_pain
        r = assess_pain(patient_id="P001", vas_score=15.0)
        assert r.get("requires_input")

    def test_multimodal_analgesia(self):
        from pain_management import multimodal_analgesia
        r = multimodal_analgesia(patient_id="P001", vas_score=8.0, renal_function="normal", liver_function="normal")
        assert len(r["layers"]) >= 3

    def test_pain_free_metrics(self):
        from pain_management import pain_free_ward_metrics
        r = pain_free_ward_metrics(ward_id="ORTHO-A", period="monthly")
        assert "targets" in r
        assert "vas_under_3_ratio" in r["targets"]

    def test_pca_config(self):
        from pain_management import pca_config
        r = pca_config(patient_id="P001", age=78, weight=55, procedure="THA", allergies=[])
        assert r["mode"] == "PCIA"
        assert "monitoring" in r

    def test_pca_elderly_warning(self):
        from pain_management import pca_config
        r = pca_config(patient_id="P001", age=85, weight=48, procedure="THA", allergies=[])
        assert r.get("warnings")


class TestEducation:
    def test_case_teaching(self):
        from education import case_teaching
        r = case_teaching(fracture_type="femoral_neck", difficulty="basic")
        assert r["case_id"] == "EDU-FN-001"
        assert r["patient"]["synthetic"] is True
        assert r["teaching_points"]

    def test_guideline_ref(self):
        from education import guideline_quick_ref
        r = guideline_quick_ref(guideline="nhsa_2022")
        assert "early_surgery" in r["items"]

    def test_learning_path(self):
        from education import learning_path
        r = learning_path(role="resident")
        assert "milestones" in r["path"]
        assert len(r["path"]["milestones"]) == 4

    def test_decision_review_alignment(self):
        from education import decision_review
        r = decision_review(
            case_id="EDU-FN-001",
            ai_recommendation={"recommended_surgery": "THA", "timing": "emergency"},
            actual_decision={"surgery": "THA", "timing": "emergency"},
        )
        assert r["alignment_rate"] == 100
        assert len(r["alignment"]) == 2


class TestHISAdapter:
    def test_query_labs(self):
        from orthopedics.his_adapter import query_labs
        r = query_labs(patient_id="P001", lab_items=["cTnI", "Hb"])
        assert r["_mock"] is True
        assert "cTnI" in r["labs"]
        assert r["labs"]["cTnI"]["status"] in ("normal", "critical_high")

    def test_query_patient(self):
        from orthopedics.his_adapter import query_patient
        r = query_patient(patient_id="P001")
        assert r["_mock"] is True
        assert r["name"] == "张**"

    def test_query_imaging(self):
        from orthopedics.his_adapter import query_imaging
        r = query_imaging(patient_id="P001", modality="pelvis_xray")
        assert r["_mock"] is True
        assert "Garden" in r["findings"]["description"]


class TestiDataAdapter:
    def test_search_knowledge(self):
        from orthopedics.idata_adapter import search_knowledge
        r = search_knowledge(query="garden")
        assert r["_mock"] is True
        assert r["priority"] == "secondary"
        assert r["results"]

    def test_list_categories(self):
        from orthopedics.idata_adapter import list_categories
        r = list_categories()
        assert len(r["categories"]) >= 3
