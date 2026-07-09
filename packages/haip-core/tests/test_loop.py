"""测试 ReAct AgentLoop."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.loop import AgentLoop, LoopResult  # noqa: E402
from haip.llm.mock import MockProvider  # noqa: E402
from haip.tools import BaseTool, ToolResult  # noqa: E402
from haip.tools.registry import register, list_all  # noqa: E402


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo back the message"
    def execute(self, msg: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"ECHO: {msg}")


class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather"
    def parameters(self) -> dict:
        return {"city": {"type": "string", "description": "City name"}}
    def execute(self, city: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"Weather in {city}: sunny")


class TestAgentLoop:
    def setup_method(self):
        list_all().clear()
        register(EchoTool())
        register(WeatherTool())

    def test_direct_answer_no_tools_needed(self):
        """LLM 返回 final answer 时直接结束。"""
        llm = MockProvider({"hello": {"content": "你好，我是AI助手。"}})
        loop = AgentLoop(llm=llm)
        result = loop.run("Hello!")
        assert result.reply == "你好，我是AI助手。"
        assert result.steps == 1
        assert len(result.tool_calls) == 0

    def test_single_tool_call(self):
        """LLM 发起一个 tool_call，执行后结束。"""
        from haip.llm import ChatResponse, ToolCall
        seq = [
            ChatResponse(tool_calls=[ToolCall(id="tc1", name="get_weather",
                         arguments={"city": "Beijing"})]),
            ChatResponse(content="北京今天晴，适合出行。"),
        ]
        class SeqMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                return seq.pop(0) if seq else ChatResponse(content="done")
        loop = AgentLoop(llm=SeqMock())
        result = loop.run("北京天气？")
        assert len(result.tool_calls) >= 1
        assert result.tool_calls[0]["tool"] == "get_weather"
        assert result.tool_calls[0]["success"] is True

    def test_max_steps_exceeded(self):
        """达到 max_steps 仍有 tool_calls 时退出。"""
        call_count = 0

        class CountingMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                nonlocal call_count
                call_count += 1
                from haip.llm import ChatResponse, ToolCall
                return ChatResponse(
                    tool_calls=[ToolCall(id="tc1", name="echo", arguments={"msg": "hi"})],
                )

        loop = AgentLoop(llm=CountingMock({}), max_steps=3)
        result = loop.run("test")
        assert result.error == "max_steps_exceeded"
        assert call_count == 3

    def test_tool_call_error_handling(self):
        """Tool 执行失败时继续循环。"""

        class FailingMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                # First call: tool_call. Second call: final answer.
                if len(messages) <= 3:
                    from haip.llm import ChatResponse, ToolCall
                    return ChatResponse(
                        tool_calls=[ToolCall(id="tc1", name="echo", arguments={})],
                    )
                return super().chat(messages, tools, temperature, max_tokens)

        llm = FailingMock({})
        loop = AgentLoop(llm=llm, max_steps=3)
        result = loop.run("test")
        assert result.steps >= 1

    def test_multiple_tool_calls_in_one_step(self):
        """LLM 一次返回多个 tool_calls 时逐个执行。"""
        from haip.llm import ChatResponse, ToolCall
        llm = MockProvider({})
        llm.fixtures["multi"] = {
            "content": "",
            "tool_calls": [
                {"name": "echo", "arguments": {"msg": "a"}},
                {"name": "echo", "arguments": {"msg": "b"}},
            ],
        }
        llm.fixtures["done"] = {"content": "完成。"}

        call_seq = ["multi", "done"]
        class SeqMock(MockProvider):
            def chat(self, messages, tools=None, temperature=0.3, max_tokens=4096):
                key = call_seq.pop(0) if call_seq else "done"
                return self._from_fixture(self.fixtures.get(key, {"content": "fallback"}))

        loop = AgentLoop(llm=SeqMock(llm.fixtures), max_steps=3)
        result = loop.run("test")
        assert len(result.tool_calls) == 2
