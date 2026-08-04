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
import os
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
from haip.meta_harness_mixins.audit import MetaHarnessAuditMixin
from haip.meta_harness_mixins.proposer import MetaHarnessProposerMixin
from haip.meta_harness_mixins.quality import MetaHarnessQualityMixin
from haip.meta_harness_mixins.runtime import MetaHarnessRuntimeMixin

# ══════════════════════════════════════════════════════════════════
# METAHARNESS ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════

class MetaHarness(MetaHarnessAuditMixin, MetaHarnessRuntimeMixin,
                  MetaHarnessQualityMixin, MetaHarnessProposerMixin):
    """Unified self-improvement framework orchestrator (v3.0.0).

    方法按域拆分至 meta_harness_mixins:
      - audit.py:     RLAIF 审计/自动测试/持续学习/多智能体评审
      - runtime.py:   运行时 A2A/规则合规/患者缓存
      - quality.py:   Guard 有效性/质量智能/评分
      - proposer.py:  多提案/提案应用
    """

    def __init__(self, project_root: str = "", runtime_a2a_limit: int | None = None,
                 a2a_timeout: int = 10):
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
        # Runtime A2A 规模控制: None=全量(生产), 数值=最多 N 次调用(测试/CI)
        self._runtime_a2a_limit = runtime_a2a_limit
        if self._runtime_a2a_limit is None:
            env_limit = os.environ.get("HAIP_RUNTIME_A2A_LIMIT", "")
            if env_limit.isdigit():
                self._runtime_a2a_limit = int(env_limit)
        self._a2a_timeout = a2a_timeout
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



_singleton_state: dict = {}


def get_meta_harness() -> MetaHarness:
    from haip._singleton import locked_singleton
    return locked_singleton(MetaHarness, _singleton_state, "meta")


if __name__ == "__main__":
    mh = MetaHarness()
    report = mh.run_full_cycle()
    print(json.dumps(report, ensure_ascii=False, indent=2))