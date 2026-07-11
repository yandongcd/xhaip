"""介入治疗科 — KnowledgeAgent-powered clinical reasoning.

Focus: 微创介入诊疗 — PCI, TACE, PTCD, ablation, embolization
GUIDELINES: 中国介入治疗临床指南（2022）
Conditions: 肝癌TACE, 胆道梗阻PTCD, 消化道出血介入, 肿瘤消融, 血管介入

Real clinical concepts: BCLC staging for TACE, contrast nephropathy prevention (Mehran score), PTA/PCI pathways.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="interventional_therapy", department="介入治疗科")
_GUIDELINES = [
    "中国介入治疗临床指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 介入适应症 + 禁忌症筛查 + 凝血评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "介入适应症评估: 肿瘤(TACE/消融) / 血管(PCI/PTA) / 非血管(PTCD/支架)",
        "禁忌症: 严重凝血障碍(PT>18s/PLT<50) / 造影剂过敏 / 未控制的感染",
        f"检验关注: Cr={labs.get('Cr','?')}, PT={labs.get('PT','?')}, ALT={labs.get('ALT','?')}, TBIL={labs.get('TBIL','?')}",
        "造影剂肾病风险评估: eGFR<30 => 水化+停肾毒性药物+减少造影剂剂量(<100mL)",
    ]

    if "肝癌T" in dx or "TACE" in dx.upper():
        findings.insert(0, f"TACE 适应症: BCLC B 期 + Child-Pugh A/B + 无门静脉主干完全闭塞")
    if "胆道梗" in dx:
        findings.insert(0, "胆道梗阻: TBIL > 50umol/L + 胆管扩张 => PTCD/ERBD 胆道引流")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["凝血功能全套", "造影剂过敏试验(非必须但推荐)", "术前水化(NS 1mL/kg/h * 12h)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — 影像导航 + 血管解剖 + 栓塞规划."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    cr = float(labs.get("Cr", 80) or 80)

    findings = [
        "DSA 血管造影: 金标准 — 动脉期/实质期/静脉期 动态评估",
        "CTA/MRA: 术前规划 — 血管分支/变异/侧支循环",
        f"造影剂肾病预防: eGFR 估算 + 水化方案(NS 1mL/kg/h 术前12h+术后24h) | Cr={cr}",
        "栓塞材料: 碘化油(Lipiodol) / 明胶海绵 / PVA颗粒 / Embosphere微球 / N-BCA胶",
        "消融: 射频(RFA)/微波(MWA) — 肿瘤<3cm / 3-5个 / 距重要结构>=1cm",
    ]

    if "肝癌T" in dx:
        findings.insert(0, "TACE 规划: 肝动脉造影(腹腔干/肠系膜上动脉) + 超选择性插管(微导管) + Lipiodol+化疗乳剂")
    if "胆道梗" in dx:
        findings.insert(0, "PTCD: 超声引导(右肝管/左肝管穿刺) + 透视引导 + 导丝通过狭窄段 => 内外引流管")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary=f"介入治疗科 — 诊断评估完成 (S3) | {dx[:30]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["监测 eGFR q12h 术后 48h", "DSA 完整记录(含造影剂用量)", "术后平卧+穿刺点沙袋压迫 6h"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 穿刺路径 + 栓塞/支架规划 + 急救预案."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "穿刺路径: 股动脉(逆行/顺行) / 肱动脉(对侧) / 右侧股静脉(肝静脉压力测定)",
        "导丝/导管选择: 0.035inch J型导丝 + Cobra/Simmons/Yashiro/RH 导管",
        "栓塞/支架规划: 尺寸测量(QCA定量冠脉分析/IVUS) + 球囊/支架(金属裸/药物涂层)",
        "急救预案: 血管破裂/穿孔 => 球囊封堵 + 覆膜支架 / 心包填塞 => 心包穿刺",
        "术前用药: 阿司匹林 300mg + 氯吡格雷 300-600mg (PCI/支架) / 预防性抗生素(胆道引流)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["腹股沟备皮", "留置尿管(预计>2h)", "知情同意(含出血/穿孔/造影剂肾病/辐射风险)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 穿刺出血 + 异位栓塞 + 造影剂肾病."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    cr = float(labs.get("Cr", 80) or 80)
    pt = float(labs.get("PT", 12) or 12)

    checklist = ["穿刺点出血", "异位栓塞", "造影剂肾病", "感染", "肝功能衰竭"]
    findings = [
        f"穿刺点出血: 腹膜后血肿(股动脉后壁) — 腹股沟疼痛+低血压 => 急诊CT+压迫/介入封堵",
        "异位栓塞: 脑梗/截瘫(脊髓动脉栓塞)/肺栓塞 — 选择性插管 + 微导管减少风险",
        f"造影剂肾病(CIN): Cr={cr} PT={pt} — 术后 Cr 升高>=25%/44umol/L, 发生率 2-25%",
        "造影剂过敏: 速发型(<1h荨麻疹/支气管痉挛/过敏性休克)/迟发型(皮肤反应) — 激素+苯海拉明预防",
        "器械并发症: 导丝穿孔/导管打结/球囊破裂(内膜剥离)/支架脱载",
    ]
    findings.append(f"高危审核: {len(checklist)} 项")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["备 FDG-6 封堵器(大血管破裂)", "血管活性药物(多巴胺/去甲肾上腺素 推泵)", "心电监护+血氧+血压 q5min"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 介入+外科+肿瘤+消化 多学科方案."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 介入科 + 肿瘤内科 + 放射科 + 肝病科/消化科 + ICU",
        "TACE 策略: 常规(cTACE: Lipiodol+化疗) / DEB-TACE(载药微球) — DEB-TACE 局部肿瘤控制更好/全身毒性更低",
        "联合治疗: TACE + 消融(消融+栓塞协同) / TACE + 系统治疗(T+A方案/Atezo+Bev)",
        "PTCD/支架: 外引流 -> 内外引流 -> 胆道支架(自膨式金属/塑料) — 逐步升级",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["个体化: TACE 周期 4-6w + 影像评估(mRECIST)", "介入 vs 外科 适应症边界明确"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """介入操作执行 — 血管/非血管介入."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "Seldinger 穿刺: 穿刺针45度 / 导丝(0.035inch)进入 / 导管鞘+扩张器 / 导管-导丝交换",
        "TACE: 超选择性肝动脉插管 + Lipiodol(5-20mL) + 化疗药(表柔比星50mg+顺铂40mg) + 明胶海绵/PVA栓塞",
        "PTA/PCI: 球囊扩张(6-12atm / 30-90s) + 支架释放(10-12atm 后扩) — TIMI 3级血流为目标",
        "PTCD: 22G穿刺针超声引导 -> 0.018导丝 -> 鞘管 -> 0.035导丝 -> 8.5F引流管(内外)",
        "术后: 穿刺点压迫 10-15min + 弹力绷带加压 6h / 血管闭合器(Angio-Seal/Perclose)可缩短制动",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 介入操作执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术后平卧制动 6-12h(手动压迫)/2h(Angio-Seal)", "穿刺点监测 q15min * 4 => q30min * 4 => q1h"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围介入期护理 — 穿刺点 + 生命体征 + 体位制动."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "穿刺点: 观察血肿/渗血/假性动脉瘤(+搏动性肿块+血管杂音) — 记录腹股沟周径",
        "远端灌注: 足背动脉/胫后动脉搏动 + 皮温/肤色 — 每 15min * 4 次",
        "造影剂排泄: 鼓励饮水(1500-2000mL/24h) / 静脉补液(NS 100-150mL/h 24h)",
        "排尿: 术后 6h 排尿困难 => 临时导尿 / 膀胱扫描",
        "疼痛: 栓塞后综合征(发热/疼痛/恶心) — 对乙酰氨基酚/NSAIDs + 甲氧氯普胺(止吐)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 围介入期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术后 24h 复查 Cr(造影剂肾病)", "出院指导: 穿刺点自检/活动限制 48h/复诊时间"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """治疗后随访 — 影像评估 + 肿瘤反应 + 支架通畅."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "影像评估: TACE 后 4-6w CT/MRI — mRECIST 评估(CR/PR/SD/PD)",
        "肿瘤反应: 碘化油沉积(肿瘤内致密积聚) + 强化区(存活/新发) => 决定下次 TACE 时机",
        "支架通畅: 彩色多普勒/CTA — 支架内再狭窄(ISR) >50% => 球囊扩张/再支架",
        "肝功能: ALT/AST/TBIL q4w — TACE 后一过性升高(栓塞后肝炎) -> 1-2w 恢复",
    ]

    recommendations = [
        "TACE: 每 6-8w 重复评估 + 重复 TACE(如需要) — 直至最佳反应/疾病进展/肝功能恶化",
        "消融: 术后 1m/3m/6m CT/MRI — 消融区无增强=>完全坏死",
        "支架: 抗血小板(阿司匹林+氯吡格雷 1-6月) + 三高控制",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("介入")
    return _agent.clinical_result(
        summary="介入治疗科 — 治疗后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
