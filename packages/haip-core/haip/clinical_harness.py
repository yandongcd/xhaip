"""ClinicalHarness v2 — 三维度 Agent 自检 (功能完备/界面美观/诊疗规范)."""
from __future__ import annotations

import json
import pathlib
import yaml
from collections import defaultdict
from typing import Any


class ClinicalHarness:
    """Three-dimensional agent quality audit."""

    def __init__(self, project_root: str = ""):
        if project_root:
            root = pathlib.Path(project_root)
        else:
            root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.agents_dir = root / "packages/haip-hospital/agents/definitions"
        self.guidelines_dir = root / "packages/haip-hospital/knowledge/guidelines"
        self.rules_dir = root / "packages/haip-hospital/knowledge/rules"

    def run(self) -> dict[str, Any]:
        agents = self._load_agents()
        guidelines = self._load_guidelines()
        rules = self._load_rules()
        issues = []

        for name, a in agents.items():
            issues.extend(self._audit_agent(name, a, guidelines, rules))

        # Categorize
        by_dim = {"feature": [], "ui": [], "clinical": []}
        by_level = {"critical": [], "warn": [], "info": []}
        by_agent = defaultdict(list)

        for iss in issues:
            by_dim[iss["dimension"]].append(iss)
            by_level[iss["level"]].append(iss)
            by_agent[iss["agent"]].append(iss)

        total_checks = len(issues)
        passed = sum(1 for i in issues if i["level"] == "info")
        score = round((1 - sum(1 for i in issues if i["level"] == "critical") / total_checks) * 100) if total_checks else 100

        return {
            "agents_total": len(agents),
            "issues_total": total_checks,
            "critical": len(by_level["critical"]),
            "warnings": len(by_level["warn"]),
            "info": len(by_level["info"]),
            "score": max(0, score),
            "by_dimension": {k: len(v) for k, v in by_dim.items()},
            "by_agent": {k: [i["message"] for i in v] for k, v in sorted(by_agent.items()) if any(i["level"] != "info" for i in v)},
            "top_issues": [i["message"] for i in issues if i["level"] in ("critical", "warn")][:20],
        }

    def _audit_agent(self, name: str, a: dict, guidelines: dict, rules: dict) -> list[dict]:
        issues = []
        agent_type = a.get("type", "business")

        # ═══ DIMENSION 1: Feature Completeness ═══
        tools = a.get("tools", [])
        if not tools:
            issues.append(self._issue(name, "feature", "critical", f"[{name}] 无工具定义"))
        elif agent_type == "business" and len(tools) < 3:
            issues.append(self._issue(name, "feature", "warn", f"[{name}] 工具数偏少 ({len(tools)}), 建议≥3"))

        stages = a.get("stages", [])
        if not stages and agent_type != "master_data":
            issues.append(self._issue(name, "feature", "warn", f"[{name}] 无阶段定义 (将使用默认)"))

        if stages:
            for s in stages:
                desc = s.get("desc", "")
                if not desc or desc.endswith("流程") or len(desc) < 10:
                    issues.append(self._issue(name, "feature", "info", f"[{name}] 阶段'{s.get('label','')}'描述过短"))

                role_ids = s.get("role_ids", [])
                if not role_ids:
                    issues.append(self._issue(name, "feature", "warn", f"[{name}] 阶段'{s.get('label','')}'未分配角色"))

        # Handler paths
        for t in tools:
            handler = t.get("handler", "")
            if not handler or "." not in handler:
                issues.append(self._issue(name, "feature", "critical", f"[{name}] 工具'{t.get('name','')}' handler 无效"))

        # Guard triggers
        if agent_type == "business":
            triggers = a.get("guard", {}).get("triggers", [])
            high_risk = a.get("guard", {}).get("high_risk_scenarios", [])

            # Check if department has clinical rules
            dept_name = a.get("department", "")
            has_rules = any(
                dept_name in rk or name.replace("-", "_") in rk
                for rk in rules
            )

            if has_rules and not triggers:
                issues.append(self._issue(name, "feature", "warn", f"[{name}] 有临床规则但无 Guard 触发"))
            if high_risk and not triggers:
                issues.append(self._issue(name, "feature", "critical", f"[{name}] 有高危场景但无 Guard 触发"))

        # ═══ DIMENSION 2: UI Quality ═══
        ui = a.get("ui", {})
        roles = ui.get("roles", [])
        if not roles and agent_type == "business":
            issues.append(self._issue(name, "ui", "warn", f"[{name}] 无 UI 角色定义"))

        if roles:
            for r in roles:
                if not r.get("label"):
                    issues.append(self._issue(name, "ui", "info", f"[{name}] 角色'{r.get('id','')}'缺少标签"))
                if not r.get("id"):
                    issues.append(self._issue(name, "ui", "critical", f"[{name}] 角色缺少 id"))

            # Check default role
            has_default = any(r.get("default") for r in roles)
            if not has_default:
                issues.append(self._issue(name, "ui", "info", f"[{name}] 无默认角色"))

        # Stage role reference consistency
        stage_roles = set()
        for s in stages:
            stage_roles.update(s.get("role_ids", []))
        ui_roles = {r.get("id") for r in roles}
        orphan = stage_roles - ui_roles
        if orphan:
            issues.append(self._issue(name, "ui", "critical", f"[{name}] 阶段引用未定义角色: {orphan}"))

        # Template
        if not ui.get("template"):
            issues.append(self._issue(name, "ui", "info", f"[{name}] 未设置 UI 模板"))

        # ═══ DIMENSION 3: Clinical Compliance ═══
        if agent_type != "business":
            return issues

        # Prompts
        prompt = a.get("prompt", {}).get("system", "")
        if not prompt or len(prompt) < 20:
            issues.append(self._issue(name, "clinical", "warn", f"[{name}] prompt 过短 (<20 字符)"))

        # Guideline references
        has_guideline = any(
            a.get("department", "") in g.get("name", "")
            for g in guidelines.values()
        )
        if not has_guideline:
            issues.append(self._issue(name, "clinical", "info", f"[{name}] 知识库中无对应指南"))

        # Guard citation enforcement
        citation = a.get("guard", {}).get("citation", {})
        high_risk_scenarios = a.get("guard", {}).get("high_risk_scenarios", [])
        if high_risk_scenarios and not citation.get("required"):
            issues.append(self._issue(name, "clinical", "warn", f"[{name}] 高危场景未强制引用检查"))

        # Stage count vs guideline recommendation
        if len(stages) < 3:
            issues.append(self._issue(name, "clinical", "info", f"[{name}] 阶段数 {len(stages)} 偏少 (建议≥3)"))

        return issues

    def _issue(self, agent: str, dimension: str, level: str, message: str) -> dict:
        return {"agent": agent, "dimension": dimension, "level": level, "message": message}

    # ── Loaders ──
    def _load_agents(self) -> dict[str, dict]:
        agents = {}
        for yf in sorted(self.agents_dir.glob("*.yaml")):
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            agents[data["name"]] = data
        return agents

    def _load_guidelines(self) -> dict[str, dict]:
        guidelines = {}
        for yf in sorted(self.guidelines_dir.glob("*.yaml")):
            if yf.name.startswith("_"):
                continue
            try:
                with open(yf, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "id" in data:
                    guidelines[data["id"]] = data
            except Exception:
                pass
        return guidelines

    def _load_rules(self) -> dict[str, dict]:
        rules = {}
        for rd in sorted(self.rules_dir.iterdir()):
            if not rd.is_dir() or rd.name.startswith("_"):
                continue
            for rf in sorted(rd.glob("*.yaml")):
                try:
                    with open(rf, encoding="utf-8") as f:
                        for doc in yaml.safe_load_all(f):
                            if doc and "rules" in doc:
                                rules[f"{rd.name}/{rf.stem}"] = doc
                except Exception:
                    pass
        return rules


if __name__ == "__main__":
    harness = ClinicalHarness()
    report = harness.run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
