"""风湿免疫科 — KnowledgeAgent-powered clinical reasoning.

Focus: 自身免疫性疾病诊疗
GUIDELINES: 中国风湿免疫病诊疗指南（2022）, EULAR Recommendations for Rheumatic Diseases (2023)
Conditions: 类风湿关节炎, SLE, 强直性脊柱炎, 干燥综合征, 痛风
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="rheumatology", department="风湿免疫科")
_GUIDELINES = [
    "中国风湿免疫病诊疗指南（2022）",
    "EULAR Recommendations for Rheumatic Diseases (2023)",
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
    findings = ["关节肿痛", "皮疹", "雷诺现象", "口干眼干", "发热"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—风湿科初诊完成 (stage S1)",
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
    findings = ["ANA/ENA", "RF/anti-CCP", "HLA-B27", "补体", "炎性指标"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—免疫学检查完成 (stage S2)",
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
    findings = ["ACR/EULAR分类标准", "疾病活动度", "器官受累评估"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—确诊分型完成 (stage S3)",
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
    findings = ["DMARDs", "生物制剂", "糖皮质激素", "靶向合成DMARDs"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—治疗计划完成 (stage S4a)",
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
    findings = ["免疫抑制监测", "感染筛查", "疫苗接种", "骨质疏松预防"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—治疗执行完成 (stage S4b)",
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
    findings = ["疾病活动度", "药物不良反应", "器官损伤", "生活质量"]
    dx = p.get("diagnosis", "")
    if "类风湿" in dx or "SLE" in dx:
        findings.insert(0, "类风湿关节炎/SLE 疾病匹配")
    checklist = ["狼疮危象", "严重感染", "肾上腺危象", "急性肾损伤", "肺出血"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: ESR, CRP, ANA, 抗dsDNA
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国风湿免疫病诊疗指南（2022）", "EULAR Recommendations for Rheumatic Diseases (2023)"]
    rules = _agent.search_rules("风湿免疫科")
    return _agent.clinical_result(
        summary="风湿免疫科—慢病管理完成 (stage S5)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )
