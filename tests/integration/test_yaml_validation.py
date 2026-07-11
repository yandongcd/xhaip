"""YAML 资产校验 — 参照疼痛科 test_pain_yaml_validation.py 模式."""

from pathlib import Path

import yaml

project_root = Path(__file__).resolve().parent.parent.parent

YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


class TestPharmacyYamlValidation:
    def test_yaml_parses(self):
        files = sorted(YAML_DIR.glob("*.yaml"))
        valid_count = 0
        for f in files:
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            assert isinstance(data, dict), f"{f.name} should be a dict"
            valid_count += 1
        assert valid_count >= 1

    def test_name_field_required(self):
        for f in sorted(YAML_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            assert "name" in data, f"{f.name} missing 'name'"
            assert isinstance(data["name"], str) and len(data["name"]) > 0

    def test_type_field_valid(self):
        valid_types = {"business", "specialist", "master_data", "rules", "architecture"}
        for f in sorted(YAML_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if "type" in data:
                assert data["type"] in valid_types, f"{f.name} invalid type: {data['type']}"

    def test_tools_have_handler(self):
        for f in sorted(YAML_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            for tool in data.get("tools", []):
                assert "name" in tool, f"{f.name} tool missing name"
                assert "handler" in tool, f"{f.name}/{tool.get('name')} missing handler"
                # handler 格式应为 pkg.fn (modules目录已在sys.path中)
                assert tool["handler"].count(".") >= 1, \
                    f"{f.name}/{tool['name']} handler should be pkg.fn: {tool['handler']}"

    def test_depends_on_format(self):
        for f in sorted(YAML_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            for dep in data.get("depends_on", []):
                assert "agent" in dep, f"{f.name} dependency missing 'agent'"

    def test_guard_triggers_valid(self):
        for f in sorted(YAML_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            for t in data.get("guard", {}).get("triggers", []):
                assert isinstance(t, str) and len(t) > 0, f"{f.name} invalid guard trigger: {t}"
