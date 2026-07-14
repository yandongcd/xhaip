"""Rule arbitration engine — resolves conflicts when multiple rules match.

Ported from haip-0710's src/agents/rules/arbitration_engine.py.

Strategies:
    - conservative: prefer safest/most cautious conclusion
    - evidence_weighted: rank by source tier + certainty
    - admin_override: administrator-specified override
    - first_match: first applicable rule wins
"""

from __future__ import annotations

from pathlib import Path

import yaml

from haip.rules_engine.evaluator import evaluate
from haip.rules_engine.models import (
    ArbitrationResult,
    Certainty,
    Conflict,
    EvaluationContext,
    GuidelineSource,
    Rule,
)

_CONFLICT_POLICY_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "data" / "policy" / "conflict_policy.yaml"
)
_POLICY_CACHE: dict | None = None


def _load_policy() -> dict:
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE
    path = _CONFLICT_POLICY_PATH
    if not path.exists():
        _POLICY_CACHE = {"arbitration": {"default_strategy": "conservative", "logging": "full"}}
        return _POLICY_CACHE
    with open(path, "r", encoding="utf-8") as f:
        _POLICY_CACHE = yaml.safe_load(f) or {}
    return _POLICY_CACHE


def reload_policy():
    global _POLICY_CACHE
    _POLICY_CACHE = None


# Global source registry (will be populated by rule loader)
_SOURCE_REGISTRY: dict[str, GuidelineSource] = {}


def register_source(source: GuidelineSource):
    _SOURCE_REGISTRY[source.id] = source


def get_source(source_id: str) -> GuidelineSource | None:
    return _SOURCE_REGISTRY.get(source_id)


def evaluate_rules(
    rules: list[Rule],
    context: EvaluationContext,
    strategy: str | None = None,
) -> ArbitrationResult:
    """Evaluate all rules against a context and arbitrate conflicts."""
    applicable = []
    for rule in rules:
        try:
            if rule.condition_expr:
                matched = evaluate(rule.condition_expr, context)
            elif rule.condition_eval:
                matched = evaluate(rule.condition_eval, context)
            else:
                matched = True
            if matched:
                applicable.append(rule)
        except Exception:
            continue

    if not applicable:
        return ArbitrationResult(
            winner_rule_id="",
            conclusion="无法判定：无匹配规则",
            certainty=Certainty.WEAK,
            reasoning="无规则适用于当前上下文",
            strategy_used=strategy or "none",
        )

    if len(applicable) == 1:
        r = applicable[0]
        return ArbitrationResult(
            winner_rule_id=r.id,
            conclusion=r.conclusion,
            certainty=r.certainty,
            reasoning=f"单一规则匹配: {r.id}",
            strategy_used="single_match",
        )

    conflicts = _detect_conflicts(applicable, context)
    if not conflicts:
        r = applicable[0]
        return ArbitrationResult(
            winner_rule_id=r.id,
            conclusion=r.conclusion,
            certainty=r.certainty,
            reasoning="多条规则结论一致",
            strategy_used="consensus",
        )

    return _arbitrate(applicable, conflicts, context, strategy)


def _detect_conflicts(rules: list[Rule], context: EvaluationContext) -> list[Conflict]:
    by_point: dict[str, list[Rule]] = {}
    for r in rules:
        by_point.setdefault(r.decision_point, []).append(r)

    conflicts = []
    for point, rs in by_point.items():
        conclusions = list(set(r.conclusion for r in rs))
        if len(conclusions) > 1:
            conflicts.append(Conflict(
                rule_ids=[r.id for r in rs],
                decision_point=point,
                conclusions=conclusions,
                context=context,
            ))
    return conflicts


def _arbitrate(
    rules: list[Rule],
    conflicts: list[Conflict],
    context: EvaluationContext,
    strategy: str | None,
) -> ArbitrationResult:
    policy = _load_policy()
    strat = strategy or policy.get("arbitration", {}).get("default_strategy", "conservative")

    # Check for admin overrides
    policy_overrides = policy.get("arbitration", {}).get("override_rules", [])
    for override in policy_overrides:
        override_rule_id = override.get("rule_id")
        for r in rules:
            if r.id == override_rule_id:
                return ArbitrationResult(
                    winner_rule_id=r.id,
                    conclusion=override.get("decision", r.conclusion),
                    certainty=r.certainty,
                    reasoning=f"管理员覆盖: {override.get('reason', '')}",
                    chain=[f"Override: {override_rule_id}"],
                    conflicts=conflicts,
                    overridden_by_admin=True,
                    strategy_used="admin_override",
                )

    ranked = _rank_rules(rules, context)
    winner = ranked[0]
    chain = _build_chain(ranked)

    return ArbitrationResult(
        winner_rule_id=winner.id,
        conclusion=winner.conclusion,
        certainty=winner.certainty,
        reasoning=f"仲裁完成，胜出: {winner.id}",
        chain=chain,
        conflicts=conflicts,
        overridden_by_admin=False,
        strategy_used=strat,
    )


def _rank_rules(rules: list[Rule], context: EvaluationContext) -> list[Rule]:
    def score(r: Rule) -> tuple:
        source_priority = 999
        certainty_score = {"strong": 0, "moderate": 1, "weak": 2}.get(r.certainty.value, 1)

        for e in r.evidence:
            src = get_source(e.source_id)
            if src:
                sp = src.admin_priority
                if sp < source_priority:
                    source_priority = sp

        return (source_priority, certainty_score, r.priority)

    return sorted(rules, key=score)


def _build_chain(ranked: list[Rule]) -> list[str]:
    chain = []
    for i, r in enumerate(ranked):
        src_info = "; ".join(
            f"{e.source_id}§{e.chapter}" for e in r.evidence
        ) if r.evidence else "无来源"
        chain.append(f"#{i + 1}: {r.id} — {r.conclusion} ({src_info})")
    return chain
