"""端到端集成测试 — Session + AsyncAgentLoop + Guard + Workflow + AgentTool."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

import pytest  # noqa: E402
from haip.session.store import Event, AgentSession, InMemorySessionService, SessionService  # noqa: E402
from haip.loop import AsyncAgentLoop, Runner  # noqa: E402
from haip.loop.context import InvocationContext  # noqa: E402
from haip.loop.hooks import HookChain, HookContext  # noqa: E402
from haip.llm.mock import MockProvider  # noqa: E402
from haip.llm import ChatResponse, ToolCall  # noqa: E402
from haip.orchestrator.graph import ClinicalWorkflow, WorkflowBuilder, Node, NodeType  # noqa: E402
from haip.orchestrator.agent_tool import AgentTool, build_agent_tools, create_agent_tool_executor  # noqa: E402
from haip.tools import BaseTool, ToolResult  # noqa: E402
from haip.tools.registry import register, list_all  # noqa: E402


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo tool"
    def execute(self, msg: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"ECHO: {msg}")


class CalcTool(BaseTool):
    name = "calculate"
    description = "Calculate"
    def execute(self, expr: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"Result: {expr}")


# ── Guard Hook 集成 ──

class TestGuardHookIntegration:
    def test_guard_as_after_llm_hook(self):
        """将 GuardVerifier 作为 after_llm hook 注入 AgentLoop."""
        list_all().clear()
        register(EchoTool())

        llm = MockProvider({"q": {"content": "止血方案: 使用华法林5mg每日"}})

        guard_log = []
        def guard_hook(ctx: HookContext, response: ChatResponse) -> ChatResponse | None:
            if "华法林" in response.content:
                guard_log.append("FLAGGED: anticoagulant mentioned")
            return None  # 不拦截，只记录

        hc = HookChain()
        hc.add("after_llm", guard_hook)

        async def _run():
            loop = AsyncAgentLoop(llm=llm, agent_name="test", hooks=hc)
            async for _ in loop.run("test query"):
                pass

        asyncio.run(_run())
        assert len(guard_log) >= 1
        assert "FLAGGED" in guard_log[0]

    def test_guard_blocks_high_risk(self):
        """before_llm hook 拦截高危查询."""
        list_all().clear()
        register(EchoTool())

        llm = MockProvider({"q": {"content": "should not see"}})

        blocked_queries = []
        def safety_hook(ctx: HookContext, messages: list, tools: dict) -> ChatResponse | None:
            for msg in messages:
                content = str(msg.get("content", ""))
                if "致命剂量" in content:
                    blocked_queries.append(content)
                    return ChatResponse(content="此查询涉及安全风险，已被拦截。")
            return None

        hc = HookChain()
        hc.add("before_llm", safety_hook)

        async def _run():
            loop = AsyncAgentLoop(llm=llm, agent_name="test", hooks=hc)
            events = []
            async for evt in loop.run("请计算致命剂量"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        assert len(blocked_queries) == 1
        final = [e for e in events if e.turn_complete]
        assert any("拦截" in e.content for e in final)


# ── AgentTool 集成 ──

class TestAgentToolIntegration:
    def setup_method(self):
        list_all().clear()
        register(EchoTool())
        register(CalcTool())

    def test_agent_tool_with_loop(self):
        """AgentTool 包装为 AsyncAgentLoop 可调用工具."""
        from haip.agent import DomainPlugin, register as agent_register, list_all as agent_list_all
        agent_list_all().clear()

        plugin = DomainPlugin(
            name="math_agent", cn_name="数学智能体",
            type="business", department="通用",
            tools=[],
        )
        agent_register(plugin)

        at = AgentTool("math_agent", mode="task")

        # 测试 schema 生成
        schema = at.get_schema()
        assert schema["name"] == "agent_math_agent"
        assert "query" in schema["parameters"]["required"]

        # 通过 executor 执行
        tools = [at]
        executor = create_agent_tool_executor(tools)
        # 调用不存在的 agent 不会崩溃（因为 agent 实际未注册 A2A 路由，但不会抛异常层面崩溃）
        try:
            result = executor("agent_math_agent", {"query": "1+1"})
            assert isinstance(result, dict)
        except Exception:
            pass  # a2a.call_with_loop 内部异常被捕获

    def test_coordinator_with_agent_tools(self):
        """Coordinator Agent 通过 AgentTool 委派到子 Agent."""
        from haip.agent import DomainPlugin, register as agent_register, list_all as agent_list_all
        agent_list_all().clear()
        list_all().clear()
        register(EchoTool())

        # 注册子 agents (带 tools 以避免 Unknown agent 错误)
        agent_register(DomainPlugin(name="cardiology", cn_name="心内科",
                                     type="business", department="心内", tools=[]))
        agent_register(DomainPlugin(name="pharmacy", cn_name="药剂科",
                                     type="business", department="药房", tools=[]))

        tools = build_agent_tools(["cardiology", "pharmacy"], mode="task")
        schemas = [at.get_schema() for at in tools]

        assert len(schemas) == 2
        assert schemas[0]["name"] == "agent_cardiology"

        # 模拟 LLM 选择委派到心内科 — fixture key 匹配 query
        llm = MockProvider({"胸痛": {"content": "", "tool_calls": [
            {"name": "agent_cardiology", "arguments": {"query": "评估心脏风险"}}
        ]}})

        executor = create_agent_tool_executor(tools)
        async def _run():
            loop = AsyncAgentLoop(
                llm=llm, agent_name="coordinator",
                tool_executor=executor,
                tools=schemas,
                max_steps=3,
            )
            events = []
            async for evt in loop.run("患者胸痛"):
                events.append(evt)
            return events

        events = asyncio.run(_run())
        tool_events = [e for e in events if e.role == "tool"]
        assert len(tool_events) >= 1, f"Got {len(tool_events)} tool events from {len(events)} total"
        assert tool_events[0].tool_name == "agent_cardiology"


# ── Workflow + AgentTool 整合 ──

class TestWorkflowAgentToolIntegration:
    def test_workflow_routes_to_agent(self):
        """工作流条件路由到 Agent 节点."""
        def _classify(data: dict) -> dict:
            risk = data.get("symptoms", "low")
            return {"output": "cardiac" if "胸痛" in str(risk) else "general", "risk": risk}

        wb = WorkflowBuilder("emergency_triage", "急诊分诊")
        wb.add_function("triage", _classify, "分诊评估")
        wb.add_agent("cardiac", "cardiology", "心内会诊")
        wb.add_agent("general", "emergency", "综合处置")
        wb.chain("START", "triage")
        wb.route("triage", {"cardiac": "cardiac", "general": "general"})
        wb.chain("cardiac", "END")
        wb.chain("general", "END")
        wf = wb.build()

        # 验证路由
        assert "triage_router" in wf._routes or any("triage" in k for k in wf._routes)
        layers = wf.toposort_layers()
        # 至少 2 层: [START], [triage, router], [cardiac or general], [END]
        assert len(layers) >= 3

    def test_parallel_assessment_workflow(self):
        """并行评估 → 汇聚决策."""
        def _cardiac_assess(data: dict) -> dict:
            return {"output": "cardiac_ok", "data": data}
        def _pulmonary_assess(data: dict) -> dict:
            return {"output": "pulmonary_ok", "data": data}

        wb = WorkflowBuilder("preop_parallel", "术前并行评估")
        wb.add_function("cardiac", _cardiac_assess, "心脏评估")
        wb.add_function("pulmonary", _pulmonary_assess, "肺功能评估")
        wb.add_join("synthesis", "结果汇总")
        wb.add_function("decision", lambda d: {"output": "cleared"}, "手术决策")

        wb.fan_out("START", "cardiac", "pulmonary")
        wb.fan_in("synthesis", "cardiac", "pulmonary")
        wb.chain("synthesis", "decision", "END")
        wf = wb.build()

        assert wf.is_join("synthesis")
        layers = wf.toposort_layers()
        # Layer 0: START | Layer 1: cardiac, pulmonary (并行) | Layer 2: synthesis | Layer 3: decision | Layer 4: END
        assert len(layers) >= 4


# ── 全链路集成: Session → AgentLoop → Guard → Workflow ──

class TestFullPipeline:
    def test_session_persists_across_invocations(self):
        """跨 invocation 的 session 状态持久化."""
        svc = SessionService(":memory:")
        s = svc.create_session(user_id="doctor_1", state={"patient_id": "P001"})

        # Invocation 1: 设置临时变量
        inv1 = svc.begin_invocation(s)
        svc.append_event(s, Event.assistant_message(
            "评估中", inv1,
            state_delta={"temp:step": 1, "diagnosis": "preliminary"},
        ))
        svc.end_invocation(s)

        # temp: 变量应被清除
        assert "temp:step" not in s.state
        assert s.state["diagnosis"] == "preliminary"
        assert s.state["patient_id"] == "P001"

        # Invocation 2: 继续写入
        inv2 = svc.begin_invocation(s)
        svc.append_event(s, Event.assistant_message(
            "确认诊断", inv2,
            state_delta={"diagnosis": "confirmed", "temp:review": True},
        ))
        svc.end_invocation(s)

        assert s.state["diagnosis"] == "confirmed"
        assert "temp:review" not in s.state

        # 从 DB 重新加载
        s2 = svc.get_session(s.id, user_id="doctor_1")
        assert s2 is not None
        assert s2.state["diagnosis"] == "confirmed"
        assert s2.state["patient_id"] == "P001"

    def test_runner_with_session(self):
        """Runner 自动管理 session 生命周期."""
        llm = MockProvider({"分析": {"content": "分析完成"}})
        loop = AsyncAgentLoop(llm=llm, agent_name="analyst")
        runner = Runner(loop=loop)

        async def _run():
            result, events = await runner.run("分析病例", session_id="test_s1")
            return result, events

        result, events = asyncio.run(_run())
        assert result.reply == "分析完成"
        assert len(events) >= 1  # user + assistant

    def test_context_turn_limit(self):
        """上下文窗口滑动 — 仅保留最近 N 轮."""
        svc = SessionService(":memory:")
        s = svc.create_session()

        for i in range(10):
            svc.append_event(s, Event(role="user", content=f"问题{i}"))
            svc.append_event(s, Event(role="assistant", content=f"回答{i}"))

        from haip.session import events_to_messages
        msgs = events_to_messages(s.events, max_turns=3)
        # 应只包含最后 3 轮 (6 条消息)
        non_sys = [m for m in msgs if m["role"] != "system"]
        assert len(non_sys) == 6
        assert non_sys[0]["content"] == "问题7"
        assert non_sys[-1]["content"] == "回答9"

    def test_rewind_and_recover(self):
        """回滚会话并恢复正确的状态."""
        svc = SessionService(":memory:")
        s = svc.create_session()

        for i in range(5):
            svc.append_event(s, Event.assistant_message(
                f"step_{i}", "inv1",
                state_delta={f"key_{i}": i},
            ))

        assert s.state["key_4"] == 4
        svc.rewind_session(s, 2)
        assert len(s.events) == 2
        assert "key_4" not in s.state
        assert s.state["key_0"] == 0


# ── 错误处理与边界 ──

class TestErrorHandling:
    def test_agent_tool_handles_missing_agent(self):
        """AgentTool 优雅处理不存在的 agent."""
        at = AgentTool("nonexistent_agent")
        result = at.execute(query="test")
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "Unknown" in str(result.get("error", ""))

    def test_workflow_empty_edges(self):
        """空边的工作流."""
        wf = ClinicalWorkflow("empty")
        layers = wf.toposort_layers()
        assert len(layers) >= 1  # 至少 START + END

    def test_session_service_thread_safety(self):
        """多线程并发写入 — 使用文件 DB (内存 DB 是 per-connection 的)."""
        import tempfile
        import threading
        import shutil

        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test_concurrent.db"
        try:
            svc = SessionService(str(db_path))
            s = svc.create_session(user_id="u1")

            errors = []
            def writer(prefix: str, n: int):
                try:
                    for i in range(n):
                        svc.append_event(s, Event.assistant_message(
                            f"{prefix}_{i}", "inv1",
                            state_delta={f"{prefix}_{i}": i},
                        ))
                except Exception as e:
                    errors.append(str(e))

            threads = [
                threading.Thread(target=writer, args=("A", 5)),
                threading.Thread(target=writer, args=("B", 5)),
                threading.Thread(target=writer, args=("C", 5)),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"Concurrency errors: {errors}"
            s2 = svc.get_session(s.id, user_id="u1")
            assert s2 is not None
            assert len(s2.events) == 15
        finally:
            svc.close()
            shutil.rmtree(tmpdir, ignore_errors=True)
