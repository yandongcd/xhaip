"""精神心理科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: psychiatry | Department: 精神心理科
Guidelines: '中国精神障碍防治指南 (2023)'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="psychiatry", department="精神心理科")
_guidelines = ['中国精神障碍防治指南 (2023)']

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
        summary=f"精神心理科智能体 ? Bp Reception??",
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
        summary=f"精神心理科智能体 ? Bp Exam??",
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
        summary=f"精神心理科智能体 ? Bp Diagnosis??",
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
        summary=f"精神心理科智能体 ? Bp Treatment??",
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
        summary=f"精神心理科智能体 ? Bp Followup??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
