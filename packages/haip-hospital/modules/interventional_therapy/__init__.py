"""介入治疗科智能体 ? KnowledgeAgent-powered clinical reasoning.

Agent: interventional-therapy | Department: 介入治疗科
Guidelines: '中华介入放射学杂志 介入诊疗规范 (2022)'
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="interventional-therapy", department="介入治疗科")
_guidelines = ['中华介入放射学杂志 介入诊疗规范 (2022)']

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
        summary=f"介入治疗科智能体 ? Bp Reg??",
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
        summary=f"介入治疗科智能体 ? Bp Diag??",
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
        summary=f"介入治疗科智能体 ? Bp Preop??",
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
        summary=f"介入治疗科智能体 ? Bp Risk??",
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
        summary=f"介入治疗科智能体 ? Bp Mdt??",
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
        summary=f"介入治疗科智能体 ? Bp Surgery??",
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
        summary=f"介入治疗科智能体 ? Bp Nursing??",
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
        summary=f"介入治疗科智能体 ? Bp Followup??",
        patient=patient,
        guidelines=guides[:3],
        alerts=alerts,
    )
