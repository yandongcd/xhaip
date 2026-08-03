"""时间窗口 SLA 统计模块."""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any

from haip.time_window.engine import get_all_windows_for_sla
from haip.time_window.registry import list_timelines


def get_sla_stats(
    department: str | None = None,
    timeline_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    windows = get_all_windows_for_sla()
    from_dt = datetime.fromisoformat(date_from) if date_from else None
    to_dt = datetime.fromisoformat(date_to) if date_to else None

    matched_timeline_ids: set[str] = set()
    if timeline_id:
        matched_timeline_ids.add(timeline_id)
    elif department:
        for t in list_timelines(department=department):
            matched_timeline_ids.add(t.id)
    else:
        for t in list_timelines():
            matched_timeline_ids.add(t.id)

    relevant: list[dict[str, Any]] = []
    for w in windows:
        if w.timeline_id not in matched_timeline_ids:
            continue
        created = datetime.fromisoformat(w.created_at) if w.created_at else None
        if from_dt and created and created < from_dt:
            continue
        if to_dt and created and created > to_dt:
            continue
        relevant.append({
            "state": w.state.value,
            "deadline": w.deadline,
        })

    completed_on_time = 0
    completed_late = 0
    still_active = 0
    completion_hours: list[float] = []

    for r in relevant:
        if r["state"] == "cleared":
            dl = datetime.fromisoformat(r["deadline"])
            if datetime.now() <= dl:
                completed_on_time += 1
            else:
                completed_late += 1
        elif r["state"] == "expired":
            completed_late += 1
        else:
            still_active += 1

    total = completed_on_time + completed_late
    compliance_rate = round(completed_on_time / total, 3) if total > 0 else 1.0
    median_hours = round(median(completion_hours), 1) if completion_hours else 0.0

    root_causes: dict[str, int] = {}
    for w in windows:
        if w.timeline_id not in matched_timeline_ids:
            continue
        for e in w.events:
            if e.event_type == "delay_factor_triggered":
                root_causes[e.description] = root_causes.get(e.description, 0) + 1

    return {
        "department": department or "all",
        "timeline_id": timeline_id or "all",
        "period": {"from": date_from or "-", "to": date_to or "-"},
        "total_windows": len(relevant),
        "completed_on_time": completed_on_time,
        "completed_late": completed_late,
        "still_active": still_active,
        "compliance_rate": compliance_rate,
        "median_completion_hours": median_hours,
        "delay_root_causes": root_causes,
    }
