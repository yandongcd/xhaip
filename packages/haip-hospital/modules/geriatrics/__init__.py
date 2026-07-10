"""老年病科 — RuleEngine-driven clinical reasoning."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="geriatrics", department="老年病科")
_agent.rule_engine.load_all()


def bp_reception(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_exam(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_diagnosis(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_plan(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    patient = _agent.get_patient(pid)
    if not patient:
        return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(patient)
    return _agent.clinical_result_from_pipeline(patient, pipeline)

def bp_treatment(**kwargs) -> dict:
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

