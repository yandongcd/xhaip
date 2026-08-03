"""Lifecycle Hooks — ADK 风格的六节点钩子系统.

钩子插入点:
  before_agent  → [Agent 执行] → after_agent
    ├── before_llm  → [LLM 调用] → after_llm
    └── before_tool → [Tool 执行] → after_tool

每个钩子可通过返回非 None 值跳过/替代默认行为:
  before_agent: return str → 跳过 agent，使用此作为回复
  before_llm:   return ChatResponse → 跳过 LLM 调用
  before_tool:  return dict → 跳过 tool 执行，使用此作为结果
  after_agent:  return str → 替换 agent 最终输出
  after_llm:    return ChatResponse → 替换 LLM 响应
  after_tool:   return dict → 替换 tool 结果
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from haip.llm import ChatResponse

# 钩子签名
BeforeAgentHook = Callable[["HookContext"], str | None]
AfterAgentHook = Callable[["HookContext", str], str | None]  # (ctx, reply) -> modified_reply | None
BeforeLLMHook = Callable[["HookContext", list[dict], dict | None], ChatResponse | None]
AfterLLMHook = Callable[["HookContext", ChatResponse], ChatResponse | None]
BeforeToolHook = Callable[["HookContext", str, dict], dict | None]  # (ctx, name, args) -> mock_result | None
AfterToolHook = Callable[["HookContext", str, dict, Any], dict | None]  # (ctx, name, args, result) -> modified_result | None


@dataclass
class HookContext:
    """钩子上下文 — 钩子函数可访问的信息."""
    agent_name: str = ""
    invocation_id: str = ""
    session_id: str = ""
    step: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookChain:
    """钩子链 — 管理所有生命周期钩子."""

    before_agent: list[BeforeAgentHook] = field(default_factory=list)
    after_agent: list[AfterAgentHook] = field(default_factory=list)
    before_llm: list[BeforeLLMHook] = field(default_factory=list)
    after_llm: list[AfterLLMHook] = field(default_factory=list)
    before_tool: list[BeforeToolHook] = field(default_factory=list)
    after_tool: list[AfterToolHook] = field(default_factory=list)

    def add(self, position: str, hook: Callable) -> None:
        """注册钩子. position: before_agent|after_agent|before_llm|after_llm|before_tool|after_tool."""
        target = getattr(self, position, None)
        if target is not None:
            target.append(hook)

    def remove(self, position: str, hook: Callable) -> None:
        target = getattr(self, position, None)
        if target is not None and hook in target:
            target.remove(hook)

    def run_before_agent(self, ctx: HookContext) -> str | None:
        """返回非 None 则跳过 Agent 执行."""
        for hook in self.before_agent:
            result = hook(ctx)
            if result is not None:
                return result
        return None

    def run_after_agent(self, ctx: HookContext, reply: str) -> str:
        for hook in self.after_agent:
            modified = hook(ctx, reply)
            if modified is not None:
                reply = modified
        return reply

    def run_before_llm(
        self, ctx: HookContext, messages: list[dict], tools: dict | None,
    ) -> ChatResponse | None:
        for hook in self.before_llm:
            result = hook(ctx, messages, tools)
            if result is not None:
                return result
        return None

    def run_after_llm(self, ctx: HookContext, response: ChatResponse) -> ChatResponse:
        for hook in self.after_llm:
            modified = hook(ctx, response)
            if modified is not None:
                response = modified
        return response

    def run_before_tool(self, ctx: HookContext, name: str, args: dict) -> dict | None:
        for hook in self.before_tool:
            result = hook(ctx, name, args)
            if result is not None:
                return result
        return None

    def run_after_tool(
        self, ctx: HookContext, name: str, args: dict, result: Any,
    ) -> dict | None:
        for hook in self.after_tool:
            modified = hook(ctx, name, args, result)
            if modified is not None:
                result = modified
        return result
