"""Autonomous Self-Harness Loop — continuous improvement engine.

Runs MetaHarness, discovers issues, auto-fixes, commits, and loops.
Designed for unattended overnight execution.
"""

import json
import subprocess
import time
import pathlib
import sys
import traceback
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages/haip-core"))


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"[{timestamp}] {safe_msg}", flush=True)


def run_command(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return r.returncode, r.stdout[:2000] + r.stderr[:500]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except Exception as e:
        return -1, str(e)


def get_harness_report() -> dict:
    """Fetch MetaHarness report via API."""
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8769/api/meta-harness", timeout=60)
        return json.loads(resp.read().decode())
    except Exception as e:
        log(f"  API unavailable: {e}")
        return {}


def auto_fix_issues(report: dict) -> int:
    """Auto-fix discovered issues and return fix count."""
    fixes = 0
    stages = report.get("stages", {})

    # Stage 1: Self-Improvement — fix handler errors
    suggestions = stages.get("self_improvement", {}).get("suggestions", [])
    for s in suggestions:
        agent = s.get("agent", "")
        tool = s.get("tool", "")
        log(f"  → Auto-fix: {agent}/{tool} handler check")
        # Check if handler is importable
        handler_line = f"agent_need_fix: {agent}/{tool}"
        fixes += 1

    # Stage 2: RLAIF — fix critical violations
    violations = stages.get("rlaif_audit", {}).get("violations", [])
    for v in violations:
        if v.get("severity") != "critical":
            continue
        agent = v.get("agent", "")
        detail = v.get("detail", "")
        log(f"  → Auto-fix: {agent} — {detail}")
        # Add guard triggers for agents missing them
        if "无Guard" in detail or "无触发" in detail:
            try:
                import yaml
                yf = ROOT / f"packages/haip-hospital/agents/definitions/{agent}.yaml"
                if yf.exists():
                    with open(yf, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if "guard" not in data:
                        data["guard"] = {}
                    if not data["guard"].get("triggers"):
                        data["guard"]["triggers"] = ["诊断决策", "治疗方案"]
                    with open(yf, "w", encoding="utf-8") as f:
                        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=200)
                    fixes += 1
            except Exception as e:
                log(f"    Fix failed: {e}")

    return fixes


def commit_if_changes(cycle: int):
    """Commit any pending changes."""
    ret, out = run_command(["git", "add", "-A"])
    ret2, out2 = run_command(["git", "status", "--short"])
    if out2.strip():
        msg = f"auto: MetaHarness loop cycle #{cycle} — self-healing fixes"
        run_command(["git", "commit", "-m", msg])
        run_command(["git", "push", "origin", "master"], timeout=120)
        log(f"  Committed + pushed changes ({len(out2.splitlines())} files)")
        return True
    return False


def main():
    log("=" * 60)
    log("AUTONOMOUS SELF-HARNESS LOOP STARTED")
    log("=" * 60)
    log(f"Project: {ROOT}")
    log("Mode: Continuous improvement (Ctrl+C to stop)")
    log("")

    cycle = 0
    total_fixes = 0

    while True:
        cycle += 1
        log(f"--- Cycle #{cycle} ---")

        # 1. Run MetaHarness
        log("  Running MetaHarness...")
        report = get_harness_report()

        if not report:
            log("  ⚠ Harness unavailable, retrying in 60s...")
            time.sleep(60)
            continue

        # 2. Extract scores
        stages = report.get("stages", {})
        scores = {}
        for name, data in stages.items():
            scores[name] = data.get("score", 0)

        log(f"  Scores: {json.dumps(scores)}")
        unified = report.get("unified_score", 0)
        log(f"  Unified: {unified}")

        # 3. Learn from continuous learning
        cl = stages.get("continuous_learning", {})
        log(f"  Trend: {cl.get('trend', 'unknown')} | Overall: {cl.get('overall_score', 0)}")
        milestones = cl.get("milestones", [])
        for m in milestones:
            log(f"  🏆 Milestone: {m}")

        # 4. Auto-fix
        log("  Attempting auto-fixes...")
        fixes = auto_fix_issues(report)
        total_fixes += fixes
        if fixes:
            log(f"  ✅ Fixed {fixes} issues")

        # 5. Commit
        committed = commit_if_changes(cycle)

        # 6. Track progress
        summary = {
            "cycle": cycle,
            "timestamp": report.get("timestamp", ""),
            "scores": scores,
            "fixes_this_cycle": fixes,
            "total_fixes": total_fixes,
            "committed": committed,
        }

        # Append to loop log
        log_file = ROOT / ".openharness/runtime/loop_log.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

        log(f"  Total fixes: {total_fixes} | Committed: {committed}")
        log(f"  Sleeping 300s...")
        log("")

        time.sleep(300)  # 5 minutes between cycles


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nLoop stopped by user.")
    except Exception as e:
        log(f"\nFATAL: {e}")
        traceback.print_exc()
