"""眼科 — KnowledgeAgent-powered clinical reasoning.

Focus: 眼科疾病 — cataract, glaucoma, diabetic retinopathy, AMD, refractive error
GUIDELINES: 中国眼科临床诊疗指南（2022）
Conditions: 白内障, 青光眼, 糖尿病视网膜病变, 黄斑变性, 屈光不正

Real clinical concepts: BCVA (LogMAR), IOP target, DR staging (ETDRS), AMD classification, OCT.
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="ophthalmology", department="眼科")
_GUIDELINES = [
    "中国眼科临床诊疗指南（2022）",
]

_agent.rule_engine.load_all()


def _clinical_error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


def bp_screening(**kwargs) -> dict:
    """筛查与初诊 — 视力 + 眼压 + 裂隙灯 + 眼底检查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    iop = float(labs.get("IOP", 16) or 16)
    bcva = labs.get("BCVA", "0.8")

    findings = [
        f"视力检查: BCVA(最佳矫正视力)={bcva} — 筛查屈光不正/白内障/眼底病变",
        f"眼压(IOP): {iop}mmHg — 正常 10-21mmHg, 青光眼风险 > 21 + 视盘改变",
        "裂隙灯: 眼前段(角膜/前房/虹膜/晶状体) — 白内障分级(LOCS-II/III 核性/皮质/后囊下)",
        "眼底检查: 视盘(杯盘比C/D <= 0.5 正常 > 0.6 青光眼可疑) + 黄斑(foveal reflex) + 血管(DR微动脉瘤)",
    ]

    if "白内障" in dx or "cataract" in dx.lower():
        findings.insert(0, f"白内障初筛: BCVA={bcva} — 视力下降 + 晶状体混浊 + 眩光/对比敏感度")
    if "青光眼" in dx or "glaucoma" in dx.lower():
        findings.insert(0, f"青光眼筛查: IOP={iop}mmHg, C/D=? — 高眼压 + 视野缺损 => 青光眼疑似")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("眼科")
    return _agent.clinical_result(
        summary=f"眼科 — 筛查与初诊完成 (S1) | BCVA={bcva} IOP={iop}",
        patient=p, stage="S1", findings=findings,
        recommendations=["电脑验光 + 显然验光(主观)", "Goldmann 压平眼压", "散瞳后裂隙灯+间接眼底镜"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_exam(**kwargs) -> dict:
    """专科检查 — OCT + 视野 + 眼底照相 + FFA."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "OCT(光相干断层扫描): 黄斑(视网膜厚度/水肿/CNV/RPE) + 视神经纤维层(RNFL 青光眼:上下颞 RNFL 变薄)",
        "视野(Humphrey 24-2/30-2): 青光眼早期(中心旁局限性暗点) => 晚期(管状视野) — MD/PSD/VFI 指标",
        "眼底照相(彩色/无赤光): 视盘立体照(盘沿宽度<0.2 青光眼) + DR(出血点/硬性渗出/棉絮斑/IRMA/NVE/NVD)",
        "FFA(荧光血管造影): DR(微动脉瘤/NVE渗漏/NVD FD-缺血 DR+) / AMD(CNV 网样渗漏/渗漏点) / 视网膜血管阻塞(CRVO/BRVO)",
        "IOL Master/光学生物测量: 白内障手术前 — 眼轴/角膜曲率/前房深度 => IOL 计算公式(Holladay 2/Barrett/SRK/T)",
    ]

    if "青光眼" in dx:
        findings.insert(0, "青光眼: OCT RNFL+GCC + 视野 + 前房角镜(Spaeth/Shaffer 分级) => 开角/闭角判定")
    if "DR" in dx or "糖尿病" in dx:
        findings.insert(0, "DR 分级: ETDRS 7-field 标准照片 — 轻度NPDR/中度/重度/PDR 分别管理")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("眼科")
    return _agent.clinical_result(
        summary="眼科 — 专科检查完成 (S2)",
        patient=p, stage="S2", findings=findings,
        recommendations=["OCT+OCTA(脉络膜新生血管)", "视野+OCT(青光眼视神经损伤)", "FFA(DR/PDR/AMD/BRVO/CRVO)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_diagnosis(**kwargs) -> dict:
    """确诊定级 — 白内障分级 + 青光眼分期 + DR分级 + AMD分型."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})
    iop = float(labs.get("IOP", 16) or 16)

    findings = [
        "白内障分级: LOCS III — 核性(NC1-NC6)/皮质(C1-C5)/后囊下(P1-P5) + BCVA 阈值(<=0.5 为手术指征)",
        f"青光眼分期: IOP={iop} + 视野(早期MD< -6dB/中期-6~-12dB/晚期> -12dB) + OCT RNFL — 靶眼压设定(降25-50%)",
        "DR 分级: 轻度NPDR(仅微动脉瘤) / 中度(微动脉瘤+点状出血+硬渗/CWS) / 重度(4-2-1规则) / PDR(NVD>1/4DD/NVE/玻璃体积血)",
        "AMD 分型: 干性(玻璃膜疣drusen+RPE改变) / 湿性(CNV浆液性/出血性+视网膜下液+RPED) — OCT/FFA/ICGA 确诊",
        "屈光不正: 近视(眼轴>24mm)/远视/散光/老视 — 角膜地形图(圆锥角膜筛查 Pentacam)",
    ]

    if "白内障" in dx:
        findings.insert(0, "白内障手术指征: BCVA<=0.5(双眼视力差) / 晶状体源性青光眼 / 影响眼底病变诊疗(DR/AMD)")
    if "青光眼" in dx:
        findings.insert(0, f"青光眼: IOP靶值设定 — 基线IOP={iop} => 降低25-50% => 靶IOP={round(iop*0.7,1)}-{round(iop*0.5,1)}mmHg")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("眼科")
    return _agent.clinical_result(
        summary=f"眼科 — 确诊定级完成 (S3) | {dx[:20]}",
        patient=p, stage="S3", findings=findings,
        recommendations=["IOL 计算公式选择(Barrett Universal II 优选)", "靶眼药制定(降眼压/神经保护/血流改善)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_treatment(**kwargs) -> dict:
    """治疗操作 — 药物/激光/手术/眼内注药."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "白内障: 超声乳化(Phaco) 2.2-2.8mm切口 + 折叠式IOL(单焦点/多焦点/散光/EDOF) — 表面麻醉+无缝合",
        "青光眼: 药物(前列腺素类似物/他氟前列素 一线 傍晚1滴) + 激光(SLT选择性激光小梁成形术) + 手术(小梁切除 Trabeculectomy + MMC)",
        "DR 治疗: 全视网膜光凝(PRP 1500-2000 点 1-4次) + 抗VEGF(PDR+黄斑DME) 雷珠单抗/阿柏西普/康柏西普 玻璃体注射",
        "AMD: 抗VEGF 每月(负荷3次) => T&E(治疗+延长) — OCT 指导再治疗(视网膜下/内积液消退)",
        "屈光: 角膜激光(飞秒LASIK/SMILE/TransPRK) + ICL(有晶体眼人工晶体 高度近视> -10D)",
    ]

    if "注药" in dx or "VEGF" in dx.upper():
        findings.insert(0, "眼内注药(抗VEGF): 碘伏消毒+铺巾+开睑器 => 3.5mm(颞下)进针 => 术后抗生素 3-7d + OCT 1w 复查")

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("眼科")
    return _agent.clinical_result(
        summary="眼科 — 治疗操作完成 (S4)",
        patient=p, stage="S4", findings=findings,
        recommendations=["术后抗生素+激素眼液 4-6w + 递减停用", "眼压监测(激光/手术后 1h/1d/1w)", "防外伤(术后护目镜)"],
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )


def bp_followup(**kwargs) -> dict:
    """定期复查 — 视力变化 + 眼压控制 + 术后恢复 + 病变进展."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    vitals = _agent.assess_vitals(p)
    dx = p.get("diagnosis", "")

    findings = [
        "视力变化: BCVA(每次复查) — 白内障术后 1d/1w/1m/3m; 屈光术后 1d/1w/1m/3m/6m/1y",
        "眼压控制: 青光眼用药 每 3m 复查(IOP+OCT RNFL+视野 q6-12m) — 靶眼压达成率 + 进展评估",
        "术后恢复: 白内障(后发障 PCO 5-20% 3m-2y => YAG 激光后囊切开) + 青光眼(滤过泡功能/术后低眼压/滤过泡感染)",
        "病变进展: DR(每 6-12m 散瞳+OCT+必要时 FFA) / AMD(每月/每2月 OCT+BCVA T&E方案)",
    ]

    recommendations = [
        "白内障术后: 1d/1w/1m/3m 复查 + 验光配镜(1m后) + 长期 每年 1次",
        "青光眼: 终生随访 — 每 3-6m(IOP+OCT+药物依从)+ 视野 q6m(不稳定/进展)",
        "DR: 每 6m(NPDR) / 每 3m(PDR+抗VEGF) + 全身(T2DM血糖+血脂+血压控制)",
        "AMD: 抗VEGF T&E — 稳定后延长至 每月 1次/每2月/每3月 复查",
    ]

    guides = _agent.search_guidelines(dx) or _GUIDELINES
    rules = _agent.search_rules("眼科")
    return _agent.clinical_result(
        summary="眼科 — 定期复查完成 (S5)",
        patient=p, stage="S5", findings=findings,
        recommendations=recommendations,
        guidelines=guides, rules=rules, alerts=vitals.get("alerts", []),
        guideline_refs=_GUIDELINES,
    )
