"""Smoke tests for fail-closed LLM provider."""
import pytest

from haip.llm import ChatResponse
from haip.llm.circuit import FailClosedProvider, is_fail_closed_response


class TestFailClosedProvider:
    def test_chat_production_mode(self):
        p = FailClosedProvider(mode="production")
        r = p.chat([{"role": "user", "content": "test"}])
        assert r.model == "fail-closed"
        assert r.finish_reason == "error"
        assert r.content == ""

    def test_chat_test_mode(self):
        p = FailClosedProvider(mode="test")
        r = p.chat([{"role": "user", "content": "test"}])
        assert r.content != ""
        assert "暂不可用" in r.content

    def test_chat_stream(self):
        p = FailClosedProvider(mode="production")
        items = list(p.chat_stream([{"role": "user", "content": "x"}]))
        assert len(items) == 1
        assert items[0].model == "fail-closed"

    def test_is_fail_closed_positive(self):
        r = ChatResponse(content="", model="fail-closed", finish_reason="error")
        assert is_fail_closed_response(r)

    def test_is_fail_closed_negative(self):
        r = ChatResponse(content="hello", model="gpt-4", finish_reason="stop")
        assert not is_fail_closed_response(r)
