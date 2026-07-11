"""皮肤科 — KnowledgeAgent-powered clinical reasoning.

Focus: 常见皮肤病诊疗 — eczema, psoriasis, urticaria, skin infection, skin cancer screening
GUIDELINES: 中国皮肤科临床诊疗指南（2022）
Conditions: 湿疹/特应性皮炎, 银屑病, 荨麻疹, 皮肤感染, 皮肤肿瘤

Real clinical scoring: SCORAD (eczema), PASI/BSA (psoriasis), UAS7 (urticaria), ABCDE melanoma.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="dermatology", department="皮肤科")
_GUIDELINES = [
    "中国皮肤科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reception(**kwargs) -> dict:
    """接诊评估 — 皮疹分布 + 瘙痒程度 + 病程 + 用药史."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "皮疹分布: 局限/泛发 + 好发部位(屈侧/伸侧/头皮/指甲/黏膜) — 对称性?",
        "瘙痒程度: NRS(0-10 数字评分) — 影响睡眠(是/否) + 搔抓痕迹/苔藓化",
        "病程: 急性(<6w)/慢性(>6w) + 诱因(食物/药物/感染/应激/环境) + 既往发作",
        "用药史: 外用(激素名称/强度/疗程) + 口服(抗组胺/激素/免疫抑制剂/生物制剂) + 不良反应",
        f"生命体征: {'异常' if vitals.get('alerts') else '正常'}",
    ]

    if "湿疹" in dx or "特应性" in dx or "AD" in dx.upper():
        findings.insert(0, f"AD 初筛: SCORAD 评分(范围/严重度/主观症状) + EASI 评分 + 瘙痒 NRS={labs.get('NRS','?')}")
    if "银屑" in dx or "psorias" in dx.lower():
        findings.insert(0, f"银屑病: BSA(体表面积)={labs.get('BSA','?')}% + PASI={labs.get('PASI','?')} + DLQI 生活质量")
    if "荨麻" in dx or "urticaria" in dx.lower():
        findings.insert(0, f"荨麻疹: UAS7={labs.get('UAS7','?')} — 每周风团+瘙痒总和(0-42) + 急性(<6w)/慢性(>6w)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("皮肤")
    return _agent.clinical_result(
        summary=f"皮肤科 — 接诊评估完成 (S1) | {dx[:20]}",
        patient=p, stage="S1", findings=findings,
        recommendations=["皮肤镜检查(皮损放大+偏光)", "过敏原(食物+吸入+接触 斑贴/点刺/IgE)", "皮肤刮屑(真菌镜检 KOH)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """检查检验 — 皮损形态 + BSA 评估 + 皮肤镜 + 过敏原."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "皮损形态: 原发(斑/丘疹/结节/水疱/脓疱/风团) + 继发(鳞屑/糜烂/溃疡/皲裂/苔藓化/瘢痕)",
        "BSA 估算: 手掌法(1个手掌面+五指=1% BSA) — 银屑病 BSA<3%(轻度)/3-10%(中度)/>10%(重度)",
        "皮肤镜: 色素性病变(良性痣 网格/球状/均质)  vs 黑色素瘤(不典型色素网/蓝白幕/不规则点/球/退化结构)",
        "过敏原检测: 斑贴试验(接触性皮炎 AD 48/72/96h 判读) + 点刺试验(荨麻疹 速发型) + 血清 IgE(总+特异性)",
        "其他: Wood 灯(白癜风/真菌/卟啉) + 皮肤刮屑(KOH 直接镜检 真菌菌丝/孢子) + 醋酸白试验(HPV 尖锐湿疣 5min)",
    ]

    if "皮肤肿" in dx or "黑色素" in dx:
        findings.insert(0, "ABCDE 筛查: Asymmetry(不对称)/Border(不规则)/Color(不均一)/Diameter(>6mm)/Evolving(变化) => 活检")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("皮肤")
    return _agent.clinical_result(
        summary="皮肤科 — 检查检验完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["皮肤活检(钻孔 3-4mm/切除) 病理+免疫组化", "血清自身抗体(天疱疮/类天疱疮/红斑狼疮)", "感染筛查(细菌/真菌培养+药敏)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """诊断确认 — SCORAD/PASI/UAS7 分级 + 鉴别诊断."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    scorad = int(labs.get("SCORAD", 25) or 25)
    pasi = int(labs.get("PASI", 8) or 8)
    bsa = float(labs.get("BSA", 5) or 5)

    findings = [
        f"SCORAD 评分: {scorad} — {'轻度(<25)' if scorad<25 else '中度(25-50)' if scorad<50 else '重度(>50)'} 特应性皮炎",
        f"PASI/BSA: PASI={pasi} / BSA={bsa}% — {'轻度(BSA<3+临床症状轻)' if pasi<3 else '中度(BSA 3-10)' if bsa<10 else '重度(BSA>10+PASI>10+DLQI>10)'} 银屑病",
        "荨麻疹: UAS7(UAS7=0-6 控制良好/7-15 轻度/16-27 中度/>=28 重度) + CU-index(ASST 自体血清皮肤试验 + 嗜碱性粒细胞活化)",
        "鉴别诊断: AD vs 接触性皮炎/脂溢性/银屑病 + 银屑病 vs 扁平苔藓/毛发红糠疹 + 皮肤感染(细菌vs真菌vs病毒vs寄生虫)",
        "外用激素强度分级: VII级(超强 氯倍他索/卤米松) -> I级(弱效 氢化可的松 1%) — 部位/年龄/面积选择",
    ]

    if "AD" in dx.upper() or "湿疹" in dx:
        findings.insert(0, f"AD: SCORAD={scorad} => 阶梯治疗(基础保湿+外用激素/钙调神经磷酸酶抑制剂+光疗+系统性)")
    if "银屑" in dx:
        findings.insert(0, f"银屑病: PASI={pasi}/BSA={bsa}% => 轻度(外用药)/中度(光疗+系统)/重度(生物制剂/小分子)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("皮肤")
    return _agent.clinical_result(
        summary=f"皮肤科 — 诊断确认完成 (S3) | SCORAD={scorad} PASI={pasi}",
        patient=p, stage="S3", findings=findings,
        recommendations=["皮肤活检(病理HE+特殊染色+免疫荧光)", "血液: 嗜酸粒细胞/IgE/ANA/抗dsDNA/ANCA/HIV/梅毒(鉴别)", "感染: 细菌+真菌培养+药敏"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗执行 — 外用药 + 系统用药 + 光疗 + 生物制剂."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "外用药: 保湿剂(AD 基础 每日至少 2 次) + 外用激素(强度匹配皮损+部位) + 钙调神经磷酸酶抑制剂(他克莫司/吡美莫司 面部/褶皱区)",
        "系统用药: 抗组胺(荨麻疹 西替利嗪/非索非那定 一线) + 免疫抑制剂(MTX/环孢素/硫唑嘌呤/吗替麦考酚酯 中重度)",
        "光疗: NB-UVB(311nm 银屑病/AD/白癜风一线光疗) + PUVA(补骨脂素+UVA 二线) + UVA1(硬皮病/特应性皮炎)",
        "生物制剂: 银屑病(IL-17i 司库奇尤/IL-23i 古塞库/Guselkumab/TNFi) / AD(dupilumab IL-4Rα) / 荨麻疹(omalizumab IgE)",
        "小分子: PDE4i(阿普米司特 银屑病/白塞) / JAKi(巴瑞替尼/乌帕替尼/阿布昔替尼 AD/银屑病/斑秃)",
    ]

    if "感染" in dx:
        findings.insert(0, "皮肤感染: 细菌(头孢氨苄/莫匹罗星) + 真菌(特比萘芬/酮康唑) + 病毒(阿昔洛韦/伐昔洛韦) + 寄生虫(伊维菌素/硫磺乳膏)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("皮肤")
    return _agent.clinical_result(
        summary="皮肤科 — 治疗执行完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["TB/肝炎 HIV 筛查(生物制剂前)", "光防护(SPF50+ PA+++ 每日)", "保湿剂+避免刺激(AD长期管理)", "治疗目标: PASI75/90/EASI75/SCORAD50"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """随访管理 — 疗效评估 + 复发监测 + 不良反应 + 生活指导."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "疗效评估: PASI 75/90/100(银屑病 12w) / EASI 75/90(AD) / UAS7<=6(或 MCID MCID 10-11) 荨麻疹 / SCORAD 改善 50%",
        "复发监测: 诱因(应激/感染/药物/酒精) + 减量后复发 => 调整方案(升级/联合/换药)",
        "不良反应: 外用激素(皮肤萎缩/萎缩纹/毛细血管扩张/激素依赖) + 免疫抑制剂(肝肾功能+血压+血象 q1-3m)",
        "生活指导: 皮肤护理(保湿+温和洁面+避免过热水/过度清洁) + 饮食(排除过敏原 但不应无依据盲目禁食)",
    ]

    recommendations = [
        "AD: 长期保湿(基础)+外用药物(按需)+避免触发物+每年随访+疫苗(灭活疫苗安全)",
        "银屑病: 定期 PASI+DLQI q3-6m + 共病筛查(银屑病关节炎 PsA 10-30% + 心血管/代谢综合征) + 生物制剂 TB/HBV 再激活监测",
        "荨麻疹: 治疗目标: 无症状+无荨麻疹=UAS7=0 / 完全控制; 慢性需评估 3-6m 减量/停药可能性",
        "皮肤癌筛查: 每年全身皮肤检查(皮肤镜) 高危(光损伤/免疫抑制/家族史/多痣)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("皮肤")
    return _agent.clinical_result(
        summary="皮肤科 — 随访管理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
