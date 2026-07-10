"""Role-based perspective system — 8 clinical role views with shared lab extraction.

Each role defines a unique perspective on patient data.
All lab extraction, range checking, and float conversion is centralized
in _LabContext to eliminate 8 copies of identical boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoleDef:
    id: str
    name: str
    short_name: str
    description: str
    focus_areas: list[str] = field(default_factory=list)
    icon: str = ""


ROLES: dict[str, RoleDef] = {
    "anesthesiologist": RoleDef(
        id="anesthesiologist", name="麻醉科医生", short_name="麻醉",
        description="围术期麻醉管理：气道评估、ASA分级、抗凝管理、容量状态、疼痛控制",
        focus_areas=["气道评估 (Mallampati)", "ASA分级", "心血管风险 (RCRI)", "抗凝桥接", "凝血功能", "疼痛管理", "药物过敏", "困难气道预案"],
        icon="💉",
    ),
    "attending": RoleDef(
        id="attending", name="主治医生", short_name="主治",
        description="整体诊疗决策：诊断确认、治疗方案、手术指征、预后评估、随访",
        focus_areas=["诊断确认", "手术指征评估", "保守方案评估", "手术时机", "并发症风险评估", "MDT需求判断", "康复计划", "随访计划", "药物治疗方案", "知情同意"],
        icon="🩺",
    ),
    "pharmacist": RoleDef(
        id="pharmacist", name="药剂师", short_name="药师",
        description="通用评估 + 药品查询 + 药品调剂",
        focus_areas=["患者信息采集", "药品信息查询", "药品调剂管理", "TPN配置流程", "实验室阈值查询"],
        icon="💊",
    ),
    "clinical_pharmacist": RoleDef(
        id="clinical_pharmacist", name="临床药师", short_name="临床药师",
        description="营养评估 + TPN处方计算 + 风险规则引擎",
        focus_areas=["NRS2002营养评估", "54条风险规则", "TPN配比计算", "疾病特异性方案", "离子摩尔量换算"],
        icon="🔬",
    ),
    "review_pharmacist": RoleDef(
        id="review_pharmacist", name="审方药师", short_name="审方",
        description="处方审核 + 配伍检查 + 3级风险判定",
        focus_areas=["处方点评审核", "配伍禁忌检查", "54条风险规则核查", "离子浓度复核", "药物相互作用核查"],
        icon="✅",
    ),
    "iv_compounding_pharmacist": RoleDef(
        id="iv_compounding_pharmacist", name="静脉配置药师", short_name="静配药师",
        description="TPN配方设计 + 渗透压计算 + 配液操作规范",
        focus_areas=["TPN配方设计", "离子摩尔量换算", "渗透压计算", "8步全合一配制", "制剂稳定性评估"],
        icon="🧪",
    ),
    "dietitian": RoleDef(
        id="dietitian", name="营养师", short_name="营养师",
        description="营养筛查 + EN/PN决策 + 结构化评估报告",
        focus_areas=["NRS2002/MUST/MNA-SF", "再喂养风险评估", "EN/PN/SPN途径决策", "营养会诊建议", "评估报告生成"],
        icon="🥗",
    ),
    "head_nurse": RoleDef(
        id="head_nurse", name="护士长", short_name="护士长",
        description="围术期护理管理：DVT预防、体位管理、压疮预防、疼痛护理、出院指导",
        focus_areas=["围术期护理方案", "DVT预防(IPC/GCS)", "体位管理", "Braden压疮风险", "疼痛护理(VAS)", "跌倒风险评估", "术前护理", "术后护理", "出院指导", "急救演练"],
        icon="👩‍⚕️",
    ),
}


# ── Shared Lab Context — eliminates 8 copies of lab extraction boilerplate ──

class _LabContext:
    """Centralized lab data extraction and range checking.
    
    Usage:
        lc = _LabContext(patient_dict)
        glucose = lc.get_float("葡萄糖")
        issues = lc.check_electrolytes(["钾离子", "钠离子", "总钙"])
        result = lc.check_range("凝血酶原时间")
    """

    def __init__(self, patient_dict: dict):
        raw = patient_dict.get("lab_tests", patient_dict.get("lab_results", []))
        if isinstance(raw, dict):
            # lab_results format: {"Hb": 110, "WBC": 8.0, ...}
            items = [{"name": k, "value": v} for k, v in raw.items()]
        elif isinstance(raw, list):
            items = raw
        else:
            items = []
        self._map = {t.get("name", ""): t for t in items if isinstance(t, dict)}
        self._all = items

    def get(self, name: str) -> dict | None:
        return self._map.get(name)

    def get_float(self, name: str) -> float | None:
        t = self._map.get(name)
        if t is None:
            return None
        try:
            return float(t.get("value", 0) or 0)
        except (ValueError, TypeError):
            return None

    def check_range(self, name: str) -> dict | None:
        """Check if a lab value is within WS/T 404 reference range."""
        t = self._map.get(name)
        if t is None:
            return None
        return check_range(name, t.get("value"))

    def check_electrolytes(self, names: list[str]) -> list[dict]:
        issues: list[dict] = []
        for name in names:
            r = self.check_range(name)
            if r and r.get("abnormal"):
                t = self._map.get(name, {})
                issues.append({"name": name, "value": t.get("value"), "unit": t.get("unit", ""), "direction": r.get("direction", "")})
        return issues


# ── WS/T 404 Reference Ranges ──

STANDARD_RANGES: dict[str, dict] = {
    "血红蛋白测定": {"low": 110, "high": 160, "unit": "g/L"},
    "白细胞计数": {"low": 3.5, "high": 9.5, "unit": "x10^9/L"},
    "血小板计数": {"low": 100, "high": 300, "unit": "x10^9/L"},
    "钾离子": {"low": 3.5, "high": 5.3, "unit": "mmol/L"},
    "钠离子": {"low": 135, "high": 145, "unit": "mmol/L"},
    "总钙": {"low": 2.11, "high": 2.52, "unit": "mmol/L"},
    "镁离子": {"low": 0.75, "high": 1.02, "unit": "mmol/L"},
    "磷离子": {"low": 0.85, "high": 1.51, "unit": "mmol/L"},
    "氯离子": {"low": 99, "high": 110, "unit": "mmol/L"},
    "白蛋白": {"low": 35, "high": 55, "unit": "g/L"},
    "凝血酶原时间": {"low": 10, "high": 14, "unit": "秒"},
    "葡萄糖": {"low": 3.9, "high": 6.1, "unit": "mmol/L"},
    "C反应蛋白": {"low": 0, "high": 6.0, "unit": "mg/L"},
}


def check_range(test_name: str, value: Any) -> dict:
    if value is None:
        return {"abnormal": False, "direction": ""}
    ref = STANDARD_RANGES.get(test_name)
    if not ref:
        return {"abnormal": False, "direction": ""}
    try:
        val = float(value)
        low = ref.get("low")
        high = ref.get("high")
        direction = "偏低" if low is not None and val < low else "偏高" if high is not None and val > high else ""
        return {"abnormal": bool(direction), "direction": direction}
    except (ValueError, TypeError):
        return {"abnormal": False, "direction": ""}


# ── Role-Specific Patient Views (refactored with _LabContext) ──

def view_patient_as_anesthesiologist(patient_dict: dict) -> dict:
    lc = _LabContext(patient_dict)
    past = str(patient_dict.get("past_history", ""))
    physical = str(patient_dict.get("physical_exam", ""))

    airway_hints: list[str] = []
    if any(kw in physical for kw in ["颈短", "小下颌", "张口受限", "Mallampati"]):
        airway_hints.append("困难气道相关体征")
    if "颈椎" in physical and any(k in physical for k in ["融合", "固定", "手术"]):
        airway_hints.append("颈椎手术史，考虑清醒插管")
    if "肥胖" in past:
        airway_hints.append("肥胖(BMI≥30)，OSA高风险")

    # RCRI score from history keywords
    has_ihd = any(kw in past for kw in ["冠心病", "冠脉", "心梗"])
    has_chf = any(kw in past for kw in ["心力衰竭", "心衰"])
    has_ckd = any(kw in past for kw in ["肾功能不全", "慢性肾病"])
    has_dm = any(kw in past for kw in ["糖尿病"])
    has_cva = any(kw in past for kw in ["脑梗", "脑出血", "卒中", "TIA"])
    rcri = sum([has_ihd, has_chf, has_ckd, has_dm, has_cva])
    rcri_risk = "低危" if rcri == 0 else "中危" if rcri == 1 else "高危"

    pt_value = lc.get_float("凝血酶原时间")
    hb_value = None
    for test in lc._all:
        if test.get("name") == "血红蛋白测定":
            hb_value = lc.get_float("血红蛋白测定")
            break

    coag_issues = []
    r = lc.check_range("凝血酶原时间")
    if r and r["abnormal"]:
        coag_issues.append(f"凝血酶原时间异常: {r['direction']}")

    anticoagulants = [m for m in ["华法林", "阿司匹林", "氯吡格雷"] if m in past]

    return {
        "role_id": "anesthesiologist", "role_name": "麻醉科医生",
        "airway": {"hints": airway_hints, "needs_eval": len(airway_hints) > 0},
        "cardiac_risk": {"rcri_score": rcri, "rcri_risk": rcri_risk, "has_ihd": has_ihd, "has_chf": has_chf},
        "coagulation": {"issues": coag_issues, "pt_value": pt_value,
                         "on_anticoagulants": len(anticoagulants) > 0, "anticoagulants": anticoagulants},
        "electrolytes": {"issues": lc.check_electrolytes(["钾离子", "钠离子", "总钙"])},
        "anemia": {"hb_value": hb_value, "severity": "重度" if (hb_value or 0) < 80 else "轻度" if (hb_value or 0) < 100 else "正常"},
        "pain": {"vas_preop": patient_dict.get("vas_preop"), "vas_postop": patient_dict.get("vas_postop")},
        "allergies": patient_dict.get("allergy_history", "未提及"),
    }


def view_patient_as_attending(patient_dict: dict) -> dict:
    diagnosis = patient_dict.get("diagnosis", "")
    age = patient_dict.get("age")
    past = str(patient_dict.get("past_history", ""))

    surgical_indicators = []
    if any(k in diagnosis for k in ["髋部骨折", "股骨颈骨折", "转子间骨折"]):
        surgical_indicators.append("髋部骨折 — 指南推荐手术")
    if age and age >= 65:
        surgical_indicators.append("高龄 — 早期手术降低并发症")

    comorbidities = []
    for name, pattern in [("高血压", "高血压"), ("糖尿病", "糖尿病"),
                           ("冠心病", "冠脉"), ("脑血管病", "脑梗"),
                           ("肾脏疾病", "肾病")]:
        if pattern in past:
            comorbidities.append({"name": name, "value": "有"})

    return {
        "role_id": "attending", "role_name": "主治医生",
        "diagnosis": diagnosis, "age": age,
        "surgical_assessment": {"surgical_indicators": surgical_indicators},
        "comorbidities": comorbidities,
        "guidelines": ["NICE NG37 (2023)", "AAOS Management of hip fractures (2022)"],
    }


def view_patient_as_pharmacist(patient_dict: dict) -> dict:
    lc = _LabContext(patient_dict)
    nutrition = patient_dict.get("nutrition_assessment", {})
    return {
        "role_id": "pharmacist", "role_name": "药剂师",
        "patient": {"age": patient_dict.get("age"), "gender": patient_dict.get("gender")},
        "nutrition": {"nrs2002": nutrition.get("nrs2002_score"), "risk": nutrition.get("risk_level")},
        "electrolytes": lc.check_electrolytes(["钾离子", "钠离子", "总钙", "镁离子", "磷离子"]),
        "glucose": lc.get_float("葡萄糖"), "albumin": lc.get_float("白蛋白"),
        "diagnosis": patient_dict.get("diagnosis", ""),
    }


def view_patient_as_clinical_pharmacist(patient_dict: dict) -> dict:
    lc = _LabContext(patient_dict)
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")
    bmi = round(float(weight) / ((float(height) / 100) ** 2), 1) if weight and height else None
    protein = max(1.2, 1.5 if (patient_dict.get("age") or 0) >= 65 else 0)
    return {
        "role_id": "clinical_pharmacist", "role_name": "临床药师",
        "patient": {"age": patient_dict.get("age"), "bmi": bmi, "weight": weight},
        "electrolytes": lc.check_electrolytes(["钾离子", "钠离子", "总钙", "镁离子", "磷离子"]),
        "glucose": lc.get_float("葡萄糖"), "triglyceride": lc.get_float("甘油三酯"),
        "tpn_params": {"energy_kcal_per_kg": 25, "protein_g_per_kg": protein},
    }


def view_patient_as_review_pharmacist(patient_dict: dict) -> dict:
    lc = _LabContext(patient_dict)
    glucose = lc.get_float("葡萄糖")
    warnings, alerts = [], []
    if glucose and glucose > 10:
        alerts.append({"level": "警告", "detail": f"高血糖({glucose})"})
    ca = lc.get_float("总钙")
    p = lc.get_float("磷离子")
    ca_p = round(ca * p, 1) if ca and p else None
    if ca_p and ca_p > 50:
        alerts.append({"level": "禁止", "detail": f"钙磷乘积{ca_p}>50"})
    return {
        "role_id": "review_pharmacist", "role_name": "审方药师",
        "ca_p_product": ca_p, "alerts": alerts, "warnings": warnings,
        "diagnosis": patient_dict.get("diagnosis", ""),
    }


def view_patient_as_iv_compounding_pharmacist(patient_dict: dict) -> dict:
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")
    bmi = round(float(weight) / ((float(height) / 100) ** 2), 1) if weight and height else None
    ideal_weight = height - 105 if height else None
    return {
        "role_id": "iv_compounding_pharmacist", "role_name": "静脉配置药师",
        "patient": {"weight_kg": weight, "bmi": bmi, "ideal_weight_kg": ideal_weight},
        "compounding": {"steps": ["加电解质", "加微量元素", "三合一混合", "排气贴签"], "storage": "避光24h"},
        "osmolarity": ["渗透压≤900—外周可用"] if weight else [],
    }


def view_patient_as_dietitian(patient_dict: dict) -> dict:
    lc = _LabContext(patient_dict)
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")
    age = patient_dict.get("age")
    bmi = round(float(weight) / ((float(height) / 100) ** 2), 1) if weight and height else None
    nutrition = patient_dict.get("nutrition_assessment", {})

    route = "EN（肠内营养）"
    if any(k in str(patient_dict.get("diagnosis", "")) for k in ["梗阻", "穿孔", "瘘"]):
        route = "PN（肠外营养）"

    refeeding = "低风险"
    if bmi and bmi < 16:
        refeeding = "高风险(1/4起始，补充B1)"

    return {
        "role_id": "dietitian", "role_name": "营养师",
        "patient": {"age": age, "bmi": bmi},
        "screening": {"nrs2002": nutrition.get("nrs2002_score"), "risk": nutrition.get("risk_level")},
        "route": {"recommendation": route, "refeeding_risk": refeeding},
        "albumin": lc.get_float("白蛋白"), "crp": lc.get_float("C反应蛋白"),
    }


def view_patient_as_head_nurse(patient_dict: dict) -> dict:
    age = patient_dict.get("age")
    past = str(patient_dict.get("past_history", ""))
    diagnosis = patient_dict.get("diagnosis", "")

    braden_score = None
    for t in patient_dict.get("lab_tests", []):
        if "braden" in str(t.get("name", "")).lower():
            braden_score = t.get("value")
            break

    dvt_risk = "高风险" if any(k in past for k in ["高龄", "卧床", "骨折", "DVT", "手术"]) else "中风险"
    fall_risk = "高风险" if (age or 0) >= 75 or any(k in past for k in ["跌倒", "眩晕", "帕金森"]) else "低风险"

    return {
        "role_id": "head_nurse", "role_name": "护士长",
        "baseline": {"age": age, "diagnosis": diagnosis},
        "dvt": {"risk": dvt_risk, "methods": ["IPC", "GCS", "踝泵"]},
        "pressure_ulcer": {"braden_score": braden_score,
                           "risk": "高风险" if (braden_score or 99) <= 12 else "中风险" if (braden_score or 99) <= 15 else "低风险"},
        "pain": {"vas_preop": patient_dict.get("vas_preop"), "vas_postop": patient_dict.get("vas_postop")},
        "fall_risk": {"level": fall_risk, "prevention": ["床栏", "呼叫器", "防滑鞋"]},
        "nursing_plan": {"stages": [
            {"stage": "术前", "items": ["健康教育", "皮肤准备"]},
            {"stage": "术后当日", "items": ["生命体征q1h", "体位管理", "DVT预防"]},
            {"stage": "术后1-3天", "items": ["饮食护理", "管道护理"]},
            {"stage": "出院", "items": ["离床活动", "出院指导"]},
        ]},
    }


# ── Public API ──

def list_roles() -> dict[str, RoleDef]:
    return dict(ROLES)


def get_role(role_id: str) -> RoleDef | None:
    return ROLES.get(role_id)


def view_patient_as_role(role_id: str, patient_dict: dict) -> dict | None:
    dispatch = {
        "anesthesiologist": view_patient_as_anesthesiologist,
        "attending": view_patient_as_attending,
        "pharmacist": view_patient_as_pharmacist,
        "clinical_pharmacist": view_patient_as_clinical_pharmacist,
        "review_pharmacist": view_patient_as_review_pharmacist,
        "iv_compounding_pharmacist": view_patient_as_iv_compounding_pharmacist,
        "dietitian": view_patient_as_dietitian,
        "head_nurse": view_patient_as_head_nurse,
    }
    fn = dispatch.get(role_id)
    return fn(patient_dict) if fn else None
