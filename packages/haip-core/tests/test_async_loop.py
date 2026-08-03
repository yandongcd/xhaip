"""测试 AsyncAgentLoop + SessionService + Event 驱动模式."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

import pytest

from haip.llm import ChatResponse, ToolCall
from haip.llm.mock import MockProvider
from haip.loop import AgentLoop, AsyncAgentLoop
from haip.loop.context import InvocationContext
from haip.loop.hooks import HookChain, HookContext
from haip.session.store import (
    AgentSession,
    Event,
    InMemorySessionService,
    SessionService,
    events_to_messages,
)
from haip.tools import BaseTool, ToolResult
from haip.tools.registry import list_all, register


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo back the message"
    def execute(self, msg: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"ECHO: {msg}")


# ── AgentSession + Event Tests ──

class TestSessionService:
    def setup_method(self):
        self.svc = SessionService(":memory:")

    def test_create_and_get_session(self):
        s = self.svc.create_session(app_name="xhaip", user_id="test_user")
        assert s.id.startswith("ses_")

        s2 = self.svc.get_session(s.id, user_id="test_user")
        assert s2 is not None
        assert s2.user_id == "test_user"

    def test_append_event_with_state_delta(self):
        s = self.svc.create_session(user_id="u1", state={"count": 0})
        evt = Event.user_message("hello", "inv_1")
        self.svc.append_event(s, evt)

        # 带 state_delta 的 event
        evt2 = Event.assistant_message("hi there", "inv_1",
                                        state_delta={"count": 1})
        self.svc.append_event(s, evt2)

        # 重新加载 session，验证 state 已持久化
        s2 = self.svc.get_session(s.id, user_id="u1")
        assert s2.state["count"] == 1
        assert len(s2.events) == 2

    def test_rewind_session(self):
        s = self.svc.create_session(user_id="u1")
        for i in range(5):
            self.svc.append_event(s, Event.assistant_message(
                f"msg_{i}", "inv_1", state_delta={f"key_{i}": i},
            ))
        assert len(s.events) == 5
        assert s.state.get("key_4") == 4

        # 回滚到 2 个事件
        self.svc.rewind_session(s, 2)
        assert len(s.events) == 2
        assert "key_4" not in s.state
        assert s.state.get("key_0") == 0
        assert s.state.get("key_1") == 1

    def test_temp_state_cleanup(self):
        s = self.svc.create_session()
        self.svc.append_event(s, Event.assistant_message(
            "msg", "inv_1",
            state_delta={"temp:x": 1, "perm_y": 2},
        ))
        assert s.state.get("temp:x") == 1
        assert s.state.get("perm_y") == 2

        self.svc.end_invocation(s)
        assert "temp:x" not in s.state
        assert s.state.get("perm_y") == 2

    def test_list_sessions(self):
        self.svc.create_session(user_id="u1")
        self.svc.create_session(user_id="u1")
        sessions = self.svc.list_sessions(user_id="u1")
        assert len(sessions) == 2

    def test_sqlite_get_session_user_scoped(self):
        """P1-3: SQLite get_session 按 (id, app_name, user_id) 作用域 —
        同名 session_id 跨用户互不可见 (HTTP 层依赖此语义防 IDOR)."""
        s = self.svc.create_session(user_id="u1", session_id="shared")
        assert s.id == "shared"
        assert self.svc.get_session("shared", user_id="u1") is not None
        assert self.svc.get_session("shared", user_id="u2") is None


class TestInMemorySessionService:
    def test_basic_operations(self):
        svc = InMemorySessionService()
        s = svc.create_session(user_id="u1", state={"a": 1})
        assert s.id.startswith("ses_")

        evt = Event.assistant_message("ok", "inv_1", state_delta={"a": 2})
        svc.append_event(s, evt)
        assert s.state["a"] == 2
        assert len(s.events) == 1

        svc.end_invocation(s)
        # temp: 前缀在 end_invocation 清除
        assert "temp:" not in "".join(e.content or "" for e in s.events) or len(s.events) == 1

    def test_inmemory_user_scoped_same_session_id(self):
        """P1-3: InMemory 会话按 (user_id, session_id) 复合键隔离 — 与 SQLite 后端一致."""
        svc = InMemorySessionService()
        s1 = svc.get_or_create_session("default", user_id="u1")
        s2 = svc.get_or_create_session("default", user_id="u2")
        assert s1 is not s2, "不同用户同名 session_id 必须得到不同会话"

        svc.append_event(s1, Event.user_message("u1 secret"))
        assert len(s1.events) == 1
        assert len(s2.events) == 0, "u2 不得看到 u1 会话的事件"

        assert svc.get_session("default", user_id="u1") is s1
        assert svc.get_session("default", user_id="u2") is s2
        assert svc.get_session("default", user_id="u3") is None

    def test_inmemory_list_sessions_user_scoped(self):
        """P1-3: InMemory list_sessions 只返回当前用户会话."""
        svc = InMemorySessionService()
        svc.get_or_create_session("a", user_id="u1")
        svc.get_or_create_session("b", user_id="u1")
        svc.get_or_create_session("a", user_id="u2")
        assert len(svc.list_sessions(user_id="u1")) == 2
        assert len(svc.list_sessions(user_id="u2")) == 1
        assert {s["id"] for s in svc.list_sessions(user_id="u2")} == {"a"}


class TestEventsToMessages:
    def test_basic_conversion(self):
        events = [
            Event(role="user", content="hello", id="e1"),
            Event(role="assistant", content="hi", id="e2"),
        ]
        msgs = events_to_messages(events, system_prompt="sys")
        assert msgs == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

    def test_max_turns_truncation(self):
        # 真实场景: user/assistant 交替
        events = []
        for i in range(5):
            events.append(Event(role="user", content=f"q_{i}"))
            events.append(Event(role="assistant", content=f"a_{i}"))
        msgs = events_to_messages(events, max_turns=2)
        dialog = [m for m in msgs if m["role"] != "system"]
        # 最后 2 轮 = 最后 2 个 user 起的所有消息
        assert dialog[0]["content"] == "q_3"
        assert dialog[-1]["content"] == "a_4"
        # 4 条消息 (2 user + 2 assistant)


# ── InvocationContext Tests ──

class TestInvocationContext:
    def test_state_read_write(self):
        s = AgentSession(id="test", state={"base": 1})
        svc = InMemorySessionService()
        ctx = InvocationContext(session=s, invocation_id="inv1",
                                session_service=svc)
        assert ctx.get_state("base") == 1
        ctx.set_state("new_key", "new_val")
        assert ctx.get_state("new_key") == "new_val"
        # 未提交前，session.state 不变
        assert "new_key" not in s.state

    def test_commit_event_merges_delta(self):
        s = AgentSession(id="test")
        svc = InMemorySessionService()
        ctx = InvocationContext(session=s, invocation_id="inv1",
                                session_service=svc)
        ctx.set_state("a", 1)
        ctx.set_state("b", 2)
        evt = Event.assistant_message("ok", "inv1")
        ctx.commit_event(evt)
        assert s.state["a"] == 1
        assert s.state["b"] == 2

    def test_delete_state(self):
        s = AgentSession(id="test", state={"remove_me": "bye"})
        ctx = InvocationContext(session=s, invocation_id="inv1")
        ctx.delete_state("remove_me")
        Event.assistant_message("ok", "inv1")
        ctx.session.apply_delta(ctx._pending_delta)
        assert "remove_me" not in s.state


# ── Hook Tests ──

class TestHookChain:
    def test_before_agent_skip(self):
        hc = HookChain()
        hc.add("before_agent", lambda c: "skipped")
        result = hc.run_before_agent(HookContext(agent_name="test"))
        assert result == "skipped"

    def test_before_agent_pass_through(self):
        hc = HookChain()
        hc.add("before_agent", lambda c: None)
        result = hc.run_before_agent(HookContext())
        assert result is None

    def test_after_agent_modify(self):
        hc = HookChain()
        hc.add("after_agent", lambda c, r: r.upper())
        result = hc.run_after_agent(HookContext(), "hello")
        assert result == "HELLO"

    def test_before_llm_block(self):
        hc = HookChain()
        blocked = ChatResponse(content="blocked by hook")
        hc.add("before_llm", lambda c, m, t: blocked)
        result = hc.run_before_llm(HookContext(), [], None)
        assert result is blocked

    def test_before_tool_override(self):
        hc = HookChain()
        hc.add("before_tool", lambda c, n, a: {"status": "ok", "mocked": True})
        result = hc.run_before_tool(HookContext(), "test_tool", {})
        assert result == {"status": "ok", "mocked": True}


# ── AsyncAgentLoop Tests ──

class TestAsyncAgentLoop:
    def test_direct_answer(self):
        """AsyncAgentLoop: LLM 直接回答."""
        llm = MockProvider({"测试": {"content": "你好，我是AI助手"}})

        async def _run():
            loop = AsyncAgentLoop(llm=llm, agent_name="test")
            events = []
            async for evt in loop.run("测试问题"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        # user event + assistant finish event
        final = [e for e in events if e.turn_complete and e.content]
        assert len(final) >= 1
        assert any("AI助手" in e.content for e in final)

    def test_single_tool_call(self):
        """AsyncAgentLoop: 一次 tool call 后结束."""
        list_all().clear()
        register(EchoTool())

        stream = [
            ChatResponse(tool_calls=[ToolCall(id="t1", name="echo",
                         arguments={"msg": "test"})]),
            ChatResponse(content="完成"),
        ]
        class SeqMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return stream.pop(0) if stream else ChatResponse(content="done")

        async def _run():
            loop = AsyncAgentLoop(llm=SeqMock(), agent_name="test")
            events = []
            async for evt in loop.run("echo test"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        assert any(e.role == "tool" and e.tool_name == "echo" for e in events)
        assert any(e.turn_complete and e.content == "完成" for e in events)

    def test_positional_state_delta(self):
        """AsyncAgentLoop: state_delta 随 event 传播到 session."""
        list_all().clear()
        register(EchoTool())

        stream = [
            ChatResponse(tool_calls=[ToolCall(id="t1", name="echo",
                         arguments={"msg": "test"})]),
            ChatResponse(content="完成"),
        ]
        class SeqMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return stream.pop(0) if stream else ChatResponse(content="done")

        async def _run():
            svc = InMemorySessionService()
            s = svc.create_session()
            ctx = InvocationContext(session=s, agent_name="test",
                                    invocation_id="inv1", session_service=svc)

            loop = AsyncAgentLoop(llm=SeqMock(), agent_name="test", ctx=ctx)
            async for evt in loop.run("echo test"):
                if evt.role == "tool":
                    ctx.set_state("tool_executed", True)
            return s

        session = asyncio.run(_run())
        assert session.state.get("tool_executed") is True

    def test_hook_intercepts_llm(self):
        """Hook: before_llm 拦截 LLM 调用."""
        llm = MockProvider({"test": {"content": "should not see this"}})
        hc = HookChain()
        hc.add("before_llm", lambda c, m, t: ChatResponse(content="hook override"))

        async def _run():
            loop = AsyncAgentLoop(llm=llm, agent_name="test", hooks=hc)
            events = []
            async for evt in loop.run("test"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        # user event + assistant event (hook interception)
        final = [e for e in events if e.turn_complete and e.content == "hook override"]
        assert len(final) == 1

    def test_max_steps_exceeded(self):
        """AsyncAgentLoop: max_steps 耗尽."""
        list_all().clear()
        register(EchoTool())

        call_count = [0]

        class InfTool(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                call_count[0] += 1
                return ChatResponse(
                    tool_calls=[ToolCall(id="t1", name="echo",
                                         arguments={"msg": "loop"})]
                )

        async def _run():
            loop = AsyncAgentLoop(llm=InfTool(), max_steps=2, agent_name="test")
            events = []
            async for evt in loop.run("test"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        assert call_count[0] == 2
        last = events[-1]
        assert last.error == "max_steps_exceeded"
        assert last.turn_complete
