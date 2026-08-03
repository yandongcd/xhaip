"""MDT 多学科会诊 — v2.0 协议层入口 (standalone).

This module provides the standalone MDT agent capability.
For embedded MDT, use orthopedics.mdt or haip.a2a.mdt_protocol directly.
"""

from haip.togaf.knowledge_agent import KnowledgeAgent
from orthopedics.mdt import mdt_aggregate, mdt_summary  # noqa: F401

_agent = KnowledgeAgent(agent_name="mdt", department="跨科室")
_GUIDELINES = [
    "国家卫健委《多学科诊疗(MDT)管理制度》",
    "南方医院 MDT 会诊流程规范",
    "xhaip v2.0 MDT Protocol Layer",
]
_agent.rule_engine.load_all()
