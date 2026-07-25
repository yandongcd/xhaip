"""LLM Provider 抽象 — 所有 LLM 调用的统一接口."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """LLM 调用的统一抽象。上层组件只依赖此接口，不关心底层实现。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        """非流式对话请求。"""

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Iterator[ChatResponse]:
        """流式对话请求，yield 逐块 ChatResponse。"""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LLMProvider:
        """工厂方法: 从配置字典创建 Provider。
        配置格式:
            {"provider": "deepseek", "api_key": "...", "model": "deepseek-chat"}
        或:
            {"provider": "mock", "fixtures": {...}}
        """
        provider_name = config.get("provider", "mock")
        if provider_name == "deepseek":
            from haip.llm.deepseek import DeepSeekProvider
            return DeepSeekProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "deepseek-chat"),
                base_url=config.get("base_url") or config.get("api_base", "https://api.deepseek.com"),
            )
        if provider_name == "mock":
            from haip.llm.mock import MockProvider
            return MockProvider(fixtures=config.get("fixtures", {}))
        raise ValueError(f"Unknown provider: {provider_name}")
