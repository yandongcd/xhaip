"""重症医学科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: icu | Department: 重症医学科
Guidelines: 'SCCM 2021 重症监护管理指南'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="icu", department="重症医学科")
_guidelines = ['SCCM 2021 重症监护管理指南']

def bp_triage(**kwargs) -> dict:
    """Bp Triage"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"重症医学科智能体 ? Bp Triage??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_rescue(**kwargs) -> dict:
    """Bp Rescue"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"重症医学科智能体 ? Bp Rescue??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_icu(**kwargs) -> dict:
    """Bp Icu"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"重症医学科智能体 ? Bp Icu??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_transfer(**kwargs) -> dict:
    """Bp Transfer"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"重症医学科智能体 ? Bp Transfer??",
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
        summary=f"重症医学科智能体 ? Bp Followup??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
