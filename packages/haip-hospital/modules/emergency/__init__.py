"""急诊科 — RuleEngine-powered clinical reasoning.

Rules: ESI triage, SOFA critical care scoring, SIRS sepsis criteria
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="emergency", department="急诊科")
_guidelines = ["中国急诊医学杂志 急诊诊疗指南 (2023)", "SCCM Surviving Sepsis Campaign 2021"]
_agent.rule_engine.load_all()  # Pre-load rules


def bp_triage(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(p)
    return _agent.clinical_result_from_pipeline(p, pipeline)


def bp_rescue(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(p)
    return _agent.clinical_result_from_pipeline(p, pipeline)


def bp_icu(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(p)
    return _agent.clinical_result_from_pipeline(p, pipeline)


def bp_monitor(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(p)
    return _agent.clinical_result_from_pipeline(p, pipeline)


def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    pipeline = _agent.run_clinical_pipeline(p)
    return _agent.clinical_result_from_pipeline(p, pipeline)
