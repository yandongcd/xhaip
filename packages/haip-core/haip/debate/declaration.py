"""Declaration layer — structured fact extraction from agent outputs.

Uses LLM to extract verifiable, structured declarations from each agent's
free-text output. Declarations are the atomic unit of debate — agents can
only reference declarations by ID, preventing fact cascade pollution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from haip.llm import LLMProvider

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """你是临床事实提取器。从以下医疗Agent输出中提取所有**可验证的事实断言**，返回JSON数组。

每条断言格式:
{
  "id": "D{序号}",
  "metric": "评估维度",
  "value": "结论",
  "category": "分类值",
  "evidence": "依据的检验值或指南",
  "confidence": 0.0-1.0
}

规则:
- 只提取确定的诊断结论、风险评级、治疗建议
- metric取: surgical_timing|risk_level|diagnosis|treatment|complication|anesthesia|nursing
- category取: emergency|urgent|elective|high|medium|low|normal|abnormal|recommend|avoid
- 不提取主观描述或模糊建议
- 只输出JSON数组，不要解释

Agent输出:
{output}

声明数组:"""


@dataclass
class Declaration:
    id: str
    agent: str
    metric: str
    value: str
    category: str
    evidence: str = ""
    confidence: float = 0.5
    raw_output: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "agent": self.agent, "metric": self.metric,
            "value": self.value, "category": self.category, "evidence": self.evidence,
            "confidence": self.confidence,
        }


class DeclarationLayer:
    """LLM-powered structured declaration extractor."""

    def __init__(self, llm: LLMProvider | None = None):
        self._llm = llm

    @property
    def available(self) -> bool:
        return self._llm is not None

    def extract(self, agent_name: str, output_text: str) -> list[Declaration]:
        """Extract structured declarations from an agent's output."""
        if not self._llm or not output_text.strip():
            return self._empty_declarations(agent_name)

        try:
            prompt = _EXTRACTION_PROMPT.format(output=output_text[:4000])
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
            )
            raw = response.content.strip()
            raw = raw[raw.index("["):raw.rindex("]") + 1] if "[" in raw and "]" in raw else raw
            items = json.loads(raw)
            if not isinstance(items, list):
                items = [items]

            return [
                Declaration(
                    id=f"D{agent_name}_{i}",
                    agent=agent_name,
                    metric=item.get("metric", "unknown"),
                    value=str(item.get("value", "")),
                    category=item.get("category", "unknown"),
                    evidence=item.get("evidence", ""),
                    confidence=float(item.get("confidence", 0.5)),
                    raw_output=output_text[:500],
                )
                for i, item in enumerate(items)
            ]
        except Exception as e:
            logger.warning("Declaration extraction failed for %s: %s", agent_name, e)
            return self._empty_declarations(agent_name)

    def extract_batch(self, outputs: dict[str, str]) -> list[Declaration]:
        """Extract declarations from multiple agent outputs."""
        all_decls = []
        for agent_name, output in outputs.items():
            all_decls.extend(self.extract(agent_name, output))
        return all_decls

    @staticmethod
    def _empty_declarations(agent_name: str) -> list[Declaration]:
        return [
            Declaration(
                id=f"D{agent_name}_0", agent=agent_name,
                metric="unknown", value="unable_to_extract",
                category="unknown", confidence=0.0,
            )
        ]
