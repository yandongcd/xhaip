"""心血管外科 — EuroSCORE + 抗凝方案 + 术后管理.

业务流来源:
  - EuroSCORE II 心脏手术风险评估
  - ACC/AHA 瓣膜疾病指南
  - ACCP 抗栓治疗指南
"""

from __future__ import annotations

from typing import Any


def evaluate(
    patient_id: str = "", age: int = 60, gender: str = "M",
    conditions: list[str] | None = None,
    labs: dict[str, float] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """简化 EuroSCORE II 心脏手术风险评估。

    参考: EuroSCORE II (2011)
    """
    conditions = [c.lower() for c in (conditions or [])]
    labs = labs or {}
    euroscore = 0

    if age >= 60: euroscore += 1
    if age >= 70: euroscore += 1
    if gender == "F": euroscore += 1
    cr = labs.get("creatinine", 80)
    if cr > 200: euroscore += 2
    elif cr > 133: euroscore += 1
    if any(c in " ".join(conditions) for c in ["copd", "慢性肺病"]): euroscore += 1
    if any(c in " ".join(conditions) for c in ["糖尿病", "dm"]): euroscore += 1
    if any(c in " ".join(conditions) for c in ["心衰", "chf", "nyha iii", "nyha iv"]): euroscore += 2
    if any(c in " ".join(conditions) for c in ["心梗", "mi"]) and "recent" in " ".join(conditions):
        euroscore += 2

    risk = "low" if euroscore <= 2 else "moderate" if euroscore <= 5 else "high"
    mortality = {"low": "<2%", "moderate": "2-5%", "high": ">5%"}[risk]

    return {
        "patient_id": patient_id, "euroscore": euroscore,
        "risk_level": risk, "estimated_mortality": mortality,
        "recommendations": (
            ["常规手术评估"] if risk == "low"
            else ["心内科 + 麻醉科联合评估"] if risk == "moderate"
            else ["MDT讨论 + 术前优化 + ICU备床"]
        ),
        "evidence": ["EuroSCORE II (2011)"],
    }


def plan(
    patient_id: str = "", surgery_type: str = "",
    age: int = 60, labs: dict[str, float] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """抗凝方案: 机械瓣 vs 生物瓣 vs CABG。

    参考: ACCP / ACC/AHA
    """
    labs = labs or {}
    st = surgery_type.lower()
    inr_target = "2.0-3.0"
    duration = "3 months"
    drug = "warfarin"

    if "mechanical" in st or "机械瓣" in st:
        inr_target = "2.5-3.5 (主动脉瓣) / 3.0-4.0 (二尖瓣)"
        duration = "lifetime"
        drug = "warfarin"
    elif "bioprosthetic" in st or "生物瓣" in st:
        duration = "3-6 months"
        drug = "warfarin" if any(k in st for k in ["mitral", "二尖瓣"]) else "aspirin"
    elif "cabg" in st or "搭桥" in st:
        drug = "aspirin + clopidogrel (DAPT 12 months)"
        duration = "12 months"
        inr_target = "N/A"

    return {
        "patient_id": patient_id, "anticoagulation": drug,
        "inr_target": inr_target, "duration": duration,
        "bridge": "LMWH" if drug == "warfarin" else "N/A",
        "monitoring": ["INR weekly → monthly"] if drug == "warfarin" else ["platelet function"],
    }


def manage(
    patient_id: str = "", procedure: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """术后管理方案。"""
    return {
        "patient_id": patient_id,
        "icu_stay": "24-48h",
        "monitoring": ["ECG连续", "CVP q1h", "胸引量 q1h", "尿量 q1h"],
        "medications": [
            "β-blocker (术前续用)", "statin (术前续用)",
            "anticoagulation (12-24h 后启动, 确认无活动性出血)",
            "PPI (应激性溃疡预防)", "insulin sliding scale (血糖 6-10 mmol/L)",
        ],
        "complication_watch": {
            "tamponade": "心包填塞 (Beck三联征) — 紧急超声 + 心包穿刺",
            "bleeding": "术后 6h > 500ml — 探查",
            "afib": "术后房颤 (20-40%) — 控制心率 + 抗凝",
            "mi": "围术期心梗 — ECG + 心肌酶 + 心内科会诊",
        },
    }
