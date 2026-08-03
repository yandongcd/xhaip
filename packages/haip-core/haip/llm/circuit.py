"""Fail-closed LLM provider — returns structured errors instead of fabricated content.

Replaces the previous mock fallback pattern. In production, when all LLM providers
are unavailable, this provider returns a clear SERVICE_UNAVAILABLE error rather
than generating fabricated clinical content.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from haip.llm import DEFAULT_MAX_TOKENS, ChatResponse, LLMProvider


class FailClosedProvider(LLMProvider):
    """Fail-closed provider — NEVER returns fabricated content.

    In development mode (HAIP_TEST_MODE=true), returns neutral placeholder text
    for testing workflows. In production mode, returns SERVICE_UNAVAILABLE.
    """

    def __init__(self, mode: str = "production"):
        self._mode = mode

    def _build_response(self) -> ChatResponse:
        if self._mode == "test":
            return ChatResponse(
                content="[系统通知] LLM 服务暂不可用，请稍后重试。此响应不包含任何临床建议。",
                model="fail-closed",
                finish_reason="error",
            )
        return ChatResponse(
            content="",
            model="fail-closed",
            finish_reason="error",
        )

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> ChatResponse:
        return self._build_response()

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Iterator[ChatResponse]:
        yield self._build_response()


def is_fail_closed_response(response: ChatResponse) -> bool:
    """Check if a response came from the fail-closed provider."""
    return response.model == "fail-closed" or response.finish_reason == "error"
