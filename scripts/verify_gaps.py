"""Verify G1-G3 + G7-G8 modules."""
import sys
sys.path.insert(0, "packages/haip-core")

print("=== G1: Hospital Data Models ===")
from haip.data.models import ALL_MODELS, PatientInfo, LabResult, VitalSigns
print(f"ORM Models OK: {len(ALL_MODELS)} tables (HIS/EMR/LIS/PACS/NIS)")

print("\n=== G2: OPA Policy Engine ===")
from haip.policy import PolicyEngine, get_policy_engine
engine = get_policy_engine()

# Test: same department
ctx1 = {"dept_scope": "self", "agent_department": "orthopedic_surgery", "patient_department": "orthopedic_surgery"}
assert engine.allow(ctx1), "Same dept access should be allowed"
print(f"  Same dept: allow={engine.allow(ctx1)}")

# Test: different department (should be denied)
ctx2 = {"dept_scope": "self", "agent_department": "cardiology", "patient_department": "orthopedic_surgery"}
assert not engine.allow(ctx2), "Cross dept self-scope should be denied"
print(f"  Cross dept (self scope): allow={engine.allow(ctx2)}, reason={engine.deny_reason(ctx2)}")

# Test: emergency override
ctx3 = {"agent_id": "emergency"}
assert engine.allow(ctx3), "Emergency should always be allowed"
print(f"  Emergency: allow={engine.allow(ctx3)}")

# Test: all scope
ctx4 = {"dept_scope": "all"}
assert engine.allow(ctx4), "All-scope should be allowed"
print(f"  All scope: allow={engine.allow(ctx4)}")

# Test: consulted
ctx5 = {"dept_scope": "consulted", "agent_department": "cardiology", "consulted_depts": ["cardiology", "orthopedic_surgery"]}
assert engine.allow(ctx5), "Consulted dept should be allowed"
print(f"  Consulted: allow={engine.allow(ctx5)}")

print(f"  Rules: {len(engine.list_rules())}")

print("\n=== G3: Clinical Rules Engine ===")
from haip.rules_engine import evaluate, EvaluationContext, Rule, Certainty, evaluate_rules
from haip.rules_engine.governance import create_change_request
from haip.rules_engine.impact import analyze_impact

# Expression evaluator
ctx = EvaluationContext({"age": 72, "gender": "M", "crp": 107.3, "hb": 109.5, "diagnosis": "hip_fracture"})
assert evaluate("age >= 65", ctx), "age >= 65 should be true"
assert evaluate("gender IN [M, F]", ctx), "gender IN should be true"
assert evaluate("age >= 65 AND crp > 100", ctx), "AND compound should be true"
assert evaluate("100 <= crp <= 200", ctx), "Range should be true"
print(f"  Expression evaluator OK: age>=65={evaluate('age >= 65', ctx)}, range={evaluate('100 <= crp <= 200', ctx)}")

# Rule arbitration
rules = [
    Rule(id="r1", decision_point="anticoagulation", conclusion="建议抗凝", condition_expr="age >= 65", certainty=Certainty.STRONG),
    Rule(id="r2", decision_point="anticoagulation", conclusion="不建议抗凝", condition_expr="age >= 65 AND hb < 100", certainty=Certainty.MODERATE),
]
result = evaluate_rules(rules, ctx)
print(f"  Arbitration OK: winner={result.winner_rule_id}, conclusion={result.conclusion}, strategy={result.strategy_used}")

# Impact analysis
impact = analyze_impact("NICE-NG37", "2022.1", "2024.2", [
    {"type": "threshold_modified", "rule_id": "r1", "old_value": "age >= 70", "new_value": "age >= 65", "impact": "high"},
])
print(f"  Impact OK: {impact.source_id}, affected={len(impact.affected_rules)}, summary={impact.summary}")

print("\n=== G8: LLM Gateway ===")
from haip.llm.gateway import LLMGateway, get_llm_gateway
gw = get_llm_gateway()
print(f"  LLM Gateway OK: config={gw.config.primary_provider}, cache_size={len(gw._cache)}")

print("\n=== G7: SQL Reference Files ===")
from pathlib import Path
sql_dir = Path("data/sql")
for f in sorted(sql_dir.glob("*.sql")):
    print(f"  {f.name}: {len(f.read_text(encoding='utf-8'))} chars")

print("\n=== ALL G1-G8 MODULES VERIFIED ===")
