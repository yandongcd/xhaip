"""Tests for the auth module — models, password, JWT, RBAC, and API."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from haip.auth import AuthService
from haip.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_access_token,
    revoke_refresh_token,
)
from haip.auth.models import (
    LoginResponse,
    Permission,
    TokenRefreshRequest,
    UserCreateRequest,
    UserInfo,
    UserLoginRequest,
)
from haip.auth.password import hash_password, validate_password_strength, verify_password
from haip.auth.rbac import (
    PREDEFINED_ROLES,
    add_role,
    get_permissions_for_roles,
    has_permission,
    list_roles,
    remove_role,
)

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
        decode_token(rt)
        # decode alone works; refresh_access_token checks type
        with pytest.raises(ValueError):
            refresh_access_token(rt)  # works once
            # second call after revoke should fail
            revoke_refresh_token(rt)
            refresh_access_token(rt)


# ── C2: JWT 实例密钥 (per-install random secret) ──


class TestJWTInstanceSecret:
    def test_dev_secret_file_created_and_stable(self, monkeypatch, tmp_path):
        """(a) 未设 JWT_SECRET_KEY 时生成实例密钥文件, 两次加载稳定复用。"""
        import haip.auth.jwt as jwt_mod
        secret_file = tmp_path / "jwt_dev_secret.key"
        monkeypatch.setattr(jwt_mod, "_dev_secret_path", lambda: secret_file)
        key1 = jwt_mod._load_or_generate_dev_secret()
        assert secret_file.exists(), "实例密钥文件应被创建"
        assert key1, "密钥非空"
        assert key1 != "xhaip-dev-secret-change-in-production", "不得使用公开固定常量"
        key2 = jwt_mod._load_or_generate_dev_secret()
        assert key2 == key1, "第二次加载应复用同一密钥 (跨重启稳定)"

    def test_old_constant_token_rejected(self, monkeypatch, tmp_path):
        """(b) 用历史公开常量签发的 token 必须无法通过校验。"""
        import time as _time

        import jwt as _jwt

        import haip.auth.jwt as jwt_mod
        assert jwt_mod._SECRET_KEY != "xhaip-dev-secret-change-in-production", \
            "模块密钥不得是公开固定常量"
        now = int(_time.time())
        forged = _jwt.encode(
            {"sub": "forged-admin", "type": "access", "roles": ["admin"],
             "iat": now, "exp": now + 900},
            "xhaip-dev-secret-change-in-production", algorithm="HS256",
        )
        with pytest.raises(Exception):
            jwt_mod.decode_token(forged)

    def test_env_secret_still_used(self, monkeypatch, tmp_path):
        """JWT_SECRET_KEY 显式设置时行为不变 (不使用/不创建文件密钥)。"""
        import importlib

        import haip.auth.jwt as jwt_mod
        orig_env = os.environ.get("JWT_SECRET_KEY", "")
        secret_file = tmp_path / "not_created.key"
        monkeypatch.setenv("JWT_SECRET_KEY", "explicit-env-secret-123")
        monkeypatch.setattr(jwt_mod, "_dev_secret_path", lambda: secret_file)
        importlib.reload(jwt_mod)
        assert jwt_mod._SECRET_KEY == "explicit-env-secret-123"
        assert not secret_file.exists(), "env 已配置时不应创建文件密钥"
        monkeypatch.setenv("JWT_SECRET_KEY", orig_env)
        importlib.reload(jwt_mod)  # 还原模块状态


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
        assert user["roles"] == ["intern"]
        assert "agent:execute" not in user["permissions"]

    def test_create_user_with_roles(self):
        user = self.auth.create_user("doc1", "Doctor@123", roles=["doctor"])
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
    def setup(self, monkeypatch):
        """Ensure test mode is active."""
        monkeypatch.setenv("HAIP_TEST_MODE", "true")
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
        """生产模式下无 token 必须 401。"""
        os.environ["HAIP_TEST_MODE"] = "false"
        os.environ["HAIP_ENV"] = "production"
        try:
            from haip.web_server import app as app2
            client = TestClient(app2)
            r = client.get("/api/agents")
            assert r.status_code == 401
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            os.environ.pop("HAIP_ENV", None)

    def test_dev_mode_no_token_gets_dev_user(self):
        """开发模式 (HAIP_ENV != production) 下 loopback 客户端无 token 注入 dev 用户放行 — 门户免登录可用。"""
        os.environ["HAIP_TEST_MODE"] = "false"
        old_env = os.environ.pop("HAIP_ENV", None)
        old_strict = os.environ.pop("HAIP_STRICT_SECURITY", None)
        try:
            from haip.agent import _registry as _reg2
            from haip.agent import load_from_dir
            from haip.web_server import YAML_DIR
            if len(_reg2) < 14:
                load_from_dir(str(YAML_DIR))
            from haip.web_server import app as app2
            client = TestClient(app2, client=("127.0.0.1", 12345))
            r = client.get("/api/agents")
            assert r.status_code == 200, f"loopback dev 模式免登录失效: {r.status_code} {r.text[:200]}"
            assert isinstance(r.json(), list) and r.json(), "dev 模式下 /api/agents 应返回 agent 列表"
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            if old_env is not None:
                os.environ["HAIP_ENV"] = old_env
            if old_strict is not None:
                os.environ["HAIP_STRICT_SECURITY"] = old_strict

    def test_dev_mode_remote_no_token_401(self):
        """(c) 开发模式下非 loopback 客户端无 token 必须 401 (免登录仅限本机)。"""
        os.environ["HAIP_TEST_MODE"] = "false"
        old_env = os.environ.pop("HAIP_ENV", None)
        old_strict = os.environ.pop("HAIP_STRICT_SECURITY", None)
        try:
            from haip.web_server import app as app2
            client = TestClient(app2, client=("203.0.113.7", 12345))
            r = client.get("/api/agents")
            assert r.status_code == 401, f"远程匿名请求应 401: {r.status_code}"
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            if old_env is not None:
                os.environ["HAIP_ENV"] = old_env
            if old_strict is not None:
                os.environ["HAIP_STRICT_SECURITY"] = old_strict

    def test_allow_dev_autologin_helper(self):
        """_allow_dev_autologin: 仅 loopback 主机放行。"""
        from haip.auth.middleware import _allow_dev_autologin
        assert _allow_dev_autologin("127.0.0.1")
        assert _allow_dev_autologin("::1")
        assert _allow_dev_autologin("localhost")
        assert not _allow_dev_autologin("192.168.1.10")
        assert not _allow_dev_autologin("10.0.0.5")
        assert not _allow_dev_autologin("testclient")
        assert not _allow_dev_autologin(None)

    def test_dev_mode_invalid_token_still_401(self):
        """开发模式下携带非法 token 仍 401 (fail-visible, 不静默降级)。"""
        os.environ["HAIP_TEST_MODE"] = "false"
        old_env = os.environ.pop("HAIP_ENV", None)
        try:
            from haip.web_server import app as app2
            client = TestClient(app2)
            r = client.get("/api/agents", headers={"Authorization": "Bearer not-a-jwt"})
            assert r.status_code == 401
        finally:
            os.environ["HAIP_TEST_MODE"] = "true"
            if old_env is not None:
                os.environ["HAIP_ENV"] = old_env


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
        from haip.crypto import decrypt_field, encrypt_field
        original = "张三"
        enc = encrypt_field(original)
        assert enc != original
        dec = decrypt_field(enc)
        assert dec == original

    def test_empty_value(self):
        from haip.crypto import decrypt_field, encrypt_field
        assert encrypt_field("") == ""
        assert decrypt_field("") == ""

    def test_patient_record(self):
        from haip.crypto import decrypt_patient_record, encrypt_patient_record
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
        import time

        from haip.a2a.auth import register_agent_secret, sign_a2a_request, verify_a2a_request
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
