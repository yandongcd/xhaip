"""Role-based perspective system — multi-role patient data views.

Each role defines a unique perspective on patient data:
- 麻醉科医生: Airway / ASA / Cardiac / Anticoagulation / Volume / Pain / Coagulation / Allergy
- 主治医生: Diagnosis / Treatment plan / Surgical indications / Conservative vs Surgery / Prognosis / Follow-up
- 药剂师: General assessment / Drug lookup / Drug dispensing (user entry point)
- 临床药师: Nutrition assessment / Prescription parameter calculation / Plan formulation
- 审方药师: Prescription review / Compatibility check / Risk alert
- 静脉配置药师: TPN formula design / Preparation selection / Compounding process
- 营养师: Nutrition screening / Nutrition consultation / Report generation
- 护士长: Perioperative nursing / DVT prevention / Positioning / Pressure ulcer / Pain / Discharge guidance

Key functions:
  - list_roles()         — return all role definitions
  - get_role(role_id)    — get a single role definition
  - view_patient_as_role(role_id, patient_dict) — dispatch to role-specific view

Port from haip-0705-2: ``src/agents/domains/togaf/core/roles.py``
Adapted for xhaip v1.0 — self-contained, no A2A dispatcher dependency,
no external knowledge import (hardcoded WS/T 404 reference ranges).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ═══════════════════════════════════════════════════════════
# RoleDef — clinical role perspective (simpler than org RoleDef)
# ═══════════════════════════════════════════════════════════

@dataclass
class RoleDef:
    """A clinical role defined by its perspective on patient data."""

    id: str
    name: str
    short_name: str
    description: str
    focus_areas: list[str] = field(default_factory=list)
    icon: str = ""


# ═══════════════════════════════════════════════════════════
# 8 Clinical Role Definitions
# ═══════════════════════════════════════════════════════════

ROLES: dict[str, RoleDef] = {
    "anesthesiologist": RoleDef(
        id="anesthesiologist",
        name="麻醉科医生",
        short_name="麻醉",
        description="专注于围术期麻醉管理：气道评估、ASA分级、心脏风险、抗凝管理、容量状态、疼痛控制、凝血功能、药物过敏",
        focus_areas=[
            "气道评估 (Mallampati分级、颈椎活动度)",
            "ASA分级与围术期风险",
            "心血管风险评估 (RCRI、心脏超声、心肌酶)",
            "抗凝药物管理与桥接方案",
            "容量状态与液体管理",
            "凝血功能与出血风险评估",
            "疼痛管理 (VAS评分、镇痛方案)",
            "药物过敏史与麻醉药物选择",
            "术后恶心呕吐 (PONV) 风险评估",
            "困难气道预案",
        ],
        icon="💉",
    ),
    "attending": RoleDef(
        id="attending",
        name="主治医生",
        short_name="主治",
        description="专注于整体诊疗决策：诊断确认、治疗方案选择、手术vs保守治疗、预后评估、康复计划、长期随访",
        focus_areas=[
            "诊断确认与鉴别诊断",
            "手术指征评估 (绝对/相对/禁忌)",
            "保守治疗方案评估",
            "手术时机选择 (急诊/限期/择期)",
            "围术期并发症风险评估",
            "多学科会诊 (MDT) 需求判断",
            "康复计划与功能恢复预测",
            "术后随访计划",
            "长期药物治疗方案",
            "患者教育与知情同意要点",
        ],
        icon="🩺",
    ),
    "pharmacist": RoleDef(
        id="pharmacist",
        name="药剂师",
        short_name="药师",
        description="通用评估 + 药品查询 + 药品调剂（用户入口角色）：患者信息采集、药品信息查询与对比、药品调剂与发药管理",
        focus_areas=[
            "患者信息采集与通用评估",
            "药品信息查询与肠内营养产品对比",
            "药品调剂与发药管理",
            "TPN配置顺序标准流程查询",
            "实验室指标阈值查询",
        ],
        icon="💊",
    ),
    "clinical_pharmacist": RoleDef(
        id="clinical_pharmacist",
        name="临床药师",
        short_name="临床药师",
        description="营养评估 + 处方参数计算 + 方案制定：营养风险综合评估、TPN处方配比计算、54条风险规则引擎、疾病特异性方案制定",
        focus_areas=[
            "营养风险综合评估 (NRS2002/再喂养/电解质/糖脂/肝功)",
            "54条风险规则引擎",
            "TPN处方配比计算 (能量/蛋白质/渗透压/阳离子)",
            "疾病特异性方案调整 (肝/肾/ICU/老年/肥胖/肿瘤)",
            "药品→离子摩尔量换算",
        ],
        icon="🔬",
    ),
    "review_pharmacist": RoleDef(
        id="review_pharmacist",
        name="审方药师",
        short_name="审方",
        description="处方审核 + 配伍检查 + 风险预警：处方点评与审核、药物配伍禁忌检查、3级风险判定（提示/警告/禁止）",
        focus_areas=[
            "处方点评与审核 (适应症/用量/配伍/渗透压评分)",
            "药物配伍禁忌检查 (钙磷/脂肪乳/阳离子/药物相互作用)",
            "54条风险规则完整核查与3级判定",
            "药品→离子摩尔量换算与阳离子浓度复核",
            "营养液-常用药物相互作用核查",
        ],
        icon="✅",
    ),
    "iv_compounding_pharmacist": RoleDef(
        id="iv_compounding_pharmacist",
        name="静脉配置药师",
        short_name="静配药师",
        description="TPN配方设计 + 制剂选择 + 配置流程：药品选择与用量计算、渗透压/阳离子浓度计算、配液操作规范管理",
        focus_areas=[
            "TPN配方设计 (药品选择与用量)",
            "药品→离子摩尔量换算",
            "渗透压/阳离子浓度/钙磷乘积计算",
            "配液操作流程 (8步全合一配制规范)",
            "制剂稳定性评估 (避光/破乳/沉淀检查)",
        ],
        icon="🧪",
    ),
    "dietitian": RoleDef(
        id="dietitian",
        name="营养师",
        short_name="营养师",
        description="营养筛查 + 营养会诊建议 + 报告生成：多工具营养风险筛查（NRS2002/MUST/MNA-SF）、EN/PN途径决策、结构化营养评估报告",
        focus_areas=[
            "营养风险筛查 (NRS2002/MUST/MNA-SF三工具选择)",
            "再喂养综合征风险评估",
            "EN/PN/SPN途径决策 (完整适应证/禁忌证)",
            "营养会诊建议 (能量/蛋白质/制剂/监测计划)",
            "结构化营养评估报告生成",
        ],
        icon="🥗",
    ),
    "head_nurse": RoleDef(
        id="head_nurse",
        name="护士长",
        short_name="护士长",
        description="专注于围术期护理管理：围术期护理方案制定、DVT预防、体位管理、压疮预防、疼痛护理、出院指导",
        focus_areas=[
            "围术期护理方案 (4阶段21项)",
            "DVT物理预防 (IPC/GCS/踝泵)",
            "体位管理 (15-30°外展位)",
            "Braden压疮风险评估",
            "疼痛护理 (VAS评估q4h)",
            "术前护理 (宣教/皮肤/禁食)",
            "术后当日护理 (生命体征q1h)",
            "术后早期护理 (饮食/管道/锻炼)",
            "出院指导 (家庭护理/心理评估)",
            "跌倒风险评估与预防",
        ],
        icon="👩‍⚕️",
    ),
}


def list_roles() -> dict[str, RoleDef]:
    """Return all clinical role definitions."""
    return dict(ROLES)


def get_role(role_id: str) -> RoleDef | None:
    """Get a single clinical role by its id."""
    return ROLES.get(role_id)


# ═══════════════════════════════════════════════════════════
# WS/T 404 Reference Ranges (hardcoded — no external import)
# ═══════════════════════════════════════════════════════════
# Sources: WS/T 404.1-2018 through WS/T 404.9-2018

STANDARD_RANGES: dict[str, dict[str, Any]] = {
    # Electrolytes (WS/T 404.3-2012)
    "钾离子":   {"low": 3.5, "high": 5.3, "unit": "mmol/L"},
    "钠离子":   {"low": 137, "high": 147, "unit": "mmol/L"},
    "氯离子":   {"low": 99, "high": 110, "unit": "mmol/L"},
    "总钙":     {"low": 2.1, "high": 2.6, "unit": "mmol/L"},
    "无机磷":   {"low": 0.85, "high": 1.51, "unit": "mmol/L"},
    "镁离子":   {"low": 0.75, "high": 1.02, "unit": "mmol/L"},
    "磷离子":   {"low": 0.85, "high": 1.51, "unit": "mmol/L"},

    # Renal (WS/T 404.5-2015)
    "尿素":     {"low": 3.1, "high": 8.0, "unit": "mmol/L"},
    "肌酐":     {"low": 44, "high": 104, "unit": "μmol/L"},
    "尿酸":     {"low": 150, "high": 420, "unit": "μmol/L"},

    # Hepatic (WS/T 404.1-2012, 404.2-2012, 404.4-2018)
    "丙氨酸氨基转移酶":   {"low": None, "high": 40, "unit": "U/L"},
    "天门冬氨酸氨基转移酶": {"low": None, "high": 35, "unit": "U/L"},
    "总蛋白":   {"low": 65, "high": 85, "unit": "g/L"},
    "白蛋白":   {"low": 40, "high": 55, "unit": "g/L"},
    "总胆红素": {"low": None, "high": 21, "unit": "μmol/L"},

    # Cardiac (WS/T 404.7-2015)
    "乳酸脱氢酶": {"low": 120, "high": 250, "unit": "U/L"},
    "肌酸激酶":   {"low": 30, "high": 200, "unit": "U/L"},

    # Metabolic
    "葡萄糖":     {"low": 3.9, "high": 6.1, "unit": "mmol/L"},
    "甘油三酯":   {"low": None, "high": 1.7, "unit": "mmol/L"},
    "总胆固醇":   {"low": None, "high": 5.2, "unit": "mmol/L"},

    # Inflammation (WS/T 404.9-2018)
    "C反应蛋白":  {"low": 0, "high": 6.0, "unit": "mg/L"},
}


def check_range(name: str, value: float | str | None) -> dict[str, Any]:
    """Check if a lab test value falls within WS/T 404 reference range.

    Returns: {"abnormal": bool, "direction": str, "range": dict|None, "message": str}
    """
    result: dict[str, Any] = {"abnormal": False, "direction": "", "range": None, "message": ""}

    if value is None or value == "":
        return result

    if isinstance(value, str):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return result

    key: str | None = None
    for rk in STANDARD_RANGES:
        if rk == name or rk in name or name in rk:
            key = rk
            break

    if key is None:
        return result

    r = STANDARD_RANGES[key]
    result["range"] = r

    if r["low"] is not None and value < r["low"]:
        result["abnormal"] = True
        result["direction"] = "↓"
        result["message"] = f"低于正常值 ({r['low']} {r['unit']})"
    elif r["high"] is not None and value > r["high"]:
        result["abnormal"] = True
        result["direction"] = "↑"
        result["message"] = f"高于正常值 (≤{r['high']} {r['unit']})"
    else:
        result["message"] = "正常"

    return result


# ═══════════════════════════════════════════════════════════
# Role-specific patient data views
# ═══════════════════════════════════════════════════════════

def view_patient_as_anesthesiologist(patient_dict: dict) -> dict:
    """麻醉科医生视角 — 提取围术期麻醉相关数据."""
    lab_tests = patient_dict.get("lab_tests", [])
    lab_map = {t.get("name", ""): t for t in lab_tests}
    past = patient_dict.get("past_history", "")
    physical = patient_dict.get("physical_exam", "")
    vas_preop = patient_dict.get("vas_preop")
    vas_postop = patient_dict.get("vas_postop")

    # Airway assessment hints
    airway_hints: list[str] = []
    if any(kw in physical for kw in ["颈短", "小下颌", "张口受限", "Mallampati"]):
        airway_hints.append("存在困难气道相关体征，需详细气道评估")
    if "颈椎" in physical and any(k in physical for k in ["融合", "固定", "手术"]):
        airway_hints.append("颈椎手术史/融合，需考虑清醒插管或视频喉镜")
    if "肥胖" in past:
        airway_hints.append("肥胖（BMI≥30），OSA高风险，需评估气道")

    # Cardiac risk — NOTE: replaces A2A dispatch (cardio-risk agent call)
    # In xhaip, the cardio-risk assessment should be called externally via A2A dispatcher.
    cardiac_risks: list[str] = []

    past_text = str(past)
    has_ihd = any(kw in past_text for kw in ["冠心病", "冠脉", "心梗", "心肌梗死"])
    has_chf = any(kw in past_text for kw in ["心力衰竭", "心衰"])
    has_ckd = any(kw in past_text for kw in ["肾功能不全", "慢性肾病"])
    has_dm = any(kw in past_text for kw in ["糖尿病"])
    has_cva = any(kw in past_text for kw in ["脑梗", "脑出血", "卒中", "TIA"])
    rcri_score = sum([has_ihd, has_chf, has_ckd, has_dm, has_cva])
    rcri_risk = "低危 (<1%)" if rcri_score == 0 else "中危 (2.1-10.1%)" if rcri_score == 1 else "高危 (>10.1%)"

    # Coagulation
    coagulation_issues: list[str] = []
    pt_value = None
    if "凝血酶原时间" in lab_map:
        t = lab_map["凝血酶原时间"]
        result = check_range("凝血酶原时间", t.get("value"))
        if result["abnormal"]:
            coagulation_issues.append(
                f"凝血酶原时间: {t['value']} {t.get('unit','')} {result['direction']}"
            )
        try:
            pt_value = float(lab_map["凝血酶原时间"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    # Hemoglobin
    hb_value = None
    for test in lab_tests:
        if test.get("name") == "血红蛋白测定":
            try:
                hb_value = float(test.get("value", 0) or 0)
            except (ValueError, TypeError):
                pass

    # Anticoagulants
    anticoagulants: list[str] = []
    if "华法林" in past_text or "warfarin" in past_text.lower():
        anticoagulants.append("华法林")
    if "阿司匹林" in past_text:
        anticoagulants.append("阿司匹林")
    if "氯吡格雷" in past_text:
        anticoagulants.append("氯吡格雷")

    # Allergies
    allergies = patient_dict.get("allergy_history", "")

    # Electrolytes
    electrolyte_issues: list[str] = []
    for name in ["钾离子", "钠离子", "总钙"]:
        if name in lab_map:
            t = lab_map[name]
            result = check_range(name, t.get("value"))
            if result["abnormal"]:
                electrolyte_issues.append(
                    f"{name}: {t['value']} {t.get('unit','')} {result['direction']}"
                )

    return {
        "role_id": "anesthesiologist",
        "role_name": "麻醉科医生",
        "airway_assessment": {
            "hints": airway_hints,
            "needs_detailed_evaluation": len(airway_hints) > 0,
        },
        "asa": {"note": "建议通过 A2A 调用 anesthesia-risk 获取完整 ASA 分级"},
        "cardiac_risk": {
            "rcri_score": rcri_score,
            "rcri_risk": rcri_risk,
            "has_ihd": has_ihd,
            "has_chf": has_chf,
            "findings": cardiac_risks,
        },
        "coagulation": {
            "issues": coagulation_issues,
            "pt_value": pt_value,
            "on_anticoagulants": len(anticoagulants) > 0,
            "anticoagulants": anticoagulants,
        },
        "fluid_and_electrolytes": {
            "electrolyte_issues": electrolyte_issues,
            "needs_correction": len(electrolyte_issues) > 0,
        },
        "anemia": {
            "hb_value": hb_value,
            "severity": (
                "正常" if hb_value is None
                else "重度" if hb_value < 80
                else "轻度" if hb_value < 100
                else "正常"
            ),
        },
        "pain_management": {
            "vas_preop": vas_preop,
            "vas_postop": vas_postop,
            "needs_analgesia_plan": (vas_preop or 0) >= 4 or (vas_postop or 0) >= 4,
        },
        "allergies": allergies if allergies else "未提及",
    }


def view_patient_as_attending(patient_dict: dict) -> dict:
    """主治医生视角 — 提取整体诊疗决策相关数据."""
    diagnosis = patient_dict.get("diagnosis", "")
    chief = patient_dict.get("chief_complaint", "")
    age = patient_dict.get("age")
    past = patient_dict.get("past_history", "")
    examinations = patient_dict.get("examinations", [])

    # Surgical vs conservative indicators
    surgical_indicators: list[str] = []
    conservative_indicators: list[str] = []

    if any(kw in diagnosis for kw in ["髋部骨折", "股骨颈骨折", "转子间骨折"]):
        surgical_indicators.append("髋部骨折 — 指南推荐手术治疗（NICE NG37）")
    if any("开放" in d for d in [diagnosis]):
        surgical_indicators.append("开放性骨折 — 需急诊清创内/外固定")
    if age and age >= 65:
        surgical_indicators.append("高龄患者 — 早期手术降低并发症及死亡率")

    if "保守" in diagnosis or "非手术" in diagnosis:
        conservative_indicators.append("诊断/病历提及保守治疗")
    if any(kw in past for kw in ["严重心衰", "近期心梗", "凝血功能障碍"]):
        conservative_indicators.append("存在手术高风险因素，需评估保守治疗可行性")

    # Comorbidity summary
    comorbidities: list[dict[str, str]] = []
    if "高血压" in past:
        comorbidities.append({"name": "高血压", "value": "有"})
    if "糖尿病" in past:
        comorbidities.append({"name": "糖尿病", "value": "有"})
    if any(kw in past for kw in ["冠心病", "冠脉", "心梗"]):
        comorbidities.append({"name": "冠心病", "value": "有"})
    if "卒中" in past or "脑梗" in past:
        comorbidities.append({"name": "脑血管病", "value": "有"})
    if "肾功能" in past or "肾病" in past:
        comorbidities.append({"name": "肾脏疾病", "value": "有"})

    # Time from injury
    time_from_injury = "不详"
    admission_date = patient_dict.get("admission_date", "")
    if admission_date:
        time_from_injury = f"入院日期: {admission_date}"

    # Exam highlights
    exam_highlights: list[str] = []
    for e in examinations:
        name = e.get("name", "")
        result = e.get("result", "")
        if "骨折" in result:
            exam_highlights.append(f"{name}: {result[:120]}")
        elif "异常" in result or any(kw in result for kw in ["血栓", "积液", "占位"]):
            exam_highlights.append(f"{name}: {result[:120]}")

    return {
        "role_id": "attending",
        "role_name": "主治医生",
        "diagnosis": diagnosis,
        "chief_complaint": chief,
        "age": age,
        "surgical_assessment": {
            "surgical_indicators": surgical_indicators,
            "conservative_indicators": conservative_indicators,
            "recommendation": "建议调用 evaluate_timing() 获取完整手术时机评估",
        },
        "comorbidities": comorbidities,
        "time_from_injury": time_from_injury,
        "exam_highlights": exam_highlights,
        "checklist_summary": {
            "note": "分诊评估由各科室 agent 自行调用 generate_checklist()",
        },
        "guidelines": ["NICE NG37 (2023)", "AAOS Management of hip fractures (2022)"],
    }


def view_patient_as_pharmacist(patient_dict: dict) -> dict:
    """药剂师视角 — 提取临床药学相关数据."""
    lab_tests = patient_dict.get("lab_tests", [])
    lab_map = {t.get("name", ""): t for t in lab_tests}
    age = patient_dict.get("age")
    gender = patient_dict.get("gender")
    diagnosis = patient_dict.get("diagnosis", "")

    nutrition = patient_dict.get("nutrition_assessment", {})
    nrs2002_score = nutrition.get("nrs2002_score") or nutrition.get("total")

    electrolyte_issues: list[dict[str, Any]] = []
    for name in ["钾离子", "钠离子", "总钙", "镁离子", "磷离子", "氯离子"]:
        if name in lab_map:
            t = lab_map[name]
            result = check_range(name, t.get("value"))
            if result.get("abnormal"):
                electrolyte_issues.append({
                    "name": name,
                    "value": t.get("value"),
                    "unit": t.get("unit", ""),
                    "direction": result.get("direction", ""),
                })

    glucose = None
    if "葡萄糖" in lab_map:
        try:
            glucose = float(lab_map["葡萄糖"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    triglyceride = None
    if "甘油三酯" in lab_map:
        try:
            triglyceride = float(lab_map["甘油三酯"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    albumin = None
    if "白蛋白" in lab_map:
        try:
            albumin = float(lab_map["白蛋白"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    crp = None
    if "C反应蛋白" in lab_map:
        try:
            crp = float(lab_map["C反应蛋白"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    compatibility_risks: list[str] = []
    if "钙离子" in lab_map and "磷离子" in lab_map:
        try:
            ca = float(lab_map["钙离子"].get("value", 0))
            p = float(lab_map["磷离子"].get("value", 0))
            ca_p_product = ca * p
            if ca_p_product > 50:
                compatibility_risks.append(f"钙磷乘积={ca_p_product:.1f}>50, 磷酸钙沉淀风险")
        except (ValueError, TypeError):
            pass

    return {
        "role_id": "pharmacist",
        "role_name": "药剂师",
        "patient": {"age": age, "gender": gender},
        "nutrition_screening": {
            "nrs2002_score": nrs2002_score,
            "risk_level": nutrition.get("risk_level"),
            "suggestion": nutrition.get("suggestion"),
        },
        "electrolyte_assessment": {
            "issues": electrolyte_issues,
            "needs_correction": len(electrolyte_issues) > 0,
        },
        "metabolic_monitoring": {
            "glucose": glucose,
            "triglyceride": triglyceride,
            "glucose_alert": glucose is not None and glucose > 10,
            "lipid_alert": triglyceride is not None and triglyceride > 5,
        },
        "nutrition_markers": {
            "albumin": albumin,
            "crp": crp,
        },
        "compatibility_risks": compatibility_risks,
        "diagnosis": diagnosis,
        "medication_review_needed": bool(diagnosis),
    }


def view_patient_as_clinical_pharmacist(patient_dict: dict) -> dict:
    """临床药师视角 — 营养评估 + 处方参数计算 + 方案制定."""
    lab_tests = patient_dict.get("lab_tests", [])
    lab_map = {t.get("name", ""): t for t in lab_tests}
    age = patient_dict.get("age")
    gender = patient_dict.get("gender")
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")
    diagnosis = patient_dict.get("diagnosis", "")
    nutrition = patient_dict.get("nutrition_assessment", {})
    nrs2002_score = nutrition.get("nrs2002_score") or nutrition.get("total")

    bmi = None
    if weight and height:
        try:
            bmi = round(float(weight) / ((float(height) / 100) ** 2), 1)
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    energy_per_kg = 25
    protein_per_kg = 1.2
    condition_adjustments: list[str] = []

    if nrs2002_score is not None and nrs2002_score >= 5:
        condition_adjustments.append("高营养风险(NRS≥5)：建议积极营养干预")
    if age is not None and age >= 65:
        condition_adjustments.append("老年(≥65岁)：注意肌少症，目标蛋白1.2-1.5g/kg/d")
        protein_per_kg = max(protein_per_kg, 1.2)
    if bmi is not None and bmi >= 30:
        condition_adjustments.append("肥胖(BMI≥30)：使用理想体重计算，低热量高蛋白方案")
        protein_per_kg = max(protein_per_kg, 2.0)
        energy_per_kg = 22

    electrolyte_issues: list[dict[str, Any]] = []
    for name in ["钾离子", "钠离子", "总钙", "镁离子", "磷离子", "氯离子"]:
        if name in lab_map:
            t = lab_map[name]
            result = check_range(name, t.get("value"))
            if result.get("abnormal"):
                electrolyte_issues.append({
                    "name": name,
                    "value": t.get("value"),
                    "unit": t.get("unit", ""),
                    "direction": result.get("direction", ""),
                })

    glucose = None
    if "葡萄糖" in lab_map:
        try:
            glucose = float(lab_map["葡萄糖"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    triglyceride = None
    if "甘油三酯" in lab_map:
        try:
            triglyceride = float(lab_map["甘油三酯"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    return {
        "role_id": "clinical_pharmacist",
        "role_name": "临床药师",
        "patient": {
            "age": age, "gender": gender,
            "weight_kg": weight, "height_cm": height, "bmi": bmi,
        },
        "nutrition_screening": {
            "nrs2002_score": nrs2002_score,
            "risk_level": nutrition.get("risk_level"),
        },
        "electrolyte_assessment": {
            "issues": electrolyte_issues,
            "needs_correction": len(electrolyte_issues) > 0,
        },
        "metabolic": {
            "glucose": glucose,
            "triglyceride": triglyceride,
            "hyperglycemia_alert": glucose is not None and glucose > 10,
            "hyperlipidemia_alert": triglyceride is not None and triglyceride > 5,
        },
        "tpn_parameters": {
            "energy_kcal_per_kg": energy_per_kg,
            "protein_g_per_kg": protein_per_kg,
        },
        "condition_adjustments": condition_adjustments,
        "diagnosis": diagnosis,
    }


def view_patient_as_review_pharmacist(patient_dict: dict) -> dict:
    """审方药师视角 — 处方审核 + 配伍检查 + 风险预警."""
    lab_tests = patient_dict.get("lab_tests", [])
    lab_map = {t.get("name", ""): t for t in lab_tests}
    diagnosis = patient_dict.get("diagnosis", "")

    warnings: list[dict[str, str]] = []
    alerts: list[dict[str, str]] = []

    glucose = None
    if "葡萄糖" in lab_map:
        try:
            glucose = float(lab_map["葡萄糖"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass
    if glucose is not None:
        if glucose > 15:
            alerts.append({"level": "🔴禁止", "rule": "R002",
                          "detail": "高血糖危急(>15mmol/L)，暂停含糖液体"})
        elif glucose > 10:
            warnings.append({"level": "🟠警告", "rule": "R001",
                            "detail": f"高血糖({glucose}mmol/L)，调整胰岛素方案"})

    for name in ["钾离子", "钠离子"]:
        if name in lab_map:
            t = lab_map[name]
            result = check_range(name, t.get("value"))
            if result.get("abnormal") and result.get("direction") in ("偏低", "偏高"):
                val = t.get("value", "")
                rule_id = "R008" if "钠" in name else "R011"
                warnings.append({"level": "🟠警告", "rule": rule_id,
                                "detail": f"血{name[-1]}异常({val}{t.get('unit','')})"})

    ca_p_product = None
    if "总钙" in lab_map and "磷离子" in lab_map:
        try:
            ca = float(lab_map["总钙"].get("value", 0) or 0)
            p = float(lab_map["磷离子"].get("value", 0) or 0)
            ca_p_product = round(ca * p, 1)
            if ca_p_product > 50:
                alerts.append({"level": "🔴禁止", "rule": "配伍禁忌",
                               "detail": f"钙磷乘积{ca_p_product}>50，磷酸钙沉淀风险，建议分开输注"})
        except (ValueError, TypeError):
            pass

    return {
        "role_id": "review_pharmacist",
        "role_name": "审方药师",
        "compatibility_check": {
            "ca_p_product": ca_p_product,
            "ca_p_safe": ca_p_product is None or ca_p_product < 50,
        },
        "risk_alerts": {
            "🔴禁止": alerts,
            "🟠警告": warnings,
            "🟡提示": [],
            "total_alerts": len(alerts),
            "total_warnings": len(warnings),
        },
        "diagnosis": diagnosis,
        "prescription_review_needed": True,
    }


def view_patient_as_iv_compounding_pharmacist(patient_dict: dict) -> dict:
    """静脉配置药师视角 — TPN配方设计 + 制剂选择 + 配置流程."""
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")

    bmi = None
    ideal_weight = None
    eff_weight = weight
    if weight and height:
        try:
            h_cm = float(height)
            bmi = round(float(weight) / ((h_cm / 100) ** 2), 1)
            ideal_weight = h_cm - 105
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    if bmi is not None and bmi >= 28 and ideal_weight:
        eff_weight = round(ideal_weight + (float(weight) - ideal_weight) * 0.4, 1)

    osm_warnings: list[str] = []
    if weight:
        try:
            w = float(weight)
            glucose_g = round(25 * w * 0.6 / 4, 1)
            aa_g = round(1.2 * w, 1)
            osm = round((glucose_g * 5 + aa_g * 10) / 2.0, 0)
            if osm > 900:
                osm_warnings.append(f"渗透压{osm}mOsm/L>900，建议中心静脉输注")
            else:
                osm_warnings.append(f"渗透压{osm}mOsm/L≤900，外周静脉可用")
        except (ValueError, TypeError):
            pass

    compound_steps = [
        "1. 加电解质入葡萄糖/氨基酸",
        "2. 加磷入另一瓶氨基酸",
        "3. 加微量元素入氨基酸",
        "4. 加水溶维生素入葡萄糖",
        "5. 加脂溶维生素入脂肪乳",
        "6. 三合一混合（糖+AA→最后加脂肪乳）",
        "7. 排气、检查、贴签",
        "8. 充填、封口（避光24h内使用）",
    ]

    return {
        "role_id": "iv_compounding_pharmacist",
        "role_name": "静脉配置药师",
        "patient": {
            "weight_kg": weight, "bmi": bmi,
            "ideal_weight_kg": ideal_weight, "effective_weight_kg": eff_weight,
        },
        "formulation_params": {
            "energy_kcal_per_kg": 25,
            "protein_g_per_kg": 1.2,
            "glucose_fat_ratio": "6:4",
        },
        "osmolarity_check": osm_warnings,
        "compounding": {
            "steps": compound_steps,
            "storage": "避光保存，24小时内使用",
        },
    }


def view_patient_as_dietitian(patient_dict: dict) -> dict:
    """营养师视角 — 营养筛查 + 营养会诊建议 + 报告生成."""
    lab_tests = patient_dict.get("lab_tests", [])
    lab_map = {t.get("name", ""): t for t in lab_tests}
    age = patient_dict.get("age")
    weight = patient_dict.get("weight_kg")
    height = patient_dict.get("height_cm")
    diagnosis = patient_dict.get("diagnosis", "")
    nutrition = patient_dict.get("nutrition_assessment", {})
    nrs2002_score = nutrition.get("nrs2002_score") or nutrition.get("total")

    bmi = None
    if weight and height:
        try:
            bmi = round(float(weight) / ((float(height) / 100) ** 2), 1)
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    screening_tool = "NRS2002"
    if age is not None and age >= 65:
        screening_tool = "MNA-SF（推荐老年人）"

    route_recommendation = "EN（肠内营养）"
    bowel = patient_dict.get("bowel_function", "")
    if "障碍" in bowel or "障碍" in diagnosis:
        route_recommendation = "PN（肠外营养）"

    refeeding_risk = "低风险"
    if bmi is not None and bmi < 16.0:
        refeeding_risk = "高风险(目标量1/4起始，每日监测电解质，补充B1)"
    elif bmi is not None and bmi < 18.5:
        refeeding_risk = "中风险(目标量1/2起始)"

    albumin = None
    if "白蛋白" in lab_map:
        try:
            albumin = float(lab_map["白蛋白"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    crp = None
    if "C反应蛋白" in lab_map:
        try:
            crp = float(lab_map["C反应蛋白"].get("value", 0) or 0)
        except (ValueError, TypeError):
            pass

    monitoring_plan = {
        "daily": ["生命体征", "出入量", "血糖qid", "EN耐受性(GRV/腹胀/排便)"],
        "weekly_2_3": ["电解质(K/Na/Ca/P/Mg)", "血糖", "血脂"],
        "weekly_1": ["肝功能(ALT/AST/TBIL)", "肾功能(BUN/Cr)", "CRP", "PAB/ALB"],
    }

    return {
        "role_id": "dietitian",
        "role_name": "营养师",
        "patient": {"age": age, "bmi": bmi, "diagnosis": diagnosis},
        "screening": {
            "tool": screening_tool,
            "nrs2002_score": nrs2002_score,
            "risk_level": nutrition.get("risk_level"),
        },
        "nutrition_route": {
            "recommendation": route_recommendation,
            "refeeding_risk": refeeding_risk,
        },
        "nutrition_markers": {"albumin": albumin, "crp": crp},
        "monitoring_plan": monitoring_plan,
    }


def view_patient_as_head_nurse(patient_dict: dict) -> dict:
    """护士长视角 — 提取围术期护理相关数据."""
    lab_tests = patient_dict.get("lab_tests", [])
    age = patient_dict.get("age")
    diagnosis = patient_dict.get("diagnosis", "")
    past = patient_dict.get("past_history", "")
    physical = patient_dict.get("physical_exam", "")
    vas_preop = patient_dict.get("vas_preop")
    vas_postop = patient_dict.get("vas_postop")

    braden_score = None
    for test in lab_tests:
        if "braden" in test.get("name", "").lower():
            braden_score = test.get("value")

    dvt_risk = "高风险" if any(kw in past for kw in ["高龄", "卧床", "骨折", "DVT史", "手术"]) else "中风险"

    fall_risk = "高风险" if (age is not None and age >= 75) or any(
        kw in past for kw in ["跌倒史", "眩晕", "帕金森"]
    ) else "低风险"

    nursing_stages = [
        {"stage": "术前",
         "items": ["健康教育", "皮肤准备", "禁食禁水", "排便训练", "心理护理"]},
        {"stage": "术后当日",
         "items": ["生命体征q1h", "体位管理", "切口观察", "VAS评估q4h",
                   "DVT预防(IPC+踝泵)", "Braden压疮预防"]},
        {"stage": "术后1-3天",
         "items": ["饮食护理", "管道护理", "功能锻炼", "便秘预防", "睡眠护理"]},
        {"stage": "术后4天至出院",
         "items": ["离床活动", "跌倒预防", "出院指导", "家庭护理培训", "心理评估"]},
    ]

    return {
        "role_id": "head_nurse",
        "role_name": "护士长",
        "patient_baseline": {
            "age": age,
            "diagnosis": diagnosis,
            "mobility": "卧床" if "卧床" in (physical or "") else "可自主活动",
        },
        "dvt_prevention": {
            "risk_level": dvt_risk,
            "physical_methods": ["间歇充气加压(IPC)", "弹力袜(GCS)", "踝泵运动"],
        },
        "pressure_ulcer": {
            "braden_score": braden_score,
            "risk": (
                "高风险" if (braden_score is not None and braden_score <= 12)
                else "中风险" if (braden_score is not None and braden_score <= 15)
                else "低风险"
            ),
        },
        "pain_nursing": {
            "vas_preop": vas_preop,
            "vas_postop": vas_postop,
            "needs_analgesia": (vas_preop or 0) >= 4 or (vas_postop or 0) >= 4,
        },
        "fall_risk": {
            "level": fall_risk,
            "prevention": ["床栏保护", "呼叫器在侧", "防滑鞋", "协助如厕"],
        },
        "nursing_plan": {"stages": nursing_stages},
    }


# ═══════════════════════════════════════════════════════════
# Dispatcher
# ═══════════════════════════════════════════════════════════

def view_patient_as_role(role_id: str, patient_dict: dict) -> dict | None:
    """Dispatch patient data view to the appropriate role-specific analyzer.

    Args:
        role_id: One of the 8 role IDs (e.g. "anesthesiologist", "attending")
        patient_dict: Patient data dictionary with keys like lab_tests, past_history, etc.

    Returns:
        Role-specific view dict, or None if role_id is unrecognized.
    """
    dispatcher: dict[str, type[view_patient_as_anesthesiologist]] = {
        "anesthesiologist": view_patient_as_anesthesiologist,
        "attending": view_patient_as_attending,
        "pharmacist": view_patient_as_pharmacist,
        "clinical_pharmacist": view_patient_as_clinical_pharmacist,
        "review_pharmacist": view_patient_as_review_pharmacist,
        "iv_compounding_pharmacist": view_patient_as_iv_compounding_pharmacist,
        "dietitian": view_patient_as_dietitian,
        "head_nurse": view_patient_as_head_nurse,
    }
    func = dispatcher.get(role_id)
    if func is None:
        return None
    return func(patient_dict)
