"""CLI 测试."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from typer.testing import CliRunner

from haip.cli import app
from haip.agent import _registry

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
        from haip.agent import register, DomainPlugin
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
