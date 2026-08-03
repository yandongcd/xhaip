"""测试 A2A HMAC 认证 — 密钥注册 / 签名 / 验签 / 重放保护."""

from __future__ import annotations

import time

import pytest

from haip.a2a import auth as auth_mod


@pytest.fixture(autouse=True)
def _clean_secret_store():
    auth_mod._AGENT_SECRET_KEYS.clear()
    yield
    auth_mod._AGENT_SECRET_KEYS.clear()


def test_register_agent_secret_idempotent():
    first = auth_mod.register_agent_secret("pharmacy")
    second = auth_mod.register_agent_secret("pharmacy")
    assert first == second
    assert auth_mod.get_agent_secret("pharmacy") == first


def test_register_custom_secret_preserved():
    secret = auth_mod.register_agent_secret("orthopedic-surgery", "custom-123")
    assert secret == "custom-123"
    assert auth_mod.get_agent_secret("orthopedic-surgery") == "custom-123"
    re_registered = auth_mod.register_agent_secret("orthopedic-surgery", "ignored-456")
    assert re_registered == "custom-123"


def test_auto_generated_secret_nonempty_unique():
    s1 = auth_mod.register_agent_secret("agent-a")
    s2 = auth_mod.register_agent_secret("agent-b")
    assert s1 and s2
    assert len(s1) == 64
    assert s1 != s2


def test_get_agent_secret_unknown_returns_none():
    assert auth_mod.get_agent_secret("ghost-agent") is None


def test_sign_a2a_request_headers():
    headers = auth_mod.sign_a2a_request("pharmacy", "check_dose", {"drug": "warfarin"})
    assert headers["X-A2A-Agent"] == "pharmacy"
    assert headers["X-A2A-Timestamp"].isdigit()
    assert len(headers["X-A2A-Signature"]) == 64


def test_sign_auto_registers_unknown_caller():
    headers = auth_mod.sign_a2a_request("never-seen", "t", {})
    assert headers["X-A2A-Agent"] == "never-seen"
    assert auth_mod.get_agent_secret("never-seen") is not None


def test_verify_valid_signature_passes():
    auth_mod.register_agent_secret("pharmacy")
    headers = auth_mod.sign_a2a_request("pharmacy", "check_dose", {"drug": "warfarin"})
    assert auth_mod.verify_a2a_request(
        "pharmacy",
        "check_dose",
        {"drug": "warfarin"},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_verify_tampered_params_fails():
    auth_mod.register_agent_secret("pharmacy")
    headers = auth_mod.sign_a2a_request("pharmacy", "check_dose", {"drug": "warfarin"})
    assert not auth_mod.verify_a2a_request(
        "pharmacy",
        "check_dose",
        {"drug": "aspirin"},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_verify_tampered_tool_fails():
    auth_mod.register_agent_secret("pharmacy")
    headers = auth_mod.sign_a2a_request("pharmacy", "check_dose", {"drug": "warfarin"})
    assert not auth_mod.verify_a2a_request(
        "pharmacy",
        "check_interaction",
        {"drug": "warfarin"},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_verify_wrong_agent_fails():
    auth_mod.register_agent_secret("agent-a")
    auth_mod.register_agent_secret("agent-b")
    headers = auth_mod.sign_a2a_request("agent-a", "t", {})
    assert not auth_mod.verify_a2a_request(
        "agent-b",
        "t",
        {},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_verify_stale_timestamp_fails():
    auth_mod.register_agent_secret("pharmacy")
    old_ts = int(time.time()) - 10000
    headers = auth_mod.sign_a2a_request("pharmacy", "t", {}, timestamp=old_ts)
    assert not auth_mod.verify_a2a_request(
        "pharmacy",
        "t",
        {},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_verify_malformed_timestamp_fails():
    auth_mod.register_agent_secret("pharmacy")
    headers = auth_mod.sign_a2a_request("pharmacy", "t", {})
    assert not auth_mod.verify_a2a_request(
        "pharmacy",
        "t",
        {},
        "not-a-timestamp",
        headers["X-A2A-Signature"],
    )


def test_verify_unregistered_agent_fails():
    headers = auth_mod.sign_a2a_request("temp-agent", "t", {})
    auth_mod._AGENT_SECRET_KEYS.pop("temp-agent", None)
    assert auth_mod.get_agent_secret("temp-agent") is None
    assert not auth_mod.verify_a2a_request(
        "temp-agent",
        "t",
        {},
        headers["X-A2A-Timestamp"],
        headers["X-A2A-Signature"],
    )


def test_signature_deterministic_sorted_keys():
    ts = int(time.time())
    a = auth_mod.sign_a2a_request("pharmacy", "t", {"b": 2, "a": 1}, timestamp=ts)
    b = auth_mod.sign_a2a_request("pharmacy", "t", {"a": 1, "b": 2}, timestamp=ts)
    assert a["X-A2A-Signature"] == b["X-A2A-Signature"]


def test_init_agent_secrets_bulk():
    auth_mod.init_agent_secrets(["pharmacy", "cardiology", "radiology"])
    for name in ("pharmacy", "cardiology", "radiology"):
        assert auth_mod.get_agent_secret(name) is not None
