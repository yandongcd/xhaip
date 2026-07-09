"""骨科 — 质控审计 + 术前检查清单 + 检查完备性 + 康复跟踪 + 骨质疏松."""

from __future__ import annotations

from typing import Any


# ════════════════════════════════════
# 质控审计 (quality_control)
# ════════════════════════════════════

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


def quality_audit(
    patient_id: str = "",
    compliance: dict[str, list[str]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """6 阶段 18 检查点质控审计。

    扣分规则:
      - 严重项缺失: -30 分
      - 非严重项缺失: -10 分
    """
    compliance = compliance or {}
    results: dict[str, Any] = {}
    total_score = 100

    for stage, points in QUALITY_CHECKPOINTS.items():
        passed = 0
        failed = 0
        stage_penalty = 0
        for cp in points:
            if compliance.get(stage, []) and cp["id"] in compliance[stage]:
                passed += 1
            else:
                failed += 1
                penalty = 30 if cp["critical"] else 10
                stage_penalty += penalty
                total_score -= penalty
        results[stage] = {
            "label": f"阶段 {stage}",
            "total": len(points), "passed": passed, "failed": failed,
            "score": max(0, 100 - stage_penalty),
        }

    total_score = max(0, total_score)
    grade = "优秀" if total_score >= 90 else "良好" if total_score >= 70 else "需改进" if total_score >= 50 else "不合格"

    return {
        "patient_id": patient_id, "total_score": total_score,
        "grade": grade, "stages": results,
        "recommendations": (
            [] if total_score >= 90
            else ["重点改进失败阶段", "组织科室质控讨论"] if total_score >= 50
            else ["需全面整改", "提请医务科介入"]
        ),
    }


# ════════════════════════════════════
# 术前检查清单 (checklist)
# ════════════════════════════════════

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
     "emergency": True, "action": "绿色通道 + 48h手术窗口"},
    {"id": "glucose", "label": "血糖评估", "triggers": ["糖尿病", "血糖异常"],
     "emergency": False, "action": "血糖监测 q6h + 胰岛素方案"},
    {"id": "renal", "label": "肾功能", "triggers": ["高龄", "糖尿病", "高血压", "肌酐升高"],
     "emergency": False, "action": "eGFR计算 + 肾内科会诊(必要时)"},
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
    """11 项术前检查清单。"""
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


# ════════════════════════════════════
# 检查完备性 (completeness)
# ════════════════════════════════════

REQUIRED_TESTS = {
    "lab": ["血常规", "凝血功能 (PT/INR/APTT)", "肝肾功能", "电解质", "血糖", "心肌酶 (cTnI/CK-MB)", "CRP", "白蛋白", "血型+交叉配血"],
    "exam": ["ECG", "胸片", "髋关节X光 (AP+侧位)", "下肢静脉超声", "心脏超声"],
}


def completeness(
    patient_id: str = "",
    completed_tests: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """14 项术前检查完备性评估。"""
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


# ════════════════════════════════════
# 康复跟踪 (rehab_tracker)
# ════════════════════════════════════

def rehab_track(
    patient_id: str = "",
    procedure: str = "",
    baseline_vas: int = 0,
    **kwargs: Any,
) -> dict[str, Any]:
    """4 阶段康复跟踪 + Harris 评分。"""
    phases = [
        {"phase": 1, "label": "早期 (0-2周)", "goals": ["踝泵", "股四头肌等长收缩", "CPM 0-30°", "床上转移"],
         "criteria": "可独立床上转移"},
        {"phase": 2, "label": "中期 (2-6周)", "goals": ["助行器部分负重", "直腿抬高", "髋外展", "坐位平衡"],
         "criteria": "可助行器行走 10m"},
        {"phase": 3, "label": "恢复期 (6-12周)", "goals": ["单拐行走", "上下楼梯", "户外活动", "平衡训练"],
         "criteria": "可单拐行走 100m"},
        {"phase": 4, "label": "长期 (12周+)", "goals": ["独立行走", "恢复日常活动", "肌力训练", "防跌倒"],
         "criteria": "可独立行走 500m"},
    ]

    harris_scores = [
        {"time": "术前", "expected_range": "20-40"},
        {"time": "术后1月", "expected_range": "40-55"},
        {"time": "术后3月", "expected_range": "60-75"},
        {"time": "术后6月", "expected_range": "75-85"},
        {"time": "术后12月", "expected_range": "85-95"},
    ]

    return {
        "patient_id": patient_id, "phases": phases,
        "harris_hip_score_targets": harris_scores,
        "early_rehab_goal": "<24h 启动康复",
    }


# ════════════════════════════════════
# 骨质疏松管理 (osteoporosis)
# ════════════════════════════════════

def osteoporosis_mgmt(
    patient_id: str = "", age: int = 0, gender: str = "M",
    conditions: list[str] | None = None, **kwargs: Any,
) -> dict[str, Any]:
    """FRAX 简化评估 + 骨质疏松治疗方案。"""
    conditions = [c.lower() for c in (conditions or [])]
    score = 0
    if (gender == "F" and age >= 65) or (gender == "M" and age >= 70): score += 2
    if any(c in " ".join(conditions) for c in ["脆性骨折", "fragility"]): score += 3
    if any(c in " ".join(conditions) for c in ["骨质疏松", "osteoporosis"]): score += 2
    if any(c in " ".join(conditions) for c in ["类固醇", "steroid"]): score += 1

    risk = "high" if score >= 4 else "moderate" if score >= 2 else "low"

    return {
        "patient_id": patient_id, "frax_risk": risk, "frax_score": score,
        "calcium": "1000-1200 mg/d", "vitamin_d": "800-1200 IU/d",
        "medications": {
            "first_line": ["阿仑膦酸钠 70mg/wk PO", "唑来膦酸 5mg/yr IV"],
            "alternative": ["地舒单抗 60mg q6mo SC", "特立帕肽 20μg/d SC (≤24月)"],
        },
        "bmd_monitoring": "基线 DXA → 1年 → 每1-2年",
    }
