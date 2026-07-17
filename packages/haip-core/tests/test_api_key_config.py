"""API Key 配置测试 (web 端 /api/config/llm)."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def clean_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from haip.api_key_store import clear_api_key
    clear_api_key()
    # Redirect persist path to tmp
    import haip.api_key_store as store
    monkeypatch.setattr(store, "_PERSIST_FILE", type(store._PERSIST_FILE)(tmp_path / "llm_key.json"))
    yield
    clear_api_key()


class TestApiKeyStore:
    def test_set_and_get(self, clean_api_key):
        from haip.api_key_store import get_api_key, is_configured, set_api_key
        assert not is_configured()
        set_api_key("sk-test-abc123")
        assert is_configured()
        assert get_api_key() == "sk-test-abc123"

    def test_env_priority(self, clean_api_key, monkeypatch):
        from haip.api_key_store import get_api_key, set_api_key
        set_api_key("sk-persisted")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-value")
        assert get_api_key() == "sk-env-value"

    def test_clear(self, clean_api_key):
        from haip.api_key_store import clear_api_key, get_api_key, set_api_key
        set_api_key("sk-to-clear")
        clear_api_key()
        assert get_api_key() == ""


class TestLlmConfigEndpoint:
    def test_set_and_status(self, clean_api_key):
        os.environ["HAIP_TEST_MODE"] = "true"
        from fastapi.testclient import TestClient
        from haip.web_server import app
        client = TestClient(app)
        r = client.post("/api/config/llm", json={"api_key": "sk-test-xyz"})
        assert r.status_code == 200
        assert r.json()["configured"]
        s = client.get("/api/config/llm").json()
        assert s["configured"] and "***" in s["masked_key"]

    def test_clear_endpoint(self, clean_api_key):
        os.environ["HAIP_TEST_MODE"] = "true"
        from fastapi.testclient import TestClient
        from haip.web_server import app
        client = TestClient(app)
        client.post("/api/config/llm", json={"api_key": "sk-test-xyz"})
        r = client.post("/api/config/llm", json={"clear": True})
        assert not r.json()["configured"]

    def test_empty_key_rejected(self, clean_api_key):
        os.environ["HAIP_TEST_MODE"] = "true"
        from fastapi.testclient import TestClient
        from haip.web_server import app
        client = TestClient(app)
        r = client.post("/api/config/llm", json={"api_key": "   "})
        assert r.status_code == 400


class TestLlmConfigIntegration:
    def test_api_key_fed_into_llm_config(self, clean_api_key, monkeypatch):
        """web 端设置 key 后, _load_llm_config 应返回该 key (非 mock 模式)."""
        from haip.api_key_store import set_api_key
        from haip.a2a import _load_llm_config
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        set_api_key("sk-integration-test")
        cfg = _load_llm_config()
        assert cfg.get("api_key") == "sk-integration-test"
