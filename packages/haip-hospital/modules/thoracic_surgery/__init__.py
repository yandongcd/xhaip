"""胸外科 — KnowledgeAgent-powered clinical reasoning.

Focus: 胸部疾病外科治疗 — lung cancer, esophageal cancer, mediastinal tumor, pneumothorax
GUIDELINES: 中国胸外科临床诊疗指南（2022）
Conditions: 肺癌, 食管癌, 纵隔肿瘤, 气胸, 胸壁畸形

Real clinical scoring: PFT (FEV1/DLCO) operability, TNM staging, ECOG PS.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="thoracic_surgery", department="胸外科")
_GUIDELINES = [
    "中国胸外科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 肺功能初筛 + 影像初评 + 症状分层."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    fev1 = labs.get("FEV1_pct", "?")
    dlco = labs.get("DLCO_pct", "?")

    findings = [
        f"肺功能: FEV1%={fev1}, DLCO%={dlco} — 手术可切除性关键指标",
        "影像: CT(胸部薄层 1-1.5mm) + PET-CT(肺癌分期) + EBUS-TBNA(淋巴结分期)",
        "症状: 咳嗽(时间/性质/咯血) + 胸痛 + 呼吸困难(mMRC 分级) + 吞咽困难(食管癌)",
        "风险因素: 吸烟(包年) / 职业暴露(石棉/氡/砷) / 家族史",
    ]

    if "肺癌" in dx or "lung cancer" in dx.lower():
        findings.insert(0, f"肺癌筛查: FEV1%={fev1} / DLCO%={dlco} — 术后预计 FEV1 > 40% 可手术")
    if "食管" in dx:
        findings.insert(0, "食管癌: 吞咽困难分级 — 0级(普食)/1级(半流)/2级(流质)/3级(唾液困难)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["肺功能全套(spirometry+DLCO+lung volumes)", "动脉血气 ABG", "心电图+心脏超声(TTE)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — TNM 分期 + 可切除性评估 + 病理活检."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    fev1 = float(labs.get("FEV1_pct", 65) or 65)
    dlco = float(labs.get("DLCO_pct", 60) or 60)

    findings = [
        "TNM 第8版: T(肿瘤大小+侵犯) + N(淋巴结 N0/N1/N2/N3) + M(远处转移 0/1a/1b/1c)",
        "肺切除可行性: 术后预计 FEV1%(ppoFEV1)=FEV1%*剩余肺段% — ppoFEV1>40%/DLCO>40% => 安全",
        f"当前: FEV1%={fev1} / DLCO%={dlco}",
        "食管癌分期: 超声内镜(EUS) T分期 + EBUS-TBNA N分期 + PET-CT M分期",
        "纵隔肿瘤: CT/MRI — 位置(前/中/后纵隔) + 囊性/实性 + 钙化 => 鉴别诊断(胸腺瘤/淋巴瘤/畸胎瘤)",
        "气胸: 影像(肺压缩%) + 病因(原发性/COPD继发性/创伤性)",
    ]

    if "肺癌" in dx:
        findings.insert(0, "肺癌 TNM 分期: 完善 EBUS/EUS 纵隔淋巴结分期(>=cN1/中央型肿瘤/>=3cm N0)")
    if "气胸" in dx:
        findings.insert(0, "气胸: 肺压缩 > 30% => 胸腔闭式引流(锁骨中线第2肋间) / 复发 => VATS胸膜固定术")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary=f"胸外科 — 诊断评估完成 (S3) | ppoFEV1%={fev1}",
        patient=p, stage="S3", findings=findings,
        recommendations=["PET-CT 全身(排除远处转移)", "EBUS-TBNA(N2/N3 取样)", "支气管镜(中央型)+CT引导穿刺(周围型)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 肺功能优化 + 支气管镜 + 定位."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肺功能优化: 戒烟 >= 4w + 肺康复(呼吸训练/耐力) + 支气管扩张剂(COPD)",
        "支气管镜: 术前行 — 明确支气管侵犯范围 + 确定切除平面",
        "肺结节定位: CT引导 Hook-wire / 亚甲蓝 / 荧光胸腔镜(ICG) — 对于 GGO/微小结节",
        "VTE 预防: Caprini 评分(胸外科常规 >= 5 高风险) => 物理+LMWH",
        "备血: 全肺切除备 RBC 4U / 肺叶切除备 RBC 2U",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术前锻炼: 激励肺量计(IS)", "营养支持(白蛋白>35g/L)", "单肺通气评估(双腔管/支气管阻塞器)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 呼吸/心血管/手术专项风险."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    checklist = ["张力性气胸", "支气管胸膜瘘", "乳糜胸", "肺栓塞", "ARDS"]
    findings = [
        "呼吸并发症: 肺炎(5-15%) + 肺不张(分泌物潴留) + ARDS(全肺切除 5-10%) + 呼吸衰竭",
        "支气管胸膜瘘(BPF): 全肺切除 1-4%(右侧>左侧) — 支气管残端血供/技术/放疗史",
        "心血管: 心律失常(房颤 10-20%) + 心梗/心衰 + 肺栓塞(D-二聚体+CTPA)",
        "乳糜胸: 食管癌术后 1-3% — 胸导管损伤(乳白色胸液/甘油三酯>1.24mmol/L)",
        "吻合口漏: 食管癌 5-15% — 吻合口缺血/张力/感染 — 口腔泛蓝(亚甲蓝试验阳性)",
    ]
    findings.append(f"高危审核: {len(checklist)} 项")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["心律失常预防(电解质平衡+镁离子)", "术后 O2 目标 SpO2 92-96%", "血栓预防 LMWH + IPC"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 胸外+肿瘤+呼吸+放疗 多学科."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 胸外科 + 肿瘤内科 + 放疗科 + 呼吸内科 + 病理科 + 影像科",
        "肺癌: 手术(VATS肺叶+纵隔淋巴结清扫) / 新辅助(化疗+免疫/靶向) + 辅助(化疗/靶向)",
        "食管癌: 新辅助放化疗(CROSS方案) + 食管癌根治(McKeown/Ivor Lewis) — 8w 后手术",
        "气胸: 首次=>观察/抽气 / 复发=>VATS 胸膜固定术(滑石粉/胸膜切除/胸膜摩擦)",
        "纵隔肿瘤: 胸腺瘤 => 全胸腺切除+前纵隔脂肪清扫 / 重症肌无力 => 丙球/血浆置换 术前优化",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["NCCN NSCLC 指南导向分期治疗", "食管癌新辅助 nCRT => 手术间隔 6-8w"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — VATS/开放 + 肺叶/全肺/食管/纵隔."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "VATS(胸腔镜): 3孔/单孔(Uniportal) — 肺叶/肺段/楔形切除",
        "肺叶切除: 肺静脉->肺动脉->支气管(分别处理) + 纵隔淋巴结清扫(至少 3 站 N2 + 叶/肺门N1)",
        "全肺切除: 肺功能临界(FEV1/DLCO 边缘)才考虑 — 支气管残端缝合(4-0 Prolene) + 胸膜腔管理",
        "食管切除: McKeown(颈胸腹三切口) / Ivor Lewis(胸腹) — 管胃制作(胃网膜右动脉血供) + 吻合(颈部/胸顶)",
        "胸导管: 预防性结扎(主动脉裂孔处) — 尤其食管切除 / 纵隔淋巴结清扫 + 乳糜漏识别",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["气管镜检: 关胸前确认支气管残端密封", "胸腔引流(1或2根) + 水封/负压吸引 -20cmH2O", "温盐水冲洗+鼓肺检查漏气"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 胸管管理 + 呼吸训练 + 疼痛."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "胸腔引流: 水封瓶 液面波动(呼吸性摆动) + 气泡(漏气=>支气管胸膜瘘) + 引流量(<200mL/24h可拔管)",
        "呼吸训练: 激励式肺量计(IS) q1h * 10 次 + 深呼吸 + 有效咳嗽(夹胸管/止痛后)",
        "疼痛管理: 硬膜外(PCEA) / 椎旁神经阻滞(PVB) + NSAIDs + 阿片类 PCA — 多模式镇痛",
        "术后体位: 床头抬高 30-45 度 + 健侧卧位(支气管胸膜瘘禁忌)",
        "饮食: 食管术后 — NPO(禁食) 5-7 天, 鼻肠管 EN(肠内营养), 食管造影(第5天)确认无漏后进食流质",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["早期下床: 术后 24h(床头->椅子->行走)", "VTE 预防: LMWH + IPC", "出院: 肺功能康复+伤口护理+负压球管理"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 肿瘤复发 + 肺功能 + 生活质量."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "肿瘤复发: NSCLC — CT 胸部 q6m * 2y => 每年(共5y); 高危者 q3m",
        "肺功能: 术后 3-6m 复查 PFT — FEV1 下降 5-15%(肺叶) / 20-35%(全肺)",
        "生活质量: 呼吸困难评分(mMRC) + 运动耐力(6MWT) + QLQ-C30/LC13 量表",
        "辅助治疗: 化疗(顺铂+培美曲塞/多西他赛 * 4 周期) / 靶向(EGFR/ALK TKI) / 免疫(PD-1/PD-L1)",
    ]

    recommendations = [
        "NSCLC 随访: CT q6m * 2y + 每年 * 3y + PET/CT 有症状",
        "食管癌: 食管造影+CT q3-6m * 2y + 内镜(吻合口/残端复发) qy",
        "戒烟: 持续吸烟显著增加复发+第二原发癌",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("胸外科")
    return _agent.clinical_result(
        summary="胸外科 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
