"""血管外科 — RuleEngine-driven clinical reasoning."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="vascular-surgery", department="血管外科")
_agent.rule_engine.load_all()


def bp_reg(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_diag(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_preop(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_risk(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_mdt(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_surgery(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_nursing(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

