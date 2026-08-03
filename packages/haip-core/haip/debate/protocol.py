"""Debate protocol — context formatting for debate rounds.

Injects only conflict declarations (JSON, ~200 tokens) into agent system prompts,
not full agent outputs. This prevents context window exhaustion.
"""

from __future__ import annotations

import json
import logging

from haip.debate.conflict import Conflict
from haip.debate.declaration import Declaration

logger = logging.getLogger(__name__)

_DEBATE_ROUND_PROMPT = """你是{agent_role}专家。以下是多学科会诊中发现的**与你相关的声明冲突**。

你的声明:
{my_declarations}

冲突声明（来自其他医生）:
{conflict_declarations}

请逐条回应:
- 同意对方的观点 → 写 "AGREE: [声明ID]"
- 不同意 → 写 "DISAGREE: [声明ID], 理由: ..."
- 修改你的观点 → 写 "REVISE: [我的声明ID] → 新结论: ..."

只输出结构化回应，不要重新输出完整评估。"""


class DebateProtocol:
    """Formats debate context for each agent in a debate round."""

    @staticmethod
    def declarations_text(declarations: list[Declaration], include_agent: str | None = None) -> str:
        """Format declarations as readable text."""
        filtered = [d for d in declarations if include_agent is None or d.agent == include_agent]
        lines = []
        for d in filtered:
            lines.append(
                f"  [{d.id}] {d.agent}: {d.metric} = {d.value} ({d.category}), "
                f"置信度={d.confidence:.0%}, 依据={d.evidence}"
            )
        return "\n".join(lines) if lines else "（无声明）"

    @staticmethod
    def conflicts_text(conflicts: list[Conflict]) -> str:
        """Format conflicts as readable text."""
        if not conflicts:
            return "（未检测到冲突）"
        lines = ["检测到以下冲突:"]
        for i, c in enumerate(conflicts):
            lines.append(f"  [冲突{i + 1}] {c.summary()}")
        return "\n".join(lines)

    @staticmethod
    def compact_declarations(declarations: list[Declaration]) -> str:
        """Ultra-compact JSON format for context injection (~50 chars per declaration)."""
        items = [
            {"id": d.id, "m": d.metric, "v": d.value, "c": d.category, "a": d.agent}
            for d in declarations
        ]
        return json.dumps(items, ensure_ascii=False)

    def build_debate_prompt(
        self,
        agent_name: str,
        agent_role: str,
        my_declarations: list[Declaration],
        all_declarations: list[Declaration],
        conflicts: list[Conflict],
    ) -> str:
        """Build a debate round prompt for a specific agent."""
        conflict_ids = set()
        for c in conflicts:
            if c.agent_a == agent_name or c.agent_b == agent_name:
                conflict_ids.add(c.decl_a_id)
                conflict_ids.add(c.decl_b_id)

        conflict_decls = [d for d in all_declarations if d.id in conflict_ids and d.agent != agent_name]

        return _DEBATE_ROUND_PROMPT.format(
            agent_role=agent_role,
            my_declarations=self.declarations_text(my_declarations, agent_name),
            conflict_declarations=self.declarations_text(conflict_decls),
        )

    @staticmethod
    def synthesize_final(
        verdict: str,
        declarations: list[Declaration],
        votes_agreed: bool,
        appeal_used: bool,
    ) -> str:
        """Synthesize final MDT recommendation."""
        lines = [
            "## MDT 多学科会诊结论",
            "",
            verdict,
            "",
            "### 各专科声明",
            DebateProtocol.declarations_text(declarations),
            "",
            f"- 主持人一致: {'是' if votes_agreed else '否（已上诉）'}",
            f"- 终裁机制: {'上诉裁决' if appeal_used else '一致裁决'}",
        ]
        return "\n".join(lines)
