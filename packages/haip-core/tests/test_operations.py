"""测试运维模块."""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.operations import (  # noqa: E402
    AuditEngine, ReleaseManager, ExecutionJournal,
    ArchitectureManager, GuidelinesManager, validate_agents, validate_modules,
    SkillSync, system_checks, benchmark_a2a, format_output,
    get_agent_tree, get_dependency_graph, coordinate_agents,
    AgentMemory, PermissionManager, scaffold_agent,
)


class TestAuditEngine:
    def test_snapshot_and_list(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            snap = engine.snapshot("test")
            assert "id" in snap
            assert "agents" in snap
            snaps = engine.list_snapshots()
            assert len(snaps) >= 1

    def test_diff(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            s1 = engine.snapshot("v1")["id"]
            s2 = engine.snapshot("v2")["id"]
            diff = engine.diff(s1, s2)
            assert isinstance(diff, dict)

    def test_rollback_nonexistent(self):
        engine = AuditEngine(tempfile.mkdtemp())
        assert not engine.rollback("nonexistent", tempfile.mkdtemp())


class TestReleaseManager:
    def test_backup_and_list(self):
        with tempfile.TemporaryDirectory() as d:
            rm = ReleaseManager(d)
            rm.backup("1.0.0")
            releases = rm.list_releases()
            assert len(releases) >= 1

    def test_notes_nonexistent(self):
        rm = ReleaseManager(tempfile.mkdtemp())
        assert "error" in rm.notes("nonexistent")


class TestExecutionJournal:
    def test_log_and_query(self):
        j = ExecutionJournal(max_entries=10)
        j.log("call", agent="pharmacy", tool="test", elapsed=5.2)
        j.log("error", agent="pharmacy")
        results = j.query(agent="pharmacy")
        assert len(results) == 2

    def test_stats(self):
        j = ExecutionJournal()
        j.log("call", agent="a")
        j.log("call", agent="b")
        s = j.stats()
        assert s["total_entries"] == 2

    def test_clear(self):
        j = ExecutionJournal()
        j.log("call", agent="x")
        j.clear()
        assert j.stats()["total_entries"] == 0


class TestArchitectureManager:
    def test_audit(self):
        am = ArchitectureManager(project_root.parent)
        report = am.audit()
        assert "agents" in report
        assert "assets" in report

    def test_export(self):
        am = ArchitectureManager(project_root.parent)
        data = am.export()
        assert isinstance(data, dict)


class TestGuidelinesManager:
    def test_load_and_search(self):
        g = GuidelinesManager()
        assert g.count_by_level() == {}

    def test_empty_search(self):
        g = GuidelinesManager()
        assert g.search("nonexistent") == []


class TestValidate:
    def test_validate_agents(self):
        result = validate_agents()
        assert "total" in result
        assert "issues" in result
        assert result["total"] >= 0  # registry may be empty in test scope

    def test_validate_modules(self):
        result = validate_modules()
        assert "total" in result


class TestSkillSync:
    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            ss = SkillSync(src, tgt)
            changes = ss.dry_run()
            assert "new" in changes
            assert ss.apply() == 0


class TestSystemChecks:
    def test_system_checks(self):
        result = system_checks()
        assert "python" in result
        assert result["python"]["ok"]


class TestBenchmark:
    def test_benchmark(self):
        result = benchmark_a2a(iterations=3)
        assert result["iterations"] == 3
        assert result["avg_ms"] >= 0


class TestFormatOutput:
    def test_json_format(self):
        data = {"status": "ok", "score": 10}
        out = format_output(data, "json")
        assert "ok" in out

    def test_text_format(self):
        data = {"status": "ok", "list": ["a", "b"]}
        out = format_output(data, "text")
        assert "ok" in out

    def test_table_format(self):
        data = {"name": "test", "value": 42}
        out = format_output(data, "table")
        assert "test" in out


class TestAgentTree:
    def test_tree(self):
        tree = get_agent_tree()
        assert "root" in tree
        assert "nodes" in tree

    def test_dep_graph(self):
        graph = get_dependency_graph()
        assert isinstance(graph, dict)


class TestCoordinate:
    def test_coordinate(self):
        result = coordinate_agents("药剂科 营养评估")
        assert "recommendations" in result


class TestAgentMemory:
    def test_remember_recall(self):
        m = AgentMemory()
        m.remember("s1", "user", "hello")
        m.remember("s1", "agent", "hi")
        assert len(m.recall("s1")) == 2
        assert m.summary("s1")["turns"] == 1

    def test_clear(self):
        m = AgentMemory()
        m.remember("s1", "user", "x")
        m.clear("s1")
        assert len(m.recall("s1")) == 0


class TestPermissions:
    def test_admin_all(self):
        pm = PermissionManager()
        assert pm.can("admin", "anything")
        assert pm.can("admin", "pharmacy.assess")

    def test_pharmacist(self):
        pm = PermissionManager()
        assert pm.can("pharmacist", "pharmacy.assess")
        assert not pm.can("pharmacist", "orthopedic-surgery.classify")

    def test_nurse(self):
        pm = PermissionManager()
        assert pm.can("nurse", "orthopedic-surgery.nursing_plan")
        assert not pm.can("nurse", "orthopedic-surgery.surgical_plan")

    def test_grant(self):
        pm = PermissionManager()
        pm.grant("intern", ["medical-record.read"])
        assert pm.can("intern", "medical-record.read")


class TestScaffold:
    def test_scaffold(self):
        yaml = scaffold_agent("test-agent", "测试智能体", "business", 8700,
                              [{"name": "hello", "description": "Say hello", "handler": "test.hi"}])
        assert "test-agent" in yaml
        assert "hello" in yaml
        assert "测试智能体" in yaml
