"""住院医病历书写辅助测试 (角色洞察: 高价值错配之一; 草稿必须进签核闭环)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))


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


class TestProgressNote:
    def test_draft_with_real_patient(self, signoff_db):
        from medical_docs import draft_progress_note
        r = draft_progress_note(patient_id="P001", chief_complaint="摔倒后左髋疼痛3小时",
                                present_illness="患者3小时前不慎摔倒", 
                                exam_findings="左下肢短缩外旋畸形")
        assert r["status"] == "ok"
        assert r["note_type"] == "首次病程记录"
        for sec in ("主诉", "现病史", "体格检查", "初步诊断", "诊疗计划"):
            assert sec in r["sections"], f"缺章节: {sec}"
        assert "P001" in r["content"]
        assert r["sections"]["主诉"] == "摔倒后左髋疼痛3小时"
        assert "审核" in r["disclaimer"]

    def test_draft_creates_pending_signoff(self, signoff_db):
        from haip.signoff import get_signoff_manager
        from medical_docs import draft_progress_note
        r = draft_progress_note(patient_id="P001", chief_complaint="x")
        assert r["signoff_id"]
        rec = get_signoff_manager().get(r["signoff_id"])
        assert rec is not None and rec["status"] == "pending"
        assert rec["patient_id"] == "P001"

    def test_unknown_patient_still_drafts_with_warning(self, signoff_db):
        from medical_docs import draft_progress_note
        r = draft_progress_note(patient_id="NO-SUCH", chief_complaint="x")
        assert r["status"] == "ok"
        assert r["warnings"], "未知患者应给出警示"

    def test_incomplete_sections_flagged(self, signoff_db):
        """占位章节 (待补充) 必须触发警示 + 完整度 <1 (红线自审 V6)."""
        from medical_docs import draft_progress_note
        r = draft_progress_note(patient_id="P001", chief_complaint="外伤后髋痛")
        assert r["completeness"] < 1.0
        assert any("待补充" in w for w in r["warnings"])


class TestDischargeSummary:
    def test_draft_discharge(self, signoff_db):
        from medical_docs import draft_discharge_summary
        r = draft_discharge_summary(
            patient_id="P001", course="入院后完善检查, 行手术治疗, 恢复顺利",
            discharge_meds=["利伐沙班 10mg qd", "碳酸钙 0.6g qd"],
            followup="术后1个月门诊复查")
        assert r["status"] == "ok"
        assert r["note_type"] == "出院小结"
        for sec in ("入院情况", "诊疗经过", "出院情况", "出院医嘱", "随访计划"):
            assert sec in r["sections"], f"缺章节: {sec}"
        assert "利伐沙班 10mg qd" in r["content"]
        assert r["signoff_id"]


class TestA2AIntegration:
    def test_call_via_registry(self, signoff_db):
        from haip.a2a import call
        from haip.agent import load_from_dir
        load_from_dir(str(ROOT / "packages" / "haip-hospital" / "agents" / "definitions"))
        r = call("medical-docs", "draft_progress_note",
                 {"patient_id": "P001", "chief_complaint": "外伤后髋痛"})
        assert r["status"] == "ok"
        assert r["note_type"] == "首次病程记录"
