"""皮肤科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: dermatology | Department: 皮肤科
Guidelines: '中华皮肤科杂志 皮肤病诊疗指南 (2022)'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="dermatology", department="皮肤科")
_guidelines = ['中华皮肤科杂志 皮肤病诊疗指南 (2022)']

def bp_reception(**kwargs) -> dict:
    """Bp Reception"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"皮肤科智能体 ? Bp Reception??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_exam(**kwargs) -> dict:
    """Bp Exam"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"皮肤科智能体 ? Bp Exam??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_diagnosis(**kwargs) -> dict:
    """Bp Diagnosis"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"皮肤科智能体 ? Bp Diagnosis??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_treatment(**kwargs) -> dict:
    """Bp Treatment"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"皮肤科智能体 ? Bp Treatment??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_followup(**kwargs) -> dict:
    """Bp Followup"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"皮肤科智能体 ? Bp Followup??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
