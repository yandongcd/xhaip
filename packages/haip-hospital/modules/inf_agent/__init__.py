"""INF-Agent v2.0 — 感染鉴别智能诊断: 细菌/病毒/真菌/非感染 + 检验推荐 + 抗生素建议 + 脓毒症筛查.

Guidelines: Surviving Sepsis Campaign 2021, IDSA, CLSI M100 (2024), 中国抗菌药物临床应用指导原则
"""
from __future__ import annotations

import math
from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="inf-agent", department="检验科")
_GUIDELINES = [
    "Surviving Sepsis Campaign 2021 — 脓毒症与脓毒性休克管理国际指南",
    "IDSA 2024 感染病诊疗指南",
    "CLSI M100 药敏判读标准 (2024)",
    "中国抗菌药物临床应用指导原则 (2015)",
    "中国碳青霉烯耐药革兰阴性杆菌(CRO)感染诊治与防控指南 (2023)",
    "热病/桑福德抗微生物治疗指南 (第53版)",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ Sepsis / SIRS / qSOFA Screening ═══════

def _num(v: Any) -> float | None:
    """Safely coerce a value to float; unparseable/missing → None."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _organ_dysfunction_flags(labs: dict) -> list[str]:
    """器官功能障碍标志 — 乳酸/血小板/肌酐/胆红素.

    肌酐 (creatinine/Cr) 与胆红素 (bilirubin/TBil) 在本数据集中以
    μmol/L 存储, 先换算 mg/dL (Cr ÷88.4, TBil ÷17.1) 再与 1.2 mg/dL 阈值比较.
    """
    flags: list[str] = []
    lactate = _num(labs.get("lactate"))
    if lactate is not None and lactate > 2:
        flags.append(f"高乳酸血症 (Lac={lactate}) — 组织低灌注")
    plt = _num(labs.get("platelet", labs.get("PLT")))
    if plt is not None and plt < 100:
        flags.append(f"血小板减少 (PLT={plt})")
    cr = _num(labs.get("creatinine", labs.get("Cr")))
    if cr is not None:
        cr_mgdl = cr / 88.4
        if cr_mgdl > 1.2:
            flags.append(f"急性肾损伤 (Cr={cr:.1f}μmol/L={cr_mgdl:.1f}mg/dL)")
    bili = _num(labs.get("bilirubin", labs.get("TBil")))
    if bili is not None:
        bili_mgdl = bili / 17.1
        if bili_mgdl > 1.2:
            flags.append(f"高胆红素血症 (TBil={bili:.1f}μmol/L={bili_mgdl:.1f}mg/dL)")
    return flags


def _sirs_criteria(labs: dict, vitals: dict | None = None) -> dict:
    """SIRS 全身炎症反应综合征 4 项标准评估."""
    vt = vitals or {}
    wbc = float(labs.get("wbc", 8) or 8)
    hr = int(vt.get("heart_rate", 80) or 80)
    rr = int(vt.get("respiratory_rate", 16) or 16)
    temp = float(vt.get("temperature", 37.0) or 37.0)

    met = 0
    criteria = []
    if temp > 38 or temp < 36:
        met += 1
        criteria.append(f"体温异常 ({temp}C)")
    if hr > 90:
        met += 1
        criteria.append(f"心动过速 (HR={hr})")
    if rr > 20 or float(labs.get("paCO2", 40) or 40) < 32:
        met += 1
        criteria.append(f"呼吸急促 (RR={rr})")
    if wbc > 12 or wbc < 4 or float(labs.get("bands_pct", 5) or 5) > 10:
        met += 1
        criteria.append(f"WBC异常 (WBC={wbc})")

    return {
        "met": met,
        "positive": met >= 2,
        "criteria": criteria,
        "interpretation": "SIRS阳性 — 需进一步评估感染" if met >= 2 else "SIRS阴性",
    }


def _qsofa(vitals: dict | None = None) -> dict:
    """qSOFA 快速序贯器官衰竭评估 (床旁)."""
    vt = vitals or {}
    rr = int(vt.get("respiratory_rate", 16) or 16)
    sbp = int(vt.get("sbp", 120) or 120)
    gcs = int(vt.get("gcs", 15) or 15)

    score = 0
    criteria = []
    if rr >= 22:
        score += 1
        criteria.append(f"RR={rr} (>=22)")
    if sbp <= 100:
        score += 1
        criteria.append(f"SBP={sbp} (<=100)")
    if gcs < 15:
        score += 1
        criteria.append(f"GCS={gcs} (<15)")

    return {
        "score": score,
        "positive": score >= 2,
        "criteria": criteria,
        "interpretation": "qSOFA>=2 — 疑似脓毒症, 需评估器官功能障碍" if score >= 2 else "qSOFA阴性",
    }


# ═══════ Infection Type Probability Engine ═══════

def _calc_infection_prob(pct: float, wbc: float, crp: float, neut_pct: float,
                         lymph_pct: float, il6: float, lactate: float,
                         g_test: bool, gm_test: bool,
                         immunosuppressed: bool, abx_history: bool) -> dict:
    """多指标加权感染类型概率引擎."""
    prob = {"bacterial": 0.0, "viral": 0.0, "fungal": 0.0, "non_infectious": 0.0}
    evidence = {"bacterial": [], "viral": [], "fungal": [], "non_infectious": []}

    # ── Bacterial signals ──
    bacterial_score = 0.0
    if pct > 10:
        bacterial_score += 4.0
        evidence["bacterial"].append("PCT>10 强烈提示细菌感染/sepsis")
    elif pct > 2:
        bacterial_score += 2.5
        evidence["bacterial"].append("PCT>2 提示细菌感染可能")
    elif pct > 0.5:
        bacterial_score += 1.0
        evidence["bacterial"].append("PCT>0.5 轻度升高")

    if wbc > 15 and neut_pct > 85:
        bacterial_score += 2.0
        evidence["bacterial"].append("WBC>15+NEUT>85% 类白血病反应")
    elif wbc > 12 and neut_pct > 80:
        bacterial_score += 1.5
        evidence["bacterial"].append("WBC升高+中性粒细胞增多")
    elif wbc < 4 and neut_pct > 90:
        bacterial_score += 1.5
        evidence["bacterial"].append("WBC降低+核左移 严重感染可能")

    if crp > 100:
        bacterial_score += 2.0
        evidence["bacterial"].append("CRP>100 重度炎症")
    elif crp > 50:
        bacterial_score += 1.0
        evidence["bacterial"].append("CRP>50 中度炎症")

    if il6 > 100:
        bacterial_score += 1.5
        evidence["bacterial"].append("IL-6>100 强烈炎症反应")

    if lactate > 4:
        bacterial_score += 2.0
        evidence["bacterial"].append("Lac>4 组织低灌注/sepsis")

    # ── Viral signals ──
    viral_score = 0.0
    if pct < 0.25:
        viral_score += 2.0
        evidence["viral"].append("PCT<0.25 不支持细菌感染")
    elif pct < 0.5:
        viral_score += 1.0

    if lymph_pct > 50:
        viral_score += 2.0
        evidence["viral"].append("淋巴细胞比例升高 支持病毒感染")
    elif lymph_pct > 40:
        viral_score += 1.0

    if wbc >= 3 and wbc <= 10 and crp < 20:
        viral_score += 1.5
        evidence["viral"].append("WBC正常+CRP轻度 病毒感染特征")

    if il6 > 20 and il6 < 80:
        viral_score += 0.5

    # ── Fungal signals ──
    fungal_score = 0.0
    if g_test and gm_test:
        fungal_score += 3.0
        evidence["fungal"].append("G+GM试验双阳性 高度提示真菌感染")
    elif g_test:
        fungal_score += 1.5
        evidence["fungal"].append("G试验阳性 真菌感染可能")

    if immunosuppressed:
        fungal_score += 2.0
        evidence["fungal"].append("免疫抑制状态 真菌感染高危")
    if abx_history:
        fungal_score += 1.0
        evidence["fungal"].append("长期广谱抗生素史 真菌二重感染风险")
    if neut_pct < 50 and wbc < 3:
        fungal_score += 1.0
        evidence["fungal"].append("粒缺 侵袭性真菌感染高危")

    if pct >= 0.5 and pct <= 2:
        fungal_score += 0.5

    # ── Non-infectious signals ──
    ni_score = 0.0
    if crp < 10 and pct < 0.25 and wbc >= 4 and wbc <= 10:
        ni_score += 5.0
        evidence["non_infectious"].append("所有炎症指标正常 强烈支持非感染性")
    elif crp < 10 and pct < 0.5:
        ni_score += 2.0
        evidence["non_infectious"].append("CRP+PCT低水平 非感染性可能")

    # Boost non-infectious when there's no evidence for infection
    if pct < 0.5 and wbc >= 4 and wbc <= 10 and crp < 20 and not immunosuppressed:
        ni_score += 3.0

    # ── Normalize to probabilities ──
    raw = {"bacterial": bacterial_score, "viral": viral_score,
           "fungal": fungal_score, "non_infectious": ni_score}
    total = sum(raw.values())
    if total > 0:
        prob = {k: round(v / total * 100) for k, v in raw.items()}
    else:
        prob = {"bacterial": 25, "viral": 25, "fungal": 25, "non_infectious": 25}

    top_type = max(prob, key=prob.get)
    return {
        "probabilities": prob,
        "primary_type": top_type,
        "evidence": evidence,
        "raw_scores": raw,
    }


# ═══════ Antibiogram / Antimicrobial Advice ═══════

_SITE_EMPIRIC = {
    "respiratory": {
        "community": "头孢曲松 2g q24h IV + 阿奇霉素 500mg qd PO/IV",
        "hospital": "哌拉西林/他唑巴坦 4.5g q6h IV 或 头孢吡肟 2g q8h IV + 万古霉素 (MRSA高危)",
        "severe": "美罗培南 1g q8h IV + 万古霉素 1g q12h IV (ICU重症CAP)",
    },
    "urinary": {
        "community": "头孢曲松 1g q24h IV 或 呋喃妥因 100mg q12h PO (单纯性)",
        "hospital": "哌拉西林/他唑巴坦 4.5g q8h IV 或 头孢吡肟 1-2g q12h IV",
        "severe": "美罗培南 1g q8h IV (ESBL高危) ± 万古霉素 (肠球菌)",
    },
    "intra_abdominal": {
        "community": "头孢曲松 2g q24h + 甲硝唑 500mg q8h IV",
        "hospital": "哌拉西林/他唑巴坦 4.5g q6h IV",
        "severe": "美罗培南 1g q8h IV (穿孔/ICU) ± 万古霉素",
    },
    "bloodstream": {
        "community": "万古霉素 1g q12h IV + 哌拉西林/他唑巴坦 4.5g q6h IV",
        "hospital": "美罗培南 1g q8h IV + 万古霉素 1g q12h IV (覆盖MRSA/ESBL/铜绿)",
        "severe": "美罗培南 1g q8h IV + 万古霉素 1g q12h IV + 卡泊芬净 70mg负荷→50mg qd (粒缺+真菌高危)",
    },
    "cns": {
        "all": "头孢曲松 2g q12h IV + 万古霉素 1g q8-12h IV + 氨苄西林 2g q4h IV (覆盖李斯特菌 老年人)",
    },
    "skin_soft_tissue": {
        "community": "头孢唑林 2g q8h IV 或 克林霉素 600mg q8h IV",
        "severe": "万古霉素 1g q12h IV + 哌拉西林/他唑巴坦 4.5g q6h (坏死性筋膜炎/NSTI)",
    },
}

_MDRO_RISK_FACTORS = {
    "esbl": "近期住院/抗菌药物暴露/留置导管/ESBL定植史",
    "mrsa": "近期住院/MRSA定植/手术/透析/入住ICU",
    "cre": "碳青霉烯暴露/ESBL感染史/粒缺/器官移植",
    "vre": "万古霉素暴露/ICU住院/血液肿瘤/粒缺",
    "pseudomonas": "结构性肺病/BALF培养阳性/长期激素/粒缺",
}

_ANTIFUNGAL = {
    "candida": {
        "non_neutropenic": "卡泊芬净 70mg IV 负荷→50mg qd 或 米卡芬净 100mg qd IV",
        "neutropenic": "卡泊芬净 70mg IV 负荷→50mg qd (首选棘白菌素)",
    },
    "aspergillus": "伏立康唑 6mg/kg q12h IV×2次 负荷→4mg/kg q12h IV 或 艾沙康唑 200mg q8h×2天→200mg qd",
}


def _renal_dose(crcl: float, drug: str) -> str:
    """肾功能调整剂量."""
    if drug in ("piperacillin_tazobactam", "哌拉西林/他唑巴坦"):
        if crcl < 20:
            return "4.5g q12h IV (CrCl<20)"
        return "4.5g q6-8h IV"
    if drug in ("meropenem", "美罗培南"):
        if crcl < 10:
            return "500mg q24h IV (CrCl<10)"
        elif crcl < 26:
            return "500mg q12h IV"
        elif crcl < 51:
            return "1g q12h IV"
        return "1g q8h IV"
    if drug in ("vancomycin", "万古霉素"):
        if crcl < 20:
            return "1g IV 负荷→按TDM调整 (CrCl<20, 每周2-3次)"
        elif crcl < 50:
            return "1g q24-48h IV (依TDM谷浓度10-20mcg/mL)"
        return "1g q12h IV"
    if drug in ("cefepime", "头孢吡肟"):
        if crcl < 10:
            return "1g q24h IV (CrCl<10)"
        elif crcl < 60:
            return "1g q12h IV"
        return "2g q8h IV"
    return ""


# ═══════ Handler Functions ═══════


def infection_type(patient_id: str = "", **kwargs: Any) -> dict:
    """感染类型判别 — 细菌/病毒/真菌/非感染 → 概率分布 + 证据链."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    labs = p.get("lab_results", {}) or {}
    pct = float(labs.get("PCT", 0.5) or 0.5)
    wbc = float(labs.get("wbc", 8) or 8)
    crp = float(labs.get("crp", 20) or 20)
    neut_pct = float(labs.get("neutrophil_pct", 65) or 65)
    lymph_pct = float(labs.get("lymphocyte_pct", 25) or 25)
    il6 = float(labs.get("IL6", 20) or 20)
    lactate = float(labs.get("lactate", 1.5) or 1.5)
    g_test = str(labs.get("G_test", "")).lower() in ("positive", "阳性", "true", "1")
    gm_test = str(labs.get("GM_test", "")).lower() in ("positive", "阳性", "true", "1")

    dx = p.get("diagnosis", "")
    immunosuppressed = any(kw in dx for kw in ["粒缺", "免疫", "移植", "化疗", "HIV", "AIDS"])
    abx_history = "抗生素" in dx or "antimicrobial" in dx.lower()

    result = _calc_infection_prob(pct, wbc, crp, neut_pct, lymph_pct, il6, lactate,
                                  g_test, gm_test, immunosuppressed, abx_history)

    # SIRS/qSOFA for context
    vitals = kwargs.get("vitals", {})
    sirs = _sirs_criteria(labs, vitals)
    qsofa = _qsofa(vitals)

    prob = result["probabilities"]
    top = result["primary_type"]
    evidence = result.get("evidence", {}).get(top, [])

    return {
        "status": "ok",
        "patient_id": patient_id,
        "infection_type": top,
        "probabilities": prob,
        "evidence": evidence[:5],
        "key_indicators": {
            "PCT": f"{pct} ng/mL {'(升高)' if pct > 2 else '(正常)' if pct < 0.5 else '(轻度升高)'}",
            "WBC": f"{wbc} x10^9/L {'(升高)' if wbc > 12 else '(降低)' if wbc < 4 else '(正常)'}",
            "CRP": f"{crp} mg/L {'(显著升高)' if crp > 100 else '(升高)' if crp > 50 else '(正常)' if crp < 10 else '(轻度升高)'}",
            "NEUT": f"{neut_pct}% {'(升高)' if neut_pct > 80 else ''}",
            "LYMPH": f"{lymph_pct}% {'(升高)' if lymph_pct > 40 else ''}",
            "IL-6": f"{il6} pg/mL {'(显著升高)' if il6 > 100 else ''}",
            "Lactate": f"{lactate} mmol/L {'(升高)' if lactate > 2 else ''}",
        },
        "sirs": sirs,
        "qsofa": qsofa,
        "sepsis_alert": sirs["positive"] and qsofa["positive"],
        "summary": f"感染类型 — {top} (细菌{prob['bacterial']}% / 病毒{prob['viral']}% / 真菌{prob['fungal']}% / 非感染{prob['non_infectious']}%)",
        "disclaimer": "此为AI辅助决策, 须经感染科/检验科医师复核确认",
    }


def test_recommend(patient_id: str = "", current_labs: dict | None = None,
                   suspected_type: str = "bacterial", infection_site: str = "",
                   **kwargs: Any) -> dict:
    """检验项目推荐 — 基于当前信息缺口 + 疑似感染类型."""
    p, err = _get_patient({"patient_id": patient_id})
    current_labs = current_labs or {}
    recs = []
    tier1: list[str] = []  # 必查
    tier2: list[str] = []  # 建议
    tier3: list[str] = []  # 可选

    # Tier 1 — 所有疑似感染必查
    if "PCT" not in current_labs:
        tier1.append("降钙素原(PCT) — 细菌感染/脓毒症核心生物标志物")
    if "CRP" not in current_labs:
        tier1.append("C反应蛋白(CRP) — 炎症反应急性时相蛋白")
    if "WBC" not in current_labs:
        tier1.append("血常规+白细胞分类计数(WBC+Diff) — 基础炎症评估")

    # Tier 2 — 感染类型导向
    if suspected_type == "bacterial" and infection_site != "unknown":
        if "BloodCulture" not in current_labs:
            tier2.append("血培养×2套(需氧+厌氧) — 病原学诊断金标准")
        if infection_site == "respiratory":
            tier2.extend(["痰培养+革兰染色", "肺炎链球菌/军团菌尿抗原"])
        elif infection_site == "urinary":
            tier2.extend(["尿培养+菌落计数(>10^5 CFU/mL)", "尿常规+亚硝酸盐"])
        elif infection_site == "cns":
            tier2.extend(["脑脊液(CSF)常规+生化+培养", "CSF 革兰染色+细菌抗原"])

    if suspected_type == "viral":
        tier2.extend([
            "呼吸道病毒多重PCR/FilmArray Panel",
            "流感A/B + RSV 快速抗原",
            "EBV/CMV PCR (免疫抑制者)",
        ])

    if suspected_type == "fungal":
        tier2.extend([
            "G试验(1,3-beta-D-glucan) — 侵袭性真菌病筛查",
            "GM试验(半乳甘露聚糖) — 侵袭性曲霉病",
            "真菌培养+药敏 (血液/BALF/组织)",
        ])

    # Tier 3 — 补充评估
    if "IL6" not in current_labs:
        tier3.append("白细胞介素-6(IL-6) — 炎症因子风暴/COVID-19细胞因子释放")
    if "lactate" not in current_labs:
        tier3.append("血乳酸(Lactate) — 组织低灌注/sepsis严重度")
    if "proadrenomedullin" not in current_labs:
        tier3.append("pro-ADM — 脓毒症预后分层 (可选)")

    recs = tier1 + tier2 + tier3
    return {
        "status": "ok",
        "patient_id": patient_id,
        "recommended_tests": recs,
        "tier1_essential": tier1,
        "tier2_suggested": tier2,
        "tier3_optional": tier3,
        "summary": f"基于疑似{suspected_type}感染({infection_site or '未指定部位'}), 推荐 {len(recs)} 项检验 (T1必查{len(tier1)}项+T2建议{len(tier2)}项+T3可选{len(tier3)}项)",
        "disclaimer": "检验推荐基于临床指南, 须经主管医师审核确认",
    }


def antimicrobial_advice(patient_id: str = "", infection_type_val: str = "bacterial",
                         site: str = "unknown", mdro_risk: str = "low",
                         severity: str = "moderate",
                         creatinine: float = 1.0, age: int = 50,
                         weight_kg: float = 70.0, gender: str = "M",
                         **kwargs: Any) -> dict:
    """经验性抗感染建议 — 部位导向 + MDRO分层 + 肾功能调整."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        pass  # non-fatal, continue with defaults

    if infection_type_val != "bacterial":
        return {
            "status": "ok",
            "patient_id": patient_id,
            "infection_type": infection_type_val,
            "recommendations": ["非细菌感染 — 抗细菌抗生素非首选"],
            "summary": "非细菌感染 — 抗生素非首选, 需进一步明确病原体",
            "disclaimer": "此为AI辅助建议, 须经感染科/临床药师审核确认",
        }

    # CrCl for dosing
    crcl = round(((140 - age) * weight_kg) / (72 * max(creatinine, 0.5)) * (0.85 if gender.upper() == "F" else 1.0), 1)

    # Empiric regimen
    site_regimens = _SITE_EMPIRIC.get(site, _SITE_EMPIRIC.get("respiratory", {}))
    if severity == "severe" and "severe" in site_regimens:
        regimen = site_regimens["severe"]
        tier = "重症感染方案"
    elif mdro_risk == "high" or severity == "severe":
        regimen = site_regimens.get("hospital", site_regimens.get("community", ""))
        if mdro_risk == "high":
            regimen += " — MDRO高危, 建议升级覆盖"
        tier = "MDRO高危方案"
    else:
        regimen = site_regimens.get("community", site_regimens.get("hospital", ""))
        tier = "标准经验性方案"

    # Spectrum considerations
    spectrum = []
    if site == "respiratory":
        spectrum.append("覆盖肺炎链球菌 + 流感嗜血杆菌 + 非典型病原体(支原体/衣原体/军团菌)")
    elif site == "urinary":
        spectrum.append("覆盖大肠埃希菌 + 肺炎克雷伯菌 + 奇异变形杆菌 + 肠球菌")
    elif site == "intra_abdominal":
        spectrum.append("覆盖肠杆菌科(大肠/克雷伯) + 厌氧菌(脆弱拟杆菌) + 肠球菌")
    elif site == "bloodstream":
        spectrum.append("广谱覆盖: G+球菌(MSSA/MRSA) + G-杆菌(肠杆菌科/铜绿) + 厌氧菌")

    # De-escalation guidance
    de_escalation = [
        "48-72h后根据培养+药敏结果降阶梯",
        "血流动力学稳定+无发热>24h → 考虑窄谱抗生素",
        "治疗疗程: 一般感染5-7天, 复杂感染7-14天, 依临床反应个体化",
    ]

    return {
        "status": "ok",
        "patient_id": patient_id,
        "site": site,
        "severity": severity,
        "mdro_risk": mdro_risk,
        "crcl": crcl,
        "regimen_tier": tier,
        "empiric_regimen": regimen,
        "spectrum_coverage": spectrum,
        "de_escalation_plan": de_escalation,
        "mdro_warning": _MDRO_RISK_FACTORS.get("cre", "") if mdro_risk == "high" else "",
        "summary": f"经验性抗感染 — {site}/{severity}/MDRO:{mdro_risk} → {tier}",
        "disclaimer": "此为AI辅助决策支持, 具体方案须经感染科/临床药师审核确认, 禁止替代医师处方",
    }


def sepsis_screening(patient_id: str = "", vitals: dict | None = None,
                     **kwargs: Any) -> dict:
    """脓毒症筛查 — SIRS + qSOFA + 器官功能评估."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    vitals = vitals or {}
    labs = p.get("lab_results", {}) or {}
    lactate = float(labs.get("lactate", 1.5) or 1.5)
    pct = float(labs.get("PCT", 0.5) or 0.5)
    plt = float(labs.get("platelet", labs.get("PLT", 200)) or 200)

    sirs = _sirs_criteria(labs, vitals)
    qsofa = _qsofa(vitals)

    # Organ dysfunction indicators (Cr/TBil μmol/L → mg/dL 换算后比较)
    organ_flags = _organ_dysfunction_flags(labs)

    sepsis_likely = sirs["positive"] and qsofa["positive"]
    septic_shock = sepsis_likely and lactate > 2

    risk_level = "low"
    actions = []
    if septic_shock:
        risk_level = "critical"
        actions = [
            "立即启动脓毒性休克集束化治疗 (1h bundle)",
            "血培养+乳酸+血常规急查",
            "广谱抗生素 1h 内给予",
            "晶体液 30mL/kg 快速复苏 (SBP<65)",
            "血管活性药物 (去甲肾上腺素 首选)",
        ]
    elif sepsis_likely:
        risk_level = "high"
        actions = [
            "高度疑似脓毒症 — 启动3h bundle",
            "血培养×2套 + 乳酸 + PCT急查",
            "广谱抗生素 1h 内启动",
            "每小时尿量监测",
            "考虑ICU会诊",
        ]
    elif sirs["positive"]:
        risk_level = "medium"
        actions = [
            "SIRS阳性 — 排查感染源",
            "复查PCT+CRP+WBC",
            "必要时血培养",
            "密切监测qSOFA变化",
        ]
    else:
        actions = ["继续观察", "复查感染指标"]

    guides = _agent.search_guidelines("sepsis") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"脓毒症筛查 — {risk_level.upper()}风险 (SIRS:{sirs['positive']} qSOFA:{qsofa['positive']} Lac:{lactate})",
        patient=p, stage="S_B",
        findings=[
            f"SIRS: {sirs['met']}/4 阳性 — {sirs['interpretation']}",
            f"qSOFA: {qsofa['score']}/3 — {qsofa['interpretation']}",
            f"Lactate: {lactate} mmol/L {'(升高)' if lactate > 2 else '(正常)'}",
            f"PCT: {pct} ng/mL {'(显著升高)' if pct > 2 else ''}",
            f"器官功能: {', '.join(organ_flags) if organ_flags else '未见明显异常'}",
        ],
        recommendations=actions,
        alerts=["REACT: 疑似脓毒症" if sepsis_likely else None],
        guidelines=guides,
        guideline_refs=_GUIDELINES,
    )


def antibiogram(patient_id: str = "", pathogen: str = "",
                specimen: str = "blood", **kwargs: Any) -> dict:
    """微生物药敏大数据 — CLSI M100 导向的经验用药推荐."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        pass  # non-fatal

    pathogen_lower = pathogen.lower()
    recommendations = []
    resistance_note = ""

    if "e.coli" in pathogen_lower or "大肠" in pathogen:
        recommendations = [
            "ESBL阴性: 头孢曲松/头孢噻肟 或 哌拉西林/他唑巴坦",
            "ESBL阳性: 碳青霉烯类(美罗培南/亚胺培南) 或 头孢他啶/阿维巴坦",
            "复杂性UTI: 呋喃妥因 (仅限膀胱炎) 或 磷霉素氨丁三醇",
        ]
        resistance_note = "大肠埃希菌 ESBL产酶率 中国~45-55%, 氟喹诺酮耐药率>50%"
    elif "klebsiella" in pathogen_lower or "克雷伯" in pathogen:
        recommendations = [
            "ESBL阴性: 头孢曲松/头孢噻肟 或 哌拉西林/他唑巴坦",
            "ESBL阳性/CRE: 头孢他啶/阿维巴坦 或 多粘菌素 + 替加环素 或 头孢地尔 (KPC/NDM)",
        ]
        resistance_note = "肺炎克雷伯菌 CRE检出率逐年上升 (中国~10-20%), 碳青霉烯耐药应做酶型确认(KPC/NDM/OXA-48)"
    elif "pseudomonas" in pathogen_lower or "铜绿" in pathogen:
        recommendations = [
            "敏感菌: 哌拉西林/他唑巴坦 或 头孢吡肟 或 美罗培南",
            "MDR: 头孢他啶/阿维巴坦 + 氨曲南 或 头孢地尔",
            "常规联合治疗(重症): beta-内酰胺 + 氨基糖苷(阿米卡星)或氟喹诺酮(环丙沙星)",
        ]
        resistance_note = "铜绿假单胞菌 MDR率~20-30%, 避免单药治疗重症感染"
    elif "staph" in pathogen_lower or "葡萄球" in pathogen:
        recommendations = [
            "MSSA: 苯唑西林/氟氯西林 或 头孢唑林",
            "MRSA: 万古霉素 或 达托霉素 或 利奈唑胺",
            "MRSA菌血症: 万古霉素(MIC<=1) 或 达托霉素 6-10mg/kg qd",
        ]
        resistance_note = "金黄色葡萄球菌 MRSA检出率 ~30-40% (血液科/ICU更高)"
    elif "enterococcus" in pathogen_lower or "肠球菌" in pathogen:
        recommendations = [
            "粪肠球菌: 氨苄西林 ± 庆大霉素 (协同)",
            "屎肠球菌: 万古霉素 或 利奈唑胺 或 达托霉素",
            "VRE: 利奈唑胺 600mg q12h 或 达托霉素 8-12mg/kg qd",
        ]
        resistance_note = "屎肠球菌 氨苄西林耐药率>90%, VRE检出率逐年上升"
    else:
        recommendations = ["待药敏结果 — 继续经验性治疗", "建议送检 MALDI-TOF 快速病原鉴定 + 药敏"]
        resistance_note = ""

    return {
        "status": "ok",
        "pathogen": pathogen,
        "specimen": specimen,
        "recommendations": recommendations,
        "resistance_note": resistance_note,
        "guideline_ref": "CLSI M100 (2024) + EUCAST (2024) + 中国耐药监测网 (CARSS)",
        "summary": f"抗微生物药物敏感性指导 — {pathogen} ({specimen})",
        "disclaimer": "具体方案须依据药敏报告 + 感染科/药学部审核确认",
    }
