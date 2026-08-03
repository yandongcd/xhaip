"""场景生成 — 数字病人 × 任务模板 → EvalScenario (含金标准).

金标准来源: knowledge/rules/*.yaml 通过 shared/orthopedics 引擎计算,
避免 LLM 生成患者的同源自洽陷阱 (SEAL 教训: 生成器/评估器/知识源必须分离).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from haip.eval.checkpoints import evaluate_stage_checkpoints

_TASKS_DIR = Path(__file__).resolve().parent / "tasks"

_ORTHO_DIAGNOSIS_KEYWORDS = [
    "髋部骨折", "股骨颈骨折", "转子间骨折", "粗隆间骨折",
    "股骨转子", "髋关节", "hip fracture", "femoral neck",
]


@dataclass
class EvalScenario:
    """单个评测场景: 患者 + 任务 + 期望决策."""

    scenario_id: str
    patient: dict[str, Any]
    task: dict[str, Any]
    gold: dict[str, Any] = field(default_factory=dict)
    expected_urgency: str = ""


def load_task(task_name: str) -> dict[str, Any]:
    """加载任务模板 YAML."""
    path = _TASKS_DIR / f"{task_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"任务模板不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_tasks() -> list[str]:
    return sorted(p.stem for p in _TASKS_DIR.glob("*.yaml"))


def _is_ortho_patient(p: dict[str, Any]) -> bool:
    text = " ".join([
        str(p.get("diagnosis", "")),
        str(p.get("chief_complaint", "")),
        str(p.get("present_illness", "")),
    ]).lower()
    return any(kw in text for kw in _ORTHO_DIAGNOSIS_KEYWORDS)


def load_patients_for_task(task: dict[str, Any], limit: int = 0) -> list[dict[str, Any]]:
    """从数字病人库加载与任务科室兼容的患者."""
    from haip.patients import load_all_patients

    dept = task.get("department", "")
    try:
        patients = load_all_patients()
    except Exception:
        patients = []
    if not patients:
        return []

    compatible = [p for p in patients if dept in p.get("compatible_agents", [])]
    if not compatible:
        compatible = patients
    if task.get("name") == "orthopedics_hip_fracture":
        compatible = [p for p in compatible if _is_ortho_patient(p)]
    return compatible[:limit] if limit else compatible


def _compute_gold_urgency(patient: dict[str, Any]) -> str:
    """金标准 urgency — 用 shared.timing_engine (规则 YAML 驱动) 计算."""
    try:
        from orthopedics.timing_engine import evaluate_timing
        decision = evaluate_timing(patient)
        return decision.get("urgency", "")
    except Exception:
        return ""


def build_scenarios(
    task_name: str,
    limit: int = 0,
    patients: list[dict[str, Any]] | None = None,
) -> list[EvalScenario]:
    """构建评测场景: 患者 × 任务, 每患者计算金标准."""
    task = load_task(task_name)
    if patients is None:
        patients = load_patients_for_task(task, limit=limit)
    if not patients:
        return []

    scenarios = []
    for i, p in enumerate(patients):
        gold: dict[str, Any] = {}
        urgency = _compute_gold_urgency(p)
        if urgency:
            gold["urgency"] = urgency
        scenarios.append(EvalScenario(
            scenario_id=f"{task_name}-{p.get('patient_id', str(i))}",
            patient=p,
            task=task,
            gold=gold,
            expected_urgency=urgency,
        ))
    return scenarios


def scenario_to_case_text(p: dict[str, Any]) -> str:
    """患者 dict → 分诊用病例文本."""
    parts = []
    if p.get("age"):
        parts.append(f"{p['age']}岁{p.get('gender', '')}")
    if p.get("diagnosis"):
        parts.append(p["diagnosis"])
    if p.get("chief_complaint"):
        parts.append(p["chief_complaint"])
    if p.get("past_history"):
        parts.append(f"既往史: {p['past_history']}")
    return "，".join(parts)


def _patient_labs(p: dict[str, Any]) -> dict[str, float]:
    """患者 lab_results → 扁平数值 dict (与 handler 签名对齐)."""
    labs: dict[str, float] = {}
    for k, v in (p.get("lab_results") or {}).items():
        try:
            labs[k] = float(v)
        except (TypeError, ValueError):
            continue
    return labs


def build_stage_inputs(stage: dict[str, Any], scenario: EvalScenario) -> dict[str, Any]:
    """按阶段工具签名组装调用参数 (与 Agent YAML handler 签名对齐)."""
    tool = stage.get("tool", "")
    p = scenario.patient
    age = p.get("age", 0) or 0
    diagnosis = str(p.get("diagnosis", ""))
    labs = _patient_labs(p)

    base = {"patient_id": p.get("patient_id", "")}

    if tool == "checklist":
        base.update({
            "symptoms": [str(p.get("chief_complaint", ""))] if p.get("chief_complaint") else [],
            "conditions": [diagnosis] if diagnosis else [],
            "age": age,
        })
    elif tool == "timing_decision":
        base["labs"] = labs
        base["conditions"] = [diagnosis] if diagnosis else []
        base["ecg_findings"] = ""
    elif tool == "classify_fracture":
        base["xray_findings"] = {
            "location": "femoral_neck" if "股骨颈" in diagnosis else "intertrochanteric",
            "type": "IV" if "完全移位" in diagnosis else "II",
        }
    elif tool == "surgical_plan":
        base["fracture_type"] = "股骨颈骨折" if "股骨颈" in diagnosis else "股骨转子间骨折"
        base["age"] = age
    elif tool == "complication_risk":
        base["age"] = age
        base["labs"] = labs
        base["conditions"] = [diagnosis] if diagnosis else []
        base["procedure"] = "THA" if "股骨颈" in diagnosis else "PFNA"
    elif tool == "nursing_plan":
        base["age"] = age
        base["conditions"] = [diagnosis] if diagnosis else []
        base["procedure"] = "THA" if "股骨颈" in diagnosis else "PFNA"
    elif tool == "followup_plan":
        base["procedure"] = "THA" if "股骨颈" in diagnosis else "PFNA"
    return base


def evaluate_scenario_stages(
    scenario: EvalScenario,
    results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """对场景的全部阶段结果执行检查点评估."""
    stage_reports = []
    passed_total = 0
    check_total = 0
    for stage in scenario.task.get("stages", []):
        stage_id = stage.get("id", "")
        result = results.get(stage_id, {})
        report = evaluate_stage_checkpoints(stage, result, scenario.gold)
        stage_reports.append(report)
        passed_total += report["passed_count"]
        check_total += report["total"]
    return {
        "scenario_id": scenario.scenario_id,
        "stages": stage_reports,
        "passed_count": passed_total,
        "total": check_total,
        "completion": round(passed_total / check_total * 100, 1) if check_total else 0.0,
    }


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
