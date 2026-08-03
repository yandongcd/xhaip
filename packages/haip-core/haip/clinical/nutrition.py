"""NRS-2002 营养风险筛查 — Python implementation.

Ported from haip-0710 skill: .openharness/skills/nrs2002/SKILL.md
Trust: T1 (ESPEN 2023 + 中华医学会 2023)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NRS2002Result:
    """NRS-2002 assessment result."""

    total_score: int
    nutrition_score: int
    disease_score: int
    age_bonus: int
    risk_level: str  # 低风险 / 中度风险 / 高风险
    recommendation: str


def assess(
    age: int,
    bmi: float,
    nutrition_status: str = "正常",
    disease_severity: str = "无",
    weight_kg: float | None = None,
    height_cm: float | None = None,
    weight_loss_3m_pct: float | None = None,
    weight_loss_2m_pct: float | None = None,
    weight_loss_1m_pct: float | None = None,
    intake_reduction: str = "无",
    diagnosis: str = "",
) -> NRS2002Result:
    """Calculate NRS-2002 nutritional risk score.

    Args:
        age: Patient age in years.
        bmi: Body Mass Index (kg/m²).
        nutrition_status: 正常/轻度/中度/重度.
        disease_severity: 无/轻度应激/中度应激/重度应激.
        weight_kg: Weight in kg (used for BMI calculation if bmi not given).
        height_cm: Height in cm.
        weight_loss_3m_pct: Weight loss percentage in 3 months.
        weight_loss_2m_pct: Weight loss percentage in 2 months.
        weight_loss_1m_pct: Weight loss percentage in 1 month.
        intake_reduction: 无/25-50%/50-75%/75-100%.
        diagnosis: Clinical diagnosis for disease severity inference.
    """

    # ── Nutrition status score ──
    nutrition_score = 0

    # Auto-detect from weight loss if nutrition_status is default
    if nutrition_status == "正常":
        if weight_loss_1m_pct is not None and weight_loss_1m_pct > 5:
            nutrition_status = "重度"
        elif weight_loss_2m_pct is not None and weight_loss_2m_pct > 5:
            nutrition_status = "中度"
        elif weight_loss_3m_pct is not None and weight_loss_3m_pct > 5:
            nutrition_status = "轻度"

    # Manual nutrition status mapping
    _nutrition_map = {"正常": 0, "轻度": 1, "中度": 2, "重度": 3}
    nutrition_score = _nutrition_map.get(nutrition_status, 0)

    # BMI-based scoring
    if bmi > 0:
        if bmi < 18.5:
            nutrition_score = 3
        elif bmi < 20.5 and nutrition_status not in ("正常",):
            nutrition_score = max(nutrition_score, 2)
    elif weight_kg and height_cm and height_cm > 0:
        bmi = weight_kg / ((height_cm / 100) ** 2)
        if bmi < 18.5:
            nutrition_score = max(nutrition_score, 3)

    # Intake reduction override
    _intake_map = {"无": 0, "25-50%": 1, "50-75%": 2, "75-100%": 3}
    nutrition_score = max(nutrition_score, _intake_map.get(intake_reduction, 0))

    # ── Disease severity score ──
    disease_score = 0

    # Manual severity mapping
    _disease_map = {"无": 0, "轻度应激": 1, "中度应激": 2, "重度应激": 3}
    disease_score = _disease_map.get(disease_severity, 0)

    # Auto-detect from diagnosis keywords
    if disease_severity == "无" and diagnosis:
        _high_severity = {
            "严重烧伤", "严重创伤", "骨髓移植", "APACHE",
            "烧伤", "创伤",
        }
        _moderate_severity = {
            "腹部大手术", "卒中", "脑卒中", "重症肺炎",
            "血液恶性肿瘤", "白血病", "淋巴瘤",
        }
        _mild_severity = {
            "髋部骨折", "COPD", "肝硬化", "血液透析",
            "糖尿病", "慢性疾病", "骨折",
        }
        diag_lower = diagnosis.lower()
        for kw in _high_severity:
            if kw in diag_lower or kw in diagnosis:
                disease_score = max(disease_score, 3)
                break
        for kw in _moderate_severity:
            if kw in diag_lower or kw in diagnosis:
                disease_score = max(disease_score, 2)
                break
        for kw in _mild_severity:
            if kw in diag_lower or kw in diagnosis:
                disease_score = max(disease_score, 1)
                break

    # ── Age bonus ──
    age_bonus = 1 if age >= 70 else 0

    # ── Total ──
    total = nutrition_score + disease_score + age_bonus

    # ── Risk level ──
    if total >= 5:
        risk = "高风险"
        rec = "立即启动营养支持，强化监测（每周 NRS-2002 复查）"
    elif total >= 3:
        risk = "中度风险"
        rec = "启动营养支持，监测摄入量，目标能量 25-30 kcal/kg/d"
    else:
        risk = "低风险"
        rec = "无需营养支持，每周复查 NRS-2002"

    return NRS2002Result(
        total_score=total,
        nutrition_score=nutrition_score,
        disease_score=disease_score,
        age_bonus=age_bonus,
        risk_level=risk,
        recommendation=rec,
    )
