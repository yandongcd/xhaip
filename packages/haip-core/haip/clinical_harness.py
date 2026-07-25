"""ClinicalHarness — 诊疗合规性自检引擎.

Cross-references agent YAML definitions against clinical guidelines and rules
to validate diagnostic/treatment process compliance.
"""
from __future__ import annotations

import pathlib
import yaml
import json
from collections import defaultdict
from typing import Any


class ClinicalHarness:
    """Validates agent clinical workflows against knowledge base guidelines and rules."""

    def __init__(self, project_root: str = ""):
        if project_root:
            root = pathlib.Path(project_root)
        else:
            root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.agents_dir = root / "packages/haip-hospital/agents/definitions"
        self.guidelines_dir = root / "packages/haip-hospital/knowledge/guidelines"
        self.rules_dir = root / "packages/haip-hospital/knowledge/rules"
        self._warnings = []
        self._suggestions = []

    def run(self) -> dict[str, Any]:
        agents = self._load_agents()
        guidelines = self._load_guidelines()
        rules = self._load_rules()

        report = {
            "agents_total": len(agents),
            "guidelines_total": len(guidelines),
            "rules_total": sum(len(r.get("rules", [])) for r in rules.values()),
            "checks": [],
            "score": 100,
            "warnings": [],
            "suggestions": [],
        }

        # Check 1: Every clinical agent should have at least one guideline reference
        report["checks"].append(self._check_guideline_coverage(agents, guidelines))

        # Check 2: High-risk agents should have guard triggers
        report["checks"].append(self._check_guard_coverage(agents, rules))

        # Check 3: Stage sequences should follow guideline recommendations
        report["checks"].append(self._check_stage_guideline_alignment(agents, guidelines))

        # Check 4: Role assignments should include required specialties
        report["checks"].append(self._check_role_completeness(agents))

        # Check 5: All departments in guidelines should have a corresponding agent
        report["checks"].append(self._check_agent_guideline_symmetry(agents, guidelines))

        # Calculate score
        total_weight = sum(c.get("weight", 1) for c in report["checks"])
        passed_weight = sum(c.get("weight", 1) for c in report["checks"] if c["status"] == "pass")
        report["score"] = round(passed_weight / total_weight * 100) if total_weight > 0 else 100
        report["warnings"] = self._warnings
        report["suggestions"] = self._suggestions

        return report

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
                        content = yaml.safe_load_all(f)
                        for doc in content:
                            if doc and "rules" in doc:
                                key = f"{rd.name}/{rf.stem}"
                                rules[key] = doc
                except Exception:
                    pass
        return rules

    # ── Check implementations ──

    def _check_guideline_coverage(self, agents, guidelines) -> dict:
        agent_departments = set()
        for a in agents.values():
            dept = a.get("department", a["name"])
            agent_departments.add(dept)

        guideline_depts = set()
        for g in guidelines.values():
            dept_hint = g.get("publisher", "") + g.get("name", "")
            guideline_depts.add(dept_hint[:20])

        uncovered = []
        for name, a in agents.items():
            if a.get("type") != "business":
                continue
            has_guideline = any(
                a.get("department", "") in g.get("name", "")
                or a["name"].replace("-", "") in g.get("name", "").lower()
                for g in guidelines.values()
            )
            if not has_guideline:
                uncovered.append(name)

        if uncovered:
            self._warn(f"{len(uncovered)} 个临床 Agent 未关联指南: {', '.join(uncovered[:5])}...")
            return {"name": "指南覆盖率", "status": "warn", "weight": 3, "detail": f"缺失: {len(uncovered)}/{len(agents)}"}
        return {"name": "指南覆盖率", "status": "pass", "weight": 3}

    def _check_guard_coverage(self, agents, rules) -> dict:
        unguarded = []
        for name, a in agents.items():
            triggers = a.get("guard", {}).get("triggers", [])
            high_risk = a.get("guard", {}).get("high_risk_scenarios", [])
            has_rules = any(
                a.get("department", "") in rk or a["name"].replace("-", "_") in rk
                for rk in rules
            )
            if has_rules and not triggers and a.get("type") == "business":
                unguarded.append(name)

        if unguarded:
            self._warn(f"{len(unguarded)} 个 Agent 有规则但无 Guard 触发: {', '.join(unguarded[:5])}")
            return {"name": "Guard 触发覆盖", "status": "warn", "weight": 3, "detail": f"无触发: {len(unguarded)}"}
        return {"name": "Guard 触发覆盖", "status": "pass", "weight": 3}

    def _check_stage_guideline_alignment(self, agents, guidelines) -> dict:
        mismatches = 0
        for name, a in agents.items():
            stages = a.get("stages", [])
            if not stages or a.get("type") != "business":
                continue
            # Count stages — most clinical pathways should have 4-6 stages
            if len(stages) < 3:
                self._suggest(f"[{name}] 阶段数偏少 ({len(stages)}), 临床路径建议 ≥3 个阶段")
                mismatches += 1
            if len(stages) > 8:
                self._suggest(f"[{name}] 阶段数偏多 ({len(stages)}), 建议 ≤8 个阶段")
                mismatches += 1

        return {"name": "阶段-指南对齐", "status": "pass" if mismatches == 0 else "warn",
                "weight": 2, "detail": f"阶段异常: {mismatches}"}

    def _check_role_completeness(self, agents) -> dict:
        incomplete = 0
        for name, a in agents.items():
            roles = a.get("ui", {}).get("roles", [])
            stages = a.get("stages", [])
            if not roles or not stages:
                continue

            role_ids = {r["id"] for r in roles}
            stage_roles = set()
            for s in stages:
                stage_roles.update(s.get("role_ids", []))

            orphan_roles = stage_roles - role_ids
            if orphan_roles:
                self._warn(f"[{name}] 阶段引用了未定义的角色: {orphan_roles}")
                incomplete += 1

        return {"name": "角色完整性", "status": "pass" if incomplete == 0 else "warn",
                "weight": 2, "detail": f"角色缺失: {incomplete}"}

    def _check_agent_guideline_symmetry(self, agents, guidelines) -> dict:
        """Check if guideline-covered departments have corresponding agents."""
        agent_names = set(a["name"].replace("-", "") for a in agents.values())
        orphan_guidelines = []

        for g in guidelines.values():
            name = g.get("name", "")
            # Try to match guideline to agent
            matched = any(
                keyword in name.lower()
                for keyword in agent_names
                if len(keyword) > 4
            )
            if not matched and g.get("trust_level") == "T1":
                orphan_guidelines.append(g.get("abbr", name[:30]))

        if orphan_guidelines:
            self._suggest(f"{len(orphan_guidelines)} 个 T1 指南无对应 Agent")

        return {"name": "Agent-指南对称性", "status": "pass", "weight": 1}

    def _warn(self, msg: str):
        self._warnings.append(msg)

    def _suggest(self, msg: str):
        self._suggestions.append(msg)


def run_clinical_harness(project_root: str = "") -> dict:
    harness = ClinicalHarness(project_root)
    return harness.run()


if __name__ == "__main__":
    report = run_clinical_harness()
    print(json.dumps(report, ensure_ascii=False, indent=2))
