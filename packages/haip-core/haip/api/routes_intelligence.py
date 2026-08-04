"""智能体能力域 (harness/meta-harness/decide/plan/memory) — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

from fastapi import APIRouter, Body

router = APIRouter(tags=["intelligence"])


@router.get("/api/harness")
def harness_report():
    from haip.clinical_harness import ClinicalHarness
    return ClinicalHarness().run()


@router.get("/api/meta-harness")
def meta_harness_report():
    from haip.meta_harness import get_meta_harness
    return get_meta_harness().run_full_cycle()


@router.post("/api/decide/{agent_name}")
def decide(agent_name: str, payload: dict = Body(default_factory=dict)):
    """自主决策: POST patient data, get clinical decision."""
    from haip.decision import get_decision_engine
    engine = get_decision_engine()
    return engine.decide(agent_name, payload)


@router.post("/api/plan/{agent_name}")
def plan_workflow(agent_name: str, payload: dict = Body(default_factory=dict)):
    """智能规划: POST patient data, get dynamic workflow plan."""
    from haip.planner import get_workflow_planner
    planner = get_workflow_planner()
    return planner.plan(agent_name, payload)


@router.get("/api/memory/insights/{agent_name}")
def agent_insights(agent_name: str):
    """Agent持续探索 — 决策历史洞察."""
    from haip.memory import get_memory
    return get_memory().insights(agent_name)


@router.get("/api/memory/global")
def global_insights():
    """全量Agent学习洞察 — TOGAF治理用."""
    from haip.memory import get_memory
    return get_memory().global_insights()
