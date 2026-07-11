"""老年病科 — KnowledgeAgent-powered clinical reasoning.

Focus: 老年综合征管理与多病共存
GUIDELINES: 中国老年医学临床诊疗指南（2023）, 老年髋部骨折围手术期衰弱护理管理专家共识
Conditions: 老年衰弱, 认知障碍, 跌倒, 多重用药, 营养不良
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="geriatrics", department="老年病科")
_GUIDELINES = [
    "中国老年医学临床诊疗指南（2023）",
    "老年髋部骨折围手术期衰弱护理管理专家共识",
]

_agent.rule_engine.load_all()




def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊与初步评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["CGA评估", "ADL/IADL", "跌倒风险", "认知筛查", "营养评估"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—老年综合评估完成 (stage S1)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_exam(**kwargs) -> dict:
    """辅助检查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["认知量表", "步态评估", "骨密度", "听力视力", "多重用药审查"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—老年专项检查完成 (stage S2)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊与分型分期."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["衰弱分级", "认知障碍分期", "肌少症诊断", "营养不良分级"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—老年综合征诊断完成 (stage S3)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_plan(**kwargs) -> dict:
    """治疗方案制定."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["运动处方", "营养支持", "药物精简", "认知训练", "防跌倒"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—综合干预完成 (stage S4a)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行与监测."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["慢病管理", "康复训练", "照护计划", "社会支持"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—治疗执行完成 (stage S4b)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_followup(**kwargs) -> dict:
    """随访与长期管理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["功能状态变化", "认知轨迹", "再住院", "照护者负担"]
    dx = p.get("diagnosis", "")
    if "老年衰" in dx or "认知障" in dx:
        findings.insert(0, "老年衰弱/认知障碍 疾病匹配")
    checklist = ["跌倒", "谵妄", "ADL下降", "体重下降>5%", "多重用药≥5种"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: Hb, ALB, 25(OH)D, Cr
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国老年医学临床诊疗指南（2023）", "老年髋部骨折围手术期衰弱护理管理专家共识"]
    rules = _agent.search_rules("老年病科")
    return _agent.clinical_result(
        summary=f"老年病科—长期随访完成 (stage S5)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )
