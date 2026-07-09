"""疼痛科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: 疼痛科 | Department: 疼痛科
Guidelines: '中国疼痛医学杂志 疼痛诊疗规范 (2022)'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="疼痛科", department="疼痛科")
_guidelines = ['中国疼痛医学杂志 疼痛诊疗规范 (2022)']

def assess(**kwargs) -> dict:
    """Assess"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"疼痛科智能体 ? Assess??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def diagnose(**kwargs) -> dict:
    """Diagnose"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"疼痛科智能体 ? Diagnose??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def treat(**kwargs) -> dict:
    """Treat"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"疼痛科智能体 ? Treat??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
