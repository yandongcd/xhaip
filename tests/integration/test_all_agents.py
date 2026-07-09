"""多 Agent 注册表与 A2A 分发验证."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import load_from_dir, _registry, get as get_agent, DomainPlugin, ToolDef, register  # noqa: E402
from haip.a2a import call, clear_history  # noqa: E402

YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


class TestAllAgents:
    def setup_method(self):
        _registry.clear()
        clear_history()

    def test_all_yamls_load(self):
        count = load_from_dir(str(YAML_DIR))
        assert count == 14

    def test_all_agent_types(self):
        load_from_dir(str(YAML_DIR))
        agents = {name: get_agent(name) for name in
                  ["pharmacy", "orthopedic-surgery", "cardio-surgery",
                   "pediatrics", "cardio-risk", "anesthesia-risk", "medical-record"]}
        assert agents["pharmacy"].type == "business"
        assert agents["orthopedic-surgery"].type == "business"
        assert agents["cardio-risk"].type == "specialist"
        assert agents["anesthesia-risk"].type == "specialist"
        assert agents["medical-record"].type == "master_data"

    def test_orthopedic_assess(self):
        register(DomainPlugin(name="orthopedic-surgery", type="business",
            tools=[ToolDef(name="classify_fracture",description="",
                          handler="orthopedics.assess")]))
        r = call("orthopedic-surgery", "classify_fracture",
                 {"xray_findings": {"location": "femoral_neck", "type": "Garden III"}})
        assert r["status"] == "ok"
        assert r["severity"] == "high"

    def test_orthopedic_plan_tha(self):
        register(DomainPlugin(name="orthopedic-surgery", type="business",
            tools=[ToolDef(name="surgical_plan", description="",
                          handler="orthopedics.plan")]))
        r = call("orthopedic-surgery", "surgical_plan",
                 {"fracture_type": "femoral neck", "age": 78})
        assert r["status"] == "ok"
        assert "THA" in r["procedure"]

    def test_cardio_risk_rcri(self):
        register(DomainPlugin(name="cardio-risk", type="specialist",
            tools=[ToolDef(name="assess_cardiac", description="",
                          handler="cardio_risk.evaluate")]))
        r = call("cardio-risk", "assess_cardiac",
                 {"labs": {"creatinine": 180}, "ecg_findings": "ST depression",
                  "conditions": ["冠心病", "糖尿病"]})
        assert r["rcri_score"] >= 1  # base + cad

    def test_anesthesia_asa(self):
        register(DomainPlugin(name="anesthesia-risk", type="specialist",
            tools=[ToolDef(name="assess_asa", description="",
                          handler="anesthesia.evaluate")]))
        r = call("anesthesia-risk", "assess_asa",
                 {"conditions": ["HTN", "DM"], "functional_status": "active"})
        assert r["status"] == "ok"
        assert r["asa_class"] >= 2

    def test_medical_record_get_patient(self):
        register(DomainPlugin(name="medical-record", type="master_data",
            tools=[ToolDef(name="get_patient", description="",
                          handler="medical_record.get_patient")]))
        r = call("medical-record", "get_patient", {"patient_id": "P001"})
        assert r["found"] is True
        assert "张" in r.get("name", "")

    def test_medical_record_not_found(self):
        register(DomainPlugin(name="medical-record", type="master_data",
            tools=[ToolDef(name="get_patient", description="",
                          handler="medical_record.get_patient")]))
        r = call("medical-record", "get_patient", {"patient_id": "P999"})
        assert r["found"] is False

    def test_cardio_surgery_plan(self):
        register(DomainPlugin(name="cardio-surgery", type="business",
            tools=[ToolDef(name="anticoagulation_plan", description="",
                          handler="cardio_surgery.plan")]))
        r = call("cardio-surgery", "anticoagulation_plan",
                 {"surgery_type": "MVR"})
        assert r["status"] == "ok"
        assert r["anticoagulation"] == "warfarin"

    def test_pediatrics_dose(self):
        register(DomainPlugin(name="pediatrics", type="business",
            tools=[ToolDef(name="dose_calculate", description="",
                          handler="pediatrics.calc")]))
        r = call("pediatrics", "dose_calculate",
                 {"drug_name": "amoxicillin", "weight_kg": 15.0})
        assert r["single_dose_mg"] == 750.0

    def test_pediatrics_growth(self):
        register(DomainPlugin(name="pediatrics", type="business",
            tools=[ToolDef(name="growth_assess", description="",
                          handler="pediatrics.evaluate")]))
        r = call("pediatrics", "growth_assess",
                 {"age_months": 24, "weight_kg": 12.0, "height_cm": 88.0})
        assert "growth" in str(r).lower() or "正常" in str(r) or "weight" in str(r).lower()  # status field from business function
