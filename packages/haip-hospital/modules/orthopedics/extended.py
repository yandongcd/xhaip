"""骨科 — 质控审计 + 术前检查清单 + 检查完备性 + 康复跟踪 + 骨质疏松 + 并发症预测 + 风险告警 + 护理方案 + 麻醉评估.

v1.1 — Extended with full clinical pipeline from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

import re
from typing import Any

# ══════════════════════════════════════════════════════════════════════
# 并发症预测 (complication_predictor)
# ══════════════════════════════════════════════════════════════════════

COMPLICATION_DIMENSIONS = {
    "dvt": {
        "id": "dvt", "label": "DVT/PE 风险",
        "score_items": [
            {"id": "dvt_age", "condition": "age >= 60", "score": 1},
            {"id": "dvt_obesity", "condition": "bmi >= 30", "score": 1},
            {"id": "dvt_immobile", "condition": "past_history contains '卧床'", "score": 2},
            {"id": "dvt_immobile2", "condition": "past_history contains '制动'", "score": 2},
            {"id": "dvt_vte_history", "condition": "past_history contains '血栓'", "score": 3},
            {"id": "dvt_vte_history2", "condition": "past_history contains 'DVT'", "score": 3},
            {"id": "dvt_ddimer", "condition": "lab.d_dimer >= 0.5", "score": 2},
            {"id": "dvt_ddimer_high", "condition": "lab.d_dimer >= 2.0", "score": 4},
            {"id": "dvt_surgery", "condition": "diagnosis contains '骨折'", "score": 1},
        ],
        "risk_levels": [
            {"min_score": 5, "level": "高危", "action": "药物预防(低分子肝素)+物理预防(IPC+GCS)，术前即启动，术后延长至35天"},
            {"min_score": 3, "level": "中危", "action": "物理预防(IPC+GCS)，必要时低分子肝素，术后持续至下床活动"},
            {"min_score": 0, "level": "低危", "action": "基础预防：踝泵运动+早期下床活动"},
        ],
    },
    "infection": {
        "id": "infection", "label": "感染风险",
        "score_items": [
            {"id": "inf_dm", "condition": "past_history contains '糖尿病'", "score": 2},
            {"id": "inf_obesity", "condition": "bmi >= 30", "score": 1},
            {"id": "inf_age", "condition": "age >= 70", "score": 1},
            {"id": "inf_malnutrition", "condition": "lab.albumin <= 30", "score": 3},
            {"id": "inf_open", "condition": "diagnosis contains '开放性'", "score": 3},
        ],
        "risk_levels": [
            {"min_score": 4, "level": "高危", "action": "围术期预防性抗生素，加强切口护理，营养支持治疗"},
            {"min_score": 2, "level": "中危", "action": "围术期预防性抗生素，注意切口观察"},
            {"min_score": 0, "level": "低危", "action": "标准外科预防"},
        ],
    },
    "cardiac": {
        "id": "cardiac", "label": "心血管事件风险",
        "score_items": [
            {"id": "card_age", "condition": "age >= 80", "score": 3},
            {"id": "card_age2", "condition": "65 <= age <= 79", "score": 2},
            {"id": "card_ht", "condition": "past_history contains '高血压'", "score": 1},
            {"id": "card_cad", "condition": "past_history contains '冠心病'", "score": 3},
            {"id": "card_hf", "condition": "past_history contains '心衰'", "score": 4},
            {"id": "card_dm", "condition": "past_history contains '糖尿病'", "score": 1},
            {"id": "card_creatinine", "condition": "lab.creatinine >= 177", "score": 2},
        ],
        "risk_levels": [
            {"min_score": 5, "level": "高危", "mace_rate": ">11%", "action": "心内科会诊，优化心脏功能，术后ICU监护，围术期β-blocker继续"},
            {"min_score": 3, "level": "中危", "mace_rate": "3-11%", "action": "完善心脏超声，必要时心内科会诊，围术期严密监测"},
            {"min_score": 0, "level": "低危", "mace_rate": "<3%", "action": "常规监测"},
        ],
    },
    "fall": {
        "id": "fall", "label": "跌倒/二次骨折风险",
        "score_items": [
            {"id": "fall_age", "condition": "age >= 75", "score": 2},
            {"id": "fall_osteoporosis", "condition": "past_history contains '骨质疏松'", "score": 3},
            {"id": "fall_fracture", "condition": "diagnosis contains '骨折'", "score": 1},
            {"id": "fall_low_weight", "condition": "weight <= 45", "score": 2},
        ],
        "risk_levels": [
            {"min_score": 3, "level": "高危", "action": "启动抗骨质疏松治疗 + 防跌倒措施 + 居家环境安全评估"},
            {"min_score": 2, "level": "中危", "action": "DXA骨密度检查 + 钙+VitD补充"},
            {"min_score": 0, "level": "低危", "action": "保持健康生活方式"},
        ],
    },
}

_LAB_ALIASES: dict[str, list[str]] = {
    "d_dimer": ["d-二聚体", "d二聚体", "ddimer"],
    "albumin": ["白蛋白", "albumin"],
    "creatinine": ["肌酐", "creatinine"],
}


def _get_field(field_name: str, patient: dict) -> Any:
    if field_name.startswith("lab."):
        lab_key = field_name[4:]
        aliases = _LAB_ALIASES.get(lab_key, [lab_key])
        for t in patient.get("lab_tests", []):
            tname = (t.get("name", "") or "").lower()
            for alias in aliases:
                if alias.lower() in tname:
                    try:
                        return float(t.get("value", 0))
                    except (ValueError, TypeError):
                        return None
        return None

    if field_name == "bmi":
        bmi = patient.get("bmi")
        if bmi is None:
            for v in patient.get("vitals", []):
                if "bmi" in (v.get("name", "") or "").lower():
                    try:
                        return float(v.get("value", 0))
                    except (ValueError, TypeError):
                        pass
        return bmi

    return patient.get(field_name, "")


def _check_string_field(field_name: str, keywords: list[str], patient: dict) -> bool:
    val = _get_field(field_name, patient)
    if not isinstance(val, str):
        return False
    val_lower = val.lower()
    for kw in keywords:
        if kw.lower() in val_lower:
            return True
    return False


def _eval_condition(condition: str, patient: dict) -> bool:
    cond = condition.strip()

    if " and " in cond:
        parts = cond.split(" and ")
        return all(_eval_condition(p.strip(), patient) for p in parts)

    contains_match = re.match(r"^(\w+(?:\.\w+)?)\s+contains\s+(.+)", cond)
    if contains_match:
        field = contains_match.group(1)
        rest = contains_match.group(2)
        values = re.findall(r"'([^']*)'", rest)
        return _check_string_field(field, values, patient)

    range_match = re.match(
        r"^(-?\d+\.?\d*)\s*<=\s*(\w+(?:\.\w+)?)\s*<=\s*(-?\d+\.?\d*)$", cond
    )
    if range_match:
        low = float(range_match.group(1))
        field = range_match.group(2)
        high = float(range_match.group(3))
        val = _get_field(field, patient)
        if val is None:
            return False
        try:
            return low <= float(val) <= high
        except (ValueError, TypeError):
            return False

    simple_match = re.match(
        r"^(\w+(?:\.\w+)?)\s*(>=|<=|>|<|==)\s*(-?\d+\.?\d*)$", cond
    )
    if simple_match:
        field = simple_match.group(1)
        op = simple_match.group(2)
        threshold = float(simple_match.group(3))
        val = _get_field(field, patient)
        if val is None:
            return False
        try:
            fval = float(val)
        except (ValueError, TypeError):
            return False
        if op == ">=":
            return fval >= threshold
        elif op == "<=":
            return fval <= threshold
        elif op == ">":
            return fval > threshold
        elif op == "<":
            return fval < threshold
        elif op == "==":
            return fval == threshold

    return False


def _assess_dimension(patient: dict, dim: dict, dim_id: str) -> dict:
    score = 0
    factors: list[str] = []
    triggered_ids: list[str] = []

    for item in dim.get("score_items", []):
        condition = item.get("condition", "")
        if _eval_condition(condition, patient):
            pts = item.get("score", 0)
            score += pts
            item_id = item.get("id", "?")
            triggered_ids.append(item_id)
            factors.append(f"{item_id} (+{pts})")

    risk_levels = dim.get("risk_levels", [])
    level = "低危"
    for rl in risk_levels:
        if score >= rl.get("min_score", 0):
            level = rl.get("level", "低危")

    recommendations: list[str] = []
    for rl in risk_levels:
        if rl.get("level") == level:
            action = rl.get("action", "")
            if action:
                recommendations = [a.strip() for a in action.split("，") if a.strip()]
            break

    result: dict[str, Any] = {
        "score": score, "risk_level": level, "factors": factors, "recommendations": recommendations,
    }

    if dim_id == "cardiac":
        for rl in risk_levels:
            if rl.get("level") == level:
                result["mace_rate"] = rl.get("mace_rate", "未知")
                break
    if dim_id == "dvt":
        result["d_dimer_elevated"] = "dvt_ddimer" in triggered_ids or "dvt_ddimer_high" in triggered_ids

    return result


def complication_predictor(
    patient_id: str = "",
    age: int = 0, diagnosis: str = "", past_history: str = "",
    bmi: float = 0.0, weight: float = 0.0,
    lab_tests: list | None = None, vitals: list | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """4 维并发症风险评估：DVT/PE + 感染 + 心血管事件 + 跌倒."""
    patient: dict[str, Any] = {
        "age": age, "diagnosis": diagnosis, "past_history": past_history,
        "bmi": bmi, "weight": weight,
        "lab_tests": lab_tests or [], "vitals": vitals or [],
    }

    dims = []
    for dim_id in ["dvt", "infection", "cardiac", "fall"]:
        dim_data = COMPLICATION_DIMENSIONS.get(dim_id, {})
        result = _assess_dimension(patient, dim_data, dim_id)
        result["dimension"] = dim_id
        result["label"] = dim_data.get("label", dim_id)
        dims.append(result)

    levels = [d["risk_level"] for d in dims]
    priority = ["高危", "中危", "低危"]
    overall = "低危"
    for lvl in levels:
        if lvl in priority and priority.index(lvl) < priority.index(overall):
            overall = lvl

    return {
        "patient_id": patient_id,
        "dimensions": dims,
        "overall_risk_level": overall,
        "summary": f"并发症综合风险: {overall} (DVT/PE={levels[0]} 感染={levels[1]} 心脏={levels[2]} 跌倒={levels[3]})",
    }


# ══════════════════════════════════════════════════════════════════════
# 风险告警 (risk_alert)
# ══════════════════════════════════════════════════════════════════════

MI_ALERT_THRESHOLDS: dict[str, dict[str, Any]] = {
    "肌钙蛋白I": {"threshold_high": 0.04, "label": "cTnI", "message": "cTnI 升高提示心肌损伤, 需排除急性冠脉综合征",
                   "action": "紧急心内科会诊, 重复 cTnI 3h 后复查"},
    "肌钙蛋白T": {"threshold_high": 0.1, "label": "cTnT", "message": "cTnT 升高提示心肌损伤, 需排除急性冠脉综合征",
                   "action": "紧急心内科会诊, 重复 cTnT 3h 后复查"},
    "心型肌酸激酶": {"threshold_high": 25, "label": "CK-MB", "message": "CK-MB 升高提示心肌损伤",
                     "action": "结合 cTnI/cTnT 综合判断, 必要时心内科会诊"},
}

ECG_ALERT_PATTERNS: dict[str, dict[str, Any]] = {
    "ST段抬高": {"level": "critical", "message": "ST段抬高 — 高度提示急性 STEMI, 需立即处理",
                  "action": "紧急心内科会诊 + 急诊冠脉造影评估"},
    "ST段压低": {"level": "critical", "message": "ST段压低 — 高度提示 NSTEMI/严重心肌缺血",
                  "action": "紧急心内科会诊 + 高敏肌钙蛋白检测"},
    "室速": {"level": "critical", "message": "室性心动过速 — 恶性心律失常",
              "action": "立即除颤/抗心律失常药物治疗"},
    "室颤": {"level": "critical", "message": "心室颤动 — 心脏骤停",
              "action": "立即心肺复苏 + 电除颤"},
    "三度房室传导阻滞": {"level": "critical", "message": "三度房室传导阻滞 — 完全性心脏阻滞",
                      "action": "临时起搏器植入 + 心内科会诊"},
    "心房颤动": {"level": "high", "message": "心房颤动 — 需评估卒中和心率控制",
                  "action": "CHA2DS2-VASc 评分, 控制心室率, 抗凝评估"},
    "T波高尖": {"level": "high", "message": "T波高尖 — 超急性期心梗/高钾血症可能",
                 "action": "急查电解质和心肌酶"},
    "QTc间期延长": {"level": "high", "message": "QTc 间期延长 — 警惕尖端扭转型室速",
                    "action": "纠正电解质紊乱, 排查药物影响"},
}


def risk_alerts(
    patient_id: str = "",
    lab_tests: list | None = None,
    ecg_findings: list | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """综合风险评估 — 实验室 + ECG 双重告警."""
    lab_tests = lab_tests or []
    ecg_findings = ecg_findings or []
    alerts: list[dict] = []
    high_count = 0
    medium_count = 0

    for test in lab_tests:
        name = test.get("name", "")
        val = test.get("value")
        if val is None:
            continue
        try:
            val_num = float(val)
        except (ValueError, TypeError):
            continue
        if name in MI_ALERT_THRESHOLDS:
            t = MI_ALERT_THRESHOLDS[name]
            if val_num > t["threshold_high"]:
                alerts.append({
                    "category": f"心肌损伤标志物 — {t['label']}",
                    "level": "high", "message": t["message"],
                    "value": val_num, "threshold": t["threshold_high"], "action": t["action"],
                })
                high_count += 1

    for finding in ecg_findings:
        label = finding.get("label", "")
        if label in ECG_ALERT_PATTERNS:
            rule = ECG_ALERT_PATTERNS[label]
            alerts.append({
                "category": f"ECG — {label}",
                "level": rule["level"],
                "message": rule["message"], "action": rule["action"],
            })
            if rule["level"] == "critical":
                high_count += 2
            elif rule["level"] == "high":
                high_count += 1
            else:
                medium_count += 1

    overall = "critical" if high_count >= 3 else \
              "high" if high_count > 0 else \
              "medium" if medium_count > 0 else "normal"

    return {
        "patient_id": patient_id,
        "alerts": alerts,
        "high_risk_count": high_count, "medium_risk_count": medium_count,
        "overall_risk_level": overall,
        "recommendation": (
            "紧急会诊" if overall in ("critical", "high")
            else "密切关注" if overall == "medium" else "常规监测"
        ),
    }


# ══════════════════════════════════════════════════════════════════════
# 质控审计 (quality_control)
# ══════════════════════════════════════════════════════════════════════

QUALITY_CHECKPOINTS = {
    "triage": [
        {"id": "QC01", "label": "急诊评估完成", "critical": True},
        {"id": "QC02", "label": "生命体征记录", "critical": True},
        {"id": "QC03", "label": "入院医嘱下达", "critical": False},
    ],
    "preop": [
        {"id": "QC04", "label": "心脏风险评估 (RCRI/ECG)", "critical": True},
        {"id": "QC05", "label": "麻醉评估 (ASA/气道/抗凝)", "critical": True},
        {"id": "QC06", "label": "合并症优化 (血糖/血压/贫血)", "critical": False},
        {"id": "QC07", "label": "48h 手术窗口评估", "critical": True},
    ],
    "surgery": [
        {"id": "QC08", "label": "骨折分型确认", "critical": True},
        {"id": "QC09", "label": "手术方案讨论记录", "critical": True},
        {"id": "QC10", "label": "MDT 会诊 (必要时)", "critical": False},
    ],
    "perioperative": [
        {"id": "QC11", "label": "DVT 预防方案 (IPC+GCS+踝泵)", "critical": True},
        {"id": "QC12", "label": "疼痛管理 (VAS q4h)", "critical": False},
        {"id": "QC13", "label": "护理计划执行", "critical": False},
    ],
    "rehab": [
        {"id": "QC14", "label": "24h 内早期康复", "critical": True},
        {"id": "QC15", "label": "出院康复计划", "critical": False},
    ],
    "followup": [
        {"id": "QC16", "label": "1月随访安排", "critical": False},
        {"id": "QC17", "label": "3/6/12月随访计划", "critical": False},
        {"id": "QC18", "label": "用药指导 (抗凝/骨质疏松)", "critical": False},
    ],
}

QC_STAGES = [
    {"id": "triage", "name": "接诊分诊阶段", "order": 1},
    {"id": "preop", "name": "术前评估阶段", "order": 2},
    {"id": "surgery", "name": "手术决策阶段", "order": 3},
    {"id": "perioperative", "name": "围术期管理阶段", "order": 4},
    {"id": "rehab", "name": "术后康复阶段", "order": 5},
    {"id": "followup", "name": "出院随访阶段", "order": 6},
]


def quality_audit(
    patient_id: str = "",
    compliance: dict[str, list[str]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """6 阶段 18 检查点质控审计."""
    compliance = compliance or {}
    results: dict[str, Any] = {}
    total_score = 100
    overall_passed = 0
    overall_total = 0

    for stage_info in QC_STAGES:
        stage = stage_info["id"]
        points = QUALITY_CHECKPOINTS.get(stage, [])
        passed = 0
        failed = 0
        stage_penalty = 0
        for cp in points:
            overall_total += 1
            if compliance.get(stage, []) and cp["id"] in compliance[stage]:
                passed += 1
                overall_passed += 1
            else:
                failed += 1
                penalty = 30 if cp["critical"] else 10
                stage_penalty += penalty
                total_score -= penalty
        results[stage] = {
            "label": f"{stage_info['name']}",
            "total": len(points), "passed": passed, "failed": failed,
            "score": max(0, 100 - stage_penalty),
        }

    total_score = max(0, total_score)
    compliance_pct = round(overall_passed / overall_total * 100, 1) if overall_total > 0 else 0.0
    grade = "优秀" if total_score >= 90 else "良好" if total_score >= 70 else "需改进" if total_score >= 50 else "不合格"

    return {
        "patient_id": patient_id, "total_score": total_score,
        "compliance_pct": compliance_pct,
        "grade": grade, "stages": results,
        "overall_passed": overall_passed, "overall_total": overall_total,
        "recommendations": (
            [] if total_score >= 90
            else ["重点改进失败阶段", "组织科室质控讨论"] if total_score >= 50
            else ["需全面整改", "提请医务科介入"]
        ),
    }


# ══════════════════════════════════════════════════════════════════════
# 术前检查清单 (checklist)
# ══════════════════════════════════════════════════════════════════════

CHECKLIST_ITEMS = [
    {"id": "cardiac", "label": "心脏评估", "triggers": ["胸闷", "胸痛", "心悸", "ECG异常", "高血压", "糖尿病"],
     "emergency": True, "action": "ECG + 心肌酶 + 心内科会诊"},
    {"id": "dvt", "label": "DVT 筛查", "triggers": ["下肢肿胀", "制动", "术后", "高龄", "D-二聚体升高"],
     "emergency": True, "action": "下肢静脉超声 + D-二聚体"},
    {"id": "infection", "label": "感染评估", "triggers": ["发热", "WBC升高", "CRP升高"],
     "emergency": True, "action": "血培养 + 感染科会诊"},
    {"id": "fracture_urgency", "label": "骨折急症", "triggers": ["开放性骨折", "动脉搏动消失", "畸形严重"],
     "emergency": True, "action": "紧急手术准备"},
    {"id": "hip_elderly", "label": "老年髋部骨折", "triggers": ["老年", "髋部骨折", "股骨颈", "转子间", "卧床"],
     "emergency": True, "action": "绿色通道 + 48h 手术窗口"},
    {"id": "hypertension", "label": "高血压评估", "triggers": ["头晕", "头痛", "视物模糊", "血压 > 180/110"],
     "emergency": True, "action": "降压治疗 + 心内科会诊"},
    {"id": "glucose", "label": "血糖评估", "triggers": ["糖尿病", "血糖异常"],
     "emergency": False, "action": "血糖监测 q6h + 胰岛素方案"},
    {"id": "renal", "label": "肾功能", "triggers": ["高龄", "糖尿病", "高血压", "肌酐升高"],
     "emergency": False, "action": "eGFR 计算 + 肾内科会诊(必要时)"},
    {"id": "coagulation", "label": "凝血功能", "triggers": ["抗凝药", "肝病史", "出血倾向"],
     "emergency": False, "action": "INR/PT/APTT + 抗凝调整方案"},
    {"id": "osteoporosis", "label": "骨质疏松", "triggers": ["高龄", "绝经后", "脆性骨折", "低体重"],
     "emergency": False, "action": "骨密度 DXA + 骨质疏松治疗"},
    {"id": "rehab", "label": "康复评估", "triggers": ["术后", "活动受限", "肌力下降"],
     "emergency": False, "action": "康复科会诊 + 早期康复计划"},
]


def checklist(
    patient_id: str = "", symptoms: list[str] | None = None,
    conditions: list[str] | None = None, age: int = 0, **kwargs: Any,
) -> dict[str, Any]:
    """11 项术前检查清单 — 触发式评估."""
    text = " ".join((symptoms or []) + (conditions or [])).lower()
    triggers: list[dict] = []
    emergency_count = 0

    for item in CHECKLIST_ITEMS:
        match = any(t in text for t in item["triggers"])
        if item["id"] == "hip_elderly" and age >= 70 and any(
            f in text for f in ["髋部", "股骨颈", "转子间", "hip"]
        ):
            match = True
        if match:
            triggers.append({"id": item["id"], "label": item["label"],
                           "emergency": item["emergency"], "action": item["action"]})
            if item["emergency"]:
                emergency_count += 1

    triage = "急诊会诊" if emergency_count >= 2 else (
        "急诊会诊 存在急症风险" if emergency_count >= 1 else "专科门诊"
    )

    return {
        "patient_id": patient_id, "triggers": triggers,
        "emergency_count": emergency_count, "total_triggers": len(triggers),
        "triage_level": triage, "recommendation": triage,
    }


# ══════════════════════════════════════════════════════════════════════
# 检查完备性 (completeness)
# ══════════════════════════════════════════════════════════════════════

REQUIRED_TESTS = {
    "lab": ["血常规", "凝血功能 (PT/INR/APTT)", "肝肾功能", "电解质", "血糖", "心肌酶 (cTnI/CK-MB)", "CRP", "白蛋白", "血型+交叉配血"],
    "exam": ["ECG", "胸片", "髋关节X光 (AP+侧位)", "下肢静脉超声", "心脏超声"],
}


def completeness(
    patient_id: str = "",
    completed_tests: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """14 项术前检查完备性评估."""
    completed = set(c.lower() for c in (completed_tests or []))
    all_tests = [t.lower() for cat in REQUIRED_TESTS.values() for t in cat]
    missing = [t for t in all_tests if not any(c in t or t in c for c in completed)]
    pct = round((len(all_tests) - len(missing)) / len(all_tests) * 100, 1)

    return {
        "patient_id": patient_id, "completeness_pct": pct,
        "total_required": len(all_tests), "missing": len(missing),
        "missing_tests": missing,
        "ready_for_surgery": pct >= 80,
        "recommendation": (
            "检查完备, 可进行术前评估" if pct >= 80
            else "需补充检查: " + ", ".join(missing[:5])
        ),
    }


# ══════════════════════════════════════════════════════════════════════
# 康复跟踪 (rehab_tracker)
# ══════════════════════════════════════════════════════════════════════

REHAB_PHASES = [
    {"phase": "术后早期 (0-2周)", "location": "住院期间",
     "goals": ["控制疼痛和肿胀", "预防并发症 (DVT/压疮/肺炎)", "早期被动活动"],
     "interventions": ["踝泵运动 20次/组, 3组/天", "股四头肌等长收缩 10次/组, 3组/天",
                        "CPM 机被动活动(关节置换术后)", "气压泵预防 DVT", "多模式镇痛"],
     "precautions": ["避免髋关节过度屈曲>90°", "避免内收超过中线", "避免旋转动作"],
     "criteria": "可独立床上转移"},
    {"phase": "术后中期 (2-6周)", "location": "出院后家庭/社区",
     "goals": ["逐步恢复关节活动度", "肌力训练", "开始负重训练"],
     "interventions": ["髋关节主动屈伸 10次/组, 3组/天", "直腿抬高 10次/组, 3组/天",
                        "助行器辅助下部分负重", "平衡训练 (坐位→站位)", "日常生活活动训练"],
     "precautions": ["负重遵医嘱逐步增加", "防跌倒, 使用助行器"],
     "criteria": "可助行器行走 10m"},
    {"phase": "术后恢复期 (6-12周)", "location": "家庭/社区",
     "goals": ["恢复独立行走能力", "提高肌力和耐力", "回归日常生活"],
     "interventions": ["渐进性抗阻训练", "完全负重行走训练", "上下楼梯训练", "平衡板训练", "社区步行训练"],
     "precautions": ["避免高强度冲击运动", "继续防跌倒措施"],
     "criteria": "可独立行走 100m"},
    {"phase": "术后长期 (12周+)", "location": "家庭/社区/康复中心",
     "goals": ["维持功能水平", "预防二次骨折", "骨质疏松长期管理"],
     "interventions": ["每周 3-5次中等强度有氧运动", "抗骨质疏松药物长期管理",
                        "每年骨密度复查", "居家环境安全评估", "跌倒预防训练"],
     "precautions": ["坚持药物治疗", "定期随访"],
     "criteria": "Harris 评分 >80"},
]


def rehab_track(
    patient_id: str = "",
    procedure: str = "",
    baseline_vas: int = 0,
    current_phase: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """4 阶段康复跟踪 + Harris 评分."""
    phases_out = []
    for i, phase in enumerate(REHAB_PHASES):
        entry = dict(phase)
        entry["is_current"] = (i == current_phase)
        entry["is_completed"] = (i < current_phase)
        entry["phase_index"] = i
        phases_out.append(entry)

    harris_scores = [
        {"time": "术前", "expected_range": "20-40"},
        {"time": "术后1月", "expected_range": "40-55"},
        {"time": "术后3月", "expected_range": "60-75"},
        {"time": "术后6月", "expected_range": "75-85"},
        {"time": "术后12月", "expected_range": "85-95"},
    ]

    return {
        "patient_id": patient_id, "phases": phases_out,
        "current_phase_index": current_phase,
        "harris_hip_score_targets": harris_scores,
        "early_rehab_goal": "<24h 启动康复",
    }


def harris_score(
    pain: int = 44, gait: int = 11, support: int = 11, distance: int = 11,
    stairs: int = 4, socks: int = 4, sitting: int = 5, transit: int = 1,
    deformity: int = 4, range_of_motion: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """Harris 髋关节评分计算."""
    total = pain + gait + support + distance + stairs + socks + sitting + transit + deformity + range_of_motion
    if total >= 90:
        grade = "优"
    elif total >= 80:
        grade = "良"
    elif total >= 70:
        grade = "可"
    else:
        grade = "差"

    return {
        "total_score": total, "grade": grade,
        "details": {
            "pain": {"score": pain, "max": 44},
            "function": {"score": gait + support + distance + stairs + socks + sitting + transit, "max": 47},
            "deformity": {"score": deformity, "max": 4},
            "range_of_motion": {"score": range_of_motion, "max": 5},
        },
    }


def rehab_compliance(
    completed_items: list[str] | None = None,
    phase_interventions: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """康复依从性评估."""
    completed_items = completed_items or []
    phase_interventions = phase_interventions or []
    if not phase_interventions:
        return {"compliance_pct": 100, "completed": [], "missing": [], "level": "N/A"}

    completed_set = set(completed_items)
    intervention_set = set(phase_interventions)
    completed = list(completed_set & intervention_set)
    missing = list(intervention_set - completed_set)
    pct = round(len(completed) / len(intervention_set) * 100, 1)

    if pct >= 80:
        level = "优"
    elif pct >= 60:
        level = "良"
    elif pct >= 40:
        level = "中"
    else:
        level = "差"

    return {"compliance_pct": pct, "completed": completed, "missing": missing, "level": level}


# ══════════════════════════════════════════════════════════════════════
# 骨质疏松管理 (osteoporosis)
# ══════════════════════════════════════════════════════════════════════

CALCIUM_VITD_PROTOCOL = {
    "calcium": {"dose": "1000-1200mg/日", "form": "碳酸钙/枸橼酸钙", "note": "餐中服用减少胃肠刺激"},
    "vitamin_d": {"dose": "800-1200IU/日", "form": "维生素D3", "note": "监测血清25(OH)D水平, 目标>30ng/mL"},
}

BMD_MONITORING = [
    {"timing": "基线", "exam": "DXA (腰椎+髋部)", "purpose": "确诊骨质疏松/骨量减少"},
    {"timing": "治疗后1年", "exam": "DXA 复查", "purpose": "评估治疗反应"},
    {"timing": "此后每1-2年", "exam": "DXA 复查", "purpose": "长期监测"},
    {"timing": "药物切换/停药时", "exam": "DXA + 骨转换标志物", "purpose": "评估病情变化"},
]

OSTEO_MEDICATIONS = [
    {"category": "双膦酸盐类", "recommended": "阿仑膦酸钠 70mg 每周1次(首选)或 唑来膦酸 5mg 每年1次",
     "note": "骨折术后尽早启动, 注意肾功能监测"},
    {"category": "RANKL抑制剂", "recommended": "地舒单抗 60mg 每6个月1次(肾功能不全者适用)",
     "note": "不可中断治疗, 注意低钙血症风险"},
    {"category": "甲状旁腺激素类似物", "recommended": "特立帕肽 20μg 每日1次",
     "note": "治疗期限不超过24个月"},
    {"category": "选择性雌激素受体调节剂", "recommended": "雷洛昔芬 60mg 每日1次",
     "note": "仅适用于绝经后女性, VTE 病史者禁用"},
]


def osteoporosis_mgmt(
    patient_id: str = "", age: int = 0, gender: str = "M",
    conditions: list[str] | None = None, **kwargs: Any,
) -> dict[str, Any]:
    """FRAX 简化评估 + 骨质疏松治疗方案."""
    conditions = [c.lower() for c in (conditions or [])]
    combined = " ".join(conditions)
    score = 0
    factors: list[str] = []

    if "骨质疏松" in combined or "骨松" in combined:
        score += 3; factors.append("确诊骨质疏松")
    if any(c in combined for c in ["脆性骨折", "fragility", "骨折"]):
        score += 2; factors.append("既往骨折史")
    if gender == "F" and age >= 65:
        score += 2; factors.append(f"女性≥65岁 ({age}岁)")
    elif gender == "M" and age >= 70:
        score += 2; factors.append(f"男性≥70岁 ({age}岁)")
    if any(c in combined for c in ["类固醇", "steroid", "激素"]):
        score += 2; factors.append("长期糖皮质激素使用")
    if any(c in combined for c in ["吸烟", "抽烟", "smoking"]):
        score += 1; factors.append("吸烟")
    if any(c in combined for c in ["饮酒", "酗酒", "alcohol"]):
        score += 1; factors.append("过量饮酒")
    if any(c in combined for c in ["类风湿", "rheumatoid"]):
        score += 1; factors.append("类风湿关节炎")
    if any(c in combined for c in ["低体重", "weight"]):
        score += 1; factors.append("低体重")

    risk = "high" if score >= 5 else "moderate" if score >= 3 else "low"

    medication = []
    if risk == "high":
        medication = OSTEO_MEDICATIONS[:2]
    elif risk == "moderate":
        medication = [OSTEO_MEDICATIONS[-1]]

    return {
        "patient_id": patient_id, "frax_risk": risk, "frax_score": score,
        "risk_factors": factors,
        "calcium": CALCIUM_VITD_PROTOCOL["calcium"]["dose"],
        "vitamin_d": CALCIUM_VITD_PROTOCOL["vitamin_d"]["dose"],
        "medications": {
            "first_line": ["阿仑膦酸钠 70mg/wk PO", "唑来膦酸 5mg/yr IV"],
            "alternative": ["地舒单抗 60mg q6mo SC", "特立帕肽 20μg/d SC (≤24月)"],
        },
        "medication_recommendations": medication,
        "calcium_vitd_protocol": CALCIUM_VITD_PROTOCOL,
        "bmd_monitoring": BMD_MONITORING if risk in ("high", "moderate") else [],
        "recommendation": (
            "建议启动抗骨质疏松药物治疗 + 钙剂维生素D补充 + DXA基线检查" if risk == "high"
            else "建议DXA骨密度检查 + 生活方式干预(补充钙剂维生素D, 负重运动)" if risk == "moderate"
            else "保持健康生活方式, 均衡营养, 适量运动"
        ),
    }


# ══════════════════════════════════════════════════════════════════════
# 护理方案 (nursing_plan)
# ══════════════════════════════════════════════════════════════════════

NURSING_STAGES = [
    {"stage": "术前护理", "order": 1, "items": [
        {"id": "n_preop_1", "content": "术前健康教育: 手术方式, 麻醉方式, 术后注意事项"},
        {"id": "n_preop_2", "content": "术前皮肤准备: 术区备皮, 皮肤完整性评估"},
        {"id": "n_preop_3", "content": "术前禁食禁水指导: 禁食6h, 禁水2h"},
        {"id": "n_preop_4", "content": "术前排便训练: 床上排便训练"},
        {"id": "n_preop_5", "content": "心理护理: 缓解术前焦虑, 讲解手术必要性"},
        {"id": "n_preop_6", "content": "术后谵妄风险评估: CAM 筛查, 评估高危因素(≥70岁/认知障碍/视力听力障碍), 启动谵妄预防方案"},
        {"id": "n_preop_7", "content": "肺功能训练: 腹式呼吸训练(10次/组, 3组/日), 有效咳嗽排痰练习, 预防术后坠积性肺炎"},
        {"id": "n_preop_8", "content": "DVT 风险筛查: Caprini 血栓风险评分, 高危患者(评分≥5)术前即启动物理预防(IPC+弹力袜)+健康教育"},
    ]},
    {"stage": "术后当日护理", "order": 2, "items": [
        {"id": "n_postop_1", "content": "生命体征监测: q1h×4次 → q4h"},
        {"id": "n_postop_2", "content": "体位管理: 患肢外展中立位, 抬高患肢15-30°"},
        {"id": "n_postop_3", "content": "切口观察: 敷料有无渗血渗液, 引流量及性状"},
        {"id": "n_postop_4", "content": "疼痛护理: VAS评分 q4h, 遵医嘱给药"},
        {"id": "n_postop_5", "content": "DVT 预防: 气压泵+踝泵运动指导"},
        {"id": "n_postop_6", "content": "压疮预防: Braden评分, 每2小时翻身"},
    ]},
    {"stage": "术后早期(术后1-3天)", "order": 3, "items": [
        {"id": "n_early_1", "content": "饮食护理: 麻醉清醒后进流质→半流质→普食"},
        {"id": "n_early_2", "content": "管道护理: 尿管护理bid, 引流管记录量及性状"},
        {"id": "n_early_3", "content": "功能锻炼指导: 踝泵运动, 股四头肌等长收缩"},
        {"id": "n_early_4", "content": "便秘预防: 腹部按摩, 饮食调整, 必要时通便药物"},
        {"id": "n_early_5", "content": "睡眠护理: 减少夜间干扰, 必要时遵医嘱镇静"},
    ]},
    {"stage": "术后恢复期(术后4天-出院)", "order": 4, "items": [
        {"id": "n_rec_1", "content": "离床活动指导: 助行器辅助下床活动"},
        {"id": "n_rec_2", "content": "跌倒预防: 床栏使用, 呼叫器放置, 防滑鞋"},
        {"id": "n_rec_3", "content": "出院护理指导: 切口护理, 饮食指导, 复诊安排"},
        {"id": "n_rec_4", "content": "家庭护理培训: 照护者培训(翻身/助行器使用/体位摆放)"},
        {"id": "n_rec_5", "content": "心理健康评估: 术后抑郁筛查, 必要时心理科会诊"},
        {"id": "n_rec_6", "content": "DVT 药物预防: LMWH 低分子肝素 术后2-4周(关节置换延长至5周), 监测出血风险及血小板"},
    ]},
]

DVT_PHYSICAL_PREVENTION = [
    {"method": "间歇充气加压装置(IPC)", "frequency": "每日2次, 每次30min", "note": "术后即刻开始, 直至下床活动"},
    {"method": "梯度压力弹力袜(GCS)", "frequency": "持续穿戴", "note": "选择合适压力级别, 每日检查皮肤状况"},
    {"method": "踝泵运动", "frequency": "20次/组, 每小时1组", "note": "麻醉清醒后即开始"},
]

POSITIONING_PLAN = [
    {"position": "仰卧位", "detail": "患肢外展中立位, 脚尖朝上, 膝下垫软枕使髋膝关节微屈"},
    {"position": "健侧卧位", "detail": "两膝间夹软枕, 保持患肢外展位, 避免内收"},
    {"position": "半卧位", "detail": "床头抬高30-45°, 避免髋关节屈曲>90°"},
]

PAIN_NURSING_PLAN = [
    {"method": "疼痛评估", "frequency": "术后24h内 q1h, 后续 q4h", "tool": "VAS评分/NRS评分"},
    {"method": "药物镇痛护理", "content": "遵医嘱执行多模式镇痛方案, 观察药物不良反应"},
    {"method": "非药物镇痛", "content": "冰敷(每次15-20min), 心理疏导, 放松训练, 分散注意力"},
]


def nursing_plan(
    patient_id: str = "",
    diagnosis: str = "", past_history: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """4 阶段围术期护理方案."""
    combined = f"{diagnosis} {past_history}".lower()
    highlights: list[str] = []

    if "糖尿病" in combined:
        highlights.append("糖尿病患者: 加强血糖监测, 注意切口愈合情况, 预防感染")
    if "高血压" in combined:
        highlights.append("高血压患者: 监测血压, 遵医嘱给药, 注意体位性低血压")
    if any(kw in combined for kw in ["卧床", "制动"]):
        highlights.append("长期卧床患者: 加强皮肤护理, 预防压疮及 DVT")
    if any(kw in combined for kw in ["痴呆", "阿尔茨海默", "认知"]):
        highlights.append("认知障碍患者: 加强安全防护, 防坠床/拔管/跌倒")
    if "肥胖" in combined:
        highlights.append("肥胖患者: 注意切口护理, 加强呼吸功能锻炼")
    if any(kw in combined for kw in ["骨质疏", "骨质疏松"]):
        highlights.append("骨质疏松患者: 术后需启动抗骨质疏松药物治疗(双膦酸盐/地舒单抗), 补充 Ca+VitD")
    if any(kw in combined for kw in ["营养不良", "低蛋白", "消瘦", "白蛋白"]):
        highlights.append("营养不良患者: 加强营养支持(高蛋白饮食, 必要时肠内营养补充)")
    if any(kw in combined for kw in ["copd", "慢阻肺", "哮喘", "肺气肿"]):
        highlights.append("呼吸系统疾病患者: 术后加强呼吸功能锻炼, 监测血氧, 预防坠积性肺炎")

    return {
        "patient_id": patient_id,
        "stages": NURSING_STAGES,
        "dvt_prevention": DVT_PHYSICAL_PREVENTION,
        "positioning": POSITIONING_PLAN,
        "pain_nursing": PAIN_NURSING_PLAN,
        "highlights": highlights,
    }


# ══════════════════════════════════════════════════════════════════════
# 麻醉评估 (anesthesia)
# ══════════════════════════════════════════════════════════════════════

def anesthesia_assess(
    patient_id: str = "",
    age: int = 0, past_history: str = "",
    medications: list | None = None, medication_history: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """ASA 分级 + 抗凝评估 + 气道评估."""
    comorbidities = past_history or ""
    score = 1
    if age >= 80:
        score += 1
    for cond in ["心衰", "呼衰", "肾衰", "肝硬化", "恶性肿瘤"]:
        if cond in comorbidities:
            score += 1
            break
    if "冠心病" in comorbidities or "糖尿病" in comorbidities:
        score += 1
    asa_grade = str(min(score, 5))

    meds_str = medication_history
    if medications:
        meds_str = " ".join(m.get("drug_name", "") if isinstance(m, dict) else str(m) for m in medications)
    anticoag_summary = "无抗凝药物使用"
    bridge_needed = False
    if "华法林" in meds_str:
        anticoag_summary = "华法林 — 术前5天停药, INR<1.5后手术"
        bridge_needed = True
    elif "氯吡格雷" in meds_str:
        anticoag_summary = "氯吡格雷 — 术前5天停药"
    elif "阿司匹林" in meds_str:
        anticoag_summary = "阿司匹林 — 根据出血风险决定是否停药"

    return {
        "patient_id": patient_id,
        "asa_grade": asa_grade,
        "asa_summary": f"ASA {asa_grade}级",
        "asa_recommendation": (
            "高危 — 建议ICU术后监护" if int(asa_grade) >= 4
            else "中高危 — 建议麻醉科会诊" if asa_grade == "3"
            else "低中危 — 常规管理"
        ),
        "anticoagulation": {
            "summary": anticoag_summary,
            "bridge_needed": bridge_needed,
            "details": meds_str,
        },
        "airway": {"class": "I", "summary": "气道评估: Mallampati I级", "details": "预计插管无困难"},
    }
