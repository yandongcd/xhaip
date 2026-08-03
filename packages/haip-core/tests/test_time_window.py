"""time_window engine (ported from haip) + MDTOrchestrator integration tests."""

from __future__ import annotations

import pytest

from haip.time_window.models import (
    CompositeWindowSpec,
    SubWindowMode,
    SubWindowSpec,
)


@pytest.fixture(autouse=True)
def _clear_windows():
    """Each test starts with a clean in-memory window store."""
    from haip.time_window import engine as tw
    tw._WINDOWS.clear()
    tw._COMPOSITE_WINDOWS.clear()
    yield
    tw._WINDOWS.clear()
    tw._COMPOSITE_WINDOWS.clear()


def test_registry_loads_timelines() -> None:
    from haip.time_window.registry import get_timeline, list_timelines
    assert len(list_timelines()) >= 10
    spec = get_timeline("timeline-hip-fracture-48h")
    assert spec is not None
    assert spec.deadline.value == 48
    assert spec.deadline.unit.value == "hours"
    assert spec.category.value == "emergency"


def test_register_and_state() -> None:
    from haip.time_window.engine import get_window_state, register_window
    result = register_window("P-001", "timeline-hip-fracture-48h")
    assert result.state == "active"
    assert result.remaining_hours > 0
    state = get_window_state(result.window_token)
    assert state["patient_id"] == "P-001"
    assert state["state"] == "active"
    assert state["deadline"]


def test_register_unknown_timeline_raises() -> None:
    from haip.time_window.engine import register_window
    with pytest.raises(ValueError):
        register_window("P-001", "timeline-does-not-exist")


def test_expired_window_with_start_time() -> None:
    from datetime import datetime, timedelta

    from haip.time_window.engine import get_window_state, register_window
    past = (datetime.now() - timedelta(hours=60)).isoformat()
    result = register_window("P-002", "timeline-hip-fracture-48h", start_time_str=past)
    assert result.state == "expired"
    state = get_window_state(result.window_token)
    assert state["urgency"] == "expired"


def test_list_active_and_clear() -> None:
    from haip.time_window.engine import clear_window, list_active_windows, register_window
    r1 = register_window("P-003", "timeline-hip-fracture-48h")
    r2 = register_window("P-003", "timeline-hip-followup-1m")
    register_window("P-OTHER", "timeline-hip-fracture-48h")
    active = list_active_windows("P-003")
    assert len(active) == 2
    assert all("window_token" in a and "timeline_id" in a for a in active)
    cleared = clear_window(r1.window_token, reason="surgery_completed")
    assert cleared["status"] == "ok"
    assert cleared["on_time"] is True
    assert len(list_active_windows("P-003")) == 1
    assert clear_window(r2.window_token)["status"] == "ok"


def test_composite_window_verdict_emergency() -> None:
    from haip.time_window.engine import (
        register_composite_window,
        resolve_composite_verdict,
    )
    composite = register_composite_window(
        "P-004",
        CompositeWindowSpec(
            parent_timeline_id="timeline-hip-fracture-48h",
            sub_windows=[
                SubWindowSpec(member_agent_id="cardio-risk", timeline_id="timeline-hip-fracture-48h",
                              mode=SubWindowMode.PARALLEL, deadline_hours=48),
                SubWindowSpec(member_agent_id="anesthesia", timeline_id="timeline-hip-fracture-48h",
                              mode=SubWindowMode.PARALLEL, deadline_hours=48),
            ],
        ),
    )
    verdict = resolve_composite_verdict(composite.parent_token, high_risk_count=0, medium_risk_count=0)
    assert verdict["verdict"] == "emergency"
    assert verdict["window"] == "48h"


def test_composite_window_verdict_delayed_on_expired() -> None:
    from datetime import datetime, timedelta

    from haip.time_window.engine import (
        register_composite_window,
        register_sub_window,
        resolve_composite_verdict,
    )
    past = (datetime.now() - timedelta(hours=60)).isoformat()
    composite = register_composite_window(
        "P-005",
        CompositeWindowSpec(
            parent_timeline_id="timeline-hip-fracture-48h",
            sub_windows=[
                SubWindowSpec(member_agent_id="cardio-risk", timeline_id="timeline-hip-fracture-48h",
                              mode=SubWindowMode.PARALLEL, deadline_hours=48),
            ],
        ),
        start_time_str=past,
    )
    # sub window registered with a past start → expires
    register_sub_window(composite.parent_token, "cardio-risk",
                        SubWindowSpec(member_agent_id="cardio-risk", timeline_id="timeline-hip-fracture-48h",
                                      mode=SubWindowMode.PARALLEL, deadline_hours=48),
                        start_time_str=past)
    verdict = resolve_composite_verdict(composite.parent_token, high_risk_count=0, medium_risk_count=0)
    assert verdict["verdict"] == "delayed"
    assert verdict["escalated_windows"] or verdict["available_slack_hours"] <= 0


def test_mdt_orchestrator_window_integration() -> None:
    """run_session with timeline_id attaches a window verdict (best-effort)."""
    from haip.a2a.mdt_orchestrator import MDTOrchestrator

    def fake_call(agent_name, patient_id, question, context):
        return {"summary": f"{agent_name}: 建议48h内手术", "confidence": 0.8, "evidence_level": "T1"}

    orch = MDTOrchestrator(max_workers=4)
    session = orch.run_session(
        patient_id="P-006",
        question="髋部骨折手术时机",
        participants=["cardio-risk", "anesthesia", "orthopedic-surgery"],
        agent_call_fn=fake_call,
        timeline_id="timeline-hip-fracture-48h",
    )
    assert session.window_verdict is not None
    assert session.window_verdict["verdict"] in ("emergency", "urgent", "mdt", "delayed")
    assert session.window_escalated in (True, False)
    assert session.status.value == "completed"


def test_mdt_orchestrator_no_window_backward_compat() -> None:
    """Without timeline_id, session has no window fields set."""
    from haip.a2a.mdt_orchestrator import MDTOrchestrator

    def fake_call(agent_name, patient_id, question, context):
        return {"summary": "ok", "confidence": 0.8}

    orch = MDTOrchestrator(max_workers=2)
    session = orch.run_session(
        patient_id="P-007", question="q", participants=["a", "b"],
        agent_call_fn=fake_call,
    )
    assert session.window_verdict is None
    assert session.window_escalated is False
    assert session.consensus


def test_sla_stats() -> None:
    from haip.time_window.engine import register_window
    from haip.time_window.sla import get_sla_stats
    register_window("P-008", "timeline-hip-fracture-48h")
    stats = get_sla_stats(department="orthopedic_surgery")
    assert stats["total_windows"] >= 1
    assert stats["compliance_rate"] == 1.0  # no cleared/expired yet
    assert "compliance_rate" in stats
