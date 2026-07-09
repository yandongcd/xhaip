"""胸外科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: thoracic-surgery | Department: 胸外科
Guidelines: 'NCCN 非小细胞肺癌指南 (2023)'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="thoracic-surgery", department="胸外科")
_guidelines = ['NCCN 非小细胞肺癌指南 (2023)']

def bp_reg(**kwargs) -> dict:
    """Bp Reg"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Reg??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_diag(**kwargs) -> dict:
    """Bp Diag"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Diag??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_preop(**kwargs) -> dict:
    """Bp Preop"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Preop??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_risk(**kwargs) -> dict:
    """Bp Risk"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Risk??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_mdt(**kwargs) -> dict:
    """Bp Mdt"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Mdt??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_surgery(**kwargs) -> dict:
    """Bp Surgery"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Surgery??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )

def bp_nursing(**kwargs) -> dict:
    """Bp Nursing"""
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}

    dx = patient.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _guidelines
    vitals = _agent.assess_vitals(patient)
    alerts = vitals.get("alerts", [])

    return _agent.clinical_result(
        summary=f"胸外科智能体 ? Bp Nursing??",
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
        summary=f"胸外科智能体 ? Bp Followup??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
