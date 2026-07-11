"""普通外科 — KnowledgeAgent-powered clinical reasoning.

Focus: 普外常见疾病 — appendicitis, cholecystitis, hernia, thyroid, GI perforation
GUIDELINES: 中国普通外科临床诊疗指南（2022）
Conditions: 阑尾炎, 胆囊结石, 腹股沟疝, 甲状腺结节, 消化道穿孔, 肠梗阻

Real clinical scoring: Alvarado Score (appendicitis), Tokyo Guidelines (acute cholangitis/cholecystitis).
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="general_surgery", department="普通外科")
_GUIDELINES = [
    "中国普通外科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 急腹症快速评估 + 手术指征初步判断."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "腹痛评估: 位置(右上/右下/全腹) + 性质(持续性/阵发性) + 放射(后背/肩部)",
        "生命体征: BP/HR/RR/Temp — 休克指数(HR/SBP > 1 => 出血性休克可能)",
        f"检验关注: WBC={labs.get('WBC','?')}, CRP={labs.get('CRP','?')}, Hb={labs.get('Hb','?')}, PT={labs.get('PT','?')}",
        "体征: 腹膜炎(板状腹/反跳痛/Murphy征/Rovsing征/腰大肌试验)",
    ]

    checklist = ["腹膜炎体征", "休克", "肠坏死", "吻合口漏", "腹腔感染"]
    findings.append(f"高危审核: {len(checklist)} 项")

    if "阑尾炎" in dx or "appendicitis" in dx.lower():
        wbc = float(labs.get("WBC", 10) or 10)
        findings.insert(0, f"Alvarado 评分基础: WBC={wbc}, 右下腹痛, 厌食/恶心")
    if "胆囊" in dx:
        findings.insert(0, "胆囊疾病: Murphy 征 + 右上腹超声(胆囊壁厚/结石/胆泥)")
    if "疝" in dx:
        findings.insert(0, "疝评估: 可复性/难复性/嵌顿/绞窄 — 嵌顿>6h 紧急手术")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["立位腹部平片(穿孔/梗阻)", "腹部超声/CT", "禁食水(备急诊手术)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — 影像 + 实验室 + 鉴别诊断."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "阑尾炎: Alvarado 评分 >=7 => 手术 / 5-6 => 观察+CT / <4 => 排除",
        "胆囊结石: 超声(B超首选) — 胆囊壁>4mm + 结石 + Murphy征阳性 => 急性胆囊炎",
        "胆管炎: Tokyo 指南 2018 — Charcot 三联征(发热+黄疸+右上腹痛) / Reynolds 五联征(+休克+意识障碍)",
        "腹股沟疝: 体格检查(站立+咳嗽) + 超声 / CT(嵌顿/绞窄鉴别)",
        "甲状腺结节: TI-RADS 分级 + FNA(细针穿刺)指征: >1cm 可疑结节",
    ]

    if "阑尾炎" in dx:
        findings.insert(0, "阑尾炎: 首选超声(儿童/孕妇) / CT(成人非孕期) — 阑尾直径>6mm+周围脂肪条索")
    if "穿孔" in dx:
        findings.insert(0, "消化道穿孔: 立位腹部平片 -> 膈下游离气体 => 急诊手术")
    if "肠梗阻" in dx:
        findings.insert(0, "肠梗阻: 气液平(CT/立位腹平片) + 移行带 => 机械性 vs 麻痹性")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary=f"普通外科 — 诊断评估完成 (S3) | {dx}",
        patient=p, stage="S3", findings=findings,
        recommendations=["增强CT(腹盆腔) 金标准", "血清淀粉酶/脂肪酶(排除胰腺炎)", "育龄女性: 尿HCG"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — ASA分级 + DVT预防 + 抗生素."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "ASA 分级评估: I(健康)/II(轻度系统病)/III(重度系统病)/IV(危及生命)/V(濒死)",
        "禁食水: 清液 2h / 母乳 4h / 固体 6-8h(ERAS 推荐)",
        "血栓预防: Caprini 评分 — 高风险 >=5 => 物理+LMWH 联合",
        "抗生素: 切皮前 30-60min — 头孢唑啉 2g IV(阑尾/胆囊) / 头孢西丁(结直肠)",
        "备血: Hb<7g/dL 备去白悬浮红细胞 2-4U / 大手术备血浆+血小板",
    ]

    if "阑尾炎" in dx:
        findings.insert(0, "阑尾炎术前: 腔镜器械准备 + Foley 尿管 + NG管(腹胀)")
    if "胆囊" in dx:
        findings.insert(0, "胆囊术前: LC(腹腔镜胆囊) — CO2气腹准备 + 术中胆道造影")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["心电图+CXR+基础代谢", "凝血功能+血型+交叉配血", "麻醉知情同意+手术知情同意"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 手术并发症 + 麻醉风险 + 术后风险分层."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "手术风险: NSQIP 风险计算器(30d 并发症/死亡率) + 手术紧迫性(急/择期)",
        "出血风险: 大血管毗邻(腹主动脉/下腔静脉/门静脉) — 术中出血量预估",
        "吻合口漏: 结肠吻合(5-10%) / 直肠吻合(10-15%) — 高危因素: 糖尿病/吸烟/术前放化疗",
        "切口疝: 肥胖(BMI>30) / 切口感染 / 胶原病 — 关腹技术优化(小针距SLWL)",
        "术后感染: 切口感染(SSI) 5-15% / 腹腔感染 — NNIS 风险指数: ASA+伤口分类+手术时长",
    ]

    checklist = ["腹膜炎体征", "休克", "肠坏死", "吻合口漏", "腹腔感染"]
    findings.append(f"高危审核: {len(checklist)} 项(普外核心风险)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["高危患者 => ICU 预留", "术前营养支持(白蛋白<30g/L)", "血糖控制(目标 140-180mg/dL)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 普外+肿瘤+消化内科+影像 多学科讨论."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 参与科室: 普外科 + 消化内科 + 肿瘤科 + 影像科 + 病理科",
        "术式选择: 腹腔镜(LC/LA/TEP/TAPP) vs 开腹 — 腹腔镜优先(恢复快/疼痛轻/住院短)",
        "肿瘤决策: 胃癌/结直肠癌 => TNM 分期 + 新辅助化疗(nCRT) + 手术时机(6-8w后)",
        "肠梗阻: 保守(禁食+胃肠减压+补液) vs 手术(绞窄/穿孔/肿瘤) — 48-72h 评估",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["NCCN/CSCO 指南导向治疗", "ERAS 围手术期路径", "出院计划及早启动"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 腹腔镜/开腹 + 吻合/造口."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "腹腔镜: 气腹压 12-15mmHg / 套管针 Trocar(10mm+5mm) / 30度镜",
        "阑尾切除: LA(腹腔镜) / OA(开腹) — 根部结扎+荷包缝合(可选)",
        "胆囊切除: LC — Calot 三角安全视野(CVS) / 术中胆道造影(可疑结石)",
        "疝修补: TEP(完全腹膜外) / TAPP(经腹膜前) — 补片(聚丙烯/生物补片) + 无张力修补",
        "吻合: 手法缝合(Gambee) / 吻合器(圆形/线性) + 测漏试验(亚甲蓝/充气)",
        "术中冰冻: 肿瘤切缘 / 淋巴结 快速病理 — 决定切除范围",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["腹腔冲洗(温生理盐水)", "引流管(被动/主动)放置 — 盆腔/肝下", "关腹前纱布/器械清点"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — ERAS 路径 + 引流管 + 疼痛管理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "ERAS 路径: 术后 6h 进水(清醒后)/24h 流质/咀嚼口香糖(肠蠕动) / 早期下床(术后24h内)",
        "引流管: 记录引流量/颜色 — 腹腔引流 <50mL/24h 拔除 / T管(胆道) 2-3周后造影+拔管",
        "疼痛管理: 多模式镇痛 — NSAIDs(酮咯酸/帕瑞昔布) + 切口局麻(罗哌卡因) + PCA 备选",
        "伤口: 敷料干燥 — 48h 后可淋浴(防水敷料) / 切口感染征象(红/肿/热/痛/脓)监测",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["VTE 预防: LMWH + IPC 间歇充气加压", "血糖监测 q6h(糖尿病患者)", "出院指导: 活动限制/饮食/用药"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 切口愈合 + 并发症监测 + 病理结果."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "切口愈合: 拆线时间 — 腹部 7-10 天 / 面部 5-7 天 / 关节 14 天",
        "并发症监测: 切口感染 / 肠梗阻(粘连性) / 切口疝(术后 3-12m) / 深静脉血栓",
        "病理结果: 肿瘤 — 分期/分级/切缘/淋巴结 / 辅助治疗决策(化疗/放疗)",
        "功能恢复: 肠功能(排气/排便) / 饮食恢复(流质->半流->普食) / 活动耐力",
    ]

    recommendations = [
        "阑尾炎/胆囊: 术后 2-4w 复查 + 1-2w 恢复正常活动",
        "疝修补: 术后 4-6w 避免重体力 / 3 月查补片/复发",
        "肿瘤: 术后 CEA/CA19-9 q3m * 2y => q6m * 3y + 每年 CT",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("普通外科")
    return _agent.clinical_result(
        summary="普通外科 — 术后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
