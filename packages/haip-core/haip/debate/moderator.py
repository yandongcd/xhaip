"""Moderator — dual LLM judge with appeal mechanism.

Two independent LLM calls (different temperatures/prompts) judge the debate.
If they disagree, any participating agent can appeal → third tiebreaker.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from haip.llm import LLMProvider

logger = logging.getLogger(__name__)

_MODERATOR_PROMPT_A = """你是多学科会诊（MDT）的主持人。以下是各专科医生的**声明**（结构化事实断言）。
请审查这些声明，判断是否存在冲突，给出最终综合建议。

声明列表:
{declarations}

{conflict_section}

请以JSON格式回复:
{{
  "consensus": true/false,
  "resolved_conflicts": ["冲突1的解决方案", ...],
  "verdict": "综合临床建议（2-3句话）",
  "rationale": "判决理由",
  "risk_assessment": "high/medium/low"
}}"""

_MODERATOR_PROMPT_B = """你是多学科会诊（MDT）的独立审查员。请以批判性视角审视以下声明，检查是否有遗漏的风险点或被忽视的临床证据。

声明列表:
{declarations}

{conflict_section}

请以JSON格式回复:
{{
  "consensus": true/false,
  "critical_concerns": ["需要额外关注的临床风险", ...],
  "verdict": "综合临床建议（2-3句话，请从不同角度提供）",
  "rationale": "不同于Moderator A的独特见解",
  "risk_assessment": "high/medium/low"
}}

切记：你应当提出与主主持人不同的见解，关注被忽略的风险。"""

_APPEAL_PROMPT = """你是MDT会诊的终裁专家。两位主持人得出不同结论。请审查双方意见和原始声明，做出最终裁定。

主持人A的裁决:
{verdict_a}

主持人B的裁决:
{verdict_b}

原始声明:
{declarations}

请以JSON格式回复:
{{
  "final_consensus": true/false,
  "final_verdict": "终裁结论（2-3句话）",
  "rationale": "为何选择此结论",
  "remaining_disagreements": ["仍存在的分歧点（若有）"],
  "risk_assessment": "high/medium/low"
}}"""


@dataclass
class ModeratorVote:
    consensus: bool = False
    verdict: str = ""
    rationale: str = ""
    risk_assessment: str = "medium"
    resolved_conflicts: list[str] = field(default_factory=list)
    critical_concerns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "consensus": self.consensus, "verdict": self.verdict,
            "rationale": self.rationale, "risk_assessment": self.risk_assessment,
        }


class Moderator:
    """Dual LLM moderator with appeal tiebreaker."""

    def __init__(self, llm: LLMProvider | None = None):
        self._llm = llm

    @property
    def available(self) -> bool:
        return self._llm is not None

    def judge(self, declarations_text: str, conflict_text: str) -> tuple[ModeratorVote, ModeratorVote]:
        """Run dual moderator and return both votes."""
        if not self._llm:
            return ModeratorVote(), ModeratorVote()

        vote_a = self._judge_a(declarations_text, conflict_text)
        vote_b = self._judge_b(declarations_text, conflict_text)
        return vote_a, vote_b

    def appeal(self, vote_a: ModeratorVote, vote_b: ModeratorVote, declarations_text: str) -> ModeratorVote:
        """Tiebreaker when dual moderators disagree."""
        if not self._llm:
            return vote_a if vote_a.consensus else vote_b

        try:
            prompt = _APPEAL_PROMPT.format(
                verdict_a=json.dumps(vote_a.to_dict(), ensure_ascii=False),
                verdict_b=json.dumps(vote_b.to_dict(), ensure_ascii=False),
                declarations=declarations_text[:3000],
            )
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=2048,
            )
            data = self._parse_json(response.content)
            return ModeratorVote(
                consensus=data.get("final_consensus", False),
                verdict=data.get("final_verdict", ""),
                rationale=data.get("rationale", ""),
                risk_assessment=data.get("risk_assessment", "medium"),
            )
        except Exception as e:
            logger.warning("Appeal failed: %s", e)
            return vote_a

    def _judge_a(self, declarations_text: str, conflict_text: str) -> ModeratorVote:
        return self._judge_with(_MODERATOR_PROMPT_A, declarations_text, conflict_text, 0.2)

    def _judge_b(self, declarations_text: str, conflict_text: str) -> ModeratorVote:
        return self._judge_with(_MODERATOR_PROMPT_B, declarations_text, conflict_text, 0.5)

    def _judge_with(self, prompt_template: str, declarations_text: str, conflict_text: str, temperature: float) -> ModeratorVote:
        try:
            prompt = prompt_template.format(
                declarations=declarations_text[:3000],
                conflict_section=conflict_text,
            )
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature, max_tokens=2048,
            )
            data = self._parse_json(response.content)
            return ModeratorVote(
                consensus=data.get("consensus", False),
                verdict=data.get("verdict", ""),
                rationale=data.get("rationale", ""),
                risk_assessment=data.get("risk_assessment", "medium"),
                resolved_conflicts=data.get("resolved_conflicts", []),
                critical_concerns=data.get("critical_concerns", []),
            )
        except Exception as e:
            logger.warning("Moderator judge failed: %s", e)
            return ModeratorVote()

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text[text.index("\n") + 1:text.rindex("```")] if "```" in text[3:] else text
        start = text.index("{") if "{" in text else 0
        end = text.rindex("}") + 1 if "}" in text else len(text)
        return json.loads(text[start:end])
