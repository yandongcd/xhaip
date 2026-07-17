"""医生签核工作流测试 (商用 M3 / 临床 C1: AI 建议 → 复核 → 采纳/驳回 → 留痕)."""

from __future__ import annotations

import pytest


@pytest.fixture()
def signoff_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HAIP_SIGNOFF_DB", str(tmp_path / "signoff.db"))
    monkeypatch.setenv("HAIP_PERMISSION_DB", str(tmp_path / "perm.db"))
    from haip.permission import reset_permission_manager
    from haip.signoff import reset_signoff_manager
    reset_signoff_manager()
    reset_permission_manager()
    yield
    reset_signoff_manager()
    reset_permission_manager()


class TestSignoffLifecycle:
    def test_create_and_pending(self, signoff_db):
        from haip.signoff import get_signoff_manager
        sm = get_signoff_manager()
        sid = sm.create(agent="orthopedic-surgery", tool="timing_decision",
                        patient_id="P001", output_summary="建议 48h 内手术",
                        risk_level="high")
        assert sid
        pending = sm.list_pending()
        assert any(r["id"] == sid and r["status"] == "pending" for r in pending)

    def test_approve(self, signoff_db):
        from haip.signoff import get_signoff_manager
        sm = get_signoff_manager()
        sid = sm.create(agent="a", tool="t", patient_id="P001", output_summary="x")
        rec = sm.decide(sid, reviewer_id="dr_001", decision="approved")
        assert rec["status"] == "approved"
        assert rec["reviewer_id"] == "dr_001"
        assert rec["decided_at"]

    def test_reject_requires_reason(self, signoff_db):
        from haip.signoff import get_signoff_manager
        sm = get_signoff_manager()
        sid = sm.create(agent="a", tool="t", patient_id="P001", output_summary="x")
        with pytest.raises(ValueError):
            sm.decide(sid, reviewer_id="dr_001", decision="rejected", reason="")
        rec = sm.decide(sid, reviewer_id="dr_001", decision="rejected", reason="与影像不符")
        assert rec["status"] == "rejected"
        assert rec["reason"] == "与影像不符"

    def test_decide_twice_forbidden(self, signoff_db):
        from haip.signoff import get_signoff_manager
        sm = get_signoff_manager()
        sid = sm.create(agent="a", tool="t", patient_id="P001", output_summary="x")
        sm.decide(sid, reviewer_id="dr_001", decision="approved")
        with pytest.raises(ValueError):
            sm.decide(sid, reviewer_id="dr_002", decision="rejected", reason="r")

    def test_persists_across_restart(self, signoff_db):
        from haip.signoff import get_signoff_manager, reset_signoff_manager
        sid = get_signoff_manager().create(agent="a", tool="t", patient_id="P002",
                                           output_summary="y")
        reset_signoff_manager()
        rec = get_signoff_manager().get(sid)
        assert rec and rec["patient_id"] == "P002"

    def test_decision_writes_permission_audit(self, signoff_db):
        """签核决定必须落权限审计库 (D2 管道复用)."""
        from haip.permission import get_permission_manager
        from haip.signoff import get_signoff_manager
        sm = get_signoff_manager()
        sid = sm.create(agent="a", tool="t", patient_id="P001", output_summary="x")
        sm.decide(sid, reviewer_id="dr_001", decision="approved")
        logs = get_permission_manager().get_audit_logs(limit=10, action="SIGNOFF")
        assert logs and any("approved" in (r["decision"] or "") for r in logs)


class TestSignoffHttp:
    def test_guard_high_risk_creates_signoff(self, signoff_db):
        """/api/guard 判定需人工复核时自动建签核单并返回 signoff_id."""
        import os
        os.environ["HAIP_TEST_MODE"] = "true"
        from fastapi.testclient import TestClient
        from haip.web_server import app
        client = TestClient(app)
        r = client.post("/api/guard", json={
            "output": "建议立即行 THA 手术。",  # 高危场景无引文 → 低置信 → 需复核
            "scenario": "手术决策", "agent": "orthopedic-surgery",
            "patient_id": "P001",
        })
        data = r.json()
        assert data["requires_human_review"] is True
        assert data.get("signoff_id"), "需复核的输出必须生成签核单"

    def test_signoff_endpoints(self, signoff_db):
        import os
        os.environ["HAIP_TEST_MODE"] = "true"
        from fastapi.testclient import TestClient
        from haip.signoff import get_signoff_manager
        from haip.web_server import app
        client = TestClient(app)
        sid = get_signoff_manager().create(agent="a", tool="t", patient_id="P001",
                                           output_summary="x")
        r = client.get("/api/signoff/pending")
        assert r.status_code == 200
        assert any(rec["id"] == sid for rec in r.json()["items"])
        r2 = client.post(f"/api/signoff/{sid}/decision",
                         json={"reviewer_id": "dr_001", "decision": "approved"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"
