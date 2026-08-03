"""测试 AgentLoop 工具执行器 — R2: tool_executor callback 替代全局 registry."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.llm import ChatResponse, ToolCall
from haip.llm.mock import MockProvider
from haip.loop import AgentLoop


class TestToolExecutor:
    def test_uses_injected_executor(self):
        """tool_executor callback is called instead of global registry."""
        calls = []

        def my_executor(tool_name, args):
            calls.append((tool_name, args))
            return {"status": "ok", "result": f"executed {tool_name}"}

        tools = [{"name": "my_tool", "description": "test", "input": {"x": "str"}}]
        call_count = [0]

        class TwoStepMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                call_count[0] += 1
                if call_count[0] == 1:
                    return ChatResponse(
                        tool_calls=[ToolCall(id="tc1", name="my_tool", arguments={"x": "hello"})]
                    )
                return ChatResponse(content="Done.")

        loop = AgentLoop(
            llm=TwoStepMock({"fallback": {"content": "done"}}),
            tool_executor=my_executor,
            tools=tools,
        )
        result = loop.run("test")

        assert len(calls) == 1
        assert calls[0][0] == "my_tool"
        assert calls[0][1] == {"x": "hello"}
        assert result.reply == "Done."
        assert result.steps == 2

    def test_executor_error_propagated(self):
        """Error from tool_executor is propagated correctly."""
        def failing_executor(tool_name, args):
            return {"status": "error", "error": "Tool not available"}

        tools = [{"name": "bad_tool", "description": "test", "input": {}}]
        call_count = [0]

        class ErrorMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                call_count[0] += 1
                if call_count[0] == 1:
                    return ChatResponse(
                        tool_calls=[ToolCall(id="tc1", name="bad_tool", arguments={})]
                    )
                return ChatResponse(content="Cannot complete, manual review needed.")

        loop = AgentLoop(
            llm=ErrorMock({"bail": {"content": "fallback"}}),
            tool_executor=failing_executor,
            tools=tools,
        )
        result = loop.run("test")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["success"] is False

    def test_fallback_to_global_registry_when_no_executor(self):
        """Falls back to global registry when no tool_executor."""
        from haip.tools import BaseTool, ToolResult
        from haip.tools.registry import list_all, register

        list_all().clear()

        class CalcTool(BaseTool):
            name = "calc"
            description = "calculator"
            def execute(self, a: int = 0, b: int = 0, **kwargs) -> ToolResult:
                return ToolResult(success=True, output=f"{a + b}")

        register(CalcTool())

        tools = [{"name": "calc", "description": "calc", "input": {"a": "int", "b": "int"}}]
        call_count = [0]

        class CalcMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                call_count[0] += 1
                if call_count[0] == 1:
                    return ChatResponse(
                        tool_calls=[ToolCall(id="tc1", name="calc", arguments={"a": 1, "b": 2})]
                    )
                return ChatResponse(content="Result computed.")

        loop = AgentLoop(
            llm=CalcMock({"done": {"content": "result"}}),
            tools=tools,
        )
        result = loop.run("1+2?")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["success"] is True

        list_all().clear()


class TestAsyncLoopGuardStatus:
    """C4: call_with_loop_async 反映 Guard 状态 (与同步路径一致)."""

    def _ensure_antiemetic(self):
        import haip.agent
        from haip.agent import _registry
        if "antiemetic" not in _registry:
            yaml_dir = project_root.parent / "packages" / "haip-hospital" / "agents" / "definitions"
            if yaml_dir.exists():
                haip.agent.load_from_dir(str(yaml_dir))
        assert "antiemetic" in _registry, "antiemetic agent 未加载"

    @staticmethod
    def _fake_verify(passed):
        from types import SimpleNamespace

        def _verify(self, agent_output, scenario, agent_name):
            return SimpleNamespace(
                passed=passed,
                flags=[] if passed else ["simulated guard flag"],
                requires_human_review=False,
                citations=[],
            )
        return _verify

    def test_async_loop_guard_blocked(self, monkeypatch):
        """(c) guard 未通过 → status=blocked。"""
        import asyncio

        from haip.a2a import call_with_loop_async
        self._ensure_antiemetic()
        monkeypatch.setattr(
            "haip.guard.verifier.GuardVerifier.verify", self._fake_verify(False))
        result = asyncio.run(call_with_loop_async("antiemetic", "PONV prophylaxis?"))
        assert result["status"] == "blocked"
        assert "Guard" in (result["error"] or "")
        assert result["guard"]["passed"] is False

    def test_async_loop_guard_passed(self, monkeypatch):
        """(c) guard 通过 → status=ok。"""
        import asyncio

        from haip.a2a import call_with_loop_async
        self._ensure_antiemetic()
        monkeypatch.setattr(
            "haip.guard.verifier.GuardVerifier.verify", self._fake_verify(True))
        result = asyncio.run(call_with_loop_async("antiemetic", "PONV prophylaxis?"))
        assert result["status"] == "ok"
        assert result["guard"]["passed"] is True
        assert result["reply"], "guard 通过时应返回回复"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
