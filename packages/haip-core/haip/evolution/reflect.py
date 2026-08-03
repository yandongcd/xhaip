"""失败反思 — 从错误决策生成结构化经验 (SEAL experience reflection 增强版).

SEAL: 错误答案 vs 金标准 → 自然语言原则
增强: 结构化 {trigger, rule, action} 字段 + 失败摘要, 可验证可审计.
"""

from __future__ import annotations

import uuid
from typing import Any

from haip.evolution.memory_base import ExperienceEntry


def build_trigger_text(patient: dict[str, Any], result: dict[str, Any]) -> str:
    """从患者特征 + 决策结果构建触发条件文本 (检索用)."""
    parts = []
    diag = patient.get("diagnosis", "")
    if diag:
        parts.append(f"诊断: {diag}")
    age = patient.get("age")
    if age:
        parts.append(f"年龄 {age} 岁")
    lab = patient.get("lab_results") or {}
    for k, v in list(lab.items())[:5]:
        try:
            parts.append(f"{k}={v}")
        except Exception:
            pass
    urgency = (result or {}).get("urgency")
    if urgency:
        parts.append(f"判定 urgency={urgency}")
    return "，".join(parts)


def _build_rule(patient: dict[str, Any], expected: Any, actual: Any, field: str) -> str:
    """生成决策规则文本 (基于失败差异)."""
    diag = str(patient.get("diagnosis", ""))
    if field == "urgency" and expected and actual:
        return (f"当{diag}且金标准要求 {expected} 时, 需检查延迟因素 "
                f"(心脏/肺/脑高危因子或抗凝/贫血/肾/感染/血糖中危因子), "
                f"不可直接判定 {actual}")
    return f"{diag}: 期望 {field}={expected}, 实际 {actual}, 需复核临床依据"


def reflect_failure(
    agent: str,
    task: str,
    patient: dict[str, Any],
    result: dict[str, Any],
    gold: dict[str, Any],
    failed_items: list[dict[str, Any]] | None = None,
) -> ExperienceEntry:
    """从失败决策反思生成经验草案 (pending 状态)."""
    failed_items = failed_items or []
    field = ""
    expected: Any = None
    actual: Any = None
    for item in failed_items:
        if "金标准" in item.get("detail", ""):
            field = item.get("field", "")
            expected = gold.get(field)
            actual = _extract_actual(item.get("detail", ""))
            break
    if not field:
        field = next((i.get("field", "") for i in failed_items), "")

    trigger = build_trigger_text(patient, result)
    rule = _build_rule(patient, expected, actual, field) if expected is not None else (
        f"{patient.get('diagnosis', '')!s}: 检查点未通过, 需补充临床依据")
    action = (f"重新评估 {field}: 对照金标准 {expected}, 补充相应检查与专科会诊"
              if expected is not None else "重新执行相关检查清单")

    return ExperienceEntry(
        exp_id=f"exp_{uuid.uuid4().hex[:8]}",
        agent=agent,
        trigger=trigger,
        rule=rule,
        action=action,
        source_failure=json_snippet({"field": field, "expected": expected, "actual": actual}),
    )


def _extract_actual(detail: str) -> Any:
    """从检查点 detail 提取实际值 (实际=...)."""
    import re
    m = re.search(r"实际=([^,，]*?)(?:,|$)", detail)
    if m:
        val = m.group(1).strip().strip("'\"")
        if val in ("None", "null", ""):
            return None
        if val in ("True", "False"):
            return val == "True"
        try:
            return float(val) if "." in val else int(val)
        except ValueError:
            return val
    return None


def json_snippet(obj: Any, max_len: int = 300) -> str:
    import json
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s[:max_len]
