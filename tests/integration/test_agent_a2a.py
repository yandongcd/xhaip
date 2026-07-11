"""A2A integration tests for Top 10 untested agents.

Tests each agent's diagnosis/screening + treatment/plan tools via A2A dispatcher.
Uses real patient IDs from packages/haip-hospital/data/patients.json.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import _registry, DomainPlugin, ToolDef, register  # noqa: E402
from haip.a2a import call, clear_history  # noqa: E402


def setup_function():
    _registry.clear()
    clear_history()


# ── 1. Respiratory ───────────────────────────────────────────────────────

def test_respiratory_reception():
    register(DomainPlugin(name="respiratory", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="respiratory.bp_reception")]))
    r = call("respiratory", "reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_respiratory_diagnosis():
    register(DomainPlugin(name="respiratory", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="respiratory.bp_diagnosis")]))
    r = call("respiratory", "diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_respiratory_plan():
    register(DomainPlugin(name="respiratory", type="business",
        tools=[ToolDef(name="plan", description="",
                       handler="respiratory.bp_plan")]))
    r = call("respiratory", "plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 2. Cardiology ────────────────────────────────────────────────────────

def test_cardiology_reception():
    register(DomainPlugin(name="cardiology", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="cardiology.bp_reception")]))
    r = call("cardiology", "reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_cardiology_diagnosis():
    register(DomainPlugin(name="cardiology", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="cardiology.bp_diagnosis")]))
    r = call("cardiology", "diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_cardiology_plan():
    register(DomainPlugin(name="cardiology", type="business",
        tools=[ToolDef(name="plan", description="",
                       handler="cardiology.bp_plan")]))
    r = call("cardiology", "plan", {"patient_id": "P001"})
    assert r is not None
    assert "status" in r


# ── 3. Emergency ─────────────────────────────────────────────────────────

def test_emergency_triage():
    register(DomainPlugin(name="emergency", type="business",
        tools=[ToolDef(name="triage", description="",
                       handler="emergency.bp_triage")]))
    r = call("emergency", "triage", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_emergency_rescue():
    register(DomainPlugin(name="emergency", type="business",
        tools=[ToolDef(name="rescue", description="",
                       handler="emergency.bp_rescue")]))
    r = call("emergency", "rescue", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert len(r) > 1, f"Response too sparse: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_emergency_icu():
    register(DomainPlugin(name="emergency", type="business",
        tools=[ToolDef(name="icu", description="",
                       handler="emergency.bp_icu")]))
    r = call("emergency", "icu", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "assessment" in r or "stage" in r, f"Missing rescue fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 4. ICU ───────────────────────────────────────────────────────────────

def test_icu_triage():
    register(DomainPlugin(name="icu", type="business",
        tools=[ToolDef(name="triage", description="",
                       handler="icu.bp_triage")]))
    r = call("icu", "triage", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "assessment" in r or "stage" in r, f"Missing rescue fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_icu_rescue():
    register(DomainPlugin(name="icu", type="business",
        tools=[ToolDef(name="rescue", description="",
                       handler="icu.bp_rescue")]))
    r = call("icu", "rescue", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "assessment" in r or "stage" in r, f"Missing rescue fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_icu_monitoring():
    register(DomainPlugin(name="icu", type="business",
        tools=[ToolDef(name="monitoring", description="",
                       handler="icu.bp_icu")]))
    r = call("icu", "monitoring", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "assessment" in r or "stage" in r, f"Missing rescue fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 5. General Surgery ───────────────────────────────────────────────────

def test_gs_reg():
    register(DomainPlugin(name="general-surgery", type="business",
        tools=[ToolDef(name="reg", description="",
                       handler="general_surgery.bp_reg")]))
    r = call("general-surgery", "reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "assessment" in r or "stage" in r, f"Missing rescue fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_gs_risk():
    register(DomainPlugin(name="general-surgery", type="business",
        tools=[ToolDef(name="risk", description="",
                       handler="general_surgery.bp_risk")]))
    r = call("general-surgery", "risk", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_gs_preop():
    register(DomainPlugin(name="general-surgery", type="business",
        tools=[ToolDef(name="preop", description="",
                       handler="general_surgery.bp_preop")]))
    r = call("general-surgery", "preop", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "risk" in r or "stage" in r, f"Missing risk fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 6. Neurosurgery ──────────────────────────────────────────────────────

def test_neurosurgery_reg():
    register(DomainPlugin(name="neurosurgery", type="business",
        tools=[ToolDef(name="reg", description="",
                       handler="neurosurgery.bp_reg")]))
    r = call("neurosurgery", "reg", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "risk" in r or "stage" in r, f"Missing risk fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_neurosurgery_diag():
    register(DomainPlugin(name="neurosurgery", type="business",
        tools=[ToolDef(name="diag", description="",
                       handler="neurosurgery.bp_diag")]))
    r = call("neurosurgery", "diag", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_neurosurgery_risk():
    register(DomainPlugin(name="neurosurgery", type="business",
        tools=[ToolDef(name="risk", description="",
                       handler="neurosurgery.bp_risk")]))
    r = call("neurosurgery", "risk", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 7. OB/GYN ────────────────────────────────────────────────────────────

def test_obgyn_reception():
    register(DomainPlugin(name="obgyn", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="obgyn.bp_reception")]))
    r = call("obgyn", "reception", {"patient_id": "P001"})
    assert r is not None
    assert "status" in r


def test_obgyn_diagnosis():
    register(DomainPlugin(name="obgyn", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="obgyn.bp_diagnosis")]))
    r = call("obgyn", "diagnosis", {"patient_id": "P001"})
    assert r is not None
    assert "status" in r


def test_obgyn_exam():
    register(DomainPlugin(name="obgyn", type="business",
        tools=[ToolDef(name="exam", description="",
                       handler="obgyn.bp_exam")]))
    r = call("obgyn", "exam", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 8. Nephrology ────────────────────────────────────────────────────────

def test_nephrology_reception():
    register(DomainPlugin(name="nephrology", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="nephrology.bp_reception")]))
    r = call("nephrology", "reception", {"patient_id": "P001"})
    assert r is not None
    assert "status" in r


def test_nephrology_diagnosis():
    register(DomainPlugin(name="nephrology", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="nephrology.bp_diagnosis")]))
    r = call("nephrology", "diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_nephrology_plan():
    register(DomainPlugin(name="nephrology", type="business",
        tools=[ToolDef(name="plan", description="",
                       handler="nephrology.bp_plan")]))
    r = call("nephrology", "plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 9. Gastroenterology ──────────────────────────────────────────────────

def test_gastroenterology_reception():
    register(DomainPlugin(name="gastroenterology", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="gastroenterology.bp_reception")]))
    r = call("gastroenterology", "reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_gastroenterology_diagnosis():
    register(DomainPlugin(name="gastroenterology", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="gastroenterology.bp_diagnosis")]))
    r = call("gastroenterology", "diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_gastroenterology_plan():
    register(DomainPlugin(name="gastroenterology", type="business",
        tools=[ToolDef(name="plan", description="",
                       handler="gastroenterology.bp_plan")]))
    r = call("gastroenterology", "plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 10. Endocrinology ────────────────────────────────────────────────────

def test_endocrinology_reception():
    register(DomainPlugin(name="endocrinology", type="business",
        tools=[ToolDef(name="reception", description="",
                       handler="endocrinology.bp_reception")]))
    r = call("endocrinology", "reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_endocrinology_diagnosis():
    register(DomainPlugin(name="endocrinology", type="business",
        tools=[ToolDef(name="diagnosis", description="",
                       handler="endocrinology.bp_diagnosis")]))
    r = call("endocrinology", "diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_endocrinology_plan():
    register(DomainPlugin(name="endocrinology", type="business",
        tools=[ToolDef(name="plan", description="",
                       handler="endocrinology.bp_plan")]))
    r = call("endocrinology", "plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 11. Dermatology ────────────────────────────────────────────────────────

def test_dermatology_reception():
    register(DomainPlugin(name="dermatology", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="dermatology.bp_reception")]))
    r = call("dermatology", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_dermatology_treatment():
    register(DomainPlugin(name="dermatology", type="business",
        tools=[ToolDef(name="bp_treatment", description="",
                       handler="dermatology.bp_treatment")]))
    r = call("dermatology", "bp_treatment", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 12. Psychiatry ─────────────────────────────────────────────────────────

def test_psychiatry_reception():
    register(DomainPlugin(name="psychiatry", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="psychiatry.bp_reception")]))
    r = call("psychiatry", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_psychiatry_diagnosis():
    register(DomainPlugin(name="psychiatry", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="psychiatry.bp_diagnosis")]))
    r = call("psychiatry", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 13. Rehabilitation ─────────────────────────────────────────────────────

def test_rehabilitation_reception():
    register(DomainPlugin(name="rehabilitation", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="rehabilitation.bp_reception")]))
    r = call("rehabilitation", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_rehabilitation_treatment():
    register(DomainPlugin(name="rehabilitation", type="business",
        tools=[ToolDef(name="bp_treatment", description="",
                       handler="rehabilitation.bp_treatment")]))
    r = call("rehabilitation", "bp_treatment", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 14. TCM ────────────────────────────────────────────────────────────────

def test_tcm_reception():
    register(DomainPlugin(name="tcm", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="tcm.bp_reception")]))
    r = call("tcm", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_tcm_plan():
    register(DomainPlugin(name="tcm", type="business",
        tools=[ToolDef(name="bp_plan", description="",
                       handler="tcm.bp_plan")]))
    r = call("tcm", "bp_plan", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 15. Stomatology ────────────────────────────────────────────────────────

def test_stomatology_screening():
    register(DomainPlugin(name="stomatology", type="business",
        tools=[ToolDef(name="bp_screening", description="",
                       handler="stomatology.bp_screening")]))
    r = call("stomatology", "bp_screening", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_stomatology_treatment():
    register(DomainPlugin(name="stomatology", type="business",
        tools=[ToolDef(name="bp_treatment", description="",
                       handler="stomatology.bp_treatment")]))
    r = call("stomatology", "bp_treatment", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 16. ENT ────────────────────────────────────────────────────────────────

def test_ent_screening():
    register(DomainPlugin(name="ent", type="business",
        tools=[ToolDef(name="bp_screening", description="",
                       handler="ent.bp_screening")]))
    r = call("ent", "bp_screening", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_ent_diagnosis():
    register(DomainPlugin(name="ent", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="ent.bp_diagnosis")]))
    r = call("ent", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 17. Ophthalmology ──────────────────────────────────────────────────────

def test_ophthalmology_screening():
    register(DomainPlugin(name="ophthalmology", type="business",
        tools=[ToolDef(name="bp_screening", description="",
                       handler="ophthalmology.bp_screening")]))
    r = call("ophthalmology", "bp_screening", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_ophthalmology_treatment():
    register(DomainPlugin(name="ophthalmology", type="business",
        tools=[ToolDef(name="bp_treatment", description="",
                       handler="ophthalmology.bp_treatment")]))
    r = call("ophthalmology", "bp_treatment", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


# ── 18. Neonatology ────────────────────────────────────────────────────────

def test_neonatology_reception():
    register(DomainPlugin(name="neonatology", type="business",
        tools=[ToolDef(name="bp_reception", description="",
                       handler="neonatology.bp_reception")]))
    r = call("neonatology", "bp_reception", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "recommendations" in r or "stage" in r, f"Missing plan fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


def test_neonatology_diagnosis():
    register(DomainPlugin(name="neonatology", type="business",
        tools=[ToolDef(name="bp_diagnosis", description="",
                       handler="neonatology.bp_diagnosis")]))
    r = call("neonatology", "bp_diagnosis", {"patient_id": "P001"})
    assert r["status"] == "ok"
    assert isinstance(r, dict), "result should be dict"
    assert "summary" in r or "stage" in r or "findings" in r, f"Missing clinical fields: {list(r.keys())}"
    assert isinstance(r.get("guideline_refs", []) or [], (list, type(None))), "guideline_refs invalid type"


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
