"""X2: Context budget manager — prevents token overflow in unified pipeline.

Allocates LLM context window budget across RAG, debate, data, and conversation.
Truncation priorities: conversation history > RAG patients > debate context.
"""

from __future__ import annotations

CONTEXT_BUDGET = 28000  # 32K window, reserve 4K for output

DEFAULT_ALLOCATIONS = {
    "system_prompt_base": 800,
    "patient_data": 500,
    "rag_injection": 1000,
    "debate_context": 1500,
    "conversation_history": 2000,
    "reserved_output": 4000,
}

TRUNCATION_PRIORITY = [
    "conversation_history",  # truncated first (oldest messages)
    "debate_context",         # truncated second
    "rag_injection",          # truncated third (keep high-trust items)
    "patient_data",           # try not to truncate
    "system_prompt_base",     # never truncate
]


class ContextBudget:
    """Token budget allocator for unified pipeline LLM context windows."""

    def __init__(self, total: int = CONTEXT_BUDGET):
        self._total = total
        self._allocated: dict[str, int] = dict(DEFAULT_ALLOCATIONS)

    @property
    def remaining(self) -> int:
        used = sum(self._allocated.values())
        return max(0, self._total - used)

    def allocate(self, component: str, requested: int) -> int:
        """Allocate tokens for a component. Returns actual allocation (may be less)."""
        limit = self._allocated.get(component, 1000)
        return min(requested, limit)

    def check_overflow(self) -> bool:
        return sum(self._allocated.values()) > self._total

    def suggest_truncation(self) -> str | None:
        """Return which component to truncate first, or None if within budget."""
        if not self.check_overflow():
            return None
        for component in TRUNCATION_PRIORITY:
            if self._allocated.get(component, 0) > 200:
                return component
        return None

    def resize(self, component: str, tokens: int):
        self._allocated[component] = max(0, tokens)

    def snapshot(self) -> dict:
        return {
            "total": self._total,
            "allocated": dict(self._allocated),
            "used": sum(self._allocated.values()),
            "remaining": self.remaining,
            "overflow": self.check_overflow(),
        }
