"""Guard 有效性+质量智能+评分+接受门 — meta_harness mixin (P1-6 拆分)."""

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


class MetaHarnessQualityMixin:
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
        from concurrent.futures import TimeoutError as FutureTimeout

        # 测试环境 (HAIP_TEST_MODE): 注入 MockProvider, 禁止打真实 LLM API
        # (真实 DeepSeek key 无效时 400 重试风暴导致 CI 超时)
        from haip import llm as haip_llm
        orig_from_config = None
        if os.environ.get("HAIP_TEST_MODE", "") == "true":
            from haip.llm.mock import MockProvider
            orig_from_config = haip_llm.LLMProvider.from_config
            haip_llm.LLMProvider.from_config = lambda cfg: MockProvider({})

        def _call():
            try:
                from haip.a2a import call_with_loop, internal_permission_context
                result = call_with_loop(agent_name, scenario, max_steps=2,
                                        perm_ctx=internal_permission_context())
                guard = result.get("guard", {})
                if guard.get("passed") is False:
                    return "blocked"
                if result.get("status") == "blocked":
                    return "blocked"
                if guard.get("checked") is False and not guard.get("flags"):
                    return "silent_bypass"
                return "missed"
            finally:
                if orig_from_config is not None:
                    haip_llm.LLMProvider.from_config = orig_from_config
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

