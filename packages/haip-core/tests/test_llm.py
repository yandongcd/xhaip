"""测试 LLM Provider 抽象层."""

import pytest

from haip.llm import ChatResponse, LLMProvider, ToolCall
from haip.llm.mock import MockProvider


class TestLLMProviderAbstract:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()
        assert True, "Abstract LLMProvider cannot be instantiated"

    def test_from_config_mock(self):
        provider = LLMProvider.from_config({"provider": "mock"})
        assert isinstance(provider, MockProvider)

    def test_from_config_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMProvider.from_config({"provider": "nonexistent"})
        assert True, "ValueError raised for unknown provider config"


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


class TestDeepSeekProvider:
    def test_build_body_basic(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test", model="deepseek-chat")
        body = p._build_body(
            [{"role": "user", "content": "Hi"}],
            tools=None, temperature=0.3, max_tokens=4096, stream=False,
        )
        assert body["model"] == "deepseek-chat"
        assert body["stream"] is False
        assert body["messages"][0]["content"] == "Hi"
        assert "tools" not in body

    def test_build_body_with_tools(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        body = p._build_body(
            [{"role": "user", "content": "Calc"}],
            tools=[{"name": "calc", "description": "calculate", "parameters": {}}],
            temperature=0.3, max_tokens=4096,
        )
        assert "tools" in body
        assert body["tool_choice"] == "auto"
        assert body["tools"][0]["type"] == "function"

    def test_convert_tools(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        result = p._convert_tools([
            {"name": "t1", "description": "d1", "parameters": {}},
            {"name": "t2", "description": "d2", "parameters": {}},
        ])
        assert len(result) == 2
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "t1"

    def test_parse_response_content(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        data = {
            "choices": [{"message": {"content": "Hello world"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        resp = p._parse_response(data)
        assert resp.content == "Hello world"
        assert resp.finish_reason == "stop"
        assert resp.input_tokens == 10
        assert resp.output_tokens == 5

    def test_parse_response_tool_calls(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        data = {
            "choices": [{"message": {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {"name": "search", "arguments": '{"q": "test"}'},
                }]
            }, "finish_reason": "tool_calls"}],
        }
        resp = p._parse_response(data)
        assert resp.finish_reason == "tool_calls"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "search"
        assert resp.tool_calls[0].arguments == {"q": "test"}

    def test_parse_response_choices_empty(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        resp = p._parse_response({"choices": []})
        assert resp.content == ""

    def test_parse_response_invalid_json_arguments(self):
        from haip.llm.deepseek import DeepSeekProvider
        p = DeepSeekProvider(api_key="sk-test")
        data = {
            "choices": [{"message": {
                "tool_calls": [{
                    "id": "call_1",
                    "function": {"name": "bad", "arguments": "not valid json"},
                }]
            }, "finish_reason": "stop"}],
        }
        resp = p._parse_response(data)
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].arguments == {}

    def test_chat_mocked_http(self, mocker):
        import json as _json
        from haip.llm.deepseek import DeepSeekProvider
        from haip.llm import ChatResponse

        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Mocked DeepSeek reply"}, "finish_reason": "stop"}],
            "model": "deepseek-chat",
            "usage": {"prompt_tokens": 5, "completion_tokens": 10},
        }
        mock_post = mocker.patch("httpx.post", return_value=mock_response)

        p = DeepSeekProvider(api_key="sk-test")
        resp = p.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, ChatResponse)
        assert "Mocked DeepSeek reply" in resp.content
        mock_post.assert_called_once()

    def test_chat_stream_mocked(self, mocker):
        import json as _json
        from haip.llm.deepseek import DeepSeekProvider
        from haip.llm import ChatResponse

        def fake_lines():
            yield 'data: {"choices":[{"message":{"content":"Hello"},"finish_reason":"stop"}],"model":"test"}'
            yield 'data: [DONE]'

        mock_resp = mocker.MagicMock()
        mock_resp.__enter__ = mocker.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mocker.MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = fake_lines()
        mock_resp.raise_for_status = mocker.MagicMock()
        mock_stream = mocker.patch("httpx.stream", return_value=mock_resp)

        p = DeepSeekProvider(api_key="sk-test")
        chunks = list(p.chat_stream([{"role": "user", "content": "Hi"}]))
        assert len(chunks) >= 1
        assert isinstance(chunks[0], ChatResponse)
        mock_stream.assert_called_once()

    def test_chat_stream_malformed_json_line(self, mocker):
        from haip.llm.deepseek import DeepSeekProvider
        from haip.llm import ChatResponse

        def fake_lines():
            yield 'data: {"choices":[{"message":{"content":"ok"},"finish_reason":"stop"}]}'
            yield 'data: this is not valid json {{{'
            yield 'data: {"choices":[{"message":{"content":"after_error"},"finish_reason":"stop"}]}'
            yield 'data: [DONE]'

        mock_resp = mocker.MagicMock()
        mock_resp.__enter__ = mocker.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mocker.MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = fake_lines()
        mock_resp.raise_for_status = mocker.MagicMock()
        mock_stream = mocker.patch("httpx.stream", return_value=mock_resp)

        p = DeepSeekProvider(api_key="sk-test")
        chunks = list(p.chat_stream([{"role": "user", "content": "Hi"}]))
        assert len(chunks) >= 1
        mock_stream.assert_called_once()

    def test_chat_stream_empty_data_line(self, mocker):
        from haip.llm.deepseek import DeepSeekProvider

        def fake_lines():
            yield 'data: '
            yield 'data: [DONE]'

        mock_resp = mocker.MagicMock()
        mock_resp.__enter__ = mocker.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mocker.MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = fake_lines()
        mock_resp.raise_for_status = mocker.MagicMock()
        mock_stream = mocker.patch("httpx.stream", return_value=mock_resp)

        p = DeepSeekProvider(api_key="sk-test")
        chunks = list(p.chat_stream([{"role": "user", "content": "Hi"}]))
        assert len(chunks) == 0
        mock_stream.assert_called_once()

    def test_stream_non_data_prefix_line(self, mocker):
        from haip.llm.deepseek import DeepSeekProvider

        def fake_lines():
            yield ': keepalive'
            yield 'data: {"choices":[{"message":{"content":"hello"},"finish_reason":"stop"}]}'
            yield 'data: [DONE]'

        mock_resp = mocker.MagicMock()
        mock_resp.__enter__ = mocker.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mocker.MagicMock(return_value=False)
        mock_resp.iter_lines.return_value = fake_lines()
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("httpx.stream", return_value=mock_resp)

        p = DeepSeekProvider(api_key="sk-test")
        chunks = list(p.chat_stream([{"role": "user", "content": "Hi"}]))
        assert len(chunks) >= 1

    def test_chat_timeout_retries_then_error(self, mocker):
        from haip.llm.deepseek import DeepSeekProvider
        from haip.llm import ChatResponse

        mock_post = mocker.patch("httpx.post", side_effect=Exception("timeout"))

        p = DeepSeekProvider(api_key="sk-test", max_retries=2)
        resp = p.chat([{"role": "user", "content": "Hello"}])
        assert isinstance(resp, ChatResponse)
        assert "LLM error after 2 retries" in resp.content
        assert mock_post.call_count == 2


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
