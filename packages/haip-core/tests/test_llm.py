"""测试 LLM Provider 抽象层."""

import pytest

from haip.llm import ChatResponse, LLMProvider, ToolCall
from haip.llm.mock import MockProvider


class TestLLMProviderAbstract:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_from_config_mock(self):
        provider = LLMProvider.from_config({"provider": "mock"})
        assert isinstance(provider, MockProvider)

    def test_from_config_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMProvider.from_config({"provider": "nonexistent"})


class TestMockProvider:
    def test_basic_chat(self, mock_llm):
        resp = mock_llm.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, ChatResponse)
        assert "Mock response" in resp.content

    def test_fixture_match(self, mock_llm):
        resp = mock_llm.chat([{"role": "user", "content": "评估患者 nutrition 风险"}])
        assert "NRS2002" in resp.content

    def test_fixture_tool_call(self, mock_llm):
        resp = mock_llm.chat([{"role": "user", "content": "计算 tpn 配比"}])
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "calculate_tpn"

    def test_call_history_recorded(self, mock_llm):
        mock_llm.chat([{"role": "user", "content": "test"}])
        assert len(mock_llm.call_history) == 1
        assert mock_llm.call_history[0]["messages_count"] == 1

    def test_chat_stream_yields_chunks(self, mock_llm):
        chunks = list(mock_llm.chat_stream([{"role": "user", "content": "Hi"}]))
        assert len(chunks) > 0
        for c in chunks:
            assert isinstance(c, ChatResponse)

    def test_default_no_fixture_match(self):
        provider = MockProvider()
        resp = provider.chat([{"role": "user", "content": "Something unrelated"}])
        assert "simulated medical AI" in resp.content
        assert len(resp.tool_calls) == 0


class TestChatResponse:
    def test_dataclass_defaults(self):
        cr = ChatResponse()
        assert cr.content == ""
        assert cr.tool_calls == []
        assert cr.finish_reason == "stop"

    def test_dataclass_with_content(self):
        cr = ChatResponse(content="Hello", model="test", input_tokens=10, output_tokens=5)
        assert cr.content == "Hello"
        assert cr.model == "test"
        assert cr.input_tokens == 10
        assert cr.output_tokens == 5

    def test_dataclass_with_tool_calls(self):
        tc = ToolCall(id="c1", name="test_tool", arguments={"key": "val"})
        cr = ChatResponse(tool_calls=[tc], finish_reason="tool_calls")
        assert len(cr.tool_calls) == 1
        assert cr.tool_calls[0].name == "test_tool"
        assert cr.tool_calls[0].arguments == {"key": "val"}
