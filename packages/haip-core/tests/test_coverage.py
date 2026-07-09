"""补充测试 — 提升覆盖率到 90%+."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.a2a.router import build_routes, resolve_handler  # noqa: E402
from haip.agent import register, _registry, DomainPlugin, ToolDef  # noqa: E402
from haip.a2a import call_batch, call as a2a_dispatch, clear_history  # noqa: E402
from haip.guard.citation import CitationEngine, Citation  # noqa: E402
from haip.guard.confidence import ConfidenceScorer  # noqa: E402
from haip.guard.verifier import GuardVerifier  # noqa: E402
from haip.llm.mock import MockProvider  # noqa: E402
from haip.llm import LLMProvider  # noqa: E402


class TestA2ARouter:
    def setup_method(self):
        _registry.clear()

    def test_build_routes_empty(self):
        assert build_routes() == {}

    def test_build_routes_with_agents(self):
        register(DomainPlugin(name="ph", type="business",
            tools=[ToolDef(name="t1", description="", handler="mod.fn")]))
        register(DomainPlugin(name="noop", type="specialist"))  # no tools
        routes = build_routes()
        assert "ph" in routes
        assert "noop" not in routes

    def test_resolve_handler_found(self):
        register(DomainPlugin(name="ph", type="business",
            tools=[ToolDef(name="t1", description="", handler="pkg.mod.func")]))
        result = resolve_handler("ph", "t1")
        assert result == ["pkg.mod", "func"]

    def test_resolve_handler_not_found(self):
        result = resolve_handler("ghost", "x")
        assert result is None

    def test_resolve_handler_tool_not_found(self):
        register(DomainPlugin(name="ph", type="business",
            tools=[ToolDef(name="t1", description="", handler="pkg.fn")]))
        assert resolve_handler("ph", "unknown") is None


class TestA2ADispatcher:
    def setup_method(self):
        _registry.clear()
        clear_history()

    def test_call_module_not_found(self):
        """调用不存在的模块返回 error。"""
        register(DomainPlugin(name="ph", type="business",
            tools=[ToolDef(name="t1", description="", handler="no.such.module.fn")]))
        result = a2a_dispatch("ph", "t1")
        assert result["status"] == "error"

    def test_call_function_not_found(self):
        """调用不存在的函数返回 error。"""
        register(DomainPlugin(name="ph", type="business",
            tools=[ToolDef(name="t1", description="",
                          handler="haip.llm.mock.nonexistent_func")]))
        result = a2a_dispatch("ph", "t1")
        assert result["status"] == "error"

    def test_call_batch(self):
        register(DomainPlugin(name="a", type="business"))
        register(DomainPlugin(name="b", type="specialist"))
        results = call_batch([
            {"agent": "a", "tool": "no_tool"},
            {"agent": "b", "tool": "no_tool"},
            {"agent": "ghost", "tool": "x"},
        ])
        assert len(results) == 3
        assert all(r["status"] == "error" for r in results)

    def test_call_agent_not_found(self):
        from haip.a2a import call
        result = call("ghost", "any")
        assert result["status"] == "error"
        assert "Unknown agent" in result["error"]


class TestCitationCoverage:
    def test_index_guidelines(self):
        import tempfile
        engine = CitationEngine()
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "nice_ng37.yaml").write_text("trust_level: T1")
            (dp / "readme.txt").write_text("not indexed")
            engine.index_guidelines(dp)
        assert len(engine._index) > 0

    def test_has_unverified_with_index(self):
        c = Citation(verified=False)
        assert CitationEngine.has_unverified([c])
        assert not CitationEngine.has_unverified([Citation(verified=True)])

    def test_verify_substring_match(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dp = Path(d)
            (dp / "nice_ng37.yaml").write_text("trust_level: T1")
            engine = CitationEngine(dp)
            c = Citation(source="NICE")
            engine.verify([c])
            assert c.verified

    def test_format_summary(self):
        c = [Citation(source="NICE NG37", trust_level="T1", verified=True)]
        s = CitationEngine.format_summary(c)
        assert "[verified]" in s
        assert "[T1]" in s


class TestConfidenceCoverage:
    def test_custom_weights(self):
        scorer = ConfidenceScorer(
            source_weight=0.5, tool_weight=0.2,
            llm_weight=0.2, cross_weight=0.1,
        )
        assert scorer.source_weight == 0.5
        score = scorer.compute(citations=[
            Citation(source="NICE", trust_level="T1", verified=True),
        ])
        assert score.value > 0.7


class TestGuardVerifierCoverage:
    def test_bind_llm(self):
        v = GuardVerifier()
        llm = MockProvider()
        v.bind_llm(llm)
        assert v.llm is llm

    def test_auto_correct_fallback(self):
        v = GuardVerifier()
        result = v._auto_correct("test", "agent")
        assert result == ""  # no LLM bound


class TestKnowledgeCoverage:
    def test_empty_sync(self):
        from haip.knowledge import KnowledgeStore
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            store = KnowledgeStore(":memory:")
            stats = store.sync_from_dir(
                guidelines_dir=Path(d) / "nonexistent",
                rules_dir=Path(d) / "nonexistent")
            assert stats["guidelines"] == 0
            assert stats["rules"] == 0
            store.close()


class TestLoopCoverage:
    def test_build_tool_schemas_string_params(self):
        """测试 parameters() 返回 string value 而非 dict 的边界情况."""
        from haip.tools import BaseTool, ToolResult
        from haip.tools.registry import register, _tools
        from haip.loop import AgentLoop
        _tools.clear()

        class StrParamTool(BaseTool):
            name = "str_tool"
            description = "test"
            def parameters(self) -> dict:
                return {"x": "string", "y": {"type": "int", "description": "num"}}
            def execute(self, **kw) -> ToolResult:
                return ToolResult(success=True)

        register(StrParamTool())
        llm = MockProvider({"test": {"content": "ok"}})
        loop = AgentLoop(llm=llm)
        result = loop.run("test")
        assert result.reply == "ok"
        _tools.clear()


class TestOrchestratorCoverage:
    def test_plan_no_llm(self):
        from haip.orchestrator import A2AOrchestrator
        orch = A2AOrchestrator()
        dag =         orch.plan("task")
        assert dag.metadata.get("plan_error") == "no LLM provider"

    def test_plan_with_available_agents(self):
        from haip.orchestrator import A2AOrchestrator
        import json
        dag_json = json.dumps([
            {"id": "n1", "agent": "a", "tool": "t1"},
        ])
        llm = MockProvider({"task": {"content": dag_json}})
        orch = A2AOrchestrator(llm=llm)
        dag = orch.plan("task", available_agents=[
            {"name": "a", "description": "Agent A"},
        ])
        assert len(dag.nodes) == 1

    def test_plan_invalid_json(self):
        from haip.orchestrator import A2AOrchestrator
        llm = MockProvider({"task": {"content": "not valid json"}})
        orch = A2AOrchestrator(llm=llm)
        dag =         orch.plan("task")
        assert "plan_error" in dag.metadata

    def test_plan_json_in_code_block(self):
        from haip.orchestrator import A2AOrchestrator
        import json
        dag_json = json.dumps([{"id": "n1", "agent": "a", "tool": "t1"}])
        llm = MockProvider({"task": {"content": f"```json\n{dag_json}\n```"}})
        orch = A2AOrchestrator(llm=llm)
        dag =         orch.plan("task")
        assert len(dag.nodes) == 1

    def test_plan_with_list_agents(self):
        from haip.orchestrator import A2AOrchestrator
        import json
        from haip.agent import register, DomainPlugin, _registry
        _registry.clear()
        register(DomainPlugin(name="x", cn_name="X", type="business"))
        dag_json = json.dumps([{"id": "n1", "agent": "x", "tool": "test"}])
        llm = MockProvider({"task": {"content": dag_json}})
        orch = A2AOrchestrator(llm=llm)
        dag =         orch.plan("task")
        assert len(dag.nodes) == 1


class TestLLMProviderCoverage:
    def test_from_config_deepseek(self):
        p = LLMProvider.from_config({
            "provider": "deepseek",
            "api_key": "sk-test",
            "model": "deepseek-chat",
        })
        from haip.llm.deepseek import DeepSeekProvider
        assert isinstance(p, DeepSeekProvider)

    def test_provider_error_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMProvider.from_config({"provider": "bad"})


class TestDeepSeekCoverage:
    def test_parse_response(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        data = {
            "choices": [{
                "message": {"content": "Hello"},
                "finish_reason": "stop",
            }],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        resp = p._parse_response(data)
        assert resp.content == "Hello"
        assert resp.model == "deepseek-chat"
        assert resp.input_tokens == 10

    def test_parse_response_with_tool_calls(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        data = {
            "choices": [{
                "message": {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "get_weather", "arguments": '{"city":"BJ"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "model": "test",
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }
        resp = p._parse_response(data)
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "get_weather"

    def test_parse_response_bad_json_args(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        data = {
            "choices": [{"message": {"tool_calls": [
                {"id": "1", "function": {"name": "x", "arguments": "not json"}},
            ]}}],
            "model": "", "usage": {},
        }
        resp = p._parse_response(data)
        assert resp.tool_calls[0].arguments == {}

    def test_build_body_with_tools(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        body = p._build_body(
            [{"role": "user", "content": "hi"}],
            tools=[{"name": "t1", "description": "d"}],
            temperature=0.3, max_tokens=100,
        )
        assert "tools" in body
        assert body["tool_choice"] == "auto"

    def test_build_body_no_tools(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="test")
        body = p._build_body(
            [{"role": "user", "content": "hi"}],
            tools=None, temperature=0.3, max_tokens=100,
        )
        assert "tools" not in body
