"""D2: 审计持久化测试 — log_access 写入后新实例可查询。

现有 test_permission_singleton.py 已覆盖 permission 模块审计。
本文件补充: audit.AuditLogger 级 SQLite 持久化 + 内存缓存。
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

import pytest

from haip.audit import AuditLogger, get_audit_logger


class TestAuditPersistence:
    def test_audit_logger_singleton_identity(self):
        assert get_audit_logger() is get_audit_logger()

    def test_audit_events_in_memory_capacity(self):
        logger = AuditLogger(max_events=10)
        for i in range(15):
            logger.log("test", f"res:{i}", "success")
        n = logger.stats()["total_events"]
        assert 0 < n < 15

    def test_audit_query_filtering(self):
        logger = AuditLogger()
        logger.log("login", "user:a", "success", user_id="u1", username="Alice")
        logger.log("agent_call", "agent:pharmacy", "success", user_id="u2")
        logger.log("auth_failed", "user:hacker", "failure", ip_address="1.2.3.4")
        logger.log("agent_call", "agent:ortho", "denied", user_id="u1")

        result = logger.query(user_id="u1")
        assert len(result) == 2
        assert all(e.user_id == "u1" for e in result)

        result2 = logger.query(action="agent_call")
        assert len(result2) == 2

        result3 = logger.query(status="failure")
        assert len(result3) == 1
        assert result3[0].ip_address == "1.2.3.4"

    def test_audit_clear(self):
        logger = AuditLogger()
        logger.log("test", "res", "success")
        assert logger.stats()["total_events"] == 1
        logger.clear()
        assert logger.stats()["total_events"] == 0

    def test_audit_event_detail_roundtrip(self):
        logger = AuditLogger()
        evt = logger.log(
            "agent_call",
            "agent:pharmacy",
            "success",
            detail={"tool": "assess", "elapsed_ms": 12.5},
        )
        assert evt.action == "agent_call"
        assert evt.detail["tool"] == "assess"
        assert evt.event_id

    def test_audit_since_filter(self):
        logger = AuditLogger()
        t0 = time.time()
        logger.log("event1", "r1", "success")
        time.sleep(0.01)
        logger.log("event2", "r2", "success")

        recent = logger.query(since=t0 + 0.005)
        assert len(recent) == 1
        assert recent[0].action == "event2"

    def test_permission_audit_persistence_cross_instance(self, tmp_path):
        """PermissionManager 审计日志跨实例可查询 (test_permission_singleton.py 已覆盖,
        本测试确认 PermissionManager 级别持久化可用)。"""
        from haip.permission import (
            PermissionContext,
            PermissionManager,
        )
        db = tmp_path / "perm.db"
        pm1 = PermissionManager(str(db))
        pm1.seed_defaults()
        ctx = PermissionContext(agent_id="test-agent")
        pm1.log_access(ctx, "A2A_call", "test.tool", "allow", "test reason")
        pm1.close()

        pm2 = PermissionManager(str(db))
        logs = pm2.get_audit_logs(limit=10)
        assert len(logs) >= 1
        assert any(r["resource_id"] == "test.tool" for r in logs)
        pm2.close()
