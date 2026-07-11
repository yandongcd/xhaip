"""Shared triage engine — LLM + Rules hybrid keyword matching for checklists.

Port from haip-0705-2 v0.2.0. Pure Python, keyword matching + lab threshold logic.
"""

from __future__ import annotations

from typing import Any


def _keyword_match(text: str, item: dict[str, Any]) -> list[str]:
    text_lower = text.lower()
    return [t for t in item.get("triggers", []) if t.lower() in text_lower]


def evaluate_checklist(
    patient_text: str,
    rule_items: list[dict[str, Any]],
    *,
    use_llm: bool = False,
    domain: str = "",
) -> dict[str, Any]:
    """Evaluate a checklist against patient text using rule-based matching.

    Args:
        patient_text: Free-text patient case description.
        rule_items: List of dicts with {id, label, question, triggers, emergency_if}.
        use_llm: If True, supplements rule matching with LLM analysis (future).
        domain: Department tag for LLM prompt context (future).

    Returns:
        {all_items, emergency_flags, triggered_count, recommendation, domain}
    """
    all_items: list[dict[str, Any]] = []
    emergency_flags: list[dict[str, Any]] = []
    triggered_count = 0

    for item in rule_items:
        matched = _keyword_match(patient_text, item)
        is_triggered = len(matched) > 0
        if is_triggered:
            triggered_count += 1
            if item.get("emergency_if"):
                emergency_flags.append({
                    "id": item["id"],
                    "label": item["label"],
                    "question": item["question"],
                })

        all_items.append({
            "id": item["id"],
            "label": item["label"],
            "question": item["question"],
            "triggered": is_triggered,
            "matched_triggers": matched,
            "emergency_if": item.get("emergency_if", False),
        })

    recommendation = _generate_recommendation(emergency_flags, triggered_count, domain)

    return {
        "patient_case": patient_text,
        "all_items": all_items,
        "emergency_flags": emergency_flags,
        "triggered_count": triggered_count,
        "recommendation": recommendation,
        "domain": domain or "general",
    }


def _generate_recommendation(
    emergency_flags: list[dict[str, Any]],
    triggered_count: int,
    domain: str,
) -> str:
    n = len(emergency_flags)
    if n >= 2:
        return "急诊会诊 — 多项急症指标触发，建议立即转急诊科处理"
    elif n == 1:
        return "急诊会诊 — 存在急症风险，建议急诊科进一步评估"
    elif triggered_count >= 3:
        return "建议专科门诊 — 存在多项风险因素，建议专科门诊全面评估"
    elif triggered_count >= 1:
        return "建议专科门诊 — 存在相关风险因素，建议门诊评估"
    else:
        return "暂无明确专科诊疗指征，建议定期随访"


def extract_keywords_from_patient(
    patient_dict: dict,
    reference_ranges_func=None,
) -> list[dict]:
    """Auto-extract keywords from patient data (labs, diagnosis, history, etc.).

    This is the ortho-specific keyword extractor. Other agents should provide
    their own extraction logic or skip this step.
    """
    keywords: list[dict] = []
    added: set[str] = set()

    def add(label: str, triggers: list[str], item_ids: list[str],
            source: str = "", severity: str = "medium"):
        if label in added:
            return
        added.add(label)
        keywords.append({
            "id": label, "label": label, "triggers": triggers,
            "checklist_item_ids": item_ids, "data_source": source, "severity": severity,
        })

    # Lab-based keywords
    for test in patient_dict.get("lab_tests", []):
        val = test.get("value")
        name = test.get("name", "")
        try:
            val_f = float(val) if val is not None else None
        except (ValueError, TypeError):
            continue

        if val_f is None:
            continue

        if reference_ranges_func:
            result = reference_ranges_func(name, val_f)
            if not result.get("abnormal"):
                continue

        if name == "肌酸激酶" and val_f > 200:
            add("心梗高风险", ["心梗", "CK升高"], ["cardiac"], f"{name}={val_f}", "high")
        if name == "C反应蛋白" and val_f > 6:
            add("感染风险", ["CRP升高"], ["infection"], f"{name}={val_f}", "high")
        if "肾小球滤过率" in name and val_f < 60:
            add("肾功能不全", ["肌酐升高"], ["renal_function"], f"{name}={val_f}", "medium")
        if name == "肌酐" and val_f > 104:
            add("肾功能不全", ["肌酐升高"], ["renal_function"], f"{name}={val_f}", "medium")
        if name == "葡萄糖" and val_f > 6.1:
            add("血糖异常", ["血糖异常"], ["blood_glucose"], f"{name}={val_f}", "medium")
        if name == "总钙" and val_f < 2.1:
            add("电解质异常", ["电解质紊乱"], ["renal_function"], f"{name}={val_f}", "medium")
        if name in ("总蛋白", "白蛋白") and val_f < 65:
            add("营养不良", ["低蛋白"], ["osteoporosis", "rehabilitation"], f"{name}={val_f}", "medium")

    # Diagnosis + chief complaint
    combined = patient_dict.get("diagnosis", "") + " " + patient_dict.get("chief_complaint", "")
    if any(kw in combined for kw in ["髋部骨折", "股骨颈骨折", "转子间骨折", "髋关节"]):
        add("老年髋部骨折", ["髋部骨折", "老年"], ["hip_fracture_elderly", "osteoporosis"],
            str(patient_dict.get("diagnosis", "")))
    if "胸闷" in combined or "胸痛" in combined:
        add("胸闷胸痛", ["胸闷", "胸痛"], ["cardiac"], str(patient_dict.get("chief_complaint", "")))

    # Past history
    past = str(patient_dict.get("past_history", ""))
    if "冠心病" in past or "冠脉" in past or "心脏" in past:
        add("冠心病史", ["冠心病"], ["cardiac"], "既往史")
    if "高血压" in past:
        add("高血压史", ["高血压史"], ["hypertension", "cardiac", "renal_function"], "既往史")
    if "糖尿病" in past:
        add("糖尿病史", ["糖尿病史"], ["blood_glucose", "cardiac", "renal_function"], "既往史")
    if "肝" in past:
        add("肝功能异常", ["肝病史"], ["coagulation"], "既往史")

    # Age-based
    age = patient_dict.get("age", 0)
    if age and int(age) >= 65:
        add("高龄", ["高龄"], ["cardiac", "hip_fracture_elderly", "renal_function", "osteoporosis"],
            f"年龄 {age}", "low")

    # ECG findings from examinations
    try:
        from .ecg_analyzer import extract_ecg_keywords_from_exam
        for ekw in extract_ecg_keywords_from_exam(patient_dict):
            if ekw["label"] not in added:
                added.add(ekw["label"])
                keywords.append(ekw)
    except ImportError:
        pass

    # Examination-based keywords
    for exam in patient_dict.get("examinations", []):
        res = exam.get("result", "")
        name_e = exam.get("name", "")
        if "心电" in name_e or "ECG" in name_e.upper() or "心电图" in name_e:
            continue
        if "超声" in name_e and "静脉" in name_e and ("血栓" in res or "异常" in res):
            add("DVT风险", ["DVT"], ["deep_vein_thrombosis"], res[:60], "high")
        if "放射" in name_e and "骨折" in res:
            add("骨折确诊", ["骨折"], ["fracture_urgency", "hip_fracture_elderly"], res[:60])

    return keywords
