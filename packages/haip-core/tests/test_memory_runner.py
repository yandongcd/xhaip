"""测试 MemoryService + WorkflowRunner."""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

import pytest

from haip.llm.mock import MockProvider
from haip.loop.context import InvocationContext
from haip.orchestrator.graph import ClinicalWorkflow, Node, NodeType, WorkflowBuilder
from haip.orchestrator.runner import run_workflow_sync
from haip.session.memory import MemoryEntry, MemoryService
from haip.session.store import AgentSession, Event, SessionService

# ── MemoryService ──

class TestMemoryService:
    def setup_method(self):
        self.svc = MemoryService(":memory:")

    def test_add_and_retrieve(self):
        entry = MemoryEntry(content="患者对青霉素过敏", category="patient",
                            importance=10, tags=["过敏", "青霉素"],
                            user_id="doctor_1")
        mid = self.svc.add_memory(entry)

        found = self.svc.get_memory(mid)
        assert found is not None
        assert "青霉素" in found.content
        assert found.importance == 10
        assert found.category == "patient"

    def test_search_by_keyword(self):
        self.svc.add_memory(MemoryEntry(content="糖尿病史", category="clinical",
                                         importance=8, user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="高血压三级", category="clinical",
                                         importance=9, user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="药物偏好中药", category="preference",
                                         importance=5, user_id="u1"))

        results = self.svc.search_memory("糖尿病", user_id="u1")
        assert len(results) >= 1
        assert "糖尿病" in results[0].content

    def test_search_by_category(self):
        self.svc.add_memory(MemoryEntry(content="test1", category="clinical", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="test2", category="patient", user_id="u1"))

        results = self.svc.search_memory("test", user_id="u1", category="patient")
        assert len(results) == 1
        assert results[0].category == "patient"

    def test_search_min_importance(self):
        self.svc.add_memory(MemoryEntry(content="low", importance=2, user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="high", importance=9, user_id="u1"))

        results = self.svc.search_memory("", user_id="u1", min_importance=5)
        assert len(results) == 1
        assert results[0].importance == 9

    def test_delete_memory(self):
        mid = self.svc.add_memory(MemoryEntry(content="test", user_id="u1"))
        assert self.svc.delete_memory(mid) is True
        assert self.svc.get_memory(mid) is None

    def test_ingest_session(self):
        events = [
            Event(role="user", content="我有糖尿病"),
            Event(role="assistant", content="根据您的糖尿病史，建议定期检查血糖"),
            Event(role="user", content="我对青霉素过敏"),
            Event(role="assistant", content="已记录青霉素过敏史"),
        ]
        ids = self.svc.ingest_session(events, user_id="u1", session_id="s1")
        # 应至少提取 clinical 和 patient 两类
        assert len(ids) >= 2

        results = self.svc.search_memory("糖尿病", user_id="u1")
        assert len(results) >= 1

        results = self.svc.search_memory("过敏", user_id="u1")
        assert len(results) >= 1

    def test_consolidate(self):
        self.svc.add_memory(MemoryEntry(content="重复信息", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="重复信息", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="重复信息", user_id="u1"))

        count = self.svc.consolidate(user_id="u1")
        assert count == 2  # 删除了2个重复

    def test_stats(self):
        self.svc.add_memory(MemoryEntry(content="a", category="clinical", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="b", category="clinical", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="c", category="patient", user_id="u1"))

        stats = self.svc.stats(user_id="u1")
        assert stats["total"] == 3
        assert stats["by_category"]["clinical"] == 2
        assert stats["by_category"]["patient"] == 1

    def test_user_isolation(self):
        self.svc.add_memory(MemoryEntry(content="u1_mem", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="u2_mem", user_id="u2"))

        u1r = self.svc.search_memory("mem", user_id="u1")
        u2r = self.svc.search_memory("mem", user_id="u2")
        assert len(u1r) == 1
        assert len(u2r) == 1
        assert u1r[0].content != u2r[0].content

    def test_access_tracking(self):
        mid = self.svc.add_memory(MemoryEntry(content="test", user_id="u1"))
        self.svc.get_memory(mid)
        self.svc.get_memory(mid)
        entry = self.svc.get_memory(mid)
        assert entry is not None
        assert entry.access_count >= 2

    def test_clear_user(self):
        self.svc.add_memory(MemoryEntry(content="a", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="b", user_id="u1"))
        self.svc.add_memory(MemoryEntry(content="c", user_id="u2"))

        deleted = self.svc.clear_user("u1")
        assert deleted == 2
        assert len(self.svc.search_memory("", user_id="u1")) == 0
        assert len(self.svc.search_memory("", user_id="u2")) == 1


# ── Workflow Runner ──

class TestWorkflowRunner:
    def test_simple_function_workflow(self):
        """简单函数工作流: A → B → C."""
        def _step_a(data: dict) -> dict:
            return {"output": "a_done", "val": 1}
        def _step_b(data: dict) -> dict:
            return {"output": "b_done", "val": 2}

        wb = WorkflowBuilder("test", "test")
        wb.add_function("A", _step_a)
        wb.add_function("B", _step_b)
        wb.chain("START", "A", "B", "END")
        wf = wb.build()

        svc = SessionService(":memory:")
        session = svc.create_session()
        ctx = InvocationContext(session=session, invocation_id="wf1", session_service=svc)

        events = run_workflow_sync(wf, ctx)
        assert len(events) >= 2
        final = [e for e in events if e.turn_complete]
        assert len(final) == 1

    def test_workflow_with_route(self):
        """条件路由工作流."""
        def _classify(data: dict) -> dict:
            return {"output": "high"}
        def _risky(data: dict) -> dict:
            return {"output": "risky_handled"}

        wb = WorkflowBuilder("route_test", "route test")
        wb.add_function("classify", _classify)
        wb.add_function("high_handler", _risky)
        wb.add_function("low_handler", lambda d: {"output": "low"})
        wb.route("classify", {"high": "high_handler", "low": "low_handler"})
        wb.chain("high_handler", "END")
        wb.chain("low_handler", "END")
        wf = wb.build()

        svc = SessionService(":memory:")
        ctx = InvocationContext(session=svc.create_session(), invocation_id="wf1", session_service=svc)

        events = run_workflow_sync(wf, ctx)
        assert any("high" in e.content for e in events)

    def test_workflow_with_agent(self):
        """Agent 节点工作流."""
        from haip.agent import DomainPlugin, list_all, register
        list_all().clear()

        plugin = DomainPlugin(
            name="test_wf_agent", cn_name="测试Agent",
            type="business", department="测试科",
            prompt=type("P", (), {"system": "你是一个测试助手。"})(),
        )
        register(plugin)

        wb = WorkflowBuilder("agent_test", "agent test")
        wb.add_agent("analyze", "test_wf_agent", "分析")
        wb.chain("START", "analyze", "END")
        wf = wb.build()

        svc = SessionService(":memory:")
        ctx = InvocationContext(session=svc.create_session(), invocation_id="wf1", session_service=svc)

        llm = MockProvider({"分析": {"content": "分析完成"}})
        events = run_workflow_sync(wf, ctx, llm=llm)
        assert len(events) >= 1
        assert any("分析" in e.content for e in events)

    def test_parallel_workflow(self):
        """并行工作流: A 和 B 同时执行 → 汇聚."""
        import time as _time
        results = []

        def _slow_a(data: dict) -> dict:
            _time.sleep(0.02)
            results.append("A")
            return {"output": "a"}
        def _fast_b(data: dict) -> dict:
            results.append("B")
            return {"output": "b"}

        wb = WorkflowBuilder("parallel", "parallel")
        wb.add_function("A", _slow_a)
        wb.add_function("B", _fast_b)
        wb.add_join("J", "result")
        wb.fan_out("START", "A", "B")
        wb.fan_in("J", "A", "B")
        wb.chain("J", "END")
        wf = wb.build()

        svc = SessionService(":memory:")
        ctx = InvocationContext(session=svc.create_session(), invocation_id="wf1", session_service=svc)

        run_workflow_sync(wf, ctx)
        # A 和 B 都执行了
        assert "A" in results
        assert "B" in results


# ── Memory + Session 集成 ──

class TestMemorySessionIntegration:
    def test_memory_extracts_from_session(self):
        """从完整 session 提取记忆."""
        svc = SessionService(":memory:")
        session = svc.create_session(user_id="doctor_1")

        events = [
            Event(role="user", content="患者有高血压病史"),
            Event(role="assistant", content="根据诊断，高血压患者需治疗方案：监测血压，建议每天测量。"),
            Event(role="assistant", content="考虑到患者高血压，推荐低盐饮食方案。"),
        ]
        for evt in events:
            svc.append_event(session, evt)

        mem_svc = MemoryService(":memory:")
        ids = mem_svc.ingest_session(session.events, user_id="doctor_1",
                                     session_id=session.id)

        assert len(ids) > 0
        results = mem_svc.search_memory("高血压", user_id="doctor_1")
        assert len(results) > 0

    def test_memory_survives_sessions(self):
        """记忆跨 session 持久化."""
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "mem.db"
            mem_svc = MemoryService(str(db_path))

            # Session 1
            mem_svc.add_memory(MemoryEntry(
                content="患者对阿司匹林过敏", category="patient",
                importance=10, user_id="u1", source_session_id="s1",
            ))

            # 关闭再打开
            mem_svc2 = MemoryService(str(db_path))
            results = mem_svc2.search_memory("阿司匹林", user_id="u1")
            assert len(results) == 1
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
