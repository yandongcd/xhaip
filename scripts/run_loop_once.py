import sys
from pathlib import Path

_proj_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_proj_root / "packages" / "haip-core"))
from haip.meta_harness import MetaHarness

mh = MetaHarness()
r = mh.run_full_cycle(run_proposer=True)

print(f"Version:  {r['version']}")
print(f"Unified:  {r['unified_score']}")
print(f"Duration: {r['duration_ms']}ms")
print()

s = r["stages"]
print(f"  auto_test:          {s['auto_testing']['score']}%  ({s['auto_testing']['passed']}/{s['auto_testing']['total_tests']})")
print(f"  rlaif_audit:        {s['rlaif_audit']['score']}%  (critical: {s['rlaif_audit']['critical_violations']})")
print(f"  self_improvement:   {s['self_improvement'].get('score',0)}%")
print(f"  continuous_learn:   {s['continuous_learning'].get('score',0)}%  trend={s['continuous_learning'].get('trend','?')}")
print(f"  multi_agent_review: {s['multi_agent_review'].get('score',0)}%")
print(f"  causal_diagnosis:   {s['causal_diagnosis'].get('score',0)}%  (clusters={s['causal_diagnosis'].get('clusters_count',0)}, failed={s['causal_diagnosis'].get('failed_cases',0)})")

p = s.get("multi_proposer", {})
print(f"  multi_proposer:     {p.get('score',0)}%  ({p.get('total_proposals',0)} proposals)")

g = s.get("acceptance_gate", {})
print(f"  acceptance_gate:    {g.get('score',0)}%  ({g.get('decision','?')}: {g.get('reason','?')})")

print()
print("Proposals:")
for prop in p.get("proposals", []):
    print(f"  [{prop['mechanism_family']}] {prop['title']}")

print()
print("Top actions:")
for a in r.get("top_actions", [])[:5]:
    print(f"  - {a}")
