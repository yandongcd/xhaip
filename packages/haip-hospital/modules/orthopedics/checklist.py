# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/checklist.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: REFERENCE — requires import adaptation for xhaip engine
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""Checklist generator — ortho triage with shared triage engine.

Uses haip/core/triage_engine.py for rule matching + keyword extraction.
Rule items are ortho-specific (11 items based on NICE NG37 / AAOS / NHC guidelines).
"""

from __future__ import annotations

import sys

from agents.domains.haip.core.triage_engine import evaluate_checklist, extract_keywords_from_patient
from agents.domains.haip.rules.core.knowledge import check_range
from agents.domains.haip.rules.core.guidelines import available_guidelines


CHECKLIST_ITEMS = [
    {
        "id": "cardiac",
        "label": "心梗相关检查",
        "question": "是否需要做心肌酶谱 / 心电图排除急性冠脉综合征？",
        "triggers": ["胸闷", "胸痛", "心悸", "气促", "心电图异常", "高血压", "糖尿病", "高龄"],
        "emergency_if": True,
    },
    {
        "id": "hypertension",
        "label": "高血压评估",
        "question": "是否需要监测血压、评估高血压急症？",
        "triggers": ["头晕", "头痛", "视物模糊", "高血压史", "血压 > 180/110"],
        "emergency_if": True,
    },
    {
        "id": "deep_vein_thrombosis",
        "label": "下肢深静脉血栓（DVT）筛查",
        "question": "是否存在 DVT 风险？是否需要超声筛查？",
        "triggers": ["下肢肿胀", "下肢疼痛", "制动", "骨折术后", "高龄", "D-二聚体升高"],
        "emergency_if": True,
    },
    {
        "id": "infection",
        "label": "创面/感染评估",
        "question": "是否存在创面感染、骨髓炎或脓毒症风险？",
        "triggers": ["发热", "创面渗液", "红肿", "WBC升高", "CRP升高", "糖尿病足"],
        "emergency_if": True,
    },
    {
        "id": "fracture_urgency",
        "label": "骨折急症判断",
        "question": "是否为开放性骨折、病理性骨折或合并神经血管损伤？",
        "triggers": ["开放性骨折", "远端麻木", "皮温低", "动脉搏动消失", "畸形严重", "剧痛"],
        "emergency_if": True,
    },
    {
        "id": "hip_fracture_elderly",
        "label": "老年髋部骨折手术时机评估",
        "question": "老年髋部骨折是否需 48h 内手术？是否合并内科并发症？",
        "triggers": ["老年", "髋部骨折", "股骨颈骨折", "转子间骨折", "卧床"],
        "emergency_if": True,
    },
    {
        "id": "blood_glucose",
        "label": "血糖评估",
        "question": "是否需要监测血糖，排除糖尿病酮症酸中毒？",
        "triggers": ["糖尿病史", "多饮多尿", "意识改变", "血糖异常"],
        "emergency_if": True,
    },
    {
        "id": "renal_function",
        "label": "肾功能评估",
        "question": "是否需要评估肾功能，避免造影剂肾病？",
        "triggers": ["高龄", "糖尿病", "高血压", "利尿剂使用", "肌酐升高"],
        "emergency_if": False,
    },
    {
        "id": "coagulation",
        "label": "凝血功能评估",
        "question": "是否需要检测凝血功能，评估出血/血栓风险？",
        "triggers": ["抗凝药使用", "肝病史", "出血倾向", "术前评估"],
        "emergency_if": False,
    },
    {
        "id": "osteoporosis",
        "label": "骨质疏松评估",
        "question": "是否需要骨密度检查，启动抗骨质疏松治疗？",
        "triggers": ["高龄", "绝经后", "脆性骨折史", "低体重"],
        "emergency_if": False,
    },
    {
        "id": "rehabilitation",
        "label": "康复评估",
        "question": "是否需要康复科会诊？是否需要物理治疗？",
        "triggers": ["术后", "活动受限", "肌力下降", "平衡障碍"],
        "emergency_if": False,
    },
]


def generate_checklist(patient_case: str) -> dict:
    """Analyze patient case using shared triage engine + ortho rule items."""
    guideline_refs = available_guidelines()
    result = evaluate_checklist(patient_case, CHECKLIST_ITEMS, domain="orthopedic_surgery")
    result["guidelines_available"] = len(guideline_refs)
    result["guidelines_count"] = len(guideline_refs)
    return result


def print_checklist(result: dict) -> None:
    """Pretty-print the checklist result to stdout."""
    header = f"===== 分级诊疗 Checklist ====="
    print(header)
    print(f"病例: {result['patient_case'][:80]}{'...' if len(result['patient_case']) > 80 else ''}")
    print()

    # Table header
    print(f"检查项目 (触发 {result['triggered_count']}/{len(result['all_items'])}):")
    print(f"{'项目':<24} {'触发':<6} {'触发词':<30} {'急症':<4}")
    print("-" * 70)

    for item in result["all_items"]:
        triggered_str = "Y" if item["triggered"] else "-"
        emergency_str = "是" if item["emergency_if"] else "否"
        matched = ", ".join(item["matched_triggers"]) if item["matched_triggers"] else ""
        # Truncate matched for display
        if len(matched) > 28:
            matched = matched[:26] + ".."
        print(f"{item['label']:<24} {triggered_str:<6} {matched:<30} {emergency_str:<4}")

    if result["emergency_flags"]:
        print()
        print("触发急症指标:")
        for flag in result["emergency_flags"]:
            print(f"  - {flag['label']}: {flag['question']}")

    print()
    print(f"推荐结论: {result['recommendation']}")

    if result["guidelines_count"] > 0:
        print(f"(参考指南: {result['guidelines_count']} 份, references/haip/orthopedic_surgery/)")


def extract_keywords_from_patient(patient_dict: dict) -> list[dict]:
    """Auto-extract keywords from patient data using shared triage engine."""
    from agents.domains.haip.core.triage_engine import extract_keywords_from_patient as _engine_extract
    from agents.domains.haip.rules.core.knowledge import check_range as _cr
    return _engine_extract(patient_dict, _cr)


def generate_checklist_from_keywords(keywords: list[dict]) -> dict:
    """Generate checklist from pre-extracted keywords using shared triage engine.

    Uses checklist_item_ids to directly mark items as triggered,
    then falls back to text matching for any remaining unmatched items.
    """
    from agents.domains.haip.core.triage_engine import evaluate_checklist as _eval
    all_text_parts = []
    directly_triggered_ids: set[str] = set()
    for kw in keywords:
        all_text_parts.append(kw.get("label", "") + " " + " ".join(kw.get("triggers", [])))
        for item_id in kw.get("checklist_item_ids", []):
            directly_triggered_ids.add(item_id)
    case_text = " ".join(all_text_parts)
    fallback_result = _eval(case_text, CHECKLIST_ITEMS, domain="orthopedic_surgery")
    all_items = []
    emergency_flags = []
    triggered_count = 0
    for item in CHECKLIST_ITEMS:
        item_id = item["id"]
        if item_id in directly_triggered_ids:
            matched = [kw.get("label", "") for kw in keywords if item_id in kw.get("checklist_item_ids", [])]
            is_triggered = True
        else:
            fb_item = next((i for i in fallback_result["all_items"] if i["id"] == item_id), None)
            is_triggered = fb_item and fb_item["triggered"] if fb_item else False
            matched = fb_item["matched_triggers"] if fb_item else []
        if is_triggered:
            triggered_count += 1
            if item.get("emergency_if"):
                emergency_flags.append({"id": item_id, "label": item["label"], "question": item["question"]})
        all_items.append({"id": item_id, "label": item["label"], "question": item["question"],
                          "triggered": is_triggered, "matched_triggers": matched, "emergency_if": item.get("emergency_if", False)})
    n = len(emergency_flags)
    if n >= 2:
        recommendation = "急诊会诊 - 多项急症指标触发，建议立即转急诊科处理"
    elif n == 1:
        recommendation = "急诊会诊 - 存在急症风险，建议急诊科进一步评估"
    elif triggered_count >= 3:
        recommendation = "建议普通门诊 - 存在多项风险因素，建议专科门诊全面评估"
    else:
        recommendation = "建议普通门诊 - 无明确急症指征，可转普通门诊处理"
    guideline_refs = available_guidelines()
    return {"patient_case": case_text, "all_items": all_items, "emergency_flags": emergency_flags,
            "triggered_count": triggered_count, "recommendation": recommendation,
            "guidelines_available": len(guideline_refs), "guidelines_count": len(guideline_refs)}
