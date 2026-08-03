"""耳鼻喉科 — KnowledgeAgent-powered clinical reasoning.

Focus: 耳鼻喉科常见疾病 — hearing loss, rhinosinusitis, tonsillitis, laryngeal cancer, epistaxis
GUIDELINES: 中国耳鼻喉科临床诊疗指南（2022）
Conditions: 听力障碍, 中耳炎, 鼻炎/鼻窦炎, 扁桃体炎, 头颈肿瘤

Real clinical concepts: pure-tone audiometry (PTA) grading, CRS diagnosis, Paradise tonsillectomy criteria, TNM.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="ent", department="耳鼻喉科")
_GUIDELINES = [
    "中国耳鼻喉科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_screening(**kwargs) -> dict:
    """筛查与初诊 — 听力 + 鼻内镜 + 喉镜 + 头颈触诊."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "听力: 纯音测听(PTA 气导/骨导) — 传导性/感觉神经性/混合性 听力损失; 言语识别率(WRS)",
        "耳镜: 外耳道(耵聍/异物/炎症) + 鼓膜(光泽/充血/穿孔/中耳积液/胆脂瘤)",
        "鼻内镜: 鼻黏膜(充血/水肿/息肉 0-4级) + 中鼻道(脓涕 CRS标志) + 鼻中隔(偏曲/穿孔)",
        "喉镜(间接/纤维): 声带(麻痹/息肉/结节/白斑) + 梨状隐窝(对称/积液) + 喉咽部",
        "头颈触诊: 颈部淋巴结(I-VI区) + 甲状腺 + 唾液腺(腮腺/颌下腺) + 鼻咽(EBV serology)",
    ]

    if "听力" in dx or "耳" in dx:
        findings.insert(0, "听力障碍: 初筛 PTA 500/1000/2000/4000Hz + 言语测听")
    if "鼻炎" in dx or "鼻窦" in dx or "CRS" in dx.upper():
        findings.insert(0, "鼻窦炎初筛: 鼻塞/流涕/嗅觉减退+持续时间>12w => 慢性鼻-鼻窦炎(CRS)可能")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("耳鼻喉")
    return _agent.clinical_result(
        summary="耳鼻喉科 — 筛查与初诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["纯音测听+声导抗", "鼻内镜(高清)", "纤维喉镜(窄带成像 NBI 可疑病变)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """专科检查 — 听力 + 影像 + 内镜 + 活检."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "听力测试: 纯音测听(PTA)+声导抗(鼓室图 A/As/Ad/B/C) + 镫骨肌反射 + OAE(耳声发射)+ ABR(听性脑干反应)",
        "鼻窦 CT: 冠状位(OMU 窦口鼻道复合体/筛窦) — 评估 CRS 范围/息肉/真菌球(钙化灶) + Lund-Mackay 评分",
        "内镜+窄带成像(NBI): 可疑喉/鼻咽/下咽病变(白斑/红斑/不规则/溃疡) — 上皮内乳头样毛细血管袢(IPCL)分型",
        "鼻内压/鼻阻力: 鼻通气功能 — 鼻中隔偏曲/鼻瓣区塌陷 + 过敏原检测(SPT/血清 IgE)",
        "颈部超声: 颈部淋巴结(I-VI区) + 甲状腺结节(TI-RADS) + 唾液腺  — 可疑淋巴结=>FNA(细针穿刺)",
    ]

    if "听力" in dx:
        findings.insert(0, "PTA 纯音测听: 传导性(骨导正常+气导差>15dB) vs 感觉神经性(气骨导差<15dB) + 听力损失分级")
    if "鼻窦" in dx:
        findings.insert(0, "CRS 诊断: 鼻窦CT Lund-Mackay 评分(0-24) + 鼻内镜(息肉/脓涕/水肿) 评分")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("耳鼻喉")
    return _agent.clinical_result(
        summary="耳鼻喉科 — 专科检查完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["颞骨 CT(中耳炎/胆脂瘤/耳硬化)", "颈部增强 CT/MRI(头颈肿瘤 TNM)", "过敏原(鼻窦炎/鼻炎)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊定级 — 听力分级 + CRS分型 + 扁桃体手术指征 + 喉癌TNM."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "听力损失分级(WHO): 正常(<=25dB)/轻度(26-40)/中度(41-60)/重度(61-80)/极重度(>81dB)",
        "中耳炎: 急性(OME AOM) / 慢性化脓性(CSOM ±胆脂瘤) — 鼓膜穿孔(中央/边缘/上鼓室) + 听力(传导性)",
        "CRS 分型: 伴鼻息肉(CRSwNP) / 不伴息肉(CRSsNP) — 组织嗜酸粒细胞/中性粒细胞分型",
        "扁桃体切除指征(Paradise): >=7次/1y OR >=5次/年*2y OR >=3次/年*3y + 药物治疗无效 + 严重影响生活(OSAHS)",
        "喉癌 TNM(AJCC 8th): T1-4(声门上/声门/声门下) + N0-3 + M0-1 — 早期(T1-2) 保喉/RT => 晚期(T3-4) 全喉+RT/CRT",
        "鼻出血分级: 轻度(前鼻 鼻腔填塞) / 中度(后鼻 后鼻孔填塞) / 重度(出血性休克+内镜+电凝/栓塞)",
    ]

    if "听力" in dx:
        findings.insert(0, "听力损失分级 => 决定助听器/人工耳蜗/BAHA 候选")
    if "鼻窦" in dx:
        findings.insert(0, "CRS 治疗方案: 药物治疗(激素喷鼻+冲洗+抗生素 4-12w) -> 无效 => FESS(功能性内镜鼻窦手术)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("耳鼻喉")
    return _agent.clinical_result(
        summary=f"耳鼻喉科 — 确诊定级完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["CRS: 术前药物治疗 4-12w(激素+抗生素+冲洗)", "扁桃体: 严格 Paradise 标准", "肿瘤: 病理+影像 TNM 分期"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗操作 — 药物/内镜手术/听力康复/语音训练."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "药物治疗: 鼻炎(鼻用激素+口服抗组胺+孟鲁司特) / 鼻窦炎(鼻用激素+生理盐水冲洗+抗生素 4w+/-口服激素 1-2w)",
        "内镜手术: FESS(额窦/筛窦/上颌窦/蝶窦 开口扩大+息肉切除) + 鼻中隔矫正术 + 下鼻甲减容术(射频/微切)",
        "听力康复: 助听器(双侧 按听力损失程度/处方) + 中耳手术(鼓膜成形/听骨链重建TORP/PORP) + 人工耳蜗(重度-极重度)",
        "嗓音手术: 声带显微手术(剥脱/切除 微瓣技术) + 喉内注射(声带麻痹 透明质酸/自体脂肪)",
        "耳科手术: 乳突根治术(CWD/CWU) / 鼓室成形术(Type I-V Wullstein) / 人工镫骨(耳硬化)",
    ]

    if "扁桃" in dx:
        findings.insert(0, "扁桃体切除: 冷器械/双极电凝/等离子(coblation) — 术后出血风险 1-5%(第1/第7-10天)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("耳鼻喉")
    return _agent.clinical_result(
        summary="耳鼻喉科 — 治疗操作完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术后鼻内镜+冲洗(CRS)", "术后发音休息(喉)", "术后抗生素/镇痛", "出院教育(鼻塞/出血/吞咽)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """定期复查 — 听力变化 + 术后恢复 + 复发监测."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "听力变化: 听力图复查(1m/3m/6m/1y) — 助听器效益评估(APHAB问卷) / 人工耳蜗程序调机(MAP)",
        "术后恢复: FESS 术后鼻内镜(1w/2w/1m/3m — 囊泡形成/粘连/息肉复发/窦口通畅) + 鼻腔冲洗 2-4w+",
        "复发监测: CRS 复发率(5-15% 1y/30% 5y) — 持续用药(鼻用激素+冲洗+生物制剂 dupilumab)",
        "肿瘤随访: 喉癌 — 喉镜+颈部触诊+影像 q2-3m(1y) => q4-6m(2y) => q6-12m(3-5y)",
    ]

    recommendations = [
        "听力: 每年听力检查 + 助听器调试/电池更换(每年)",
        "CRS 术后: 鼻内镜(1w/2w/1m/3m) + 鼻用激素(持续 6-12m) + 生理盐水冲洗(每日)",
        "扁桃体术后: 1w/2w 复查(白膜形成/疼痛/出血)/6m 症状改善评估",
        "鼻出血: 避免干抠/用力擤鼻 + 凡士林/生理盐水鼻内 + 控制血压",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("耳鼻喉")
    return _agent.clinical_result(
        summary="耳鼻喉科 — 定期复查完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
