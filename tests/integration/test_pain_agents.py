"""疼痛科 6 Agent 集成测试."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import _registry, DomainPlugin, ToolDef, register  # noqa: E402
from haip.a2a import call, clear_history  # noqa: E402


class TestPainHub:
    def setup_method(self):
        _registry.clear()
        clear_history()

    def test_triage_acute_back_pain(self):
        register(DomainPlugin(name="pain-hub", type="business",
            tools=[ToolDef(name="triage", description="", handler="pain_hub.triage")]))
        r = call("pain-hub", "triage", {"pain_type": "acute post-surgical", "vas_score": 8, "description": ""})
        assert r["route_to"] == "acute-pain"
        assert r["urgency"] == "urgent"

    def test_triage_cancer_pain(self):
        register(DomainPlugin(name="pain-hub", type="business",
            tools=[ToolDef(name="triage", description="", handler="pain_hub.triage")]))
        r = call("pain-hub", "triage", {"pain_type": "cancer", "vas_score": 6, "description": ""})
        assert r["route_to"] == "cancer-pain"

    def test_triage_cauda_equina_red_flag(self):
        register(DomainPlugin(name="pain-hub", type="business",
            tools=[ToolDef(name="triage", description="", handler="pain_hub.triage")]))
        r = call("pain-hub", "triage", {"pain_type": "acute", "vas_score": 9,
                  "description": "cauda equina symptoms"})
        assert len(r["red_flags"]) > 0
        assert r["urgency"] == "critical"


class TestAcutePain:
    def setup_method(self):
        _registry.clear()

    def test_assess_severe(self):
        register(DomainPlugin(name="acute-pain", type="specialist",
            tools=[ToolDef(name="assess_acute", description="", handler="acute_pain.assess")]))
        r = call("acute-pain", "assess_acute", {"vas_score": 8, "description": ""})
        assert r["nrs_level"] == "severe"

    def test_pca_elderly(self):
        register(DomainPlugin(name="acute-pain", type="specialist",
            tools=[ToolDef(name="manage_pca", description="", handler="acute_pain.pca")]))
        r = call("acute-pain", "manage_pca", {"age": 80, "weight_kg": 60.0, "renal_ok": True})
        assert r["adjustment_needed"]
        assert r["bolus_mg"] <= 1.0

    def test_detect_compartment_syndrome(self):
        register(DomainPlugin(name="acute-pain", type="specialist",
            tools=[ToolDef(name="detect_crisis", description="", handler="acute_pain.crisis")]))
        r = call("acute-pain", "detect_crisis", {"symptoms": ["被动牵拉痛加重"]})
        assert r["crisis_detected"]
        assert r["crisis_type"] == "compartment_syndrome"


class TestChronicPain:
    def test_chronic_assess(self):
        register(DomainPlugin(name="chronic-pain", type="specialist",
            tools=[ToolDef(name="assess_chronic", description="", handler="chronic_pain.assess")]))
        r = call("chronic-pain", "assess_chronic", {"pain_duration_months": 12, "vas_score": 5})
        assert r["is_chronic"]

    def test_stepped_care_step3(self):
        register(DomainPlugin(name="chronic-pain", type="specialist",
            tools=[ToolDef(name="stepped_care", description="", handler="chronic_pain.care")]))
        r = call("chronic-pain", "stepped_care", {"vas_score": 8, "odi_score": 55, "failed_prev": True})
        assert r["step"] == 3


class TestCancerPain:
    def test_who_step3(self):
        register(DomainPlugin(name="cancer-pain", type="specialist",
            tools=[ToolDef(name="assess_cancer", description="", handler="cancer_pain.assess")]))
        r = call("cancer-pain", "assess_cancer", {"vas_score": 8, "current_opioid_mg": 80})
        assert r["who_step"] == 3

    def test_opioid_overdose_risk(self):
        register(DomainPlugin(name="cancer-pain", type="specialist",
            tools=[ToolDef(name="opioid_safety", description="", handler="cancer_pain.safety")]))
        r = call("cancer-pain", "opioid_safety", {"daily_me_mg": 150, "concurrent_meds": ["diazepam"]})
        assert r["overdose_risk"]
        assert r["ddi_detected"]

    def test_palliative_refer_terminal(self):
        register(DomainPlugin(name="cancer-pain", type="specialist",
            tools=[ToolDef(name="palliative_refer", description="", handler="cancer_pain.palliative")]))
        r = call("cancer-pain", "palliative_refer", {"cancer_stage": "IV", "ecog": 4, "prognosis_months": 2})
        assert r["refer_recommended"]


class TestInterventionalPain:
    def test_imaging_gate_fail(self):
        register(DomainPlugin(name="interventional-pain", type="specialist",
            tools=[ToolDef(name="imaging_gate", description="", handler="interventional_pain.gate")]))
        r = call("interventional-pain", "imaging_gate", {"has_mri": False, "has_ct": False})
        assert not r["gate_passed"]

    def test_postop_infection(self):
        register(DomainPlugin(name="interventional-pain", type="specialist",
            tools=[ToolDef(name="postop_safety", description="", handler="interventional_pain.postop")]))
        r = call("interventional-pain", "postop_safety", {"procedure": "epidural", "signs": {"temp": 38.5, "redness": True}})
        assert r["complication_detected"]


class TestPainRehab:
    def test_severe_odi_limited(self):
        register(DomainPlugin(name="pain-rehab", type="specialist",
            tools=[ToolDef(name="exercise_rx", description="", handler="pain_rehab.exercise")]))
        r = call("pain-rehab", "exercise_rx", {"pain_location": "lumbar", "odi_score": 65})
        assert r["intensity"] == "low"
        assert len(r.get("precautions", [])) > 0

    def test_suicide_risk(self):
        register(DomainPlugin(name="pain-rehab", type="specialist",
            tools=[ToolDef(name="comorbidity", description="", handler="pain_rehab.comorbid")]))
        r = call("pain-rehab", "comorbidity", {"phq9_score": 18, "gad7_score": 12})
        assert r["suicide_risk"]
        assert r["needs_psychology"]
