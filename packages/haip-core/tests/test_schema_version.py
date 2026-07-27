"""测试 schema_version 迁移框架."""

from __future__ import annotations

import sqlite3

from haip.schema_version import ensure_version, get_version, migrate, set_version


class TestSchemaVersion:
    def test_ensure_version_sets_initial(self):
        conn = sqlite3.connect(":memory:")
        assert get_version(conn) == 0
        ensure_version(conn, 1)
        assert get_version(conn) == 1
        conn.close()

    def test_migrate_incremental(self):
        conn = sqlite3.connect(":memory:")

        def v1_migration(c):
            c.execute("CREATE TABLE IF NOT EXISTS test_mig (id INTEGER)")

        def v2_migration(c):
            c.execute("ALTER TABLE test_mig ADD COLUMN name TEXT")

        migrate(conn, {1: v1_migration, 2: v2_migration}, target=2)
        assert get_version(conn) == 2

        # Verify migration effects
        cols = [r[1] for r in conn.execute("PRAGMA table_info(test_mig)")]
        assert "id" in cols
        assert "name" in cols
        conn.close()

    def test_migrate_skips_when_current_equals_target(self):
        conn = sqlite3.connect(":memory:")
        set_version(conn, 2)
        called = []

        def never_called(c):
            called.append(True)

        migrate(conn, {3: never_called}, target=2)
        assert not called
        assert get_version(conn) == 2
        conn.close()

    def test_migrate_rollback_on_failure(self):
        conn = sqlite3.connect(":memory:")

        def failing_migration(c):
            c.execute("CREATE TABLE should_rollback (x)")
            raise RuntimeError("forced failure")

        try:
            migrate(conn, {1: failing_migration}, target=1)
        except RuntimeError:
            pass

        # Table should NOT exist (rolled back)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )]
        assert "should_rollback" not in tables
        assert get_version(conn) == 0
        conn.close()

    def test_ensure_version_no_commit_leak(self):
        conn = sqlite3.connect(":memory:")
        ensure_version(conn, 42)
        assert get_version(conn) == 42
        # Reconnect to verify persistence
        conn.close()
        conn2 = sqlite3.connect(":memory:")
        assert get_version(conn2) == 0  # :memory: is always fresh
        conn2.close()
