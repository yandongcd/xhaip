"""D4 文档漂移门禁 — AGENTS.md 数字与源码实数一致性."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = ROOT / "AGENTS.md"


def _agents_content() -> str:
    return AGENTS_MD.read_text(encoding="utf-8")


def _extract_number(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    if not m:
        raise AssertionError(f"AGENTS.md 中未找到模式: {pattern}")
    return int(m.group(1))


class TestDocDrift:
    """AGENTS.md 文档中的数字必须与源码实体数量一致."""

    def test_yaml_agent_definitions_count(self):
        """AGENTS.md '(\\d+) 个 YAML Agent 定义' 与 definitions 目录实数比对."""
        content = _agents_content()
        doc_count = _extract_number(content, r"(\d+)\s*个\s*YAML\s*Agent\s*定义")
        actual = len(list((ROOT / "packages" / "haip-hospital" / "agents" / "definitions").glob("*.yaml")))
        assert doc_count == actual, f"AGENTS.md: {doc_count}, 实际: {actual}"

    def test_knowledge_counts(self):
        """AGENTS.md BP/指南 数字与 knowledge 目录实数比对."""
        content = _agents_content()
        bp_dir = ROOT / "packages" / "haip-hospital" / "knowledge" / "business_processes"
        guidelines_dir = ROOT / "packages" / "haip-hospital" / "knowledge" / "guidelines"
        rules_dir = ROOT / "packages" / "haip-hospital" / "knowledge" / "rules"

        actual_bp = len(list(bp_dir.glob("*.yaml")))
        actual_gd = len(list(guidelines_dir.glob("*.yaml")))
        actual_rg = len(list(rules_dir.glob("*.yaml")))

        m = re.search(
            r"(\d+)\s*BP\s*YAML\s*\+\s*(\d+)\s*指南\s*\+\s*(\d+)\s*规则组\s*\((\d+)\s*条\)",
            content,
        )
        if not m:
            raise AssertionError("AGENTS.md 中未找到 BP/指南/规则组 模式")
        doc_bp, doc_gd, doc_rg, doc_rule_count = map(int, m.groups())

        assert doc_bp == actual_bp, f"BP: AGENTS.md={doc_bp}, 实际={actual_bp}"
        assert doc_gd == actual_gd, f"指南: AGENTS.md={doc_gd}, 实际={actual_gd}"
        assert doc_rg == actual_rg, f"规则组: AGENTS.md={doc_rg}, 实际={actual_rg}"

        # 验证规则总数
        total_rules = 0
        import yaml as _yaml
        for f in sorted(rules_dir.glob("*.yaml")):
            with open(f, "r", encoding="utf-8") as fh:
                data = _yaml.safe_load(fh)
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        total_rules += len(v)
                    elif isinstance(v, dict) and "rules" in v and isinstance(v["rules"], list):
                        total_rules += len(v["rules"])
        assert doc_rule_count == total_rules, f"规则条数: AGENTS.md={doc_rule_count}, 实际={total_rules}"

    def test_patients_count(self):
        """AGENTS.md 病人数与 patients.json 实数比对."""
        content = _agents_content()
        doc_count = _extract_number(content, r"(\d+)\s*位数字病人")
        pts_file = ROOT / "packages" / "haip-hospital" / "data" / "patients.json"
        data = json.loads(pts_file.read_text(encoding="utf-8"))
        all_pts = data.get("patients", []) if isinstance(data, dict) else data
        actual = len(all_pts) if isinstance(all_pts, list) else 0
        assert doc_count == actual, f"AGENTS.md: {doc_count}, 实际: {actual}"
