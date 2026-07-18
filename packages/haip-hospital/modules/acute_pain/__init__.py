"""急性疼痛评估与管理 — NRS/VAS + DN4 筛查 + 疼痛危象检测 + PCA 管理.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any


def assess(vas_score: int = 0, description: str = "", nrs_score: int = 0,
           pain_quality: str = "", pain_site: str = "", dn4_items: dict | None = None,
           **kwargs: Any) -> dict:
    """急性疼痛综合评估 — NRS/VAS + DN4 神经病理痛筛查."""
    nrs = nrs_score if nrs_score > 0 else max(0, min(10, round(vas_score / 10)))
    if nrs <= 3:
        nrs_level, level_en = "轻度疼痛", "mild"
        recs = ["NSAIDs 口服", "冷敷/局部理疗"]
    elif nrs <= 6:
        nrs_level, level_en = "中度疼痛", "moderate"
        recs = ["曲马多 50-100mg q6h prn + NSAIDs", "必要时加巴喷丁"]
    else:
        nrs_level, level_en = "重度疼痛", "severe"
        recs = ["吗啡/羟考酮注射", "PCA 评估", "疼痛危象筛查"]

    dn4 = dn4_items or {}
    dn4_score = sum(1 for v in dn4.values() if v)
    is_neuropathic = dn4_score >= 4
    neuro_keywords = ["电击", "烧灼", "针刺", "麻木", "蚁走", "冰冷"]
    if not dn4 and any(kw in pain_quality for kw in neuro_keywords):
        is_neuropathic = True
        dn4_score = max(dn4_score, 4)

    if is_neuropathic and level_en in ("moderate", "severe"):
        recs.append("加巴喷丁/普瑞巴林")

    return {
        "status": "ok",
        "vas_score": vas_score, "nrs_score": nrs,
        "nrs_level": nrs_level, "nrs_level_en": level_en,
        "dn4_score": dn4_score, "is_neuropathic": is_neuropathic,
        "pain_site": pain_site, "pain_quality": pain_quality,
        "recommendations": recs,
        "description": description,
    }


def crisis(symptoms: list | None = None,
           pain_description: str = "", physical_exam: str = "",
           postop_day: int = 99,
           **kwargs: Any) -> dict:
    """疼痛危象检测 — 筋膜室综合征/动脉栓塞/急腹症."""
    symptoms = symptoms or []
    pain = (pain_description or "").lower()
    exam = (physical_exam or "").lower()
    combined = f"{pain} {exam} {' '.join(s.lower() for s in symptoms)}"

    crisis_type = ""
    urgency = "routine"
    alert = ""
    action = ""

    if any(kw in combined for kw in ["被动牵拉痛", "牵拉痛加重"]) and postop_day <= 2:
        if "张力高" in combined or "皮温低" in combined:
            crisis_type = "筋膜室综合征"
            urgency = "emergent"
            alert = "5P征监测"
            action = "立即通知骨科，测筋膜室压力，备急诊切开减压"
    elif any(kw in combined for kw in ["突", "剧痛", "苍白", "发凉"]) and ("动脉" in combined or "搏动消失" in combined):
        crisis_type = "急性动脉栓塞"
        urgency = "emergent"
        alert = "6P征评估"
        action = "立即血管外科急会诊，急诊 CTA，备取栓/溶栓"
    elif "板状腹" in combined or "反跳痛" in combined:
        crisis_type = "急腹症/内脏穿孔"
        urgency = "emergent"
        alert = "禁食水，急诊腹部 CT，普外科急会诊"
        action = "立即通知外科值班"

    # Fallback for backward-compatible simple symptoms list
    if not crisis_type:
        if any("calf" in s.lower() or "肿胀" in s for s in symptoms):
            crisis_type = "dvt"
            urgency = "urgent"
            alert = "下肢肿胀 — 需排除 DVT"
            action = "下肢静脉超声 + D-二聚体"

    return {
        "status": "ok",
        "crisis_detected": bool(crisis_type),
        "crisis_type": crisis_type or "无疼痛危象",
        "urgency": urgency,
        "alert_message": alert,
        "recommended_action": action if crisis_type else "无疼痛危象",
        "symptoms": symptoms,
    }


def pca(age: int = 0, weight_kg: float = 0.0, renal_ok: bool = True,
        creatinine: float = 0.0, **kwargs: Any) -> dict:
    """PCA (患者自控镇痛) 参数计算 — 年龄/肾功能调整."""
    weight = weight_kg if weight_kg > 0 else 70
    adjustment_needed = False
    adj_reason = ""

    if age < 14:
        bolus = round(0.015 * weight, 1)
        lockout = 8
        basal = round(bolus * 0.3, 1)
        limit = round(bolus * 8, 1)
        note = "pediatric PCA — 按体重精确计算，需专人监护"
        adjustment_needed = True
        adj_reason = "儿童患者 — 儿科剂量调整"
    elif age >= 75:
        bolus = 0.5
        lockout = 10
        basal = 0.2
        limit = 6
        note = "高龄患者 — 起始剂量减半，缓慢滴定"
        adjustment_needed = True
        adj_reason = f"高龄患者({age}岁) — 减量并延长锁定时间"
    elif age >= 65:
        bolus = 0.8
        lockout = 8
        basal = 0.3
        limit = 8
        note = "老年患者 — 适当减量"
        adjustment_needed = True
        adj_reason = f"老年患者({age}岁) — 减量调整"
    else:
        bolus = 1.0
        lockout = 6
        basal = 0.5
        limit = 10
        note = "标准成人剂量"

    if not renal_ok or creatinine > 133:
        note += " | 肾功能不全 — 避免哌替啶"
        adjustment_needed = True
        adj_reason += " | 肾功能不全调整"

    regimen = {
        "drug": "morphine", "concentration": "1 mg/mL",
        "bolus_mg": bolus, "lockout_min": lockout,
        "basal_rate_mg_h": basal, "four_hour_limit_mg": limit,
        "note": note,
    }
    monitoring = ["呼吸频率 q1h×6h", "镇静评分 Ramsay", "SpO2 持续", "恶心/呕吐", "尿潴留", "瘙痒"]

    return {
        "status": "ok",
        "pca_regimen": regimen,
        "adjustment_needed": adjustment_needed,
        "adjustment_reason": adj_reason if adjustment_needed else "标准方案无需调整",
        "side_effect_monitoring": monitoring,
        "bolus_mg": round(bolus, 2),
        "age": age, "weight_kg": weight,
    }
