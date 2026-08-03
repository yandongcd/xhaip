import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-core"))
from haip.meta_harness import MetaHarness

mh = MetaHarness()
history = []

for cycle in range(3):
    t0 = time.time()
    print(f"\n=== Cycle {cycle+1} ===")
    r = mh.run_full_cycle(run_proposer=True)
    s = r["stages"]

    rt = s.get("runtime_a2a", {})
    rc = s.get("rule_compliance", {})
    gi = s.get("quality_intelligence", {})
    g = s.get("acceptance_gate", {})

    print(f"  Unified: {r['unified_score']} | Duration: {r['duration_ms']}ms")
    print(f"  Runtime: {rt.get('score',0)}% ({rt.get('passed',0)}/{rt.get('total',0)})")
    print(f"  RuleComp: {rc.get('score',0)}% ({rc.get('violated',0)} violations)")
    print(f"  QualIntel: {gi.get('score',0)}% trend={gi.get('trend','?')}")
    print(f"  Gate: {g.get('decision','?')} -- {g.get('reason','?')}")

    actions = r.get("top_actions", [])
    for a in actions[:3]:
        print(f"  Action: {a[:120]}")

    history.append({
        "cycle": cycle + 1,
        "unified": r["unified_score"],
        "runtime_score": rt.get("score", 0),
        "rule_score": rc.get("score", 0),
        "gate_decision": g.get("decision", ""),
    })

    elapsed = time.time() - t0
    print(f"  Cycle time: {elapsed:.0f}s")

print("\n=== Iteration Summary ===")
for h in history:
    print(f"  Cycle {h['cycle']}: unified={h['unified']} runtime={h['runtime_score']}% rule={h['rule_score']}% gate={h['gate_decision']}")
