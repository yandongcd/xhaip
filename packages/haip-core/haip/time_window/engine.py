"""时间窗口引擎 — 状态机核心：窗口注册、状态追踪、超时判定、复合窗口合成.

Ported from haip-0710 (agents.domains.haip.time_window.engine) to xhaip haip-core.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from haip.time_window.models import (
    CompositeWindowSpec,
    CompositeWindowState,
    CompositionRule,
    EscalationLevel,
    RegisterResult,
    SubWindowMode,
    SubWindowSpec,
    WindowEvent,
    WindowState,
    WindowStateEnum,
)
from haip.time_window.registry import get_timeline

_WINDOWS: dict[str, WindowState] = {}


def _now() -> datetime:
    return datetime.now()


def _to_deadline(start: datetime, value: float, unit: str) -> datetime:
    unit_lower = unit.lower()
    if unit_lower == "minutes":
        return start + timedelta(minutes=value)
    elif unit_lower == "hours":
        return start + timedelta(hours=value)
    elif unit_lower == "days":
        return start + timedelta(days=value)
    elif unit_lower == "weeks":
        return start + timedelta(weeks=value)
    elif unit_lower == "months":
        return start + timedelta(days=value * 30)
    return start + timedelta(hours=value)


def _compute_remaining(deadline: datetime) -> float:
    return (deadline - _now()).total_seconds() / 3600.0


def _resolve_state(remaining_hours: float, spec) -> WindowStateEnum:
    if remaining_hours <= 0:
        return WindowStateEnum.EXPIRED

    for threshold in sorted(
        spec.re_evaluation.escalation_threshold,
        key=lambda t: t.at_value,
        reverse=True,
    ):
        threshold_hours = threshold.at_value
        if threshold.unit == "minutes":
            threshold_hours = threshold.at_value / 60.0
        elif threshold.unit == "days":
            threshold_hours = threshold.at_value * 24.0

        if remaining_hours <= threshold_hours:
            if threshold.level == EscalationLevel.CRITICAL:
                return WindowStateEnum.CRITICAL
            elif threshold.level == EscalationLevel.WARNING:
                return WindowStateEnum.WARNING

    return WindowStateEnum.ACTIVE


def _resolve_urgency(remaining_hours: float, spec) -> str:
    if remaining_hours <= 0:
        return "expired"
    for threshold in sorted(
        spec.re_evaluation.escalation_threshold,
        key=lambda t: t.at_value,
        reverse=True,
    ):
        threshold_hours = threshold.at_value
        if threshold.unit == "minutes":
            threshold_hours = threshold.at_value / 60.0
        elif threshold.unit == "days":
            threshold_hours = threshold.at_value * 24.0
        if remaining_hours <= threshold_hours:
            if threshold.level == EscalationLevel.CRITICAL:
                return "critical"
            elif threshold.level == EscalationLevel.WARNING:
                return "high"
    return "normal"


def _build_escalation_plan(spec) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for t in sorted(spec.re_evaluation.escalation_threshold, key=lambda x: x.at_value, reverse=True):
        plan.append({
            "at_value": t.at_value,
            "unit": t.unit,
            "level": t.level.value,
        })
    return plan


def register_window(patient_id: str, timeline_id: str, start_time_str: str | None = None) -> RegisterResult:
    spec = get_timeline(timeline_id)
    if spec is None:
        raise ValueError(f"未知时间窗口: {timeline_id}")

    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
    else:
        start_time = _now()

    deadline = _to_deadline(start_time, spec.deadline.value, spec.deadline.unit.value)
    token = f"tw_{uuid.uuid4().hex[:8]}"
    remaining = _compute_remaining(deadline)
    state = _resolve_state(remaining, spec)
    urgency = _resolve_urgency(remaining, spec)

    window = WindowState(
        window_token=token,
        timeline_id=timeline_id,
        patient_id=patient_id,
        state=state,
        start_time=start_time.isoformat(),
        deadline=deadline.isoformat(),
        events=[
            WindowEvent(
                timestamp=_now().isoformat(),
                event_type="registered",
                description=f"窗口注册: {spec.name}",
            )
        ],
        urgency=urgency,
        created_at=_now().isoformat(),
    )
    _WINDOWS[token] = window

    return RegisterResult(
        window_token=token,
        timeline_id=timeline_id,
        state=state.value,
        start_time=start_time.isoformat(),
        deadline=deadline.isoformat(),
        remaining_hours=max(0, round(remaining, 2)),
        urgency=urgency,
        escalation_plan=_build_escalation_plan(spec),
    )


def get_window_state(window_token: str) -> dict[str, Any] | None:
    window = _WINDOWS.get(window_token)
    if window is None:
        return None

    spec = get_timeline(window.timeline_id)
    if spec is None:
        return None

    deadline = datetime.fromisoformat(window.deadline)
    remaining = _compute_remaining(deadline)
    new_state = _resolve_state(remaining, spec)
    new_urgency = _resolve_urgency(remaining, spec)

    old_state = window.state
    if new_state != old_state:
        window.state = new_state
        window.urgency = new_urgency
        window.events.append(WindowEvent(
            timestamp=_now().isoformat(),
            event_type="state_change",
            description=f"状态变更: {old_state.value} → {new_state.value}",
            old_state=old_state.value,
            new_state=new_state.value,
        ))

    elapsed_hours = (_now() - datetime.fromisoformat(window.start_time)).total_seconds() / 3600.0

    return {
        "window_token": window.window_token,
        "timeline_id": window.timeline_id,
        "patient_id": window.patient_id,
        "state": window.state.value,
        "elapsed_hours": round(elapsed_hours, 2),
        "remaining_hours": max(0, round(remaining, 2)),
        "urgency": window.urgency,
        "deadline": window.deadline,
        "start_time": window.start_time,
        "events": [
            {
                "time": e.timestamp,
                "type": e.event_type,
                "description": e.description,
            }
            for e in window.events
        ],
    }


def list_active_windows(patient_id: str, category: str | None = None, sort_by: str = "urgency") -> list[dict[str, Any]]:
    active = []
    for window in _WINDOWS.values():
        if window.patient_id != patient_id:
            continue
        if window.state in (WindowStateEnum.EXPIRED, WindowStateEnum.CLEARED):
            continue

        spec = get_timeline(window.timeline_id)
        if spec is None:
            continue
        if category and spec.category.value != category:
            continue

        deadline = datetime.fromisoformat(window.deadline)
        remaining = _compute_remaining(deadline)
        active.append({
            "window_token": window.window_token,
            "timeline_id": window.timeline_id,
            "timeline_name": spec.name,
            "category": spec.category.value,
            "state": window.state.value,
            "remaining_hours": max(0, round(remaining, 2)),
            "urgency": window.urgency,
            "deadline": window.deadline,
        })

    urgency_order = {"critical": 0, "high": 1, "normal": 2, "expired": 3}
    if sort_by == "urgency":
        active.sort(key=lambda w: urgency_order.get(w["urgency"], 99))
    elif sort_by == "remaining":
        active.sort(key=lambda w: w["remaining_hours"])
    elif sort_by == "deadline":
        active.sort(key=lambda w: w["deadline"])
    return active


def clear_window(window_token: str, reason: str = "") -> dict[str, Any]:
    window = _WINDOWS.get(window_token)
    if window is None:
        return {"status": "error", "error": f"窗口不存在: {window_token}"}

    if window.state == WindowStateEnum.CLEARED:
        return {"status": "error", "error": "窗口已清除"}

    deadline = datetime.fromisoformat(window.deadline)
    was_expired = _now() > deadline
    window.state = WindowStateEnum.CLEARED
    window.events.append(WindowEvent(
        timestamp=_now().isoformat(),
        event_type="cleared",
        description=reason or "窗口已关闭",
    ))

    return {
        "status": "ok",
        "window_token": window_token,
        "was_expired": was_expired,
        "on_time": not was_expired,
        "reason": reason,
    }


def record_event(window_token: str, event_type: str, description: str = "", timestamp_str: str | None = None) -> dict[str, Any]:
    window = _WINDOWS.get(window_token)
    if window is None:
        return {"status": "error", "error": f"窗口不存在: {window_token}"}

    ts = timestamp_str if timestamp_str else _now().isoformat()
    window.events.append(WindowEvent(
        timestamp=ts,
        event_type=event_type,
        description=description,
    ))
    return {
        "status": "ok",
        "window_token": window_token,
        "event_type": event_type,
        "timestamp": ts,
    }


def get_all_windows_for_sla() -> list[WindowState]:
    return list(_WINDOWS.values())


# ── 复合窗口存储 ──

_COMPOSITE_WINDOWS: dict[str, CompositeWindowState] = {}


def register_composite_window(
    patient_id: str,
    composite_spec: CompositeWindowSpec,
    start_time_str: str | None = None,
) -> CompositeWindowState:
    parent_spec = get_timeline(composite_spec.parent_timeline_id)
    if parent_spec is None:
        raise ValueError(f"未知父窗口: {composite_spec.parent_timeline_id}")

    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
    else:
        start_time = _now()

    parent_token = register_window(
        patient_id, composite_spec.parent_timeline_id, start_time_str
    ).window_token

    sub_states: dict[str, str] = {}
    for sub in composite_spec.sub_windows:
        if sub.mode == SubWindowMode.CONDITIONAL and sub.trigger_condition is None:
            sub_states[sub.member_agent_id] = "skipped"
        else:
            sub_states[sub.member_agent_id] = "pending"

    parent_deadline = _to_deadline(
        start_time, parent_spec.deadline.value, parent_spec.deadline.unit.value
    )
    remaining = _compute_remaining(parent_deadline)

    composite = CompositeWindowState(
        parent_token=parent_token,
        parent_timeline_id=composite_spec.parent_timeline_id,
        patient_id=patient_id,
        sub_states=sub_states,
        critical_path=0,
        available_slack=remaining,
        status="active",
        escalated_windows=[],
        sub_windows=composite_spec.sub_windows,
        composition_rule=composite_spec.composition_rule.value,
        created_at=_now().isoformat(),
        updated_at=_now().isoformat(),
    )
    _COMPOSITE_WINDOWS[parent_token] = composite
    return composite


def register_sub_window(
    parent_token: str,
    member_agent_id: str,
    sub_spec: SubWindowSpec,
    start_time_str: str | None = None,
) -> RegisterResult | None:
    composite = _COMPOSITE_WINDOWS.get(parent_token)
    if composite is None:
        return None

    token = register_window(
        composite.patient_id, sub_spec.timeline_id, start_time_str
    )
    composite.sub_states[member_agent_id] = "active"
    composite.updated_at = _now().isoformat()
    return token


def get_composite_state(parent_token: str) -> CompositeWindowState | None:
    composite = _COMPOSITE_WINDOWS.get(parent_token)
    if composite is None:
        return None

    for member_id, token_str in list(composite.sub_states.items()):
        if token_str in ("pending", "skipped", "triggered", "completed", "expired"):
            continue
        state = get_window_state(token_str)
        if state is None:
            continue
        composite.sub_states[member_id] = state["state"]

    elapsed_paths: list[float] = []
    expired_windows: list[str] = []

    for sub in composite.sub_windows:
        state_val = composite.sub_states.get(sub.member_agent_id, "pending")
        if state_val == "completed":
            elapsed_paths.append(sub.deadline_hours)
        elif state_val == "active":
            elapsed_paths.append(sub.deadline_hours * 0.5)
        elif state_val == "expired":
            elapsed_paths.append(sub.deadline_hours * 1.5)
            expired_windows.append(sub.member_agent_id)

    if composite.composition_rule == CompositionRule.CRITICAL_PATH:
        composite.critical_path = max(elapsed_paths) if elapsed_paths else 0

    parent_state = get_window_state(composite.parent_token)
    if parent_state:
        composite.available_slack = parent_state.get("remaining_hours", 0)
        composite.status = parent_state["state"]

    composite.escalated_windows = expired_windows
    composite.updated_at = _now().isoformat()

    return composite


def resolve_composite_verdict(
    parent_token: str,
    high_risk_count: int,
    medium_risk_count: int,
) -> dict[str, Any]:
    composite = get_composite_state(parent_token)
    if composite is None:
        return {"error": "复合窗口不存在"}

    has_expired = len(composite.escalated_windows) > 0
    parent_exceeded = composite.available_slack <= 0

    if has_expired or parent_exceeded:
        verdict = "delayed"
        window = "7-day"
        action = "升级为限期手术窗口(7d), 等待延迟因素解决"
    elif high_risk_count >= 1 or medium_risk_count >= 3:
        verdict = "mdt"
        window = "7-day"
        action = "MDT会诊通道: 逐项优化 + 每48h重新评估"
    elif medium_risk_count >= 1:
        verdict = "urgent"
        window = "3-7-day"
        action = "限期手术: 积极优化可逆因素"
    else:
        verdict = "emergency"
        window = "48h"
        action = "48h急诊手术"

    return {
        "verdict": verdict,
        "window": window,
        "action": action,
        "critical_path_hours": composite.critical_path,
        "available_slack_hours": composite.available_slack,
        "escalated_windows": composite.escalated_windows,
        "parent_token": parent_token,
    }
