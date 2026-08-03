"""时间窗口注册表加载器 — 从 knowledge/timelines/registry.yaml 加载窗口定义.

Ported from haip-0710 (agents.domains.haip.time_window.registry).
Adapted: registry asset now lives in packages/haip-hospital/knowledge/timelines/.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from haip.time_window.models import (
    DeadlineSpec,
    DeadlineUnit,
    EscalationLevel,
    EscalationThreshold,
    ReEvaluationSpec,
    TimelineSpec,
    WindowCategory,
)

# 定位 xhaip 知识库: 向上搜索直到找到 packages/haip-hospital/knowledge/timelines/registry.yaml
_PKG_ROOT = Path(__file__).resolve()
for _parent in _PKG_ROOT.parents:
    _candidate = _parent / "packages" / "haip-hospital" / "knowledge" / "timelines" / "registry.yaml"
    if _candidate.exists():
        _REGISTRY_PATH = _candidate
        break
else:
    _REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"

_TIMELINES: dict[str, TimelineSpec] = {}
_LOADED: bool = False


def load_all() -> dict[str, TimelineSpec]:
    global _TIMELINES, _LOADED
    if _LOADED:
        return _TIMELINES
    _TIMELINES = {}
    _TIMELINES.clear()
    if not _REGISTRY_PATH.exists():
        return _TIMELINES

    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for item in data.get("timelines", []):
        cat_str = item.get("category", "emergency")
        try:
            category = WindowCategory(cat_str)
        except ValueError:
            category = WindowCategory.EMERGENCY

        dl = item.get("deadline", {})
        deadline = DeadlineSpec(
            value=float(dl.get("value", 0)),
            unit=DeadlineUnit(dl.get("unit", "hours")),
        )

        re_eval = item.get("re_evaluation", {})
        thresholds: list[EscalationThreshold] = []
        for t in re_eval.get("escalation_threshold", []):
            level_str = t.get("level", "warning").lower()
            try:
                level = EscalationLevel(level_str)
            except ValueError:
                level = EscalationLevel.WARNING
            if "at_remaining_hours" in t:
                thresholds.append(EscalationThreshold(
                    at_value=float(t["at_remaining_hours"]),
                    unit="hours",
                    level=level,
                ))
            elif "at_remaining_minutes" in t:
                thresholds.append(EscalationThreshold(
                    at_value=float(t["at_remaining_minutes"]),
                    unit="minutes",
                    level=level,
                ))
            elif "at_remaining_days" in t:
                thresholds.append(EscalationThreshold(
                    at_value=float(t["at_remaining_days"]),
                    unit="days",
                    level=level,
                ))

        re_eval_spec = ReEvaluationSpec(
            active_interval_minutes=re_eval.get("active_interval_minutes", 0),
            active_interval_hours=re_eval.get("active_interval_hours", 0),
            active_interval_days=re_eval.get("active_interval_days", 0),
            escalation_threshold=thresholds,
        )

        spec = TimelineSpec(
            id=item["id"],
            name=item.get("name", ""),
            abbr=item.get("abbr", ""),
            category=category,
            department=item.get("department", ""),
            start_event=item.get("start_event", ""),
            deadline=deadline,
            re_evaluation=re_eval_spec,
            guideline_ref=item.get("guideline_ref", []),
            trust_level=item.get("trust_level", "T1"),
            owner=item.get("owner", ""),
            status=item.get("status", "active"),
        )
        _TIMELINES[spec.id] = spec

    _LOADED = True
    return _TIMELINES


def get_timeline(timeline_id: str) -> TimelineSpec | None:
    _ = load_all()
    return _TIMELINES.get(timeline_id)


def register_timeline(spec: TimelineSpec) -> None:
    _ = load_all()
    _TIMELINES[spec.id] = spec


def list_timelines(department: str | None = None) -> list[TimelineSpec]:
    _ = load_all()
    result = list(_TIMELINES.values())
    if department:
        result = [t for t in result if t.department == department]
    return sorted(result, key=lambda t: t.id)
