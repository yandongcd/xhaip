"""测试 MDT 编排器 — 会话编排 / 意见聚合 / 复合窗口判定 / 单例."""

from __future__ import annotations

import time

import pytest

import haip.a2a.mdt_orchestrator as mdt_mod
from haip.a2a.mdt_orchestrator import MDTOrchestrator
from haip.a2a.mdt_protocol import MDTOpinion, MDTSession, MDTStatus
from haip.time_window import engine as tw_engine
from haip.time_window import registry as tw_registry
from haip.time_window.models import (
    DeadlineSpec,
    DeadlineUnit,
    ReEvaluationSpec,
    TimelineSpec,
    WindowCategory,
)

_TEST_TIMELINE_ID = "mdt-test-window"


@pytest.fixture(autouse=True)
def _clean_state():
    mdt_mod._singleton_state.clear()
    tw_engine._WINDOWS.clear()
    tw_engine._COMPOSITE_WINDOWS.clear()
    yield
    mdt_mod._singleton_state.clear()
    tw_engine._WINDOWS.clear()
    tw_engine._COMPOSITE_WINDOWS.clear()


@pytest.fixture()
def mdt_timeline():
    tw_registry.register_timeline(TimelineSpec(
        id=_TEST_TIMELINE_ID,
        name="MDT测试窗口",
        abbr="MDTT",
        category=WindowCategory.URGENT,
        department="test",
        start_event="入院",
        deadline=DeadlineSpec(value=48, unit=DeadlineUnit.HOURS),
        re_evaluation=ReEvaluationSpec(),
        guideline_ref=["test"],
    ))


def _opinion_response(agent, recommendation, evidence_level="T2", confidence=0.8, risks=None):
    return {
        "summary": recommendation,
        "evidence_level": evidence_level,
        "confidence": confidence,
        "alerts": risks or [],
        "citations": ["测试指南"],
    }


def test_run_session_happy_path():
    def agent_call(agent, patient_id, question, context):
        return _opinion_response(agent, f"{agent} 建议尽快手术")

    session = MDTOrchestrator(max_workers=4).run_session(
        patient_id="P001",
        question="是否需要手术？",
        participants=["orthopedic-surgery", "anesthesiology"],
        agent_call_fn=agent_call,
    )
    assert session.status == MDTStatus.COMPLETED
    assert session.all_responded()
    assert len(session.opinions) == 2
    assert session.consensus
    assert session.patient_id == "P001"


def test_agent_error_does_not_abort_session():
    def failing_call(agent, patient_id, question, context):
        raise RuntimeError("agent crashed")

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["ghost-agent"],
        agent_call_fn=failing_call,
    )
    assert session.status == MDTStatus.COMPLETED
    assert len(session.opinions) == 1
    opinion = session.opinions[0]
    assert opinion.agent_name == "ghost-agent"
    assert "[ERROR]" in opinion.recommendation
    assert opinion.confidence == 0.0


def test_agent_timeout_records_timeout_opinion():
    def slow_call(agent, patient_id, question, context):
        time.sleep(1.5)
        return {"output": "late"}

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["slow-agent"],
        timeout=1,
        agent_call_fn=slow_call,
    )
    assert session.status == MDTStatus.COMPLETED
    assert len(session.opinions) == 1
    assert "[TIMEOUT]" in session.opinions[0].recommendation
    assert session.opinions[0].confidence == 0.0


def test_divergence_detected_and_resolved():
    def agent_call(agent, patient_id, question, context):
        if agent == "orthopedic-surgery":
            return _opinion_response(
                "orthopedic-surgery", "建议行手术治疗", evidence_level="T1", confidence=0.9
            )
        return _opinion_response("anesthesiology", "建议保守治疗", confidence=0.8)

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="治疗方式？",
        participants=["orthopedic-surgery", "anesthesiology"],
        agent_call_fn=agent_call,
    )
    assert session.divergences
    assert session.divergences[0].conflict_type.value == "treatment"
    assert session.status == MDTStatus.COMPLETED
    assert session.consensus.startswith("[T1优先]")


def test_unresolvable_divergence_yields_empty_consensus():
    def agent_call(agent, patient_id, question, context):
        conf = {"agent-a": 0.4, "agent-b": 0.9, "agent-c": 0.5}
        return {
            "summary": f"方案{agent[-1]}",
            "evidence_level": "T1" if agent == "agent-a" else "T2",
            "confidence": conf[agent],
        }

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="治疗方式？",
        participants=["agent-a", "agent-b", "agent-c"],
        agent_call_fn=agent_call,
    )
    assert session.divergences
    assert session.consensus == ""
    assert session.status == MDTStatus.DEADLOCKED


def test_default_agent_call_error_for_unknown_agent():
    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["no-such-agent-mdt"],
    )
    assert session.status == MDTStatus.COMPLETED
    assert len(session.opinions) == 1
    assert "[ERROR]" in session.opinions[0].recommendation
    assert session.opinions[0].confidence == 0.0


def test_output_field_used_for_recommendation():
    def agent_call(agent, patient_id, question, context):
        return {"output": "医嘱内容", "confidence": 0.7}

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["orthopedic-surgery"],
        agent_call_fn=agent_call,
    )
    assert session.opinions[0].recommendation == "医嘱内容"


def test_recommendations_field_used_for_recommendation():
    def agent_call(agent, patient_id, question, context):
        return {"recommendations": ["首选方案"], "confidence": 0.6}

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["orthopedic-surgery"],
        agent_call_fn=agent_call,
    )
    assert session.opinions[0].recommendation == "首选方案"


def test_session_add_opinion_and_get_opinion():
    session = MDTSession(
        patient_id="P001", question="q", participants=["orthopedic-surgery"]
    )
    opinion = MDTOpinion(agent_name="orthopedic-surgery", recommendation="手术", confidence=0.9)
    session.add_opinion(opinion)
    assert session.get_opinion("orthopedic-surgery") is opinion
    assert session.get_opinion("missing") is None
    assert session.all_responded()


def test_composite_verdict_attached(mdt_timeline):
    def agent_call(agent, patient_id, question, context):
        risks = ["出血风险"] if agent == "orthopedic-surgery" else []
        return _opinion_response(agent, f"{agent} 意见", risks=risks)

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["orthopedic-surgery", "anesthesiology"],
        agent_call_fn=agent_call,
        timeline_id=_TEST_TIMELINE_ID,
    )
    assert session.window_verdict is not None
    assert session.window_verdict["verdict"] == "mdt"
    assert session.window_escalated is False


def test_unknown_timeline_no_verdict_no_crash():
    def agent_call(agent, patient_id, question, context):
        return _opinion_response(agent, "意见")

    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=["orthopedic-surgery"],
        agent_call_fn=agent_call,
        timeline_id="no-such-timeline",
    )
    assert session.status == MDTStatus.COMPLETED
    assert session.window_verdict is None


def test_empty_participants_completes():
    session = MDTOrchestrator().run_session(
        patient_id="P001",
        question="q",
        participants=[],
        agent_call_fn=lambda *a, **k: {},
    )
    assert session.status == MDTStatus.COMPLETED
    assert session.opinions == []


def test_empty_patient_id_completes():
    def agent_call(agent, patient_id, question, context):
        return _opinion_response(agent, "意见")

    session = MDTOrchestrator().run_session(
        patient_id="",
        question="q",
        participants=["orthopedic-surgery"],
        agent_call_fn=agent_call,
    )
    assert session.status == MDTStatus.COMPLETED
    assert session.patient_id == ""


def test_get_mdt_orchestrator_singleton():
    assert mdt_mod.get_mdt_orchestrator() is mdt_mod.get_mdt_orchestrator()


def test_singleton_reset_after_state_clear():
    first = mdt_mod.get_mdt_orchestrator()
    mdt_mod._singleton_state.clear()
    second = mdt_mod.get_mdt_orchestrator()
    assert second is not first
    assert mdt_mod.get_mdt_orchestrator() is second
