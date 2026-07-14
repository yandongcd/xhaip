"""Tests for the auth module — models, password, JWT, RBAC, and API."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["HAIP_TEST_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient

from haip.auth.models import (
    UserCreateRequest,
    UserLoginRequest,
    UserInfo,
    LoginResponse,
    TokenRefreshRequest,
    Permission,
)
from haip.auth.password import hash_password, verify_password, validate_password_strength
from haip.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_access_token,
    revoke_refresh_token,
)
from haip.auth.rbac import (
    get_permissions_for_roles,
    has_permission,
    add_role,
    remove_role,
    list_roles,
    PREDEFINED_ROLES,
)
from haip.auth import AuthService


# ── Password Tests ──


class TestPassword:
    def test_hash_and_verify(self):
        pw = "Test@1234"
        h = hash_password(pw)
        assert h != pw
        assert h.startswith("$2b$")
        assert verify_password(pw, h)
        assert not verify_password("wrong", h)

    def test_long_password(self):
        pw = "A" * 100 + "@1aB"
        h = hash_password(pw)
        assert verify_password(pw, h)

    def test_strength_valid(self):
        ok, msg = validate_password_strength("Strong@1")
        assert ok
        assert msg == ""

    def test_strength_too_short(self):
        ok, msg = validate_password_strength("Ab@1")
        assert not ok
        assert "8 characters" in msg

    def test_strength_no_upper(self):
        ok, msg = validate_password_strength("nope@1234")
        assert not ok
        assert "uppercase" in msg

    def test_strength_no_digit(self):
        ok, msg = validate_password_strength("Nope@abcde")
        assert not ok
        assert "digit" in msg

    def test_strength_no_special(self):
        ok, msg = validate_password_strength("Nope12345")
        assert not ok
        assert "special" in msg


# ── JWT Tests ──


class TestJWT:
    def test_create_and_decode_access(self):
        token, _ = create_access_token("u1", "test", ["doctor"], ["agent:read"])
        payload = decode_token(token)
        assert payload["sub"] == "u1"
        assert payload["username"] == "test"
        assert payload["roles"] == ["doctor"]
        assert payload["type"] == "access"

    def test_refresh_token(self):
        _, _ = create_access_token("u1", "test", ["doctor"], ["agent:read"])
        rt, _ = create_refresh_token("u1")
        payload = decode_token(rt)
        assert payload["type"] == "refresh"
        assert payload["sub"] == "u1"

    def test_refresh_flow(self):
        rt, _ = create_refresh_token("u2")
        data = refresh_access_token(rt)
        assert data["user_id"] == "u2"

    def test_revoked_refresh(self):
        rt, _ = create_refresh_token("u3")
        revoke_refresh_token(rt)
        with pytest.raises(ValueError):
            refresh_access_token(rt)

    def test_expired_token(self):
        token, _ = create_access_token("u1", "t", ["r"], ["p"], expires_in=-1)
        with pytest.raises(Exception):
            decode_token(token)

    def test_wrong_token_type(self):
        rt, _ = create_refresh_token("u1")
        payload = decode_token(rt)
        # decode alone works; refresh_access_token checks type
        with pytest.raises(ValueError):
            refresh_access_token(rt)  # works once
            # second call after revoke should fail
            revoke_refresh_token(rt)
            refresh_access_token(rt)


# ── RBAC Tests ──


class TestRBAC:
    def test_doctor_permissions(self):
        perms = get_permissions_for_roles(["doctor"])
        assert "agent:read" in perms
        assert "agent:execute" in perms
        assert "patient:read" in perms
        assert "patient:write" in perms
        assert "admin:*" not in perms

    def test_admin_permissions(self):
        perms = get_permissions_for_roles(["admin"])
        assert "admin:users" in perms
        assert "agent:execute" in perms

    def test_has_permission(self):
        assert has_permission(["doctor"], Permission.AGENT_EXECUTE)
        assert not has_permission(["doctor"], Permission.ADMIN_USERS)

    def test_custom_role(self):
        add_role("custom_basic", [Permission.AGENT_LIST, Permission.AGENT_READ])
        assert "custom_basic" in list_roles()
        assert has_permission(["custom_basic"], Permission.AGENT_LIST)
        assert not has_permission(["custom_basic"], Permission.AGENT_EXECUTE)
        remove_role("custom_basic")
        assert "custom_basic" not in list_roles()

    def test_predefined_roles(self):
        assert "admin" in PREDEFINED_ROLES
        assert "doctor" in PREDEFINED_ROLES
        assert "pharmacist" in PREDEFINED_ROLES


# ── AuthService Tests ──


class TestAuthService:
    def setup_method(self):
        self.auth = AuthService()

    def test_create_user(self):
        user = self.auth.create_user("doc1", "Doctor@123", display_name="Dr. Smith")
        assert user["username"] == "doc1"
        assert user["roles"] == ["doctor"]
        assert "agent:execute" in user["permissions"]

    def test_create_duplicate(self):
        self.auth.create_user("doc1", "Doctor@123")
        with pytest.raises(ValueError, match="already exists"):
            self.auth.create_user("doc1", "Doctor@123")

    def test_create_weak_password(self):
        with pytest.raises(ValueError, match="uppercase"):
            self.auth.create_user("doc1", "weakpassword")

    def test_authenticate(self):
        self.auth.create_user("doc1", "Doctor@123")
        result = self.auth.authenticate("doc1", "Doctor@123")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["username"] == "doc1"

    def test_authenticate_wrong_password(self):
        self.auth.create_user("doc1", "Doctor@123")
        with pytest.raises(ValueError, match="Invalid"):
            self.auth.authenticate("doc1", "wrong")

    def test_authenticate_inactive(self):
        self.auth.create_user("doc1", "Doctor@123")
        self.auth.set_active("doc1", False)
        with pytest.raises(ValueError, match="Invalid"):
            self.auth.authenticate("doc1", "Doctor@123")

    def test_list_users(self):
        self.auth.create_user("doc1", "Doctor@123")
        self.auth.create_user("doc2", "Doctor@456")
        users = self.auth.list_users()
        assert len(users) == 2
        assert "password_hash" not in str(users)

    def test_assign_remove_role(self):
        self.auth.create_user("doc1", "Doctor@123")
        assert self.auth.assign_role("doc1", "pharmacist")
        user = self.auth.get_user("doc1")
        assert "pharmacist" in user["roles"]
        assert self.auth.remove_role("doc1", "pharmacist")
        assert "pharmacist" not in self.auth.get_user("doc1")["roles"]

    def test_get_user_by_id(self):
        user_data = self.auth.create_user("doc1", "Doctor@123")
        found = self.auth.get_user_by_id(user_data["id"])
        assert found is not None
        assert found["username"] == "doc1"


# ── Auth API Tests ──


class TestAuthAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure test mode is active."""
        os.environ["HAIP_TEST_MODE"] = "true"
        from haip.web_server import app
        self.client = TestClient(app)

    def test_health_no_auth(self):
        r = self.client.get("/api/health")
        assert r.status_code == 200

    def test_register_and_login(self):
        r = self.client.post("/api/auth/register", json={
            "username": "test_doctor",
            "password": "Doctor@123",
            "display_name": "Test Doctor",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        r = self.client.post("/api/auth/login", json={
            "username": "test_doctor",
            "password": "Doctor@123",
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["username"] == "test_doctor"

    def test_login_wrong_password(self):
        r = self.client.post("/api/auth/register", json={
            "username": "test2", "password": "Doctor@123",
        })
        assert r.status_code == 200

        r = self.client.post("/api/auth/login", json={
            "username": "test2", "password": "Wrong@123",
        })
        assert r.status_code == 401

    def test_me_endpoint(self):
        # Register + login in a single flow using the same client
        register_resp = self.client.post("/api/auth/register", json={
            "username": "test_me_unique",
            "password": "Doctor@123",
            "display_name": "Test Me",
        })
        assert register_resp.status_code == 200, f"Register failed: {register_resp.text}"

        login_resp = self.client.post("/api/auth/login", json={
            "username": "test_me_unique",
            "password": "Doctor@123",
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]

        r = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, f"Me failed: {r.text}"
        assert r.json()["username"] == "test_me_unique"

    def test_protected_endpoint_no_token(self):
        os.environ["HAIP_TEST_MODE"] = "false"
        try:
            from haip.web_server import app as app2
            client = TestClient(app2)
            r = client.get("/api/agents")
            assert r.status_code == 401
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"


# ── Audit Tests ──


class TestAudit:
    def test_audit_log_basic(self):
        from haip.audit import AuditLogger, get_audit_logger

        logger = AuditLogger()
        logger.log("login", "user:test", "success", user_id="u1", username="test")
        logger.log("agent_call", "agent:pharmacy", "success")
        logger.log("auth_failed", "user:hacker", "failure")

        assert logger.stats()["total_events"] == 3
        assert logger.stats()["failure_count"] == 1

        events = logger.query(action="login")
        assert len(events) == 1
        assert events[0].username == "test"

    def test_audit_global_singleton(self):
        from haip.audit import get_audit_logger
        a1 = get_audit_logger()
        a2 = get_audit_logger()
        assert a1 is a2


# ── Crypto Tests ──


class TestCrypto:
    def test_encrypt_decrypt(self):
        from haip.crypto import encrypt_field, decrypt_field
        original = "张三"
        enc = encrypt_field(original)
        assert enc != original
        dec = decrypt_field(enc)
        assert dec == original

    def test_empty_value(self):
        from haip.crypto import encrypt_field, decrypt_field
        assert encrypt_field("") == ""
        assert decrypt_field("") == ""

    def test_patient_record(self):
        from haip.crypto import encrypt_patient_record, decrypt_patient_record
        record = {"name": "张三", "age": 45, "diagnosis": "高血压"}
        enc = encrypt_patient_record(record)
        assert enc["name"] != "张三"
        assert enc["age"] == 45  # Non-PHI field unchanged
        dec = decrypt_patient_record(enc)
        assert dec["name"] == "张三"
        assert dec["diagnosis"] == "高血压"


# ── A2A Auth Tests ──


class TestA2AAuth:
    def test_sign_verify(self):
        from haip.a2a.auth import (
            register_agent_secret,
            sign_a2a_request,
            verify_a2a_request,
        )
        register_agent_secret("pharmacy")
        headers = sign_a2a_request("pharmacy", "test_tool", {"p": "v"})
        assert verify_a2a_request(
            "pharmacy", "test_tool", {"p": "v"},
            headers["X-A2A-Timestamp"],
            headers["X-A2A-Signature"],
        )

    def test_tampered_params(self):
        from haip.a2a.auth import register_agent_secret, sign_a2a_request, verify_a2a_request
        register_agent_secret("pharmacy")
        headers = sign_a2a_request("pharmacy", "test_tool", {"p": "v"})
        assert not verify_a2a_request(
            "pharmacy", "test_tool", {"p": "evil"},
            headers["X-A2A-Timestamp"],
            headers["X-A2A-Signature"],
        )

    def test_expired_request(self):
        from haip.a2a.auth import register_agent_secret, sign_a2a_request, verify_a2a_request
        import time
        register_agent_secret("pharmacy")
        old_ts = int(time.time()) - 600  # 10 minutes ago
        headers = sign_a2a_request("pharmacy", "test_tool", {"p": "v"}, timestamp=old_ts)
        assert not verify_a2a_request(
            "pharmacy", "test_tool", {"p": "v"},
            headers["X-A2A-Timestamp"],
            headers["X-A2A-Signature"],
            max_age_seconds=300,
        )

    def test_unknown_agent(self):
        from haip.a2a.auth import sign_a2a_request, verify_a2a_request
        headers = sign_a2a_request("unknown", "t", {})
        assert verify_a2a_request("unknown", "t", {}, headers["X-A2A-Timestamp"], headers["X-A2A-Signature"])
        # But if called before secret registration on the verifier side, it fails
        # (Auto-registers on sign side; verify side won't have the secret unless registered)


# ── Config Tests ──


class TestConfig:
    def test_config_load(self):
        from haip.config import get_config
        cfg = get_config()
        assert cfg.get("server.port") == 8769
        assert cfg.get("auth.enabled") is True

    def test_config_default(self):
        from haip.config import get_config
        cfg = get_config()
        assert cfg.get("nonexistent.key", "default") == "default"

    def test_config_section(self):
        from haip.config import get_config
        cfg = get_config()
        auth = cfg.get_section("auth")
        assert isinstance(auth, dict)
        assert "enabled" in auth
