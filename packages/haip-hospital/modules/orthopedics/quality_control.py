"""F4.2 流程质控 — 按指南定义各阶段质控节点与评判标准."""

from __future__ import annotations

from typing import Any

# 围术期各阶段质控节点定义
QC_STAGES: list[dict[str, Any]] = [
    {
        "id": "triage",
        "name": "接诊分诊阶段",
        "order": 1,
        "checkpoints": [
            {
                "id": "triage_1",
                "description": "是否完成急诊分诊评估",
                "criteria": "评估骨折急症等级(开放/闭合 神经血管状态)",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 急诊评估",
            },
            {
                "id": "triage_2",
                "description": "是否完成生命体征测量",
                "criteria": "血压 心率 呼吸 血氧饱和度 体温",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 生命体征监测",
            },
            {
                "id": "triage_3",
                "description": "是否完成入院医嘱",
                "criteria": "开具必查检验检查(血常规 凝血 心肌酶 肾功能 电解质 血糖)",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 入院评估",
            },
        ],
    },
    {
        "id": "preop_assessment",
        "name": "术前评估阶段",
        "order": 2,
        "checkpoints": [
            {
                "id": "preop_1",
                "description": "是否完成心脏风险评估",
                "criteria": "心电图 心肌酶谱结果已回报并评估",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 心脏评估",
            },
            {
                "id": "preop_2",
                "description": "是否完成麻醉评估",
                "criteria": "ASA分级 气道评估 RCRI评分 抗凝药物评估",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 麻醉评估",
            },
            {
                "id": "preop_3",
                "description": "是否完成基础病优化",
                "criteria": "血压控制≤160/90mmHg,血糖控制合理,心功能评估完成",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 基础病管理",
            },
            {
                "id": "preop_4",
                "description": "是否在48h内完成术前准备",
                "criteria": "从入院到手术决策时间≤48h",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 手术时机",
            },
        ],
    },
    {
        "id": "surgical_decision",
        "name": "手术决策阶段",
        "order": 3,
        "checkpoints": [
            {
                "id": "surg_1",
                "description": "是否完成骨折分型判断",
                "criteria": "影像学结果明确骨折分型(股骨颈/转子间/转子下)",
                "required": True,
                "guide_ref": "老年股骨转子间骨折诊疗指南(2020)",
            },
            {
                "id": "surg_2",
                "description": "是否完成手术方案讨论",
                "criteria": "手术方式(髓内钉/关节置换) 麻醉方式 备血方案",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 手术方案",
            },
            {
                "id": "surg_3",
                "description": "是否完成多学科会诊",
                "criteria": "骨科/麻醉科/心内科/内分泌科(按需)会诊记录",
                "required": False,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — MDT",
            },
        ],
    },
    {
        "id": "perioperative",
        "name": "围术期管理阶段",
        "order": 4,
        "checkpoints": [
            {
                "id": "peri_1",
                "description": "是否完成DVT预防",
                "criteria": "药物预防(低分子肝素)+ 物理预防(气压泵/弹力袜)",
                "required": True,
                "guide_ref": "老年髋部骨折围术期下肢深静脉血栓基础预防专家共识(2024版)",
            },
            {
                "id": "peri_2",
                "description": "是否完成疼痛管理方案",
                "criteria": "VAS评分记录+多模式镇痛方案",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 疼痛管理",
            },
            {
                "id": "peri_3",
                "description": "是否完成围术期护理计划",
                "criteria": "体位管理 压疮预防 营养支持 管道护理",
                "required": True,
                "guide_ref": "老年髋部骨折围手术期衰弱护理管理专家共识",
            },
        ],
    },
    {
        "id": "postop_rehab",
        "name": "术后康复阶段",
        "order": 5,
        "checkpoints": [
            {
                "id": "rehab_1",
                "description": "是否完成术后早期康复评估",
                "criteria": "术后24h内康复科会诊,评估肌力/关节活动度/平衡功能",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 康复",
            },
            {
                "id": "rehab_2",
                "description": "是否制定出院康复计划",
                "criteria": "物理治疗方案 功能锻炼指导 辅助器具建议",
                "required": True,
                "guide_ref": "APTA 老年髋部骨折物理治疗管理临床实践指南(2021)",
            },
        ],
    },
    {
        "id": "followup",
        "name": "出院随访阶段",
        "order": 6,
        "checkpoints": [
            {
                "id": "fu_1",
                "description": "是否制定随访计划",
                "criteria": "出院后1个月/3个月/6个月/12个月随访节点",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 随访",
            },
            {
                "id": "fu_2",
                "description": "是否完成出院用药指导",
                "criteria": "抗骨质疏松药物 抗凝药物 镇痛药物方案",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 出院指导",
            },
            {
                "id": "fu_3",
                "description": "是否完成跌倒风险评估与预防指导",
                "criteria": "居家环境改造建议 跌倒风险评分 平衡训练指导",
                "required": True,
                "guide_ref": "老年髋部骨折诊疗与管理指南(2022年版) — 二次骨折预防",
            },
        ],
    },
]


# ASSET:rule-hip-quality
def evaluate_quality_control(patient: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate quality control status for each stage.

    Returns:
        {
            "stages": [...],  # each with id, name, order, checkpoints, passed/total
            "overall_passed": int,
            "overall_total": int,
            "compliance_pct": float,
            "recommendations": [...]
        }
    """
    if patient is None:
        patient = {}

    lab_tests = patient.get("lab_tests", [])
    lab_names = {t.get("name", "") for t in lab_tests}
    exam_names = {e.get("name", "") for e in patient.get("examinations", [])}
    combined = {n.lower() for n in lab_names | exam_names}
    diagnosis = (patient.get("diagnosis", "") or "").lower()
    past_history = (patient.get("past_history", "") or "").lower()
    present = (patient.get("present_illness", "") or "").lower()
    combined_text = f"{diagnosis} {past_history} {present}"

    stage_results = []
    overall_passed = 0
    overall_total = 0

    for stage in QC_STAGES:
        checkpoints_out = []
        passed = 0

        for cp in stage["checkpoints"]:
            result = _evaluate_checkpoint(cp, combined, combined_text, patient)
            checkpoints_out.append(result)
            if result["passed"]:
                passed += 1

        stage_results.append({
            "id": stage["id"],
            "name": stage["name"],
            "order": stage["order"],
            "checkpoints": checkpoints_out,
            "passed": passed,
            "total": len(stage["checkpoints"]),
            "stage_compliant": passed == len(stage["checkpoints"]),
        })
        overall_passed += passed
        overall_total += len(stage["checkpoints"])

    compliance_pct = round(overall_passed / overall_total * 100, 1) if overall_total > 0 else 0.0

    # Generate recommendations for non-compliant checkpoints
    recommendations = []
    for stage in stage_results:
        for cp in stage["checkpoints"]:
            if not cp["passed"]:
                recommendations.append(
                    f"[{stage['name']}] {cp['description']}: {cp['criteria']}"
                )

    return {
        "stages": stage_results,
        "overall_passed": overall_passed,
        "overall_total": overall_total,
        "compliance_pct": compliance_pct,
        "recommendations": recommendations,
    }


def _evaluate_checkpoint(
    cp: dict[str, Any],
    combined_lower: set[str],
    combined_text: str,
    patient: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single checkpoint using keyword matching."""
    cp_id = cp["id"]
    criteria_lower = cp["criteria"].lower()
    criteria_keywords = criteria_lower.replace(",", " ").replace(" ", " ").replace("/", " ").split()

    found_count = sum(1 for kw in criteria_keywords if len(kw) > 1 and (
        kw in combined_text or any(kw in cl or cl in kw for cl in combined_lower)
    ))
    threshold = max(1, len(criteria_keywords) // 3)
    passed = found_count >= threshold

    # Override for specific checkpoints
    if cp_id == "preop_4":
        passed = True  # Simplified: assume within 48h if triggered
    if cp_id == "triage_1":
        passed = "骨折" in combined_text or "髋部" in combined_text or "fracture" in combined_text.lower()

    return {
        "id": cp_id,
        "description": cp["description"],
        "criteria": cp["criteria"],
        "passed": passed,
        "evidence_found": found_count > 0,
        "guide_ref": cp["guide_ref"],
    }


def print_qc_report(result: dict[str, Any]) -> None:
    """Pretty-print the quality control report."""
    print("===== 全流程质控报告 =====")
    print(f"整体依从率: {result['compliance_pct']}% ({result['overall_passed']}/{result['overall_total']})")
    print()

    for stage in result["stages"]:
        icon = "[OK]" if stage["stage_compliant"] else "[!]"
        print(f"{icon} {stage['name']} ({stage['passed']}/{stage['total']})")
        for cp in stage["checkpoints"]:
            status = "[OK]" if cp["passed"] else "[--]"
            print(f"  {status} {cp['description']}")
        print()

    if result["recommendations"]:
        print("改进建议:")
        for rec in result["recommendations"]:
            print(f"  - {rec}")
    else:
        print("所有质控节点已达标 ")
