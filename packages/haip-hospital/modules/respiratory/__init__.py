"""呼吸内科 — KnowledgeAgent-powered clinical reasoning.

GUIDELINES: GOLD 2024 (COPD), GINA 2024 (Asthma)
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="respiratory", department="呼吸内科")
_guidelines = ["GOLD 2024 慢性阻塞性肺疾病全球倡议", "GINA 2024 哮喘管理和预防全球策略"]


def bp_reception(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    dx = p.get("diagnosis", "")
    guides = _agent.search_guidelines("COPD" if "COPD" in dx else "asthma" if "哮喘" in dx else dx) or _guidelines
    return _agent.clinical_result(f"接诊评估完成 — {dx}", p, guides)


def bp_exam(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    labs = p.get("lab_results", {})
    findings = [f"{k}: {v}" for k, v in list(labs.items())[:5]]
    return {"status": "ok", "patient_id": pid, "summary": "辅助检查完成",
            "key_findings": findings,
            "recommendations": ["肺功能检查", "胸部CT", "血气分析"] if "COPD" in p.get("diagnosis", "")
            else ["肺功能检查", "过敏原检测", "胸部X线"]}


def bp_diagnosis(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    dx = p.get("diagnosis", "")
    vitals = _agent.assess_vitals(p)
    severity = "重度" if len(vitals.get("alerts", [])) >= 2 else "中度" if vitals.get("alerts") else "轻度"
    return _agent.clinical_result(f"确诊: {dx} — {severity}", p, _agent.search_guidelines(dx))


def bp_plan(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    dx = p.get("diagnosis", "")
    if "COPD" in dx:
        plan = "LAMA/LABA + ICS + 肺康复 + LTOT"
    elif "哮喘" in dx:
        plan = "ICS + 按需SABA + 过敏原规避"
    elif "肺炎" in dx:
        plan = "抗生素 + 支持治疗 + 氧疗"
    else:
        plan = "对症治疗 + 定期随访"
    return _agent.clinical_result(f"方案: {plan}", p, _agent.search_guidelines(dx))


def bp_treatment(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    return _agent.clinical_result("治疗执行中 — 监测生命体征与化验指标", p)


def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return {"status": "error", "error": f"Patient {pid} not found"}
    return _agent.clinical_result("随访计划 — 1/3/6/12月定期复查", p)
