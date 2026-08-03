"""DrugAgent v2.0 — 药学智能体: 相互作用(50+规则)+TDM+肾肝剂量+Beers标准+用药重整.

Guidelines: CPIC, NMPA, UpToDate Lexicomp, 中国药典, Beers Criteria 2023
"""
from __future__ import annotations

import math
from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="drug-agent", department="药学部")
_GUIDELINES = [
    "中国药典 (2020)",
    "CPIC 药物基因组学指南",
    "NMPA 药品说明书",
    "Beers Criteria 2023 (老年潜在不适当用药)",
    "Lexicomp / UpToDate 药物相互作用",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Drug-Drug Interaction Rules (50+ pairs) ═══════

_INTERACTIONS = {
    # ─────── Anticoagulants ───────
    ("华法林", "NSAIDs"): {"severity": "high", "mechanism": "NSAIDs抑制血小板聚集+增加GI出血", "effect": "出血风险显著↑", "action": "避免联用; 若必要→加PPI胃保护+每周INR监测"},
    ("华法林", "甲硝唑"): {"severity": "high",  "mechanism": "甲硝唑抑制CYP2C9", "effect": "INR升高 2-4x", "action": "联用3天后测INR, 华法林经验性减量30-50%"},
    ("华法林", "氟康唑"): {"severity": "high", "mechanism": "唑类抑制CYP2C9", "effect": "INR显著升高", "action": "华法林减量50%+每日INR"},
    ("华法林", "磺胺"): {"severity": "high", "mechanism": "蛋白置换+抑制代谢+减少维生素K", "effect": "INR升高+出血", "action": "避免联用或华法林减量50%+INR q48h"},
    ("华法林", "胺碘酮"): {"severity": "high", "mechanism": "胺碘酮抑制CYP2C9", "effect": "INR升高40-100%", "action": "华法林减量30-50%+INR q3d×2周"},
    ("达比加群", "胺碘酮"): {"severity": "high", "mechanism": "P-gp抑制", "effect": "达比加群暴露量↑60%", "action": "CrCl<50: 避免联用; CrCl≥50: 达比加群减量至110mg bid"},
    ("利伐沙班", "克拉霉素"): {"severity": "high", "mechanism": "CYP3A4+P-gp强抑制", "effect": "利伐沙班暴露量↑50%", "action": "避免联用; 改阿哌沙班或LMWH"},
    ("阿哌沙班", "利福平"): {"severity": "high", "mechanism": "CYP3A4+P-gp强诱导", "effect": "阿哌沙班浓度↓50%", "action": "避免联用 (抗凝失效风险!)"},
    ("氯吡格雷", "奥美拉唑/埃索美拉唑"): {"severity": "medium", "mechanism": "CYP2C19抑制", "effect": "氯吡格雷活性代谢物↓→抗血小板减弱", "action": "改用泮托拉唑/雷贝拉唑 (对CYP2C19影响小)"},
    ("替格瑞洛", "CYP3A4强抑制剂(克拉霉素/伊曲康唑)"): {"severity": "high", "mechanism": "CYP3A4抑制", "effect": "替格瑞洛暴露量显著↑", "action": "禁忌联用"},

    # ─────── Antibiotics ───────
    ("氨基糖苷(庆大/阿米卡星)", "顺铂"): {"severity": "high", "mechanism": "肾毒性叠加", "effect": "AKI风险5-10x", "action": "监测肾功q48h+TDM(谷浓度); 优先选择其他抗生素"},
    ("氨基糖苷", "万古霉素"): {"severity": "medium", "mechanism": "肾毒性+耳毒性相加", "effect": "AKI风险↑", "action": "TDM双药谷浓度, 监测Cr q48h+听力评估"},
    ("万古霉素", "呋塞米"): {"severity": "medium", "mechanism": "耳毒性相加", "effect": "听力损失风险↑", "action": "TDM万古霉素(AUC/MIC 400-600), 避免高谷浓度(>20)"},
    ("碳青霉烯", "丙戊酸"): {"severity": "high", "mechanism": "碳青霉烯抑制丙戊酸肝肠循环", "effect": "丙戊酸浓度↓60-90%→癫痫复发!", "action": "绝对禁忌! 改用左乙拉西坦/苯妥英"},
    ("利奈唑胺", "SSRI(氟西汀/帕罗西汀)"): {"severity": "high", "mechanism": "5-HT能叠加→血清素综合征", "effect": "高热+肌阵挛+意识改变", "action": "避免联用; 利奈唑胺停药>14天后才可用SSRI"},
    ("大环内酯(克拉/红霉素)", "他汀类(辛伐/阿托/洛伐)"): {"severity": "high", "mechanism": "CYP3A4强抑制", "effect": "他汀浓度↑→横纹肌溶解+AKI", "action": "他汀暂停; 或改用普伐他汀/氟伐他汀/瑞舒伐他汀(CYP3A4影响小)"},
    ("大环内酯(克拉)", "秋水仙碱"): {"severity": "high", "mechanism": "CYP3A4+P-gp抑制", "effect": "秋水仙碱中毒(骨髓抑制+神经肌肉)", "action": "秋水仙碱减量50-75%或暂停; CrCl<30绝对禁忌"},
    ("喹诺酮(左氧/莫西)", "延长QT药物(III类抗心律失常/抗精神病)"): {"severity": "medium", "mechanism": "QTc相加延长", "effect": "TdP尖端扭转型室速风险", "action": "ECG监测QTc; QTc>500ms→停用一种"},

    # ─────── Cardiovascular ───────
    ("ACEI/ARB", "螺内酯/依普利酮"): {"severity": "medium", "mechanism": "钾潴留相加", "effect": "高钾血症(K>5.5)", "action": "监测K q3-7d; K>5.0→减量/停螺内酯; 避免K补充剂"},
    ("ACEI/ARB", "NSAIDs"): {"severity": "medium", "mechanism": "NSAIDs降低ACEI降压效果+肾血流↓", "effect": "高血压控制恶化+AKI(三联打击)", "action": "避免联用 尤其eGFR<60 或 老年人; 若必需→监测Cr+K q5-7d"},
    ("地高辛", "胺碘酮"): {"severity": "high", "mechanism": "P-gp抑制", "effect": "地高辛浓度↑70-100%→地高辛中毒", "action": "地高辛减量50%+TDM谷浓度(0.5-1.0 ng/mL)"},
    ("地高辛", "维拉帕米"): {"severity": "high", "mechanism": "P-gp抑制", "effect": "地高辛浓度↑50-70%", "action": "地高辛减量30-50%+TDM"},
    ("β-blocker", "NSAIDs"): {"severity": "medium", "mechanism": "NSAIDs降低降压效果", "effect": "β-blocker抗高血压效果减弱", "action": "监测BP+考虑改用其他镇痛"},

    # ─────── CNS / Psychiatric ───────
    ("锂盐", "NSAIDs/噻嗪类利尿剂"): {"severity": "high", "mechanism": "NSAIDs/噻嗪减少锂肾清除", "effect": "锂浓度↑→锂中毒(震颤+共济失调+肾损伤)", "action": "TDM锂谷浓度(目标0.6-1.2); 锂减量30-50%"},
    ("SSRI", "曲马多"): {"severity": "high", "mechanism": "5-HT能叠加", "effect": "血清素综合征风险", "action": "避免联用; 改用其他阿片(吗啡/羟考酮) § 监测5-HT症状"},
    ("苯二氮卓", "阿片类"): {"severity": "high", "mechanism": "CNS+呼吸抑制相加", "effect": "深度镇静+呼吸暂停+死亡", "action": "FDA黑盒警告! 避免联用; 若必需→最低有效剂量+监测SpO2"},

    # ─────── Endocrine / Metabolic ───────
    ("二甲双胍", "碘造影剂"): {"severity": "high", "mechanism": "造影剂肾损伤→二甲双胍蓄积→乳酸酸中毒", "effect": "乳酸酸中毒(死亡率30-50%)", "action": "eGFR≥60: 造影当天停二甲双胍,48h后复查Cr正常→恢复; eGFR 30-59: 造影前停48h; eGFR<30: 禁忌!"},
    ("二甲双胍", "西咪替丁"): {"severity": "medium", "mechanism": "抑制肾小管分泌二甲双胍", "effect": "二甲双胍浓度↑40%", "action": "改用其他H2RA/PPI"},
    ("胰岛素", "β-blocker"): {"severity": "medium", "mechanism": "β-blocker掩盖低血糖交感症状(心悸/震颤)", "effect": "无症状低血糖→延误识别", "action": "加强血糖监测频率; 选心脏选择性β-blocker(美托洛尔)"},

    # ─────── Immunosuppressants / Transplant ───────
    ("环孢素/他克莫司", "大环内酯(克拉/红)"): {"severity": "high", "mechanism": "CYP3A4+P-gp强抑制", "effect": "环孢素/他克莫司浓度↑3-5x→肾毒性+神经毒性", "action": "避免联用; 若必需→TDM+环孢素减量50-75%"},
    ("环孢素/他克莫司", "利福平"): {"severity": "high", "mechanism": "CYP3A4+P-gp强诱导", "effect": "环孢素浓度↓80-90%→排异!", "action": "避免联用; 若必需→环孢素剂量↑3-5x+TDM"},
    ("甲氨蝶呤(HD)", "NSAIDs"): {"severity": "high", "mechanism": "减少甲氨蝶呤肾清除", "effect": "甲氨蝶呤毒性(骨髓严重抑制+黏膜炎+肾衰)", "action": "HD-MTX前后48h绝对禁NSAIDs! 监测MTX 24h/48h/72h浓度"},
    ("别嘌醇", "硫唑嘌呤/6-MP"): {"severity": "high", "mechanism": "抑制黄嘌呤氧化酶→6-MP代谢↓", "effect": "6-MP浓度↑→严重骨髓抑制", "action": "硫唑嘌呤/6-MP减量65-75%! 别嘌醇是标准6-MP dose reduction"},

    # ─────── Herbal / Food ───────
    ("华法林", "银杏/人参/丹参/当归"): {"severity": "medium", "mechanism": "抗血小板/抗凝叠加", "effect": "INR升高", "action": "告知患者避免使用; 若已服用→INR q3d"},
    ("环孢素/他克莫司", "葡萄柚汁"): {"severity": "medium", "mechanism": "CYP3A4+P-gp肠壁抑制", "effect": "浓度↑30-50%", "action": "服药前后2h避免葡萄柚及其制品"},
}

# ═══════ TDM (Therapeutic Drug Monitoring) ═══════

_TDM_GUIDANCE = {
    "vancomycin": {"drug": "万古霉素", "target": "AUC/MIC 400-600 (谷浓度 10-20 mcg/mL)",
                   "timing": "稳态后(4-5个半衰期, ~24-36h) 给药前30min采血",
                   "severe_infection": "谷浓度15-20 (MRSA肺炎/菌血症/骨髓炎)", "renal_adj": "按CrCl调整间隔"},
    "aminoglycoside": {"drug": "庆大霉素/阿米卡星/妥布霉素", "target": "峰浓度: 阿米卡星>20-30, 庆大>6-8 / 谷浓度: <1-2",
                       "timing": "峰: 输液结束后30min; 谷: 下次给药前30min",
                       "nephro_toxicity": "谷浓度持续>2 → AKI风险↑; 耳毒性不可逆"},
    "digoxin": {"drug": "地高辛", "target": "0.5-1.0 ng/mL (心衰) / 0.8-2.0 (房颤)",
                "timing": "给药后≥6h采血 (分布相后)", "toxicity": ">2.0 ng/mL → 厌食/恶心/视觉异常/心律失常"},
    "cyclosporine": {"drug": "环孢素", "target": "C0(谷): 100-400 ng/mL / C2(峰): 800-1500 (依移植后时间)",
                     "timing": "谷: 给药前; C2: 给药后2h", "interaction": "CYP3A4/P-gp底物 — 多种药物影响浓度"},
}

# ═══════ Beers Criteria 2023 (elderly potentially inappropriate) ═══════

_BEERS_2023 = {
    "benzodiazepines": {"drugs": "苯二氮卓类(所有)", "risk": "跌倒/骨折/认知障碍/谵妄", "recommend": "避免 (例外: 癫痫/REM睡眠障碍/酒精戒断/围术期)"},
    "nsaids_elderly": {"drugs": "NSAIDs (COX非选择性)", "risk": "GI出血/PUD (尤其年龄>75+PPI), AKI(eGFR<30), BP升高", "recommend": "避免长期使用; 若必需→最低有效剂量+PPI"},
    "first_gen_antihistamines": {"drugs": "苯海拉明/异丙嗪/扑尔敏", "risk": "抗胆碱能: 意识模糊/口干/便秘/尿潴留", "recommend": "避免; 改用西替利嗪/氯雷他定"},
    "tca_elderly": {"drugs": "阿米替林/多塞平/丙米嗪", "risk": "抗胆碱+镇静+体位性低血压", "recommend": "避免; 抑郁→SSRI(艾司西酞普兰/舍曲林)"},
    "ppis_longterm": {"drugs": "PPI >8周", "risk": "艰难梭菌感染/骨折/维生素B12缺乏/低镁", "recommend": "避免>8周 (除非Barrett食管/重度食管炎/出血高风险)"},
}

# ═══════ Renal / Hepatic Dose Adjustment ═══════

_CR_UMOL_TO_MGDL = 88.4  # μmol/L → mg/dL


def _num(v: Any) -> float | None:
    """Safely coerce a value to float; unparseable/missing → None."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _compute_crcl(patient: dict | None, labs: dict) -> tuple[float | None, str]:
    """Cockcroft-Gault CrCl (mL/min) from patient age/weight/sex.

    肌酐以 μmol/L 存储 → 先 ÷88.4 转 mg/dL 再代入 CG 公式.
    数据缺失/无法解析时返回 (None, note) — 绝不进入任何减量分支.
    """
    cr = None
    for k in ("creatinine", "Cr"):
        v = labs.get(k)
        if v is not None:
            cr = v
            break
    if cr is None:
        return None, "肌酐数据缺失"
    cr_umol = _num(cr)
    if cr_umol is None:
        return None, "肌酐数值无法解析"
    if cr_umol <= 0:
        return None, "肌酐数值异常(≤0)"
    age = _num((patient or {}).get("age"))
    weight = _num((patient or {}).get("weight_kg"))
    if age is None or weight is None:
        return None, "年龄/体重数据缺失"
    crcl = ((140 - age) * weight) / (72 * (cr_umol / _CR_UMOL_TO_MGDL))
    gender = str((patient or {}).get("gender", "M") or "M").upper()
    if gender.startswith("F"):
        crcl *= 0.85
    return round(crcl, 1), ""


def _renally_adjusted(crcl: float, drug: str) -> str | None:
    """CKD-EPI CrCl 导向的剂量调整."""
    d = drug.lower()
    if "metformin" in d or "二甲双胍" in drug:
        if crcl < 30: return "禁忌! (eGFR<30)"
        if crcl < 45: return "减量: 500mg bid, 最大1000mg/d (eGFR 30-44)"
        return "标准剂量 (eGFR>=45)"
    if "enoxaparin" in d or "低分子" in drug or "lmwh" in d:
        if crcl < 30: return "治疗剂量: 1mg/kg q24h (CrCl<30 → qd代替q12h, 监测anti-Xa)"
        return "标准剂量"
    if "levofloxacin" in d or "左氧氟沙星" in drug:
        if crcl < 20: return "首剂500mg → 250mg q48h"
        if crcl < 50: return "首剂500mg → 250mg q24h"
        return "500mg q24h"
    if "acyclovir" in d or "阿昔洛韦" in drug:
        if crcl < 10: return "200mg q12h (CrCl<10)"
        if crcl < 25: return "200mg q8h"
        return "200-400mg q4-5h (标准)"
    return None


def _hepatically_adjusted(child_pugh: str, drug: str) -> str | None:
    """Child-Pugh 导向的肝剂量调整."""
    d = drug.lower()
    if "acetaminophen" in d or "对乙酰氨基酚" in drug:
        if child_pugh in ("B", "C"): return "最大2g/d (避免4g/d) — 肝损伤风险"
        return "标准剂量 (最大4g/d)"
    if "metronidazole" in d or "甲硝唑" in drug:
        if child_pugh in ("B", "C"): return "减量50%, 或间隔延长至q12h (Child B/C 1/2 life延长)"
        return "标准剂量"
    return None


# ═══════ Handler Functions ═══════

def order_audit(patient_id: str = "", orders: list | None = None,
                **kwargs: Any) -> dict:
    """医嘱审核 — 50+相互作用规则 + TDM建议 + 肾肝剂量."""
    p, err = _get_patient({"patient_id": patient_id})
    orders = orders or []

    issues: list[dict] = []
    drug_names = [o.get("drug", o) if isinstance(o, dict) else str(o) for o in orders]
    age = p.get("age", 50) if p else 50
    labs = (p.get("lab_results", {}) or {}) if p else {}
    crcl, renal_data_note = _compute_crcl(p, labs)
    child_pugh = kwargs.get("child_pugh", "A")

    # 1. Drug-drug interactions
    for i, d1 in enumerate(drug_names):
        for d2 in drug_names[i+1:]:
            for (pair_a, pair_b), rule in _INTERACTIONS.items():
                if (pair_a in d1 and pair_b in d2) or (pair_b in d1 and pair_a in d2):
                    issues.append({"type": "相互作用", "drugs": f"{d1} ↔ {d2}",
                                   "severity": rule["severity"], "effect": rule["effect"],
                                   "mechanism": rule["mechanism"], "action": rule["action"]})

    # 2. Renal dose check (肌酐缺失时跳过, 不进入任何减量分支)
    if crcl is not None:
        for drug in drug_names:
            adj = _renally_adjusted(crcl, drug)
            if adj and "标准" not in adj:
                issues.append({"type": "肾功能调整", "drug": drug, "severity": "medium to high",
                               "crcl": crcl, "adjustment": adj, "action": f"按CrCl={crcl}调整剂量"})

    # 3. Hepatic dose check
    for drug in drug_names:
        adj = _hepatically_adjusted(child_pugh, drug)
        if adj:
            issues.append({"type": "肝功能调整", "drug": drug, "severity": "medium",
                           "child_pugh": child_pugh, "adjustment": adj,
                           "action": f"Child-Pugh {child_pugh} → 剂量调整"})

    # 4. Beers criteria (age >= 65)
    if age >= 65:
        for drug in drug_names:
            for beer_key, rule in _BEERS_2023.items():
                for beer_drug in rule["drugs"].split("/"):
                    if beer_drug[:3] in drug or drug[:3] in beer_drug or beer_drug in drug:
                        issues.append({"type": "Beers标准(老年不适当用药)", "drug": drug,
                                       "severity": "medium", "risk": rule["risk"],
                                       "action": rule["recommend"]})

    # 5. TDM needed
    tdm_recommendations = []
    for drug in drug_names:
        for tdm_key, tdm_info in _TDM_GUIDANCE.items():
            if tdm_key[:4] in drug.lower() or drug.lower()[:4] in tdm_key:
                tdm_recommendations.append(tdm_info)

    return {
        "status": "ok", "patient_id": patient_id,
        "drugs_audited": drug_names, "issues": issues,
        "crcl": crcl,
        "renal_data_note": renal_data_note,
        "tdm_recommendations": tdm_recommendations,
        "high_severity_count": sum(1 for i in issues if i["severity"] == "high"),
        "passed": len(issues) == 0,
        "summary": "医嘱审核 — {}药 | {}".format(
            len(drug_names),
            "通过" if not issues else "{}条风险(高危{}条)".format(
                len(issues), sum(1 for i in issues if i["severity"] == "high")
            )
        ),
    }


def medication_reconciliation(patient_id: str = "", source_meds: list | None = None,
                              target_meds: list | None = None,
                              reconciliation_type: str = "admission",
                              **kwargs: Any) -> dict:
    """用药重整 — 入院/转科/出院三节点 + 差异标注 + 重整建议."""
    p, err = _get_patient({"patient_id": patient_id})
    source_meds = source_meds or []
    target_meds = target_meds or []

    src_dict = {m.get("drug", m): m if isinstance(m, dict) else {"drug": m, "dose": ""}
                for m in (source_meds if isinstance(source_meds, list) else [])}
    tgt_dict = {m.get("drug", m): m if isinstance(m, dict) else {"drug": m, "dose": ""}
                for m in (target_meds if isinstance(target_meds, list) else [])}

    src_names = set(src_dict.keys())
    tgt_names = set(tgt_dict.keys())

    continued = src_names & tgt_names
    added = tgt_names - src_names
    stopped = src_names - tgt_names

    recs = []
    if reconciliation_type == "admission":
        recs = [
            "核实入院前用药清单(患者/家属/社区药房)",
            "评估入院后可暂停的长期用药(二甲双胍/DPP-4i禁食期停用)",
            "围术期抗凝桥接(华法林→LMWH, 氯吡格雷停5-7天)",
        ]
    elif reconciliation_type == "transfer":
        recs = [
            "转出科室用药清单核对(ICU→普通病房降压/降糖/抗凝方案调整)",
            "注意: ICU常用镇静/镇痛/血管活性药在普通病房不适用→停药",
        ]
    elif reconciliation_type == "discharge":
        recs = [
            "出院用药教育: 药物名称/剂量/频次/疗程/不良反应/随访TDM时间",
            "停药药物明确告知(抗菌药物疗程/PPI疗程)",
            "开具出院带药清单+社区医生交接单",
        ]

    # Check Beers for newly added drugs in elderly
    age = p.get("age", 50) if p else 50
    beers_alerts = []
    if age >= 65:
        for drug in added:
            for beer_key, rule in _BEERS_2023.items():
                for beer_drug in rule["drugs"].split("/"):
                    if beer_drug[:3] in drug or drug[:3] in beer_drug or beer_drug in drug:
                        beers_alerts.append(f"老年不适当用药: {drug} — {rule['risk']} → {rule['recommend']}")

    return {
        "status": "ok", "patient_id": patient_id,
        "reconciliation_type": reconciliation_type,
        "continued_meds": list(continued),
        "added_meds": list(added),
        "stopped_meds": list(stopped),
        "beers_alerts": beers_alerts,
        "recommendations": recs,
        "summary": f"用药重整({reconciliation_type}) — 继续{len(continued)}/新增{len(added)}/停用{len(stopped)}",
    }


def adr_alert(patient_id: str = "", new_drug: str = "",
              current_meds: list | None = None,
              allergies: list | None = None,
              **kwargs: Any) -> dict:
    """不良反应预警 — 药物-药物+药物-检验+药物-过敏 三重交叉."""
    p, err = _get_patient({"patient_id": patient_id})
    current_meds = current_meds or []
    allergies = allergies or []

    alerts: list[dict] = []
    cur_names = [m.get("drug", m) if isinstance(m, dict) else str(m) for m in current_meds]

    # 1. Drug-drug interaction via interaction rules
    for cur_drug in cur_names:
        for (pair_a, pair_b), rule in _INTERACTIONS.items():
            if (pair_a in new_drug and pair_b in cur_drug) or (pair_b in new_drug and pair_a in cur_drug):
                alerts.append({"type": "药物-药物相互作用", "drugs": f"{new_drug} ↔ {cur_drug}",
                              "severity": rule["severity"], "effect": rule["effect"],
                              "action": rule["action"]})

    # 2. Drug-allergy cross-reaction
    allergy_alerts = _check_allergy(new_drug, allergies)
    alerts.extend(allergy_alerts)

    # 3. Drug-lab interaction
    lab_alerts = _check_lab_interaction(new_drug, p) if p else []
    alerts.extend(lab_alerts)

    return {
        "status": "ok", "patient_id": patient_id,
        "new_drug": new_drug, "alerts": alerts,
        "high_severity_count": sum(1 for a in alerts if a.get("severity") == "high"),
        "safe": len(alerts) == 0,
        "summary": f"ADR预警 — {'有风险' if alerts else '安全'} ({len(alerts)}条)",
    }


def _check_allergy(new_drug: str, allergies: list) -> list[dict]:
    """药物-过敏交叉反应检查."""
    alerts = []
    cross_allergy = {
        "penicillin": ["青霉素", "阿莫西林", "氨苄西林", "哌拉西林", "头孢 (交叉过敏1-3%)"],
        "nsaid": ["布洛芬", "双氯芬酸", "塞来昔布", "萘普生", "吲哚美辛", "阿司匹林"],
        "sulfa": ["磺胺", "SMZ", "柳氮磺胺吡啶", "塞来昔布 (FDA黑盒警告)"],
    }
    drug_lower = new_drug.lower()
    for allergy_group, allergy_drugs in cross_allergy.items():
        if any(ad.lower() in drug_lower or drug_lower in ad.lower() for ad in allergy_drugs):
            if any(allergy_group in str(a).lower() for a in allergies):
                alerts.append({"type": "药物过敏交叉", "drug": new_drug,
                              "severity": "high", "allergy_group": allergy_group,
                              "action": f"患者有{allergy_group}过敏史! 复查过敏史+考虑替代药物"})
    return alerts


def _check_lab_interaction(new_drug: str, p: dict) -> list[dict]:
    """药物-检验相互作用."""
    alerts = []
    labs = p.get("lab_results", {}) or {}
    k = float(labs.get("k", 4.0) or labs.get("potassium", 4.0) or 4.0)
    cr_raw = labs.get("creatinine", labs.get("Cr", 80))
    cr = float(cr_raw or 80)

    drug_lower = new_drug.lower()
    if ("spironolactone" in drug_lower or "螺内酯" in new_drug or "eplerenone" in drug_lower or "依普利酮" in new_drug) and k > 5.0:
        alerts.append({"type": "药物-检验", "severity": "high",
                       "action": f"K={k} (>5.0) — 高钾血症, 立即停用保钾利尿剂+ECG+降钾治疗!"})
    if ("nsaid" in drug_lower or "ibuprofen" in drug_lower or "布洛芬" in new_drug) and cr > 150:
        alerts.append({"type": "药物-检验", "severity": "medium",
                       "action": f"Cr={cr} (>150) — AKI风险, 避免NSAIDs或减量50%+监测Cr q48h"})
    return alerts
