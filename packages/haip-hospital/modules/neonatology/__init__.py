"""新生儿科 — KnowledgeAgent-powered clinical reasoning.

Focus: 新生儿疾病筛查与重症救治
GUIDELINES: 中国新生儿临床诊疗指南（2022）, ESPEN Guidelines on Clinical Nutrition
Conditions: 新生儿窒息, 早产儿管理, 新生儿黄疸, 新生儿败血症, NRDS
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="neonatology", department="新生儿科")
_GUIDELINES = [
    "中国新生儿临床诊疗指南（2022）",
    "ESPEN Guidelines on Clinical Nutrition",
]

_agent.rule_engine.load_all()




def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_reception(**kwargs) -> dict:
    """接诊评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["Apgar评分", "孕周/出生体重", "分娩方式", "高危因素"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—新生儿入院评估完成 (stage S1)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_exam(**kwargs) -> dict:
    """专项检查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["血气分析", "血糖监测", "胆红素", "感染指标", "心脏超声"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—新生儿专项检查完成 (stage S2)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断分级."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["黄疸分度", "RDS分期", "HIE分级", "感染定位"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—疾病诊断完成 (stage S3)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_treatment(**kwargs) -> dict:
    """分娩/治疗执行."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["蓝光治疗", "PS替代", "抗感染", "营养支持", "体温管理"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—新生儿治疗完成 (stage S4)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_nursing(**kwargs) -> dict:
    """产后/儿科护理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["产后/儿科护理完成"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—产后/儿科护理完成 (stage S1)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )


def bp_followup(**kwargs) -> dict:
    """随访与保健."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    findings = ["神经发育", "听力筛查", "ROP筛查", "疫苗接种"]
    dx = p.get("diagnosis", "")
    if "新生儿" in dx or "早产儿" in dx:
        findings.insert(0, "新生儿窒息/早产儿管理 疾病匹配")
    checklist = ["呼吸暂停", "血氧下降", "喂养不耐受", "体温不稳", "惊厥"]
    findings.append(f"高危审核: {len(checklist)} 项")
    # 专科检验关注: TSB, CRP, PCT, 血糖
    if vitals.get("alerts"):
        findings.append("检验异常需关注")
    guides = _agent.search_guidelines(p.get("diagnosis", "")) or ["中国新生儿临床诊疗指南（2022）", "ESPEN Guidelines on Clinical Nutrition"]
    rules = _agent.search_rules("新生儿科")
    return _agent.clinical_result(
        summary="新生儿科—新生儿随访完成 (stage S5)",
        patient=p,
        guidelines=guides,
        rules=rules,
        alerts=vitals.get("alerts", []),
    )
