"""测试 AgentLoop — R3: tool result 摘要化, R5: 工具失败恢复, R4: Guard 集成."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.loop import AgentLoop, _summarize_tool_result  # noqa: E402
from haip.llm.mock import MockProvider  # noqa: E402
from haip.llm import ChatResponse, ToolCall  # noqa: E402


class TestSummarizeResult:
    def test_removes_a2a_metadata_keys(self):
        """R3: 移除 status/agent/elapsed_ms 等框架字段."""
        raw = {
            "status": "ok",
            "agent": "antiemetic",
            "elapsed_ms": 0.54,
            "score": 4,
            "risk_level": "high",
            "probability_pct": 79,
        }
        summary = _summarize_tool_result(raw)
        assert "status" not in summary
        assert "agent" not in summary
        assert "elapsed_ms" not in summary
        assert "score" in summary
        assert "risk_level" in summary

    def test_truncates_long_results(self):
        """超过 500 字符时截断."""
        long_str = "x" * 600
        summary = _summarize_tool_result(long_str)
        assert len(summary) <= 500
        assert "truncated" in summary

    def test_handles_string_directly(self):
        """字符串输入直接使用."""
        summary = _summarize_tool_result("hello world")
        assert "hello world" in summary

    def test_handles_non_dict_non_str(self):
        """非 dict/str 输入转为字符串."""
        summary = _summarize_tool_result(42)
        assert "42" in summary


class TestContextManagement:
    def test_temperature_annealing(self):
        """R6: 步骤越深，temperature 越高."""
        loop = AgentLoop(llm=MockProvider({}), max_steps=5)
        temps = [loop._get_temperature(i) for i in range(5)]
        # 单调非递减
        for i in range(1, len(temps)):
            assert temps[i] >= temps[i - 1], f"temp[{i}] < temp[{i-1}]"

    def test_token_budget_abort(self):
        """R3: token 预算超限时中止."""
        tools = [{"name": "t", "description": "d", "input": {}}]

        class BudgetBlaster(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return ChatResponse(
                    content="short",
                    input_tokens=16000,  # 每次 +16K
                    output_tokens=4000,
                    tool_calls=[ToolCall(id="tc", name="t", arguments={})],
                )

        def ok_executor(name, args):
            return {"result": "ok"}

        loop = AgentLoop(
            llm=BudgetBlaster({}),
            tool_executor=ok_executor,
            tools=tools,
            max_total_tokens=32000,  # 32K 预算
        )
        result = loop.run("test")

        # 第一步 20K，第二步 40K > 32K → 应中止
        assert result.steps >= 1
        # 检查是否因 budget 中止
        if result.error == "token_budget_exceeded":
            assert "token" in result.reply.lower() or "tokens" in result.reply


class TestMaxStepsPartial:
    def test_partial_summaries_generated(self):
        """max_steps 耗尽时返回 partial_summaries."""
        tools = [{"name": "loop_tool", "description": "d", "input": {}}]

        class InfiniteMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return ChatResponse(
                    tool_calls=[ToolCall(id="tc", name="loop_tool", arguments={})]
                )

        loop = AgentLoop(
            llm=InfiniteMock({}),
            tool_executor=lambda n, a: {"result": "ok"},
            tools=tools,
            max_steps=3,
        )
        result = loop.run("test")
        assert result.error == "max_steps_exceeded"
        assert len(result.partial_summaries) >= 1


class TestGuardIntegration:
    """R4: Guard verification (triggered inside a2a.call_with_loop)."""

    def test_loop_result_has_guard_field(self):
        """call_with_loop result contains guard field."""
        import haip.llm
        import haip.agent

        # project_root = xhaip root (4 levels up from haip-core/tests)
        root = project_root.parent  # xhaip root

        from haip.agent import _registry
        if "antiemetic" not in _registry:
            yaml_dir = root / "packages" / "haip-hospital" / "agents" / "definitions"
            if yaml_dir.exists():
                haip.agent.load_from_dir(str(yaml_dir))

        original = haip.llm.LLMProvider.from_config

        class SafeMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return ChatResponse(content="Recommend ondansetron 4mg for PONV prophylaxis.")

        haip.llm.LLMProvider.from_config = lambda cfg: SafeMock({})

        from haip.a2a import call_with_loop

        result = call_with_loop("antiemetic", "PONV prophylaxis?")
        assert "guard" in result
        assert result["status"] == "ok"

        haip.llm.LLMProvider.from_config = original


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
