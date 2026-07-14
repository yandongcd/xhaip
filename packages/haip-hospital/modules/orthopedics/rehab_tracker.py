# @origin: haip-0710/src/agents/domains/haip/orthopedic_surgery/core/rehab_tracker.py
# @origin_repo: https://github.com/yandongcd/haip
# @ported_date: 2026-07-12
# @status: REFERENCE — requires import adaptation for xhaip engine
#   Key deps to adapt:
#     agents.domains.haip.core.* -> packages/haip-hospital/modules/shared/
#     agents.harness.* -> packages/haip-core/haip/
#     Rule path resolution -> packages/haip-hospital/knowledge/rules/
"""康复追踪模块 — 术后康复阶段管理和 Harris 评分追踪.

功能:
  1. 按康复阶段生成个性化计划
  2. Harris 髋关节评分追踪
  3. 康复依从性评估
"""

from __future__ import annotations

from typing import Any

# 康复阶段定义
REHAB_PHASES: list[dict[str, Any]] = [
    {
        "phase": "术后早期 (0-2周)",
        "location": "住院期间",
        "goals": ["控制疼痛和肿胀", "预防并发症 (DVT/压疮/肺炎)", "早期被动活动"],
        "interventions": [
            "踝泵运动 20次/组, 3组/天",
            "股四头肌等长收缩 10次/组, 3组/天",
            "CPM机被动活动(关节置换术后)",
            "气压泵预防DVT",
            "多模式镇痛",
        ],
        "precautions": ["避免髋关节过度屈曲>90°", "避免内收超过中线", "避免旋转动作"],
        "criteria": ["VAS<4", "患肢无肿胀加重", "生命体征平稳"],
    },
    {
        "phase": "术后中期 (2-6周)",
        "location": "出院后家庭/社区",
        "goals": ["逐步恢复关节活动度", "肌力训练", "开始负重训练"],
        "interventions": [
            "髋关节主动屈伸 10次/组, 3组/天",
            "直腿抬高 10次/组, 3组/天",
            "助行器辅助下部分负重",
            "平衡训练 (坐位→站位)",
            "日常生活活动训练",
        ],
        "precautions": ["负重遵医嘱逐步增加", "防跌倒,使用助行器", "保持切口干燥清洁"],
        "criteria": ["可借助助行器行走>10m", "无切口感染", "VAS<3"],
    },
    {
        "phase": "术后恢复期 (6-12周)",
        "location": "家庭/社区",
        "goals": ["恢复独立行走能力", "提高肌力和耐力", "回归日常生活"],
        "interventions": [
            "渐进性抗阻训练",
            "完全负重行走训练",
            "上下楼梯训练",
            "平衡板训练",
            "社区步行训练",
        ],
        "precautions": ["避免高强度冲击运动", "继续防跌倒措施", "骨质疏松治疗不中断"],
        "criteria": ["可独立行走>100m", "上下楼梯自如", "Harris评分>70"],
    },
    {
        "phase": "术后长期 (12周+)",
        "location": "家庭/社区/康复中心",
        "goals": ["维持功能水平", "预防二次骨折", "骨质疏松长期管理"],
        "interventions": [
            "每周3-5次中等强度有氧运动",
            "抗骨质疏松药物长期管理",
            "每年骨密度复查",
            "居家环境安全评估",
            "跌倒预防训练",
        ],
        "precautions": ["坚持药物治疗", "定期随访", "出现疼痛/肿胀及时就诊"],
        "criteria": ["Harris评分>80", "无跌倒事件", "骨密度稳定或改善"],
    },
]

# Harris 髋关节评分标准
HARRIS_SCORE_COMPONENTS: list[dict[str, Any]] = [
    {"component": "疼痛", "max_score": 44, "levels": [
        {"range": (40, 44), "label": "无或轻微疼痛,不影响活动"},
        {"range": (30, 39), "label": "轻度疼痛,偶有不适"},
        {"range": (20, 29), "label": "中度疼痛,需服止痛药"},
        {"range": (10, 19), "label": "重度疼痛,活动受限"},
        {"range": (0, 9), "label": "极度疼痛,无法活动"},
    ]},
    {"component": "功能", "max_score": 47, "sub_items": [
        ("步态", 11), ("行走辅助", 11), ("行走距离", 11), ("上下楼梯", 4), ("穿鞋袜", 4), ("坐", 5), ("公共交通", 1),
    ]},
    {"component": "畸形", "max_score": 4, "desc": "无畸形=4分"},
    {"component": "活动度", "max_score": 5, "desc": "按屈曲+外展+内收+外旋总和评分"},
]


def generate_rehab_plan(patient: dict | None = None, current_phase: int = 0) -> dict:
    """生成个性化康复计划.

    Args:
        patient: 患者信息 dict
        current_phase: 当前康复阶段索引 (0-3)

    Returns:
        包含各阶段康复指导和当前阶段详细计划的 dict
    """
    if patient is None:
        patient = {}

    diagnosis = patient.get("diagnosis", "")
    surgery_type = "关节置换" if any(kw in diagnosis for kw in ["置换", "THA", "HA"]) else "内固定"

    phases = []
    for i, phase in enumerate(REHAB_PHASES):
        entry = dict(phase)
        entry["is_current"] = (i == current_phase)
        entry["is_completed"] = (i < current_phase)
        phases.append(entry)

    current = phases[current_phase] if 0 <= current_phase < len(phases) else None

    return {
        "phases": phases,
        "current_phase": current,
        "current_phase_index": current_phase,
        "surgery_type": surgery_type,
        "patient_highlights": _get_patient_highlights(patient),
    }


def _get_patient_highlights(patient: dict) -> list[str]:
    """获取患者特定的康复注意事项."""
    past = (patient.get("past_history", "") or "").lower()
    highlights = []
    if "高血压" in past:
        highlights.append("监测血压,避免Valsalva动作")
    if "糖尿病" in past:
        highlights.append("控制血糖,促进切口愈合")
    if "骨质疏松" in past:
        highlights.append("强调抗骨质疏松治疗依从性,预防二次骨折")
    return highlights


def estimate_harris_score(
    pain: int = 44,
    gait: int = 11,
    support: int = 11,
    distance: int = 11,
    stairs: int = 4,
    socks: int = 4,
    sitting: int = 5,
    transit: int = 1,
    deformity: int = 4,
    range_of_motion: int = 5,
) -> dict:
    """估算 Harris 髋关节评分.

    Args:
        pain: 疼痛评分 (0-44)
        gait: 步态评分 (0-11)
        support: 行走辅助 (0-11)
        distance: 行走距离 (0-11)
        stairs: 上下楼梯 (0-4)
        socks: 穿鞋袜 (0-4)
        sitting: 坐 (0-5)
        transit: 公共交通 (0-1)
        deformity: 畸形 (0-4)
        range_of_motion: 活动度 (0-5)

    Returns:
        评分结果和等级
    """
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
        "total_score": total,
        "grade": grade,
        "details": {
            "pain": {"score": pain, "max": 44},
            "function": {"score": gait + support + distance + stairs + socks + sitting + transit, "max": 47},
            "deformity": {"score": deformity, "max": 4},
            "range_of_motion": {"score": range_of_motion, "max": 5},
        },
    }


def assess_rehab_compliance(completed_items: list[str], phase_interventions: list[str]) -> dict:
    """评估康复依从性.

    Args:
        completed_items: 已完成的康复项目列表
        phase_interventions: 当前阶段所有推荐项目列表

    Returns:
        依从率, 完成项目和未完成项目
    """
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


def print_rehab_plan(plan: dict) -> None:
    """打印康复计划."""
    print("===== 术后康复计划 =====")
    print(f"手术类型: {plan.get('surgery_type', '')}")
    print()

    for phase in plan.get("phases", []):
        marker = "▶ " if phase.get("is_current") else ("✅ " if phase.get("is_completed") else "  ")
        print(f"{marker}{phase['phase']} ({phase['location']})")
        print(f"    目标: {', '.join(phase['goals'])}")
        print(f"    干预措施:")
        for i in phase["interventions"]:
            print(f"      - {i}")
        if phase.get("precautions"):
            print(f"    注意事项:")
            for p in phase["precautions"]:
                print(f"      ! {p}")
        print()

    if plan.get("patient_highlights"):
        print("患者特殊情况:")
        for h in plan["patient_highlights"]:
            print(f"  ! {h}")
        print()

    print("Harris 评分等级: ≥90=优, ≥80=良, ≥70=可, <70=差")


def print_harris_score(score_result: dict) -> None:
    """打印 Harris 评分结果."""
    print("===== Harris 髋关节评分 =====")
    print(f"总分: {score_result.get('total_score', '?')}")
    print(f"等级: {score_result.get('grade', '?')}")
    details = score_result.get("details", {})
    for key, val in details.items():
        print(f"  {key}: {val.get('score', '?')}/{val.get('max', '?')}")
