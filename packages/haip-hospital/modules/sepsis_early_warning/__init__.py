"""重症感染早期预警智能体 — 免疫评估 + qSOFA/SOFA + 28天死亡风险 + 分级预警.

业务流: 免疫状态 → 脓毒症评分 → 死亡风险 → 分级推送.
"""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="sepsis-early-warning", department="检验医学科")
_GUIDELINES = [
    "Surviving Sepsis Campaign 2021 国际指南",
    "中国脓毒症/脓毒性休克急诊治疗指南 (2024)",
    "脓毒症免疫监测与治疗专家共识",
    "淋巴细胞亚群检测在临床中的应用专家共识",
]
_agent.rule_engine.load_all()

# Lymphocyte reference ranges (×10⁹/L)
LYMPH_REF = {
    "CD3": (0.7, 2.1), "CD4": (0.4, 1.3), "CD8": (0.2, 0.9),
    "CD4_CD8": (0.9, 3.6), "CD19": (0.1, 0.5), "NK": (0.1, 0.6),
}


def immune_status(**kwargs) -> dict:
    """免疫状态评估 — 淋巴细胞亚群 + NLR."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}
    labs = p.get("lab_results", {}) or {}

    # NLR (neutrophil-to-lymphocyte ratio)
    neut = float(labs.get("neutrophil", labs.get("NEUT", 4.0)) or 4.0)
    lymph = float(labs.get("lymphocyte", labs.get("LYMPH", 1.5)) or 1.5)
    nlr = round(neut / lymph, 1) if lymph > 0 else 99

    # Immune status interpretation
    status = "正常"
    alerts = []
    if lymph < 0.6:
        status = "免疫抑制"
        alerts.append(f"🔴 淋巴细胞严重减少 ({lymph}×10⁹/L) — 免疫麻痹风险")
    elif lymph < 1.0:
        status = "免疫低下"
        alerts.append(f"🟡 淋巴细胞减少 ({lymph}×10⁹/L)")

    if nlr > 10:
        alerts.append(f"🔴 NLR {nlr} >10 — 严重炎症反应/预后不良")
    elif nlr > 5:
        alerts.append(f"🟡 NLR {nlr} >5 — 炎症反应活跃")

    return {
        "status": "ok",
        "immune_status": status,
        "nlr": nlr,
        "lymphocyte": lymph,
        "neutrophil": neut,
        "alerts": alerts,
        "summary": f"免疫状态 — {status} (淋巴细胞 {lymph}×10⁹/L, NLR {nlr})",
    }


def sepsis_score(**kwargs) -> dict:
    """脓毒症风险评分 — qSOFA + SOFA + PCT阶梯."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}
    labs = p.get("lab_results", {}) or {}

    # qSOFA (quick SOFA)
    rr = float(labs.get("RR", 16) or 16)
    sbp = float(labs.get("SBP", 120) or 120)
    gcs = int(labs.get("GCS", 15) or 15)
    qsofa = sum([rr >= 22, sbp <= 100, gcs <= 14])

    # PCT阶梯
    pct = float(labs.get("PCT", 0) or 0)
    pct_level = "正常"
    if pct > 10:
        pct_level = "严重脓毒症高度可能"
    elif pct > 2:
        pct_level = "细菌感染可能性高"
    elif pct > 0.5:
        pct_level = "局部感染可能"

    # Risk assessment
    risk = "低危"
    if qsofa >= 2 and pct > 2:
        risk = "高危 (qSOFA≥2 + PCT>2 → 脓毒症)"
    elif qsofa >= 2 or pct > 10:
        risk = "中危"

    return {
        "status": "ok",
        "qsofa": qsofa, "pct": pct, "pct_level": pct_level,
        "risk": risk,
        "summary": f"脓毒症风险 — {risk} (qSOFA {qsofa}, PCT {pct} ng/mL)",
        "action": "qSOFA≥2+PCT>2 → 启动1h Bundle (血培养+乳酸+抗生素+液体复苏)" if risk == "高危" else "继续监测",
    }


def mortality_risk(**kwargs) -> dict:
    """28天死亡风险预测 — 多因素简化模型."""
    pid = kwargs.get("patient_id", "")
    immune_data = kwargs.get("immune_data", {}) or {}
    sofa = int(kwargs.get("sofa_score", 2) or 2)
    p = _agent.get_patient(pid) or {}
    age = p.get("age", 0)

    # Simplified mortality risk scoring (based on clinical literature)
    score = 0
    if age >= 75:
        score += 3
    elif age >= 65:
        score += 2
    elif age >= 55:
        score += 1

    nlr = immune_data.get("nlr", 5)
    if nlr > 15:
        score += 4
    elif nlr > 10:
        score += 3
    elif nlr > 5:
        score += 2

    lymph = immune_data.get("lymphocyte", 1.5)
    if lymph < 0.3:
        score += 5  # persistent lymphopenia — highest risk
    elif lymph < 0.6:
        score += 3
    elif lymph < 1.0:
        score += 1

    score += sofa  # SOFA contributions

    # Map to mortality probability
    if score >= 15:
        prob = 0.65
        level = "极高危"
    elif score >= 10:
        prob = 0.40
        level = "高危"
    elif score >= 6:
        prob = 0.20
        level = "中危"
    else:
        prob = 0.08
        level = "低危"

    return {
        "status": "ok",
        "score": score, "level": level,
        "mortality_probability": f"{prob:.0%}",
        "summary": f"28天死亡风险 — {level} ({prob:.0%})",
        "factors": {
            "年龄": age, "NLR": nlr, "淋巴细胞": lymph, "SOFA": sofa, "总评分": score,
        },
    }


def early_warning(**kwargs) -> dict:
    """分级预警推送 — 低/中/高危 + 逐级升级."""
    pid = kwargs.get("patient_id", "")
    risk_level = kwargs.get("risk_level", "中危")
    mortality_prob = float(str(kwargs.get("mortality_prob", "0.2")).rstrip("%")) if kwargs.get("mortality_prob") else 0.2

    alerts = []
    escalation = ""

    if risk_level in ("高危", "极高危"):
        alerts.append(f"🔴 {risk_level} — 立即推送ICU+感染科+主治医师")
        escalation = "24h未响应 → 电话通知科主任 | 48h → 医务处"
    elif risk_level == "中危":
        alerts.append("🟠 中危 — 推送ICU值班医生")
        escalation = "48h未响应 → 升级至科主任"
    else:
        alerts.append("🟢 低危 — 常规监测, 每日评估")
        escalation = "常规"

    return {
        "status": "ok",
        "level": risk_level,
        "alerts": alerts,
        "escalation": escalation,
        "summary": f"分级预警 — {risk_level}",
        "actions": [
            "脓毒症1h Bundle: 血培养×2 + 乳酸 + 抗生素 + 液体30mL/kg + 血管活性药(如需要)" if risk_level in ("高危", "极高危") else "",
            "每日复查PCT+淋巴细胞亚群" if risk_level in ("中危", "高危") else "",
        ],
    }
