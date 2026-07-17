"""测试 P4: 知识库运行时 + 病例管理."""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent  # xhaip root
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

import yaml  # noqa: E402


class TestKnowledgeRuntime:
    def test_sync_from_assets(self):
        """从实际YAML资产同步到SQLite。"""
        from haip.knowledge.runtime import KnowledgeRuntime
        kb = KnowledgeRuntime(str(project_root))
        stats = kb.sync()
        assert stats["guidelines"] + stats["rules"] >= 1
        kb.close()

    def test_search_guidelines(self):
        from haip.knowledge.runtime import KnowledgeRuntime, reset_kb
        reset_kb()
        kb = KnowledgeRuntime(str(project_root))
        kb.sync()
        results = kb.search_guidelines("NICE")
        if len(results) >= 1:
            assert any("NICE" in (r.get("name", "") or "") for r in results)
        kb.close()
        reset_kb()

    def test_count_trust_levels(self):
        from haip.knowledge.runtime import KnowledgeRuntime, reset_kb
        reset_kb()
        kb = KnowledgeRuntime(str(project_root))
        kb.sync()
        counts = kb.count_by_trust_level()
        assert "T1" in counts or "T2" in counts
        kb.close()
        reset_kb()

    def test_find_rules(self):
        from haip.knowledge.runtime import KnowledgeRuntime, reset_kb
        reset_kb()
        kb = KnowledgeRuntime(str(project_root))
        kb.sync()
        rules = kb.find_rules("cardiac_delay")
        assert isinstance(rules, list)
        kb.close()
        reset_kb()

    def test_resync(self):
        from haip.knowledge.runtime import KnowledgeRuntime, reset_kb
        reset_kb()
        kb = KnowledgeRuntime(str(project_root))
        s1 = kb.sync()
        kb.resync()
        assert s1["guidelines"] > 0, "知识库同步后指南数应为正 — 检查 assets/knowledge/ 数据"
        kb.close()
        reset_kb()


class TestCaseManager:
    def test_load_patients(self):
        from haip.knowledge.cases import CaseManager
        data_dir = project_root / "packages" / "haip-hospital" / "data"
        assert data_dir.exists(), "患者数据目录缺失"
        cm = CaseManager()
        cm.load(data_dir)
        assert len(cm.cases) > 0, "患者数据加载为空 — 检查 patients.json 格式"
        s = cm.stats()
        assert "total" in s

    def test_search(self):
        from haip.knowledge.cases import CaseManager
        cm = CaseManager()
        patients_file = project_root / "packages" / "haip-hospital" / "data"
        if patients_file.exists():
            cm.load(patients_file)
        results = cm.search(department="orthopedic_surgery")
        if cm.cases:
            assert isinstance(results, list)


class TestKnowledgeGlobal:
    def test_get_kb_singleton(self):
        from haip.knowledge.runtime import get_kb, reset_kb
        reset_kb()
        kb1 = get_kb(str(project_root))
        kb2 = get_kb(str(project_root))
        assert kb1 is kb2  # 单例
        kb1.close()
        reset_kb()
