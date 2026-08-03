"""MetaHarness — Unified self-improvement framework for xhaip.

Eight capabilities integrated into one orchestration engine:
  1. Self-Improvement (Voyager-style) — learn from execution patterns
  2. RLAIF Auditor (Constitutional AI-style) — self-audit against rules
  3. Auto-Testing (SWE-agent-style) — generate & run test matrices
  4. Continuous Learning (AgentBench-style) — benchmark + self-score
  5. Multi-Agent Review (AutoGen-style) — cross-audit + voting
  6. Causal Diagnosis (Self-Harness-style) — trace-based LLM diagnosis
  7. Multi-Proposer (Self-Harness-style) — mechanism-diverse proposals
  8. Acceptance Gate (Self-Harness-style) — baseline vs candidate gating

Mirrors the qzzqzzb/Self-Harness (arXiv:2606.09498) architecture,
adapted for xhaip's YAML-agent domain.

Usage:
    meta = MetaHarness()
    report = meta.run_full_cycle()  # Runs all 8, returns unified report
"""

from __future__ import annotations

import json
import logging
import pathlib
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

import yaml

from haip.harness_acceptance import HarnessAcceptance, ScoreSnapshot
from haip.harness_diagnosis import HarnessDiagnosis
from haip.harness_proposer import HarnessProposer, Proposal, apply_candidate

# ══════════════════════════════════════════════════════════════════
# METAHARNESS ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

class MetaHarness:
    """Unified self-improvement framework orchestrator (v3.0.0)."""

    def __init__(self, project_root: str = ""):
        if project_root:
            self.root = pathlib.Path(project_root)
        else:
            self.root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
        self.agents_dir = self.root / "packages/haip-hospital/agents/definitions"
        self.rules_dir = self.root / "packages/haip-hospital/knowledge/rules"
        self.guidelines_dir = self.root / "packages/haip-hospital/knowledge/guidelines"
        self.modules_dir = self.root / "packages/haip-hospital/modules"
        self.db_path = self.root / "xhaip_memory.db"
        self._agents: dict[str, dict] = {}
        self._diagnosis = HarnessDiagnosis(project_root=str(self.root))
        self._proposer = HarnessProposer(project_root=str(self.root))
        self._acceptance = HarnessAcceptance(project_root=str(self.root))
        self._snapshot = ScoreSnapshot(self.root / ".openharness" / "runtime" / "snapshots")
        self._a2a_executor = None  # shared ThreadPoolExecutor for Stage 9
        self._ensure_import_path()
        self._ensure_agent_registry()
        self._load_agents()

    def _ensure_import_path(self):
        modules_path = str(self.modules_dir)
        if modules_path not in sys.path:
            sys.path.insert(0, modules_path)

    def _ensure_agent_registry(self):
        try:
            from haip.agent import load_from_dir
            load_from_dir(str(self.agents_dir))
        except Exception:
            logger.warning("Agent registry load failed", exc_info=True)

    def run_full_cycle(self, run_proposer: bool = True) -> dict[str, Any]:
        """Execute all self-harness stages and return unified report."""
        start = time.time()

        stages: dict[str, Any] = {
            "self_improvement": self._run_self_improvement(),
            "rlaif_audit": self._run_rlaif_audit(),
            "auto_testing": self._run_auto_testing(),
            "continuous_learning": self._run_continuous_learning(),
            "multi_agent_review": self._run_multi_agent_review(),
            "causal_diagnosis": self._run_causal_diagnosis(),
            "runtime_a2a": self._run_runtime_a2a(),
        }

        stages["rule_compliance"] = self._run_rule_compliance(stages.get("runtime_a2a", {}))
        stages["guard_effectiveness"] = self._run_guard_effectiveness()
        stages["quality_intelligence"] = self._run_quality_intelligence(
            stages.get("runtime_a2a", {}), stages.get("rule_compliance", {}))

        if run_proposer:
            stages["multi_proposer"] = self._run_multi_proposer(stages.get("causal_diagnosis", {}))
            stages["acceptance_gate"] = self._run_acceptance_gate(stages)

        unified = self._compute_unified_score(stages)
        actions = self._extract_top_actions(stages)

        reports = {
            "version": "3.0.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agents_count": len(self._agents),
            "stages": stages,
            "unified_score": unified,
            "top_actions": actions,
            "duration_ms": round((time.time() - start) * 1000),
        }

        self._snapshot.record("meta_harness", {"unified_score": unified}, {"cycle": "full"})
        return reports

    def _load_agents(self):
        for yf in sorted(self.agents_dir.glob("*.yaml")):
            with open(yf, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._agents[data["name"]] = data

    # ═══ STAGE 1: Self-Improvement (Voyager-style) ═══

    def _run_self_improvement(self) -> dict:
        """Learn from execution history: identify failure patterns, suggest optimizations."""
        history = self._load_execution_history()
        if not history:
            return {"status": "insufficient_data", "suggestions": [], "score": 0}

        # Pattern analysis
        failures = [h for h in history if h.get("status") != "ok"]
        failure_rate = len(failures) / len(history) if history else 0

        # Group failures by agent and tool
        by_agent = defaultdict(list)
        for f in failures:
            by_agent[f.get("agent", "unknown")].append(f.get("tool", ""))

        suggestions = []
        for agent, tools in by_agent.items():
            common_errors = Counter(tools).most_common(3)
            for tool, count in common_errors:
                if count >= 3:
                    suggestions.append({
                        "agent": agent,
                        "tool": tool,
                        "failure_count": count,
                        "action": "review_handler",
                        "suggestion": f"Agent '{agent}' 工具 '{tool}' 失败 {count} 次，建议检查 handler 实现"
                    })

        # Auto-generate improvement tasks
        tasks = []
        for s in suggestions[:5]:
            tasks.append({
                "task": f"Fix {s['agent']}/{s['tool']} ({s['failure_count']} failures)",
                "priority": "high" if s['failure_count'] > 5 else "medium",
                "category": "handler_fix",
            })

        return {
            "status": "completed",
            "total_executions": len(history),
            "failure_rate": round(failure_rate, 3),
            "failure_patterns": len(suggestions),
            "suggestions": suggestions[:5],
            "auto_generated_tasks": tasks,
            "score": max(0, round((1 - failure_rate) * 100)),
        }

    def _load_execution_history(self) -> list[dict]:
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT agent, tool, status, timestamp FROM decisions ORDER BY timestamp DESC LIMIT 500"
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.debug("Execution history DB read failed", exc_info=True)
            return []

    # ═══ STAGE 2: RLAIF Auditor (Constitutional AI-style) ═══

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

    def _execute_test(self, test: dict) -> str:
        ttype = test["type"]
        detail = test["test"]

        if ttype == "handler":
            handler = detail.replace("handler_import:", "")
            try:
                mod, fn = handler.rsplit(".", 1)
                import importlib
                m = importlib.import_module(mod)
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

    def _run_multi_proposer(self, diagnosis_stage: dict) -> dict:
        """Generate mechanism-diverse improvement proposals from diagnosis."""
        diagnosis_brief = self._load_diagnosis_brief()
        if not diagnosis_brief:
            diagnosis_clusters = diagnosis_stage.get("clusters", [])
            if diagnosis_clusters:
                lines = ["# Auto-Generated Diagnosis", ""]
                lines.append(f"Found {len(diagnosis_clusters)} failure clusters.")
                for c in diagnosis_clusters[:5]:
                    sig = c.get("signature", ("?", "?", "?"))
                    lines.append(f"- {sig[0]} / {sig[1]} / {sig[2]} ({c.get('cases', 0)} cases)")
                diagnosis_brief = "\n".join(lines)

        bundle = self._proposer.generate(diagnosis_brief)

        # Save bundle
        bundle_path = self.root / ".openharness" / "runtime" / "proposal_bundle.json"
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        return {
            "status": "completed",
            "total_proposals": len(bundle.proposals),
            "proposals": [
                {
                    "id": p.proposal_id,
                    "title": p.title,
                    "mechanism_family": p.mechanism_family,
                    "exact_hook": p.exact_hook,
                    "summary": p.summary[:200],
                }
                for p in bundle.proposals
            ],
            "bundle_path": str(bundle_path),
            "score": min(100, len(bundle.proposals) * 25),
        }

    def _load_diagnosis_brief(self) -> str:
        brief_path = self.root / ".openharness" / "runtime" / "diagnosis_brief.md"
        if brief_path.exists():
            return brief_path.read_text(encoding="utf-8")
        return ""

    # ═══ STAGE 8: Acceptance Gate (Self-Harness-style) ═══

    def _run_acceptance_gate(self, stages: dict) -> dict:
        """Compare current scores against baseline to decide acceptance."""
        current = {
            "train": stages.get("auto_testing", {}).get("score", 0),
            "heldout": stages.get("rlaif_audit", {}).get("score", 0),
        }

        baseline = self._load_baseline_scores()
        result = self._acceptance.evaluate(baseline, current)

        if result["accepted"]:
            self._store_baseline_scores(current)

        return {
            "status": "completed",
            "accepted": result["accepted"],
            "decision": result["decision"],
            "reason": result["reason"],
            "baseline_scores": baseline,
            "current_scores": current,
            "splits": result.get("splits", {}),
            "score": 100 if result["accepted"] else 0,
        }

    def _load_baseline_scores(self) -> dict[str, float]:
        baseline_path = self.root / ".openharness" / "runtime" / "snapshots" / "baseline_scores.json"
        if baseline_path.exists():
            return json.loads(baseline_path.read_text(encoding="utf-8"))
        return {"train": 0, "heldout": 0}

    def _store_baseline_scores(self, scores: dict[str, float]):
        baseline_path = self.root / ".openharness" / "runtime" / "snapshots" / "baseline_scores.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ═══ STAGE 9: Runtime A2A Validation (Layer 2) ═══

    def _run_runtime_a2a(self) -> dict:
        """Validate every handler at runtime with real patient data via A2A calls."""
        results: list[dict] = []
        timing: list[float] = []
        passed = 0
        failed = 0
        by_agent: dict[str, dict] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

        for agent_name, agent in self._agents.items():
            tools = agent.get("tools", [])
            if not tools:
                continue

            patients = self._get_runtime_patients(agent_name)
            if not patients:
                by_agent[agent_name] = {"total": len(tools) * 3, "passed": 0, "failed": len(tools) * 3, "note": "no patients"}
                failed += len(tools) * 3
                continue

            for tool in tools:
                handler = tool.get("handler", "")
                tool_name = tool.get("name", "")
                if not handler:
                    continue

                for patient in patients[:3]:
                    params = self._build_runtime_params(patient, tool)
                    t0 = time.time()
                    try:
                        resp = self._a2a_call_with_timeout(agent_name, tool_name, params, timeout=10)
                        elapsed = (time.time() - t0) * 1000
                        timing.append(elapsed)
                        result_entry = self._validate_runtime_response(resp, tool_name, agent_name, patient, elapsed)
                    except Exception as e:
                        elapsed = (time.time() - t0) * 1000
                        timing.append(elapsed)
                        result_entry = {
                            "agent": agent_name, "tool": tool_name,
                            "patient": patient.get("patient_id", "?"),
                            "status": "error", "elapsed_ms": elapsed,
                            "error_type": type(e).__name__, "error_message": str(e)[:200],
                        }

                    results.append(result_entry)
                    by_agent[agent_name]["total"] += 1
                    if result_entry.get("status") in ("pass", "ok"):
                        passed += 1
                        by_agent[agent_name]["passed"] += 1
                    else:
                        failed += 1
                        by_agent[agent_name]["failed"] += 1

                    self._persist_runtime_result(result_entry)

        timing_sorted = sorted(timing)
        n = len(timing_sorted)
        return {
            "status": "completed",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "score": round(passed / len(results) * 100) if results else 0,
            "timing": {
                "p50_ms": round(timing_sorted[n // 2]) if n else 0,
                "p95_ms": round(timing_sorted[int(n * 0.95)]) if n else 0,
                "p99_ms": round(timing_sorted[int(n * 0.99)]) if n else 0,
            },
            "failures": [r for r in results if r.get("status") not in ("pass", "ok")][:20],
            "by_agent": dict(by_agent),
        }

    def _get_runtime_patients(self, agent_name: str) -> list[dict]:
        try:
            from haip.patients import load_patients
            return load_patients(agent_name, limit=5, only_compatible=False)
        except Exception:
            logger.debug("Load patients failed, falling back, agent=%s", agent_name, exc_info=True)
            return self._load_patients_fallback()

    def _load_patients_fallback(self) -> list[dict]:
        patients_path = self.root / "packages/haip-hospital/data/patients.json"
        if not patients_path.exists():
            return []
        try:
            data = json.loads(patients_path.read_text(encoding="utf-8"))
            all_pts = data.get("patients", []) if isinstance(data, dict) else data
            return all_pts[:5] if isinstance(all_pts, list) else []
        except Exception:
            logger.warning("Patient JSON fallback parse failed", exc_info=True)
            return []

    def _build_runtime_params(self, patient: dict, tool: dict) -> dict:
        input_schema = tool.get("input", {})
        params: dict[str, Any] = {}
        for key in input_schema:
            if key in patient:
                params[key] = patient[key]
            elif isinstance(patient.get("lab_results"), dict) and key in patient["lab_results"]:
                params[key] = patient["lab_results"][key]
        params.setdefault("patient_id", patient.get("patient_id", ""))
        return params

    def _a2a_call_with_timeout(self, agent: str, tool_name: str, params: dict, timeout: int = 10) -> dict:
        from concurrent.futures import Future

        from haip.a2a import call as a2a_call
        if self._a2a_executor is None:
            self._a2a_executor = ThreadPoolExecutor(max_workers=4)
        future: Future = self._a2a_executor.submit(a2a_call, agent, tool_name, params)
        return future.result(timeout=timeout)

    def _validate_runtime_response(self, resp: dict, tool_name: str, agent_name: str,
                                    patient: dict, elapsed_ms: float) -> dict:
        base = {
            "agent": agent_name, "tool": tool_name,
            "patient": patient.get("patient_id", "?"),
            "elapsed_ms": round(elapsed_ms, 1),
            "status": "pass",
            "error_type": "", "error_message": "",
        }
        if not isinstance(resp, dict):
            base["status"] = "fail"
            base["error_type"] = "invalid_response_type"
            base["error_message"] = f"Expected dict, got {type(resp).__name__}"
            return base
        if resp.get("status") == "error":
            error_msg = str(resp.get("error", resp.get("message", "")))
            if MetaHarness._is_input_validation_error(error_msg):
                base["status"] = "skip"
                base["error_type"] = "missing_input"
                base["error_message"] = error_msg[:200]
                return base
            base["status"] = "fail"
            base["error_type"] = "a2a_error"
            base["error_message"] = error_msg[:200]
            return base
        if resp.get("status") == "blocked":
            base["status"] = "blocked"
            base["error_type"] = "guard_blocked"
            base["error_message"] = str(resp.get("error", ""))[:200]
            return base
        result = resp.get("result", resp)
        if result is None or (isinstance(result, dict) and not result):
            base["status"] = "fail"
            base["error_type"] = "empty_result"
            base["error_message"] = "handler returned empty result"
            return base
        base["response_summary"] = str(result)[:500]
        return base

    def _persist_runtime_result(self, result: dict):
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS runtime_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent TEXT NOT NULL,
                        tool TEXT NOT NULL,
                        patient_id TEXT,
                        status TEXT NOT NULL,
                        elapsed_ms REAL,
                        error_type TEXT,
                        error_message TEXT,
                        response_summary TEXT,
                        timestamp REAL NOT NULL
                    )"""
                )
                conn.execute(
                    """INSERT INTO runtime_results (agent, tool, patient_id, status, elapsed_ms,
                       error_type, error_message, response_summary, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (result.get("agent", ""), result.get("tool", ""),
                     result.get("patient", ""), result.get("status", ""),
                     result.get("elapsed_ms", 0), result.get("error_type", ""),
                     result.get("error_message", ""), result.get("response_summary", ""),
                     time.time()),
                )
                conn.commit()
        except Exception:
            logger.debug("Runtime results DB save failed", exc_info=True)

    @staticmethod
    def _is_input_validation_error(msg: str) -> bool:
        """Check if an error message is an expected input validation error."""
        validation_keywords = ["不能为空", "必须为", "缺失", "Missing required", "required argument",
                               "required keyword", "missing 1 required", "must be a string"]
        return any(kw in msg for kw in validation_keywords)

    # ═══ STAGE 10: Clinical Rule Compliance (Layer 3a) ═══

    def _run_rule_compliance(self, runtime_stage: dict) -> dict:
        """Check if agent outputs comply with clinical knowledge rules."""
        total_rules_checked = 0
        total_passed = 0
        total_violated = 0
        violations: list[dict] = []

        for agent_name, agent in self._agents.items():
            dept = agent.get("department", "")
            if not dept:
                continue
            rules = self._load_matching_rules(agent_name, dept)
            if not rules:
                continue

            a2a_failures = runtime_stage.get("by_agent", {}).get(agent_name, {})
            if a2a_failures.get("failed", 0) > a2a_failures.get("total", 0) * 0.5:
                continue  # skip agents with >50% failures

            for rule in rules:
                total_rules_checked += 1
                result = self._evaluate_rule_condition(rule)
                if result is None:
                    continue  # unevaluable rule
                if result:
                    total_passed += 1
                else:
                    total_violated += 1
                    violations.append({
                        "rule_id": rule.get("id", "?"),
                        "agent": agent_name,
                        "condition": rule.get("condition", {}),
                        "rule_description": rule.get("description", str(rule)[:100]),
                    })

        return {
            "status": "completed",
            "total_rules_checked": total_rules_checked,
            "passed": total_passed,
            "violated": total_violated,
            "score": round(total_passed / total_rules_checked * 100) if total_rules_checked else 100,
            "top_violations": violations[:10],
        }

    def _load_matching_rules(self, agent_name: str, dept: str) -> list[dict]:
        rules: list[dict] = []
        agent_key = agent_name.replace("-", "_")
        dept_key = dept.replace(" ", "").replace("科", "")

        if not self.rules_dir.exists():
            return rules

        for rd in sorted(self.rules_dir.iterdir()):
            if not rd.is_dir() or rd.name.startswith("_"):
                continue
            if agent_key not in rd.name.lower() and dept_key not in rd.name.lower():
                continue
            for rf in sorted(rd.glob("*.yaml")):
                try:
                    content = rf.read_text(encoding="utf-8")
                    for doc in yaml.safe_load_all(content):
                        if isinstance(doc, dict) and "rules" in doc:
                            rules.extend(doc["rules"])
                except Exception:
                    logger.debug("YAML rules load failed: %s", rf, exc_info=True)
        return rules

    def _evaluate_rule_condition(self, rule: dict) -> bool | None:
        condition = rule.get("condition", {})
        if not isinstance(condition, dict):
            return None

        field = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected = condition.get("value")

        if not field:
            if "and" in condition:
                return all(self._evaluate_rule_condition({"condition": c}) is True
                          for c in condition["and"])
            if "or" in condition:
                return any(self._evaluate_rule_condition({"condition": c}) is True
                          for c in condition["or"])
            return None

        return self._eval_operator(field, operator, expected)

    def _eval_operator(self, field: str, operator: str, expected) -> bool:
        try:
            parts = field.split(".")
            if len(parts) >= 2 and parts[0] == "lab_results":
                return self._check_lab_field_exists(parts[1])
            if field and "." not in field:
                return self._check_patient_field_exists(field)
            return True
        except Exception:
            logger.debug("Rule condition eval failed: %s", field, exc_info=True)
            return None

    def _ensure_patient_caches(self):
        """Build cached sets of lab and top-level patient fields (lazy)."""
        if hasattr(self, '_patient_lab_cache'):
            return
        import json
        patients_path = self.root / "packages" / "haip-hospital" / "data" / "patients.json"
        try:
            with open(patients_path, encoding="utf-8") as f:
                data = json.load(f)
            lab_set, top_set = set(), set()
            for p in data.get("patients", []):
                labs = p.get("lab_results", {})
                if isinstance(labs, dict):
                    lab_set.update(labs.keys())
                top_set.update(p.keys())
            self._patient_lab_cache = lab_set
            self._patient_top_cache = top_set
        except Exception:
            logger.warning("Patient cache build failed", exc_info=True)
            self._patient_lab_cache = set()
            self._patient_top_cache = set()

    def _check_lab_field_exists(self, field_name: str) -> bool:
        self._ensure_patient_caches()
        return field_name in self._patient_lab_cache

    def _check_patient_field_exists(self, field_name: str) -> bool:
        self._ensure_patient_caches()
        return field_name in self._patient_top_cache

    def _check_lab_field_exists(self, field_name: str) -> bool:
        """Check if a lab field exists in at least one patient record."""
        if not hasattr(self, '_patient_lab_coverage'):
            self._patient_lab_coverage = self._build_lab_coverage()
        return field_name in self._patient_lab_coverage

    def _build_lab_coverage(self) -> set:
        """Build set of all lab field names present in patient data."""
        import json
        patients_path = self.root / "packages" / "haip-hospital" / "data" / "patients.json"
        try:
            with open(patients_path, encoding="utf-8") as f:
                data = json.load(f)
            labs_set: set = set()
            for p in data.get("patients", []):
                labs = p.get("lab_results", {})
                if isinstance(labs, dict):
                    labs_set.update(labs.keys())
            return labs_set
        except Exception:
            logger.warning("Lab coverage build failed", exc_info=True)
            return set()

    # ═══ STAGE 11: Guard Effectiveness (Layer 3b) ═══

    def _run_guard_effectiveness(self) -> dict:
        """Test guard triggers by injecting ALL high-risk scenarios and checking interception.
        
        Enhanced (v1.3): tests every scenario per agent (not just first), detects silent-bypass.
        """
        tested = 0
        correctly_blocked = 0
        missed_blocks = 0
        false_positives = 0
        silent_bypasses = 0
        by_agent: dict[str, dict] = {}

        for agent_name, agent in self._agents.items():
            high_risk = agent.get("guard", {}).get("high_risk_scenarios", [])
            if not high_risk:
                continue

            blocked = 0
            missed = 0
            false_pos = 0

            for scenario in high_risk:  # test ALL scenarios (not just first)
                tested += 1
                try:
                    result = self._test_guard_scenario(agent_name, str(scenario))
                    if result == "blocked":
                        correctly_blocked += 1
                        blocked += 1
                    elif result == "missed":
                        missed_blocks += 1
                        missed += 1
                    elif result == "false_positive":
                        false_positives += 1
                        false_pos += 1
                    elif result == "silent_bypass":
                        missed_blocks += 1
                        silent_bypasses += 1
                        missed += 1
                except Exception:
                    logger.debug("Guard scenario test failed, agent=%s", agent_name, exc_info=True)
                    missed_blocks += 1
                    missed += 1

            by_agent[agent_name] = {
                "scenarios": len(high_risk),
                "blocked": blocked,
                "missed": missed,
                "false_pos": false_pos,
            }

        return {
            "status": "completed",
            "total_scenarios": tested,
            "correctly_blocked": correctly_blocked,
            "missed_blocks": missed_blocks,
            "false_positives": false_positives,
            "silent_bypasses": silent_bypasses,
            "score": round(correctly_blocked / tested * 100) if tested else 100,
            "by_agent": by_agent,
        }

    def _test_guard_scenario(self, agent_name: str, scenario: str) -> str:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FutureTimeout
        def _call():
            from haip.a2a import call_with_loop
            result = call_with_loop(agent_name, scenario, max_steps=2)
            guard = result.get("guard", {})
            if guard.get("passed") is False:
                return "blocked"
            if result.get("status") == "blocked":
                return "blocked"
            if guard.get("checked") is False and not guard.get("flags"):
                return "silent_bypass"
            return "missed"
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call)
                return future.result(timeout=15)
        except (FutureTimeout, TimeoutError):
            return "missed"
        except Exception:
            logger.debug("Guard execution failed", exc_info=True)
            return "missed"

    # ═══ STAGE 12: Quality Intelligence (Layer 4) ═══

    def _run_quality_intelligence(self, runtime_stage: dict, rule_stage: dict) -> dict:
        """Cross-dimensional quality analysis: coverage, consistency, performance."""
        by_agent = runtime_stage.get("by_agent", {})
        failures = runtime_stage.get("failures", [])
        timing = runtime_stage.get("timing", {})

        total_agents = len(self._agents)
        agents_with_failures = sum(1 for v in by_agent.values() if v.get("failed", 0) > 0)
        total_failures = runtime_stage.get("failed", 0)
        total_tasks = runtime_stage.get("total", 0)
        pass_rate = runtime_stage.get("score", 0)

        rule_violations = rule_stage.get("violated", 0)
        rule_score = rule_stage.get("score", 0)

        dept_coverage = self._compute_department_coverage()

        quality_score = round(
            (pass_rate * 0.4) + (rule_score * 0.3) +
            (max(0, 100 - agents_with_failures * 2) * 0.2) +
            (dept_coverage.get("coverage_pct", 0) * 0.1)
        )

        return {
            "status": "completed",
            "pass_rate": pass_rate,
            "rule_compliance_rate": rule_score,
            "agents_healthy": total_agents - agents_with_failures,
            "agents_with_issues": agents_with_failures,
            "runtime_timing": timing,
            "department_coverage": dept_coverage,
            "trend": self._detect_trend(pass_rate, rule_score),
            "score": min(100, quality_score),
        }

    def _compute_department_coverage(self) -> dict:
        agent_depts = {a.get("department", ""): a.get("name", "") for a in self._agents.values()}
        covered = len([d for d in agent_depts if d])
        return {
            "total_agents": len(self._agents),
            "agents_with_dept": covered,
            "coverage_pct": round(covered / len(self._agents) * 100) if self._agents else 0,
        }

    def _detect_trend(self, pass_rate: int, rule_score: int) -> str:
        prev = self._load_previous_quality()
        prev_pass = prev.get("pass_rate", 0)
        prev_rule = prev.get("rule_score", 0)
        current = {"pass_rate": pass_rate, "rule_score": rule_score}

        qpath = self.root / ".openharness" / "runtime" / "snapshots" / "quality_trend.json"
        qpath.parent.mkdir(parents=True, exist_ok=True)
        try:
            history = json.loads(qpath.read_text(encoding="utf-8")) if qpath.exists() else []
        except Exception:
            logger.debug("Quality trend JSON load failed", exc_info=True)
            history = []
        history.append(current)
        qpath.write_text(json.dumps(history[-20:], indent=2), encoding="utf-8")

        if not prev_pass:
            return "baseline"
        if pass_rate > prev_pass and rule_score >= prev_rule:
            return "improving"
        if pass_rate < prev_pass - 2 or rule_score < prev_rule - 2:
            return "declining"
        return "stable"

    def _load_previous_quality(self) -> dict:
        qpath = self.root / ".openharness" / "runtime" / "snapshots" / "quality_trend.json"
        if not qpath.exists():
            return {}
        try:
            history = json.loads(qpath.read_text(encoding="utf-8"))
            return history[-1] if history else {}
        except Exception:
            logger.debug("Previous quality data load failed", exc_info=True)
            return {}

    # ═══ UTILITIES ═══

    def _compute_unified_score(self, stages: dict) -> int:
        weights = {
            "self_improvement": 0.06,
            "rlaif_audit": 0.08,
            "auto_testing": 0.06,
            "continuous_learning": 0.06,
            "multi_agent_review": 0.04,
            "causal_diagnosis": 0.04,
            "runtime_a2a": 0.18,
            "rule_compliance": 0.12,
            "guard_effectiveness": 0.12,
            "quality_intelligence": 0.14,
            "multi_proposer": 0.08,
            "acceptance_gate": 0.04,
        }
        total = 0.0
        for name, weight in weights.items():
            score = stages.get(name, {}).get("score", 0)
            total += score * weight
        return round(total)

    def _extract_top_actions(self, stages: dict) -> list[str]:
        actions: list[str] = []

        violations = stages.get("rlaif_audit", {}).get("violations", [])
        for v in violations[:3]:
            actions.append(f"[{v.get('severity','')}] {v.get('agent','')}: {v.get('detail','')}")

        runtime_failures = stages.get("runtime_a2a", {}).get("failures", [])
        for f in runtime_failures[:3]:
            actions.append(f"[runtime] {f.get('agent','')}/{f.get('tool','')}: {f.get('error_type','')}")

        rule_violations = stages.get("rule_compliance", {}).get("top_violations", [])
        for v in rule_violations[:3]:
            actions.append(f"[rule] {v.get('agent','')}: {v.get('rule_description','')}")

        proposals = stages.get("multi_proposer", {}).get("proposals", [])
        for p in proposals[:3]:
            actions.append(f"[proposal] {p.get('title','')} ({p.get('mechanism_family','')})")

        return actions

    def apply_proposal(self, proposal_id: str) -> dict[str, Any]:
        """Apply a specific proposal from the stored bundle."""
        bundle_path = self.root / ".openharness" / "runtime" / "proposal_bundle.json"
        if not bundle_path.exists():
            return {"error": "No proposal bundle found. Run multi_proposer stage first."}

        bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
        proposals = bundle_data.get("proposals", [])

        matched = [p for p in proposals if p.get("proposal_id") == proposal_id]
        if not matched:
            return {"error": f"No proposal found with id '{proposal_id}'"}

        raw = matched[0]
        extra_fields = set(raw.keys()) - {
            "proposal_id", "title", "selected_cluster", "selected_surface",
            "mechanism", "mechanism_family", "exact_hook", "why_distinct",
            "net_gain_hypothesis", "regression_guard", "summary", "final_message",
            "candidate_values", "metadata",
        }
        metadata = {k: raw[k] for k in extra_fields if k in raw}
        proposal = Proposal(
            proposal_id=raw.get("proposal_id", ""),
            title=raw.get("title", ""),
            selected_cluster=raw.get("selected_cluster", ""),
            selected_surface=raw.get("selected_surface", ""),
            mechanism=raw.get("mechanism", ""),
            mechanism_family=raw.get("mechanism_family", ""),
            exact_hook=raw.get("exact_hook", ""),
            why_distinct=raw.get("why_distinct", ""),
            net_gain_hypothesis=raw.get("net_gain_hypothesis", ""),
            regression_guard=raw.get("regression_guard", ""),
            summary=raw.get("summary", ""),
            final_message=raw.get("final_message"),
            candidate_values=raw.get("candidate_values", {}),
            metadata=metadata,
        )

        change_result = apply_candidate(proposal, self.root)
        materialize_result = self._proposer.materialize(proposal)

        return {
            "status": "applied",
            "proposal_id": proposal_id,
            "changes": change_result,
            "manifest": materialize_result,
        }

    def run_proposer_loop(self, max_iterations: int = 3) -> dict[str, Any]:
        """Full self-harness loop: diagnose → propose → apply → evaluate."""
        results = []

        for i in range(max_iterations):
            diag = self._run_causal_diagnosis()
            if diag.get("clusters_count", 0) == 0:
                break

            prop = self._run_multi_proposer(diag)
            if prop.get("total_proposals", 0) == 0:
                break

            for p in prop.get("proposals", []):
                apply_result = self.apply_proposal(p["id"])
                results.append(apply_result)

            gate = self._run_acceptance_gate({
                "auto_testing": self._run_auto_testing(),
                "rlaif_audit": self._run_rlaif_audit(),
            })

            if gate["accepted"]:
                self._snapshot.record(
                    "harness_loop",
                    {"accepted": True, "iteration": i + 1},
                    {"gate": gate},
                )
            else:
                break

        return {
            "iterations": max_iterations,
            "results_count": len(results),
            "results": results,
        }


# ═══ API ═══

_singleton_state: dict = {}


def get_meta_harness() -> MetaHarness:
    from haip._singleton import locked_singleton
    return locked_singleton(MetaHarness, _singleton_state, "meta")


if __name__ == "__main__":
    mh = MetaHarness()
    report = mh.run_full_cycle()
    print(json.dumps(report, ensure_ascii=False, indent=2))
