"""Mock LLM Provider — 测试用，返回预制响应."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from haip.llm import DEFAULT_MAX_TOKENS, ChatResponse, LLMProvider, ToolCall


class MockProvider(LLMProvider):
    def __init__(self, fixtures: dict[str, Any] | None = None):
        self.fixtures = fixtures or {}
        self.call_history: list[dict[str, Any]] = []

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> ChatResponse:
        self.call_history.append({
            "messages_count": len(messages),
            "tools_count": len(tools) if tools else 0,
            "temperature": temperature,
            "last_user_msg": self._extract_last_user(messages),
        })

        key = self._match_fixture(messages)
        if key and key in self.fixtures:
            return self._from_fixture(self.fixtures[key])

        return ChatResponse(
            content="Mock response: I am a simulated medical AI assistant.",
            model="mock-model",
        )

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> Iterator[ChatResponse]:
        response = self.chat(messages, tools, temperature, max_tokens)
        # Simulate streaming by yielding content in chunks
        words = response.content.split()
        chunk_size = max(1, len(words) // 3)
        for i in range(0, len(words), chunk_size):
            yield ChatResponse(
                content=" ".join(words[i:i + chunk_size]),
                model=response.model,
            )

    def _match_fixture(self, messages: list[dict[str, Any]]) -> str | None:
        last = self._extract_last_user(messages)
        for key in self.fixtures:
            if key.lower() in last.lower():
                return key
        return None

    def _extract_last_user(self, messages: list[dict[str, Any]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
        return ""

    def _from_fixture(self, fixture: dict[str, Any]) -> ChatResponse:
        tool_calls: list[ToolCall] = []
        for tc in fixture.get("tool_calls", []):
            tool_calls.append(ToolCall(
                id=tc.get("id", f"call_{len(tool_calls)}"),
                name=tc["name"],
                arguments=tc.get("arguments", {}),
            ))
        return ChatResponse(
            content=fixture.get("content", ""),
            tool_calls=tool_calls,
            model="mock-model",
            input_tokens=fixture.get("input_tokens", 0),
            output_tokens=fixture.get("output_tokens", 0),
        )


class SeqMockProvider(MockProvider):
    """序列化 Mock: 按顺序返回预设的 ChatResponse (支持 tool_calls).

    Usage:
        mock = SeqMockProvider([
            ChatResponse(content='', tool_calls=[ToolCall(id='1', name='timing_decision', arguments={})]),
            ChatResponse(content='基于工具结果...'),
        ])
        # 第1次 chat → tool_call, 第2次 chat → 文本回复
    """

    def __init__(self, responses: list[ChatResponse]):
        super().__init__({})
        self.responses = responses
        self._idx = 0

    def chat(self, messages=None, tools=None, temperature=0.3, max_tokens=4096):
        if self._idx < len(self.responses):
            resp = self.responses[self._idx]
            self._idx += 1
            return resp
        return ChatResponse(content="Analysis complete.", model="mock-seq")
