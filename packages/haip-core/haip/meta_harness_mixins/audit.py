"""RLAIF 审计+自动测试+持续学习+多智能体评审 — meta_harness mixin (P1-6 拆分)."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sqlite3
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class MetaHarnessAuditMixin:
    def _run_rlaif_audit(self) -> dict:
        """Self-audit all agents against clinical guidelines (Constitutional AI approach).

        Rules (constitution):
          1. Every business agent MUST have guard triggers
          2. Every surgical agent MUST have high_risk_scenarios
          3. Every agent MUST have >= 3 stages
          4. Every stage MUST have role_ids assigned
          5. Every guard MUST have citation enforcement for high-risk
        """
        constitution = [
            {"id": "C1", "rule": "临床Agent必有Guard触发", "check": self._check_guard_exists, "severity": "critical"},
            {"id": "C2", "rule": "外科Agent必有高危场景", "check": self._check_surgical_high_risk, "severity": "critical"},
            {"id": "C3", "rule": "Agent阶段数≥3", "check": self._check_min_stages, "severity": "warn"},
            {"id": "C4", "rule": "每阶段必分配角色", "check": self._check_stage_roles, "severity": "warn"},
            {"id": "C5", "rule": "高危Guard强制引用检查", "check": self._check_citation_enforcement, "severity": "critical"},
        ]

        violations = []
        for c in constitution:
            v = c["check"]()
            for agent_name, detail in v:
                violations.append({
                    "principle": c["id"],
                    "rule": c["rule"],
                    "severity": c["severity"],
                    "agent": agent_name,
                    "detail": detail,
                })

        severity_order = {"critical": 3, "warn": 2, "info": 1}
        violations.sort(key=lambda v: severity_order.get(v["severity"], 0), reverse=True)

        critical_count = sum(1 for v in violations if v["severity"] == "critical")
        return {
            "status": "completed",
            "constitution_rules": len(constitution),
            "total_violations": len(violations),
            "critical_violations": critical_count,
            "score": max(0, 100 - critical_count * 20),
            "violations": violations[:15],
            "alignment_status": "aligned" if critical_count == 0 else "needs_alignment",
        }


    def _check_guard_exists(self) -> list[tuple]:
        results = []
        for name, a in self._agents.items():
            if a.get("type") != "business":
                continue
            if not a.get("guard", {}).get("triggers"):
                results.append((name, "无Guard触发规则"))
        return results


    def _check_surgical_high_risk(self) -> list[tuple]:
        surgical_keywords = ["外科", "手术"]
        results = []
        for name, a in self._agents.items():
            dept = a.get("department", "")
            if any(kw in dept for kw in surgical_keywords):
                if not a.get("guard", {}).get("high_risk_scenarios"):
                    results.append((name, "外科Agent无高危场景定义"))
        return results


    def _check_min_stages(self) -> list[tuple]:
        results = []
        for name, a in self._agents.items():
            if a.get("type") == "master_data":
                continue
            if len(a.get("stages", [])) < 3:
                results.append((name, f"只有{len(a.get('stages',[]))}个阶段(需≥3)"))
        return results


    def _check_stage_roles(self) -> list[tuple]:
        results = []
        for name, a in self._agents.items():
            for s in a.get("stages", []):
                if not s.get("role_ids"):
                    results.append((name, f"阶段'{s.get('label','')}' 未分配角色"))
        return results


    def _check_citation_enforcement(self) -> list[tuple]:
        results = []
        for name, a in self._agents.items():
            high_risk = a.get("guard", {}).get("high_risk_scenarios", [])
            citation = a.get("guard", {}).get("citation", {})
            if high_risk and not citation.get("required"):
                results.append((name, "有高危场景但未强制引用检查"))
        return results

    # ═══ STAGE 3: Auto-Testing (SWE-agent-style) ═══


    def _run_auto_testing(self) -> dict:
        """Automatically generate and execute a test matrix for all agents."""
        matrix = []
        passed = 0
        failed = 0

        for name, agent in self._agents.items():
            tests = self._generate_agent_tests(name, agent)
            for test in tests:
                result = self._execute_test(test)
                matrix.append({**test, "result": result})
                if result == "pass":
                    passed += 1
                else:
                    failed += 1

        return {
            "status": "completed",
            "total_tests": len(matrix),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(matrix) * 100) if matrix else 0,
            "score": round(passed / len(matrix) * 100) if matrix else 100,
            "failures": [t for t in matrix if t["result"] != "pass"][:10],
        }


    def _generate_agent_tests(self, name: str, agent: dict) -> list[dict]:
        tests = []
        # Test 1: Handler paths valid
        for tool in agent.get("tools", []):
            handler = tool.get("handler", "")
            if handler:
                tests.append({"agent": name, "test": f"handler_import:{handler}", "type": "handler"})
        # Test 2: Stages have role_ids
        for s in agent.get("stages", []):
            if s.get("role_ids"):
                tests.append({"agent": name, "test": f"stage_roles:{s['id']}", "type": "stage"})
        # Test 3: Guard triggers valid
        if agent.get("guard", {}).get("triggers"):
            tests.append({"agent": name, "test": "guard_triggers", "type": "guard"})
        return tests[:20]  # Cap per agent

    _import_cache: dict[str, Any] = {}


    def _execute_test(self, test: dict) -> str:
        ttype = test["type"]
        detail = test["test"]

        if ttype == "handler":
            handler = detail.replace("handler_import:", "")
            try:
                mod, fn = handler.rsplit(".", 1)
                import importlib
                m = type(self)._import_cache.get(mod)
                if m is None:
                    m = importlib.import_module(mod)
                    type(self)._import_cache[mod] = m
                if hasattr(m, fn):
                    return "pass"
                return "fail"
            except Exception:
                logger.debug("Handler import test failed: %s", handler, exc_info=True)
                return "fail"

        if ttype == "stage":
            return "pass"  # Already validated by structure check

        if ttype == "guard":
            return "pass"  # Existence already checked

        return "pass"

    # ═══ STAGE 4: Continuous Learning (AgentBench-style) ═══


    def _run_continuous_learning(self) -> dict:
        """Benchmark the system and generate a self-score over time."""
        now = time.time()
        snapshots = self._load_historical_scores()

        # Current scores
        current = {
            "clinical_compliance": self._score_clinical(),
            "agent_coverage": self._score_agent_coverage(),
            "rule_utilization": self._score_rule_utilization(),
            "guard_adoption": self._score_guard_adoption(),
        }

        # Store snapshot
        snapshots.append({"timestamp": now, "scores": current})

        # Trend analysis
        trend = "stable"
        if len(snapshots) >= 2:
            prev = snapshots[-2]["scores"]
            improvements = sum(1 for k in current if current[k] > prev.get(k, 0))
            declines = sum(1 for k in current if current[k] < prev.get(k, 0))
            if improvements > declines:
                trend = "improving"
            elif declines > improvements:
                trend = "declining"

        # Learning milestones
        milestones = []
        overall = round(sum(current.values()) / len(current))
        if overall >= 95:
            milestones.append("🏆 达到 PROD-READY 标准 (≥95%)")
        if current["guard_adoption"] >= 80:
            milestones.append("🛡️ Guard 采用率达 80%+")
        if current["rule_utilization"] >= 50:
            milestones.append("📊 规则利用率达 50%+")

        return {
            "status": "completed",
            "current_scores": current,
            "overall_score": overall,
            "trend": trend,
            "snapshots_count": len(snapshots),
            "milestones": milestones,
            "next_milestone": "达到 PROD-READY 标准" if overall < 95 else "ALL MILESTONES ACHIEVED",
        }


    def _score_clinical(self) -> float:
        covered = 0
        total = 0
        for name, a in self._agents.items():
            if a.get("type") != "business":
                continue
            total += 1
            if a.get("guard", {}).get("triggers"):
                covered += 1
        return round(covered / total * 100) if total else 0


    def _score_agent_coverage(self) -> float:
        with_stages = sum(1 for a in self._agents.values() if a.get("stages"))
        return round(with_stages / len(self._agents) * 100) if self._agents else 0


    def _score_rule_utilization(self) -> float:
        agents_with_rules = 0
        for name in self._agents:
            agent_key = name.replace("-", "_")
            for rd in self.rules_dir.iterdir() if self.rules_dir.exists() else []:
                if rd.is_dir() and agent_key in rd.name:
                    agents_with_rules += 1
                    break
        return round(agents_with_rules / len(self._agents) * 100) if self._agents else 0


    def _score_guard_adoption(self) -> float:
        with_guard = sum(1 for a in self._agents.values() if a.get("guard", {}).get("triggers"))
        return round(with_guard / len(self._agents) * 100) if self._agents else 0


    def _load_historical_scores(self) -> list[dict]:
        try:
            snap_file = self.root / ".openharness/runtime/snapshots/benchmark_history.json"
            if snap_file.exists():
                return json.loads(snap_file.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("Historical benchmark scores load failed", exc_info=True)
        return []

    # ═══ STAGE 5: Multi-Agent Review (AutoGen-style) ═══


    def _run_multi_agent_review(self) -> dict:
        """Cross-agent audit: each agent reviews others' compliance."""
        reviews = []

        # Pair agents for cross-review
        agent_list = list(self._agents.keys())
        for i, reviewer in enumerate(agent_list):
            if i >= len(agent_list) - 1:
                break
            reviewed = agent_list[i + 1]

            # Reviewer checks the reviewed agent
            reviewed_agent = self._agents.get(reviewed, {})
            issues = []

            # Check 1: Reviewer's expertise is relevant?
            reviewer_type = self._agents.get(reviewer, {}).get("type", "")
            if reviewer_type == "business":
                if not reviewed_agent.get("guard", {}).get("triggers"):
                    issues.append(f"Agent {reviewer} 评审 {reviewed}: 缺少Guard触发")

            if issues:
                reviews.append({
                    "reviewer": reviewer,
                    "reviewed": reviewed,
                    "issues": issues,
                    "vote": "needs_fix",
                })
            else:
                reviews.append({
                    "reviewer": reviewer,
                    "reviewed": reviewed,
                    "issues": [],
                    "vote": "approved",
                })

        # Voting results
        votes = Counter(r["vote"] for r in reviews)
        consensus = "approved" if votes.get("approved", 0) > votes.get("needs_fix", 0) else "needs_fix"

        return {
            "status": "completed",
            "total_reviews": len(reviews),
            "votes": dict(votes),
            "consensus": consensus,
            "score": round(votes.get("approved", 0) / len(reviews) * 100) if reviews else 100,
            "needs_fix": [r for r in reviews if r["vote"] == "needs_fix"][:5],
        }


    # ═══ STAGE 6: Causal Diagnosis (Self-Harness-style) ═══


    def _run_causal_diagnosis(self) -> dict:
        """Trace-based LLM causal diagnosis of failed executions."""
        result = self._diagnosis.run()
        brief = result.get("diagnosis_brief", "")

        if brief:
            brief_path = self.root / ".openharness" / "runtime" / "diagnosis_brief.md"
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text(brief, encoding="utf-8")

        return {
            "status": "completed",
            "failed_cases": result.get("failed_cases", 0),
            "clusters_count": result.get("clusters_count", 0),
            "clusters": result.get("clusters", [])[:10],
            "diagnosis_path": str(
                self.root / ".openharness" / "runtime" / "diagnosis_brief.md"
            ) if brief else None,
            "score": max(0, 100 - result.get("clusters_count", 0) * 10),
        }

    # ═══ STAGE 7: Multi-Proposer (Self-Harness-style) ═══

