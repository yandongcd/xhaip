"""LLM 配置插值与离线降级测试 (聊天 401 根因)."""

from __future__ import annotations


class TestLlmConfigInterpolation:
    def test_env_interpolated(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        from haip.a2a import _load_llm_config
        cfg = _load_llm_config()
        assert cfg.get("api_key") == "sk-test-123", \
            "config 中 ${DEEPSEEK_API_KEY} 必须被环境变量插值"

    def test_missing_env_resolves_empty(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        from haip.a2a import _load_llm_config
        cfg = _load_llm_config()
        assert cfg.get("api_key", "") == "", \
            "env 缺失时不得把字面量 ${...} 当 api_key 发给远端 (401 根因)"


class TestOfflineFallback:
    def test_loop_falls_back_to_mock_without_key(self, monkeypatch):
        """无 API key 时按 config fallback 声明降级 MockProvider, 聊天离线可用."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        from haip.a2a import _build_loop_components
        from haip.agent import DomainPlugin, register
        from haip.llm.mock import MockProvider
        register(DomainPlugin(name="chat-fallback-test", type="specialist"))
        _, _, llm, _ = _build_loop_components("chat-fallback-test")
        assert isinstance(llm, MockProvider)

    def test_real_provider_used_with_key(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-123")
        from haip.a2a import _build_loop_components
        from haip.agent import DomainPlugin, register
        from haip.llm.deepseek import DeepSeekProvider
        register(DomainPlugin(name="chat-fallback-test2", type="specialist"))
        _, _, llm, _ = _build_loop_components("chat-fallback-test2")
        assert isinstance(llm, DeepSeekProvider)
        assert llm.api_key == "sk-test-123"
