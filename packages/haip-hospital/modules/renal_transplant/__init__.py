"""肾移植科 — KnowledgeAgent-powered clinical reasoning.

Focus: 肾移植围术期及长期管理 — donor evaluation, immunosuppression, rejection, infection
GUIDELINES: 中国肾移植临床诊疗指南（2022）, KDIGO Guideline on Kidney Transplant (2020)

Real clinical concepts: HLA matching, PRA, Banff rejection classification, Tacrolimus trough, CMV/BKV.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="renal_transplant", department="肾移植科")
_GUIDELINES = [
    "中国肾移植临床诊疗指南（2022）",
    "KDIGO Guideline on Kidney Transplant (2020)",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 移植等待名单 + HLA配型 + PRA + 供体评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "移植等待: 肾移植等待名单登记 + 每 6-12m 评估 + MELD/CTP(肝)或 KDPI/EPTS(肾)评分",
        "HLA 配型: A/B/DR(6位点) — 0错配最佳(长期存活), DR匹配最重要",
        "PRA(群体反应抗体): 0-19%低风险 / 20-79% 中风险 / >=80% 高风险(脱敏治疗)",
        "供体评估: 活体(自愿+伦理) — ABO相容 + 交叉配型(CDC)阴性 + 解剖学评估(CTA/MRA)",
        f"检验: Cr={labs.get('Cr','?')}, eGFR={labs.get('eGFR','?')}, Hb={labs.get('Hb','?')}",
    ]

    if "移植" in dx or "transplant" in dx.lower():
        findings.insert(0, f"肾移植评估: 受体 Cr={labs.get('Cr','?')}/eGFR={labs.get('eGFR','?')} — 终末期肾病(ESRD)确认")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["HLA 高分辨分型(A/B/C/DR/DQ)", "PRA 筛查+供体特异性抗体(DSA)", "供体评估(活体: 心理+伦理委员会)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — 供体-受体匹配 + 排斥风险评估 + 感染筛查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "交叉配型: 补体依赖细胞毒(CDC)交叉配型 + 流式细胞术交叉配型(FCXM) — 均为阴性 => 移植可行",
        "DSA(供体特异性抗体): MFI < 1000 忽略 / 1000-3000 弱阳性(可能可接受) / > 3000 强阳性(需要脱敏)",
        "ABO 血型相容性: 血型不相容可移植(血浆置换+免疫吸附+利妥昔+IVIG) — 但仍以ABO相同/相容优先",
        "免疫风险分层: 低危(非致敏 首次移植) / 中危(PRA 1-50%/再移植) / 高危(PRA > 50%/DSA+/CDC+)",
        "感染筛查: CMV-IgG/IgM / EBV / HIV/HBV/HCV / TB(潜伏性PPD/T-SPOT) / 梅毒",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary=f"肾移植科 — 诊断评估完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["供体肾活检(植入前) — 评估肾小球硬化/间质纤维化/动脉硬化", "受体: 心脏+血管+肿瘤筛查"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 免疫诱导 + 供肾修整 + 预处理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "免疫诱导: 低危 => 巴利昔单抗(CD25单抗 Day0+Day4) / 高危 => ATG(抗胸腺细胞球蛋白) 1.5mg/kg/d * 3-5d",
        "脱敏治疗: 高危/ABO不相容 => 血浆置换(PLEX 3-7次) + IVIG(2g/kg) + 利妥昔单抗(375mg/m2)",
        "供肾修整: 低温(4°C 保存液 UW/HTK) — 修整血管(肾A/肾V剥脱) + 输尿管修整(保留输尿管外膜/血管)",
        "术前用药: 免疫抑制(他克莫司 0.1mg/kg pre-op 口服) + 抗生素(切皮前) + PJP预防(复方新诺明)",
        "受体准备: 透析(调整电解质/酸碱/容量) — 维持血K+<5.5/无肺水肿",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["交叉配型(术前再次确认阴性)", "备血(4U RBC + FFP)", "预防性抗生素 切皮前 30-60min"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 排斥/DGF/感染/血管并发症."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "排斥反应: 超急性(<72h 已有抗体) / 急性细胞性(>5d Banff I/II/III 间质-小管-血管 T细胞) / 抗体介导型(AMR DSA+C4d+)",
        "DGF(移植肾功能延迟恢复): 发生率 20-40%(DBD)/30-50%(DCD) — CIT(冷缺血时间)>18h 风险显著增加",
        "感染: CMV(D+/R-最危险 发病2-4m) + BKV(3-12m 多瘤病毒+BK肾病 免疫过强) + EBV(移植后淋巴增殖病 PTLD)",
        "血管并发症: 肾动脉血栓(<1% 术后72h内) / 肾静脉血栓(1-4% DCD/S体型) / 肾动脉狭窄(5-10% 3-24m)",
        "尿路并发症: 尿漏(输尿管坏死 5-10% 术后7-14d) + 输尿管狭窄(1-3% 远期)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["DGF: 多普勒超声 qd + 延迟免疫抑制减量(ATG替代CNI)", "感染预防: CMV 缬更昔洛韦 / PJP TMP-SMX / 疫苗"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 移植外科+肾内科+感染科+病理 多学科."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 移植外科 + 肾内科 + 感染科 + 病理科 + 免疫科/输血科",
        "免疫抑制方案: 诱导(ATG/Basi) + 维持(他克莫司+霉酚酸酯+激素 三联) — 减量方案(DGF/老年/感染)",
        "排斥治疗: 细胞性 => 甲泼尼龙冲击 500mg * 3-5d + ATG(激素耐药) / AMR => PLEX+IVIG+利妥昔+硼替佐米",
        "机会性感染: CMV(缬更昔洛韦预防 D+/R- 100-200d) / BKV(每月筛查PCR 1y => 减量ISM) / PCP(TMP-SMX 预防 6-12m)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["KDIGO 推荐: Tac 谷浓度 6-10 ng/mL(前3月) => 4-8(3-12m) => 3-7(>12m)", "BK 病毒 PCR 每月 1y"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 肾移植(开放/机器人) + 血管吻合 + 输尿管吻合."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "切口: Gibson 切口(右下腹斜切口) — 腹直肌旁 / 经腹/经腹膜外(首选)",
        "血管吻合: 肾静脉-髂外静脉(端-侧 5-0 Prolene) + 肾动脉-髂外动脉/髂内动脉(端-端/端-侧 6-0 Prolene)",
        "松开阻断: 先静脉后动脉 — 肾脏再灌注(即刻均匀粉红+充盈) / 术中补液+甘露醇+速尿",
        "输尿管吻合: Lich-Gregoir 术(膀胱外输尿管-膀胱吻合 5-0 PDS) + 抗反流隧道(3-4cm) + DJ 管(输尿管支架 2-4w)",
        "术中超声: 吻合口血流(肾动脉RI<0.8/肾静脉血流)/输尿管口喷尿",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术中静脉注射甲泼尼龙 500mg(再灌注前)", "留置 Foley 尿管 + 引流管(盆腔)", "监测尿量(qh 目标>100mL/h)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 尿量/电解质/引流/感染."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "尿量: 每小时记录 — 目标 > 100mL/h(24h 内) / 少尿(<30mL/h) => DGF 可能",
        "出入量: 静脉补液(NS 100-150mL/h) + 口服(术后 24h) — 精确平衡",
        "电解质: K+/Cr q6-12h — 高K+(>5.5 紧急处理: 胰岛素+葡糖/钙剂/速尿/透析)",
        "引流管: 盆腔引流(透明/淡血性) — 大量鲜红=>出血 / 尿液=>尿漏",
        "免疫抑制: 他克莫司/环孢素谷浓度监测 qd — 严格按时给药(每日相差<30min)",
        "感染预防: 手卫生+口罩 / 体温 q4h / 预防性抗生素/抗病毒/抗真菌",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["DJ 管留置 2-4w + 膀胱镜拔除", "每日超声 qd(3d)", "早期下床(24h 无并发症)", "出院教育: 免疫抑制剂+感染+复诊"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """术后随访 — 肾功能 + 药物浓度 + BK病毒 + 恶性肿瘤."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        f"肾功能: Cr={labs.get('Cr','?')} + eGFR={labs.get('eGFR','?')} — 目标 eGFR > 60 mL/min 长期; DSA q3-6m",
        "药物浓度: 他克莫司 谷浓度 5-8ng/mL(>12m) / 霉酚酸酯 稳态AUC 30-60 mg*h/L / 激素减量 5mg/d 或停药",
        "BK 病毒: 每月 PCR(前 6-12m) => 每 3m(>12m) — > 10^4 copies/mL => 减少 ISM(MMF 减半/改为 mTORi)",
        "心血管: 血压<130/80 / LDL-C<2.6 / HbA1c<7%(新发糖尿病 NODAT 10-25%) — 心脏超声/ECG 每年",
        "恶性肿瘤筛查: PTLD(EBV相关 1-2% / 年龄+EBV R-/D+) + 皮肤癌(每年) + 肾细胞癌(原肾 超声 qy)",
    ]

    recommendations = [
        "随访频率: 前 3 月(每周) -> 3-6m(每2周) -> 6-12m(每月) -> >1y(每 2-3 月)",
        "终身免疫抑制: 他克莫司(或环孢素或西罗莫司)+MMF+/-激素",
        "疫苗: 灭活疫苗(流冠/肺炎/乙肝/HPV/带状疱疹)安全",
        "避孕: 移植后 1y 内避免妊娠 / 霉酚酸酯致畸(停药+替换为硫唑嘌呤/Belatacept 孕前 6w)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("移植")
    return _agent.clinical_result(
        summary="肾移植科 — 移植后随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
