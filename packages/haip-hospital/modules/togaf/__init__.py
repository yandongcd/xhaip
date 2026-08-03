"""TOGAF 架构治理智能体 — 企业架构元模型 / 4A 构建 / 布局 / 审计 / 模板."""

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="togaf", department="信息中心")
_GUIDELINES = [
    "TOGAF 10 Standard (The Open Group 2022)",
    "医院信息互联互通标准化成熟度测评方案 (2020)",
    "HL7 FHIR R4 互操作性标准",
    "等保三级 GB/T 22239-2019",
]
_agent.rule_engine.load_all()

from .handlers import *  # noqa: F401, F403
