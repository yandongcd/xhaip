"""ReAct AgentLoop — LLM + Tool 执行循环.

核心流程:
  1. 将用户 query + system_prompt + 可用 tool schemas 发给 LLM
  2. LLM 返回 final_answer → 结束
  3. LLM 返回 tool_call → 执行 tool → 将结果追加到 messages → 回到步骤 1
  4. 最多循环 max_steps 步
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from haip.llm import LLMProvider
from haip.tools.registry import execute as execute_tool, list_schemas


@dataclass
class LoopResult:
    reply: str = ""
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


class AgentLoop:
    """ReAct 模式: LLM 推理 → Tool 执行 → 迭代循环。"""

    def __init__(
        self,
        llm: LLMProvider,
        system_prompt: str = "你是一个医疗AI助手，请用中文回答。",
        max_steps: int = 5,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        agent_name: str = "default",
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.agent_name = agent_name

    def run(self, query: str) -> LoopResult:
        import time
        t0 = time.perf_counter()
        result = LoopResult()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]
        tool_schemas = self._build_tool_schemas()

        for step in range(self.max_steps):
            resp = self.llm.chat(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            result.input_tokens += resp.input_tokens
            result.output_tokens += resp.output_tokens

            if not resp.tool_calls:
                result.reply = resp.content
                result.steps = step + 1
                break

            # 执行所有 tool calls
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": resp.content or ""}
            tc_list = []
            for tc in resp.tool_calls:
                tc_list.append({
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
                })
                tool_result = execute_tool(tc.name, **tc.arguments)
                result.tool_calls.append({
                    "step": step + 1, "tool": tc.name,
                    "args": tc.arguments, "success": tool_result.success,
                    "output": tool_result.output or tool_result.error,
                })
                messages.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": tool_result.output or tool_result.error or "done",
                })
            if tc_list:
                assistant_msg["tool_calls"] = tc_list
            messages.append(assistant_msg)
        else:
            result.reply = "已达到最大推理步数，请重新描述问题。"
            result.steps = self.max_steps
            result.error = "max_steps_exceeded"

        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        schemas = list_schemas()
        result = []
        for s in schemas:
            params = s.get("parameters", {})
            properties = {}
            required = []
            for name, spec in params.items():
                if isinstance(spec, dict):
                    properties[name] = spec
                else:
                    properties[name] = {"type": "string", "description": str(spec)}
                required.append(name)
            result.append({
                "name": s["name"],
                "description": s["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            })
        return result
