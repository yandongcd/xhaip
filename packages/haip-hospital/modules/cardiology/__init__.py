"""心血管内科 — KnowledgeAgent-powered clinical reasoning.

GUIDELINES: 中国心衰指南2024, 中国高血压指南2024, AHA/ACC
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cardiology", department="心血管内科")
_guidelines = ["中国心力衰竭诊断和治疗指南 (2024)", "中国高血压防治指南 (2024)"]


def bp_reception(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or _guidelines
    return _agent.clinical_result(f"接诊评估完成 — {p.get('diagnosis', '')}", p, guides)


def bp_exam(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    return {"status": "ok", "patient_id": pid, "summary": "心脏辅助检查完成",
            "recommendations": ["心电图", "心脏超声", "心肌酶谱", "BNP/NT-proBNP", "动态心电图"]}


def bp_diagnosis(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    dx = p.get("diagnosis", "")
    vitals = _agent.assess_vitals(p)
    troponin = p.get("lab_results", {}).get("Troponin", 0)
    risk = "高危" if float(troponin or 0) > 0.04 else "中危"
    return _agent.clinical_result(f"确诊: {dx} — {risk}", p, _agent.search_guidelines(dx), alerts=vitals.get("alerts", []))


def bp_plan(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    dx = p.get("diagnosis", "")
    if "心衰" in dx:
        plan = "GDMT四联疗法(ARNI+BB+MRA+SGLT2i) + 限盐 + 体重监测"
    elif "高血压" in dx:
        plan = "CCB/ACEI/ARB + 限盐 + 运动处方"
    else:
        plan = "对症治疗 + 危险因素控制"
    return _agent.clinical_result(f"方案: {plan}", p, _agent.search_guidelines(dx))


def bp_treatment(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    return _agent.clinical_result("治疗执行与监测中", p)


def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    return _agent.clinical_result("慢病随访 — 1/3/6/12月", p, _agent.search_guidelines(p.get("diagnosis", "")))
