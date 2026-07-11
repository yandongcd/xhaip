"""ReAct AgentLoop — LLM + Tool 执行循环.

核心流程:
  1. 将用户 query + system_prompt + 可用 tool schemas 发给 LLM
  2. LLM 返回 final_answer → 结束
  3. LLM 返回 tool_call → 通过 tool_executor 执行 → 摘要化结果 → 回到步骤 1
  4. 最多循环 max_steps 步，超出 token 预算中止

修复记录:
  R1: _build_tool_schemas 不再将所有 params 标记为 required — 仅 YAML input 中声明的 key
  R2: tool_executor callback 替代全局 execute_tool() — 支持 A2A 路由
  R3: tool result 摘要化 — 截断至 500 字符，去除状态元数据
  R6: temperature 退火 — 越深入越允许探索
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from haip.llm import LLMProvider


@dataclass
class LoopResult:
    reply: str = ""
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    partial_summaries: list[str] = field(default_factory=list)


def _summarize_tool_result(raw: Any, max_chars: int = 500) -> str:
    """摘要化 tool 返回结果: 截断 + 去除无意义元数据 key."""
    if isinstance(raw, dict):
        # 移除 A2A 框架字段，保留业务数据
        keys_to_remove = {"status", "agent", "elapsed_ms", "workflow_id"}
        summary = {k: v for k, v in raw.items() if k not in keys_to_remove}
        text = str(summary)
    elif isinstance(raw, str):
        text = raw
    else:
        text = str(raw)

    if len(text) > max_chars:
        text = text[:max_chars - 20] + "...(truncated)"
    return text


_TEMPERATURE_SCHEDULE = (0.3, 0.4, 0.5, 0.6, 0.7)


class AgentLoop:
    """ReAct 模式: LLM 推理 → Tool 执行 → 迭代循环。"""

    def __init__(
        self,
        llm: LLMProvider,
        system_prompt: str = "你是一个医疗AI助手，请用中文回答。",
        tool_executor: Callable[[str, dict], Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_steps: int = 5,
        temperature_schedule: tuple[float, ...] = _TEMPERATURE_SCHEDULE,
        max_tokens: int = 4096,
        max_total_tokens: int = 32000,
        agent_name: str = "default",
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tool_executor = tool_executor
        self.tools = tools
        self.max_steps = max_steps
        self.temperature_schedule = temperature_schedule
        self.max_tokens = max_tokens
        self.max_total_tokens = max_total_tokens
        self.agent_name = agent_name

    def _get_temperature(self, step: int) -> float:
        """退火策略: 步骤越深，temperature 越高，允许探索."""
        idx = min(step, len(self.temperature_schedule) - 1)
        return self.temperature_schedule[idx]

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
            # Token 预算检查
            if result.input_tokens + result.output_tokens > self.max_total_tokens:
                result.error = "token_budget_exceeded"
                result.reply = (
                    f"推理过程超出了 token 预算限制（{self.max_total_tokens} tokens），"
                    "请简化问题或分步提问。"
                )
                result.steps = step + 1
                break

            temperature = self._get_temperature(step)
            resp = self.llm.chat(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=temperature,
                max_tokens=self.max_tokens,
            )
            result.input_tokens += resp.input_tokens
            result.output_tokens += resp.output_tokens

            if not resp.tool_calls:
                result.reply = resp.content
                result.steps = step + 1
                break

            # 执行所有 tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": resp.content or "",
            }
            tc_list = []
            step_summaries = []

            for tc in resp.tool_calls:
                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": str(tc.arguments),
                    },
                })

                # R2: 通过注入的 tool_executor 执行，而非全局 registry
                if self.tool_executor is not None:
                    raw_result = self.tool_executor(tc.name, tc.arguments)
                    # 判断成功/失败
                    is_success = (
                        isinstance(raw_result, dict)
                        and raw_result.get("status") != "error"
                    )
                    output_str = _summarize_tool_result(raw_result)
                    error_str = "" if is_success else raw_result.get("error", str(raw_result))
                else:
                    # 回退：全局 registry（兼容旧测试）
                    from haip.tools.registry import execute as _global_exec

                    tool_result = _global_exec(tc.name, **tc.arguments)
                    is_success = tool_result.success
                    output_str = _summarize_tool_result(tool_result.output)
                    error_str = tool_result.error or ""

                result.tool_calls.append({
                    "step": step + 1,
                    "tool": tc.name,
                    "args": tc.arguments,
                    "success": is_success,
                    "output": output_str,
                })

                # R3: tool result 摘要化，非完整 JSON
                tool_content = output_str
                if error_str:
                    tool_content = f"调用失败: {error_str}\n请尝试其他方法或告知用户当前限制。"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content,
                })
                step_summaries.append(f"[Step{step+1}] {tc.name}: {'✓' if is_success else '✗'}")

            if tc_list:
                assistant_msg["tool_calls"] = tc_list
            messages.append(assistant_msg)

            if step_summaries:
                result.partial_summaries.append(" | ".join(step_summaries))
        else:
            # max_steps 耗尽——返回中间结果摘要
            result.reply = (
                f"已进行 {self.max_steps} 步推理，以下是中间结果摘要：\n"
                + "\n".join(result.partial_summaries)
                + "\n\n如需完整分析，请缩小问题范围。"
            )
            result.steps = self.max_steps
            result.error = "max_steps_exceeded"

        result.duration_ms = (time.perf_counter() - t0) * 1000
        return result

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        """R1: From per-agent tools build OpenAI tool schemas.

        required only includes params declared in YAML input.
        Extra params (patient_id etc) injected by A2A layer, not exposed to LLM.
        """
        if self.tools is None:
            # Fallback: global registry (backward compat)
            from haip.tools.registry import list_schemas

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
                        properties[name] = {
                            "type": "string",
                            "description": str(spec),
                        }
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

        result = []
        for tool in self.tools:
            input_spec = tool.get("input", {})
            properties = {}
            required = []

            for name, type_hint in input_spec.items():
                type_str = str(type_hint).lower()
                if "int" in type_str or "float" in type_str:
                    json_type = "number" if "float" in type_str else "integer"
                elif "bool" in type_str:
                    json_type = "boolean"
                elif "dict" in type_str or "list" in type_str:
                    json_type = "object"
                else:
                    json_type = "string"

                properties[name] = {
                    "type": json_type,
                    "description": name,
                }
                # R1: 仅 YAML input 中声明的参数标记为 required
                required.append(name)

            result.append({
                "name": tool["name"],
                "description": tool.get("description", tool["name"]),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            })

        return result
