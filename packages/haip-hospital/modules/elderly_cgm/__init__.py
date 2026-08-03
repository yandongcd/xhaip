"""Elderly CGM v2.0 — 动态血糖监测综合管理: AGP + 年龄分层目标 + 胰岛素调整 + 营养/固醇诱发.

Guidelines: ADA 2025, 中国老年糖尿病指南(2024), 住院血糖管理共识, Endocrine Society 2023
"""
from __future__ import annotations

from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="elderly-cgm", department="老年病科")
_GUIDELINES = [
    "ADA 糖尿病医学诊疗标准 (2025)",
    "中国2型糖尿病防治指南 (2024)",
    "中国老年糖尿病诊疗指南 (2024)",
    "中国住院患者血糖管理专家共识 (2023)",
    "Endocrine Society 老年糖尿病管理指南 (2023)",
]
_agent.rule_engine.load_all()


def _get_patient(kwargs: dict) -> tuple[dict | None, dict | None]:
    return _agent.get_patient_from_kwargs(kwargs)


# ═══════ CGM Metrics Engine ═══════

def _cgm_metrics(readings: list[float]) -> dict:
    """AGP (Ambulatory Glucose Profile) 核心指标计算."""
    if not readings or len(readings) < 3:
        return {"tir": 0, "tar": 0, "tbr": 0, "cv": 0, "gmi": 0, "mean": 0, "sd": 0}

    n = len(readings)
    mean = sum(readings) / n
    sd = (sum((g - mean) ** 2 for g in readings) / n) ** 0.5
    cv = round(sd / mean * 100, 1) if mean > 0 else 0

    tir = round(sum(1 for g in readings if 3.9 <= g <= 10.0) / n * 100, 1)
    tar_above = round(sum(1 for g in readings if g > 10.0) / n * 100, 1)
    tar_very_high = round(sum(1 for g in readings if g > 13.9) / n * 100, 1)
    tbr_below = round(sum(1 for g in readings if g < 3.9) / n * 100, 1)
    tbr_severe = round(sum(1 for g in readings if g < 3.0) / n * 100, 1)

    # GMI (glucose management indicator) — ADA formula
    gmi = round(3.31 + 0.02392 * mean, 1) if mean > 0 else 0

    return {
        "tir": tir, "tar": tar_above, "tar_very_high": tar_very_high,
        "tbr": tbr_below, "tbr_severe": tbr_severe,
        "cv": cv, "gmi": gmi, "mean": round(mean, 1),
        "sd": round(sd, 1), "readings_count": n,
    }


# ═══════ Age-Stratified Glucose Targets ═══════

def _elderly_targets(age: int, health_status: str, comorbidities: list[str]) -> dict:
    """老年糖尿病患者个体化血糖目标 (ADA 2024 + 中国老年指南)."""

    # Determine frailty tier
    if health_status in ("very_poor", "终末期", "hospice", "palliative"):
        tier = "very_complex"
        targets = {"fasting": "7.8-10.0", "postprandial": "<13.9", "bedtime": "8.0-11.0",
                   "tir_goal": ">50% (3.9-10.0)", "hba1c": "<8.0-8.5%",
                   "priority": "避免低血糖+避免高血糖危象+维持生活质量"}
    elif health_status in ("complex", "中重度", "frail") or len(comorbidities) >= 3:
        tier = "complex"
        targets = {"fasting": "6.1-8.3", "postprandial": "<11.1", "bedtime": "6.5-9.0",
                   "tir_goal": ">50% (3.9-10.0)", "hba1c": "<7.5-8.0%",
                   "priority": "避免低血糖+血糖总体稳定"}
    elif health_status in ("healthy", "良好", "robust"):
        tier = "healthy"
        targets = {"fasting": "5.0-7.2", "postprandial": "<10.0", "bedtime": "5.5-7.5",
                   "tir_goal": ">70% (3.9-10.0)", "hba1c": "<7.0-7.5%",
                   "priority": "严格控制+低血糖最小化"}
    else:
        tier = "intermediate"
        targets = {"fasting": "5.6-7.8", "postprandial": "<10.0", "bedtime": "6.0-8.0",
                   "tir_goal": ">50%", "hba1c": "<7.5%",
                   "priority": "平衡血糖达标+安全"}

    return {"tier": tier, "targets": targets}


# ═══════ Insulin Dose Adjustment ═══════

def _insulin_adjust(current_glucose: float, trend: float, basal_dose: float | None,
                    prandial_dose: float | None, nutrition: str) -> dict:
    """胰岛素个体化调整建议."""

    actions = []
    basal_change = 0
    prandial_change = 0

    # Hypoglycemia management
    if current_glucose < 3.0:
        actions.append("严重低血糖! 立即50%葡萄糖20mL IV 或 胰高血糖素1mg IM/SC (若意识障碍)")
        if basal_dose:
            basal_change = -basal_dose * 0.5
            actions.append(f"基础胰岛素减量 ≥50% 并持续降低至少24h (当前{basal_dose}U→约{basal_dose*0.5:.0f}U)")
        return {"actions": actions, "emergency": True, "basal_reduce_pct": 50}

    if current_glucose < 3.9:
        actions.append("低血糖! 口服15g葡萄糖(3片葡萄糖片/150mL果汁), 15min后复查血糖")
        if basal_dose:
            basal_change = -basal_dose * 0.2
            actions.append(f"基础胰岛素减量20% (当前{basal_dose}U→{basal_dose*0.8:.0f}U)")
        if prandial_dose:
            prandial_change = -prandial_dose * 0.5
            actions.append(f"餐时胰岛素减量50% (当前{prandial_dose}U→{prandial_dose*0.5:.0f}U)")
        return {"actions": actions, "emergency": False, "basal_reduce_pct": 20}

    # Trend-based adjustments
    if trend < -1.5:
        actions.append(f"快速下降中 (Δ{trend:.1f} mmol/L/h) — 60min内低血糖风险高, 暂停餐时胰岛素, 若进食后>15min仍下降→口服15g糖")
    elif trend > 2.0 and current_glucose > 10.0:
        actions.append(f"持续升高 (Δ{trend:.1f} mmol/L/h) — 考虑追加纠正量")
        if prandial_dose:
            prandial_change = prandial_dose * 0.1

    # Nutrition-related
    if nutrition in ("npo", "禁食", "fasting"):
        actions.append("NPO/禁食 — 基础胰岛素减量30-50%, 停餐时胰岛素, 每2h监测血糖")

    return {"actions": actions, "emergency": False, "basal_adjust_pct": round(basal_change / max(basal_dose or 1, 1) * 100) if basal_dose else 0,
            "prandial_adjust_pct": round(prandial_change / max(prandial_dose or 1, 1) * 100) if prandial_dose else 0}


# ═══════ Steroid-Induced Hyperglycemia ═══════

def _steroid_hyperglycemia(steroid: str, dose_mg: float, timing: str) -> dict:
    """糖皮质激素诱发高血糖管理."""

    steroid_map = {
        "prednisone": {"peak": "4-8h", "duration": "12-16h", "adjust": "中效胰岛素(NPH)午餐前/下午"},
        "methylprednisolone": {"peak": "4-6h", "duration": "8-12h", "adjust": "NPH/常规胰岛素 午餐前"},
        "dexamethasone": {"peak": "12-16h", "duration": "24-36h", "adjust": "基础胰岛素加量+NPH或甘精胰岛素全天覆盖"},
        "hydrocortisone": {"peak": "1-2h", "duration": "4-8h", "adjust": "常规胰岛素 每6h"},
    }

    info = steroid_map.get(steroid.lower().split(" ")[0], steroid_map["prednisone"])

    if dose_mg >= 40:
        severity = "大剂量 (>40mg/d) — 午餐后/下午血糖飙升, 建议NPH 0.1-0.2 U/kg 午餐前 + 每2-4h监测"
    elif dose_mg >= 20:
        severity = "中等剂量 — 下午高血糖常见, 午餐后胰岛素追加"
    else:
        severity = "低剂量 — 常规监测即可"

    return {
        "steroid": steroid, "dose_mg": dose_mg,
        "peak_time": info["peak"], "duration": info["duration"],
        "management": info["adjust"], "severity": severity,
    }


# ═══════ Handler Functions ═══════


def cgm_analysis(patient_id: str = "", cgm_readings: list | None = None,
                 **kwargs: Any) -> dict:
    """CGM + AGP 综合分析 — TIR/TAR/TBR/CV/GMI + 年龄分层目标."""
    p, err = _get_patient({"patient_id": patient_id})
    cgm_readings = cgm_readings or []

    metrics = _cgm_metrics(cgm_readings)

    # Patient context
    age = p.get("age", 75) if p else 75
    health = kwargs.get("health_status", "intermediate")
    comorbidities = kwargs.get("comorbidities", [])
    targets = _elderly_targets(age, health, comorbidities)

    # Alerts based on targets
    alerts = []
    if metrics["tir"] < 50:
        alerts.append(f"TIR {metrics['tir']}% — 严重不达标 (目标{targets['targets']['tir_goal']})")
    elif targets["tier"] == "healthy" and metrics["tir"] < 70:
        alerts.append(f"TIR {metrics['tir']}% — 未达标 (>70%目标)")
    if metrics["tbr"] >= 5:
        alerts.append(f"低血糖时间 {metrics['tbr']}% — 超过安全阈值(<5%)")
    if metrics["tbr_severe"] > 1:
        alerts.append(f"严重低血糖时间 {metrics['tbr_severe']}% — 需紧急调整方案!")
    if metrics["cv"] > 36:
        alerts.append(f"血糖变异度 CV={metrics['cv']}% — 超过目标(<36%), 提示血糖波动大")

    # CV color coding
    if metrics["cv"] <= 20:
        cv_level = "稳定 (CV≤20%)"
    elif metrics["cv"] <= 36:
        cv_level = "可接受 (CV 20-36%)"
    else:
        cv_level = f"不稳定 (CV={metrics['cv']}% >36%)"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "age_stratification": targets,
        "tir": metrics["tir"], "tar": metrics["tar"],
        "tar_very_high": metrics["tar_very_high"],
        "tbr": metrics["tbr"], "tbr_severe": metrics["tbr_severe"],
        "cv": metrics["cv"], "cv_level": cv_level,
        "gmi": metrics["gmi"], "mean_glucose": metrics["mean"], "sd": metrics["sd"],
        "readings_count": metrics["readings_count"],
        "alerts": alerts, "alert_level": "red" if metrics["tbr_severe"] > 1 else ("yellow" if alerts else "green"),
        "summary": f"CGM — TIR {metrics['tir']}% | CV={metrics['cv']}% | GMI≈{metrics['gmi']}% | {cv_level}",
        "guideline_ref": "ADA 2025 + 中国老年糖尿病指南 2024",
    }


def hypo_predict(patient_id: str = "", recent_glucose: list | None = None,
                 medications: list | None = None,
                 creatinine: float = 1.0, weight_kg: float = 70.0,
                 nutrition: str = "eating", age: int = 75,
                 **kwargs: Any) -> dict:
    """前瞻性低血糖预测 — 趋势+胰岛素+肾功+营养 四维评估."""
    p, err = _get_patient({"patient_id": patient_id})
    recent_glucose = recent_glucose or []
    medications = medications or []

    if not recent_glucose:
        return {"status": "ok", "patient_id": patient_id, "risk": "数据不足",
                "summary": "需要近2h CGM数据 (至少3个点)"}

    current = recent_glucose[-1]
    trend = recent_glucose[-1] - recent_glucose[0] if len(recent_glucose) >= 2 else 0
    trend_per_h = trend / (len(recent_glucose) * 5 / 60) if len(recent_glucose) >= 2 else 0

    # Multi-factor risk scoring
    risk_score = 0
    risk_factors = []

    # Factor 1: Current glucose level
    if current < 3.0:
        risk_score += 10
        risk_factors.append("当前严重低血糖 (<3.0 mmol/L)")
    elif current < 3.9:
        risk_score += 6
        risk_factors.append(f"当前低血糖 ({current} mmol/L)")
    elif current < 4.5:
        risk_score += 2
        risk_factors.append(f"血糖处于低血糖边缘 ({current})")

    # Factor 2: Trend
    if trend_per_h < -2.0:
        risk_score += 4
        risk_factors.append(f"快速下降趋势 ({trend_per_h:.1f} mmol/L/h) — 30min内低血糖可能")
    elif trend_per_h < -1.0:
        risk_score += 2
        risk_factors.append(f"下降趋势 ({trend_per_h:.1f} mmol/L/h) — 60min内关注")

    # Factor 3: Insulin on board
    has_insulin = any("胰岛素" in str(m) or "insulin" in str(m).lower() for m in medications)
    has_sulfonylurea = any(su in str(medications).lower() for su in ["格列", "glipizide", "glyburide", "glimepiride", "gliclazide"])
    if has_insulin:
        risk_score += 3
        risk_factors.append("使用胰岛素 — 低血糖风险增高")
    if has_sulfonylurea:
        risk_score += 2
        risk_factors.append("使用磺脲类 — 老年患者低血糖风险显著 (建议停用/减量)")

    # Factor 4: Renal impairment (decreased insulin clearance)
    egfr = round(175 * (creatinine ** -1.154) * (age ** -0.203) * (0.742 if p and p.get("gender", "M") == "F" else 1)) if creatinine > 0 else 90
    if egfr < 30:
        risk_score += 4
        risk_factors.append(f"严重肾功能不全 (eGFR={egfr}) — 胰岛素清除降低, 半衰期延长")
    elif egfr < 60:
        risk_score += 1
        risk_factors.append(f"中度肾功能不全 (eGFR={egfr})")

    # Factor 5: Nutrition
    if nutrition in ("npo", "禁食"):
        risk_score += 5
        risk_factors.append("NPO/禁食 — 高血糖+低血糖双重风险, 基础胰岛素减30-50%")

    # Risk tier
    if risk_score >= 10:
        risk = "红 — 立即干预"
        action = f"严重低血糖风险! 当前血糖{current} mmol/L → " + \
                 ("立即口服50%葡萄糖20mL IV (意识障碍)" if current < 3.0 else
                  "口服15g葡萄糖+15min后复查 → 基础胰岛素减量50%")
    elif risk_score >= 6:
        risk = "橙 — 30min内干预"
        action = f"高概率低血糖预警 → 当前{current}, 趋势{trend_per_h:.1f}/h → 建议预防性口服15g糖或暂停餐时胰岛素"
    elif risk_score >= 3:
        risk = "黄 — 60min监测"
        action = "中等低血糖风险 → 加强监测(每30-60min), 准备碳水"
    else:
        risk = "绿 — 安全"
        action = "低血糖风险低, 常规监测 (每2-4h)"

    return {
        "status": "ok",
        "patient_id": patient_id,
        "current_glucose": current,
        "trend_per_hour": round(trend_per_h, 1),
        "risk_score": risk_score,
        "risk_tier": risk,
        "risk_factors": risk_factors,
        "recommended_action": action,
        "egfr": egfr,
        "summary": f"低血糖预测 — {risk} (得分{risk_score}) | {'立即干预!' if risk_score >= 6 else '常规监测'}",
    }


def regimen_optimize(patient_id: str = "", tir_percent: float = 60.0,
                     hypo_risk: str = "绿",
                     current_regimen: list | None = None,
                     weight_kg: float = 70.0, age: int = 75,
                     health_status: str = "complex",
                     steroid: str = "", steroid_dose_mg: float = 0.0,
                     nutrition: str = "eating",
                     **kwargs: Any) -> dict:
    """降糖方案个体化优化 — 胰岛素调整+年龄分层+固醇诱发+营养+出院过渡."""
    p, err = _get_patient({"patient_id": patient_id})

    targets = _elderly_targets(age, health_status, kwargs.get("comorbidities", []))
    recs = []
    alerts = []

    # 1. Hypoglycemia-first principle
    if hypo_risk in ("红 — 立即干预", "橙 — 30min内干预"):
        recs.append("最高优先级: 立即减少胰岛素/磺脲类剂量 ≥30-50% (安全优先原则)")
        if age >= 80:
            recs.append("高龄(≥80岁): 放宽血糖目标 — 空腹7.8-10.0, 避免低血糖优先于血糖达标")

    # 2. TIR-based adjustment
    if tir_percent < 50:
        if targets["tier"] == "healthy":
            recs.append("增加基础胰岛素 2-4U qd 或 加用DPP-4i/GLP-1RA (低血糖风险低)")
        else:
            recs.append(f"老年{targets['tier']}状态: TIR达标目标已放宽至{targets['targets']['tir_goal']}, "
                       "以安全为优先, 避免过度积极降糖")
    elif tir_percent < 70 and targets["tier"] == "healthy":
        recs.append("TIR <70% — 基础胰岛素增加10-15% (2-3U)")

    # 3. Drug-specific recommendations
    current_regimen = current_regimen or []
    regimen_names = [str(m) for m in current_regimen]

    if any("sulfonylurea" in m.lower() or "磺脲" in m or "格列" in m for m in regimen_names):
        recs.append("老年患者避免磺脲类 (低血糖风险高)! 建议替换为 DPP-4i (西格列汀/利格列汀) 或 SGLT-2i (若eGFR≥20)")

    if any("metformin" in m.lower() or "二甲双胍" in m for m in regimen_names) and age >= 80:
        recs.append("二甲双胍 ≥80岁: 减量至500mg bid 或停用 (eGFR<30禁忌), 监测维生素B12")

    # 4. Steroid-induced hyperglycemia
    if steroid:
        steroid_mgmt = _steroid_hyperglycemia(steroid, steroid_dose_mg, "")
        recs.append(f"固醇诱发高血糖 ({steroid} {steroid_dose_mg}mg): "
                   f"{steroid_mgmt['management']} — 血糖高峰在{steroid_mgmt['peak_time']}")
        if steroid_mgmt["severity"].startswith("大剂量"):
            alerts.append("大剂量固醇 → 午餐后血糖可>15 mmol/L, 需积极加用NPH/餐时胰岛素")

    # 5. Nutrition-related
    if nutrition in ("npo", "禁食"):
        recs.append("禁食/NPO: 基础胰岛素减量30-50%, 停用所有餐时/口服降糖药")
        recs.append("每2h血糖监测 (若输注含糖液, 根据输糖速率+±2-4g/h估算血糖影响)")

    # 6. Transition planning
    recs.append("出院注意事项: ")
    recs.append("  • 出院前1-2天转回口服/皮下方案, 确认血糖稳定(空腹<7.8, 餐后<10.0)")
    recs.append("  • 患者/家属教育: 低血糖识别+处理 (规则15: 15g糖→15min→复查)")
    recs.append("  • 出院后1周内随访: 内分泌科/老年科门诊 确认方案")

    return {
        "status": "ok",
        "patient_id": patient_id,
        "age_stratification": targets,
        "tir": tir_percent,
        "hypo_risk": hypo_risk,
        "recommendations": recs,
        "alerts": alerts,
        "summary": f"方案优化 — {'紧急调整!' if hypo_risk[:1] in ('红','橙') else '个体化优化'} | {targets['tier']}状态 | TIR={tir_percent}%",
        "disclaimer": "此建议为AI辅助生成, 须经主管医师/药师确认后执行",
        "guideline_ref": "ADA 2025 + 中国老年指南 2024 + 住院血糖共识",
    }
