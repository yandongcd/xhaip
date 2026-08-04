"""MDT — Multi-Disciplinary Team collaboration handler (v2.0 protocol layer).

Uses haip.a2a.mdt_protocol + mdt_orchestrator for structured MDT sessions.
Replaces v1.x standalone agent with collaboration protocol per 10-round expert consensus.
"""

from __future__ import annotations

from haip.a2a.mdt_orchestrator import get_mdt_orchestrator
from haip.a2a.mdt_protocol import MDTStatus


def mdt_aggregate(**kwargs) -> dict:
    """MDT 多学科会诊聚合 — fan-out to participant agents, detect conflicts, reach consensus."""
    patient_id = kwargs.get("patient_id", "")
    question = kwargs.get("chief_complaint", kwargs.get("question", ""))

    # Determine participants
    _EVAL_TO_AGENT = {
        "cardio": "cardio-risk",
        "anesthesia": "anesthesia",
        "ortho": "orthopedic-surgery",
        "orthopedic": "orthopedic-surgery",
        "pain": "pain-management",
    }
    participants = []
    for key in ["cardio_eval", "anesthesia_eval", "ortho_eval", "orthopedic_eval", "pain_eval"]:
        if kwargs.get(key):
            agent = _EVAL_TO_AGENT[key.replace("_eval", "")]
            if agent and agent not in participants:
                participants.append(agent)

    if not participants:
        # Default participants based on available eval data
        if kwargs.get("cardio_eval"):
            participants.append("cardio-risk")
        if kwargs.get("anesthesia_eval"):
            participants.append("anesthesia")
        if kwargs.get("ortho_eval") or kwargs.get("orthopedic_eval"):
            participants.append("orthopedic-surgery")
        if kwargs.get("pain_eval"):
            participants.append("pain-management")

    context = {k: v for k, v in kwargs.items() if k not in ("patient_id", "chief_complaint", "question")}

    # 可选: 时间窗口追踪 (haip.time_window), 如 'timeline-hip-fracture-48h'
    timeline_id = kwargs.get("timeline_id", "") or None

    orchestrator = get_mdt_orchestrator()
    session = orchestrator.run_session(
        patient_id=patient_id,
        question=question or "MDT多学科会诊评估",
        participants=participants or ["cardio-risk", "anesthesia", "orthopedic-surgery"],
        context=context,
        timeout=120,
        timeline_id=timeline_id,
    )

    return {
        "status": "ok",
        "agent": "mdt",
        "patient_id": patient_id,
        "summary": session.consensus or "MDT会诊完成 — 各专科意见已汇总",
        "session_id": session.session_id,
        "participants": session.participants,
        "window_verdict": session.window_verdict,
        "window_escalated": session.window_escalated,
        "opinions": [
            {
                "agent": o.agent_name,
                "recommendation": o.recommendation,
                "confidence": o.confidence,
                "evidence": o.evidence_level,
                "citations": o.citations,
                "risks": o.risks,
            }
            for o in session.opinions
        ],
        "divergences": [
            {
                "type": d.conflict_type.value,
                "agents": f"{d.agent_a} vs {d.agent_b}",
                "severity": d.severity,
                "resolution": d.resolution_strategy,
            }
            for d in session.divergences
        ],
        "deadlocked": session.status == MDTStatus.DEADLOCKED,
        "needs_human_review": len(session.divergences) > 0 or session.window_escalated,
        "stage_audit": _stage_audit_attached(kwargs),
    }


def _stage_audit_attached(kwargs: dict) -> dict | None:
    """Attach stage audit result when patient data is available in kwargs."""
    patient = kwargs.get("patient")
    has_patient_data = isinstance(patient, dict) and patient or any(
        kwargs.get(k) for k in ("diagnosis", "lab_tests", "examinations")
    )
    if not has_patient_data:
        return None
    audit = audit_stage(**kwargs)
    return {
        "score": audit["score"],
        "conclusion": audit["conclusion"],
        "compliance_pct": audit["compliance_pct"],
        "needs_human_review": audit["needs_human_review"],
    }


def mdt_summary(**kwargs) -> dict:
    """MDT 纪要生成 — format the session results as structured markdown."""
    result = kwargs.get("mdt_result")
    if not isinstance(result, dict):
        result = mdt_aggregate(**kwargs)

    opinions_md = ""
    for o in result.get("opinions", []):
        opinions_md += f"- **{o['agent']}** (置信度 {o['confidence']:.0%}): {o['recommendation']}\n"
        if o.get("citations"):
            opinions_md += f"  引用: {', '.join(o['citations'])}\n"

    divergences_md = ""
    for d in result.get("divergences", []):
        divergences_md += f"- ⚠️ {d['type']}: {d['agents']} ({d['severity']})\n"

    markdown = f"""# MDT 多学科会诊纪要

**会诊结论**: {result.get('summary', '')}

## 各专科意见
{opinions_md}

## 分歧记录
{divergences_md if divergences_md else '无重大分歧'}

---

> 本纪要由 AI 辅助生成，需经 MDT 首席组长审核确认
"""

    return {
        "status": "ok",
        "agent": "mdt",
        "summary": result.get("summary", ""),
        "markdown": markdown,
        "needs_human_review": result.get("needs_human_review", False),
    }


def audit_stage(**kwargs) -> dict:
    """阶段审计评分 — 全流程质控 + Stage Audit 评分 (score = 100 - failed*30 - critical*50 - warnings*10).

    从 kwargs 中提取患者数据 (patient dict 或拆分的诊断/检验/检查字段),
    运行 quality_control.evaluate_quality_control 生成质控报告,
    组装 StageAuditReport 输出评分与结论. 评分可供 Guard/HITL 门控.

    Args (kwargs):
        patient: 完整患者 dict (优先)
        diagnosis / lab_tests / examinations / past_history / present_illness: 拆分字段
        stage_id / stage_name / role: 审计元信息 (默认 s4/多学科评估/MDT)

    Returns:
        {status, score, conclusion, compliance_pct, overall_passed, overall_total,
         recommendations, report, stage_id}
    """
    from .quality_control import evaluate_quality_control
    from .stage_reporter import StageAuditReport

    patient = kwargs.get("patient") or {}
    if not isinstance(patient, dict):
        patient = {}
    if not patient:
        patient = {k: kwargs.get(k) for k in (
            "diagnosis", "lab_tests", "examinations", "past_history",
            "present_illness", "chief_complaint", "age", "gender",
        ) if kwargs.get(k) is not None}

    qc = evaluate_quality_control(patient)

    stage_id = kwargs.get("stage_id", "s4")
    stage_name = kwargs.get("stage_name", "多学科评估 (MDT)")
    role = kwargs.get("role", "MDT 首席组长")

    report = StageAuditReport(stage_id=stage_id, stage_name=stage_name, role=role)
    for stage in qc["stages"]:
        for cp in stage["checkpoints"]:
            status = "passed" if cp["passed"] else "failed"
            report.add_item(
                category=f"{stage['name']}-{cp['id']}",
                status=status,
                detail=cp["description"],
                suggestion=cp["criteria"],
                guideline_ref=cp.get("guide_ref", ""),
                evidence=str(cp.get("evidence_found", False)),
            )
    report.finalize()

    # raw_score: 未 clamp 的原始分，保留区分度 (clamp 后中段流程均为 0)
    failed_n = sum(1 for i in report.items if i.status == "failed")
    critical_n = sum(1 for i in report.items if i.status == "critical")
    warning_n = sum(1 for i in report.items if i.status == "warning")
    raw_score = 100 - failed_n * 30 - critical_n * 50 - warning_n * 10

    needs_human = report.score < 60
    return {
        "status": "ok",
        "agent": "mdt",
        "score": report.score,
        "raw_score": raw_score,
        "conclusion": report.conclusion,
        "stage_id": stage_id,
        "stage_name": stage_name,
        "compliance_pct": qc["compliance_pct"],
        "overall_passed": qc["overall_passed"],
        "overall_total": qc["overall_total"],
        "recommendations": qc["recommendations"][:10],
        "report": report.to_dict(),
        "needs_human_review": needs_human,
    }
