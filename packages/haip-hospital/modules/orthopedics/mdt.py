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
    participants = []
    for key in ["cardio_eval", "anesthesia_eval", "ortho_eval", "pain_eval"]:
        if kwargs.get(key):
            participants.append(key.replace("_eval", "").replace("cardio", "cardio-risk"))

    if not participants:
        # Default participants based on available eval data
        if kwargs.get("cardio_eval"):
            participants.append("cardio-risk")
        if kwargs.get("anesthesia_eval"):
            participants.append("anesthesia")
        if kwargs.get("ortho_eval"):
            participants.append("orthopedic-surgery")
        if kwargs.get("pain_eval"):
            participants.append("pain-management")

    context = {k: v for k, v in kwargs.items() if k not in ("patient_id", "chief_complaint", "question")}

    orchestrator = get_mdt_orchestrator()
    session = orchestrator.run_session(
        patient_id=patient_id,
        question=question or "MDT多学科会诊评估",
        participants=participants or ["cardio-risk", "anesthesia", "orthopedic-surgery"],
        context=context,
        timeout=120,
    )

    return {
        "status": "ok",
        "agent": "mdt",
        "summary": session.consensus or "MDT会诊完成 — 各专科意见已汇总",
        "session_id": session.session_id,
        "participants": session.participants,
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
        "needs_human_review": len(session.divergences) > 0,
    }


def mdt_summary(**kwargs) -> dict:
    """MDT 纪要生成 — format the session results as structured markdown."""
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
