"""A2A integration tests ? split from test_agent_a2a.py for CI parallelism."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.a2a import call, clear_history
from haip.agent import DomainPlugin, ToolDef, _registry, register


def setup_function():
    _registry.clear()
    clear_history()

# ── 19. Rheumatology ───────────────────────────────────────────────────────

def test_rheumatology_reception():
    register(DomainPlugin(name="rheumatology", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="rheumatology.bp_reception")]))
    r = call("rheumatology", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_rheumatology_diagnosis():
    register(DomainPlugin(name="rheumatology", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="rheumatology.bp_diagnosis")]))
    r = call("rheumatology", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 20. Oncology ───────────────────────────────────────────────────────────

def test_oncology_reception():
    register(DomainPlugin(name="oncology", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="oncology.bp_reception")]))
    r = call("oncology", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_oncology_plan():
    register(DomainPlugin(name="oncology", type="business",
        tools=[ToolDef(name="bp_plan", description="",
                       handler="oncology.bp_plan")]))
    r = call("oncology", "bp_plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 21. Hematology ─────────────────────────────────────────────────────────

def test_hematology_reception():
    register(DomainPlugin(name="hematology", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="hematology.bp_reception")]))
    r = call("hematology", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_hematology_diagnosis():
    register(DomainPlugin(name="hematology", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="hematology.bp_diagnosis")]))
    r = call("hematology", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 22. Infectious Disease ─────────────────────────────────────────────────

def test_infectious_reception():
    register(DomainPlugin(name="infectious-disease", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="infectious_disease.bp_reception")]))
    r = call("infectious-disease", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_infectious_diagnosis():
    register(DomainPlugin(name="infectious-disease", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="infectious_disease.bp_diagnosis")]))
    r = call("infectious-disease", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 23. Geriatrics ─────────────────────────────────────────────────────────

def test_geriatrics_reception():
    register(DomainPlugin(name="geriatrics", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="geriatrics.bp_reception")]))
    r = call("geriatrics", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_geriatrics_diagnosis():
    register(DomainPlugin(name="geriatrics", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="geriatrics.bp_diagnosis")]))
    r = call("geriatrics", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 24. Health Management ──────────────────────────────────────────────────

def test_healthmgmt_reception():
    register(DomainPlugin(name="health-management", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="health_management.bp_reception")]))
    r = call("health-management", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_healthmgmt_diagnosis():
    register(DomainPlugin(name="health-management", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="health_management.bp_diagnosis")]))
    r = call("health-management", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 25. Huigiao ────────────────────────────────────────────────────────────

def test_huigiao_reception():
    register(DomainPlugin(name="huigiao", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="huigiao.bp_reception")]))
    r = call("huigiao", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_huigiao_treatment():
    register(DomainPlugin(name="huigiao", type="business",
        tools=[ToolDef(name="bp_treatment", description="",
                       handler="huigiao.bp_treatment")]))
    r = call("huigiao", "bp_treatment", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 26. Breast Center ──────────────────────────────────────────────────────

def test_breast_reg():
    register(DomainPlugin(name="breast-center", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="breast_center.bp_reg")]))
    r = call("breast-center", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_breast_diag():
    register(DomainPlugin(name="breast-center", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="breast_center.bp_diag")]))
    r = call("breast-center", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 27. Burns Plastic ──────────────────────────────────────────────────────

def test_burns_reg():
    register(DomainPlugin(name="burns-plastic", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="burns_plastic.bp_reg")]))
    r = call("burns-plastic", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_burns_diag():
    register(DomainPlugin(name="burns-plastic", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="burns_plastic.bp_diag")]))
    r = call("burns-plastic", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 28. Cosmetic Surgery ───────────────────────────────────────────────────

def test_cosmetic_reg():
    register(DomainPlugin(name="cosmetic-surgery", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="cosmetic_surgery.bp_reg")]))
    r = call("cosmetic-surgery", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_cosmetic_diag():
    register(DomainPlugin(name="cosmetic-surgery", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="cosmetic_surgery.bp_diag")]))
    r = call("cosmetic-surgery", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 29. Hepatobiliary Surgery ──────────────────────────────────────────────

def test_hepatobiliary_reg():
    register(DomainPlugin(name="hepatobiliary-surgery", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="hepatobiliary_surgery.bp_reg")]))
    r = call("hepatobiliary-surgery", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_hepatobiliary_diag():
    register(DomainPlugin(name="hepatobiliary-surgery", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="hepatobiliary_surgery.bp_diag")]))
    r = call("hepatobiliary-surgery", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 30. Thoracic Surgery ───────────────────────────────────────────────────

def test_thoracic_reg():
    register(DomainPlugin(name="thoracic-surgery", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="thoracic_surgery.bp_reg")]))
    r = call("thoracic-surgery", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_thoracic_diag():
    register(DomainPlugin(name="thoracic-surgery", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="thoracic_surgery.bp_diag")]))
    r = call("thoracic-surgery", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 31. Vascular Surgery ───────────────────────────────────────────────────

def test_vascular_reg():
    register(DomainPlugin(name="vascular-surgery", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="vascular_surgery.bp_reg")]))
    r = call("vascular-surgery", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_vascular_diag():
    register(DomainPlugin(name="vascular-surgery", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="vascular_surgery.bp_diag")]))
    r = call("vascular-surgery", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 32. Renal Transplant ───────────────────────────────────────────────────

def test_renal_reg():
    register(DomainPlugin(name="renal-transplant", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="renal_transplant.bp_reg")]))
    r = call("renal-transplant", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_renal_diag():
    register(DomainPlugin(name="renal-transplant", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="renal_transplant.bp_diag")]))
    r = call("renal-transplant", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 33. Interventional Therapy ─────────────────────────────────────────────

def test_interv_reg():
    register(DomainPlugin(name="interventional-therapy", type="business",
        tools=[ToolDef(name="bp_reg", description="",
                       handler="interventional_therapy.bp_reg")]))
    r = call("interventional-therapy", "bp_reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_interv_diag():
    register(DomainPlugin(name="interventional-therapy", type="business",
        tools=[ToolDef(name="bp_diag", description="",
                       handler="interventional_therapy.bp_diag")]))
    r = call("interventional-therapy", "bp_diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 34. Metrics (Master Data) ──────────────────────────────────────────────

def test_metrics_dept():
    register(DomainPlugin(name="metrics", type="master_data",
        tools=[ToolDef(name="get_department_metrics", description="",
                       handler="metrics.get_department_metrics")]))
    r = call("metrics", "get_department_metrics", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_metrics_quality():
    register(DomainPlugin(name="metrics", type="master_data",
        tools=[ToolDef(name="get_quality_metrics", description="",
                       handler="metrics.get_quality_metrics")]))
    r = call("metrics", "get_quality_metrics", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert isinstance(r, dict)
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 35. Medical Record (Master Data) ───────────────────────────────────────

def test_mr_patient():
    register(DomainPlugin(name="medical-record", type="master_data",
        tools=[ToolDef(name="get_patient", description="",
                       handler="medical_record.get_patient")]))
    r = call("medical-record", "get_patient", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert r.get("found") is True


def test_mr_labs():
    register(DomainPlugin(name="medical-record", type="master_data",
        tools=[ToolDef(name="get_labs", description="",
                       handler="medical_record.get_labs")]))
    r = call("medical-record", "get_labs", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r.get("summary", ""), str)
