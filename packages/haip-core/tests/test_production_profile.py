"""D: 生产安全 Profile 测试 — HAIP_ENV=production 行为验证。

验证:
 - CORS 不含 "*"
 - rate_limit 默认启用
 - demo 不种子 (除非 HAIP_SEED_DEMO_USERS=1)
 - security_baseline 严格模式 (违规→raise)
"""

from __future__ import annotations

import os

import pytest


class TestProductionProfile:
    def test_production_cors_is_restricted(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "production")
        # production 模式下 jwt.py 模块级强制校验 JWT_SECRET_KEY, 需显式注入
        monkeypatch.setenv("JWT_SECRET_KEY", "prod-secret-" + "x" * 24)
        monkeypatch.setenv("ENCRYPTION_KEY", "y" * 32)
        from haip.web_server import _get_cors_origins
        origins = _get_cors_origins()
        assert "*" not in origins

    def test_development_cors_is_wildcard(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "development")
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        from haip.web_server import _get_cors_origins
        origins = _get_cors_origins()
        assert "*" in origins

    def test_production_rate_limit_enabled(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "production")
        from haip.web_server import _get_rate_limit_config
        cfg = _get_rate_limit_config()
        assert cfg["enabled"] is True

    def test_development_rate_limit_disabled(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "development")
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        from haip.web_server import _get_rate_limit_config
        cfg = _get_rate_limit_config()
        assert cfg["enabled"] is False

    def test_production_demo_not_seeded_without_flag(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HAIP_ENV", "production")
        monkeypatch.setenv("HAIP_AUTH_DB", str(tmp_path / "auth.db"))
        monkeypatch.delenv("HAIP_SEED_DEMO_USERS", raising=False)
        from haip.auth import AuthService, reset_auth_service
        reset_auth_service()
        auth = AuthService(backend="sqlite", db_path=str(tmp_path / "auth.db"))
        n = auth.seed_demo_identities()
        assert n == 0
        auth.close()
        reset_auth_service()

    def test_production_demo_seeded_with_flag(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HAIP_ENV", "production")
        monkeypatch.setenv("HAIP_SEED_DEMO_USERS", "1")
        monkeypatch.setenv("HAIP_DEMO_PASSWORD", "TestDemo@123")
        monkeypatch.setenv("HAIP_AUTH_DB", str(tmp_path / "auth.db"))
        from haip.auth import AuthService, reset_auth_service
        reset_auth_service()
        auth = AuthService(backend="sqlite", db_path=str(tmp_path / "auth.db"))
        n = auth.seed_demo_identities()
        assert n > 0
        auth.close()
        reset_auth_service()

    def test_production_baseline_strict(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "production")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        from haip.security_baseline import SecurityBaselineError, check_security_baseline
        with pytest.raises(SecurityBaselineError):
            check_security_baseline()

    def test_production_baseline_passes_when_configured(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "prod-secret-" + "x" * 24)
        monkeypatch.setenv("HAIP_ADMIN_PASSWORD", "Pr0d!AdminPass")
        monkeypatch.setenv("HAIP_DOCTOR_PASSWORD", "Pr0d!DoctorPass")
        monkeypatch.setenv("ENCRYPTION_KEY", "x" * 32)
        from haip.security_baseline import check_security_baseline
        assert check_security_baseline() == []

    def test_is_production_mode_detection(self, monkeypatch):
        monkeypatch.setenv("HAIP_ENV", "production")
        from haip.security_baseline import is_production_mode
        assert is_production_mode() is True

        monkeypatch.setenv("HAIP_ENV", "development")
        monkeypatch.delenv("HAIP_STRICT_SECURITY", raising=False)
        assert is_production_mode() is False

        monkeypatch.setenv("HAIP_STRICT_SECURITY", "true")
        monkeypatch.setenv("HAIP_ENV", "development")
        assert is_production_mode() is True  # backward compat
