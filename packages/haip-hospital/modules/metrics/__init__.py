"""全院指标数据中心 — KnowledgeAgent-powered clinical reasoning.

Agent: metrics | Department: 全院
Guidelines: 全院指标标准
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="metrics", department="全院")
_guidelines = ['全院指标标准']

def get_department_metrics(**kwargs) -> dict:
    """Get Department Metrics"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"全院指标数据中心 — Get Department Metrics",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def get_quality_metrics(**kwargs) -> dict:
    """Get Quality Metrics"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"全院指标数据中心 — Get Quality Metrics",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def get_efficiency_metrics(**kwargs) -> dict:
    """Get Efficiency Metrics"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"全院指标数据中心 — Get Efficiency Metrics",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
