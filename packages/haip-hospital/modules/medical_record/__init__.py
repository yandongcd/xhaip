"""患者数据中心 ? KnowledgeAgent-powered clinical reasoning.

Agent: medical-record | Department: 全院
Guidelines: '??????'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="medical-record", department="全院")
_guidelines = ['??????']

def get_patient(**kwargs) -> dict:
    """Get Patient"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"患者数据中心 ? Get Patient??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def get_labs(**kwargs) -> dict:
    """Get Labs"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"患者数据中心 ? Get Labs??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def get_exams(**kwargs) -> dict:
    """Get Exams"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"患者数据中心 ? Get Exams??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
