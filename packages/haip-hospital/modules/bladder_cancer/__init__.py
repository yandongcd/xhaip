"""Bladder Cancer v2.0 — MIBC/NMIBC分层 + TMT/RC决策 + 新辅助化疗 + BCG方案 + 术后监测.

Guidelines: EAU 2024, NCCN 2025, CUA 2024
"""
from __future__ import annotations

import math
from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="bladder-cancer", department="泌尿外科")
_GUIDELINES = [
    "EAU 2024 肌层浸润性膀胱癌指南",
    "NCCN 膀胱癌指南 (2025)",
    "CUA 中国泌尿外科疾病诊断治疗指南 (2024)",
    "EAU 2024 NMIBC 非肌层浸润性膀胱癌指南",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


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
    数据缺失/无法解析时返回 (None, note) — 不进入任何肾功能减量分支.
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


# ═══════ EAU NMIBC Risk Stratification ═══════

_NMIBC_RISK = {
    "low": {"criteria": "原发+单发+Ta G1(低级别)+<3cm+无CIS",
            "recurrence_1yr": "15%", "progression_5yr": "0.8%",
            "treatment": "TURBT单次术后即刻膀胱灌注化疗(丝裂霉素C 40mg)"},
    "intermediate": {"criteria": "不符合低危也不符合高危的所有",
                     "recurrence_1yr": "24-38%", "progression_5yr": "5-8%",
                     "treatment": "TURBT+诱导BCG膀胱灌注(每周1次×6周)+维持BCG(3周 q3月×1-3年)"},
    "high": {"criteria": "T1 G3(高级别)+CIS+多发+复发+>3cm",
             "recurrence_1yr": "61%", "progression_5yr": "17-45%",
             "treatment": "TURBT(2-6周后二次电切!)→ BCG诱导+维持(3年) 或 早期RC"},
    "very_high": {"criteria": "T1 G3+CIS+前列腺部尿道CIS+组织学变异(微乳头/浆细胞样/肉瘤样)+LVI+多发/大体积T1",
                  "recurrence_1yr": ">60%", "progression_5yr": ">50%",
                  "treatment": "强烈建议早期RC(根治性膀胱切除) 或 BCG诱导+维持+严格随访(膀胱镜 q3m)"},
}


# ═══════ TMT Eligibility Scoring ═══════

_TMT_CRITERIA = {
    "T_stage": {"T2": 0, "T3a": -10, "T3b": -20, "T4a": -40, "T4b": -100},
    "N_status": {"N0": 0, "N1": -30, "N2": -60, "N3": -100},
    "hydronephrosis": {"unilateral": -15, "bilateral": -30, "none": 0},
    "CIS_extensive": {"focal": -5, "extensive": -25, "none": 0},
    "tumor_size": {">5cm": -10, "3-5cm": -5, "<3cm": 0},
    "tumor_count": {">3": -10, "2-3": -5, "1": 0},
    "bladder_function": {"normal": 0, "reduced_capacity": -15, "incontinence": -25},
    "age": {">80": -10, "70-80": -5, "<70": 0},
    "comorbidity": {"severe": -15, "moderate": -5, "none": 0},
    "patient_preference": {"strong_spare": 10, "accept_rc": 5, "prefer_rc": -5},
}


def _tm_et_score(kwargs: dict) -> dict:
    """TMT eligibility: 0-100, >=70 eligible, 50-70 borderline, <50 RC preferred."""
    score = 100
    deductions = []

    t = kwargs.get("T_stage", "T2")
    score += _TMT_CRITERIA["T_stage"].get(t, 0)
    if _TMT_CRITERIA["T_stage"].get(t, 0) < -20:
        deductions.append(f"T分期{t} — 不适合保留膀胱(局部晚期)")

    n = kwargs.get("N_status", "N0")
    score += _TMT_CRITERIA["N_status"].get(n, 0)
    if n != "N0":
        deductions.append(f"淋巴结阳性({n}) — TMT相对禁忌")

    hydro = kwargs.get("hydronephrosis", "none")
    score += _TMT_CRITERIA["hydronephrosis"].get(hydro, 0)
    if hydro != "none":
        deductions.append(f"肾积水({hydro}) — 提示T3+局部进展")

    cis = kwargs.get("CIS_extensive", "none")
    score += _TMT_CRITERIA["CIS_extensive"].get(cis, 0)

    size = float(kwargs.get("tumor_size", 3) or 3)
    size_cat = ">5cm" if size > 5 else ("3-5cm" if size >= 3 else "<3cm")
    score += _TMT_CRITERIA["tumor_size"].get(size_cat, 0)

    count_cat = ">3" if kwargs.get("tumor_count", 1) > 3 else ("2-3" if kwargs.get("tumor_count", 1) >= 2 else "1")
    score += _TMT_CRITERIA["tumor_count"].get(count_cat, 0)

    bf = kwargs.get("bladder_function", "normal")
    score += _TMT_CRITERIA["bladder_function"].get(bf, 0)

    age = kwargs.get("age", 65)
    age_cat = ">80" if age > 80 else ("70-80" if age >= 70 else "<70")
    score += _TMT_CRITERIA["age"].get(age_cat, 0)

    score += _TMT_CRITERIA["comorbidity"].get(kwargs.get("comorbidity", "none"), 0)
    score += _TMT_CRITERIA["patient_preference"].get(kwargs.get("patient_preference", "accept_rc"), 0)

    eligible = score >= 70
    if eligible:
        rec = "TMT保膀胱治疗 — 符合EAU/NCCN适应证"
    elif score >= 50:
        rec = "临界 — MDT讨论: 倾向保留膀胱(严密随访) vs 根治术"
    else:
        rec = "根治性膀胱切除术(RC) + 盆腔淋巴结清扫 + 尿流改道"

    return {"score": max(0, score), "eligible": eligible, "recommendation": rec, "deductions": deductions}


# ═══════ Neoadjuvant Chemotherapy ═══════

def _neoadjuvant_eval(age: int, crcl: float | None, ecog: int, t_stage: str) -> dict:
    """Cisplatin eligibility for neoadjuvant chemotherapy."""
    cisplatin_eligible = True
    reasons = []
    if crcl is None:
        reasons.append("肾功能数据缺失 — 建议检测 CrCl 后确认顺铂资格")
    elif crcl < 60:
        cisplatin_eligible = False
        reasons.append(f"CrCl={crcl} <60 — 顺铂相对禁忌")
    if ecog >= 2:
        cisplatin_eligible = False
        reasons.append(f"ECOG={ecog} — 顺铂耐受性差")
    if age > 80:
        cisplatin_eligible = False
        reasons.append(f"年龄={age}>80 — 顺铂相对禁忌")

    if cisplatin_eligible:
        regimen = "ddMVAC (剂量密集甲氨蝶呤+长春碱+阿霉素+顺铂, q2w×3-4周期) 或 GC (吉西他滨+顺铂, q3w×4周期)"
        note = "新辅助化疗可改善OS 5-8% (MIBC T2-T4a)"
    else:
        regimen = "顺铂不合格 → 直接手术(无证据支持卡铂替代方案) 或 免疫治疗临床试验"
        note = "新辅助免疫(pembrolizumab/nivolumab)正在III期试验中"

    return {"cisplatin_eligible": cisplatin_eligible, "regimen": regimen, "note": note,
            "reasons": reasons, "crcl": crcl}


# ═══════ Handler Functions ═══════

def eligibility_score(patient_id: str = "", T_stage: str = "T2",
                      N_status: str = "N0", hydronephrosis: str = "none",
                      CIS_extensive: str = "none", tumor_size: float = 3.0,
                      tumor_count: int = 1, bladder_function: str = "normal",
                      age: int = 65, comorbidity: str = "none",
                      patient_preference: str = "accept_rc",
                      **kwargs: Any) -> dict:
    """保膀胱TMT适应证综合评分 — EAU 2024 10维评分."""
    p, err = _get_patient({"patient_id": patient_id})

    score_result = _tm_et_score({
        "T_stage": T_stage, "N_status": N_status, "hydronephrosis": hydronephrosis,
        "CIS_extensive": CIS_extensive, "tumor_size": tumor_size,
        "tumor_count": tumor_count, "bladder_function": bladder_function,
        "age": age, "comorbidity": comorbidity, "patient_preference": patient_preference,
    })

    # NMIBC risk if T stage is Ta/T1
    nmibc_info = {}
    if T_stage in ("Ta", "T1"):
        if T_stage == "T1" or CIS_extensive == "extensive":
            risk_cat = "very_high" if T_stage == "T1" and CIS_extensive == "extensive" else "high"
        elif tumor_count > 1 or tumor_size > 3:
            risk_cat = "intermediate"
        else:
            risk_cat = "low"
        nmibc_info = {"risk_group": risk_cat, **_NMIBC_RISK.get(risk_cat, {})}

    # Neoadjuvant for MIBC (CrCl 由 Cockcroft-Gault 真实计算, 肌酐 μmol/L→mg/dL)
    labs = (p.get("lab_results", {}) or {}) if p else {}
    crcl, crcl_note = _compute_crcl(p, labs)
    neoadj = _neoadjuvant_eval(age, crcl, kwargs.get("ecog", 0), T_stage) if T_stage in ("T2", "T3a", "T3b") else None

    return {
        "status": "ok", "patient_id": patient_id,
        "tmt_score": score_result["score"],
        "tmt_eligible": score_result["eligible"],
        "tmt_recommendation": score_result["recommendation"],
        "deductions": score_result["deductions"],
        "nmibc_risk": nmibc_info,
        "neoadjuvant": neoadj,
        "crcl": crcl,
        "renal_data_note": crcl_note,
        "summary": f"保膀胱评分 — {score_result['score']}/100 → {score_result['recommendation'][:40]}",
    }


def trimodal_comparison(patient_id: str = "", eligibility: dict | None = None,
                        age: int = 65, comorbidities: list | None = None,
                        **kwargs: Any) -> dict:
    """TMT vs RC 多维对比 — 生存率/并发症/QoL/费用/随访."""
    p, err = _get_patient({"patient_id": patient_id})
    eligibility = eligibility or {}
    score = eligibility.get("tmt_score", 50)

    comparison = {
        "TMT (三模态保留膀胱)": {
            "组成": "最大限度TURBT + 同步放化疗(顺铂+放疗60-66Gy) + 挽救性RC(复发时)",
            "5年OS": "50-70% (cT2), 30-50% (cT3)",
            "膀胱保留率": "70-80% (5年)",
            "并发症": "放射性膀胱炎(20-30%), 膀胱挛缩(10-15%), 性功能障碍(男30%)",
            "QoL": "较好 — 保留自然排尿, 无需尿流改道装置",
            "随访强度": "高 — 膀胱镜q3m×2年→q6m×3年→每年终身; CT q6-12m; 尿液细胞学",
            "费用": "初始费用较低, 但随访+挽救RC(30%→5年)增加长期费用",
            "适用": "cT2N0, 肿瘤<5cm, 单发, 无不全CIS, 膀胱功能好, 强烈保膀胱意愿",
        },
        "RC (根治性膀胱切除)": {
            "组成": "根治性膀胱切除+盆腔淋巴结清扫(标准/扩大)+尿流改道(回肠膀胱/原位新膀胱/输尿管皮肤造口)",
            "5年OS": "55-75% (cT2), 40-60% (cT3)",
            "膀胱保留率": "0% — 膀胱全部切除",
            "并发症": "肠梗阻(10-20%), 尿路感染(50%), 肾积水(15-30%), 性功能障碍(90%), 围术期死亡率1-3%",
            "QoL": "受影响 — 需终身尿流改道管理(造口袋/导管); 原位新膀胱可恢复部分控尿(66-85%夜间可控)",
            "随访强度": "中等 — CT q6-12m×5年; 电解质; 维生素B12(回肠); 尿道残端尿道镜",
            "费用": "初始费用高(手术+住院2-3周), 但长期随访简化",
            "适用": "cT3-4a, N+, 多灶, 广泛CIS, TMT后复发, 肾功能不全, 膀胱功能差",
        },
    }

    # Decision factors weighted for this patient
    factors = []
    if score >= 70:
        factors.append("TMT评分≥70 → 优先推荐保膀胱")
    if age > 75:
        factors.append("高龄>75 → RC耐受性需评估, 可能不适合新膀胱")
    if any(c in str(comorbidities).lower() for c in ["copd", "心衰", "心", "cirrhosis"]):
        factors.append("严重合并症 → RC围术期风险高, 倾向TMT")
    if kwargs.get("T_stage", "T2") in ("T3b", "T4a"):
        factors.append("局部晚期肿瘤 → 推荐RC (T3b-4a保膀胱复发率>50%)")

    return {
        "status": "ok", "patient_id": patient_id,
        "comparison": comparison,
        "decision_factors": factors,
        "summary": f"TMT vs RC比较 — {'倾向保膀胱' if score >= 70 else '倾向根治术' if score < 50 else '需MDT讨论'}",
    }


def guideline_reference(clinical_scenario: str = "mibc_t2_n0",
                        **kwargs: Any) -> dict:
    """指南依据查询 — EAU/NCCN/CUA 分层推荐."""
    scenarios = {
        "mibc_t2_n0": {"title": "cT2N0M0 MIBC",
                       "EAU 2024": "TMT保留膀胱为强烈推荐(证据级别1a) — 适用于单发<3cm, 无CIS, 无肾积水, 膀胱功能好的患者进行最大限度TURBT+同步放化疗",
                       "NCCN 2025": "保膀胱治疗(Grade 2B推荐)适用于cT2-T3a, 需在最大TURBT+化疗/放疗后进行严密膀胱镜随访",
                       "CUA 2024": "TMT保膀胱在中国为可选项(证据级别2a), 建议在经验丰富的大型医学中心进行"},
        "mibc_t3_n0": {"title": "cT3N0M0 MIBC",
                       "EAU 2024": "TMT在cT3患者中可考虑(证据级别2b), 但复发率高于cT2(5年38% vs 24%), 需密切随访",
                       "NCCN 2025": "TMT在cT3患者为选择性适应证, 需讨论治疗失败风险",
                       "CUA 2024": "cT3患者TMT为次要推荐, 需在严密MDT讨论下进行"},
        "nmibc_high": {"title": "高危NMIBC (T1 G3/CIS)",
                       "EAU 2024": "二次TURBT(2-6周后)必须! BCG诱导+维持3年",
                       "NCCN 2025": "BCG膀胱灌注(Grade 1推荐) — 诱导: 每周×6次, 维持: 3周 q3-6月×1-3年",
                       "CUA 2024": "高危NMIBC标准治疗: TURBT+BCG — 极高危(very high risk)建议早期RC"},
        "neoadjuvant": {"title": "新辅助化疗",
                        "EAU 2024": "顺铂为基础的新辅助化疗(NAC)为MIBC的1a级推荐 — ddMVAC或GC方案",
                        "NCCN 2025": "新辅助化疗(Grade 1)推荐所有cT2-T4a MIBC",
                        "CUA 2024": "新辅助化疗推荐顺铂合格(GC或ddMVAC)患者在手术前行3-4周期化疗"},
        "surveillance_tmt": {"title": "TMT术后随访",
                             "EAU 2024": "膀胱镜q3m×2年→q6m×3年→每年终身; 上尿路影像q12-24m; 尿液细胞学每次膀胱镜",
                             "NCCN 2025": "TMT后严密监测方案: 膀胱镜+尿液细胞学q3m×2年, q6m×3年, q12m终身",
                             "CUA 2024": "TMT后随访: 膀胱镜q3m×2年→q6m×3年→每年, CT/MRI q6-12m×5年"},
    }

    scenario = scenarios.get(clinical_scenario, scenarios["mibc_t2_n0"])
    return {
        "status": "ok", "clinical_scenario": clinical_scenario,
        "title": scenario["title"],
        "guidelines": {k: v for k, v in scenario.items() if k not in ("title",)},
        "summary": f"指南依据 — {scenario['title']}",
    }
