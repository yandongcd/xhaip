"""内分泌科 — KnowledgeAgent-powered clinical reasoning.

Focus: 内分泌代谢疾病管理
GUIDELINES: 中国糖尿病防治指南（2024版）, ADA Standards of Care in Diabetes
Conditions: 2型糖尿病, 1型糖尿病, 甲状腺疾病, 骨质疏松, 肥胖症
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="endocrinology", department="内分泌科")
_GUIDELINES = [
    "中国糖尿病防治指南（2024版）",
    "ADA Standards of Care in Diabetes",
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
    findings = ["血糖水平", "体重变化", "多饮多尿", "甲状腺体征"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—内分泌初诊完成 (stage S1)",
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
    findings = ["血糖/OGTT", "HbA1c", "甲状腺功能", "骨密度", "肾上腺功能"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—内分泌检查完成 (stage S2)",
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
    findings = ["糖尿病分型", "甲功分类", "代谢综合征", "并发症筛查"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—疾病诊断完成 (stage S3)",
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
    findings = ["降糖方案", "甲状腺激素", "抗骨质疏松", "生活方式干预"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—治疗计划完成 (stage S4a)",
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
    findings = ["血糖监测", "胰岛素调整", "甲功监测", "药物不良反应"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—治疗执行完成 (stage S4b)",
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
    findings = ["HbA1c趋势", "并发症筛查", "生活方式依从", "甲功"]
    dx = p.get("diagnosis", "")
    if "2型糖" in dx or "1型糖" in dx:
        findings.insert(0, "2型糖尿病/1型糖尿病 疾病匹配")
    checklist = ["DKA", "低血糖昏迷", "甲亢危象", "肾上腺危象", "高钙危象"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: FPG, HbA1c, TSH, FT3
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国糖尿病防治指南（2024版）", "ADA Standards of Care in Diabetes"]
    rules = _agent.search_rules("内分泌科")
    return _agent.clinical_result(
        summary="内分泌科—慢病随访完成 (stage S5)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )
