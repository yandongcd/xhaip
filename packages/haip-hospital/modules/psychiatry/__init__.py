"""精神心理科 — KnowledgeAgent-powered clinical reasoning.

Focus: 精神心理疾病 — depression, anxiety, schizophrenia, bipolar, suicide prevention
GUIDELINES: 中国精神障碍防治指南（2023）
Conditions: 抑郁症, 焦虑症, 精神分裂症, 双相情感障碍, 创伤后应激障碍

Real clinical tools: PHQ-9, GAD-7, HAM-D/HAM-A, BPRS, YMRS, C-SSRS suicide risk.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="psychiatry", department="精神心理科")
_GUIDELINES = [
    "中国精神障碍防治指南（2023）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊评估 — 情绪状态 + 精神症状 + 自杀风险 + 社会功能."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    phq9 = int(labs.get("PHQ9", 10) or 10)
    gad7 = int(labs.get("GAD7", 8) or 8)

    findings = [
        f"PHQ-9 抑郁筛查: {phq9}/27 — {'轻度(5-9)' if phq9<10 else '中度(10-14)' if phq9<15 else '中重度(15-19)' if phq9<20 else '重度(20-27)'}",
        f"GAD-7 焦虑筛查: {gad7}/21 — {'轻度(5-9)' if gad7<10 else '中度(10-14)' if gad7<15 else '重度(15-21)'}",
        "自杀风险评估: C-SSRS(哥伦比亚自杀严重程度量表) — 意念/计划/行为/手段/保护因素",
        "精神症状: 幻觉(幻听/幻视)/妄想(被害/关系/被控制)/思维障碍/自知力(CGI-S)",
        "社会功能: GAF(功能大体评定量表 1-100) / SDS(社会功能缺陷) / 职业/家庭/人际关系",
    ]

    if phq9 >= 20:
        findings.insert(0, f"重度抑郁(PHQ-9={phq9}): 需要立即精神科评估 + 安全计划")
    if "自杀" in dx or phq9 >= 15:
        findings.insert(0, "自杀风险: C-SSRS 紧急评估 + 一人陪护 + 环境安全(移除危险物品)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("精神")
    return _agent.clinical_result(
        summary=f"精神心理科 — 接诊评估完成 (S1) | PHQ-9={phq9} GAD-7={gad7}",
        patient=p, stage="S1", findings=findings,
        recommendations=["PHQ-9 + GAD-7 初筛", "安全评估: 自杀/自伤/伤人风险", "躯体疾病排查(甲功/维生素B12/神经系统)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """检查检验 — 量表评估 + 认知测试 + 心理评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "量表评估: HAM-D(汉密尔顿抑郁)/HAM-A(焦虑)/BPRS(简明精神病)/YMRS(躁狂)/SCID-5(结构式临床访谈)",
        "认知测试: MMSE(简易智能)/MoCA(蒙特利尔)/WAIS-IV(韦氏成人智力) — 排除认知障碍",
        "心理评估: 人格(MMPI-2/MCMI-IV) + 防御机制 + 应对方式(CSQ)",
        "躯体检查: 甲状腺功能(TSH) + 维生素 B12/叶酸 + 性激素 + 血常规/生化 / EEG(排除颞叶癫痫)",
        "药物监测: 血药浓度(锂 0.6-1.2 / 丙戊酸 50-100 / 氯氮平 350-600 ng/mL) + 肝肾功能/代谢(血糖/血脂)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("精神")
    return _agent.clinical_result(
        summary="精神心理科 — 检查检验完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["DSM-5/ICD-11 诊断访谈(SCID)", "排除器质性精神障碍(影像/EEG/实验室)", "神经心理测查(记忆/执行功能/注意)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — DSM-5/ICD-11 + 严重程度 + 共病评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "DSM-5/ICD-11 诊断标准: 症状数量 + 持续时间 + 功能损害 + 排除其他",
        "严重程度: 轻度(轻微功能损害)/中度(介于轻-重之间)/重度(显著功能损害+多种症状)",
        "共病评估: 物质使用障碍(烟草/酒精/药物) + 人格障碍 + 焦虑-抑郁共病(最常见)",
        "鉴别诊断: 双相障碍(青春/产后首发 轻躁狂史) / 精神病性(精神分裂症谱系) / 器质性(甲功/脑病)",
    ]

    if "抑郁" in dx:
        findings.insert(0, "重度抑郁发作(MDD): 至少 2w + 5/9 症状(含情绪低落或兴趣减退) + 无助/无望/无价值感")
    if "焦虑" in dx:
        findings.insert(0, "广泛性焦虑障碍(GAD): >=6m + 至少 3/6(含不安/易疲/注意力难/激惹/肌紧张/失眠)")
    if "精神分" in dx or "schizo" in dx.lower():
        findings.insert(0, "精神分裂症: >=1m(DSM-5 at least 6m总病程) + >=2 项(幻觉/妄想/思维紊乱/阴性症状/紧张症)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("精神")
    return _agent.clinical_result(
        summary=f"精神心理科 — 诊断确认完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["DSM-5 诊断确认 + 共病评估", "治疗目标制定(症状缓解率+功能恢复)", "知情同意(药物不良反应/疗效预期/非药物选择)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行 — 药物治疗 + 心理治疗 + 物理治疗 + 社会干预."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "药物治疗: SSRI(舍曲林/艾司西酞普兰 一线) / SNRI(文拉法辛/度洛西汀) / 米氮平 / 安非他酮",
        "抗精神病药: 第二代(SGA: 奥氮平/利培酮/阿立哌唑/喹硫平) 首选 — 代谢综合征监测(血糖/血脂/体重 q3m)",
        "心境稳定剂: 锂盐(双相首选 血药浓度0.6-1.2) + 丙戊酸/拉莫三嗪/卡马西平",
        "心理治疗: CBT(认知行为 抑郁/焦虑一线 12-20次) / IPT(人际心理治疗) / DBT(边缘型人格障碍) / 行为激活",
        "物理治疗: MECT(改良电休克 严重抑郁/自杀/紧张症) / rTMS(重复经颅磁 左侧DLPFC 高频) / 深部脑刺激(DBS 难治性)",
        "社会干预: 家庭治疗 + 职业康复(支持性就业) + 个案管理(ACT/FACT 严重精神障碍)",
    ]

    if "抑郁" in dx:
        findings.insert(0, "MDD: SSRI 4-8w 评估 => 无效则换 SNRI/米氮平/安非他酮 + CBT/IPT 联合")
    if "精神分" in dx:
        findings.insert(0, "精神分裂症: SGA 4-6w 评估 => 无效换药/增效/氯氮平(难治性)+ CST(认知适应训练)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("精神")
    return _agent.clinical_result(
        summary="精神心理科 — 治疗执行完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["监测: 第1月 q1-2w => 稳定后 q1-3m", "血药浓度(锂/丙戊酸/氯氮平)", "代谢综合征监测(体重/腰围/血糖/血脂)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访管理 — 症状变化 + 药物依从 + 社会功能 + 复发预防."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "症状变化: PHQ-9/GAD-7/BPRS/YMRS 每月 — 缓解标准(PHQ-9<5/GAD-7<5) / 复燃(症状再现 4m内)/复发(新发作)",
        "药物依从: Morisky 8 项量表(MMAS-8) — 低依从率(非依从 30-50%) 主要复发原因",
        "社会功能: SDS / GAF 恢复 + 职业/学习/人际功能 — 康复(社会技能训练/职业康复/同伴支持)",
        "复发预防: MDD 首发 用药 6-12m / 多次发作 >= 2-3y(长期维持) + CBT 预防复发",
    ]

    recommendations = [
        "稳定期: q1-3m 复诊 + 量表监测 + 血药浓度",
        "减/停药: 至少 6m(首发) / 2y+(复发) 缓解期 — 逐渐减量(缓慢 taper 4-8w+)",
        "心理治疗: CBT/IPT 维持(每月 1 次 booster session)",
        "监测: 体重/腰围/血糖/血脂/肝肾功能 q3-6m + ECG(QTc) 每年",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("精神")
    return _agent.clinical_result(
        summary="精神心理科 — 随访管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
