"""cardio_risk — RuleEngine-driven clinical reasoning."""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="cardio-risk", department="cardio_risk")
_agent.rule_engine.load_all()


