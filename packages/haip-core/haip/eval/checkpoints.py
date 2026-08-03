"""检查点评估 — 规则式检查点与金标准对比检查点执行器."""

from __future__ import annotations

from typing import Any


class CheckpointError(Exception):
    """检查点定义或执行错误."""


def _get_field(result: dict[str, Any], field: str) -> Any:
    """点路径取字段, 如 'a.b.c'."""
    cur: Any = result
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def evaluate_checkpoint(
    cp: dict[str, Any],
    result: dict[str, Any],
    gold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """执行单个检查点, 返回 {id, passed, detail, weight}."""
    cp_id = cp.get("id", "unknown")
    weight = float(cp.get("weight", 1.0))
    cp_type = cp.get("type", "rule")
    field = cp.get("field", "")
    message = cp.get("message", "")

    if cp_type == "gold":
        if gold is None:
            return {"id": cp_id, "passed": False, "weight": weight,
                    "detail": f"{message} — 无金标准可对比", "field": field}
        actual = _get_field(result, field)
        expected = gold.get(field)
        passed = actual == expected
        return {"id": cp_id, "passed": passed, "weight": weight,
                "detail": f"{message} — 实际={actual!r}, 金标准={expected!r}", "field": field}

    actual = _get_field(result, field)
    op = cp.get("op", "nonempty")
    value = cp.get("value")

    passed = False
    detail = f"字段 {field}={actual!r}"
    try:
        if op == "nonempty":
            passed = bool(actual) and actual != [] and actual != {}
            detail += f" — {message}"
        elif op == "eq":
            passed = actual == value
            detail += f" == {value!r} — {message}"
        elif op == "neq":
            passed = actual != value
            detail += f" != {value!r} — {message}"
        elif op == "in":
            passed = actual in (value or [])
            detail += f" ∈ {value!r} — {message}"
        elif op == "notin":
            passed = actual not in (value or [])
            detail += f" ∉ {value!r} — {message}"
        elif op == ">":
            passed = _to_num(actual) > _to_num(value)
            detail += f" > {value!r} — {message}"
        elif op == ">=":
            passed = _to_num(actual) >= _to_num(value)
            detail += f" >= {value!r} — {message}"
        elif op == "<":
            passed = _to_num(actual) < _to_num(value)
            detail += f" < {value!r} — {message}"
        elif op == "<=":
            passed = _to_num(actual) <= _to_num(value)
            detail += f" <= {value!r} — {message}"
        elif op == "contains":
            passed = value in (actual or [])
            detail += f" 含 {value!r} — {message}"
        else:
            raise CheckpointError(f"未知操作符: {op}")
    except (TypeError, ValueError):
        passed = False
        detail += " (类型不可比较)"

    return {"id": cp_id, "passed": passed, "weight": weight,
            "detail": detail, "field": field}


def _to_num(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("%", "").strip())
    except (TypeError, ValueError):
        raise TypeError(f"不可转数值: {v!r}")


def evaluate_stage_checkpoints(
    stage: dict[str, Any],
    result: dict[str, Any],
    gold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """评估一个阶段的所有检查点, 返回 {stage_id, passed_count, total, passed, score, items}."""
    items = []
    passed = 0
    for cp in stage.get("checkpoints", []):
        item = evaluate_checkpoint(cp, result, gold)
        items.append(item)
        if item["passed"]:
            passed += 1
    total = len(items)
    score = round(passed / total * 100, 1) if total else 0.0
    return {
        "stage_id": stage.get("id", ""),
        "stage_name": stage.get("name", ""),
        "passed_count": passed,
        "total": total,
        "passed": passed == total if total else False,
        "score": score,
        "items": items,
    }
