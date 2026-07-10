"""重症医学科 — RuleEngine-driven clinical reasoning."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="icu", department="重症医学科")
_agent.rule_engine.load_all()


def bp_triage(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_rescue(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_icu(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_transfer(**kwargs) -> dict:
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

