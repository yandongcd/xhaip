"""aHUS Detective v2.0 — TMA三联征 + PLASMIC评分 + 补体通路鉴别 + 治疗决策 + 遗传风险.

Guidelines: KDIGO 2024, aHUS专家共识(2025), ASH/ISTH, ERKNet
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="ahus-detective", department="肾内科")
_GUIDELINES = [
    "KDIGO 2024 肾小球疾病临床实践指南",
    "aHUS多学科诊疗实践专家共识 (2025)",
    "ASH/ISTH 血栓性微血管病(TMA)诊疗指南 (2023)",
    "ERKNet 欧洲罕见肾病参考网络 aHUS诊断路径",
    "依库珠单抗(Eculizumab)临床应用中国专家共识",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ PLASMIC Score (TTP prediction) ═══════

def _plasmic_score(plt: float, cr: float, inr: float, mcv: float,
                   has_cancer: bool, has_transplant: bool) -> dict:
    """PLASMIC评分 — 预测ADAMTS13严重缺乏 (<10%) 的可能性."""
    score = 0
    criteria = []

    if plt < 30:
        score += 1
        criteria.append("PLT<30")
    if cr < 177:
        score += 1
        criteria.append("Cr<177 (无严重AKI)")
    if inr < 1.5:
        score += 1
        criteria.append("INR<1.5")
    if mcv < 90:
        score += 1
        criteria.append("MCV<90")

    if not has_cancer:
        score += 1
        criteria.append("无活动性恶性肿瘤")
    if not has_transplant:
        score += 1
        criteria.append("无移植史")
    # Note: PLASMIC has 7 criteria total

    if score >= 6:
        probability = "高危 (72% ADAMTS13缺乏)"
        action = "立即送检ADAMTS13活性, 考虑经验性血浆置换"
    elif score >= 5:
        probability = "中高危 (10-30%)"
        action = "送检ADAMTS13, 准备血浆置换"
    else:
        probability = "低危 (<5% ADAMTS13缺乏)"
        action = "aHUS/TMA其他病因可能性大, 完善补体检查"

    return {"score": score, "probability": probability, "action": action, "criteria": criteria}


# ═══════ Complement Pathway Assessment ═══════

def _complement_assessment(c3: float, c4: float, sc5b9: float,
                           factor_h: float, factor_i: float,
                           anti_cfh: float, ch50: float) -> dict:
    """补体通路综合评估 — 经典/旁路/终末通路鉴别."""

    patterns = []

    # Pattern 1: Classic pathway activation (low C4 too)
    if c3 < 0.7 and c4 < 0.15:
        patterns.append({
            "pattern": "经典/凝集素途径激活",
            "suggested_dx": ["系统性红斑狼疮(SLE)", "冷球蛋白血症", "C1q肾病"],
            "next_step": "ANA/anti-dsDNA/C1q/C3Nef检测",
        })

    # Pattern 2: Alternative pathway activation (normal C4)
    if c3 < 0.7 and c4 >= 0.15:
        patterns.append({
            "pattern": "旁路途径异常激活",
            "suggested_dx": ["aHUS (CFH/CFI/MCP/CD46突变)", "C3肾小球病(C3G)", "致密物沉积病(DDD)"],
            "next_step": "补体基因Panel(CFH/CFI/MCP/CD46/C3/CFB/THBD/DGKE) + 抗CFH抗体 + C3Nef",
        })

    # Pattern 3: Terminal pathway activation
    if sc5b9 > 300:
        patterns.append({
            "pattern": "终末补体途径过度激活",
            "suggested_dx": ["aHUS活动期", "灾难性抗磷脂综合征(CAPS)", "HELLP综合征"],
            "next_step": "sC5b-9动态监测 + 依库珠单抗评估",
        })

    # Pattern 4: Anti-CFH antibody
    if anti_cfh > 1000:
        patterns.append({
            "pattern": "抗CFH抗体阳性aHUS",
            "suggested_dx": ["抗CFH抗体相关aHUS (占aHUS 5-10%)"],
            "next_step": "免疫抑制治疗(糖皮质激素+环磷酰胺/利妥昔单抗) + 血浆置换",
        })

    # Pattern 5: Low CH50
    if ch50 < 30:
        patterns.append({
            "pattern": "CH50总补体活性降低",
            "suggested_dx": ["补体经典途径缺陷", "补体消耗性疾病(SLE/冷球蛋白)"],
            "next_step": "AP50 (旁路途径溶血活性) 区分",
        })

    if not patterns:
        patterns = [{"pattern": "补体指标未见明显异常", "suggested_dx": ["继续观察或非补体介导TMA"],
                     "next_step": "复查补体(48-72h), 完善ADAMTS13+STEC"}]

    return {
        "c3": c3, "c4": c4, "sc5b9": sc5b9,
        "patterns": patterns,
        "summary_complement": f"C3={c3} / C4={c4} / sC5b-9={sc5b9} → {patterns[0]['pattern']}",
    }


# ═══════ Acute Kidney Injury Staging ═══════

def _aki_stage(cr_baseline: float, cr_current: float, urine_output: float) -> dict:
    """KDIGO AKI分期 (基于肌酐+尿量)."""
    cr_ratio = cr_current / max(cr_baseline, 0.5)

    if cr_ratio >= 3 or cr_current >= 354 or urine_output < 0.3:
        return {"stage": "AKI 3期", "severity": "severe",
                "action": "紧急肾脏替代治疗(RRT)评估 | ICU会诊",
                "cr_ratio": round(cr_ratio, 1)}
    elif cr_ratio >= 2:
        return {"stage": "AKI 2期", "severity": "moderate",
                "action": "严格液体管理 | 肾脏超声 | 肾内科急会诊",
                "cr_ratio": round(cr_ratio, 1)}
    elif cr_ratio >= 1.5 or cr_current - cr_baseline >= 26.5:
        return {"stage": "AKI 1期", "severity": "mild",
                "action": "停用肾毒性药物 | 优化容量 | 48h复查Cr",
                "cr_ratio": round(cr_ratio, 1)}
    return {"stage": "无AKI", "severity": "none", "action": "常规监测", "cr_ratio": round(cr_ratio, 1)}


# ═══════ Genetic Risk Panel ═══════

_GENETIC_RISK = {
    "CFH": {"risk": "高危", "relapse": "50-70%", "renal_survival": "30-50% (5年)",
            "note": "CFH突变是aHUS最常见致病突变, 肾脏预后差, 复发率高, 肾移植后复发风险~80%"},
    "CFI": {"risk": "高危", "relapse": "30-40%", "renal_survival": "40-60% (5年)",
            "note": "CFI突变导致因子I功能缺陷, 补体调控能力下降"},
    "MCP": {"risk": "中危", "relapse": "20-30%", "renal_survival": "70-90% (5年)",
            "note": "MCP/CD46突变预后相对较好(膜结合蛋白, 肾移植复发低)"},
    "C3": {"risk": "高危", "relapse": "40-50%", "renal_survival": "40-50% (5年)",
           "note": "C3突变导致补体过度激活抵抗调控"},
    "CFB": {"risk": "高危", "relapse": "30-40%", "renal_survival": "50-60% (5年)",
            "note": "CFB功能获得性突变, 补体旁路过度激活"},
    "THBD": {"risk": "中危", "relapse": "20-30%", "renal_survival": "60-80% (5年)",
             "note": "血栓调节蛋白(THBD)突变, 内皮保护功能受损"},
    "DGKE": {"risk": "中危", "relapse": "10-20%", "renal_survival": "70-90% (5年)",
             "note": "DGKE突变致非补体介导TMA(婴幼儿为主), 依库珠单抗无效"},
    "CFHR1-3_del": {"risk": "高危", "relapse": "40-60%", "renal_survival": "40-50% (5年)",
                    "note": "CFHR1-3缺失+抗CFH抗体 — 自身免疫型aHUS"},
}


# ═══════ Handler Functions ═══════


def tma_triad(patient_id: str = "", **kwargs: Any) -> dict:
    """TMA三联征筛查 — PLT<150 + MAHA(贫血+LDH) + AKI + PLASMIC评分."""
    p, err = _get_patient({"patient_id": patient_id})
    if err:
        return err

    labs = p.get("lab_results", {}) or {}
    plt = float(labs.get("platelet", 150) or 150)
    hb = float(labs.get("hb", 140) or 140)
    ldh = float(labs.get("LDH", 200) or 200)
    cr = float(labs.get("creatinine", 80) or 80)
    cr_baseline = float(labs.get("creatinine_baseline", 70) or 70)
    inr = float(labs.get("INR", 1.0) or 1.0)
    mcv = float(labs.get("MCV", 88) or 88)
    haptoglobin = float(labs.get("haptoglobin", 1.0) or 1.0)
    schistocytes = str(labs.get("schistocytes", "") or "")

    dx = p.get("diagnosis", "")
    has_cancer = any(kw in dx for kw in ["癌", "肿瘤", "malignant"])
    has_transplant = any(kw in dx for kw in ["移植", "transplant"])

    # TMA triad
    thrombocytopenia = plt < 150
    maha = hb < 120 and ldh > 250 and (
        haptoglobin < 0.3 or "positive" in schistocytes.lower() or "阳性" in schistocytes)
    aki = cr > 100 or (cr - cr_baseline) > 26.5

    tma = thrombocytopenia and maha and aki
    aki_info = _aki_stage(cr_baseline, cr, 1.0)
    plasmic = _plasmic_score(plt, cr, inr, mcv, has_cancer, has_transplant)

    return {
        "status": "ok",
        "patient_id": patient_id,
        "tma_suspected": tma,
        "tma_triad": {"thrombocytopenia": thrombocytopenia, "MAHA": maha, "AKI": aki},
        "platelet": plt, "hb": hb, "LDH": ldh,
        "creatinine": cr, "cr_baseline": cr_baseline,
        "haptoglobin": haptoglobin, "schistocytes": schistocytes,
        "aki_staging": aki_info,
        "plasmic_score": plasmic,
        "summary": f"TMA三联征 — {'疑似TMA!' if tma else '不符合'} | PLASMIC={plasmic['score']}/7 | AKI{aki_info['stage']}",
        "next_step": ("急查外周血涂片(破碎红细胞>1%) + ADAMTS13活性 + STEC PCR + 补体C3/C4 + sC5b-9"
                      if tma else "常规随访, 监测PLT/Hb/Cr趋势"),
    }


def differential_diagnosis(patient_id: str = "", adamts13: float = 50.0,
                           stec_test: str = "negative",
                           complement_panel: dict | None = None,
                           clinical_context: str = "",
                           **kwargs: Any) -> dict:
    """排除诊断 — TTP vs STEC-HUS vs aHUS vs 继发性TMA."""
    p, err = _get_patient({"patient_id": patient_id})
    complement_panel = complement_panel or {}

    c3 = float(complement_panel.get("C3", 1.0) or 1.0)
    c4 = float(complement_panel.get("C4", 0.2) or 0.2)
    sc5b9 = float(complement_panel.get("sC5b9", 200) or 200)
    anti_cfh = float(complement_panel.get("anti_CFH", 0) or 0)
    factor_h = float(complement_panel.get("factor_H", 100) or 100)
    factor_i = float(complement_panel.get("factor_I", 100) or 100)
    ch50 = float(complement_panel.get("CH50", 50) or 50)

    dx_list = []
    dx_action = ""
    urgency = "routine"

    # Step 1: TTP
    if adamts13 < 10:
        dx_list.append({"diagnosis": "TTP (血栓性血小板减少性紫癜)",
                       "confidence": "高 (ADAMTS13<10%)",
                       "treatment": "血浆置换 qd + 利妥昔单抗 + 卡普赛珠单抗(vWF抑制剂)",
                       "note": "血浆置换需每日进行直至PLT恢复+ADAMTS13>20%"})
        dx_action = "立即血浆置换 (TTP是医疗紧急情况!)"
        urgency = "emergent"

    # Step 2: STEC-HUS
    elif stec_test.lower() in ("positive", "阳性"):
        dx_list.append({"diagnosis": "STEC-HUS (产志贺毒素大肠杆菌HUS)",
                       "confidence": "高 (STEC阳性)",
                       "treatment": "支持治疗(液体+电解质) + 必要时RRT | 禁用抗生素! (增加毒素释放风险)",
                       "note": "前驱腹泻史, 多为自限性, 预后较好"})
        dx_action = "支持治疗 + 每日监测Cr/PLT/Hb"
        urgency = "urgent"

    # Step 3: aHUS (complement-mediated)
    elif c3 < 0.7 and c4 >= 0.15:
        dx_list.append({"diagnosis": "aHUS (非典型溶血尿毒综合征) — 补体旁路途径异常",
                       "confidence": "高 (C3低+C4正常+排除TTP/STEC)",
                       "treatment": "依库珠单抗(Eculizumab) 900mg IV qw×4次→1200mg q2w",
                       "note": "抗C5单抗, 需脑膜炎球菌疫苗(接种后≥2周) | 可同时血浆置换过渡"})
        dx_action = "立即依库珠单抗 ± 血浆置换过渡 | 脑膜炎球菌疫苗"
        urgency = "emergent"

    elif sc5b9 > 350:
        dx_list.append({"diagnosis": "aHUS (终末补体途径激活)",
                       "confidence": "中等 (sC5b-9升高+C3正常)", "treatment": "依库珠单抗评估",
                       "note": "sC5b-9>350提示补体终末途径过度激活"})
        dx_action = "动态监测sC5b-9+临床, 补体基因检测"
        urgency = "urgent"

    # Step 4: Secondary TMA
    else:
        secondary_causes = []
        if "SLE" in clinical_context or "狼疮" in clinical_context:
            secondary_causes.append("系统性红斑狼疮(SLE)")
        if "恶性" in clinical_context or "hypertensive" in clinical_context.lower():
            secondary_causes.append("恶性高血压")
        if "药物" in clinical_context:
            secondary_causes.append("药物诱导TMA (钙调磷酸酶抑制剂/奎宁/吉西他滨/丝裂霉素C)")

        if secondary_causes:
            dx_list.append({"diagnosis": f"继发性TMA — {', '.join(secondary_causes)}",
                           "confidence": "中等", "treatment": "治疗原发病 + 支持治疗",
                           "note": "控制原发病后TMA可缓解, 通常不需要依库珠单抗"})
            dx_action = f"治疗原发病: {', '.join(secondary_causes)}"
            urgency = "urgent"
        else:
            dx_list.append({"diagnosis": "TMA — 病因待进一步评估",
                           "confidence": "不确定", "treatment": "补体基因Panel + 抗CFH抗体 + C3Nef + ADAMTS13(若未做)",
                           "note": "需排除罕见病因: 维生素B12缺乏/钴胺素C缺乏(MMACHC突变)"})
            dx_action = "完善基因检测+补体全套+排除罕见病因"
            urgency = "urgent"

    # Complement assessment
    compl_assess = _complement_assessment(c3, c4, sc5b9, factor_h, factor_i, anti_cfh, ch50)

    return {
        "status": "ok",
        "patient_id": patient_id,
        "differential_list": dx_list,
        "primary_action": dx_action,
        "urgency": urgency,
        "complement_assessment": compl_assess,
        "key_labs": {"ADAMTS13": f"{adamts13}%", "STEC": stec_test,
                     "C3": c3, "C4": c4, "sC5b9": sc5b9},
        "summary": f"排除诊断 — {dx_list[0]['diagnosis']} | 紧急度={urgency}",
    }


def risk_stratify(patient_id: str = "", genetic_results: dict | None = None,
                  sc5b9: float = 200.0, anti_cfh: float = 0.0,
                  age_at_onset: int = 30, renal_biopsy: str = "",
                  **kwargs: Any) -> dict:
    """遗传风险分层 + 依库珠单抗治疗决策 + 肾移植风险评估."""
    p, err = _get_patient({"patient_id": patient_id})
    genetic_results = genetic_results or {}

    genetic_risks = []
    overall_risk = "中危"
    relapse_risk = "中度"
    renal_prognosis = "中等"

    for gene, info in _GENETIC_RISK.items():
        if genetic_results.get(gene):
            genetic_risks.append({**info, "gene": gene})
            if info["risk"] == "高危":
                overall_risk = "高危"
                relapse_risk = "高危"
                renal_prognosis = "差"

    # Anti-CFH antibody risk
    if anti_cfh > 1000:
        overall_risk = "高危"
        genetic_risks.append({"gene": "anti-CFH_Ab", "risk": "高危",
                              "relapse": "40-60%",
                              "renal_survival": "40-50% (5年)",
                              "note": "抗CFH抗体相关自身免疫型aHUS — 免疫抑制+血浆置换"})

    # Treatment decision
    eculizumab_indicated = False
    eculizumab_reason = ""

    if overall_risk == "高危":
        eculizumab_indicated = True
        eculizumab_reason = "高危基因型 — 依库珠单抗强烈推荐 (预防复发/保护移植肾)"
    elif sc5b9 > 350:
        eculizumab_indicated = True
        eculizumab_reason = "补体终末途径过度激活 — 依库珠单抗适应证"
    elif renal_biopsy and "TMA" in renal_biopsy.upper():
        eculizumab_indicated = True
        eculizumab_reason = "肾活检证实活动性TMA — 依库珠单抗治疗指征"

    # Transplant risk
    transplant_risk = "未评估"
    transplant_advice = ""
    if "CFH" in str(genetic_results) or "C3" in str(genetic_results) or "CFB" in str(genetic_results):
        transplant_risk = "高危 — 移植肾复发风险60-80%"
        transplant_advice = "推荐依库珠单抗预防 + 活体供肾慎用 (CFH突变者不建议亲属供肾)"
    elif "MCP" in str(genetic_results):
        transplant_risk = "低危 — MCP/CD46为膜蛋白, 移植肾不复发"
        transplant_advice = "可考虑单独肾移植 (无需依库珠单抗预防)"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "genetic_risks": genetic_risks,
        "overall_risk": overall_risk,
        "relapse_risk": relapse_risk,
        "renal_prognosis": renal_prognosis,
        "eculizumab_indicated": eculizumab_indicated,
        "eculizumab_reason": eculizumab_reason,
        "treatment_plan": ("依库珠单抗 900mg IV qw×4→1200mg q2w + 脑膜炎球菌疫苗"
                          if eculizumab_indicated else "血浆置换 ± 免疫抑制 (依具体病因)"),
        "transplant_risk": transplant_risk,
        "transplant_advice": transplant_advice,
        "genetic_counseling": "推荐遗传咨询 + 家系筛查 (一级亲属)" if genetic_risks else "",
        "summary": f"遗传风险 — {overall_risk} | {'依库珠单抗有适应证' if eculizumab_indicated else '保守治疗'}",
    }


def monitoring_plan(patient_id: str = "", phase: str = "acute",
                    on_eculizumab: bool = False,
                    **kwargs: Any) -> dict:
    """aHUS 全周期监测方案 — 急性期/稳定期/长期随访."""
    p, err = _get_patient({"patient_id": patient_id})

    if phase == "acute":
        plan = {
            "phase": "急性期 (住院)",
            "frequency": "每日",
            "labs": ["血常规+PLT qd", "LDH+Haptoglobin qd", "Cr+BUN+尿量 qd",
                     "C3/C4+sC5b-9 隔日", "外周血涂片(破碎红细胞%) qd",
                     "ADAMTS13活性 (结果回报前)"],
            "imaging": ["肾脏超声 (排除肾后性/肾静脉血栓)", "头颅MRI (若神经症状)"],
            "monitor": ["血压 q4h", "尿量 q1h", "神经系统查体 q8h"],
            "eculizumab_specific": (["脑膜炎球菌疫苗接种确认", "补体活性监测(CH50/AH50)",
                                     "脑膜炎球菌感染征象监测(发热/头痛/颈强直)"]
                                   if on_eculizumab else []),
        }
    elif phase == "stable":
        plan = {
            "phase": "稳定期 (出院后)",
            "frequency": "第1个月每周, 之后每2-4周",
            "labs": ["血常规+PLT q2w", "LDH+Haptoglobin q2w", "Cr+蛋白尿(UPC) q4w",
                     "C3/C4+sC5b-9 每月", "依库珠单抗谷浓度 (给药前) 每月"],
            "monitor": ["血压 每周", "尿量/水肿 每日自我监测"],
            "eculizumab_specific": (["依库珠单抗 1200mg q2w 确保不遗漏",
                                     "脑膜炎球菌感染风险持续告知",
                                     "CH50监测(目标<10% — 完全补体抑制)"]
                                   if on_eculizumab else ["血浆置换方案评估"]),
        }
    else:
        plan = {
            "phase": "长期随访 (>6个月)",
            "frequency": "每1-3月",
            "labs": ["Cr+eGFR+CKD分期 q3m", "UPC(尿蛋白肌酐比) q3m",
                     "C3/C4+sC5b-9 q3-6m", "依库珠单抗谷浓度 q3-6m"],
            "monitor": ["CKD进展评估", "心血管风险评估(血压+血脂)",
                        "是否达到停药标准: C3/C4正常+sC5b-9<250+肾功能稳定>6m+无溶血"],
            "eculizumab_specific": (["停药评估: 基因型+补体指标+肾功能稳定",
                                     "停药后密切监测(每1-2周×3月)"]
                                   if on_eculizumab else []),
        }

    return {
        "status": "ok",
        "patient_id": patient_id,
        **plan,
        "summary": f"监测方案 — {plan['phase']} (复查{plan['frequency']})",
    }
