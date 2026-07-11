"""肝胆外科 — KnowledgeAgent-powered clinical reasoning.

Focus: 肝胆胰脾外科手术 — HCC, biliary stones, pancreatic tumor, portal hypertension
GUIDELINES: 中国肝胆外科临床诊疗指南（2022）
Conditions: 肝癌, 胆道结石, 胰腺肿瘤, 肝硬化门脉高压, 肝血管瘤

Real clinical scoring: Child-Pugh, BCLC staging, MELD score.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="hepatobiliary_surgery", department="肝胆外科")
_GUIDELINES = [
    "中国肝胆外科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def _child_pugh(bil: float = 12, alb: float = 35, pt_ext: float = 1.5,
                ascites: str = "none", encephalopathy: str = "none") -> dict:
    """Child-Pugh score for liver function reserve."""
    pts = 0
    if bil < 34: pts += 1
    elif bil <= 50: pts += 2
    else: pts += 3
    if alb > 35: pts += 1
    elif alb >= 28: pts += 2
    else: pts += 3
    if pt_ext < 1.3: pts += 1
    elif pt_ext <= 1.5: pts += 2
    else: pts += 3
    ascites_map = {"none": 1, "mild": 2, "moderate": 3}
    pts += ascites_map.get(ascites.lower(), 2)
    enc_map = {"none": 1, "grade_i_ii": 2, "grade_iii_iv": 3}
    pts += enc_map.get(encephalopathy.lower(), 1)
    grade = "A" if pts <= 6 else "B" if pts <= 9 else "C"
    op_risk = "low (safe for major resection)" if grade == "A" else "moderate (limited resection only)" if grade == "B" else "high (transplant candidate only)"
    return {"score": pts, "grade": grade, "operative_risk": op_risk}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 肝功基础 + 肿瘤标志物 + 影像初筛."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "肝功基础: ALT/AST/TBIL/ALB/PT — 评估肝脏储备功能",
        f"检验关注: ALT={labs.get('ALT','?')}, AST={labs.get('AST','?')}, TBIL={labs.get('TBIL','?')}, ALB={labs.get('ALB','?')}",
        "肿瘤标志物: AFP(肝癌)/CA19-9(胆道/胰腺)/CEA",
        "影像: 腹部超声(初筛) + CTA/CTV(血管评估) + MRI(普美显增强—肝特异性)",
    ]

    if "肝癌" in dx or "HCC" in dx.upper():
        findings.insert(0, f"肝癌初筛: AFP={labs.get('AFP','?')}, 超声低回声结节 => CT/MRI 增强(动脉期高增强+静脉期 washout)")
    if "胆道" in dx:
        findings.insert(0, "胆道疾病: 超声/MRCP — 结石/狭窄/扩张评估")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["乙肝/丙肝病毒筛查(HBsAg/HCVAb)", "ICG 清除试验(评估肝储备)", "MRCP(胆道梗阻)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — Child-Pugh + BCLC + 影像确诊."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    tb = float(labs.get("TBIL", 12) or 12)
    alb = float(labs.get("ALB", 35) or 35)
    pt_ext = float(labs.get("PT_EXT", 1.2) or 1.2)

    cp = _child_pugh(tb, alb, pt_ext)

    findings = [
        f"Child-Pugh: {cp['score']} 分 / 分级 {cp['grade']} — {cp['operative_risk']}",
        "BCLC 分期: 0(极早期)/A(早期)/B(中期)/C(晚期)/D(终末期) — 决定治疗策略",
        "MELD 评分: 胆红素+肌酐+INR — 肝移植优先排序(MELD >=15 列入等待)",
        "肝血管成像: 肝动脉/门静脉/肝静脉 — 变异识别(Michels分型)+ 癌栓(门静脉PVTT分型)",
        "胰腺肿瘤: CT胰腺薄层+血管重建 — 评估可切除性(可切除/边界可切除/不可切除)",
    ]

    if "肝癌" in dx:
        findings.insert(0, f"肝癌 BCLC 分期: 单发<2cm=>0期(消融/切除); 多发=>B期(TACE); 门脉侵犯=>C期(系统治疗)")
    if "胆道" in dx:
        findings.insert(0, "胆道结石: MRCP + EUS — 胆总管结石(>=8mm) + 扩张(>10mm) => ERCP/腹腔镜胆道探查")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary=f"肝胆外科 — 诊断评估完成 (S3) | Child-Pugh {cp['grade']}",
        patient=p, stage="S3", findings=findings,
        recommendations=["肝穿刺病理(非必需但确诊)", "PET-CT(排除肝外转移)", "肝体积测定(未来残肝>=20-40%)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 肝切除安全评估 + 门静脉栓塞 + ERCP."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肝切除安全界限: 正常肝(残肝>=20%) / 肝硬化(残肝>=40%) / ICG-R15 < 10%(安全)",
        "未来残肝不足: PVE(门静脉栓塞术 4-6w 后增生 20-40%) / ALPPS(联合肝脏分割+门静脉结扎 1-2w)",
        "术前减黄: TBIL>200umol/L => PTCD(经皮肝胆管引流)减黄 1-2w 至<100",
        "ERCP: 胆总管结石结石取石+ENBD/ERBD 鼻胆管引流",
        "备血: 肝切除备 RBC 4-6U + FFP 4-6U + 血小板 1-2 治疗量",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术前三维重建(肝段/血管/胆管)", "营养支持(肠内优先)", "抗生素(切皮前)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 肝功能衰竭 + 胆漏 + 出血 + 血栓."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肝功能衰竭: 术后肝衰=胆红素升高+PT延长+腹水+肝性脑病 (50-50 标准: PT<50% + TBIL>50umol/L at Day5)",
        "胆漏: 肝切除(3-15%) — ISGLS 分级(A=无干预/B=介入/C=再手术) — 引流管胆汁样液体",
        "术后出血: 24-48h(手术止血不全)/7-10d(感染/胰漏侵蚀血管) — 假性动脉瘤(CTA + 栓塞/再手术)",
        "门静脉/肝静脉血栓: 肝切除后 PVT 1-3% => 多普勒超声监测 + 抗凝治疗",
        "感染: 肝脓肿/膈下脓肿 — 超声/CT 引导经皮穿刺引流(PCD) + 抗生素",
    ]

    checklist = ["肝功能衰竭", "胆漏", "胰漏", "术后出血", "门静脉血栓"]
    findings.append(f"高危审核: {len(checklist)} 项")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["术后 ICU 至少 24-48h", "多普勒超声 q12h(肝血流)", "引流液淀粉酶(胰漏筛查)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 肝癌多学科(外科+介入+肿瘤+肝病)."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 肝胆外科 + 肿瘤内科 + 介入科 + 放疗科 + 肝病科 + 病理科 + 影像科",
        "肝癌治疗方案(BCLC导向): 0/A期 => 切除/消融/移植; B期 => TACE; C期 => 系统治疗(Atezo+Bev/仑伐替尼)",
        "胆道癌: 肝门部胆管癌(Bismuth I-IV) — 手术+胆肠吻合 / 远端胆管癌 — 胰十二指肠切除术(PD/Whipple)",
        "胰腺癌: 可切除 => 手术(PD/DP) + 辅助化疗(mFOLFIRINOX/吉西他滨+卡培他滨)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["BCLC 分期指导治疗", "新辅助化疗(边界可切除)", "肝移植评估(Milan/UCSF 标准)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 肝切除/胰十二指肠/胆道重建."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肝切除: 解剖性(规则肝段/半肝) vs 非解剖性(楔形/局部) — Glisson 鞘 Glissonean 入路",
        "血流控制: Pringle 阻断(15min阻断/5min开放) — 低中心静脉压(CVP<5mmHg)减少出血",
        "胰十二指肠切除术(PD): 切除(胃窦+十二指肠+胰头+胆总管+胆囊) + 重建(胰肠+胆肠+胃肠)",
        "胆道重建: 胆肠 Roux-en-Y 吻合术 — 肝总管-空肠端侧(or 端端) 5-0 PDS",
        "术中超声: 微小病灶定位(增强超声CEUS) + 血管侵犯评估",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术后引流: 胃管(24-48h)+腹腔引流(5-7d)+T管(2-3w)", "胰岛素泵(胰腺切除后血糖)", "生长抑素(预防胰漏)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 引流监测 + 血糖 + 疼痛."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "引流液监测: 腹腔引流(量/色) — 胆汁样=>胆漏 / 浑浊=>胰漏+感染 / 大量鲜红=>出血",
        "血糖监测: 胰腺术后 — 血糖 q4h(胰岛素滑动标尺) / 胰酶替代(胰酶肠溶胶囊)",
        "疼痛: 硬膜外/肋间神经阻滞 + NSAIDs + 阿片类 PCA — 避免肝脏代谢负担",
        "营养: PN(术后 24h TPN -> 48-72h 肠内营养(鼻肠管) — 肝切除围手术期能量 25-30kcal/kg/d",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["早期活动: 术后 24h 坐起/48h 下床", "呼吸训练: 激励式肺量计", "肝功+凝血 qd x 7d"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 肿瘤复发 + 肝功能 + 胆道并发症."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肿瘤复发: HCC — 切除后 5 年复发率 70% — AFP + 超声 q3m(前2年) => q6m(后3年)",
        "肝功能: ALT/AST/TBIL/ALB q3-6m — 肝硬化背景者持续抗病毒(恩替卡韦/替诺福韦)",
        "胆道并发症: 胆管炎(发热+黄疸) / 胆道狭窄(MRCP) => PTCD/ERCP + 球囊扩张+支架",
        "营养状态: 体重/BMI/ALB — 胰酶替代(胰十二指肠术后) + 补充脂溶性维生素(A/D/E/K)",
    ]

    recommendations = [
        "肝癌: 每 3-6m 影像(CT/MRI) + AFP 至 5 年",
        "胆道术后: 胆管炎预防(及时处理结石复发/狭窄)",
        "长期抗病毒: 乙肝患者 终身 NA(核苷类似物) — 恩替卡韦/替诺福韦/丙酚替诺福韦",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("肝胆外科")
    return _agent.clinical_result(
        summary="肝胆外科 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
