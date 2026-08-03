"""Stage audit (stage_reporter + quality_control) and Guard/HITL wiring tests."""

from __future__ import annotations

import pytest


def test_stage_audit_score_formula() -> None:
    """score = 100 - failed*30 - critical*50 - warnings*10 (clamped at 0)."""
    from orthopedics.stage_reporter import StageAuditReport
    r = StageAuditReport(stage_id="s1", stage_name="分诊", role="护士长")
    r.add_item("完整性", "failed", "缺分诊记录")
    r.add_item("完整性", "warning", "生命体征未完全记录")
    r.add_item("完整性", "passed", "评估完成")
    r.finalize()
    assert r.score == 60
    assert "不达标" in r.conclusion  # failed outranks warning
    assert "warning" in r.to_dict()["items"][1]["status"]


def test_stage_audit_warning_only() -> None:
    """Warnings only → 需优化 (not 不达标)."""
    from orthopedics.stage_reporter import StageAuditReport
    r = StageAuditReport(stage_id="s1", stage_name="分诊", role="护士长")
    r.add_item("完整性", "warning", "生命体征未完全记录")
    r.finalize()
    assert r.score == 90
    assert "需优化" in r.conclusion


def test_stage_audit_critical_blocked() -> None:
    from orthopedics.stage_reporter import StageAuditReport
    r = StageAuditReport(stage_id="s4", stage_name="多学科评估", role="MDT组长")
    r.add_item("安全", "critical", "心梗急性期仍建议手术")
    r.finalize()
    assert r.score == 50
    assert "不达标" in r.conclusion


def test_full_audit_trail() -> None:
    from orthopedics.stage_reporter import FullAuditTrail, StageAuditReport
    trail = FullAuditTrail(patient_id="P-001")
    for sid in ("s1", "s4"):
        r = StageAuditReport(stage_id=sid, stage_name=f"阶段{sid}", role="x")
        r.add_item("完整性", "passed", "ok")
        r.finalize()
        trail.add_report(r)
    trail.finalize()
    assert trail.overall_score == 100
    assert trail.overall_conclusion == "全部达标"


def test_quality_control_compliance() -> None:
    from orthopedics.quality_control import evaluate_quality_control
    patient = {
        "diagnosis": "左股骨颈骨折",
        "lab_tests": [{"name": "血常规"}, {"name": "凝血功能"}],
        "examinations": [{"name": "心电图"}],
        "past_history": "高血压",
    }
    result = evaluate_quality_control(patient)
    assert result["overall_total"] == 18
    assert 0 <= result["compliance_pct"] <= 100
    assert len(result["stages"]) == 6
    assert isinstance(result["recommendations"], list)


def test_mdt_audit_stage_tool() -> None:
    """audit_stage must return score + report and flag low compliance."""
    from orthopedics.mdt import audit_stage
    result = audit_stage(
        patient_id="P-002",
        diagnosis="左股骨颈骨折",
        lab_tests=[{"name": "血常规"}],
        examinations=[{"name": "心电图"}],
    )
    assert result["status"] == "ok"
    assert 0 <= result["score"] <= 100
    assert result["conclusion"]
    assert result["report"]["items"]
    assert result["needs_human_review"] is True  # low compliance patient


def test_mdt_audit_stage_complete_patient() -> None:
    """More process data → higher score than an empty patient."""
    from orthopedics.mdt import audit_stage
    patient = {
        "diagnosis": "左股骨颈骨折，股骨颈 Garden IV，开放性骨折",
        "past_history": "高血压",
        "present_illness": "摔倒后左髋疼痛，需急诊评估骨折，生命体征平稳",
        "lab_tests": [
            {"name": "血常规"}, {"name": "凝血功能"}, {"name": "心肌酶谱"},
            {"name": "肾功能"}, {"name": "电解质"}, {"name": "血糖"},
        ],
        "examinations": [{"name": "心电图"}, {"name": "髋部X线"}, {"name": "胸部CT"}],
    }
    rich = audit_stage(patient=patient, patient_id="P-003")
    empty = audit_stage(patient_id="P-000")
    assert rich["status"] == "ok"
    assert rich["raw_score"] > empty["raw_score"]
    assert rich["score"] >= 0


def test_guard_stage_score_blocked() -> None:
    """Guard blocks when stage score < 40 (critical/failed items)."""
    from haip.guard.verifier import GuardVerifier
    v = GuardVerifier()
    r = v.verify("建议立即手术", scenario="手术决策", stage_score=30)
    assert r.passed is False
    assert any("阶段审计不达标" in f for f in r.flags)


def test_guard_stage_score_review() -> None:
    """Guard flags human review when 40 <= stage score < 60."""
    from haip.guard.verifier import GuardVerifier
    v = GuardVerifier()
    r = v.verify("建议观察", scenario="门诊评估", stage_score=50)
    assert r.passed is True
    assert r.requires_human_review is True


def test_guard_stage_score_ok_no_effect() -> None:
    """High stage score does not affect guard result."""
    from haip.guard.verifier import GuardVerifier
    v = GuardVerifier()
    r = v.verify("建议观察", scenario="门诊评估", stage_score=85)
    assert r.passed is True
    assert r.requires_human_review is False


def test_guard_stage_score_backward_compat() -> None:
    """verify() without stage_score behaves exactly as before."""
    from haip.guard.verifier import GuardVerifier
    v = GuardVerifier()
    r = v.verify("建议观察", scenario="门诊评估")
    assert r.passed is True


def test_hitl_stage_score_triggers() -> None:
    """HITLHook pauses when stage_score is below stage_required_below."""
    from haip.loop.hitl import HITLHook
    from haip.loop.hooks import HookContext
    hook = HITLHook()
    ctx = HookContext(agent_name="orthopedic-surgery", metadata={"stage_score": 55})
    out = hook.check(ctx, "建议择期手术")
    assert out is not None
    assert "[HITL PENDING]" in out
    assert "阶段审计评分" in out
    assert ctx.metadata["hitl_pending"] is True


def test_hitl_stage_score_pass() -> None:
    """High stage score with good confidence → no HITL."""
    from haip.loop.hitl import HITLHook
    from haip.loop.hooks import HookContext
    hook = HITLHook()
    ctx = HookContext(agent_name="orthopedic-surgery", metadata={"stage_score": 90})
    assert hook.check(ctx, "建议择期手术") is None


def test_hitl_stage_score_none_ok() -> None:
    """No stage_score in metadata → old behavior (no HITL when confidence ok)."""
    from haip.loop.hitl import HITLHook
    from haip.loop.hooks import HookContext
    hook = HITLHook()
    ctx = HookContext(agent_name="x", metadata={})
    assert hook.check(ctx, "ok") is None
