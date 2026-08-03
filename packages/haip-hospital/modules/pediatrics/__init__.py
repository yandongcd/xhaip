"""儿科 — 生长发育评估 + IMCI 决策树 + 儿童用药剂量.

业务流来源:
  - WHO IMCI (Integrated Management of Childhood Illness) 2014
  - 中国 0-18岁 儿童生长发育标准 (卫健委 2023)
  - 中国国家处方集 (儿童版)
"""

from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pediatrics", department="儿科")
_GUIDELINES = [
    "WHO IMCI 儿童疾病综合管理 (2014)",
    "中国 0-18岁 儿童生长发育标准 (卫健委 2023)",
    "中国国家处方集 (儿童版)",
    "中国儿童保健指南 (2023)",
    "AAP 美国儿科学会 Bright Futures Guidelines (2022)",
]
_agent.rule_engine.load_all()

# ── IMCI 决策树 ──

IMCI_RULES = [
    {
        "symptoms": ["fever", "cough", "tachypnea", "chest_indrawing"],
        "diagnosis": "重症肺炎",
        "severity": "severe",
        "treatment": "住院 + IV 抗生素 (头孢曲松 80mg/kg/d)",
        "warning": "需紧急转诊",
    },
    {
        "symptoms": ["fever", "cough", "tachypnea"],
        "diagnosis": "肺炎",
        "severity": "moderate",
        "treatment": "口服阿莫西林 50mg/kg/d 分2次 ×5天",
    },
    {
        "symptoms": ["fever", "cough"],
        "diagnosis": "上呼吸道感染",
        "severity": "mild",
        "treatment": "对症 + 观察",
    },
    {
        "symptoms": ["diarrhea", "dehydration", "sunken_eyes"],
        "diagnosis": "重度脱水",
        "severity": "severe",
        "treatment": "IV 补液 (乳酸林格 100ml/kg) + ORS 补充",
        "warning": "需紧急补液",
    },
    {
        "symptoms": ["diarrhea", "dehydration"],
        "diagnosis": "中度脱水/胃肠炎",
        "severity": "moderate",
        "treatment": "ORS 75ml/kg 4h + 补锌 20mg/d ×10-14天",
    },
    {
        "symptoms": ["diarrhea"],
        "diagnosis": "轻度胃肠炎",
        "severity": "mild",
        "treatment": "ORS 预防脱水 + 继续喂养",
    },
    {
        "symptoms": ["fever", "rash"],
        "diagnosis": "病毒性皮疹",
        "severity": "mild",
        "treatment": "对症 + 观察",
    },
    {
        "symptoms": ["wheeze", "cough"],
        "diagnosis": "喘息性支气管炎/哮喘",
        "severity": "moderate",
        "treatment": "沙丁胺醇雾化 + 必要时口服激素",
    },
]

# 儿童常用药物剂量 (mg/kg)
PEDIATRIC_DOSING = {
    "amoxicillin": {"dose_mg_kg": 50, "frequency": "bid", "max_daily_mg": 2000},
    "ceftriaxone": {"dose_mg_kg": 80, "frequency": "qd", "max_daily_mg": 4000},
    "azithromycin": {"dose_mg_kg": 10, "frequency": "qd", "max_daily_mg": 500},
    "ibuprofen": {"dose_mg_kg": 10, "frequency": "tid", "max_daily_mg": 1200},
    "paracetamol": {"dose_mg_kg": 15, "frequency": "q6h", "max_daily_mg": 3000},
    "salbutamol": {"dose_mg_kg": 0.15, "frequency": "q4-6h", "max_daily_mg": 10},
    "prednisolone": {"dose_mg_kg": 2, "frequency": "qd", "max_daily_mg": 60},
    "zinc": {"dose_mg_kg": 1, "frequency": "qd", "max_daily_mg": 20},
}


def evaluate(
    patient_id: str = "", age_months: int = 0,
    weight_kg: float = 0.0, height_cm: float = 0.0,
    gender: str = "M", **kwargs: Any,
) -> dict[str, Any]:
    """生长发育评估: 身高/体重/BMI 百分位。

    参考: 中国 0-18岁 儿童生长发育标准 (卫健委 2023)
    """
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1) if height_cm > 0 else 0
    age_y = age_months / 12

    # 简化百分位判断 (实际应查标准生长曲线表)
    weight_status = "正常"
    if age_y < 5:
        if weight_kg < 10:
            weight_status = "偏低"
        elif weight_kg > 22:
            weight_status = "偏高"
    else:
        if weight_kg < 18:
            weight_status = "偏低"
        elif weight_kg > 50:
            weight_status = "偏高"

    height_status = "正常"
    if age_y < 5:
        if height_cm < 85:
            height_status = "偏低"
        elif height_cm > 115:
            height_status = "偏高"

    return {
        "patient_id": patient_id,
        "age_months": age_months, "age_years": round(age_y, 1),
        "weight_kg": weight_kg, "height_cm": height_cm, "bmi": bmi,
        "weight_status": weight_status, "height_status": height_status,
        "growth_assessment": "正常发育" if weight_status == "正常" and height_status == "正常" else "需进一步评估",
    }


def calc(
    patient_id: str = "", drug_name: str = "", weight_kg: float = 0.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """儿童用药剂量: 按体重/体表面积计算。

    参考: 中国国家处方集 (儿童版)
    """
    d = PEDIATRIC_DOSING.get(drug_name.lower(), {"dose_mg_kg": 20, "frequency": "bid", "max_daily_mg": 2000})
    dose_per_kg = d["dose_mg_kg"]
    dose_mg = round(weight_kg * dose_per_kg, 1)
    daily_mg = round(dose_mg * (2 if d["frequency"] in ("bid", "q12h") else 3 if d["frequency"] == "tid" else 1), 1)
    max_daily = d["max_daily_mg"]

    return {
        "patient_id": patient_id, "drug": drug_name,
        "dose_mg_per_kg": dose_per_kg,
        "single_dose_mg": min(dose_mg, max_daily),
        "frequency": d["frequency"],
        "max_daily_mg": max_daily,
        "calculated_daily_mg": daily_mg,
        "dose_exceeded": daily_mg > max_daily,
        "warning": f"日剂量超过上限 {max_daily}mg !" if daily_mg > max_daily else None,
    }


def diagnose(
    patient_id: str = "", symptoms: list[str] | None = None,
    age_months: int = 0, **kwargs: Any,
) -> dict[str, Any]:
    """WHO IMCI 常见病决策树。

    参考: WHO IMCI 2014
    """
    symptoms = [s.lower() for s in (symptoms or [])]
    best_match = None
    best_score = 0

    for rule in IMCI_RULES:
        score = sum(1 for s in rule["symptoms"] if any(k in " ".join(symptoms) for k in [s, s.replace("_", " ")]))
        if score > best_score and score >= len(rule["symptoms"]) * 0.5:
            best_score = score
            best_match = rule

    if best_match:
        return {
            "patient_id": patient_id, "diagnosis": best_match["diagnosis"],
            "severity": best_match["severity"], "treatment": best_match["treatment"],
            "matched_symptoms": best_score, "total_rule_symptoms": len(best_match["symptoms"]),
            "warning": best_match.get("warning"),
            "evidence": ["WHO IMCI 2014"],
        }

    return {
        "patient_id": patient_id, "diagnosis": "待进一步检查",
        "severity": "undetermined", "treatment": "建议线下就诊",
        "evidence": [],
    }
