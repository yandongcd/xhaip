"""B: 认证持久化测试 — SQLite 落盘, 创建→查询跨实例。

确保:
 - tmp_path HAIP_AUTH_DB 指定路径创建用户
 - 新 AuthService 实例可以 get_user/authenticate
 - 已有测试的直接 AuthService() 构造不破坏 (测试模式下默认 :memory:)
"""

from __future__ import annotations

import os

import pytest

from haip.auth import AuthService, reset_auth_service


@pytest.fixture(autouse=True)
def _ensure_test_mode(monkeypatch):
    monkeypatch.setenv("HAIP_TEST_MODE", "true")
    reset_auth_service()


class TestAuthPersistence:
    def test_sqlite_create_and_query_new_instance(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        user = auth1.create_user(
            "persist_doc", "Doctor@123", display_name="Dr. Persist", roles=["doctor"],
        )
        assert user["username"] == "persist_doc"
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        found = auth2.get_user("persist_doc")
        assert found is not None
        assert found["display_name"] == "Dr. Persist"
        assert "doctor" in found["roles"]
        auth2.close()

    def test_sqlite_authenticate_after_reopen(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        auth1.create_user("auth_test", "Doctor@123", roles=["doctor"])
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        result = auth2.authenticate("auth_test", "Doctor@123")
        assert "access_token" in result
        assert result["user"]["username"] == "auth_test"
        with pytest.raises(ValueError, match="Invalid"):
            auth2.authenticate("auth_test", "Wrong@123")
        auth2.close()

    def test_sqlite_set_active_persists(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        auth1.create_user("deactivate_me", "Doctor@123")
        auth1.set_active("deactivate_me", False)
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        user = auth2.get_user("deactivate_me")
        assert user is not None
        assert user["is_active"] is False
        auth2.close()

    def test_sqlite_assign_remove_role_persists(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        auth1.create_user("role_test", "Doctor@123")
        auth1.assign_role("role_test", "pharmacist")
        auth1.remove_role("role_test", "doctor")
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        user = auth2.get_user("role_test")
        assert user is not None
        assert "pharmacist" in user["roles"]
        assert "doctor" not in user["roles"]
        auth2.close()

    def test_sqlite_list_users(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        auth1.create_user("u1", "Doctor@123")
        auth1.create_user("u2", "Doctor@456", roles=["pharmacist"])
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        users = auth2.list_users()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert usernames == {"u1", "u2"}
        auth2.close()

    def test_sqlite_get_user_by_id(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        user = auth1.create_user("by_id", "Doctor@123")
        uid = user["id"]
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        found = auth2.get_user_by_id(uid)
        assert found is not None
        assert found["username"] == "by_id"
        auth2.close()

    def test_seed_demo_idempotent(self, tmp_path):
        db = tmp_path / "auth.db"
        auth1 = AuthService(backend="sqlite", db_path=str(db))
        auth1.seed_demo_identities()
        n2 = auth1.seed_demo_identities()
        assert n2 == 0
        auth1.close()

        auth2 = AuthService(backend="sqlite", db_path=str(db))
        n3 = auth2.seed_demo_identities()
        assert n3 == 0
        auth2.close()

    def test_legacy_memory_backend_still_works(self):
        auth = AuthService(backend="memory")
        user = auth.create_user("legacy", "Doctor@123")
        assert user["username"] == "legacy"
        found = auth.get_user("legacy")
        assert found is not None

    def test_default_test_mode_is_memory(self):
        """HAIP_TEST_MODE=true + no explicit path → :memory: (doesn't pollute filesystem)."""
        auth = AuthService()
        auth.create_user("tm", "Doctor@123")
        assert auth.get_user("tm") is not None
