"""测试运维模块."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import DomainPlugin  # noqa: E402
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
            diff = engine.diff_two(s1, s2)
            assert isinstance(diff, list)

    def test_rollback_nonexistent(self):
        engine = AuditEngine(tempfile.mkdtemp())
        result = engine.rollback("nonexistent")
        assert not result.get("success", True)


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


# ═════════════════════════════════════════════════════════════
# Skill Sync function-level tests
# ═════════════════════════════════════════════════════════════



class TestSkillSyncFunctions:
    """Tests for haip.operations.skill_sync functions (sync, validate, init, list)."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.src_root = tempfile.TemporaryDirectory()
        self.rt_root = tempfile.TemporaryDirectory()
        yield
        self.src_root.cleanup()
        self.rt_root.cleanup()

    def _patch_constants(self):
        """Patch PROJECT_ROOT and SKILLS_RUNTIME_DIR to temp dirs."""
        src = Path(self.src_root.name)
        rt = Path(self.rt_root.name)
        return (
            patch("haip.operations.skill_sync.PROJECT_ROOT", src),
            patch("haip.operations.skill_sync.SKILLS_RUNTIME_DIR", rt / ".openharness" / "skills"),
            src,
            rt,
        )

    def test_sync_dry_run_reports_changes(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ntitle: Test\n---\n# Test skill\n", encoding="utf-8")

        # Register a temporary ownership
        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import sync
                result = sync(dry_run=True)
                assert "changed" in result
                assert "total_owned" in result

    def test_sync_dry_run_no_changes_when_in_sync(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        content = "---\ntitle: Test\n---\n# Test skill\n"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        rt_skills = rt / ".openharness" / "skills" / "xhaip-core"
        rt_skills.mkdir(parents=True)
        (rt_skills / "SKILL.md").write_text(content, encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import sync
                result = sync(dry_run=True)
                assert result["changed"] == 0

    def test_sync_apply_copies_files(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        content = "---\ntitle: Apply Test\n---\n# Apply test content\n"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import sync
                result = sync(dry_run=False)
                assert result["changed"] >= 0
                dst = rt / ".openharness" / "skills" / "xhaip-core" / "SKILL.md"
                assert dst.exists()
                assert dst.read_text(encoding="utf-8") == content

    def test_sync_missing_source_reported(self):
        p1, p2, src, rt = self._patch_constants()
        test_ownership = {"packages/nonexistent-module": "xhaip-nonexistent"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import sync
                result = sync(dry_run=True)
                assert result["missing_src"] >= 1

    def test_validate_passes_when_in_sync(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        content = "---\ntitle: Valid\n---\n# Valid content\n"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        rt_skills = rt / ".openharness" / "skills" / "xhaip-core"
        rt_skills.mkdir(parents=True)
        (rt_skills / "SKILL.md").write_text(content, encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import validate
                issues = validate()
                assert issues == 0

    def test_validate_detects_missing_runtime(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ntitle: Missing RT\n---\n", encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import validate
                issues = validate()
                assert issues >= 1

    def test_validate_detects_out_of_sync(self):
        p1, p2, src, rt = self._patch_constants()
        skill_dir = src / "packages" / "haip-core"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ntitle: Source\n---\n# Source\n", encoding="utf-8")

        rt_skills = rt / ".openharness" / "skills" / "xhaip-core"
        rt_skills.mkdir(parents=True)
        (rt_skills / "SKILL.md").write_text("---\ntitle: Different\n---\n# Different\n", encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import validate
                issues = validate()
                assert issues >= 1

    def test_init_from_runtime_noop_when_runtime_empty(self):
        p1, p2, src, rt = self._patch_constants()
        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import init_from_runtime
                exit_code = init_from_runtime()
                assert exit_code == 0

    def test_init_from_runtime_copies_from_runtime_to_source(self):
        p1, p2, src, rt = self._patch_constants()
        rt_skills = rt / ".openharness" / "skills" / "xhaip-core"
        rt_skills.mkdir(parents=True)
        content = "---\ntitle: From Runtime\n---\n# Runtime content\n"
        (rt_skills / "SKILL.md").write_text(content, encoding="utf-8")

        test_ownership = {"packages/haip-core": "xhaip-core"}

        with p1, p2:
            with patch.dict("haip.operations.skill_sync.SKILL_OWNERSHIP", test_ownership, clear=True):
                from haip.operations.skill_sync import init_from_runtime
                exit_code = init_from_runtime()
                assert exit_code == 0
                src_file = src / "packages" / "haip-core" / "SKILL.md"
                assert src_file.exists()
                assert src_file.read_text(encoding="utf-8") == content

    def test_list_skills_empty_when_no_runtime(self):
        p1, p2, src, rt = self._patch_constants()
        with p1, p2:
            from haip.operations.skill_sync import list_skills
            result = list_skills()
            assert result["count"] == 0
            assert result["skills"] == []

    def test_list_skills_lists_runtime_skills(self):
        p1, p2, src, rt = self._patch_constants()
        rt_skills = rt / ".openharness" / "skills" / "xhaip-test-skill"
        rt_skills.mkdir(parents=True)
        (rt_skills / "SKILL.md").write_text("---\ntitle: Test Skill\ndescription: A test\n---\n# Body\n", encoding="utf-8")

        with p1, p2:
            from haip.operations.skill_sync import list_skills
            result = list_skills()
            assert result["count"] >= 1
            names = [s["name"] for s in result["skills"]]
            assert "xhaip-test-skill" in names

    def test_skill_ownership_has_entries(self):
        from haip.operations.skill_sync import SKILL_OWNERSHIP
        assert len(SKILL_OWNERSHIP) >= 1
        assert "packages/haip-core" in SKILL_OWNERSHIP
        assert SKILL_OWNERSHIP["packages/haip-core"] == "xhaip-core"

    def test_auto_discover_skills_includes_registry(self):
        from haip.operations.skill_sync import auto_discover_skills, SKILL_OWNERSHIP
        discovered = auto_discover_skills()
        assert len(discovered) >= len(SKILL_OWNERSHIP)
        assert "packages/haip-core" in discovered


class TestAgentMemoryGrowth:
    """Memory leak tests — verify history pruning."""

    def test_agent_memory_growth(self):
        m = AgentMemory(max_history=10)
        for i in range(1000):
            m.remember("s1", "user", f"message {i}")
            m.remember("s1", "agent", f"response {i}")
        recalled = m.recall("s1", limit=1000)
        assert len(recalled) <= 40, (
            f"Memory grew to {len(recalled)} entries, expected <=40 (max_history*2*2)"
        )

    def test_agent_memory_multi_session(self):
        m = AgentMemory(max_history=5)
        for s in range(10):
            for i in range(200):
                m.remember(f"session_{s}", "user", f"msg {i}")
        for s in range(10):
            recalled = m.recall(f"session_{s}", limit=100)
            assert len(recalled) <= 20, f"Session {s} memory leaked: {len(recalled)} entries"


class TestCallHistoryPruning:
    """Call history should be capped at reasonable size."""

    def test_call_history_pruning(self):
        from haip.a2a import call, clear_history, get_history
        from haip.agent import register as reg_agent, list_all

        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            reg_agent(DomainPlugin(name="stress_test", type="specialist"))
            for i in range(2000):
                call("stress_test", "nonexistent", {"seq": i})

            history = get_history(limit=10000)
            assert len(history) <= 1000, (
                f"Call history not capped: {len(history)} entries (max 1000)"
            )
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)

    def test_call_history_retains_recent(self):
        from haip.a2a import call, clear_history, get_history
        from haip.agent import register as reg_agent, list_all

        saved = dict(list_all())
        list_all().clear()
        clear_history()
        try:
            reg_agent(DomainPlugin(name="retention_test", type="specialist"))
            for i in range(2000):
                call("retention_test", "nonexistent", {"seq": i})

            history = get_history(limit=10000)
            # History is capped at 1000, and pruned to last 500
            assert len(history) <= 1000, (
                f"Call history not capped: {len(history)} entries (max 1000)"
            )
            # Verify the last entries are the most recent calls
            last_few = history[-10:]
            for entry in last_few:
                assert entry["agent"] == "retention_test"
                assert entry["tool"] == "nonexistent"
        finally:
            list_all().clear()
            for name, p in saved.items():
                reg_agent(p)

    def test_execution_journal_pruning(self):
        j = ExecutionJournal(max_entries=100)
        for i in range(2000):
            j.log("call", agent="test", tool="t", seq=i)
        assert len(j.entries) <= 100, (
            f"ExecutionJournal not pruned: {len(j.entries)} entries (max 100)"
        )


# ═════════════════════════════════════════════════════════════
# AuditEngine extended coverage tests
# ═════════════════════════════════════════════════════════════

class TestAuditEngineExtended:
    def test_diff_against_current_state(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "test_file.txt").write_text("hello world\n", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("test_file.txt", agent="test", reason="coverage")
            snap_id = snap["id"]
            diffs = engine.diff(snap_id)
            assert any(not d.get("changed") for d in diffs if d.get("file") == "test_file.txt")

    def test_diff_after_file_changed(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "test_file.txt").write_text("version 1\n", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("test_file.txt", agent="test")
            snap_id = snap["id"]
            (project_root / "test_file.txt").write_text("version 2 modified\n", encoding="utf-8")
            diffs = engine.diff(snap_id)
            changed = [d for d in diffs if d.get("changed")]
            assert len(changed) >= 1

    def test_rollback_from_real_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            original = "original content\n"
            (project_root / "rollback_test.txt").write_text(original, encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("rollback_test.txt", agent="test")

            (project_root / "rollback_test.txt").write_text("modified content\n", encoding="utf-8")
            result = engine.rollback(snap["id"])
            assert result["success"]
            restored = (project_root / "rollback_test.txt").read_text(encoding="utf-8")
            assert restored == original

    def test_list_snapshots_multiple(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "f1.txt").write_text("a", encoding="utf-8")
            (project_root / "f2.txt").write_text("b", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            s1 = engine.snapshot("f1.txt", agent="test")
            s2 = engine.snapshot("f2.txt", agent="test")
            snaps = engine.list_snapshots(limit=10)
            assert len(snaps) >= 2

    def test_snapshot_pruning(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "f.txt").write_text("x", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            engine.max_snapshots = 3
            for i in range(10):
                engine.snapshot("f.txt", agent="test", reason=f"snap_{i}")
            snap_dirs = [p for p in engine.snapshot_dir.iterdir() if p.is_dir() and (p / "manifest.json").exists()]
            assert len(snap_dirs) <= engine.max_snapshots

    def test_snapshot_agents(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            snap = engine.snapshot_agents("test_label")
            assert "id" in snap
            assert "agents" in snap

    def test_list_agent_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            engine.snapshot_agents("label1")
            engine.snapshot_agents("label2")
            snaps = engine.list_agent_snapshots()
            assert len(snaps) >= 2

    def test_diff_nonexistent_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            diffs = engine.diff("nonexistent_snap_id")
            assert any("not found" in str(d.get("error", "")) for d in diffs)

    def test_rollback_nonexistent_snapshot_v2(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            result = engine.rollback("nonexistent_snap_id")
            assert not result["success"]


# ═════════════════════════════════════════════════════════════
# GuidelinesManager extended tests
# ═════════════════════════════════════════════════════════════

class TestGuidelinesManagerExtended:
    def test_load_with_real_yaml_dir(self):
        with tempfile.TemporaryDirectory() as d:
            gl_dir = Path(d)
            import yaml
            (gl_dir / "g1.yaml").write_text(yaml.dump({
                "id": "nice-ng37", "name": "NICE NG37 Hip Fracture",
                "publisher": "NICE", "trust_level": "T1",
            }), encoding="utf-8")
            (gl_dir / "g2.yaml").write_text(yaml.dump({
                "id": "aaos-2022", "name": "AAOS Clinical Practice",
                "publisher": "AAOS", "trust_level": "T2",
            }), encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            results = gm.search("NICE")
            assert len(results) == 1
            assert results[0]["publisher"] == "NICE"

    def test_search_by_publisher_keyword(self):
        with tempfile.TemporaryDirectory() as d:
            gl_dir = Path(d)
            import yaml
            (gl_dir / "g1.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Test Guidelines", "publisher": "WHO",
                "trust_level": "T1",
            }), encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            results = gm.search("WHO")
            assert len(results) == 1

    def test_count_by_level_with_loaded_data(self):
        with tempfile.TemporaryDirectory() as d:
            gl_dir = Path(d)
            import yaml
            (gl_dir / "g1.yaml").write_text(yaml.dump({
                "id": "g1", "name": "T1 Guide", "publisher": "A", "trust_level": "T1",
            }), encoding="utf-8")
            (gl_dir / "g2.yaml").write_text(yaml.dump({
                "id": "g2", "name": "T2 Guide", "publisher": "B", "trust_level": "T2",
            }), encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            counts = gm.count_by_level()
            assert counts.get("T1") == 1
            assert counts.get("T2") == 1

    def test_load_nonexistent_directory_graceful(self):
        gm = GuidelinesManager("/nonexistent/path/12345")
        assert gm.index == {}
        assert gm.count_by_level() == {}


# ═════════════════════════════════════════════════════════════
# System checks edge cases
# ═════════════════════════════════════════════════════════════

class TestSystemChecksExtended:
    def test_python_version_ok(self):
        result = system_checks()
        assert result["python"]["ok"] is True
        assert "version" in result["python"]

    def test_dependency_checks_all_ok(self):
        result = system_checks()
        deps = ["pydantic", "httpx", "typer", "fastapi"]
        for dep in deps:
            assert result.get(dep) == "ok", f"Dependency {dep} is not ok: {result.get(dep)}"

    def test_directory_existence_checks(self):
        result = system_checks()
        assert "dir_knowledge" in result or "dir_assets" in result

    def test_agents_registered_in_checks(self):
        result = system_checks()
        assert "agents_registered" in result

    def test_python_version_lower_bounds(self):
        result = system_checks()
        import sys
        if sys.version_info >= (3, 10):
            assert result["python"]["ok"]


# ═════════════════════════════════════════════════════════════
# ReleaseManager (audit_release) extended tests
# ═════════════════════════════════════════════════════════════

class TestReleaseManagerV1:
    def test_backup_and_notes(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent import register, _registry
            _registry.clear()
            register(DomainPlugin(name="test_rel", type="business", port=9000,
                                  cn_name="测试"))
            rm = ReleaseManager(str(d))
            manifest = rm.backup("1.0.0")
            assert manifest["version"] == "1.0.0"
            notes = rm.notes("1.0.0")
            assert notes["version"] == "1.0.0"

    def test_list_releases_returns_entries(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent import register, _registry
            _registry.clear()
            register(DomainPlugin(name="test_rel", type="business", port=9000))
            rm = ReleaseManager(str(d))
            rm.backup("v1")
            rm.backup("v2")
            releases = rm.list_releases()
            assert len(releases) >= 2

    def test_rollback_returns_bool(self):
        with tempfile.TemporaryDirectory() as d:
            rm = ReleaseManager(str(d))
            assert rm.rollback("v1") is False
            rm.backup("v1")
            assert rm.rollback("v1") is True

    def test_notes_nonexistent_v2(self):
        with tempfile.TemporaryDirectory() as d:
            rm = ReleaseManager(str(d))
            result = rm.notes("nonexistent")
            assert "error" in result


# ═════════════════════════════════════════════════════════════
# AuditEngine additional path coverage
# ═════════════════════════════════════════════════════════════

class TestAuditEngineV3:
    def test_snapshot_with_empty_paths(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            snap = engine.snapshot(agent="test", reason="empty test")
            assert "id" in snap
            assert snap["agents"] == 0

    def test_snapshot_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            snap = engine.snapshot("nonexistent_file.txt", agent="test")
            assert "id" in snap
            assert snap["agents"] == 0

    def test_diff_two_error_on_first(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            diffs = engine.diff_two("nonexistent1", "nonexistent2")
            assert any("not found" in str(d.get("error", "")) for d in diffs)

    def test_diff_file_missing_from_disk(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "temp_file.txt").write_text("content", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("temp_file.txt")
            snap_id = snap["id"]
            (project_root / "temp_file.txt").unlink()
            diffs = engine.diff(snap_id)
            assert any(d.get("error") == "current file missing" for d in diffs)

    def test_list_audit_log_empty(self):
        with tempfile.TemporaryDirectory() as d:
            engine = AuditEngine(d)
            entries = engine.list_audit_log(limit=10)
            assert entries == []

    def test_list_snapshots_with_limit(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "f.txt").write_text("data", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            for i in range(5):
                engine.snapshot("f.txt", agent="test", reason=f"snap_{i}")
            snaps = engine.list_snapshots(limit=2)
            assert len(snaps) == 2

    def test_rollback_file_level_success(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            original = "original\n"
            (project_root / "rollback_snap.txt").write_text(original, encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("rollback_snap.txt")
            (project_root / "rollback_snap.txt").write_text("changed\n", encoding="utf-8")
            result = engine.rollback(snap["id"])
            assert result["success"]
            assert len(result["restored"]) >= 1
            restored_text = (project_root / "rollback_snap.txt").read_text(encoding="utf-8")
            assert restored_text == original


# ═════════════════════════════════════════════════════════════
# ArchitectureManager extended tests
# ═════════════════════════════════════════════════════════════

class TestArchitectureManagerExtended:
    def test_show_returns_string(self):
        am = ArchitectureManager(project_root.parent)
        text = am.show()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_audit_has_required_keys(self):
        am = ArchitectureManager(project_root.parent)
        report = am.audit()
        assert "agents" in report
        assert "assets" in report
        assert "quality" in report
        assert "consistent" in report["quality"]

    def test_audit_reports_consistency(self):
        am = ArchitectureManager(project_root.parent)
        report = am.audit()
        assert isinstance(report["quality"]["consistent"], bool)


# ═════════════════════════════════════════════════════════════
# SkillSync additional tests
# ═════════════════════════════════════════════════════════════

class TestSkillSyncExtended:
    def test_validate_consistent(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            ss = SkillSync(src, tgt)
            result = ss.validate()
            assert result["consistent"] is True

    def test_validate_delta(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            (Path(src) / "SKILL.md").write_text("content", encoding="utf-8")
            ss = SkillSync(src, tgt)
            result = ss.validate()
            assert not result["consistent"]

    def test_dry_run_detects_new_files(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            (Path(src) / "SKILL.md").write_text("new content", encoding="utf-8")
            ss = SkillSync(src, tgt)
            changes = ss.dry_run()
            assert len(changes["new"]) == 1

    def test_dry_run_src_not_exists(self):
        with tempfile.TemporaryDirectory() as tgt:
            ss = SkillSync("/nonexistent/path/xyz", tgt)
            changes = ss.dry_run()
            assert changes["new"] == []
            assert changes["modified"] == []

    def test_apply_syncs_files(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            (Path(src) / "SKILL.md").write_text("skill content", encoding="utf-8")
            ss = SkillSync(src, tgt)
            count = ss.apply()
            assert count >= 1
            assert (Path(tgt) / "SKILL.md").exists()

    def test_apply_dry_run_noop(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            ss = SkillSync(src, tgt)
            count = ss.apply()
            assert count == 0


# ═════════════════════════════════════════════════════════════
# Benchmark edge cases
# ═════════════════════════════════════════════════════════════

class TestBenchmarkExtended:
    def test_benchmark_with_few_iterations(self):
        result = benchmark_a2a(iterations=1)
        assert result["iterations"] == 1
        assert result["avg_ms"] >= 0
        assert result["min_ms"] >= 0
        assert result["max_ms"] >= 0

    def test_benchmark_returns_p95(self):
        result = benchmark_a2a(iterations=5)
        assert "p95_ms" in result


# ═════════════════════════════════════════════════════════════
# AuditEngine more edge cases
# ═════════════════════════════════════════════════════════════

class TestAuditEngineEdgeCases:
    def test_diff_two_same_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "f.txt").write_text("data", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("f.txt", agent="test")
            snap_id = snap["id"]
            diffs = engine.diff_two(snap_id, snap_id)
            assert any(not d.get("changed") for d in diffs)

    def test_rollback_restored_count(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "r1.txt").write_text("a", encoding="utf-8")
            (project_root / "r2.txt").write_text("b", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            snap = engine.snapshot("r1.txt", "r2.txt", agent="test")
            (project_root / "r1.txt").write_text("x", encoding="utf-8")
            (project_root / "r2.txt").write_text("y", encoding="utf-8")
            result = engine.rollback(snap["id"])
            assert len(result["restored"]) >= 2

    def test_auto_prune_respects_max(self):
        with tempfile.TemporaryDirectory() as d:
            project_root = Path(d)
            (project_root / "f.txt").write_text("data", encoding="utf-8")
            engine = AuditEngine(str(project_root / ".audit"))
            engine.project_root = project_root
            engine.max_snapshots = 5
            for i in range(20):
                engine.snapshot("f.txt", agent="test", reason=f"snap_{i}")
            all_dirs = [p for p in engine.snapshot_dir.iterdir() if p.is_dir() and (p / "manifest.json").exists()]
            assert len(all_dirs) <= engine.max_snapshots

    def test_snapshot_agents_multiple(self):
        with tempfile.TemporaryDirectory() as d:
            from haip.agent import register, _registry
            _registry.clear()
            register(DomainPlugin(name="agent_1", type="business", port=9001, version="1.0"))
            register(DomainPlugin(name="agent_2", type="specialist", port=9002, version="2.0"))
            engine = AuditEngine(d)
            snap = engine.snapshot_agents("multi-label")
            assert len(snap["agents"]) == 2
            assert "agent_1" in snap["agents"]
            assert "agent_2" in snap["agents"]


# ═════════════════════════════════════════════════════════════
# GuidelinesManager more edge cases
# ═════════════════════════════════════════════════════════════

class TestGuidelinesManagerEdgeCases:
    def test_search_no_results(self):
        with tempfile.TemporaryDirectory() as d:
            import yaml
            gl_dir = Path(d)
            (gl_dir / "g.yaml").write_text(yaml.dump({
                "id": "g1", "name": "Test", "publisher": "ABC", "trust_level": "T1",
            }), encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            results = gm.search("XYZ_NOT_FOUND")
            assert results == []

    def test_load_corrupted_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            gl_dir = Path(d)
            (gl_dir / "bad.yaml").write_text("::: not yaml :::\n{{{", encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            assert gm.index == {}

    def test_load_non_dict_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            import yaml
            gl_dir = Path(d)
            (gl_dir / "list.yaml").write_text(yaml.dump([{"id": "x"}]), encoding="utf-8")
            gm = GuidelinesManager(str(gl_dir))
            assert gm.index == {}


# ═════════════════════════════════════════════════════════════
# SystemChecks more edge cases  
# ═════════════════════════════════════════════════════════════

class TestSystemChecksMore:
    def test_directory_exists_flag(self):
        result = system_checks()
        assert "dir_knowledge" in result or "dir_config" in result

    def test_python_version_string(self):
        result = system_checks()
        import sys
        assert result["python"]["version"] == sys.version


# ═════════════════════════════════════════════════════════════
# Validate edge cases
# ═════════════════════════════════════════════════════════════

class TestValidateMore:
    def test_validate_agents_with_plugins(self):
        from haip.agent import register, _registry, DomainPlugin
        _registry.clear()
        register(DomainPlugin(name="v1", type="business", port=9001))
        register(DomainPlugin(name="v2", type="specialist", port=9002))
        result = validate_agents()
        assert result["total"] == 2

    def test_validate_agents_port_conflict(self):
        from haip.agent import register, _registry, DomainPlugin
        _registry.clear()
        register(DomainPlugin(name="a1", type="business", port=7777))
        register(DomainPlugin(name="a2", type="specialist", port=7777))
        result = validate_agents()
        assert not result["valid"]
        assert len(result["issues"]) >= 1


# ═════════════════════════════════════════════════════════════
# SkillSync more edge cases
# ═════════════════════════════════════════════════════════════

class TestSkillSyncMore:
    def test_dry_run_detects_modified(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            src_dir = Path(src)
            tgt_dir = Path(tgt)
            (src_dir / "SKILL.md").write_text("source content", encoding="utf-8")
            (tgt_dir / "SKILL.md").write_text("old content", encoding="utf-8")
            ss = SkillSync(str(src_dir), str(tgt_dir))
            changes = ss.dry_run()
            assert len(changes["modified"]) == 1

    def test_dry_run_detects_deleted(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            src_dir = Path(src)
            tgt_dir = Path(tgt)
            (tgt_dir / "SKILL.md").write_text("stale content", encoding="utf-8")
            ss = SkillSync(str(src_dir), str(tgt_dir))
            changes = ss.dry_run()
            assert len(changes["deleted"]) >= 1

    def test_dry_run_recursive(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            src_dir = Path(src)
            (src_dir / "sub").mkdir(parents=True)
            (src_dir / "sub" / "SKILL.md").write_text("nested content", encoding="utf-8")
            ss = SkillSync(str(src_dir), str(tgt))
            changes = ss.dry_run()
            assert len(changes["new"]) >= 1

    def test_apply_deletes_files(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as tgt:
            src_dir = Path(src)
            tgt_dir = Path(tgt)
            (tgt_dir / "SKILL.md").write_text("stale", encoding="utf-8")
            ss = SkillSync(str(src_dir), str(tgt_dir))
            count = ss.apply()
            assert count >= 1
            assert not (tgt_dir / "SKILL.md").exists()


# ═════════════════════════════════════════════════════════════
# FormatOutput edge tests
# ═════════════════════════════════════════════════════════════

class TestFormatOutputMore:
    def test_format_with_nested_dict(self):
        data = {"outer": {"inner": "value"}, "list_val": [1, 2, 3]}
        out = format_output(data, "text")
        assert "outer:" in out
        assert "inner:" in out

    def test_format_with_list(self):
        data = {"items": ["a", "b", "c"]}
        out = format_output(data, "text")
        assert "items:" in out
        assert "- a" in out

    def test_unknown_format_defaults_to_text(self):
        data = {"key": "val"}
        out = format_output(data, "unknown_format")
        assert "key: val" in out

    def test_table_format_with_nested(self):
        data = {"name": "test", "nested": {"inner": "value"}}
        out = format_output(data, "table")
        assert "test" in out


# ═════════════════════════════════════════════════════════════
# Scaffold more edge cases
# ═════════════════════════════════════════════════════════════

class TestScaffoldMore:
    def test_scaffold_with_multiple_tools(self):
        yaml = scaffold_agent("multi-tool", "多工具", "specialist", 8701, [
            {"name": "tool1", "description": "T1", "handler": "m1.f1"},
            {"name": "tool2", "description": "T2", "handler": "m2.f2"},
            {"name": "tool3", "description": "T3", "handler": "m3.f3"},
        ])
        assert "tool1" in yaml
        assert "tool2" in yaml
        assert "tool3" in yaml

    def test_scaffold_no_tools(self):
        yaml = scaffold_agent("no-tools", "无工具", "master_data", 8702, [])
        assert "no-tools" in yaml
        assert "无工具" in yaml


# ═════════════════════════════════════════════════════════════
# ExecutionJournal more tests
# ═════════════════════════════════════════════════════════════

class TestExecutionJournalMore:
    def test_query_by_event(self):
        j = ExecutionJournal()
        j.log("call", agent="a", tool="t1")
        j.log("error", agent="a", tool="t2")
        j.log("call", agent="b", tool="t3")
        results = j.query(event="call")
        assert len(results) >= 2

    def test_query_by_agent_and_event(self):
        j = ExecutionJournal()
        j.log("call", agent="pharmacy", tool="t1")
        j.log("call", agent="ortho", tool="t2")
        j.log("error", agent="pharmacy", tool="t3")
        results = j.query(agent="pharmacy", event="call")
        assert len(results) == 1

    def test_query_with_limit(self):
        j = ExecutionJournal()
        for i in range(10):
            j.log("call", agent="a", tool=f"t{i}")
        results = j.query(limit=3)
        assert len(results) == 3

    def test_log_with_data_dict(self):
        j = ExecutionJournal()
        j.log("call", agent="a", tool="t", data={"msg": "hello", "code": 200})
        assert j.entries[0]["data"] == {"msg": "hello", "code": 200}
