"""anesthesia-risk — 围术期麻醉评估 (thin wrapper, handlers in anesthesia module)."""
from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="anesthesia-risk", department="跨科室")
_GUIDELINES = [
    "ASA Physical Status Classification System (2020)",
    "2022 ASA Difficult Airway Algorithm",
    "ASRA 抗凝指南 (2025)",
    "中国麻醉学指南与专家共识 (2024)",
]
_agent.rule_engine.load_all()
