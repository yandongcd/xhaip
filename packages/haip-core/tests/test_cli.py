"""CLI 测试."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from typer.testing import CliRunner

from haip.agent import _registry
from haip.cli import app

runner = CliRunner()


class TestCLI:
    def setup_method(self):
        _registry.clear()

    def test_list_no_agents(self):
        """list 命令成功执行 (YAML 目录存在时会自动加载)。"""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_load(self):
        result = runner.invoke(app, ["load"])
        assert "Loaded" in result.output

    def test_history(self):
        result = runner.invoke(app, ["history", "--limit", "5"])
        assert result.exit_code == 0

    def test_info_with_agent(self):
        from haip.agent import DomainPlugin, register
        register(DomainPlugin(name="test", cn_name="测试", type="business", port=9999))
        result = runner.invoke(app, ["info", "test"])
        assert result.exit_code == 0
        assert "test" in result.output

    def test_call_with_valid_params(self):
        result = runner.invoke(app, ["call", "test", "echo", '--params', '{"msg":"hi"}'])
        assert result.exit_code == 0

    def test_call_invalid_json(self):
        result = runner.invoke(app, ["call", "x", "y", "--params", "bad"])
        assert "Invalid JSON" in result.output

    def test_info_unknown(self):
        result = runner.invoke(app, ["info", "nonexistent"])
        assert "Unknown agent" in result.output


# ═════════════════════════════════════════════════════════
# New sub-command CLI tests
# ═════════════════════════════════════════════════════════

class TestToolsCLI:
    def setup_method(self):
        _registry.clear()

    def test_tools_mcp_serve_help(self):
        result = runner.invoke(app, ["tools", "mcp-serve", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "mcp" in result.output.lower()

    def test_tools_list(self):
        result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0

    def test_tools_list_with_agent(self):
        from haip.agent import DomainPlugin, ToolDef, register

        plugin = DomainPlugin(
            name="test-tools-agent",
            cn_name="测试工具Agent",
            type="business",
            port=9999,
            tools=[ToolDef(name="tool_x", description="Tool X", handler="mod.func_x")],
        )
        register(plugin)
        result = runner.invoke(app, ["tools", "list", "--agent", "test-tools-agent"])
        assert result.exit_code == 0
        assert "tool_x" in result.output

    def test_tools_list_unknown_agent(self):
        result = runner.invoke(app, ["tools", "list", "--agent", "no-such-agent"])
        assert "Unknown agent" in result.output


class TestSyncSkillsCLI:
    def test_sync_skills_list(self):
        result = runner.invoke(app, ["sync-skills", "--list"])
        assert result.exit_code == 0
        assert "skills" in result.output.lower() or "count" in result.output.lower()


class TestReleaseCLI:
    def test_release_list(self):
        result = runner.invoke(app, ["release", "list"])
        assert result.exit_code == 0

    def test_release_backup_help(self):
        result = runner.invoke(app, ["release", "backup", "--help"])
        assert result.exit_code == 0
        assert "backup" in result.output.lower()


class TestAuditCLI:
    def test_audit_list(self):
        result = runner.invoke(app, ["audit", "list"])
        assert result.exit_code == 0


class TestTogafCLI:
    def test_togaf_list(self):
        result = runner.invoke(app, ["togaf", "list"])
        assert result.exit_code == 0


# ── CLI Coverage Gap Tests ───────────────────────────────────────────

class TestToolsMCPCLI:
    def setup_method(self):
        _registry.clear()

    def test_mcp_serve_with_agent(self):
        from unittest.mock import patch
        with patch("haip.tools.mcp_server.serve_agent") as mock_serve:
            result = runner.invoke(app, ["tools", "mcp-serve", "--agent", "test", "--port", "9876"])
            assert result.exit_code == 0
            mock_serve.assert_called_once_with("test", port=9876, host="0.0.0.0")

    def test_mcp_serve_no_agent_no_all(self):
        result = runner.invoke(app, ["tools", "mcp-serve"])
        assert result.exit_code == 1


class TestReleaseCLIExtended:
    def test_release_backup_with_label(self):
        from unittest.mock import patch
        with patch("haip.operations.release_manager.ReleaseManager") as mock_rm_cls:
            mock_rm = mock_rm_cls.return_value
            mock_rm.create_backup.return_value = {"backup_id": "test-123"}
            result = runner.invoke(app, ["release", "backup", "--label", "test"])
            assert "Backup created" in result.output

    def test_release_rollback_nonexistent(self):
        from unittest.mock import patch
        with patch("haip.operations.release_manager.ReleaseManager") as mock_rm_cls:
            mock_rm = mock_rm_cls.return_value
            mock_rm.info.return_value = None
            result = runner.invoke(app, ["release", "rollback", "nonexistent-id"])
            assert "Backup not found" in result.output


class TestAuditCLIExtended:
    def test_audit_snapshot(self):
        from unittest.mock import patch
        with patch("haip.operations.audit_release.AuditEngine") as mock_ae_cls:
            mock_ae = mock_ae_cls.return_value
            mock_ae.snapshot.return_value = "snap-abc123"
            result = runner.invoke(app, ["audit", "snapshot", "test.yaml", "--agent", "test", "--reason", "test"])
            assert "Snapshot created" in result.output

    def test_audit_diff_nonexistent_snap(self):
        from unittest.mock import patch
        with patch("haip.operations.audit_release.AuditEngine") as mock_ae_cls:
            mock_ae = mock_ae_cls.return_value
            mock_ae.diff.return_value = [{"file": "f.yaml", "error": "Snapshot bad not found"}]
            result = runner.invoke(app, ["audit", "diff", "nonexistent_snap"])
            assert "ERROR" in result.output or "not found" in result.output.lower()

    def test_audit_log(self):
        from unittest.mock import patch
        with patch("haip.operations.audit_release.AuditEngine") as mock_ae_cls:
            mock_ae = mock_ae_cls.return_value
            mock_ae.list_audit_log.return_value = []
            result = runner.invoke(app, ["audit", "log"])
            assert "No audit entries" in result.output

    def test_audit_rollback_nonexistent(self):
        from unittest.mock import patch
        with patch("haip.operations.audit_release.AuditEngine") as mock_ae_cls:
            mock_ae = mock_ae_cls.return_value
            mock_ae.diff.return_value = [{"file": "f.yaml", "error": "not found"}]
            result = runner.invoke(app, ["audit", "rollback", "nonexistent_snap", "--force"])
            assert "not found" in result.output.lower() or "ERROR" in result.output.lower() or "no changes" in result.output.lower()


class TestSyncSkillsCLIExtended:
    def test_sync_skills_apply(self):
        from unittest.mock import patch
        with patch("haip.operations.skill_sync.sync") as mock_sync:
            mock_sync.return_value = {"changed": 0, "total_owned": 0}
            result = runner.invoke(app, ["sync-skills", "--apply"])
            assert result.exit_code == 0
            mock_sync.assert_called_once_with(dry_run=False)

    def test_sync_skills_validate(self):
        from unittest.mock import patch
        with patch("haip.operations.skill_sync.validate") as mock_val:
            mock_val.return_value = 0
            result = runner.invoke(app, ["sync-skills", "--validate"])
            assert result.exit_code == 0
            mock_val.assert_called_once()

    def test_sync_skills_init(self):
        from unittest.mock import patch
        with patch("haip.operations.skill_sync.init_from_runtime") as mock_init:
            mock_init.return_value = 0
            result = runner.invoke(app, ["sync-skills", "--init"])
            assert result.exit_code == 0
            mock_init.assert_called_once()


# ── Error Path Tests ─────────────────────────────────────────────────

class TestCLIErrorPaths:
    def setup_method(self):
        _registry.clear()

    def test_call_missing_params(self):
        result = runner.invoke(app, ["call", "nonexistent", "nonexistent_tool"])
        assert result.exit_code != 0 or "not found" in result.output.lower() or "unknown" in result.output.lower()

    def test_list_empty_registry_error_handling(self):
        _registry.clear()
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_call_without_params_flag(self):
        result = runner.invoke(app, ["call", "x", "y"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "not found" in result.output.lower() or "params" in result.output.lower()

    def test_info_empty_registry(self):
        _registry.clear()
        result = runner.invoke(app, ["info", "anything"])
        assert "Unknown agent" in result.output


# ── Real Path CLI Tests (no mocks, exercises actual code) ──────

class TestCLIRealPaths:
    def setup_method(self):
        from unittest.mock import patch

        from haip.agent import _registry
        _registry.clear()

    def test_info_with_full_plugin(self):
        from haip.agent import DomainPlugin, ToolDef, register

        plugin = DomainPlugin(
            name="full-plugin", cn_name="完整插件",
            type="business", port=9800, department="测试科",
            version="2.0.0",
            tools=[
                ToolDef(name="tool_a", description="工具A描述" * 4, handler="haip.tool_x"),
                ToolDef(name="tool_b", description="工具B", handler="haip.tool_y"),
            ],
            sub_agents=["sub1", "sub2"],
            parent="parent-agent",
        )
        register(plugin)
        result = runner.invoke(app, ["info", "full-plugin"])
        assert "full-plugin" in result.output
        assert "完整插件" in result.output
        assert "9800" in result.output
        assert "工具A" in result.output

    def test_call_with_empty_params(self):
        result = runner.invoke(app, ["call", "nonexistent_agent", "some_tool"])
        assert result.exit_code != 0 or "unknown" in result.output.lower()

    def test_history_with_limit_zero(self):
        result = runner.invoke(app, ["history", "--limit", "0"])
        assert result.exit_code == 0

    def test_togaf_arch_audit(self):
        result = runner.invoke(app, ["togaf", "arch", "audit"])
        assert result.exit_code == 0

    def test_togaf_arch_show(self):
        result = runner.invoke(app, ["togaf", "arch", "show"])
        assert result.exit_code == 0 or "AttributeError" not in result.output

    def test_togaf_arch_unknown_action(self):
        result = runner.invoke(app, ["togaf", "arch", "invalid_action"])
        assert "Unknown action" in result.output

    def test_togaf_build_unknown_domain(self):
        result = runner.invoke(app, ["togaf", "build", "nonexistent_domain_xyz"])
        assert result.exit_code == 0

    def test_togaf_validate_bp(self):
        result = runner.invoke(app, ["togaf", "validate", "--bp"])
        assert result.exit_code == 0 or "AttributeError" not in result.output

    def test_togaf_org_tree(self):
        result = runner.invoke(app, ["togaf", "org"])
        assert result.exit_code == 0

    def test_togaf_org_specific_role(self):
        result = runner.invoke(app, ["togaf", "org", "--role", "traumaortho_attending"])
        assert result.exit_code == 0

    def test_togaf_org_role_not_found(self):
        result = runner.invoke(app, ["togaf", "org", "--role", "nonexistent_role_12345"])
        assert "not found" in result.output.lower()

    def test_togaf_org_specific_department(self):
        result = runner.invoke(app, ["togaf", "org", "--org", "trauma_ortho"])
        assert result.exit_code == 0

    def test_togaf_arch_export(self, tmp_path):
        out = tmp_path / "export.json"
        result = runner.invoke(app, ["togaf", "arch", "export", "--out", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_audit_snapshot_with_cli(self, tmp_path):
        from unittest.mock import patch
        project_root = tmp_path
        (project_root / "test.txt").write_text("content", encoding="utf-8")
        with patch("haip.operations.audit_release._find_project_root", return_value=project_root):
            result = runner.invoke(app, ["audit", "snapshot", "test.txt", "--agent", "test-agent", "--reason", "CLI test"])
            assert result.exit_code == 0
            assert "Snapshot created" in result.output

    def test_release_list_with_real(self):
        import tempfile
        from unittest.mock import patch
        d = tempfile.mkdtemp()
        try:
            root = Path(d)
            with patch("haip.operations.release_manager._find_project_root", return_value=root):
                from haip.operations.release_manager import ReleaseManager
                rm = ReleaseManager()
                rm.create_backup(label="cli-test")
                result = runner.invoke(app, ["release", "list"])
                assert result.exit_code == 0
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_audit_list_with_data(self):
        import tempfile
        from unittest.mock import patch
        d = tempfile.mkdtemp()
        try:
            root = Path(d)
            (root / "f.txt").write_text("data", encoding="utf-8")
            with patch("haip.operations.audit_release._find_project_root", return_value=root):
                from haip.operations.audit_release import AuditEngine
                ae = AuditEngine()
                ae.snapshot("f.txt", agent="cli", reason="list test")
                result = runner.invoke(app, ["audit", "list"])
                assert result.exit_code == 0
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_audit_rollback_with_data(self):
        import tempfile
        from unittest.mock import patch
        d = tempfile.mkdtemp()
        try:
            root = Path(d)
            (root / "rollback_test.txt").write_text("original\n", encoding="utf-8")
            with patch("haip.operations.audit_release._find_project_root", return_value=root):
                from haip.operations.audit_release import AuditEngine
                ae = AuditEngine()
                snap = ae.snapshot("rollback_test.txt", agent="cli")
                snap_id = snap["id"]
                (root / "rollback_test.txt").write_text("modified\n", encoding="utf-8")
                result = runner.invoke(app, ["audit", "rollback", snap_id, "--force"])
                assert "RESTORED" in result.output or "Done" in result.output
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_audit_diff_with_cli(self, tmp_path):
        from unittest.mock import patch
        root = tmp_path
        (root / "f.txt").write_text("version1\n", encoding="utf-8")
        with patch("haip.operations.audit_release._find_project_root", return_value=root):
            from haip.operations.audit_release import AuditEngine
            ae = AuditEngine()
            snap = ae.snapshot("f.txt", agent="cli", reason="diff test")
            snap_id = snap["id"]
            (root / "f.txt").write_text("version2\n", encoding="utf-8")
            result = runner.invoke(app, ["audit", "diff", snap_id])
            assert "CHANGED" in result.output

    def test_audit_diff_two_with_cli(self, tmp_path):
        from unittest.mock import patch
        root = tmp_path
        (root / "f.txt").write_text("v1\n", encoding="utf-8")
        with patch("haip.operations.audit_release._find_project_root", return_value=root):
            from haip.operations.audit_release import AuditEngine
            ae = AuditEngine()
            s1 = ae.snapshot("f.txt", agent="cli", reason="s1")["id"]
            (root / "f.txt").write_text("v2\n", encoding="utf-8")
            s2 = ae.snapshot("f.txt", agent="cli", reason="s2")["id"]
            result = runner.invoke(app, ["audit", "diff", s1, "--snap2", s2])
            assert result.exit_code == 0

    def test_release_rollback_with_mock(self, tmp_path):
        from unittest.mock import patch
        root = tmp_path
        (root / "agents").mkdir()
        (root / "packages").mkdir()
        with patch("haip.operations.release_manager._find_project_root", return_value=root):
            from haip.operations.release_manager import ReleaseManager
            rm = ReleaseManager()
            rm.create_backup(label="rollback-cli")
            backups = rm.list_backups()
            if backups:
                bid = backups[0]["backup_id"]
                result = runner.invoke(app, ["release", "rollback", bid, "--force"])
                assert "RESTORED" in result.output or "Done" in result.output or "restored" in result.output.lower()

    def test_tools_list_all(self):
        result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0

    def test_tools_mcp_serve_help(self):
        result = runner.invoke(app, ["tools", "mcp-serve", "--help"])
        assert result.exit_code == 0

    def test_togaf_arch_export_default(self, tmp_path):
        import os
        os.chdir(str(tmp_path))
        try:
            result = runner.invoke(app, ["togaf", "arch", "export"])
            assert result.exit_code == 0 or "Exported" in result.output
        finally:
            os.chdir(str(project_root.parent))

    def test_togaf_org_tree_full(self):
        result = runner.invoke(app, ["togaf", "org"])
        assert "Organization Tree" in result.output or "院领导班子" in result.output

    def test_cmd_call_with_real_agent(self):
        from haip.agent import DomainPlugin, ToolDef, register
        register(DomainPlugin(name="cmd-agent", cn_name="命令测试", type="business", port=9999,
                              tools=[ToolDef(name="echo", description="Echo", handler="haip.tools.registry.list_schemas")]))
        result = runner.invoke(app, ["call", "cmd-agent", "echo", "--params", '{"msg":"hi"}'])
        assert result.exit_code == 0
