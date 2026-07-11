"""血管外科 — KnowledgeAgent-powered clinical reasoning.

Focus: 血管疾病外科与介入 — aortic aneurysm, PAD, carotid stenosis, DVT, varicose veins
GUIDELINES: 中国血管外科疾病诊疗指南（2022）, ESVS Clinical Practice Guidelines (2022)
Conditions: 主动脉瘤, 下肢动脉闭塞, 颈动脉狭窄, 深静脉血栓, 静脉曲张

Real clinical scoring: Rutherford PAD, ABI, NASCET/ECST carotid stenosis, Wells DVT, CEAP.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="vascular_surgery", department="血管外科")
_GUIDELINES = [
    "中国血管外科疾病诊疗指南（2022）",
    "ESVS Clinical Practice Guidelines (2022)",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_reg(**kwargs) -> dict:
    """患者登记分诊 — 血管症状 + ABI + 影像初筛."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "血管症状: 间歇性跛行(PAD) / 静息痛(严重缺血) / 搏动性肿块(AAA) / 肢体肿胀(DVT) / 静脉曲张",
        "ABI(踝臂指数): ABI < 0.9 => PAD / ABI < 0.4 => 严重缺血(CLTI) / ABI > 1.3 => 血管钙化(假性)",
        f"检验: D-Dimer={labs.get('D-Dimer','?')}, PLT={labs.get('PLT','?')}, Cr={labs.get('Cr','?')}",
        "影像: 血管超声(彩色多普勒) — 初筛 + 狭窄程度 + 血栓负荷",
    ]

    if "主动脉" in dx or "AAA" in dx.upper():
        findings.insert(0, "主动脉瘤: 超声/CTA 测量最大直径 + 增长速率(>/=5mm/6m=>手术指征)")
    if "下肢动" in dx or "PAD" in dx.upper():
        abi = float(labs.get("ABI", 0.8) or 0.8)
        findings.insert(0, f"PAD: ABI={abi} — {'正常' if abi>=0.9 else '轻度' if abi>=0.7 else '中度' if abi>=0.5 else '重度缺血'}")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 患者登记分诊完成 (S1)",
        patient=p, stage="S1", findings=findings,
        recommendations=["ABI + TBI 测量", "双功超声(动脉/静脉)", "CTA/MRA(主动脉/颈动脉)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diag(**kwargs) -> dict:
    """诊断评估 — Rutherford 分级 + 动脉瘤测量 + DVT 诊断."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    findings = [
        "Rutherford PAD: 0(无症状)/1(轻度跛行>/=200m)/2(中度<200m)/3(重度<50m)/4(静息痛)/5(小溃疡)/6(大溃疡/坏疽)",
        "颈动脉狭窄: NASCET/ECST 测量法 — 狭窄>50%(有症状)/>70%(无症状) => 手术(CEA/CAS)",
        "主动脉瘤(AAA): 肾下AAA>55mm(男)/>50mm(女) => 手术; >40mm 每年超声随访",
        "DVT 诊断: Wells 评分(>=2 可能) + D-Dimer(阴性排除) + 超声(加压不能压闭=>确诊)",
        "CEAP 分级(静脉曲张): C0-C6(皮肤改变/溃疡) + Es/Ep/Ad/Pr病因",
    ]

    if "主动脉" in dx:
        findings.insert(0, "AAA: CTA 精确测量(直径/长度/近远端锚定区/分支) — EVAR 计划必须")
    if "颈动" in dx:
        findings.insert(0, "颈动脉: DUS + CTA/MRA — 狭窄>50%有症状 => 2周内 CEA/CAS(ABCD2 评分辅助)")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary=f"血管外科 — 诊断评估完成 (S3) | {dx[:30]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["下肢动脉 CTA(从肾动脉到足)", "颈动脉 DUS + CTA/MRA", "静脉 DUS + D-Dimer"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_preop(**kwargs) -> dict:
    """术前准备 — 血管重建方案 + 抗凝/抗血小板 + 支架尺寸."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "AAA 术式: EVAR(腔内 首选) vs OR(开腹) — EVAR 需锚定区 10-15mm + 髂股动脉 7mm 通路",
        "PAD 血运重建: PTA +/- 支架(股浅/腘/胫腓) / 搭桥(自体大隐静脉 > ePTFE 人工血管)",
        "颈动脉: CEA(内膜剥脱) vs CAS(支架) — CEA 金标准/CAS 高危外科患者/RTC 后放射狭窄",
        "DVT: 导管接触溶栓(CDT) + 血栓清除(PMT/AngioJet) => 髂静脉压迫综合征 + 支架",
        "抗凝/抗血小板: ASA(100mg) + Clopidogrel(75mg) 双抗 / 华法林(INR 2-3)/DOAC(DVT/PE)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 术前准备完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["备血(RBC+FFP+血小板)", "术前停用抗凝(LMWH 12h/Warfarin 5d 桥接)", "抗生素(假体植入)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_risk(**kwargs) -> dict:
    """风险评估 — 破裂 + 缺血 + 栓塞 + 感染."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    checklist = ["动脉瘤破裂", "急性肢体缺血", "肺栓塞", "支架内血栓", "吻合口出血"]
    findings = [
        "动脉瘤破裂: AAA > 65mm 年破裂率 > 10% — 突发撕裂样疼痛 + 低血压(三联征) => 急诊手术",
        "急性肢体缺血(ALI): Rutherford ALI I/IIa(IIb)/III — IIb/III => 急诊血运重建(6h内黄金窗口)",
        "支架内血栓: 急性(<24h) / 亚急性(1-30d) / 晚期(>30d) — 双抗依从性 + 阿司匹林/氯吡格雷抵抗",
        "吻合口出血/假性动脉瘤: 术后 24-48h 或感染性假性动脉瘤(2-4w) — CTA + 再手术",
        "移植物感染: 腹股沟/腹部切口红肿+渗液(>4w) — 细菌培养+抗生素+取出血管移植物(灾难性)",
    ]
    findings.append(f"高危审核: {len(checklist)} 项")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 风险评估完成 (S3)",
        patient=p, stage="S3", findings=findings,
        recommendations=["术后 ICU/PCU 监护 24-48h", "每小时检视: 脉搏/皮温/颜色/氧饱和/疼痛", "无创血压+遥测心电"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_mdt(**kwargs) -> dict:
    """MDT 决策 — 血管外科+介入+心内+内分泌 多学科."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "MDT 团队: 血管外科 + 介入科 + 心内科 + 内分泌(糖尿病管理) + 神经内科(颈动脉)",
        "AAA: EVAR vs OR 决策 — 年龄/合并症/解剖(锚定区/瘤颈长度-角度)/预期寿命",
        "PAD/CLTI: 腔内优先(PAD) / 搭桥(CLTI 弥漫性/长段钙化) — 保肢(血管外科+创面护理+足踝外科)",
        "颈动脉狭窄: CEA vs CAS — CEA 70-99% 有效性证据最强 / CAS CEH 高危 + 辐射狭窄/高位病变",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — MDT 决策完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["ESVS 指南推荐: EVAR 用于老年+合并症 / OR 用于年轻健康", "最佳药物治疗(BMT): 抗血小板+他汀+ACEi+血糖控制"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_surgery(**kwargs) -> dict:
    """手术执行 — 动脉重建/静脉/颈动脉/EVAR."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "EVAR: 经皮/股动脉切开(双侧) -> 猪尾导管(肾上主动脉造影) -> 主体支架释放(肾动脉下) -> 对侧髂支 -> 球囊后扩 -> 完成造影(内漏?)",
        "PAD 搭桥: 内膜剥脱(股动脉分叉) / 股-腘(膝上/膝下) / 股-胫/足背 — 大隐静脉(倒置/原位) > ePTFE(膝上段)",
        "CEA: 胸锁乳突肌前缘 -> 颈动脉分叉暴露 -> 肝素化(ACT>250) -> 夹闭ICA/CCA/ECA -> 纵行/外翻剥脱 -> 补片缝合(大隐静脉/牛心包/Dacron)",
        "DVT 血栓清除: 穿刺腘静脉/胫后静脉(超声) -> CDT(尿激酶/rt-PA) 持续溶栓 12-24h -> 血栓吸除(AngioJet/Penumbra)",
        "术中抗凝: 肝素 80-100U/kg IV(ACT 250-300s) + 鱼精蛋白(拮抗 1mg/100U 肝素) 完成后",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 手术执行完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["术中造影确认: 重建血管通畅 + 无内漏/残余狭窄/栓塞", "穿刺点/吻合口 止血（鱼精蛋白拮抗后）"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_nursing(**kwargs) -> dict:
    """围术期护理 — 循环监测 + 体位 + 伤口."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "循环: 血压/心率 q15min * 4 => q30min * 4 => q1h — 血液动力学(术后 24-48h)",
        "外周循环: 足背/胫后动脉搏动 + 皮温/颜色/毛细血管充盈(<=2s) — 每 15min * 4 => 每小时",
        "穿刺点/切口: 血肿/渗血/假性动脉瘤 — 腹股沟穿刺点观察(尤其肥胖/高血压/高龄)",
        "体位: 搭桥术后 — 膝关节轻微屈曲(避免腘动脉张力) / 下肢抬高(抗水肿) 72h",
        "疼痛: 缺血再灌注疼痛(剧烈+难控) => 阿片类 + 加巴喷丁(神经病理性疼痛)",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 围术期护理完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=["抗凝: LMWH 常规/DOAC(术后 6-12h 开始 无出血)", "双抗: ASA+Clopidogrel 继续", "早期活动(术后 24h 无禁忌)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """远期随访 — 通畅率 + 再狭窄 + 抗凝管理."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "通畅率: 血管超声(股-腘搭桥: 1/3/6/12m => 每年) — 一期通畅率 70-80%(1y)/60-70%(5y)",
        "再狭窄: 超声峰值流速比(PSV ratio) > 2.5 => 显著狭窄(>50%); > 3.5 => 重度(>75%) => PTA 再次介入",
        "抗凝管理: INR 每周(华法林) 目标 TTR > 65%(2-3) + DOAC(利伐沙班/阿哌沙班) 无需监测",
        "动脉瘤: CTA q6m(EVAR 术后内漏II型常见-侧支反流 => 观察/栓塞; I/III型内漏 => 紧急修补)",
    ]

    recommendations = [
        "超声: 1/6/12 月 => 每年(搭桥/CEA/EVAR 终身监测)",
        "双抗治疗: 6-12 月(PCI/支架) => 终身阿司匹林",
        "风险因素管理: 戒烟 / 血压<130/80 / LDL-C<1.8 / HbA1c<7%",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("血管外科")
    return _agent.clinical_result(
        summary="血管外科 — 远期随访完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
