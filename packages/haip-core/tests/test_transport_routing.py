"""Tests for Sprint 5: Transport + Pre-LLM Routing + HITL."""

import pytest

from haip.a2a.transport import (
    AgentTransport,
    InProcessTransport,
    MCPTransport,
    MockTransport,
    get_transport,
    remove_transport,
    set_transport,
)
from haip.loop.hitl import HITLHook, HITLRequest
from haip.loop.hooks import HookChain, HookContext
from haip.loop.routing import KeywordRouter, RouteRule


class TestTransport:
    def test_in_process_transport(self):
        t = InProcessTransport()
        assert isinstance(t, AgentTransport)

    def test_mock_transport_basic(self):
        t = MockTransport({"test/assess": {"status": "ok", "result": "pass"}})
        result = t.call("test", "assess", {})
        assert result["status"] == "ok"
        assert result["result"] == "pass"

    def test_mock_transport_fallback(self):
        t = MockTransport()
        result = t.call("unknown", "tool", {})
        assert result["status"] == "ok"
        assert "mock:unknown/tool" in result["result"]

    def test_mock_transport_logs_calls(self):
        t = MockTransport()
        t.call("agent-a", "tool-x", {"key": "val"})
        assert len(t.call_log) == 1
        assert t.call_log[0]["agent"] == "agent-a"

    def test_transport_registry(self):
        t = MockTransport()
        set_transport("test-agent", t)
        assert get_transport("test-agent") is t
        assert get_transport("nonexistent") is None
        remove_transport("test-agent")
        assert get_transport("test-agent") is None


class TestKeywordRouter:
    def test_add_and_match(self):
        router = KeywordRouter()
        router.add("NRS2002", "pharmacy", "assess_nutrition")
        router.add("ASA", "anesthesia-risk", "assess_asa")

        ctx = HookContext(agent_name="test", metadata={"query": "请做 NRS2002 评估"})
        result = router.match(ctx)
        assert result is not None
        assert "pharmacy" in result
        assert "assess_nutrition" in result

    def test_no_match(self):
        router = KeywordRouter()
        router.add("NRS2002", "pharmacy", "assess_nutrition")

        ctx = HookContext(agent_name="test", metadata={"query": "患者有心悸症状"})
        result = router.match(ctx)
        assert result is None

    def test_empty_query(self):
        router = KeywordRouter()
        router.add("NRS2002", "pharmacy", "assess_nutrition")
        ctx = HookContext(agent_name="test", metadata={})
        result = router.match(ctx)
        assert result is None

    def test_priority_matching(self):
        router = KeywordRouter()
        router.add_batch(["ECG", "心电图"], "cardio-risk", "interpret_ecg_high", priority=100)
        router.add_batch(["ECG", "心电图"], "cardio-risk", "interpret_ecg_low", priority=10)

        ctx = HookContext(agent_name="test", metadata={"query": "请分析这份心电图"})
        result = router.match(ctx)
        assert "interpret_ecg_high" in result  # high priority wins

    def test_hook_chain_integration(self):
        hooks = HookChain()
        router = KeywordRouter()
        router.add("NRS2002", "pharmacy", "assess_nutrition")
        hooks.add("before_agent", router.match)

        ctx = HookContext(agent_name="test", metadata={"query": "NRS2002 营养风险筛查"})
        skip = hooks.run_before_agent(ctx)
        assert skip is not None


class TestHITL:
    def test_hitl_request_defaults(self):
        req = HITLRequest()
        assert req.status == "pending"
        assert req.action_required == "confirm_or_reject"

    def test_hitl_hook_triggers_on_low_confidence(self):
        hook = HITLHook(required_below=0.5)
        ctx = HookContext(
            agent_name="cardiology",
            metadata={"confidence": 0.2, "guard_blocked": False, "query": "手术方案评估"},
        )
        result = hook.check(ctx, "建议进行 THA 手术")
        assert result is not None
        assert "HITL PENDING" in result
        assert ctx.metadata.get("hitl_pending") is True

    def test_hitl_hook_triggers_on_guard_block(self):
        hook = HITLHook(required_below=0.3)
        ctx = HookContext(
            agent_name="orthopedic",
            metadata={"confidence": 0.8, "guard_blocked": True,
                      "guard_flags": ["存在未验证的指南引用"], "query": "手术时机"},
        )
        result = hook.check(ctx, "建议 48 小时内手术")
        assert result is not None
        assert "HITL PENDING" in result

    def test_hitl_hook_skips_on_high_confidence(self):
        hook = HITLHook(required_below=0.3)
        ctx = HookContext(
            agent_name="dermatology",
            metadata={"confidence": 0.9, "guard_blocked": False, "query": "皮肤问题"},
        )
        result = hook.check(ctx, "建议使用外用药膏")
        assert result is None  # No HITL needed


class TestMCPTransport:
    """MCP transport error handling (no live server needed)."""

    def test_mcp_instantiation(self):
        t = MCPTransport(base_url="http://localhost:8765")
        assert isinstance(t, AgentTransport)
        assert t.base_url == "http://localhost:8765"
        assert t.timeout == 30.0

    def test_mcp_custom_timeout(self):
        t = MCPTransport(base_url="http://localhost:8765", timeout=10.0)
        assert t.timeout == 10.0

    def test_mcp_connection_error(self):
        t = MCPTransport(base_url="http://127.0.0.1:19999")
        result = t.call("test-agent", "test-tool", {})
        assert result["status"] == "error"
        assert "Connection failed" in result["error"]

    def test_mcp_url_construction(self):
        t = MCPTransport(base_url="http://host:1234/")
        result = t.call("agent-x", "tool-y", {"key": "val"})
        assert result["status"] == "error"  # connection refused, but url is correct

    def test_mcp_registry_integration(self):
        t = MCPTransport(base_url="http://localhost:8765")
        set_transport("remote-agent", t)
        stored = get_transport("remote-agent")
        assert stored is t
        assert isinstance(stored, MCPTransport)
        remove_transport("remote-agent")
