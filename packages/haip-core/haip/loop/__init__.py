"""ReAct AgentLoop — LLM + Tool 执行循环.

v1.2: 新增 AsyncAgentLoop — ADK 风格的 async generator + Event + state_delta 模式.
      AgentLoop (v1.0/v1.1) 保留向后兼容.

核心流程 (AsyncAgentLoop):
  1. 将用户 query + system_prompt + 可用 tool schemas 发给 LLM
  2. LLM 返回 final_answer → 结束
  3. LLM 返回 tool_call → 通过 tool_executor 执行 → 摘要化结果 → 回到步骤 1
  4. 每步 yield Event (state_delta + content)
  5. 最多循环 max_steps 步，超出 token 预算中止
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

from haip.llm import LLMProvider
from haip.session import Event as SessionEvent
from haip.session import events_to_messages
from haip.loop.context import InvocationContext
from haip.loop.hooks import HookChain, HookContext


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
    events: list[SessionEvent] = field(default_factory=list)


def _summarize_tool_result(raw: Any, max_chars: int = 500) -> str:
    """摘要化 tool 返回结果: 截断 + 去除无意义元数据 key."""
    if isinstance(raw, dict):
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
    """ReAct 模式: LLM 推理 → Tool 执行 → 迭代循环 (v1.0 同步版本，向后兼容)."""

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
        idx = min(step, len(self.temperature_schedule) - 1)
        return self.temperature_schedule[idx]

    def run(self, query: str) -> LoopResult:
        t0 = time.perf_counter()
        result = LoopResult()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query},
        ]
        tool_schemas = self._build_tool_schemas()

        for step in range(self.max_steps):
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

                if self.tool_executor is not None:
                    raw_result = self.tool_executor(tc.name, tc.arguments)
                    is_success = (
                        isinstance(raw_result, dict)
                        and raw_result.get("status") != "error"
                    )
                    output_str = _summarize_tool_result(raw_result)
                    error_str = "" if is_success else raw_result.get("error", str(raw_result))
                else:
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
        if self.tools is None:
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

                properties[name] = {"type": json_type, "description": name}
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


# ── AsyncAgentLoop (v1.2 — ADK 风格 async generator) ──

class AsyncAgentLoop:
    """ReAct 模式: async generator，每步 yield Event (中间状态可观察/可中断).

    与 AgentLoop 的区别:
      - run() → async generator，每步 yield SessionEvent
      - 支持 InvocationContext (session state 读写 + temp: 前缀)
      - 支持 HookChain (before/after_llm, before/after_tool)
      - state_delta 在 event 中携带，由 Runner 提交持久化
    """

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
        hooks: HookChain | None = None,
        ctx: InvocationContext | None = None,
        # 上下文管理
        max_context_turns: int = 0,       # 最多保留最近 N 轮对话 (0 = 全部)
        auto_summarize: bool = False,     # 是否自动摘要旧轮次
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
        self.hooks = hooks or HookChain()
        self.ctx = ctx
        self.max_context_turns = max_context_turns
        self.auto_summarize = auto_summarize

    def _get_temperature(self, step: int) -> float:
        idx = min(step, len(self.temperature_schedule) - 1)
        return self.temperature_schedule[idx]

    async def run(self, query: str) -> AsyncIterator[SessionEvent]:
        """异步执行 ReAct Loop，每步 yield 一个 Event.

        Usage:
            async for event in loop.run("患者评估"):
                # event.content 包含当前步的文本/工具结果
                # event.state_delta 包含状态变更
                # event.turn_complete=True 时 loop 结束
        """
        invocation_id = ""
        if self.ctx is not None:
            invocation_id = self.ctx.invocation_id

        # 构建 hook context
        hook_ctx = HookContext(
            agent_name=self.agent_name,
            invocation_id=invocation_id,
            session_id=self.ctx.session.id if self.ctx else "",
        )

        # before_agent hook
        skip_reply = self.hooks.run_before_agent(hook_ctx)
        if skip_reply is not None:
            evt = SessionEvent.assistant_message(
                content=skip_reply,
                invocation_id=invocation_id,
                turn_complete=True,
            )
            if self.ctx:
                self.ctx.commit_event(evt)
            yield evt
            return

        # 构建初始 messages
        messages = events_to_messages(
            self.ctx.session.events if self.ctx else [],
            system_prompt=self.system_prompt,
            max_turns=self.max_context_turns,
            summarize_older=self.auto_summarize,
        )
        # 如果没有任何用户事件（首次对话），直接加入 query
        if not any(m["role"] == "user" for m in messages):
            messages.append({"role": "user", "content": query})

        # 用户消息 event
        user_evt = SessionEvent.user_message(query, invocation_id)
        if self.ctx:
            self.ctx.commit_event(user_evt)
        yield user_evt

        tool_schemas = self._build_tool_schemas()
        total_in = 0
        total_out = 0
        tool_calls_log: list[dict[str, Any]] = []
        partial_summaries: list[str] = []

        for step in range(self.max_steps):
            if total_in + total_out > self.max_total_tokens:
                evt = SessionEvent.assistant_message(
                    content=f"推理过程超出了 token 预算限制（{self.max_total_tokens} tokens），请简化问题或分步提问。",
                    invocation_id=invocation_id,
                    turn_complete=True,
                    error="token_budget_exceeded",
                    state_delta={"temp:error": "token_budget_exceeded"},
                )
                if self.ctx:
                    self.ctx.commit_event(evt)
                yield evt
                break

            temperature = self._get_temperature(step)
            hook_ctx.step = step

            # before_llm hook
            llm_response = self.hooks.run_before_llm(hook_ctx, messages, tool_schemas)
            if llm_response is None:
                llm_response = self.llm.chat(
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    temperature=temperature,
                    max_tokens=self.max_tokens,
                )

            # after_llm hook
            llm_response = self.hooks.run_after_llm(hook_ctx, llm_response)
            total_in += llm_response.input_tokens
            total_out += llm_response.output_tokens

            # 如果没有 tool_calls → final answer
            if not llm_response.tool_calls:
                evt = SessionEvent.assistant_message(
                    content=llm_response.content,
                    invocation_id=invocation_id,
                    turn_complete=True,
                    state_delta={
                        "temp:total_steps": step + 1,
                        "temp:total_tokens_in": total_in,
                        "temp:total_tokens_out": total_out,
                    },
                )
                if self.ctx:
                    self.ctx.commit_event(evt)
                yield evt
                break

            # 执行 tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": llm_response.content or "",
            }
            tc_list = []
            step_summaries = []

            for tc in llm_response.tool_calls:
                # before_tool hook
                mock_result = self.hooks.run_before_tool(hook_ctx, tc.name, tc.arguments)

                if mock_result is not None:
                    raw_result = mock_result
                elif self.tool_executor is not None:
                    raw_result = self.tool_executor(tc.name, tc.arguments)
                else:
                    from haip.tools.registry import execute as _global_exec
                    tr = _global_exec(tc.name, **tc.arguments)
                    raw_result = {"success": tr.success, "output": tr.output, "error": tr.error}

                # after_tool hook
                hook_result = self.hooks.run_after_tool(
                    hook_ctx, tc.name, tc.arguments, raw_result,
                )
                if hook_result is not None:
                    raw_result = hook_result

                # 判断成功/失败
                is_success = (
                    isinstance(raw_result, dict)
                    and raw_result.get("status") != "error"
                )
                output_str = _summarize_tool_result(raw_result)
                error_str = "" if is_success else (
                    raw_result.get("error", str(raw_result))
                    if isinstance(raw_result, dict) else str(raw_result)
                )

                tool_content = output_str
                if error_str:
                    tool_content = f"调用失败: {error_str}\n请尝试其他方法或告知用户当前限制。"

                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": str(tc.arguments)},
                })

                # yield tool result event
                tool_evt = SessionEvent.tool_result(
                    name=tc.name,
                    content=tool_content,
                    invocation_id=invocation_id,
                    state_delta={f"temp:last_tool_{tc.name}": output_str},
                )
                if self.ctx:
                    self.ctx.commit_event(tool_evt)
                yield tool_evt

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content,
                })

                tool_calls_log.append({
                    "step": step + 1,
                    "tool": tc.name,
                    "args": tc.arguments,
                    "success": is_success,
                    "output": output_str,
                })
                step_summaries.append(f"[Step{step+1}] {tc.name}: {'✓' if is_success else '✗'}")

            if tc_list:
                assistant_msg["tool_calls"] = tc_list
            messages.append(assistant_msg)

            # yield assistant thought event (step intermediate)
            thought_evt = SessionEvent.assistant_message(
                content=llm_response.content or f"调用工具: {', '.join(s['tool'] for s in tool_calls_log[-len(tc_list):])}",
                invocation_id=invocation_id,
                partial=False,
                state_delta={
                    f"temp:step_{step+1}_thought": llm_response.content,
                    f"temp:step_{step+1}_tools": [tc["tool"] for tc in tool_calls_log[-len(tc_list):]],
                },
            )
            if self.ctx:
                self.ctx.commit_event(thought_evt)
            yield thought_evt

            if step_summaries:
                partial_summaries.append(" | ".join(step_summaries))
        else:
            # max_steps 耗尽
            evt = SessionEvent.assistant_message(
                content=(
                    f"已进行 {self.max_steps} 步推理，以下是中间结果摘要：\n"
                    + "\n".join(partial_summaries)
                    + "\n\n如需完整分析，请缩小问题范围。"
                ),
                invocation_id=invocation_id,
                turn_complete=True,
                error="max_steps_exceeded",
                state_delta={"temp:error": "max_steps_exceeded"},
            )
            if self.ctx:
                self.ctx.commit_event(evt)
            yield evt

        # after_agent hook
        if self.ctx and self.ctx._last_event and self.ctx._last_event.turn_complete:
            final_content = self.ctx._last_event.content
            modified = self.hooks.run_after_agent(hook_ctx, final_content)
            if modified is not None and modified != final_content:
                corrected_evt = SessionEvent.assistant_message(
                    content=modified,
                    invocation_id=invocation_id,
                    turn_complete=True,
                )
                if self.ctx:
                    self.ctx.commit_event(corrected_evt)
                yield corrected_evt

    def _build_tool_schemas(self) -> list[dict[str, Any]]:
        return AgentLoop._build_tool_schemas(self)


# ── Runner ──

class Runner:
    """Runner — ADK 风格的事件循环驱动器.

    职责:
      1. 创建/获取 Session
      2. 创建 InvocationContext
      3. 驱动 AsyncAgentLoop.run() 的 async generator
      4. 每个 event 通过 SessionService 持久化
      5. 生成最终 LoopResult
    """

    def __init__(
        self,
        loop: AgentLoop | AsyncAgentLoop | None = None,
        session_service: Any = None,
    ):
        self.loop = loop
        self.session_service = session_service

    async def run(
        self,
        query: str,
        session_id: str = "default",
        user_id: str = "default",
    ) -> tuple[LoopResult, AsyncIterator[SessionEvent]]:
        """执行 Agent Loop，返回 (最终结果, 事件流).

        实际使用建议直接迭代 async generator:
            async for event in runner.stream("query"):
                yield event  # SSE 推送给前端
        """
        # 确保 session
        if self.session_service is None:
            from haip.session.store import InMemorySessionService
            self.session_service = InMemorySessionService()

        session = self.session_service.get_or_create_session(session_id, user_id=user_id)
        invocation_id = self.session_service.begin_invocation(session)

        # 创建 context
        ctx = InvocationContext(
            session=session,
            agent_name=self.loop.agent_name if self.loop else "default",
            invocation_id=invocation_id,
            session_service=self.session_service,
        )

        # 使用 AsyncAgentLoop
        if isinstance(self.loop, AsyncAgentLoop):
            self.loop.ctx = ctx
            result = LoopResult()
            events: list[SessionEvent] = []
            try:
                async for evt in self.loop.run(query):
                    events.append(evt)
                    if evt.turn_complete:
                        result.reply = evt.content
                        result.error = evt.error or ""
                    result.events = events
            finally:
                self.session_service.end_invocation(session)
            return result, events

        # 回退: sync AgentLoop
        if isinstance(self.loop, AgentLoop):
            sync_result = self.loop.run(query)
            result = LoopResult(
                reply=sync_result.reply,
                steps=sync_result.steps,
                input_tokens=sync_result.input_tokens,
                output_tokens=sync_result.output_tokens,
                duration_ms=sync_result.duration_ms,
                tool_calls=sync_result.tool_calls,
                error=sync_result.error,
                partial_summaries=sync_result.partial_summaries,
            )
            # 生成等价的 events
            evt = SessionEvent.assistant_message(
                content=sync_result.reply,
                invocation_id=invocation_id,
                turn_complete=True,
                error=sync_result.error or "",
            )
            if ctx:
                ctx.commit_event(evt)
            self.session_service.end_invocation(session)
            result.events = [evt]
            return result, [evt]

        raise ValueError("loop must be AgentLoop or AsyncAgentLoop")
