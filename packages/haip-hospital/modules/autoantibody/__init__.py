"""Autoantibody v2.0 — ANA IIF模式 + EULAR/ACR分类标准 + ANCA+APS + 趋势监控.

Guidelines: EULAR/ACR 2019 SLE, EULAR/ACR 2013 SSc, ACR/EULAR 2016 SS, ACR 2022 ANCA
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="autoantibody", department="检验医学科")
_GUIDELINES = [
    "EULAR/ACR 2019 系统性红斑狼疮(SLE)分类标准",
    "EULAR/ACR 2013 系统性硬化症(SSc)分类标准",
    "ACR/EULAR 2016 干燥综合征(SS)分类标准",
    "国际自身抗体检测共识 (2018)",
    "ACR 2022 ANCA相关性血管炎管理指南",
    "2006 修订Sapporo APS分类标准",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ ANA IIF Pattern Classification ═══════

_ANA_PATTERNS = {
    "speckled": {"name": "颗粒型 (Speckled)", "titer_clinical": "≥1:80 (IIF)",
                 "targets": ["SS-A/Ro", "SS-B/La", "Sm", "RNP", "Scl-70", "Jo-1", "RNA Pol III", "Ku", "Mi-2"],
                 "associated_disease": ["SLE", "干燥综合征(SS)", "系统性硬化症(SSc)", "MCTD", "PM/DM"]},
    "homogeneous": {"name": "均质型 (Homogeneous)", "titer_clinical": "≥1:80",
                    "targets": ["dsDNA", "核小体", "组蛋白"],
                    "associated_disease": ["SLE (活动期)", "药物性狼疮", "JIA"]},
    "nucleolar": {"name": "核仁型 (Nucleolar)", "titer_clinical": "≥1:80",
                  "targets": ["PM-Scl", "RNA Pol I/III", "fibrillarin (U3-RNP)", "Th/To"],
                  "associated_disease": ["SSc (弥漫型)", "PM/SSc 重叠综合征"]},
    "centromere": {"name": "着丝点型 (Centromere)", "titer_clinical": "≥1:80",
                   "targets": ["CENP-A/B/C"],
                   "associated_disease": ["SSc局限型 (CREST)", "原发性胆汁性胆管炎(PBC)"]},
    "cytoplasmic": {"name": "胞浆型 (Cytoplasmic)", "titer_clinical": "≥1:80",
                    "targets": ["Jo-1 (抗合成酶)", "SRP", "PL-7/PL-12", "EJ/OJ", "线粒体AMA-M2"],
                    "associated_disease": ["抗合成酶综合征", "PM/DM", "PBC (AMA-M2)"]},
    "nuclear_dots": {"name": "核点型 (Nuclear Dots)", "titer_clinical": "≥1:80",
                     "targets": ["Sp100", "PML"],
                     "associated_disease": ["PBC", "自身免疫性肝炎"]},
    "nuclear_membrane": {"name": "核膜型 (Nuclear Membrane)", "titer_clinical": "≥1:80",
                         "targets": ["gp210", "Lamin B"],
                         "associated_disease": ["PBC", "SLE"]},
}


# ═══════ Disease Classification Criteria ═══════

_DISEASE_PATTERNS = {
    "SLE": {
        "name": "系统性红斑狼疮",
        "criteria_ref": "EULAR/ACR 2019",
        "entry_criterion": "ANA≥1:80",
        "required_abs": ["ANA", "dsDNA", "Sm"],
        "supporting_abs": ["RNP", "SS-A", "SS-B", "Rib-P", "核小体", "组蛋白"],
        "clinical_criteria": ["颊部红斑", "盘状红斑", "光敏感", "口腔溃疡", "关节炎", "浆膜炎", "肾脏病变", "神经精神", "血液系统", "低补体(C3/C4)", "抗磷脂抗体+"],
        "scoring": {"anti-dsDNA": 6, "anti-Sm": 6, "抗磷脂抗体": 2, "C3/C4低": 3, "ANA≥1:80": 0},
    },
    "SSc": {
        "name": "系统性硬化症",
        "criteria_ref": "EULAR/ACR 2013",
        "required_abs": ["Scl-70", "RNA Pol III", "CENP"],
        "supporting_abs": ["PM-Scl", "Th/To", "U3-RNP"],
        "clinical_criteria": ["手指皮肤硬化(双)", "指尖溃疡", "毛细血管扩张", "间质性肺病(ILD)", "肺动脉高压(PAH)", "雷诺现象", "食管扩张"],
        "scoring": {"anti-Scl-70": 3, "anti-CENP": 2, "anti-RNA Pol III": 2, "手指硬化": 2, "ILD/PAH": 2},
    },
    "SS": {
        "name": "干燥综合征",
        "criteria_ref": "ACR/EULAR 2016",
        "required_abs": ["SS-A"],
        "supporting_abs": ["SS-B", "ANA"],
        "clinical_criteria": ["口干症状", "眼干症状", "Schirmer试验≤5mm", "角膜染色评分(OSS)≥5", "唇腺活检(灶性指数≥1)"],
        "scoring": {"anti-SS-A": 3, "唇腺活检≥1": 3, "OSS≥5": 1, "Schirmer≤5": 1},
    },
    "MCTD": {
        "name": "混合性结缔组织病",
        "criteria_ref": "Sharp/Kasukawa",
        "required_abs": ["RNP"],
        "supporting_abs": ["ANA"],
        "clinical_criteria": ["雷诺现象", "手指/手背肿胀", "关节炎", "肌炎", "ILD", "食管动力障碍"],
    },
    "PM_DM": {
        "name": "多发性肌炎/皮肌炎",
        "criteria_ref": "EULAR/ACR 2017",
        "required_abs": ["Jo-1"],
        "supporting_abs": ["Mi-2", "SRP", "MDA5", "TIF1-γ", "NXP2", "SAE", "PL-7", "PL-12", "EJ", "OJ"],
        "clinical_criteria": ["对称性近端肌无力", "肌酸激酶(CK)升高", "肌电图(EMG)肌源性损害", "皮肌炎皮疹(Gottron征/Heliotrope疹)", "ILD"],
        "scoring": {"anti-Jo-1": 5},
    },
    "RA": {
        "name": "类风湿关节炎",
        "criteria_ref": "ACR/EULAR 2010",
        "required_abs": ["CCP", "RF"],
        "supporting_abs": ["AKA", "APF", "anti-CCP IgG/IgA"],
        "clinical_criteria": ["≥1个关节肿胀", "RF/CCP高滴度", "CRP/ESR升高", "症状持续≥6周"],
        "scoring": {"CCP>3xULN": 3, "RF>3xULN": 3, "CRP/ESR异常": 1, "≥10个关节": 5, "症状≥6周": 1},
    },
    "ANCA_Vasculitis": {
        "name": "ANCA相关性血管炎",
        "criteria_ref": "ACR 2022",
        "required_abs": ["MPO", "PR3"],
        "supporting_abs": ["ANA"],
        "clinical_criteria": ["肾脏(新月体肾炎/血尿/蛋白尿)", "肺部(结节/空洞/肺泡出血)", "ENT(鼻窦炎/鼻出血/中耳炎)", "周围神经病变", "紫癜/皮肤溃疡"],
        "scoring": {"PR3/c-ANCA": 3, "MPO/p-ANCA": 2, "肾活检新月体": 3, "肺泡出血": 3},
    },
    "APS": {
        "name": "抗磷脂综合征",
        "criteria_ref": "2006 Sapporo修订",
        "required_abs": ["Lupus Anticoagulant", "anti-Cardiolipin", "anti-β2GPI"],
        "supporting_abs": [],
        "clinical_criteria": ["血栓事件(动脉/静脉/小血管)", "病态妊娠(≥3次连续流产/≥1次晚期胎儿死亡/重度子痫前期)"],
        "scoring": {"LA阳性": 2, "anti-CL IgG>40": 2, "anti-β2GPI IgG>40": 2, "血栓事件": 3, "病态妊娠": 2},
    },
}


# ═══════ ANCA interpretation ═══════

def _anca_interpretation(pr3: float, mpo: float, c_anca: str, p_anca: str) -> dict:
    """ANCA 综合分析 — PR3/c-ANCA vs MPO/p-ANCA + 器官指向."""

    pattern = ""
    disease = ""
    organs = []

    if pr3 > 20 or c_anca.lower() == "positive":
        pattern = "c-ANCA/PR3-ANCA"
        disease = "肉芽肿性多血管炎(GPA/Wegener) — PR3阳性"
        organs = ["ENT: 鼻窦炎/鼻出血/鞍鼻", "肺: 结节/空洞/肺泡出血", "肾: 坏死性新月体肾炎(Pauci-immune)", "眼: 巩膜炎/眼眶假瘤"]
    elif mpo > 20 or p_anca.lower() == "positive":
        pattern = "p-ANCA/MPO-ANCA"
        if any(kw in str(organs) for kw in ["肾", "renal", "Cr"]):
            disease = "显微镜下多血管炎(MPA) — MPO阳性+急进性肾小球肾炎"
            organs = ["肾: 急进性肾炎(RPGN) 90%+", "肺: 肺泡出血/ILD", "皮肤: 紫癜", "神经: 多发性单神经炎"]
        else:
            disease = "嗜酸性肉芽肿性多血管炎(EGPA/Churg-Strauss) — MPO阳性+哮喘+EOS增高"
            organs = ["ENT: 鼻息肉/鼻窦炎", "肺: 哮喘/游走性浸润", "心: 心肌炎/心包炎", "外周血: 嗜酸性粒细胞>10%"]
    else:
        pattern = "ANCA阴性"
        disease = "ANCA阴性不能排除血管炎 — 约10-20% MPA/GPA为ANCA阴性, 肾活检是金标准"

    return {
        "pattern": pattern, "disease_orientation": disease,
        "organ_involvement": organs,
        "next_step": "肾活检(免疫荧光: Pauci-immune新月体肾炎) + 胸部HRCT + ENT评估" if pr3 > 20 or mpo > 20 else "临床随访+肾活检",
    }


# ═══════ Handler Functions ═══════


def pattern_match(patient_id: str = "", antibodies: dict | None = None,
                  ana_pattern: str = "", ana_titer: str = "1:80",
                  **kwargs: Any) -> dict:
    """抗体组合模式匹配 — 8种风湿病+ANA IIF模式+分类标准打分."""
    p, err = _get_patient({"patient_id": patient_id})
    antibodies = antibodies or {}

    positives = [k for k, v in antibodies.items() if v]
    positives_lower = [p.lower() for p in positives]

    # ANA IIF pattern
    ana_info = _ANA_PATTERNS.get(ana_pattern.lower(), {})
    if not ana_info and ana_pattern:
        ana_info = {"name": ana_pattern, "note": "非标准AC-ICAP命名, 建议对照ICAP国际共识命名"}

    # Disease pattern matching with scoring
    matches = []
    for disease_code, pattern_info in _DISEASE_PATTERNS.items():
        req = pattern_info.get("required_abs", [])
        sup = pattern_info.get("supporting_abs", [])

        req_matched = sum(1 for r in req if r.lower() in positives_lower or r in positives)
        sup_matched = sum(1 for s in sup if s.lower() in positives_lower)

        if req_matched >= 1:
            confidence = "高" if req_matched >= len(req) else ("中" if sup_matched >= 2 else "低")
            criteria = pattern_info.get("clinical_criteria", [])
            # Count how many clinical criteria might be present
            clinical_hints = [c for c in criteria if
                            any(kw in str(kwargs.get("symptoms", "")).lower() for kw in [c[:4], c[-4:]])]

            matches.append({
                "disease": f"{pattern_info['name']} ({disease_code})",
                "disease_code": disease_code,
                "criteria_ref": pattern_info.get("criteria_ref", ""),
                "confidence": confidence,
                "required_abs_matched": req_matched,
                "total_required": len(req),
                "supporting_abs_matched": sup_matched,
                "supporting_abs": sup,
                "clinical_criteria_hints": clinical_hints[:5],
                "diagnostic_workup": _get_workup(disease_code),
            })

    return {
        "status": "ok",
        "patient_id": patient_id,
        "positive_antibodies": positives,
        "ana_pattern": ana_info,
        "ana_titer": ana_titer,
        "disease_matches": matches,
        "total_matches": len(matches),
        "summary": f"自身抗体 — {len(positives)}项阳性 | ANA={ana_pattern or '未检测'}({ana_titer}) | {len(matches)}个疾病模式匹配",
        "recommendation": ("风湿免疫科会诊" if any(m["confidence"] == "高" for m in matches) else
                          "建议补充ENA/ANCA/补体检测 + 风湿免疫科随访"),
    }


def _get_workup(disease_code: str) -> list[str]:
    """疾病特异性检查建议."""
    workups = {
        "SLE": ["补体 C3/C4", "抗dsDNA (ELISA/Farr)", "尿蛋白/尿沉渣", "CBC+贫血评估", "抗磷脂抗体 (LA/aCL/anti-β2GPI)"],
        "SSc": ["甲襞毛细血管镜", "HRCT 胸部 (ILD筛查)", "超声心动图 (PAH筛查)", "食管测压", "RNA Pol III抗体"],
        "SS": ["Schirmer试验", "角膜染色(OSS)", "唇腺活检 (灶性指数)", "唾液腺超声/ECT", "抗SS-A(ELISA定量)"],
        "MCTD": ["HRCT (ILD)", "食管测压", "心脏超声 (心包炎/PAH)", "RNP滴度定量"],
        "PM_DM": ["CK/AST/ALT/LDH", "肌电图(EMG)", "肌肉MRI/活检", "HRCT (ILD)", "肿瘤筛查(年龄>40)"],
        "RA": ["CCP IgG/IgA定量", "RF IgM/IgA定量", "ESR/CRP", "关节X线/超声/MRI", "DAS28-CRP 活动度评分"],
        "ANCA_Vasculitis": ["肾活检(免疫荧光+光镜)", "胸部HRCT", "支气管肺泡灌洗(BAL)", "MPO/PR3 ELISA定量", "尿沉渣+24h尿蛋白"],
        "APS": ["狼疮抗凝物(LA)", "anti-Cardiolipin IgG/IgM", "anti-β2GPI IgG/IgM", "重复检测12周后(确诊须持续阳性)"],
    }
    return workups.get(disease_code, ["风湿免疫科会诊"])


def trend_track(patient_id: str = "", current_results: dict | None = None,
                historical_results: list | None = None,
                **kwargs: Any) -> dict:
    """抗体动态趋势追踪 — 滴度4倍变化+新抗体出现+疾病活动度关联."""
    p, err = _get_patient({"patient_id": patient_id})
    current_results = current_results or {}
    historical_results = historical_results or []

    if not historical_results:
        return {"status": "ok", "patient_id": patient_id, "changes": [],
                "summary": "无历史数据, 无法追踪趋势 — 建议3-6月后复查建立基线"}

    last = historical_results[-1] if historical_results else {}
    changes = []
    significant = False
    new_abs = []

    for k, v in current_results.items():
        if k not in last:
            if v:  # New antibody detected
                new_abs.append(k)
                changes.append(f"新抗体: {k} — 首次检出, 建议确认试验(ELISA/LIA)")
                significant = True
            continue

        if isinstance(v, (int, float)) and isinstance(last.get(k), (int, float)):
            old_val = float(last[k] or 0.01)
            if old_val > 0 and v / old_val >= 4:
                changes.append(f"{k}: {old_val:.0f}→{v:.0f} (升高≥4倍 — 临床显著活动!)")
                significant = True
            elif old_val > 0 and v / old_val >= 2:
                changes.append(f"{k}: {old_val:.0f}→{v:.0f} (升高2-4倍 — 需关注)")
            elif v / old_val <= 0.5 and v > 0:
                changes.append(f"{k}: {old_val:.0f}→{v:.0f} (下降>50% — 治疗有效? )")

    # Clinical correlation
    alerts = []
    if any("dsDNA" in c for c in changes) and any("升高" in c for c in changes):
        alerts.append("抗dsDNA 滴度显著升高 — 与SLE疾病活动度相关, 需评估补体C3/C4+尿蛋白+临床活动度(SLEDAI)")
    if any("MPO" in c or "PR3" in c for c in changes) and any("升高" in c for c in changes):
        alerts.append("ANCA滴度显著升高 — 与ANCA血管炎复发相关, 需密切监测肾/肺/ENT")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "significant_changes": changes,
        "new_antibodies": new_abs,
        "clinically_significant": significant,
        "comparison_points": len(historical_results),
        "alerts": alerts,
        "recommendation": ("建议风湿免疫科随访 — 抗体滴度显著变化" if significant else
                          "抗体稳定 — 继续定期监测"),
        "summary": f"趋势追踪 — {len(changes)}项变化 | {'有临床显著变化!' if significant else '稳定'}",
    }


def disease_orientation(patient_id: str = "", antibody_pattern: dict | None = None,
                        symptoms: list | None = None,
                        pr3: float = 0.0, mpo: float = 0.0,
                        c_anca: str = "", p_anca: str = "",
                        acr_criteria_count: int = 0,
                        **kwargs: Any) -> dict:
    """疾病指向性评估 — 整合抗体谱+临床表现+ANCA+分类标准."""
    p, err = _get_patient({"patient_id": patient_id})
    antibody_pattern = antibody_pattern or {}
    symptoms = symptoms or []

    matches = antibody_pattern.get("disease_matches", [])
    if not matches:
        return {
            "status": "ok",
            "patient_id": patient_id,
            "primary": "",
            "confidence": "无匹配",
            "differential": [],
            "recommendation": "无明确抗体模式 — 建议补充: 抗CCP/RF(RA筛查)+ANCA(血管炎)+抗dsDNA定量",
            "summary": "无明确疾病指向",
        }

    # Sort by confidence (high > medium > low)
    priority_map = {"高": 3, "中": 2, "低": 1}
    matches_sorted = sorted(matches, key=lambda m: priority_map.get(m["confidence"], 0), reverse=True)
    primary = matches_sorted[0]

    # ANCA interpretation if relevant
    anca_info = {}
    if "ANCA" in primary.get("disease_code", "") or "血管炎" in primary.get("disease", ""):
        anca_info = _anca_interpretation(pr3, mpo, c_anca, p_anca)

    # Build differential
    differential = [{
        "disease": m["disease"],
        "confidence": m["confidence"],
        "key_test": m.get("diagnostic_workup", [""])[0] if m.get("diagnostic_workup") else "",
    } for m in matches_sorted[:4]]

    # Clinical criteria match
    primary_disease = _DISEASE_PATTERNS.get(primary.get("disease_code", ""), {})
    clinical_clues = [c for c in primary_disease.get("clinical_criteria", [])
                     if any(s.lower()[:4] in c.lower() or c.lower()[:4] in s.lower() for s in symptoms)]

    return {
        "status": "ok",
        "patient_id": patient_id,
        "primary_disease": primary["disease"] if primary else "",
        "confidence": primary["confidence"] if primary else "",
        "criteria_ref": primary_data.get("criteria_ref", "") if (primary_data := _DISEASE_PATTERNS.get(primary.get("disease_code", ""), {})) else "",
        "matched_clinical_clues": clinical_clues[:5],
        "differential_diagnoses": differential,
        "anca_interpretation": anca_info if anca_info else None,
        "workup": primary.get("diagnostic_workup", []) if primary else [],
        "recommendation": (f"高度指向 {primary['disease']} — 建议风湿免疫科/肾内科紧急会诊" if primary and primary["confidence"] == "高"
                          else f"中概率 {primary['disease']} — 建议补充检查+风湿科门诊"),
        "summary": f"疾病指向 — {primary['disease']} ({primary['confidence']}置信度)" if primary else "待进一步评估",
    }
