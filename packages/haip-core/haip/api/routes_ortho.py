"""骨科 v1 API — 从 web_server 拆出 (P1-6)."""

from __future__ import annotations

from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/v1/orthopedic", tags=["orthopedic-v1"])


@router.post("/classify")
def ortho_classify(payload: dict = Body(default_factory=dict)):
    """骨折分型 (Garden/Evans/AO)"""
    from modules.orthopedics import assess
    return assess(**payload)


@router.post("/assess")
def ortho_assess(payload: dict = Body(default_factory=dict)):
    """术前综合评估"""
    from modules.orthopedics import evaluate
    return evaluate(**payload)


@router.post("/plan")
def ortho_plan(payload: dict = Body(default_factory=dict)):
    """手术方案推荐"""
    from modules.orthopedics import plan
    return plan(**payload)


@router.post("/timing")
def ortho_timing(payload: dict = Body(default_factory=dict)):
    """T2 手术时机决策"""
    from modules.orthopedics import evaluate_timing
    return evaluate_timing(**payload)


@router.post("/complications")
def ortho_complications(payload: dict = Body(default_factory=dict)):
    """并发症风险预测"""
    from modules.orthopedics import predict_complications
    return predict_complications(**payload)


@router.post("/mdt")
def ortho_mdt(payload: dict = Body(default_factory=dict)):
    """MDT 多学科会诊聚合"""
    from modules.orthopedics.mdt import mdt_aggregate
    return mdt_aggregate(**payload)


@router.post("/pain")
def ortho_pain(payload: dict = Body(default_factory=dict)):
    """疼痛评估"""
    from modules.pain_management import assess_pain
    return assess_pain(**payload)


@router.post("/rehab")
def ortho_rehab(payload: dict = Body(default_factory=dict)):
    """康复跟踪"""
    from modules.orthopedics.extended import rehab_track
    return rehab_track(**payload)


@router.post("/followup")
def ortho_followup(payload: dict = Body(default_factory=dict)):
    """随访计划"""
    from modules.orthopedics import followup_plan
    return followup_plan(**payload)
